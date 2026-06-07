# AI 剧本创作助手 (AI Novel Studio)

将小说文本自动转换为结构化剧本（YAML 格式），支持 AI 重新询问、版本历史、在线编辑，让小说作者快速获得可迭代打磨的剧本。

## 演示视频

[观看演示视频](https://pan.baidu.com/s/12HD0hn7fqp48hSaF2QuasA?pwd=pezu)（百度网盘，提取码：pezu）

## 功能

- **项目化管理**：每部小说一个 Project，所有 AI 分析结果 SQLite 持久化
- **8 步 AI 流水线**：文本清洗 → 章节检测 → 角色提取 → 剧情分析 → 场景规划 → 剧本生成 → 世界观分析 → Schema 校验
- **多格式上传**：支持 TXT / DOCX / PDF 文件上传
- **AI 重新询问**：选择剧本/剧情/世界观/角色任一维度，输入修改意见，AI 根据当前数据 + 原文上下文重新生成并直接写入数据库
- **版本历史**：每次重新询问前自动保存快照（含角色/剧情/场景/YAML/世界观），支持双版本差异对比和任意版本回滚
- **剧情分析**：AI 提取主线、支线、主题、冲突、高潮、结局、关键事件、叙事节奏；支持行内编辑
- **角色分析**：AI 提取角色姓名/性别/年龄/人设/性格特征/关系；支持行内编辑
- **场景规划**：事件→场景映射、冲突强度、时长；支持行内编辑
- **世界观分析**：6 维度（地点/势力/技能/物品/时间线/规则），每种类型有专属标签和 AI 分析视角
- **AI 自动修复**：Schema 校验不通过时自动调用 AI 修复（最多 3 次重试）
- **剧本查看 & 在线编辑**：结构化展示场景标题/地点/时间/角色/动作/对白/转场，支持编辑每个场景字段
- **实时进度**：SSE 推送 8 步流水线进度
- **插件系统**：编剧点评（三幕式/节奏/角色弧光/对白评价）、爆款分析（爆点/标题/钩子/高光场景）
- **YAML 预览 + 下载**
- **小说类型系统**：6 种内置类型（每种有独立 AI 分析视角：叙事看人生、玄幻看成长、科幻看思想、言情看感情、魔幻看世界、武侠看侠义）+ 用户可自定义最多 10 个类型
- **在线编辑**：角色/剧情/场景规划/剧本场景均支持行内编辑，修改直接持久化

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Python 3.12 + FastAPI |
| AI | DeepSeek（OpenAI 兼容接口，`deepseek-chat` 模型） |
| 数据库 | SQLite（aiosqlite 异步驱动，12 张表） |
| 安全 | bcrypt 密码哈希 + token 认证 |

## 快速开始

### 方式一：Docker（推荐）

前提：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```bash
# 1. 设置 API Key（PowerShell）
$env:DEEPSEEK_API_KEY = "你的API密钥"

# 2. 构建并启动
docker compose up -d --build

# 3. 浏览器打开 http://localhost:8000
```

数据持久化在 `./data/` 目录，容器重建不丢失。卸载项目时删除该目录即可。

### 方式二：手动启动
$env:DEEPSEEK_API_KEY = "你的API密钥"

#### 1. 安装依赖

```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend
npm install
```

#### 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=你的API密钥
```

#### 3. 启动服务

```bash
# 终端 1：启动后端
cd backend
python run.py

# 终端 2：启动前端
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`

## 项目结构

```
ai-novel-studio/
├── backend/
│   ├── main.py                      # FastAPI 路由（31 个端点）
│   ├── models.py                    # Pydantic 数据模型
│   ├── pipeline.py                  # 8 步 AI 流水线 + 重新询问
│   ├── prompts.py                   # LLM Prompt 模板（13 个）
│   ├── plugins.py                   # 插件系统（编剧点评/爆款分析）
│   ├── services/
│   │   └── project_service.py       # 业务逻辑层
│   ├── database.py                  # SQLite 持久化（12 张表）
│   ├── auth.py                      # 用户认证（bcrypt）
│   ├── fsm.py                       # 工作流状态机（9 状态）
│   ├── llm.py                       # LLM 调用（3 次重试 + JSON 解析）
│   ├── file_parser.py               # TXT/DOCX/PDF 文件解析
│   ├── genres.json                  # 内置小说类型
│   ├── run.py                       # 启动脚本
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx                  # 路由入口
│       ├── api.ts                   # API 客户端（32 个函数）
│       ├── main.tsx
│       └── components/
│           ├── LoginPage.tsx         # 登录/注册
│           ├── HomePage.tsx          # 项目列表
│           ├── ProjectPage.tsx       # 项目主页（AI 交互核心）
│           ├── UploadSection.tsx     # 文件上传 + 文本输入
│           ├── WorkflowStepper.tsx   # 8 步进度指示器
│           ├── EditableCharacterTable.tsx  # 角色表格（在线编辑）
│           ├── EditablePlotSection.tsx     # 剧情分析（在线编辑 + 重分析按钮）
│           ├── WorldSection.tsx      # 世界观展示（重分析按钮）
│           ├── ScenePlanTable.tsx    # 场景规划表
│           ├── EditableScenePlanTable.tsx  # 场景规划（在线编辑）
│           ├── ScriptViewer.tsx      # 剧本查看 + 场景编辑
│           ├── PluginPanel.tsx       # 插件管理
│           ├── FeedbackPanel.tsx     # AI 重新询问面板（目标选择 + 历史反馈）
│           ├── VersionHistory.tsx    # 版本对比 + 回滚
│           ├── GenreManager.tsx      # 类型管理
│           └── useProtagonistValidation.ts  # 主角验证 Hook
├── docs/
│   └── script-yaml-schema.md        # YAML Schema 设计文档
└── README.md
```

## 数据库表

| 表名 | 用途 |
|------|------|
| `projects` | 项目元信息（标题/类型/状态） |
| `novel_chapters` | 分章原文 |
| `project_characters` | 角色分析结果 |
| `plot_analysis` | 剧情分析（主线/主题/冲突/事件） |
| `scene_plan` | 场景规划 |
| `script_scenes` | 剧本场景 |
| `world_building` | 世界观分析 |
| `project_yaml` | YAML 剧本（用于下载 + 版本快照） |
| `project_versions` | 版本快照（完整数据快照 + 反馈记录） |
| `plugin_results` | 插件运行结果 |
| `users` | 用户认证信息 |
| `user_genres` | 用户自定义小说类型 |

## API 端点

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 当前用户 |

### 项目
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情（含全部数据） |
| DELETE | `/api/projects/{id}` | 删除项目 |

### 转换
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/{id}/convert` | 启动 AI 转换 |
| GET | `/api/convert/{id}/progress` | SSE 进度推送 |
| GET | `/api/convert/{id}/result` | 获取转换结果 |

### AI 重新询问 ★
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/{id}/requery` | 按目标重新生成（script/plot/world/characters） |

### 在线编辑
| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/projects/{id}/plot` | 编辑剧情字段 |
| PUT | `/api/projects/{id}/characters/{id}` | 编辑角色字段 |
| PUT | `/api/projects/{id}/script/{id}` | 编辑场景 |
| PUT | `/api/projects/{id}/scene-plan/{id}` | 编辑场景规划 |

### 版本历史
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/{id}/versions` | 保存版本快照 |
| GET | `/api/projects/{id}/versions` | 版本列表 |
| GET | `/api/projects/{id}/versions/{id}` | 版本详情（含完整快照） |
| POST | `/api/projects/{id}/versions/{id}/restore` | 回滚到指定版本 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 文件上传 |
| GET | `/api/genres` | 类型列表 |
| POST/PUT/DELETE | `/api/genres[/{id}]` | 类型 CRUD |
| GET | `/api/plugins` | 插件列表 |
| POST | `/api/projects/{id}/plugins/{name}` | 运行插件 |
| GET | `/api/steps` | 流水线步骤列表 |
| GET | `/api/health` | 健康检查 |

## 修改日志

### v1.3.0（当前版本）

**Docker 部署**
- 新增多阶段 Dockerfile（Node 编译前端 + Python 运行后端合一）
- 新增 `docker-compose.yml`，一键 `docker compose up -d --build` 启动
- 数据持久化至 `./data/` 目录（数据库、用户信息）
- `database.py` / `auth.py` 支持 `DATA_DIR` 环境变量配置路径

**版本对比增强**
- 版本对比新增 YAML 预览（语法着色、暗色终端风格、左右并排）
- 新增深度审阅"看栏目"：对比后发现 YAML 行数差 > 30 自动提示，填写意见后 AI 综合两版本 + 原文重新生成新剧本
- 新增 `POST /api/projects/{id}/deep-review` 端点
- 新增 `DEEP_REVIEW_PROMPT` 和 `Pipeline.deep_review_and_regenerate()` 方法

**类型系统深化 — "看"框架**
- 6 种类型各有明确分析视角：叙事看人生、玄幻看成长、科幻看思想、言情看感情、魔幻看世界、武侠看侠义
- 每种类型的 genre_guidance 细化为角色/剧情/世界观/场景四个维度的针对性指引
- 世界观 6 维度支持按类型显示不同标签和 AI 分析字段（如叙事用"地点/环境、人物/群体、能力/经历..."，玄幻用"界域/地点、势力/宗门、功法/技能..."）

**世界观维度按类型适配**
- `prompts.py` 新增 `WORLD_FIELDS` 字典（6 种类型 × 6 维度专属描述），`WORLD_BUILDING_PROMPT` 改用 `{world_fields}` 动态注入
- `pipeline.py` 的 `_build_world` 根据 genre 选择对应维度描述
- 前端 `WorldSection.tsx` 新增 `GENRE_LABELS` 映射，按类型渲染不同标签

**修复**
- 清理所有 Git 合并冲突标记（8 个文件共 25 处）
- 升级 bcrypt 至 5.0.0，python-dotenv 至 1.2.2

### v1.2.0

**AI 重新询问**
- 新增 `POST /api/projects/{id}/requery` 端点，支持 script/plot/world/characters 四种目标
- 新增 3 个 Requery Prompt（REQUERY_PLOT/WORLD/CHARACTERS_PROMPT）
- 新增 `pipeline.requery_plot/requery_world/requery_characters` 方法
- 原文上下文注入：角色/剧情重询问时自动加载前 10 章原文作为参考
- FeedbackPanel 新增目标选择器（剧本/剧情/世界观/角色标签切换）
- 重新询问期间面板保持显示，展示加载动画

**版本历史增强**
- 版本快照新增 `yaml_content` 和 `world_building` 字段
- 版本回滚新增恢复 YAML 和世界观数据
- 差异对比新增「剧本场景」和「YAML 剧本」展示项

**修复**
- 初始转换后 `script_scenes` 未写入数据库，导致剧本无法在线查看 — 已在 `_persist` 和 `run_full` 中修复
- 下载按钮改为优先使用数据库中的最新 YAML
- 后端启动时 `load_dotenv()` 加载 `.env` 文件

### v1.1.0

**架构重构**
- 新增 Service 层（`services/project_service.py`）
- 前端拆分为 17 个组件
- 剧情/角色/场景规划/Script 均支持在线编辑
- 新增版本历史（保存/对比/回滚）
- 新增 FeedbackPanel 面板
- 新增用户可编辑场景规划表

**安全升级**
- bcrypt 密码哈希
- Token 72 小时过期
- 文件上传大小限制

### v1.0.0（初版）

- 基础小说→YAML 转换流水线
- 用户注册/登录
- 6 种内置小说类型
- YAML Schema 设计文档
