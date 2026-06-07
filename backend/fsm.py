from __future__ import annotations

from enum import Enum
from typing import Any

import logging

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    IDLE = "IDLE"
    UPLOADING = "UPLOADING"
    PARSING = "PARSING"
    ANALYZING = "ANALYZING"
    PLANNING_SCENES = "PLANNING_SCENES"
    GENERATING_SCRIPT = "GENERATING_SCRIPT"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


VALID_TRANSITIONS: dict[WorkflowState, list[WorkflowState]] = {
    WorkflowState.IDLE: [WorkflowState.UPLOADING],
    WorkflowState.UPLOADING: [WorkflowState.PARSING],
    WorkflowState.PARSING: [WorkflowState.ANALYZING],
    WorkflowState.ANALYZING: [WorkflowState.PLANNING_SCENES],
    WorkflowState.PLANNING_SCENES: [WorkflowState.GENERATING_SCRIPT],
    WorkflowState.GENERATING_SCRIPT: [WorkflowState.VALIDATING],
    WorkflowState.VALIDATING: [WorkflowState.COMPLETED, WorkflowState.GENERATING_SCRIPT],
    WorkflowState.COMPLETED: [WorkflowState.IDLE],
    WorkflowState.FAILED: [WorkflowState.IDLE],
}

STATE_LABELS: dict[WorkflowState, str] = {
    WorkflowState.IDLE: "空闲",
    WorkflowState.UPLOADING: "上传中",
    WorkflowState.PARSING: "解析中",
    WorkflowState.ANALYZING: "分析中",
    WorkflowState.PLANNING_SCENES: "场景规划中",
    WorkflowState.GENERATING_SCRIPT: "剧本生成中",
    WorkflowState.VALIDATING: "校验中",
    WorkflowState.COMPLETED: "已完成",
    WorkflowState.FAILED: "失败",
}

STATE_ORDER: list[WorkflowState] = [
    WorkflowState.IDLE,
    WorkflowState.UPLOADING,
    WorkflowState.PARSING,
    WorkflowState.ANALYZING,
    WorkflowState.PLANNING_SCENES,
    WorkflowState.GENERATING_SCRIPT,
    WorkflowState.VALIDATING,
    WorkflowState.COMPLETED,
]


class FSMError(Exception):
    pass


class WorkflowFSM:
    def __init__(self, initial: WorkflowState = WorkflowState.IDLE) -> None:
        self._state = initial

    @property
    def state(self) -> WorkflowState:
        return self._state

    @property
    def label(self) -> str:
        return STATE_LABELS.get(self._state, self._state.value)

    def transition(self, target: WorkflowState) -> None:
        if target not in VALID_TRANSITIONS.get(self._state, []):
            raise FSMError(f"非法状态转移: {self._state.value} -> {target.value}")
        old = self._state
        self._state = target
        logger.info("FSM transition: %s -> %s", old.value, target.value)

    def circuit_breaker(self, target: WorkflowState, allowed_from: list[WorkflowState]) -> None:
        if self._state not in allowed_from:
            logger.warning("FSM circuit-breaker: %s -> %s (allowed from %s)", self._state.value, target.value, [s.value for s in allowed_from])
        self._state = target

    def is_terminal(self) -> bool:
        return self._state in (WorkflowState.COMPLETED, WorkflowState.FAILED)

    def is_processing(self) -> bool:
        return self._state not in (WorkflowState.IDLE, WorkflowState.COMPLETED, WorkflowState.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "label": self.label,
            "is_terminal": self.is_terminal(),
            "is_processing": self.is_processing(),
        }
