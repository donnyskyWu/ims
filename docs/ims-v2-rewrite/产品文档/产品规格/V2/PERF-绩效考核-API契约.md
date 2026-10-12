# PERF - 绩效考核 API 契约（OPS 并入 · 走查 #12）

> **范围**：考核方案 / 执行考核 / 考核结果（OPS M3 主路径）+ 与 IMS V2 `PERF-002` 批量计算的关系说明。  
> **OPS SSOT**：`football-front/apps/web-ele/src/api/ops/perfTemplate.ts`、`perfRecord.ts`、`perfResult.ts`（路径前缀 `/ops/perf/*`）。  
> **IMS 自建 SSOT**：《PERF-绩效考试-API契约.md》（`/admin-api/ims/perf/metric|calc|rank|exam/*`）。  
> **禁止**：本文未列字段不得写入切片；IMS 新表字段在 ADR 冻结前标 **TBD**。  
> **2026-10-05（v2.6.34）**：状态映射按 **ADR-IMS-005（已冻结）本期实现**（断点 B8）——canonical `dict_perf_status` 大写，P2 前端 Tag 按映射推导，P3 七态不压缩。

---

## 0. 路由与 BFF 策略

| 域 | 现网 OPS | IMS 目标路由 | 状态 |
|----|----------|--------------|------|
| 考核模板 | `/ops/performance/perf-template` | `/ims/perf/scheme` | 交互 SSOT = OPS UX |
| 考核执行 | `/ops/performance/perf-execution` | `/ims/perf/execution` | 同上 |
| 绩效结果 | `/ops/performance/perf-result` | `/ims/perf/result` | 同上 |
| 订单归因 | `/ops/performance/order-attribution` | **Out of Scope** 走查 #12 | M3 FR-M3-004 独立菜单 |

切流期可选：BFF 将 `/admin-api/ims/perf/execution/*` 代理到 `/ops/perf/record/*` → 须 ADR 记录，**非默认**。

---

## 1. OPS 考核模板（方案 · P1）

