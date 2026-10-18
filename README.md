# AI 产品经理 Agent

输入一句产品想法，Agent 自动完成需求分析、任务规划、调用外部工具（竞品搜索、本地知识库），
生成一份结构化 PRD，并支持在后续对话里继续修改。

技术栈：FastAPI + LangGraph + SQLite + React (Vite + TypeScript)。
前端和后端打包在同一个容器里，一条命令启动。

---

## 快速开始

### 用 Docker（推荐）

先准备两个 Key，写进系统环境变量，不要写进代码或 .env 提交：

```
setx OPENCODE_GO_API_KEY "你的模型网关 key"
setx TAVILY_API_KEY "你的 tavily key"
```

重开一个终端让环境变量生效，然后在项目根目录执行：

```
docker compose up --build
```

浏览器打开 http://localhost:8000 。

- 前端和接口同源，都走 8000 端口，不需要额外配置。
- 数据存在 `./data` 目录（挂载了 volume），容器删了重建，会话和 PRD 版本都还在。
- 停止：`docker compose down`

### 本地开发

后端需要 Python 3.12：

```
conda create -n ai-pm-agent python=3.12 -y
conda activate ai-pm-agent
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

前端需要 Node 18+，另开一个终端：

```
cd frontend
npm install
npm run dev
```

前端在 http://localhost:5173，开发服务器的 `/api` 已经代理到 8000。

---

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `OPENCODE_GO_API_KEY` | 模型网关的 key（也接受 `LLM_API_KEY`） | 无，必填 |
| `TAVILY_API_KEY` | Tavily 搜索的 key | 无，不填则跳过联网调研 |
| `LLM_BASE_URL` | OpenAI 兼容的接口地址 | `https://opencode.ai/inference/go/v1` |
| `LLM_MODEL` | 模型名 | `deepseek-v4.1-flash` |
| `APP_DB_PATH` | 业务数据库路径 | `./data/app.db` |
| `CHECKPOINT_DB_PATH` | LangGraph 记忆库路径 | `./data/checkpoints.db` |

如果想换成别的 OpenAI 兼容服务（DeepSeek 官方、GLM、Kimi 等），只改 `LLM_BASE_URL`、
`LLM_MODEL`、`LLM_API_KEY` 三个值就行，不用动代码。

---

## 目录结构

```
.
├─ docker-compose.yml
├─ Dockerfile                  # 多阶段：先构建前端，再打进后端镜像
├─ .env.example
├─ docs/
│  ├─ agent-flow.png           # Agent 工作流程图
│  └─ agent-flow.gv            # 流程图的 Graphviz 源文件
├─ backend/
│  ├─ requirements.txt
│  ├─ tests/                   # smoke.py（图级）、api_smoke.py（接口级）
│  └─ app/
│     ├─ main.py               # FastAPI 入口，托管前端静态文件
│     ├─ config.py             # 读环境变量
│     ├─ db.py / models.py     # SQLite：sessions / messages / prd_versions
│     ├─ schemas.py            # PRD、调研计划、修订结果等的 Pydantic 模型
│     ├─ agent/
│     │  ├─ graph.py           # LangGraph 状态机 + checkpointer 生命周期
│     │  ├─ state.py           # AgentState 定义
│     │  ├─ nodes.py           # 各个节点
│     │  ├─ tools.py           # web_search(Tavily) + knowledge_query(本地知识库)
│     │  ├─ knowledge_base.json
│     │  └─ llm.py             # 模型封装，JSON 模式 + 校验 + 重试
│     └─ api/
│        ├─ chat.py            # SSE 流式对话
│        └─ sessions.py        # 会话 / PRD / 版本 / 事件
└─ frontend/
   └─ src/
      ├─ App.tsx
      ├─ api.ts
      ├─ types.ts
      ├─ styles.css
      └─ components/           # Chat / Sidebar / PrdPanel / AgentSteps
```

---

## Agent 是怎么跑的

整个流程是一张 LangGraph 状态图，节点和执行顺序在 `backend/app/agent/graph.py` 里定义。
完整流程图见 `docs/agent-flow.png`。

分五个阶段：

**一、输入与会话初始化**

用户在前端输入想法，发到 `POST /api/chat`（SSE 长连接）。后端先判断是新建会话还是已有会话，
再判断这个会话是否已经有 PRD——这决定了后面的流程走"新建"还是"修订"。

**二、需求分析**

`analyze` 节点先判断这句话属于哪一类：

- 是一个新的产品想法 → `create`
- 是要求修改已有 PRD（比如"再加个导出功能"）→ `revise`
- 只是寒暄或与产品无关（比如"你好"、"你是谁"）→ `chat`

分到 `chat` 的话，只回一句普通对话，不会生成 PRD，也不会占用版本。
其余两类才进入后面的流程。

**三、任务规划**

`planning` 节点让模型输出一份调研计划：要不要联网搜竞品、要不要查知识库、具体查什么词。
这里模型只做决策，不执行。

**四、调用工具**

