# BI - 数据分析 页面规格（V3 增量，17 模块，第 29~36 周）

> **模块范围**：BI-001 自助报表设计 / BI-002 多维查询下钻 / BI-003 看板订阅分享。
> **模块定性**：**补齐类**——指标管理/自定义查询已完成（✅ 不重复建设），本次仅补齐自助报表/下钻/订阅分享能力。
> **权威依据**：《IMS第三期PRD-V3.md》5.7~5.9；《BI-数据分析-API契约.md》（20 接口，1191~1197 错误码段）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**（4 页）：P1 自助报表设计器（Web，**三栏自由拖拽**）｜P2 报表预览与下钻（Web，含单元格穿透）｜P3 订阅与分享管理（Web + 分享落地页）｜P4 查询性能监控（Web，R1/R9）。
> **本次修订（v2.6.26 · 2026-10-03）**：对标 `参考文件/DW-PRD-Phase1.md` §9.9 + `DW-UI-Prototype-Phase1.html`，P1 **由「表单式四区 + 静态画布预览」升级为「三栏可拖拽设计器」**（组件库四类 21 组件 / 图层面板 / 属性三区 / 组件级数据源与动态参数 / 联动·跳转·循环依赖 / 发布链接密码与有效期 / 导入导出 JSON / 分类树与缩略图 / 发布快照 / 全屏大屏）。落库为 `ims_` 前缀新表，DW API/方言不映射。详见 §10。

## 0.1 导航（走查 #21 · v2.6.27 · SSOT = 完整 PRD v2.6.27）

**侧栏路径（本模块）**  
- **数据报表** L2（**仅两叶**）：**报表管理**（`biList` · 编辑/新增进入设计器）· **报表中心**（`bi0Report` · M6 八张标准报表；原「标准报表」v2.6.27 更名）  
  - **报表设计**（`biDesign`）**转隐藏路由** `/ims/bi/report/designer`，不出侧栏，由报表管理 [+ 新建报表] / [编辑] 进入  
  - **大屏** 为报表类型 `DASHBOARD`，无独立菜单（原「大屏配置」菜单退役，`bi0Screen` 归一化到 `biList`）  
- **数据指标** L2：指标管理 · 指标分析  
- **数据分析** L2：**查询工具**（QT-001 · `/ims/analysis/query-tool` · 走查 #18）· 自定义查询（BI0 P4）· **预览与下钻**（本规格 P2）· 穿透查询（DC）· 组织人效（EFF 页内 Tab）  

**边界**：M6 八张标准报表在 **数据报表 · 报表中心**；场次链路 → **穿透查询**；作品/账号监测 → **18 / 内部分析 / 竞品分析**。  
**兼容**：`go('bi')` → 报表管理；`go('biShare')` → 报表管理；`go('bi0Screen')`/`go('bi0ScreenConfig')` → 报表管理；`go('biSession')` → `dc`；`go('biWorks')` → `mon`。P3 订阅 **无侧栏**；P4 性能监控 **无菜单**。
> **模块核心口径**：**长查询异步规范（V3-B6）——超时异步双态**：报表查询超 10 秒自动转异步任务（queryMode: SYNC/ASYNC 双响应结构，结果 OSS 落盘 + 钉钉/工作台通知领取）；单报表查询并发上限 10/用户（1193）；**查询性能 BR-204**：10 万行级 < 30 秒，超 30 秒强制终止提示缩小范围（1194）；**权限继承 BR-212**：行级双重过滤（创建者 ∩ 查看者），分享不突破原权限；**敏感分享审批**：含成本/利润数据的分享链接须 R4 审批（1196），有效期 7~30 天（1197）。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase（`report_no → reportNo`、`layout_config → layoutConfig`）。
- 枚举：报表状态 `BiReportStatus`（DRAFT/PUBLISHED）、查询任务 `BiAsyncTaskStatus`（RUNNING/COMPLETED/FAILED）、订阅状态（ACTIVE/PAUSED，EnableStatus 语义复用契约内联 ACTIVE/PAUSED）、分享审批 `BiShareApproval`（NOT_REQUIRED/PENDING_APPROVAL/APPROVED/REJECTED/EXPIRED；EXPIRED=分享链接过期，已回写全局规范）、订阅周期（DAILY/WEEKLY/MONTHLY）。
- 报表编号 reportNo = `BR+日期+流水`（code 样式）。
- 权限矩阵引用 PRD 5.7~5.9.5：R1/R3/R4/R9（全量，R9 成本脱敏）、R5/R6（本域数据集）、创建者本人；订阅 R1~R9（R10 不开放）；分享审批 R4。
- 金额：指标含成本/利润字段时 ¥ 前缀千分位两位小数；R9 视角成本类指标服务端脱敏。
- **异步双态 UI 总则**：所有查询入口（P1 预览、P2 报表/下钻）统一处理 queryMode 两分支——SYNC 直接渲染（展示 costMs + cacheHit 标记）；ASYNC 转"任务卡"态（§7 异步任务卡）。

---

# P1 自助报表设计器（BI-001）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/ims/bi/report/designer`（**隐藏路由** · 不出侧栏；报表管理列表页 [+ 新建报表] / [编辑] 进入；`?reportId=` 带参进入编辑态；v2.6.27 走查 #21：原「报表设计」独立菜单取消） |
| 页面级别 | 二级（设计器工作台） |
| 前置依赖 | 数据集已接入（指标库/自定义查询/V3 聚合层宽表，V3-B1 元数据驱动） |
| 权限 | 创建/编辑：R1/R3/R4/R9/R5/R6（本域数据集）；列表查看：同上 + 分享范围内用户 |
| 用户 | 财务 R3 / 运营总监 R4 / 运营 R5 / 内容 R6（本域自助分析） |
| 设计器形态 | **三栏自由拖拽画布（free layout）**——左「数据集/字段/组件库」· 中「画布 + 图层面板」· 右「属性三区」（基础/数据源/交互） |

