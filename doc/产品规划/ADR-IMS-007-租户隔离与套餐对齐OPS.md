# ADR-IMS-007 租户隔离与租户套餐对齐 OPS

> **状态**：已确认（2026-10-01 · 用户拍板）  
> **关联**：ADR-IMS-001（共享 OPS 业务库）、ADR-IMS-003、完整 PRD §01 SYS-008、`docs/delivery/OPS-FOOTBALL-DATA-OWNERSHIP-ANALYSIS.md`（`system_tenant` / `system_tenant_package` SSOT）

## 1. 决策

1. **IMS 全部业务表**（含新建 `ims_*` 与 IMS 写入的 OPS 扩展列）必须带 **`tenant_id`**，查询/写入从登录上下文取租户，**禁止**跨租户读写（与 OPS 1504 / BR-305 数据范围一致）。
2. **租户主数据与套餐**不另建 IMS 平行表：读写 **Football shenyu-system** 表 **`system_tenant`**、**`system_tenant_package`**（及关联 **`system_tenant_package_menu`** 等现网结构）。IMS 提供 **SYS-008 租户套餐** 管理页与 `/admin-api/ims/system/tenant/**` BFF，语义对齐 OPS **FR-M9-003**（租户管理 · P0）。
3. **套餐 → 菜单**：租户绑定套餐后，可见菜单由套餐内 menu 集合决定（与 OPS 一致）；IMS 新增业务菜单（含 **`ims:corp:*`** 公司资产 L3）须在 **套餐 seed / 菜单 seed** 中登记，**menuId 须与 `system_menu.id` 一致**（禁止前端写死臆造 ID）。

## 2. 数据范围

| 层级 | 规则 |
|------|------|
| 登录上下文 | `tenantId` 来自 Token / `LoginUser`（与 OPS 相同来源） |
| 列表/详情/导出 | SQL / ORM **强制** `WHERE tenant_id = :ctxTenantId`（只读聚合层同理） |
| 写操作 | 请求体 **不得** 覆盖 `tenant_id`；服务端注入 ctx |
| 平台管理员 | 若未来支持跨租户运维，须单独 ADR + 审计；**本期不做** 跨租户切换 UI |

共享库 **只读** OPS 表（ADR-001 允许处）仍须 **按 tenant_id 过滤**，不得因「同库」省略隔离。

## 3. 权限与菜单（SYS-008）

| IMS 权限码 | 映射 OPS / Football | 说明 |
|------------|---------------------|------|
| `ims:tenant:query` | `system:tenant:query` | 租户列表 |
| `ims:tenant:update` | `system:tenant:update` | 分配套餐、启停 |
| `ims:tenant-package:query` | `system:tenant-package:query` | 套餐只读（可选） |

**本期页面**：系统管理 → **租户套餐**（L3 · SYS-008）— 租户列表 + 当前套餐名称 + 状态 + 分配套餐抽屉；业务规则 **不超出** OPS FR-M9-003（租户 CRUD、套餐绑定、启用/停用）。

## 4. `ims:corp:*` 与套餐 seed（摘要）

公司资产域菜单权限建议使用前缀 **`ims:corp:*`**（见《CORP-公司资产-页面规格》）。**套餐 seed 时**须将下列 **逻辑菜单** 纳入可分配集合（具体 `system_menu.id` 以 SYS-003 seed 脚本为准，**实施前与 shenyu `system_menu` 对账**）：

| 逻辑能力 | 建议 perm 前缀 | 备注 |
|----------|----------------|------|
| 账号管理 L3（各平台叶） | `ims:corp:account:*` | 对应 OPS `ops:account:*` 能力迁移 |
| 资源管理 L3 | `ims:corp:resource:*` | 公司/实名人/SIM/证件 |
| 设备管理 L3 | `ims:corp:device:*` | 办公/直播/手机 |

**禁止**在 ADR 内粘贴整份 SQL；若仓库已有 SYS-003 seed 文件模式，切片时 **追加 corp 行** 并记录在 CHECKLIST-SYS §套餐。

## 5. 实现约束

- 切片 `@`《SYS-系统管理-页面规格》SYS-008 + 本文 + PRD §01。
- **阻塞**：若 dev 库 `system_menu` 与文档 perm 不一致，先修 seed 再开 CORP/业务模块 Gate（**menuId 对账**为上线前硬门槛）。

## 6. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-10-01 | 用户拍板：纳入租户套餐 L3；废止「不出租户套餐」 |
