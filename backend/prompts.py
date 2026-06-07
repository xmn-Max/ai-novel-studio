COMMON_JSON_RULE = "\n\n【重要】只输出纯 JSON，不要添加任何解释、说明或 markdown 代码块标记。"

WORLD_FIELDS: dict[str, str] = {
    "叙事": """1. 地点/环境 (realms)：城市、乡村、家庭、工作场所——记录故事发生的重要地点和环境
2. 人物/群体 (factions)：主人公、家人、朋友、同事——记录重要的人物关系群体
3. 能力/经历 (techniques)：职业技能、生活经验、人生经历——记录人物的重要能力和经历
4. 物品/符号 (items)：生活用品、纪念品、信件、日记——记录推动情节的关键物品
5. 时间线 (timeline)：事件顺序、回忆、人生阶段——记录故事中的重要时间节点
6. 规则/制度 (rules)：社会规范、人际关系准则、命运规律——记录制约人物的社会规则""",

    "玄幻": """1. 界域/地点 (realms)：魔法大陆、秘境、宗门、异世界——记录修炼世界的重要地理节点
2. 势力/宗门 (factions)：门派、宗族、家族、势力阵营——记录各方修炼势力
3. 功法/技能 (techniques)：武学心法、魔法、特技、修炼体系——记录修炼相关的功法技能
4. 法宝/物品 (items)：神器、魔法道具、灵药、法阵——记录关键法宝和道具
5. 时间线 (timeline)：历练、修炼、战斗、事件高潮——记录修炼历程的关键时间点
6. 规则 (rules)：修炼法则、等级体系、禁忌与契约——记录世界运行的修炼规则""",

    "科幻": """1. 空间/星域 (realms)：星系、行星、实验室、未来都市——记录故事发生的重要空间节点
2. 群体/组织 (factions)：科研机构、宇航员、外星文明、公司势力——记录各方科技势力
3. 科技/能力 (techniques)：高科技装备、人工智能、超能力、科学实验——记录关键科技能力
4. 物品/载具 (items)：飞船、机器人、武器、实验设备——记录关键科技物品
5. 时间线 (timeline)：科技发展、探索历程、任务流程——记录科技发展的关键节点
6. 规则/原理 (rules)：物理法则、社会制度、科技伦理——记录世界运行的科技规则""",

    "言情": """1. 地点/空间 (realms)：家庭、学校、咖啡厅、海边——记录推动感情发展的重要场所
2. 人物/群体 (factions)：男女主、亲友、同事、情敌——记录影响感情的人物群体
3. 情感/技能 (techniques)：沟通方式、约会、误会处理、心理成长——记录情感交互的重要方式
4. 物品/象征 (items)：信物、礼物、信件、纪念品——记录象征感情的关键物品
5. 时间线 (timeline)：相遇、相知、冲突、分离、重逢——记录感情发展的关键节点
6. 规则/社会约束 (rules)：家长安排、社会礼仪、性格矛盾——记录影响感情的社会规则""",

    "魔幻": """1. 奇幻空间 (realms)：魔法王国、神秘森林、奇异岛屿——记录魔幻世界的地理节点
2. 势力/种族 (factions)：精灵、矮人、巫师、魔法组织——记录各方魔幻势力
3. 魔法/技能 (techniques)：咒语、魔法能力、召唤、炼金——记录魔法体系的核心技能
4. 神器/道具 (items)：魔杖、魔法书、护符、传送门——记录关键魔法道具
5. 时间线 (timeline)：冒险旅程、成长过程、史诗事件——记录魔幻冒险的关键节点
6. 规则/魔法法则 (rules)：魔法系统、契约约束、种族规则——记录世界运行的魔法法则""",

    "武侠": """1. 江湖地点 (realms)：山谷、武林门派、城镇、秘境——记录江湖世界的重要地点
2. 势力/门派 (factions)：帮派、门派、朝廷、江湖人物圈——记录各方江湖势力
3. 武功/技能 (techniques)：内功、轻功、剑法、拳掌——记录各路武学体系
4. 兵器/道具 (items)：剑、刀、轻功道具、秘籍——记录关键兵器和武学道具
5. 时间线 (timeline)：比武、仇恨、成长、复仇——记录江湖恩怨的关键节点
6. 规矩/侠义准则 (rules)：江湖规矩、恩怨情仇、正邪观——记录约束江湖人的行为准则""",
}

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