> **设计器定位（v2.6.26 采纳 DW）**：P1 由原「行/列/值/筛选四区**表单式** + 静态画布预览」升级为 **三栏可拖拽设计器**——组件（图表/查询条件/容器/交互四类）从组件库拖入画布，画布内可拖动定位、可选中编辑、可删除/撤销；右侧属性面板按选中组件动态切换三区（基础属性 / 数据源配置 / 交互配置）。**行/列/值/筛选的元数据驱动（V3-B1）语义不变**，但表达方式从「四区表单」改为「组件 + 属性面板配置」，二者不是两套能力。

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 报表设计器  [报表名称 Input][撤销][保存并发布]  [设备预览 PC|TV|移动]      │
├──────────────┬───────────────────────────────────────┬───────────────────┤
│ ◆ 左栏 198px │ ◆ 中部：画布区（自由拖拽栅格 40px）      │ ◆ 右栏 272px 属性  │
│ ┌──────────┐ │ ┌───────────────────────────────────┐ │ ┌───────────────┐ │
│ │数据集 ▾  │ │ │ [KPI 卡]      [折线图]   [饼图]    │ │ │▾ 基础属性     │ │
│ │平台▼      │ │ │  ¥412.8万        ╱╲       ◐      │ │ │  标题 [____]  │ │
│ │账号      │ │ │                                   │ │ │  X/Y [__][__] │ │
│ │团队      │ │ │  [数据表]              [日期筛选] │ │ │  宽/高 [__][__]│ │
│ │行数 128万⚠│ │ └───────────────────────────────────┘ │ │▾ 数据源配置   │ │
│ └──────────┘ │ 图层：KPI合计 · 折线趋势 · 饼图占比 ⋯ │ │  数据集/指标/  │ │
│ ┌──────────┐ │ ┌───────────────────────────────────┐ │ │  聚合/动态参数 │ │
│ │🔍 字段   │ │ │ ① 图表组件 11 种                   │ │ │▾ 交互配置     │ │
│ │platform  │ │ │ ② 查询条件组件 5 种                │ │ │  联动/跳转/刷新│ │
│ │gmv 指标  │ │ │ ③ 容器组件 3 种  ④ 交互组件 3 种   │ │ │  最小刷新 30s  │ │
│ └──────────┘ │ └───────────────────────────────────┘ │ └───────────────┘ │
│ ◆ 组件库（可拖）│ 未选中组件时右栏显示「报表级属性」（可见范围/分类/标签）│
├──────────────┴───────────────────────────────────────┴───────────────────┤
│ ◆ 报表管理列表（独立路由 /ims/bi/report/list，QueryBar + 卡片/列表双视图） │
│ [缩略图|编号/名称|类型|可见范围|数据集/版本|状态|创建人|更新时间|操作]      │
└──────────────────────────────────────────────────────────────────────────┘
```

**组件库四类（21 组件）**

| 类 | 组件 |
|----|------|
| 图表（11） | KPI 指标卡 · 柱状图 · 折线图 · 饼图 · 环形图 · 雷达图 · 漏斗图 · 散点图 · 数据表 · 明细表 · 富文本 |
| 查询条件（5） | 日期范围 · 下拉单选 · 下拉多选 · 文本输入 · 数值区间 |
| 容器（3） | 分组容器 · 卡片容器 · Tab 容器 |
| 交互（3） | 按钮 · 跳转链接 · 联动触发件 |

**画布约束**：自由布局（`layout_mode=free`）；组件最小尺寸 **80×80px**；栅格吸附 40px；组件可拖动、可选中、可删除；支持撤销栈；左侧图层面板按 z-index 排序，点击图层反向选中画布组件。设备预览（PC 1920×1080 / TV 4K / 移动端）仅切换画布承载宽度与栅格列数。

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（契约内联） =====
type BiDatasetSource = 'METRIC_LIB' | 'CUSTOM_QUERY' | 'DWS_AGGREGATION';
type BiFieldType = 'DIMENSION' | 'METRIC';
type BiAggType = 'SUM' | 'AVG' | 'COUNT' | 'MAX' | 'MIN';
type BiChartType = 'TABLE' | 'BAR' | 'LINE' | 'PIE';
type BiShareScope = 'PRIVATE' | 'SPECIFIED' | 'ALL';

/** 报表类型（v2.6.26 采纳 DW §9.9.1：报表 / 大屏） */
type BiReportType = 'REPORT' | 'DASHBOARD';
/** 布局模式：栅格（grid，行/列/值四区派生）｜自由（free，绝对定位拖拽） */
type BiLayoutMode = 'GRID' | 'FREE';

/** 组件库四类（v2.6.26 采纳 DW §9.9.2） */
type BiCompGroup = 'CHART' | 'FILTER' | 'CONTAINER' | 'ACTION';
type BiCompType =
  // 图表（11）
  | 'KPI' | 'BAR' | 'LINE' | 'PIE' | 'DONUT' | 'RADAR' | 'FUNNEL' | 'SCATTER' | 'TABLE' | 'DETAIL_TABLE' | 'RICH_TEXT'
  // 查询条件（5）
  | 'DATE_RANGE' | 'SELECT_SINGLE' | 'SELECT_MULTI' | 'TEXT_INPUT' | 'NUMBER_RANGE'
  // 容器（3）
  | 'GROUP' | 'CARD' | 'TAB'
  // 交互（3）
  | 'BUTTON' | 'LINK' | 'TRIGGER';

/** 组件数据源来源（v2.6.26 采纳 DW §9.9.3） */
type BiCompDsSource = 'DATASET_FIELD' | 'REPORT_DATA' | 'STATIC' | 'COMP_OUTPUT' | 'CALC';

// ===== 请求 =====
interface BiReportCreateReq {
  reportName: string;
  datasetId: number;
  /** v2.6.26：类型 + 布局模式（REPORT/DASHBOARD · GRID/FREE） */
  reportType?: BiReportType;
  layoutMode?: BiLayoutMode;
  /** 自由布局组件集合（layoutMode=FREE 时唯一权威；GRID 时由 rows/columns/values 派生） */
  components?: BiCompDef[];
  /** 栅格布局：行/列/值/筛选（V3-B1 元数据驱动，grid 模式保留；free 模式下由组件属性派生） */
  layoutConfig: {
    rows: Array<{ fieldKey: string }>;
    columns: Array<{ fieldKey: string }>;
    values: Array<{ fieldKey: string; aggType: BiAggType }>;
    filters: Array<{ fieldKey: string; operator: 'EQ' | 'IN' | 'RANGE'; value: unknown }>;
    chartType: BiChartType;
  };
  /** 计算字段：聚合与简单表达式（加减乘除/占比） */
  calcFields?: Array<{ fieldKey: string; fieldLabel: string; expression: string }>;
  /** 分类与标签（v2.6.26 采纳 DW §9.9.1 分类树 + 标签） */
  category?: string;
  tags?: string[];
  shareScope: BiShareScope;
  specifiedUserIds?: number[];           // SPECIFIED 时必填
}

/** 画布组件定义（v2.6.26 新增，对齐 DW dw_report_component） */
interface BiCompDef {
  /** 组件唯一 id（画布内，用于联动引用 ${component_id.field_name}） */
  compId: string;
  compType: BiCompType;
  compGroup: BiCompGroup;
  title: string;
  /** 绝对定位（px）与尺寸；最小 80×80（DW §9.9.2） */
  position: { x: number; y: number; w: number; h: number };
  /** 样式：主色/字号/对齐/显示图例等 */
  style?: Record<string, string | number>;
  /** 数据源配置（§9.9.3） */
  datasourceConfig?: {
    source: BiCompDsSource;
    fieldKey?: string;                   // DATASET_FIELD
    aggType?: BiAggType;
    /** 动态参数：值来自其他组件输出，形如 ${compId.field} */
    dynamicParams?: Array<{ paramName: string; expression: string }>;
  };
  /** 组件对外输出参数（供下游组件 ${compId.field} 引用） */
  outputParams?: string[];
  /** 交互配置（§9.9.4 联动 / 跳转 / 刷新策略） */
  interactionConfig?: {
    linkTo?: Array<{ targetCompId: string; triggerType: 'CLICK' | 'SELECT' | 'RANGE' }>;
    jumpTo?: { type: 'REPORT' | 'DRILL_DETAIL' | 'MODULE_DETAIL' | 'EXTERNAL'; target: string; paramMap?: Record<string, string> };
    refreshInterval?: number;            // 秒，最小 30（§9.9.3）
  };
  zIndex: number;
}

interface BiReportQueryReq {
  reportId: number;
  version?: number;
  filterOverrides?: BiReportCreateReq['layoutConfig']['filters'];   // 预览态临时筛选
  /** 单组件查询（自由布局按组件独立取数） */
  compId?: string;
  pageNo?: number;
  pageSize?: number;
}

// ===== 响应 =====
interface BiDatasetVO {
  id: number;
  datasetName: string;
  datasetSource: BiDatasetSource;
  fields: Array<{
    fieldKey: string;
    fieldLabel: string;
    fieldType: BiFieldType;
    dataType: 'STRING' | 'NUMBER' | 'DATE';
    /** 指标口径引用（BIR-R3：不允许自造口径，统一引用指标管理） */
    metricCode?: string;
  }>;
  /** 数据新鲜度（Redis 缓存 TTL 依据，V3-B3 默认 15 分钟） */
  freshnessMinutes: number;
  rowCountEstimate: number;              // 行数估计（前端性能预警）
}

interface BiReportVO {
  id: number;
  reportNo: string;                      // BR+日期+流水
  reportName: string;
  datasetId: number;
  datasetName: string;
  /** v2.6.26：类型 / 布局模式 / 组件集合 / 分类标签 / 缩略图 */
  reportType?: BiReportType;
  layoutMode?: BiLayoutMode;
  components?: BiCompDef[];
  category?: string;
  tags?: string[];
  /** 自动缩略图（发布时生成，列表卡片展示，DW §9.9.1） */
  thumbnail?: string;
  layoutConfig: BiReportCreateReq['layoutConfig'];
  calcFields: BiReportCreateReq['calcFields'];
  version: number;                       // 修改生成新版本，分享链接不变（BIR-R4）
  ownerUserId: number;
  ownerName: string;
  shareScope: BiShareScope;
  status: 'DRAFT' | 'PUBLISHED';
  /** 竞品资产引用联动（BR-214，引用 COMP 档案时报表侧留痕） */
  compAssetRefs?: string[];
  createdAt: string;
}

/** 组件数据集字段（组件级取数用，含指标口径引用） */
interface BiCompDatasetFieldVO {
  fieldKey: string;
  fieldLabel: string;
  fieldType: BiFieldType;
  metricCode?: string;                   // BIR-R3：仅已登记口径
}

// ===== 查询双态响应（V3-B6 核心） =====
/** 同步路径（< 10 秒） */
interface BiReportQueryResp {
  queryMode: 'SYNC';
  costMs: number;                        // BR-204 监控埋点
  columns: Array<{ fieldKey: string; fieldLabel: string; dataType: string }>;
  rows: Array<Record<string, string | number | null>>;
  total: number;
  /** Redis 缓存命中（V3-B3：TTL = 数据集新鲜度） */
  cacheHit: boolean;
  dataAsOf: string;
}

/** 异步路径（超 10 秒自动转异步任务，V3-B6） */
interface BiReportQueryAsyncResp {
  queryMode: 'ASYNC';
  asyncTaskId: string;
  message: string;                       // '查询超时转异步，完成后通知领取'
  resultUrl: string;                     // GET /bi/report/async/{taskId}
}
```

