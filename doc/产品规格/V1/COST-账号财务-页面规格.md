# COST - 账号财务 页面规格（OPS M5 并入）

> 完整 PRD COST-001～002。场次利润见 V3 FIN 规格，**分开展示**。  
> 前缀：`/admin-api/ims/cost`

## 页面

| 页面 | 路由 | 功能点 |
|------|------|--------|
| P1 账号成本 | `/ims/cost/account` | COST-001 |
| P2 ROI 分析 | `/ims/cost/roi` | COST-002 |

## P1

账号选择器 → 采购成本（一条）+ 过程成本明细（多条：类型/金额/周期/经办人）。

## P2

维度：公司 / IP 组 / 账号 / 人员。列：成本、营收、ROI。页头注明 **「账号粒度；营收来自 Football 订单 WebAPI 日汇总」**。

**订单只读（盘点 2026-10-02）**：`GET /admin-api/ops/football-order/list`（`pay_all_order` · 无 `{id}` 详情 HTTP）。表格列对齐：`orderNo`、`payAmount`、`status`、`orderType`、`payTime`、`authorId`。ROI 汇总走 `GET /ops/finance/roi/analysis`，**非**全表订单 join。

## 规则

- 成本表同构迁入作期初。
- 营收禁止 JDBC 连 pay；Football 失败显示「营收延迟」不写 0。
- 与 FIN 看板入口分开，避免混读。
