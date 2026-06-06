# AI 剧本创作助手 (AI Novel Studio)

将小说文本自动转换为结构化剧本（YAML 格式），让小说作者快速获得可编辑、可进一步打磨的剧本初稿。

## 功能

- **文件导入**：支持上传 .txt / .md / .pdf / .docx / .doc 文件（自动提取文本）
- AI 驱动 7 步转换流水线：文本清洗 → 章节检测 → 角色提取 → 场景切分 → 剧本转换 → 主角验证 → Schema 校验
- 实时进度推送（SSE，每 0.5s 更新）
- YAML 预览（语法高亮）+ 结构化视图（章节→场景→对白树）
- **转换历史记录**：所有转换结果持久保存至 SQLite，支持查看、删除
- **在线编辑**：生成后可直接在页面上编辑 YAML 剧本，保存后即时生效
- **多格式导出**：PDF / DOCX / YAML 三种格式一键下载
- 智能重生成：主角验证不达标时，可提交补充信息让 AI 重新生成
- 6 种系统默认小说类型 + 每用户最多 10 种自定义类型（含 AI 指引和主角关键词）
- 改密码：登录后可修改密码
- **速率限制**：注册、登录、转换、重生成等敏感端点均有速率限制
- **超时清理**：后台任务自动清理超过 30 分钟未完成的转换任务
- Docker 支持

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Python 3.12 + FastAPI + Uvicorn |
| 数据库 | SQLite（WAL 模式） |
| AI | DeepSeek V4（OpenAI 兼容接口） |
| 限流 | slowapi |
| 密码 | bcrypt（SHA256 → bcrypt 自动升级） |
| 导出 | fpdf2（PDF）+ python-docx（DOCX）|

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

### 4. Docker 部署

```bash
# 生产模式（前端打包进后端，单服务端口 8000）
docker compose up -d

# 开发模式（含前端热重载 dev server）
docker compose --profile dev up -d
```

### 5. 运行测试

```bash
cd backend
python -m unittest test_pipeline -v
```

## 项目结构

```
ai-novel-studio/
├── backend/
│   ├── main.py          # FastAPI 应用入口 (REST API + 限流 + 中间件)
│   ├── pipeline.py      # 7 步转换流水线 + DeepSeek AI 调用
│   ├── prompts.py       # LLM Prompt 模板
│   ├── models.py        # Pydantic 数据模型
│   ├── auth.py          # 用户认证（bcrypt + SHA256 兼容）
│   ├── database.py      # SQLite 数据库层（含自动迁移）
│   ├── middleware.py     # 统一异常处理中间件
│   ├── export.py        # PDF/DOCX 导出模块
│   ├── run.py           # 启动脚本 (uvicorn)
│   ├── test_pipeline.py # 单元测试（29 项）
│   ├── genres.json      # 系统默认类型参考（启动时迁移至 DB）
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # 主页面（登录/转换/历史/编辑/上传/导出/改密）
│   │   ├── api.ts       # API 客户端（SSE + 文件上传 + 导出）
│   │   ├── index.css    # Tailwind + 自定义动画
│   │   └── main.tsx     # React 入口
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── Dockerfile            # 多阶段构建（前端构建 + Python 运行）
├── docker-compose.yml    # 生产/开发双模式
└── docs/
    └── script-yaml-schema.md  # YAML Schema 设计文档
```

## API 端点

| 方法 | 路径 | 限流 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 10/min | 注册新用户 |
| POST | `/api/auth/login` | 20/min | 登录，返回 Token |
| GET | `/api/auth/me` | - | 获取当前用户信息 |
| POST | `/api/auth/change-password` | - | 修改密码 |
| GET | `/api/genres` | - | 列出所有类型（系统+自定义） |
| POST | `/api/genres` | - | 添加自定义类型（最多 10 个） |
| PUT | `/api/genres/{index}` | - | 修改自定义类型 |
| DELETE | `/api/genres/{index}` | - | 删除自定义类型 |
| POST | `/api/convert` | 5/min | 启动转换，返回 task_id |
| GET | `/api/convert/{id}/progress` | - | SSE 进度流（?token= 鉴权） |
| GET | `/api/convert/{id}/result` | - | 获取转换结果（YAML + Meta） |
| POST | `/api/convert/{id}/regenerate` | 3/min | 提交补充信息重新生成 |
| GET | `/api/conversions` | - | 查询历史记录列表 |
| PUT | `/api/conversions/{id}` | - | 在线编辑 YAML |
| DELETE | `/api/conversions/{id}` | - | 删除历史记录 |
| POST | `/api/upload` | 10/min | 上传 .txt/.md/.pdf/.docx/.doc 文件（≤5MB） |
| GET | `/api/convert/{id}/export/pdf` | - | 导出 PDF |
| GET | `/api/convert/{id}/export/docx` | - | 导出 DOCX |
| GET | `/api/health` | - | 健康检查 |

## 数据持久化

所有数据存储在 SQLite 数据库 (`backend/app.db`)：

- **users** — 密码 bcrypt/SHA256 兼容，token 每次登录刷新
- **genres** — 系统默认类型 + 用户自定义类型
- **conversions** — 原文、YAML 输出、元信息、中间产物、进度

首次启动时若存在旧 `users.json` / `genres.json`，自动迁移至 SQLite 并备份为 `.bak`。

## 安全性

- 密码：bcrypt 加密（旧 SHA256 密码登录时自动升级）
- 速率限制：注册/登录/转换/重生成/上传 均有频率限制
- 全局异常处理：统一 JSON 格式错误响应
- Token 鉴权：所有业务端点需 Bearer Token