## 4. 交互流程

**页面加载**：
1. `GET /admin-api/ims/bi/report/datasets` → 左栏数据集 Select；选中后展示字段列表（DIMENSION/METRIC 分组 + 搜索），并显示 **行数预估**：rowCountEstimate > 100,000 → 黄色预警 "数据量约 {n} 行，查询可能较慢（BR-204 目标 10 万行 < 30s）"。
2. 编辑态（`?reportId=`）：`GET /bi/report/{id}` 回填 reportType/layoutMode/components/layoutConfig/calcFields/shareScope/category/tags，并按 `positions` 重建画布与图层面板。
3. 新建态：画布空；`layoutMode` 默认 **FREE**（自由拖拽）；图层面板空；右栏显示**报表级属性**（报表名称/可见范围/分类/标签）。

**核心操作（拖拽链路）**：
- **拖入组件**：从左栏组件库（四类 21 组件）`dragstart` → 画布 `drop` → 在落点创建组件（`compId` 自增、`zIndex` 递增、初始尺寸按组件类型默认值，夹取画布边界且不小于 80×80）；落点亦可**双击组件库项**按列自动落位（无鼠标拖拽场景）。每次增删改入**撤销栈**。
- **拖动定位**：画布内组件 `mousedown` 拖动 → 实时更新 `position.x/y`，吸附栅格 40px；越界夹取到画布内。
- **选中与图层**：点击组件 → `selected` 高亮 + 右栏切换为该组件**属性三区**；左侧图层面板同步高亮；点击图层面板项 → 反向选中画布组件；点击画布空白 → 取消选中（右栏回报表级属性）。
- **属性三区（右栏，选中组件时）**：
  - **① 基础属性**：标题、X/Y、宽/高、字号/对齐/主色；改动**实时**反映到画布 DOM（不整页重绘）。
  - **② 数据源配置**：数据源来源（DATASET_FIELD / REPORT_DATA / STATIC / COMP_OUTPUT / CALC）；DATASET_FIELD → 选字段 + 聚合方式（SUM/AVG/COUNT/MAX/MIN）；**动态参数**以 `${compId.field}` 形式引用上游组件输出（带 ⚡动态标）；**BIR-R3：字段仅可选已登记指标口径（metricCode），不允许自造口径**。
  - **③ 交互配置**：**组件联动**（点击/选择/范围三种触发 → 多选目标组件；A→B→C 链式，前端检测**循环依赖**并阻断）、**跳转**（其他报表 / 下钻详情 DC-001 / 来源模块详情 / 外部链接 + 参数映射）、**自动刷新**（秒，最小 30）。
- **删除 / 撤销**：组件右上角 [×] 或图层面板删除 → 移除并重排 zIndex；顶栏 [撤销] 回退最近一次增删改（栈式）。
- **计算字段**：[+ 计算字段] → 表达式编辑器（白名单提示：仅支持 SUM/AVG/COUNT/MAX/MIN 聚合函数与 + - * / ( ) 四则运算，示例 `(SUM(gmv) - SUM(cost)) / SUM(gmv)`）；表达式非法返回 1192 → 编辑器红字定位。
- **实时预览**：画布内**每个组件按自身数据源独立取数**（`POST /bi/report/query` 携带 `compId`；未保存时可用临时 components + filterOverrides 预览态）：
  - **SYNC（<10s）**：渲染该组件图表/表格 + 底部状态条 `耗时 {costMs}ms · 缓存命中 ✓（V3-B3，TTL {freshnessMinutes} 分钟）`。
  - **ASYNC（超 10s）**：该组件切换为**异步任务卡**（§7.1）：`任务 {asyncTaskId} 已转后台执行，完成后通过钉钉/工作台通知您领取`——可离开页面，通知点击回设计器/报表页领取。
  - 1193 并发超限 → toast "查询并发已达上限（10/用户），请稍候重试"；1194 超 30s 强制终止 → 提示 "查询超 30 秒已终止（BR-204），建议缩小筛选范围"。
- **设备预览**：PC 1920×1080 / TV 4K / 移动端切换 → 仅改画布承载宽度与栅格列数，不改组件坐标语义。
- **保存**：[保存并发布]（PUBLISHED；含**自动生成缩略图**）；[撤销] 非保存动作。编辑保存 version 自增 → toast "已生成新版本 v{n}，分享链接保持不变（BIR-R4）"。**发布即刻生效**（DW §9.9.2 实时保存草稿 + 手动发布口径在 IMS 归并为「保存并发布」单动作，DRAFT 由订阅/分享前的中间态承担）。
- **导入 / 导出 JSON 模板**：列表页 [导入模板] 上传 `*.json`（组件结构 + 布局 + 数据源引用）→ 校验通过后新建报表；行操作 [导出模板 JSON] 下载当前报表定义。**数据源引用（如自定义查询 id）跨环境失效时提示"数据源 custom_sql_1 需重新配置"**（不阻断导入）。
- **字段引用非法**：1191 → 拖拽配置区红字（字段不存在或 DIMENSION/METRIC 用法错误，如维度字段拖入值区）。
- **报表管理列表**（`/ims/bi/report/list`）：QueryBar（reportName/datasetId/ownerUserId/shareScope）+ **卡片/列表双视图** + **左栏分类树**（全部/运营（含子：日报·周报·大屏）/内容/财务/未分类）；卡片展示**缩略图**（line/bar/pie/stack 形态 SVG 生成图）| 名称/编号 | 类型 | 可见范围 | 数据集/版本 | 状态 | 创建人 | 更新时间；行操作：编辑设计器（创建者/R1）/ 预览（跳 P2）/ 发布管理 / 分享范围设置 / 复制 / 导出模板 JSON / 订阅（跳 P3）/ 删除（R1/创建者；有活跃订阅 → ConfirmDialog "该报表存在 {n} 个活跃订阅，删除前须先取消订阅"）。

## 5. 查询条件表（报表管理列表）

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| cat | 左栏分类树 | string | 分类/子分类（全部/运营（日报·周报·大屏）/内容/财务/未分类） |
| reportName | Input | string | 名称模糊 |
| datasetId | Select | number | 数据集 |
| ownerUserId | 人员选择 | number | 所有者 |
| reportType | Select | BiReportType | 报表/大屏 |
| shareScope | Select | BiShareScope | 私有/指定人/全员 |

## 6. 表格列定义（报表管理列表 · 列表视图）

| 列 | 字段 | 渲染 |
|----|------|------|
| 缩略图 | thumbnail | 56×36 自动生成缩略图（无图则按 chartType 内联 SVG 占位） |
| 报表编号 / 名称 | reportNo · reportName | 两行：`reportNo` code 样式（BR+日期+流水） + 名称文本 |
| 类型 | reportType | REPORT 蓝"报表" / DASHBOARD 紫"大屏" |
| 可见范围 | shareScope | PRIVATE 灰"私有" / SPECIFIED 蓝"指定人 {n}" / ALL 绿"全员" |
| 数据集 / 版本 | datasetName · version | `{datasetName} · v{n}` |
| 状态 | status | DRAFT 灰 / PUBLISHED 绿 |
| 创建人 | ownerName | 文本 |
| 更新时间 | updatedAt | yyyy-MM-dd HH:mm |
| 操作 | — | 编辑设计器 / 预览 / 发布管理 / 分享设置 / 复制 / 导出模板 JSON / 删除（按权限） |

> **卡片视图**（默认）：左侧 230px 分类树 + 右侧卡片栅格；卡片含缩略图（`.bi-thumb`，light/dark 变体）、名称、类型/可见范围标签、数据集·版本、状态、创建人、更新时间、[⋯ 更多]（同列表行操作）。
> **视图切换**：卡片 / 列表两键，状态存 `biListView`（默认 card）；分类筛选存 `biListCat`（默认 all，支持两级匹配「分类/子分类」）。

## 7. 抽屉/弹窗规格

### 7.1 异步任务卡（预览区内联组件，非抽屉）

- **形态**：预览区切换渲染——图标 ⏳ + `任务 {asyncTaskId}` + 文案"查询超时已转后台（V3-B6），完成后通过钉钉工作通知与工作台消息通知领取"。
- **操作**：[稍后领取]（关闭任务卡保留报表态）/ [等待并轮询]（10 秒间隔轮询 `GET /bi/report/async/{taskId}`，COMPLETED 直接渲染结果）。
- COMPLETED：小结果集 inlineResult 直接渲染；大结果集 [下载结果文件]（downloadUrl OSS 60 秒签名 URL）。FAILED：红字 failReason + [调整筛选重试]。

