from __future__ import annotations

import json
import logging
from typing import Any

import prompts
from llm import call_llm, parse_json_object

logger = logging.getLogger(__name__)


class PluginBase:
    name: str = "base"
    label: str = "基础插件"

    def __init__(self, client, model: str, genre_guidance: str) -> None:
        self.client = client
        self.model = model
        self.genre_guidance = genre_guidance

    async def run(self, project_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def _call(self, system_prompt: str, user_content: str) -> str:
        return await call_llm(self.client, self.model, system_prompt, user_content)

    async def _try_run(self, prompt_template: str, project_data: dict[str, Any]) -> dict[str, Any]:
        try:
            characters = json.dumps(project_data.get("characters", []), ensure_ascii=False)
            yaml_content = str(project_data.get("yaml_content", ""))[:4000]
            prompt = prompt_template.format(
                genre_guidance=self.genre_guidance, characters=characters,
                script_summary=yaml_content)
            result = await self._call(prompt, yaml_content)
            parsed = parse_json_object(result)
            if not parsed:
                return {"error": "插件返回空结果"}
            return parsed
        except Exception as e:
            logger.exception("Plugin %s failed", self.name)
            return {"error": f"插件运行失败: {str(e)}"}


class ScreenwriterPlugin(PluginBase):
    name = "screenwriter"
    label = "编剧点评插件"

    async def run(self, project_data: dict[str, Any]) -> dict[str, Any]:
        return await self._try_run(prompts.PLUGIN_SCREENWRITER_PROMPT, project_data)


class BoomAnalysisPlugin(PluginBase):
    name = "boom_analysis"
    label = "爆款分析插件"

    async def run(self, project_data: dict[str, Any]) -> dict[str, Any]:
        return await self._try_run(prompts.PLUGIN_BOOM_ANALYSIS_PROMPT, project_data)


def get_available_plugins() -> list[dict[str, str]]:
    return [
        {"name": "screenwriter", "label": "编剧点评插件",
         "description": "三幕式分析、节奏评分、角色弧光点评"},
        {"name": "boom_analysis", "label": "爆款分析插件",
         "description": "爆点提取、标题生成、短视频钩子设计"},
    ]


def create_plugin(name: str, client, model: str, genre_guidance: str) -> PluginBase | None:
    if name == "screenwriter":
        return ScreenwriterPlugin(client, model, genre_guidance)
    elif name == "boom_analysis":
        return BoomAnalysisPlugin(client, model, genre_guidance)
    return None
