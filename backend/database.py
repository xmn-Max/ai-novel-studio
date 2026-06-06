from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import aiosqlite
from pathlib import Path

DB_FILE = Path(__file__).parent / "projects.db"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_FILE))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


@asynccontextmanager
async def db_session() -> AsyncIterator[Any]:
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '未命名',
            genre TEXT DEFAULT '叙事',
            state TEXT DEFAULT 'IDLE',
            word_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS novel_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            index_num INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_characters (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT DEFAULT '',
            age TEXT DEFAULT '',
            role TEXT DEFAULT '',
            traits TEXT DEFAULT '[]',
            description TEXT DEFAULT '',
            aliases TEXT DEFAULT '[]',
            relationships TEXT DEFAULT '[]',
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS plot_analysis (
            project_id TEXT PRIMARY KEY,
            theme TEXT DEFAULT '',
            conflict TEXT DEFAULT '',
            climax TEXT DEFAULT '',
            ending TEXT DEFAULT '',
            main_line TEXT DEFAULT '',
            sub_lines TEXT DEFAULT '[]',
            events TEXT DEFAULT '[]',
            pacing TEXT DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scene_plan (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            purpose TEXT DEFAULT '',
            location TEXT DEFAULT '',
            time_of_day TEXT DEFAULT '',
            event_refs TEXT DEFAULT '[]',
            conflict_level TEXT DEFAULT '',
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS script_scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            scene_id INTEGER NOT NULL,
            scene_heading TEXT DEFAULT '',
            location TEXT DEFAULT '',
            time_of_day TEXT DEFAULT '',
            characters_present TEXT DEFAULT '[]',
            action TEXT DEFAULT '[]',
            dialogues TEXT DEFAULT '[]',
            transition TEXT DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS world_building (
            project_id TEXT PRIMARY KEY,
            realms TEXT DEFAULT '[]',
            factions TEXT DEFAULT '[]',
            techniques TEXT DEFAULT '[]',
            items TEXT DEFAULT '[]',
            timeline TEXT DEFAULT '[]',
            rules TEXT DEFAULT '[]',
            raw TEXT DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS plugin_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            plugin_name TEXT NOT NULL,
            result_data TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_yaml (
            project_id TEXT PRIMARY KEY,
            yaml_content TEXT DEFAULT '',
            schema_validation TEXT DEFAULT '{}',
            validation_result TEXT DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """)
        await db.commit()
    finally:
        await db.close()


def row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[aiosqlite.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]
