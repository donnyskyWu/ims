# API-M2-工作任务管理

> **FR**：FR-M2-010  
> **PRD**：[`PRD-M2-工作任务管理.md`](../product/PRD-M2-工作任务管理.md) v0.8  
> **ADR**：[ADR-074](../adr/ADR-074-工作任务登记SOP全节点生成与营销计划绑定.md) · ADR-072 · [ADR-077](../adr/ADR-077-SOP内容生成节点文档类型与登记自动草稿AI.md) · [ADR-078](../adr/ADR-078-工作任务确认登记钉钉提醒执行人.md) · [ADR-079](../adr/ADR-079-任务完成工作说明与内容审核通过门禁.md) · [ADR-080](../adr/ADR-080-任务节点名称与执行页登记备注.md)  
> **基路径**：`/admin-api/ops/work-task`（前端 `#/api/ops/workTask.ts` 相对路径 `/ops/work-task/**`）
> **版本**：v0.9 | 2026-10-02

---

## 1. 通用约定

| 项 | 规则 |
|----|------|
| 鉴权 | Dev Token + `@PreAuthorize`；Tab1 写 `ops:work-task:register`（DB 过渡期可能仍为 `oa:work-task:*`） |
| 租户 | 全接口 `tenant_id` 隔离（1504） |
| 用户 ID | JSON 传字符串（snowflake）；写入 `FootballSystemUserValidator.resolveStorableUserId`（ADR-056） |
| 错误码 | 1500–1504；营销计划无启用 SOP → **1502** |
| IP 组长组列表 | **非** work-task 路径；见 §2.0 |

---

## 2. 登记 Sheet

### 2.0 GET `/admin-api/ops/ip-group/led`

当前用户担任组长的 IP 组列表（`IpGroupController.ledGroups`）。前端 `getLedIpGroups()`；工作任务页 `IpGroupTreeSelect scope="led"`。

~~GET `/led-ip-groups`~~（Spec 草案路径，**实现无**）。

### GET `/sheet/get-or-create`

| 参数 | 类型 | 必填 |
|------|------|------|
| ipGroupId | Long | ✅ |
| workDate | date | ✅ |

响应：`WorkTaskSheetVO`（含 `status`、默认 10 行 `assignments`）。

### PUT `/sheet/save`

保存 DRAFT；全量 rows 覆盖。

**`WorkTaskAssignmentSaveReq`（行）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| rowNo | int | ✅ | |
| competitionIdsJson | array | ✅ | ≥1 项；每项含 competitionId/competitionName/leagueName/matchTime |
| authorId | string | ✅ | author_user.id |
| assigneeId | string | — | **可选**审计；不参与 confirm assignee |
| publishAccountId | long | — | 发布平台账号 `oa_account.id`（V205 · 登记行） |
| workDate | date | ✅ | |
| marketingPlan | string | ✅ | `@InDict dict_marketing_plan_type` |
| isLive | int | ✅ | |
| liveTime | time | △ | isLive=1 时 |
| salesPlatform | string | ✅ | `@InDict dict_sales_platform` |
| competitions | array | △ | 多赛事快照（优先于单行 `competitionId` · ADR-074） |

**校验**：

- author ∈ IP 组 anchors（1501）
- 同一 sheet 内 `(workDate, authorId)` 下 **competitionId 不可跨行重复**（1502）

### POST `/sheet/confirm`

确认登记；sheet 须 `DRAFT`。

**请求体** `WorkTaskSheetIdReq`：

```json
{
  "sheetId": 123,
  "assignmentIds": [1001, 1002]
}
```

- `assignmentIds`：**必填**非空；仅对选中行生成/确认任务（行级 confirm）

**流程（ADR-074）**：

1. 校验行必填 + 字典 + IP 组范围  
2. 按行 `marketingPlan` → `SopTemplateService.getEnabledByMarketingPlan`（无 → 1502）  
3. 加载 SOP 节点（DAG 序）  
4. 每节点：`assigneeId = PlanTaskGeneratorService.resolveAssignee(executorRole, ipGroupId, tenantId)`  
5. 创建 `oa_task`（`plan_id=null`，`competition_ids_json` 复制行，`work_task_assignment_id` 写入，**`documentType` 自节点拷贝**）  
6. `CONTENT_GENERATION`：同 TX 创建 1 条 DRAFT 内容（`task_id` 1:1，`title=plan_name`，正文可空，ADR-077）  
7. 写入 `oa_work_task_assignment_task`  
8. sheet → `CONFIRMED`  
9. **afterCommit**（非本响应）：并行入队 jingcai；**禁止**在 confirm TX 内同步 jingcai  
10. **afterCommit**（非本响应 · ADR-078）：`notifyWorkTasksPending(tenantId, createdTasks)` — 对每条新 PENDING task 的 `assigneeId` 发 `TASK_PENDING`（站内 + 钉钉）。**禁止**调用 `notifyPlanStarted`（`plan_id` 为 null）。**禁止**在 confirm TX 内同步打钉钉。