### 7.2 分享范围设置弹窗（Modal，480px，创建者/R1）

- shareScope Radio（PRIVATE/SPECIFIED/ALL）+ SPECIFIED 时人员多选；提示条 "分享不突破数据权限：查看者打开后仍按其角色行级过滤（BR-212/BIR-R1）"。
- 保存 → `PUT /bi/report/{id}/share`。

### 7.3 计算字段编辑器（Modal，640px）

- fieldKey/fieldLabel Input + expression TextArea（等宽字体）；白名单函数按钮快速插入（SUM() AVG() COUNT() MAX() MIN()）；语法高亮；实时校验（未保存前端预检：括号配对/未知字段/非法函数）。
- 1192 服务端兜底 → 红字定位。

### 7.4 筛选条件配置抽屉（Drawer，520px · 组件级）

- 由画布内「查询条件组件」双击或右栏 [配置] 打开；字段 Select（DIMENSION）+ 运算符（EQ/IN/RANGE）+ 默认值。
- **动态参数**区：可填 `${compId.field}`（如 `${dateRange.value}`），带 ⚡动态标；用于把筛选组件的选中值传给目标图表组件的数据源。

### 7.5 组件联动配置抽屉（Drawer，520px）

- 触发方式 Radio：点击 / 选择 / 范围；目标组件多选（同报表内其他组件）。
- **循环依赖检测**：形成 A→B→C→A 闭环时，确认按钮禁用 + 红字 "检测到联动循环（{链路}），请调整"（前端图遍历，DW §9.9.4）。

### 7.6 跳转配置抽屉（Drawer，520px）

- 跳转类型 Radio：其他报表 / 下钻详情页（DC-001）/ 来源模块详情 / 外部链接。
- 参数映射表（源字段 → 目标参数）；外部链接须命中**域名白名单**，否则提示"外部链接域名未在白名单内"。

### 7.7 分类管理弹窗（Modal，560px）

- 树形维护报表分类（全部 / 运营（日报·周报·大屏）/ 内容 / 财务 / 未分类）；节点可增删改名；删除非空分类 → "该分类下有 {n} 个报表，请先移动"。

### 7.8 模板导入弹窗（Modal，560px）

- 上传 `*.json`（拖放或选择）；解析后展示"报表名 / 组件数 {n} / 数据源引用 {m}"摘要；
- 数据源引用不可用（如跨环境自定义查询 id）→ 黄条警告 "数据源 {key} 需重新配置"，仍允许导入（导入后数据源置空待配）。

### 7.9 发布配置抽屉（Drawer，640px · 四段式）

- ① **发布方式**（链接分享 / 免登录 SSO / 内嵌 iframe）；② **可见范围与权限**（PRIVATE/SPECIFIED/ALL + 行级继承提示）；③ **访问控制**（密码开关 + 密码输入 + **有效期 7~30 天**，越界 → 1197）；④ **展示与刷新**（设备 PC/TV/移动、自动刷新间隔 ≥30s、发布版本快照）。
- 保存 → `POST /bi/report/{id}/publish` → 返回 `access_token`/`shareUrl`；含成本/利润 → `approvalStatus=PENDING_APPROVAL`（BIS-R3，见 P3）。
- 发布记录在 P3「发布管理」Tab 展示（发布ID/访问方式/可见范围/链接/密码/有效期/快照/访问次数/状态/发布人/发布时间/操作）。

### 7.10 快照回溯弹窗（Modal，800px）

- 推送或发布时点的数据快照（BIS-R1 可回溯当时数据）；见 P3 §7.2。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 表单红字 |
| 1191 | 数据集字段引用非法 | 拖拽区红字定位 |
| 1192 | 计算字段表达式非法 | 编辑器红字 |
| 1193 | 查询并发超限（10/用户） | toast + 3 秒后允许重试 |
| 1194 | 查询超 30s 强制终止 | 提示缩小范围 |
| 1008 | 无报表查看权限 | toast（BR-212） |
| 异步任务 FAILED | — | 任务卡红字 + 重试入口 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-204（10 万行 < 30s） | 行数预估预警 + costMs + 1194 |
| BR-212（行级双重过滤） | 分享弹窗提示 + 服务端过滤 + 1008 |
| BIR-R1（权限交集过滤） | 查询结果服务端约定（页面提示条） |
| BIR-R2（超 30s 提示缩小范围） | 1194 处理 |
| BIR-R3（不自造口径） | 字段列表仅登记指标 + 属性面板数据源仅可选 metricCode（1191/1192） |
| BIR-R4（版本化分享链接不变） | version toast |
| V3-B1（元数据驱动零代码） | 组件属性面板数据源配置（DATASET_FIELD）驱动，FREE 布局下由组件派生行/列/值 |
| V3-B2/B3（预计算 + Redis 缓存） | 组件状态条 cacheHit + TTL 展示 |
| V3-B6（超时异步双态） | 组件级异步任务卡（SYNC/ASYNC 分支） |
| BR-214（竞品引用留痕） | compAssetRefs（引用 COMP 档案字段时自动记录，页面展示于报表详情） |

## 10. DW 借鉴落地（v2.6.26 · 2026-10-03）

> **借鉴权威**：`参考文件/DW-PRD-Phase1.md` §9.9.1~§9.9.5（BI 报表与数据大屏）+ `参考文件/DW-UI-Prototype-Phase1.html`（`bi-list` / `bi-designer` / `bi-preview` / `bi-publish` / `bi-categories` / `biFullscreen`）。
> **定位**：**借结构、不搬 API**。DW 的 Python FastAPI `/api/*`、SQL Server / T-SQL、`dw_report*` 表名均**不映射**；IMS 实现 SSOT 仍为 **OPS UX-M6 + 本规格**。落库为 **`ims_` 前缀新表**（IR-04 只加列不改现网表）。

| # | 落地项 | DW 参照 | IMS 落点 | 断言 |
|---|--------|---------|----------|------|
| 1 | **三栏拖拽设计器** | `bi-designer` §9.9.2 | 左 198px（数据集/字段/组件库）· 中画布（1060×600，40px 栅格）· 右 272px（属性三区） | `.bidsn` 三栏 grid 生效；组件可拖入/拖动/删除/撤销 |
| 2 | **组件库四类 21 组件** | §9.9.2 四类 | CHART 11 / FILTER 5 / CONTAINER 3 / ACTION 3 | 组件库 21 cell，均 `draggable` |
| 3 | **图层面板** | `layer-bar` §9.9.2 | 画布下方图层条，按 zIndex 排序，双向选中 | 预置 7 组件 → 7 图层项 |
| 4 | **属性面板三区** | `prop-sec` §9.9.2/§9.9.3 | 基础属性 / 数据源配置 / 交互配置；未选中时报表级属性 | `.prop-sec` ≥ 3；改值实时反映 DOM |
| 5 | **组件级数据源 + 动态参数** | §9.9.3 | `${compId.field}` 动态参数 + outputParams + 刷新间隔 ≥30s | 筛选抽屉含 ⚡动态标 |
| 6 | **组件联动 + 循环依赖检测** | §9.9.4 | 点击/选择/范围触发；A→B→C 闭环检测阻断 | 联动抽屉 + 循环校验 |
| 7 | **跳转（4 类目标）** | §9.9.4 | 其他报表 / 下钻详情 DC-001 / 来源模块详情 / 外部链接 | 跳转抽屉参数映射表 |
| 8 | **报表管理：分类树 + 缩略图 + 卡片/列表** | `bi-list` §9.9.1 | 左分类树（两级）+ 卡片栅格（缩略图）/ 列表双视图 | 树 8 项 / 卡 7 张 / 缩略图 7 |
| 9 | **发布链接 + 密码 + 有效期** | `bi-publish` §9.9.5 | **五段式发布抽屉**（v2.6.27 走查 #21 补 ① 发布去向）：① **发布去向**（报表中心 / 单独发布为菜单，后者写 `sys_menu` + `ims_report_menu`）· ② 访问方式 · ③ 可见范围与权限 · ④ 访问控制（密码+7~30 天）· ⑤ 展示刷新 | 抽屉五段 + 1197 校验 |
| 10 | **发布版本快照** | §9.9.5 快照回滚 | 发布记录快照版本 + 快照回溯弹窗 | 发布表 12 列 |
| 11 | **全屏大屏（多终端）** | `biFullscreen` §9.9.5 | 暗色全屏页 6 KPI + 2 SVG；设备 PC/TV/移动 | `.fs-page` 存在 + KPI 6 |
| 12 | **导入 / 导出 JSON 模板** | §9.9.1 | 列表 [导入模板] + 行 [导出模板 JSON]；数据源失效警告 | 导入弹窗数据源警告条 |
| 13 | **分类管理** | `bi-categories` | 分类树增删改名；非空分类删除阻断 | 分类管理弹窗 |
| 14 | **复制报表** | §9.9.1 | 行操作 [复制] → 新报表（名称+副本，version 重置） | 列表行操作含复制 |