请根据以下维度进行分析（注意每个维度的具体含义）：

{world_fields}

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


REQUERY_PLOT_PROMPT = """你是一个专业的故事分析顾问。用户对之前的剧情分析有以下修改意见，请根据意见重新分析。

{genre_guidance}

已知角色列表：{characters}

当前剧情分析：
{current_plot}

用户修改意见：
{feedback}

请根据用户意见重新分析并输出如下 JSON 对象：
{{
  "main_line": "故事主线",
  "sub_lines": ["支线1", "支线2"],
  "theme": "核心主题",
  "conflict": "主要矛盾",
  "climax": "高潮事件",
  "ending": "结局走向",
  "pacing": "节奏评价",
  "events": [
    {{
      "id": "E001",
      "name": "事件名称",
      "description": "简要描述",
      "chapter_refs": [1, 2],
      "characters_involved": ["角色名"],
      "significance": "重大转折/推进主线/人物成长/背景铺垫"
    }}
  ]
}}

注意：
1. 重点关注用户提出的修改意见
2. 保持原有剧情分析中合理的部分
3. 事件列表应反映修改后的剧情""" + COMMON_JSON_RULE

REQUERY_WORLD_PROMPT = """你是一个小说世界观分析专家。用户对之前的世界观分析有以下修改意见，请根据意见重新分析。

{genre_guidance}

当前世界观分析：
{current_world}

用户修改意见：
{feedback}

请根据用户意见重新分析并输出如下 JSON 对象：
{{
  "realms": [{{"name": "地点名", "description": "描述"}}],
  "factions": [{{"name": "势力名", "description": "描述"}}],
  "techniques": [{{"name": "功法/技能名", "description": "描述"}}],
  "items": [{{"name": "物品名", "description": "描述"}}],
  "timeline": [{{"time": "时间节点", "event": "事件"}}],
  "rules": ["规则1", "规则2"]
}}

注意：
1. 重点关注用户提出的修改意见
2. 保留原分析中合理的部分""" + COMMON_JSON_RULE

REQUERY_CHARACTERS_PROMPT = """你是一个小说角色分析助手。用户对之前的角色分析有修改意见，请严格按照意见修改角色信息。

{genre_guidance}

小说原文片段（供参考角色背景）：
{original_text}

当前角色列表：
{current_characters}

用户修改意见：
{feedback}

请严格按照用户意见修改，输出完整的修改后角色列表 JSON 对象：
{{
  "characters": [
    {{
      "name": "角色名",
      "aliases": ["别名"],
      "gender": "男/女/未知",
      "age": "年龄",
      "description": "简要描述",
      "role": "protagonist/supporting/minor",
      "traits": ["特征1", "特征2"]
    }}
  ]
}}

注意：
1. 严格按照用户意见修改，不要遗漏任何修改要求
2. 如果用户要求将某角色设为主角，必须将该角色的 role 设为 "protagonist"
3. 如果原来已有主角被替换，将其 role 改为 "supporting" 或 "minor"
4. 未涉及的角色保持原有信息不变
5. 每个角色的 id 字段保持与原列表一致""" + COMMON_JSON_RULE

REGENERATE_SCRIPT_PROMPT = """你是一个专业影视编剧。用户对已生成的剧本有以下修改意见，请根据意见重新生成完整的剧本场景列表。

{genre_guidance}

已知角色列表：{characters}

当前剧本：
{current_script}

用户修改意见：
{feedback}

请根据用户意见修改剧本，输出完整的场景列表 JSON（保持 scene_id 不变）：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "scene_heading": "第1场  内景  地点  时间",
      "location": "地点",
      "time_of_day": "时间",
      "characters_present": ["角色1"],
      "action": ["动作描述1", "动作描述2"],
      "dialogues": [
        {{"character": "角色1", "line": "台词", "parenthetical": ""}}
      ],
      "transition": ""
    }}
  ]
}}

注意：
1. 保持原剧本的结构和场景数量
2. 重点关注用户提出的修改意见
3. 对白应该自然有力，符合角色性格""" + COMMON_JSON_RULE
