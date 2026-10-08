# UX-M10-数据采集

> **版本**：v1.3 | 2026-10-02
> **关联 PRD**：[`PRD-M10-数据采集.md`](./PRD-M10-数据采集.md)
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

| 页面 | Football 路由 | standalone | FR | permission |
|------|---------------|------------|-----|------------|
| 采集任务 | `/ops/collect/task` | `/collect/task` | FR-M10-001 | `oa:collect:task:list` |
| 任务编辑 | `/ops/collect/task/:id`（`id=0` 新增） | 同左 | FR-M10-001 | `oa:collect:task:list` |
| 采集日志 | `/ops/collect/log` | `/collect/log` | FR-M10-001 | `oa:collect:log:list` |
| 私域桥接 | `/ops/collect/private-domain-bridge` | `/collect/private-domain-bridge` | FR-M10-003 | `oa:collect:bridge:list` |
| 数据质量 | `/ops/collect/quality` | `/collect/quality` | FR-M10-002 | `oa:collect:quality:list` |

> **API 前缀 SSOT**：`/admin-api/ops/collect/**`（与 `#/api/ops/collect` 一致；勿再写 `/oa/collect`）。

---

## 2. P-M10-001 采集任务列表

| 项 | 规格 |
|----|------|
| Vue | `ops/collect/task.vue` |
| 布局 | **B** TableSearch + **A** ContentWrap extra + **C** 表格 + Pagination |

### 2.1 筛选（B）

| 控件 | dict-type / 字段 |
|------|------------------|
| 任务名 | `name` Input |
| 平台 | `dict_platform_type` |
| 采集方式 | `dict_collect_method` |
| 频率 | `dict_collect_frequency` |
| 状态 | `dict_collect_status` |

### 2.2 A 区按钮

| 按钮 | 行为 |
|------|------|
| 确保统一任务 | `POST /ops/collect/task/ensure-unified`（ADR-061） |
| 确保外部统一任务 | `POST /ops/collect/task/ensure-external-unified`（ADR-068） |
| 新增单账号任务 | 路由 `CollectTaskEdit` · `id=0` |

页顶 info Alert：Channel-A 23:00 统一任务 · Channel-D 22:00 外部统一任务说明。

### 2.3 表格列（C）

| 列 | 说明 |
|----|------|
| 任务名 | `name`/`taskName` + tag「统一任务」/「外部统一」 |
| 平台/账号 | 统一任务显示成员数；单账号 `DictLabel` 平台 + 账号名 |
| 方式 / 频率 / Cron | |
| 最近执行 | `lastRunAt` |
| 成功/失败 | `runCount` / `failCount` |
| 状态 | `dict_collect_status` tag |

### 2.4 行操作 + 显隐

| 操作 | 条件 |
|------|------|
| 启动 | `PENDING`/`STOPPED`/`FAILED` |
| 停止 | `RUNNING` |
| 立即执行 | 任意（loading 互斥） |
| 日志 | 跳转 `/ops/collect/log?taskId=` |
| 编辑 / 删除 | **非** `isUnified` 且 **非** `isExternalUnified` |
| 成员 / 外部成员 | 统一 / 外部统一任务 · Alert 列表 |

**确认流**：删除 `MessageBox.confirm` · 启停/执行失败 Toast。

**API**：`GET /ops/collect/task/page` · `POST .../{id}/run|start|stop` · `DELETE .../delete`

---

## 3. P-M10-002 采集任务编辑（独立页 · 非抽屉）

| 项 | 规格 |
|----|------|
| Vue | `ops/collect/task-edit.vue` |
| 路由 | `CollectTaskEdit` · `/ops/collect/task/:id` |
| 入口 | 列表「编辑」/「新增单账号任务」 |

### 3.1 基本信息（表单字段）

| 控件 | 类型 | 必填 | 说明 |
|------|------|------|------|
| F-NAME | Input max 100 | ✅ | 任务名 |
| F-PLATFORM | `dict_platform_type` | ✅ | 变更时写入默认 source/method |
| F-ACCOUNT | `<AccountSelect />` | ✅ | 非企微 |
| F-ACCOUNT-WEWORK | `<WeworkAccountSelect />` | ✅ | `platformType=WEWORK` |
| F-COLLECT-SCOPE | 只读 tag 列表 | — | 按平台 `PLATFORM_DEFAULTS` 展示 dataTypes 中文 |
| F-FREQUENCY | `dict_collect_frequency` | ✅ | |
| F-CRON | Input + Cron 语法 dialog | ✅ | 正则校验 |
| F-API-CONFIG | Textarea JSON | — | 保存 AES-256 提示 |
| F-STATUS | `dict_collect_status` | ✅ | |

隐藏字段（后端默认）：`method=INTERNAL` · `source` 按平台 · `dataType` null=全量。

### 3.2 监控信息（仅编辑 id>0）

只读 `el-descriptions`：最近/下次执行 · 累计成功/失败 · 创建/修改时间。

### 3.3 提交

[保存] → `POST /ops/collect/task/create` 或 `PUT .../update` · [返回] `router.back()`

**空/加载/错**：`v-loading` · 校验失败表单提示 · 1500–1504 Toast

---

## 4. P-M10-003 采集日志

| 项 | 规格 |
|----|------|
| Vue | `ops/collect/log.vue` |
| 布局 | **B** TableSearch + **C** 表格 + **二级** 80% drawer |

### 4.1 筛选

