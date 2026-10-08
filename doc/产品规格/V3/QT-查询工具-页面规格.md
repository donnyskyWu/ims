# QT - 查询工具 页面规格（V3 增量 · 走查 #18）

> **模块范围**：QT-001 三模式统一查询壳（P0：**DRILL + TRACE** 可见；**FLAT 默认隐藏** 避免与 M6 自定义查询重叠）。  
> **权威依据**：《IMS完整产品需求文档》v2.6.14 §17c；《IMS-查询工具-三模式统一引擎-产品方案-20260930》（选项 A · 走查 #18 已采纳）；《QT-查询工具-API契约.md》。  
> **不替代**：《BI0-指标查询报表-页面规格》P4 自定义查询 · 《BI-数据分析-页面规格》P2 预览与下钻 · 《DC-数据中心-页面规格》P1 穿透查询（三 L3 **保留**）。

## 0. SSOT 与元数据

### 0.1 导航（走查 #18 · SSOT = 完整 PRD v2.6.14）

**侧栏路径**  
- **数据决策 → 数据分析 → 查询工具**（本规格 QT-001）  
- 同组并列：**自定义查询**（BI0 P4）· **预览与下钻**（BI P2）· **穿透查询**（DC P1）· **组织人效**（EFF）

| 项 | 值 |
|----|-----|
| 路由 | `/ims/analysis/query-tool`（**列表为默认落地**）；执行页 `/ims/analysis/query-tool/run/{templateCode}` |
| 权限码（建议 · **待 ADR 落库**） | `ims:analysis:query-tool:query`（列表/执行）· `ims:analysis:query-tool:manage`（新增/编辑/发布/删除） |
| 页面形态 | **管理优先**：默认 = **查询模板列表**（工具栏 + 表格 + 行操作 + 空态）；新增/编辑 = **720px 抽屉向导**（6 步）；执行 = **执行页/执行视图**（复用结果壳） |
| 向导步骤 | ① 选类型（DRILL｜TRACE）② 基本信息 ③ 配置载荷（DrillTemplate.levels[] / TraceTemplate.pathSteps[]）④ 展示与来源（根层入口 / 展示项）⑤ 预览试跑 ⑥ 完成（存草稿 / 保存并发布） |

**边界**  
- **COLLECT 元数据 SSOT**：实体/字段/条件类型仅在 **数据采集 → 元数据维护**（COLLECT P4m）维护；本页 **只读** 消费 `entity/{code}/fields`（1261 未映射 → 链 P4m，与 BI0 P4 一致）。  
- **TRACE 运行时**：P0 **编排** 现网 DC 契约 `POST /dc/trace/query` 等（TracePlan），**禁止** 页内发明 graph/lineage REST。**跨层穿透由 QT 服务端在一次 run 内持有 `pathSteps[]` 逐步调用 DC Service 方法**，DC 契约 **不扩参**（DC 页直调仍为单步）；详见 API 契约 §3.2。  
- **DRILL 运行时**：P0 原型 + 规格；**P0 仅交付「配置 + 规格」，run 依赖「多层 JOIN 引擎」切片（P2）**，前此以 **stub / 末层降级** 承接；与 BI P2 **ReportPlan** 不合并 L3。  
- **DRILL ≠ 预览与下钻（C1）**：**查询工具 DRILL** = 模板级多层探索（`DrillTemplate` + `DrillPlan`）；**预览与下钻 BI P2** = 已发布报表的维度下钻（`layoutConfig` + `ReportPlan`）。**报表式维度下钻请用 BI P2**；两者 **互跳 + 远期共用 DrillSpec 元数据**，不合并 L3。  
- **FLAT**：与 M6 QueryBuilder **同形** `builderConfig`（P1+）；P0 **隐藏**（产品方案 Q5 默认），**不出现在向导「选类型」** 中，点提示深链「自定义查询」。  
- **已发布模板编辑（2026-10-04 拍板）**：已发布模板编辑**默认「直接改」**——向导保存即 `PUT template/{templateCode}` 覆盖已发布版本，**不另存草稿版本**；如需保守可先「取消发布」再改（列表行内提供）。

