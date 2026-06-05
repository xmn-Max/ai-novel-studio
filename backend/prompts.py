CHAPTER_DETECTION_PROMPT = """你是一个小说章节分析助手。请分析以下文本，识别出所有章节的边界。

对于每个章节，返回章节序号（从 1 开始）和章节标题。如果标题不存在，使用 "第N章" 作为标题。

请以纯 JSON 数组格式返回，不要包含任何其他内容：
[{"index": 1, "title": "第一章 初遇"}, {"index": 2, "title": "第二章 离别"}, ...]
"""

COMMON_JSON_RULE = "\n\n【重要】只输出纯 JSON，不要添加任何解释、说明或 markdown 代码块标记。"

CHARACTER_EXTRACTION_PROMPT = """你是一个小说角色分析助手。请阅读以下小说文本，提取所有有名字的角色。

对每个角色提供：
- name: 角色姓名
- aliases: 别名或昵称列表
- description: 简要描述（外貌、性格、身份等）
- role: 角色类型，可选值 "protagonist"(主角), "supporting"(配角), "minor"(次要角色)

请输出如下 JSON 对象：
{
  "characters": [
    {
      "name": "张三",
      "aliases": ["三哥", "阿三"],
      "description": "25岁的年轻程序员，性格内向但聪明",
      "role": "protagonist"
    }
  ]
}""" + COMMON_JSON_RULE

SCENE_SEGMENTATION_PROMPT = """你是一个影视剧本场景分析助手。请将以下章节内容拆分为独立的场景（scene）。

场景划分标准：
- 地点发生变化时，开始新场景
- 时间发生明显跳跃时，开始新场景
- 人物群体发生重大变化时，考虑新场景

已知角色列表：{characters}

对每个场景提供：
- scene_index: 场景序号（从 1 开始，在本章内编号）
- location: 场景发生地点
- time_of_day: 时间（如 "上午", "下午", "傍晚", "夜晚", "深夜"）
- characters_present: 该场景中出现的角色姓名列表（只使用已知角色列表中的名字）
- summary: 该场景的简要剧情摘要（2-3句话）

请输出如下 JSON 对象：
{{
  "scenes": [
    {{
      "scene_index": 1,
      "location": "张三的公寓",
      "time_of_day": "上午",
      "characters_present": ["张三"],
      "summary": "张三在公寓里醒来，发现手机上有一条神秘消息。"
    }}
  ]
}}""" + COMMON_JSON_RULE

SCENE_TO_SCRIPT_PROMPT = """你是一个专业影视编剧。请将以下场景描述转换为标准剧本格式。

已知角色列表：{characters}

请输出如下 JSON 对象：
{{
  "setting": {{
    "location": "场景地点",
    "time_of_day": "时间"
  }},
  "action": [
    "动作描述1",
    "动作描述2"
  ],
  "dialogues": [
    {{
      "character": "角色名",
      "line": "台词内容",
      "parenthetical": "动作提示（可为空）"
    }}
  ],
  "transition": "转场方式（如 切至、淡入、淡出 等，可为空字符串）"
}}

注意：
1. action 数组中的每项应为一句完整的动作描述，使用简洁的剧本语言
2. dialogues 中每句对话应独立成项
3. 保留原作的叙事逻辑和情感基调""" + COMMON_JSON_RULE
