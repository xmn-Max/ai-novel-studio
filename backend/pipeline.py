from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Callable

import yaml
from openai import AsyncOpenAI

import prompts
from models import Dialogue, Meta, Scene


CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*(第[一二三四五六七八九十百千万\d]+[章节回])\s*[^\n]*",
    re.MULTILINE,
)


class Pipeline:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"

    async def run(self, text: str, progress_callback: Callable) -> dict[str, Any]:
        await progress_callback(1, 5, "章节检测", "正在识别章节边界...")
        chapters = self._detect_chapters(text)

        await progress_callback(2, 5, "角色提取", "正在提取角色信息...")
        characters = await self._extract_characters(text)

        await progress_callback(3, 5, "场景切分", "正在切分场景...")
        all_scene_data: list[dict[str, Any]] = []
        for ch in chapters:
            ch_scenes = await self._segment_scenes(ch["content"], characters)
            for s in ch_scenes:
                s["chapter_index"] = ch["index"]
                s["chapter_title"] = ch["title"]
            all_scene_data.extend(ch_scenes)

        await progress_callback(4, 5, "剧本转换", f"正在转换 {len(all_scene_data)} 个场景...")
        script_scenes: list[dict[str, Any]] = []
        for i, sd in enumerate(all_scene_data):
            raw_scene = await self._convert_scene(sd, characters)
            raw_scene["scene_id"] = i + 1
            script_scenes.append(raw_scene)
            await progress_callback(4, 5, "剧本转换", f"已转换 {i + 1}/{len(all_scene_data)} 个场景")

        await progress_callback(5, 5, "组装输出", "正在生成 YAML 剧本...")
        yaml_str = self._assemble_yaml(script_scenes, characters, chapters, text)
        character_names = [c.get("name", "") for c in characters]

        return {
            "yaml": yaml_str,
            "meta": {
                "title": chapters[0]["title"] if chapters else "未命名",
                "chapter_count": len(chapters),
                "scene_count": len(script_scenes),
                "character_count": len(characters),
                "characters": character_names,
            },
        }

    def _detect_chapters(self, text: str) -> list[dict[str, Any]]:
        matches = list(CHAPTER_PATTERN.finditer(text))
        if not matches:
            return [{"index": 1, "title": "全文", "content": text}]

        chapters: list[dict[str, Any]] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            title = match.group(0).strip()
            content = text[start:end]
            chapters.append({"index": i + 1, "title": title, "content": content})

        return chapters

    async def _extract_characters(self, text: str) -> list[dict[str, Any]]:
        result = await self._call_llm(prompts.CHARACTER_EXTRACTION_PROMPT, text)
        data = self._parse_json_object(result)
        return data.get("characters", []) if data else []

    async def _segment_scenes(
        self, chapter_content: str, characters: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        char_names = [c.get("name", "") for c in characters]
        prompt = prompts.SCENE_SEGMENTATION_PROMPT.format(
            characters=json.dumps(char_names, ensure_ascii=False)
        )
        result = await self._call_llm(prompt, chapter_content)
        data = self._parse_json_object(result)
        return data.get("scenes", []) if data else []

    async def _convert_scene(
        self, scene_data: dict[str, Any], characters: list[dict[str, Any]]
    ) -> dict[str, Any]:
        char_names = [c.get("name", "") for c in characters]
        prompt = prompts.SCENE_TO_SCRIPT_PROMPT.format(
            characters=json.dumps(char_names, ensure_ascii=False)
        )
        input_text = f"章节: {scene_data.get('chapter_title', '')}\n"
        input_text += f"场景摘要: {scene_data.get('summary', '')}\n"
        result = await self._call_llm(prompt, input_text)
        return self._parse_json_object(result)

    def _assemble_yaml(
        self,
        script_scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]],
        full_text: str,
    ) -> str:
        def make_heading(s: dict[str, Any]) -> str:
            loc = s.get("setting", {}).get("location", "") or s.get("location", "")
            tod = s.get("setting", {}).get("time_of_day", "") or s.get("time_of_day", "")
            return f"第{s['scene_id']}场  {loc}  {tod}"

        scenes_out: list[dict[str, Any]] = []
        for s in script_scenes:
            setting = s.get("setting", {})
            dialogues_raw = s.get("dialogues", [])
            dialogues: list[dict[str, Any]] = []
            for d in dialogues_raw:
                dialogues.append(
                    {
                        "character": d.get("character", ""),
                        "line": d.get("line", ""),
                        "parenthetical": d.get("parenthetical", ""),
                    }
                )

            scenes_out.append(
                {
                    "scene_id": s.get("scene_id", 0),
                    "scene_heading": make_heading(s),
                    "location": setting.get("location", ""),
                    "time_of_day": setting.get("time_of_day", ""),
                    "characters_present": s.get("characters_present", []),
                    "action": s.get("action", []),
                    "dialogues": dialogues,
                    "transition": s.get("transition", ""),
                }
            )

        character_names = [c.get("name", "") for c in characters]

        output: dict[str, Any] = {
            "meta": {
                "title": chapters[0]["title"] if chapters else "未命名",
                "source_chapters": len(chapters),
                "total_scenes": len(scenes_out),
                "characters": character_names,
                "generated_at": datetime.now().isoformat(),
            },
            "script": scenes_out,
        }

        return yaml.dump(output, allow_unicode=True, default_flow_style=False, sort_keys=False)

    async def _call_llm(self, system_prompt: str, user_content: str) -> str:
        last_error: str = ""
        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
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
        raise RuntimeError(f"AI 服务请求失败，请检查网络或稍后重试")

    def _parse_json_list(self, raw: str) -> list[dict[str, Any]]:
        result = self._extract_json(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []

    def _parse_json_object(self, raw: str) -> dict[str, Any]:
        result = self._extract_json(raw)
        if isinstance(result, dict):
            return result
        return {}

    def _extract_json(self, raw: str) -> Any:
        raw = raw.strip()
        candidates: list[str] = []

        # Strategy 1: strip markdown fences
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\s*\n?", "", cleaned, count=1, flags=re.IGNORECASE)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned, count=1)
        candidates.append(cleaned)

        # Strategy 2: find first [ or { and try to parse balanced brackets
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
                            candidates.append(raw[start : i + 1])
                            break

        # Try each candidate
        for cand in candidates:
            try:
                return json.loads(cand)
            except json.JSONDecodeError:
                continue

        return None
