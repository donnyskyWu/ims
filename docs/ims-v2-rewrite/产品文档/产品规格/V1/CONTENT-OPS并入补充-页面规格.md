# CONTENT - OPS 并入补充规格（工作任务 / AI / 方案同步）

> 原 `CONTENT-内容生产-页面规格.md` 覆盖 CONTENT-001～006（IMS 短视频增量）。本文件覆盖完整 PRD CONTENT-100～110 的 **OPS 主路径**。  
> **API SSOT（2026-10-01）**：`/admin-api/ims/content/**` + IMS 自有表（见《CONTENT-内容生产-API契约》）；OPS `/oa/*`、`/ops/content/*` **仅迁移/UX 参照**，非 runtime。  
> 前缀：`/admin-api/ims/content`（禁止 IMS 运行时调用 OPS 进程）  
> **交互 SSOT**：`docs/product/UX-M2-内容生产.md`、`docs/product/UX-M2-内容生产-amphipoda对齐增量.md`、`docs/product/PRD-M2-工作任务管理.md`（**ADR-IMS-003**）。  
> **信息架构**：内容域使用 **侧栏子菜单（独立路由/页面）**，禁止单页 13 Tab 叠放 OPS 与 IMS 双轨。  
> **侧栏层级（IMS 完整原型）**：`日常运营` 一级分组下，**10 直播管理** 与 **15 内容生产（二级目录）并列**；内容生产下挂子菜单（SOP / 计划 / 工作任务 / 我的任务 / 内容 / 公推模板 / 审核），**不得**挂在直播管理下或与其 Tab 混排。  
> **v2.6.33 订正**：① **移除「SOP审核」独立子菜单**（SOP 模板不再需要审核，`contentSopReview` 已删）；② **移除「全部任务」独立子菜单**（`contentTaskAll` 已删），「我的任务」页内 Tab 保留「我的任务 / 全部任务」切换（与 OPS `task/index.vue` 一致）。内容生产子菜单由 9 项收为 **7 项**。

## 交付切片与 Gate（2026-10-05 · v2.6.34）

> **口径与《CONTENT-内容生产-页面规格.md》§「交付切片与 Gate」一致**（全文口径以此为准，本节略简）。CONTENT 端到端不可整链验收，按 **5 切片**推进，**每片独立 Gate**（四项全绿：规格评审通过 + 原型闭环 + 契约齐备 + 联调通过）；**不以整链为 Gate**。
> **开工顺序 = 门禁优先**：**S1（SOP + 计划）规格先行 + S4（内容审核门禁 G1）并行**（S4 的 G1 不依赖 Football，是整链最高频阻断点）；**未开片模块**：导航可见但页面标「**建设中**」，不接业务入口。导航 = **7 子菜单**；「全部任务」= 我的任务页内 Tab；**SOP 免审**。

| Slice | 范围 | Gate 判据 | 依赖 | 状态 |
|-------|------|-----------|------|------|
| **S1** | SOP（CONTENT-100）+ 计划（CONTENT-102） | 规格评审通过 + 原型闭环 | 无（先行） | **先行 · 进行中** |
| **S2** | 工作任务登记（CONTENT-104/105）+ 矩阵出任务 | 矩阵可操作、能生成任务 | S1 | 未开片 |
| **S3** | 我的任务（CONTENT-103）+ 内容主工作区（CONTENT-106） | 任务可执行、内容可存 | S2 | 未开片 |
| **S4** | 内容审核（CONTENT-005 级数可配）+ 发布归档（CONTENT-006）→ 门禁 G1 | 未审内容不可发布（可独立验收） | 无（**不依赖 Football**，先行） | **先行 · 进行中** |
| **S5** | Football 方案同步（CONTENT-109/110）+ 补偿 | 同步成功 / 失败进队列 | S3、S4 | 未开片 |

> **分工**：本文件为 **OPS 主路径**（SOP / 计划 / 工作任务 / 我的任务 / 内容管理 / 公推模板 / 内容审核）的规格 SSOT；《CONTENT-内容生产-页面规格.md》P1～P6 为 IMS 短视频增量（默认不出主导航）。切片 Gate 以本文件侧栏映射与页面级最小集为准。

