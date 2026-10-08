# API-M1-运营管理

> **版本**：v1.1 | 2026-06-07 | 2026-10-02
> **关联 PRD**：`docs/product/PRD-M1-运营管理.md`
> **关联 UX**：`docs/product/UX-M1-运营管理.md`
> **关联技术约束**：`docs/engineering/TECH-CONSTRAINTS.md`
> **遵循规范**：见 `## 8. API 路径规范`（v9.1 主 PRD）

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 通用约定

### 1.1 命名与前缀

- 全部接口挂在 `/admin-api/ops/...` 前缀下
- 资源名使用 **中横线**（kebab-case），如 `ip-group`、`account-analysis`
- 资源集合操作走 `/{resource}/list`、`/{resource}/create` 等显式动作（避免 REST 风格歧义）
- 单个资源的 ID 路径用 `/{id}` （已替换为具体内容）

| Header | 必填 | 说明 |
|--------|------|------|
| `Authorization` | ✅ | Bearer token |
| `X-Tenant-Id` | ✅ | 租户 ID，多租户隔离 |
| `Content-Type` | POST/PUT 必填 | `application/json` |

### 1.3 通用响应

```json
{
  "code": 0,
  "message": "ok",
  "data": { /* 业务对象 */ }
}
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1xxx | 业务错误（见第 5 节错误码） |
| 401 | 未登录 |
| 403 | 无权限 |
| 5xx | 系统异常 |

### 1.4 分页约定

- 请求参数：`page`（从 1 开始）、`size`（默认 20，最大 200）
- 响应包装：`PageResult<T>` 含 `list, total, page, size`

---

## 2. IP 组管理 API（FR-M1-001）

### 2.1 GET `/admin-api/ops/ip-group/tree`

获取 IP 组树形结构。

**请求参数**：无

**响应** `List<IpGroupTreeVO>`：

```json
[
  {
    "id": 1,
    "groupName": "娱乐八卦大组",
    "groupType": "BIG",
    "parentId": null,
    "leaderUserName": "张三",
    "memberCount": 3,
    "accountCount": 12,
    "anchorCount": 2,
    "level": "A",
    "children": [
      { "id": 11, "groupName": "八卦一组", "groupType": "SMALL", "parentId": 1, "...": "..." }
    ]
  }
]
```

### 2.2 GET `/admin-api/ops/ip-group/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | ❌ | 默认 1 |
| size | int | ❌ | 默认 20 |
| groupType | string | ❌ | BIG / SMALL |
| keyword | string | ❌ | 名称模糊 |
| status | int | ❌ | 0/1 |

**响应**：`PageResult<IpGroupVO>`

### 2.3 POST `/admin-api/ops/ip-group/create`

**请求体** `IpGroupCreateReq`：

