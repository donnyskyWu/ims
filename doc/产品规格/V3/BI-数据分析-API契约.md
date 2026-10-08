# BI - 数据分析 API 契约

> **模块范围**：17 数据分析（V3 增量，第 29~36 周，P2）——BI-001 自助报表设计、BI-002 多维查询下钻、BI-003 看板订阅分享。**补齐类**：指标管理/自定义查询已完成（不重复建设），本次仅补齐自助报表/下钻/订阅分享能力。
> **权威依据**：《IMS第三期PRD-V3.md》5.7~5.9；BR-204、BR-211、BR-212；V3-B1~B6（自助报表引擎）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章（BI 域 1191~1197，共段 1191~1199 中 EFF 使用 1198/1199）；字段 camelCase（`report_no → reportNo`、`layout_config → layoutConfig`）；周次波浪号格式。**关键口径**：**长查询异步规范（V3-B6）——单报表查询并发上限 10/用户；超 10 秒未完成的查询自动转异步任务（结果 落服务端文件目录 + 通知领取）**；查询性能 BR-204（10 万行级 < 30 秒）；权限继承 BR-212（行级双重过滤，分享不突破原权限）。
> **本次修订（v2.6.27 · 2026-10-04 · 走查 #21）**：**发布链路补 ① 发布去向**（报表中心 / 单独发布为菜单）——`BiReportPublishReq.dest` + `menu{}`，新增端点 **S10 `/bi/report/{id}/publish/menu`**；报表域 IA 重构（报表管理+设计合并单菜单、大屏归为报表类型、报表设计转隐藏路由）不影响端点路径。**v2.6.26**：报表设计器升级为**三栏自由拖拽**（组件模型 `BiCompDef` / `layoutMode` FREE·GRID / 组件级数据源与动态参数）；新增**发布链路**（发布链接密码+有效期+版本快照）、**模板导入导出**、**分类管理**。新增端点归 **§2.4 实现级补充端点**，已提请 PRD 补列；主表（20 接口）不变。详见《BI-数据分析-页面规格》§10/§11。

---

## 1. API 总览表（共 20 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/bi/report/datasets` | 可用数据集列表（指标库/自定义查询/聚合层） | R1/R3/R4/R9（全量）/R5/R6（本域） |
| 2 | POST | `/admin-api/ims/bi/report` | 创建报表 | R1/R3/R4/R9/R5/R6（本域数据集） |
| 3 | GET | `/admin-api/ims/bi/report/list` | 报表列表（分页） | 同上 |
| 4 | PUT | `/admin-api/ims/bi/report/{id}` | 编辑报表（生成新版本） | 创建者本人/R1 |
| 5 | DELETE | `/admin-api/ims/bi/report/{id}` | 删除报表 | R1/创建者本人 |
| 6 | POST | `/admin-api/ims/bi/report/query` | 报表数据查询（BR-204 性能 + V3-B6 异步） | 报表可见者（BR-212） |
| 7 | PUT | `/admin-api/ims/bi/report/{id}/share` | 分享范围设置 | 创建者/R1 |
| 8 | GET | `/admin-api/ims/bi/report/async/{taskId}` | 异步查询任务结果领取 | 任务发起人 |
| 9 | GET | `/admin-api/ims/bi/query/dimension-tree` | 维度层级定义（下钻链） | 报表查看者 |
| 10 | POST | `/admin-api/ims/bi/query/drill` | 下钻/上卷查询 | 报表查看者（BR-212） |
| 11 | POST | `/admin-api/ims/bi/query/cell-drill` | 单元格穿透下钻 | 同上 |
| 12 | GET | `/admin-api/ims/bi/query/export` | 下钻结果导出 | 同上 |
| 13 | GET | `/admin-api/ims/bi/query/perf-stats` | 查询性能统计（BR-204 监控） | R1/R9 |
| 14 | POST | `/admin-api/ims/bi/subscribe` | 创建订阅（日/周/月） | R1~R9（按数据权限，R10 不开放） |
| 15 | GET | `/admin-api/ims/bi/subscribe/list` | 我的订阅列表 | 订阅人本人 |
| 16 | PUT | `/admin-api/ims/bi/subscribe/{id}` | 修改/暂停订阅 | 订阅人本人 |
| 17 | DELETE | `/admin-api/ims/bi/subscribe/{id}` | 取消订阅 | 订阅人本人/R1 |
| 18 | POST | `/admin-api/ims/bi/subscribe/share-link` | 生成分享链接（敏感数据走审批） | 创建者/R4 |
| 19 | GET | `/admin-api/ims/bi/subscribe/snapshot/{id}` | 快照查看（回溯推送时点数据） | 订阅人/分享接收人 |
| 20 | PUT | `/admin-api/ims/bi/subscribe/share-approval/{linkId}` | 分享审批（敏感数据，R4） | R4 |

