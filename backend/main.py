import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("[WARNING] DEEPSEEK_API_KEY not found in environment. Please check your .env file.")
else:
    print(f"[INFO] DEEPSEEK_API_KEY loaded (ends with ...{API_KEY[-4:]})")

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TASK_TTL_SECONDS = 3600
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app = FastAPI(title="AI Novel Studio API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Cache-Control"],
    expose_headers=["Content-Type"],
)

GENRES_FILE = Path(__file__).parent / "genres.json"
UPLOAD_DIR = Path(__file__).parent / "uploads"

tasks: dict[str, dict[str, Any]] = {}
tasks_lock = asyncio.Lock()
fsm_registry: dict[str, WorkflowFSM] = {}
service = ProjectService(fsm_registry, tasks)

PIPELINE_STEP_NAMES = [
    "文本清洗", "章节检测", "角色提取", "剧情分析",
    "场景规划", "剧本生成", "世界观分析", "校验",
]

_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_\-.()\u4e00-\u9fff]")


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


def _sanitize_filename(name: str) -> str:
    name = Path(name).name
    if ".." in name:
        name = name.replace("..", "_")
    name = _SAFE_FILENAME_RE.sub("_", name).strip("_")
    return name or "uploaded_file"


async def _cleanup_expired_tasks() -> None:
    async with tasks_lock:
        now = datetime.now()
        expired = [
            tid for tid, t in tasks.items()
            if t.get("status") in ("completed", "failed")
            and (now - datetime.fromisoformat(t.get("_created_at", now.isoformat()))).total_seconds() > TASK_TTL_SECONDS
        ]
        for tid in expired:
            tasks.pop(tid, None)
    if expired:
        logger.info("Cleaned up %d expired tasks", len(expired))


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
    safe_name = _sanitize_filename(file.filename)
    saved_path = UPLOAD_DIR / safe_name
    saved_path.write_bytes(content)
    return {"filename": safe_name, "text": text, "char_count": len(text), "saved_path": str(saved_path)}


@app.post("/api/projects/{project_id}/convert")
async def convert_project(
    project_id: str,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(_require_auth),
) -> dict[str, str]:
    file_content = None
    safe_filename = ""
    if file and file.filename:
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail=f"文件过大，最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
        file_content = content
        safe_filename = _sanitize_filename(file.filename)
    try:
        task_id = await service.start_conversion(project_id, user["username"], text, file_content, safe_filename)
        async with tasks_lock:
            if task_id in tasks:
                tasks[task_id]["_created_at"] = datetime.now().isoformat()
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


class RegenerateRequest(BaseModel):
    feedback: str


class RequeryRequest(BaseModel):
    feedback: str
    target: str = "script"


@app.post("/api/projects/{project_id}/regenerate")
async def regenerate_script(
    project_id: str,
    req: RegenerateRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    if not req.feedback.strip():
        raise HTTPException(status_code=400, detail="请输入修改意见")
    try:
        result = await service.regenerate_script(project_id, user["username"], req.feedback.strip())
        return {"scenes": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/projects/{project_id}/requery")
async def requery_section(
    project_id: str,
    req: RequeryRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    if not req.feedback.strip():
        raise HTTPException(status_code=400, detail="请输入修改意见")
    valid_targets = {"script", "plot", "world", "characters"}
    if req.target not in valid_targets:
        raise HTTPException(status_code=400, detail=f"无效目标，可选: {', '.join(sorted(valid_targets))}")
    try:
        result = await service.requery_section(project_id, user["username"], req.feedback.strip(), req.target)
        return result
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


class UpdateCharacterRequest(BaseModel):
    field: str
    value: str


@app.put("/api/projects/{project_id}/characters/{char_id}")
async def update_character(
    project_id: str, char_id: str, req: UpdateCharacterRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, str]:
    allowed = {"name", "role", "description", "gender", "age"}
    if req.field not in allowed:
        raise HTTPException(status_code=400, detail=f"不允许修改字段: {req.field}")

    async with db_session() as db:
        proj = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?",
                                (project_id, user["username"]))
        if not await proj.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        if req.field == "role":
            allowed_roles = {"protagonist", "supporting", "minor"}
            if req.value not in allowed_roles:
                raise HTTPException(status_code=400, detail=f"无效角色: {req.value}")

            if req.value == "protagonist":
                await db.execute(
                    "UPDATE project_characters SET role = 'supporting' WHERE project_id = ? AND role = 'protagonist'",
                    (project_id,))
            else:
                count = await (await db.execute(
                    "SELECT COUNT(*) FROM project_characters WHERE project_id = ? AND role = 'protagonist' AND id != ?",
                    (project_id, char_id))).fetchone()
                if count[0] == 0:
                    await db.execute(
                        "UPDATE project_characters SET role = 'protagonist' WHERE project_id = ? AND id = (SELECT id FROM project_characters WHERE project_id = ? AND id != ? LIMIT 1)",
                        (project_id, project_id, char_id))

        await db.execute(
            f"UPDATE project_characters SET {req.field} = ? WHERE project_id = ? AND id = ?",
            (req.value, project_id, char_id))
        await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), project_id))
        await db.commit()
    return {"updated": char_id}