```json
{
  "groupName": "娱乐八卦大组",
  "groupType": "BIG",
  "parentId": null,
  "leaderUserId": 100,
  "level": "A",
  "description": "...",
  "status": 1
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `level` | String | ❌ | IP 组等级，`@InDict("dict_ip_group_level")`：S/A/B/C；空=未分级 |

**响应**：`Long`（新 ID）

**业务校验**（失败返回 1001-1004）：

- 名称 1-50 字符
- 同父级下名称唯一
- 小组必须有 parentId，且父级 groupType=BIG
- leaderUserId 必须在 sys_user 表

### 2.4 PUT `/admin-api/ops/ip-group/update`

修改 IP 组基本信息（不修改成员/账号/主播关系）。

**请求体** `IpGroupUpdateReq`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Long | ✅ | IP 组 ID |
| `groupName` | String | ❌ | 组名（不传则不改） |
| `parentId` | Long | ❌ | 上级组 ID（**仅小组可改**，大组必须为 null，不能是自己/子孙/非大组/跨租户） |
| `leaderId` | Long | ❌ | 组长 ID |
| `leaderUserId` | Long | ❌ | 组长用户 ID（与 `leaderId` 等价，优先用此字段） |
| `sortOrder` | Integer | ❌ | 排序 |
| `status` | Integer | ❌ | 状态（0/1） |
| `level` | String | ❌ | IP 组等级，`@InDict("dict_ip_group_level")`：S/A/B/C |
| `remark` | String | ❌ | 备注 |

**校验**：
- 仅 `groupType=2`（小组）可改 `parentId`
- `parentId` 不能等于自己
- `parentId` 不能是该节点的子孙（防死循环）
- `parentId` 必须存在 / 同租户 / `groupType=1`（大组）
- `groupName` 在新 `parentId` 范围内不重复（1002）

> P-GATE-UNMOCK S-E (2026-06-09)：原 spec 漏 `parentId` 字段，导致编辑时改上级组不生效。已补字段 + 校验 + 5 个 IT。

**响应**：`Boolean`

### 2.5 DELETE `/admin-api/ops/ip-group/delete`

**请求参数**：`id` (Long)

**响应**：`Boolean`

**业务规则**（BR-M1-001）：

- 当该 IP 组下存在成员/账号/主播时 → 返回 1005 "该 IP 组下存在数据，禁止删除"

### 2.6 GET `/admin-api/ops/ip-group/{id}/members`

**路径参数**：`id`

**响应**：`List<IpGroupMemberVO>`

### 2.7 POST `/admin-api/ops/ip-group/{id}/members`

**请求体**：

```json
{
  "userId": 200,
  "position": "OPERATOR",
  "isLeader": false
}
```

**响应**：`Boolean`

**业务规则**：position 枚举 `OPS_LEADER / OPERATOR / ANCHOR / EDITOR / LIVE_OPERATOR / SALES`

### 2.8 PUT `/admin-api/ops/ip-group/{id}/members/{memberId}`

修改成员信息。

### 2.9 DELETE `/admin-api/ops/ip-group/{id}/members/{memberId}`

删除成员（删除前检查是否有关联任务 → 1006）

### 2.10 GET `/admin-api/ops/ip-group/{id}/accounts`

获取该 IP 组下已关联的账号列表。

### 2.11 POST `/admin-api/ops/ip-group/{id}/accounts`

**请求体**：

```json
{
  "accountIds": [101, 102, 103],
  "accountRole": "PRIMARY"
}
```

**响应**：`Boolean`

**业务规则**：

- 同一账号已在其他 IP 组 → 1007 "账号 [X] 已属于 [其他IP组]，无法重复添加"
- 账号仅能关联到 SMALL 类型的 IP 组 → 1008

### 2.12 POST `/admin-api/ops/ip-group/{id}/anchors`

绑定**关联作者**到 IP 组（DB 列名 `anchor_user_id` 保留；语义为 `author_user.id`，见 ADR-051）。

**请求体**：

```json
{
  "anchorUserIds": [68028, 68029],
  "anchorType": "BOTH"
}
```

| 字段 | 说明 |
|------|------|
| `anchorUserIds` | **作者 ID 列表**（`author_user.id` / API 别名 `authorId`）；**非** `sys_user.id` |
| `anchorType` | `@InDict("dict_author_type")`；可空，默认取作者档案类型 |

**响应**：`Boolean`

**列表 GET `.../anchors` 响应** `IpGroupAnchorVO`：含 `authorId`/`authorName`（展示）与 `anchorUserId`/`anchorUserName`（兼容别名）。

### 2.13 GET `/admin-api/ops/ip-group/{id}/stats`

获取 IP 组统计。

**响应** `IpGroupStatsVO`：

```json
{
  "ipGroupId": 1,
  "followerCount": 1234567,
  "contentCount": 234,
  "accountCount": 12,
  "roiAvg": 3.5,
  "costTotal": 50000.00,
  "revenueTotal": 175000.00,
  "last7DaysTrend": [...],
  "last30DaysTrend": [...]
}
```

---

## 3. 作者管理 API（FR-M1-002）

### 3.1 GET `/admin-api/ops/author/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | ❌ | 默认 1 |
| size | int | ❌ | 默认 20 |
| ipGroupId | Long | ❌ | IP 组筛选 |
| keyword | string | ❌ | 作者名模糊 |
| status | int | ❌ | 0/1 |

