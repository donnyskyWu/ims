# SLICES-IMS-CONTENT — 内容生产

> 2026-10-05 · v2.6.34 · 5 切片 + 每片独立 Slice Gate（CONTENT-OPS+UX-M2）
>
> **口径（2026-10-05 用户拍板 · 唯一口径）**：CONTENT 端到端不可整链验收（走查阻断 2026-09-29 §2），正式按 **5 切片**推进，每片独立 Gate；**放弃整系统全量开写**。
> **开工顺序 = 门禁优先**：**S1 规格先行 + S4 内容审核门禁并行**（S4 的 G1 不依赖 Football，是整链最高频阻断点，可最早解除）。
> **Gate 判据**：每片 = **规格评审通过 + 原型闭环 + 契约齐备 + 联调通过（四项全绿）**；**不以整链为 Gate**。
> **未开片模块**：导航可见但页面标「**建设中**」，不接业务入口。
> **CONTENT 导航 = 7 子菜单**（SOP管理 / 计划管理 / 工作任务登记 / 我的任务 / 内容管理 / 公推模板库 / 内容审核，v2.6.33）；「全部任务」= 我的任务页内 Tab，非独立菜单；**SOP 免审**（无 SOP 审核页）。

## 切片总表

| Slice | FR/功能点 | 范围 | 关键产物 | Gate 判据 | 依赖 | 状态 |
|-------|-----------|------|----------|-----------|------|------|
| **S1** | CONTENT-100（SOP）+ CONTENT-102（计划） | SOP 管理（`/ims/content/sop`）+ 计划管理（`/ims/content/plan`） | 页面规格 + API 契约 | 规格评审通过 + 原型闭环 | 无（先行） | **先行 · 进行中** |
| **S2** | CONTENT-104 / CONTENT-105 | 工作任务登记（`/ims/content/work-task`）+ 作者×赛事矩阵出任务 | 矩阵 UI + 出任务接口 | 矩阵可操作、能生成任务 | S1（SOP 模板） | 未开片 |
| **S3** | CONTENT-103 + CONTENT-106 | 我的任务（`/ims/content/task`）+ 内容主工作区（CONTENT-106 玩法/AI/排版） | 执行 → 内容抽屉 → 玩法 | 任务可执行、内容可存 | S2 | 未开片 |
| **S4** | CONTENT-005（级数可配）+ CONTENT-006 | 内容审核（`/ims/content/review`）+ 发布归档 → **门禁 G1** | 审核门禁 | 未审内容不可发布（可独立验收） | 无（**不依赖 Football**，先行） | **先行 · 进行中** |
| **S5** | CONTENT-109 / CONTENT-110 | Football 方案同步 + 补偿 | WebAPI + 补偿队列 | 同步成功 / 失败进队列 | S3、S4 | 未开片 |

> 行内状态为文档口径标记；实际推进以每片 Gate 四项全绿为准。

---

## S1 切片清单（先行）

> S1 = **SOP 管理（CONTENT-100）+ 计划管理（CONTENT-102）**，与 S4 并行推进。

### 页面范围

| 页面 | 路由 | 功能点 | 备注 |
|------|------|--------|------|
| SOP 管理 | `/ims/content/sop` | CONTENT-100（+ CONTENT-001 升级列） | 节点库 / DAG 画布 / 属性面板；**SOP 免审**，无 SOP 审核页 |
| 计划管理 | `/ims/content/plan` | CONTENT-102 | 计划向导 / 计划列表 |

### 契约（SOP / 计划相关端点）

> 来源：`产品规格/V1/CONTENT-内容生产-API契约.md`（SOP，§1 #1~6）、`产品规格/V1/CONTENT-OPS并入补充-API契约.md`（计划，OPS 主路径端点清单 #2）。runtime canonical 前缀统一 `/admin-api/ims/content`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ims/content/sop/list` | SOP 列表（分页） |
| POST | `/admin-api/ims/content/sop` | 创建 SOP（含节点） |
| PUT | `/admin-api/ims/content/sop/{id}` | 编辑 SOP（生成新版本） |
| DELETE | `/admin-api/ims/content/sop/{id}` | 删除 SOP（逻辑删除） |
| GET | `/admin-api/ims/content/sop/{id}/nodes` | SOP 节点详情 |
| POST | `/admin-api/ims/content/sop/node/{nodeId}/check` | 质量清单校验提交 |
| GET | `/admin-api/ims/content/plan` | 计划列表 |
| POST | `/admin-api/ims/content/plan` | 创建计划 |

> OPS `/admin-api/ops/plan/*`（create/start/terminate/approve/reject/delete/get）**仅迁移与 UX 参照，非 runtime**；IMS 计划端点以补充契约 #2 为准。

### 交付物

- 页面规格（SOP 管理页 + 计划管理页）
- API 契约（上表端点，字段级以主契约 §2.1 为准）
- 原型闭环（SOP DAG 编辑 → 保存新版本；计划向导/列表）
- Gate 检查表（见下）

### Gate 检查表（S1）

- [ ] **规格**：页面规格评审通过（SOP 管理 + 计划管理）
- [ ] **原型**：核心路径原型闭环（SOP 节点编辑保存 / 计划创建启动）
- [ ] **契约**：SOP + 计划端点契约齐备（请求/响应/错误码）
- [ ] **联调**：接口联调通过

> **S4 与 S1 并行推进**：S4 的 G1（未审内容不可发布）**不依赖 Football**，是整链最高频阻断点，可最早解除；故 S4 与 S1 同批先行，无需等待 S2/S3/S5。
