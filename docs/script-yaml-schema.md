# AI 剧本创作工具 — 剧本 YAML Schema 设计文档

## 1. 概述

本 Schema 定义了从小说自动转换生成的剧本的 YAML 数据结构。它作为 AI 转换流水线的输出标准，也是下游工具（编辑器、分镜生成、制作排期等）的输入协议。

**系统架构要点：**
- **用户系统**：注册/登录后方可使用，用户信息存于 SQLite 数据库（`app.db`），密码 SHA256 哈希
- **数据持久化**：所有转换结果持久保存至 SQLite，支持历史记录查询、查看、删除
- **在线编辑器**：生成的 YAML 剧本可直接在页面上编辑并保存，无需下载后修改
- **转换流水线（7 步）**：文本清洗 → 章节检测 → 角色提取 → 场景切分 → 剧本转换 → 主角验证 → Schema 校验
- **智能重生成**：验证不达标时不自动重试，改为向用户征求补充信息后完整重跑流水线
- **自动迁移**：首次启动时自动将旧的 `users.json` / `genres.json` 迁移至 SQLite

**核心设计目标：**
- **可读性优先**：YAML 格式天然适合人类阅读和手动编辑，作者拿到初稿后可直接修改。
- **结构化但不失灵活性**：用固定字段承载剧本核心要素（场景、对白、动作），同时允许字段为空以适应不同风格。
- **工具链友好**：严格的键名和嵌套层级确保程序可无歧义解析。
- **可验证性**：内建主角验证计数（Count）和 Schema 校验结果，供作者快速判断生成质量。
- **类型适配**：支持小说类型选择（系统默认 6 种 + 用户自定义最多 10 种），AI 据此调整分析侧重点。
- **用户隔离**：自定义类型、转换历史等数据按用户隔离，互不影响。
- **中文原生支持**：所有字段值均支持中文，不使用英文缩写。

---

## 2. 数据库设计

系统使用 SQLite（WAL 模式）进行数据持久化，包含 3 张核心表：

### 2.1 users

```sql
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,    -- SHA256 哈希
    token    TEXT,                  -- UUID 登录令牌，每次登录刷新
    created_at TEXT NOT NULL        -- ISO 8601
);
```

### 2.2 genres

```sql
CREATE TABLE genres (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,        -- 类型名称
    guidance  TEXT DEFAULT '',      -- AI 指引描述
    keywords  TEXT DEFAULT '[]',    -- JSON 数组：主角关键词
    is_system INTEGER DEFAULT 0,    -- 1=系统默认, 0=用户自定义
    username  TEXT                  -- NULL=系统级，非NULL=用户级
);
```

| 类型 | is_system | username | 权限 |
|------|-----------|----------|------|
| 系统默认（6 种） | 1 | NULL | 所有用户共享，不可编辑/删除 |
| 用户自定义（≤10） | 0 | 用户名 | 仅自己可见，可增删改 |

### 2.3 conversions

```sql
CREATE TABLE conversions (
    id               TEXT PRIMARY KEY,  -- UUID task_id
    username         TEXT NOT NULL,
    title            TEXT DEFAULT '',
    genre            TEXT DEFAULT '叙事',
    original_text    TEXT NOT NULL,     -- 原始输入文本
    cleaned_text     TEXT,             -- 清洗后文本
    yaml_output      TEXT,             -- 最终 YAML 输出
    meta_json        TEXT,             -- JSON: 元信息
    intermediate_json TEXT,            -- JSON: 中间产物（角色/场景/章节）
    status           TEXT DEFAULT 'pending',  -- pending/processing/completed/failed/regenerating
    progress_json    TEXT,             -- JSON: 当前进度
    error            TEXT,             -- 错误信息
    hints            TEXT,             -- 用户补充信息
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (username) REFERENCES users(username)
);
```

转换任务状态流转：

