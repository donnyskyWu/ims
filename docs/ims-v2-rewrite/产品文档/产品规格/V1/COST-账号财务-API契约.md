# COST - 账号财务 API 契约（OPS 并入）

> **前缀（目标）**：`/admin-api/ims/cost`  
> **现网 OPS SSOT**：`/admin-api/ops/finance/*` · `/admin-api/ops/football-order/*`（见 `API-M5-财务管理.md` · wd 已检入 `football-front` / `football-backend-saas`）  
> **BR-302**：账号 ROI **营收**来自 Football 订单只读 WebAPI；**禁止** IMS/OPS JDBC 直连 pay 库。

---

## 1. 账号成本（COST-001）

| # | 方法 | IMS 路径 | OPS 下游 | 状态 |
|---|------|----------|----------|------|
| 1 | GET | `/cost/account/{accountId}` | `GET /ops/finance/cost/list` + 账号维度聚合 | ✅ |
| 2 | PUT | `/cost/account/{accountId}/purchase` | PURCHASE 单行（M5 + VA `handler_user_id`） | ✅ |
| 3 | POST/PUT/DELETE | `/cost/account/{accountId}/process` | `POST/PUT/DELETE /ops/finance/cost/*` | ✅ |

错误码：1231 账号不存在；1500～1504 全局。

---

## 2. Football 订单 WebAPI 盘点（COST-002 · 只读 · 2026-10-02）

> **用途**：账号 ROI / 订单归因 **营收侧**；与「场次利润」菜单（FIN V3）**分离**（BR-302）。

| # | 方法 | 路径 | 实现 | 状态 |
|---|------|------|------|------|
| F1 | GET | `/admin-api/ops/football-order/list` | `FootballOrderReadController.list` → Feign `PayOrderApi#pageForOps` · 表 **`pay_all_order`**（`FootballOrderListVO`） | ✅ 列表 |
| F2 | GET | `/admin-api/ops/football-order/{id}` | — | **无**（现网无详情 HTTP；列表行即 SSOT） |

**Query（F1）**：`startDate`、`endDate`（必填）· `authorId` · `status`（0 待支付 / 1 成功 / 2 失败 / 3 取消）· `pageNum` · `pageSize`

**Response `list[]` 字段**（对齐 `football-front/src/api/ops/football-order.ts` · Java `FootballOrderListVO`）：

| 字段 | 说明 |
|------|------|
| id | 订单 ID |
| orderNo | 订单号 |
| userId / authorId | 用户 / 作者 |
| amount / payAmount | 金额 / 实付 |
| status | 支付状态 |
| orderType | 0 方案 / 1 订阅 / 2 专栏 |
| payTime / createTime | 时间 |
| sourceTable | 固定 `pay_all_order` |

**权限**：`ops:order-attribution:list` 或 `ops:roi:list`（Controller `@PreAuthorize`）。

---

## 3. ROI 聚合（COST-002 · 账号粒度）

| # | 方法 | IMS 路径 | OPS 下游 | 说明 |
|---|------|----------|----------|------|
| R1 | GET | `/cost/roi` | `GET /ops/finance/roi/analysis` | 维度 + 分页；**内部**调 Football 订单日汇总（非 F1 全量拉取） |
| R2 | GET | — | `GET /ops/finance/roi/trend` | 趋势 |
| R3 | GET | — | `GET /ops/finance/roi/breakdown` | 成本结构 |
| R4 | POST | — | `POST /ops/finance/roi/export` | 导出 |

**Football 超时**：1232 营收源超时；前端展示「营收延迟」，**禁止**写 0 冒充。

---

## 4. 页面 ↔ API

| 页面 | 能力 | API |
|------|------|-----|
| P1 账号成本 | 采购 + 过程成本 CRUD | §1 |
| P2 账号 ROI | 汇总 ROI | §3 R1～R3 |
| P2 · 订单明细（可选 Tab） | 只读订单列表 | §2 F1（按 `authorId` + 日期窗） |
