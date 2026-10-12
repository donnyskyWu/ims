# ADR-IMS-001 切流：共用 OPS 业务库 + Football HTTP + 停 OPS

> 状态：已确认（2026-09-29，含切流口径修正）  
> 完整 PRD：v2.6  
> 技术栈：[ADR-IMS-002-技术栈Go与轻量Vue.md](ADR-IMS-002-技术栈Go与轻量Vue.md)  
> 并入 UX：[ADR-IMS-003-OPS并入交互以OPS-UX为准.md](ADR-IMS-003-OPS并入交互以OPS-UX为准.md)

## 5. 开工冻结（2026-09-29 产品确认）

| # | 结论 |
|---|------|
| V1 范围 | **完整做完**：SYS/SSO、钉钉组织同步、主数据、IP 组、COST、内容全链路、采集监测、指标/HOME、LIVE、Football 方案 HTTP |
| AUTH-002 | **IMS 自建**钉钉通讯录同步（事件+对账），不依赖 Football 组织同步产品化 |
| SSO 对用户 | **必须绑定手机**；用 `mobile` 对上 `system_users.id`（可辅以 dingtalk_user_id） |
| `oa_*` 加列 | IMS 出兼容脚本，**人工运维窗口**执行；切流前 OPS 回归 |
| 财务入口 | **两个菜单**：账号 ROI（订单 `authorId`）与场次利润（FIN，V3 先行时再亮场次侧） |
| 技术栈 | **Go API + Go Worker + sqlc**；前端 Vue3 Vite 轻量壳。**不用芋道/Spring**。见 ADR-IMS-002 |
| OPS 并入 UX | **交互以现网 OPS UX/PRD 为准**；完整 HTML 原型对 BI0/CONTENT/COLLECT **不作实现蓝本**。见 ADR-IMS-003 |

登录仍 IMS 自建钉钉 SSO，不复用 Football 社交登录。

## 1. 决策

**IMS 是独立应用（独立进程、独立网关 `/admin-api/ims/`），业务数据不搬库。**

- **现在**：OPS 在生产运行；Football 继续运行。  
- **目标**：IMS 验收通过后 **直接切到 IMS，停用 OPS**。**没有**「IMS 与 OPS 长期双写同一行」的阶段。  
- **Football 长期保留**：C 端 / 方案 / 订单 / 比赛；IMS **只 HTTP**，禁止 JDBC/`@DS`/Feign 作为目标态（实现上复用现网已验证的 **同一 HTTP/RPC 路径**，用 `FootballWebApiClient` 封装，不散落 URL）。

## 2. 数据

| 数据 | 切流后 |
|------|--------|
| `oa_*` 业务表 | IMS 直连现网 OPS 库，**只加列不删列** |
| 运营用户主键 | **Football `system_users.id`**（ADR-056）；`oa_*` 人员 FK 不变 |
| 登录 | **IMS 自建钉钉 SSO**（AUTH-001），发 IMS Token。**不**走 Football `social-login`。换票后按 `dingtalk_user_id` / `mobile` HTTP 对上 `system_users.id` |
| 角色/菜单/字典/参数 | IMS 自管（切流后 OPS 系统页下线）；业务 dictValue 兼容现网 |
| 方案 | HTTP 写 member `author_article`（见 WebAPI 对照） |
| 订单 ROI | HTTP `page-for-ops`，维度 **Football `authorId`** |
| 选赛 | HTTP `GET /admin-api/match/jc-match/list-by-date`（现网 MatchProxy 同源） |

## 3. 切流

```
OPS 生产运行（现状）
    → IMS 对接同一 oa_* + Football HTTP，验收主路径
    → 切网关/菜单到 IMS，停 OPS 进程与调度
    → Football 不变
```

切流前加列必须兼容仍在跑的 OPS。切流后只 IMS 写 `oa_*`。不处理「两边抢同一行」。

## 4. 对旧表述

- 「长期双轨两套闭环同时写」→ **作废**。  
- 「再复制 OPS 库迁数」→ **作废**。  
- 「IMS 自建另一套用户主键」→ **作废**；主键 = `system_users.id`。
