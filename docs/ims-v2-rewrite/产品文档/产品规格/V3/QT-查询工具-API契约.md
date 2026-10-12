# QT - 查询工具 API 契约

> **版本**：v0.1.2（2026-10-01 · B2 统一 run 拍板 · 同步编排）  
> **侧栏 IA**：**数据分析 → 查询工具** 仅消费本文 **§2 已 grounding 路径** + **§3 QueryPlan 逻辑**；未批准路径一律 **BLOCKED**。  
> **权威依据**：《IMS-查询工具-三模式统一引擎-产品方案-20260930》§3–§4；《DC-数据中心-API契约》§2.1；《COLLECT-数据采集-API契约》元数据只读；《BI0-指标查询报表-API契约》custom-query（FLAT 同形 · P1）。

---

## 1. API 总览

| # | 方法 | 路径 | 状态 | 说明 |
|---|------|------|------|------|
| — | — | `/admin-api/ims/collect/metadata/entity/{code}/fields` | **现网** | COLLECT 只读字段（DRILL/FLAT） |
| 1 | GET | `/admin-api/ims/dc/trace/entry` | **现网** | TRACE 入口搜索（DC-001） |
| 2 | POST | `/admin-api/ims/dc/trace/query` | **现网** | TRACE 图/表明细（TracePlan 执行） |
| 3 | GET | `/admin-api/ims/dc/trace/detail/{sessionCode}` | **现网** | 场次明细抽屉 |
| 4 | GET | `/admin-api/ims/dc/trace/aggregate` | **现网** | TRACE 聚合模式 |
| 5 | POST | `/admin-api/ims/bi/custom-query/preview` | **现网** | FLAT 编排（P1 · 不删 M6 页） |
| 6 | POST | `/admin-api/ims/bi/custom-query/execute` | **现网** | FLAT 执行（P1） |
| 7 | * | `/admin-api/ims/analysis/query-tool/template/**` | **IMS SSOT · 2026-10-01** | QueryTemplate CRUD（§3.1） |
| B2 | POST | `/admin-api/ims/analysis/query-tool/run` | **IMS SSOT · 2026-10-01** | 统一 **同步** QueryPlan 入口（DRILL 多层 / TRACE / FLAT · §3.2） |
| 8 | POST | `/admin-api/ims/analysis/query-tool/menu-seed` | **IMS SSOT · 2026-10-01** | MenuSeed 发布/撤销 L3（§3.3） |

---

## 2. 已 grounding 类型（与产品方案对齐）

### 2.1 QueryPlan（逻辑 · 服务端概念）

```typescript
type PlanType = 'SQL_DYNAMIC' | 'DC_TRACE' | 'REPORT_LAYOUT';

interface QueryPlan {
  planType: PlanType;
  tenantId: string;
  templateId?: string;
  runtime: {
    filters?: unknown;
    pageNo?: number;
    pageSize?: number;
    drillLevel?: number;
    drillKeys?: Record<string, string>;
    trace?: DcTraceQueryReq;
  };
}
```

- **P0 查询工具**：`DC_TRACE` → 映射 **§2.2**；运行时携带用户配置的 **穿透路径** `pathSteps[]`（每层 `entity` + 至下一层 `relationId`，depth 由步数推导，非独立 depth 字段）；`SQL_DYNAMIC` **BLOCKED** 至 P1/P2；`REPORT_LAYOUT` **不在** 本模块 P0 范围。
- **原型 mock（非 REST）**：`state.queryTool.trace.pathSteps[]` 配置链 + `runDepth` / `runFocusIdx` 驱动逐层穿透；产品方案 TraceTemplate 落库字段 **待 ADR**。

### 2.2 TracePlan → DC（现网）

复用《DC-数据中心-API契约》：

```typescript
interface DcTraceQueryReq {
  entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP';
  entryId: string;
  mode: 'GRAPH' | 'DETAIL';
  pageNo?: number;
  pageSize?: number;
  dateRange?: [string, string];
}
```

**响应**使用 `DcTraceGraphResp`（含 `queryCostMs`、`nodes`、`edges` 等）。

