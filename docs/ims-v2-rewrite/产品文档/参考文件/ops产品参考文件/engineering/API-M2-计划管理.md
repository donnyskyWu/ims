# API-M2-计划管理

> **版本**：v1.1 | 2026-08-07 | 2026-10-02  
> **关联 PRD**：[`PRD-M2-内容生产.md`](../product/PRD-M2-内容生产.md) § FR-M2-009  
> **实现**：`ContentPlanController` · `MatchController` · **ADR**：[`ADR-012`](../adr/ADR-012-计划管理任务联动.md) · [`ADR-016`](../adr/ADR-016-M2-节点类型与任务内容关联.md) · [`ADR-070`](../adr/ADR-070-计划多IP组创建.md)

---

## 0. 通用说明

- 基路径：`/admin-api/ops/plan`
- Phase 1 计划写接口**未加**方法级 `@PreAuthorize`（与 M2 其他写接口一致，Gate S2 策略）；租户隔离 + 终止审批岗位校验在 Service 层。
- 终止审批：`approveTerminate` / `rejectTerminate` 要求当前用户 `position=OPS_LEADER`，否则 **403**（`OaErrorCodes.FORBIDDEN`）。

---

## 1. GET `/admin-api/ops/plan/list`

| 参数 | 类型 | 说明 |
|------|------|------|
| planName | String | 模糊 |
| status | String | `dict_plan_status` |
| pageNo | Integer | 默认 1 |
| pageSize | Integer | 默认 20 |

**数据范围**（ADR-064/070）：非租户管理员仅见「关联 IP 组 ∩ 当前用户可访问 IP 组」非空的计划；多 IP 组计划按 junction 表 `oa_content_plan_ip_group` **并集**判定（任一组可访问即可见），兼容仅填主表 `ip_group_id` 的存量行。

**响应** `PageResult<ContentPlanRespVO>` 摘要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| ipGroupId | Long | 主 IP 组（= 创建时 `ipGroupIds[0]`，列表/兼容用） |
| ipGroupName | String | 多组时为各组名以「、」拼接 |
| ipGroupIds | Long[] | 全部关联 IP 组 id（junction 顺序） |
| ipGroupNames | String[] | 与 `ipGroupIds` 对齐 |
| ipGroups | ContentPlanIpGroupVO[] | `{ ipGroupId, ipGroupName }` |

## 2. GET `/admin-api/ops/plan/get?id=`

返回计划详情 + `competitions` + `steps` + **`tasks`**。

**响应** `ContentPlanRespVO` 在列表摘要字段基础上含：

| 字段 | 类型 | 说明 |
|------|------|------|
| tasks | TaskVO[] | 计划下全部任务（含草稿 `PLAN_DRAFT`） |
| tasks[].ipGroupId | Long | 任务所属 IP 组 |
| tasks[].ipGroupName | String | IP 组名称 |
| tasks[].scheduledStart / scheduledEnd | DateTime | 计划排期 |
| tasks[].executorRole | String | SOP 节点执行岗位 |

**ContentPlanIpGroupVO**：`{ ipGroupId, ipGroupName }`。

## 3. POST `/admin-api/ops/plan/create`

```json
{
  "planName": "6月内容计划",
  "templateId": 9401,
  "ipGroupIds": [9001, 9002],
  "startDate": "2026-06-01",
  "endDate": "2026-06-30",
  "description": "...",
  "competitions": [{ "competitionId": "123456789", "competitionName": "英超-曼联 VS 切尔西-2026-06-12 20:00" }],
  "steps": [
    {
      "nodeId": 9401,
      "competitionId": "123456789",
      "competitionIds": ["123456789", "987654321"],
      "assigneeIds": [1003],
      "scheduledStart": "2026-06-01 00:00:00",
      "scheduledEnd": "2026-06-30 23:59:59"
    }
  ],
  "tasks": [
    {
      "nodeId": 9401,
      "competitionId": "123456789",
      "ipGroupId": 9001,
      "assigneeId": 1003,
      "scheduledStart": "2026-06-11 20:00:00",
      "scheduledEnd": "2026-06-12 20:00:00"
    }
  ]
}
```

**IP 组字段**（ADR-070）：

| 字段 | 类型 | 说明 |
|------|------|------|
| ipGroupIds | Long[] | **推荐**；≥1；去重后写入 junction 表 |
| ipGroupId | Long | **兼容**单 IP 组；与 `ipGroupIds` 二选一，`ipGroupIds` 优先 |

