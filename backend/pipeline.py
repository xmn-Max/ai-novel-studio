from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from openai import AsyncOpenAI

import prompts
from llm import call_llm, parse_json_object
from models import ValidationResult, SchemaValidation

CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*((?:第[一二三四五六七八九十百千万\d]+[卷集部])?\s*第[一二三四五六七八九十百千万\d]+[章节回])\s*[^\n]*",
    re.MULTILINE,
)

GENRES_FILE = Path(__file__).parent / "genres.json"
TOTAL_STEPS = 8

LLM_TIMEOUT_SECONDS = 120
PLOT_TRUNCATE_CHARS = 8000
SCENE_PLAN_TRUNCATE_CHARS = 6000
WORLD_TRUNCATE_CHARS = 8000
SCHEMA_FIX_TRUNCATE_CHARS = 3000


def _load_genres() -> list[dict[str, Any]]:
    if GENRES_FILE.exists():
        try:
            return json.loads(GENRES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return [{"name": "叙事", "guidance": "", "keywords": []}]


def _get_genre_guidance(genre_name: str) -> str:
    for g in _load_genres():
        if g.get("name") == genre_name:
            return g.get("guidance", "")
    return ""


def _get_genre_keywords(genre_name: str) -> list[str]:
    for g in _load_genres():
        if g.get("name") == genre_name:
            return g.get("keywords", [])
    return []


class Pipeline:
    def __init__(self, api_key: str, genre: str = "叙事") -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"
        self.genre = genre
        self.genre_guidance = _get_genre_guidance(genre)

    async def run_full(self, text: str, progress_callback: Callable) -> dict[str, Any]:
        step = 0

        step += 1
        await progress_callback(step, TOTAL_STEPS, "文本清洗", "正在清洗文本格式...")
        cleaned_text = self._clean_text(text)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "章节检测", "正在识别章节边界...")
        chapters = self._detect_chapters(cleaned_text)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "角色提取", "AI 正在提取角色信息...")
        characters = await self._extract_characters(cleaned_text)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "剧情分析", "AI 正在分析剧情结构...")
        plot = await self._analyze_plot(cleaned_text, characters)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "场景规划", "AI 正在进行场景规划...")
        scene_plan = await self._plan_scenes(cleaned_text, characters, plot)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "剧本生成", "AI 正在生成剧本...")
        script_scenes = await self._generate_script(chapters, characters, scene_plan, progress_callback)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "世界观分析", "AI 正在归纳世界观...")
        world_building = await self._build_world(cleaned_text)

        step += 1
        await progress_callback(step, TOTAL_STEPS, "校验", "正在校验剧本质量...")
        validation = self._validate_main_character(script_scenes, characters, chapters)
        if validation.count < 2:
            alt = self._validate_main_character(script_scenes, characters, chapters, retry=True)
            alt.retried = True
            if alt.count >= 2:
                validation = alt

        schema_check, script_scenes = await self._validate_schema_with_ai_fix(script_scenes, characters)

        yaml_str = self._assemble_yaml(script_scenes, characters, chapters, validation, schema_check)
        character_names = [c.get("name", "") for c in characters]

        return {
            "yaml": yaml_str,
            "meta": {
                "title": chapters[0]["title"] if chapters else "未命名",
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
            "characters": characters,
            "plot": plot,
            "scene_plan": scene_plan,
            "world_building": world_building,
            "chapters": chapters,
            "script_scenes": script_scenes,
        }

    async def run_plot_analysis(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        characters = await self._extract_characters(cleaned)
        return await self._analyze_plot(cleaned, characters)

    async def run_world_building(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        return await self._build_world(cleaned)

    async def regenerate_script(
        self, feedback: str, current_script: str, characters: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        char_names = json.dumps([c.get("name", "") for c in characters], ensure_ascii=False)
        prompt = prompts.REGENERATE_SCRIPT_PROMPT.format(
            genre_guidance=self.genre_guidance,
            characters=char_names,
            current_script=current_script[:6000],
            feedback=feedback,
        )
        result = await call_llm(self.client, self.model, prompt, feedback)
        data = parse_json_object(result)
        scenes = data.get("scenes", []) if data else []
        for i, s in enumerate(scenes):
            if not s.get("scene_id"):
                s["scene_id"] = i + 1
        return scenes

    async def requery_plot(self, feedback: str, current_plot: dict[str, Any], characters: list[dict[str, Any]]) -> dict[str, Any]:
        char_names = json.dumps([c.get("name", "") for c in characters], ensure_ascii=False)
        prompt = prompts.REQUERY_PLOT_PROMPT.format(
            genre_guidance=self.genre_guidance,
            characters=char_names,
            current_plot=json.dumps(current_plot, ensure_ascii=False, indent=2)[:4000],
            feedback=feedback,
        )
        result = await call_llm(self.client, self.model, prompt, feedback)
        data = parse_json_object(result)
        return data if data else current_plot

    async def requery_world(self, feedback: str, current_world: dict[str, Any]) -> dict[str, Any]:
        prompt = prompts.REQUERY_WORLD_PROMPT.format(
            genre_guidance=self.genre_guidance,
            current_world=json.dumps(current_world, ensure_ascii=False, indent=2)[:4000],
            feedback=feedback,
        )
        result = await call_llm(self.client, self.model, prompt, feedback)
        data = parse_json_object(result)
        return data if data else current_world

    async def requery_characters(self, feedback: str, current_characters: list[dict[str, Any]], original_text: str = "") -> list[dict[str, Any]]:
        prompt = prompts.REQUERY_CHARACTERS_PROMPT.format(
            genre_guidance=self.genre_guidance,
            original_text=original_text[:3000],
            current_characters=json.dumps(current_characters, ensure_ascii=False, indent=2)[:4000],
            feedback=feedback,
        )
        result = await call_llm(self.client, self.model, prompt, feedback)
        data = parse_json_object(result)
        return data.get("characters", []) if data else current_characters

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(
            r"""[^\u4e00-\u9fff\w\s\n，。！？；：、""''（）《》…—.,.!?;:()'"@#$%&*+=<>\[\]{}|\\/~`]""",
            "",
            text,
        )
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
            chapters.append({
                "index": i + 1, "title": title, "content": content,
                "char_count": len(content),
            })
        return chapters

    async def _extract_characters(self, text: str) -> list[dict[str, Any]]:
        prompt = prompts.CHARACTER_EXTRACTION_PROMPT.format(genre_guidance=self.genre_guidance)
        result = await call_llm(self.client, self.model, prompt, text)
        data = parse_json_object(result)
        chars = data.get("characters", []) if data else []
        for i, c in enumerate(chars):
            c["id"] = f"C{i + 1:03d}"
        return chars

    async def _analyze_plot(self, text: str, characters: list[dict[str, Any]]) -> dict[str, Any]:
        char_names = json.dumps([c.get("name", "") for c in characters], ensure_ascii=False)
        context = text[:PLOT_TRUNCATE_CHARS] if len(text) > PLOT_TRUNCATE_CHARS else text
        prompt = prompts.PLOT_ANALYSIS_PROMPT.format(
            genre_guidance=self.genre_guidance, characters=char_names)
        result = await call_llm(self.client, self.model, prompt, context)
        data = parse_json_object(result) or {}
        events = data.get("events", [])
        for i, e in enumerate(events):
            if "id" not in e:
                e["id"] = f"E{i + 1:03d}"
        return {
            "theme": data.get("theme", ""),
            "conflict": data.get("conflict", ""),
            "climax": data.get("climax", ""),
            "ending": data.get("ending", ""),
            "main_line": data.get("main_line", ""),
            "sub_lines": data.get("sub_lines", []),
            "events": events,
            "pacing": data.get("pacing", ""),
        }

    async def _plan_scenes(self, text: str, characters: list[dict[str, Any]], plot: dict[str, Any]) -> list[dict[str, Any]]:
        char_names = json.dumps([c.get("name", "") for c in characters], ensure_ascii=False)
        events = json.dumps(plot.get("events", []), ensure_ascii=False)
        context = text[:SCENE_PLAN_TRUNCATE_CHARS] if len(text) > SCENE_PLAN_TRUNCATE_CHARS else text
        prompt = prompts.SCENE_PLANNING_PROMPT.format(
            genre_guidance=self.genre_guidance, characters=char_names, events=events)
        result = await call_llm(self.client, self.model, prompt, context)
        data = parse_json_object(result) or {}
        plan = data.get("scene_plan", [])
        for i, s in enumerate(plan):
            if "id" not in s:
                s["id"] = f"S{i + 1:03d}"
            if "scene_id" not in s:
                s["scene_id"] = f"scene_{i + 1}"
        return plan

    async def _generate_script(
        self, chapters: list[dict[str, Any]], characters: list[dict[str, Any]],
        scene_plan: list[dict[str, Any]], progress_callback: Callable,
    ) -> list[dict[str, Any]]:
        char_names = [c.get("name", "") for c in characters]
        char_names_json = json.dumps(char_names, ensure_ascii=False)

        all_scene_data: list[dict[str, Any]] = []
        for ch in chapters:
            ch_scenes = await self._segment_scenes(ch["content"], char_names_json)
            for s in ch_scenes:
                s["chapter_index"] = ch["index"]
                s["chapter_title"] = ch["title"]
            all_scene_data.extend(ch_scenes)

        if not all_scene_data and scene_plan:
            all_scene_data = [
                {
                    "chapter_index": 1, "chapter_title": "全文",
                    "scene_index": i + 1,
                    "location": sp.get("location", ""),
                    "time_of_day": sp.get("time_of_day", ""),
                    "summary": sp.get("purpose", ""),
                    "characters_present": [],
                    "conflict_level": sp.get("conflict_level", "中"),
                }
                for i, sp in enumerate(scene_plan)
            ]

        total_scenes = len(all_scene_data)
        script_scenes: list[dict[str, Any]] = []
        for i, sd in enumerate(all_scene_data):
            raw_scene = await self._convert_scene(sd, char_names_json)
            raw_scene["scene_id"] = i + 1
            script_scenes.append(raw_scene)
            if total_scenes > 3 and (i + 1) % 3 == 0:
                await progress_callback(6, TOTAL_STEPS, "剧本生成", f"已转换 {i + 1}/{total_scenes} 个场景")
        return script_scenes

    async def _segment_scenes(self, chapter_content: str, char_names_json: str) -> list[dict[str, Any]]:
        prompt = prompts.SCENE_SEGMENTATION_PROMPT.format(
            genre_guidance=self.genre_guidance, characters=char_names_json)
        result = await call_llm(self.client, self.model, prompt, chapter_content)
        data = parse_json_object(result)
        return data.get("scenes", []) if data else []

    async def _convert_scene(self, scene_data: dict[str, Any], char_names_json: str) -> dict[str, Any]:
        prompt = prompts.SCENE_TO_SCRIPT_PROMPT.format(
            genre_guidance=self.genre_guidance, characters=char_names_json)
        input_text = f"章节: {scene_data.get('chapter_title', '')}\n场景摘要: {scene_data.get('summary', '')}\n"
        result = await call_llm(self.client, self.model, prompt, input_text)
        parsed = parse_json_object(result)
        return parsed if parsed else {}

    async def _build_world(self, text: str) -> dict[str, Any]:
        context = text[:WORLD_TRUNCATE_CHARS] if len(text) > WORLD_TRUNCATE_CHARS else text
        world_fields = prompts.WORLD_FIELDS.get(self.genre, prompts.WORLD_FIELDS["叙事"])
        prompt = prompts.WORLD_BUILDING_PROMPT.format(
            genre_guidance=self.genre_guidance, world_fields=world_fields)
        result = await call_llm(self.client, self.model, prompt, context)
        data = parse_json_object(result) or {}
        return {
            "realms": data.get("realms", []),
            "factions": data.get("factions", []),
            "techniques": data.get("techniques", []),
            "items": data.get("items", []),
            "timeline": data.get("timeline", []),
            "rules": data.get("rules", []),
            "raw": data,
        }

    def _validate_main_character(
        self, script_scenes: list[dict[str, Any]], characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]], retry: bool = False,
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

        keywords = _get_genre_keywords(self.genre)
        exclude_list: list[str] = []
        if retry and appearance:
            exclude_list.append(max(appearance, key=lambda k: appearance[k]))

        def score(name: str) -> tuple[int, int]:
            freq = appearance.get(name, 0)
            kw_bonus = sum(2 for kw in keywords if kw in name)
            return (freq + kw_bonus, freq)

        sorted_chars = sorted(appearance.keys(), key=lambda n: score(n), reverse=True)
        candidate = next((n for n in sorted_chars if n not in exclude_list), None)
        if not candidate:
            candidate = sorted_chars[0] if sorted_chars else ""

        chapter_passes = sum(
            1 for ch in chapters
            if candidate and len(re.findall(rf"\b{re.escape(candidate)}\b", ch.get("content", ""))) >= 5
        )
        if len(chapters) > 0 and chapter_passes == len(chapters):
            count += 1

        if candidate:
            main_actions = []
            for s in script_scenes:
                if candidate in s.get("characters_present", []):
                    main_actions.extend(s.get("action", []))
            if main_actions:
                matched = sum(
                    1 for action in main_actions[:10]
                    if any(action[:6] in ch.get("content", "") for ch in chapters)
                )
                if matched >= len(main_actions[:10]) / 2:
                    count += 1

        status = "验证通过" if count >= 2 else "验证未通过，请手动确认主角"
        return ValidationResult(main_character=candidate, count=count, status=status)

    async def _validate_schema_with_ai_fix(
        self, script_scenes: list[dict[str, Any]], characters: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> tuple[SchemaValidation, list[dict[str, Any]]]:
        char_names = {c.get("name", "") for c in characters}

        for iteration in range(max_retries + 1):
            result = SchemaValidation()
            has_issue = False

            for i, s in enumerate(script_scenes):
                sid = s.get("scene_id")
                if not sid:
                    s["scene_id"] = i + 1
                    result.warnings.append(f"场景 {i + 1} 缺少 scene_id，已自动补充")

                if not s.get("scene_heading"):
                    loc = s.get("setting", {}).get("location", "") or s.get("location", "")
                    tod = s.get("setting", {}).get("time_of_day", "") or s.get("time_of_day", "")
                    s["scene_heading"] = f"第{s.get('scene_id', i + 1)}场  {loc}  {tod}".strip()

                if not s.get("location") and not s.get("setting", {}).get("location"):
                    result.warnings.append(f"场景 {s.get('scene_id', i + 1)} 缺少地点信息")
                    has_issue = True

                chars_in_scene = s.get("characters_present", [])
                for name in chars_in_scene:
                    if name and char_names and name not in char_names:
                        result.warnings.append(f"场景 {s.get('scene_id', i + 1)} 引用了未登记角色: {name}")
                        has_issue = True

                for d in s.get("dialogues", []):
                    speaker = d.get("character", "")
                    if speaker and chars_in_scene and speaker not in chars_in_scene:
                        result.warnings.append(
                            f"场景 {s.get('scene_id', i + 1)} 对白角色 '{speaker}' 不在该场角色列表中")
                        has_issue = True

            result.passed = not bool(result.errors)

            if not has_issue:
                return result, script_scenes

            if iteration < max_retries:
                fixed = await self._ai_fix_scenes(script_scenes, characters, result)
                if fixed:
                    script_scenes = fixed

        return result, script_scenes

    async def _ai_fix_scenes(
        self, script_scenes: list[dict[str, Any]], characters: list[dict[str, Any]],
        validation: SchemaValidation,
    ) -> list[dict[str, Any]] | None:
        char_names = json.dumps([c.get("name", "") for c in characters], ensure_ascii=False)
        issues = json.dumps(validation.warnings + validation.errors, ensure_ascii=False)
        fixed_scenes: list[dict[str, Any]] = []
        for s in script_scenes:
            scene_data = json.dumps(s, ensure_ascii=False)
            prompt = prompts.SCHEMA_FIX_PROMPT.format(
                characters=char_names, scene_data=scene_data[:SCHEMA_FIX_TRUNCATE_CHARS], issues=issues)
            try:
                result = await call_llm(self.client, self.model, prompt, scene_data[:2000])
                fixed = parse_json_object(result)
                fixed_scenes.append(fixed if fixed.get("scene_id") else s)
            except Exception:
                fixed_scenes.append(s)
        return fixed_scenes if fixed_scenes else None

    def _assemble_yaml(
        self, script_scenes: list[dict[str, Any]], characters: list[dict[str, Any]],
        chapters: list[dict[str, Any]], validation: ValidationResult,
        schema_check: SchemaValidation,
    ) -> str:
        scenes_out: list[dict[str, Any]] = []
        for s in script_scenes:
            setting = s.get("setting", {})
            scenes_out.append({
                "scene_id": s.get("scene_id", 0),
                "scene_heading": s.get("scene_heading", ""),
                "location": setting.get("location", "") or s.get("location", ""),
                "time_of_day": setting.get("time_of_day", "") or s.get("time_of_day", ""),
                "characters_present": s.get("characters_present", []),
                "action": s.get("action", []),
                "dialogues": [
                    {
                        "character": d.get("character", ""),
                        "line": d.get("line", ""),
                        "parenthetical": d.get("parenthetical", ""),
                    }
                    for d in s.get("dialogues", [])
                ],
                "transition": s.get("transition", ""),
            })

        output: dict[str, Any] = {
            "meta": {
                "title": chapters[0]["title"] if chapters else "未命名",
                "genre": self.genre,
                "source_chapters": len(chapters),
                "total_scenes": len(scenes_out),
                "characters": [c.get("name", "") for c in characters],
                "character_details": characters,
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