## 默认演示主路径（走查 / 原型 / 切片验收）

计划列表 → 工作任务矩阵 → 确认出任务 → **我的任务** 执行 → **内容管理** 抽屉 → 提审 → 一/二级审核 → 任务完成 → Football 同步。

AI 短视频：**不**单独占主导航 Tab；在 **内容管理** 编辑抽屉内提供「AI 视频脚本生成」「AI 视频生成」，挂 SOP 短视频节点（CONTENT-004 能力内嵌，非平行 ComfyUI 主轨）。

## 侧栏子菜单 ↔ OPS UX 映射

| IMS 子菜单 | IMS 路由 | OPS UX | 功能点 |
|------------|----------|--------|--------|
| SOP管理 | `/ims/content/sop` | P-M2-001 / P-M2-002 | CONTENT-100、CONTENT-001 |
| 计划管理 | `/ims/content/plan` | P-M2-011 | CONTENT-102 |
| 工作任务登记 | `/ims/content/work-task` | FR-M2-010 矩阵 | CONTENT-104、CONTENT-105 |
| 我的任务 | `/ims/content/task` | P-M2-003（默认 Tab「我的任务」） | CONTENT-103 |
| 内容管理 | `/ims/content/list` | P-M2-006/007 弹窗/抽屉 | CONTENT-106、107、109、110；AI 视频脚本/成片 |
| 公推模板库 | `/ims/content/layout-template` | P-M2-013~015 | CONTENT-107 |
| 内容审核 | `/ims/content/review` | P-M2-008 | CONTENT-005 |

> **本期侧栏必选（产品走查）**：上表前六项 + **内容审核**（审核员角色 R8 主入口）。  
> **降级 / 不出现在主导航**：选题计划（CONTENT-002）、独立 AI 脚本页（CONTENT-003）、ComfyUI 生产链 Tab（CONTENT-004 仅内容内嵌）、发布归档（CONTENT-006）、内容知识库（CONTENT-108）— 保留 P1/P2 规格或并入 SOP/内容流，不得与 OPS 主路径抢默认入口。

## P-SOP（CONTENT-100 / 001）

布局对齐 OPS `UX-M2` P-M2-002：左节点库 / 中 DAG 画布 / 右属性面板。节点从库拖入画布，画布内拖拽排位，前置依赖多选，并行组文本，保存前校验无环。

节点类型仅 `dict_sop_node_type` 三值（内容生成 / 内容发布 / 普通节点）。`CONTENT_GENERATION` 必填 `dict_document_type`（ADR-077）。执行/审核岗位 `dict_position`。`needReview=1` 时审核岗位必填。保存生成新版本，进行中项目沿用旧版本。预置「标准内容生产运营流程」14 节点、4 路并行（推文/方案/视频/直播）。

质量清单与交付物为 CONTENT-001 升级列，挂在节点属性。

## 计划管理

计划向导/列表（CONTENT-102，P-M2-011）。**不含**营销计划维护（营销计划作为 SOP 模板属性在 SOP 管理内维护）。

节点 `marketing_plan`（**启用态同租户 1:1**，ADR-074）为 SOP 模板属性，在 **SOP 管理**（`/ims/content/sop`）编辑页维护；工作任务登记 confirm 按此字段解析启用 SOP 全节点。

## 工作任务登记

登记表 + **作者×赛事矩阵**（可多选、合并执行组）：赛事、营销计划、是否直播/时间、销售平台。确认后出 SOP 任务；参数 `work.task.confirm.auto-ai-generate` 控制是否 jingcai 自动 AI。撤回删草稿并取消任务（IMS 内 + Football WebAPI，CONTENT-110）。

**页内三 Tab**（对齐 OPS `index.vue`）：**任务登记**（register）/ **任务执行情况**（execution，SOP 节点粒度只读列表）/ **任务管理**（matrix，区间矩阵 + summary）。

