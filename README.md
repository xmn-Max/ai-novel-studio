# AI 剧本创作助手 (AI Novel Studio)

将小说文本自动转换为结构化剧本（YAML 格式），让小说作者快速获得可编辑、可进一步打磨的剧本初稿。

## 功能

- 上传 3 章以上的小说文本，自动识别章节边界
- AI 驱动 5 步流水线转换：章节检测 → 角色提取 → 场景切分 → 剧本转换 → YAML 组装
- 实时进度推送（SSE）
- YAML 预览 + 结构化视图 + 一键下载

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Python 3.12 + FastAPI |
| AI | DeepSeek V4（OpenAI 兼容接口） |

## 快速开始

### 1. 安装依赖

```bash
# 后端（即其中的一个终端）
pip install -r backend/requirements.txt
```

### 2. 配置环境变量

```bash
$env:DEEPSEEK_API_KEY = "这里输入api"
```

### 3. 启动服务

```bash
# 终端 1：启动后端
python backend/run.py

# 终端 2：启动前端（另一个终端）
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`

## 项目结构

```   
ai-novel-studio/
├── backend/
│   ├── main.py          # FastAPI 应用入口
│   ├── pipeline.py      # 5 步转换流水线
│   ├── prompts.py       # LLM Prompt 模板
│   ├── models.py        # Pydantic 数据模型
│   ├── run.py           # 启动脚本
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # 主页面组件
│   │   └── api.ts       # API 客户端
│   └── ...
└── docs/
    └── script-yaml-schema.md  # YAML Schema 设计文档
```
