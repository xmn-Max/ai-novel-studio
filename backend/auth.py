from __future__ import annotations

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