**响应**：`PageResult<AuthorVO>`

### 3.2 POST `/admin-api/ops/author/create`

**请求体** `AuthorCreateReq`：

```json
{
  "authorName": "李四",
  "ipGroupId": 11,
  "authorType": "SHORT_VIDEO",
  "primaryAccountId": 101,
  "userId": 200,
  "status": 1
}
```

**响应**：`Long`（新 ID）

**业务校验**：

- `ipGroupId` 必须指向 SMALL 类型 → 1101
- `primaryAccountId` 必须存在且 `type=OFFICIAL_ACCOUNT` → 1102
- `primaryAccountId` 已被其他作者绑定为主推号 → 1103

### 3.3 PUT `/admin-api/ops/author/update`

**请求体** `AuthorUpdateReq`：含 `id` 字段

### 3.4 DELETE `/admin-api/ops/author/delete`

**请求参数**：`id` (Long)

**业务规则**：

- 作者存在未完成任务 → 1104 "该作者下存在未完成任务，无法删除"

### 3.5 GET `/admin-api/ops/author/{id}/dashboard`

获取作者数据看板。

**响应** `AuthorDashboardVO`：

```json
{
  "authorId": 50,
  "authorName": "李四",
  "ipGroupName": "娱乐八卦大组/八卦一组",
  "followerCount": 100000,
  "followerTrend": [...],
  "contentStats": {
    "totalCount": 50,
    "hitCount": 5,
    "avgRead": 10000
  },
  "liveStats": {
    "totalHours": 120.5,
    "totalSessions": 30
  },
  "orderAttribution": {
    "totalRevenue": 50000.00,
    "roi": 3.2
  }
}
```

### 3.6 GET `/admin-api/ops/ops-anchor/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| opsUserId | Long | ❌ | 运营用户 ID |
| anchorUserId | Long | ❌ | 主播用户 ID |
| page | int | ❌ | 默认 1 |
| size | int | ❌ | 默认 20 |

**响应**：`PageResult<OpsAnchorRelVO>`

### 3.7 POST `/admin-api/ops/ops-anchor/create`

**请求体**：

```json
{
  "opsUserId": 200,
  "anchorUserId": 300,
  "ipGroupId": 11,
  "startDate": "2026-06-01",
  "endDate": "2026-12-31"
}
```

**响应**：`Boolean`

**业务规则**：

- 同一 (opsUserId, anchorUserId) 不能有重叠的日期段 → 1201

### 3.8 PUT `/admin-api/ops/ops-anchor/update`

### 3.9 DELETE `/admin-api/ops/ops-anchor/delete`

**请求参数**：`opsUserId`, `anchorUserId`

### 3.10 GET `/admin-api/ops/author/{id}/ops-list`

获取某作者关联的所有运营人员。

**响应**：`List<OpsUserVO>`

### 3.11 GET `/admin-api/ops/ops/{userId}/anchor-stats`

获取某运营人员服务的主播统计。

**响应** `OpsAnchorStatsVO`：

```json
{
  "opsUserId": 200,
  "opsUserName": "王五",
  "anchorCount": 5,
  "totalFollower": 500000,
  "totalContent": 200,
  "totalRevenue": 100000.00
}
```

---

## 4. 账号分析 / 粉丝 / 作品 / 内部内容 / 人效 API

> 此处仅列 API 摘要，详细 DTO 见 `docs/engineering/DTO-M1-运营管理.md`（如需展开）。**所有接口均沿用通用约定**。

### 4.1 账号分析（FR-M1-003）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/account-analysis/list` | 账号列表（按 platform Tab 切换） |
| GET | `/admin-api/ops/account-analysis/{id}/followers` | 账号粉丝详情 |
| GET | `/admin-api/ops/account-analysis/{id}/contents` | 账号作品详情 |
| POST | `/admin-api/ops/account-analysis/export` | 导出账号列表（异步） |

