# UX-M3-绩效核算

> **版本**：v1.2 | 2026-10-02
> **关联 PRD**：[`PRD-M3-绩效核算.md`](./PRD-M3-绩效核算.md)
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
|---------|------|---------------|-------------------|---------|------------|
| P-M3-001 | 考核模板 | `/ops/performance/perf-template` | `/perf-template` | FR-M3-001 | `oa:perf:list` |
| P-M3-002 | 模板编辑（抽屉/弹窗） | 同页深链 | `/perf/template/:id` | FR-M3-001 | `oa:perf:list` |
| P-M3-003 | 考核执行 | `/ops/performance/perf-execution` | `/perf-execution` | FR-M3-002 | `oa:perf:list` |
| P-M3-004 | 执行详情 | 同页 | `/perf/record/:id` | FR-M3-002 | `oa:perf:list` |
| P-M3-005 | 绩效结果 | `/ops/performance/perf-result` | `/perf-result` | FR-M3-003 | `oa:perf:list` |
| P-M3-006 | 个人趋势 | 结果页抽屉 | `/perf/result/:userId/trend` | FR-M3-003 | `oa:perf:list` |
| P-M3-007 | 订单归因 | `/ops/performance/order-attribution` | `/order-attribution` | FR-M3-004 | `oa:order-attribution:list` |
| P-M3-008 | ROI（已归 M5） | `/ops/finance/roi-analysis` | — | FR-M5-002 | `oa:roi:list` |

---

## 2. P-M3-001 考核模板列表

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-POSITION | `<DictSelect dict-type="dict_position" />` | 字典 |
| F-NAME | `<Input />` | - |
| F-ACTIVE | `<DictSelect dict-type="dict_yes_no" />` | 字典 |
| TBL-TPL | 表格 | `oa_perf_template` |
| BTN-ADD | "新增模板" → **弹窗**（非路由跳转） | - |
| BTN-EDIT | 行内编辑 → `/perf/template/:id` | - |
| BTN-ACTIVATE | "启用" | - |

**新增弹窗**：岗位、模板名、指标列表（`metricId` 来自 `getMetricOptions`）、权重、算分方式、评分标准。

---

## 3. P-M3-002 考核模板编辑

### 3.1 布局

```
+----------------------------------------------------------+
| [返回] 岗位 [▾]  模板名 [__]  [保存]  [启用]              |
+----------------------------------------------------------+
| 指标列表                                                  |
| - 指标1（权重40%，自动算分）  [编辑] [删除]              |
| - 指标2（权重30%，自动算分）  [编辑] [删除]              |
| - 指标3（权重30%，人工算分）  [编辑] [删除]              |
| 合计：[100%]                                              |
| [添加指标]                                                |
+----------------------------------------------------------+
| 预览：[区间图]                                            |
+----------------------------------------------------------+
```

### 3.2 指标编辑弹窗

| 控件 | 类型 | 字典/实体 | 必填 |
|------|------|----------|------|
| F-METRIC | `<el-select>` 绑定真实 `metricId` | `oa_metric_definition`（`getMetricOptions`） | ✅ |
| F-WEIGHT | `<InputNumber :precision="2" :min="0" :max="100" />` | - | ✅ |
| F-CALC | `<DictSelect dict-type="dict_perf_calc_method" />` | 字典 | ✅ |
| F-STANDARD | `<ScoreStandardEditor />` | - | 条件（自动/混合时必填） |
| F-CALC-LABEL | 显示文本（自动/人工/混合） | - | - |

### 3.3 区间编辑器

```
[区间 1] 最小 0  最大 60  得分 0  等级 D  [删除]
[区间 2] 最小 60 最大 75  得分 60 等级 C  [删除]
[区间 3] 最小 75 最大 85  得分 75 等级 B  [删除]
[区间 4] 最小 85 最大 95  得分 85 等级 A  [删除]
[区间 5] 最小 95 最大 9999 得分 100 等级 S [删除]
[添加区间]
```

---

## 4. P-M3-003/004 考核执行列表/详情

