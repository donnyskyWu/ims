# IMS 验收标准与测试策略 —— Sprint 0 收尾 + AUTH/SYS 首批（含 B9 统一权限中间件）

> **文档类型**：验收标准 + 测试策略（**方案级**；本轮不写测试代码、不落工程文件）
> **日期**：2026-10-05
> **作者**：严过关（Yan）· QA 工程师
> **上游输入**：
> 1. `开发方案/IMS-增量PRD-Sprint0收尾与AUTHSYS首批-20261005.md`（PM·Alice）
> 2. `开发方案/IMS-架构设计-Sprint0与AUTHSYS骨架-20261005.md`（架构·Bob，§3/§4/§5/§6）
> 3. `开发方案/IMS-骨架实现设计稿与工程量-20261005.md`（工程·Kou，§5/§6/§8/§9/§10）
>
> **验收基准（过程包 SSOT）**：`delivery/SLICES-IMS-{AUTH,SYS}.md`、`delivery/CHECKLIST-IMS-{AUTH,SYS}.md`、`delivery/TESTCASES-IMS-{AUTH,SYS}.md`、`产品规格/错误码映射表-附录.md`、`产品规格/全局开发规范.md`（§2/§3/§7A）
> **编号体系**：沿用 `测试方案/` 既有体系 —— `ST-{域}-{序号}`（系统/集成）、`ET-{域}-{序号}`（端到端/异常边界）；引用既有 `TC-IMS-*`、`AT-GEN-*`、`E2E-S1-*`、`ST-SEC-*`。**本文件新增用例一律以「新增」标记**。
>
> **2026-10-05：** 用户主数据改为 `ims_sys_user` 本地管理（ADR-IMS-009）。下文「Football HTTP 只读用户 / system_users.id」的验收句，改为本地用户 ID；Go/chi 字样改为 FastAPI 依赖。数据范围四级与分页不变。  
> **已裁决口径（作为验收前提，不再论证）**：数据范围四级 = `ALL`/`DEPT`/`IP_GROUP`/`SELF`（「本部门」不含下级）；`tenant_id` 正交强制轴；用户 = `ims_sys_user`；分页 `PageParam{pageNo,pageSize}`。

---

## 0. TL;DR

| 维度 | 结论 |
|------|------|
| 交付物 | 9 Slice Gate 判据 · B9 四硬指标矩阵 · SSO/组织同步/SYS 用例设计 · §7A CI 门禁校验 · R-1~R-10 复核 · 回归清单 |
| Gate 层级 | **模块级 Slice Gate**（CHECKLIST 100% + TESTCASES P0 100%）；**非**整系统 S0~S7 |
| 四硬指标 | 4 条（1504 / 四值行数 / BR-212 交集 / fail-closed）+ 1 条配套（B9-6 扫描）= **5 条硬判据** |
| B9 矩阵用例 | 24 条（含 4 值对照四组 + DEPT 不含下级反证 + BR-212 三态 + fail-closed 五态 + 扫描正反例） |
| 新增用例合计 | **98 条**（B9 24 · SSO 17 · 组织同步 10 · 岗位供给 12 · 工作台 6 · SYS 19 · CI 10） |
| 独立发现缺陷 | **21 条**（上游三份产出 + 验收基准过程包；均带 文件+行号/章节 证据） |
| 阻塞结论 | **Slice Gate 当前不可判定** —— 验收基准（SSOT）尚未按冲突①②订正（D-2/D-3/D-5 遗留旧三级口径），须先冻结基准再开 Gate（**2026-10-05 架构师已落地 SSOT 订正，本阻塞可解除，见 §8.2 状态列**） |

> **一句话**：四硬指标判据已可执行，但「验收基准未冻结」与「BR-212 实现语义偏差（D-12）」是两个必须在编码前收口的红线。

---

## 1. 验收前置与 Gate 定义

### 1.1 前置硬门禁（Sprint 0 收尾 · 未关闭则不开 Gate）

| # | 门禁 | 可判定判据 | 未通过的后果 |
|---|------|-----------|--------------|
| P-1 | V1 PRD 冲突句清零 | 对 `产品PRD/IMS第一期PRD-V1.md` 执行 `grep -n "不重复建设\|仅做增量\|增量消费\|整体完成\|与芋道框架保持一致"`，**命中数 = 0**（或仅剩已标「过期·以完整版为准」说明行） | 不开写、不开 Gate |
| P-2 | 表映射登记册定稿 | 覆盖 ≥18 行；每行含加列清单（可生成 `ALTER TABLE ... ADD COLUMN`）；冲突项标 `冲突` 且 `ims_auth_role_matrix`/`ims_auth_data_scope` 标 `作废` | 不开写、不开 Gate |
| P-3 | 验收基准冲突①②订正 | 见 §7 缺陷 D-2/D-3/D-5/D-4：旧三级口径在 SSOT 中**命中数 = 0**，`ims_auth_role_matrix`/`ims_auth_data_scope` 在 V1/V2/V3 PRD 与共享规范中**命中数 = 0**（**2026-10-05 已订正，判据成立**） | ~~Gate 不可判定~~ **已解除（基准冻结）** |
| P-4 | §7A CI 脚本可用 | `bash scripts/ci/forbid_ops_http.sh` 在当前**空白骨架**上 `exit 0`；注入违规样例后 `exit 1` | 不得进入 T02 |

> **P-1/P-2 沿用架构 §10.4 U-5 裁决（硬前置）**；**P-3 为本次复核新增门禁**——理由见 §7 D-2/D-3/D-5：CHECKLIST/页面规格/API 契约仍残留 3 值口径，而本轮验收前提为 4 值，基准不冻结将导致 §2 的 Gate 判据无法给出确定期望值。

### 1.2 Gate 定义（模块级）

对每个 Slice，**出口条件**（三条全满足才视为 Gate 通过）：

| 条件 | 计算式 | 阈值 |
|------|--------|------|
| C1 · CHECKLIST 覆盖率 | （该 Slice 关联 CHK 项中「已勾选」数） ÷ （该 Slice 关联 CHK 项总数） | **= 100%** |
| C2 · TESTCASES P0 通过率 | （该 Slice 关联 P0 用例中「执行通过」数） ÷ （该 Slice 关联 P0 用例总数） | **= 100%** |
| C3 · 横切硬指标 | B9 五硬判据（§3）全绿 + §7A CI 绿灯 + B9-6 扫描 0 命中 | **全绿** |

> **重要**：C1/C2 的**分母**由本文件 §2 表显式给出（避免「CHECKLIST 100%」被解释为全模块而漏掉本片）。**本 Gate 是模块级，不是整系统 S0~S7 Gate**（对齐 `delivery/README.md` 首行）。

---

## 2. Slice Gate 通过判据（9 片 · 逐片可判定）

