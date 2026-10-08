# PRD-M5-财务管理

> **业务域**：M5 财务管理
> **功能模块**：账号成本 + ROI 分析
> **详细设计章节**：5.23、5.24
> **版本**：v1.1 | 2026-10-02
> **状态**：Draft
> **关联 UX**：[`UX-M5-财务管理.md`](./UX-M5-财务管理.md)（v1.3 · 2026-10-02）
> **全局规范**：[`docs/engineering/GLOBAL-CONVENTIONS.md`](./../engineering/GLOBAL-CONVENTIONS.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| 模块 | M5 财务管理 |
| 业务域 | 财务管理（FINANCE） |
| 详细设计 | `## 5.23~5.24` |
| 父 PRD | `@完整PRD-v9.1-开发版.md` |
| 关联 UX | `docs/product/UX-M5-财务管理.md` |
| 关联 API | `docs/engineering/API-M5-财务管理.md` |

---

## 1. 概述

### 1.1 一句话描述

管理账号成本（购买 + 过程成本）与营收归因（订单 → 账号/IP/人员），支持 ROI 趋势分析、成本结构分析。

### 1.2 目标与指标

| 维度 | 目标 | 可量化指标 |
|------|------|------------|
| 自动化 | 80% 成本自动归因 | 归因覆盖率 ≥ 80% |
| 实时 | 实时 ROI | ROI 更新 ≤ 5min |
| 准确性 | 0 漏算 | 财务月结 0 误差 |

### 1.3 术语表

| 术语 | 定义 |
|------|------|
| **购买成本** | 账号初始购买费用（一次性） |
| **过程成本** | 运营人力/设备/运营等（持续） |
| **ROI** | 投资回报率：`SUM(营收) / SUM(成本)` |
| **成本归属周期** | 一次性 / 月度 / 季度 / 年度 |
| **成本类型** | 购买成本 / 过程成本（人力/设备/运营） |
| **付款方式** | 现金 / 转账 / 支付宝 / 微信 / 银行承兑 |

---

## 2. 用户与权限

| 能力 \ 角色 | 系统管理员 | 运营管理者 | 财务 | 数据分析师 |
|------------|-----------|-----------|------|-----------|
| 查看成本 | ✅ | ✅ | ✅ | ✅ |
| 录入/编辑成本 | ✅ | ✅ | ✅ | ❌ |
| 查看 ROI | ✅ | ✅ | ✅ | ✅ |
| 导出 ROI | ✅ | ✅ | ✅ | ✅ |

---

## 3. 范围

### 3.1 In Scope（2 个 FR 模块）

| FR 编号 | 名称 | 优先级 | 详细设计 |
|---------|------|--------|---------|
| FR-M5-001 | 账号成本管理（购买+过程） | P0 | 5.23 |
| FR-M5-002 | ROI 分析 | P0 | 5.24 |

### 3.2 Out of Scope

1. ❌ **不实现** 实际付款（依赖财务系统）
2. ❌ **不实现** 预算管理
3. ❌ **不实现** 应收/应付账款

---

## 4. 功能需求

### FR-M5-001 账号成本管理（5.23）

#### 4.1.1 描述

管理账号的购买成本和过程成本。列表以**账号维度**聚合展示采购成本、过程成本与总成本（`AccountCostManage.vue`）。

#### 4.1.1.1 页面结构（实现 2026-06-11）

| 区块 | 说明 |
|------|------|
| 平台 Tab | 全部 / 公众号 / 视频号 / 抖音 / 快手 / 小红书 / 企微 / 个微 |
| 列表 | 账号名称、平台、采购成本、过程成本、总成本、实名人、运营人 |
| 查看 | 抽屉：账号摘要 + 成本明细表；平台/成本类型/周期用 `<DictLabel />` 展示字典 label |
| 成本管理 | 弹窗：采购成本表单（一次性）+ 过程成本表格 CRUD |
| 数据聚合 | 前端 `getAccountList` + `getCostList` 按 `accountId` 汇总 |

#### 4.1.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `account_id` | `<AccountSelect />` | `oa_account`（**强关联** ⭐） |
| `cost_type` | `<DictSelect dict-type="dict_cost_type" />` | 字典 |
| `amount` | `<InputNumber :precision="2" />` | - |
| `pay_method` | `<DictSelect dict-type="dict_cost_pay_method" />` | 字典 |
| `pay_date` | `<DatePicker />` | - |
| `period` | `<DictSelect dict-type="dict_cost_period" />` | 字典 |
| `remark` | `<TextArea />` | - |
| `attachment` | `<FileUploader />` | -（凭证） |

#### 4.1.3 业务规则

- 购买成本 = 一次性，过程成本 = 月/季/年
- 凭证上传到本地（无 MinIO）
- 月度归集：每月 1 号定时任务将过程成本分摊到账号

#### 4.1.4 验收标准

**AC-M5-001-1**（账号选择器）
- Given 录入成本
- When 选账号
- Then 弹出 `<AccountSelect />`

**AC-M5-001-2**（成本类型字典）

**AC-M5-001-3**（金额校验）
- Given `amount=0`
- When 提交
- Then 校验失败

**AC-M5-001-4**（平台 Tab 筛选）
- Given 账号成本页
- When 切换平台 Tab 为「抖音」
- Then 列表仅展示 `platformType=DOUYIN` 的账号及对应成本汇总

**AC-M5-001-5**（成本管理弹窗）
- Given 某账号行
- When 点击「成本管理」
- Then 弹窗可保存采购成本、增删改过程成本记录

---

### FR-M5-002 ROI 分析（5.24）

#### 4.2.1 描述

按 IP 组/账号/人员维度分析 ROI。

#### 4.2.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `ip_group_id` | `<IpGroupTreeSelect />` | `oa_ip_group` |
| `account_id` | `<AccountSelect />` | `oa_account` |
| `start_date` / `end_date` | `<DateRangePicker />` | - |
| `dimension` | `<Select />` | 固定值（ip_group/account/person） |

#### 4.2.3 业务规则

- **ROI 公式**：`SUM(pay_amount) / (SUM(购买成本) + SUM(过程成本))`
- **更新频率**：定时任务每 5min 刷新
- **趋势分析**：日/周/月/季

#### 4.2.3 变更 2026-06-15（实现补丁）

- **趋势成本**：`FinanceRoiServiceImpl.trend` 合并订单归因成本与 `oa_account_cost` 台账按日汇总
- **空结果防护**：IP 组/账号维度明细在 ID 集合为空时返回 `[]`，避免 MyBatis `IN ()` SQL 异常

#### 4.2.4 验收标准

**AC-M5-002-1**（ROI 计算）
**AC-M5-002-2**（多维度聚合）
**AC-M5-002-3**（趋势对比）

---

## 4.3 页面清单与页级 AC（UX v1.3 · 2026-10-02）

| 页面 ID | 名称 | Football 路由 | FR |
|---------|------|---------------|-----|
| P-M5-001 | 账号成本管理 | `/ops/finance/account-cost` | FR-M5-001 |
| P-M5-003 | ROI 分析 | `/ops/finance/roi-analysis` | FR-M5-002 |
| P-M5-004 | ROI 趋势 | 同页 Tab/图表 | FR-M5-002 |

**HTTP 前缀 SSOT**：`/admin-api/ops/finance/**`（[`API-M5-财务管理.md`](../engineering/API-M5-财务管理.md) §0）。

**AC-M5-P001**（P-M5-001 成本 CRUD）
- Given `oa:cost:list` 写权限
- When 在列表 [新增成本] 弹窗录入购买/过程成本并保存
- Then `accountId` 须 `<AccountSelect />` 校验；列表分页与 UX §2 列一致

**AC-M5-P003**（P-M5-003/004 ROI）
- When 选 IP 组/账号/人员维度 + 日期查询 ROI 并切换趋势 Tab
- Then `GET .../roi/summary` · `.../trend` · `.../cost-breakdown` 非空或规范空态；公式同 **AC-M5-002-1**（UX §3）

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.1：§4.3 页表 + P-M5 关键 AC |

---

## 5. 集成与数据

### 5.1 核心实体

| 实体 | 用途 | 关联 |
|------|------|------|
| `oa_author_cost` | 购买成本 | `oa_account` |
| `oa_cost_process_record` | 过程成本 | `oa_account`、`oa_ip_group` |
| `oa_order_attribution` | 订单归因 | `oa_account` |

### 5.2 关联属性（🔴）

| 字段 | 选择器 |
|------|--------|
| `accountId` | `<AccountSelect />` |
| `ipGroupId` | `<IpGroupTreeSelect />` |
| `costType` | `<DictSelect dict-type="dict_cost_type" />` |
| `payMethod` | `<DictSelect dict-type="dict_cost_pay_method" />` |
| `period` | `<DictSelect dict-type="dict_cost_period" />` |

---

## 6. 决策记录

| 编号 | 问题 | 决策 | 原因 |
|------|------|------|------|
| ADR-M5-001 | 凭证存储 | 本地文件系统 | 简化（无 MinIO） |
| ADR-M5-002 | ROI 更新频率 | 5min 定时 | 实时性 vs 性能 |

---

*下一步：UX Spec / API Spec / STATE / SLICES / CHECKLIST / TESTCASES。*