---

## 2. 接口明细

### 2.1 自助报表设计（BI-001）

#### 2.1.1 GET /admin-api/ims/bi/report/datasets — 可用数据集列表

**响应** `data`：

```typescript
interface BiDatasetVO {
  id: number;
  datasetName: string;
  /** 数据集来源：已建指标库 / 自定义查询 / V3 聚合层宽表（V3-B1 元数据驱动） */
  datasetSource: 'METRIC_LIB' | 'CUSTOM_QUERY' | 'DWS_AGGREGATION';
  /** 字段元数据（维度/指标/类型） */
  fields: Array<{
    fieldKey: string;
    fieldLabel: string;
    fieldType: 'DIMENSION' | 'METRIC';
    dataType: 'STRING' | 'NUMBER' | 'DATE';
    /** 指标口径引用（BIR-R3：不允许自造口径，统一引用指标管理） */
    metricCode?: string;
  }>;
  /** 数据新鲜度（Redis 缓存 TTL 依据，V3-B3 默认 15 分钟） */
  freshnessMinutes: number;
  rowCountEstimate: number;      // 行数估计（前端性能预警提示）
}
```

#### 2.1.2 POST /admin-api/ims/bi/report — 创建报表

**请求**：

```typescript
interface BiReportCreateReq {
  reportName: string;
  datasetId: number;
  /** v2.6.26：报表类型 + 布局模式（FREE 自由拖拽 / GRID 四区派生） */
  reportType?: 'REPORT' | 'DASHBOARD';
  layoutMode?: 'GRID' | 'FREE';
  /** v2.6.26：自由布局组件集合（layoutMode=FREE 时权威） */
  components?: BiCompDef[];
  /** 行/列/值/筛选拖拽配置与图表定义（V3-B1 元数据驱动，新增报表零代码；GRID 模式保留，FREE 下由组件派生） */
  layoutConfig: {
    rows: Array<{ fieldKey: string }>;
    columns: Array<{ fieldKey: string }>;
    values: Array<{ fieldKey: string; aggType: 'SUM' | 'AVG' | 'COUNT' | 'MAX' | 'MIN' }>;
    filters: Array<{ fieldKey: string; operator: 'EQ' | 'IN' | 'RANGE'; value: unknown }>;
    chartType: 'TABLE' | 'BAR' | 'LINE' | 'PIE';
  };
  /** 计算字段：聚合与简单表达式（加减乘除/占比） */
  calcFields?: Array<{
    fieldKey: string;
    fieldLabel: string;
    expression: string;          // 如 '(SUM(gmv) - SUM(cost)) / SUM(gmv)'
  }>;
  /** v2.6.26：分类与标签 */
  category?: string;
  tags?: string[];
  shareScope: 'PRIVATE' | 'SPECIFIED' | 'ALL';      // 0 私有/1 指定人/2 全员（受 BR-212 限制）
  specifiedUserIds?: number[];   // SPECIFIED 时必填
}

/** v2.6.26：画布组件定义（对齐 DW dw_report_component，落库为 ims_ 前缀新表） */
interface BiCompDef {
  compId: string;                // 画布内唯一，用于联动引用 ${compId.field}
  compType: 'KPI' | 'BAR' | 'LINE' | 'PIE' | 'DONUT' | 'RADAR' | 'FUNNEL' | 'SCATTER'
          | 'TABLE' | 'DETAIL_TABLE' | 'RICH_TEXT'      // 图表 11
          | 'DATE_RANGE' | 'SELECT_SINGLE' | 'SELECT_MULTI' | 'TEXT_INPUT' | 'NUMBER_RANGE'  // 查询条件 5
          | 'GROUP' | 'CARD' | 'TAB'                    // 容器 3
          | 'BUTTON' | 'LINK' | 'TRIGGER';              // 交互 3
  compGroup: 'CHART' | 'FILTER' | 'CONTAINER' | 'ACTION';
  title: string;
  /** 绝对定位（px）与尺寸；最小 80×80，栅格吸附 40px */
  position: { x: number; y: number; w: number; h: number };
  style?: Record<string, string | number>;
  /** 组件数据源（§9.9.3） */
  datasourceConfig?: {
    source: 'DATASET_FIELD' | 'REPORT_DATA' | 'STATIC' | 'COMP_OUTPUT' | 'CALC';
    fieldKey?: string;
    aggType?: 'SUM' | 'AVG' | 'COUNT' | 'MAX' | 'MIN';
    /** 动态参数：${compId.field} */
    dynamicParams?: Array<{ paramName: string; expression: string }>;
  };
  outputParams?: string[];       // 对外输出（供下游引用）
  /** 联动 / 跳转 / 刷新（§9.9.4；联动成环须拒绝） */
  interactionConfig?: {
    linkTo?: Array<{ targetCompId: string; triggerType: 'CLICK' | 'SELECT' | 'RANGE' }>;
    jumpTo?: { type: 'REPORT' | 'DRILL_DETAIL' | 'MODULE_DETAIL' | 'EXTERNAL'; target: string; paramMap?: Record<string, string> };
    refreshInterval?: number;    // 秒，最小 30
  };
  zIndex: number;
}
```