### 2.1 AUTH 域

| Slice | 关联 CHK（`CHECKLIST-IMS-AUTH`） | 关联 P0 用例 | Gate 判据（给定输入 → 期望） |
|-------|-------------------------------|--------------|------------------------------|
| **S-IMS-A-01** SSO 登录会话 | A-01/A-02/A-03/A-04/A-05/A-06/A-07/A-17/A-18 | TC-IMS-A-001-01/02/03 · ST-AUTH-001-01~10 · ET-AUTH-001-01~07 · ST-SEC-001/002/003 | ① CHK 9 项全勾；② 上述 P0 全过；③ 关键期望：`GET /auth/sso/redirect` 返回 `{authorizeUrl,state}`（state 5min 有效）；`POST /auth/sso/callback` 合法 → 200 + `accessToken`(exp−now≤2h) + `refreshToken`(≤7d) + `profile.userId=system_users.id`；未登录访问 `/ims/system/user` → 302 跳 `/auth/sso/redirect`；无手机 → **1006 且无 Token** |
| **S-IMS-A-02** 组织架构同步 | A-08/A-09/A-10 | TC-IMS-A-002-01/02 · ST-AUTH-002-01~07 · ET-AUTH-002-01~03 | ① CHK 3 项全勾；② P0 全过；③ 关键期望：`POST /auth/org/reconcile`（R1）→ 受理 + 事件列表可查；R4 → **403**；`GET /auth/org/sync-metrics` 返回 `delayMillis`，**<300000 绿 / ≥300000 红**（BR-001） |
| **S-IMS-A-03** 岗位-角色供给规则 | A-11/A-12/A-13 | TC-IMS-A-003-01/02 · ST-AUTH-003-01~11 · ET-AUTH-003-01 | ① CHK 3 项全勾；② P0 全过；③ 关键期望：新建规则 → `version=1`；编辑 → `version+1` 且已套用用户权限**不变**；在用用户非零删除 → **1001**；无角色岗位同步 → `PENDING_CONFIG` **空权限**角色 + R1 待办（G1/G3/G4） |
| **S-IMS-A-04** 个人工作台 | A-14/A-15/A-16 | TC-IMS-A-004-01/02 · ST-AUTH-004-01~06 | ① CHK 3 项全勾；② P0 全过；③ 关键期望：`GET /auth/workbench/todos` 仅本人；预览 ≤10 条；`deadline` 逾期行置顶；`PUT .../messages/{id}/read` 重复调用 → **200**（幂等） |

### 2.2 SYS 域

| Slice | 关联 CHK（`CHECKLIST-IMS-SYS`） | 关联 P0 用例 | Gate 判据（给定输入 → 期望） |
|-------|-------------------------------|--------------|------------------------------|
| **S-IMS-S-01** 用户 | S-01(part)/S-02(part)/S-04/S-05/S-06/S-07 | TC-IMS-S-001-01/02 · ST-SYS-001-01~04 | ① CHK 4 项全勾；② P0 全过；③ 关键期望：`GET /system/user/page` 返回 `PageResult` 且 `list[].id` = Football `system_users.id`（字符串传 snowflake）；`PUT /system/user` 夹带改 `id` → **1211**；手机列脱敏 `138****5678` |
| **S-IMS-S-02** 角色与菜单 | S-08/S-09/S-10/S-11/S-12/S-13/S-14 | TC-IMS-S-002-01/02 · ST-SYS-002-01~07 | ① CHK 7 项全勾；② P0 全过；③ 关键期望：`PUT /system/role/{id}/perm-detail|data-scope|dingtalk-position|menus` 均 200；`data-scope` 非法值（如旧三级口径值）→ **拒绝**（见 §3 ST-B9-044）；权限码不存在 → **1212**；`POST /system/role/from-position` → `PENDING_CONFIG` 空权限 + 幂等 |
| **S-IMS-S-03** 字典 | S-15/S-16/S-17/S-18 | TC-IMS-S-004-01 · ST-SYS-004-01~03 | ① CHK 4 项全勾；② P0 全过；③ 关键期望：`GET /system/dict-data/list?dictType=dict_platform_type` 非空；`dictType` 小写+下划线、`dictValue` 大写+下划线；停用值删除 → **1503** |
| **S-IMS-S-04** 参数 | S-19/S-20 | TC-IMS-S-005-01 · ST-SYS-005-01~03 | ① CHK 2 项全勾；② P0 全过；③ 关键期望：4 个必含 key 可读；`PUT /system/param` 未知 key → **1213** |
| **S-IMS-S-05** 日志与通知（SYS-006/007） | S-21/S-22 | US-SYS-06 · US-SYS-07 | **本轮不适用（批次外）** —— 见 §7 D-8/D-9。**不参与本轮 Gate**，其 CHK（S-21/S-22）与 US-SYS-06/07 从本轮分母中剔除 |

### 2.3 横切（B9 · 不单独成 Slice，绑定 T02/T05）

| 项 | 关联 | Gate 判据 |
|----|------|-----------|
| **B9 统一权限中间件** | ST-B9-001~052（§3）· CHK-A-18 · CHK-S-23/S-24 | **五硬判据全绿**（§3.1~§3.5）：跨租户 1504（不泄露存在性）· 四值行数对照（DEPT 不含下级）· BR-212 交集 · fail-closed 五态 · B9-6 扫描 0 命中 |

> **Gate 分母校正提示**：本轮 SYS 域分母 = S-IMS-S-01~04（S-05 剔除）；AUTH 域 = S-IMS-A-01~04。

---

## 3. B9 权限中间件测试矩阵（**重点** · 四硬指标 + B9-6）

### 3.0 测试夹具剧本 `DS-B9`（所有 B9 用例共用）

| 夹具 | 定义 |
|------|------|
| 租户 | `T0`（上下文 tenantId=0，V1）；`T9`（异租户，仅测试夹具注入，用于 1504） |
| 部门 | `D1`（父）、`D1-1`（D1 的子）、`D2` |
| 用户 | `U_A`(D1，creator) · `U_B`(D1-1) · `U_C`(D2) · `U_D`(无任何角色) |
| IP 组 | `G1`(含 U_A) · `G2`(含 U_C) |
| 数据表 | `oa_production_content`（含列 `tenant_id/dept_id/ip_group_id/creator_id/publish_state/share_owner_id`）；`ims_auth_user_mapping`（`dept_ids` 为 **JSON 列**） |
| 数据行 | 覆盖 {D1,D1-1,D2} × {U_A,U_B,U_C} × {G1,G2} × {PUBLISHED,DRAFT} × {share_owner=U_A/U_C}，行数已知（记 `N_all`） |

### 3.1 硬指标① · 跨租户访问 → 1504（不泄露存在性）