> **⚠️ 运行时口径（2026-10-04 订正 · 消除 §2.2↔§3.2 矛盾）**：**P0 查询工具 TRACE = 服务端一次 `POST …/query-tool/run` 内 for 循环逐步调用「与 `POST /dc/trace/query` 相同的 DC Service 方法」**，前端 **只调一次 run**、**不**逐层 POST、**不**轮询（见 §3.2）。§2.2 旧句「前端逐层下钻仍为重复调用 `POST /dc/trace/query`」**仅适用于 DC-001 页面直调**（`/ims/dc/trace` 节点/chip 下钻），**不适用于** 查询工具。
>
> **DC 契约不扩参（D2）**：跨层穿透链由 **QT 服务端** 在 run 内持有 `pathSteps[]`；DC 契约 `DcTraceQueryReq` **保持单步**（`entryType`+`entryId`+`mode`），**不新增** `pathSteps`。DC 页面（P1）与之并行，**禁止**新增 graph/lineage/step API。

### 2.3 SqlPlan → COLLECT + M6（P1+ · FLAT / DRILL）

```typescript
/** FLAT：与 OPS QueryBuilderConfig 同形 — 见 BI0/M6 契约 */
interface FlatTemplate {
  mode: 'FLAT';
  rootEntityCode: string;
  builderConfig: QueryBuilderConfig;
}

/** DRILL：多层 — 由 §3.2 run 同步逐级执行 */
interface DrillTemplate {
  mode: 'DRILL';
  levels: Array<{
    levelIndex: number;
    label: string;
    dataSource: { type: 'ENTITY'; entityCode: string } | { type: 'DATASET'; datasetId: string };
    displayFields: string[];
    drillToNext?: { leftKey: string; rightKey: string };
  }>;
}
```

> **DRILL 执行载体（D1 · 2026-10-04 订正）**：**P0 不新增多层 JOIN REST**。DRILL 的 `run` 复用 **「与 M6 同形的实体查询执行」**（COLLECT 元数据 + BI `custom-query` 执行链）；**多层 JOIN + 层级参数绑定引擎为独立依赖切片**（P2），到位前 `run` 以 **单层 + stub / 末层降级** 承接并在规格标 **BLOCKED**。**allowlist（D3）**：DRILL「加层」**仅允许** COLLECT 已注册的 **JoinEdge 维度链**（对齐 BI `BiDimensionTreeVO`：平台→账号→场次 / 部门→团队→人 / 年→月→日），**禁止**自由拼任意实体（防无意义 Join 链）。

### 2.4 统一 QueryResult（呈现壳）

```typescript
interface QueryResult {
  columns: Array<{ key: string; label: string; sensitive?: boolean }>;
  rows: Array<Record<string, unknown>>;
  chartHints?: { type: 'BAR' | 'LINE' | 'TABLE'; xKey?: string; yKeys?: string[] };
  levelState?: { activeLevel: number; breadcrumbs: string[] };
  queryCostMs: number;
  queryMode?: 'SYNC' | 'ASYNC';
  asyncTaskId?: string;
}
```

**queryMode（2026-10-01）**：经 **`POST …/query-tool/run`** 的执行 **一律 `SYNC`**；**禁止** DRILL/TRACE 走 **1262 异步任务**（1262 仍仅适用于 M6 自定义查询等大结果导出通道，与 QT run 无关）。

P0：TRACE 结果由 DC 响应 **适配** 为 `QueryResult` 子集（前端映射）；DRILL 由 run 返回完整 `levelState` + 当前层 rows。

---

## 3. QueryTemplate 与 MenuSeed（IMS 设计 SSOT · 用户拍板 2026-10-01）

### 3.1 QueryTemplate CRUD

