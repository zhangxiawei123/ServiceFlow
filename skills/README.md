# ServiceFlow 业务 Skills

这些文件是客服业务规则，不是执行工具或权限授予。加载器读取规则并按角色、关键词匹配后注入 system prompt；代码中的白名单与参数校验仍是安全边界。

## 目录与配置

三类规则位于 `general_customer_service/`、`technical_support/` 和 `billing_support/`。

`SERVICEFLOW_SKILLS_DIR` 指定根目录，`SERVICEFLOW_SKILLS_MAX_PROMPT_CHARS` 指定总预算，默认 5000 字符。旧前缀变量仅用于迁移；两者同时存在时新变量优先。

## 文件格式

推荐 `skills/<场景>/SKILL.md`：

```markdown
---
name: 技术支持处理规范
description: ServiceFlow 技术角色的排障与安全边界
keywords: 报错,错误,接口,API,部署,超时,401,500
agents: technical
enabled: true
---

# 处理规则
先确认错误码、时间及环境；不索要密码，不声称读取了真实日志。
```

加载器支持 Markdown、TXT、JSON。front matter 是项目内简单解析，不是完整 YAML 引擎；使用简单标量和逗号分隔列表，避免复杂嵌套语法。

角色值使用 `general`、`technical`、`billing`、`escalation`。角色及关键词条件都应验证，空关键词会扩大应用范围；不要未经测试加入全局规则。

## 编写要求

- 先写职责和禁止事项，再写处理流程。
- 将关键约束放在前部，过长内容会截断。
- 不索要密码、验证码、完整卡号、API Key 或 Token。
- 不宣称执行不存在的退款、业务查询、日志读取和工单动作。
- 规则属于可信维护文件，变更要审阅；外部文档不能任意覆盖工具授权。

## 热加载与验收

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/skills/reload
Invoke-RestMethod http://localhost:8000/skills | ConvertTo-Json -Depth 8
```

检查加载错误、匹配角色和实际回答，再提交。公网演示禁用管理接口，应在本地验证后部署。热加载不提供版本回滚或分布式同步，生产应增加规则版本和发布审计。
