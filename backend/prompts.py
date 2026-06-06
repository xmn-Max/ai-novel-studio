COMMON_JSON_RULE = "\n\n【重要】只输出纯 JSON，不要添加任何解释、说明或 markdown 代码块标记。"

CHARACTER_EXTRACTION_PROMPT = """你是一个小说角色分析助手。请阅读以下小说文本，提取所有有名字的角色。

{genre_guidance}

对每个角色提供：
- name: 角色姓名
- aliases: 别名或昵称列表
- gender: 性别（男/女/未知）
- age: 年龄（如未明确提及可留空或写"未知"）
- description: 简要描述（外貌、性格、身份等）
- role: 角色类型，可选值 "protagonist"(主角), "supporting"(配角), "minor"(次要角色)
- traits: 性格特征数组（如 ["冷静", "坚韧", "善良"]）

请输出如下 JSON 对象：
{{
  "characters": [
    {{
      "name": "张三",
      "aliases": ["三哥", "阿三"],
      "gender": "男",
      "age": "25",
      "description": "25岁的年轻程序员，性格内向但聪明",
      "role": "protagonist",
      "traits": ["冷静", "聪明", "内向"]
    }}
  ]
}}""" + COMMON_JSON_RULE

SCENE_SEGMENTATION_PROMPT = """你是一个影视剧本场景分析助手。请将以下章节内容拆分为独立的场景（scene）。

{genre_guidance}

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
- conflict_level: 该场景的冲突强度（"低", "中", "高"）

请输出如下 JSON 对象：
{{
  "scenes": [
    {{
      "scene_index": 1,
      "location": "张三的公寓",
      "time_of_day": "上午",
      "characters_present": ["张三"],
      "summary": "张三在公寓里醒来，发现手机上有一条神秘消息。",
      "conflict_level": "低"
    }}
  ]
}}""" + COMMON_JSON_RULE

SCENE_TO_SCRIPT_PROMPT = """你是一个专业影视编剧。请将以下场景描述转换为标准剧本格式。

{genre_guidance}

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

PLOT_ANALYSIS_PROMPT = """你是一个专业的故事分析顾问。请深入分析以下小说的剧情结构。

{genre_guidance}

已知角色列表：{characters}

请分析并输出以下内容：

1. 主线 (main_line)：用一句话概括故事主线
2. 支线 (sub_lines)：识别出重要的支线剧情（列表）
3. 主题 (theme)：小说的核心主题（如"复仇与救赎""成长与责任"）
4. 核心冲突 (conflict)：主要矛盾是什么
5. 高潮事件 (climax)：故事的最高潮部分
6. 结局 (ending)：故事的结局走向
7. 关键事件列表 (events)：按时间顺序列出所有重要事件
8. 节奏分析 (pacing)：整体叙事节奏（如"慢热型""层层递进""快节奏"）

对于每个事件，提供：
- id: 事件ID（E001 格式）
- name: 事件名称
- description: 简要描述
- chapter_refs: 涉及的章节序号
- characters_involved: 涉及的角色名字列表
- significance: 重要性（"重大转折/推进主线/人物成长/背景铺垫"）

请输出如下 JSON 对象：
{{
  "main_line": "一个少年从废柴成长为最强修仙者的故事",
  "sub_lines": ["爱情线：与师妹的感情纠葛", "复仇线：寻找灭族凶手"],
  "theme": "逆境成长与命运抗争",
  "conflict": "主角与魔教之间的正邪对抗",
  "climax": "在宗门大比中击败宿敌，揭露幕后黑手",
  "ending": "主角飞升仙界，与挚爱团聚",
  "pacing": "层层递进",
  "events": [
    {{
      "id": "E001",
      "name": "主角遇险获得奇遇",
      "description": "主角在意外中落入秘境，获得上古传承",
      "chapter_refs": [2, 3],
      "characters_involved": ["林凡"],
      "significance": "重大转折"
    }}
  ]
}}""" + COMMON_JSON_RULE

SCENE_PLANNING_PROMPT = """你是一个影视场景规划专家。请根据剧情事件列表和角色信息，规划出完整的场景列表。

{genre_guidance}

已知角色：{characters}
已知事件：{events}

场景规划要求：
1. 每个事件至少对应 1 个场景，重要事件可能需要多个场景
2. 场景之间要有逻辑推进
3. 考虑场景的地点、时间变化
4. 控制冲突节奏（起承转合）

对于每个场景，提供：
- id: 场景ID（S001 格式）
- scene_id: 场景标识（如 "scene_1"）
- purpose: 这个场景的叙事目的
- location: 建议的地点
- time_of_day: 建议的时间
- event_refs: 关联的事件ID列表
- conflict_level: 冲突强度（"低/中/高/极高"）