**前缀**：`/admin-api/ims/analysis/query-tool/template`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/page` | 分页列表 |
| GET | `/{templateCode}` | 详情 |
| POST | `/` | 创建 DRAFT |
| PUT | `/{templateCode}` | 更新 DRAFT 载荷（DrillTemplate/TraceTemplate） |
| POST | `/{templateCode}/publish` | DRAFT→PUBLISHED |
| POST | `/{templateCode}/unpublish` | PUBLISHED→DRAFT（**不**自动下线 MenuSeed · 见 §3.3） |
| DELETE | `/{templateCode}` | 删除模板（须确认 · 已挂 MenuSeed 时 **BLOCKED** 或走审批 · 待 ADR） |

**列表筛选**：`GET /page?status=DRAFT|PUBLISHED&mode=DRILL|TRACE&keyword=` — **列表为默认落地**，qbar 状态/模式筛选（FR-QT-008）。

**记录字段**：`templateCode`、`name`、`mode`、`status`（DRAFT|PUBLISHED）、`menuSeed`（boolean · 是否已挂数据分析 L3）、`menuRoute`、`permCode`、`ownerUserId`、`updatedAt`、`desc`。

> **UI 载体（2026-10-04 · 管理优先）**：CRUD 由 **列表页 + 720px 抽屉向导** 驱动（页面规格 §3.1）。**新建**=向导「存草稿/保存并发布」→ `POST`；**编辑**=向导第②~⑥步 → `PUT`（**已发布模板 = 直接改**，覆盖已发布版本，不另存草稿）。CRUD 语义与路径**不变**，仅承载 UI 从「常驻配置面板」改为「列表 + 向导」。

### 3.2 统一 run（B2 · 同步编排 · 2026-10-01）

**路径**：`POST /admin-api/ims/analysis/query-tool/run`  
**语义**：HTTP **单请求-单响应**；服务端在 **同一事务/请求线程** 内完成编排，**不**创建异步 job（无 1262、无 `asyncTaskId`）。

**请求**：

```typescript
interface QueryToolRunReq {
  mode: 'FLAT' | 'DRILL' | 'TRACE';
  templateCode?: string;
  inlineTemplate?: FlatTemplate | DrillTemplate | TraceTemplate;
  runtime?: QueryPlan['runtime'];
}
```

**响应**：`QueryResult`（§2.4）；`queryMode` 固定 **`SYNC`**。

**编排策略（SSOT）**

| mode | 服务端行为 |
|------|------------|
| **FLAT** | 将 `FlatTemplate.builderConfig` 转为 M6 执行载荷，**同步调用** 现网 `POST /admin-api/ims/bi/custom-query/execute`（或等价 in-process Service）；结果适配 `QueryResult`。 |
| **DRILL** | 读取 `DrillTemplate.levels[]`；**for 循环** L0→Ln：用上一层选中行的 `drillKeys`（`drillToNext.leftKey/rightKey`）拼 `runtime.drillLevel` + `drillKeys`，调用 **与 M6 同形的实体查询执行**（COLLECT 元数据 + BI custom-query 执行链）；**禁止**拆成多 HTTP 让前端轮询。末层返回 `rows` + `levelState.breadcrumbs`。**（D1）**：多层 JOIN 引擎为 **P2 依赖切片**，未到位前 run 降级 **单层 + stub**（不阻塞本契约的 run 形状）。 |
| **TRACE** | 读取 `TraceTemplate.pathSteps[]` + 入口 `entryType/entryId`；**for 循环** 每一步 **同步调用** 与 `POST /admin-api/ims/dc/trace/query` **相同的服务方法**（可 in-process 复用 DC Service，**不**要求前端逐步 POST，**不**给 DC 契约加参）；图/表 payload 以 **最后一步** DC 响应为准并附 `levelState`。**（D5）`queryCostMs` 取「最后一步」单次耗时，不各步相加**（对齐 BR-205 P95<3s；各步相加会使 TRACE 指标失真）。 |

**与直调 DC 的关系**：穿透查询 L3（DC-001）仍可直接调 `POST /dc/trace/query`；QT **TRACE 模式** 的 run **在服务端代行** 相同 step 逻辑，前端只调 **一次** run。

**错误**：模板不存在/未发布 → **1263**；无权限 → **1264**；实体未映射 → 1261（与 BI0 一致）；已挂 MenuSeed 不可删 → **1265**（2026-10-03 裁决 · BI0 段）。

### 3.3 MenuSeed 动态 L3（**In Scope · 2026-10-01**）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/ims/analysis/query-tool/menu-seed` | 为 **PUBLISHED** 模板创建侧栏 L3 |
| DELETE | `/admin-api/ims/analysis/query-tool/menu-seed/{templateCode}` | 撤销 L3（模板可仍为 PUBLISHED） |

