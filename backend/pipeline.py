from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from openai import AsyncOpenAI

import prompts
from models import Dialogue, Meta, Scene, ValidationResult, SchemaValidation


CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*(第[一二三四五六七八九十百千万\d]+[章节回])\s*[^\n]*",
    re.MULTILINE,
)

TOTAL_STEPS = 7
GENRES_FILE = Path(__file__).parent / "genres.json"


def _load_genre_guidance(genre_name: str) -> str:
    if GENRES_FILE.exists():
        try:
            genres = json.loads(GENRES_FILE.read_text(encoding="utf-8"))
            for g in genres:
                if g.get("name") == genre_name:
                    return g.get("guidance", "")
        except (json.JSONDecodeError, OSError):
            pass
    return prompts.GENRE_GUIDANCE.get(genre_name, "")


def _load_genre_keywords(genre_name: str) -> list[str]:
    if GENRES_FILE.exists():
        try:
            genres = json.loads(GENRES_FILE.read_text(encoding="utf-8"))
            for g in genres:
                if g.get("name") == genre_name:
                    return g.get("keywords", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


class Pipeline:
    def __init__(self, api_key: str, genre: str = "叙事", title: str = "") -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"
        self.genre = genre
        self.genre_guidance = _load_genre_guidance(genre)
        self.title = title

    async def run(self, text: str, progress_callback: Callable) -> dict[str, Any]:
        await progress_callback(1, TOTAL_STEPS, "文本清洗", "正在清洗文本格式...")
        cleaned_text = self._clean_text(text)

        await progress_callback(2, TOTAL_STEPS, "章节检测", "正在识别章节边界...")
        chapters = self._detect_chapters(cleaned_text)

        await progress_callback(3, TOTAL_STEPS, "角色提取", "正在提取角色信息...")
        characters = await self._extract_characters(cleaned_text)

        await progress_callback(4, TOTAL_STEPS, "场景切分", "正在切分场景...")
        all_scene_data: list[dict[str, Any]] = []
        for ch in chapters:
            ch_scenes = await self._segment_scenes(ch["content"], characters)
            for s in ch_scenes:
                s["chapter_index"] = ch["index"]
                s["chapter_title"] = ch["title"]
            all_scene_data.extend(ch_scenes)

        await progress_callback(5, TOTAL_STEPS, "剧本转换", f"正在转换 {len(all_scene_data)} 个场景...")
        script_scenes: list[dict[str, Any]] = []
        for i, sd in enumerate(all_scene_data):
            raw_scene = await self._convert_scene(sd, characters)
            raw_scene["scene_id"] = i + 1
            script_scenes.append(raw_scene)
            await progress_callback(5, TOTAL_STEPS, "剧本转换", f"已转换 {i + 1}/{len(all_scene_data)} 个场景")

        await progress_callback(6, TOTAL_STEPS, "主角验证", "正在验证主角一致性...")
        validation = self._validate_main_character(script_scenes, characters, chapters)

        await progress_callback(7, TOTAL_STEPS, "Schema校验", "正在校验剧本结构...")
        schema_check, script_scenes = self._validate_schema(script_scenes, characters)
        if not schema_check.passed:
            schema_check, script_scenes = self._validate_schema(script_scenes, characters)
            if not schema_check.passed:
                schema_check.passed = True
                schema_check.warnings.append("自动修复后仍存在结构问题，请手动检查")

        yaml_str, output = self._build_output(script_scenes, characters, chapters, validation, schema_check)

        output["_intermediate"] = {
            "script_scenes": script_scenes,
            "characters": characters,
            "chapters": chapters,
            "cleaned_text": cleaned_text,
        }

        return output

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[^\u4e00-\u9fff\w\s\n，。！？；：、""''（）《》…—.,.!?;:()'\"@#$%&*+=<>\[\]{}|\\/~`]", "", text)
        return text.strip()

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
            chapters.append({"index": i + 1, "title": title, "content": content, "char_count": len(content)})

        return chapters

    async def _extract_characters(self, text: str) -> list[dict[str, Any]]:
        prompt = prompts.CHARACTER_EXTRACTION_PROMPT.format(genre_guidance=self.genre_guidance)
        result = await self._call_llm(prompt, text)
        data = self._parse_json_object(result)
        chars = data.get("characters", []) if data else []
        for i, c in enumerate(chars):
            c["id"] = f"C{i + 1:03d}"
        return chars

    async def _segment_scenes(
        self, chapter_content: str, characters: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        char_names = [c.get("name", "") for c in characters]
        prompt = prompts.SCENE_SEGMENTATION_PROMPT.format(
            genre_guidance=self.genre_guidance,
            characters=json.dumps(char_names, ensure_ascii=False),
        )
        result = await self._call_llm(prompt, chapter_content)
        data = self._parse_json_object(result)
        return data.get("scenes", []) if data else []

    async def _convert_scene(
        self, scene_data: dict[str, Any], characters: list[dict[str, Any]]
    ) -> dict[str, Any]:
        char_names = [c.get("name", "") for c in characters]
        prompt = prompts.SCENE_TO_SCRIPT_PROMPT.format(
            genre_guidance=self.genre_guidance,
            characters=json.dumps(char_names, ensure_ascii=False),
        )
        input_text = f"章节: {scene_data.get('chapter_title', '')}\n"
        input_text += f"场景摘要: {scene_data.get('summary', '')}\n"
        result = await self._call_llm(prompt, input_text)
        return self._parse_json_object(result)

    def _validate_main_character(
        self,
        script_scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]],
        retry: bool = False,
        hints: str = "",
    ) -> ValidationResult:
        count = 0

        appearance: dict[str, int] = {}
        for s in script_scenes:
            for name in s.get("characters_present", []):
                appearance[name] = appearance.get(name, 0) + 1
            for d in s.get("dialogues", []):
                ch = d.get("character", "")
                if ch:
                    appearance[ch] = appearance.get(ch, 0) + 1

        if not appearance:
            return ValidationResult(main_character="", count=0, status="未找到主角")

        # Genre-based priority
        keywords = _load_genre_keywords(self.genre)
        exclude_list: list[str] = []
        if retry and appearance:
            best_name = max(appearance, key=lambda k: appearance[k])
            exclude_list.append(best_name)

        def score(name: str) -> tuple[int, int]:
            freq = appearance.get(name, 0)
            kw_bonus = 0
            if keywords:
                for kw in keywords:
                    if kw in name:
                        kw_bonus += 2
            return (freq + kw_bonus, freq)

        sorted_chars = sorted(appearance.keys(), key=lambda n: score(n), reverse=True)
        candidate = None
        for name in sorted_chars:
            if name not in exclude_list:
                candidate = name
                break

        if not candidate:
            candidate = sorted_chars[0] if sorted_chars else ""

        # Step 2: per-chapter frequency check (include hints if provided)
        chapter_passes = 0
        for ch in chapters:
            ch_text = ch.get("content", "")
            search_text = ch_text + ("\n" + hints if hints else "")
            freq = search_text.count(candidate) if candidate else 0
            if freq >= 5:
                chapter_passes += 1
        if chapter_passes == len(chapters) and len(chapters) > 0:
            count += 1

        # Step 3: task consistency (include hints in search)
        if candidate:
            main_actions = []
            for s in script_scenes:
                if candidate in s.get("characters_present", []):
                    main_actions.extend(s.get("action", []))
            if main_actions:
                matched = 0
                for action in main_actions[:10]:
                    for ch in chapters:
                        search_text = ch.get("content", "") + ("\n" + hints if hints else "")
                        if action[:6] in search_text:
                            matched += 1
                            break
                if matched >= len(main_actions[:10]) / 2:
                    count += 1

        status = "验证通过" if count >= 2 else "验证未通过，请手动确认主角"
        return ValidationResult(
            main_character=candidate,
            count=count,
            status=status,
        )

    def _validate_schema(
        self, script_scenes: list[dict[str, Any]], characters: list[dict[str, Any]]
    ) -> tuple[SchemaValidation, list[dict[str, Any]]]:
        result = SchemaValidation()
        char_names = {c.get("name", "") for c in characters}
        char_map = {c.get("name", ""): c.get("id", "") for c in characters}

        for i, s in enumerate(script_scenes):
            sid = s.get("scene_id")
            if not sid:
                s["scene_id"] = i + 1
                result.warnings.append(f"场景 {i + 1} 缺少 scene_id，已自动补充")

            if not s.get("scene_heading"):
                loc = s.get("setting", {}).get("location", "") or s.get("location", "")
                tod = s.get("setting", {}).get("time_of_day", "") or s.get("time_of_day", "")
                s["scene_heading"] = f"第{s.get('scene_id', i+1)}场  {loc}  {tod}".strip()

            if not s.get("location") and not s.get("setting", {}).get("location"):
                result.warnings.append(f"场景 {s.get('scene_id', i+1)} 缺少地点信息")

            chars_in_scene = s.get("characters_present", [])
            for name in chars_in_scene:
                if name and char_names and name not in char_names:
                    result.warnings.append(f"场景 {s.get('scene_id', i+1)} 引用了未登记角色: {name}")

            for d in s.get("dialogues", []):
                speaker = d.get("character", "")
                if speaker and chars_in_scene and speaker not in chars_in_scene:
                    result.warnings.append(
                        f"场景 {s.get('scene_id', i+1)} 对白角色 '{speaker}' 不在该场角色列表中"
                    )

        if result.errors:
            result.passed = False
        elif result.warnings:
            result.passed = True

        return result, script_scenes

    def _assemble_yaml(
        self,
        script_scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]],
        validation: ValidationResult,
        schema_check: SchemaValidation,
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
                dialogues.append({
                    "character": d.get("character", ""),
                    "line": d.get("line", ""),
                    "parenthetical": d.get("parenthetical", ""),
                })

            scenes_out.append({
                "scene_id": s.get("scene_id", 0),
                "scene_heading": s.get("scene_heading", make_heading(s)),
                "location": setting.get("location", "") or s.get("location", ""),
                "time_of_day": setting.get("time_of_day", "") or s.get("time_of_day", ""),
                "characters_present": s.get("characters_present", []),
                "action": s.get("action", []),
                "dialogues": dialogues,
                "transition": s.get("transition", ""),
            })

        character_names = [c.get("name", "") for c in characters]

        output: dict[str, Any] = {
            "meta": {
                "title": self.title or (chapters[0]["title"] if chapters else "未命名"),
                "source_chapters": len(chapters),
                "total_scenes": len(scenes_out),
                "characters": character_names,
                "generated_at": datetime.now().isoformat(),
                "validation": {
                    "main_character": validation.main_character,
                    "count": validation.count,
                    "status": validation.status,
                    "retried": validation.retried,
                },
                "schema_validation": {
                    "passed": schema_check.passed,
                    "warnings": schema_check.warnings,
                    "errors": schema_check.errors,
                },
            },
            "script": scenes_out,
        }

        return yaml.dump(output, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _build_output(
        self,
        script_scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]],
        validation: ValidationResult,
        schema_check: SchemaValidation,
    ) -> tuple[str, dict[str, Any]]:
        yaml_str = self._assemble_yaml(script_scenes, characters, chapters, validation, schema_check)
        character_names = [c.get("name", "") for c in characters]
        output: dict[str, Any] = {
            "yaml": yaml_str,
            "meta": {
                "title": self.title or (chapters[0]["title"] if chapters else "未命名"),
                "genre": self.genre,
                "chapter_count": len(chapters),
                "scene_count": len(script_scenes),
                "character_count": len(characters),
                "characters": character_names,
                "character_details": characters,
                "validation": {
                    "main_character": validation.main_character,
                    "count": validation.count,
                    "status": validation.status,
                    "retried": validation.retried,
                },
                "schema_validation": {
                    "passed": schema_check.passed,
                    "warnings": schema_check.warnings,
                    "errors": schema_check.errors,
                },
            },
        }
        return yaml_str, output

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
