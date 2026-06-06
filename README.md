# AI 剧本创作助手 (AI Novel Studio)

将小说文本自动转换为结构化剧本（YAML 格式），让小说作者快速获得可编辑、可进一步打磨的剧本初稿。

## 功能

- 上传 3 章以上的小说文本，自动识别章节边界
- AI 驱动 7 步转换流水线：文本清洗 → 章节检测 → 角色提取 → 场景切分 → 剧本转换 → 主角验证 → Schema 校验
- 实时进度推送（SSE）
- YAML 预览（语法高亮）+ 结构化视图（章节→场景→对白树）
- **转换历史记录**：所有转换结果持久保存，支持查看、删除历史
- **在线编辑**：生成后可直接在页面上编辑 YAML 剧本，保存后即时生效
- 智能重生成：主角验证不达标时，可提交补充信息让 AI 重新生成
- 6 种系统默认小说类型 + 每用户最多 10 种自定义类型（含 AI 指引和主角关键词）
- 一键下载 YAML / 一键复制到剪贴板

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Python 3.12 + FastAPI |
| 数据库 | SQLite（WAL 模式） |
| AI | DeepSeek V4（OpenAI 兼容接口） |

## 快速开始

### 1. 安装依赖

```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install
```

### 2. 配置环境变量

```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
```

### 3. 启动服务

```bash
# 终端 1：启动后端
python backend/run.py

# 终端 2：启动前端
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173`

### 4. 运行测试

```bash
cd backend
python -m unittest test_pipeline -v
```

## 项目结构

```
ai-novel-studio/
├── backend/
│   ├── main.py          # FastAPI 应用入口 (REST API)
│   ├── pipeline.py      # 7 步转换流水线 + AI 调用
│   ├── prompts.py       # LLM Prompt 模板
│   ├── models.py        # Pydantic 数据模型
│   ├── auth.py          # 用户认证（SHA256 哈希）
│   ├── database.py      # SQLite 数据库层
│   ├── run.py           # 启动脚本 (uvicorn)
│   ├── test_pipeline.py # 单元测试（29 项）
│   ├── genres.json      # 系统默认类型（启动时迁移至 DB）
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # 主页面组件（含登录/转换/历史/编辑）
│   │   ├── api.ts       # API 客户端（含 SSE 进度订阅）
│   │   ├── index.css    # Tailwind + 自定义动画
│   │   └── main.tsx     # React 入口
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
└── docs/
    └── script-yaml-schema.md  # YAML Schema 设计文档
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 获取当前用户 |
| GET | `/api/genres` | 列出所有类型（系统+自定义） |
| POST | `/api/genres` | 添加自定义类型 |
| PUT | `/api/genres/{index}` | 修改自定义类型 |
| DELETE | `/api/genres/{index}` | 删除自定义类型 |
| POST | `/api/convert` | 启动转换，返回 task_id |
| GET | `/api/convert/{id}/progress` | SSE 进度流 |
| GET | `/api/convert/{id}/result` | 获取转换结果 |
| POST | `/api/convert/{id}/regenerate` | 提交补充信息重新生成 |
| GET | `/api/conversions` | 查询历史记录列表 |
| PUT | `/api/conversions/{id}` | 编辑已生成的 YAML |
| DELETE | `/api/conversions/{id}` | 删除历史记录 |

## 数据持久化

所有数据存储在 SQLite 数据库 (`backend/app.db`)：

- **users** — 用户账号和认证 token
- **genres** — 系统默认类型 + 用户自定义类型
- **conversions** — 转换任务（原文、YAML 输出、元信息、中间产物）

首次启动时，若存在旧的 `users.json` / `genres.json`，数据将自动迁移至 SQLite，旧文件重命名为 `.bak` 备份。
