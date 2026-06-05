from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

USERS_FILE = Path(__file__).parent / "users.json"
MAX_USER_GENRES = 10


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users() -> list[dict]:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_users(users: list[dict]) -> None:
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def register_user(username: str, password: str) -> dict:
    users = load_users()
    for u in users:
        if u["username"] == username:
            raise ValueError("用户名已存在")

    token = str(uuid.uuid4())
    new_user = {
        "username": username,
        "password_hash": _hash(password),
        "token": token,
        "genres": [],
        "created_at": datetime.now().isoformat(),
    }
    users.append(new_user)
    _save_users(users)

    return {"username": username, "token": token, "created_at": new_user["created_at"]}


def login_user(username: str, password: str) -> Optional[dict]:
    users = load_users()
    pw_hash = _hash(password)
    for u in users:
        if u["username"] == username and u["password_hash"] == pw_hash:
            token = str(uuid.uuid4())
            u["token"] = token
            _save_users(users)
            return {"username": u["username"], "token": token, "created_at": u["created_at"]}
    return None


def verify_token(token: str) -> Optional[dict]:
    if not token:
        return None
    users = load_users()
    for u in users:
        if u.get("token") == token:
            return {"username": u["username"], "created_at": u.get("created_at", "")}
    return None


# --- User-specific genres ---

def get_user_genres(username: str) -> list[dict]:
    users = load_users()
    for u in users:
        if u["username"] == username:
            return u.get("genres", [])
    return []


def add_user_genre(username: str, name: str, guidance: str, keywords: list[str]) -> dict:
    users = load_users()
    for u in users:
        if u["username"] == username:
            genres = u.get("genres", [])
            if len(genres) >= MAX_USER_GENRES:
                raise ValueError(f"最多只能添加 {MAX_USER_GENRES} 个自定义类型")
            existing = {g["name"] for g in genres}
            if name in existing:
                raise ValueError(f"类型 '{name}' 已存在")
            item = {"name": name, "guidance": guidance, "keywords": keywords}
            genres.append(item)
            u["genres"] = genres
            _save_users(users)
            return item
    raise ValueError("用户不存在")


def update_user_genre(username: str, index: int, name: str, guidance: str, keywords: list[str]) -> dict:
    users = load_users()
    for u in users:
        if u["username"] == username:
            genres = u.get("genres", [])
            if index < 0 or index >= len(genres):
                raise ValueError("类型不存在")
            existing = {g["name"] for i, g in enumerate(genres) if i != index}
            if name in existing:
                raise ValueError(f"类型 '{name}' 已存在")
            genres[index] = {"name": name, "guidance": guidance, "keywords": keywords}
            u["genres"] = genres
            _save_users(users)
            return genres[index]
    raise ValueError("用户不存在")


def delete_user_genre(username: str, index: int) -> str:
    users = load_users()
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