**响应** `data`：

```typescript
interface BiReportVO {
  id: number;
  reportNo: string;              // BR+日期+流水
  reportName: string;
  datasetId: number;
  datasetName: string;
  /** v2.6.26 */
  reportType?: 'REPORT' | 'DASHBOARD';
  layoutMode?: 'GRID' | 'FREE';
  components?: BiCompDef[];
  category?: string;
  tags?: string[];
  thumbnail?: string;            // 自动缩略图（发布时生成）
  layoutConfig: BiReportCreateReq['layoutConfig'];
  calcFields: BiReportCreateReq['calcFields'];
  version: number;               // 修改生成新版本，分享链接不变（BIR-R4）
  ownerUserId: number;
  ownerName: string;
  shareScope: 'PRIVATE' | 'SPECIFIED' | 'ALL';
  status: 'DRAFT' | 'PUBLISHED';
  /** 竞品资产引用计数联动（BR-214，引用 COMP 档案时报表侧留痕） */
  compAssetRefs?: string[];
  createdAt: string;
}
```

**错误码**：1191（数据集字段引用非法——字段不存在或 DIMENSION/METRIC 用法错误）、1192（计算字段表达式非法——仅支持白名单聚合函数与四则运算）、1001（参数校验）；**v2.6.26 新增校验（均走 1001 参数校验 + 具体 msg，不新增错误码，避免与 1195 下钻路径非法冲突）**：`组件联动成环（A→B→C→A）`、`组件尺寸 <80×80`、`刷新间隔 <30s`、`外部链接域名非白名单`、`有效期越界（7~30 天）`。

#### 2.1.3 GET /admin-api/ims/bi/report/list — 报表列表（分页）

**请求**（Query）：`PageParam` + `{ reportName?: string; datasetId?: number; ownerUserId?: number; shareScope?: string }` → **响应** `data`：`PageResult<BiReportVO>`（按 BR-212 可见性过滤：创建者/指定人/全员）。

#### 2.1.4 PUT /admin-api/ims/bi/report/{id} — 编辑报表（新版本）

**请求**：`BiReportCreateReq` → **响应** `data`：`BiReportVO`（`version` 自增，分享链接指向最新发布版本）。

#### 2.1.5 DELETE /admin-api/ims/bi/report/{id} — 删除报表

**响应**：`data: null`。有活跃订阅时提示先取消订阅（软校验）。

