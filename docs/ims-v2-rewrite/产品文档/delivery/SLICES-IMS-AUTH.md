# SLICES-IMS-AUTH — 权限与工作台

> **版本**：v1.0 | 2026-10-01  
> **规格 SSOT**：《AUTH-权限管理-页面规格.md》《AUTH-权限管理-API契约.md》《HOME-首页-页面规格.md》  
> **BLOCKED**：租户套餐 L3、独立数据权限 L3（#15）

---

## 1. 切片总览

| Slice | 目标 | FR | 依赖 | 备注 |
|-------|------|-----|------|------|
| S-IMS-A-01 | SSO 登录会话 | AUTH-001 | 钉钉应用配置 | `/auth/sso/*` |
| S-IMS-A-02 | 组织架构同步 | AUTH-002 | S-IMS-A-01 | 事件 + reconcile |
| S-IMS-A-03 | 岗位-角色供给规则 | AUTH-003 | S-IMS-S-04 字典 `dict_position` + **SYS-002 角色**（ADR-IMS-008） | 权限明细在角色；本片只管供给规则 + 自动建角色 |
| S-IMS-A-04 | 个人工作台 | AUTH-004 | 各域待办源 seed | dashboard/todos/messages |

---

## 2. S-IMS-A-01 SSO

**前端**：P1 `/login`  
**后端**：契约 #1～4、D1  
**验收**：未登录重定向；callback 换 JWT；refresh/logout

---

## 3. S-IMS-A-02 组织同步

**前端**：P2 `/ims/auth/org`  
**后端**：#5～9  
**验收**：事件列表、手动 reconcile、同步指标 BR-001

---

## 4. S-IMS-A-03 岗位-角色供给规则（ADR-IMS-008）

**前端**：P3 `/ims/auth/position`  
**后端**：#10～14（`/auth/position/rule*` + `role-auto-create`）  
**验收**：供给规则 CRUD、版本、授予角色、自动建角色（PENDING_CONFIG 空权限 + 待办 + 幂等）

---

## 5. S-IMS-A-04 工作台

**前端**：P4/P4a/P4b  
**后端**：#15～20  
**验收**：dashboard 聚合；待办/消息分页与已读