**任务管理（matrix）矩阵表头**：**两级合并表头** —— 一级「赛事信息」`colspan=5`（日期/场次/赛事/比赛名称/比赛时间），每个作者列组 `colspan=4`（营销计划/直播时间/销售平台/红黑），表头文案 `{authorName}【{ipGroupName}-{ipGroupLeaderName}】`；表体**日期列按 `workDate` 纵向合并 `rowspan`**（竖排文字）。顶部 summary 条：总任务/赛事行/直播公推/付费销售/红/黑/待判定。对齐 OPS `WorkTaskMatrixTable.vue`（`FIXED_COL_COUNT=5` / `SUB_COL_COUNT=4`）。

## 我的任务

页内 Tab：**我的任务**（默认）/ **全部任务**（与 OPS 一致，非侧栏拆分）。执行入口 → 任务执行页或内容抽屉（`taskId`）。完成门禁 ADR-079。

## 内容编辑（内容管理）

玩法 / matchScheme、付费/免费正文、AI 排版抽屉、Football 同步状态（成功/补偿中/失败）。**AI 视频脚本**、**AI 视频生成** 抽屉（SOP 短视频链路；`aiGenerateStatus` ADR-077）。删除草稿二次确认：Football `status-change` **下架**，IMS 逻辑删。

## 内容审核

Tab：**一级审核** / **二级审核**（随 review-config）。与内容管理同一 content id；通过后任务可完成。

## 公推模板库

列表 + 导入向导 + 编辑/预览（FR-M2-005），与 OPS `/prod/layout-template` 对齐。

## 规则

- 原表列保留（execution_group_id、document_type、ai_generate_status 等）。
- 同步仅 HTTP；失败不回滚 IMS 保存。
- SOP 引擎不被 FLOW 替换。
- 完整 UI 原型子菜单仅作 IA 示意；**实现与验收以 UX-M2 为准**（ADR-IMS-003）。

---

## 页面级字段/按钮/状态（UX-M2 → IMS 路由 · 2026-10-01 补齐）

> SSOT：`docs/product/UX-M2-内容生产.md`。下列为切片最小集；未列字段 **不得** 推断。

### `/ims/content/sop`（P-M2-001/002）

| 类型 | 项 |
|------|-----|
| 筛选 | F-NAME、F-CONTENT-TYPE（`dict_content_type`）、F-PLATFORM |
| 按钮 | 新增模板、编辑、删除、启用 |
| 编辑页 | 节点库拖拽、LogicFlow 画布、属性：`dict_sop_node_type`、`dict_document_type`（内容生成节点）、`dict_position`、needReview+审核岗位、SLA |
| 状态 | DAG 环保存失败 Banner；节点缺执行岗位 1500 |

### `/ims/content/plan`（P-M2-011）

| 类型 | 项 |
|------|-----|
| 区 | 计划向导 / 计划列表 |
| 字段 | 计划名、SOP 模板、IP 组、周期 |

### `/ims/content/work-task`（工作任务登记 · FR-M2-010）

| 类型 | 项 |
|------|-----|
| 页内 Tab | 任务登记（register）/ 任务执行情况（execution）/ 任务管理（matrix） |
| 矩阵列（matrix） | 两级合并表头：「赛事信息」`colspan=5`（日期/场次/赛事/比赛名称/比赛时间）+ 每作者 `colspan=4`（营销计划/直播时间/销售平台/红黑）；列头 `{authorName}【{ipGroupName}-{ipGroupLeaderName}】`；日期列 `rowspan` 纵合并 |
| 矩阵字典 | `dict_marketing_plan_type`（直播公推 LIVE_PUBLIC / 付费销售 PAID_SALES）· `dict_sales_platform`（私域 PRIVATE / 快手 KUAISHOU / 抖音 DOUYIN / 无 NONE）· `dict_win_prediction`（红 RED / 黑 BLACK / 未知 UNKNOWN） |
| 按钮 | 确认出任务、撤回（删草稿+取消任务+Football 下架 CONTENT-110） |
| 状态 | 确认后出 SOP 任务；参数 `work.task.confirm.auto-ai-generate` 控制 jingcai |