`research` 节点按上一步的计划，并发执行两个工具：

- `web_search`：调 Tavily，搜竞品、市场、价格
- `knowledge_query`：在本地知识库里检索 PRD 方法论（RICE、KANO、JTBD 这些）

结果汇总成带来源链接的上下文。没有配 Tavily key，或者调用失败，就跳过联网这几步，不阻塞主流程。

**五、生成或修订 PRD**

- 新建走 `draft_prd`：让模型按 Pydantic 定义的 PRD 结构输出，字段不全或 JSON 解析失败会自动重试。
- 修订走 `revise_prd`：带上当前 PRD 和用户的修改要求，输出新的 PRD，外加这次改了哪些字段。

无论哪种，每完成一轮都会写一条新的 PRD 版本记录，前端把被修改的字段高亮出来。

流程里的每一步都会通过 SSE 推给前端，前端在对话流里内联显示"执行过程"。
我们只推步骤和工具调用，不推模型内部的思考内容。

---

## 几个设计选择

**为什么用 LangGraph**

主要图三样东西：状态图做可控编排、条件边做 create/revise 分流、checkpointer 做多轮记忆。
它的 checkpointer 直接把整轮 state 按 thread_id 持久化，省掉了手写会话状态管理。
代价是框架偏重、版本更新快，所以图本身写得很薄，重逻辑都放在普通函数里；checkpointer
初始化失败时会自动降级成内存记忆，不让框架拖垮主流程。

**为什么用显式决策节点，而不是原生的 function calling 循环**

原生做法是把工具定义通过 `tools=` 参数交给模型，模型返回 `tool_calls`，代码执行后再喂回去，
循环直到模型不再调用工具——控制流在模型手里。

我们改成：`planning` 节点让模型输出一个结构化的 JSON 计划（要不要工具、查什么），
`research` 节点再根据这个计划真正调用工具。控制流在代码里，只跑一轮。
这么做主要是为了稳定和可控：决策变成一个可校验的 JSON，节点固定，前端也好展示。

**PRD 为什么用 Pydantic 强约束 + 版本化**

PRD 字段是固定的（背景、目标、用户画像、功能、竞品、指标、里程碑、风险、待确认问题）。
用 Pydantic 约束住以后，多轮修订才能稳定地定位到具体字段去改，而不是每次重写一整篇。
每轮改动都存成新版本，记录了变更说明和被改的字段名。

**为什么用两个数据库**

`checkpoints.db` 是 LangGraph 的记忆，`app.db` 是业务数据。
分开是为了避开 SQLite 单文件的写锁竞争。

**为什么不做思维链展示**

前端只渲染步骤事件；结构化输出的步骤关掉了模型的 thinking（既快又省），
即使开了 thinking，网关也会把推理放在单独的 `reasoning` 字段里，代码只取 `content`。

---

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/chat` | 流式对话（SSE），body 是 `{ session_id?, message }` |
| GET | `/api/sessions` | 会话列表 |
| GET | `/api/sessions/{id}` | 会话详情，含消息和每轮的事件 |
| GET | `/api/sessions/{id}/prd` | 当前 PRD |
| GET | `/api/sessions/{id}/prd/versions` | 版本历史 |
| GET | `/api/sessions/{id}/events` | 流程事件回放 |
| GET | `/api/health` | 健康检查（模型、搜索是否就绪） |

SSE 事件类型：`session`、`step`、`prd`、`message_delta`、`done`、`error`。

---

## 数据库

三张表（都在 `app.db`）：

- `sessions`：会话，id、标题、创建/更新时间
- `messages`：消息，角色（user/assistant）、内容、以及该轮产生的流程事件（JSON）
- `prd_versions`：PRD 版本，版本号、PRD 内容（JSON）、变更说明、被改字段（JSON）

`checkpoints.db` 里是 LangGraph 自己的 `checkpoints` 和 `writes` 两张表，不用手动看。

---

## 测试

图级冒烟（不需要起服务）：

```
cd backend
python -m tests.smoke
```

接口级（需要先起好后端）：

```
cd backend
python tests/api_smoke.py
```

---

## 已知限制

- SQLite 单文件，LangGraph 的异步 checkpointer 也不是为生产准备的，演示和评估够用，上生产建议换 Postgres。
- 没有鉴权和多租户，超出题目范围，没做。
- 竞品调研依赖 Tavily，没配 key 时会降级成"跳过调研"。
- `deepseek-v4.1-flash` 生成 PRD 时开思考，会更慢一点，换的是质量。

---

## 排错

| 现象 | 处理 |
| --- | --- |
| `/api/health` 里 `llm_enabled` 是 false | 没读到 key，确认 `setx` 之后重开过终端 |
| 前端能打开，对话报错 | 检查模型网关地址、模型名和余额 |
| 竞品搜索没结果 | 检查 `TAVILY_API_KEY`，没配会自动跳过 |
| 8000 端口被占 | 改 `docker-compose.yml` 里的端口映射 |