**兼容**：无 `go()` 废止键；深链 `queryTool` 可选（原型键）。

### 0.2 与 COLLECT / BI0 / DC 交叉引用

| 维度 | COLLECT P4m | 查询工具 QT | BI0 P4 自定义查询 |
|------|-------------|-------------|-------------------|
| 写映射 | ✅ | ❌ | ❌ |
| 读实体字段 | 源 | ✅ DRILL/FLAT | ✅ |
| 导航 | 数据采集 | 数据分析 | 数据分析 |
| 文档 | 《COLLECT-数据采集-页面规格》§ P4m | 本文 | BI0 § P4 |

---

# P1 查询工具工作台（QT-001）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/ims/analysis/query-tool` |
| 页面级别 | 二级（**列表 / 执行** 双视图 + 新增·编辑 抽屉向导） |
| 前置依赖 | COLLECT 至少一个 **已映射** 实体（seed-analytics）；TRACE 依赖 DC 宽表 seed |
| 权限 | R1/R3/R4/R9 全量；R5/R6 本域；R7 本人链路（TRACE 对齐 DC 矩阵） |
| 用户 | 数据分析师 R9、运营总监 R4、财务 R3 |

## 2. 页面布局（ASCII）

> **原型交互 demo 范围（`IMS-完整系统-UI原型.html` · `.page-query-tool`）**  
> P0 规格页以 **可点击 mock** 演示：**列表**（`queryToolListHtml`：工具栏 + 6 列表格 + 行操作 + 空态）→「+ 新增查询模板」打开 **720px 抽屉向导**（`queryToolOpenWizard`，6 步 stepper）→ 第③步内嵌与旧「查询配置」相同的 `DrillTemplate.levels[]` / `TraceTemplate.pathSteps[]` 编辑器（复用 `queryToolDrillConfigHtml` / `queryToolTraceConfigHtml`）→ 第⑤步试跑复用 **QueryResultPanel**。行内「执行」切到 **执行视图**（`queryToolRunPageView`，`state.tab.queryToolView='run'`），复用同一结果壳。DRILL：`state.queryTool.drill.levels[]`；TRACE：`state.queryTool.trace.pathSteps[]`（depth 由步数推导）。向导态由 `state.queryTool.wizard{step,editCode}` 驱动；`queryToolRefresh()` 在抽屉打开时只重绘 `#qtWizBody` 与 `#dr-foot`，**不整页重渲**。

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 查询模板                                              [+ 新增查询模板]      │
│  qbar：名称 [___] 状态[全部▾] 模式[全部▾]                                   │
├──────────────────────────────────────────────────────────────────────────┤
│ 查询名称 │ 类型 │ 状态 │ 更新时间 │ 菜单路径 │ 操作                         │
│ IP组周产出│DRILL │已发布│ 09-30…  │ 未挂菜单 │ 执行 编辑 取消发布 发布到侧栏 删除│
│ …                                                                         │
├──────────────────────────────────────────────────────────────────────────┤
│ pagination · 页脚：列表为默认落地 · 行内「执行」进入执行页                    │
└──────────────────────────────────────────────────────────────────────────┘