**`/list` 关键参数**：`platform`（枚举：WECHAT_OFFICIAL / WECHAT_VIDEO / DOUYIN / KUAISHOU / XIAOHONGSHU / WECHAT_SERVICE / WEWORK / WX_PERSONAL / ALL）、`ipGroupId`、`keyword`、`accountStatus`、`realnameId`、`operatorUserId`、`page`、`size`

**M10 采集桥接（ADR-049）**：Channel-A 五平台列表/详情合并 `CollectedDataQueryService` 读取的 M10 表；响应项可含 `dataSource=COLLECT`。粉丝/作品数优先采集快照，否则回退 `oa_account_status_log` / 补录表。

### 4.2 粉丝分析（FR-M1-004）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/follower-analysis/list` | 粉丝列表 |
| GET | `/admin-api/ops/follower-analysis/trend` | 粉丝趋势 |
| POST | `/admin-api/ops/follower-analysis/export` | 导出 |

**`/list` 关键参数**：`startDate`、`endDate`、`ipGroupId`、`accountId`、`platformType`、`timeDimension (DAY/WEEK/MONTH)`、`page`、`size`

**`/trend` 关键参数**：同 `/list`，返回 `List<FollowerTrendVO>` 含 `timePeriod, accountName, ipGroupName, followerCount, newFollower, unfollowCount, netGrowth, growthRate`

### 4.3 作品分析（FR-M1-005）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/content-analysis/list` | 作品列表 |
| GET | `/admin-api/ops/content-analysis/trend` | 作品数据趋势（按日） |
| GET | `/admin-api/ops/content-analysis/stats` | 汇总统计 |
| POST | `/admin-api/ops/content-analysis/export` | 导出 |

**`/list` 关键参数**：`startDate`、`endDate`（可选；空=全量）、`ipGroupId`、`accountId`、`platformType`、`contentType`、`keyword`、`isHit`、`page`、`size`

**`/trend` 关键参数**：`contentId`（必填）、`startDate`、`endDate`（详情弹窗传入；默认近 7 日）

**`isHit` 字段** 命中 BR-003 阈值规则计算。

**UI 默认**（2026-06-11）：列表 `dateRange` 默认空；详情趋势默认 7 日。

### 4.4 内部内容分析 + 数据补录（FR-M1-006）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/internal-content/list` | 内部作品列表 |
| GET | `/admin-api/ops/internal-content/{id}/trend` | 趋势（抽屉默认近 7 日） |
| POST | `/admin-api/ops/internal-content/export` | 导出 |
| **POST** | **`/admin-api/ops/internal-content/import`** | **数据补录（v9.1 新增）** |
| GET | `/admin-api/ops/internal-content/import/list` | 补录记录列表 |
| GET | `/admin-api/ops/internal-content/import/{id}` | 补录详情 |
| PUT | `/admin-api/ops/internal-content/import/{id}/review` | 审核补录 |

**`/list` 关键参数**：`startDate`、`endDate`（可选；前端默认不传=全量）、`ipGroupId`、`keyword`、`platformType`、`contentType`、`page`、`size`

**M10 采集桥接（ADR-049）**：Channel-A 五平台合并 M10 作品/笔记表；`dataSource=COLLECT` 标识采集来源；补录审核数据仍按 ADR-M1-001 合并。

**补录请求体** `ImportContentDataReq`：

```json
{
  "contentId": 500,
  "statDate": "2026-05-30",
  "importType": "API_EXCEPTION",
  "readCount": 8000,
  "likeCount": 200,
  "commentCount": 50,
  "forwardCount": 30,
  "followerChange": 100,
  "remark": "5月30日平台接口异常"
}
```

**补录业务校验**：

- statDate 距今 > 90 天 → 1301 "仅可补录过去 90 天内的数据"
- contentId 不存在或已删除 → 1302
- 该 content+date 已有"已通过"补录 → 1303 "该作品当日已存在已审核的补录"

