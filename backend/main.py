from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import ConvertRequest, ConvertResponse
from pipeline import Pipeline

app = FastAPI(title="AI Novel Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks: dict[str, dict[str, Any]] = {}

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def _get_pipeline(genre: str = "叙事") -> Pipeline:
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")
    return Pipeline(api_key=API_KEY, genre=genre)


async def _run_pipeline(task_id: str, text: str, genre: str) -> None:
    pipeline = _get_pipeline(genre)
    tasks[task_id]["status"] = "processing"

    async def progress_callback(step: int, total: int, step_name: str, message: str) -> None:
        tasks[task_id]["progress"] = {
            "step": step,
            "total": total,
            "step_name": step_name,
            "message": message,
        }

    try:
        result = await pipeline.run(text, progress_callback)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


@app.post("/api/convert", response_model=ConvertResponse)
async def convert(request: ConvertRequest) -> ConvertResponse:
    text = request.text.strip()
    if len(text) < 100:
        raise HTTPException(status_code=400, detail="文本内容过短，至少需要 100 个字符")

    genre = request.genre.strip()
    if genre not in ["武侠", "玄幻", "科幻", "言情", "叙事", "魔幻"]:
        genre = "叙事"

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "progress": {
            "step": 0,
            "total": 7,
            "step_name": "初始化",
            "message": "任务已创建，等待处理...",
        },
        "result": None,
    }

    asyncio.create_task(_run_pipeline(task_id, text, genre))
    return ConvertResponse(task_id=task_id)


@app.get("/api/convert/{task_id}/progress")
async def progress(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_stream():
        while True:
            task = tasks.get(task_id)
            if task is None:
                break

            progress_data = task.get("progress", {})
            status = task.get("status", "pending")
            error = task.get("error", "")

            event_data = {
                **progress_data,
                "status": status,
                "error": error,
            }

            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            if status in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/convert/{task_id}/result")
async def result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] == "processing" or task["status"] == "pending":
        raise HTTPException(status_code=202, detail="任务尚未完成")

    if task["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"任务失败: {task.get('error', '未知错误')}")

    return task["result"]