【新增/编辑 · 720px 抽屉向导】                       【执行视图（行内「执行」）】
┌────────────────────────────────────┐             ┌───────────────────────────┐
│ ①选类型 ②基本信息 ③配置载荷 ④展示与来源 │             │ ← 返回模板列表   执行查询  │
│ ⑤预览试跑 ⑥完成      （stepper 可跳）  │             │ [QueryResultPanel]        │
│ ────────────────────────────────── │             │  面包屑/层标签 · 下一层      │
│ ③ DRILL: levels 表（实体/展示列/Join）│             │  列表|图表 Tab · queryCostMs│
│ ③ TRACE: pathSteps 表 + 入口/源头     │             └───────────────────────────┘
│ ⑤ 试跑 → 内嵌 QueryResultPanel        │
│ 底部：上一步 / 存草稿 / 下一步 / 保存并发布│
└────────────────────────────────────┘
```

> **旧 IA 变更（2026-10-04）**：原「查询配置 \| 查询记录」两 L1 Tab 已废弃。**配置不再常驻页面**，改由「+ 新增查询模板」进入的 **720px 抽屉向导**承载；「查询记录」提升为 **默认落地列表**（去 Tab 化，直接是页面主体）。

## 3. 模式行为（产品）

| 模式 | P0 UI | P0 运行 | 配置载荷 |
|------|-------|---------|----------|
| **DRILL** | ✅ 向导第③步 levels 表 | **`POST …/query-tool/run`** 一次返回；UI 可逐步展示层，**不**轮询 job | `DrillTemplate.levels[]` |
| **TRACE** | ✅ 向导第③步 pathSteps 表 + 第④步入口 | **同上 run**；服务端逐步 DC trace，前端 **不**分步 POST | `TraceTemplate.pathSteps[]` + 入口 |
| **FLAT** | **隐藏**（向导选类型不出） | P1 复用 M6 builderConfig | `FlatTemplate` |

### 3.1 新增 / 编辑抽屉向导（720px · 2026-10-04）

**入口**：列表页「+ 新增查询模板」（`queryToolOpenWizard()`，`step=0`）· 行内「编辑」（`queryToolOpenWizard(code)`，**直接落到 `step=2`**，熟手免走 1~2）。

**六步**（`state.queryTool.wizard{step,editCode}`；顶部 stepper 显示「完成/当前/待办」三态）：

| 步 | 内容 | 校验 / 说明 |
|----|------|-------------|
| ① 选类型 | 卡片二选一：**分级下钻 DRILL** / **逐级穿透 TRACE**；含场景说明与要点 | `editCode` 非空时类型**按模板锁定**，点击提示不可改；FLAT **不在**类型中（提示深链「自定义查询」） |
| ② 基本信息 | 模板名称（必填 1–50）/ 查询类型（只读）/ 描述（可选） | 名称必填校验；已发布模板提示「**直接改**」 |
| ③ 配置载荷 | DRILL：levels 表（实体 / Join 至下一层 / 关联键 / 展示列 chip，≤5 层）；TRACE：pathSteps 表（实体 / 关联边→下一层 / 下一层只读，≤6 层）+ 路径预览 | 进第④步前校验：DRILL ≥1 层、TRACE ≥2 层 |
| ④ 展示与来源 | DRILL：结果展示项（默认视图 列表/图表 · 图表类型 · 排序）；TRACE：**根层入口**（`GET /dc/trace/entry` 选源头）+ 呈现方式（分栏/关系图/明细表） | TRACE 进第⑤步前须选源头 |
| ⑤ 预览试跑 | 「▶ 试跑一次」→ `POST …/query-tool/run`，内嵌 **QueryResultPanel** 展示逐层结果 | TRACE 未选源头 / 缺关联边时拦截并提示 |
| ⑥ 完成 | 汇总（类型 · 层数 · 是否已试跑）+ 回填模板名/状态 | 底部动作：**存草稿**（`POST/PUT template`）· **保存并发布**（`…/publish`） |

**行为细则**
- **已发布模板编辑 = 直接改**：`PUT template/{templateCode}` 覆盖已发布版本，**不**新建草稿副本；如保守可先列表「取消发布」。
- **存草稿（第③~⑥步可用）**：新建→`POST template`（生成 `templateCode` 并回填 `editCode`）；已有→`PUT template/{code}`。**抽屉保持打开**，仅素材落库。
- **切换类型不清空对侧**：DRILL/TRACE 草稿分键保存（`drill.levels[]` 与 `trace.pathSteps[]` 独立）。
- **抽屉内刷新**：向导内所有控件回调经 `queryToolRefresh()`，抽屉打开时只重渲 `#qtWizBody` + `#dr-foot`（避免整页重渲丢失抽屉态）。