**请求（发布）**：

```typescript
interface QueryToolMenuSeedReq {
  templateCode: string;
  menuTitle: string;           // ≤16 字，默认模板 name
  parentMenuCode: 'ims:analysis:query-tool-group'; // 固定挂「数据分析」下
  sortOrder?: number;
  permCode?: string;           // 默认 ims:analysis:qt:run:{templateCode}
}
```

**响应**：`{ menuId: number; routePath: string }` — 路由 `/ims/analysis/query-tool/run/{templateCode}`（执行页复用 QT-001 壳 + 预载模板）。

**规则**：仅 `status=PUBLISHED` 可 seed；`unpublish` 模板 **不** 自动删 MenuSeed（须显式 DELETE menu-seed 或 UI 勾选「同时下线菜单」）；已 seed 模板 **禁止 DELETE** 模板直至 menu-seed 撤销（**1265**）。

---

## 4. 错误码（2026-10-03 裁决：归 BI0 段，原 1271~1279 已腾退）

| 码 | 说明 | 状态 |
|----|------|------|
| 1261 | 实体未映射（链 COLLECT P4m） | 现网 BI0 复用 |
| 1262 | 查询超时转异步 | **仅 M6 custom-query**；**QT run 不得返回 1262** |
| **1263** | QueryTemplate 不存在或未发布 | run / CRUD · 2026-10-03 自 1271 腾退 |
| **1264** | 无 run 权限 | run · 2026-10-03 自 1272 腾退 |
| **1265** | 模板已挂 MenuSeed 不可删 | 2026-10-03 自 1273 腾退 |
| **1266~1270** | 分析域段内预留（BI0/QT 按需分配） | 待切片登记 |

---

## 5. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-30 | 走查 #18 初版：TracePlan/SqlPlan grounding；REST BLOCKED 清单 |
| 2026-09-30 | FR-QT-008~011：§3.1 增补 unpublish/delete 与列表 status 筛选 |
| 2026-10-01 | §3.1 status 筛选对齐 **单列表 UX**（查询记录 Tab + 前端 filter） |
| 2026-10-01 | **B2 关闭**：§3.2 统一 run 同步编排（DRILL 多层 / TRACE 服务端逐步 DC / FLAT→M6）；禁止 QT 1262 |
| 2026-10-03 | **错误码腾退**：§4 的 1271/1272/1273 改为 1263/1264/1265（归 BI0 段），1271~1273 归还 Football WebAPI；§3.2/§3.3 同步 |
| 2026-10-04 | **一致性订正**（审查《查询工具与下钻穿透-一致性与完整性审查-2026-10-04》）：① §2.2 消除 **C2 矛盾** —— TRACE 运行时统一为「QT 服务端一次 run 内 for 循环调用 DC Service」，旧「前端逐层重复 POST」仅限 DC-001 页直调；② §2.3 补 **D1**（DRILL 执行载体 = P2 多层 JOIN 依赖切片，P0 降级单层）与 **D3**（DRILL allowlist 仅 COLLECT JoinEdge 维度链）；③ §3.2 TRACE **D5**：`queryCostMs` 取末步单次、非各步相加；④ §2.1 明确 **D2**（DC 契约不扩 `pathSteps`） |
| **2026-10-04** | **IA 改造：管理优先（列表 + 抽屉向导）**。§3.1 补「UI 载体」注记：CRUD 由列表 + 720px 抽屉向导驱动；**新建**=POST / **编辑**=PUT（已发布模板 = **直接改**）；记录字段补 `desc`。**CRUD / run / menu-seed 路径与语义不变**（仅承载 UI 变更）。 |
