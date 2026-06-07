# AI 剧本创作助手 — 剧本 YAML Schema 设计文档

## 1. 概述

本 Schema 定义了从小说自动转换生成的剧本的 YAML 数据结构。它是 AI 转换流水线的输出标准，也是下游工具（编辑器、分镜生成、制作排期等）的输入协议。

**系统架构要点：**
- **用户系统**：注册/登录后方可使用，密码 bcrypt 哈希，Token 72 小时过期
- **转换流水线（8 步）**：文本清洗 → 章节检测 → 角色提取 → 剧情分析 → 场景规划 → 剧本生成 → 世界观分析 → Schema 校验
- **AI 重新询问**：用户可针对剧本/剧情/世界观/角色任一维度提交修改意见，AI 根据当前数据 + 原文上下文重新生成并直接写回数据库
- **深度审阅**：版本对比后行数差异 > 30 行时触发，AI 同时审阅版本 A YAML + 版本 B YAML + 小说原文 + 用户补充意见，综合生成新剧本
- **版本历史**：每次重新询问前自动保存完整快照（角色/剧情/场景规划/剧本场景/YAML/世界观），支持双版本差异对比和任意版本回滚
- **在线编辑**：角色/剧情/场景规划/对白均支持行内编辑，修改直接持久化
- **持久化**：所有数据存于 SQLite（12 张表），无需额外配置

**核心设计目标：**
- **可读性优先**：YAML 格式天然适合人类阅读和手动编辑。
- **结构化但不失灵活性**：固定字段承载剧本核心要素，同时允许字段为空。
- **工具链友好**：严格键名和嵌套层级确保程序可无歧义解析。
- **可验证性**：内建主角验证和 Schema 校验结果。
- **可迭代性**：通过重新询问 + 版本历史实现"反馈→生成→对比→回滚"闭环。
- **类型适配**：6 种内置类型 + 用户自定义（最多 10 个），每种有独立 AI 分析指引。
- **中文原生支持**：所有字段值均支持中文。

---

## 2. 顶层结构

```yaml
meta:   # 元信息（含验证结果 + 角色详情）
script: # 场景列表
```

| 键 | 类型 | 必需 | 说明 |
|----|------|------|------|
| `meta` | Mapping | 是 | 剧本级别的元信息、验证结果、角色详情 |
| `script` | Sequence | 是 | 按先后顺序排列的场景列表 |

---

## 3. `meta` 元信息

```yaml
meta:
  title: "离奇的来信"
  genre: "科幻"
  chapter_count: 3
  scene_count: 6
  character_count: 3
  characters:
    - "林晓"
    - "陈默"
    - "周老板"
  character_details:
    - id: "C001"
      name: "林晓"
      gender: "女"
      age: "28"
      role: "protagonist"
      description: "28岁女程序员，独自租房居住"
      traits: ["冷静", "聪明"]
      aliases: ["晓晓"]
      relationships:
        - target: "陈默"
          relation: "室友"
  validation:
    main_character: "林晓"
    count: 2
    status: "验证通过"
    retried: false
  schema_validation:
    passed: true
    warnings: []
    errors: []
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 剧本标题，优先使用首个章节标题 |
| `genre` | string | 小说类型 |
| `chapter_count` | int | 源小说被转换的章节数 |
| `scene_count` | int | 总场景数 |
| `character_count` | int | 角色数 |
| `characters` | string[] | 角色姓名列表 |
| `character_details` | object[] | 完整角色信息（含性别/年龄/性格特征/关系） |
| `validation` | Mapping | 主角验证结果 |
| `schema_validation` | Mapping | Schema 校验结果 |

---

## 4. `character_details` 角色详情

```yaml
character_details:
  - id: "C001"
    name: "林晓"
    gender: "女"
    age: "28"
    role: "protagonist"
    description: "28岁女程序员，对技术敏感，性格内向但坚韧"
    traits: ["冷静", "聪明", "内向"]
    aliases: ["晓晓", "小林"]
    relationships:
      - target: "陈默"
        relation: "室友"
      - target: "周老板"
        relation: "线索提供者"
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 角色唯一标识（C001 格式） |
| `name` | string | 姓名 |
| `gender` | string | 性别（男/女/未知） |
| `age` | string | 年龄 |
| `role` | string | 角色类型：protagonist / supporting / minor |
| `description` | string | 人物描述 |
| `traits` | string[] | 性格特征 |
| `aliases` | string[] | 别名/昵称 |
| `relationships` | object[] | 人物关系（target + relation） |