| 控件 | 说明 |
|------|------|
| 任务 | filterable Select（`GET task/page` 预载 200 条） |
| 状态 | `dict_collect_status`（含 SUCCESS/FAILED/PARTIAL） |
| 执行时间 | daterange → `startDate`/`endDate` |

### 4.2 表格列

| 列 | 说明 |
|----|------|
| 任务名 | |
| 状态 | tag 成功/失败/部分成功 |
| 开始时间 / 耗时 / 采集记录 / 重试 | |
| 错误信息 | link「查看」→ 500px 错误 drawer |
| 操作 | 查看详情 · 查看任务（跳 task-edit） |

行点击 = 打开详情 drawer。

### 4.3 详情 drawer（`log-detail.vue`）

| 区域 | 内容 |
|------|------|
| 头 | 任务名 + 状态 · 平台/账号 · 时间区间/耗时/条数/重试 |
| 执行信息 | descriptions |
| 采集结果 | 单类型 summary；多类型 `el-collapse` **`typeResults[]`**（recordCount/错误/样本） |

**API**：`GET /ops/collect/log/page` · `GET /ops/collect/log/{id}` → `result.typeResults[]`（ADR-049）

**空/加载/错**：`el-empty`「暂无日志」· `v-loading`

---

## 5. P-M10-004 数据质量检查

| 项 | 规格 |
|----|------|
| Vue | `ops/collect/quality.vue` |
| 布局 | 左右 **14/10** 双栏：规则表 + 质量日志 |

### 5.1 质量检查规则（左）

**筛选**：规则名 · `dict_quality_check_type` · `dict_quality_level`

**表格列**：规则名 · 类型 tag · 级别 tag · 表名 · 通过率（`<90%` 红）· 最近检查 · 启用 switch · 操作

| A 区 | [新增规则] |
|------|------------|
| 行操作 | 编辑 · 删除（confirm） |

**现网边缘**：新增/编辑 **未实现完整弹窗** — 点击仅 `ElMessage.info` 占位；API 失败时 fallback `#/mock/ops/collect`（**Spec 仍描述目标弹窗字段如下**）。

**目标规则编辑 dialog 字段（待实现）**

| 字段 | 控件 |
|------|------|
| name | Input |
| checkType | `dict_quality_check_type` |
| level | `dict_quality_level` |
| tableName | Input |
| ruleExpression | Textarea SQL/表达式 |
| enabled | Switch |

**API**：`GET /ops/collect/quality/check/page` · CRUD 以 API-M10 为准

### 5.2 质量日志（右）

筛选：级别 · 日期范围

列：规则名 · 级别 · 检查时间 · 通过/失败/总数

**API**：`GET /ops/collect/quality/log/page`

---

## 6. 跨页通用

- **强关联**：Channel-A `accountId` 强制选择器；Channel-D `collectConfigId` 强制外部配置选择器
- **字典**：`dict_collect_*` + `dict_quality_*` + `dict_collect_method.EXTERNAL` 全部用 `<DictSelect />`
- **凭证**：`apiConfig` 输入框 + 加密存储；Channel-D 凭账号在 M8 租户级维护
- **空/错/加载**：三态完整

---

## 7. Channel-D 任务编辑增量（ADR-052 · P0+）

当 `method=EXTERNAL` 时，编辑页与 Channel-A 区分：

| 控件 | 类型 | 说明 |
|------|------|------|
| F-COLLECT-CONFIG | 外部竞品配置选择器 | 必填；`scope=EXTERNAL` |
| F-CREDENTIAL-PROFILE | `<Input />` 可空 | 默认 `default` |
| F-DATA-TYPE | `<DictSelect dict-type="dict_collect_data_type" />` | 如 `EXT_KUAISHOU_USER_VIDEOS` |
| ~~F-ACCOUNT~~ | 隐藏 | `account_id` 必须 null |

> 现网 `task-edit.vue` 以 Channel-A 单账号表单为主；EXTERNAL 字段在统一外部任务 + M8 配置链路体现，单账号 EXTERNAL 编辑对齐本表为 **增量 Spec**。

---

## 8. P-M10-005 私域桥接（`/ops/collect/private-domain-bridge`）

**组件**：`ops/collect/private-domain-bridge.vue` · **权限**：`oa:collect:bridge:list`

| 区域 | 控件 |
|------|------|
| B | `F-REVIEW-STATUS` `<DictSelect dict-type="dict_private_domain_review_status" />`（默认 `PENDING`）· `F-SOURCE-TYPE` `dict_private_domain_identity_type` · `F-MATCH-METHOD` `dict_private_domain_match_method` |
| C | 表格：来源类型+标签、目标类型+标签、匹配方式、置信度、审核状态、创建时间 |
| 行操作 | `PENDING`：[确认][驳回]；否则 `—` |

**API**：分页 `GET /admin-api/ops/collect/private-domain-bridge/page` · 确认/驳回 `POST .../confirm` · `.../reject`（以 API-M10 为准）

**交互**：确认/驳回前 `MessageBox.confirm` · 成功后刷新列表并保持筛选

**空/加载/错**：`v-loading` · 无待审 `el-empty`「暂无待审核桥接记录」

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.3：§2–5 任务/日志/质量 Football 对齐 · `/ops/collect` API · 任务编辑独立页 · 质量规则弹窗占位标注 |
| 2026-06-24 | v1.2 | Channel-D 增量 §7 |
| 2026-10-02 | v1.2 | §0 OPS SSOT |

---

*下一步：API / STATE / SLICES / CHECKLIST / TESTCASES。*