## 4. TypeScript（页面态 · 非已批准 REST）

```typescript
type QueryMode = 'FLAT' | 'DRILL' | 'TRACE';

interface QueryToolUiState {
  /** 页面视图：list=默认列表 · run=执行视图；配置走抽屉向导（见 wizard） */
  view: 'list' | 'run';
  mode: 'DRILL' | 'TRACE';           // P0 无 FLAT
  templateCode?: string;
  /** 新增/编辑抽屉向导态 */
  wizard: { step: 0 | 1 | 2 | 3 | 4 | 5; editCode: string };
  drill: {
    rootEntityCode: string;
    levels: Array<{
      levelIndex: number;
      label: string;
      entityCode: string;
      /** 至下一层的 Join 边（末层可无） */
      drillToNext?: { leftKey: string; rightKey: string; joinType?: 'LEFT' | 'INNER' };
      displayFields: string[];
    }>;
    activeLevel: number;
  };
  trace: {
    /** 用户显式搭建的穿透链（每层 entity + 至下一层 relationId；depth 由步数推导，非固定字段） */
    pathSteps: Array<{ entity: string; relationToNext?: string }>;
    /** 入口（根层源头） */
    entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP';
    entryId?: string;
    keyword: string;
    /** 呈现：分栏/关系图/明细表（对齐 DC P1 GRAPH|DETAIL + 分栏；不含独立 depth 下拉） */
    presentation: 'GRAPH' | 'DETAIL';
  };
  resultTab: 'list' | 'chart';
}
```

> **⚠️ 一致性注记（2026-10-04 订正）**：`trace` 旧形状曾含 `depth: number` + `presentation`（对齐早期 TraceTemplate），与 §2/§3 的 **`pathSteps[]` 链**（depth 由步数推导）冲突。本版已改为 **`pathSteps[]`** 形状；`depth` 不再是独立字段。**D1 执行载体**与 **D5 `queryCostMs` 口径**见《QT-查询工具-API契约》§3.2。

## 5. 交互细则

| # | 规则 |
|---|------|
| U1 | 切换 DRILL/TRACE **不清空** 对侧已填草稿（分 `state.queryTool.drill/trace` 子键） |
| U2 | 实体下拉仅 **MAPPED** 实体；空列表展示 1261 文案 + 链 `/ims/collect/metadata` |
| U3 | DRILL 「下钻下一层」更新面包屑与 `activeLevel`；末层禁用下钻 |
| U4 | TRACE 「执行」须先选 entryType + 有效 entryId（搜索来自 `GET /dc/trace/entry`）；提交 **`POST …/query-tool/run`**（同步，无 async 轮询 UI） |
| U4b | DRILL 「执行」同上；页脚 hint：**多层下钻为服务端一次 run 内逐级调用，非 1262 异步任务** |
| U5 | 结果区 **必须** 展示 `queryCostMs`；**口径**：DRILL = 本次 run 总耗时；**TRACE = 取末步（最后一步）单次 DC `queryCostMs`，非各步相加**（相加会与 BR-205 P95<3s 口径失真）。>3000ms 橙色（BR-205） |
| U6 | **禁止** 提供「替代自定义查询」为唯一入口的文案；页内可深链 `bi0Query` |
| **U7** | **列表为默认落地**（`view='list'`）：**单列表** 展示 `state.queryTool.templates[]`；列含 **类型**（DRILL/TRACE）、**状态**（草稿/已发布）、更新时间、**菜单路径**（未挂菜单 / 已挂 L3）；**去 L1 Tab 化**（旧「查询配置 \| 查询记录」两 Tab 废弃） |
| U8 | qbar **筛选**：名称 keyword + 状态（全部 \| 草稿 \| 已发布）+ 模式（全部 \| DRILL \| TRACE）· 对应 API `status`/`mode` 参数 |
| U9 | 行操作齐全：**执行 · 编辑 · 发布/取消发布 · 发布到侧栏/撤销侧栏 · 删除**；删除须 ConfirmDialog；发布到侧栏须已发布（否则提示） |
| **U10** | 「+ 新增查询模板」/ 行内「编辑」→ 打开 **720px 抽屉向导**（§3.1）；编辑**直接落 `step=2`**，新建**从 `step=0`**；已发布编辑 = **直接改** |
| **U11** | 行内「执行」→ 切 **执行视图**（`view='run'`，`queryToolRunPageView`），复用 **QueryResultPanel**；顶部提供「← 返回模板列表」 |
| U12 | 向导第 1 步类型卡片：DRILL/TRACE 二选一（含场景说明）；`editCode` 非空时类型锁定；FLAT 不出现在类型中 |

