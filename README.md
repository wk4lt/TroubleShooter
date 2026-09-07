# TroubleShooter

企业级 AI Agent 运行平台(Agent Runtime,非 ChatBot)。支持自主任务执行:
LLM 推理 → 工具调用 → 结果回填 → 继续推理 → 输出最终结果,全程通过 SSE 流式推送到前端。

## 架构

```
Web UI (React + TS + Vite)
   │  SSE 流式事件
Streaming API (FastAPI)
   │
Agent Runtime
   │
LLM (OpenAI 兼容接口) + Tools + Session Memory
```

## 技术栈

- 后端:Python 3.9+ / FastAPI / LangGraph / OpenAI SDK(兼容接口,默认 DeepSeek)
- 前端:React + TypeScript + Vite(原生,无 UI 框架)
- 通信:SSE(`/api/task/{id}/stream`)

## 目录结构

```
backend/
├── app/
│   ├── main.py          # FastAPI 入口、CORS、session 自动清理后台任务
│   ├── config.py        # 环境变量配置
│   ├── logger.py        # 结构化日志(文件 + 控制台)
│   ├── agent/           # Agent Runtime(LangGraph 状态图)
│   │   ├── loop.py      # 模型节点 → 工具节点 → 条件路由 → final
│   │   ├── state.py     # AgentState
│   │   ├── event.py     # AgentEvent 事件类型
│   │   ├── planner.py   # 消息组装 + system prompt + 工具规格
│   │   └── executor.py  # 工具调用执行
│   ├── api/             # task / stream / files / logs 路由
│   ├── llm/             # OpenAI 兼容 LLM 客户端
│   ├── rag/             # LlamaIndex 文档切片与知识检索
│   ├── tools/           # 工具注册表 + 内置工具 + Skill 脚本执行器
│   ├── skills/          # Skill 加载器(扫描、解析、按需读取)
│   └── storage/         # sessions / files / logs / contextvars
├── skills/              # 预置 Skill(SKILL.md),当前为股票相关 skill
├── data/knowledge/      # RAG 知识库: <subsystem_id>/<knowledge_type>/<file>
├── requirements.txt
└── .env                 # 实际密钥(已 gitignore,需自行创建)
frontend/
└── react-app/           # Vite + React + TS 控制台
dev.sh                   # 根目录启停/管理脚本(推荐)
```

## 快速开始

### 一键启动(推荐)

```bash
./dev.sh start       # 同时启动 backend + frontend
./dev.sh stop        # 停止
./dev.sh restart     # 重启
./dev.sh status      # 查看状态
./dev.sh logs        # 查看日志尾部
./dev.sh logs -f     # 实时跟随日志
./dev.sh build       # 构建前端生产包
./dev.sh health      # 健康检查
./dev.sh help        # 帮助
```

脚本支持参数:`--port 8000 --host 127.0.0.1 --ui-port 5173 --ui-host 127.0.0.1`。

### 手动启动

后端:

```bash
cd backend
cp .env.example .env        # 填入 OPENAI_API_KEY
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

前端:

```bash
cd frontend/react-app
npm install
npm run dev
```

首次启动前端必须先执行一次 `npm install`;根目录 `./dev.sh start` 不会自动安装依赖。它会优先使用依赖完整的 `backend/.venv/bin/python`,并在后端依赖缺失时输出安装命令。

- 后端监听 `http://127.0.0.1:8000`
- 前端监听 `http://127.0.0.1:5173`,已配置 `/api` 代理到后端

## 配置

环境变量写在 `backend/.env`(参考 `backend/.env.example`):

| 变量 | 说明 | 默认 |
|------|------|------|
| `OPENAI_BASE_URL` | LLM 接口地址 | `https://api.deepseek.com` |
| `OPENAI_API_KEY` | API Key | - |
| `OPENAI_MODEL` | 模型名 | `deepseek-chat` |
| `AGENT_MAX_ITERATIONS` | Agent 循环上限 | `10` |
| `SESSION_TTL_SECONDS` | 空闲 session 自动清理时间(秒) | `1800` |
| `SKILLS_DIR` | Skill 目录 | `backend/skills` |

