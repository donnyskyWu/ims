# BI0 - 指标 / 报表 / 自定义查询 页面规格（OPS M6 并入）

> 完整 PRD 17a。前缀：`/admin-api/ims/bi`  
> **交互 SSOT**：`docs/product/UX-M6-数据分析.md`（P-M6-001~015）  
> V3 自助下钻/订阅见 `BI-数据分析-页面规格.md`，**不替代**本模块 M6 闭环。  
> **走查 #13**：原 DC-003「全链路数据看板」侧栏入口并入 **数据报表 · 大屏**（v2.6.27 走查 #21：**大屏配置独立菜单退役**，大屏归为报表类型 `DASHBOARD`；API 仍用 `/admin-api/ims/dc/dashboard/*`，与 BI 数据集并存，不重复建穿透页）。  
> **走查 #17 深化**：四能力 IA/API 见 `一体化管理/产品规划/IMS-数据决策-四能力设计分析-20260930.md`；**功能/逻辑/DW 原型对标**见 `…-产品逻辑与原型对标-20260930.md`；**报表设计**属 **数据报表** L2（`/ims/bi/report/designer`），**不在**数据指标 L2。  
> **走查 #21（v2.6.27 · 2026-10-04）**：「**标准报表**」更名「**报表中心**」；**报表管理 + 报表设计合并单菜单**（设计转隐藏路由）；**大屏归为报表类型**（报表/大屏），**「大屏配置」菜单退役**。

## 0.1 导航（走查 #21 · v2.6.27 · SSOT = 完整 PRD v2.6.27）

**侧栏路径（本模块）**：数据决策 → **数据指标**（可展开 L2）→ **指标管理 · 指标分析** 两叶。  
**同域路由外置**：**报表中心**（原「标准报表」）/ **大屏**（报表类型）→ **数据报表** L2；自定义查询 → **数据分析** L2。  
**兼容**：`go('bi0')` → 指标管理；`go('bi0Standard')` → **报表中心**（`bi0Report`）；`go('bi0Screen')`/`go('bi0ScreenConfig')` → **报表管理**（`biList`，大屏为报表类型，独立菜单退役）。元数据维护在 **16 数据采集**。  
**交叉**：DC-003 看板 API = **数据报表 · 大屏**（`reportType=DASHBOARD`）；V3 自助报表 = **数据报表 · 报表管理/设计**。

## 0. 页面清单（须独立路由或同级菜单，禁止压成 5 Tab 示意）

| 页面 ID | 名称 | 路由 | FR |
|---------|------|------|-----|
| P1 | 指标管理 | `/ims/bi/metric` | FR-M6-001 |
| P2 | 指标分析 | `/ims/bi/metric-analysis` | FR-M6-001 |
| P3 | **报表中心**（原「数据报表中心」） | `/ims/bi/report` | FR-M6-002 入口 |
| P3a~h | 八张标准报表 | `/ims/bi/report/{slug}` | 见下表 |
| P3i | 财务概览 | `/ims/bi/finance-overview` | FR-M6-003 |
| P3j/k | 漏斗分析 | `/ims/bi/funnel`、`/ims/bi/funnel/custom` | FR-M6-004 |
| P4 | 自定义查询 | `/ims/bi/query` | FR-M6-005 |
| P5 | 数据大屏 | `/ims/bi/screen/:id` | FR-M6-006 全屏暗色 |
| ~~P5b~~ | ~~大屏配置~~ | ~~`/ims/bi/screen-config`~~ | **v2.6.27 退役**（并入报表管理，`reportType=DASHBOARD`；深链归一化到 `biList`） |

### 八张标准报表 slug（与 OPS 一致，禁止改名）

| slug | 名称 |
|------|------|
| unified-account | 全平台账号视图 |
| account-status | 账号状态监控 |
| video-output | 短视频产出统计 |
| live-duration | 直播时长统计（作者·小时） |
| cost-allocation | 账号成本分摊 |
| roi | ROI 分析报表 |
| team-config | IP 团队人员配置 |
| account-alert | 账号异常预警 |