来源：`perfTemplate.ts`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/ops/perf/template/list` | 分页列表；Query 见 `PerfTemplateQuery` |
| GET | `/ops/perf/template/{id}/items` | 模板详情 + 指标项 |
| POST | `/ops/perf/template/create` | 创建；Body：`PerfTemplateDetail` |
| PUT | `/ops/perf/template/update` | 更新 |
| POST | `/ops/perf/template/activate` | 启用；Body：`{ id: number }` |

类型 SSOT：`football-front/apps/web-ele/src/types/ops/perfTemplate.ts`（`PerfTemplateListItem`、`PerfTemplateItem`、`ScoreRange` 等）。**不得**在 IMS 契约中重命名或增删字段。

---

## 2. OPS 考核执行（P2）

来源：`perfRecord.ts`

### 2.1 GET `/ops/perf/record/list`

Query（现有前端封装）：

```typescript
interface PerfRecordQuery {
  ipGroupId?: number;
  targetUserId?: number;
  periodType?: string;
  status?: string;
  pageNum?: number;
  pageSize?: number;
}
```

响应：分页列表（字段以现网后端为准；前端展示 `evaluateeName`、`position`、`cycleDisplay`、`totalScore`、`status`、`evaluatorName`、`createdAt`）。

### 2.2 POST `/ops/perf/record/create`

```typescript
{
  targetUserId: number;
  templateId?: number;
  periodType: string;
  periodStart: string;
  periodEnd: string;
}
```

### 2.3 POST `/ops/perf/record/calculate`

Body：`{ recordId: number }`

### 2.4 PUT `/ops/perf/record/adjust`

```typescript
{
  itemRecordId: number;
  manualAdjustment: number;
  remark?: string;
}
```

### 2.5 GET `/ops/perf/record/detail`

Query：`{ id: number }`

### 2.6 POST `/ops/perf/record/confirm`

Body：`{ id: number }`

---

## 2A. 状态映射（ADR-IMS-005 · 已冻结）

> **口径来源**：《产品规划/ADR-IMS-005-绩效状态机待定.md》（状态：**已冻结**）。**本期按 ADR-IMS-005 实现**（用户 2026-10-05 决策断点 B8）。禁止臆造等价。

### 2A.1 Canonical 枚举（唯一 SSOT 字段值）

三套来源、**禁止自动合并**：

| 来源域 | 字段 | canonical 值 | 说明 |
|--------|------|--------------|------|
| OPS 单条记录 | `oa_perf_record.status` | `dict_perf_status` **大写七态**：`DRAFT` · `CALCULATING` · `CALCULATED` · `REVIEWED` · `CONFIRMED` · `ISSUED` · `REJECTED` | 写路径 SSOT = OPS `perf/record/*`（IMS BFF 透传同语义） |
| IMS 周期批量 | `ims_perf_result.resultStatus` | **四态**：`CALCULATING` · `PENDING_MANUAL` · `PENDING_APPROVE` · `PUBLISHED` | **独立域**，与单条 record **不自动合并** |

**写路径约束**：

- 单条记录 `status` **仅** 由 OPS `POST/PUT …/perf/record/*` 写入；**禁止**用 IMS `perf/calc` 回写单条 `status`。
- 周期批量核准 **仅** 由 `PUT /admin-api/ims/perf/calc/{period}/approve` 写入；**禁止**与 `POST …/record/confirm` 合并。

### 2A.2 展示层映射（P2 执行考核 · 由 canonical 推导）

API 响应 `status` **始终为大写 canonical**；前端 Tag 按下表推导（**存储仍为大写 dict**，仅展示别名）：

| UI Tag（P2） | canonical `dict_perf_status` | 说明 |
|--------------|-------------------------------|------|
| `draft` | `DRAFT` | |
| `calculating` | `CALCULATING` | |
| `calculated` | `CALCULATED` **或** `REVIEWED` | 列表统一「已计算」色；**详情**展示 `REVIEWED` |
| `confirmed` | `CONFIRMED` | |
| （结果页扩展） | `ISSUED` · `REJECTED` | P3「考核结果」列表须展示完整 **7 态**字典标签，**不得**压成四态 |

### 2A.3 P3 考核结果双来源（读屏可双 Tab，写路径单选）

| 入口 | 数据源 | 状态字段 |
|------|--------|----------|
| 执行考核 / 单条详情 | OPS record | `dict_perf_status`（7 态） |
| 批量核准 / 排名 | IMS calc | `resultStatus`（4 态） |

Slice 须 **单选** 写路径；读屏可 **双 Tab**（OPS 已确认 / IMS 已发布），**不得双写**。

### 2A.4 禁止项

- **禁止** `calculated` → `PENDING_APPROVE`。
- **禁止** `confirmed` → `PUBLISHED`。
- **禁止**合并 `POST …/record/confirm` 与 `PUT …/calc/{period}/approve`。
- **禁止**用 IMS `perf/calc` 回写单条 record `status`。

### 2A.5 实现检查清单（ADR §4）

- [ ] P2 列表/详情 API 响应 `status` = 大写 canonical；前端 Tag 走 §2A.2 映射函数
- [ ] P3 若展示 OPS 结果：7 态 `<DictLabel dict-type="dict_perf_status" />`
- [ ] P3 若展示 IMS 批量：`resultStatus` 四态独立 Tag
- [ ] 原型 `perfExec` 四态文案与 ADR 一致（`REVIEWED` 归入 calculated 展示）

---

## 3. 状态机（已冻结 · ADR-IMS-005 · 2026-10-01）

**Canonical 单条记录** = `dict_perf_status` 大写七态（STATE-M3 §1）。**IMS 批量** = `resultStatus` 四态（PERF-002）。**并行产品，禁止自动等价。**

| 域 | 字段 | 枚举 |
|----|------|------|
| OPS record | `status` | `DRAFT` · `CALCULATING` · `CALCULATED` · `REVIEWED` · `CONFIRMED` · `ISSUED` · `REJECTED` |
| IMS calc | `resultStatus` | `CALCULATING` · `PENDING_MANUAL` · `PENDING_APPROVE` · `PUBLISHED` |

**P2 UI Tag 映射**（展示别名 → canonical）：`draft`→`DRAFT` · `calculating`→`CALCULATING` · `calculated`→`CALCULATED|REVIEWED` · `confirmed`→`CONFIRMED`。详情/结果页须可展示 `ISSUED`/`REJECTED` 字典标签。

**写路径**：执行考核 **仅** OPS record API；批量核准 **仅** `/admin-api/ims/perf/calc/{period}/approve`。详见《ADR-IMS-005-绩效状态机待定.md》（标题：已冻结）。

---

## 4. IMS 批量绩效（PERF-002 · 与 OPS 单条记录并行）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/ims/perf/calc/run` | 月度批量计算 |
| GET | `/admin-api/ims/perf/calc/{period}` | 周期结果列表 |
| PUT | `/admin-api/ims/perf/calc/detail/{id}/manual` | 人工补录 |
| PUT | `/admin-api/ims/perf/calc/{period}/approve` | 核准发布 |

与 OPS `/ops/perf/record/*` **非 1:1**。走查 #12 执行考核页 **优先对齐 OPS 单条考核**；批量核准为 R4 补算入口（见《PERF-绩效考试-页面规格》P2）。

---

## 5. 考核结果（P3）

| 来源 | 说明 |
|------|------|
| OPS | `perfResult.ts`（路径以仓库为准）· 列表/趋势 **TBD 逐接口补全**（走查 #12 未改 OPS 后端） |
| IMS | `GET /admin-api/ims/perf/calc/{period}`（`resultStatus=PUBLISHED`）+ `GET /admin-api/ims/perf/rank/period/{period}` |

---

## 6. 错误码

- OPS 业务错误：沿用 OPS 全局规范（未在本文展开）。
- IMS PERF 段：1151～1164（见《PERF-绩效考试-API契约.md》）。

---

## 7. 页面 ↔ 接口对照

| 页面 | 首屏加载 | 关键写操作 |
|------|----------|------------|
| P1 考核方案 | `GET …/template/list` | `POST …/create`、`POST …/activate` |
| P2 执行考核 | `GET …/record/list` | `POST …/create`、`POST …/calculate`、`PUT …/adjust`、`POST …/confirm` |
| P3 考核结果 | OPS 列表 **TBD** 或 IMS `GET …/calc/{period}` | 导出 **TBD** |
