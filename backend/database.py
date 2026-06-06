from __future__ import annotations

<<<<<<< HEAD
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent / "app.db"
GENRES_JSON = Path(__file__).parent / "genres.json"
USERS_JSON = Path(__file__).parent / "users.json"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            token TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            guidance TEXT DEFAULT '',
            keywords TEXT DEFAULT '[]',
            is_system INTEGER DEFAULT 0,
            username TEXT
        );

        CREATE TABLE IF NOT EXISTS conversions (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            title TEXT DEFAULT '',
            genre TEXT DEFAULT '叙事',
            original_text TEXT NOT NULL,
            cleaned_text TEXT,
            yaml_output TEXT,
            meta_json TEXT,
            intermediate_json TEXT,
            status TEXT DEFAULT 'pending',
            progress_json TEXT,
            error TEXT,
            hints TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        );
    """)
    conn.commit()
    conn.close()

    _seed_system_genres()
    _migrate_users_if_needed()


def _seed_system_genres() -> None:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM genres WHERE is_system=1").fetchone()
    if row["cnt"] > 0:
        conn.close()
        return

    system_genres: list[dict[str, Any]] = []
    if GENRES_JSON.exists():
        try:
            system_genres = json.loads(GENRES_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if not system_genres:
        system_genres = [
            {"name": "武侠", "guidance": "这是一部武侠小说。请重点关注武功描写、江湖恩怨、侠义精神。", "keywords": ["侠", "剑", "江湖", "掌门", "弟子"]},
            {"name": "玄幻", "guidance": "这是一部玄幻小说。请重点关注修炼体系、奇幻元素、世界观构建。", "keywords": ["修士", "灵力", "神", "魔", "仙"]},
            {"name": "科幻", "guidance": "这是一部科幻小说。请重点关注科技设定、未来世界观、理性逻辑。", "keywords": ["科学家", "AI", "飞船", "星际", "基地"]},
            {"name": "言情", "guidance": "这是一部言情小说。请重点关注情感发展、人物关系、内心独白。", "keywords": ["爱", "情", "婚", "恋", "心"]},
            {"name": "叙事", "guidance": "这是一部叙事小说。请重点关注故事结构、人物心理。", "keywords": []},
            {"name": "魔幻", "guidance": "这是一部魔幻小说。请重点关注魔法体系、种族设定、史诗叙事。", "keywords": ["魔法", "龙", "精灵", "巫师", "诅咒"]},
        ]

    for g in system_genres:
        conn.execute(
            "INSERT INTO genres (name, guidance, keywords, is_system) VALUES (?, ?, ?, 1)",
            (g["name"], g.get("guidance", ""), json.dumps(g.get("keywords", []), ensure_ascii=False)),
        )
    conn.commit()
    conn.close()


def _migrate_users_if_needed() -> None:
    if not USERS_JSON.exists():
        return

    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    if row["cnt"] > 0:
        # Check if migration already done
        already = conn.execute("SELECT COUNT(*) as cnt FROM genres WHERE is_system=0").fetchone()
        if already["cnt"] > 0:
            conn.close()
            return

    try:
        users = json.loads(USERS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        conn.close()
        return

    for u in users:
        existing = conn.execute("SELECT id FROM users WHERE username=?", (u["username"],)).fetchone()
        if existing:
            conn.execute("UPDATE users SET token=? WHERE username=?", (u.get("token", ""), u["username"]))

            for g in u.get("genres", []):
                gen_exists = conn.execute(
                    "SELECT id FROM genres WHERE name=? AND username=? AND is_system=0",
                    (g["name"], u["username"]),
                ).fetchone()
                if not gen_exists:
                    conn.execute(
                        "INSERT INTO genres (name, guidance, keywords, is_system, username) VALUES (?, ?, ?, 0, ?)",
                        (g["name"], g.get("guidance", ""), json.dumps(g.get("keywords", []), ensure_ascii=False), u["username"]),
                    )
        else:
            conn.execute(
                "INSERT INTO users (username, password_hash, token, created_at) VALUES (?, ?, ?, ?)",
                (u["username"], u["password_hash"], u.get("token", ""), u.get("created_at", datetime.now().isoformat())),
            )

            for g in u.get("genres", []):
                conn.execute(
                    "INSERT INTO genres (name, guidance, keywords, is_system, username) VALUES (?, ?, ?, 0, ?)",
                    (g["name"], g.get("guidance", ""), json.dumps(g.get("keywords", []), ensure_ascii=False), u["username"]),
                )

    conn.commit()

    try:
        backup = USERS_JSON.with_suffix(".json.bak")
        USERS_JSON.rename(backup)
    except OSError:
        pass

    conn.close()


# ── User operations ──

def db_create_user(username: str, password_hash: str, token: str) -> dict[str, str]:
    conn = get_db()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, token, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, token, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("用户名已存在")
    conn.close()
    return {"username": username, "token": token, "created_at": now}


def db_get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def db_get_user_by_token(token: str) -> Optional[dict[str, Any]]:
    if not token:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def db_update_user_token(username: str, token: str) -> None:
    conn = get_db()
    conn.execute("UPDATE users SET token=? WHERE username=?", (token, username))
    conn.commit()
    conn.close()


# ── Genre operations ──

def db_get_system_genres() -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM genres WHERE is_system=1 ORDER BY id").fetchall()
    conn.close()
    result: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["keywords"] = json.loads(d["keywords"])
        except (json.JSONDecodeError, TypeError):
            d["keywords"] = []
        result.append(d)
    return result


def db_get_user_genres(username: str) -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM genres WHERE is_system=0 AND username=? ORDER BY id", (username,)
    ).fetchall()
    conn.close()
    result: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["keywords"] = json.loads(d["keywords"])
        except (json.JSONDecodeError, TypeError):
            d["keywords"] = []
        result.append(d)
    return result


def db_count_user_genres(username: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM genres WHERE is_system=0 AND username=?", (username,)
    ).fetchone()
    conn.close()
    return row["cnt"]


def db_add_user_genre(username: str, name: str, guidance: str, keywords: list[str]) -> dict[str, Any]:
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM genres WHERE name=? AND (is_system=1 OR (is_system=0 AND username=?))",
        (name, username),
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"类型 '{name}' 已存在")

    kw_json = json.dumps(keywords, ensure_ascii=False)
    conn.execute(
        "INSERT INTO genres (name, guidance, keywords, is_system, username) VALUES (?, ?, ?, 0, ?)",
        (name, guidance, kw_json, username),
    )
    conn.commit()
    conn.close()
    return {"name": name, "guidance": guidance, "keywords": keywords}


def db_update_user_genre(username: str, index: int, name: str, guidance: str, keywords: list[str]) -> dict[str, Any]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name FROM genres WHERE is_system=0 AND username=? ORDER BY id", (username,)
    ).fetchall()
    if index < 0 or index >= len(rows):
        conn.close()
        raise ValueError("类型不存在")

    kw_json = json.dumps(keywords, ensure_ascii=False)
    genre_id = rows[index]["id"]
    conn.execute(
        "UPDATE genres SET name=?, guidance=?, keywords=? WHERE id=?",
        (name, guidance, kw_json, genre_id),
    )
    conn.commit()
    conn.close()
    return {"name": name, "guidance": guidance, "keywords": keywords}


def db_delete_user_genre(username: str, index: int) -> str:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name FROM genres WHERE is_system=0 AND username=? ORDER BY id", (username,)
    ).fetchall()
    if index < 0 or index >= len(rows):
        conn.close()
        raise ValueError("类型不存在")

    genre_id = rows[index]["id"]
    deleted_name = rows[index]["name"]
    conn.execute("DELETE FROM genres WHERE id=?", (genre_id,))
    conn.commit()
    conn.close()
    return deleted_name


# ── Conversion operations ──

def db_create_conversion(
    task_id: str,
    username: str,
    original_text: str,
    genre: str,
    title: str,
) -> None:
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO conversions (id, username, title, genre, original_text, status, progress_json, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'pending', '{}', ?, ?)""",
        (task_id, username, title, genre, original_text, now, now),
    )
    conn.commit()
    conn.close()


