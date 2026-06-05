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
    source_chapters: int = 0
    total_scenes: int = 0
    characters: list[str] = Field(default_factory=list)
    character_details: list[dict] = Field(default_factory=list)
    validation: Optional[ValidationResult] = None
    schema_validation: Optional[SchemaValidation] = None
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ConvertRequest(BaseModel):
    text: str
    genre: str = "叙事"


class ConvertResponse(BaseModel):
    task_id: str


class ProgressEvent(BaseModel):
    step: int
    total: int
    step_name: str
    message: str