| 编号 | 用例 | 输入 | 期望（可判定） |
|------|------|------|----------------|
| **ST-B9-001** 新增 | 跨租户读单条 | U_A 请求 `GET /system/user/{T9 用户ID}` | `code=1504`，HTTP 403，`msg` 不含目标数据任何字段 |
| **ET-B9-001** 新增 | 存在性不可区分（**已裁决**） | ① 请求 T9 中**存在**的 ID；② 请求全库**不存在**的 ID | 两者响应必须**不可区分**：同为 **1504**、文案同为「资源不可用」；内部日志区分。若 ①=1504、②=1500 则判失败 |
| **ST-B9-002** 新增 | 跨租户写 | U_A `PUT /system/user` 改 T9 用户 | `code=1504`，且**不落库**（DB 校验 tenant 未变） |
| **ST-B9-003** 新增 | 跨租户列表 | U_A 请求列表且夹带 `tenantId=9` 参数 | 参数被**忽略**，仍按 ctx.tenantId=0 过滤（返回 T0 行） |

### 3.2 硬指标② · 不同角色看到不同行数（`ALL`/`DEPT`/`IP_GROUP`/`SELF` 四值对照 + DEPT 不含下级）

| 编号 | 角色 dataScope | 输入 | 期望（可判定） |
|------|---------------|------|----------------|
| **ST-B9-010** 新增 | `ALL` | U_A `GET /oa/production/content/list` | `total = N_all`（T0 全量） |
| **ST-B9-011** 新增 | `DEPT` | U_A（D1）请求 | `total = count(dept_id=D1)`；**断言结果中不含任何 `dept_id=D1-1` 的行** |
| **ST-B9-012** 新增 | `IP_GROUP` | U_A（G1）请求 | `total = count(ip_group_id=G1)` |
| **ST-B9-013** 新增 | `SELF` | U_A 请求 | `total = count(creator_id=U_A)` |
| **ST-B9-020** 新增 | `DEPT` 不含下级（反证） | 同一查询：U_A(D1) 与 U_B(D1-1) 分别请求 | 两者 `total` 不等且互不含对方部门行；**U_A 结果 ∩ U_B 结果的部门集合 = ∅** |
| **ST-B9-021** 新增 | 多角色并集取 maxScope | U_A 同时挂 `DEPT`+`SELF` 两角色 | 生效范围 = `DEPT`（`maxScopeRank(DEPT)=2 > SELF=1`），`total = count(dept_id=D1)` |

> **验收意义**：四组用例的 `total` **必须两两可区分**（`ALL ≥ DEPT/IP_GROUP ≥ SELF`，且 DEPT≠IP_GROUP 由夹具保证），否则「不同角色不同行数」判失败。

### 3.3 硬指标③ · BR-212 发布/分享「创建者 ∩ 查看者」

| 编号 | 输入 | 期望（可判定） |
|------|------|----------------|
| **ST-B9-030** 新增 | U_C（查看者，D2）打开 U_A（创建者，D1）的 **PUBLISHED 分享行**（`share_owner_id=U_A`） | **被过滤**（结果不含该行）—— 创建者范围(D1) ∩ 查看者范围(D2) = ∅ |
| **ST-B9-031** 新增 | U_B（D1-1）打开 U_A 的 PUBLISHED 分享行，且两者范围有交（同父 `D1`） | 按交集结果判定（夹具定义期望值，二者范围相交则可见，否则不可见） |
| **ST-B9-032** 新增 | U_C 打开 U_A 的 **DRAFT 行** | 草稿不受分享交集放大；按**创建者范围**约束（U_C 无权 → 不可见） |
| **ET-B9-030** 新增 | `ALL` 查看者 ∩ `DEPT` 创建者 | 交集 = `DEPT` 创建者范围（`ALL ∩ X = X`）；反向 `DEPT ∩ ALL = DEPT` |

> ⚠ **实现语义红线**：工程师骨架的谓词 `(publish_state <> 'PUBLISHED' OR share_owner = self)`（§5.3）**不等价**于「创建者范围 ∩ 查看者范围」——它只把「已发布行」限定为「查看者=本人」，未做两集合求交。见 §7 **D-12**（有异议，须重定义后再冻结用例期望）。

### 3.4 硬指标④ · fail-closed（空权限 ≠ 放行）

| 编号 | 场景（输入） | 期望（可判定） |
|------|-------------|----------------|
| **ST-B9-040** 新增 | 用户挂 1 个角色但该角色**权限码集合为空** | 受限接口 → **1008 / 403 拒绝**（不得放行） |
| **ST-B9-041** 新增 | 用户仅挂 `status=PENDING_CONFIG` 角色 | 受限接口 → **拒绝**（PENDING_CONFIG 不贡献范围，G3） |
| **ST-B9-042** 新增 | 请求命中的**数据源未在 `scope_registry` 登记** | **拒绝**（未登记 → fail-closed，B9-6） |
| **ST-B9-043** 新增 | 请求上下文缺失（无合法 `LoginContext` / `authenticated=false`） | **拒绝**（1008） |
| **ST-B9-044** 新增 | 角色 `dataScope` 为**非法/未配置**值（含旧三级口径值） | **拒绝**（不降级、不默认 `ALL`） |
| **ST-B9-045** 新增 | `DEPT` 用户但 `ctx.deptIds` 为空 | **拒绝**（不得静默降级为 SELF 或放行） —— 见 §7 D-13 相关 |

> **反面模式禁用**：任何 `if(无角色){放行}` 形式一律判失败（ADR-IMS-008 §4 G1）。

### 3.5 硬指标⑤ · B9-6「业务代码不得手写 `tenant_id`/`dataScope`」

| 编号 | 用例 | 输入 | 期望（可判定） |
|------|------|------|----------------|
| **ST-B9-050** 新增 | 违规扫描（正例应阻断） | 在 `internal/domain/**` 注入 `WHERE tenant_id = ?` 或手写 `dataScope==` | 扫描脚本 `exit 1`，CI 红灯 |
| **ET-B9-050** 新增 | 合规扫描（反例应通过） | `internal/domain/**` 无手写过滤（仅经 `authmw` 注册表） | 扫描 `exit 0` |
| **ST-B9-051** 新增 | 白名单边界 | `internal/authmw/**` 与 `db/query/**` 内出现 `tenant_id` | **放行**（白名单） |
| **ST-B9-052** 新增 | 新数据源登记强制 | 新增一张业务表但未注册 `scope_registry` | 该表访问 → 拒绝（联动 ST-B9-042） |

---

## 4. SSO 全链路用例（AUTH-001）

