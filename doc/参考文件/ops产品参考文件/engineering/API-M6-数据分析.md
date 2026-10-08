# API-M6-数据分析

> **版本**：v1.1 | 2026-06-12 | 2026-10-02
> **关联 PRD**：[`PRD-M6-数据分析.md`](../product/PRD-M6-数据分析.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 指标 API

### 1.1 GET `/admin-api/ops/metric/list`

| 参数 | 字典 |
|------|------|
| metricType | `dict_perf_metric_type` |

### 1.2 POST `/admin-api/ops/metric/create`

```json
{
  "metricName": "推文发布数",
  "metricCode": "ARTICLE_PUBLISH_COUNT",
  "metricFormula": "SELECT COUNT(*) FROM oa_content WHERE content_type='ARTICLE'",
  "dataSource": "oa_content",
  "metricType": "BASIC",
  "unit": "篇",
  "description": "..."
}
```

**校验**：
- `metricName` `@NotBlank`
- `metricCode` 英文+下划线+唯一
- `metricType` `@InDict(type="dict_perf_metric_type")`

### 1.3 PUT `/admin-api/ops/metric/update`

### 1.4 DELETE `/admin-api/ops/metric/{id}`

**业务**：被引用 → 错误码 1502

### 1.5 POST `/admin-api/ops/metric/preview`（实现 2026-06-11）

校验并试跑指标 SQL（只读 SELECT，经 `SqlSafetySupport` 白名单校验）。

**请求** `MetricPreviewReq`：

```json
{
  "metricFormula": "SELECT COUNT(*) AS cnt FROM oa_content WHERE tenant_id = ?"
}
```

**响应** `MetricPreviewVO`：

```json
{
  "rows": [{ "cnt": 1234 }]
}
```

（最多返回 20 行；SQL 无 `LIMIT` 时自动追加 `LIMIT 20`）

**说明**：

- 原 PRD 未定义预览端点；本期实现后补登本 API 规格
- `metric_formula` / `data_source` 持久化字段见 `V40__metric_formula_datasource.sql`
- 前端 `MetricBuilder`（`metricSchema.ts`）支持数据源、计算方式、group by、joins、filters 生成 SQL；`COMPOSITE` 类型除外

---

## 2. 报表 API（8 张）

### 2.1 全平台账号视图

- `GET /admin-api/ops/report/unified-account/list`
- `GET /admin-api/ops/report/unified-account/stats`
- `POST /admin-api/ops/report/unified-account/export`

### 2.2 账号状态监控

- `GET /admin-api/ops/report/account-status/trend`
- `GET /admin-api/ops/report/account-status/summary`
- `GET /admin-api/ops/report/account-status/log`
- `POST /admin-api/ops/report/account-status/export`

### 2.3 短视频产出

- `GET /admin-api/ops/report/video-output/list`
- `GET /admin-api/ops/report/video-output/trend`
- `GET /admin-api/ops/report/video-output/ranking`
- `POST /admin-api/ops/report/video-output/export`

### 2.4 直播时长（S-tier · 2026-08-26）

- `GET /admin-api/ops/report/live-duration/list`
- `GET /admin-api/ops/report/live-duration/trend`
- `POST /admin-api/ops/report/live-duration/export`（stub export job；前端用 list 分页拉全量 Excel）

**数据源**：Feign `LiveRoomApi.getLiveRoomCount(authorId, dateTime[])`；作者范围来自 `oa_ip_group_anchor_rel`（`ipGroupId` 可选）。

**list 请求参数**：`ipGroupId`、`startDate`、`endDate`、`pageNum`、`pageSize`

**list 响应行**（snake_case）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `author_id` | Long | 作者 ID |
| `author_name` | String | member 昵称 |
| `session_count` | Long | 场次 |
| `total_duration` | Decimal | 总时长（**小时**，1 位小数） |
| `avg_duration` | Decimal | 均时长（**小时**） |
| `date` | Date | 区间结束日 |

**trend 响应点**：`date` / `stat_date`、`session_count`、`total_duration`（小时）

**v1 不含**：`peak_viewers`（后端占位 `"-"`，前端不展示）

### 2.5 账号成本分摊

- `GET /admin-api/ops/report/cost-allocation/list`
- `POST /admin-api/ops/report/cost-allocation/export`

### 2.6 ROI 分析报表

- `GET /admin-api/ops/report/roi/list`
- `POST /admin-api/ops/report/roi/export`

### 2.7 IP 团队人员配置

- `GET /admin-api/ops/report/team-config/list`

### 2.8 账号异常预警

- `GET /admin-api/ops/report/account-alert/list`
- `POST /admin-api/ops/report/account-alert/export`

**通用请求参数**：

| 参数 | 类型 | 字典 |
|------|------|------|
| ipGroupId | Long | - |
| accountId | Long | - |
| platformType | String | `dict_platform_type` |
| startDate / endDate | Date | - |
| timeDimension | String | 固定 DAY/WEEK/MONTH |

**响应字段**：列表/统计 VO 使用 **snake_case** 键名（`ReportServiceImpl` + `reportField()`）；前端 `DictLabel` 渲染枚举。

**ROI 维度**：`dict_roi_dimension`（V42）。

---

## 3. 漏斗 API

### 3.1 GET `/admin-api/ops/funnel/list`

### 3.2 POST `/admin-api/ops/funnel/create`

```json
{
  "funnelName": "我的漏斗",
  "funnelType": "CUSTOM",
  "steps": [
    {"stepOrder": 1, "metricId": 1, "metricCode": "ARTICLE_PUBLISH_COUNT"},
    {"stepOrder": 2, "metricId": 2, "metricCode": "FANS_GROWTH"}
  ]
}
```

**说明**：自定义漏斗步骤绑定 **已定义指标**（`oa_metric`），非预设 eventCode。种子步骤见 V45。

**校验**：
- `funnelType` `@InDict(type="dict_funnel_type")`

### 3.3 GET `/admin-api/ops/funnel/{id}/data`

**响应**：

```json
{
  "funnelId": 1,
  "steps": [
    {"stepOrder": 1, "name": "曝光", "count": 10000, "conversionRate": 100.0},
    {"stepOrder": 2, "name": "关注", "count": 3000, "conversionRate": 30.0},
    {"stepOrder": 3, "name": "二次访问", "count": 800, "conversionRate": 8.0}
  ]
}
```

### 3.4 POST `/admin-api/ops/funnel/export`

---

## 4. 自定义查询 API

### 4.1 GET `/admin-api/ops/query/list`

| 参数 | 字典 |
|------|------|
| status | `dict_query_status` |

### 4.2 POST `/admin-api/ops/query/preview`（实现 2026-06-11）

试跑 QueryBuilder 生成的 SQL，不落库。

**请求**：

```json
{
  "sqlText": "SELECT ...",
  "paramsJson": "{\"tables\":[...],\"filters\":[...]}"
}
```

**响应**：`{ "columns": [...], "rows": [...] }`（列名可映射中文 label）

### 4.3 POST `/admin-api/ops/query/create`

```json
{
  "queryName": "近 30 天抖音粉丝增长",
  "status": "DRAFT",
  "sqlText": "SELECT date, count FROM ...",
  "paramsJson": "{...}"
}
```

**校验**：
- `status` `@InDict(type="dict_query_status")`
- `sqlText` SQL 注入检查（`SqlSafetySupport`）

### 4.4 PUT `/admin-api/ops/query/update`

同 create 字段；更新已保存查询。

### 4.5 POST `/admin-api/ops/query/{id}/execute`

执行已保存查询，返回 columns + rows。

### 4.6 POST `/admin-api/ops/query/{id}/publish`

草稿 → 已发布。

---

## 5. 大屏 API

### 5.1 GET `/admin-api/ops/dashboard/{id}`

返回模板元数据（含 `layout` JSON 字符串）。

### 5.2 GET `/admin-api/ops/dashboard/{id}/data`（实现 2026-06-12）

按 layout 解析各 widget 并返回聚合数据。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `startDate` | Date (ISO) | 否 | 默认 `endDate - 6 天` |
| `endDate` | Date (ISO) | 否 | 默认当天 |
| `ipGroupId` | Long | 否 | 未传则不按 IP 组过滤 |
| `platformType` | String | 否 | `dict_platform_type`；未传则不按平台过滤 |

**响应** `DashboardDataVO`：

```json
{
  "dashboard": { "id": 98601, "dashboardName": "内部运营大屏", "layout": "..." },
  "widgets": [
    {
      "id": "k1",
      "type": "KPI",
      "title": "作品数",
      "payload": { "value": 1234 }
    }
  ]
}
```

**widget 数据规则**：

- `BUILTIN`：后端内置查询；`STAT` 类型忽略 `startDate`/`endDate`，固定按当天
- `METRIC` / `QUERY`：经 `DashboardSqlParamBinder.prepareSql` 绑定参数后执行
- 单 widget 失败时 `payload.error` 返回错误信息，不阻断整屏

### 5.3 layout_json / widget schema

`layout` 为 JSON 字符串，根结构：

```json
{
  "version": 1,
  "scope": "INTERNAL",
  "refreshSeconds": 60,
  "widgets": [ { "...": "..." } ]
}
```

**widget 公共字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 组件唯一 ID |
| `type` | string | `KPI` \| `STAT` \| `CHART` \| `LIST` |
| `title` | string | 展示标题 |
| `sourceType` | string | `BUILTIN` \| `METRIC` \| `QUERY` |
| `builtinKey` | string | BUILTIN 数据源键 |
| `metricId` | number | METRIC 时必填 |
| `queryId` | number | QUERY 时必填 |
| `globalFilter` | object | METRIC/QUERY 全局筛选映射（见下） |
| `filterBind` | object | **已废弃**；占位符 → 全局来源，后端兼容 |

**`globalFilter` 对象**（METRIC/QUERY）：

```json
{
  "dateField": "publish_time",
  "dateColumn": "t.publish_time",
  "dateFieldType": "datetime",
  "ipGroupField": "ip_group_id",
  "ipGroupColumn": "t.ip_group_id"
}
```

- `dateField` / `ipGroupField`：业务字段名（配置页下拉，来源 `metricSchema.ts`）
- `dateColumn` / `ipGroupColumn`：SQL 列表达式（前端解析写入，供后端注入 WHERE）
- `dateFieldType`：`date`（默认）或 `datetime`

**SQL 参数绑定**（`DashboardSqlParamBinder`）：

1. `:tenantId` → 当前租户（`TenantContextHolder`），**始终自动替换**
2. 若存在 `globalFilter`：按 `dateColumn` / `ipGroupColumn` 注入 AND/WHERE 条件
3. 若存在 `filterBind`：按「占位符 → 全局来源」映射替换（旧版兼容）
4. 若两者皆无：legacy 绑定 `:startDate`、`:endDate`、`:ipGroupId`、`:platformType` 等标准占位符

详见 [`ADR-015`](../adr/ADR-015-大屏全局筛选与layout-globalFilter.md)。

### 5.4 POST `/admin-api/ops/dashboard/create`

```json
{
  "dashboardName": "运营总览大屏",
  "dashboardType": "BUSINESS",
  "layout": "{\"version\":1,\"scope\":\"INTERNAL\",...}"
}
```

**校验**：
- `dashboardType` `@InDict(type="dict_dashboard_type")`

### 5.5 GET `/admin-api/ops/dashboard-config/list`

### 5.6 PUT `/admin-api/ops/dashboard-config/full-update`

更新模板元数据 + `layout_json`。

---

## 6. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500~1504 | 全局关联 |
| 1503 | 字典值不合法 |
| 2017 | SQL 注入风险 |
| 2018 | 公式语法错误 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

---

## 字典与数据安全（🔴 API 必含）

### 字典使用（dict-type）

| 字段 | dict-type | 取值约束 |
|------|-----------|----------|
| report_dim | `dict_report_dim` | 字典合法值，错误码 1503 |
| metric_type | `dict_metric_type` | 字典合法值，错误码 1503 |
| export_format | `dict_export_format` | 字典合法值，错误码 1503 |
| time_range | `dict_time_range` | 字典合法值，错误码 1503 |

### 数据安全

- **脱敏**：`导出报表中的姓名、手机号` 在 API 响应中按权限脱敏（前端展示如 `138****1234`）
- **加密**：所有凭证字段在数据库中以 **AES-256** 加密存储（key 由配置中心注入）
- **日志**：所有写操作记录 `sys_audit_log`（含 operatorId / operation / before / after）
- **传输**：HTTPS + JWT；敏感字段二次加密（前端公钥 + 后端私钥）

详见 [`GLOBAL-CONVENTIONS.md § 5`](./GLOBAL-CONVENTIONS.md) (数据安全)

---

## 字段字典映射表（🔴 API 必含）

下表列出 数据分析 模块所有需要走数据字典的字段。前端使用 `<DictSelect dict-type="..." />` 组件，后端 `@InDict` 注解校验。

| 字段 | dict-type | 取值范围 | 错误码（不合法时） |
|------|-----------|----------|--------------------|
| `reportType` | `dict_report_type` | 日报/周报/月报/自定义 | 1503 |
| `dim` | `dict_report_dim` | 平台/IP组/作者/时间 | 1503 |
| `metric` | `dict_metric_type` | 浏览/点赞/评论/转化 | 1503 |
| `exportFormat` | `dict_export_format` | Excel/CSV/PDF | 1503 |
| `timeRange` | `dict_time_range` | 今日/本周/本月/自定义 | 1503 |

### 使用规范

1. **前端**：`<DictSelect v-model="form.reportType" dict-type="dict_report_type" />`
2. **后端**：`@InDict("dict_report_type") private String reportType;`
3. **字典维护**：在 M8 配置管理模块维护
4. **错误码**：字典值不在范围内 → 1503

详见 [`GLOBAL-CONVENTIONS.md § 2`](./GLOBAL-CONVENTIONS.md) (字典)
