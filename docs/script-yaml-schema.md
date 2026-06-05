# AI 剧本创作工具 — 剧本 YAML Schema 设计文档

## 1. 概述

本 Schema 定义了从小说自动转换生成的剧本的 YAML 数据结构。它作为 AI 转换流水线的输出标准，也是下游工具（编辑器、分镜生成、制作排期等）的输入协议。

**转换流水线（7 步）：** 文本清洗 → 章节检测 → 角色提取 → 场景切分 → 剧本转换 → 主角验证 → Schema 校验

**核心设计目标：**
- **可读性优先**：YAML 格式天然适合人类阅读和手动编辑，作者拿到初稿后可直接修改。
- **结构化但不失灵活性**：用固定字段承载剧本核心要素（场景、对白、动作），同时允许字段为空以适应不同风格。
- **工具链友好**：严格的键名和嵌套层级确保程序可无歧义解析。
- **可验证性**：内建主角验证计数（Count）和 Schema 校验结果，供作者快速判断生成质量。
- **类型适配**：支持用户指定小说类型（武侠/玄幻/科幻/言情/叙事/魔幻或自定义），AI 据此调整分析侧重点。
- **中文原生支持**：所有字段值均支持中文，不使用英文缩写。

---

## 2. 顶层结构

```yaml
meta:   # 元信息（含验证结果）
script: # 场景列表
```

| 键 | 类型 | 必需 | 说明 |
|----|------|------|------|
| `meta` | Mapping | 是 | 剧本级别的元信息、验证结果、角色详情 |
| `script` | Sequence | 是 | 按先后顺序排列的场景列表 |

### 设计原因

将元信息与剧本内容分离在两个顶层键下：

1. **消费者可按需读取**：如果只需要统计信息或验证结果，仅解析 `meta` 即可，无需遍历整个 `script`。
2. **编辑隔离**：作者后续手动修改剧本内容时改动集中在 `script` 下，避免误触元信息和验证数据。
3. **版本管理友好**：Git diff 中元信息的变更不会淹没在剧本内容变更中。

---

## 3. `meta` 元信息

```yaml
meta:
  title: "第一章 离奇的来信"    # 剧本标题
  genre: "科幻"                 # 小说类型
  source_chapters: 3            # 源小说章节数
  total_scenes: 6               # 总场景数
  characters:                    # 角色姓名清单
    - "林晓"
    - "程帆"
    - "周老板"
  character_details:             # 角色详情（AI 提取的原始数据）
    - id: "C001"
      name: "林晓"
      role: "protagonist"
      description: "28岁的女程序员，独自租房居住"
      aliases: ["晓晓"]
    - id: "C002"
      name: "程帆"
      role: "supporting"
      description: "林晓的室友，性格开朗"
      aliases: []
  validation:                    # 主角验证结果
    main_character: "林晓"
    count: 2
    status: "验证通过"
    retried: false
  schema_validation:             # Schema 校验结果
    passed: true
    warnings: []
    errors: []
  generated_at: "2026-06-05T14:30:00"
```

### 字段说明

| 字段 | 类型 | 说明 | 设计原因 |
|------|------|------|----------|
| `title` | string | 剧本标题，取自小说第一章标题或全文推断 | 提供辨识度，方便多剧本管理 |
| `genre` | string | 小说类型，由用户在界面上选择或自定义 | AI 据此调整角色提取和场景分析的侧重点；产出物可追溯类型 |
| `source_chapters` | int | 源小说被转换的章节数 | 追溯剧本覆盖范围 |
| `total_scenes` | int | 转换后总场景数 | 快速评估剧本体量 |
| `characters` | string[] | 所有角色姓名列表 | 作为角色清单供作者核对完整性 |
| `character_details` | object[] | AI 提取的完整角色信息（id、角色类型、描述、别名） | 保留 AI 中间产物供作者参考；与 `characters` 互补 |
| `validation` | Mapping | 主角验证结果（见下方） | 让作者快速判断 AI 是否正确识别了主角 |
| `schema_validation` | Mapping | Schema 校验结果（见下方） | 标注自动修复或遗留的结构问题 |
| `generated_at` | string | AI 生成时间（ISO 8601） | 区分不同版本，对比迭代 |

### 为何 `characters` 和 `character_details` 并存

- `characters`：简洁的姓名清单，供工具链和快速索引使用
- `character_details`：AI 推断的完整人物信息（含角色类型、描述等），是中间产物。两个字段共存：前者保证读取效率，后者保留 AI 上下文。

---

## 4. `validation` 主角验证

```yaml
validation:
  main_character: "林晓"
  count: 2
  status: "验证通过"
  retried: false
```