| 编号 | 用例 | Given → When → Then（可判定） |
|------|------|------------------------------|
| <s>ST-SEC-001</s>（既有） | SSO 唯一入口 | 无 Token 直访 API → **401**；无旁路 |
| **ST-AUTH-001-01** 新增 | 未登录重定向 | 无有效 JWT 访问 `/ims/system/user` → 302/前端守卫跳 `/auth/sso/redirect` → `/login` |
| **ST-AUTH-001-02** 新增 | state 一次校验 | ① 合法 state 首次 callback → 成功；② **同一 state 二次** callback → **1002** |
| **ET-AUTH-001-01** 新增 | state 过期 | state 存入 > 5min 后 callback → **1002** |
| **ET-AUTH-001-02** 新增 | state 缺失/伪造 | 无 state 或随机 state → **1002** |
| **ST-AUTH-001-03** 新增 | callback 换 JWT | 合法 authCode → 200；`accessToken` 有效期 ≤2h；`refreshToken` ≤7d；`profile.userId = system_users.id` |
| **ST-AUTH-001-04** 新增 | refresh 生效 | 合法 refresh → 新 access 可用；旧 access 仍受 exp 约束 |
| **ET-AUTH-001-03** 新增 | logout 失效 | logout 后旧 access/refresh 调用 → **1002**（黑名单命中） |
| **ST-AUTH-001-05** 新增 | **BR-308 无手机不得签发** | 钉钉返回 `mobile=""` → **1006** 且**响应无 Token** |
| **ST-AUTH-001-06** 新增 | mobile 匹配失败 | mobile 有值但 `simple-list` 无命中，且即时同步（V1-A5）仍失败 → **1006 不签发** |
| **ST-AUTH-001-07** 新增 | 离职冻结不签发 | `sysUser` 处于冻结态 → **不签发**（业务码按契约，非 200） |
| **ST-AUTH-001-08** 新增 | 并发会话 ≤3 踢最早 | 同一用户连续登录 4 次 → 第 4 次成功且**第 1 次会话被踢**（其 access 再调用 → 1002）；活动会话数恒 ≤3（联动 ST-SEC-003） |
| **ET-AUTH-001-04** 新增 | 被踢会话失效验证 | 被踢的最早会话 access → **1002** |
| **ET-AUTH-001-05** 新增 | **失败 5 次锁 15min** | 同一主体连续 5 次失败登录 → 第 6 次 **1001（附 R4 说明）**；15min 后自动解锁 | 
| **ET-AUTH-001-06** 新增 | Football HTTP 超时降级 | Football connect/read 超时 → **5003**（钉钉侧）或 **1006**（Football 侧），**均不签发 Token** |
| **ET-AUTH-001-07** 新增 | 钉钉授权码超时/限流 | 钉钉接口超时 → **5003** |
| **ST-AUTH-001-09** 新增 | 埋点 BR-002 | 每次登录尝试产生 success/fail 埋点；统计成功率 **> 99.5%** 判达标 |
| **ST-AUTH-001-10** 新增 | D1 回调跳转 | `GET /sso/dingtalk/callback` 合法 → 302 → `/ims/workbench` |

> ⚠ **实现缺口（见 §7 D-14）**：工程师骨架 §6.1 `Callback` **未实现 AUTH-R4 锁定逻辑**（常量 `lockFailLimit/lockDuration` 已定义但无执行路径），且**未实现** ET-AUTH-001-04 所需的「新会话入并发 ZSET」（§7 D-15）。ET-AUTH-001-05 用例当前**必然失败**，属须先修复项。

---

## 5. AUTH-002 组织同步 & AUTH-003 岗位供给用例

### 5.1 AUTH-002 组织架构同步

| 编号 | 用例 | 期望（可判定） |
|------|------|----------------|
| **ST-AUTH-002-01** 新增 | 事件幂等 upsert | 同一 `(dingtalkEventId,eventType)` 投递 2 次 → `ims_auth_user_mapping` 仅 1 行；第 2 次不重复写 |
| **ET-AUTH-002-01** 新增 | 幂等键组合 | 同 `eventId` 不同 `eventType` → **2 行**（键 = `eventId+eventType`，与架构 §6/outbox 唯一键一致） |
| **ST-AUTH-002-02** 新增 | BR-001 < 5min | hire 事件后 `GET /auth/org/sync-metrics` `delay < 300000ms`（绿）；构造延迟 >5min → **红显** |
| **ST-AUTH-002-03** 新增 | 回调 P95 < 500ms | 200 并发事件投递 → P95 ACK **< 500ms**（只验签+入队，业务异步） |
| **ST-AUTH-002-04** 新增 | 退避 ≤16 次 | 构造持续失败事件 → 重试时刻 = 1m/5m/15m/1h…；`retry_count` 达 16 后 `dead_letter=true` |
| **ET-AUTH-002-02** 新增 | 死信告警 | 达 16 次 → 触发 `ims.org.dead_letter` 告警；事件不再重试 |
| **ST-AUTH-002-05** 新增 | 手动对账权限 | R1 `POST /auth/org/reconcile` → 受理 + 可查记录；**R4 → 403**（TC-IMS-A-002-01/02） |
| **ET-AUTH-002-03** 新增 | 对账连续 2 次失败 | 连续 2 次失败 → **P1 告警**（V1-A4） |
| **ST-AUTH-002-06** 新增 | 调岗 24h 缓冲 | transfer → 部门更新但权限缓冲；**24h 内旧范围仍生效**，超 24h 切新范围（ORG-R3） |
| **ST-AUTH-002-07** 新增 | 离职先冻结 | resign → 用户冻结；**归还未闭环前保持冻结**；闭环后终态（ORG-R4 / BR-015） |

### 5.2 AUTH-003 岗位-角色供给规则（含 G1~G8 自动建角色护栏）

| 编号 | 用例 | 期望（可判定） |
|------|------|----------------|
| **ST-AUTH-003-01** 新增 | 规则 CRUD + 版本 | 新建 → `version=1`；编辑 → `version+1` 且**已套用用户权限不变**（POS-R2，TC-IMS-A-003-01） |
| **ST-AUTH-003-02** 新增 | POS-R1 一岗一启用版本 | 同 `dingtalkPosition` 建第二条启用规则 → **1001** |
| **ST-AUTH-003-03** 新增 | POS-R3 在用拒删 | 规则关联在用用户非零时删除 → **1001**；用户归零后逻辑删除成功 |
| **ST-AUTH-003-04** 新增 | 授予角色含 PENDING_CONFIG | 所选角色 `status=PENDING_CONFIG` → 前端 **fail-closed 提醒（1002）**，且不生效 |
| **ST-AUTH-003-05** 新增 | **G1** fail-closed | 自动建角色权限为**空集**；绝不放行（TC-IMS-A-003-02） |
| **ST-AUTH-003-06** 新增 | **G2** 来源标记 | 自动角色 `source=DINGTALK_AUTO`；手工角色 `source=MANUAL` |
| **ST-AUTH-003-07** 新增 | **G3** 待配置状态 | 自动角色 `status=PENDING_CONFIG`；配置权限后转 `ENABLED` |
| **ST-AUTH-003-08** 新增 | **G4** 进待办 | 自动建角色 → 推「新岗位 X 已自动建角色，请配置权限」到 AUTH-004 待办（R1 收件） |
| **ST-AUTH-003-09** 新增 | **G5** 1:1 唯一 | 同一 `dingtalkPosition` 已绑角色再同步 → **不新建第二个**（唯一约束） |
| **ET-AUTH-003-01** 新增 | **G6** 幂等不覆盖 | 重复同步同一岗位已配置权限的角色 → 权限**不被覆盖** |
| **ST-AUTH-003-10** 新增 | **G7** 回收 | 岗位消失且角色无在用用户 → 角色**归档**（有在用用户 → 拒，沿用 POS-R3） |
| **ST-AUTH-003-11** 新增 | **G8** 审计 | 自动创建 + 自动挂载均写操作日志（SYS-006） |

