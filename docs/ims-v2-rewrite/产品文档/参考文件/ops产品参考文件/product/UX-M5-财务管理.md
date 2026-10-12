# UX-M5-财务管理

> **版本**：v1.3 | 2026-10-02
> **关联 PRD**：[`PRD-M5-财务管理.md`](./PRD-M5-财务管理.md)
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

| 页面 ID | 名称 | Football 路由 | standalone（历史） | 关联 FR | permission |
|---------|------|------|---------|
| P-M5-001 | 账号成本管理 | `/ops/finance/account-cost` | `/account-cost` | FR-M5-001 | `oa:cost:list` |
| P-M5-003 | ROI 分析 | `/ops/finance/roi-analysis` | `/roi-analysis` | FR-M5-002 | `oa:roi:list` |
| P-M5-004 | ROI 趋势 | 同页 Tab/图表 | `/finance/roi/trend` | FR-M5-002 | `oa:roi:list` |

> **偏差**：原 spec 独立录入页 `/finance/cost/edit` 已合并入 P-M5-001「成本管理」弹窗。

---

## 2. P-M5-001 账号成本管理（AccountCostManage）

### 2.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 平台 Tab | `el-tabs` | 全部 + 7 平台枚举 |
| 筛选 | `TableSearch`：账号名称关键词 | - |
| 列表 | 表格 | 采购/过程/总成本列右对齐 |
| 分页 | `Pagination` | pageNo/pageSize |
| 查看抽屉 | `el-drawer` 640px | 账号信息 + 成本明细；`DictLabel` 渲染 platform/costType/period |
| 成本管理弹窗 | `el-dialog` 820px | 采购区 + 过程成本表 |
| 过程成本表单 | 嵌套 `el-dialog` 520px | 类型/金额/日期/支付方式/周期 |

### 2.2 控件规格

| 控件 ID | 类型 | 字典/实体 |
|---------|------|----------|
| TAB-PLATFORM | Tab | `dict_platform_type` 子集 |
| F-KEYWORD | `<Input />` | 账号名称 |
| COL-PURCHASE | 列 | 采购成本 `PURCHASE` 汇总 |
| COL-PROCESS | 列 | 过程成本非 PURCHASE 汇总 |
| COL-TOTAL | 列 | 采购 + 过程 |
| BTN-VIEW | Link | 查看 → 抽屉 |
| DL-PLATFORM | `<DictLabel dict-type="dict_platform_type" />` | 列表 + 抽屉账号平台 |
| DL-COST-TYPE | `<DictLabel dict-type="dict_cost_type" />` | 明细表成本类型 |
| DL-PERIOD | `<DictLabel dict-type="dict_cost_period" />` | 明细表归属周期 |
| BTN-MANAGE | Link | 成本管理 → 弹窗 |
| F-COST-TYPE | `<DictSelect dict-type="dict_cost_type" />` | 过程成本 |
| F-PAY-METHOD | `<DictSelect dict-type="dict_cost_pay_method" />` | 支付方式 |
| F-PERIOD | `<DictSelect dict-type="dict_cost_period" />` | 周期 |

### 2.3 交互规则

- 切换平台 Tab → 重置分页并重新 `loadData`
- 采购成本：单条 `PURCHASE` 类型记录，保存时 create 或 update
- 过程成本：列表内新增/编辑/删除，类型非 `PURCHASE`
- 金额展示：`formatMoney` 千分位，最小 0.01

---

## 3. P-M5-003 ROI 分析

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| F-ACCOUNT | `<AccountSelect />` | `oa_account` |
| F-DATE-RANGE | `<DateRangePicker />` | - |
| F-DIMENSION | `<Select />` | 固定值（ip_group/account/person） |
| TBL-ROI | 表格 | 聚合 |

### 3.1 ROI 卡片

```
+---------------------+
|  ROI = 4.20         |
|  营收 100w          |
|  成本 23.8w         |
+---------------------+
```

### 3.2 趋势图（Vue `RoiAnalysis.vue`）

| 系列 | 图表类型 | 轴 |
|------|----------|-----|
| ROI | 折线 | X=日期 · Y=ROI |
| 营收 vs 成本 | **双轴** 折线/柱 | 左轴营收 · 右轴成本（图例可切换） |
| 成本结构 | 饼图 / 表格 | 类型(`dict_cost_type`) · 金额 · 占比 · 账号均摊 · 环比 |

**C 表格列（汇总）**：维度名称 · 营收 · 总成本 · 利润 · ROI(tag 阈值 2/3) · 趋势箭头。

**B 筛选**：IP 组 · 账号 · 日期 · 维度(ip_group/account/person)。

**API**：`GET /admin-api/ops/finance/roi/summary` · `.../trend` · `.../cost-breakdown`（见 API-M5）。

**导出**：表格区 Excel · 大数据 confirm。

---

## 4. 跨页通用

- 账号/IP 组选择器强制
- 金额字段 `<InputNumber :precision="2" />`
- Skeleton / Error / Empty 三态

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.3：§3.2 ROI 双轴/成本结构/表格列/API |
| 2026-06-11 | v1.2：Football 路由 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*
