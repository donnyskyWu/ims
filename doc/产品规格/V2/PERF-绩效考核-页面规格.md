# PERF - 绩效考核 页面规格（OPS 并入 · 走查 #12）

> 依据：`docs/product/UX-M3-绩效核算.md`（P-M3-001～006 · **交互 SSOT**）、`docs/product/PRD-M3-绩效核算.md`（FR-M3-001～003）、`docs/engineering/STATE-M3-绩效核算.md`（OPS 考核记录状态机）、完整 PRD v2.6.7 §05、《PERF-绩效考核-API契约.md》、《PERF-绩效考试-API契约.md》（PERF-003 在线考试 · IMS 自建）。
> 技术栈：Vue 3 + Element Plus；**考核方案 / 执行考核 / 考核结果** 三叶对齐 OPS 路由语义；IMS 路由前缀 `/ims/perf/*`（切流前 BFF 可代理现网 `/ops/perf/*`，见契约 §0）。
> 归属：V2.3 批次 + OPS M3 并入（ADR-IMS-003）。

## 0. 模块总览

**主路径（走查 #12）**：建好考核方案 → **执行考核** → 查看考核结果。废止单页 Tab「考核方案 | 考核结果」跳过执行态。

| 页面 | 路由（IMS） | OPS 对照 | 级别 | 功能点 / FR |
|------|-------------|----------|------|-------------|
| P1 考核方案 | `/ims/perf/scheme` | `/ops/performance/perf-template` · P-M3-001/002 | L3 菜单 | FR-M3-001 · IMS PERF-001 指标/岗位绑定（方案层） |
| P2 执行考核 | `/ims/perf/execution` | `/ops/performance/perf-execution` · P-M3-003/004 | L3 菜单 | FR-M3-002 · IMS PERF-002 周期计算/核准（执行层） |
| P3 考核结果 | `/ims/perf/result` | `/ops/performance/perf-result` · P-M3-005/006 | L3 菜单 | FR-M3-003 · IMS PERF-004 排名/预警（发布后） |
| P4 在线考试 | `/ims/perf/exam` | —（IMS PERF-003 自建） | L3 菜单（可选第四叶） | PERF-003 · **不**替代 TRAIN QUIZ |

**侧栏 IA（协同与成长）**：可展开 **绩效考核** → 考核方案 · 执行考核 · 考核结果 ·（在线考试）。

**深链**：`go('perf')` → **考核方案**（`perfScheme`）。方案卡「发起考核」→ P2 并带 `schemeId` / 方案名 query。

---

## 状态 Tag 映射（ADR-IMS-005 · 已冻结）

> 口径来源：《产品规划/ADR-IMS-005-绩效状态机待定.md》（状态：**已冻结**，2026-10-05 v2.6.34 本期实现）。API 响应 `status` 恒为**大写 canonical**，前端 Tag 走映射函数（**存储不改**，仅展示别名）。

### P2 执行考核 — 四态展示（由 canonical 推导）

| UI Tag | canonical `dict_perf_status` | 说明 |
|--------|-------------------------------|------|
| `draft` | `DRAFT` | |
| `calculating` | `CALCULATING` | |
| `calculated` | `CALCULATED` **或** `REVIEWED` | 列表统一「已计算」色；**详情**展示 `REVIEWED` |
| `confirmed` | `CONFIRMED` | |

### P3 考核结果 — 七态不压缩

- 若展示 **OPS record** 结果：状态列用 **完整 7 态** `<DictLabel dict-type="dict_perf_status" />`（含 `ISSUED` / `REJECTED`），**不得**压成四态。
- 若展示 **IMS 批量**结果：用 **`resultStatus` 四态独立 Tag**（`CALCULATING` / `PENDING_MANUAL` / `PENDING_APPROVE` / `PUBLISHED`），**不**映射 record Tag。
- 读屏可 **双 Tab**（OPS 已确认 vs IMS 已发布），写路径 **单选**，**不得双写**。

