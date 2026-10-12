# ADR-IMS-002 技术栈：Go 后端 + 轻量 Vue 前端（不用芋道）

> 状态：**部分取代**（2026-10-05）。后端语言、sqlc、调试器、「禁止 Python 做 API」以 **ADR-IMS-009** 为准。本文仍有效的是：Vue 3 轻量壳、禁 Vben、禁芋道、禁 OPS HTTP、Football 业务 HTTP。  
> 关联：ADR-IMS-001、ADR-IMS-009、完整 PRD v2.6.35、《全局开发规范》§7  
> 取代：原三期 PRD / 共享规范中的 **Spring Boot 3 + 芋道（Yudao）** 作为 IMS 实现基线

## 1. 决策

IMS **独立仓库/独立进程** 实现，**不**基于芋道脚手架，**不**复用 OPS Java 单体作为 IMS 运行时。

| 层 | 冻结 |
|----|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + Axios。**轻量壳**，禁止 Vben Admin 全家桶作为基线 |
| 后端 API | **Go**（建议 Go 1.23+），`cmd/api` 单一 HTTP 进程，前缀仍 `/admin-api/ims/` |
| 后端 Worker | **同仓库** `cmd/worker`：钉钉事件、Football 补偿、采集调度。禁止把长任务堵在 API 进程里 |
| 数据访问 | **sqlc + 显式 SQL** 打现网 MySQL（OPS 业务库 + IMS `ims_*`）。禁止重 ORM 当默认（禁止以 GORM AutoMigrate 改现网表） |
| 缓存/会话 | Redis（Token 黑名单、幂等 `clientToken`、序列号、SSO state） |
| 认证 | IMS **自建**钉钉 OAuth 授权码 SSO → 签发 IMS JWT。不走 Football `social-login`，不走芋道 SSO 模块 |
| Football | 仅 HTTP Client（超时/重试见完整 PRD BR-301）。禁止 JDBC/`@DS`/Feign |
| AI / jingcai | 管理端与编排在 Go；现成 Python 脚本允许 **旁路进程** 调用，禁止把整站改成 Python |
| 调试 | 本地 **Delve** 断点（Cursor/VS Code Go 扩展）。禁止以「Go 不能断点」为由改栈 |

## 2. 理由

- 产品要求启动快、接口快、少框架魔法；芋道与该目标冲突。
- 团队无 Go 经验，但已接受约 1～2 周学费；V1 以 CRUD + HTTP + 定时任务为主，不依赖 Python AI 训练栈。
- sqlc 对着 `oa_*` 写 SQL，便于和现网 OPS 对字段，避免推断表结构。

## 3. 工程约定（实现时不得另起一套）

- 模块目录按域分包（auth / sys / master / ipg / content / collect / …），**禁止**再引入 `cn.shenyu.ims` Java 包名作为 IMS 代码根。
- JSON 出参 **camelCase**（struct `json` tag）；库列 **snake_case**（sqlc）。禁止接口透出 snake_case。
- `tenant_id` 全表隔离语义保留；V1 恒 0 且接口不透出（沿用全局规范）。
- 敏感字段 AES-256 应用层加解密（沿用 OPS 铁律）。
- 业务错误码段沿用完整版补充 §4（12xx / 1500～1504 / 1271～1273=Football WebAPI 适配段）。
- 钉钉事件：回调只验签入队，Worker 消费；可用 Redis Stream 或 DB outbox，**V1 不强制 RocketMQ**。
- DDL：只加列；脚本人工运维窗口执行（ADR-IMS-001）。

## 4. 明确不做

| 不做 | 说明 |
|------|------|
| 芋道 / Spring Boot 作为 IMS 后端 | 历史文档仍出现时，以本 ADR 为准 |
| 复用 `sys_*` 芋道系统表作为 IMS 菜单角色 | IMS SYS 用 `ims_sys_*`（或完整 PRD 已命名的 IMS 自管表） |
| 用 Python 做 IMS API 主进程 | 已否决 |
| 本 ADR 发明新业务 API 路径或字段 | 路径仍以各模块 API 契约为准；契约未写的停止实现 |

## 5. 文档冲突裁决

技术栈冲突顺序：**本 ADR > 完整 PRD v2.5 > 全局开发规范 §7（已改写）> 完整版补充 > 原三期 PRD / 共享规范旧句**。  
原 V1/V2/V3 PRD 中的「芋道 SSO / TenantLineInnerInterceptor / MapStruct」视为过期实现描述，**不**作为切片依据。
