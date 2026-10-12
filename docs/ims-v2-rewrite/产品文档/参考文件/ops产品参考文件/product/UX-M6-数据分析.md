# UX-M6-数据分析

> **版本**：v1.6 | 2026-10-02
> **关联 PRD**：[`PRD-M6-数据分析.md`](./PRD-M6-数据分析.md)
> **全局规范**：[`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md)

---


> **视觉规范参考**：[`开发规范/UI设计与开发规范.md`](../../开发规范/UI设计与开发规范.md)（仅原型/设计阶段）
> **实现技术栈**：[`TECH-CONSTRAINTS.md § 1.2`](../engineering/TECH-CONSTRAINTS.md)（Vue 3 + Element Plus）
> **决策记录**：[`ADR-002`](../../adr/ADR-002-前端规范源选择.md)


## 0. OPS 设计 SSOT

> **设计规范**：[UX-OPS-设计规范.md](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[UX-OPS-页面原型索引.md](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[OPS-MENU-ROUTE-INDEX.md](../delivery/OPS-MENU-ROUTE-INDEX.md)

## 1. 页面清单

> **菜单 SSOT**：下列「Football 路由」对应 [`OPS-MENU-ROUTE-INDEX`](../delivery/OPS-MENU-ROUTE-INDEX.md) 6103 数据分析分组。P-M6-002~009 为 **ReportCenter 内 Tab/子视图**，菜单入口 `/ops/analysis/data-report`。

| 页面 ID | 名称 | Football 路由（菜单） | 组件内子路由（历史） | FR |
|---------|------|----------------------|----------------------|-----|
| P-M6-001 | 指标管理 | `/ops/analysis/metric` | `/analysis/metric` | FR-M6-001 |
| P-M6-002 | 全平台账号视图 | `/ops/analysis/data-report`（Tab） | `/analysis/report/unified-account` | FR-M6-002 |
| P-M6-003 | 账号状态监控 | 同上 | `/analysis/report/account-status` | FR-M6-002 |
| P-M6-004 | 短视频产出统计 | 同上 | `/analysis/report/video-output` | FR-M6-002 |
| P-M6-005 | 直播时长统计 | 同上 | `/analysis/report/live-duration` | FR-M6-002 |
| P-M6-006 | 账号成本分摊 | 同上 | `/analysis/report/cost-allocation` | FR-M6-002 |
| P-M6-007 | ROI 分析报表 | 同上 | `/analysis/report/roi` | FR-M6-002 |
| P-M6-008 | IP 团队人员配置 | 同上 | `/analysis/report/team-config` | FR-M6-002 |
| P-M6-009 | 账号异常预警 | 同上 | `/analysis/report/account-alert` | FR-M6-002 |
| P-M6-010 | 总体财务分析 | `/ops/analysis/financial-analysis` | `/analysis/finance-overview` | FR-M6-003 |
| P-M6-011 | 漏斗分析 | `/ops/analysis/funnel-analysis` | `/analysis/funnel` | FR-M6-004 |
| P-M6-012 | 漏斗自定义 | 同页 | `/analysis/funnel/custom` | FR-M6-004 |
| P-M6-013 | 自定义查询 | `/ops/analysis/custom-query` | `/analysis/query` | FR-M6-005 |
| P-M6-014 | 数据大屏 | `/ops/analysis/screen` | `/analysis/dashboard/:id` | FR-M6-006 |
| P-M6-015 | 大屏配置 | `/ops/analysis/screen-config` | `/analysis/dashboard-config` | FR-M6-007 |
| P-M6-016 | 指标分析 | `/ops/analysis/metric-analysis` | — | FR-M6-001 |

---

### P-M6-005 直播时长（2026-08-26）

| 区域 | 内容 |
|------|------|
| 筛选 | IP 组 + 日期范围 |
| 趋势 | ECharts 双轴：场次（柱）+ 总时长/小时（折线） |
| 明细表 | 日期 · **作者** · 场次 · 总时长(小时) · 均时长(小时) |
| 导出 | 客户端 Excel（作者/场次/时长列） |
| **不含** | 峰值在线、账号维度、平台列 |

---

## 2. 通用筛选条

所有报表页：

| 控件 | 类型 | 字典 |
|------|------|------|
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| F-PLATFORM | `<DictSelect dict-type="dict_platform_type" />` | 字典 |
| F-DATE-RANGE | `<DateRangePicker />` | - |
| F-TIME-DIM | `<Select />` | DAY/WEEK/MONTH |
| F-REPORT-TYPE | `<DictSelect dict-type="dict_report_type" />` | 字典 |

---

## 3. P-M6-001 指标管理

| 控件 | 类型 |
|------|------|
| F-NAME | `<Input />` |
| F-CODE | `<Input />` |
| F-METRIC-TYPE | `<DictSelect dict-type="dict_perf_metric_type" />`（**现网**：基础指标 BASIC / 复合指标 COMPOSITE） |
| F-BUILDER | `<MetricBuilder />`（非 COMPOSITE） | 数据源/计算/汇总/joins/过滤 → SQL |
| F-FORMULA | `<CodeEditor />` 或 Builder 输出（COMPOSITE 仅手输） |
| F-DESCRIPTION | `<TextArea />` | 仅前端，未持久化 |
| BTN-PREVIEW | 按钮 | 调用 `POST /metric/preview` |
| TBL-METRIC | 表格 |

---

## 3.2 P-M6-016 指标分析（`/ops/analysis/metric-analysis`）

**组件**：`ops/analysis/MetricAnalysis.vue` · **权限**：`oa:metric-analysis:list`

| 区域 | 控件 / 行为 |
|------|-------------|
| B | `F-METRIC-IDS` 多选 `<el-select>`（指标库 `metricName/metricCode`）· 动态参数区 `MetricConditionInput`（按指标定义 `queryConditionType` + 可选 `dictType`）· [运行分析][重置][导出] |
| C-Tab1 | 「指标明细」：每指标 card Tab · 结果表（列随指标 SQL 动态） |
| C-Tab2 | 「指标趋势」：多指标同图 ECharts（实现允许时）· 图表类型 柱/折/**饼** + X 轴 + Y 轴 + **系列字段** |

**API**：选项 `GET /admin-api/ops/metric/simple-list` · 运行 `POST /admin-api/ops/metric-analysis/run`（body：`metricIds` + `bindParams`）· 导出客户端 Excel（有结果时启用）

**空/加载/错**：未选指标点运行 → 表单校验 · 无结果 `el-empty`「请选择指标并运行分析」· `v-loading` 覆盖结果区

**边缘**：复合指标参数缺失时后端 1501；导出大数据量提示「仅导出当前结果集」

---

## 4. P-M6-002~009 八张报表

### 4.0 入口与路由（Vue 对齐）

| 入口 | Football 路由 | 组件 | permission |
|------|---------------|------|------------|
| 报表中心（卡片） | `/ops/analysis/data-report` | `ReportCenter.vue` / `DataReport.vue` | `oa:report:list` |
| 单张报表（推荐） | `/ops/analysis/report/*`（见下表 `name`） | `Report*.vue` | 同左 |
| 老 URL 兜底 | 同菜单 + `DataReport.vue` 内 **8 Tab** | Tab `name` 切换内嵌视图 | 同左 |

**布局变体**：单页报表为 **B 筛选 + C 图表/卡/表**（[`UX-OPS-设计规范` §4](./UX-OPS-设计规范.md)）；`DataReport.vue` 额外含卡片导航 + Tab 兜底。

**导出（ADR-018）**：`exportToExcel` + `fetchAllPaginated` 拉全量；无独立 PDF 按钮（Spec 历史文案已废弃）。

**字段键**：列表 VO **snake_case**；前端 `reportField(row, snake, camel)` 双读。

**API SSOT**：[`API-M6-数据分析.md`](../engineering/API-M6-数据分析.md) §2。

---

### 4.1 P-M6-002 全平台账号视图

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/unified-account` · `ReportUnifiedAccount.vue` |
| **B 筛选** | `IpGroupTreeSelect` → `ipGroupId` · 平台 `el-select`/`dict_platform_type` → `platformType` · `DateRangePicker` → `startDate`/`endDate` · [查询][导出] |
| **C 汇总** | 4× `el-statistic`：账号总数 · 总粉丝 · 总营收 · 综合 ROI |
| **C 表格列** | 账号 · 平台(`DictLabel`) · IP 组 · 粉丝数 · 营收 · 成本 · ROI |
| **行操作** | 无 |
| **API** | `GET .../report/unified-account/list` · `GET .../stats` · 导出客户端 Excel（list 分页拉全） |
| **状态** | `v-loading` 表格 · 失败清空列表 · 导出失败 `ElMessage.error` |

---

### 4.2 P-M6-003 账号状态监控

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/account-status` · `ReportAccountStatus.vue` |
| **B 筛选** | `AccountSelect` → `accountId` · 日期范围 · [查询][导出] |
| **C 图表** | ECharts 折线：X=日期 · 系列=在线/异常/掉线（`trend` 点字段 `online`/`abnormal`/`offline`） |
| **C 摘要卡** | 在线 · 异常 · 掉线 · 恢复（`summary`） |
| **C 表格列** | 日期 · 账号 · 状态(`el-tag`：NORMAL/ONLINE/WARNING/ABNORMAL/OFFLINE/RECOVERED) · 备注 |
| **API** | `GET .../account-status/trend` · `.../summary` · `.../log` · 导出=log 全量 Excel |

---

### 4.3 P-M6-004 短视频产出

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/video-output` · `ReportVideoOutput.vue` |
| **B 筛选** | IP 组 · `AccountSelect`（联动 `ipGroupId`）· 日期 · [查询][重置][导出] |
| **C 图表** | 日产出趋势（折线/柱，`trend`） |
| **C 排行表** | # · 账号 · 平台 · 产出数 · 均播放(formatK) · 爆款数(`top_count`) |
| **C 明细表** | 日期 · 账号 · 标题 · 平台 · 阅读数 · 点赞数 · 分页 |
| **API** | `GET .../video-output/list` · `.../trend` · `.../ranking` · 导出=list 全量 |

---

### 4.4 P-M6-005 直播时长

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/live-duration` · `ReportLiveDuration.vue` |
| **B 筛选** | IP 组 · 日期 · [查询][导出] |
| **C 图表** | 双轴：场次(柱) + 总时长/小时(折)（`trend`：`session_count`/`total_duration`） |
| **C 表格列** | 日期 · **作者**(`author_name`) · 场次 · 总时长(小时) · 均时长(小时) |
| **不含** | 峰值在线 · 账号维度列 · 平台列（v1 · API-M6 §2.4） |
| **API** | `GET .../live-duration/list` · `.../trend` · 导出=list 全量 |

---

### 4.5 P-M6-006 账号成本分摊

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/cost-allocation` · `ReportCostAllocation.vue` |
| **B 筛选** | `AccountSelect` · 日期 · [查询][导出] |
| **C 表格列** | 账号 · 成本类型(`dict_cost_type`) · 金额(元) · 占比(`share_ratio`×100%) · 备注 |
| **API** | `GET .../cost-allocation/list` · 导出=list 全量 |

---

### 4.6 P-M6-007 ROI 分析报表

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/roi` · `ReportRoi.vue` |
| **B 筛选** | IP 组 · 日期 · [查询][导出] |
| **C 表格列** | 日期 · IP 组 · 平台 · 营收 · 成本 · ROI(`el-tag` ≥1 success) |
| **API** | `GET .../report/roi/list` · 导出=list 全量 |

---

### 4.7 P-M6-008 IP 团队人员配置

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/team-config` · `ReportTeamConfig.vue` |
| **B 筛选** | IP 组（可选）· [查询][导出] |
| **C 表格列** | IP 组 · 人员数 · 账号数 · 人均账号 · 人均营收 · 人效 |
| **边缘** | 后端若返回数组，前端 **客户端分页**（`clientPaging`） |
| **API** | `GET .../report/team-config/list` · 导出=当前结果集 Excel |

---

### 4.8 P-M6-009 账号异常预警

| 项 | 规格 |
|----|------|
| 路由 / Vue | `/ops/analysis/report/account-alert` · `ReportAccountAlert.vue` |
| **B 筛选** | 日期范围 · [查询][导出] |
| **C 表格列** | 日期 · 账号 · 级别(`dict_alert_level` + tag 色) · 类型(映射 ACCOUNT_OFFLINE/DATA_ABNORMAL/FAN_FLUCTUATION) · 预警内容 |
| **API** | `GET .../report/account-alert/list` · 导出=list 全量 |

---

### 4.9 二级面：DataReport 8 Tab（老 URL）

与 §4.1–4.8 **字段一致**；Tab `name`：`unified-account` | `account-status` | `video-output` | `live-duration` | `cost-allocation` | `roi-analysis` | `team-config` | `account-alert`。Tab 内筛选为简化版（部分硬编码平台选项），**新开发以独立 `Report*.vue` 为准**。

---

## 4.10 P-M6-010 总体财务分析

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/analysis/financial-analysis` |
| Vue | `ops/finance/FinancialAnalysis.vue`（菜单在「数据分析」，组件在 finance 目录） |
| permission | `oa:financial-analysis:list` |
| 布局 | **B** 筛选 + **C** KPI / 图表 / 双表（无独立 A 区标题栏，用 `ContentWrap` 分段） |

### 4.10.1 筛选（B）

| 控件 ID | 类型 | query / 行为 |
|---------|------|----------------|
| F-DATE-RANGE | `el-date-picker` daterange | `startDate` / `endDate`（必填，默认近 30 天） |
| F-IP-GROUP | `<IpGroupTreeSelect scope="accessible" />` | `ipGroupId` 可空 |
| F-DIMENSION | `<el-select>` | `IP_GROUP` \| `ACCOUNT`（维度拆解粒度） |
| BTN-QUERY | 按钮 | [查询] → 并行拉 summary + trend + cost breakdown |
| BTN-EXPORT | 按钮 | [导出] → `exportRoi`；失败降级 `exportToExcel(breakdownRows)` |

页内双条 `el-alert`：数据权限提示（`DATA_SCOPE_FILTER_HINT`）+ 数据来源说明（订单归因 + 账号成本台账，非外部财务实时）。

### 4.10.2 KPI 区（4 卡）

| 指标 | 字段 |
|------|------|
| 总营收 | `summary.totalRevenue`（¥，2 位小数） |
| 总成本 | `summary.totalCost` |
| 总毛利 | `summary.totalProfit`（前端 revenue − cost） |
| 综合 ROI | `summary.roi` |

### 4.10.3 图表「营收趋势」

- ECharts 折线：**营收** · **成本** · **毛利**（三系列同轴）
- X：`statDate` / `date`；无数据时文案「所选时间范围内暂无趋势数据」

### 4.10.4 表格「维度拆解」

| 列 | 说明 |
|----|------|
| 维度项 | `name` |
| 营收 / 成本 / 毛利 | 右对齐 ¥ |
| ROI | `el-tag`：≥1 success，否则 danger |

数据来自 `getRoiAnalysis` 的 `details[]`，受 **F-DIMENSION** 影响。

### 4.10.5 表格「成本结构」

| 列 | 说明 |
|----|------|
| 成本类型 | `DictLabel dict_cost_type` 或 `typeLabel` |
| 金额 | `amount` |
| 占比 | `percentage`% |

数据来自 `getRoiBreakdown` → `byType[]`。

### 4.10.6 API（`/admin-api/ops`，与 `#/api/ops/finance` 一致）

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/ops/finance/roi/analysis` | KPI + 维度拆解（query：日期、ipGroupId、dimension） |
| GET | `/ops/finance/roi/trend` | 趋势 `points[]` |
| GET | `/ops/finance/roi/breakdown` | 成本结构 `byType[]` |
| POST | `/ops/finance/roi/export` | 异步/后端导出（失败走前端 Excel） |

### 4.10.7 空 / 加载 / 错

| 状态 | 表现 |
|------|------|
| 未选日期点查询 | `ElMessage.warning('请选择时间范围')` |
| 加载 | 页级 `v-loading` |
| 接口失败 | Toast「加载财务分析数据失败」；表格 `empty-text` |

---

## 5. P-M6-011 / P-M6-012 漏斗分析

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/analysis/funnel-analysis` |
| Vue | `ops/analysis/FunnelAnalysis.vue` |
| permission | `oa:funnel-analysis:list` |
| 布局 | 顶栏 **Tab**：`preset` 预设漏斗 \| `custom` 自定义漏斗 |

### 5.1 预设漏斗 Tab（P-M6-011）

**筛选**

| 控件 | 类型 | 说明 |
|------|------|------|
| F-FUNNEL | `<el-select>` | 漏斗定义 `GET /ops/funnel/list`（展示 `funnelType` 为 `PRIVATE_DOMAIN` 或 `CONVERSION`） |
| F-DATE-RANGE | daterange | 传 `getFunnelData` query |
| F-PLATFORM | `<DictSelect dict_platform_type />` | 可空；私域漏斗忽略平台 |
| BTN-QUERY / RESET / EXPORT | 按钮 | 导出 `POST /ops/funnel/export` |

**私域提示**：选中 `funnelType=PRIVATE_DOMAIN` 时展示 info Alert（奥创好友 + 身份桥接，与平台筛选无关）。

**图表区**

- ECharts 漏斗图 + 摘要条：首步总量 · 末步留存 · 总转化率 · 最大流失环节（名 + dropOffRate%）
- `v-loading` 覆盖图表区

**明细表**

| 列 | 说明 |
|----|------|
| 顺序 | `stepOrder` |
| 步骤 | `name` |
| 数量 | 千分位 |
| 较上步(%) | `<50` 标红 |
| 流失数 | 负号红色 |
| 总转化(%) | `conversionRate` |

### 5.2 自定义漏斗 Tab + 编辑器（P-M6-012）

**列表（C）**

| 列 | 行操作 |
|----|--------|
| ID · 漏斗名称 · 类型(`dict_funnel_type`) · 状态(启用/停用) | [查看数据] 切回预设 Tab 并加载该漏斗 · [删除] |

- 客户端分页（`pageNum`/`pageSize` 切片 `customFunnelList`）
- A 区：[新建自定义漏斗]

**新建对话框（700px）— 字段表**

| 字段 | 控件 | 必填 |
|------|------|------|
| funnelName | Input max 50 | ✅ |
| funnelType | `<DictSelect dict_funnel_type />`（默认 `CUSTOM`） | ✅ |
| steps[] | 动态列表：序号 · `stepName` Input · `eventCode` `<el-select>`（选项 `GET /ops/metric/list` → metricCode/metricName） | ≥1 步 |

- [+ 添加步骤] / 行内 [删除]
- 保存：`POST /ops/funnel/create`（body 含 steps 与 stepOrder）
- **无拖拽排序**（现网按添加顺序；若需 DnD 开 FR）

**删除确认**：`MessageBox.confirm` → 删除 API 后刷新列表。

### 5.3 漏斗 API 汇总

| 方法 | 路径 |
|------|------|
| GET | `/ops/funnel/list` |
| GET | `/ops/funnel/{id}/data` |
| POST | `/ops/funnel/create` |
| POST | `/ops/funnel/export` |

### 5.4 空 / 加载 / 错

未选漏斗查询 → 空图表；加载/导出失败 Toast。

---

## 6. P-M6-013 自定义查询

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/analysis/custom-query` |
| Vue | `ops/analysis/CustomQuery.vue` |
| permission | `oa:custom-query:list` |

### 6.1 页级 Tab

| Tab name | 标签 | 说明 |
|----------|------|------|
| `builder` | 自定义查询 | QueryBuilder + 内联结果 |
| `saved` | 我的查询 | 已保存列表 |

### 6.2 自定义查询 Tab

**可折叠「查询配置」卡片**

| 控件 | 行为 |
|------|------|
| QueryBuilder | 数据源 / 字段 / 条件 / 聚合 / JOIN → 同步 `sqlText` |
| BTN-EXECUTE | 「执行查询」→ `POST /ops/query/preview`（body：`sqlText`, `pageNum`, `pageSize`） |
| BTN-SAVE-INLINE | 「保存为我的查询」→ 480px dialog（名称 1–50、状态 草稿/已发布）→ `POST /ops/query/create`（含 `params` JSON 存 builder） |

**QueryResultPanel**（Tab 外渲染，避免嵌套 tabs）

- 条件：已执行且（有行 \| `inlineExecuted`）
- 分页：`page-change` → 再次 `preview` 同 SQL
- 子 Tab：结果表（动态中文表头）\| 图表（柱/折线，基于当前页数据）
- 导出：`exportToExcel`

执行成功后 **折叠** 配置区（`configExpanded=false`）。

### 6.3 我的查询 Tab

**筛选**：名称（前端 contains 过滤）· 状态（草稿 `DRAFT` / 已发布 `PUBLISHED`）

**表格列**：查询名称 · 创建人 · 状态 tag · 更新时间

**行操作**

| 操作 | 行为 |
|------|------|
| 执行 | 90% 宽 dialog + `POST /ops/query/{id}/execute` 分页 |
| 编辑 | 960px dialog：名称/状态 + QueryBuilder → `PUT /ops/query/update` |
| 发布 | 仅草稿：`POST /ops/query/{id}/publish` |
| 删除 | `MessageBox.confirm` → delete API |

列表：`GET /ops/query/list`（`pageNum`/`pageSize`/`status`）。

### 6.4 状态与字典

| 控件 | 说明 |
|------|------|
| 保存/编辑 status | 现网 **硬编码** DRAFT/PUBLISHED（非 `dict_query_status` Select） |

### 6.5 空 / 加载 / 错

| 场景 | 表现 |
|------|------|
| 无 SQL 执行/保存 | warning Toast |
| 列表/执行失败 | error Toast + 空表 |
| loading | 表格/executing 态 |

---

## 7. P-M6-014 数据大屏（全屏）

| 项 | 值 |
|----|-----|
| Football 路由 | `/ops/analysis/screen`（query/path 带 `id`，默认 INTERNAL `98601` / EXTERNAL `98602`） |
| Vue | `ops/screen/DataScreenFullscreen.vue` |
| permission | `oa:screen:list`（菜单 SSOT） |
| 布局 | **全屏 C**（暗色顶栏 + KPI/STAT/图表/列表网格，无侧边菜单） |

### 7.1 顶栏全局筛选

| 控件 ID | 类型 | 说明 |
|---------|------|------|
| F-SCOPE | 按钮组 | 内部数据 / 外部数据（切换模板 scope） |
| F-DATE-RANGE | 原生 `<select>` 暗色 | 今日 / 近7天 / 近30天 |
| F-IP-GROUP | 原生 `<select>` 暗色 | 全部 IP 组 + 树扁平选项 |
| F-PLATFORM | 原生 `<select>` 暗色 | 全部平台 + `dict_platform_type` |
| F-REFRESH | 原生 `<select>` 暗色 | 30s / 1min / 5min / 不刷新 |

- 筛选项变更 → `GET /admin-api/ops/dashboard/{id}/data`（query 由 `buildDashboardDataQuery`：scope/dateRangeKey/ipGroupId/platformType）
- 模板切换 → `GET /admin-api/ops/dashboard-config/list` + 路由 `id` 同步
- 与配置页预览区筛选参数一致

### 7.2 内容区布局

```
+----------------------------------------------------------+
| 顶栏：标题 | 模板 | [内部|外部] | 日期 | IP组 | 平台 | 刷新 |
+----------------------------------------------------------+
| KPI 网格（最多 6 列）                                     |
+----------------------------------------------------------+
| [今日工作概览] STAT 网格（仅 INTERNAL scope 显示标题）    |
+----------------------------------------------------------+
| 图表行 ×2（两列）                                         |
| 末行：单图 + 列表并排 / 或列表通栏                        |
+----------------------------------------------------------+
```

- 暗色主题；样式对齐 `dashboard.html` 原型
- ECharts 渲染 CHART；`ScreenListTable` 渲染 LIST
- **子组件清单**：`ScreenListTable` · ECharts 实例 per widget · 原生暗色 `<select>` 顶栏筛选 · scope 切换按钮组
- **状态**：全页 `loading-overlay` · `errorMsg` + [重试] · 无 widget 时空网格隐藏
- **确认流**：退出全屏 / 退出链接 → 路由回 OPS 首页（无 MessageBox）

### 7.3 组件行为

| type | 全局日期 | IP 组 / 平台 |
|------|----------|--------------|
| KPI | 生效 | 生效 |
| STAT | **不生效**（固定当天） | 生效 |
| CHART / LIST | 生效 | 生效 |

### 7.4 大屏类型

| 控件 | 字典 |
|------|------|
| F-DASHBOARD-TYPE | `<DictSelect dict-type="dict_dashboard_type" />` |

---

## 8. P-M6-015 大屏配置

| 项 | 值 |
|----|-----|
| Football 路由 | `/ops/analysis/screen-config` |
| Vue | `ops/screen/ScreenConfig.vue` |
| permission | `oa:screen-config:list` |
| 布局 | **A 工具栏** + **B 左配置 / C 右预览**（双栏） |

### 8.1 布局

```
+----------------------------------------------------------+
| 工具栏：模板选择 | 保存 | 预览大屏                        |
+----------------------------------------------------------+
| 左栏（配置）          | 右栏（预览 + 说明）                |
| - 模板信息            | - 预览筛选条（同全屏）             |
| - 指标卡（≤6）        | - ScreenPreviewPanel              |
| - 今日统计            | - 配置说明                         |
| - 图表（≤4）          |                                    |
| - 列表                |                                    |
+----------------------------------------------------------+
```

### 8.2 组件编辑弹窗（`el-dialog` 680px）

| 字段 | 组件 | 说明 |
|------|------|------|
| 标题 | `el-input` | 必填 |
| 数据源 | `el-select` | BUILTIN / METRIC / QUERY |
| 内置键 | `el-select` filterable | KPI/STAT/CHART/LIST 各内置枚举（`BUILTIN_*_KEYS`） |
| 指标 | `el-select` | `getMetricList` · 变更触发 schema 列预览 |
| 查询 | `el-select` | `getCustomQueryList` 已发布项 |
| 值字段 | `el-input` | KPI/STAT：`metric_value` / `value` |
| 图表类型 | `el-select` | line / bar / pie |
| X/Y/分组轴 | `el-select` filterable | METRIC/QUERY 动态列；BUILTIN 只读 |
| Y 轴聚合 | `el-select` | SUM/AVG/COUNT/MAX/MIN |
| 列表列 | checkbox + 列标题 input | `listFieldRows` |
| 排序字段 / limit | `el-select` + `el-input-number` | LIST 专用 |

**保存**：工具栏 [保存] → `updateDashboardFull` / 新建 → `createAnalyticsDashboard` · [预览大屏] → 路由 `/ops/analysis/screen?id=`。

**API**：[`API-M6`](../engineering/API-M6-数据分析.md) §5 `dashboard-config/list` · `dashboard/{id}/data` · `full-update`。

### 8.3 全局筛选映射（METRIC / QUERY）

弹窗内「全局筛选映射」分区：

| 控件 | 类型 | 说明 |
|------|------|------|
| F-GF-DATE | `<Select />` 可清空 | 日期字段（`metricSchema` 可过滤日期列） |
| F-GF-IP | `<Select />` 可清空 | IP 组字段（`metricSchema` 可过滤 IP 组列） |

- 选项随所选指标/查询的数据源变化
- 保存时写入 widget `globalFilter`（含 `dateColumn` / `ipGroupColumn`）
- 平台筛选：内置组件自动生效；自定义 SQL 平台过滤见 ADR-015

### 8.4 预览区筛选

与 P-M6-014 顶栏一致：`IpGroupTreeSelect` + `DictSelect dict_platform_type` + 日期快捷项。

---

## 9. 跨页通用

- 所有 IP/账号 强制选择器
- 所有 报表类型/平台/状态 用 `<DictSelect />`
- 大屏：暗色主题 + 自动刷新

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-03 | 订正 §3.2 C-Tab2 文案「对比视图」→「**指标趋势**」并补图表类型/系列字段（对齐 `MetricAnalysis.vue`）；§3 F-METRIC-TYPE 标注现网字典取值 |
| 2026-10-02 | v1.6：§4.10 总体财务 · §5–6 漏斗/自定义查询 Football+API 对齐 `CustomQuery`/`FunnelAnalysis`/`FinancialAnalysis` |
| 2026-10-02 | v1.5：§4.0–4.9 八报表逐页字段/API · P-M6-014/015 Football 路由与子组件 · `/ops/dashboard` API |
| 2026-06-13 | v1.4：直播时长 S-tier |
| 2026-06-11 | v1.3：大屏全局筛选映射 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*