### 非法转移禁止（ADR-IMS-005 §3）

- **禁止** `calculated` → `PENDING_APPROVE`。
- **禁止** `confirmed` → `PUBLISHED`。
- **禁止**合并 `POST …/record/confirm` 与 `PUT …/calc/{period}/approve`。
- **禁止**用 IMS `perf/calc` 回写单条 record `status`。

> P2/P3 实现检查清单见《PERF-绩效考核-API契约.md》§2A.5。

---

## P1 考核方案（FR-M3-001 / PERF-001）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 交互 SSOT | `UX-M3` §2～3：模板列表、按岗位编辑、指标权重合计 100%、启用/停用 |
| 权限 | 运营组长 / 运营管理者：本组可见；系统管理员：全量（PRD-M3 §4.1） |
| 用户 | 运营总监 R4、HR R2（只读）、超管 R1 |

### 2. 布局要点

- QueryBar：岗位 `dict_position`、模板名、启用状态。
- 表格或卡片：方案名、周期类型、适用岗位/部门、指标摘要、被考核人规模、启停。
- 操作：**新建方案**（Drawer/路由编辑）、**编辑**、**启用/停用**、**发起考核**（跳转 P2 创建抽屉并预填 `templateId`）。
- 底部说明：指标定义与自动取数覆盖率见 PERF-001 指标配置（可链 `/ims/perf/metric`，V2 工程页）。

### 3. 加载与 API（禁止臆造字段）

| 动作 | OPS SSOT（现网） | IMS 目标（切片后） |
|------|------------------|-------------------|
| 列表 | `GET /ops/perf/template/list`（`PerfTemplateQuery`） | **TBD** 是否 1:1 代理或映射 `ims_perf_scheme`；字段以 `PerfTemplateListItem` 为准 |
| 详情/编辑 | `GET /ops/perf/template/{id}/items`、`POST/PUT …/create|update` | 同上 **TBD** |
| 启用 | `POST /ops/perf/template/activate` | 对齐 OPS `ACTIVE` 语义 |

### 4. FR / AC（走查 #12）

| 编号 | 需求 / 验收 |
|------|-------------|
| FR-PERF-011 | 侧栏三叶顺序固定：考核方案 → 执行考核 → 考核结果 |
| FR-PERF-012 | 方案页须能 **发起考核**，进入 P2 且关联所选方案（非 toast） |
| AC-PERF-011 | 废止仅「方案+结果」两 Tab 作为主 IA |
| AC-PERF-012 | 启用方案行操作含「发起考核」；禁用方案灰显并拦截 |

---

## P2 执行考核（FR-M3-002 / PERF-002）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 交互 SSOT | `UX-M3` §4：列表 + 创建考核 Dialog + 详情 Drawer（指标明细、人工调整、确认） |
| 状态展示 | P2 Tag 四别名（ADR-IMS-005 §3）：`draft`/`calculating`/`calculated`/`confirmed` |
| 状态 SSOT（后端） | `dict_perf_status` 大写七态；`REVIEWED` 展示归入 calculated Tag |
| 批量核准 | P3 若走 IMS calc：**独立** `resultStatus` 四态，**不**映射 record Tag |

### 2. 列表

| 列 | 来源 |
|----|------|
| 被考核人 | `target_user_id` → UserSelect 回显（ADR-056） |
| 岗位 | `dict_position` |
| 考核周期 | `period_type` + 起止 |
| 总分 | 算分完成后展示 |
| 状态 | Tag 语义色 |
| 考核人 | 当前 `assessor_id` |
| 操作 | 查看、编辑（仅 draft）、删除（draft）、**评分/调整**（calculated）、**确认结果**（calculated） |

QueryBar：IP 组树（可选）、被考核人 UserSelect、状态 Select。

主按钮：**创建考核** → Dialog（被考核人、考核模板、周期字典、起止日期）→ 创建后可选 **自动算分**。

### 3. 详情 / 评分 Drawer

