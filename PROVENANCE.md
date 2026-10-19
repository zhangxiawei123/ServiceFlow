# ServiceFlow 来源与第三方说明

## 维护与代码来源

ServiceFlow 由 GitHub 用户 [zhangxiawei123](https://github.com/zhangxiawei123) 维护，仓库为 [zhangxiawei123/ServiceFlow](https://github.com/zhangxiawei123/ServiceFlow)。

项目初始代码来源为 [Biscuit-AI531/EchoMind](https://github.com/Biscuit-AI531/EchoMind)。现有仓库对产品命名、文档、模型配置、前端、部署保护及记忆检索进行了工程整理与调整。名称统一不改变已有代码的来源或原作者权利，也不表示所有模块均由当前维护者从零原创。

## 本仓库可核验的工程调整

- DeepSeek Anthropic Messages 兼容配置，以及配置回归测试。
- 独立聊天工作台和 ServiceFlow 网页登录入口。
- Render 单域名演示部署、签名 Cookie、请求限制及管理接口隔离。
- Chroma 情景记忆多条件查询、用户范围约束和画像 upsert 修复。
- 单元测试、真实 Chroma 记忆集成测试及构建阶段验证。
- ServiceFlow 品牌、文档结构、API 用例和评测口径整理。

具体变更以本仓库 Git 提交、测试和运行记录为准；不得把未实施的优化计划写成已经取得的成果。

## 许可状态

当前整理版本中没有找到可确认的上游 LICENSE 文件。公开可访问不等于可以任意重新授权；本次访问上游链接也未能核验其当前许可状态。

本说明不是新的开源授权，不将上游代码改授为 MIT、Apache 或其他许可证。后续应核实上游授权范围，保留取得的许可证、版权及 NOTICE；若存在额外授权要求，应先满足再进一步分发或商业使用。维护者新增内容也不能替代上游部分所需授权。

## 第三方组件与模型

Python、FastAPI、Pydantic、Uvicorn、Redis、ChromaDB、Anthropic SDK、Prometheus 等组件及容器镜像保留各自权利和许可。依赖清单见 `requirements.txt`；向量模型 all-MiniLM-L6-v2 不是本项目训练的模型。DeepSeek 属外部模型服务，调用遵循对应账户与服务条款。

演示知识仅用于功能测试，不构成真实价格、退款政策、隐私保证或合规认证。不得从项目命名、示例文档或模型回复推断存在真实客户或商业运营。
