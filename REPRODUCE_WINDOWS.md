# EchoMind Windows 复现指南

本文给出两条复现路径：Docker Compose 用于完整体验，Conda 用于运行源码和单元测试。推荐先走 Docker Compose，因为它会同时提供 Redis、ChromaDB、Prometheus 和 Nginx。

## 1. 先理解运行链路

```text
POST /chat
  -> Redis / ChromaDB 读取记忆
  -> IntentRecognizer 三路融合识别意图
  -> AgentOrchestrator 选择 General / Technical / Billing / Escalation
  -> 按 Agent 白名单执行工具，并按需检索知识库
  -> LLM 生成或合成回复
  -> 写回记忆、记录工具轨迹和监控指标
```

## 2. 完整复现：Docker Compose（推荐）

### 2.1 前置条件

- Windows 10/11，已启用 WSL 2
- Docker Desktop，使用 Linux containers
- 一个可用的 DeepSeek API Key（项目通过 Anthropic Messages 兼容协议调用）

确认 Docker 可用：

```powershell
docker version
docker compose version
```

### 2.2 配置环境变量

在项目根目录执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

至少把下面三项改成实际值：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
```

不要提交 `.env`。它已经写入 `.gitignore` 和 `.dockerignore`；但如果该文件在历史上已被 Git 跟踪，还需在确认后执行 `git rm --cached .env`，并提交这次“仅停止跟踪”的变更。命令不会删除本机文件。若真实密钥曾推送到远端，应立即在模型服务商后台轮换密钥。

### 2.3 构建并启动

```powershell
docker compose config
docker compose up -d --build
docker compose ps
```

首次构建会下载 Python 镜像、依赖和 ChromaDB 的 ONNX embedding 模型，耗时取决于网络。若应用没有变成 healthy：

```powershell
docker compose logs --tail 200 echomind
docker compose logs --tail 100 redis chromadb
```

### 2.4 分层验收

健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

查看 Skills：

```powershell
Invoke-RestMethod http://localhost:8000/skills
```

发起对话：

```powershell
$body = @{
  message = '登录时报 401，同时订单被重复扣款'
  user_id = 'demo_user'
  conv_id = 'demo_conv'
} | ConvertTo-Json

$chat = Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/chat `
  -ContentType 'application/json' `
  -Body $body

$chat | ConvertTo-Json -Depth 8
```

这个用例应展示复合意图路由；响应中的 `primary_agent`、`supporting_agents`、`tools_used` 和 `request_id` 是重点。

查询本次工具轨迹：

```powershell
Invoke-RestMethod "http://localhost:8000/trace/tool/$($chat.request_id)" |
  ConvertTo-Json -Depth 10
```

导入并检索演示知识库：

```powershell
curl.exe -X POST http://localhost:8000/knowledge/upload `
  -F "file=@data/demo_docs/sample_knowledge.json"

Invoke-RestMethod `
  -Method Post `
  -Uri 'http://localhost:8000/search?query=API如何接入&top_k=3'
```

最后检查监控和评测：

```powershell
Invoke-RestMethod http://localhost:8000/monitor | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post http://localhost:8000/eval/run | ConvertTo-Json -Depth 10
```

`/eval/run` 会产生多次模型调用，可能耗时并产生 API 费用；学习主链路时可以暂时跳过。

可视化入口：

- EchoMind 聊天前端：<http://localhost>
- Swagger：<http://localhost:8000/docs>
- Prometheus：<http://localhost:9090>

停止服务但保留数据：

```powershell
docker compose down
```

## 3. 源码复现：Conda + Docker 依赖服务

Windows 本地建议使用 Python 3.11。仓库锁定的 `chromadb==0.5.23` 在 Python 3.12/Windows 上可能需要本机安装 Microsoft C++ Build Tools；Docker 中的 Python 3.12 是 Linux 环境，不受这个问题影响。

```powershell
conda create -p .\.conda-env python=3.11 -y
conda run -p .\.conda-env python -m pip install -r requirements-dev.txt
conda run -p .\.conda-env python -m pytest -q
```

只启动本地源码所需的数据库：

```powershell
docker compose up -d redis chromadb
conda run -p .\.conda-env python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

此时 `.env.example` 的本机连接值应保持为：

```env
REDIS_URL=redis://:echomind123@localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_PERSIST_DIRECTORY=./data/chroma
```

## 4. 常见失败与定位

### `Microsoft Visual C++ 14.0 or greater is required`

这是 Python 3.12/Windows 安装 `chroma-hnswlib==0.7.6` 时从源码编译导致的。优先改用 Python 3.11，或直接用 Docker Compose。

### `/health` 返回 503 或应用反复重启

```powershell
docker compose ps
docker compose logs --tail 200 echomind
```

优先检查 DeepSeek API Key、模型名、Redis 密码，以及 ChromaDB 是否 healthy。

### `/chat` 报 Redis 认证或连接错误

容器内必须连接 `redis:6379`，宿主机源码必须连接 `localhost:6379`。Compose 已自动覆盖容器内地址，不要把本机 `.env` 的 `localhost` 手工写进 `docker-compose.yml`。

### 第一次知识检索很慢

本地嵌入式 ChromaDB 可能首次下载 embedding 模型。Dockerfile 已在构建阶段预下载该模型；完整复现优先走 Docker。

## 5. 建议阅读顺序

1. `api/main.py`：HTTP 主入口和完整请求链路
2. `core/intent_recognizer.py`：LLM、Embedding、Pattern 三路融合
3. `agents/agent_orchestrator.py`：路由、并行协作、工具调用和降级
4. `agents/tools.py`：各 Agent 的工具边界
5. `memory/conversation_memory.py`：Redis + ChromaDB 三级记忆
6. `mcp/tool_manager.py`：缓存、熔断、查询改写和重排
7. `monitor/performance_monitor.py` 与 `evaluation/evaluator.py`：可观测与评测闭环