### `/ims/content/task`（P-M2-003 · Tab 我的任务/全部任务）

| 类型 | 项 |
|------|-----|
| 筛选 | IP 组、F-STATUS（`dict_sop_node_status`）、执行人（全部任务 Tab） |
| 行操作 | 执行、提交审核、完成（门禁 ADR-079） |
| 入口 | 执行 → `/ims/content/task/:id/execute` 或内容抽屉 |

### `/ims/content/task/:id/execute`（P-M2-012 · 全页规格）

> **来源**：`docs/product/UX-M2-内容生产.md` §4.3 · `docs/product/PRD-M2-内容生产.md` §4.2.5.1 · `docs/engineering/API-M2-内容生产.md` §2.6～2.8 · ADR-079/080/077。

**路由**：`/ims/content/task/:id/execute`（隐藏叶，不入侧栏）· **入口**：我的任务 →「执行」。

#### ASCII 布局

```
+------------------------------------------------------------------+
| [← 返回我的任务]  任务执行 · {nodeName}                             |
+------------------------------------------------------------------+
| 基本信息：任务号、节点名、计划名、IP 组、赛事（competitionName）      |
|           状态 Tag（dict_sop_node_status）· **不展示 SLA**（ADR-080）|
| 工作任务来源时 · 备注一行 workTaskRemark（多段「赛事-营销计划-…」）   |
+------------------------------------------------------------------+
| 执行说明（只读 · executionInstruction ← oa_sop_node.instruction_text）|
+------------------------------------------------------------------+
| 节点参考附件（只读 · attachments[] ← SOP 节点 attachment_urls JSON） |
| 执行人上传附件（可增删 · userAttachments · 见 API §附件上传）        |
+------------------------------------------------------------------+
| [nodeType=CONTENT_GENERATION]                                     |
|   关联内容摘要（linkedContent：id/title/status/documentType）       |
|   Badge：aiGenerateStatus 生成中/失败+原因+「重试」                   |
|   [进入内容创作] → ContentEditDialog（taskId，非菜单路由）            |
| [nodeType=CONTENT_PUBLISH] 占位文案（BLK-M2-009 · 本期不发明字段）    |
| [nodeType=NORMAL] 工作说明 Textarea（deliverables · 完成必填）      |
+------------------------------------------------------------------+
| 多 IP 组并行：ipGroupTabs[]（仅 sibling>1 时 Tab 切换）             |
+------------------------------------------------------------------+
| [保存]  [提交审核]（条件）  [完成]                                   |
+------------------------------------------------------------------+
```

#### 字段（GET `TaskExecuteVO` 映射 · 只读除非注明）

| 字段 | 展示 | 来源/说明 |
|------|------|-----------|
| id | 任务号 | `oa_task.id` |
| nodeName | 节点名 | SOP `node_name`（ADR-080，不得被计划名覆盖） |
| nodeType | 隐藏驱动 UI 区 | `CONTENT_GENERATION` / `CONTENT_PUBLISH` / `NORMAL` |
| planName | 计划 | |
| ipGroupName | IP 组 | ADR-070 |
| competitionName | 赛事 | 单场摘要；合并任务见备注 |
| workTaskRemark | 备注一行 | ADR-075/080 格式 |
| executionInstruction | 执行说明 | BLK-M2-008 已决 |
| attachments | 只读链接列表 | SOP 预置参考附件 |
| userAttachments | 上传列表 | 执行人上传，save 时持久化 |
| linkedContent | 内容摘要区 | id、title、status、documentType、aiGenerateStatus、aiGenerateError |
| ipGroupTabs | Tab | 同计划同节点同赛事多 IP 组（API-M2-计划管理 §11） |
| deliverables | 可编辑 | 仅 NORMAL 节点；POST save/complete |

#### 按钮与 API