| 字段 | 类型 | 说明 | 设计原因 |
|------|------|------|----------|
| `main_character` | string | AI 判定的主角姓名 | 供作者快速确认 |
| `count` | int | 验证评分（0-2），2 为通过 | 两维度验证：①每章出场次数≥5 ②主角动作与原文事件一致性>50% |
| `status` | string | "验证通过" 或 "验证未通过，请手动确认主角" | 人类可读的状态标签 |
| `retried` | bool | 是否已执行过重试 | 重试最多 1 次：首次 count<2 时换次高出场角色重算；若仍<2，直接输出结果 |

### 验证逻辑（Count 机制）

```
Step A: 扫描 YAML 所有场景，按出场次数 + 类型关键词加分，选出主角候选
Step B: 遍历原文每章，统计主角名出现次数 → 每章 ≥5 次则 count += 1
Step C: 检查 YAML 中主角动作与原文事件的相关性 → >50% 则 count += 1
Step D: 若 count < 2 → 换候选角色重试一次 → 仍 <2 则直接输出
```

### 设计原因：为何要主角验证

小说改编剧本时，主角视角统一至关重要。AI 可能将次要角色误判为主角，导致剧本偏离原作主线。Count 机制通过原文频率 + 动作一致性双重验证，降低误判概率。`retried` 字段记录重试状态，帮助作者理解系统行为。

---

## 5. `schema_validation` Schema 校验

```yaml
schema_validation:
  passed: true
  warnings:
    - "场景 3 对白角色 '王五' 不在该场角色列表中"
  errors: []
```

| 字段 | 类型 | 说明 | 设计原因 |
|------|------|------|----------|
| `passed` | bool | 校验是否通过 | 快速判断是否需要人工介入 |
| `warnings` | string[] | 警告信息列表 | 轻微问题（如对白角色不在出场列表中），不影响使用 |
| `errors` | string[] | 错误信息列表 | 严重问题（当前版本主要产生警告） |

### 校验规则

| 检查项 | 失败处理 |
|--------|---------|
| `scene_id` 不为空 | 自动补序号 |
| `characters_present` 中角色在 `meta.characters` 中存在 | 记录警告 |
| `dialogues[].character` 在 `characters_present` 中 | 记录警告 |
| `location` 不为空 | 记录警告 |
| `scene_heading` 不为空 | 自动生成 |

校验失败时重试最多 1 次自动修复；二次仍未通过则直接输出并记录警告。

---

## 6. `script` 场景列表

每个场景是一个 Mapping，按剧中出现顺序排列：

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

### 字段说明

| 字段 | 类型 | 必需 | 说明 | 设计原因 |
|------|------|------|------|----------|
| `scene_id` | int | 是 | 全局唯一场景序号，从 1 开始 | 供引用和跳转；数字比字符串 ID 更短且天然有序 |
| `scene_heading` | string | 是 | 场景标题（场号 + 地点 + 时间），如"第1场 内景 咖啡馆 日" | 传统剧本格式的标题行，人类阅读和打印时最直观 |
| `location` | string | 否 | 场景地点 | 与 scene_heading 信息有重叠但以结构化形式存储，方便按拍摄地点排期 |
| `time_of_day` | string | 否 | 大致时间段（上午/下午/傍晚/夜晚/深夜） | 辅助拍摄计划，比精确时间更通用 |
| `characters_present` | string[] | 否 | 该场景出场的角色姓名列表 | 快速确认哪些演员需要到场；与 schema_validation 交叉校验 |
| `action` | string[] | 否 | 动作描述数组 | 方便在编辑器中逐行动作修改；格式统一 |
| `dialogues` | Sequence | 否 | 对白列表（时序排列） | 剧本核心；见下方对白子结构 |
| `transition` | string | 否 | 转场提示（如"切至""淡入""淡出"），空字符串表示无需显式转场 | 影视制作需要，但小说改编时常为空，故设计为可选 |

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
| `parenthetical` | string | 否 | 夹注/动作提示（括号内的表演指示），AI 可能留空 |

### 为何 `action` 和 `dialogues` 都是数组

- **`action` 为数组**而非一段长文本：方便在编辑器中逐行动作修改，也方便按动作节点插入新的对白。
- **`dialogues` 为数组**：保持对白的时序关系。每个对话项独立，方便增删和重排。

### 为何不做更细粒度的"镜头"层级

剧本（Screenplay）位于比"分镜脚本（Shot List）"更上的抽象层。本 Schema 定位在**剧本层面**，不包含景别、运镜方式、镜头号等导演/摄影层面的信息。可扩展可选的 `shot` 子字段。

---

## 7. 小说类型系统（Genre System）

类型数据持久化在 `genres.json` 中，结构如下：

```json
{
  "name": "武侠",
  "guidance": "这是一部武侠小说。请重点关注江湖纷争、武打场面...",
  "keywords": ["侠", "掌门", "江湖", "刀", "剑"]
}
```