---

## 5. `validation` 主角验证

```yaml
validation:
  main_character: "林晓"
  count: 2
  status: "验证通过"
  retried: false
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `main_character` | string | AI 判定的主角姓名 |
| `count` | int | 验证评分（0-2），2 为通过 |
| `status` | string | "验证通过" 或 "验证未通过" |
| `retried` | bool | 是否已重试 |

### 验证逻辑

```
Step A: 扫描所有场景，按出场次数 + 类型关键词加分，选出主角候选
Step B: 遍历原文每章，统计主角名出现次数 → 每章 ≥5 次则 count += 1
Step C: 检查主角动作与原文事件相关性 → >50% 则 count += 1
Step D: 若 count < 2 → 自动换候选重算一次 → 仍不通过则前端显示警告
```

---

## 6. `schema_validation` Schema 校验

```yaml
schema_validation:
  passed: true
  warnings:
    - "场景 3 对白角色 '王五' 不在该场角色列表中"
  errors: []
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `passed` | bool | 校验是否通过 |
| `warnings` | string[] | 警告（不影响使用） |
| `errors` | string[] | 错误列表 |

### 校验规则

| 检查项 | 失败处理 |
|--------|---------|
| `scene_id` 不为空 | 自动补序号 |
| `characters_present` 中角色在已知角色列表中 | 记录警告 |
| `dialogues[].character` 在 `characters_present` 中 | 记录警告 |
| `location` 不为空 | 记录警告 |
| `scene_heading` 不为空 | 自动生成 |

校验失败时自动调用 AI 修复，最多 3 次重试。

---

## 7. `script` 场景列表

```yaml
script:
  - scene_id: 1
    scene_heading: "第1场  内景  张三的公寓  上午"
    location: "张三的公寓"
    time_of_day: "上午"
    characters_present:
      - "张三"
    action:
      - "张三从床上醒来，揉了揉眼睛。"
      - "他拿起手机，屏幕上显示一条未读消息。"
    dialogues:
      - character: "张三"
        line: "谁这么早发消息..."
        parenthetical: ""
    transition: "切至"
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `scene_id` | int | 是 | 全局唯一场景序号，从 1 开始 |
| `scene_heading` | string | 是 | 场景标题（场号 + 地点 + 时间） |
| `location` | string | 否 | 场景地点 |
| `time_of_day` | string | 否 | 时间段（上午/下午/傍晚/夜晚/深夜） |
| `characters_present` | string[] | 否 | 出场角色列表 |
| `action` | string[] | 否 | 动作描述数组 |
| `dialogues` | Sequence | 否 | 对白列表（时序排列） |
| `transition` | string | 否 | 转场提示（切至/淡入/淡出），空字符串表示无显式转场 |

### 对白子结构

```yaml
dialogues:
  - character: "张三"
    line: "谁这么早发消息..."
    parenthetical: "（拿起手机，皱眉）"
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `character` | string | 是 | 说话的角色名 |
| `line` | string | 是 | 台词正文 |
| `parenthetical` | string | 否 | 夹注/动作提示 |

---

## 8. AI 重新询问系统

### 设计目标

- 允许用户针对四类目标提交修改意见：**剧本 / 剧情 / 世界观 / 角色**
- AI 接收当前数据 + 用户反馈 + 原文上下文（前 10 章），返回修改后的完整结果
- 结果直接写入数据库对应表，前端即时刷新显示
- 每次询问前自动保存版本快照供回滚

### 工作流程

```
用户选择目标 → 输入修改意见 → 提交
  ↓
保存版本快照（当前全部数据）
  ↓
后端加载当前数据 + 原文上下文 + 反馈 → 注入对应 Prompt → 调用 DeepSeek
  ↓
AI 返回新数据 → 写入数据库 → 前端刷新
```

### 四类 Prompt