| 控件 | 条件 | 调用（IMS canonical） |
|------|------|------------------------|
| 进入内容创作 | `nodeType=CONTENT_GENERATION` | 打开编辑抽屉；`taskId` 必填（UX §5.2 模式 B） |
| 保存 | 始终 | `POST /admin-api/ims/content/task/{id}/execute/save` |
| 提交审核 | CG 且 `linkedContent.status` ∈ `DRAFT`,`REJECTED` | `POST /admin-api/ims/content/{contentId}/submit-review` |
| 完成 | 见状态 | `POST /admin-api/ims/content/task/{id}/execute/complete` |
| 重试 AI | `aiGenerateStatus=FAILED` | `POST /admin-api/ims/content/{contentId}/retry-ai-generate` |

#### 状态与错误码

| 状态 | UI |
|------|-----|
| 无 linkedContent | 提示「请先进入内容创作」（confirm 后通常已有 DRAFT · ADR-077） |
| 内容未达 `PENDING_PUBLISH` 及之后 | **完成** disabled + Tooltip「内容须审核通过后方可完成任务」（ADR-079 · STATE-M2 §1） |
| NORMAL 未填 deliverables | 完成 disabled 或提交时 **1500**「请填写工作说明」（并入域保留现网语义 · BR-307） |
| AI QUEUED/GENERATING | Badge「生成中」 |
| AI FAILED | Badge「失败」+ 原因 + 重试 |
| 非 assignee / 非 IN_PROGRESS | **1501**（执行人非本租户有效成员，对齐 API-M2）/ **1504** |
| 完成成功 | Toast → 返回 `/ims/content/task` |

