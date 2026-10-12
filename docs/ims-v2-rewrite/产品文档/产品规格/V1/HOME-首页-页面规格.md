# HOME - 首页 / 工作台 页面规格（OPS 并入）

> 依据：《IMS完整产品需求文档》HOME-001、AUTH-004；OPS `PRD-M0-首页.md`。  
> API 前缀：`/admin-api/ims/home` ；工作台沿用 `/admin-api/ims/auth/workbench`。

## 0. 页面

| 页面 | 路由 | 功能点 |
|------|------|--------|
| P1 运营仪表盘 | `/ims/home` | HOME-001 |
| P2 个人工作台 | `/ims/workbench` | AUTH-004（原 V1 规格仍有效；本页补充 OPS 待办源） |

## P1 运营仪表盘

```
+------------------------------------------------------------------+
| IP组筛选 [树选择]     日期 [近7天]     [刷新]                      |
+------------------------------------------------------------------+
| KPI×4: 账号数 | 今日作品 | 待办任务 | 采集异常                      |
+------------------------------------------------------------------+
| 折线: 播放/互动     | 柱状: IP组产出                                 |
+------------------------------------------------------------------+
| 待办: 内容审核/工作任务/采集失败   快捷入口卡片（按权限）     |
+------------------------------------------------------------------+
```

### 类型

```typescript
interface HomeDashboardReq { ipGroupId?: string; dateFrom?: string; dateTo?: string; }
interface HomeDashboardVO {
  kpis: { key: string; label: string; value: string; wow?: string }[];
  todos: { type: string; title: string; bizId: string; url: string }[];
  shortcuts: { code: string; name: string; route: string }[];
}
```

### 规则

- 数据范围 BR-305；无 IP 组权限则筛选器仅可见授权节点。
- 待办聚合 IMS 内任务/审核/采集，**不请求 OPS**。
- KPI 采集类延迟展示「数据延迟」不得请求 Football 库。

## P2 工作台补充待办源

在原 AUTH-004 待办上增加：`WORK_TASK_CONFIRM`、`CONTENT_REVIEW`、`COLLECT_FAIL`、`ACCT_RETURN`。