## 1. 通用筛选条（P3a~h 统一）

IP 组树 | 平台字典 | 日期范围 | 时间维度 DAY/WEEK/MONTH | [查询] [重置] [导出 Excel/PDF]

布局：**汇总卡 → 图表 → 明细表**（UX-M6 §4）。

## 2. P1 指标管理

**用户目标**：统一指标口径 CRUD + SQL 预览；供标准报表、大屏 METRIC、17b `METRIC_LIB` 引用（BIR-R3）。**禁止**趋势分析（→ P2）、拖拽报表（→ 17b）。

### 2.1 功能（对标 DW §9.7.1，实现 SSOT = UX-M6 P-M6-001）

| 功能块 | 说明 | DW 原型 id | IMS 本期 |
|--------|------|------------|----------|
| 指标列表 | 编码/名称/类型/状态筛选；CRUD | `mt-list` | ✅ |
| 指标定义表单 | Builder 或 COMPOSITE 公式 | `mt-form` | ✅ Drawer |
| 试算预览 | 执行 preview SQL（**Builder 内联面板**，≤20 行） | `mt-list` | ✅ BTN-PREVIEW → `POST /ops/metric/preview` |
| 指标分类 | 列表 **分类** 列 + 表单 **指标分类** 字段 | `mt-list` / `mt-form` | ✅ **v2.6.25 采列**（`BI0_METRIC_CATEGORIES`） |
| 计算频率 | 列表 **计算频率** 列 + 表单字段（实时/每日/每周/每月） | `mt-form` | ✅ **v2.6.25 采列**（`BI0_METRIC_FREQS`） |
| 结果历史查询 | 批次/维度/版本对比 | `mt-result` | ❌ → P2 分析或 OPS 能力 |
| 分类树 | 多级分类（≤3 级树） | `mt-category` | ❌ non-goal |
| 计算调度 | 定时/依赖触发落库 | `mt-schedule` | ❌ non-goal |

### 2.2 业务逻辑 / 流程

1. 分析师维护指标编码唯一、类型与 Builder/公式一致 → **预览通过** → 保存（启用态供引用）。
2. 删除/停用前 **引用保护**（已绑定查询/大屏/17b 数据集则阻断）。
3. 消费侧（八张报表、P5 widget、17b）**只读引用**，不得在本页改口径。

### 2.3 界面结构

- **顶区**：QueryBar（名称/编码 + 指标类型 `dict_perf_metric_type`）+ 主按钮「新建指标」+ 导出。
- **主区**：**TBL-METRIC**（ID、指标名称、指标编码、类型、**分类**、数据源、计算公式、**计算频率**、单位、状态、操作：编辑 / 删除）。
- **Drawer（960px）**：F-NAME、F-CODE、F-METRIC-TYPE、**F-CATEGORY**、**F-FREQ**、**F-UNIT**、F-BUILDER（非 COMPOSITE）/ F-FORMULA（COMPOSITE）、可选 F-DESCRIPTION；底栏「保存」；**预览为 Builder 内联面板**（≤20 行），非二级弹窗。
- **指标类型二分（2026-10-03 订正）**：`dict_perf_metric_type` = **BASIC 基础指标 / COMPOSITE 复合指标**。非 COMPOSITE 走 `MetricBuilder`（数据源 / 计算方式 / 计算字段 / 汇总字段 / 关联表 / 查询条件 / 字段列表侧栏）；COMPOSITE 仅「数据源 + 公式手输」。
- **交叉引用**：DW `mt-list` 宽表列 IMS 不照搬（无 DW 维度/频率列 unless UX-M6 扩展）；布局深度见 `IMS-完整系统-UI原型.html` · `bi0Metric`。

## 3. P4 自定义查询

**用户目标**：对已映射实体 ad-hoc 探索，保存并 **发布** 供大屏 QUERY 与 17b `CUSTOM_QUERY` 消费。**禁止**元数据 CRUD（→ **16 · 元数据维护**）。

**页级 Tab（本模块唯一 L3 Tab）**：**自定义查询** | **我的查询**