class UpdatePlotRequest(BaseModel):
    field: str
    value: str


@app.put("/api/projects/{project_id}/plot")
async def update_plot_field(
    project_id: str, req: UpdatePlotRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, str]:
    allowed = {"theme", "conflict", "climax", "ending", "main_line", "pacing"}
    if req.field not in allowed:
        raise HTTPException(status_code=400, detail=f"不允许修改字段: {req.field}")

    async with db_session() as db:
        proj = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?",
                                (project_id, user["username"]))
        if not await proj.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        exists = await (await db.execute(
            "SELECT project_id FROM plot_analysis WHERE project_id = ?", (project_id,))).fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO plot_analysis (project_id, theme, conflict, climax, ending, main_line, sub_lines, events, pacing) VALUES (?, '', '', '', '', '', '[]', '[]', '')",
                (project_id,))

        await db.execute(
            f"UPDATE plot_analysis SET {req.field} = ? WHERE project_id = ?",
            (req.value, project_id))
        await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), project_id))
        await db.commit()
    return {"updated": req.field}


class SaveVersionRequest(BaseModel):
    feedback: str = ""


@app.post("/api/projects/{project_id}/versions")
async def save_version(
    project_id: str, req: SaveVersionRequest,
    user: dict = Depends(_require_auth),
) -> dict[str, Any]:
    async with db_session() as db:
        proj = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?",
                                (project_id, user["username"]))
        if not await proj.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # Gather current snapshot
        chars = rows_to_list(await (await db.execute(
            "SELECT * FROM project_characters WHERE project_id = ?", (project_id,))).fetchall())
        for c in chars:
            _deserialize_json_fields(c, "traits", "aliases", "relationships")

        plot = row_to_dict(await (await db.execute(
            "SELECT * FROM plot_analysis WHERE project_id = ?", (project_id,))).fetchone())
        if plot:
            _deserialize_json_fields(plot, "sub_lines", "events")

        sp_list = rows_to_list(await (await db.execute(
            "SELECT * FROM scene_plan WHERE project_id = ?", (project_id,))).fetchall())
        for sp in sp_list:
            _deserialize_json_fields(sp, "event_refs")

        ss_list = rows_to_list(await (await db.execute(
            "SELECT * FROM script_scenes WHERE project_id = ? ORDER BY scene_id", (project_id,))).fetchall())
        for ss in ss_list:
            _deserialize_json_fields(ss, "characters_present", "action", "dialogues")

        yaml_row = await (await db.execute(
            "SELECT yaml_content FROM project_yaml WHERE project_id = ?", (project_id,))).fetchone()

        wb_row = await (await db.execute(
            "SELECT * FROM world_building WHERE project_id = ?", (project_id,))).fetchone()

        snapshot = json.dumps({
            "characters": chars, "plot": plot, "events": plot.get("events", []) if plot else [],
            "scene_plan": sp_list, "script_scenes": ss_list,
            "yaml_content": yaml_row["yaml_content"] if yaml_row else "",
            "world_building": row_to_dict(wb_row) if wb_row else None,
        }, ensure_ascii=False)

        # Count versions for label and cleanup
        count_row = await (await db.execute(
            "SELECT COUNT(*) FROM project_versions WHERE project_id = ?", (project_id,))).fetchone()
        count = count_row[0] if count_row else 0

        # Delete oldest if >= 10
        if count >= 10:
            await db.execute(
                "DELETE FROM project_versions WHERE id = (SELECT id FROM project_versions WHERE project_id = ? ORDER BY timestamp_ms ASC LIMIT 1)",
                (project_id,))

        now = datetime.now()
        version_id = f"V{now.strftime('%y%m%d%H%M%S')}"
        label = f"V{count + 1} - {now.strftime('%Y-%m-%d %H:%M:%S')}"
        ts_ms = int(now.timestamp() * 1000)

        await db.execute(
            "INSERT INTO project_versions (id, project_id, label, timestamp_ms, feedback, snapshot) VALUES (?, ?, ?, ?, ?, ?)",
            (version_id, project_id, label, ts_ms, req.feedback, snapshot))
        await db.commit()

    return {"version_id": version_id, "label": label, "count": count + 1}


