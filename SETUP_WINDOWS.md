# ServiceFlow Windows 安装与本地开发

## 1. 检查 Docker 环境

打开 Docker Desktop，等待引擎就绪，并使用 Linux containers。然后在 PowerShell 中执行：

```powershell
docker version
docker compose version
```

`docker version` 必须同时出现 Client 和 Server。若报 `npipe/docker_engine` 不存在，说明本机引擎未启动或当前 context 不正确，尚不是项目代码问题：

```powershell
docker context ls
wsl --status
```

先检查 Docker Desktop 的 WSL 集成和启动错误，不要通过删除数据卷来修复引擎问题。

## 2. 获取源码和配置

```powershell
git clone https://github.com/zhangxiawei123/ServiceFlow.git
Set-Location ServiceFlow
Copy-Item .env.example .env
notepad .env
```

已有 `.env` 时不要再次覆盖。填写 `DEEPSEEK_API_KEY`，确认 `DEEPSEEK_MODEL` 和 `DEEPSEEK_BASE_URL` 与账户一致。Redis 密码和 `REDIS_URL` 中的密码必须匹配；示例密码仅用于本地演示。

Compose 会把应用容器中的数据库地址覆盖为 `redis:6379`、`chromadb:8000`。宿主机源码开发则使用 `localhost:6379`、`localhost:8001`，两种地址不能混用。

## 3. 构建与访问

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 serviceflow
```

首次启动需要下载依赖和向量模型。访问 [聊天页面](http://localhost)、[Swagger](http://localhost:8000/docs) 和 [健康检查](http://localhost:8000/health)。访问 8000 端口根路径会进入接口文档；聊天页面由 80 端口的 Nginx 提供。

## 4. 验证聊天、检索和追踪

```powershell
$body = @{
  message = '登录报 401，同时订单被重复扣款'
  user_id = 'local-demo'
  conv_id = 'first-session'
} | ConvertTo-Json

$result = Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType 'application/json' -Body $body
$result | ConvertTo-Json -Depth 8
Invoke-RestMethod "http://localhost:8000/trace/tool/$($result.request_id)" | ConvertTo-Json -Depth 10
```

观察 `primary_agent`、`supporting_agents`、`routing_reason`、`tools_used` 和 `request_id`。模型输出存在不确定性，不保证每次走相同工具；混合问题应分别覆盖技术与账单诉求。

```powershell
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/search?query=退款政策&top_k=3'
Invoke-RestMethod http://localhost:8000/skills
Invoke-RestMethod http://localhost:8000/monitor
```

检索返回默认示例政策，不是维护者真实经营业务的承诺。

## 5. 源码开发

完整安装优先使用 Docker。Windows 原生开发可尝试 Python 3.11；旧版 Chroma 的原生依赖可能需要 C++ 编译工具，是否有 wheel 取决于 Python 版本和平台。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
docker compose up -d redis chromadb
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

激活受执行策略限制时，直接使用 `.\.venv\Scripts\python.exe`，不必修改系统全局策略。源码运行 API 不会自动启动前端；需要工作台时使用 Compose 全栈方案。

## 6. 回归与停止

```powershell
python -m pytest -q
node --check frontend/app.js
docker compose down
```

`down` 不附加 `-v`，保留命名卷。不要为了排障清空已有数据。

## 7. 升级命名的注意事项

当前应用服务名为 `serviceflow`，日志命令和 Nginx 上游已同步更新。旧版 Skills 环境变量仍可读取，新配置使用 `SERVICEFLOW_SKILLS_DIR` 和 `SERVICEFLOW_SKILLS_MAX_PROMPT_CHARS`。

如已有旧 Compose 项目，先确认其 project name、容器和卷，备份后停止旧服务，再启动新版。更换目录或 project name 会改变默认卷前缀；本次更新不执行数据迁移或删除旧卷。

浏览器优先读取 `serviceflow-user-id`，没有时沿用旧用户标识。Chroma collection 名称及 Redis key 结构未更改。

更多配置、接口及故障定位见[完整使用指南](wiki/完整使用指南.md)。