### 3.1 功能（对标 DW §9.8，实现 SSOT = UX-M6 P-M6-013）

| 功能块 | DW 原型 id | IMS 本期 |
|--------|------------|----------|
| 查询列表 hub | `qy-list` | 合并进「我的查询」Tab |
| QueryBuilder + SQL 预览 + 结果表/图 | `qy-editor`（grid2） | ✅ Tab「自定义查询」；**布局以 OPS 为准**（非 DW 左右分栏） |
| 分组 / 排序 / 结果行数限制 | `qy-editor` ③ | ✅ **v2.6.25 采列**：GROUP BY / ORDER BY / LIMIT（默认 1000 · 上限 10 万） |
| SQL 复制 | `qy-editor` 右栏 | ✅ **v2.6.25 采列**（`bi0QueryCopySql`） |
| 模板库（个人/公开） | `qy-templates` | ❌ 用「保存+发布」替代 |
| 定时计划 + 邮件 | `qy-schedules` | ❌ → **17b 订阅**（BIS-R1/BR-211 钉钉+工作台；邮件通道暂不开放） |

### 3.2 业务逻辑 / 流程

1. 选 **COLLECT 已映射** 实体 → 配置字段/过滤/聚合/排序 → 预览 SQL → 执行 preview。
2. 保存 → 草稿；**发布** → 大屏/17b 可选数据源。
3. 「我的查询」：执行 / 编辑 / 删除 / 发布；未映射 → **1261** + 按钮跳转 `/ims/collect/metadata`；超时 → **1262**。

### 3.3 界面结构（实现 SSOT = OPS 现网 + UX-M6 §6）

**OPS 源码引用（football-front）**

| 区域 | 文件 | 要点 |
|------|------|------|
| 页壳 + 双 Tab | `apps/web-ele/src/views/ops/analysis/CustomQuery.vue` | `el-tabs`：**自定义查询** \| **我的查询**；内联结果放在 **page tabs 外**（避免嵌套 tabs） |
| QueryBuilder | `apps/web-ele/src/components/ops/QueryBuilder.vue` | 主区表单（数据源/展示字段/计算/汇总/关联/可折叠条件/SQL 预览）+ 侧栏字段列表 |
| 结果区 | `apps/web-ele/src/components/ops/QueryResultPanel.vue` | 可折叠条件摘要 + 结果卡；子 Tab **结果列表 \| 图表展示**；分页 + 导出 |
| 条件控件 | `MetricConditionInput.vue` | 按 M8 元数据 `queryConditionType` |
| SQL 生成 | `constants/ops/metricSchema.ts` | `QueryBuilderConfig`、`buildQuerySqlFromConfig` |
| API | `api/ops/custom-query.ts` | list/create/preview/update/execute/publish |

| Tab | 布局（对齐 CustomQuery.vue） |
|-----|--------------------------------|
| **自定义查询** | 可折叠 **查询配置** 卡：标题栏 **[执行查询] [保存为我的查询]**；展开内嵌 **QueryBuilder**（含 SQL 预览 textarea）。其下（与页 Tab 同级）**QueryResultPanel**：执行后出现；条件摘要 + **[结果列表 \| 图表展示]** + 分页 + 导出 |
| **我的查询** | 卡片「已保存查询」+ 总数；筛选：**名称**、**状态**（DRAFT/PUBLISHED，**现网硬编码**非 `dict_query_status`）、**查询**；表格列：**查询名称、创建人、状态、更新时间**；行操作：**执行 / 编辑 / 发布**（非 PUBLISHED）/ **删除**；底部分页 |

**弹窗（OPS）**：保存/编辑（名称 + 状态 + QueryBuilder）；已保存项 **执行** → 宽弹窗内 QueryResultPanel。

顶栏辅助：「元数据维护」深链 16（COLLECT P4m）。路由 OPS：`#/ops/analysis/custom-query`（菜单 6125 · `ops:custom-query:list`）。IMS 原型：`bi0Query`（`/ims/bi/query`）。

## 4. P5 / P5b 数据大屏

