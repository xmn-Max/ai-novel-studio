from __future__ import annotations

<<<<<<< HEAD
import hashlib
import uuid
from typing import Optional

from database import (
    db_create_user,
    db_get_user_by_token,
    db_get_user_by_username,
    db_update_user_token,
    db_get_user_genres,
    db_count_user_genres,
    db_add_user_genre,
    db_update_user_genre,
    db_delete_user_genre,
)

MAX_USER_GENRES = 10


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> dict:
    existing = db_get_user_by_username(username)
    if existing:
        raise ValueError("用户名已存在")

    token = str(uuid.uuid4())
    return db_create_user(username, _hash(password), token)


def login_user(username: str, password: str) -> Optional[dict]:
    user = db_get_user_by_username(username)
    if not user:
        return None
    if user["password_hash"] != _hash(password):
        return None

    token = str(uuid.uuid4())
    db_update_user_token(username, token)
    return {"username": user["username"], "token": token, "created_at": user.get("created_at", "")}


def verify_token(token: str) -> Optional[dict]:
    user = db_get_user_by_token(token)
    if not user:
        return None
    return {"username": user["username"], "created_at": user.get("created_at", "")}


def get_user_genres(username: str) -> list[dict]:
    genres = db_get_user_genres(username)
    return [{"name": g["name"], "guidance": g.get("guidance", ""), "keywords": g.get("keywords", [])} for g in genres]


def add_user_genre(username: str, name: str, guidance: str, keywords: list[str]) -> dict:
    count = db_count_user_genres(username)
    if count >= MAX_USER_GENRES:
        raise ValueError(f"最多只能添加 {MAX_USER_GENRES} 个自定义类型")
    return db_add_user_genre(username, name, guidance, keywords)


def update_user_genre(username: str, index: int, name: str, guidance: str, keywords: list[str]) -> dict:
    return db_update_user_genre(username, index, name, guidance, keywords)


def delete_user_genre(username: str, index: int) -> str:
    return db_delete_user_genre(username, index)
=======
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt

USERS_FILE = Path(__file__).parent / "users.json"
LOCK_FILE = Path(__file__).parent / "users.lock"
MAX_USER_GENRES = 10
TOKEN_TTL_HOURS = 72


def _acquire_lock() -> None:
    for _ in range(50):
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError("无法获取用户文件锁")


def _release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _load_users() -> list[dict]:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_users(users: list[dict]) -> None:
    _acquire_lock()
    try:
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        raise RuntimeError("无法写入用户数据文件")
    finally:
        _release_lock()


def register_user(username: str, password: str) -> dict:
    users = _load_users()
    for u in users:
        if u["username"] == username:
            raise ValueError("用户名已存在")

    token = str(uuid.uuid4())
    now = datetime.now().isoformat()
    new_user = {
        "username": username,
        "password_hash": _hash(password),
        "token": token,
        "token_created_at": now,
        "genres": [],
        "created_at": now,
    }
    users.append(new_user)
    _save_users(users)
    return {"username": username, "token": token, "created_at": new_user["created_at"]}


def login_user(username: str, password: str) -> Optional[dict]:
    users = _load_users()
    for u in users:
        if u["username"] == username and _verify(password, u["password_hash"]):
            token = str(uuid.uuid4())
            u["token"] = token
            u["token_created_at"] = datetime.now().isoformat()
            _save_users(users)
            return {"username": u["username"], "token": token, "created_at": u["created_at"]}
    return None


def verify_token(token: str) -> Optional[dict]:
    if not token:
        return None
    users = _load_users()
    now = datetime.now()
    for u in users:
        if u.get("token") == token:
            created = u.get("token_created_at", u.get("created_at", ""))
            if created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    if now - created_dt > timedelta(hours=TOKEN_TTL_HOURS):
                        return None
                except (ValueError, TypeError):
                    pass
            return {"username": u["username"], "created_at": u.get("created_at", "")}
    return None


def get_user_genres(username: str) -> list[dict]:
    users = _load_users()
    for u in users:
        if u["username"] == username:
            return u.get("genres", [])
    return []


def add_user_genre(username: str, name: str, guidance: str, keywords: list[str]) -> dict:
    users = _load_users()
    for u in users:
        if u["username"] == username:
            genres = u.get("genres", [])
            if len(genres) >= MAX_USER_GENRES:
                raise ValueError(f"最多只能添加 {MAX_USER_GENRES} 个自定义类型")
            if any(g["name"] == name for g in genres):
                raise ValueError(f"类型 '{name}' 已存在")
            item = {"name": name, "guidance": guidance, "keywords": keywords}
            genres.append(item)
            u["genres"] = genres
            _save_users(users)
            return item
    raise ValueError("用户不存在")


def update_user_genre(username: str, index: int, name: str, guidance: str, keywords: list[str]) -> dict:
    users = _load_users()
    for u in users:
        if u["username"] == username:
            genres = u.get("genres", [])
            if index < 0 or index >= len(genres):
                raise ValueError("类型不存在")
            if any(g["name"] == name for i, g in enumerate(genres) if i != index):
                raise ValueError(f"类型 '{name}' 已存在")
            genres[index] = {"name": name, "guidance": guidance, "keywords": keywords}
            u["genres"] = genres
            _save_users(users)
            return genres[index]
    raise ValueError("用户不存在")


def delete_user_genre(username: str, index: int) -> str:
    users = _load_users()
    for u in users:
        if u["username"] == username:
            genres = u.get("genres", [])
            if index < 0 or index >= len(genres):
                raise ValueError("类型不存在")
            deleted = genres.pop(index)
            u["genres"] = genres
            _save_users(users)
            return deleted["name"]
    raise ValueError("用户不存在")
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
