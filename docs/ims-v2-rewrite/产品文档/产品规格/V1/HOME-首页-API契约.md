# HOME - 首页 API 契约（OPS 并入）

> `/admin-api/ims/home` ｜ 完整 PRD HOME-001

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/admin-api/ims/home/dashboard` | 仪表盘 |
| 2 | GET | `/admin-api/ims/home/todos` | 待办列表 |
| 3 | GET | `/admin-api/ims/home/shortcuts` | 快捷入口 |

工作台接口仍见 `AUTH-权限管理-API契约.md`。

```typescript
// GET dashboard
interface HomeDashboardVO { /* 见页面规格 */ }
```

错误码：1201 无 IP 组权限；1202 日期跨度超 90 天。