#### 2.1.6 POST /admin-api/ims/bi/report/query — 报表数据查询

**请求**：

```typescript
interface BiReportQueryReq {
  reportId: number;
  version?: number;
  /** 临时筛选覆盖（预览态） */
  filterOverrides?: BiReportCreateReq['layoutConfig']['filters'];
  pageNo?: number;
  pageSize?: number;
}
```

**响应** `data`（同步路径）：

```typescript
interface BiReportQueryResp {
  /** 同步完成（< 10 秒） */
  queryMode: 'SYNC';
  costMs: number;                // BR-204 监控埋点
  columns: Array<{ fieldKey: string; fieldLabel: string; dataType: string }>;
  rows: Array<Record<string, string | number | null>>;
  total: number;
  /** 查询结果 Redis 缓存命中标记（V3-B3：TTL = 数据集新鲜度，默认 15 分钟） */
  cacheHit: boolean;
  dataAsOf: string;
}
```

**响应** `data`（异步路径，V3-B6：**超 10 秒未完成自动转异步任务**）：

```typescript
interface BiReportQueryAsyncResp {
  queryMode: 'ASYNC';
  asyncTaskId: string;
  message: string;               // '查询超时转异步，完成后通知领取'
  /** 领取轮询端点 */
  resultUrl: string;             // GET /bi/report/async/{taskId}
}
```

**错误码**：1193（并发超限——单报表查询并发上限 10/用户，V3-B6）、1194（查询超 30 秒强制终止——BR-204 超时提示缩小范围）、1008（无该报表查看权限，BR-212）。

**权限约束**：查询结果按创建者与查看者角色数据权限**双重过滤**（行级交集，BIR-R1/BR-212）；R9 成本类指标脱敏。

#### 2.1.7 PUT /admin-api/ims/bi/report/{id}/share — 分享范围设置

**请求**：`{ shareScope: 'PRIVATE' | 'SPECIFIED' | 'ALL'; specifiedUserIds?: number[] }` → **响应**：`data: null`。分享不突破原权限（BR-212）。

#### 2.1.8 GET /admin-api/ims/bi/report/async/{taskId} — 异步任务结果领取（实现级补充端点，V3-B6 异步查询配套，已提请 PRD 补列）

**响应** `data`：

```typescript
interface BiReportAsyncResultResp {
  asyncTaskId: string;
  taskStatus: 'RUNNING' | 'COMPLETED' | 'FAILED';
  /** COMPLETED：结果 落服务端文件目录（V3-B6），60 秒签名下载 URL */
  downloadUrl?: string;
  /** 小结果集可直接回传 */
  inlineResult?: BiReportQueryResp;
  failReason?: string;
  notifiedAt?: string;           // 完成通知（钉钉工作通知 + 工作台）时间
}
```

### 2.2 多维查询下钻（BI-002）

#### 2.2.1 GET /admin-api/ims/bi/query/dimension-tree — 维度层级定义

**响应** `data`：

```typescript
interface BiDimensionTreeVO {
  /** 预定义维度层级链（V3-B4 下钻复用 dataset 元数据动态生成 SQL） */
  trees: Array<{
    treeName: string;
    levels: Array<{ level: number; dimensionKey: string; dimensionLabel: string }>;
  }>;
  // 示例：平台→账号→场次；部门→团队→人；年→月→日（DrillDimension）
}
```

#### 2.2.2 POST /admin-api/ims/bi/query/drill — 下钻/上卷查询

**请求**：

```typescript
interface BiDrillReq {
  reportId?: number;
  dashboardId?: number;          // 二选一
  drillPath: Array<string>;      // 维度层级序列（如 ['PLATFORM', 'ACCOUNT']）
  direction: 'DOWN' | 'UP';
  /** 下钻时维度组合过滤（上下文自动携带） */
  filterContext: Record<string, string | number>;
  pageNo?: number;
  pageSize?: number;
}
```

**响应** `data`：`BiReportQueryResp`（同 2.1.6 同步结构）。**SQL 白名单校验**（V3-B4：只能查登记过的 dataset）。

