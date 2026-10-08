# API-M2-内容生产

> **版本**：v1.7 | 2026-10-02
> **关联 PRD**：[`PRD-M2-内容生产.md`](../product/PRD-M2-内容生产.md)
> **关联 UX**：[`UX-M2-内容生产.md`](../product/UX-M2-内容生产.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---

## 0. 路径 SSOT（2026-10-02）

| 模块 | 规范前缀 | Controller 示例 |
|------|----------|-----------------|
| 内容 | `/admin-api/ops/content/**` | `ProductionContentController`（list `pageNum`/`pageSize`；`GET /by-task` 先于 `/{id}`） |
| SOP/任务 | `/admin-api/ops/sop/**`、`/admin-api/ops/task/**` | `SopTemplateController`、`TaskController` |
| 工作任务 | [`API-M2-工作任务管理.md`](./API-M2-工作任务管理.md) | `/admin-api/ops/work-task/**` |
| Football 方案 / 上下架 | §3.8（ADR-054） | `football-scheme` · `shelf-on/off` |
| 排版 | [`API-M2-AI排版增量.md`](./API-M2-AI排版增量.md) | `/typeset` · `/typeset/ai-semantic/*` |

正文 HTTP 路径已与 `football-module-ops` Controller 对齐（前缀 `/admin-api/ops/**`）。个别 **Spec 历史 / 当前未实现** 端点见各节标注。Gateway 过渡双路由见 [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)。

---

## 1. SOP 模板 API

### 1.1 GET `/admin-api/ops/sop/template/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| templateName | String | ❌ | 模糊匹配 |
| contentType | String | ❌ | `dict_content_type` |
| platformType | String | ❌ | `dict_platform_type` |
| status | Integer | ❌ | 0/1 |
| pageNum | Integer | ❌ | 默认 1 |
| pageSize | Integer | ❌ | 默认 20 |

**响应**：`CommonResult<PageResult<SopTemplateVO>>`

**字段**：

```json
{
  "id": 1,
  "templateName": "标准内容生产运营流程",
  "contentType": "ALL",
  "platformType": "ALL",
  "description": "...",
  "status": 1,
  "nodeCount": 14,
  "createdAt": "2026-06-01T10:00:00+08:00"
}
```

**字典**：`contentType` / `platformType` 使用字典 value。

---

### 1.2 POST `/admin-api/ops/sop/template/create`

**请求体** `SopTemplateCreateReq`：

```json
{
  "templateName": "...",
  "contentType": "SHORT_VIDEO",
  "platformType": "DOUYIN",
  "description": "...",
  "status": 1
}
```

**校验**：
- `templateName` `@NotBlank @Size(max=100)`
- `contentType` `@InDict(type="dict_content_type")`
- `platformType` `@InDict(type="dict_platform_type")`
- `description` `@Size(max=500)`

---

### 1.3 PUT `/admin-api/ops/sop/template/update`

**请求体** `SopTemplateUpdateReq`：包含 `id` + 同 create 字段。

---

### 1.4 DELETE `/admin-api/ops/sop/template/{id}`

**响应**：`true`

**业务规则**：
- 若模板被任务引用 → 拒绝删除（错误码 1502）
- 软删除（`status=0`），保留 90 天后物理删除

---

### 1.5 GET `/admin-api/ops/sop/node/list?templateId=xxx`

**响应**：`List<SopNodeVO>`

**字段**：

```json
{
  "id": 1,
  "templateId": 1,
  "nodeName": "写推文",
  "nodeOrder": 2,
  "executorRole": "OPS_OFFICIAL",
  "needReview": 1,
  "reviewerRole": "OPS_LEADER",
  "predecessors": [1],
  "parallelGroup": "GROUP_A",
  "slaHours": 24,
  "nodeType": "CONTENT_GENERATION",
  "documentType": "OFFICIAL_PLAN"
}
```

**字典**：`executorRole` / `reviewerRole` 使用 `dict_position` value；`nodeType` 使用 `dict_sop_node_type`（ADR-016：CONTENT_GENERATION / CONTENT_PUBLISH / NORMAL）。`documentType` 使用 `dict_document_type`；**仅** `CONTENT_GENERATION` 必填（ADR-077）。

---

### 1.6 POST `/admin-api/ops/sop/node/create`

**请求体** `SopNodeCreateReq`：

```json
{
  "templateId": 1,
  "nodeName": "写推文",
  "nodeOrder": 2,
  "executorRole": "OPS_OFFICIAL",
  "needReview": 1,
  "reviewerRole": "OPS_LEADER",
  "predecessors": [1],
  "parallelGroup": "GROUP_A",
  "slaHours": 24,
  "nodeType": "NORMAL",
  "documentType": null
}
```

**校验**：
- `nodeName` `@NotBlank @Size(max=50)`
- `nodeType` `@NotBlank @InDict(type="dict_sop_node_type")`
- `documentType`：`nodeType=CONTENT_GENERATION` 时 `@NotBlank @InDict(type="dict_document_type")`（否则 **1503**，ADR-077）；其它节点类型可空
- `executorRole` `@InDict(type="dict_position")`
- `needReview=1` → `reviewerRole` 必填
- `predecessors` → 同模板节点 ID 列表
- `slaHours` ≥ 0
- DAG 合法性（调用 `validate-dag`）

---

### 1.7 PUT `/admin-api/ops/sop/node/update`

同 create 字段 + `id`。

---

### 1.8 POST `/admin-api/ops/sop/node/validate-dag`

**请求体**：

```json
{
  "templateId": 1,
  "nodes": [
    {"id": 1, "predecessors": []},
    {"id": 2, "predecessors": [1]},
    ...
  ]
}
```

**响应**：

```json
{
  "valid": true
}
```

或

```json
{
  "valid": false,
  "cyclePath": [1, 2, 3, 1]
}
```

---

### 1.9 GET `/admin-api/ops/sop/review/pending`

**请求参数**：

| 参数 | 类型 | 必填 |
|------|------|------|
| reviewerId | Long | ❌（默认当前用户） |

**响应**：`List<SopReviewVO>`

---

### 1.10 POST `/admin-api/ops/sop/review/approve`

**请求体**：

```json
{
  "reviewId": 123,
  "comment": "审核通过"
}
```

**业务**：
- 校验当前用户 `position` = `reviewer_role`
- 状态：`PENDING` → `APPROVED`
- 触发后续节点（重新 DAG 计算）

---

### 1.11 POST `/admin-api/ops/sop/review/reject`

**请求体**：

```json
{
  "reviewId": 123,
  "comment": "内容需修改"
}
```

**业务**：
- 状态：`PENDING` → `REJECTED`
- 任务回到 `IN_PROGRESS`

---

## 2. 任务管理 API

### 2.1 GET `/admin-api/ops/task/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ipGroupId | Long | ❌ | IP 组筛选 |
| status | String | ❌ | `dict_sop_node_status` |
| executorId | Long | ❌ | 执行人 |
| startDate | Date | ❌ | 创建时间 |
| endDate | Date | ❌ | - |
| pageNum | Integer | ❌ | - |
| pageSize | Integer | ❌ | - |

**响应**：`PageResult<TaskVO>`

**字段**：

```json
{
  "id": 1,
  "planName": "6月娱乐八卦计划",
  "nodeName": "写推文",
  "ipGroupId": 9001,
  "ipGroupName": "八卦一组",
  "assigneeName": "张三",
  "executorRole": "OPS_OFFICIAL",
  "status": "IN_PROGRESS",
  "slaDeadline": "2026-06-08T18:00:00+08:00"
}
```

**字典**：`executorRole` / `status` 使用字典 value。

---

### 2.2 POST `/admin-api/ops/task/{id}/start`

**业务**：
- 校验当前用户 = `assignee_id`
- 状态：`PENDING` → `IN_PROGRESS`

---

### 2.3 POST `/admin-api/ops/task/{id}/complete`

**请求体**：

```json
{
  "deliverables": "推文草稿 URL"
}
```

**业务**（[ADR-079](../adr/ADR-079-任务完成工作说明与内容审核通过门禁.md)）：
- 校验当前用户 = `assignee_id`；状态须 `IN_PROGRESS`
- `nodeType ≠ CONTENT_GENERATION` → `deliverables` trim 非空，否则 **1500**「请填写工作说明」（字段=`oa_task.deliverables`）
- `nodeType = CONTENT_GENERATION` → 须关联内容且状态 ∈ 审核通过集合（`PENDING_PUBLISH` / `PUBLISHED_DRAFT` / `FORMALLY_PUBLISHED` / `PUBLISHED` / `UNPUBLISHED`），否则 **1500**；**不**要求工作说明
- 状态：`IN_PROGRESS` → `DONE`（`need_review=0`）或 `PENDING_REVIEW`（`need_review=1`）

列表与执行页走 **同一**校验。

---

### 2.4 POST `/admin-api/ops/task/{id}/submit-review`

**业务**：
- 状态：`COMPLETED` 或 `IN_PROGRESS` → `PENDING_REVIEW`
- 创建 `oa_sop_review` 记录
- **ADR-079**：完成门禁与 `complete` 相同（防列表旁路）

---

### 2.5 GET `/admin-api/ops/task/my-tasks`

**业务**：
- 默认查询当前用户被分配的任务
- 包含超时任务（标红）

---

### 2.6 GET `/admin-api/ops/task/{id}/execute`（需求 4–5，✅ S-12）

**响应** `TaskExecuteVO`：

```json
{
  "id": 1,
  "nodeName": "撰写短视频文案",
  "nodeType": "CONTENT_GENERATION",
  "planName": "6月内容计划",
  "ipGroupId": 9001,
  "ipGroupName": "八卦一组",
  "competitionId": "cmp-001",
  "competitionName": "2026 春季城市赛",
  "marketingPlan": "KUAISHOU_PAID_COURSE",
  "isLive": 1,
  "liveTime": "20:00:00",
  "salesPlatform": "PRIVATE,KUAISHOU",
  "workTaskRemark": "英超 · 阿森纳vs切尔西-快手付费课程-是（20:00）-私域、快手；",
  "executionInstruction": "...",
  "attachments": [],
  "linkedContent": { "id": 100, "title": "...", "status": "DRAFT", "documentType": "OFFICIAL_PLAN", "aiGenerateStatus": "GENERATING", "aiGenerateError": null },
  "ipGroupTabs": [
    {
      "taskId": 1,
      "ipGroupId": 9001,
      "ipGroupName": "八卦一组",
      "status": "IN_PROGRESS",
      "linkedContent": { "id": 100, "title": "...", "status": "DRAFT" }
    },
    {
      "taskId": 2,
      "ipGroupId": 9002,
      "ipGroupName": "八卦二组",
      "status": "PENDING"
    }
  ]
}
```

- `nodeName` = `oa_sop_node.node_name`（按 `oa_task.node_id`）；工作任务来源 **不得**用营销计划覆盖（ADR-080）。
- `marketingPlan` / `isLive` / `liveTime` / `salesPlatform`：有关联登记行时 **read-through** 首行（ADR-080）；计划 task 为 null。执行页 **不展示** `slaDeadline`。
- `workTaskRemark`：执行页「备注」SSOT。每条关联登记行一段 `赛事-营销计划标签-是/否（HH:mm 仅直播）-销售平台标签；`（ADR-075 合并组 = 多段）。
- `executionInstruction` 来源 `oa_sop_node.instruction_text`（空则回退 `nodeName`）；`attachments` 来源同表 `attachment_urls` JSON 只读，**无上传 API**（BLK-M2-007 上传仍阻塞）。
- `linkedContent`：内容生成节点关联的内容（0..1）。ADR-077：工作任务 confirm 后通常已存在 DRAFT；含 `documentType` / `aiGenerateStatus` / `aiGenerateError`。
- `ipGroupId` / `ipGroupName`：当前任务所属 IP 组（ADR-070）。
- `ipGroupTabs`：同计划、同节点、同赛事的多 IP 组并行任务 Tab；**仅 sibling 数 > 1 时非空**（详见 [API-M2-计划管理 §11](API-M2-计划管理.md)）。
- **列表** `GET /task/list` · `/my-tasks` 的 `TaskVO` 另含 `nodeType` + `linkedContent`（至少 `id`/`status`），供 ADR-079 按钮显隐。

### 2.7 POST `/admin-api/ops/task/{id}/execute/save`（✅ S-12）

保存执行页草稿（交付说明等，字段待 BLK 定稿）。

### 2.8 POST `/admin-api/ops/task/{id}/execute/complete`（需求 5，✅ S-12 · ADR-079）

**请求体**（可选，与 `complete` 对齐）：

```json
{
  "deliverables": "工作说明"
}
```

**业务**：
- 校验当前用户 = `assignee_id`；状态须 `IN_PROGRESS`
- 门禁与 `POST /task/{id}/complete` **相同**（ADR-079）：非内容生成须工作说明；内容生成须关联内容审核通过
- `deliverables`：本次 body 非空则写入；否则用已存 `oa_task.deliverables`
- 状态：`IN_PROGRESS` → `DONE`（`need_review=0`）或 `PENDING_REVIEW`（`need_review=1`）

---

## 3. 内容管理 API

### 3.1 GET `/admin-api/ops/content/list`

**请求参数**：

| 参数 | 类型 | 字典 |
|------|------|------|
| title | String | - |
| platformType | String | `dict_platform_type` |
| contentType | String | `dict_content_type` |
| accountId | Long | `oa_account` |
| status | String | `dict_content_status` |
| aiGenerated | Integer | `dict_yes_no` |
| pageNum / pageSize | Integer | - |

**数据范围**（BR-006）：非 ALL 权限用户自动过滤为「本人关联内容」——创建者、绑定作者、任务指派人在数据范围用户集内；审核队列状态 + 具备审核列表权限时不过滤（一级审核无全量时仍限本 IP 组）。

---

### 3.2 POST `/admin-api/ops/content/create`

**请求体** `ContentCreateReq`：

```json
{
  "title": "...",
  "contentType": "SHORT_VIDEO",
  "platformType": "DOUYIN",
  "platformTypes": ["DOUYIN", "KUAISHOU"],
  "accountId": 123,
  "accountIds": [123, 456],
  "creatorUserId": 456,
  "body": "...",
  "aiGenerated": 0,
  "taskId": null,
  "competitionId": "123456789",
  "competitionName": "英超-曼联 VS 切尔西",
  "documentType": null,
  "ipGroupId": 9001,
  "finalVideoUrl": null,
  "bodyFormat": "PLAIN",
  "layoutJson": null,
  "layoutHtml": null,
  "layoutTemplateId": null
}
```

**校验**：
- `title` `@NotBlank @Size(max=200)`
- `contentType` `@InDict(type="dict_content_type")`
- `platformType` / `platformTypes` 可选；若传 `accountId(s)` 则校验平台匹配（2006）
- `accountId` / `accountIds` **可选**（任务场景可不填）
- `creatorUserId` `@NotNull`
- `ipGroupId` `@NotNull`：独立创作须为用户所属 IP 组；任务场景继承任务 IP 组
- `body` LONGTEXT；`contentType=SHORT_VIDEO` 时可为空（视频 URL 为准）
- `coverImage` **UI 已移除**；库字段保留，可不传
- `taskId` 非空时：同一 `taskId` 仅允许 1 条内容（1502）
- `documentType`：`contentType=ARTICLE` 时 `@NotBlank @InDict(type="dict_document_type")`
- `bodyFormat` `@InDict(type="dict_content_body_format")`；默认 `PLAIN`
- `layoutJson` / `layoutHtml`：当 `bodyFormat=LAYOUT` 时 `layoutJson` 必填；服务端同步生成/校验 `layoutHtml`
- `layoutTemplateId` 可选；若传则校验模板存在且类型匹配（**2011**）

### 3.2.6 POST `/admin-api/ops/content/{id}/apply-layout-template`（草案 · S-14）

**请求体** `ContentApplyLayoutTemplateReq`：

```json
{
  "layoutTemplateId": 501,
  "overwrite": false
}
```

**业务**：
- 校验 `contentType=ARTICLE`
- 校验模板 `status=ENABLED` 且 document_type 匹配（ADR-019 §2.3）
- 若内容已有 `bodyFormat=LAYOUT` 且 `overwrite=false` → **2012**
- 复制模板 `layoutJson`/`layoutHtml` → 内容；设置 `layoutTemplateId`；`bodyFormat=LAYOUT`

**响应**：更新后的 `ContentRespVO`

---

### 3.2.1 GET `/admin-api/ops/content/by-task?taskId=`（✅ S-12）

返回任务关联内容（0..1），供执行页与编辑页预加载。

### 3.2.2 GET `/admin-api/ops/content/script-ref?competitionId=`（✅ S-13）

返回同赛事 `documentType=SHORT_VIDEO_SCRIPT` 且 `status=COMPLETED` 的文档正文（供短视频引用）。

### 3.2.3 POST `/admin-api/ops/content/{id}/confirm`（Spec 历史 / 当前未实现）

**业务（旧稿）**：`DRAFT` → `COMPLETED`。**现网**无此端点；请用 `POST /content/{id}/submit-review`（ADR-017）。

---

### 3.2.4 GET `/admin-api/ops/content/review-config`（✅ ADR-017）

**响应** `ContentReviewConfigVO`：

```json
{
  "level1Enabled": true,
  "level2Enabled": true,
  "level1Role": "OPS_LEADER",
  "level2Role": "DEPT_HEAD"
}
```

---

### 3.2.5 GET `/admin-api/ops/content/ai-prompt-options`（Spec 历史 / 当前未实现）

按 `contentType` / `documentType` 返回可选 M8 提示词列表（AI 弹窗）。**`ProductionContentController` 无此路由**；AI 弹窗以 `GET /admin-api/ops/ai-content/models` 等 `AiContentController` 为准。

---

### 3.3 PUT `/admin-api/ops/content/update`

同 create + `id`。

---

### 3.4 POST `/admin-api/ops/content/{id}/submit-review`

**业务**（ADR-017）：
- 校验 `ipGroupId`、内容完整性
- 按 `review-config` 决定目标状态：`PENDING_FIRST_REVIEW` / `PENDING_SECOND_REVIEW` / `PENDING_PUBLISH`
- 记录 `oa_review_record`；返回审核流程 steps（含角色+可审用户）

---

### 3.5 POST `/admin-api/ops/content/{id}/review`

**请求体** `ContentReviewReq`：

```json
{
  "action": "APPROVE",
  "stage": "FIRST_REVIEW",
  "comment": "..."
}
```

**stage**：`FIRST_REVIEW` | `SECOND_REVIEW`（默认配置）；`FINAL_REVIEW` 仅遗留数据。

**校验**：
- 当前用户满足 ADR-017 权限（含 IP 组长范围）
- 驳回 → `REJECTED`；通过 → 按配置进入下一级或 `PENDING_PUBLISH`

---

### 3.5.1 GET `/admin-api/ops/content/{id}/publish-options`（Spec 历史 / 当前未实现 · ADR-022 草案）

**权限（旧稿）**：`oa:content:publish`。**现网**无 publish-options / publish 端点；Football 方案上下架见 `POST /content/{id}/shelf-on` · `shelf-off`（ADR-054）。

---

### 3.5.2 POST `/admin-api/ops/content/{id}/publish`（Spec 历史 / 当前未实现 · ADR-022 草案）

**请求体（旧稿）** `ContentPublishReq`：`platformType` + `accountIds[]`。**未在 `ProductionContentController` 实现**。

---

### 3.8 Football 方案与上下架（ADR-054 · 现网 `ProductionContentController`）

> UX：内容抽屉/编辑页「同步 Football 方案」「上架/下架」· [`UX-M2-内容生产.md`](../product/UX-M2-内容生产.md) P-M2-006/007

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ops/content/{id}/football-scheme` | Master + ext 组装 VO（含上架状态） |
| POST | `/admin-api/ops/content/{id}/sync-football-scheme` | 幂等重试双写 Football 草稿 |
| POST | `/admin-api/ops/content/{id}/shelf-on` | 上架（Football 侧状态） |
| POST | `/admin-api/ops/content/{id}/shelf-off` | 下架 |

**权限**：与内容写权限一致（`ops:content:update` / `oa:content:update` 过渡）。**未实现** legacy `publish-options` / `publish`（§3.5.1–3.5.2）。

### 3.9 排版端点（摘要 · 详规见 AI 排版增量）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/ops/content/{id}/typeset/ai-semantic/preview` | AI 语义排版预览（LLM） |
| POST | `/admin-api/ops/content/{id}/typeset/ai-semantic/apply` | AI 语义排版写回 |
| POST | `/admin-api/ops/content/typeset` | 编辑态一键排版（无 id） |
| POST | `/admin-api/ops/content/{id}/typeset` | 带内容 id 一键排版 · `mode=FOOTBALL_AI` |

详请求/响应字段：[`API-M2-AI排版增量.md`](./API-M2-AI排版增量.md) · UX：[`UX-M2-AI排版增量.md`](../product/UX-M2-AI排版增量.md)。

---

### 3.6a POST `/admin-api/ops/content/{id}/retry-ai-generate`（ADR-077 Slice D）

**请求**：无 body。权限：`ops:content:list` 或 `ops:task:list`；任务关联内容另须执行人（ADR-016）。

**业务**：
- 仅 `aiGenerateStatus=FAILED` 可重试；`QUEUED` / `GENERATING` → **2010**
- 重置 `QUEUED` 后异步再入队同一 jingcai Job（`WorkTaskConfirmJingcaiJob.processContent`，内部仍走现网 generate）
- 内容保持 `DRAFT`；**不**自动完成任务

**响应**：`ProductionContentVO`（含更新后的 `aiGenerateStatus` / `aiGenerateError`）

---

### 3.6 DELETE `/admin-api/ops/content/{id}`

**业务**（S-R22-Mike）：
- 仅 `DRAFT` / `REJECTED` 可删除
- 其他状态 → `2010` CONTENT_STATUS_INVALID
- 逻辑删除（`deleted=1`）

### 3.6.1 内容列表批量操作（ADR-081）

**不新增**路径。前端对当前页勾选行串行调用 §3.4 / §3.6 / `POST /ops/content/{id}/transfer-to-knowledge`。资格与单条一致；不合格跳过。

---

### 3.7 POST `/admin-api/ops/ai-content/generate`（✅ 真实 LLM · `AiContentController`）

> 按内容 ID 触发现网生成：`POST /admin-api/ops/content/{id}/generate` · 失败重试 §3.6a。

**请求体** `ContentAiGenerateReq`：

```json
{
  "modelId": 1,
  "promptId": 2,
  "contentType": "ARTICLE",
  "documentType": "POST_MATCH_REVIEW",
  "competitionId": "20260626001",
  "competitionName": "2026 中超联赛 第 12 轮 上海申花 2:1 山东泰山",
  "taskId": 8801,
  "ipGroupId": 9001,
  "authorId": 68028,
  "authorName": "李四",
  "historicalRecord": "近5场3胜1平1负",
  "matchDirection": "主队受让",
  "streamerPersona": "理性分析型",
  "revisionFeedback": "加强结尾互动",
  "lengthType": "MEDIUM"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `modelId` | ✅ | M8 `oa_ai_model_config` 已启用记录 |
| `promptId` | ✅ | M8 提示词；须与 `contentType`/`documentType` 匹配 |
| `contentType` | ✅ | `@InDict("dict_content_type")` |
| `documentType` | 条件 | `contentType=ARTICLE` 时必填 |
| `competitionId` / `competitionName` | 推荐 | 赛事解析优先级见 API-REQ-M2 |
| `taskId` | ❌ | 任务驱动创作 |
| `ipGroupId` | ❌ | 校验作者归属 |
| `authorId` / `authorName` | ❌ | 填充 `{{author}}`；`authorId` = `author_user.id` |
| `historicalRecord` / `matchDirection` / `streamerPersona` / `revisionFeedback` | ❌ | V134 提示词占位符 |
| `lengthType` | ❌ | `@InDict("dict_content_length_type")`：SHORT/MEDIUM/LONG |

- 后端 HTTP 调 LLM（`oa.ai-generate.llm-timeout-seconds` 默认 300s），写入 `body` 或返回占位（模型未连通时 `mock=true`）

**响应**：`ContentAiGenerateResultVO`（生成文本/URL）

---

## 4. 知识库 API

### 4.1 GET `/admin-api/ops/knowledge/list`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| title | String | ❌ | - |
| category | String | ❌ | 固定枚举 |
| tag | String | ❌ | - |
| isPublic | Integer | ❌ | `dict_yes_no` |
| pageNum | Integer | ❌ | - |

---

### 4.2 POST `/admin-api/ops/knowledge/create`

**请求体**：

```json
{
  "title": "...",
  "category": "TEMPLATE_LIB",
  "content": "...",
  "tags": ["运营", "SOP"],
  "isPublic": 1
}
```

**校验**：
- `title` `@NotBlank @Size(max=100)`
- `category` `@InDict(type="dict_knowledge_category")`（**v1.0 用固定值，v2.0 改字典**）
- `isPublic` `@InDict(type="dict_yes_no")`

---

### 4.3 PUT `/admin-api/ops/knowledge/update`

---

### 4.4 GET `/admin-api/ops/knowledge/search?keyword=xxx`（Spec 历史 / 当前未实现）

**业务（旧稿）**：ES/全文搜索。**现网**用 `GET /admin-api/ops/knowledge/list?title=`（及 `category` / `tags`）模糊查询。

---

## 6. 公推模板库 API（FR-M2-005 · 草案 · S-14）

> **路径前缀**：`/admin-api/ops/layout-template/*`（`LayoutTemplateController`）  
> **存储格式**：见 [`ADR-019`](../adr/ADR-019-M2-公推模板库存储与导入.md)

### 6.1 GET `/admin-api/ops/layout-template/list`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| templateName | String | ❌ | 模糊 |
| documentType | String | ❌ | `dict_document_type`；传 `__GENERAL__` 筛「通用（空）」 |
| status | String | ❌ | `dict_layout_template_status` |
| sourceType | String | ❌ | `dict_layout_template_source` |
| pageNum / pageSize | Integer | ❌ | 默认 20 |

**响应**：`PageResult<LayoutTemplateVO>`

```json
{
  "id": 501,
  "templateName": "赛后复盘标准版式",
  "contentType": "ARTICLE",
  "documentType": "POST_MATCH_REVIEW",
  "description": "...",
  "sourceType": "MANUAL",
  "sourceUrl": null,
  "status": "ENABLED",
  "thumbnailUrl": "https://...",
  "creatorUserId": 1003,
  "creatorName": "张三",
  "updatedAt": "2026-06-14T10:00:00+08:00"
}
```

**说明**：列表 **不** 返回完整 `layoutJson`（过大）；详情接口返回。

---

### 6.2 GET `/admin-api/ops/layout-template/{id}`

**响应** `LayoutTemplateDetailVO`：含 `layoutJson`、`layoutHtml`（只读冗余）。

---

### 6.3 GET `/admin-api/ops/layout-template/select-list`

**用途**：内容创作页模板选择器（轻量列表）。

| 参数 | 类型 | 必填 |
|------|------|------|
| documentType | String | ❌ | 当前内容 documentType；服务端按 ADR-019 匹配规则过滤 |
| contentType | String | ✅ | 固定 `ARTICLE` |

**响应**：`List<LayoutTemplateSelectVO>`（id、templateName、documentType、thumbnailUrl）

---

### 6.4 POST `/admin-api/ops/layout-template/create`

**请求体** `LayoutTemplateCreateReq`：

```json
{
  "templateName": "标准引流版式",
  "description": "...",
  "documentType": null,
  "layoutJson": { "version": 1, "blocks": [] },
  "status": "ENABLED"
}
```

**校验**：
- `templateName` `@NotBlank @Size(max=100)`
- `contentType` 服务端固定 `ARTICLE`
- `documentType` 可空；非空则 `@InDict(dict_document_type)`
- `layoutJson` `@NotNull`；schema 校验（**2013** 非法块结构）
- `status` `@InDict(dict_layout_template_status)`

**业务**：服务端 `layoutHtml = renderAndSanitize(layoutJson)`

---

### 6.5 PUT `/admin-api/ops/layout-template/update`

同 create + `id`；已停用模板可编辑。

---

### 6.6 DELETE `/admin-api/ops/layout-template/{id}`

- 逻辑删除；若被 `oa_production_content.layout_template_id` 引用 → **仍允许删除**（内容保留快照）
- 无引用要求

---

### 6.7 POST `/admin-api/ops/layout-template/import-url`（BLK-M2-012）

**请求体**：

```json
{
  "sourceUrl": "https://mp.weixin.qq.com/s/...",
  "templateName": "导入-竞品排版",
  "documentType": null
}
```

**响应**：

```json
{
  "jobId": 9001,
  "status": "PENDING"
}
```

**异步 Job 完成**：`GET /layout-template/import-job/{jobId}` → `SUCCESS` 时含 `layoutJson` 预览 + 建议 `templateName`

**失败**：`FAILED` + `errorCode`（**2014** URL 不可抓取）

---

### 6.8 POST `/admin-api/ops/layout-template/import-docx`（BLK-M2-013/014）

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 |
|------|------|------|
| file | File | ✅ `.docx` |
| templateName | String | ❌ |
| documentType | String | ❌ |

**响应**：同 import-url（异步 Job）

---

### 6.9 POST `/admin-api/ops/layout-template/import-paste`（Fallback）

**请求体**：

```json
{
  "templateName": "粘贴导入",
  "documentType": null,
  "html": "<section>...</section>"
}
```

**业务**：HTML → parse → `layoutJson` + `layoutHtml`；同步返回详情（无异步）

---

### 6.10 GET `/admin-api/ops/layout-template/import-job/{jobId}`

**响应** `LayoutImportJobVO`：

```json
{
  "id": 9001,
  "status": "SUCCESS",
  "sourceType": "URL",
  "sourceUrl": "https://...",
  "previewLayoutJson": { "version": 1, "blocks": [] },
  "errorMessage": null
}
```

**字典** `status`：`PENDING` / `RUNNING` / `SUCCESS` / `FAILED`

---

## 5. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500 | 关联实体不存在；ADR-079：请填写工作说明 / 须先关联内容记录 / 内容须审核通过后方可完成任务 |
| 1501 | 关联实体已停用/注销 |
| 1502 | 关联实体已被引用 |
| 1503 | 字典值不合法 |
| 1504 | 跨租户访问禁止 |
| 2001 | DAG 存在环 |
| 2002 | 节点 `executor_role` 缺失 |
| 2003 | `need_review=1` 但 `reviewer_role` 缺失 |
| 2004 | 前置节点未完成 |
| 2005 | 模板无节点，无法启用 |
| 2006 | 账号平台类型与内容平台类型不匹配 |
| 2007 | 审核人岗位不匹配 |
| 2008 | **（ADR-079 取代）** 原内容生成完成门禁；现用 **1500** |
| 2010 | 内容状态不允许删除 |
| **2011** | 版式模板不存在或类型不匹配（FR-M2-005） |
| **2012** | 内容已有版式且未确认覆盖 |
| **2013** | `layoutJson` schema 校验失败 |
| **2014** | 公众号 URL 抓取/解析失败（BLK-M2-012） |
| **2015** | Word 导入解析失败 |
| **2016** | 导入 Job 不存在或已过期 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

## 强关联字段 → 选择器映射（🔴 API 必含）

本模块涉及以下强关联字段，**前端必须使用对应选择器组件**：

| 字段 | 选择器组件 | 关联实体 | 错误码 |
|------|----------|---------|--------|
| `authorId` | `<RealNameSelect />` | 作者 | 1501 / 1504 |
| `accountId` | `<AccountSelect />` | 发布平台账号 | 1501 / 1504 |
| `platform` | `<DictSelect dict-type="dict_platform_type" />` | 平台字典 | 1503 |
| `reviewStage` | `<DictSelect dict-type="dict_review_stage" />` | 审核阶段 | 1503 |
| `layoutTemplateId` | `<LayoutTemplateSelect />` | 公推版式模板 | 1501 / 2011 |

---

## CHANGELOG

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-10-02 | v1.7 | §3.8 Football 方案/上下架 · §3.9 排版端点摘要 |
| 2026-10-02 | v1.6 | 全文 `/oa/` → `/ops/` 与 Controller 对齐；标注未实现端点；AI 生成路径改为 `ai-content/generate` |
| 2026-10-02 | v1.5 | §0 路径 SSOT 声明 |