> G1~G8 定义取自 `产品规划/ADR-IMS-008-角色与岗位权限模型收敛.md` §4（逐条对齐，无自造）；G1~G4 亦可由 AUTH-002 组织同步链路触发（同一护栏，两入口）。

### 5.3 AUTH-004 个人工作台

| 编号 | 用例 | 期望（可判定） |
|------|------|----------------|
| **ST-AUTH-004-01** 新增 | 卡片按权限渲染 | 无权卡片**隐藏**（不可见，非置灰可点） |
| **ST-AUTH-004-02** 新增 | 预览各 10 条 | 待办/消息预览均 ≤ 10 条；[查看更多] 进二级列表（TC-IMS-A-004-01） |
| **ST-AUTH-004-03** 新增 | 逾期置顶 | 待办按 `deadline` 升序；**逾期行红底置顶**（WB-R1） |
| **ST-AUTH-004-04** 新增 | 外协仅指派 | `R10` 用户**仅显示被指派任务**（WB-R3） |
| **ST-AUTH-004-05** 新增 | 已读幂等 | `PUT .../messages/{id}/read` 重复调用 → **200**；钉钉推送去重 ≤ 3 次（WB-R2，TC-IMS-A-004-02） |
| **ST-AUTH-004-06** 新增 | 跳转失效单据 | 跳转目标不存在 → 提示 + 待办自动置 `DONE` |

---

## 6. SYS 域用例（SYS-001~005）

### 6.1 SYS-001 用户

| 编号 | 用例 | 期望 |
|------|------|------|
| **ST-SYS-001-01** 新增 | 分页列表 | `GET /system/user/page` → `PageResult`；`list[].id` = Football `system_users.id`；`total/pageNo/pageSize` 一致（TC-IMS-S-001-01） |
| **ST-SYS-001-02** 新增 | 禁改主键 | `PUT /system/user` 夹带改 `id` → **1211**；DB 中 id 未变（TC-IMS-S-001-02） |
| **ET-SYS-001-01** 新增 | 脱敏 | 手机列返回 `138****5678`（明文不落响应/日志） |
| **ST-SYS-001-03** 新增 | U-2「仅建 IMS 侧映射」**负向** | `POST /system/user`（SYS-001 创建）→ **仅写 `ims_auth_user_mapping`/`ims_sys_user_role`**；**断言未调用 Football 建号 API**（mock Football 断言零写入调用） |

### 6.2 SYS-002 角色与菜单（含 5 端点）

| 编号 | 用例 | 期望 |
|------|------|------|
| **ST-SYS-002-01** 新增 | perm-detail | `PUT /system/role/{id}/perm-detail` 保存功能点×R/W/D → 200 并可回读 |
| **ST-SYS-002-02** 新增 | data-scope（4 值） | `PUT /system/role/{id}/data-scope` 入参 ∈ {ALL,DEPT,IP_GROUP,SELF} → 200；旧三级口径值 → **拒绝** |
| **ST-SYS-002-03** 新增 | dingtalk-position 唯一 | 绑定已占用岗位 → **1001**；解绑后再绑 → 200 |
| **ST-SYS-002-04** 新增 | preview | `POST /system/role/{id}/preview` 模拟用户 → 返回权限 Diff |
| **ST-SYS-002-05** 新增 | from-position | `POST /system/role/from-position` 无角色岗位 → `PENDING_CONFIG` **空权限** + R1 待办；重复调用**幂等** |
| **ST-SYS-002-06** 新增 | 权限码兼容 `ops:*` | 菜单权限码含 `ops:*` → 保存成功；非法权限码 → **1212** |
| **ST-SYS-002-07** 新增 | 角色并集 | 用户挂 2 角色 → 可见菜单 = 两角色菜单**并集**（FR-AUTH-022） |

### 6.3 SYS-003 菜单

| 编号 | 用例 | 期望 |
|------|------|------|
| **ST-SYS-003-01** 新增 | 菜单树 SSOT | `GET /system/menu/tree` 数据源 = `ims_sys_menu`，返回树结构 |
| **ST-SYS-003-02** 新增 | **menuId 对账（U-3）** | 上线前对账脚本：`ims_sys_menu.id` 与 `system_menu.id` **差异数 = 0**（含预留段登记）；差异 >0 → 阻断上线 |

### 6.4 SYS-004 字典

| 编号 | 用例 | 期望 |
|------|------|------|
| **ST-SYS-004-01** 新增 | 含 OPS 并入项 | `dict_platform_type`/`dict_content_type`/`dict_sop_node_type`/`dict_position` 等**非空**（seed） |
| **ET-SYS-004-01** 新增 | 命名规则 | `dictType` 非法（大写/连字符）或 `dictValue` 非法 → **1503** |
| **ET-SYS-004-02** 新增 | 停用值不可删 | 删除停用字典值 → **1503/1502** 拒绝 |

### 6.5 SYS-005 参数

| 编号 | 用例 | 期望 |
|------|------|------|
| **ST-SYS-005-01** 新增 | 必含 key 可读写 | `work.task.confirm.auto-ai-generate`(bool 默认 false)、`content.review.*`、钉钉开关、`air.key.ip_whitelist.enabled` 均可读；bool 持久化（TC-IMS-S-005-01） |
| **ET-SYS-005-01** 新增 | 未知 key | `PUT /system/param` 未知 key → **1213** |
| **ST-SYS-005-02** 新增 | key 不改 | 切流后 key 只读不改（无 rename 接口） |

---

## 7. CI 门禁校验（§7A · 正例/反例，命中即阻断）

