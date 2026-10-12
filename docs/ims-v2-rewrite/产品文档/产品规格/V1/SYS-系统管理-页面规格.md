# SYS - 系统管理 页面规格（OPS M9 并入）

> 依据：完整 PRD SYS-001～007；OPS `PRD-M9-系统管理.md`。AUTH-001～003 仍见 `AUTH-权限管理-页面规格.md`。  
> 前缀：`/admin-api/ims/system`

### 0.1 侧栏信息架构（走查 #15）

默认进入 **系统管理 → 用户**（`sysUser`）。废止完整原型单页「系统管理」七 Tab 混排。

```
系统与权限（L1 侧栏组）
└── 系统管理（L2 nav-sub-g）
    ├── 用户        /ims/system/user     SYS-001
    ├── 角色        /ims/system/role     SYS-002（权限唯一载体 · ADR-IMS-008）
    ├── 菜单        /ims/system/menu     SYS-003
    ├── 字典        /ims/system/dict     SYS-004
    ├── 参数        /ims/system/param    SYS-005
    ├── 日志        /ims/system/log      SYS-006
    ├── 通知        /ims/system/notify   SYS-007
    └── 租户套餐    /ims/system/tenant   SYS-008
```

**SYS-008（2026-10-01 · ADR-IMS-007）**：对齐 OPS **FR-M9-003** 租户管理 — 租户列表、绑定 **租户套餐**（`system_tenant_package`）、启用/停用；数据来自 **`system_tenant`** / **`system_tenant_package`**（shenyu-system SSOT）。权限：`ims:tenant:query`、`ims:tenant:update`（映射 `system:tenant:*` / `system:tenant-package:query`）。**不出** 套餐 CRUD 业务规则扩展（沿用 OPS 摘要：分配套餐、状态切换）。

## 页面

| 页面 | 路由 | 导航级别 | 功能点 |
|------|------|----------|--------|
| P1 用户 | `/ims/system/user` | L3 · 系统管理 | SYS-001 |
| P2 角色 | `/ims/system/role` | L3 · 系统管理 | SYS-002（吸收功能点 R/W/D + dataScope + 钉钉岗位 · ADR-IMS-008） |
| P3 菜单 | `/ims/system/menu` | L3 · 系统管理 | SYS-003 |
| P4 字典 | `/ims/system/dict` | L3 · 系统管理 | SYS-004 |
| P5 参数 | `/ims/system/param` | L3 · 系统管理 | SYS-005 |
| P6 日志 | `/ims/system/log` | L3 · 系统管理 | SYS-006 |
| P7 通知 | `/ims/system/notify` | L3 · 系统管理 | SYS-007 |
| P8 租户套餐 | `/ims/system/tenant` | L3 · 系统管理 | SYS-008 |

通用：左侧可部门树（用户页）；敏感列脱敏；权限码展示兼容 `ops:*`；**全模块查询须带 ctx.tenantId**（ADR-IMS-007）。

## P2 角色（SYS-002 · ADR-IMS-008 · 角色 = 权限唯一载体）

> **2026-10-04 扩展**：吸收原 AUTH-003 岗位模板的权限明细（功能点 R/W/D + 数据范围 + 钉钉岗位绑定），成为系统内**唯一的权限载体**。

列表：角色名、角色标识、权限来源（`手工`/`钉钉自动`角标）、状态（启用/待配置）、钉钉岗位、在用人数、更新时间。
权限配置 Tab（编辑抽屉）：
1. **菜单权限**：菜单树多选（权限码，兼容 `ops:*`）；
2. **功能点权限**：按模块分组折叠，每功能点一行 `[功能点名][R][W][D]`（吸收自原 AUTH-003）；
3. **数据范围**：`ALL` / `DEPT` / `IP_GROUP` / `SELF`（=全部 / 本部门 / IP 组 / 仅本人；吸收自原 AUTH-003 `dataScope`。**「本部门」不含下级**）；
4. **钉钉岗位绑定**：可选下拉（唯一；一个钉钉岗位至多绑一个角色）。
操作：`[权限预览]`（模拟用户按角色的权限 Diff：新增绿底/移除红底）、`[一键从岗位生成角色]`（PENDING_CONFIG 空权限 + 进 R1 待办）。
**待配置提示**：`status=PENDING_CONFIG` 的角色（钉钉自动建）以警示 tag 展示，提示"用户将无任何权限（fail-closed）"。

## P2A. 统一权限中间件（B9 · 2026-10-05 决策）

> **决策口径（用户 2026-10-05 拍板，本期落地）**：全业务表的租户隔离与数据范围过滤**在统一权限中间件一处生效**；各业务模块**禁止各写一套**数据范围过滤逻辑。AUTH 定义"谁有哪些权限"（角色权限载体，见《AUTH-权限管理-页面规格》），中间件负责"权限如何执行"（数据范围落地）。

