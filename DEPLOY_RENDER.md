# ServiceFlow 免费云端演示

此方案部署完整聊天页面与 Python API，使用一个 Render Free Web Service 和一个 Free Key Value 实例（兼容 Redis）。ChromaDB 使用项目已有的嵌入式降级路径，不额外购买向量数据库。

[一键部署到 Render](https://render.com/deploy?repo=https://github.com/zhangxiawei123/ServiceFlow)

## 首次部署

1. 打开上方链接，使用 GitHub 注册或登录 Render，并按提示允许读取 `zhangxiawei123/ServiceFlow`。
2. 检查两个资源 `serviceflow`、`serviceflow-redis` 的计划均为 **Free**，不添加付费磁盘或升级实例。
3. 在部署页面填写两个私密环境变量：
   - `DEEPSEEK_API_KEY`：你的模型 Key，只填在 Render，不写入 GitHub 文件。
   - `SERVICEFLOW_DEMO_PASSWORD`：自行设置至少 12 位的演示访问口令，建议使用密码管理器生成。
4. 点击部署，等待 Key Value 就绪、镜像构建完成和 Web Service 状态变为 **Live**。
5. 打开 Render 实际分配的 HTTPS 地址，在网页内的登录表单填写账号 `demo` 和刚设置的演示口令。口令可在服务的 Environment 页面查看，不是 DeepSeek API Key。
6. 发送一条简短消息，再问一个知识库问题。只有页面、真实模型回复、会话及检索都验证成功，才算部署完成。

网页登录后使用仅 HTTPS、HttpOnly、SameSite=Strict 的签名会话 Cookie，有效期 8 小时；服务重启或重新部署后需要重新登录。前端的 `/chat`、`/health` 与逐条工具追踪请求均使用同一域名。不需要填写额外 API 地址。命令行仍兼容 Basic Auth。平台会提供 HTTPS，不需要自购域名。

## 演示入口的约束

- 入口：`python -m deploy.serve`，监听 Render 提供的 `PORT`，只运行一个 Uvicorn worker。
- 公开 `/healthz` 只返回就绪状态，用于平台健康检查；应用生命周期初始化完成后才接收请求，且探针会检查 Redis 连接，不暴露连接细节。
- 首页未登录时显示公开登录表单；聊天界面、静态资源、聊天及逐条追踪都要求访问口令。登录尝试共享每分钟 10 次限制，Cookie 鉴权的跨站写请求被拒绝。评测、知识库写入、全量追踪列表、管理面板和 API 文档不通过演示入口公开。
- 每次消息最多 2000 字、请求体最多 16 KiB。同一进程只同时处理一条聊天请求，所有访问者共享默认每小时 30 次的请求额度，超限返回 429。
- 这只是单账号演示入口，不是完整的多租户用户系统；请只把演示口令分享给需要体验的人。
- 进程级额度在服务重启后重置，不构成模型账户的金额上限。模型生成、查询改写、重排和后台画像更新仍可能消耗你已有的模型额度。
- 本地开发继续使用原有 `docker-compose.yml`，无需设置演示口令。
- Render 镜像构建时运行 4 项真实 Chroma 记忆集成测试（固定测试向量，不下载额外模型、不调用 LLM）；失败会阻止发布，pytest 不进入最终运行镜像。

## 免费版限制

- Render Free Web Service 的内存为 512 MB，CPU 有限。此配置减少了独立进程和并发，但真实 RAG 初始化与推理的内存、延迟仍需在平台上验证；没有自动升级付费实例的配置。
- 闲置约 15 分钟后会休眠；再次访问需要冷启动，应用加载嵌入模型还需要额外时间。面试前应先打开地址确认能聊天。
- 本地文件系统是临时的。重启、重新部署或休眠后，嵌入式 ChromaDB 的对话画像、情景记忆及新增知识可能丢失。知识库为空时项目会加载内置默认文档。
- Free Key Value 不持久化，重启可能丢失近期会话。工作记忆与向量记忆还可能在不同时间重置，不应在这里保存重要对话或真实客户信息。
- Free Web Service 每个工作区共享月度运行时长及构建、流量额度。没有添加付款方式时，超过相应额度可能暂停服务或构建；本方案不要求升级或购买资源。
- 免费托管不等于免费模型调用，模型仍使用你自己的 DeepSeek 账户额度。

## 排查

- `Missing ... PASSWORD` 或口令长度错误：检查私密变量，至少 12 位；默认用户名为 `demo`。
- Redis 连接失败：检查两个资源是否同区域、Key Value 是否就绪；`REDIS_URL` 应由 Blueprint 自动引用内部连接串，不是 `localhost`。
- 模型 401/403：检查 Key 与账户权限；模型不可用时核对 `DEEPSEEK_MODEL` 与供应商实际提供的模型。
- `Exited with status 137`、OOM 或进程反复重启：先查看平台日志及内存，不要自动升级付费计划；反馈具体错误后再决定是否改用本机临时公网演示等方案。
- 看到网页但聊天失败：网页可打开不代表 Redis 和模型可用，需要检查 `/chat` 的响应与服务日志。
- 502 或启动页：等待冷启动；持续失败时检查 Events 与 Logs，而非反复点击发送。
- 首页显示登录表单是正常状态；旧版入口返回 401 并依赖浏览器原生 Basic 弹窗，部分内嵌浏览器无法处理。请使用新版网页登录；已有 Cookie 失效时重新填写访问口令。
- 情景记忆多条件过滤使用 `$and` 组合用户与会话条件，跨会话补充检索仍只查询同一用户。空记忆直接返回空结果。画像使用 `upsert`，不会先删除不存在的记录。ChromaDB 0.5.23 的遥测依赖锁定兼容版本，保持遥测关闭，避免 capture 签名不兼容告警。

## 官方说明

- [Render 免费版限制](https://render.com/docs/free)
- [Render 计算资源](https://render.com/docs/compute-plans)
- [Render Blueprint 配置](https://render.com/docs/blueprint-spec)
- [Render Key Value](https://render.com/docs/key-value)

一键部署文件和测试通过，不代表云资源已经创建或公网聊天已验证。最终地址以 Render 控制台实际分配为准。