请输出如下 JSON 对象：
{{
  "scene_plan": [
    {{
      "id": "S001",
      "scene_id": "scene_1",
      "purpose": "介绍主角的日常生活和世界观",
      "location": "青云宗外门",
      "time_of_day": "清晨",
      "event_refs": ["E001"],
      "conflict_level": "低"
    }}
  ]
}}""" + COMMON_JSON_RULE

WORLD_BUILDING_PROMPT = """你是一个小说世界观分析专家。请从以下小说中提取和归纳完整的世界观设定。

{genre_guidance}

请分析以下维度：

1. 界域/地点 (realms)：重要的地理位置或世界
2. 势力/宗门 (factions)：各个组织、门派、势力
3. 功法/技能 (techniques)：重要的功法、技能体系
4. 法宝/物品 (items)：关键的道具、法宝
5. 时间线 (timeline)：故事中的重要时间节点
6. 世界观规则 (rules)：这个世界的基本运行规则

对于每项都提供 name 和 description。

请输出如下 JSON 对象：
{{
  "realms": [
    {{"name": "青云宗山门", "description": "青云宗坐落于青云山脉，灵气充沛"}}
  ],
  "factions": [
    {{"name": "青云宗", "description": "正道第一大宗，以剑道著称"}},
    {{"name": "魔教", "description": "邪道势力，暗中图谋天下"}}
  ],
  "techniques": [
    {{"name": "九天玄功", "description": "青云宗镇宗功法，修炼至大成可飞天遁地"}}
  ],
  "items": [
    {{"name": "青云剑", "description": "青云宗传承宝剑"}}
  ],
  "timeline": [
    {{"time": "三百年前", "event": "正邪大战，魔教被封印"}},
    {{"time": "故事开始", "event": "主角入门"}}
  ],
  "rules": [
    "修炼分为九层境界：炼气、筑基、金丹、元婴、化神、合体、渡劫、大乘、飞升"
  ]
}}""" + COMMON_JSON_RULE

SCHEMA_FIX_PROMPT = """你是一个剧本格式修复助手。以下剧本场景存在 Schema 验证问题，请根据指出的问题修复它。

已知角色列表：{characters}

当前剧本场景：
{scene_data}

验证发现的问题：
{issues}

请修复上述问题，输出修复后的完整场景 JSON 对象（保持原有结构）：
{{
  "scene_id": 1,
  "scene_heading": "第1场  内景  地点  时间",
  "location": "地点",
  "time_of_day": "时间",
  "characters_present": ["角色1"],
  "action": ["动作描述"],
  "dialogues": [
    {{"character": "角色1", "line": "台词", "parenthetical": ""}}
  ],
  "transition": ""
}}

注意：
1. 保持原场景的剧情内容不变
2. 只修复格式问题
3. characters_present 中的角色必须在已知角色列表中
4. dialogues 中的 character 必须在 characters_present 中""" + COMMON_JSON_RULE

PLUGIN_SCREENWRITER_PROMPT = """你是一个资深影视编剧顾问。请对以下剧本进行专业点评。

{genre_guidance}

请从以下维度进行点评建议：
1. 三幕式分析：是否具备清晰的三幕结构（建置/对抗/解决）
2. 节奏评分（1-10分）：剧情节奏是否合理
3. 角色弧光：主角的成长轨迹是否完整
4. 对白评价：对白是否自然有力
5. 改进建议：具体可操作的修改建议（3-5条）

已知角色：{characters}

剧本内容：
{script_summary}

请输出如下 JSON：
{{
  "three_act_analysis": "对该剧本三幕式结构的详细分析",
  "pacing_score": 7,
  "character_arc": "主角成长轨迹分析",
  "dialogue_review": "对白评价",
  "improvement_suggestions": ["建议1", "建议2", "建议3"]
}}""" + COMMON_JSON_RULE

PLUGIN_BOOM_ANALYSIS_PROMPT = """你是一个短视频/MCN内容分析专家。请分析以下剧本的爆款潜力。

{genre_guidance}

请分析：
1. 爆点提取 (boom_points)：找出最有冲击力的 3-5 个情节转折
2. 标题建议 (title_suggestions)：生成 5 个吸引眼球的短视频标题
3. 钩子设计 (hooks)：设计 3 个开头5秒的钩子（用于短视频）
4. 高光场景 (highlight_scenes)：推荐 3 个最适合做成短视频片段的场景

已知角色：{characters}

剧本摘要：
{script_summary}

请输出如下 JSON：
{{
  "boom_points": [
    {{"name": "反转点名称", "description": "为什么这是爆点", "scene_ref": 1}}
  ],
  "title_suggestions": ["标题1", "标题2"],
  "hooks": ["开头钩子1", "开头钩子2"],
  "highlight_scenes": [{{"scene_id": 1, "reason": "推荐理由"}}]
}}""" + COMMON_JSON_RULE