**仍为 non-goal（v2.6.26 不变）**：DW 的**多租户报表模板市场**、**iframe 内嵌跨域携带登录态**（安全评估未过，链接一律走 SSO 免登录）、**大屏 TV 端自动轮播切页**、**告警推送到大屏**（P1+ 视需求）。

## 11. 报表域 IA 重构（v2.6.27 · 走查 #21 · 2026-10-04）

> **触发**：用户走查 #21。**侧栏「数据报表」由 4 叶压缩为 2 叶**，报表设计/大屏转隐藏，发布补「去向」段。

| # | 变更 | 落地 |
|---|------|------|
| 1 | **「标准报表」更名「报表中心」** | 菜单/页名 `bi0Report` 由「标准报表」改为「**报表中心**」（避免与 17b「报表管理」混淆）；深链 `bi0Standard` 仍归一化到 `bi0Report` |
| 2 | **报表管理 + 报表设计合并单菜单** | 侧栏「数据报表」= **报表管理 `biList` + 报表中心 `bi0Report`** 两叶；**报表设计 `biDesign` 转隐藏路由** `/ims/bi/report/designer`；报表管理 [+ 新建报表]/[编辑] → `biOpenDesigner(id)` 进入 |
| 3 | **报表类型化（报表 / 大屏）** | 新建抽屉 **报表类型 pills**（📑 报表 / 🖥 大屏）→ `reportType = REPORT / DASHBOARD`；**「大屏配置」独立菜单退役**，`bi0Screen`/`bi0ScreenConfig` 归一化到 `biList`；编辑态读 `fpv('type')`（pills 值） |
| 4 | **发布去向二选一** | 发布抽屉 **① 发布去向**：**发布到报表中心**（进「报表管理」目录，不动系统菜单）/ **单独发布为菜单**（写 `sys_menu` + `ims_report_menu`，可单独授权角色，报表下线/删除时菜单自动置灰） |
| 5 | **自定义查询结果图表 Tab 修复** | 结果面板在「**内联页**」与「**执行抽屉**」两处渲染；新增 `bi0QueryReRenderResult()` 双容器重绘；图表类型 **柱/折/饼** 切换（补 `bi0SvgLine` 折线图 + `bi0-chart-stage` 容器）；`bi0QueryResultPanel` 图表段按 `state.q.bi0ChartType` 三态渲染 |
| — | **隐藏路由清单（v2.6.27）** | `biDesign`（报表设计）· `bi0Screen`（大屏，归一化）· `biShare`（订阅与分享，归一化到 `biList` 并置 `tab=share`）；侧栏可见 = `BI_REPORT_NAV_IDS = ['biList','bi0Report']` |

**验收（AC）**：`go('bi0Screen')`/`go('bi0ScreenConfig')` → `biList`；侧栏「数据报表」childCount=**2**；新建抽屉含 2 个 `reportType` pills；选「大屏」建出 `reportType=DASHBOARD` 且落 `biDesign`；发布抽屉含 5 段（① 发布去向 + ②~⑤）；自定义查询结果「图表展示」Tab 在**抽屉与内联两路径**均可切换且柱/折/饼渲染互异。

---

# P2 报表预览与下钻（BI-002 + 报表查看）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/ims/bi/report/view/{id}`（列表"预览"进入；分享链接 SSO 落地复用本页） |
| 页面级别 | 二级（报表查看 + 下钻交互） |
| 前置依赖 | 报表 PUBLISHED 或 DRAFT 预览权限 |
| 权限 | 报表可见者（BR-212 过滤；分享链接打开后按查看者权限）；下钻同权限 |
| 用户 | 报表查看者（各角色按数据权限） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ◆ 报表查看页（POST /bi/report/query 数据区）                              │
│ [报表名] v3 · 数据集: 直播聚合层 · [筛选条件折叠区(临时覆盖)] [刷新]       │
│ 耗时 856ms · 缓存命中✓ · 数据截至 14:00                                   │
│ ┌────────────────────────────────────────────────────┐                  │
│ │ 图表渲染（TABLE/BAR/LINE/PIE）                       │                  │
│ │ TABLE 模式: 维度列│指标列(¥千分位) ── 单元格可点击穿透│                  │
│ │ BAR/LINE: 维度轴点击下钻                             │                  │
│ │ 面包屑下钻条: 平台 ▸ 抖音 ▸ 账号 DY123 ▸ (返回上卷)  │                  │
│ └────────────────────────────────────────────────────┘                  │
│ 底部: [导出 XLSX/CSV]（GET /bi/query/export）                            │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 下钻交互（POST /bi/query/drill）                                        │
│ 维度点击 → 层级下钻（平台→账号→场次；部门→团队→人；年→月→日）             │
│ 数值单元格点击 → 单元格穿透（POST /bi/query/cell-drill）                  │
│   → jumpType: MODULE_DETAIL(跳V1台账) / DC_TRACE(跳DC-001穿透)           │
├──────────────────────────────────────────────────────────────────────────┤
│ 工作台通知区: [异步任务消息卡片] → 点击跳回本页自动领取结果（V3-B6）       │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 请求 =====
interface BiDrillReq {
  reportId?: number;
  dashboardId?: number;                  // 二选一
  drillPath: Array<string>;              // 维度层级序列 ['PLATFORM','ACCOUNT']
  direction: 'DOWN' | 'UP';
  /** 下钻时维度组合过滤（上下文自动携带） */
  filterContext: Record<string, string | number>;
  pageNo?: number;
  pageSize?: number;
}

interface BiCellDrillReq {
  reportId: number;
  /** 数值单元格的当前维度组合 */
  cellDimensions: Record<string, string | number>;
  /** 穿透目标：明细单据（BIQ-R3 跳来源模块详情） */
  drillToDetail: boolean;
}

// ===== 响应 =====
interface BiDimensionTreeVO {
  trees: Array<{
    treeName: string;
    levels: Array<{ level: number; dimensionKey: string; dimensionLabel: string }>;
  }>;
  // 预定义层级链：平台→账号→场次；部门→团队→人；年→月→日
}

interface BiCellDrillResp {
  jumpType: 'MODULE_DETAIL' | 'DC_TRACE';
  jumpUrl: string;
  jumpParams: Record<string, string>;
}