**错误码**：1195（下钻路径非法——超出预定义维度层级）、1194（超 30 秒终止）。

#### 2.2.3 POST /admin-api/ims/bi/query/cell-drill — 单元格穿透下钻

**请求**：

```typescript
interface BiCellDrillReq {
  reportId: number;
  /** 数值单元格的当前维度组合 */
  cellDimensions: Record<string, string | number>;
  /** 穿透目标：明细单据（BIQ-R3 跳转来源模块详情页，如场次 → V1 台账详情） */
  drillToDetail: boolean;
}
```

**响应** `data`：`{ jumpType: 'MODULE_DETAIL' | 'DC_TRACE'; jumpUrl: string; jumpParams: Record<string, string> }`（明细层跳转：场次 → V1 台账；穿透层跳转 → DC-001 链路，BIQ-R1 最深到场次/明细单据）。

#### 2.2.4 GET /admin-api/ims/bi/query/export — 下钻结果导出

**请求**（Query）：`{ reportId?: number; dashboardId?: number; drillPath?: string; filterContext?: string; format: 'XLSX' | 'CSV' }` → **响应** `data`：`{ downloadUrl: string; expiresIn: number }`。

#### 2.2.5 GET /admin-api/ims/bi/query/perf-stats — 查询性能统计

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ totalQueries: number; avgCostMs: number; p95CostMs: number; over30sCount: number; asyncConvertedCount: number; topSlowReports: Array<{ reportId: number; reportName: string; avgCostMs: number; queryCount: number }> }`（BR-204 监控 + V3-B6 异步转化统计）。

### 2.3 看板订阅分享（BI-003）

#### 2.3.1 POST /admin-api/ims/bi/subscribe — 创建订阅

**请求**：

```typescript
interface BiSubscribeCreateReq {
  targetType: 'REPORT' | 'DASHBOARD';    // 1 报表 / 2 看板
  targetId: number;
  period: 'DAILY' | 'WEEKLY' | 'MONTHLY';   // BR-211 订阅周期
  pushTime: string;              // 推送时刻（如 '09:00'）
}
```

**响应** `data`：`{ id: number; nextPushAt: string }`（推送 = 钉钉工作通知 + 工作台消息，附数据快照摘要与链接，BIS-R1/BR-211；推送任务纳入 V2 集群化调度，失败重试 3 次，V3-B5）。

#### 2.3.2 GET /admin-api/ims/bi/subscribe/list — 我的订阅列表

**响应** `data`：`PageResult<{ id: number; targetType: 'REPORT' | 'DASHBOARD'; targetName: string; period: 'DAILY' | 'WEEKLY' | 'MONTHLY'; pushTime: string; status: 'ACTIVE' | 'PAUSED'; nextPushAt: string; lastPushAt?: string; lastPushResult?: 'SUCCESS' | 'FAILED_RESENT' }>`（订阅推送失败自动补发 1 次并记录，BIS-R4）。

#### 2.3.3 PUT /admin-api/ims/bi/subscribe/{id} — 修改/暂停订阅

**请求**：`{ period?: 'DAILY' | 'WEEKLY' | 'MONTHLY'; pushTime?: string; status?: 'ACTIVE' | 'PAUSED' }` → **响应**：`data: null`。

#### 2.3.4 DELETE /admin-api/ims/bi/subscribe/{id} — 取消订阅

**响应**：`data: null`。

#### 2.3.5 POST /admin-api/ims/bi/subscribe/share-link — 生成分享链接

**请求**：

```typescript
interface BiShareLinkReq {
  targetType: 'REPORT' | 'DASHBOARD';
  targetId: number;
  /** 含成本/利润数据须 R4 审批（BIS-R3） */
  expireDays: number;            // 默认 7，最长 30
}
```

**响应** `data`：

```typescript
interface BiShareLinkVO {
  linkId: number;
  linkToken: string;
  shareUrl: string;              // 免登录走 SSO 钉钉授权
  creatorUserId: number;
  expireAt: string;
  /** 审批状态：目标含成本/利润数据 → PENDING_APPROVAL（须 R4 审批后生效） */
  approvalStatus: 'NOT_REQUIRED' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED';
  /** R4 审批端点提示 */
  approvalEndpoint?: string;     // PUT /bi/subscribe/share-approval/{linkId}
  createdAt: string;
}
```

**错误码**：1196（敏感数据分享未审批不可用）、1197（分享有效期非法：7~30 天范围外）。

**权限约束**：分享链接不突破数据权限——打开后按查看者权限行级过滤（BIS-R2/BR-212）。

**审批端点（R4）**：`PUT /admin-api/ims/bi/subscribe/share-approval/{linkId}`，请求 `{ approve: boolean; remark?: string }` → `data: null`。

#### 2.3.6 GET /admin-api/ims/bi/subscribe/snapshot/{id} — 快照查看

**请求**（Path）：`id`（推送记录 ID）→ **响应** `data`：`{ pushAt: string; snapshotData: Array<Record<string, string | number | null>>; summaryText: string; targetName: string }`（推送时点数据快照存档，可回溯当时数据，BIS-R1）。

### 2.4 报表设计链路补充端点（v2.6.26 · 实现级，已提请 PRD 补列）

> **说明**：下列为 DW 借鉴落地（三栏拖拽 + 发布链路 + 模板）配套端点，**主表 20 接口不变**，本节作**实现级补充**登记。所有端点遵循同一响应包裹与错误码约定；落库为 `ims_` 前缀新表（IR-04）。

| # | 方法 | 路径 | 说明 | 权限 |
|---|------|------|------|------|
| S1 | POST | `/admin-api/ims/bi/report/{id}/publish` | 生成发布（**发布去向**/方式/可见范围/密码/有效期/快照版本）→ 返回 shareUrl + expireAt；去向=菜单时返回 menuId | 创建者/R1 |
| S2 | GET | `/admin-api/ims/bi/report/{id}/publish/list` | 发布记录列表（含访问次数/状态） | 创建者/R1 |
| S3 | PUT | `/admin-api/ims/bi/report/publish/{publishId}` | 重新配置发布（可见范围/密码/有效期/展示刷新） | 创建者/R1 |
| S4 | DELETE | `/admin-api/ims/bi/report/publish/{publishId}` | 发布链接失效（status→REVOKED） | 创建者/R1 |
| S5 | POST | `/admin-api/ims/bi/report/import` | 导入 JSON 模板（校验结构；数据源引用失效返回 warning 列表） | R1/R3/R4/R9/R5/R6 |
| S6 | GET | `/admin-api/ims/bi/report/{id}/export` | 导出报表定义 JSON | 创建者/R1 |
| S7 | POST | `/admin-api/ims/bi/report/{id}/copy` | 复制报表（名称"副本"，version 重置） | 创建者/R1 |
| S8 | GET | `/admin-api/ims/bi/report/categories` | 报表分类树 | 报表可见者 |
| S9 | POST | `/admin-api/ims/bi/report/category` | 分类增删改名（非空删除阻断） | R1/创建者 |
| S10 | POST | `/admin-api/ims/bi/report/{id}/publish/menu` | **单独发布为菜单**（v2.6.27 · 写 `sys_menu` + `ims_report_menu`，含菜单名/父级/图标/排序/授权角色）→ 返回 menuId | R1/R5 |

**S1 请求**：

```typescript
interface BiReportPublishReq {
  dest: 'CENTER' | 'MENU';                 // v2.6.27 发布去向：报表中心 / 单独发布为菜单
  menu?: {                                 // dest=MENU 时必填（写 sys_menu + ims_report_menu）
    name: string;                          // 侧栏显示名，1~30 字
    parentId: number;                      // 父级菜单（数据报表 / 数据决策顶级 / 工作台）
    icon?: string;                         // chart / doc / spark / target
    orderNum?: number;                     // 排序
    roleIds?: number[];                    // 授权角色（决定谁能看到该菜单）
  };
  accessType: 'SHARE_LINK' | 'SSO_URL';   // iframe 为 non-goal
  shareScope: 'PRIVATE' | 'SPECIFIED' | 'ALL';
  passwordEnabled: boolean;
  password?: string;                       // ≥8 位；服务端加密存储
  expireDays: number;                      // 7~30，越界 1197
  device?: 'PC' | 'TV' | 'MOBILE';
  refreshInterval?: number;                // ≥30
  lockSnapshot?: boolean;                  // 锁定当前版本为发布快照
}
```

**S1 响应**：`BiReportPublishVO`（见页面规格 P3 §3；含 publishId/shareUrl/hasPassword/expireAt/snapshotVersion/visitCount/status/approvalStatus；`dest=MENU` 时含 menuId）。含成本/利润 → `approvalStatus=PENDING_APPROVAL`（BIS-R3，1196/1197）。**报表下线/删除（S4/删除报表）时菜单自动置灰**（`ims_report_menu` 关联解除，`sys_menu.status=DISABLED`）。

**S5 响应**：`{ reportId: number; warnings: Array<{ key: string; message: string }> }`（如 `{ key: 'custom_sql_1', message: '数据源需重新配置' }`）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**报表（BiReportVO.status）**：`DRAFT → PUBLISHED`（版本化递增，分享链接指向最新发布版本）。

**查询任务（BiReportQueryAsyncResp.taskStatus）**：`RUNNING → COMPLETED（结果 落服务端文件目录 + 通知领取）/ FAILED`。

**订阅（status）**：`ACTIVE ↔ PAUSED`（按 period 周期推送）。

**分享链接（approvalStatus）**：

```
NOT_REQUIRED（无敏感数据，直接生效）
PENDING_APPROVAL（含成本/利润）──R4 审批──▶ APPROVED（生效，7~30 天有效）
                     └──驳回──▶ REJECTED
