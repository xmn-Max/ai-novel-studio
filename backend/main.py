import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from database import init_db, row_to_dict, rows_to_list, db_session
from auth import register_user, login_user, verify_token
from auth import get_user_genres, add_user_genre, update_user_genre, delete_user_genre
from file_parser import parse_file, SUPPORTED_EXTENSIONS
from fsm import WorkflowFSM, WorkflowState
from plugins import get_available_plugins
from models import AuthRequest, GenreItem, CreateProjectRequest, UpdateScriptRequest
from services.project_service import ProjectService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

app = FastAPI(title="AI Novel Studio API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

GENRES_FILE = Path(__file__).parent / "genres.json"
UPLOAD_DIR = Path(__file__).parent / "uploads"

tasks: dict[str, dict[str, Any]] = {}
fsm_registry: dict[str, WorkflowFSM] = {}
service = ProjectService(fsm_registry, tasks)

PIPELINE_STEP_NAMES = [
    "文本清洗", "章节检测", "角色提取", "剧情分析",
    "场景规划", "剧本生成", "世界观分析", "校验",
]


def _load_genres() -> list[dict[str, Any]]:
    if GENRES_FILE.exists():
        try:
            return json.loads(GENRES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return [{"name": "叙事", "guidance": "", "keywords": []}]


def _merged_genres(username: str) -> list[dict[str, Any]]:
    system = _load_genres()
    user = get_user_genres(username)
    return [*({**g, "readonly": True} for g in system), *({**g, "readonly": False} for g in user)]


def _deserialize_json_fields(row: dict[str, Any], *fields: str) -> None:
    for field in fields:
        val = row.get(field)
        if isinstance(val, str):
            try:
                row[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass


def _require_auth(authorization: str = Header(default="")) -> dict:
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return user


def _check_auth(token: str) -> dict:
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/steps")
async def pipeline_steps() -> list[str]:
    return PIPELINE_STEP_NAMES


@app.post("/api/auth/register")
async def api_register(req: AuthRequest) -> dict[str, str]:
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(req.username) < 2 or len(req.username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度需在 2-20 之间")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少需要 4 个字符")
    try:
        result = register_user(req.username.strip(), req.password)
        logger.info("User registered: %s", req.username)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/auth/login")
async def api_login(req: AuthRequest) -> dict[str, str]:
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    result = login_user(req.username.strip(), req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    logger.info("User logged in: %s", req.username)
    return result


@app.get("/api/auth/me")
async def api_me(user: dict = Depends(_require_auth)) -> dict:
    return {"username": user["username"], "logged_in": True}


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
    if index < len(system):
        raise HTTPException(status_code=403, detail="系统默认类型不可修改")
    user_index = index - len(system)
    if any(g["name"] == item.name for i, g in enumerate(user_genres) if i != user_index):
        raise HTTPException(status_code=409, detail=f"类型 '{item.name}' 已存在")
    try:
        return update_user_genre(user["username"], user_index, item.name, item.guidance, item.keywords)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/genres/{index}")
async def delete_genre(index: int, user: dict = Depends(_require_auth)) -> dict[str, str]:
    system = _load_genres()
    if index < len(system):
        raise HTTPException(status_code=403, detail="系统默认类型不可删除")
    user_index = index - len(system)
    try:
        deleted_name = delete_user_genre(user["username"], user_index)
        return {"deleted": deleted_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    return await service.create_project(user["username"], req.title, req.genre)


@app.get("/api/projects")
async def list_projects(user: dict = Depends(_require_auth)) -> list[dict[str, Any]]:
    return await service.list_projects(user["username"])


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    async with db_session() as db:
        proj = await db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user["username"]))
        project = row_to_dict(await proj.fetchone())
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        ch_cursor = await db.execute(
            "SELECT * FROM novel_chapters WHERE project_id = ? ORDER BY index_num", (project_id,))
        chapters = rows_to_list(await ch_cursor.fetchall())

        char_cursor = await db.execute(
            "SELECT * FROM project_characters WHERE project_id = ?", (project_id,))
        characters = rows_to_list(await char_cursor.fetchall())
        for c in characters:
            _deserialize_json_fields(c, "traits", "aliases", "relationships")

        plot = row_to_dict(await (await db.execute(
            "SELECT * FROM plot_analysis WHERE project_id = ?", (project_id,))).fetchone())
        if plot:
            _deserialize_json_fields(plot, "sub_lines", "events")

        sp_cursor = await db.execute("SELECT * FROM scene_plan WHERE project_id = ?", (project_id,))
        scene_plan = rows_to_list(await sp_cursor.fetchall())
        for sp in scene_plan:
            _deserialize_json_fields(sp, "event_refs")

        ss_cursor = await db.execute(
            "SELECT * FROM script_scenes WHERE project_id = ? ORDER BY scene_id", (project_id,))
        script_scenes = rows_to_list(await ss_cursor.fetchall())
        for ss in script_scenes:
            _deserialize_json_fields(ss, "characters_present", "action", "dialogues")

        wb = row_to_dict(await (await db.execute(
            "SELECT * FROM world_building WHERE project_id = ?", (project_id,))).fetchone())

        yaml_data = row_to_dict(await (await db.execute(
            "SELECT * FROM project_yaml WHERE project_id = ?", (project_id,))).fetchone())

        pl_cursor = await db.execute("SELECT * FROM plugin_results WHERE project_id = ?", (project_id,))
        plugin_results = rows_to_list(await pl_cursor.fetchall())
        for pr in plugin_results:
            _deserialize_json_fields(pr, "result_data")

        fsm = fsm_registry.get(project_id)
        fsm_state = fsm.to_dict() if fsm else {"state": project.get("state", "IDLE")}

        return {
            "project": project, "chapters": chapters, "characters": characters,
            "plot": plot, "scene_plan": scene_plan, "script_scenes": script_scenes,
            "world_building": wb, "yaml_data": yaml_data,
            "plugin_results": plugin_results, "fsm": fsm_state,
        }


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(_require_auth)) -> dict[str, str]:
    try:
        await service.delete_project(project_id, user["username"])
        return {"deleted": project_id}
    except ValueError:
        raise HTTPException(status_code=404, detail="项目不存在")


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400,
                            detail=f"不支持的文件类型: {ext}。支持: {', '.join(SUPPORTED_EXTENSIONS)}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"文件过大，最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
    try:
        text = parse_file(file.filename, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")
    UPLOAD_DIR.mkdir(exist_ok=True)
    saved_path = UPLOAD_DIR / f"{file.filename}"
    saved_path.write_bytes(content)
    return {"filename": file.filename, "text": text, "char_count": len(text), "saved_path": str(saved_path)}


@app.post("/api/projects/{project_id}/convert")
async def convert_project(
    project_id: str,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(_require_auth),
) -> dict[str, str]:
    file_content = None
    filename = ""
    if file and file.filename:
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail=f"文件过大，最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
        file_content = content
        filename = file.filename
    try:
        task_id = await service.start_conversion(project_id, user["username"], text, file_content, filename)
        return {"task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/convert/{task_id}/progress")
async def progress(task_id: str, token: str):
    _check_auth(token)
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_stream():
        while True:
            t = tasks.get(task_id)
            if t is None:
                break
            pd = t.get("progress", {})
            yield f"data: {json.dumps({**pd, 'status': t.get('status', 'pending'), 'error': t.get('error', '')}, ensure_ascii=False)}\n\n"
            if t.get("status") in ("completed", "failed"):
                break
            import asyncio
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/convert/{task_id}/result")
async def result(task_id: str, user: dict = Depends(_require_auth)):
    t = tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    if t["status"] in ("processing", "pending"):
        raise HTTPException(status_code=202, detail="任务尚未完成")
    if t["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"任务失败: {t.get('error', '未知错误')}")
    return t["result"]


@app.post("/api/projects/{project_id}/plot")
async def run_plot_analysis(
    project_id: str,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    fc = None
    fn = ""
    if file and file.filename:
        fc = await file.read()
        fn = file.filename
    try:
        return await service.run_analysis(project_id, user["username"], "plot", text, fc, fn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/projects/{project_id}/world")
async def run_world_building(
    project_id: str,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    fc = None
    fn = ""
    if file and file.filename:
        fc = await file.read()
        fn = file.filename
    try:
        return await service.run_analysis(project_id, user["username"], "world", text, fc, fn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/plugins")
async def list_plugins() -> list[dict[str, str]]:
    return get_available_plugins()


@app.post("/api/projects/{project_id}/plugins/{plugin_name}")
async def run_plugin(project_id: str, plugin_name: str, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    try:
        return await service.run_plugin(project_id, user["username"], plugin_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/projects/{project_id}/script/{scene_id}")
async def update_script_scene(
    project_id: str, scene_id: int, req: UpdateScriptRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, str]:
    async with db_session() as db:
        proj = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?",
                                (project_id, user["username"]))
        if not await proj.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")
        updates: dict[str, Any] = {}
        for field in ("scene_heading", "location", "time_of_day", "transition"):
            val = getattr(req, field)
            if val is not None:
                updates[field] = val
        for field in ("characters_present", "action", "dialogues"):
            val = getattr(req, field)
            if val is not None:
                updates[field] = json.dumps(val, ensure_ascii=False)
        if not updates:
            raise HTTPException(status_code=400, detail="无修改内容")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id, scene_id]
        await db.execute(
            f"UPDATE script_scenes SET {set_clause} WHERE project_id = ? AND scene_id = ?", values)
        await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), project_id))
        await db.commit()
    return {"updated": f"scene_{scene_id}"}


@app.get("/api/projects/{project_id}/state")
async def get_project_state(project_id: str, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    fsm = fsm_registry.get(project_id)
    if fsm:
        return fsm.to_dict()
    async with db_session() as db:
        row = await db.execute("SELECT state FROM projects WHERE id = ?", (project_id,))
        proj = await row.fetchone()
        return {"state": proj["state"] if proj else "IDLE", "label": proj["state"] if proj else "空闲"}


FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Database initialized OK")
