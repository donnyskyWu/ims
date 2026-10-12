# CHECKLIST-IMS-AUTH — 权限与工作台

> **关联**：[SLICES-IMS-AUTH](./SLICES-IMS-AUTH.md) · 页面/API 规格 `产品规格/V1/AUTH-*`

---

## 1. 范围

- [ ] S-IMS-A-01～04 全部完成
- [ ] AUTH-001～004 页面路由与 PRD §01 导航一致（走查 #15）
- [ ] **未**实现租户套餐 / 独立数据权限 L3（保持 BLOCKED）

## 2. AUTH-001 SSO

- [ ] `GET /auth/sso/redirect` 返回钉钉授权 URL
- [ ] `POST /auth/sso/callback` 绑定 mobile 后 `LoginUser.userId` = `system_users.id`（见《IMS-用户FK与ADR-056摘要》）
- [ ] Token refresh / logout 生效
- [ ] 未登录访问业务路由 → `/login`

## 3. AUTH-002 组织

- [x] 人员列表含同步状态列
- [x] `POST /auth/org/reconcile` 仅 R1
- [x] 事件查询分页、同步延迟指标可展示

## 4. AUTH-003 岗位

- [ ] 模板列表/抽屉 CRUD（列表、新建、新版本、逻辑删除已做；编辑不是抽屉）
- [x] 编辑产生新版本；删除为逻辑删除
- [x] `POST /system/role/{id}/preview` Diff 可演示（**已迁角色侧 SYS-002**；见架构 §4 列 4d `4d POST /system/role/{id}/preview`；AUTH-003 不再承载权限预览）

## 5. AUTH-004 工作台

- [x] `GET /auth/workbench/dashboard` 首屏字段与 HOME 规格一致（允许部分 VO 薄）
- [x] 待办/消息分页、关闭/已读（接口已测；页面预览最多 10 条。待办关闭按钮和消息已读按钮在没有消息时页面上点不到）
- [ ] P4a/P4b 二级列表可深链

## 6. 全局

- [ ] 敏感字段脱敏（手机）
- [ ] chi 中间件权限码校验（`RequirePerm`）与菜单 seed 一致（**Go/chi 口径**，非 Java `@PreAuthorize`）
- [ ] TESTCASES-IMS-AUTH **P0 100%**
