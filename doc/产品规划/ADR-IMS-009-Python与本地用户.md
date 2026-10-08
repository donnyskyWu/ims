# ADR-IMS-009 技术栈改为 Python，用户由 IMS 本地管理

> **状态**：**已确认**（2026-10-05，产品决定：优先做完整套管理功能；用户不从 Football 读取）  
> **取代**：ADR-IMS-002 的后端语言、数据访问、调试器，以及「禁止用 Python 做 IMS API」；PRD §5.1、§7.2、§11.3 中「用户经 Football HTTP 只读」；登记册冲突③  
> **仍有效**：ADR-IMS-002 的前端（Vue 3 轻量壳、禁 Vben）、禁芋道、禁 OPS HTTP、Football **业务** HTTP（方案、订单、赛程）；ADR-IMS-001 的 OPS 业务库只加列；ADR-IMS-006 范围；ADR-IMS-008 角色模型

## 1. 决策

| 项 | 冻结 |
|----|------|
| 后端 | **Python 3.11+**，**FastAPI**。一个 API 进程 + 一个 Worker 进程，同一仓库 |
| 数据访问 | **SQLAlchemy 2.0 + Alembic**。显式模型与迁移。禁止把现网 `oa_*` 交给自动删列 |
| 前端 | 继续 ADR-IMS-002：Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts |
| 缓存 | 本机开发可先用进程内会话存储；上线用 Redis（Token 黑名单、SSO state、幂等键） |
| 用户主数据 | **`ims.ims_sys_user`**。IMS 内完整管理：新建、修改、启用停用、重置密码、角色、部门、钉钉 userid |
| 登录 | 本地账号密码；钉钉 SSO 换票后按**手机号命中本地用户**。命不中不签发 |
| 上线导入 | 一次性导入 Football / OPS 用户，**保留来源主键**。重复执行按 id 幂等。新用户 ID 从已导入最大 ID 之后分配 |
| 人员外键 | 业务表人员 ID = `ims_sys_user.id` |
| Football | 只保留方案、订单、赛程等**业务** HTTP。运行时不读、不写 Football 用户，不连接 Football 库 |
| 部署 | Docker 或本机虚拟环境 + 进程守护。API 与 Worker 两个进程 |

## 2. 理由

管理端以表单、权限和流程为主，第一目标是做完功能。Python 对这类接口的交付快于 Go 和 Java。运行吞吐低于 Java 与 Go，管理端并发下瓶颈在 MySQL，可以接受。相对以前的 Java 微服务，两个 Python 进程更轻。

用户若继续从 Football 读，登录、选择器和业务外键都会绑在外部系统上。上线时导入并保留主键后，历史外键与 IMS 用户一致，之后以 IMS 为准。

## 3. 工程约定

- 目录按域分包：`app/domains/auth`、`app/domains/sys` 及后续业务域。
- 接口字段 **camelCase**（Pydantic `serialization_alias`）。库列 **snake_case**。
- 响应 `{code,msg,data}`。分页 `pageNo` / `pageSize`，默认 1 / 10，最大 100。
- 主键创建后不可改，违反返回 **1211**。手机号列表脱敏。
- 空权限、`PENDING_CONFIG`、未登记表、非法数据范围返回 **1008**。跨租户与不存在对外都是 **1504**「资源不可用」。
- 本地登录失败 5 次锁定 15 分钟。访问令牌 2 小时，刷新令牌 7 天，同时会话最多 3 个。
- 每片交付：该片 CHECKLIST、P0 用例、Playwright 在 1440×900 与 390×844 各跑主路径。
- 计划 SSOT：`开发方案/IMS-Python完整开发计划-20261005.md`。

## 4. 明确不做

| 不做 | 说明 |
|------|------|
| Go / sqlc 作为 IMS 后端 | 历史设计稿保留，不开工 |
| 运行时 Football 用户接口 | `simple-list` 不进入登录与用户管理 |
| 芋道 / Spring / Java 微服务 | 继续否决 |
| 在本文发明新业务 API | 路径仍以各模块 API 契约为准 |

## 5. 冲突顺序

**本 ADR > ADR-IMS-002（仅前端与禁芋道条款）> 完整 PRD > 全局开发规范 > 页面规格 > 原型。**  
2026-10-05 之前的架构设计、骨架设计稿、验收策略里写 Go、sqlc、Football 读用户的段落，视为历史，实现以本 ADR 与 Python 开发计划为准。
