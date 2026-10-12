# API-M0-首页

> **版本**：v1.1 | 2026-06-11 | 2026-10-02
> **关联 PRD**：[`PRD-M0-首页.md`](../product/PRD-M0-首页.md)
> **关联 UX**：[`UX-M0-首页.md`](../product/UX-M0-首页.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)
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

见 `TECH-CONSTRAINTS.md § 1`。所有接口遵循统一响应格式、分页约定、Header 要求。

---

## 2. 首页 API

### 2.1 GET `/admin-api/ops/dashboard/home/metrics`

获取首页 4 个核心指标。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| ipGroupId | Long | ❌ | IP 组筛选；null=全部 | 必须存在且启用 + 用户有权限 |
| startDate | Date | ❌ | 开始日期 | 默认今日 |
| endDate | Date | ❌ | 结束日期 | 默认今日 |

**响应** `HomeMetricsVO`：

```json
{
  "totalAuthors": 123,
  "totalContent": 4567,
  "sopCompletionRate": 87.50,
  "avgPerfGrade": "A"
}
```

**字段**：

| 字段 | 类型 | 数据来源 | 计算 |
|------|------|----------|------|
| totalAuthors | Integer | `oa_author` | COUNT(DISTINCT id) WHERE status=1 AND ip_group_id IN (用户权限范围) |
| totalContent | Integer | `oa_content` | COUNT(*) WHERE publish_time BETWEEN ? AND ? |
| sopCompletionRate | Decimal(5,2) | `oa_task` | SUM(CASE WHEN status='DONE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)，0~100 |
| avgPerfGrade | String | `oa_perf_record` | AVG(score) → S(≥90)/A(80-89)/B(70-79)/C(60-69)/D(<60)；无数据时显示 "-" |

**权限**：所有登录用户，按 BR-006 过滤数据范围。

---

### 2.2 GET `/admin-api/ops/dashboard/home/trend`

获取内容发布趋势。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| ipGroupId | Long | ❌ | IP 组筛选 | 同上 |
| startDate | Date | ❌ | 开始日期 | 默认近 7 天 |
| endDate | Date | ❌ | 结束日期 | 默认今日 |
| platformType | String | ❌ | 平台筛选 | `@InDict(type="dict_platform_type")` |
| type | String | ❌ | 趋势类型：CONTENT（内容）/ FOLLOWER（粉丝） | 默认 CONTENT |
| groupBy | String | ❌ | 分组维度：PLATFORM / IP_GROUP | 默认 PLATFORM |

**响应** `List<TrendPointVO>`：

```json
[
  { "date": "2026-06-01", "count": 120, "platform": "WECHAT_OFFICIAL" },
  { "date": "2026-06-01", "count": 80, "platform": "DOUYIN" },
  { "date": "2026-06-01", "count": 45, "ipGroupId": 101, "ipGroupName": "八卦一组" }
]
```

**字段说明**：

| 字段 | 条件 | 说明 |
|------|------|------|
| platform | `groupBy=PLATFORM` | `dict_platform_type` value |
| ipGroupId / ipGroupName | `groupBy=IP_GROUP` | 账号归属的 IP 小组 |

**IP 组范围**：`ipGroupId` 为大组（`group_type=1`）时，SQL 范围扩展为旗下所有启用小组关联账号；小组仅自身。

**字典值**：`platform` 使用 `dict_platform_type` value，前端展示 label。

**测试数据**：`V39__seed_dashboard_content.sql` 灌入近 7 天 `oa_content` 样本。

---

### 2.3 GET `/admin-api/ops/dashboard/home/platform-dist`

获取平台分布。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ipGroupId | Long | ❌ | IP 组筛选 |
| startDate | Date | ❌ | 开始日期 |
| endDate | Date | ❌ | 结束日期 |

**响应** `List<PlatformDistVO>`：

```json
[
  { "platform": "WECHAT_OFFICIAL", "count": 500, "percentage": 45.50 },
  { "platform": "DOUYIN", "count": 300, "percentage": 27.30 },
  ...
]
```

**校验**：`platform` 必须是 `dict_platform_type` 有效值。

---

### 2.4 GET `/admin-api/ops/dashboard/home/todos`

获取待办提醒。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ipGroupId | Long | ❌ | IP 组筛选 |
| limit | Integer | ❌ | 限制条数，默认 10，最大 50 |

**响应** `List<TodoVO>`：

```json
[
  {
    "title": "SOP《娱乐八卦》待审核",
    "source": "SOP",
    "time": "2026-06-07T10:30:00+08:00",
    "actionUrl": "/ops/sop/review/123"
  },
  ...
]
```

**字典值**：`source` 使用 `dict_alert_type`（`SOP / PUBLISH / PERF / INTEGRATION`）。

**聚合规则**（待产品确认，OQ-M0-002）：
- 优先级：SOP > 发布 > 绩效 > 集成
- 去重：同 SOP 节点只显示 1 条
- 过期任务：超时任务标红

---

### 2.5 GET `/admin-api/ops/dashboard/home/quick-actions`

获取当前用户可见的快捷入口。

**请求参数**：无

**响应** `List<QuickActionVO>`：

```json
[
  {
    "name": "IP 组管理",
    "icon": "icon-ip-group",
    "url": "/ops/ip-group",
    "permission": "oa:ip-group:view"
  },
  ...
]
```

**后端逻辑**：
1. 查询 `sys_menu` 表，过滤 `status=0` 的菜单
2. 校验当前用户拥有该菜单的权限（`@PreAuthorize` 等价）
3. 仅返回用户有权限的菜单（最多 8 个，按 `sort` 升序）
4. 仅返回 `menu_type='MENU'` 且 `is_home_quick_action=1` 的菜单

**配置**：
- 菜单表新增字段 `is_home_quick_action`（TINYINT）
- 通过 `## 9. 系统管理 > 菜单管理` 配置

---

## 3. 缓存

- 首页数据走本地缓存（`ConcurrentHashMap`），key = `userId:ipGroupId:dateRange`
- 缓存 TTL：5 分钟
- 手动刷新 → 清空当前用户缓存
- 数据变更（如新建作者）→ 通过事件总线清空（本期可选，本期不实现）

---

## 4. 错误码

| 错误码 | 含义 |
|--------|------|
| 2001 | IP 组不存在或已停用 |
| 2002 | 日期范围非法（endDate < startDate） |
| 2003 | 平台字典值不合法 |
| 2004 | 趋势类型不合法（仅支持 CONTENT / FOLLOWER） |

---

## 5. 数据契约

- 所有响应字段遵循 `DICT` 规范（`platform` 等枚举字段使用 `dict_platform_type` 的 value）
- 数字字段不允许 null，使用 0 或默认值
- 时间字段使用 ISO-8601

---

## 6. 鉴权

- 5 个接口均需 `@PreAuthorize("hasAuthority('oa:home:view')")` 或类似的宽松权限
- 数据权限过滤：内部 SQL 自动注入 `WHERE ip_group_id IN (用户权限范围)`

---

*下一步：基于本 API 规格生成 SLICES（`docs/delivery/SLICES-M0-首页.md`）。*
