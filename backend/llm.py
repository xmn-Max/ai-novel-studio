from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from openai import AsyncOpenAI


async def call_llm(client: AsyncOpenAI, model: str, system_prompt: str, user_content: str) -> str:
    last_error = ""
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("AI 返回空内容，请重试")
            return content
        except RuntimeError:
            raise
        except Exception as e:
            last_error = str(e)
            err_lower = last_error.lower()
            if "401" in err_lower or "unauthorized" in err_lower:
                raise RuntimeError("API Key 无效或已过期，请检查 DEEPSEEK_API_KEY")
            if "402" in err_lower or "insufficient" in err_lower or "balance" in err_lower:
                raise RuntimeError("DeepSeek 账户余额不足，请充值后重试")
            if "429" in err_lower or "rate" in err_lower:
                raise RuntimeError("请求过于频繁，请稍后重试")
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError("AI 服务请求失败，请检查网络或稍后重试")


def extract_json(raw: str) -> Any:
    raw = raw.strip()
    candidates: list[str] = []

    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\s*\n?", "", cleaned, count=1, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned, count=1)
    candidates.append(cleaned)

    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = raw.find(start_char)
        if start >= 0:
            depth = 0
            in_string = False
            escape = False
            for i, ch in enumerate(raw[start:], start):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        candidates.append(raw[start: i + 1])
                        break

    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue

    return None


def parse_json_object(raw: str) -> dict[str, Any]:
    result = extract_json(raw)
    if isinstance(result, dict):
        return result
    return {}


def parse_json_list(raw: str) -> list[dict[str, Any]]:
    result = extract_json(raw)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return [result]
    return []