def db_update_conversion_progress(task_id: str, progress: dict[str, Any]) -> None:
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE conversions SET progress_json=?, updated_at=? WHERE id=?",
        (json.dumps(progress, ensure_ascii=False), now, task_id),
    )
    conn.commit()
    conn.close()


def db_update_conversion_status(task_id: str, status: str, error: str = "") -> None:
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE conversions SET status=?, error=?, updated_at=? WHERE id=?",
        (status, error, now, task_id),
    )
    conn.commit()
    conn.close()


def db_save_conversion_result(
    task_id: str,
    yaml_output: str,
    meta_json: str,
    intermediate_json: str,
    cleaned_text: str,
) -> None:
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE conversions
           SET status='completed', yaml_output=?, meta_json=?, intermediate_json=?,
               cleaned_text=?, updated_at=?
           WHERE id=?""",
        (yaml_output, meta_json, intermediate_json, cleaned_text, now, task_id),
    )
    conn.commit()
    conn.close()


def db_get_conversion(task_id: str) -> Optional[dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM conversions WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        for key in ("meta_json", "intermediate_json", "progress_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = {}
        return d
    return None


def db_list_conversions(username: str, limit: int = 50) -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, genre, status, created_at, updated_at FROM conversions WHERE username=? ORDER BY updated_at DESC LIMIT ?",
        (username, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_delete_conversion(task_id: str, username: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM conversions WHERE id=? AND username=?", (task_id, username))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def db_update_conversion_yaml(task_id: str, yaml_output: str, username: str) -> bool:
    conn = get_db()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE conversions SET yaml_output=?, updated_at=? WHERE id=? AND username=?",
        (yaml_output, now, task_id, username),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated
=======
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

        CREATE TABLE IF NOT EXISTS project_versions (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            label TEXT NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            feedback TEXT DEFAULT '',
            snapshot TEXT NOT NULL,
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
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
