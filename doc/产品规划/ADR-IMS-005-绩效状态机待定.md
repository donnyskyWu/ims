# ADR-IMS-005：绩效执行态与 IMS 批量核准 — 状态映射（已冻结）

> **状态**：**已冻结**（2026-10-01 用户拍板）  
> **关联**：OPS `docs/engineering/STATE-M3-绩效核算.md` · 《PERF-绩效考核-API契约.md》§3 · 《PERF-绩效考试-API契约.md》§3

---

## 1. 背景

OPS 单条考核记录（`/ops/perf/record/*`）、IMS 周期批量核准（`/admin-api/ims/perf/calc/*`）、现网执行页 Tag 展示 **三套来源**。本 ADR 冻结 **canonical 枚举** 与 **允许映射**，禁止实现期臆造等价。

---

## 2. Canonical 枚举（唯一 SSOT 字段值）

### 2.1 单条考核记录 — `oa_perf_record.status`

**Canonical = `dict_perf_status`（大写）**，全生命周期见 STATE-M3 §1：

| value | 中文 |
|-------|------|
| `DRAFT` | 草稿 |
| `CALCULATING` | 计算中 |
| `CALCULATED` | 已计算 |
| `REVIEWED` | 已审核 |
| `CONFIRMED` | 已确认 |
| `ISSUED` | 已发放 |
| `REJECTED` | 已驳回 |

**写路径 SSOT**：OPS `POST/PUT …/perf/record/*`（IMS BFF 透传同语义）；**禁止**用 IMS `perf/calc` 回写单条 `status`。

### 2.2 周期批量结果 — `ims_perf_result.resultStatus`（PERF-002）

**独立域**，与 record **不自动合并**：

| value | 含义 |
|-------|------|
| `CALCULATING` | 批量计算中 |
| `PENDING_MANUAL` | 待人工补录 |
| `PENDING_APPROVE` | 待核准发布 |
| `PUBLISHED` | 已发布（对 R4/R9 可见） |

---

## 3. 展示层映射（P2 执行考核 · 已冻结）

OPS 执行页历史 Tag 使用 **小写四态别名**；IMS **展示**须按下表由 canonical 推导（**存储仍为大写 dict**）：

| UI Tag（P2） | canonical `dict_perf_status` | 说明 |
|--------------|-------------------------------|------|
| `draft` | `DRAFT` | |
| `calculating` | `CALCULATING` | |
| `calculated` | `CALCULATED` **或** `REVIEWED` | 审核中仍展示为「已计算」色，详情展示 `REVIEWED` |
| `confirmed` | `CONFIRMED` | |
| （结果页扩展） | `ISSUED` · `REJECTED` | P3「考核结果」列表须展示完整 7 态字典标签，**不得**压成四态 |

**禁止**：`calculated` → `PENDING_APPROVE`；`confirmed` → `PUBLISHED`；合并 `POST …/record/confirm` 与 `PUT …/calc/{period}/approve`。

### 3.1 P3 考核结果数据源（并行产品）

| 入口 | 数据源 | 状态字段 |
|------|--------|----------|
| 执行考核 / 单条详情 | OPS record | `dict_perf_status` |
| 批量核准 / 排名 | IMS calc | `resultStatus` |

Slice 须 **单选** 写路径；读屏可 **双 Tab**（OPS 已确认 vs IMS 已发布），不得双写。

---

## 4. 实现检查清单

- [ ] P2 列表/详情 API 响应 `status` = 大写 canonical；前端 Tag 走 §3 映射函数  
- [ ] P3 若展示 OPS 结果：7 态 `<DictLabel dict-type="dict_perf_status" />`  
- [ ] P3 若展示 IMS 批量：`resultStatus` 四态独立 Tag  
- [ ] 原型 `perfExec` 四态文案与本 ADR 一致（`REVIEWED` 归入 calculated 展示）

---

## 5. 引用

- STATE-M3：`docs/engineering/STATE-M3-绩效核算.md`  
- 用户拍板：2026-10-01 · 《IMS-PRD与原型完整性核验-20261001.md》