落库：`oa_content_plan.ip_group_id` = `ipGroupIds[0]`（列表/兼容）；完整集合在 `oa_content_plan_ip_group`。

**规则**：
- 须覆盖模板**全部**节点（缺一报错 1500）
- 每 step 须 `competitionIds`（≥1）或兼容字段 `competitionId`；均须属于 `competitions` 列表
- 每节点 `assigneeIds` **长度=1**（UI 单选执行人）；须本租户有效用户且在**所选 IP 组并集**的成员或组长内（1501，ADR-066）
- **步骤模式**（无 `tasks` 或 `tasks` 为空）：对每个 `(ipGroupId × assigneeId × competitionId)` 生成一条 `oa_task`
- **任务模式**（传 `tasks`，优先）：须覆盖模板全部节点；**多 IP 组时**每条 task **必填** `ipGroupId` 且须属于计划 IP 组集合；执行人须为该 task 所属 IP 组成员或组长
- `templateId` / 各 `ipGroupId` 须同租户（1501 / 1504）
- `endDate` 不得早于 `startDate`
- `scheduledStart` / `scheduledEnd` 可选；缺省为计划起止日 00:00:00 / 23:59:59

**响应**：`CommonResult<Long>`（计划 id）

## 4. PUT `/admin-api/ops/plan/update`

**仅草稿（`DRAFT`）可编辑**；非草稿 → **2023**。

**请求体** `ContentPlanUpdateReq`（**不可改** `templateId` / IP 组集合，沿用创建时 junction 与主表 `ip_group_id`）：

```json
{
  "id": 1001,
  "planName": "6月内容计划（修订）",
  "startDate": "2026-06-01",
  "endDate": "2026-06-30",
  "description": "...",
  "competitions": [{ "competitionId": "123456789", "competitionName": "英超-曼联 VS 切尔西-2026-06-12 20:00" }],
  "steps": [
    {
      "nodeId": 9401,
      "competitionId": "123456789",
      "competitionIds": ["123456789", "987654321"],
      "assigneeIds": [1003],
      "scheduledStart": "2026-06-01 00:00:00",
      "scheduledEnd": "2026-06-30 23:59:59"
    }
  ]
}
```

**规则**（与 create 步骤/赛事部分一致）：
- 须覆盖模板**全部**节点（缺一报错 1500）
- 每 step `competitionIds` 必填（≥1），且均须属于 `competitions` 列表（1500）
- 每节点 `assigneeIds` 长度=1；执行人须本租户有效用户且在**创建时锁定的 IP 组并集**内（1501）
- 多 IP 组 + `tasks` 模式：每条 task 仍须带有效 `ipGroupId`（同 create）
- `endDate` 不得早于 `startDate`（1503）
- 更新时级联替换计划赛事、步骤及关联 `PLAN_DRAFT` 任务；**不**修改 `oa_content_plan_ip_group`

**响应**：`CommonResult<Boolean>`

## 5. POST `/admin-api/ops/plan/{id}/start`

草稿 → 进行中；计划任务 `PLAN_DRAFT` → `PENDING`，`visible_in_list=1`。

## 6. POST `/admin-api/ops/plan/{id}/terminate`

进行中 → 终止审批中（`TERMINATE_PENDING`）。

**请求体**（可选）`ContentPlanTerminateReq`：

```json
{ "reason": "赛事取消" }
```

非进行中状态 → **2023**。

## 7. POST `/admin-api/ops/plan/{id}/terminate/approve`

仅 `position=OPS_LEADER`；计划与关联任务 → `TERMINATED`。

## 8. POST `/admin-api/ops/plan/{id}/terminate/reject`

终止审批中 → 进行中（`IN_PROGRESS`）。仅 `OPS_LEADER`。

## 9. DELETE `/admin-api/ops/plan/delete?id=`

仅草稿可删；非草稿 → **2023**。级联删除计划赛事/步骤、junction 行及关联 `oa_task`。

---

## 10. POST `/admin-api/ops/plan/preview-tasks`

创建向导内按模板 + 赛事预览任务清单（不写库）。对每个所选 IP 组分别按 SOP 节点 × 赛事生成预览行。