1. **全业务表 `tenant_id` 行级隔离**：所有 `ims_*` 及并入 OPS 的业务表访问，中间件按当前登录上下文 `ctx.tenantId` 自动追加行级过滤谓词，业务代码不得手写 `tenant_id` 条件、不得绕过（对齐 §P2 通用约定"全模块查询须带 ctx.tenantId"、ADR-IMS-007）。
2. **BR-305 四级数据范围（中间件统一执行）**：`ALL` / `DEPT` / `IP_GROUP` / `SELF`（=全部 / 本部门 / IP 组 / 仅本人）四级，取自用户所绑角色的数据范围；**「本部门」不含下级**（旧「本部门及下级」口径已废弃）；判定与 SQL 注入**只在中间件执行**。SYS-002 角色页仅**配置**数据范围值（见 §P2 功能点 3），**不落执行逻辑**。
3. **发布/分享双重过滤（BR-212）**：对含"发布态/分享链接"的数据（如 CONTENT 已发布内容、BI 分享报表），访问须同时满足「**创建者数据范围 ∩ 查看者数据范围**」；中间件对读路径统一施加该交集谓词，任一维度不满足即不可见。
4. **fail-closed（ADR-IMS-008 G1 护栏）**：权限为空、数据范围未配置、角色 `PENDING_CONFIG`、上下文缺失等**一律视为无权**（空权限 ≠ 放行），中间件默认拒绝而非默认放行。
5. **跨租户访问返回 1504**：请求目标 `tenant_id` 与上下文不一致时，中间件统一拦截并返回 **1504**（并入 OPS 租户校验语义保留段，见《全局开发规范-完整版补充》§4）；**响应体不得包含目标资源 id、名称等任何存在性信息**（仅回 1504 + 通用 msg，不区分「存在/不存在」——**B-2 裁决 2026-10-05**）。
6. **禁止各模块自行实现数据范围过滤**：AUTH/ASSET/ACCT/CERT/LIVE/CONTENT/… 各模块页面与 API 契约**不得**自行编写 `tenant_id`/`dataScope` 过滤；如需新增数据源接入，统一由中间件注册过滤规则，禁止旁路。
7. **认证级接口白名单（B9-7 · B-5 裁决 2026-10-05）**：个人工作台（AUTH-004）等**仅需校验登录态**的认证级接口，可仅执行**登录校验 + `tenant_id` 强制轴**，**不做 dataScope 行过滤**；**但不得因此绕过 `tenant_id` 强制轴**（仍强制 `WHERE tenant_id = ctx.tenantId`）。白名单须在中间件注册表**显式登记**（禁默认放行；fail-closed 基线不变）。

## P8 租户套餐（SYS-008）

QueryBar：租户名/联系人/状态。表格：租户 ID、名称、**套餐名称**、过期时间、状态。操作：分配套餐（抽屉 · 套餐下拉 · 确认）。**禁止**手输 menuId；套餐变更后菜单可见性由 **`system_tenant_package_menu`** 决定（与 OPS 一致）。

## P3 菜单

表格：菜单 ID、名称（目录缩进）、路由、权限码（兼容 `ops:*`）、类型（目录/菜单/按钮）、可见。抽屉：名称、路由、权限码、类型。数据来源 `GET /system/menu/tree`。

## P4 字典

左：字典类型列表（`dictType` + 值数量）。右：选中类型的 `dictLabel` / `dictValue` / 排序 / 状态。规则：`dictType` 小写+下划线；`dictValue` 全大写+下划线；停用值不可删。须含并入 OPS 业务字典：`dict_sop_node_type`、`dict_document_type`、`dict_marketing_plan_type`、`dict_position`、`dict_platform_type`、`dict_content_type`、`dict_ai_scene` 等（与系统字典合并）。

## P1 用户

查询：用户名/手机/部门/状态。表格：用户 ID、用户名、昵称、部门、IMS 角色、钉钉 userid、手机、状态。抽屉：新建与编辑（用户名、昵称、手机、部门、状态、角色、初始或重置密码）。禁止改用户主键。

## P5 参数（必含 key）

`work.task.confirm.auto-ai-generate`（bool，默认 false）、`content.review.*`、钉钉开关、`air.key.ip_whitelist.enabled`。

## 规则

- 用户主键 = `ims_sys_user.id`（ADR-IMS-009，本地完整管理）。不回写 Football。手机列脱敏。
- 字典合并系统字典 + 营销计划等业务字典。
- 日志仅记 IMS 新操作。