APPROVED ──到期/手动失效──▶ EXPIRED
```

**发布记录（BiReportPublishVO.status · v2.6.26）**：`ACTIVE → EXPIRED（到期）/ REVOKED（手动失效）`；发布快照 `snapshotVersion` 锁定发布时点结构，报表后续改版不影响已发布链接内容（BIR-R4）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-204 | 10 万行级查询 < 30 秒（含聚合下钻） | 2.1.6 costMs / 2.2.5 |
| BR-211 | 订阅周期日/周/月；钉钉+工作台推送，快照留档 | 2.3.1 |
| BR-212 | 行级双重过滤（创建者∩查看者），分享不突破权限 | 2.1.6 / 2.1.7 / 2.3.5 |
| BIR-R1 | 查询结果按权限交集过滤 | 2.1.6 服务端 |
| BIR-R2 | 超 30 秒提示缩小范围 | 2.1.6 错误码 1194 |
| BIR-R3 | 字段引用已建指标口径，不自造 | 2.1.1 metricCode |
| BIR-R4 | 报表版本化，分享链接不变 | 2.1.4 |
| BIQ-R1 | 下钻最深到场次/明细单据（复用 DC 穿透） | 2.2.3 jumpType |
| BIQ-R2 | 下钻同受 BR-204 性能与 BR-212 权限约束 | 2.2.2 |
| BIQ-R3 | 明细层跳转来源模块详情页 | 2.2.3 jumpUrl |
| BIS-R1 | 订阅推送含摘要+链接，快照留档 | 2.3.1 / 2.3.6 |
| BIS-R2 | 分享打开后按查看者权限过滤 | 2.3.5 权限约束 |
| BIS-R3 | 敏感数据分享须 R4 审批，7~30 天有效 | 2.3.5 错误码 1196/1197 |
| BIS-R4 | 推送失败自动补发 1 次 | 2.3.2 lastPushResult |
| V3-B1 | 元数据驱动（dataset+维度指标+图表，零代码新增） | 2.1.1 / 2.1.2 |
| V3-B2 | 高频指标预计算入 DWS/ADS，命中优先 | 2.1.6 cacheHit |
| V3-B3 | Redis 缓存 TTL = 数据集新鲜度（15 分钟），定义变更主动失效 | 2.1.6 cacheHit |
| V3-B4 | 下钻动态生成 SQL + 白名单校验 | 2.2.2 |
| V3-B5 | 订阅推送纳入集群化调度，失败重试 3 次 | 2.3.1 |
| **V3-B6** | **并发上限 10/用户；超 10 秒自动转异步（落服务端文件目录+通知领取）** | 2.1.6 双响应结构 / 2.1.8 |
| 9.2 安全 | 报表设计/分享审批全量审计 | 全模块审计 |
| **DW-1**（三栏拖拽 4 类 21 组件） | 组件模型 + 布局模式 | 2.1.2 `components` / `layoutMode` |
| **DW-3**（联动成环拒绝） | 有向无环校验 | 2.1.2 组件 `interactionConfig.linkTo` + 1001（msg 提示成环） |
| **DW-4**（发布密码/有效期/快照） | **五段式**发布（v2.6.27 补 ① 发布去向） | 2.4 S1~S4 + S10 + 1196/1197 |
| **DW-5**（模板导入导出） | JSON 模板复用 | 2.4 S5/S6 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 自助报表设计器（数据集选择 → 拖拽画布） | 可用数据集列表加载（字段元数据） | GET /bi/report/datasets |
| 设计器-组件库/画布/图层（v2.6.26） | 组件增删拖动、图层选中、撤销 | 前端态（`components[]`，保存时随 2.1.2/2.1.4 提交） |
| 设计器-属性三区（基础/数据源/交互） | 组件级取数、动态参数、联动、跳转、刷新 | POST /bi/report/query（携带 compId） |
| 设计器-保存并发布（生成缩略图 + 版本自增） | 创建/编辑报表（计算字段编辑器） | POST /bi/report、PUT /bi/report/{id} |
| 报表管理页（分类树 + 卡片/列表双视图） | 报表列表查询（分类/类型筛选） | GET /bi/report/list |
| 报表管理页 | 分类树加载 / 分类维护 | GET /bi/report/categories、POST /bi/report/category（**2.4 S8/S9**） |
| 报表行操作 | 复制 / 导入模板 / 导出模板 JSON | POST /bi/report/{id}/copy、POST /bi/report/import、GET /bi/report/{id}/export（**2.4 S7/S5/S6**） |
| 报表行操作 | 删除（有订阅提示）/ 分享范围设置 | DELETE /bi/report/{id}、PUT /bi/report/{id}/share |
| 报表预览区 / 组件状态条 | 实时预览查询（超 10 秒转异步提示 + 任务领取） | POST /bi/report/query、GET /bi/report/async/{taskId} |
| 工作台-异步任务通知 | 领取异步查询结果（下载链接） | GET /bi/report/async/{taskId} |
| 发布配置抽屉（**五段式** · v2.6.27） | 生成/重配/失效发布（去向+密码+有效期+快照） | POST /bi/report/{id}/publish、PUT /bi/report/publish/{publishId}、DELETE …（**2.4 S1~S4**）；单独发布为菜单 → **S10** |
| 发布管理 Tab | 发布记录列表（访问次数/状态） | GET /bi/report/{id}/publish/list（**2.4 S2**） |
| 报表/看板-维度点击下钻 | 下钻/上卷查询（过滤上下文携带） | POST /bi/query/drill |
| 报表-单元格点击穿透 | 单元格穿透下钻（跳转明细/DC 链路） | POST /bi/query/cell-drill |
| 下钻结果区 | 导出（Excel/CSV） | GET /bi/query/export |
| 维度层级配置查看 | 维度层级定义加载 | GET /bi/query/dimension-tree |
| 查询性能监控页（R1/R9） | BR-204 性能统计与慢报表清单 | GET /bi/query/perf-stats |
| 订阅管理页（我的订阅） | 创建/修改/暂停/取消订阅 | POST /bi/subscribe、PUT /bi/subscribe/{id}、DELETE /bi/subscribe/{id} |
| 订阅管理页 | 我的订阅列表（推送结果状态） | GET /bi/subscribe/list |
| 报表/看板-分享按钮 | 生成分享链接（敏感数据审批提示） | POST /bi/subscribe/share-link |
| 分享审批工作台（R4） | 敏感分享审批（通过/驳回） | PUT /bi/subscribe/share-approval/{linkId} |
| 推送快照回溯页 | 快照查看（推送时点数据） | GET /bi/subscribe/snapshot/{id} |

（全文完）