**审核请求体** `ImportReviewReq`：

```json
{
  "reviewStatus": 1,
  "remark": "数据确认无误"
}
```

**`reviewStatus` 枚举**：

| 值 | 含义 | 后续可改 |
|----|------|----------|
| 1 | 审核通过 | ❌ 不可改/删 |
| 2 | 审核不通过 | ✅ 补录人修改后重提 |

### 4.5 人效盘点（FR-M1-007）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/productivity-review/list` | 人效列表 |
| GET | `/admin-api/ops/productivity-review/detail/{userId}` | 单人展开详情 |
| GET | `/admin-api/ops/productivity-review/detail/anchors` | 主播详情 |
| POST | `/admin-api/ops/productivity-review/export` | 导出 |

**`/list` 关键参数**：`startDate`、`endDate`、`ipGroupId`、`userId`、`timeDimension (week/month)`、`page`、`size`

---

## 5. 错误码

| 错误码 | 含义 | 关联 FR |
|--------|------|---------|
| 1001 | IP 组名称不合法（1-50 字符） | FR-M1-001 |
| 1002 | 同父级下名称重复 | FR-M1-001 |
| 1003 | 上级必须是大组 | FR-M1-001 |
| 1004 | 组长用户不存在 | FR-M1-001 |
| 1005 | 该 IP 组下存在数据，禁止删除 | FR-M1-001 |
| 1006 | 成员存在关联任务，无法删除 | FR-M1-001 |
| 1007 | 账号已属于其他 IP 组 | FR-M1-001 |
| 1008 | 账号仅可关联到小组（SMALL） | FR-M1-001 |
| 1101 | 作者 IP 组必须选择小组 | FR-M1-002 |
| 1102 | 主推号类型必须为 OFFICIAL_ACCOUNT | FR-M1-002 |
| 1103 | 该主推号已被其他作者绑定 | FR-M1-002 |
| 1104 | 作者存在未完成任务，无法删除 | FR-M1-002 |
| 1201 | 运营→主播关联存在重叠日期段 | FR-M1-002 |
| 1301 | 仅可补录过去 90 天内的数据 | FR-M1-006 |
| 1302 | 作品不存在或已删除 | FR-M1-006 |
| 1303 | 该作品当日已存在已审核的补录 | FR-M1-006 |
| 1304 | 已审核的补录不可修改/删除 | FR-M1-006 |
| 1401 | 导出任务创建失败（系统异常） | 通用 |
| 1402 | 导出数据量超限（>10w 行） | 通用 |

---

## 6. 鉴权

- 每个接口均需登录态（`Authorization` Bearer token）
- 接口级权限校验由 `@PreAuthorize` 注解控制，权限点见 `PRD § 2.1`
- 越权 → 403

---

## 7. 数据契约

### 7.1 必填与可空

- 所有 DTO 字段使用 `@NotNull/@NotBlank/@NotEmpty` 校验
- 详见各 Controller 的 `@Valid` 注解

### 7.2 数值精度

- 金额：`BigDecimal`，保留 2 位小数
- 比率：`*100` 存整数百分比，DTO 上注明单位（%）
- 粉丝/作品数：Integer
- ID：Long

### 7.3 时间字段

- 客户端 → 服务端：`yyyy-MM-dd HH:mm:ss` 或 ISO-8601
- 服务端 → 客户端：ISO-8601 (`2026-06-07T15:00:00+08:00`)

---

## 8. 异步导出约定

- `POST /*/export` 同步返回 `taskId`
- 前端通过 `GET /admin-api/ops/common/export-task/{taskId}` 轮询状态
- 状态：`PENDING` / `RUNNING` / `SUCCESS` / `FAILED`
- `SUCCESS` 时返回 `downloadUrl`（带签名，5 分钟有效）
- `FAILED` 时返回 `errorMessage`

---

*下一步：基于本 API 规格生成 SLICES（`docs/delivery/SLICES-M1-运营管理.md`）。*