> 来源：`产品规格/全局开发规范.md` §7A.1 + 工程师 §9.2 `forbid_ops_http.sh`。**白名单仅 `FootballWebApiClient`（`internal/pkg/football/**`，配置键 `football.webapi.*`）**。

| 编号 | 用例 | 输入 | 期望 |
|------|------|------|------|
| **ST-CI-01** 新增 | 禁项一 · 正例（阻断） | 源码/配置注入 `ops.internal`/`ops-gateway` | 扫描命中 → `exit 1` |
| **ET-CI-01** 新增 | 禁项一 · 反例（放行） | 无 OPS host | `exit 0` |
| **ST-CI-02** 新增 | 禁项二 · 正例（阻断） | 配置注入 `ops.base-url` / `FeignClient` / `@DS(` / `/rpc-api/ops` | `exit 1` |
| **ET-CI-02** 新增 | 禁项二 · 反例（放行） | 无上述串 | `exit 0` |
| **ST-CI-03** 新增 | 禁项三 · 正例（阻断） | `internal/domain/**` 出现 `http.Get(` 外网调用 | `exit 1` |
| **ST-CI-04** 新增 | 白名单边界 | `internal/pkg/football/client.go` 出现 `http.NewRequest(` | **放行**（唯一白名单） |
| **ET-CI-03** 新增 | 白名单外第二 HTTP 依赖 | 新增 `internal/pkg/other/client.go` 调外部 host | `exit 1` |
| **ST-CI-05** 新增 | §7A+B9-6 双跑 | 同时注入 OPS host 与手写 `tenant_id` | 两项均报错，`exit 1` |
| **ST-CI-06** 新增 | **`--no-verify` 绕过应被拒** | 本地 `git commit --no-verify` | **不作为合法绕过**：门禁必须在**服务端 CI job（MR 事件）**运行并红灯阻断合并；本地 hook 绕过不影响 MR 结果 |
| **ST-CI-07** 新增 | 架构测试互补 | `go test ./internal/architecture/...` | `TestForbidOpsHTTP` 与 shell 脚本结论一致 |

> ⚠ **实现缺口（§7 D-16）**：脚本 `WHITELIST_PATHS` 仅排除 `internal/pkg/football/**`，**未排除 `internal/pkg/dingtalk/**`**（禁项一/二），而 dingtalk 依赖为合法外部依赖 → **潜在误报**；禁项一正则 `ops[._-]?` 过宽（可能误伤 `operations`/`props`）→ **潜在误报**。

---

## 8. 风险复核结论（R-1~R-10）与独立发现缺陷

### 8.1 R-1~R-10 逐条复核（工程师 §10）

| 风险 | 结论 | 说明 / 需补充项 |
|------|------|-----------------|
| **R-1** T02/T03 时序耦合 | **需补充** | 「T02 无角色 → 全部拒绝」会使 T02 阶段受保护端点 100% fail-closed、联调不可用；须显式定义 T02 阶段**认证级白名单**（如 workbench），否则阻塞开发 |
| **R-2** sqlc × IR-04 只加列 | **认可** | 补充：`db/compat/*.sql` 须幂等 + 提供 down 脚本 + OPS 运行期兼容验证用例 |
| **R-3** Football 读降级 | **认可** | 补充：短 TTL 缓存**必须包含冻结状态或 TTL ≤ 60s**，否则离职冻结用户可能被缓存放行（违反 ORG-R4） |
| **R-4** fail-closed 误伤 | **有异议** | 「工作台走公开级」与 B9-4 fail-closed 存在张力，需 ADR 明确「认证级 vs 数据范围级」两档；PENDING_CONFIG 的 **1002（前端提示）** 与中间件 **1008（拒绝）** 边界须写清 |
| **R-5** tenant_id 越权传参 | **认可** | 补充用例 ST-B9-003 |
| **R-6** BR-212 交集语义 | **有异议** | 骨架谓词 `(publish_state <> 'PUBLISHED' OR share_owner = self)` 与「创建者∩查看者」**不等价**（详见 D-12），须重定义 |
| **R-7** 并发踢人竞态 | **认可** | 补充：骨架**未把新会话写入并发 ZSET**（D-15），计数恒 0，限流形同失效；须 Lua 原子化 |
| **R-8** 回调超时 | **认可** | 补充：outbox 唯一键去重须覆盖「解密失败」分支 |
| **R-9** §7A 误报/漏报 | **认可** | 补充：白名单漏 `dingtalk`、正则过宽（D-16），须补白名单与收紧正则 |
| **R-10** menu_id 对账 | **认可** | 补充：须给出对账脚本 + 阈值（差异=0）+ 预留 id 段区间定义 |

### 8.2 独立发现缺陷（带证据 · 文件+行号/章节）

**A. 上游产出内部矛盾 / 未吸收已裁决口径**

| # | 缺陷 | 证据 | 影响 |
|---|------|------|------|
| **D-1** ✅已订正 | 增量 PRD §2.3 B9-2 原写旧三值口径、**缺 `IP_GROUP`**，与已裁决口径（ALL/DEPT/IP_GROUP/SELF）矛盾 → **2026-10-05 已改为 4 值口径** | `IMS-增量PRD-...-20261005.md` **行 161** | 已消解 |
| **D-2** ✅已订正 | `CHECKLIST-IMS-SYS` 原为 3 值 → **2026-10-05 已改为 4 值口径** | `delivery/CHECKLIST-IMS-SYS.md` **行 24** | 已消解 |
| **D-3** ✅已订正 | 页面规格/API 契约原 3 值 → **2026-10-05 已改为 4 值口径** | `产品规格/V1/SYS-系统管理-页面规格.md` **行 48/58**；`SYS-系统管理-API契约.md` **行 12/34** | 已消解 |
| **D-4** ✅已订正 | ADR-IMS-008 §2 原 `ALL`/旧三值 → **2026-10-05 已改为 `ALL`/`DEPT`/`IP_GROUP`/`SELF`** | `产品规划/ADR-IMS-008-...md` **行 28** | 已消解 |
| **D-5** ✅已订正 | AUTH 页面规格原含旧三值 → **2026-10-05 已改为 4 值口径** | `产品规格/V1/AUTH-权限管理-页面规格.md` **行 7** | 已消解 |
| **D-6** ✅已订正 | `CHECKLIST-IMS-AUTH` 原用 **`@PreAuthorize`（Spring/芋道注解）** → **2026-10-05 已改为 Go/chi 口径（chi 中间件 `RequirePerm` + 权限码校验）** | `delivery/CHECKLIST-IMS-AUTH.md` **行 39** | 已消解 |
| **D-7** | AUTH 侧仍引用 `/auth/position/preview`，但 Diff 预览已迁至**按角色** `/system/role/{id}/preview`（架构 §4 列 4d） | `delivery/CHECKLIST-IMS-AUTH.md` **行 30**；`delivery/TESTCASES-IMS-AUTH.md` **行 30**；对照 `AUTH-权限管理-页面规格.md` **行 350** | 端点归属矛盾 |
| **D-8** ✅已订正 | 原 `SLICES-IMS-SYS` 声明 SYS-008 In Scope，与增量 PRD「批次外」冲突 → **2026-10-05 已统一为「批次外」**（待 menuId 对账） | `delivery/SLICES-IMS-SYS.md` **行 5**；`delivery/CHECKLIST-IMS-SYS.md` **行 11**；对照 `IMS-增量PRD-...md` **行 198** | 已消解 |
| **D-9** ✅已订正 | S-IMS-S-05（日志通知）本轮无 Gate 归属 → **2026-10-05 已在 SLICES/CHECKLIST 显式标注「批次外 · 本轮无 Gate 归属」** | `IMS-架构设计-...md` **§6.1**；`delivery/SLICES-IMS-SYS.md` | 已消解（分母明确为 8 片） |
| **D-10** ✅已订正 | 测试基准原 **Token 8h / 刷新 30 天** → **2026-10-05 已改为 2h / 刷新 7 天**（ST-SEC-002 · E2E-S1-02 · UT-AUTH-001-03） | `测试方案/IMS-系统测试用例.md` **行 58**；`IMS-E2E测试用例Checklist.md` **行 34**；`IMS-单元测试Checklist.md` **行 30** | 已消解 |
| **D-11** ✅已订正 | 测试基准原「本部门/下级/全部三档」→ **2026-10-05 已改为 4 值口径（无下级）** | `测试方案/IMS-接口与集成测试用例.md` **行 39**；`IMS-单元测试Checklist.md` **行 47**；`IMS-整体测试方案.md` **行 149** | 已消解 |

