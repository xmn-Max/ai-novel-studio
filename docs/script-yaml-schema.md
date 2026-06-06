# AI 剧本创作工具 — 剧本 YAML Schema 设计文档

## 1. 概述

本 Schema 定义了从小说自动转换生成的剧本的 YAML 数据结构。它作为 AI 转换流水线的输出标准，也是下游工具（编辑器、分镜生成、制作排期等）的输入协议。

**系统架构要点：**
- **用户系统**：注册/登录后方可使用，密码 bcrypt 加密（兼容旧 SHA256），存于 SQLite
- **数据持久化**：所有转换结果持久保存至 SQLite，支持历史记录查询、查看、删除
- **在线编辑器**：生成的 YAML 剧本可直接在页面上编辑并保存
- **多格式导出**：支持 PDF、DOCX、YAML 三种格式一键下载
- **文件导入**：支持上传 .txt/.md/.pdf/.docx/.doc 文件（UTF-8/GBK 自动识别，≤5MB）
- **转换流水线（7 步）**：文本清洗 → 章节检测 → 角色提取 → 场景切分 → 剧本转换 → 主角验证 → Schema 校验
- **智能重生成**：验证不达标时向用户征求补充信息后完整重跑流水线
- **速率限制**：注册 10/min、登录 20/min、转换 5/min、重生成 3/min、上传 10/min
- **超时清理**：后台任务每 10 分钟标记超过 30 分钟未完成的任务为失败
- **自动迁移**：首次启动时自动将旧的 `users.json` / `genres.json` 迁移至 SQLite
- **Docker 支持**：多阶段构建 + docker-compose 生产/开发双模式

**核心设计目标：**
- **可读性优先**：YAML 格式天然适合人类阅读和手动编辑。
- **结构化但不失灵活性**：固定字段承载剧本核心要素，同时允许字段为空。
- **工具链友好**：严格的键名和嵌套层级确保程序可无歧义解析。
- **可验证性**：内建主角验证计数（Count）和 Schema 校验结果。
- **类型适配**：系统默认 6 种 + 用户自定义最多 10 种，AI 据此调整分析侧重点。
- **用户隔离**：自定义类型、转换历史等数据按用户隔离。
- **中文原生支持**：所有字段值均支持中文。

---

## 2. 数据库设计

系统使用 SQLite（WAL 模式，`backend/app.db`）进行数据持久化。