## 6. 分期与 BLOCKED

| 阶段 | 页面交付 |
|------|----------|
| P0 | IA（列表 + 720px 抽屉向导）+ 本规格 + 原型 + DRILL 线框 + TRACE 编排 DC |
| P1 | FLAT **可选向导类型** + SqlPlan 与 M6 编排 |
| P2 | DRILL 模板 CRUD + run（B2 已拍板 · 同步 run） |
| P3 | MenuSeed 发布 L3 · TraceTemplate 用户可配链（ADR） |

| BLOCKED | 说明 |
|---------|------|
| run 超时策略 | 仅同步等待 + 1181/超时提示；**禁止** QT run 1262 |
| 发布挂菜单 | FR-QT-007 · P3 |
| FLAT 默认展示 | Q5 已决：**P0 隐藏**（向导选类型不出现） |

## 7. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-30 | 走查 #18：选项 A 新 L3；P0 DRILL+TRACE；FLAT 隐藏；COLLECT 只读引用 |
| 2026-09-30 | 原型 `.page-query-tool` 交互 demo：Drill levels[] / TRACE 内嵌 DC 分栏；§2 注明 mock 范围 |
| 2026-09-30 | 原型 TRACE 改为 pathSteps[] 配置链 + 运行态 runDepth 逐层穿透；结果壳对齐 bi0 QueryResultPanel |
| 2026-09-30 | FR-QT-008~011：L1 Tab 查询配置/已保存/已发布；模板闭环 mock（edit/publish/unpublish/delete） |
| 2026-10-01 | FR-QT-008 修正：**查询配置 \| 查询记录** 两 Tab；草稿/已发布为 **同一 records 列表 status 列 + 筛选**，非两个 L1 |
| 2026-10-01 | B2：统一 run 同步编排；DRILL/TRACE 执行 hint；禁止 async 轮询 UI |
| 2026-10-04 | **一致性订正**（审查《查询工具与下钻穿透-一致性与完整性审查-2026-10-04》）：§4 类型 `trace.depth/presentation` → **`pathSteps[]`**（D7）；§0.1 边界补 **C1（DRILL≠BI P2）** 与 **TRACE 跨层走 QT 服务端 run（DC 不扩参）**、**DRILL run 依赖 P2 多层 JOIN**（D1）；§5 U5 明确 **`queryCostMs` 口径（TRACE 取末步，非相加）**（D5）|
| **2026-10-04** | **IA 改造：管理优先（列表 + 抽屉向导）**。旧「查询配置 \| 查询记录」两 L1 Tab **废弃**；**默认落地 = 查询模板列表**；新增/编辑 = **720px 抽屉 6 步向导**（选类型→基本信息→配置载荷→展示与来源→预览试跑→完成）；**执行解耦为执行视图**（行内「执行」）；**已发布模板编辑 = 直接改**。§0.1/§1/§2/§3.1/§4/§5/§6 同步；接口（run / template CRUD / menu-seed）**不变**。 |
