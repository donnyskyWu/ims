# CHECKLIST-IMS-SYS — 系统管理

> **关联**：[SLICES-IMS-SYS](./SLICES-IMS-SYS.md)

---

## 1. 范围

- [ ] S-IMS-S-01～04 完成（**S-IMS-S-05 日志/通知 = 批次外，本轮无 Gate 归属**）
- [ ] 侧栏 7 L3 与走查 #15 一致
- [ ] SYS-008 租户套餐 L3 —— **批次外**（不在本轮 Gate；待 menuId 对账后另开，ADR-IMS-007 §5）

## 2. SYS-001 用户

- [ ] 部门树 + 用户分页
- [ ] 抽屉仅改 IMS 角色等允许字段；**不可改** user id
- [ ] 1211 改主键被拒绝
- [ ] 列表 id 列 = Football `system_users.id`

## 3. SYS-002/003 角色权限 + 菜单（ADR-IMS-008）

- [ ] 角色列表 + 菜单树勾选保存（权限码，兼容 `ops:*`）
- [ ] **角色吸收功能点 R/W/D 明细**（按模块分组勾选）
- [ ] **数据范围** dataScope（ALL / DEPT / IP_GROUP / SELF；「本部门」不含下级）
- [ ] **钉钉岗位绑定**（唯一；一岗位至多一角色）
- [ ] 角色来源角标（`MANUAL` / `DINGTALK_AUTO`）+ `PENDING_CONFIG` 警示
- [ ] [权限预览] 模拟用户 Diff；[一键从岗位生成角色]（空权限 + 待办）
- [ ] 菜单抽屉：路由、权限码、类型、可见

## 4. SYS-004 字典

- [ ] 左类型右数据联动
- [ ] `dictType` / `dictValue` 命名规则
- [ ] 停用值不可删
- [ ] 含 `dict_platform_type`、`dict_sop_node_type` 等并入字典

## 5. SYS-005 参数

- [ ] 必含 key 可读写
- [ ] 1213 未知 key 拒绝

## 6. SYS-006/007（**批次外 · 本轮无 Gate 归属**）

- [x] 操作/登录日志分页
- [x] 通知列表可读

## 7. 全局

- [ ] tenant 隔离（1504）在列表接口生效
- [ ] TESTCASES-IMS-SYS P0 100%