**用户目标**：暗色全屏 KPI/图表/列表 + 自动刷新；配置与全屏 **筛选一致**（UX-M6 §7~§8）。**禁止**穿透画布（→ DC-001）；DW 自由拖拽大屏 → **17b 报表设计**（v2.6.26 采纳，≠ 17a 大屏模板）。

### 4.1 功能（对标 DW §9.9.5 + `bi-list` dashboard 类型，实现 = M6）

| 功能块 | DW 原型 | IMS |
|--------|---------|-----|
| 大屏/报表同列表、新建大屏 | `bi-list` | ❌ IMS 大屏无 DW 卡片目录，仅 **配置叶 + 全屏路由**（报表侧卡片目录见 **17b 报表管理**） |
| 拖拽画布编大屏 | `bi-designer` | ❌ 17a 仍为 **模板 + widget 表单**（P5b）；**自由拖拽设计器** 归 **17b 报表设计**（v2.6.26 采纳） |
| 全屏展示 + 自动刷新 | `biFullscreen` | ✅ P5 |
| 发布链接/密码 | `bi-publish` | ✅ **v2.6.26 采纳** → **17b 报表设计** P3 §7.4 四段式发布（方式/可见范围/访问控制/展示刷新） |

### 4.2 业务逻辑 / 流程

1. 管理员在 **P5b** 选模板 → 逐 widget 配置数据源（BUILTIN / METRIC / 已发布 QUERY）→ 保存。
2. 「预览大屏」→ P5 全屏；顶栏全局筛选与配置预览 **同参**。
3. 可选 DC-003 数据经 BUILTIN/扩展 widget；API `/admin-api/ims/dc/dashboard/*`，菜单入口仍在本模块。

### 4.3 界面结构

| 页 | 结构 |
|----|------|
| P5b | 工具栏（模板/保存/预览全屏）；**左** widget 列表与数据源表单；**右** ScreenPreviewPanel（暗色 KPI 网格 + 图/表占位） |
| P5 | 暗色顶栏（scope、日期、IP 组、平台、刷新）+ KPI≤6 + STAT/CHART/LIST |

原型：`bi0Screen`（配置/全屏模式切换 mock）。DW `bi-list` 卡片视图 **不**迁入 17a。

## 5. 规则

- 查询只打 IMS 库（现网 `oa_*`）；账号 ROI 营收类标注 Football WebAPI 已落库汇总。
- 行级权限 BR-305。

---

## OPS 前后端对照（2026-10-02 · M6）

> **现网前缀**：`/admin-api/ops/metric/**` · `/admin-api/ops/query/**` · `/admin-api/ops/report/**` · `/admin-api/ops/dashboard-config/**` · `/admin-api/ops/dashboard/**`  
> **Vue**：`football-front/apps/web-ele/src/views/ops/analysis/` · **API**：`metric.ts` · `custom-query.ts` · `report.ts` · `dashboard.ts`

| IMS L3 | Vue SFC | Java Controller | 主按钮 → API |
|--------|---------|-----------------|--------------|
| 指标管理 | `MetricManage.vue`（`components/ops/MetricBuilder.vue`） | `metric/MetricController` | 新增 `POST /ops/metric/create` · 编辑 `PUT …/update` · 删 `DELETE /ops/metric/{id}` · 试算 `POST …/preview` · 列表 `GET …/list` |
| 指标分析 | `MetricAnalysis.vue` | `MetricController`（analyze/preview 同服务） | 运行分析（多指标 + 绑定参数）· 导出 |
| 标准报表入口 | `DataReport.vue`（8 卡片）· 各子页 `Report*.vue` | `report/ReportController` | 卡片跳转子路由；子页 查询/重置/导出 · 例 `GET /ops/report/unified-account/list` · `…/export` |
| 自定义查询 | `CustomQuery.vue`（`QueryBuilder.vue`） | `query/CustomQueryController` | Tab「自定义查询」：`POST /ops/query/preview` · `POST …/create`；Tab「我的查询」：`GET …/list` · 执行 `POST …/{id}/execute` · 发布 `POST …/{id}/publish` · 编辑 `PUT …/update` · **删除：前端演示，后端暂无 DELETE** |
| 大屏配置/全屏 | `screen/ScreenConfig.vue` · `DataScreen.vue` · `DataScreenFullscreen.vue` | `dashboard/DashboardConfigController` · `DashboardController` | 配置 list/save · 全屏 `GET /ops/dashboard/*`（widget 绑定 METRIC/QUERY/BUILTIN） |