**B. 工程师骨架实现缺陷（设计稿 §5/§6/§9）**

| # | 缺陷 | 证据 | 影响 |
|---|------|------|------|
| **D-12** | BR-212 谓词实现 `(publish_state <> 'PUBLISHED' OR share_owner = self)` **≠** 「创建者范围 ∩ 查看者范围」：只把已发布行限定为「查看者=本人」，未做集合求交；且注释「未发布行由创建者范围约束」与谓词分支方向不一致 | §5.3 `Predicate`（行 976~980） | BR-212 硬指标③不可验收（R-6） |
| **D-13** | DEPT 分支对注册为 **JSON 列**的 `dept_ids` 生成 `dept_ids IN (?,?)`，语义错误；§5.2 注释自认「需专用解析（见 resolver）」但 resolver 未实现 | §5.2 `registerAll`（行 824~826）+ §5.3 `Predicate`（行 962） | 组织映射表 DEPT 过滤失效 |
| **D-14** | **AUTH-R4（失败 5 次锁 15min）未实现**：常量 `lockFailLimit/lockDuration` 定义但 `Callback` 无执行路径；而 §5.1 时序图 line 44 声称有 → 骨架与自身时序图不一致 | §6.1（行 1173~1176 常量；`Callback` 行 1200~1257 无锁定） | ET-AUTH-001-05 必失败 |
| **D-15** | `enforceConcurrent` **只读 ZCard / 踢人，未 `ZAdd` 新会话** → 并发 ZSET 永不增长、限流恒不触发；且 `n>=3` 才踢且只踢 1 个，「≤3」边界未澄清 | §6.1（行 1284~1296） | AUTH-R3 形同失效（R-7） |
| **D-16** | §7A 脚本**白名单漏 `internal/pkg/dingtalk/**`**；禁项一正则 `ops[._-]?` 过宽（易误伤 `operations`/`props`） | §9.2（行 1829/1832） | 误报→CI 假红灯 |
| **D-17** | 跨租户 **1504 由 per-handler `EnsureTenant` 触发**，非「中间件统一拦截」；中间件链自身无法产出 1504 → 与 B9-5「一处执行」矛盾 | §5.5 `guard.go`（行 1127~1138）；对照 §5.3 `RowScope` 中间件（无 1504） | 1504 分散落地，易漏（B9-6 精神） |
| **D-18** | 前端 `ensureProfile()` 用 **`GET /auth/sso/refresh`**（契约 refresh 为 POST，且返回 Token 非 Profile）；`hasPerm` 兜底 `|| this.roles.length > 0` → **任意有角色用户前端放行所有权限码**（前端 fail-open） | §7.5 `stores/user.ts`（行 1656~1661） | 前端越权/契约漂移 |
| **D-19** | `isCfgPending: s.profile?.status === 'FROZEN'` 把「离职冻结(FROZEN)」误等同「待配置(PENDING_CONFIG)」 | §7.5（行 1649） | 状态语义错误 |

**C. 其他**

| # | 缺陷 | 证据 | 影响 |
|---|------|------|------|
| **D-20** | 架构 §3.2 登记册 row 12 引用「迁 **§11**」，但架构文档章节止于 §10（无 §11） | `IMS-架构设计-...md` **§3.2 行 389** | 断链（轻微） |
| **D-21** | **1504 与「不泄露存在性」张力**：跨租户返回 1504、不存在返回 1500，二者码不同 → 攻击者可区分「他租户存在」vs「不存在」 | 错误码附录 §3；架构 §5.3 行 124 注释「不泄露存在性」 | 需架构裁决：跨租户查询是否统一返回 1504/1500 不可区分（见 ET-B9-001） |

> 缺陷合计 **21 项**（其中 A 类基准/文档 11、B 类实现 8、C 类 2）。**A 类 D-1~D-5 与 D-8/D-9 属「验收基准未冻结」，是 Gate 不可判定的直接原因（见 §1.1 P-3）。**

### 8.3 设计稿 v1.1 复核（2026-10-05 开工闸门）

对照《IMS-骨架实现设计稿与工程量-20261005》文首修订表与 §5/§6/§9 正文：

| 缺陷 | 复核结论 |
|------|----------|
| D-12 | §5.3 已改为查看者维度 AND 创建者维度，去掉顶层 OR 短路。**勾销** |
| D-13 | DEPT 改为 `ims_auth_user_dept` 关联表 `EXISTS`，`JSON_CONTAINS` 仅兜底。**勾销** |
| D-14 | `checkLoginLock` / `incrLoginFail` / `resetLoginFail` 已写入 SSO。**勾销** |
| D-15 / D-25 | 新会话 `ZAdd`，score 为时间戳高位 + 序列低位，Lua 原子踢最早。**勾销** |
| D-16 | 白名单扩为 Football / 钉钉 / ComfyUI·jingcai，正则收紧。**勾销** |
| D-17 / D-24 | 1504 收口到统一拦截；未登记 `{id}` 路由 fail-closed。**勾销** |
| D-18 | 前端 `hasPerm` 改为无明确权限码不放行；profile 走 `POST /auth/sso/refresh`。**勾销** |
| D-19 | `FROZEN` 与 `PENDING_CONFIG` 不再等同。**勾销** |
| D-20 | 架构章节引用断链，不影响编码。**不阻塞** |
| D-21 | **已裁决**：调用方统一 1504 +「资源不可用」，见架构 §10.4 |
| D-7 | CHECKLIST 已指向 `POST /system/role/{id}/preview`；TESTCASES 负向用例已补。**勾销** |