| 目标 | Prompt | 注入参数 |
|------|--------|---------|
| `script` | REGENERATE_SCRIPT_PROMPT | genre_guidance, characters, current_script[:6000], feedback |
| `plot` | REQUERY_PLOT_PROMPT | genre_guidance, characters, current_plot[:4000], feedback |
| `world` | REQUERY_WORLD_PROMPT | genre_guidance, current_world[:4000], feedback |
| `characters` | REQUERY_CHARACTERS_PROMPT | genre_guidance, original_text[:3000], current_characters[:4000], feedback |

### 深度审阅

当版本对比发现两个版本 YAML 行数差 > 30 行时触发，工作流程：

```
用户选择两个版本对比 → 行数差 > 30 → 显示审阅面板
  → 用户输入补充意见（如"B版场景划分合理但A版对白更自然"）
  → AI 同时审阅：版本A YAML[:3000] + 版本B YAML[:3000] + 原文[:4000] + 补充意见
  → 综合生成新剧本 → 自动保存为新版本
```

| Prompt | 注入参数 |
|--------|---------|
| `DEEP_REVIEW_PROMPT` | genre_guidance, characters, original_text[:4000], version_a_summary[:3000], version_b_summary[:3000], feedback |

---

## 9. 版本历史系统

### 快照内容

每次保存版本时，从数据库读取并序列化以下全部数据：

```
project_characters  →  角色列表（含关系/特征）
plot_analysis       →  剧情分析（主线/主题/冲突/事件）
scene_plan          →  场景规划
script_scenes       →  剧本场景（含对白/动作）
project_yaml        →  YAML 剧本文本
world_building      →  世界观分析
```

### 版本操作

| 操作 | 说明 |
|------|------|
| 自动保存 | 每次 AI 重新询问前自动触发 |
| 手动保存 | 版本历史面板中「+ 保存当前版本」 |
| 差异对比 | 选择任意两个版本，对比角色/剧情/事件/场景/剧本/YAML 差异 |
| 版本回滚 | 恢复到指定版本的完整数据（覆盖当前） |
| 自动清理 | 每个项目最多保留 10 个版本，超出自动删除最旧 |

---

## 10. 小说类型系统

### 数据结构

```json
{
  "name": "悬疑",
  "guidance": "这是一部悬疑小说。请重点关注线索铺设、反转设计...",
  "keywords": ["侦探", "嫌疑人", "线索", "密室"]
}
```

| 字段 | 说明 |
|------|------|
| `name` | 类型名称 |
| `guidance` | AI 指引描述，注入到角色提取/剧情分析/剧本生成的 Prompt 中 |
| `keywords` | 主角关键词，用于 Count 验证中为主角候选加权评分 |

### 隔离逻辑

| 角色 | 可见类型 |
|------|---------|
| 用户 A | 6 个系统默认 + 用户 A 的自定义（最多 10） |
| 用户 B | 6 个系统默认 + 用户 B 的自定义（最多 10） |

系统默认类型不可编辑/删除，自定义类型达到 10 个上限后添加按钮禁用。

### 类型适配的世界观维度

每种小说类型在生成世界观分析时使用不同的维度描述（`WORLD_FIELDS`）：

| 类型 | realms | factions | techniques | items |
|------|--------|----------|------------|-------|
| 叙事 | 地点/环境 | 人物/群体 | 能力/经历 | 物品/符号 |
| 玄幻 | 界域/地点 | 势力/宗门 | 功法/技能 | 法宝/物品 |
| 科幻 | 空间/星域 | 群体/组织 | 科技/能力 | 物品/载具 |
| 言情 | 地点/空间 | 人物/群体 | 情感/技能 | 物品/象征 |
| 魔幻 | 奇幻空间 | 势力/种族 | 魔法/技能 | 神器/道具 |
| 武侠 | 江湖地点 | 势力/门派 | 武功/技能 | 兵器/道具 |

前端 `WorldSection` 据此显示不同的栏目名称。

---

## 11. 完整示例