---

## DW 借鉴落地（2026-10-03 · v2.6.26）

> **借鉴权威**：`参考文件/DW-PRD-Phase1.md`（§9.7 指标管理 / §9.8 自定义查询 / §9.9 BI 报表与大屏）+ `参考文件/DW-UI-Prototype-Phase1.html`（`mt-list`/`mt-form`/`qy-editor`/`bi-list`/`bi-designer`/`bi-publish`）。
> **定位**：**借结构、不搬 API**。IMS 实现 SSOT 仍为 **OPS UX-M6 + 本规格**；DW 的 `/api/*`、SQL Server / T-SQL 方言、Python FastAPI 均**不映射**。

| # | 落地项 | DW 参照 | 原型实现 | 断言 |
|---|--------|---------|----------|------|
| 1 | 标准报表（→**报表中心**）**逐张差异化** | `mt-result` / `qy-editor` 的「汇总卡 → 图表 → 明细表」 | `BI0_REPORT_DEFS`（8 slug 各自 KPI / 明细列 / 图表类型）+ `bi0SvgBars` / `bi0SvgPie` | 8 张 SVG≥1、明细行≥3、内容互异 |
| 2 | 标准报表（→**报表中心**）**统一筛选条** | `mt-result` 筛选区 | IP 组树 / 平台字典 / 日期范围 / **时间维度 DAY·WEEK·MONTH**；导出 **Excel + PDF** | 含「时间维度」「PDF」 |
| 3 | 指标管理 **分类 / 计算频率** | §9.7.1 指标定义字段 | `BI0_METRIC_CATEGORIES` / `BI0_METRIC_FREQS`；列表 2 列 + Drawer 2 字段 | 表头含「分类」「计算频率」 |
| 4 | 自定义查询 **分组/排序/限制 + 复制 SQL** | §9.8.1 查询配置 | QueryBuilder ③ 区 + `bi0QueryCopySql`；结果行展示耗时与截断 | 含 GROUP BY / ORDER BY / 结果行数 / 复制 SQL |
| 5 | 查询结果 **图表 Tab 真渲染 + 多图表切换** | §9.8.2 多图表类型 | `bi0QueryResultPanel` 按 `state.q.bi0ChartType` 三态渲染（`bi0SvgBars`/`bi0SvgLine`/`bi0SvgPie`）；**抽屉与内联双容器重绘**（`bi0QueryReRenderResult`） | 抽屉/内联两路径「图表展示」Tab 均可切换；柱/折/饼 SVG 互异 |
| 6 | 指标分析 **趋势真图表** | `mt-result` 折线 | 按选中指标着色的柱状 SVG | `#content svg` ≥ 1 |
| 7 | 大屏 widget **四类** | §9.9.2 / §9.9.5 | KPI（≤6）/ STAT / CHART / LIST，数据源 BUILTIN / METRIC / 已发布 QUERY | 含 KPI·STAT·CHART·LIST |

**DW 借鉴升级（v2.6.26 · 原 non-goal → 已采纳）**：以下三项原列 non-goal，现**移入 17b 报表设计（BI-数据分析规格 P1）** 并已落地原型：

| 原 non-goal 项 | DW 参照 | 现落点 | 说明 |
|----------------|---------|--------|------|
| DW **50 组件自由拖拽画布** | `bi-designer` §9.9.2 | **《BI-数据分析-页面规格》P1 §2/§10** | IMS 裁剪为 **4 类 21 组件 + 自由拖拽 + 图层面板 + 属性三区**（非 50 组件平铺） |
| 报表 **发布链接密码 / 有效期** | `bi-publish` §9.9.5 | **《BI-数据分析-页面规格》P3 §7.4** | **五段式**发布抽屉（v2.6.27 补 ① 发布去向：报表中心/菜单）：去向/方式/可见范围/访问控制（密码+7~30 天）/展示刷新 |
| DW **导入 / 导出 JSON 模板** | §9.9.1 | **《BI-数据分析-页面规格》P1 §7.8** | 列表 [导入模板] + 行 [导出模板 JSON]；数据源失效警告 |