// 异步领取（复用 P1 §3）
interface BiReportAsyncResultResp {
  asyncTaskId: string;
  taskStatus: 'RUNNING' | 'COMPLETED' | 'FAILED';
  downloadUrl?: string;                  // OSS 60 秒签名
  inlineResult?: BiReportQueryResp;
  failReason?: string;
  notifiedAt?: string;
}
```

## 4. 交互流程

**页面加载**：
1. `POST /bi/report/query`（reportId，最新发布版本）→ SYNC/ASYNC 双态（同 P1：SYNC 渲染；ASYNC 显示任务卡，可轮询或等待通知）。
2. 筛选条件折叠区可临时覆盖 filters（filterOverrides，不改报表定义）。

**核心操作**：
- **维度下钻**：表格维度值/图表轴元素点击 → `POST /bi/query/drill`（drillPath 沿预定义层级链 +1 层，direction=DOWN，filterContext 自动携带当前维度组合）→ 下方表格刷新 + 面包屑追加一级；1195 路径非法 → toast "已到达预定义层级末端或路径非法"。
- **上卷**：面包屑点击上级 → direction=UP → 返回该层结果。
- **单元格穿透**：数值单元格点击 → `POST /bi/query/cell-drill`（cellDimensions = 该行维度组合）：
  - jumpType=MODULE_DETAIL → 新窗口打开来源模块详情（如场次 → V1 LIVE 台账详情，jumpParams 携带 sessionCode）；
  - jumpType=DC_TRACE → 跳 DC-001 穿透查询（携带维度入口，BIQ-R1 最深到场次/明细单据复用 DC 穿透）。
- **导出**：[导出 XLSX/CSV] → `GET /bi/query/export`（携带当前 drillPath+filterContext）→ 签名 URL 下载。
- **异步通知领取**：工作台收到"查询完成"通知卡片 → 点击跳回本页 URL 携带 asyncTaskId → 自动调 `GET /bi/report/async/{taskId}` 渲染结果（V3-B6 闭环）。

## 5. 查询条件表

| 字段 | 组件 | 说明 |
|------|------|------|
| filterOverrides | 折叠筛选区 | 临时筛选（字段+EQ/IN/RANGE），不改报表定义 |
| 分页 | Pagination | TABLE 模式数据分页 |

## 6. 表格列定义

动态列（columns 来自查询响应：fieldKey/fieldLabel/dataType）；DIMENSION 列可点击下钻（显示下钻箭头）；METRIC 列 ¥ 千分位（金额类）右对齐；**数值单元格 Hover 显示穿透提示**（"点击穿透到明细"）；行数 total + `耗时 {costMs}ms` 状态条。

## 7. 抽屉/弹窗规格

复用 P1 §7.1 异步任务卡（本页同组件）。无独立抽屉。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1195 | 下钻路径非法 | toast + 面包屑回退 |
| 1194 | 下钻查询超 30s | 提示缩小范围 |
| 1008 | 无权限（BR-212） | 空态 "您无权查看该报表" |
| 分享链接 EXPIRED | — | 落地页空态 "链接已过期（有效期 7~30 天）" |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-204（下钻性能） | drill 耗时 + 1194 |
| BR-212（下钻行级权限） | 服务端过滤 + 1008 |
| BIQ-R1（下钻最深到场次/明细，复用 DC） | cell-drill → DC_TRACE 分支 |
| BIQ-R2（下钻受性能+权限双约束） | 1194/1008 处理 |
| BIQ-R3（明细跳来源模块详情页） | jumpType=MODULE_DETAIL |
| V3-B4（动态 SQL + 白名单） | 1195 路径校验 |
| V3-B6（异步领取闭环） | 通知卡片跳转自动领取 |

---

# P3 订阅与分享管理（BI-003）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/ims/bi/subscribe`（菜单：数据分析 → 我的订阅；报表/看板页 [订阅]/[分享]/[发布] 按钮发起） |
| 页面级别 | 二级（订阅管理 + 分享链接管理 + **发布管理** + 快照回溯） |
| 前置依赖 | 已发布报表/看板 |
| 权限 | 订阅：R1~R9 按数据权限（R10 不开放）；订阅管理本人；分享链接：创建者/R4；**发布管理：创建者/R1**；分享审批：R4 |
| 用户 | 全角色订阅人 / R4 审批人 / 报表创建者 |
| 页内 Tab | **我的订阅** · **分享链接** · **发布管理**（v2.6.26 采纳 DW `bi-publish`） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 订阅与分享   [ 我的订阅 | 分享链接 | 发布管理 ]                            │
├──────────────────────────────────────────────────────────────────────────┤
│ Tab1 我的订阅（GET /bi/subscribe/list）                                    │
│ ┌────────┬────────┬──────┬──────┬────────┬──────────┬────────────────┐   │
│ │目标     │类型     │周期  │时刻  │状态    │下次推送   │操作            │   │
│ ├────────┼────────┼──────┼──────┼────────┼──────────┼────────────────┤   │
│ │直播月报 │报表     │每周  │09:00 │订阅中  │05-27 09:00│编辑 暂停 取消  │   │
│ │        │        │      │      │        │           │查看快照        │   │
│ └────────┴────────┴──────┴──────┴────────┴──────────┴────────────────┘   │
│ lastPushResult: FAILED_RESENT → 橙标"上次推送失败已补发"(BIS-R4)          │
│ [订阅] 按钮（报表/看板页）→ 订阅创建弹窗                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ Tab2 分享链接（创建者/R4 审批队列）                                        │
│ 我的分享链接: [链接|目标|审批状态|有效期|操作: 复制/失效]                   │
│ 待审批（R4）: [链接|目标|创建人|敏感标记|操作: 通过/驳回]                   │
│ 审批状态四值展示：NOT_REQUIRED 灰 · PENDING_APPROVAL 橙 · APPROVED 绿 ·     │
│                  REJECTED 红（EXPIRED 灰删除线）                            │
├──────────────────────────────────────────────────────────────────────────┤
│ Tab3 发布管理（GET /bi/report/{id}/publish/list；DW `bi-publish` 四段式）  │
│ [发布ID|访问方式|可见范围/权限|访问链接|密码|有效期|快照|访问次数|状态|      │
│  发布人|发布时间|操作: 复制链接/重新配置/失效]                              │
│ 发布配置抽屉（§7.3）：① 发布方式 ② 可见范围与权限 ③ 访问控制（密码+7~30）  │
│                      ④ 展示与刷新配置（设备/自动刷新/快照版本）            │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 快照回溯弹窗（GET /bi/subscribe/snapshot/{id}）                        │
│ [推送时点 {pushAt} 快照表格 + summaryText]（BIS-R1 回溯当时数据）        │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（契约内联） =====
type BiSubscribePeriod = 'DAILY' | 'WEEKLY' | 'MONTHLY';
type BiSubscribeStatus = 'ACTIVE' | 'PAUSED';
/** 分享审批状态（值集对齐全局规范；EXPIRED=分享链接过期，已回写全局规范） */
type BiShareApproval = 'NOT_REQUIRED' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

// ===== 请求 =====
interface BiSubscribeCreateReq {
  targetType: 'REPORT' | 'DASHBOARD';
  targetId: number;
  period: BiSubscribePeriod;              // BR-211 订阅周期
  pushTime: string;                       // '09:00'
}

interface BiShareLinkReq {
  targetType: 'REPORT' | 'DASHBOARD';
  targetId: number;
  /** 含成本/利润数据须 R4 审批（BIS-R3） */
  expireDays: number;                     // 默认 7，最长 30（1197）
}

interface BiShareApprovalReq {
  approve: boolean;
  remark?: string;
}

// ===== 响应 =====
interface BiSubscribeVO {
  id: number;
  targetType: 'REPORT' | 'DASHBOARD';
  targetName: string;
  period: BiSubscribePeriod;
  pushTime: string;
  status: BiSubscribeStatus;
  nextPushAt: string;
  lastPushAt?: string;
  lastPushResult?: 'SUCCESS' | 'FAILED_RESENT';   // BIS-R4 补发记录
}

interface BiShareLinkVO {
  linkId: number;
  linkToken: string;
  shareUrl: string;                       // 免登录 SSO 钉钉授权
  creatorUserId: number;
  expireAt: string;
  approvalStatus: BiShareApproval;
  approvalEndpoint?: string;              // PUT /bi/subscribe/share-approval/{linkId}
  createdAt: string;
}

interface BiSnapshotVO {
  pushAt: string;
  snapshotData: Array<Record<string, string | number | null>>;
  summaryText: string;
  targetName: string;
}

