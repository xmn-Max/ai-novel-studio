# AI 剧本创作助手 (AI Novel Studio)

将小说文本自动转换为结构化剧本（YAML 格式），让小说作者快速获得可编辑、可进一步打磨的剧本初稿。

## 功能

- **项目化管理**：每部小说一个 Project，所有 AI 分析结果持久化存储
- **8 步 AI 流水线**：文本清洗 → 章节检测 → 角色提取 → 剧情分析 → 场景规划 → 剧本生成 → 世界观分析 → Schema 校验
- **多格式上传**：支持 TXT / DOCX / PDF 文件上传（10MB 限制）
- **剧情分析**：AI 自动提取主线、支线、主题、冲突、高潮、结局、关键事件、叙事节奏
- **场景规划**：从事件到场景的完整规划，含事件关联和冲突强度
- **世界观分析**：AI 归纳界域/势力/功法/法宝/时间线/世界规则
- **AI 自动修复**：Schema 校验不通过时自动调用 AI 修复（最多 3 次重试）
- **剧本编辑器**：在线编辑场景标题、地点、动作描述、转场
- **实时进度**：SSE 推送 8 步流水线进度
- **插件系统**：编剧点评（三幕式分析/节奏评分/角色弧光）、爆款分析（爆点提取/标题生成/短视频钩子）
- **YAML 预览 + 结构化视图 + 一键下载**
- **用户类型系统**：6 种内置类型 + 用户自定义类型，每种类型有独立的 AI 分析指引

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Python 3.12 + FastAPI |
| AI | DeepSeek V4（OpenAI 兼容接口） |
| 持久化 | SQLite（aiosqlite 异步驱动） |
| 安全 | bcrypt 密码哈希 + token 72h 过期 |

## 快速开始

### 1. 安装依赖

```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend
npm install
```

### 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=你的API密钥
```

### 3. 启动服务

```bash
# 终端 1：启动后端
python backend/run.py

# 终端 2：启动前端
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`

## 项目结构

```
ai-novel-studio/
├── backend/
│   ├── main.py                    # FastAPI 路由入口（薄层）
│   ├── models.py                  # Pydantic 数据模型
│   ├── pipeline.py                # 8 步 AI 转换流水线
│   ├── prompts.py                 # LLM Prompt 模板（10个）
│   ├── plugins.py                 # 插件系统（编剧点评/爆款分析）
│   ├── services/
│   │   └── project_service.py     # 业务逻辑层（Service 层）
│   ├── database.py                # SQLite 持久化 + 表结构
│   ├── auth.py                    # 用户认证（bcrypt + token 过期）
│   ├── fsm.py                     # 工作流状态机（9 状态）
│   ├── llm.py                     # LLM 调用公共模块
│   ├── file_parser.py             # TXT/DOCX/PDF 解析
│   ├── genres.json                # 小说类型配置
│   ├── run.py                     # 启动脚本
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx                # 路由根组件
│       ├── api.ts                 # API 客户端（统一错误处理）
│       └── components/
│           ├── LoginPage.tsx       # 登录/注册
│           ├── HomePage.tsx        # 首页+项目列表
│           ├── ProjectPage.tsx     # 项目主页（组合各子组件）
│           ├── UploadSection.tsx   # 文件上传+文本输入
│           ├── WorkflowStepper.tsx # 8步进度指示器
│           ├── CharacterTable.tsx  # 角色分析表格
│           ├── PlotSection.tsx     # 剧情分析展示
│           ├── WorldSection.tsx    # 世界观展示
│           ├── ScenePlanTable.tsx  # 场景规划表
│           ├── ScriptViewer.tsx    # 剧本查看/编辑
│           └── PluginPanel.tsx     # 插件管理面板
├── docs/
│   └── script-yaml-schema.md      # YAML Schema 设计文档
└── .gitignore
```

## 架构说明

本项目采用 **Route → Service → Model** 三层架构：

- **Route 层**（`main.py`）：FastAPI 路由定义，参数校验，委托给 Service
- **Service 层**（`services/project_service.py`）：业务逻辑、流水线编排、数据持久化
- **Model 层**（`models.py`）：Pydantic 数据模型定义
- **Infrastructure 层**：`database.py`（持久化）、`llm.py`（AI 通信）、`fsm.py`（状态管理）、`auth.py`（认证）、`file_parser.py`（文件解析）

前端采用 **View → API Client** 两层分离：
- **View 层**：10 个 React 组件，纯展示，无业务逻辑
- **API Client 层**（`api.ts`）：统一 HTTP 请求、错误处理、SSE 管理

## 修改日志

### v1.1.0（当前版本）

**架构重构**
- 新增 Service 层（`services/project_service.py`），从 `main.py` 分离业务逻辑
- `main.py` 路由层精简，只做参数校验和委托
- 前端拆分为 10 个子组件（LoginPage / HomePage / ProjectPage / UploadSection / WorkflowStepper / CharacterTable / PlotSection / WorldSection / ScenePlanTable / ScriptViewer / PluginPanel）

**新增功能**
- 项目化管理：Project CRUD + SQLite 持久化（8 张表）
- 剧情分析：AI 提取主线/支线/主题/冲突/高潮/结局/关键事件/节奏
- 场景规划：事件→场景映射 + 冲突强度
- 世界观分析：界域/势力/功法/法宝/时间线/规则归纳
- 插件系统：编剧点评 + 爆款分析，可扩展挂载点
- 工作流状态机（FSM）：9 状态（IDLE→UPLOADING→PARSING→ANALYZING→PLANNING_SCENES→GENERATING_SCRIPT→VALIDATING→COMPLETED/FAILED）
- TXT/DOCX/PDF 文件上传解析
- AI 自动 Schema 修复 + 重试闭环（最多 3 次）
- 剧本在线编辑器
- `/api/health` 健康检查 + `/api/steps` 步骤列表
- `api.ts` 统一 `handleResponse<T>()` 泛型错误处理

**安全升级**
- 密码哈希：SHA256 → bcrypt（带随机 salt）
- Token 72 小时过期机制
- 用户文件并发锁（O_CREAT|O_EXCL）
- `.gitignore` 覆盖 `.env` / `*.db` / `users.json` / `venv/` / `uploads/`
- 文件上传 10MB 大小限制

**修复**
- `pipeline.py:315` 运算符链 bug（`chapter_passes == len(chapters) > 0`）
- `world_building` INSERT 未 await 导致数据丢失
- `auth.py` 并发写竞态
- `models.py` 字段名统一（`source_chapters` → `chapter_count`，`total_scenes` → `scene_count`）
- 消除重复：`_load_genres`、`_insert_world`、`_call_llm`、`handleResponse` 各只保留一份
- 死代码清除：`task_engine.py`、未使用的 Pydantic 模型、冗余 import

### v1.0.0（初版）

- 基础小说→YAML 转换流水线（5 步）
- 用户注册/登录
- 6 种内置小说类型 + 用户自定义
- YAML Schema 设计文档