内容域业务校验（玩法/文档类型等）在内容抽屉保存时返回 **1500**；租户/权限 **1504**/**403**；强关联实体缺失 **1500**。**节内 1500~1502 语义以《错误码映射表（附录）》§3 及现网 `API-M2-计划管理.md` §错误码为准**（2026-10-03 对齐）。

---

### `/ims/content/list`（P-M2-006/007 · 含玩法区）

| 按钮 | 新增、导出、批量删除/提交/转知识库、行内提交审核 |
| 抽屉字段 | 模式 A/B 见 UX §5.2；RichText/版式/AI 排版/视频生成；Football 同步状态 |
| 状态 | `DRAFT`/`PENDING_*`/`REJECTED`/审核 steps |

#### 玩法区 matchScheme / amphipoda（ContentEditPanel）

> **来源**：`docs/product/UX-M2-内容生产-amphipoda对齐增量.md` §2～3 · `docs/engineering/API-M2-内容生产-amphipoda对齐增量.md` §1.2 · ADR-076/077。

**位置**：内容编辑抽屉「赛事与玩法」区（替换原单场 MatchSelect + `dict_scheme_type` 主 SSOT）。

| 项 | 规格 |
|----|------|
| Tab | 竞足(1) / 传足(2) / 北单(3) / 足球(4) → `matchType` |
| Tab 内 | 日期筛选 + 比赛多选列表（赛程 WebAPI，禁止手输非法 ID） |
| 已选区 | N 场卡片：队名、玩法标签、`mainPlayMethod`、删除 |
| 确定玩法 | 「确定玩法」→ `panduan=true`；切换 Tab **清空**未确认玩法（U1） |
| AI | ≥1 场可点 AI；`matchPlays` **可空**（ADR-077 D10）；0 场 AI disabled +「请先选择比赛」 |
| 传足 | 已选场次数 **等于** 套餐要求（否则 **1500**） |
| 持久化 | `matchType` + `matchScheme[]`（`MatchSchemeItemVO`）+ 可选 `competitionIdsJson` |
| 任务预填 | 模式 B：`task.competitions[]` 预填 scheduleId/队名；Banner「已从任务带入 N 场…」（UX §3.1） |
| 列表列 | `matchSummary` 或「N场：首场…」（UX §5） |
| 隐藏 | `dict_scheme_type` 折叠为「AI 辅助标签（可选）」，**非**玩法 SSOT |

**MatchSchemeItemVO 元素**（保存/回显，与 Football 同构）：`matchId`、`scheduleId`、`className`、`homeName`、`awayName`、`matchTime`、`matchPlays[]`（`playId/result/resultType/type/opinion` 可空数组）、`mainPlayMethod`。

---

### `/ims/content/review`（P-M2-008 · LayoutViewer 只读）

> **来源**：UX-M2 §6、§8.4 · amphipoda 增量 §5 · ADR-017。

| Tab | 一级审核 / 二级审核（随 review-config；均未开 → 提示直接发布） |
| 表格 | 待审内容：id、标题、matchSummary/玩法摘要、审核阶段 |
| BTN-VIEW | 打开只读抽屉（**必须先查看再结论** · 产品走查） |

#### 审核只读抽屉（BTN-VIEW）

| 区域 | 行为 |
|------|------|
| 元信息 | 标题、作者、IP 组、documentType、contentType、审核 steps（`{角色名}：{用户1、用户2}`） |
| 玩法区 | **只读**：当前 matchType Tab + 场次列表 + 玩法摘要（amphipoda 增量 §5） |
| 正文 | 有 `layout_html` → **`LayoutViewer readOnly`**（约 677px 宽）；无则 `body` 纯文本 fallback（UX §8.4） |
| 付费/免费 | 双栏只读（与编辑态同结构，全部 disabled） |
| Football | 同步状态条只读 |

**禁用（相对编辑抽屉）**：RichText/LayoutEditor、一键排版、AI 排版、AI 内容/视频、保存、提交审核、玩法 Tab 切换与确定玩法、模板套用、图片上传 — **全部不可操作**。

**可用**：BTN-APPROVE / BTN-REJECT（待审 + 有审核权限）；关闭抽屉。

| 操作 | API |
|------|-----|
| 通过/驳回 | `PUT /admin-api/ims/content/review/{reviewNo}/conclusion`（R8/R4；与主契约 CONTENT-005 合并实现） |

---

### `/ims/content/layout-template`（P-M2-013~015）

| 按钮 | 导入向导、编辑、预览（FR-M2-005） |

---

## OPS 前后端对照（2026-10-02 · ADR-IMS-003）

> **网关前缀（现网 OPS runtime）**：`/admin-api/ops/**`（前端 `#/api/ops/client` 相对路径 `/ops/...`）。  
> **IMS canonical** 仍为 `/admin-api/ims/content/**`（见补充 API 契约）；下表 **仅** 用于 UX/按钮/状态对齐，禁止 IMS 新代码直连 OPS HTTP（IR-03）。  
> **Java 根路径**：`football-backend-saas/football-module-ops/football-module-ops-server/src/main/java/football/module/ops/controller/`  
> **Vue 根路径**：`football-front/apps/web-ele/src/views/ops/`

| IMS 路由 | 用户主路径（口语） | Vue SFC | Java Controller（类名） | 前端 API 封装 |
|----------|-------------------|---------|-------------------------|---------------|
| `/ims/content/sop` | 维护 SOP 模板、待审核节点 | `production/sop/index.vue` · `sop/edit.vue` | `sop/SopTemplateController` · `sop/SopNodeController` | `#/api/ops/sop.ts` |
| `/ims/content/plan` | 计划向导 / 计划列表 | `production/plan/index.vue` · `detail.vue` | `plan/ContentPlanController` | `#/api/ops/plan.ts` |
| `/ims/content/work-task` | 登记矩阵 → 确认出任务 / 撤回 | `production/work-task/index.vue` · `WorkTaskMatrixTable.vue` | `worktask/WorkTaskController` | `#/api/ops/workTask.ts` |
| `/ims/content/task` | 我的/全部任务 → 执行 | `production/task/index.vue` · `all.vue` · `execute.vue` · `TaskExecutePanel.vue` | `task/TaskController` | `#/api/ops/task.ts` |
| `/ims/content/list` | 内容 CRUD、上下架、发布、转知识库 | `production/content/index.vue` · `ContentEditPanel.vue` · `AiContentDrawer.vue` | `content/ProductionContentController` · `aicontent/AiContentController` | `#/api/ops/content.ts` · `aiContent.ts` |
| `/ims/content/review` | 一/二级审核队列 | `production/content/review.vue` · `sop/review.vue` | `content/ProductionContentController`（review 子路径） | `#/api/ops/content.ts` |
| `/ims/content/layout-template` | 公推模板库 | `production/layout-template/index.vue` · `edit.vue` · `import.vue` | `layout/LayoutTemplateController` | `#/api/ops/layoutTemplate.ts` |
| `/ims/content/task/:id/execute` | 全页执行：附件、关联内容、完成门禁 | `production/task/TaskExecutePanel.vue` | `task/TaskController` + `content/ProductionContentController` | `#/api/ops/task.ts` · `content.ts` |

### 状态与行内按钮（以 Vue 为准 · 映射 IMS）

| 页面 | 状态/字典 | 行内/顶栏按钮 → OPS API（method + path） |
|------|-----------|------------------------------------------|
| 内容管理 | `dict_content_status`：`DRAFT` / `REJECTED` / `PENDING_*` / `PENDING_PUBLISH` / `PUBLISHED_DRAFT` / `PUBLISHED` | 顶栏：新增 `POST /ops/content/create`、导出、批量删/提审/转知识库；行：`PUT update`、删 `DELETE /{id}`、提审 `POST /{id}/submit-review`、上架 `POST /{id}/shelf-on`、下架 `POST /{id}/shelf-off`、预发布 `POST /{id}/publish-draft`、正式发布 `POST /{id}/formal-publish`、转知识库（content API） |
| 我的任务 | `dict_sop_node_status` | 执行 → `GET /ops/task/{id}/execute`；完成 `POST …/complete` 或 execute/complete；关联内容提审 `POST /ops/content/{id}/submit-review`（`task/index.vue` 条件按钮） |
| 任务执行页 | ADR-079 完成门禁 | 保存 `POST …/execute/save`；上传 `POST …/execute/upload`；完成 `POST …/execute/complete`；内容重试 AI `POST /ops/content/{id}/retry-ai-generate` |
| 工作任务 | sheet 状态 | `GET /ops/work-task/sheet/get-or-create` · `PUT …/save` · `POST …/confirm` · `POST …/withdraw` · 合并/取消合并 execution |
| SOP | 模板启停 | `GET /ops/sop/template/list` · CRUD template/node · `POST …/validate-dag` |

**本地仓库说明**：`WorkTaskController.java` 已检入；其余 Controller 类名来自 `docs/delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md` 与 `docs/engineering/API-M2-*`，与现网 football-module-ops 一致。

---

## 操作序列（OPS 源码 → IMS 原型 · 2026-10-02）

> 原型键 = `一体化管理/UI原型/IMS-完整系统-UI原型.html` 内 `PAGES.*` / 同名 handler。API 路径为现网 OPS `/admin-api/ops/**`（IMS runtime 映射见上文 IR-03）。

### `/ims/content/plan`（`contentPlan`）

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 「新增计划」→ 保存草稿 | `football-front/apps/web-ele/src/views/ops/production/plan/index.vue` 弹窗向导 | `POST /ops/plan/create` → `OPS_PLANS[]` status=`DRAFT` |
| 2 | 草稿行「启动」 | `handleStart` | `POST /ops/plan/{id}/start` → `IN_PROGRESS` · 追加 `OPS_TASKS` |
| 3 | 执行中「申请终止」→ 填原因 | `handleTerminate` | `POST /ops/plan/{id}/terminate` → `TERMINATE_PENDING` |
| 4 | 「批准终止 / 驳回终止」 | `handleApproveTerminate` · `handleRejectTerminate` | `POST …/terminate/approve` · `…/reject` |
| 5 | 草稿「删除」 | `handleDelete` | `DELETE /ops/plan/delete?id=` → 移除行 |
| 6 | 「详情」抽屉 | `handleView` · `plan/detail.vue` | `GET /ops/plan/get` |

### `/ims/content/layout-template`（`contentLayout`）

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 「导入向导」 | `production/layout-template/import.vue` | `POST /ops/layout-template/import-url` · `import-paste` → `OPS_LAYOUTS` DRAFT |
| 2 | 草稿行「发布」 | `layout-template/index.vue` `handlePublish` | `POST /ops/layout-template/{id}/publish` → `ENABLED` |
| 3 | 启用行「停用 / 重新启用」 | `handleDisable` · `handleEnable` | `POST …/disable` · `…/enable` |
| 4 | PRESET 行「复制」 | `handleCopy` | `POST …/{id}/copy` → 新 DRAFT 行 |
| 5 | 非 PRESET「删除」 | `handleDelete` | `DELETE /ops/layout-template/{id}` |

### `/ims/content/sop`（`contentSop`）

> **v2.6.33：SOP 模板审核整体移除**（用户决策「内容生产不需要 SOP 审核」）——原「待审核任务」Tab / 审核通过 / 驳回 / `sop/review` 端点与 `contentSopReview` 菜单一并下线；模板保存后可直接启用/停用。

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 模板列表启停 Switch | `handleStatusChange` | `PUT /ops/sop/template/status` → `SOPS[].on` |
| 2 | 编辑 → DAG 校验 →「保存为新版本」 | `sop/edit.vue`（路由跳转） | CRUD template/node · 原型 `sopDagSave()` |

### `/ims/content/work-task`（`contentWork` · 登记 Tab）

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 「保存」 | `work-task/index.vue` sheet save | `PUT /ops/work-task/sheet/save`（`WorkTaskController.java` L47-49） |
| 2 | 勾选 ≥2 行 →「合并执行」 | merge 按钮 | `POST /ops/work-task/sheet/merge-execution` → `executionGroupId` |
| 3 | 行「确认出任务」 | confirm 行/顶栏 | `POST /ops/work-task/sheet/confirm` → `WT_ROWS[].generatedTaskId` + `OPS_TASKS` + 内容 `DRAFT` |
| 4 | 「撤回」 | withdraw | `POST /ops/work-task/sheet/withdraw` → 删任务/草稿（CONTENT-110） |

### `/ims/content/task` + `/ims/content/task/:id/execute`（`contentTask` · `contentTaskExecute`）

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 「执行」 | `task/index.vue` | `GET /ops/task/{id}/execute` → 全页执行 |
| 2 | 「进入内容创作」→ 保存 | `TaskExecutePanel.vue` + `ContentEditPanel.vue` | `POST /ops/content/create|update` |
| 3 | 「提交审核」 | 执行页/内容抽屉 | `POST /ops/content/{id}/submit-review` → `PENDING_FIRST_REVIEW` |
| 4 | 「完成」 | ADR-079 门禁 | `POST …/execute/complete` · 须内容 `PENDING_PUBLISH+` |

### `/ims/content/list` + `/ims/content/review`（`contentList` · `contentReview`）

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 编辑 → 提交审核 | `production/content/index.vue` | `submit-review` → 审核队列 |
| 2 | 审核 Tab 一级「通过」 | `production/content/review.vue` | `review/conclusion` → `PENDING_SECOND_REVIEW` |
| 3 | 二级「通过」 | 同上 | → `PENDING_PUBLISH` |
| 4 | 预发布 / 正式发布 / 上·下架 | 行内条件按钮 | `publish-draft` · `formal-publish` · `shelf-on/off` |

**本地源码（wd 已检入）**：Vue 根目录 `football-front/apps/web-ele/src/views/ops/production/`（含 `plan/index.vue` · `work-task/index.vue` · `task/index.vue` · `content/index.vue` · `content/review.vue` · `layout-template/index.vue` · `sop/edit.vue` 等）；Java 现网类名见上表，wd 仓库内 ops Controller 以 `WorkTaskController.java` 等为部分样例，完整清单见 `docs/engineering/API-M2-内容生产.md`。
