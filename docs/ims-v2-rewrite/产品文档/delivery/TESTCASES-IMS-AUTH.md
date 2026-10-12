# TESTCASES-IMS-AUTH — 权限与工作台（P0）

> **版本**：v1.0 | 2026-10-01 · 验收叙述，非伪代码

---

## AUTH-001 SSO

### TC-IMS-A-001-01 未登录拦截

- **Given** 无有效 JWT  
- **When** 访问 `/ims/system/user`  
- **Then** 重定向 `/login`

### TC-IMS-A-001-02 扫码登录成功

- **Given** 钉钉 callback 合法 authCode + state  
- **When** `POST /auth/sso/callback`  
- **Then** 返回 accessToken；会话 userId 为 `ims_sys_user.id`

### TC-IMS-A-001-03 注销

- **When** `POST /auth/sso/logout`  
- **Then** 旧 Token 不可用

---

## AUTH-002 组织

### TC-IMS-A-002-01 对账

- **Given** R1  
- **When** `POST /auth/org/reconcile`  
- **Then** 任务受理；事件列表可查到对账记录

### TC-IMS-A-002-02 非 R1 对账

- **Given** R4  
- **When** reconcile  
- **Then** 403

---

## AUTH-003 岗位-角色供给规则（ADR-IMS-008）

### TC-IMS-A-003-01 新建供给规则

- **When** R1 创建「岗位-角色供给规则」（选钉钉岗位 + 授予角色）  
- **Then** 列表可见、版本 +1；角色权限在 SYS-002 维护

### TC-IMS-A-003-02 岗位自动建角色（fail-closed）

- **When** 钉钉同步到无对应角色的岗位  
- **Then** 自动建 `DINGTALK_AUTO`/`PENDING_CONFIG` **空权限**角色 + 推 R1 待办；重复同步幂等；无角色不放行

---

## AUTH-004 工作台

### TC-IMS-A-004-01 本人待办

- **Given** seed 待办归属当前用户  
- **When** `GET /auth/workbench/todos`  
- **Then** 仅本人待办；关闭后状态更新

### TC-IMS-A-004-02 消息已读

- **When** `PUT …/messages/{id}/read`  
- **Then** 未读数减少


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-HOME-01 运营看板总览

### TC-IMS-HOME-01-01 P0 主路径

- **Given** 已登录且套餐含首页；HOME-001 seed。
- **When** 用户按故事主路径操作（页面 `home`）
- **Then** 卡片数值与 seed 一致；跳转 `go()` 到达目标页且侧栏高亮正确。

## US-HOME-02 个人工作台待办与消息

### TC-IMS-HOME-02-01 P0 主路径

- **Given** 钉钉 SSO 已绑手机（BR-308）；AUTH-004。
- **When** 用户按故事主路径操作（页面 `workbench`）
- **Then** 待办在业务页处理后回到工作台预览减少；消息已读态同步。

## US-AUTH-01 钉钉组织同步与对账

### TC-IMS-AUTH-01-01-01 P0 主路径

- **Given** AUTH 规格。
- **When** 用户按故事主路径操作（页面 `authOrg`）
- **Then** 组织树/岗位列表更新；非 R1 对账 403。

## US-AUTH-02 岗位-角色供给规则与权限预览

### TC-IMS-AUTH-02-01-01 P0 主路径

- **Given** AUTH 规格；SYS-002 角色（权限明细载体）
- **When** 用户按故事主路径操作（页面 `authPosition`）
- **Then** 岗位角色映射更新、版本 +1；`PENDING_CONFIG` 护栏生效；非 R1 操作 403。权限 Diff **只**走 `POST /admin-api/ims/system/role/{id}/preview`；`POST /auth/position/preview` 不存在（D-7）。权限 Diff **只**走 `POST /admin-api/ims/system/role/{id}/preview`；`POST /auth/position/preview` 不存在（D-7）。

