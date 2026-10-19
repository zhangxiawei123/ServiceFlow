# ServiceFlow

面向客服场景的多 Agent 服务编排系统，将意图识别、专业角色协作、知识检索、会话记忆和运行观测组织成一条可追踪的处理链路。

[在线演示](https://serviceflow-yejw.onrender.com/) · [文档中心](wiki/文档中心.md) · [Windows 安装](SETUP_WINDOWS.md) · [云端部署](DEPLOY_RENDER.md)

演示站点需要访问口令，账号默认为 `demo`。口令由项目维护者在 Render 私密环境变量中管理，不是模型 API Key。免费实例可能冷启动；模型调用消耗维护者的账户额度。

## 能做什么

- 意图分析：融合 LLM、向量匹配和规则，输出业务意图、实体、紧急度与置信度。
- 服务编排：General、Technical、Billing 与 Escalation 分工；复合问题支持主辅 Agent 并行处理及结果合成。
- 工具执行：按角色暴露工具，校验输入，限制调用轮次，并记录请求级工具轨迹。
- RAG：ChromaDB 文档切片、查询改写、并行召回、去重及 LLM 重排；失败时有回退路径。
- 分层记忆：Redis 保存近期消息与摘要，ChromaDB 保存情景记忆和用户画像。
- 业务规则：从本地 Skills 文件加载 SOP，按角色及关键词匹配，可热加载。
- 质量治理：运行统计、告警、路由惩罚，以及意图分类和对话质量评测。

这是可运行的工程演示，不执行真实退款、修改订单或创建外部工单。角色差异不等于多个模型，也不表示模型经过训练或微调。

## 快速启动

需要 Docker Desktop（Linux containers）及可用的 DeepSeek API Key。Windows 详细步骤见[安装指南](SETUP_WINDOWS.md)。

```powershell
Copy-Item .env.example .env
notepad .env
```

填写：

```dotenv
DEEPSEEK_API_KEY=replace_with_your_key
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
```

模型通过 Anthropic Messages 兼容协议接入；模型标识和权限以账户实际可用配置为准。`.env`、数据库和日志不应提交。

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 serviceflow
```

- 聊天工作台：[http://localhost](http://localhost)
- 本地接口文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)
- Prometheus：[http://localhost:9090](http://localhost:9090)

本地完整 API 未提供生产级鉴权，只应在可信开发环境使用。公网演示采用独立的口令网关，不开放管理及评测接口。

## 处理链路

```text
用户消息 → 读取记忆 → 意图与实体识别 → 主辅 Agent 路由
                                     ↓
                            Skills + 角色工具 + 按需 RAG
                                     ↓
                      回复合成 → 写回记忆 → 请求轨迹与统计
```

RAG 在聊天主链路中由 Agent 的共享工具触发；不是每条消息固定检索。记忆压缩和画像更新也可能额外调用模型。

## 工程结构

| 目录 | 职责 |
|---|---|
| `frontend/` | 原生 HTML、CSS、JavaScript 聊天与登录页面 |
| `api/` | FastAPI 生命周期、请求模型和 HTTP 接口 |
| `core/` | 模型配置、意图识别、文本处理和 Skills 加载 |
| `agents/` | 角色契约、路由、工具执行及回复合成 |
| `mcp/` | 项目内工具管理和 ChromaDB 知识库 |
| `memory/` | 工作记忆、历史摘要及画像 |
| `monitor/`、`evaluation/` | 在线观测与离线评测 |
| `deploy/`、`config/` | 公网演示网关、容器及反向代理配置 |
| `tests/`、`wiki/` | 自动化验证与项目文档 |

`MCPToolManager` 是内部工具抽象，当前不等于实现了标准 MCP Server。

## 文档导航

- [项目定位](wiki/ServiceFlow定位与技术亮点.md)：范围与能力边界
- [技术亮点](wiki/技术亮点.md)：设计取舍和优化方向
- [重点代码](wiki/重点代码.md)：按调用关系阅读源码
- [业务流程说明](wiki/业务流程说明.md)：单轮、多轮及异常路径
- [完整使用指南](wiki/完整使用指南.md)：配置、API、数据和排障
- [评测与优化](wiki/评测与优化.md)：数据集、实验和证据要求
- [开发与面试手册](wiki/ServiceFlow开发手册.md)：模块知识与深挖问题

## 验证

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --check frontend/app.js
```

全量测试需要 ChromaDB 依赖；Windows 原生安装遇到编译问题时可使用 Linux 容器。云端镜像构建额外执行真实 Chroma 记忆集成测试。单元测试通过不代表回答准确率，功能参数也不代表性能提升；评测结果应附带数据集和运行报告。

## 来源与维护

项目由 [zhangxiawei123](https://github.com/zhangxiawei123) 维护。代码来源、第三方依赖和本仓库的工程调整见[来源说明](PROVENANCE.md)。本仓库未声明拥有全部上游代码的原创权，也未附加未经确认的开源许可证。