```
pending → processing → completed
                    → failed
         regenerating → completed
                      → failed
```

---

## 3. 顶层结构

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

1. **消费者可按需读取**：如果只需要统计信息或验证结果，仅解析 `meta` 即可。
2. **编辑隔离**：作者后续手动修改剧本内容时改动集中在 `script` 下。
3. **版本管理友好**：Git diff 中元信息的变更不会淹没在剧本内容变更中。

---

## 4. `meta` 元信息

```yaml
meta:
  title: "离奇的来信"            # 剧本标题（用户可自定义，留空则用第一章标题）
  genre: "科幻"                  # 小说类型
  source_chapters: 3             # 源小说章节数
  total_scenes: 6                # 总场景数
  characters:                     # 角色姓名清单
    - "林晓"
    - "陈默"
    - "周老板"
  character_details:              # 角色详情
    - id: "C001"
      name: "林晓"
      role: "protagonist"
      description: "28岁的女程序员，独自租房居住"
      aliases: ["晓晓"]
  validation:                     # 主角验证结果
    main_character: "林晓"
    count: 2
    status: "验证通过"
    retried: false
  schema_validation:              # Schema 校验结果
    passed: true
    warnings: []
    errors: []
  generated_at: "2026-06-05T14:30:00"
```

### 字段说明

| 字段 | 类型 | 说明 | 设计原因 |
|------|------|------|----------|
| `title` | string | 剧本标题，优先使用用户在输入界面填写的标题，留空则回退为第一章标题 | 作者可自定义有意义的标题，而非被第一章标题限制 |
| `genre` | string | 小说类型，由用户在下拉框中选择（系统默认 6 种 + 用户自定义类型） | AI 据此调整分析侧重点；类型数据按用户隔离 |
| `source_chapters` | int | 源小说被转换的章节数 | 追溯剧本覆盖范围 |
| `total_scenes` | int | 转换后总场景数 | 快速评估剧本体量 |
| `characters` | string[] | 所有角色姓名列表 | 角色清单供作者核对 |
| `character_details` | object[] | AI 提取的完整角色信息 | 保留 AI 中间产物供参考 |
| `validation` | Mapping | 主角验证结果 | 快速判断 AI 是否正确识别了主角 |
| `schema_validation` | Mapping | Schema 校验结果 | 标注自动修复或遗留的结构问题 |
| `generated_at` | string | AI 生成时间（ISO 8601） | 区分不同版本，对比迭代 |

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
| `status` | string | "验证通过" 或 "验证未通过，请手动确认主角" |
| `retried` | bool | 是否已由用户提供补充信息并重新生成 |

### 验证逻辑（Count 机制）

```
Step A: 扫描 YAML 所有场景，按出场次数 + 类型关键词加分，选出主角候选
Step B: 遍历原文每章，统计主角名出现次数 → 每章 ≥5 次则 count += 1
Step C: 检查 YAML 中主角动作与原文事件的相关性 → >50% 则 count += 1
Step D: 若 count < 2 → 界面提示用户输入补充信息 → 全文重跑流水线 → 重新验证
        用户也可选择跳过，直接使用当前结果
```

### 设计原因：为何不自动重试

v2.0 中 count < 2 时会自动换候选角色重算。但这只是"从错误选项中再选一次"，并未解决根本问题。v3.0 改为向用户征求补充信息（如"主角是林晓，故事是悬疑向"），将其作为额外上下文注入原文后重新跑完整流水线，从根本上改善 AI 的理解。同时保留"跳过"选项，不强制用户等待。

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
| `warnings` | string[] | 警告信息列表（不影响使用） |
| `errors` | string[] | 错误信息列表 |

### 校验规则

| 检查项 | 失败处理 |
|--------|---------|
| `scene_id` 不为空 | 自动补序号 |
| `characters_present` 中角色在 `meta.characters` 中存在 | 记录警告 |
| `dialogues[].character` 在 `characters_present` 中 | 记录警告 |
| `location` 不为空 | 记录警告 |
| `scene_heading` 不为空 | 自动生成 |

