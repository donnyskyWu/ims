# SLICES-IMS-SYS — 系统管理

> **版本**：v1.0 | 2026-10-01  
> **规格 SSOT**：《SYS-系统管理-页面规格.md》《SYS-系统管理-API契约.md》  
> **本轮批次外**：SYS-008 租户套餐（ADR-IMS-007 · FR-M9-003）——**不在本轮 Gate 内**；待 `system_menu` menuId 对账完成后另行开片（ADR-IMS-007 §5）。

---

## 1. 切片总览

| Slice | 目标 | FR | 依赖 |
|-------|------|-----|------|
| S-IMS-S-01 | 用户 | SYS-001 | S-IMS-A-01 · ADR-056 摘要 |
| S-IMS-S-02 | 角色与菜单 | SYS-002/003 | S-IMS-S-01 |
| S-IMS-S-03 | 字典 | SYS-004 | seed 业务字典 |
| S-IMS-S-04 | 参数 | SYS-005 | — |
| S-IMS-S-05 | 日志与通知（**批次外 · 本轮无 Gate 归属**） | SYS-006/007 | 后续切片 |

---

## 2. S-IMS-S-01 用户

**路由**：`/ims/system/user` · **API**：`/system/user/page`、POST/PUT user  
**验收**：列表 `system_users.id`；禁止改主键（1211）

---

## 3. S-IMS-S-02 角色权限（权限唯一载体 · ADR-IMS-008）

**路由**：role + menu · **API**：role/list、role menus、**role perm-detail / data-scope / dingtalk-position / preview / from-position**、menu/tree  
**验收**：权限码兼容 `ops:*`；**角色吸收功能点 R/W/D + dataScope + 钉钉岗位绑定**；菜单树与 IMS 导航 seed 一致；`PENDING_CONFIG` 角色 fail-closed

---

## 4. S-IMS-S-03 字典

**路由**：`/ims/system/dict` · **API**：dict-type、dict-data  
**验收**：含 OPS 并入字典类型（platform、content、sop 等）

---

## 5. S-IMS-S-04 参数

**必含 key**：`work.task.confirm.auto-ai-generate`、`content.review.*`、钉钉开关

---

## 6. S-IMS-S-05 日志通知

**API**：operate-log、login-log、notify/page