@app.get("/api/projects/{project_id}/versions")
async def list_versions(project_id: str, user: dict = Depends(_require_auth)) -> list[dict[str, Any]]:
    async with db_session() as db:
        cursor = await db.execute(
            "SELECT id, label, timestamp_ms, feedback FROM project_versions WHERE project_id = ? ORDER BY timestamp_ms DESC",
            (project_id,))
        rows = await cursor.fetchall()
    return [{"version_id": r["id"], "label": r["label"], "timestamp_ms": r["timestamp_ms"],
             "feedback": r["feedback"]} for r in rows]


@app.get("/api/projects/{project_id}/versions/{version_id}")
async def get_version(project_id: str, version_id: str, user: dict = Depends(_require_auth)) -> dict[str, Any]:
    async with db_session() as db:
        row = await (await db.execute(
            "SELECT * FROM project_versions WHERE project_id = ? AND id = ?",
            (project_id, version_id))).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="版本不存在")
        return {"version_id": row["id"], "label": row["label"],
                "timestamp_ms": row["timestamp_ms"], "feedback": row["feedback"],
                "snapshot": json.loads(row["snapshot"])}


@app.post("/api/projects/{project_id}/versions/{version_id}/restore")
async def restore_version(project_id: str, version_id: str, user: dict = Depends(_require_auth)) -> dict[str, str]:
    async with db_session() as db:
        row = await (await db.execute(
            "SELECT snapshot FROM project_versions WHERE project_id = ? AND id = ?",
            (project_id, version_id))).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="版本不存在")

        snap = json.loads(row["snapshot"])

        # Restore characters
        await db.execute("DELETE FROM project_characters WHERE project_id = ?", (project_id,))
        for c in snap.get("characters", []):
            await db.execute(
                "INSERT INTO project_characters (id, project_id, name, gender, age, role, traits, description, aliases, relationships) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c.get("id", ""), project_id, c.get("name", ""),
                 c.get("gender", ""), c.get("age", ""), c.get("role", ""),
                 json.dumps(c.get("traits", []) if isinstance(c.get("traits"), list) else [], ensure_ascii=False),
                 c.get("description", ""),
                 json.dumps(c.get("aliases", []) if isinstance(c.get("aliases"), list) else [], ensure_ascii=False),
                 json.dumps(c.get("relationships", []) if isinstance(c.get("relationships"), list) else [], ensure_ascii=False)))

        # Restore plot
        plot = snap.get("plot") or {}
        await db.execute("DELETE FROM plot_analysis WHERE project_id = ?", (project_id,))
        await db.execute(
            "INSERT INTO plot_analysis (project_id, theme, conflict, climax, ending, main_line, sub_lines, events, pacing) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, plot.get("theme", ""), plot.get("conflict", ""),
             plot.get("climax", ""), plot.get("ending", ""), plot.get("main_line", ""),
             json.dumps(plot.get("sub_lines", []) if isinstance(plot.get("sub_lines"), list) else [], ensure_ascii=False),
             json.dumps(snap.get("events", []) if isinstance(snap.get("events"), list) else [], ensure_ascii=False),
             plot.get("pacing", "")))

        # Restore scene plan
        await db.execute("DELETE FROM scene_plan WHERE project_id = ?", (project_id,))
        for sp in snap.get("scene_plan", []):
            await db.execute(
                "INSERT INTO scene_plan (id, project_id, scene_id, purpose, location, time_of_day, event_refs, conflict_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sp.get("id", ""), project_id, sp.get("scene_id", ""),
                 sp.get("purpose", ""), sp.get("location", ""), sp.get("time_of_day", ""),
                 json.dumps(sp.get("event_refs", []) if isinstance(sp.get("event_refs"), list) else [], ensure_ascii=False),
                 sp.get("conflict_level", "")))

        # Restore script scenes
        await db.execute("DELETE FROM script_scenes WHERE project_id = ?", (project_id,))
        for ss in snap.get("script_scenes", []):
            await db.execute(
                "INSERT INTO script_scenes (project_id, scene_id, scene_heading, location, time_of_day, characters_present, action, dialogues, transition) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, ss.get("scene_id", 0), ss.get("scene_heading", ""),
                 ss.get("location", ""), ss.get("time_of_day", ""),
                 json.dumps(ss.get("characters_present", []) if isinstance(ss.get("characters_present"), list) else [], ensure_ascii=False),
                 json.dumps(ss.get("action", []) if isinstance(ss.get("action"), list) else [], ensure_ascii=False),
                 json.dumps(ss.get("dialogues", []) if isinstance(ss.get("dialogues"), list) else [], ensure_ascii=False),
                 ss.get("transition", "")))

        # Restore YAML content
        if snap.get("yaml_content"):
            await db.execute("DELETE FROM project_yaml WHERE project_id = ?", (project_id,))
            await db.execute(
                "INSERT INTO project_yaml (project_id, yaml_content, schema_validation, validation_result) VALUES (?, ?, ?, ?)",
                (project_id, snap["yaml_content"], "{}", "{}"))

        # Restore world building
        wb = snap.get("world_building")
        if wb and isinstance(wb, dict):
            await db.execute("DELETE FROM world_building WHERE project_id = ?", (project_id,))
            for field in ("realms", "factions", "techniques", "items", "timeline", "rules"):
                val = wb.get(field, [])
                if isinstance(val, str):
                    wb[field] = json.loads(val)
            await db.execute(
                "INSERT INTO world_building (project_id, realms, factions, techniques, items, timeline, rules, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id,
                 json.dumps(wb.get("realms", []), ensure_ascii=False),
                 json.dumps(wb.get("factions", []), ensure_ascii=False),
                 json.dumps(wb.get("techniques", []), ensure_ascii=False),
                 json.dumps(wb.get("items", []), ensure_ascii=False),
                 json.dumps(wb.get("timeline", []), ensure_ascii=False),
                 json.dumps(wb.get("rules", []), ensure_ascii=False),
                 json.dumps({}, ensure_ascii=False)))

        await db.execute("UPDATE projects SET updated_at = ?, state = 'COMPLETED' WHERE id = ?",
                         (datetime.now().isoformat(), project_id))
        await db.commit()

    return {"restored": version_id}


FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(_periodic_cleanup())
    logger.info("Database initialized OK")


async def _periodic_cleanup() -> None:
    while True:
        await asyncio.sleep(600)
        await _cleanup_expired_tasks()