校验失败时自动修复最多 1 次；二次仍未通过则输出并记录警告。

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
| `characters_present` | string[] | 否 | 该场景出场的角色姓名列表 |
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

## 8. API 端点参考

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 注册新用户（用户名 2-20 字符，密码 ≥4 字符） |
| POST | `/api/auth/login` | 否 | 登录，返回 UUID Token |
| GET | `/api/auth/me` | Bearer | 获取当前用户信息 |
| GET | `/api/genres` | Bearer | 列出所有类型（系统+自定义，含 readonly 标记） |
| POST | `/api/genres` | Bearer | 添加自定义类型（最多 10 个） |
| PUT | `/api/genres/{index}` | Bearer | 修改自定义类型 |
| DELETE | `/api/genres/{index}` | Bearer | 删除自定义类型 |
| POST | `/api/convert` | Bearer | 启动转换（文本≥100字符，≥3章），返回 task_id |
| GET | `/api/convert/{id}/progress` | ?token= | SSE 进度流（每 0.5s 推送） |
| GET | `/api/convert/{id}/result` | Bearer | 获取完成的转换结果（YAML + Meta） |
| POST | `/api/convert/{id}/regenerate` | Bearer | 提交补充信息后重新生成 |
| GET | `/api/conversions` | Bearer | 查询当前用户的转换历史列表 |
| PUT | `/api/conversions/{id}` | Bearer | 在线编辑已生成的 YAML 剧本 |
| DELETE | `/api/conversions/{id}` | Bearer | 删除一条历史记录 |

---

## 9. 在线编辑功能

v4.0 新增：生成的 YAML 剧本支持在线编辑，无需下载到本地修改。

**流程：**
1. 转换完成后，YAML 预览区右上角出现「编辑」按钮
2. 点击进入编辑模式，YAML 代码以等宽字体显示在可编辑的 textarea 中
3. 修改后点击「保存」，通过 `PUT /api/conversions/{id}` 将新内容回写至数据库
4. 保存成功后自动退出编辑模式，预览区即时刷新
5. 可随时「取消」退出编辑，恢复原始内容

**后端校验：**
- 仅允许编辑状态为 `completed` 的转换
- 仅允许编辑自己的转换记录（username 匹配）

---

## 10. 历史记录功能

v4.0 新增：所有转换结果持久保存至 SQLite，支持事后查看和管理。

**功能：**
- 顶部「历史」按钮展开历史面板
- 列表显示标题、类型、状态（完成/失败/处理中）、更新时间
- 点击「查看」加载该转换的结果到当前视图
- 点击「删除」移除记录（若当前正在查看该记录则同时清空视图）
- 历史数据按用户隔离，互不可见

**数据保留：**
- 转换过程中产生的中间产物（清洗文本、角色信息、章节数据）一并保存
- 用于支持智能重生成功能（重新生成时复用原始文本和类型信息）

---

## 11. 小说类型系统（Genre System）

类型数据分为两层，统一存储在 SQLite `genres` 表中：

**系统默认类型**（6 种，所有用户共享，不可编辑不可删除）：
武侠、玄幻、科幻、言情、叙事、魔幻

**用户自定义类型**（每用户最多 10 个）：
用户可增、删、改，仅自己可见

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
| `guidance` | AI 指引描述，注入到角色提取、场景切分、剧本转换的 Prompt 中 |
| `keywords` | 主角关键词，用于 Count 验证中为主角候选加权评分 |

### 隔离逻辑

| 角色 | 可见类型 |
|------|---------|
| 用户 A | 6 个系统默认 + 用户 A 的自定义（最多 10） |
| 用户 B | 6 个系统默认 + 用户 B 的自定义（最多 10） |

自定义类型达到 10 个上限后，添加按钮禁用。

