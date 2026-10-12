# UX-M9-系统管理

> **版本**：v1.1 | 2026-06-11
> **关联 PRD**：[`PRD-M9-系统管理.md`](./PRD-M9-系统管理.md)
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

| 页面 | 路由 | FR |
|------|------|-----|
| 用户管理（部门树） | `/system/user` | FR-M9-001 + ADR-013 |
| 角色权限 | `/system/role` | FR-M9-002 |
| 租户管理 | `/system/tenant` | FR-M9-003 |
| 系统参数 | `/system/config` | FR-M9-004 |
| **字典管理** | `/system/dict` | FR-M9-005 |
| 操作日志 | `/system/log/operation` | FR-M9-006 |
| 登录日志 | `/system/log/login` | FR-M9-006 |
| 消息通知 | `/system/message` | FR-M9-007 |

---

## 2. P-M9-001 用户管理（实现 2026-06-11）

```
+------------------+----------------------------------------+
| 部门树 (240px)   | 用户列表 + 筛选 + 表格                  |
| 搜索部门         | 用户名/姓名模糊、角色、状态              |
| 同步钉钉部门     | [新增用户]                              |
| 同步钉钉人员     |                                        |
| 部门 CRUD        |                                        |
+------------------+----------------------------------------+
```

| 控件 | 类型 | 说明 |
|------|------|------|
| TREE-DEPT | `el-tree` | 点击筛选 `deptId`；模糊 `filter-node-method` |
| BTN-SYNC-DEPT | 按钮 | `POST /dept/sync-dingtalk` |
| BTN-SYNC-USER | 按钮 | `POST /dept/sync-dingtalk-users` |
| F-DEPT | 表单 | 用户 create/update 可选 `deptId` |
| COL-DEPT | 列 | `deptName` |

**Phase 2 Out of Scope**：钉钉 OAuth 登录（ADR-003 / ADR-013）

---

## 3. 字典管理（⭐）

### 3.1 列表

| 控件 | 字典 |
|------|------|
| F-DICT-TYPE | `<Input />` |
| F-DICT-NAME | `<Input />` |
| F-STATUS | `<DictSelect dict-type="dict_yes_no" />` |

### 3.2 字典项编辑

- `dictType` 全局唯一
- `dictValue` 全大写+下划线
- 新增后自动通知全局规范文档（人工 + 流程提醒）

---

## 10. OPS 壳内 OA 页面（menu 6105 · Football `#/ops/system-oa/*`）

> 与 Football 原生 `/system/*` 不同；下列页面在 OPS 业务区内挂载，路由见 [`OPS-MENU-ROUTE-INDEX`](../delivery/OPS-MENU-ROUTE-INDEX.md)。

### 10.1 P-M9-OPS-001 消息管理（6140 · `/ops/system-oa/system-message`）

**组件**：`ops/system/MessageManage.vue` · **权限**：`oa:message:list`

| 区域 | 内容 |
|------|------|
| A-Tab | 全部 / 预警(ALERT) / 系统(SYSTEM) / 业务(BUSINESS) |
| B | 标题 · 接收人 · 状态（PENDING/SENT/FAILED） |
| A-按钮 | [发送消息] |
| C | 列：标题、类型、渠道、接收人、状态 Tag、发送时间 · 操作：查看、删除 |
| 发送弹窗 | 标题、类型、渠道、接收人（UserSelect 或多选）、正文 TextArea · confirm 后 POST send |
| 详情 dialog | `el-descriptions` 只读 |

**确认**：删除 → `MessageBox.confirm` · 发送失败行展示 FAILED Tag + 可重试（若实现）

### 10.2 P-M9-OPS-002 系统参数（6141 · `/ops/system-oa/system-param`）

**组件**：`ops/system/ParamManage.vue` · **权限**：`oa:param:list`

| Tab | 过滤 `paramCategory` / 业务域 |
|-----|--------------------------------|
| 基础 / 采集 / AI / 钉钉 / 通知 / 内容审核 | 各 Tab 独立分页列表 |

| B | 参数名称 · 参数键 |
| C | 列：名称、键、值（脱敏/截断）、类型 Tag、说明、更新时间 · 编辑/删除 |
| 编辑 dialog 700px | `paramName` · `paramKey`（编辑禁用）· `paramValue`（按 `paramType` 切换 Input/Select/Switch；审核角色键用角色下拉）· `remark` |

**API**：`GET /admin-api/ops/system-param/page` · CRUD 同 Controller（前缀以 API-M9 为准）

**边缘**：内容审核 Tab 内 `review.role.*` 键使用角色 Select；敏感值展示 `****`

---

*下一步：API / STATE / SLICES / CHECKLIST / TESTCASES。*
