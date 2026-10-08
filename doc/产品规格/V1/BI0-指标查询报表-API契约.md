# BI0 - 指标查询报表 API 契约（OPS 并入）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET/POST/PUT | `/admin-api/ims/bi/metric` | 指标 CRUD |
| 2 | GET | `/bi/metric/{id}/analyze` | 指标分析 |
| 3 | GET | `/bi/report/{code}` | 标准报表 `code` 枚举 8 张 |
| 4 | GET/POST/PUT | `/bi/query` | 自定义查询 |
| 5 | POST | `/bi/query/{id}/run` | 执行 |
| 6 | PUT | `/bi/query/{id}/publish` | 发布 |
| 8 | GET/PUT | `/bi/metadata` | 元数据实体/字段（原 `/oa/metadata`，错误码 1261） |

错误码：1261 实体未映射；1262 查询超时走异步导出。

---

## OPS runtime 对照（2026-10-02 · 非 IMS canonical）

| 能力 | 现网 OPS 路径（`admin-api/ops`） | Controller | 前端 |
|------|----------------------------------|------------|------|
| 指标 CRUD/预览 | `/metric/list` · `/create` · `/update` · `DELETE /{id}` · `/preview` | `MetricController` | `api/ops/metric.ts` |
| 自定义查询 | `/query/list` · `/create` · `/update` · `/preview` · `POST /{id}/execute` · `POST /{id}/publish` | `CustomQueryController` | `api/ops/custom-query.ts` |
| 标准报表 | `/report/unified-account/list` 等 8 组（见 API-M6 §2） | `ReportController` | `api/ops/report.ts` |
| 大屏 | `/dashboard-config/list` · `/dashboard/*` | `DashboardConfigController` · `DashboardController` | `api/ops/dashboard.ts` |

页面 SSOT：`analysis/DataReport.vue`（报表中心）· `MetricManage.vue` · `CustomQuery.vue` · `screen/ScreenConfig.vue`。