**侧效应**：confirm HTTP **立即**成功。jingcai 失败不回滚 sheet；内容 `aiGenerateStatus=FAILED`。钉钉/站内失败 **不**回滚 confirm（ADR-078 D7）。响应 **不**新增字段。  
`TASK_PENDING`：`biz_key=task:{id}:PENDING`；每 task 一条（同一 assignee 多节点多条）；跳转 `/production/task`。withdraw **不** un-notify。

**响应**：

```json
{
  "sheetId": "123",
  "generatedTaskCount": 42,
  "confirmedAt": "2026-08-31T10:00:00"
}
```

`generatedTaskCount` = Σ(行数 × 对应 SOP 节点数)。

### POST `/sheet/withdraw`

请求体同 confirm（`sheetId` + `assignmentIds`）。

| 条件 | 行为 |
|------|------|
| sheet.status = CONFIRMED | 允许 |
| 关联 task 存在 IN_PROGRESS/COMPLETED | **1502** 禁止 |

行为：取消未完成自动生成 Job；**删除**关联 `DRAFT` 内容（ADR-077 D13）；选中行关联 `oa_task` → `CANCELLED` + `visible_in_list=0`；删 assignment_task 关联；未确认行保持 DRAFT。

### POST `/sheet/merge-execution`

请求体：`WorkTaskSheetIdReq`。将选中登记行并入同一 **执行合并组**（同营销计划 + 同作者；confirm 后共享任务集）。响应：`WorkTaskSheetVO`（行上 `executionGroupId` / `executionGroupIndex`）。

### POST `/sheet/unmerge-execution`

取消合并组（请求体同上）。

---

## 3. 矩阵与执行视图

### GET `/matrix`

参数（与 `WorkTaskController.getMatrix` 一致）：`workDate` · `dateFrom` · `dateTo` · `ipGroupIds[]`（**无** `authorIds` 服务端过滤 · 2026-10-02）

响应结构见 PRD §4.3 `WorkTaskMatrixVO`。多赛事行：`matchName` 可为首场或「N 场」摘要。

### GET `/execution`

Tab「任务执行情况」：按赛事/营销计划/日期/IP 组筛选，返回 `List<WorkTaskExecutionRowVO>`（SOP 节点粒度：`nodeName`、`assigneeName`、`publishAccountName`、`status`、计划时段等）。

### GET `/matrix/summary`

区间统计：各作者任务数、营销计划分布、红黑分布。

### POST `/assignment/{id}/refresh-win-prediction`

人工改判红黑（`win_prediction_source=MANUAL`）；见 ADR-072。

---

## 4. SOP 模板扩展（FR-M2-001 · ADR-074 D2）

SOP CRUD 基路径：`/admin-api/ops/sop/template`（见 [`API-M2-内容生产.md`](./API-M2-内容生产.md) §1）

| 字段 | 说明 |
|------|------|
| marketingPlan | `@InDict dict_marketing_plan_type`；**启用时必填** |
| 唯一 | 同租户 **启用态** `marketing_plan` 唯一（1502） |
| 节点 `documentType` | `@InDict dict_document_type`；**仅** `nodeType=CONTENT_GENERATION` 必填（缺/非法 → **1503**，ADR-077） |

---

## 5. 字典

### `dict_marketing_plan_type`（v0.4）

| value | label |
|-------|-------|
| KUAISHOU_PAID_COURSE | 快手付费课程 |
| COMPANY_PAID | 公司平台付费 |
| FREE_PUBLIC | 免费公推 |

### `dict_document_type` / `dict_ai_generate_status`（ADR-077）

五值文档类型见 ADR-016。`dict_ai_generate_status`：`QUEUED` / `GENERATING` / `SUCCESS` / `FAILED`（落在内容表，不落付费墙列）。

---

## 6. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-08-31 | 初稿：ADR-074 confirm/withdraw · 多赛事 · SOP marketing_plan |
| 2026-09-02 | ADR-077：节点/task `documentType` · confirm 建 DRAFT + afterCommit jingcai · withdraw 删草稿 |
| 2026-09-03 | ADR-078：confirm afterCommit 对每条新 task 的 assignee 发 `TASK_PENDING`；失败不回滚 |
| 2026-09-03 | ADR-079：任务完成规则见 `API-M2-内容生产` `complete` / `execute/complete`（工作说明 / 内容审核通过） |
| 2026-09-03 | ADR-080：`TaskVO`/`TaskExecuteVO.nodeName` = SOP `node_name`；execute 增加登记备注四字段（见 `API-M2-内容生产` §2.6） |
| 2026-09-04 | ADR-080：`TaskExecuteVO.workTaskRemark` 每场一段 `赛事-营销计划标签-是/否（时间）-销售平台标签；` |
| 2026-10-02 | 基路径 `/admin-api/ops/work-task`；`led` → `/ops/ip-group/led`；confirm/withdraw 行级 `assignmentIds`；`merge/unmerge-execution`；GET `/execution`；`publishAccountId`（V205） |