**仍为 non-goal（两文档一致）**：DW 指标**分类树**、**结果历史/版本对比**、**计算调度落库**（无指标结果库）；DW 查询**公共模板库**、**定时计划+邮件/钉钉**（用「保存 + 发布」替代）；DW **多租户报表模板市场**、**iframe 内嵌携带登录态**。

**八张报表 slug 与 OPS 子页**：`ReportUnifiedAccount.vue` · `ReportAccountStatus.vue` · `ReportVideoOutput.vue` · `ReportLiveDuration.vue` · `ReportCostAllocation.vue` · `ReportRoi.vue` · `ReportTeamConfig.vue` · `ReportAccountAlert.vue` — 路径见 `#/api/ops/report.ts`。

**私域报表（扩展）**：`privateDomainReport.ts` · `MonthlyAchievementReport.vue` · `WeeklyFunnelReport.vue`（卡片挂于 `DataReport.vue`，非八张标准 slug）。

---

## 操作序列（OPS → 原型 · 2026-10-02）

| 页面键 | 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|--------|------|----------|----------|------------|
| `bi0Metric` | 1 | 新增/编辑 → 试算 → 保存 | `MetricManage.vue` + `MetricBuilder.vue` | `POST/PUT /ops/metric/*` · `POST …/preview` → `BI0_METRICS` |
| `bi0Metric` | 2 | 删除（引用检查） | 列表删除 | `DELETE /ops/metric/{id}` · `refCount>0` 阻断 |
| `bi0Query` | 1 | 配置 →「执行查询」 | `CustomQuery.vue` + `QueryBuilder.vue` | `POST /ops/query/preview` → 结果面板 |
| `bi0Query` | 2 | 「保存为我的查询」 | 保存抽屉 | `POST /ops/query/create` → Tab「我的查询」 |
| `bi0Query` | 3 | 我的查询「发布」 | 行内发布 | `POST /ops/query/{id}/publish` → `st=已发布` |
| `bi0Report` | 1 | 卡片打开报表 → 查询 | `DataReport.vue` + `Report*.vue` | `GET /ops/report/{slug}/list` |
| `bi0Screen` | 1 | Widget 配置 → 保存 → 预览全屏 | `ScreenConfig.vue` · `DataScreenFullscreen.vue` | dashboard-config save · `GET /ops/dashboard/*` |
| `bi0Analysis` | 1 | 多选指标 + `MetricConditionInput` 绑定参数 → **运行分析** | `MetricAnalysis.vue` §B 筛选区 | `GET /ops/metric/simple-list` · `POST /ops/metric-analysis/run` |
| `bi0Analysis` | 2 | Tab **指标明细**：每指标 card · 动态列表格 + 分页 | 同 Vue C-Tab1 | run 响应 `columns`/`rows` |
| `bi0Analysis` | 3 | Tab **指标趋势**：图表类型 / X·Y 轴 → ECharts | 同 Vue C-Tab2 | 同 run 结果前端制图 · **非**独立 drag 设计器 |
| `bi0Analysis` | 4 | **导出**（有结果时） | 客户端 Excel | 与 OPS 一致 |

**本地源码（wd 已检入）**：`football-front/apps/web-ele/src/views/ops/analysis/`（`MetricManage.vue` · `MetricAnalysis.vue` · `CustomQuery.vue` · `DataReport.vue` · `Report*.vue`）· `screen/ScreenConfig.vue` · `DataScreenFullscreen.vue`；API `#/api/ops/metric.ts` · `custom-query.ts` · `report.ts` · `dashboard.ts`。Java Controller 类名见 §OPS 对照表与 `docs/engineering/API-M6-数据分析.md`。