### 旧数据迁移

首次启动时，若存在 `genres.json` 文件且数据库 `genres` 表为空，系统类型自动写入 SQLite。`genres.json` 保留作为参考文件。若存在 `users.json`，其中用户数据和自定义类型一并迁移至 SQLite，旧文件重命名为 `.bak` 备份。

---

## 12. 用户认证系统

- **注册**：用户名 2-20 字符，密码 ≥ 4 字符
- **登录**：返回 UUID Token，存于 `sessionStorage`
- **鉴权**：所有 API 需 `Authorization: Bearer <token>` 头（SSE 通过 `?token=` 传参）
- **存储**：SQLite `users` 表，密码 SHA256 哈希，Token 每次登录时刷新
- **迁移**：首次启动自动从 `users.json` 迁移（若有），完成后重命名为 `.bak`

---

## 13. 单元测试

```bash
cd backend
python -m unittest test_pipeline -v
```

测试覆盖（29 项）：

| 模块 | 测试数 | 内容 |
|------|--------|------|
| TextCleaning | 3 | 空格规范化、换行折叠、空白去除 |
| ChapterDetection | 5 | 数字/中文序号、无章节回退、内容边界 |
| JSONExtraction | 5 | 纯JSON、markdown围栏、文本包围、数组、无效输入 |
| SchemaValidation | 4 | 完整场景、ID补全、孤立角色预警、对白角色校验 |
| MainCharacterValidation | 3 | 正常通过、无角色、空出场 |
| YAMLAssembly | 1 | 完整输出结构和字段 |
| Models | 2 | ValidationResult/SchemaValidation 默认值 |
| Database | 6 | 用户CRUD、Token更新、流派完整CRUD、转换CRUD |

---

## 14. 完整示例

```yaml
meta:
  title: "离奇的来信"
  genre: "科幻"
  source_chapters: 3
  total_scenes: 6
  characters:
    - "林晓"
    - "陈默"
    - "周老板"
  character_details:
    - id: "C001"
      name: "林晓"
      role: "protagonist"
      description: "28岁女程序员，对技术敏感"
      aliases: ["晓晓"]
    - id: "C002"
      name: "陈默"
      role: "supporting"
      description: "林晓的室友，性格开朗"
      aliases: []
    - id: "C003"
      name: "周老板"
      role: "minor"
      description: "神秘中年男人，穿唐装，开咖啡馆"
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

## 15. 扩展性考虑

| 扩展 | 位置 | 方式 |
|------|------|------|
| 章节分组 | `script` 中插入 `chapter_break` | 在场景间添加 `{type: "chapter_break", title: "第二章"}` |
| 分镜信息 | `action`/`dialogues` 新增 `shot` 字段 | 可选子字段 |
| BGM/音效 | `scene` 新增 `audio` 字段 | 可选扩展 |
| 审阅批注 | 整个文档支持 `_comments` 顶层键 | 工具链可忽略 |
| 自定义类型 | SQLite `genres` 表 per-user 存储 | 已实现，最多 10 个 |
| 多用户协作 | 引入数据库 + 权限系统 | 未来方向 |
| 多格式导出 | 新增导出模块 | PDF/DOCX/Fountain 等 |

---

## 16. 与其他剧本格式的关系

| 格式 | 对比 |
|------|------|
| **Final Draft (.fdx)** | XML 格式，复杂且不易人类编辑。本 YAML Schema 更轻量。 |
| **Fountain** | 纯文本标记语言，不结构化，程序解析困难。本 Schema 在可读性和可解析性之间平衡。 |
| **JSON** | YAML 可读性远高于 JSON，尤其对非技术背景的小说作者。 |

YAML 的选择核心在于：**作者拿到的是一个可直接阅读的文档，而非需要特殊软件打开的格式**。

---

*文档版本: 4.0 · 最后更新: 2026-06-06*
