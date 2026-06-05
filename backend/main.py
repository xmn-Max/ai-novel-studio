from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models import ConvertRequest, ConvertResponse
from pipeline import Pipeline
from auth import register_user, login_user, verify_token
from auth import get_user_genres, add_user_genre, update_user_genre, delete_user_genre

app = FastAPI(title="AI Novel Studio API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks: dict[str, dict[str, Any]] = {}
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GENRES_FILE = Path(__file__).parent / "genres.json"


def _load_genres() -> list[dict[str, Any]]:
    if GENRES_FILE.exists():
        try:
            return json.loads(GENRES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return [{"name": "叙事", "guidance": "这是一部叙事小说。请重点关注故事结构、人物心理。", "keywords": []}]


def _merged_genres(username: str) -> list[dict[str, Any]]:
    system = _load_genres()
    user = get_user_genres(username)
    result: list[dict[str, Any]] = []
    for g in system:
        result.append({**g, "readonly": True})
    for g in user:
        result.append({**g, "readonly": False})
    return result


def _get_pipeline(genre: str = "叙事") -> Pipeline:
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")
    return Pipeline(api_key=API_KEY, genre=genre)


async def _run_pipeline(task_id: str, text: str, genre: str) -> None:
    pipeline = _get_pipeline(genre)
    tasks[task_id]["status"] = "processing"

    async def progress_callback(step: int, total: int, step_name: str, message: str) -> None:
        tasks[task_id]["progress"] = {
            "step": step,
            "total": total,
            "step_name": step_name,
            "message": message,
        }

    try:
        result = await pipeline.run(text, progress_callback)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


def _require_auth(authorization: str = Header(default="")) -> dict:
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return user


def _check_auth(token: str = "") -> dict:
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


# --- Auth ---

class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
async def api_register(req: AuthRequest) -> dict[str, str]:
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(req.username) < 2 or len(req.username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度需在 2-20 之间")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少需要 4 个字符")
    try:
        return register_user(req.username.strip(), req.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/auth/login")
async def api_login(req: AuthRequest) -> dict[str, str]:
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    result = login_user(req.username.strip(), req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return result


@app.get("/api/auth/me")
async def api_me(user: dict = Depends(_require_auth)) -> dict:
    return {"username": user["username"], "logged_in": True}


# --- Genre CRUD (per-user) ---

class GenreItem(BaseModel):
    name: str
    guidance: str = ""
    keywords: list[str] = []


@app.get("/api/genres")
async def list_genres(user: dict = Depends(_require_auth)) -> list[dict[str, Any]]:
    return _merged_genres(user["username"])


@app.post("/api/genres")
async def add_genre(item: GenreItem, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    all_genres = _merged_genres(user["username"])
    if any(g["name"] == item.name for g in all_genres):
        raise HTTPException(status_code=409, detail=f"类型 '{item.name}' 已存在")
    try:
        return add_user_genre(user["username"], item.name, item.guidance, item.keywords)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/genres/{index}")
async def update_genre(index: int, item: GenreItem, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    system = _load_genres()
    user_genres = get_user_genres(user["username"])
    system_len = len(system)

    if index < system_len:
        raise HTTPException(status_code=403, detail="系统默认类型不可修改")

    user_index = index - system_len
    all_user_names = {g["name"] for i, g in enumerate(user_genres) if i != user_index}
    if item.name in all_user_names:
        raise HTTPException(status_code=409, detail=f"类型 '{item.name}' 已存在")

    try:
        return update_user_genre(user["username"], user_index, item.name, item.guidance, item.keywords)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/genres/{index}")
async def delete_genre(index: int, user: dict = Depends(_require_auth)) -> dict[str, str]:
    system = _load_genres()
    system_len = len(system)

    if index < system_len:
        raise HTTPException(status_code=403, detail="系统默认类型不可删除")

    user_index = index - system_len
    try:
        deleted_name = delete_user_genre(user["username"], user_index)
        return {"deleted": deleted_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Conversion ---

@app.post("/api/convert", response_model=ConvertResponse)
async def convert(request: ConvertRequest, user: dict = Depends(_require_auth)) -> ConvertResponse:
    text = request.text.strip()
    if len(text) < 100:
        raise HTTPException(status_code=400, detail="文本内容过短，至少需要 100 个字符")

    genre = request.genre.strip()
    genres = _load_genres()
    valid_names = {g["name"] for g in genres}
    if genre not in valid_names:
        genre = genres[0]["name"] if genres else "叙事"

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "progress": {
            "step": 0,
            "total": 7,
            "step_name": "初始化",
            "message": "任务已创建，等待处理...",
        },
        "result": None,
    }

    asyncio.create_task(_run_pipeline(task_id, text, genre))
    return ConvertResponse(task_id=task_id)


@app.get("/api/convert/{task_id}/progress")
async def progress(task_id: str, token: str = ""):
    _check_auth(token)
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_stream():
        while True:
            task = tasks.get(task_id)
            if task is None:
                break

            progress_data = task.get("progress", {})
            status = task.get("status", "pending")
            error = task.get("error", "")

            event_data = {
                **progress_data,
                "status": status,
                "error": error,
            }

            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            if status in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/convert/{task_id}/result")
async def result(task_id: str, user: dict = Depends(_require_auth)):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] == "processing" or task["status"] == "pending":
        raise HTTPException(status_code=202, detail="任务尚未完成")

    if task["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"任务失败: {task.get('error', '未知错误')}")

    return task["result"]