### 4.1 列表

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| F-TARGET | `<UserSelect />` | `sys_user` |
| F-PERIOD | `<DictSelect dict-type="dict_perf_period" />` | 字典 |
| F-STATUS | `<DictSelect dict-type="dict_perf_status" />` | 字典 |
| TBL-RECORD | 表格 | `oa_perf_record` |

### 4.2 详情（弹窗/抽屉）

| 区域 | 内容 |
|------|------|
| 基本信息 | 考核人/被考核人/周期/模板/状态 |
| 指标明细 | 表格（指标、值、得分、手动调整、最终得分、备注） |
| 操作 | 自动算分（重新计算）、人工调整、确认结果 |

### 4.3 人工调整

- 每行有"调整"按钮
- 调整框显示当前基础分 + 输入框
- 校验：调整幅度 ≤ 20%

---

## 5. P-M3-005 绩效结果列表

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-USER | `<UserSelect />` | `sys_user` |
| F-PERIOD | `<DictSelect dict-type="dict_perf_period" />` | 字典 |
| F-GRADE | `<DictSelect dict-type="dict_perf_grade" />` | 字典（V34） |
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| TBL-RESULT | 表格 | `oa_perf_record` |

---

## 6. P-M3-006 个人绩效趋势

```
+--------------------------------------+
| 折线图：近 6 月得分                  |
| X 轴：月份                            |
| Y 轴：分数                            |
+--------------------------------------+
| 等级分布（饼图）：S 1 / A 2 / B 2 / C 1 |
+--------------------------------------+
| 历史记录列表                          |
+--------------------------------------+
```

---

## 7. P-M3-007/008 订单归因/ROI

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| F-ACCOUNT | `<AccountSelect />` | `oa_account` |
| F-DATE-RANGE | `<DateRangePicker />` | - |
| TBL-ATTR | 表格 | `oa_order_attribution` |
| CARD-ROI | 卡片 | 实时计算 |

### 7.1 ROI 卡片

```
[ROI = 4.2]
[营收 100w]
[成本 23.8w]
```

---

## 8. 薄页补全（DOC-UX-PAGE-FULL-01）

> **API**：`/admin-api/ops/performance/**` · Vue `ops/performance/*.vue`

### 8.1 P-M3-001 考核模板

| C 列 | 岗位(`dict_position`) · 模板名 · 指标数量 · 状态 · 创建时间 · 操作(编辑/启用/删除) |
| 新增 dialog | 岗位 · 模板名 · 指标表格(`metricId`/`weight`/`calcMethod`/区间) · 权重合计 100% 校验 |
| API | `GET .../perf-template/list` · `POST .../create` · `PUT .../update` |

### 8.2 P-M3-003 考核执行

| C 列 | 被考核人 · IP 组 · 周期 · 模板 · 状态 · 得分 · 操作(详情/算分) |
| **执行 drawer** | 基本信息 · 指标明细表(值/得分/调整/备注) · [自动算分][人工调整][确认] |
| 调整 | 单行弹窗 · 幅度 ≤20% 校验 |
| API | `GET .../perf-record/list` · `POST .../recalculate` · `POST .../adjust` |

### 8.3 P-M3-005 绩效结果

| C 列 | 用户 · IP 组 · 周期 · 等级(`dict_perf_grade`) · 总分 · 操作(趋势/导出) |
| 导出 | MessageBox「导出当前筛选」→ Excel |
| API | `GET .../perf-result/list` |

### 8.4 P-M3-007 订单归因

| C 列 | 订单号 · 账号 · IP 组 · 归因模型 · 归因金额 · 订单时间 · 渠道 |
| dialog/筛选 | 归因模型(`dict_attribution_model`) · 日期 · 账号 · IP 组 |
| API | `GET .../order-attribution/list` |

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.2：§8 四菜单页列/抽屉/API |
| 2026-06-07 | v1.1：模板编辑区间 |

---

## 9. 跨页通用约定

- 所有 `*_id` 字段必须用选择器
- 岗位 / 周期 / 算分方式 / 状态一律 `<DictSelect />`
- IP 组选择器：`<IpGroupTreeSelect />`（联动筛选）
- Skeleton / Error / Empty 三态完整

---

*下一步：API Spec / STATE / SLICES / CHECKLIST / TESTCASES。*