```yaml
meta:
  title: "离奇的来信"
  genre: "科幻"
  chapter_count: 3
  scene_count: 6
  character_count: 3
  characters:
    - "林晓"
    - "陈默"
    - "周老板"
  character_details:
    - id: "C001"
      name: "林晓"
      gender: "女"
      age: "28"
      role: "protagonist"
      description: "28岁女程序员，对技术敏感"
      traits: ["冷静", "聪明", "内向"]
      aliases: ["晓晓"]
      relationships:
        - target: "陈默"
          relation: "室友"
    - id: "C002"
      name: "陈默"
      gender: "女"
      age: "27"
      role: "supporting"
      description: "林晓的室友，性格开朗"
      traits: ["活泼", "善良"]
      aliases: []
      relationships:
        - target: "林晓"
          relation: "室友"
    - id: "C003"
      name: "周老板"
      gender: "男"
      age: "45"
      role: "minor"
      description: "神秘中年男人，穿唐装，开咖啡馆"
      traits: ["神秘", "深沉"]
      aliases: []
      relationships: []
  validation:
    main_character: "林晓"
    count: 2
    status: "验证通过"
    retried: false
  schema_validation:
    passed: true
    warnings: []
    errors: []

script:
  - scene_id: 1
    scene_heading: "第1场  内景  林晓的出租屋  夜晚"
    location: "林晓的出租屋"
    time_of_day: "夜晚"
    characters_present: ["林晓"]
    action:
      - "林晓坐在书桌前，笔记本屏幕的蓝光照亮她的脸。"
      - "她刷新邮箱，一封标题为【你被选中了】的邮件出现。"
    dialogues:
      - character: "林晓"
        line: "又是垃圾邮件..."
        parenthetical: ""
    transition: ""

  - scene_id: 2
    scene_heading: "第2场  内景  林晓的出租屋  夜晚"
    location: "林晓的出租屋"
    time_of_day: "夜晚"
    characters_present: ["林晓", "陈默"]
    action:
      - "林晓犹豫片刻，还是点开了邮件。"
      - "室友陈默推门进来，手里提着外卖。"
    dialogues:
      - character: "陈默"
        line: "还在加班？我带了宵夜。"
        parenthetical: "（将外卖放在桌上）"
      - character: "林晓"
        line: "你看这个——有人知道我的秘密邮箱地址。"
        parenthetical: "（指着屏幕，声音微颤）"
    transition: "切至"

  - scene_id: 3
    scene_heading: "第3场  内景  咖啡馆  上午"
    location: "街角咖啡馆"
    time_of_day: "上午"
    characters_present: ["林晓", "周老板"]
    action:
      - "林晓根据邮件地址来到一家老旧咖啡馆。"
      - "角落坐着一个穿唐装的中年男人。"
    dialogues:
      - character: "周老板"
        line: "林小姐，请坐。我知道你会来。"
        parenthetical: "（微微一笑，做个请的手势）"
      - character: "林晓"
        line: "你到底是谁？为什么要找我？"
        parenthetical: ""
    transition: ""
```

---

## 12. 扩展性考虑

| 扩展 | 位置 | 方式 |
|------|------|------|
| 章节分组 | `script` 中插入 `chapter_break` | 在场景间添加 `{type: "chapter_break", title: "第二章"}` |
| 分镜信息 | `action`/`dialogues` 新增 `shot` 字段 | 可选子字段 |
| BGM/音效 | `scene` 新增 `audio` 字段 | 可选扩展 |
| 审阅批注 | 整个文档支持 `_comments` 顶层键 | 工具链可忽略 |
| 自定义类型 | `user_genres` 表 per-user 存储 | 已实现，最多 10 个 |
| 多用户协作 | 引入权限系统 + 共享项目 | 未来方向 |

---

## 13. 与其他剧本格式的关系

| 格式 | 对比 |
|------|------|
| **Final Draft (.fdx)** | XML 格式，复杂且不易人类编辑。本 YAML Schema 更轻量。 |
| **Fountain** | 纯文本标记语言，不结构化，程序解析困难。 |
| **JSON** | YAML 可读性远高于 JSON，尤其对非技术背景的小说作者。 |

YAML 的核心优势：**作者拿到的是一个可直接阅读的文档，而非需要特殊软件打开的格式**。

---

*文档版本: 5.0 · 最后更新: 2026-06-07*