> 依赖版本已固定(尤其 `openai==1.35.7` 需配合 `httpx==0.27.2`,否则会报
> `AsyncClient.__init__() got an unexpected keyword argument 'proxies'`)。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/task` | 创建任务,body `{"input": "..."}`,返回 `task_id` |
| GET | `/api/task/{task_id}` | 查询任务状态与事件 |
| GET | `/api/task/{task_id}/stream` | SSE 实时事件流 |
| POST | `/api/files` | 上传文件(multipart) |
| GET | `/api/files` | 列出工作区文件 |
| GET | `/api/files/{file_id}` | 下载文件 |
| DELETE | `/api/files/{file_id}` | 删除文件 |
| GET | `/api/knowledge` | 查看已建立索引的知识文档 |
| POST | `/api/knowledge/reindex` | 增量刷新知识库索引 |
| POST | `/api/logs` | 上报前端日志 |
| GET | `/api/logs` | 查询日志 |
| GET | `/api/logs/stream` | SSE 实时日志流 |
| GET | `/health` | 健康检查 |

> 所有接口通过 `X-Session-Id` 请求头区分用户 session(文件下载用 `?session=` 查询参数)。

## 企业知识库与 Skill 协作

RAG 是 Skill 的内部辅助能力，不是用户上传文件问答功能。企业文档由部署或管理员放入：
`backend/data/knowledge/<subsystem_id>/<knowledge_type>/<file>`，例如
`order-system/sop/refund.md`，然后调用 `/api/knowledge/reindex` 刷新索引。

已选定的 Skill 在执行日志分析、故障定位等任务时，可以调用 `search_knowledge` 查询设计文档、SOP
和历史解决方案；用户上传到 Session 工作区的文件仍由 `read_file` 等文件工具处理，不会进入企业 RAG。

## Session 隔离与文件释放

- 每个 `X-Session-Id` 对应一个独立工作区:上传/生成的文件、对话上下文、任务事件互相隔离。
- 文件落盘在 `backend/data/{session_id}/`，并保留前端上传时的相对目录结构；Skill 脚本通过 `WORKSPACE_DIR` 访问当前工作区。
- 空闲超过 `SESSION_TTL_SECONDS` 且无运行中任务的 session 会被后台任务自动清理(连同磁盘文件一并释放)。

## Skill 机制

类似 opencode 的 skill:每个 skill 是一份 Markdown 说明文档,放在 `backend/skills/<name>/SKILL.md`(或 `backend/skills/<name>.md`),用 frontmatter 声明元信息:

```markdown
---
name: log-troubleshooting
description: 日志故障定位:根据服务日志与错误堆栈系统化定位线上故障根因。
---

# 正文(可写任意长度)
```

- 启动时自动扫描 `SKILLS_DIR`(默认 `backend/skills`),将每个 skill 的 `name + description` 注入 system prompt,让 Agent 知道有哪些能力。
- Agent 需要详细说明时调用 `read_skill` 工具按需读取正文,避免大段说明常驻上下文。
- Skill 需要执行外部脚本时调用 `run_skill_script`;运行路径限制在所选 Skill 目录内,且不经过 shell。
- 股票 skill 的运行依赖在各自的 `SKILL.md` 中说明；按需安装后才可执行行情和公告查询脚本。
- `name` 缺省时用目录名(或文件名)作为技能名。

## MCP 工具接入

后端可作为 MCP Client 连接受控的 MCP Server,并将其工具注册为带命名空间的内部工具名。复制
`backend/mcp_servers.example.json` 为 `backend/mcp_servers.json`,将 CodeGraph 的仓库路径替换为实际路径,
然后设置 `MCP_SERVERS_CONFIG`(可选,默认读取 `backend/mcp_servers.json`)。

CodeGraph stdio 示例:

```bash
codegraph mcp serve --root /path/to/repository --stdio
```

使用 MCP 前先执行 `python3 -m pip install mcp==0.9.1`。

每个 MCP Server 必须配置 `allowed_tools`;每个 Skill 可通过 `skill_tools` 进一步限制工具。工具会以
`mcp__codegraph__search` 这类名称暴露给 Agent。当前版本只接入 MCP Tools,不会自动加载 Resources 或 Prompts,
以控制 128k 上下文占用。

## Knowledge MCP

企业知识检索运行在独立的 `knowledge-mcp/` 服务中，使用 Python 3.11+ 和 LlamaIndex；现有 Agent Runtime 保持
原有 Python 3.9.11 环境，并且只通过 MCP Streamable HTTP 调用它。详细的安装、语料导入、检索配置和评测说明见
[`knowledge-mcp/README.md`](knowledge-mcp/README.md)。

首次安装并启动：

```bash
./knowledge-mcp/dev.sh setup
./knowledge-mcp/dev.sh fetch-datasets
./knowledge-mcp/dev.sh serve
cp backend/mcp_servers.example.json backend/mcp_servers.json
```

Knowledge MCP 只暴露 `search_knowledge`、`search_runbook`、`get_document`、`get_context` 和
`list_knowledge_bases`。文档导入和重建索引是管理员 CLI 操作，不会暴露给 Agent。

## 事件类型

`thinking` / `tool_call` / `tool_result` / `message` / `final`

## 日志

- 后端日志写入 `backend/logs/app.log`(轮转,5MB×5),同时输出到控制台。
- 服务进程日志写入 `.run/backend.log` 与 `.run/frontend.log`(`./dev.sh logs` 可查看)。

## 非目标(当前版本)

Multi Agent、Skill 系统、Workflow 编排、长期 Memory、复杂权限、自动优化。
