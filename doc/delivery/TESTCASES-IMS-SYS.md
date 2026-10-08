# TESTCASES-IMS-SYS — 系统管理（P0）

---

## SYS-001 用户

### TC-IMS-S-001-01 分页列表

- **When** R1 `GET /system/user/page`  
- **Then** 返回 list+total；id 为 snowflake 字符串

### TC-IMS-S-001-02 禁止改主键

- **When** PUT user 修改 id  
- **Then** 1211

---

## SYS-002 角色权限（权限唯一载体 · ADR-IMS-008）

### TC-IMS-S-002-01 保存菜单 + 权限明细

- **Given** 角色 R 与菜单 id 集合、功能点 R/W/D、dataScope、钉钉岗位  
- **When** `PUT /system/role/{id}/menus` + `perm-detail` + `data-scope` + `dingtalk-position`  
- **Then** 该角色登录后可见菜单与子集一致；用户权限按**角色并集**生效

### TC-IMS-S-002-02 从岗位自动建角色（fail-closed）

- **When** `POST /system/role/from-position`（钉钉岗位无对应角色）  
- **Then** 生成 `PENDING_CONFIG` 空权限角色 + R1 待办；重复调用幂等；无角色不放行

---

## SYS-004 字典

### TC-IMS-S-004-01 业务字典可读

- **When** `GET /system/dict-data/list?dictType=dict_platform_type`  
- **Then** 非空（seed）

---

## SYS-005 参数

### TC-IMS-S-005-01 work.task 开关

- **When** 读/写 `work.task.confirm.auto-ai-generate`  
- **Then** bool 持久化


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-SYS-01 维护系统用户

### TC-IMS-SYS-01-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysUser`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-02 配置角色权限（角色 = 权限唯一载体）

### TC-IMS-SYS-02-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysRole`）—— 菜单权限 + 功能点 R/W/D + 数据范围 + 钉钉岗位
- **Then** 角色权限变更生效；用户权限按角色并集判定；`PENDING_CONFIG` 未配权限 → 用户无权限（fail-closed）。

## US-SYS-03 维护 IMS 菜单树

### TC-IMS-SYS-03-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysMenu`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-04 维护业务字典

### TC-IMS-SYS-04-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysDict`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-05 维护系统参数

### TC-IMS-SYS-05-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysParam`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-06 审计操作日志

### TC-IMS-SYS-06-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysLog`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-07 配置通知渠道

### TC-IMS-SYS-07-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysNotify`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

## US-SYS-08 分配套户套餐

### TC-IMS-SYS-08-01-01 P0 主路径

- **Given** SYS 规格；tenant 对齐 ADR-IMS-007。
- **When** 用户按故事主路径操作（页面 `sysTenant`）
- **Then** 变更生效；租户套餐控制侧栏可见 L3。

