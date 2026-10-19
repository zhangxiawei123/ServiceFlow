# ServiceFlow 云端演示部署

部署文件：`render.yaml`、`deploy/render.Dockerfile` 和 `deploy/serve.py`。当前演示入口为 [ServiceFlow](https://serviceflow-yejw.onrender.com/)。

采用 Web Service 承载前端与 API，Key Value 提供 Redis 兼容服务；ChromaDB 在 Web 进程内以嵌入式模式运行。本方案面向个人演示，不是高可用生产架构。

## 创建与配置

[打开部署入口](https://render.com/deploy?repo=https://github.com/zhangxiawei123/ServiceFlow)，关联 GitHub 仓库。检查两个资源的计划均为 Free，不添加付费磁盘。

私密变量：

| 变量 | 用途 |
|---|---|
| `DEEPSEEK_API_KEY` | 模型调用凭据，只填在平台私密配置 |
| `SERVICEFLOW_DEMO_PASSWORD` | 至少 12 位访问口令，不是模型 Key |
| `SERVICEFLOW_DEMO_USERNAME` | 演示用户名，默认为 `demo` |
| `REDIS_URL` | Blueprint 引用 Key Value 内部连接串 |

模型名、接口地址和请求额度在 `render.yaml` 中提供默认配置。已有部署更新代码时不需要重设口令或新建数据库。

## 发布验收

1. 推送已经测试的代码，确认部署对应的 commit。
2. 查看构建日志；镜像构建必须通过 Chroma 记忆集成测试。
3. 等待服务状态为 Live，而不是仅看到构建成功。
4. 检查公开 `GET /healthz` 返回 200。
5. 首页显示 ServiceFlow 登录表单；输入账号及演示口令后进入工作台。
6. 发起真实聊天和知识检索，检查响应、工具轨迹及新增错误日志。

公共 Git URL 来源的部署需要手动发布；是否自动部署以当前服务来源和设置为准。失败时定位构建、启动或健康检查的首个错误，不反复触发部署。

## 网关安全边界

- 登录后签发 Secure、HttpOnly、SameSite=Strict 签名 Cookie，有效期 8 小时，重启后需要重新登录。
- 命令行请求兼容 Basic Auth；浏览器使用网页表单，不依赖原生认证弹窗。
- 未认证不能访问聊天 API 和工作台资源；公开探针只返回就绪状态。
- Cookie 鉴权下拒绝跨站写请求。登录尝试受限，聊天最多 2000 字、请求体最多 16 KiB。
- 单进程同一时刻只处理一条聊天，默认共享每小时 30 次额度。
- 评测、知识写入、全量轨迹、监控管理及接口文档不通过公网网关开放。
- 此设计是单账号演示保护，不是多租户权限系统；用户标识不是可信身份。

额度不是金额上限：意图识别、回复、改写、重排、摘要与画像都可能调用模型。不要公开口令或上传真实客户信息。

## 存储与免费方案限制

Free 服务可能休眠、冷启动，存在 CPU、内存、运行时长、构建和流量限制。平台规则以[官方免费方案说明](https://render.com/docs/free)为准。

此配置没有持久化磁盘，向量知识、画像和情景记忆可能在实例更换或部署后丢失；Free Key Value 也不应当作可靠数据库。应使用可重新导入的示例知识，不保存重要数据。空知识库会装载内置演示文档。

## 排障

| 现象 | 检查点 |
|---|---|
| 口令错误 | Environment 中的 `SERVICEFLOW_DEMO_PASSWORD`，不要填模型 Key |
| 发布后掉线 | Cookie 随进程重启失效，重新登录 |
| Redis 连接失败 | Key Value 就绪、区域一致、内部连接串正确 |
| 模型 401/403 | 模型 Key、账户额度及模型权限 |
| 页面可见但无回复 | 检查 `/chat` 响应和对应时间段运行日志 |
| 502 或长时间加载 | 区分冷启动、启动异常、健康探针失败和 OOM |
| 记忆过滤错误 | 使用用户与会话条件的 `$and` 组合，先运行集成测试 |

记忆修复包含多条件过滤、同用户跨会话检索、去重与画像 upsert；不是把检索异常简单屏蔽。遥测兼容依赖已锁定，但仍需持续观察运行日志。