### 8.3 设计稿 v1.1 复核（2026-10-05 开工闸门）

对照《IMS-骨架实现设计稿与工程量-20261005》文首修订表与 §5/§6/§9 正文：

| 缺陷 | 复核结论 |
|------|----------|
| D-12 | §5.3 已改为查看者维度 AND 创建者维度，去掉顶层 OR 短路。**勾销** |
| D-13 | DEPT 改为 `ims_auth_user_dept` 关联表 `EXISTS`，`JSON_CONTAINS` 仅兜底。**勾销** |
| D-14 | `checkLoginLock` / `incrLoginFail` / `resetLoginFail` 已写入 SSO。**勾销** |
| D-15 / D-25 | 新会话 `ZAdd`，score 为时间戳高位 + 序列低位，Lua 原子踢最早。**勾销** |
| D-16 | 白名单扩为 Football / 钉钉 / ComfyUI·jingcai，正则收紧。**勾销** |
| D-17 / D-24 | 1504 收口到统一拦截；未登记 `{id}` 路由 fail-closed。**勾销** |
| D-18 | 前端 `hasPerm` 改为无明确权限码不放行；profile 走 `POST /auth/sso/refresh`。**勾销** |
| D-19 | `FROZEN` 与 `PENDING_CONFIG` 不再等同。**勾销** |
| D-20 | 架构章节引用断链，不影响编码。**不阻塞** |
| D-21 | **已裁决**：调用方统一 1504 +「资源不可用」，见架构 §10.4 |
| D-7 | CHECKLIST 已指向 `POST /system/role/{id}/preview`；TESTCASES 负向用例已补。**勾销** |

---

## 9. 回归清单（每片完成后必重跑的最小集合）

> **每次提交（任一 Slice 完成后）必跑「常驻集」；再叠加「本片集」。**

### 9.1 常驻集（回归基线 · 每片必跑）

| 组 | 用例 | 备注 |
|----|------|------|
| CI 门禁 | ST-CI-01~07（§7A + B9-6 双扫描 + 架构测试） | 红灯即阻断 |
| B9 四硬指标 | ST-B9-001/003 · ST-B9-010~013 · ST-B9-020 · ST-B9-030~032 · ST-B9-040~045 · ST-B9-050 | 安全红线，永不豁免 |
| 认证冒烟 | ST-AUTH-001-01/03/05/07 · ET-AUTH-001-03 | 登录/无手机/冻结/注销 |
| 契约通用 | AT-GEN-001/004/005/008/009（鉴权/包裹/分页/命名/错误码段位） | 防契约漂移 |
| 基准对账 | ST-SYS-003-02（menuId 对账） | 上线门禁 |

### 9.2 分片叠加集

| 完成片 | 额外必跑 |
|--------|----------|
| S-IMS-A-01 | ST-AUTH-001-02/08/09/10 · ET-AUTH-001-01/02/04/05/06/07 |
| S-IMS-A-02 | ST-AUTH-002-01~07 · ET-AUTH-002-01~03 |
| S-IMS-A-03 | ST-AUTH-003-01~11 · ET-AUTH-003-01（规则 CRUD/版本/POS-R1~R3 + G1~G8） |
| S-IMS-A-04 | ST-AUTH-004-01~06（预览 10/逾期置顶/外协仅指派/已读幂等） |
| S-IMS-S-01 | ST-SYS-001-01~03 · ET-SYS-001-01 |
| S-IMS-S-02 | ST-SYS-002-01~07 |
| S-IMS-S-03 | ST-SYS-004-01 · ET-SYS-004-01/02 |
| S-IMS-S-04 | ST-SYS-005-01/02 · ET-SYS-005-01 |
| 横切 T05 | B9 全矩阵（§3 全部 24 条）+ §4/§5 全量 |

### 9.3 进入下一片的前置（分层准入）

> 下层不达标不进上层：`单元 + 接口(AT) 不达标 → 不进入 集成(IT)`；`B9 四硬指标不绿 → 不进入任何业务片 Gate`。

---

## 附录 A. 用例编号与新引用速查

| 前缀 | 含义 | 本文件新增数 |
|------|------|-------------|
| `ST-B9-*` / `ET-B9-*` | B9 权限中间件（系统/边界） | 24 |
| `ST-AUTH-001-*` / `ET-AUTH-001-*` | SSO 全链路 | 17 |
| `ST-AUTH-002-*` / `ET-AUTH-002-*` | 组织同步（AUTH-002） | 10 |
| `ST-AUTH-003-*` / `ET-AUTH-003-*` | 岗位-角色供给 + G1~G8（AUTH-003） | 12 |
| `ST-AUTH-004-*` / `ET-AUTH-004-*` | 个人工作台（AUTH-004） | 6 |
| `ST-SYS-*` / `ET-SYS-*` | SYS 域（SYS-001~005） | 19 |
| `ST-CI-*` / `ET-CI-*` | §7A CI 门禁 | 10 |
| **合计新增** | | **98** |

**复用既有（不新增）**：`TC-IMS-A-*`、`TC-IMS-S-*`、`ST-SEC-001/002/003`、`AT-GEN-001~010`、`E2E-S1-*`、`US-*`。

## 附录 B. 待裁决项（影响 Gate 可判定性）

| # | 事项 | 关联缺陷 | 建议默认 |
|---|------|----------|----------|
| B-1 | 冻结验收基准：SSOT 内旧三级口径命中清零（先订正 CHECKLIST/页面规格/API 契约/ADR-008） —— **2026-10-05 已落地** | D-1~D-5 | ✅ 已订正，可开 Gate |
| B-2 | 跨租户与不存在对调用方不可区分 | D-21 / ET-B9-001 | **已裁决**：统一 1504 +「资源不可用」 |
| B-3 | BR-212 谓词重定义（创建者∩查看者求交） | D-12 / ST-B9-030~032 | **已勾销**：设计稿 v1.1 两维 AND |
| B-4 | S-IMS-S-05 是否纳入本轮（当前批次外，无 Gate 归属） | D-9 | **已剔除**，本轮分母不含 |
| B-5 | T02 阶段认证级白名单 | R-1 / R-4 | **已裁决**：仅 `/auth/workbench/**` 为认证级；其余 1008 |

---

（全文完）
