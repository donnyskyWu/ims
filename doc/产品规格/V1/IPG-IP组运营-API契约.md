# IPG - IP 组 API 契约（OPS 并入）

> **SSOT 字段与校验**：`docs/engineering/API-M1-运营管理.md` §2（路径前缀 OPS 为 `/admin-api/oa`，IMS 为 `/admin-api/ims`）。  
> 错误码：1001～1004 组 CRUD；**1203** 大组绑账号非法；**1204** 成员用户不存在（须 IMS/Football 可存 user id）。

## 树与 CRUD（IPG-001）

| # | 方法 | IMS 路径 | 说明 |
|---|------|----------|------|
| 1 | GET | `/admin-api/ims/ip-group/tree` | 全量树（管理员） |
| 1b | GET | `/admin-api/ims/ip-group/accessible-tree` | 数据权限过滤树（运营角色） |
| 2 | GET | `/admin-api/ims/ip-group/list` | 分页列表（keyword、groupType、status） |
| 3 | POST | `/admin-api/ims/ip-group/create` | 创建大组/小组 |
| 4 | PUT | `/admin-api/ims/ip-group/update` | 更新基本信息（含 level、sortOrder、remark、status） |
| 5 | DELETE | `/admin-api/ims/ip-group/delete?id=` | 删除（有成员/账号/作者则失败） |

**树节点 VO**（与 OPS 同构）：`id, groupName, groupType(BIG/SMALL), parentId, leaderUserName, memberCount, accountCount, anchorCount, level, status, children[]`

## 成员（IPG-002）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 6 | GET | `/admin-api/ims/ip-group/{id}/members` | 成员列表 |
| 7 | POST | `/admin-api/ims/ip-group/{id}/members` | 添加成员（userId + position + relationType） |
| 8 | PUT | `/admin-api/ims/ip-group/{id}/members/{memberId}` | 修改岗位/主兼 |
| 9 | DELETE | `/admin-api/ims/ip-group/{id}/members/{memberId}` | 移除成员 |

岗位枚举：`dict_position`（@InDict）；写入 userId 须 `FootballSystemUserValidator.resolveStorableUserId`（ADR-056）。

## 账号绑定（IPG-003）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 10 | GET | `/admin-api/ims/ip-group/{id}/accounts` | 已绑账号 |
| 11 | POST | `/admin-api/ims/ip-group/{id}/accounts` | 关联账号（仅 SMALL；accountId 选择器） |

> **级联范式（2026-10-05 · 全系统统一）**：`GET /admin-api/ims/ip-group/{id}/accounts` 是**全系统「实体 → 账号」级联的统一数据源**——REPORT 等域在选定作者/实体后，读取其 `ipGroupId` 再调本端点过滤 `AccountSelect`。**禁止**为每种实体新造 `…/{entity}/accounts` 聚合接口（如 `authors/{id}/accounts`，REPORT 契约已明令禁止）。共池失败返回 **1127**。

## 关联作者（IPG-001 / IPG-004 组内）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 12 | GET | `/admin-api/ims/ip-group/{id}/anchors` | 关联作者列表（返回 `isPrimary` 标记） |
| 13 | POST | `/admin-api/ims/ip-group/{id}/anchors` | 绑定作者（`author_user.id`，ADR-051）；body 增 **`isPrimary?: boolean`** |

> **主作者（`is_primary` · 2026-10-05 拍板「加列」唯一化）**：`oa_ip_group_anchor_rel` **新增列 `is_primary TINYINT(1) DEFAULT 0`**（IR-04 只加列）。**每租户每 IP 组至多 1 个主作者**；设为新主作者时原主自动降级（`is_primary=0`）并**留痕**。删除主作者时同组若有其他作者 → 不自动递补，提示重设（保证"账号→作者"解析**确定性**）。
>
> **为什么**：账号经 IP 组可达多作者（关系表 1:N），而 COST-002 ROI / CONTENT `createArticle` 的 `authorId` **必须唯一**。主作者 + 账号物化列 `oa_platform_account.author_user_id` 共同保证唯一化，解析优先级与错误码 **1223** 见《MASTER-主数据-API契约》§「账号→作者映射列」。**禁止**新造 `authors/{id}/accounts` 反查接口。
>
> **级联读一致性**：`GET /ip-group/{id}/accounts`（账号池）与 `GET /ip-group/{id}/anchors`（作者，含 `isPrimary`）**同源同租户**；二者合起来即"IP 组 → 账号池 / 作者"的统一级联数据源。

## 统计（详情 Tab）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 14 | GET | `/admin-api/ims/ip-group/{id}/stats` | 粉丝/作品/账号/ROI 等聚合 |

## 作者与分析（独立页 IPG-004～005）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 15 | GET | `/admin-api/ims/ip-group/author/page` | 作者分页（P2） |
| 16 | GET | `/admin-api/ims/ops/account-analysis` | 账号分析 |
| 17 | GET | `/admin-api/ims/ops/work-analysis` | 作品/粉丝分析 |
| 18 | GET | `/admin-api/ims/ops/internal-content` | 内部内容分析 |

分析指标来自 **IMS 采集库**，实现期禁止回源 OPS 库。

## 扩展列

- `oa_ip_group.ding_dept_id`：可空，钉钉部门映射（IMS 组织同步）
- `oa_ip_group_anchor_rel.is_primary`：**TINYINT(1) DEFAULT 0**，主作者标记（每租户每 IP 组至多 1 条为 1；2026-10-05 加列，见上「关联作者」）
- `oa_platform_account.author_user_id`：**BIGINT NULL**，账号→作者物化引用（2026-10-05 加列，见《MASTER-主数据-API契约》§账号→作者映射列）