| 区域 | 内容 |
|------|------|
| 基本信息 | 方案名、周期、被考核人、考核人、状态 |
| 指标明细 | 指标名、原始值、自动得分、人工调整（±20%）、最终得分、备注 |
| 操作 | **重新算分**（draft/calculated）、**保存调整**、**确认考核**（calculated → confirmed） |

确认后：Toast + 提供 **查看考核结果** 跳转 P3（同周期筛选）。

### 4. FR / AC

| 编号 | 需求 / 验收 |
|------|-------------|
| FR-PERF-013 | 从 P1「发起考核」须带方案上下文创建周期实例 |
| FR-PERF-014 | 支持自动算分 + 人工微调 + 确认发布（FR-M3-002 主流程 1～7） |
| AC-PERF-013 | 创建考核 Dialog 字段与 OPS `createPerfRecord` 请求体一致（见契约） |
| AC-PERF-014 | 同周期同员工不可重复创建（BR-031 / AC-M3-002-6） |
| AC-PERF-015 | 确认后 P3 列表可见该条（权限隔离仍按 FR-M3-003） |

### 5. API 映射（OPS SSOT）

| 动作 | OPS |
|------|-----|
| 列表 | `GET /ops/perf/record/list` |
| 创建 | `POST /ops/perf/record/create` |
| 算分 | `POST /ops/perf/record/calculate` |
| 调整 | `PUT /ops/perf/record/adjust` |
| 详情 | `GET /ops/perf/record/detail` |
| 确认 | `POST /ops/perf/record/confirm` |

IMS 月度批量计算（PERF-002）：`POST /admin-api/ims/perf/calc/run` 等为 **并行能力**（部门周期核准），与 OPS 单条考核记录 **并存** 时须 ADR 冻结归并策略 → **BLOCKED**。**（2026-10-05 补注：ADR-IMS-005 已冻结——双域不自动合并，写路径单选、读屏可双 Tab，见 §状态 Tag 映射）**

---

## P3 考核结果（FR-M3-003 / PERF-004）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 交互 SSOT | `UX-M3` §5：筛选 + 列表 + 详情 + 个人趋势 |
| 数据范围 | 仅 **已确认/已发布** 记录；OPS `confirmed` 或 IMS `PUBLISHED`（映射 BLOCKED → **2026-10-05 补注：ADR-IMS-005 已冻结，双域不自动合并，见 §状态 Tag 映射**） |
| 增强 | PERF-004 TOP3 / 末位预警 / 导出（原 V2 页面规格 P5 部分能力） |

### 2. 布局

- QueryBar：UserSelect、周期、绩效等级。
- 排名区（PERF-004）：TOP3、末位 PIP 预警、部门均分（有数据时）。
- 表格：排名、被考核人、部门、周期、KPI 得分、加减分、综合分、评级、操作（查看明细 / PIP）。

### 3. API

| 动作 | OPS | IMS |
|------|-----|-----|
| 结果列表 | **TBD**（现网 `perfResult.ts` 封装，路径以仓库为准） | `GET /admin-api/ims/perf/calc/{period}`（`PUBLISHED`） |
| 排名 | — | `GET /admin-api/ims/perf/rank/period/{period}` |

---

## P4 在线考试（PERF-003）

不变更 SSOT：仍用《PERF-绩效考试-页面规格.md》P3/P4/P5/P6。与走查 #12 主路径 **正交**；菜单为第四叶或从方案页链接，**禁止**用考试 Tab 顶替「执行考核」。

---

## 5. 原型验收（IMS-完整系统-UI原型.html）

| 检查项 | 期望 |
|--------|------|
| 侧栏 | 绩效考核 4 L3（至少前三叶） |
| P2 | 活动周期列表 + 创建 Dialog + 评分 Drawer + 确认后跳 P3 |
| P1 | 方案卡「发起考核」非 toast |
| P3 | 排名表 + 从 P2「查看结果」联动 |