### 2.1 users

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,    -- bcrypt（新注册）/ SHA256（旧数据兼容）
    token         TEXT,             -- UUID，每次登录刷新
    created_at    TEXT NOT NULL
);
```

密码安全：
- 新注册用户使用 **bcrypt** 加密
- 旧用户 SHA256 密码登录时自动升级为 bcrypt
- 支持 `POST /api/auth/change-password` 修改密码

### 2.2 genres

```sql
CREATE TABLE genres (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    guidance  TEXT DEFAULT '',
    keywords  TEXT DEFAULT '[]',    -- JSON 数组
    is_system INTEGER DEFAULT 0,    -- 1=系统, 0=用户自定义
    username  TEXT
);
```

### 2.3 conversions

```sql
CREATE TABLE conversions (
    id                TEXT PRIMARY KEY,  -- UUID
    username          TEXT NOT NULL,
    title             TEXT DEFAULT '',
    genre             TEXT DEFAULT '叙事',
    original_text     TEXT NOT NULL,
    cleaned_text      TEXT,
    yaml_output       TEXT,             -- 最终 YAML
    meta_json         TEXT,             -- 元信息 JSON
    intermediate_json TEXT,             -- 中间产物 JSON
    status            TEXT DEFAULT 'pending',
    progress_json     TEXT,
    error             TEXT,
    hints             TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
```

状态流转：`pending → processing → completed` / `failed` / `regenerating → completed`

超时处理：后台任务每 10 分钟将超过 30 分钟的未完成任务标记为 `failed`。

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

---

## 4. `meta` 元信息

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
      description: "28岁的女程序员"
      aliases: ["晓晓"]
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
```

---

## 5. `validation` 主角验证

```yaml
validation:
  main_character: "林晓"
  count: 2
  status: "验证通过"
  retried: false
```

验证逻辑（Count 机制）：

```
Step A: 按出场次数 + 类型关键词加分，选出主角候选
Step B: 每章主角名出现 ≥5 次 → count += 1
Step C: 主角动作与原文事件相关性 >50% → count += 1
Step D: count < 2 → 提示用户输入补充信息 → 全文重跑
```

---

## 6. `schema_validation` Schema 校验

校验规则：`scene_id` 补全、`scene_heading` 自动生成、角色引用检查、对白角色检查。失败时自动修复 1 次。

---

## 7. `script` 场景列表

```yaml
script:
  - scene_id: 1
    scene_heading: "第1场  内景  公寓  上午"
    location: "公寓"
    time_of_day: "上午"
    characters_present: ["张三"]
    action:
      - "张三醒来"
    dialogues:
      - character: "张三"
        line: "早上好"
        parenthetical: ""
    transition: ""
```

对白子结构：`character`（说话角色）、`line`（台词）、`parenthetical`（夹注/动作提示，可选）。

---

## 8. API 端点参考

| 方法 | 路径 | 限流 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 10/min | 注册 |
| POST | `/api/auth/login` | 20/min | 登录 |
| GET | `/api/auth/me` | - | 当前用户 |
| POST | `/api/auth/change-password` | - | 修改密码 |
| GET | `/api/genres` | - | 列出类型 |
| POST | `/api/genres` | - | 添加自定义类型 |
| PUT | `/api/genres/{index}` | - | 修改类型 |
| DELETE | `/api/genres/{index}` | - | 删除类型 |
| POST | `/api/convert` | 5/min | 启动转换 |
| GET | `/api/convert/{id}/progress` | - | SSE 进度 |
| GET | `/api/convert/{id}/result` | - | 获取结果 |
| POST | `/api/convert/{id}/regenerate` | 3/min | 重生成 |
| GET | `/api/conversions` | - | 历史列表 |
| PUT | `/api/conversions/{id}` | - | 编辑 YAML |
| DELETE | `/api/conversions/{id}` | - | 删除历史 |
| POST | `/api/upload` | 10/min | 上传文件 (.txt/.md/.pdf/.docx/.doc) |
| GET | `/api/convert/{id}/export/pdf` | - | 导出 PDF |
| GET | `/api/convert/{id}/export/docx` | - | 导出 DOCX |
| GET | `/api/health` | - | 健康检查 |

## 9. 多格式导出

v5.0 新增 PDF 和 DOCX 导出。

| 格式 | 引擎 | 特点 |
|------|------|------|
| **PDF** | fpdf2 | 自动检测系统字体（宋体/微软雅黑/黑体），含角色列表、场景分隔、对白缩进 |
| **DOCX** | python-docx | 标题居中、角色名加粗、夹注斜体、转场右对齐 |
| **YAML** | 前端直接下载 | 原始剧本数据，可重新导入编辑 |

导出端点使用 `?token=` query 参数鉴权（支持 `<a>` 标签直接下载）。

## 10. 文件上传

v5.0 新增文件导入功能。

- 端点：`POST /api/upload`
- 支持格式：`.txt`、`.md`、`.text`（纯文本）、`.pdf`（PyPDF2 提取）、`.docx`（python-docx 提取）、`.doc`（最佳努力提取，建议先转为 DOCX）
- 大小限制：≤ 5MB
- 编码：UTF-8 优先，失败则尝试 GBK
- 上传后自动填充到输入框，文件名（去扩展名）作为默认标题

## 11. 异常处理与中间件

v5.0 新增统一异常处理：

| 异常类型 | 响应 |
|---------|------|
| 通用 Exception | 500 + `{"detail": "...", "type": "..."}` |
| HTTPException | 对应状态码 + `{"detail": "..."}` |
| RequestValidationError | 422 + `{"detail": "...", "errors": [...]}` |
| RateLimitExceeded | 429 + 标准限流提示 |

## 12. 在线编辑功能

- 转换完成后 YAML 预览区右上角「编辑」按钮
- 编辑模式：等宽字体 textarea，保存/取消按钮
- 保存通过 `PUT /api/conversions/{id}` 回写数据库

## 13. 历史记录功能

- 顶部「历史」按钮展开面板
- 列表：标题、类型、状态、时间
- 查看：加载转换结果到当前视图
- 删除：移除记录

## 14. 小说类型系统

系统默认（6 种，不可编辑/删除）：武侠、玄幻、科幻、言情、叙事、魔幻

用户自定义（≤10 个，仅自己可见）：含 name / guidance / keywords

首次启动自动从 `genres.json` 种子数据到 SQLite。旧 `users.json` 迁移后备份。

## 15. 用户认证系统

- 注册：用户名 2-20 字符，密码 ≥ 4 字符
- 密码：bcrypt 加密，旧 SHA256 登录时自动升级
- 改密码：`POST /api/auth/change-password`
- Token：UUID，每次登录刷新，存于 sessionStorage
- SSE 鉴权：`?token=` query 参数

## 16. 单元测试

```bash
cd backend
python -m unittest test_pipeline -v
```

29 项测试覆盖：TextCleaning(3)、ChapterDetection(5)、JSONExtraction(5)、SchemaValidation(4)、MainCharacterValidation(3)、YAMLAssembly(1)、Models(2)、Database(6)

## 17. Docker 部署

```bash
# 生产模式（前端打包进后端，端口 8000）
docker compose up -d

# 开发模式（前端热重载，端口 5173+8000）
docker compose --profile dev up -d
```

Dockerfile 多阶段构建：Node 20 构建前端 → Python 3.12-slim 运行后端。

## 18. 完整示例

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

## 19. 扩展性考虑

| 扩展 | 位置 | 方式 |
|------|------|------|
| 章节分组 | `script` 中插入 `chapter_break` | 在场景间添加分隔标记 |
| 分镜信息 | `action`/`dialogues` 新增 `shot` 字段 | 可选子字段 |
| BGM/音效 | `scene` 新增 `audio` 字段 | 可选扩展 |
| 审阅批注 | `_comments` 顶层键 | 工具链可忽略 |
| 多格式导出 | `backend/export.py` | 已实现 PDF/DOCX/YAML |
| 多用户协作 | 数据库 + 权限系统 | 未来方向 |

## 20. 与其他剧本格式的关系

| 格式 | 对比 |
|------|------|
| **Final Draft (.fdx)** | XML 格式，不易人类编辑。本 YAML Schema 更轻量。 |
| **Fountain** | 纯文本标记语言，程序解析困难。本 Schema 在可读性和可解析性之间平衡。 |
| **JSON** | YAML 可读性远高于 JSON。 |

YAML 的核心优势：**作者拿到的是一个可直接阅读的文档，而非需要特殊软件打开的格式**。

---

*文档版本: 5.0 · 最后更新: 2026-06-06*
