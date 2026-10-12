# MON - 作品监测 API 契约（OPS 并入 · 内部 + 主题）

> 外部竞品 **作品/账号** 列表 API → 《COMP-竞品分析-API契约.md》（透传 OPS `/admin-api/oa/monitor/*`）。

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/admin-api/ims/monitor/internal/page` | 内部作品 |
| 2 | GET | `/admin-api/ims/monitor/ip-theme/page` | IP 主题聚合 |
| 3 | GET | `/admin-api/ims/monitor/industry/page` | 行业聚合 |

错误码：1251 阈值未配置（竞品分析只读引用 COLLECT 阈值）。