---

## 🔴 M1 全局规范补丁（2026-06-07）

> 本模块必须严格遵循 [`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md) 的三大铁律。

### 三大铁律（必查）

#### 铁律一：关联属性必须用"选择器"，禁止手动填写

M1 中所有 `*_id` 字段必须通过选择器：

| 字段 | 选择器 |
|------|--------|
| `ip_group_id` | `<IpGroupTreeSelect />` |
| `parent_id` | `<IpGroupTreeSelect />` |
| `account_id` | `<AccountSelect />`（**强关联** ⭐，需从 M4 选择） |
| `author_id` | `<UserSelect />` |
| `assignee_id` | `<UserSelect />` |
| `anchor_user_id` | **作者选择器**（`author_user.id`） |
| `ops_user_id` | `<UserSelect />` |
| `metric_id` | `<MetricSelect />` |

#### 铁律二：枚举属性（方式/状态/类型/平台）必须从数据字典选择

| 字段 | 字典 type |
|------|----------|
| `platform_type` | `dict_platform_type` |
| `account_type` | `dict_account_type` |
| `account_status` | `dict_account_status` |
| `ip_group_type` | `dict_ip_group_type` |
| `ip_group_status` | `dict_ip_group_status` |
| `level` | `dict_ip_group_level` |
| `author_type` | `dict_author_type` |
| `author_status` | `dict_author_status` |
| `content_type` | `dict_content_type` |
| `import_type` | `dict_content_import_type` |
| `data_source` | `dict_data_source` |
| `position` | `dict_position` |
| `is_primary` | `dict_yes_no` |
| `need_review` | `dict_yes_no` |
| `is_public` | `dict_yes_no` |

#### 铁律三：实体关系必须在 ER 图中明确

所有跨实体的关联已在 `PRD-M1-运营管理.md § 5 集成与数据` 中明确。

### 与 M4 账号管理的关键关联

M1 中所有平台账号必须通过 M4 的"实名人/手机/手机卡/公司"选择：

```
M1 IP 组 → M1 账号 → M4 实名人（强关联）
                     → M4 手机（强关联）
                     → M4 手机卡（强关联）
                     → M4 公司（强关联）
```

**校验**：
- 已停用实名人/手机/手机卡 不可被新账号引用（错误码 1501）
- 已绑定到其他账号的实名人/手机/手机卡 需"强制替换"（错误码 1502）
- 跨租户过滤（错误码 1504）

### 错误码

| 错误码 | 含义 |
|--------|------|
| 1500 | 关联的实体不存在 |
| 1501 | 关联的实体已停用/注销 |
| 1502 | 关联的实体已被其他记录引用 |
| 1503 | 字典值不合法 |
| 1504 | 跨租户访问禁止 |

详见 [`GLOBAL-CONVENTIONS.md § 5.3`](../engineering/GLOBAL-CONVENTIONS.md)

---

*补丁完成：M1 全套文档（M0/M1/M2/M3/M4/M5/M6/M7/M8/M9/M10）已统一遵循全局规范。*

## 强关联字段 → 选择器映射（🔴 API 必含）

本模块涉及以下强关联字段，**前端必须使用对应选择器组件**：

| 字段 | 选择器组件 | 关联实体 | 错误码 |
|------|----------|---------|--------|
| `realnameId` | `<RealNameSelect />` | 实名人 | 1501 / 1504 |
| `intermediaryId` | `<RealNameSelect />` | 中介人 | 1501 / 1504 |
| `accountId` | `<AccountSelect />` | 平台账号 | 1501 / 1504 |
| `authorId` | `<RealNameSelect />` (或作者专用选择器) | 作者 | 1501 / 1504 |
| `phoneId` | `<PhoneSelect />` | 手机 | 1501 / 1504 |
| `simCardId` | `<SimCardSelect />` | 手机卡 | 1501 / 1504 |
| `companyId` | `<CompanySelect />` | 公司 | 1501 / 1504 |
