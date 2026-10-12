# PRD-M9-系统管理

> **业务域**：M9 系统管理
> **功能模块**：用户 + 角色 + 租户 + 字典 + 日志 + 消息
> **详细设计章节**：5.35
> **版本**：v1.5 | 2026-10-03
> **关联 UX**：[`UX-M9-系统管理.md`](./UX-M9-系统管理.md)（v1.1 · OPS §10）
> **全局规范**：[`docs/engineering/GLOBAL-CONVENTIONS.md`](./../engineering/GLOBAL-CONVENTIONS.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| 模块 | M9 系统管理 |
| 业务域 | 系统（SYSTEM） |
| 详细设计 | `## 5.35` |

---

## 1. 概述

系统级管理：用户/角色/权限/租户/字典/日志/消息。**字典管理是核心**（关联所有模块）。

### 实现补充（2026-06-11，ADR-013）

**FR-M9-001 扩展**：用户管理页左侧部门树 + 钉钉组织同步。

| 能力 | 说明 |
|------|------|
| 部门树 | `sys_dept` 表；左侧 `el-tree` 筛选 `GET /user/list?deptId=` |
| 部门 CRUD | 本地创建/编辑/删除（有子部门或用户 → 1502） |
| 钉钉同步 | 手动触发 `sync-dingtalk`（部门）、`sync-dingtalk-users`（人员） |
| 用户扩展 | `sys_user.dept_id`、`ding_user_id`；`ding_user_id` 供后续消息/SSO（Phase 2） |

**Out of Scope**：钉钉 OAuth 登录、同步删除本地用户、定时自动同步（见 ADR-013）。

### 实现补充（2026-06-13）

**FR-M9-001 多角色**：用户创建/编辑支持 `roleIds` **多选**；权限取角色并集（`UserManage.vue`）。

**FR-M9-004 内容审核参数**：系统参数页 Tab「内容审核」筛选四条 `content.review.*` 键；`level1.role` / `level2.role` 使用 **角色下拉**（非手输）。详见 ADR-017。

### 实现补充（2026-06-15 · ADR-026）

**FR-M9-007 业务通知扩展**：

| 能力 | 说明 |
|------|------|
| 事件类型 | `TASK_PENDING`、`CONTENT_REVIEW_SUBMIT`、`CONTENT_REVIEW_APPROVED`、`WORK_HIT`、`WORK_LOW_SCORE`、`ACCOUNT_HIGH_FANS`、`ACCOUNT_LOW_FANS` |
| 去重 | 表 `sys_notification_event`；`(tenant_id, event_type, biz_key)` 唯一 |
| 站内信 | `sys_message`，channel 含 `IN_APP,DINGTALK` |
| 钉钉主通道 | 工作通知 `asyncsend_v2`（`oa.dingtalk.agent-id`）；需 `sys_user.ding_user_id` |
| 钉钉降级 | 群机器人 Webhook（`oa.dingtalk.robot.*`，可选） |
| 定时扫描 | `MonitorAlertScanner`，默认每 30 分钟 |

**Out of Scope**：用户自定义通知模板、按用户关闭某类通知（v1.0 未实现）。

---

## 2. 范围

| FR 编号 | 名称 | 优先级 |
|---------|------|--------|
| FR-M9-001 | 用户管理 | P0 |
| FR-M9-002 | 角色权限管理 | P0 |
| FR-M9-003 | 租户管理（v7.0 新增） | P0 |
| FR-M9-004 | 系统参数配置 | P0 |
| FR-M9-005 | **字典管理**（核心） | P0 |
| FR-M9-006 | 日志管理（操作日志 + 登录日志） | P0 |
| FR-M9-007 | 消息通知 | P1 |

---

## 3. 关键 FR 详述

### FR-M9-005 字典管理（⭐ 核心）

#### 数据项

| 字段 | 控件 | 字典 |
|------|------|------|
| `dictType` | `<Input />`（唯一） | - |
| `dictName` | `<Input />` | - |
| `dictLabel` | `<Input />` | - |
| `dictValue` | `<Input />` | - |
| `sort` | `<InputNumber />` | - |
| `status` | `<DictSelect dict-type="dict_yes_no" />` | 字典 |
| `colorType` | `<Select />` | 固定值（default/primary/success/warning/danger） |
| `remark` | `<TextArea />` | - |

#### 业务规则

- `dictType` 命名规范：`dict_value_placeholder`（小写+下划线）
- `dictValue` 命名规范：全大写+下划线
- 停用值不可删除（保留历史）
- 新增/修改字典 value 必须同步更新 [`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md) § 2

#### 验收标准

**AC-M9-005-1**（字典 type 唯一）
**AC-M9-005-2**（value 命名）
**AC-M9-005-3**（停用不可删）

---

### FR-M9-006 日志管理

#### 业务

- 操作日志：所有 CRUD + 审核 + 强制替换 → 审计追踪
- 登录日志：登录/登出 + IP + 设备

#### 验收标准

**AC-M9-006-1**（操作日志记录）
**AC-M9-006-2**（登录日志）
**AC-M9-006-3**（日志保留 90 天）

---

## 4. OPS 壳内页面（Football `#/ops/system-oa/*` · UX §10）

> Football 原生 `/system/*` 用户/角色/字典等仍属 FR-M9-001~006；下列为 **OPS 业务区** 挂载页，路由见 [`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)。

| 页面 ID | 名称 | Football 路由 | FR | permission |
|---------|------|---------------|-----|------------|
| P-M9-OPS-001 | 消息管理 | `/ops/system-oa/system-message` | FR-M9-007 | `oa:message:list` |
| P-M9-OPS-002 | 系统参数 | `/ops/system-oa/system-param` | FR-M9-004 | `oa:param:list` |

**HTTP 前缀 SSOT**：`/admin-api/ops/system-message/**` · `/admin-api/ops/system-param/**`（[`API-M9-系统管理.md`](../engineering/API-M9-系统管理.md) §0）。

**AC-M9-OPS-P001**（P-M9-OPS-001 消息管理）
- Given `oa:message:list`
- When 切换 Tab（全部/预警/系统/业务）并 [发送消息]
- Then 列表分页；发送弹窗须选接收人（UserSelect）+ 渠道；删除前 `MessageBox.confirm`；FAILED 状态 Tag 可见（UX §10.1）

**AC-M9-OPS-P002**（P-M9-OPS-002 系统参数）
- When 切换 Tab（基础/采集/AI/钉钉/通知/内容审核）并编辑参数
- Then `paramKey` 编辑态禁用；内容审核 Tab 内 `review.role.*` 用角色下拉；敏感值展示 `****`（UX §10.2 · 与 M2 二级审核参数联动 ADR-017）

**AC-M9-OPS-P002-D**（D-M9-001 参数编辑 dialog · 二级面）
- When 在参数列表点击 [编辑]
- Then 弹窗加载 `GET /admin-api/ops/system-param/get?id=`；保存 `PUT .../update`；取消不脏写列表（UX §10.2 · [`OPS-UX-PAGE-COVERAGE`](../../delivery/OPS-UX-PAGE-COVERAGE-20261002.md) §4）

### 4.1 Football `/system/*` 域（不在 OPS 77 面）

| 范围 | FR | PRD 锚点类型 | 说明 |
|------|-----|--------------|------|
| 用户/角色/菜单/租户/字典/日志等 | FR-M9-001~006 | **Football 原生 SSOT** | 路由 `#/system/*`；**不计入** OPS 77 面 UX 审计 |
| OPS 挂载消息/参数 | P-M9-OPS-001~002 | 可测 AC §4 | 上表 |

- **Gate 验收**：OPS Phase 1 P0 仅强制 **P-M9-OPS-001/002**；`/system/*` 能力沿用 Football 平台既有 FR/AC（本章 §3 FR-M9-001~006 摘要），字段级见 **UX-M9 §1–§9**（非 OPS 壳线框）。

---

## 5. 关联属性

| 字段 | 字典 |
|------|------|
| `userStatus` | `dict_user_status` |
| `tenantStatus` | `dict_tenant_status` |
| `logLevel` | `dict_log_level` |
| `logModule` | `dict_log_module` |
| `yesNo` | `dict_yes_no` |
| `gender` | `dict_gender` |

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-03 | v1.5：§4.1 Football `/system/*` 与 OPS 77 面边界 · D-M9-001 参数 dialog AC |
| 2026-10-02 | v1.4：§4 OPS 消息/参数页表 + 可测 AC（UX §10） |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES（Football `/system/*` 域另册）。*
