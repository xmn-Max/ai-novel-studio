from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from database import db_session
from pipeline import Pipeline, TOTAL_STEPS
from fsm import WorkflowFSM, WorkflowState

logger = logging.getLogger(__name__)


def _build_project_id() -> str:
    return f"P{datetime.now().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


async def _insert_world(db, pid: str, wb: dict[str, Any]) -> None:
    await db.execute(
        "INSERT INTO world_building (project_id, realms, factions, techniques, items, timeline, rules, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (pid,
         json.dumps(wb.get("realms", []), ensure_ascii=False),
         json.dumps(wb.get("factions", []), ensure_ascii=False),
         json.dumps(wb.get("techniques", []), ensure_ascii=False),
         json.dumps(wb.get("items", []), ensure_ascii=False),
         json.dumps(wb.get("timeline", []), ensure_ascii=False),
         json.dumps(wb.get("rules", []), ensure_ascii=False),
         json.dumps(wb.get("raw", {}), ensure_ascii=False)))


class ProjectService:
    def __init__(self, fsm_registry: dict[str, WorkflowFSM], tasks: dict[str, dict[str, Any]]) -> None:
        self.fsm_registry = fsm_registry
        self.tasks = tasks

    async def create_project(self, username: str, title: str, genre: str) -> dict[str, Any]:
        project_id = _build_project_id()
        now = datetime.now().isoformat()
        async with db_session() as db:
            await db.execute(
                "INSERT INTO projects (id, user_id, title, genre, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, username, title, genre, "IDLE", now, now))
            await db.commit()
        self.fsm_registry[project_id] = WorkflowFSM(WorkflowState.IDLE)
        logger.info("Project created: %s by %s", project_id, username)
        return {"project_id": project_id, "title": title, "genre": genre, "state": "IDLE"}

    async def list_projects(self, username: str) -> list[dict[str, Any]]:
        from database import rows_to_list
        async with db_session() as db:
            cursor = await db.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC", (username,))
            return rows_to_list(await cursor.fetchall())

    async def delete_project(self, project_id: str, username: str) -> None:
        async with db_session() as db:
            cursor = await db.execute(
                "DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, username))
            await db.commit()
            if cursor.rowcount == 0:
                raise ValueError("项目不存在")
        self.fsm_registry.pop(project_id, None)

    async def start_conversion(
        self, project_id: str, username: str, text: str,
        file_content: bytes | None = None, filename: str = "",
    ) -> str:
        from file_parser import parse_file
        if file_content and filename:
            text = parse_file(filename, file_content)
        if not text or len(text.strip()) < 100:
            raise ValueError("文本内容过短，至少需要 100 个字符")

        async with db_session() as db:
            row = await db.execute(
                "SELECT genre FROM projects WHERE id = ? AND user_id = ?", (project_id, username))
            proj = await row.fetchone()
            if not proj:
                raise ValueError("项目不存在")
            genre = proj["genre"]

        fsm = self.fsm_registry.get(project_id) or WorkflowFSM()
        fsm.circuit_breaker(WorkflowState.UPLOADING, [WorkflowState.IDLE, WorkflowState.COMPLETED, WorkflowState.FAILED])
        self.fsm_registry[project_id] = fsm

        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "project_id": project_id,
            "status": "pending",
            "progress": {"step": 0, "total": TOTAL_STEPS, "step_name": "初始化", "message": "任务已创建"},
            "result": None,
        }
        asyncio.create_task(self._run_pipeline(task_id, project_id, text, genre))
        return task_id

    async def _run_pipeline(self, task_id: str, project_id: str, text: str, genre: str) -> None:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        pipeline = Pipeline(api_key=api_key, genre=genre)
        fsm = self.fsm_registry.get(project_id) or WorkflowFSM()
        self.fsm_registry[project_id] = fsm

        state_sequence = [
            WorkflowState.UPLOADING, WorkflowState.PARSING, WorkflowState.ANALYZING,
            WorkflowState.PLANNING_SCENES, WorkflowState.GENERATING_SCRIPT, WorkflowState.VALIDATING,
        ]

        async def progress_callback(step: int, total: int, step_name: str, message: str) -> None:
            if task_id in self.tasks:
                self.tasks[task_id]["progress"] = {
                    "step": step, "total": total, "step_name": step_name, "message": message}
            idx = step - 1
            if 0 <= idx < len(state_sequence):
                try:
                    fsm.transition(state_sequence[idx])
                except Exception:
                    fsm.circuit_breaker(state_sequence[idx], [s for s in WorkflowState])

        self.tasks[task_id]["status"] = "processing"
        try:
            logger.info("Pipeline start: project=%s genre=%s", project_id, genre)
            result = await pipeline.run_full(text, progress_callback)
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["result"] = result
            fsm.transition(WorkflowState.COMPLETED)
            await self._persist(project_id, result)
            logger.info("Pipeline complete: project=%s", project_id)
        except Exception as e:
            logger.exception("Pipeline failed: project=%s", project_id)
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)
            fsm.circuit_breaker(WorkflowState.FAILED, [s for s in WorkflowState])

    async def _persist(self, project_id: str, result: dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        meta = result.get("meta", {})
        async with db_session() as db:
            await db.execute("UPDATE projects SET state = ?, updated_at = ? WHERE id = ?",
                             ("COMPLETED", now, project_id))
            await db.execute("DELETE FROM novel_chapters WHERE project_id = ?", (project_id,))
            for ch in result.get("chapters", []):
                await db.execute(
                    "INSERT INTO novel_chapters (project_id, index_num, title, content, word_count) VALUES (?, ?, ?, ?, ?)",
                    (project_id, ch["index"], ch["title"], ch["content"], ch.get("char_count", 0)))
            await db.execute("DELETE FROM project_characters WHERE project_id = ?", (project_id,))
            for c in result.get("characters", []):
                await db.execute(
                    "INSERT INTO project_characters (id, project_id, name, gender, age, role, traits, description, aliases, relationships) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (c.get("id", ""), project_id, c.get("name", ""),
                     c.get("gender", ""), c.get("age", ""), c.get("role", ""),
                     json.dumps(c.get("traits", []), ensure_ascii=False),
                     c.get("description", ""),
                     json.dumps(c.get("aliases", []), ensure_ascii=False),
                     json.dumps(c.get("relationships", []), ensure_ascii=False)))
            plot = result.get("plot", {})
            await db.execute("DELETE FROM plot_analysis WHERE project_id = ?", (project_id,))
            await db.execute(
                "INSERT INTO plot_analysis (project_id, theme, conflict, climax, ending, main_line, sub_lines, events, pacing) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, plot.get("theme", ""), plot.get("conflict", ""),
                 plot.get("climax", ""), plot.get("ending", ""),
                 plot.get("main_line", ""),
                 json.dumps(plot.get("sub_lines", []), ensure_ascii=False),
                 json.dumps(plot.get("events", []), ensure_ascii=False),
                 plot.get("pacing", "")))
            scene_plan = result.get("scene_plan", [])
            await db.execute("DELETE FROM scene_plan WHERE project_id = ?", (project_id,))
            for sp in scene_plan:
                await db.execute(
                    "INSERT INTO scene_plan (id, project_id, scene_id, purpose, location, time_of_day, event_refs, conflict_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (sp.get("id", ""), project_id, sp.get("scene_id", ""),
                     sp.get("purpose", ""), sp.get("location", ""), sp.get("time_of_day", ""),
                     json.dumps(sp.get("event_refs", []), ensure_ascii=False),
                     sp.get("conflict_level", "")))
            await db.execute("DELETE FROM script_scenes WHERE project_id = ?", (project_id,))
            await db.execute("DELETE FROM world_building WHERE project_id = ?", (project_id,))
            await _insert_world(db, project_id, result.get("world_building", {}))
            await db.execute("DELETE FROM project_yaml WHERE project_id = ?", (project_id,))
            await db.execute(
                "INSERT INTO project_yaml (project_id, yaml_content, schema_validation, validation_result) VALUES (?, ?, ?, ?)",
                (project_id, result.get("yaml", ""),
                 json.dumps(meta.get("schema_validation", {}), ensure_ascii=False),
                 json.dumps(meta.get("validation", {}), ensure_ascii=False)))
            await db.commit()

    async def run_analysis(self, project_id: str, username: str, analysis_type: str,
                           text: str = "", file_content: bytes | None = None,
                           filename: str = "") -> dict[str, Any]:
        from file_parser import parse_file
        if file_content and filename:
            text = parse_file(filename, file_content)
        if not text or len(text.strip()) < 100:
            raise ValueError("文本过短")

        async with db_session() as db:
            row = await db.execute(
                "SELECT genre FROM projects WHERE id = ? AND user_id = ?", (project_id, username))
            proj = await row.fetchone()
            genre = proj["genre"] if proj else "叙事"

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        pipeline = Pipeline(api_key=api_key, genre=genre)

        result: dict[str, Any] = {}
        if analysis_type == "plot":
            result = await pipeline.run_plot_analysis(text)
            async with db_session() as db:
                await db.execute("DELETE FROM plot_analysis WHERE project_id = ?", (project_id,))
                await db.execute(
                    "INSERT INTO plot_analysis (project_id, theme, conflict, climax, ending, main_line, sub_lines, events, pacing) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (project_id, result.get("theme", ""), result.get("conflict", ""),
                     result.get("climax", ""), result.get("ending", ""),
                     result.get("main_line", ""),
                     json.dumps(result.get("sub_lines", []), ensure_ascii=False),
                     json.dumps(result.get("events", []), ensure_ascii=False),
                     result.get("pacing", "")))
                await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?",
                                 (datetime.now().isoformat(), project_id))
                await db.commit()
        elif analysis_type == "world":
            result = await pipeline.run_world_building(text)
            async with db_session() as db:
                await db.execute("DELETE FROM world_building WHERE project_id = ?", (project_id,))
                await _insert_world(db, project_id, result)
                await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?",
                                 (datetime.now().isoformat(), project_id))
                await db.commit()
        else:
            raise ValueError(f"未知分析类型: {analysis_type}")
        return result

    async def run_plugin(self, project_id: str, username: str, plugin_name: str) -> dict[str, Any]:
        from plugins import create_plugin
        from database import rows_to_list

        async with db_session() as db:
            row = await db.execute(
                "SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, username))
            proj = await row.fetchone()
            if not proj:
                raise ValueError("项目不存在")
            project = dict(proj)
            char_cursor = await db.execute(
                "SELECT * FROM project_characters WHERE project_id = ?", (project_id,))
            characters = rows_to_list(await char_cursor.fetchall())
            yaml_row = await db.execute(
                "SELECT yaml_content FROM project_yaml WHERE project_id = ?", (project_id,))
            yaml_data = await yaml_row.fetchone()
            yaml_content = yaml_data["yaml_content"] if yaml_data else ""

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        pipeline = Pipeline(api_key=api_key, genre=project["genre"])
        plugin = create_plugin(plugin_name, pipeline.client, pipeline.model, pipeline.genre_guidance)
        if not plugin:
            raise ValueError(f"未知插件: {plugin_name}")

        result = await plugin.run({"characters": characters, "yaml_content": yaml_content})

        async with db_session() as db:
            await db.execute(
                "INSERT INTO plugin_results (project_id, plugin_name, result_data, created_at) VALUES (?, ?, ?, ?)",
                (project_id, plugin_name, json.dumps(result, ensure_ascii=False), datetime.now().isoformat()))
            await db.commit()
        return result