| 字段 | 说明 |
|------|------|
| `name` | 类型名称，用户在下拉框中选择，支持自定义 |
| `guidance` | AI 指引描述，注入到角色提取、场景切分、剧本转换的 Prompt 中 |
| `keywords` | 主角关键词，用于 Count 验证中为主角候选加权评分 |

### 设计原因：硬编码 vs 动态配置

初始版本将 6 种类型硬编码在代码中。但小说类型高度多样化（悬疑、历史、军事、末日等），硬编码无法满足所有作者。改为 JSON 动态配置后：
- 用户可通过界面随时增删改类型，无需改代码
- 每种类型可独立配置 AI 指引和验证关键词
- `genres.json` 是纯文本文件，便于备份和分享

---

## 8. 完整示例

```yaml
meta:
  title: "第一章 离奇的来信"
  genre: "科幻"
  source_chapters: 3
  total_scenes: 6
  characters:
    - "林晓"
    - "程帆"
    - "周老板"
  character_details:
    - id: "C001"
      name: "林晓"
      role: "protagonist"
      description: "28岁的女程序员，独自租房居住，对技术敏感"
      aliases: ["晓晓"]
    - id: "C002"
      name: "程帆"
      role: "supporting"
      description: "林晓的室友，性格开朗，喜欢打游戏"
      aliases: []
    - id: "C003"
      name: "周老板"
      role: "minor"
      description: "神秘的中年男人，穿唐装，开一家老旧咖啡馆"
      aliases: []
  validation:
    main_character: "林晓"
    count: 2
    status: "验证通过"
    retried: false
  schema_validation:
    passed: true
    warnings: []
    errors: []
  generated_at: "2026-06-05T14:30:00"

script:
  - scene_id: 1
    scene_heading: "第1场  内景  林晓的出租屋  夜晚"
    location: "林晓的出租屋"
    time_of_day: "夜晚"
    characters_present:
      - "林晓"
    action:
      - "林晓坐在破旧的书桌前，笔记本电脑屏幕的蓝光照亮她的脸。"
      - "她刷新邮箱，一封标题为【你被选中了】的邮件出现在收件箱顶部。"
    dialogues:
      - character: "林晓"
        line: "又是垃圾邮件..."
        parenthetical: ""
    transition: ""

  - scene_id: 2
    scene_heading: "第2场  内景  林晓的出租屋  夜晚"
    location: "林晓的出租屋"
    time_of_day: "夜晚"
    characters_present:
      - "林晓"
      - "程帆"
    action:
      - "林晓犹豫片刻，还是点开了邮件。"
      - "室友陈默推门进来，手里提着两袋外卖。"
    dialogues:
      - character: "程帆"
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
    characters_present:
      - "林晓"
      - "周老板"
    action:
      - "林晓根据邮件中的地址来到一家老旧的咖啡馆。"
      - "角落里坐着一个穿唐装的中年男人，桌上放着一杯没动过的茶。"
    dialogues:
      - character: "周老板"
        line: "林小姐，请坐。我知道你会来。"
        parenthetical: "（微微一笑，做了个请的手势）"
      - character: "林晓"
        line: "你到底是谁？为什么要找我？"
        parenthetical: ""
    transition: ""
```

---

## 9. 扩展性考虑

Schema 采用"开放封闭"原则：核心字段固定（封闭），不阻止添加额外字段（开放）。

| 扩展 | 位置 | 方式 |
|------|------|------|
| 章节分组 | `script` 中插入 `chapter_break` | 在场景间添加 `{type: "chapter_break", title: "第二章"}` |
| 分镜信息 | `action`/`dialogues` 新增 `shot` 字段 | 可选子字段，不影响当前解析器 |
| BGM/音效 | `scene` 新增 `audio` 字段 | 可选扩展 |
| 审阅批注 | 整个文档支持 `_comments` 顶层键 | 工具链可忽略此键 |
| 自定义类型 | `genres.json` 动态增删 | 已实现，通过 API + UI 管理 |

---

## 10. 与其他剧本格式的关系

| 格式 | 对比 |
|------|------|
| **Final Draft (.fdx)** | 工业标准，XML 格式，复杂且不易人类编辑。本 YAML Schema 更轻量、更适合 AI 生成和人工审阅。 |
| **Fountain** | 纯文本标记语言，简洁但不结构化，程序解析困难。本 Schema 在可读性和可解析性之间取得平衡。 |
| **JSON** | 同结构下 YAML 的可读性远高于 JSON，尤其对非技术背景的小说作者而言。 |

YAML 的选择核心在于：**作者拿到的是一个可直接阅读的文档，而非需要特殊软件打开的格式**。

---

*文档版本: 2.0 · 最后更新: 2026-06-05*