**请求体** `ContentPlanPreviewTasksReq`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| templateId | Long | ✅ | SOP 模板 |
| ipGroupIds | Long[] | △ | 多 IP 组；与 `ipGroupId` 二选一 |
| ipGroupId | Long | △ | 兼容单 IP 组 |
| matches | ContentPlanPreviewMatchReq[] | ✅ | `{ competitionId, competitionName, matchTimeRaw? }` |

**响应** `ContentPlanTaskPreviewVO[]`（按 ipGroupId → competitionId → nodeOrder 排序）：

| 字段 | 说明 |
|------|------|
| ipGroupId / ipGroupName | 预览所属 IP 组 |
| nodeId / nodeName / nodeOrder / executorRole | SOP 节点 |
| competitionId / competitionName | 赛事 |
| assigneeId / assigneeName | 按节点 `executor_role` 匹配 IP 组成员岗位；无匹配回退 IP 组长 |
| assigneeFallback | 是否因岗位无匹配回退组长 |
| positionWarning | 组内无对应岗位时的提示文案 |
| scheduledStart / scheduledEnd | 默认「开赛前 24h」至开赛时刻（`matchTimeRaw` 缺省则估算） |

---

## 11. 任务执行上下文（多 IP 组 Tab）

计划任务进入执行页时，[`API-M2-内容生产`](API-M2-内容生产.md) §2.6 `GET /admin-api/ops/task/{id}/execute` 响应 `TaskExecuteVO` 额外携带：

| 字段 | 类型 | 说明 |
|------|------|------|
| ipGroupId / ipGroupName | Long / String | 当前任务所属 IP 组 |
| ipGroupTabs | TaskExecuteIpGroupTabVO[] | 同计划、同节点、同赛事的**各 IP 组并行任务** Tab；仅当 sibling 数 > 1 时非空 |

**TaskExecuteIpGroupTabVO**：`{ taskId, ipGroupId, ipGroupName, status, linkedContent? }` — 用于执行页切换查看各组进度与关联内容。

---

## 12. 错误码

| 码 | 场景 |
|----|------|
| 1501 | 模板/IP 组/执行人不存在 |
| 1504 | 跨租户 |
| 403 | 非运营组长审批终止 |
| 2023 | 计划状态不允许（启动/终止/删除/编辑） |

---

## 13. 外部赛事代理（BLK-M2-004 已决）

> 前端**禁止**直连外部域名（CORS）；统一经本模块后端转发。外部 API **无 tenant**，代理层不做租户过滤。

### 13.1 GET `/admin-api/ops/match/list`

| 参数 | 类型 | 说明 |
|------|------|------|
| date | String | 比赛日期 `yyyy-MM-dd`，默认当天 |
| pageNo | Integer | 默认 1 |
| pageSize | Integer | 默认 20，最大 200 |
| leagueId | String | 联赛 `sclassId` |
| teamKeyword | String | 主队/客队模糊（服务端过滤） |
| lotteryType | String | 竞彩类型，如 `jc` |

**响应** `PageResult<MatchVO>`：

| 字段 | 来源（外部 `/app-api/match/list`） | 说明 |
|------|-----------------------------------|------|
| scheduleId | scheduleId | 计划/任务 `competitionId` |
| displayName | 拼接 | `{联赛}-{主队} VS {客队}-{matchTime}` |
| sClassId | sclassId | 联赛 ID |
| sClassName | `/filter/competitions/flat` 或 sClassName | 联赛中文名 |
| homeTeamName | homeTeamName | 主队 |
| guestTeamName | guestTeamName | 客队 |
| matchTime | matchTime(ms) | 格式化 `yyyy-MM-dd HH:mm` |
| matchTimeRaw | matchTime | 原始毫秒时间戳 |
| lotteryType | lotteryType / 默认 `jc` | 竞彩类型 |

### 13.2 GET `/admin-api/ops/match/leagues`

返回联赛下拉列表（转发 `/filter/competitions/flat`）。

| 字段 | 外部字段 |
|------|---------|
| id | sclassId |
| name | nameZh |
| nameEn | nameEn |
| shortName | shortName |

**配置**（`application-*.yml`）：

```yaml
oa:
  match:
    api-base-url: https://h5.shenyu.com/app-api/match
    headers: {}   # 可选，外部 API 鉴权头
```

**前端**：`src/api/match.ts` · `MatchSelectDialog.vue` · 计划页 `plan/index.vue`。