from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Dialogue(BaseModel):
    character: str
    line: str
    parenthetical: str = ""


class Scene(BaseModel):
    scene_id: int
    scene_heading: str
    location: str = ""
    time_of_day: str = ""
    characters_present: list[str] = Field(default_factory=list)
    action: list[str] = Field(default_factory=list)
    dialogues: list[Dialogue] = Field(default_factory=list)
    transition: str = ""


class Script(BaseModel):
    scenes: list[Scene] = Field(default_factory=list)


class ValidationResult(BaseModel):
    main_character: str = ""
    count: int = 0
    status: str = "未验证"
    retried: bool = False


class SchemaValidation(BaseModel):
    passed: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Meta(BaseModel):
    title: str
    genre: str = ""
    chapter_count: int = 0
    scene_count: int = 0
    character_count: int = 0
    characters: list[str] = Field(default_factory=list)
    character_details: list[dict] = Field(default_factory=list)
    validation: Optional[ValidationResult] = None
    schema_validation: Optional[SchemaValidation] = None
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AuthRequest(BaseModel):
    username: str
    password: str


class GenreItem(BaseModel):
    name: str
    guidance: str = ""
    keywords: list[str] = []


class CreateProjectRequest(BaseModel):
    title: str
    genre: str = "叙事"


class UpdateScriptRequest(BaseModel):
    scene_id: int
    scene_heading: Optional[str] = None
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    characters_present: Optional[list[str]] = None
    action: Optional[list[str]] = None
    dialogues: Optional[list[dict]] = None
    transition: Optional[str] = None