/** 发布记录（v2.6.26 采纳 DW dw_report_publish §9.9.5） */
interface BiReportPublishVO {
  publishId: number;
  reportId: number;
  reportName: string;
  /** 发布方式：分享链接 / 免登录 SSO / 内嵌 iframe（iframe 为 non-goal 暂不开放） */
  accessType: 'SHARE_LINK' | 'SSO_URL';
  shareScope: BiShareScope;
  shareUrl: string;
  /** 访问密码（服务端加密存储，前端脱敏显示；无密码为空） */
  hasPassword: boolean;
  passwordMask?: string;                 // 如 '••••••'
  expireAt: string;                      // 有效期至（7~30 天，1197）
  /** 发布版本快照（BIR-R4 分享链接不变 + 快照可回滚） */
  snapshotVersion: number;
  visitCount: number;
  status: 'ACTIVE' | 'EXPIRED' | 'REVOKED';
  publisherUserId: number;
  publisherName: string;
  publishedAt: string;
}
```

## 4. 交互流程

**页面加载**：`GET /bi/subscribe/list`（本人订阅）；R4 附加载待审批队列（Tab2，服务端下发 PENDING_APPROVAL 列表）；Tab3 加载 `GET /bi/report/{id}/publish/list`（创建者/R1）。

**核心操作**：
- **创建订阅**：报表/看板页 [订阅] → 弹窗（周期日/周/月 + 推送时刻）→ `POST /bi/subscribe` → toast "订阅成功，下次推送 {nextPushAt}"。推送 = 钉钉工作通知 + 工作台消息（附数据快照摘要与链接，BIS-R1/BR-211）；推送任务集群化调度、失败重试 3 次后补发 1 次并记录（V3-B5/BIS-R4，lastPushResult=FAILED_RESENT 橙标展示）。
- **修改/暂停**：行操作 → `PUT /bi/subscribe/{id}`（period/pushTime/status）。
- **取消订阅**：ConfirmDialog → `DELETE /bi/subscribe/{id}`。
- **生成分享链接**：报表/看板页 [分享] → 弹窗（有效期天数，默认 7，max 30——越界返回 1197 红字）→ `POST /bi/subscribe/share-link`：
  - approvalStatus=NOT_REQUIRED → 直接显示 shareUrl + [复制链接]（免登录 SSO 钉钉授权打开）；
  - approvalStatus=PENDING_APPROVAL（目标含成本/利润）→ 弹窗显示"**该报表含敏感数据（成本/利润），链接须运营总监审批后生效（BIS-R3）**"+ 已提交审批状态；此时直接打开链接返回 1196 → 落地页空态 "分享链接待审批，暂不可用"。
- **R4 审批**（Tab2）：行 [通过]/[驳回]（remark）→ `PUT /bi/subscribe/share-approval/{linkId}` → APPROVED 生效（expireAt 起算）/REJECTED。
- **发布管理**（Tab3，v2.6.26）：行 [重新配置] → 发布配置抽屉（§7.3 四段式）→ `PUT /bi/report/publish/{publishId}`；[复制链接]（含密码时提示"请通过安全渠道告知访问密码"）；[失效] → `DELETE /bi/report/publish/{publishId}`（status=REVOKED，链接立即不可用）；**访问次数**列只读统计（DW §9.9.5）。
- **快照回溯**：订阅行 [查看快照] → 快照弹窗（§7.2）展示推送时点数据（BIS-R1 可回溯当时数据）；发布行 [快照] → 展示 `snapshotVersion` 对应发布时点结构（发布后修改报表不影响已发布链接内容，BIR-R4）。
- **分享打开**：接收人点击 shareUrl → SSO 钉钉授权（**有密码则先验密码**）→ P2 报表查看页（**按查看者权限行级过滤**，BIS-R2/BR-212——页面提示条 "按您的数据权限过滤展示"）；链接过期 → 空态 "链接已过期（有效期 7~30 天）"。

## 5. 查询条件表

无复杂查询（本人订阅列表固定）；Tab2 R4 审批队列可按创建人筛选。

## 6. 表格列定义

**我的订阅**：目标名称、类型（报表/看板 Tag）、周期（DAILY 每日/WEEKLY 每周/MONTHLY 每月）、推送时刻、状态（ACTIVE 绿"订阅中"/PAUSED 灰"暂停"）、下次推送时间、上次推送结果（SUCCESS "—"/FAILED_RESENT 橙"失败已补发"）、操作（编辑/暂停/取消/查看快照）。

**分享链接 Tab1**：链接 Token（脱敏显示前 8 位）、目标、审批状态（NOT_REQUIRED 灰"无需审批"/PENDING_APPROVAL 橙/APPROVED 绿/REJECTED 红/EXPIRED 灰删除线）、有效期至（expireAt）、操作（复制 [APPROVED]/失效）。

**待审批 Tab2（R4）**：目标、创建人、敏感标记（含成本/利润 ⚠红）、创建时间、操作（通过/驳回 + remark 必填驳回）。

**发布管理 Tab3（创建者/R1 · v2.6.26）**：发布ID、访问方式（分享链接/免登录 SSO）、可见范围/权限、访问链接（脱敏 + [复制]）、密码（有则 `••••••` 显示 + 提示）、有效期（expireAt 倒计时）、快照（snapshotVersion `v{n}` + [查看]）、访问次数、状态（ACTIVE 绿/EXPIRED 灰/REVOKED 灰删除线）、发布人、发布时间、操作（复制链接/重新配置/失效）。

## 7. 抽屉/弹窗规格

### 7.1 订阅创建/编辑弹窗（Modal，440px）

- targetType/targetId 只读回显 + 周期 Radio（日/周/月，BR-211）+ 推送时刻 TimePicker（默认 09:00）。
- 提示条：推送通道 = 钉钉工作通知 + 工作台消息，附快照摘要（BIS-R1）。

### 7.2 快照回溯弹窗（Modal，800px）

- 头部：目标名 + `推送时点 {pushAt}`；summaryText 摘要卡；快照表格（snapshotData 动态列，¥ 千分位）。
- 只读；提示 "快照为推送时点数据存档，非当前实时数据"。

### 7.3 分享链接生成弹窗（Modal，480px，创建者/R4）

- 有效期 InputNumber（7~30 天，默认 7；1197 预校验）；生成后展示 shareUrl（[复制]）+ approvalStatus 状态区（PENDING_APPROVAL 时显示审批说明）；expireAt 倒计时。

### 7.4 发布配置抽屉（Drawer，640px · 四段式 · v2.6.26）

- ① **发布方式**：共享链接 / 免登录 SSO 链接（Radio；内嵌 iframe 为 non-goal）。
- ② **可见范围与权限**：PRIVATE / SPECIFIED（人员多选）/ ALL；提示条"发布不突破数据权限，访问者按角色行级过滤（BR-212/BIR-R1）"。
- ③ **访问控制**：密码开关（开 → 密码 Input，建议 ≥8 位；生成随机密码按钮）+ **有效期 InputNumber（7~30 天，默认 7）** → 越界 1197 红字；**含成本/利润数据 → 提示"须运营总监审批后生效（BIS-R3）"**。
- ④ **展示与刷新**：设备（PC 1920×1080 / TV 4K / 移动端）、自动刷新间隔（秒，≥30）、**快照版本**（勾选"锁定当前版本为发布快照"）。
- 确认 → `POST /bi/report/{id}/publish`；返回 shareUrl + expireAt；toast 含"分享链接已生成，有效期至 {expireAt}"。含敏感数据 → approvalStatus=PENDING_APPROVAL。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1196 | 敏感分享未审批不可用 | 落地页空态 + 生成弹窗审批说明 |
| 1197 | 有效期非法（7~30 天外） | InputNumber 预校验 + 红字 |
| 1193/1194 | 快照查询并发/超时 | 常规 toast |
| R10 订阅 | 不开放 | [订阅] 按钮隐藏 |
| 访问密码错误 | 打开带密码分享链接 | 落地页密码输入 + "密码错误，请重试" |
| 发布链接 REVOKED/EXPIRED | — | 落地页空态 "链接已失效/已过期" |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-211（订阅周期日/周/月，钉钉+工作台推送） | 订阅弹窗 + 推送说明 |
| BR-212（分享不突破权限） | 落地页按查看者过滤 + 提示条 |
| BIS-R1（推送摘要+快照留档） | 快照回溯弹窗 |
| BIS-R2（按查看者权限过滤） | 分享打开流程 |
| BIS-R3（敏感分享 R4 审批 7~30 天） | 审批队列 + 1196/1197 |
| BIS-R4（推送失败补发 1 次） | FAILED_RESENT 橙标 |
| V3-B5（推送集群化调度 + 重试 3 次） | 推送说明文案（服务端） |
| DW-4（发布链接密码/有效期/快照/访问统计） | Tab3 发布管理 + §7.4 四段式抽屉 |

---

# P4 查询性能监控（BI 域，R1/R9）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/ims/bi/query/perf`（**无菜单** · R1/R9） |
| 页面级别 | 三级（运维监控页） |
| 前置依赖 | 报表查询使用产生埋点 |
| 权限 | R1/R9 |
| 用户 | 系统管理员 R1（BR-204 验证） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 查询性能监控（BR-204 / V3-B6 验证）  [日期范围 RangePicker: 默认近7天]    │
├──────────────────────────────────────────────────────────────────────────┤
│ 指标卡（GET /bi/query/perf-stats）:                                       │
│ ┌────────┬────────┬────────┬────────────┬──────────────┐                │
│ │查询总量 │平均耗时 │P95耗时  │超30s次数    │异步转化次数   │                │
│ │ 12,840 │ 1,230ms│ 8,200ms│  3 ⚠       │ 18 (V3-B6)   │                │
│ └────────┴────────┴────────┴────────────┴──────────────┘                │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 慢报表清单（topSlowReports）                                            │
│ [报表|平均耗时|查询次数]  avgCostMs 超标红色 → 点击跳报表设计器建议优化   │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
interface BiPerfStatsResp {
  totalQueries: number;
  avgCostMs: number;
  p95CostMs: number;
  over30sCount: number;                  // BR-204 超时统计
  asyncConvertedCount: number;           // V3-B6 异步转化统计
  topSlowReports: Array<{ reportId: number; reportName: string; avgCostMs: number; queryCount: number }>;
}
```

## 4. 交互流程

加载 `GET /bi/query/perf-stats`（默认近 7 天）；over30sCount > 0 → 卡片橙红警示；topSlowReports 行点击 → 跳 P1 设计器（编辑该报表，建议缩小筛选范围）。

## 5~7. 查询条件表 / 表格列定义 / 抽屉

查询条件：dateRange。慢报表表：报表编号/名称、平均耗时（>30000ms 红）、查询次数。无抽屉。

## 8. 错误处理

只读监控；接口失败常规 toast。

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-204（10 万行 < 30s 监控） | P95/超 30s 次数卡 + 慢报表清单 |
| V3-B6（异步转化统计） | asyncConvertedCount 卡 |
| 9.2 安全（查询审计） | 查询日志服务端留痕（本页消费统计） |

---

## 操作序列（OPS / DW 对标 · 2026-10-03 修订）

> **说明**：现网 OPS **无** V3 全量拖拽设计器；M6 为 **八张固定报表**（`DataReport.vue`）——故 P1 设计器的**实现蓝本仍以 OPS UX-M6 为准**，DW `bi-designer` 仅作**完整链路的参照系**（补齐 IMS 原型的交互深度）。IMS `biDesign` 对标参考原型 `bi-designer`，已升级为 **三栏自由拖拽设计器（FREE 布局）**，并保留 GRID 四区语义。

| 页面键 | 步骤 | 用户操作 | 参照 | API / 状态 |
|--------|------|----------|------|------------|
| `biDesign` | 1 | 选数据集（指标库 / 已发布查询）+ 浏览字段（分组/搜索/行数预警） | DW 左栏 · V3 P1 左栏 | `GET /ims/bi/report/datasets`（V3）· P1 可用 **指标库 + CUSTOM_QUERY** |
| `biDesign` | 2 | 从**组件库**拖入组件到画布 → 拖动定位 → 图层面板调序 | DW `bi-designer` §9.9.2 | 前端 `state.bidsn.comps[]`（FREE 布局） |
| `biDesign` | 3 | 右栏三区配置：**基础属性**（标题/坐标/尺寸）· **数据源**（字段+聚合+动态参数）· **交互**（联动/跳转/刷新） | DW `prop-sec` §9.9.2/3/4 | `POST /ims/bi/report/query`（按 compId 独立取数） |
| `biDesign` | 4 | 运行预览（组件级 SYNC/ASYNC 双态） | 画布内联状态条 | `POST /ims/bi/report/query`（预览态临时 components） |
| `biDesign` | 5 | **保存并发布**（生成缩略图 + 版本自增） | 顶栏 DW `bi-publish` | `POST/PUT …/report` · `POST …/report/{id}/publish` |
| `biDesign` | 6 | 配置发布：方式 / 可见范围 / 密码 + 有效期 / 展示刷新 | DW `bi-publish` 四段式 | 含敏感数据 → PENDING_APPROVAL（BIS-R3） |
| `biDesign` | — | `DWS_AGGREGATION` 宽表 | 左栏第三项 | **V3 P2+** · 原型置灰，不 toast BLOCKED |

---

# 附录 A：模块级约定

1. **超时异步双态（V3-B6，模块 UI 核心）**：统一"异步任务卡"组件（P1/P2 复用）——SYNC（<10s 直接渲染 + costMs/cacheHit 状态条）与 ASYNC（任务卡：任务号 + 完成通知钉钉/工作台 + 轮询/稍后领取 + OSS 下载/inline 双回传）两分支；并发上限 10/用户（1193）；超 30s 强制终止（1194，BR-204）。**v2.6.26 补充**：自由布局下异步态为**组件级**（单组件转异步，其余组件正常渲染）。
2. **权限继承（BR-212/BIR-R1）**：查询结果行级双重过滤（创建者 ∩ 查看者）全链路服务端执行；分享链接打开后同样按查看者过滤；前端不做任何权限判断（仅 1008/1196 空态处理）。
3. **口径纪律（BIR-R3）**：数据集字段必须引用指标管理已登记口径（metricCode）；属性面板数据源配置仅可选中已登记指标；计算字段表达式白名单（SUM/AVG/COUNT/MAX/MIN + 四则运算），1191/1192 双拦截。
4. **版本化（BIR-R4）**：报表修改 version 自增，分享链接永不变（指向最新发布版本）；DRAFT/PUBLISHED 两态。
5. **敏感分享审批链（BIS-R3）**：目标含成本/利润 → PENDING_APPROVAL → R4 审批（通过生效/驳回）→ EXPIRED（7~30 天到期）；1196/1197 双拦截。
6. **订阅推送（BR-211/BIS-R1/R4/V3-B5）**：日/周/月周期；钉钉 + 工作台双通道 + 快照摘要；失败重试 3 次后补发 1 次（FAILED_RESENT 标记）；快照可回溯（BIS-R1）。
7. **下钻层级（BIQ-R1~R3/V3-B4）**：预定义维度层级链（平台→账号→场次；部门→团队→人；年→月→日）；单元格穿透双跳转（MODULE_DETAIL 来源模块详情 / DC_TRACE 复用 DC-001 穿透）；SQL 白名单（1195）。
8. **缓存（V3-B2/B3）**：高频指标预计算 DWS/ADS 命中优先；Redis TTL = 数据集新鲜度（默认 15 分钟）；预览状态条展示 cacheHit。
9. **既有能力复用**：指标管理/自定义查询已完成，本模块数据集三种来源（METRIC_LIB/CUSTOM_QUERY/DWS_AGGREGATION）直接消费，不重复建设。
10. **设计器布局态（v2.6.26 新增）**：`layoutMode` = **GRID**（行/列/值/筛选四区派生，等价旧"表单式"）｜**FREE**（自由拖拽绝对定位，默认）。两者共享同一套**组件模型**与**数据源/交互配置**语义；GRID 可视为 FREE 的一种**自动排列投影**，切换布局不丢失数据源配置。组件最小 80×80，栅格吸附 40px。
11. **联动图约束（v2.6.26 新增）**：组件联动为**有向图**；发布前须通过**无环校验**（A→B→C 不得回到 A）；单组件下游联动目标 ≤ 10，跨报表跳转每报表 ≤ 5。

# 附录 B：BR / BIR / BIQ / BIS / V3-B 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-204 | 10 万行级查询 < 30s | P1 行数预警、P1/P2 1194、P4 监控 |
| BR-211 | 订阅周期日/周/月 + 推送 | P3 订阅弹窗 |
| BR-212 | 行级双重过滤，分享不突破权限 | P1 分享弹窗提示、P2 1008、P3 落地过滤 |
| BR-214 | 竞品资产引用留痕 | P1 compAssetRefs |
| BIR-R1 | 权限交集过滤 | 服务端 + 页面提示条 |
| BIR-R2 | 超 30s 提示缩小范围 | 1194 处理 |
| BIR-R3 | 不自造口径 | P1 字段列表 + 表达式白名单（1191/1192） |
| BIR-R4 | 版本化链接不变 | version toast |
| BIQ-R1 | 下钻最深到场次/明细 | P2 DC_TRACE 分支 |
| BIQ-R2 | 下钻受性能+权限 | P2 1194/1008 |
| BIQ-R3 | 明细跳来源模块详情 | P2 MODULE_DETAIL 分支 |
| BIS-R1 | 推送摘要+快照留档 | P3 快照弹窗 |
| BIS-R2 | 分享按查看者过滤 | P3 落地页 |
| BIS-R3 | 敏感分享 R4 审批 7~30 天 | P3 审批队列 + 1196/1197 |
| BIS-R4 | 推送失败补发 1 次 | FAILED_RESENT 标 |
| V3-B1 | 元数据驱动零代码 | P1 组件属性面板数据源配置（FREE 布局下由组件派生行/列/值） |
| V3-B2/B3 | 预计算 + Redis 缓存 | 组件状态条 cacheHit |
| V3-B4 | 动态 SQL + 白名单 | P2 1195 |
| V3-B5 | 推送集群化调度重试 3 次 | P3 推送说明 |
| V3-B6 | 并发 10/用户 + 10s 转异步 | 异步任务卡（全模块核心组件）+ P4 统计 |
| DW-1（三栏拖拽 + 4 类 21 组件） | 组件库/画布/图层 | P1 §2 · §4 §10-1/2/3 |
| DW-2（组件数据源 + 动态参数） | `${compId.field}` | P1 §7.4 · §10-5 |
| DW-3（联动 + 循环依赖） | 有向无环图 | P1 §7.5 · 附录 A-11 |
| DW-4（发布链接 + 密码 + 有效期 + 快照） | 四段式发布 | P1 §7.9 · P3 发布管理 · §10-9/10 |
| DW-5（导入导出 JSON 模板） | 模板复用 | P1 §7.8 · §10-12 |

（全文完）
