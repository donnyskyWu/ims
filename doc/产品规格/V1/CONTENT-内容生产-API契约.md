# CONTENT - 内容生产 API 契约

> **模块范围**：15 内容生产（V1，第 10~13 周，升级）——CONTENT-001 执行标准级 SOP、CONTENT-002 选题计划、CONTENT-003 AI 辅助脚本、CONTENT-004 AI 短视频自动化生产（ComfyUI）、CONTENT-005 在线审核、CONTENT-006 发布归档。  
> **双边契约边界（方案甲 · 2026-10-05 拍板）**：
> | 契约 | 权限 | 裁定什么 |
> |------|------|----------|
> | 本文《CONTENT-内容生产-API契约》 | **字段权** | **所有端点的字段级 SSOT**——请求/响应 DTO、校验、状态机、错误码；含 IMS-only 端点（选题/脚本/ComfyUI/发布归档） |
> | 《CONTENT-OPS并入补充-API契约》 | **范围权** | **端点范围与 OPS 主路径清单**——哪些端点是 OPS 主路径、哪些是 IMS-only、OPS 现网对照；**不定义字段** |
>
> **裁决规则**：**「这个端点在不在范围内 / 是否属 OPS 主路径」→ 查补充契约；「这个端点的字段长什么样」→ 查本文**。两者**互不越界**、不重复定义字段。若发现字段描述不一致，**一律以本文为准**（补充契约字段表仅为索引，冲突即失效）。
>
> **写模型（2026-10-01）**：IMS 重写业务表 + 本文 **`/admin-api/ims/content/**`** 为唯一 runtime 前缀。**任务执行/工作任务/内容 CRUD/matchScheme** 的**范围**（属 OPS 主路径）见补充契约；其**字段**仍以本文 §1/§2 为准。OPS `/oa/*`、`/ops/content/*` **仅 UX/行为/迁移对照**，禁止新代码直连 OPS HTTP。
> **权威依据**：《IMS第一期PRD-V1.md》5.20~5.25；《共享技术规范-数据库与API.md》8.3（`POST /content/ai-job/submit`、`GET /content/ai-job/{id}/status` 典型端点）及 V1-C1~C6 ComfyUI 集成约束。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》；字段 camelCase。

---

## 1. API 总览表（共 36 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/content/sop/list` | SOP 列表（分页） | R1/R4/R6/R5（直播 SOP）/R7（只读）/R10（被指派） |
| 2 | POST | `/admin-api/ims/content/sop` | 创建 SOP（含节点） | R1/R4 |
| 3 | PUT | `/admin-api/ims/content/sop/{id}` | 编辑（生成新版本） | R1/R4 |
| 4 | DELETE | `/admin-api/ims/content/sop/{id}` | 删除 SOP | R1/R4 |
| 5 | GET | `/admin-api/ims/content/sop/{id}/nodes` | SOP 节点详情 | 同查看 |
| 6 | POST | `/admin-api/ims/content/sop/node/{nodeId}/check` | 质量清单校验提交 | R6/R10（被指派） |
| 7 | POST | `/admin-api/ims/content/topic` | 提报选题 | R5/R6/R7 |
| 8 | GET | `/admin-api/ims/content/topic/list` | 选题列表（分页） | R1/R4/R6/R9/R5（直播选题） |
| 9 | PUT | `/admin-api/ims/content/topic/{id}` | 编辑选题 | R4/R6（本人） |
| 10 | PUT | `/admin-api/ims/content/topic/{id}/review` | 评审（立项/落选） | R4 |
| 11 | GET | `/admin-api/ims/content/topic/gantt` | 排期甘特数据 | R1/R4/R6/R9 |
| 12 | POST | `/admin-api/ims/content/script/generate` | AI 生成候选脚本 | R6/R5 |
| 13 | GET | `/admin-api/ims/content/script/list` | 脚本列表（分页） | R1/R4/R6/R5（只读） |
| 14 | PUT | `/admin-api/ims/content/script/{id}` | 编辑脚本 | R6 |
| 15 | PUT | `/admin-api/ims/content/script/{id}/finalize` | 定稿 | R6 |
| 16 | GET | `/admin-api/ims/content/script/{id}/versions` | 版本历史 | R1/R4/R6 |
| 17 | POST | `/admin-api/ims/content/ai-production/task` | 创建 AI 生产任务 | R6/R10（被指派） |
| 18 | GET | `/admin-api/ims/content/ai-production/task/page` | AI 生产任务列表（分页） | R1/R4/R6（本人）/R10（被指派） |
| 19 | GET | `/admin-api/ims/content/ai-production/task/{taskNo}` | 任务详情（含 DAG 状态） | R1/R4/R6/R10（被指派） |
| 20 | PUT | `/admin-api/ims/content/ai-production/task/{taskNo}/prompt` | 修改提示词 | R6/R1 |
| 21 | POST | `/admin-api/ims/content/ai-production/task/{taskNo}/run` | 启动工作流 | R6 |
| 22 | PUT | `/admin-api/ims/content/ai-production/task/{taskNo}/review` | 人工终审 | R6/R1（见权限说明） |
| 23 | POST | `/admin-api/ims/content/ai-production/task/{taskNo}/retry-node` | 打回指定节点重生成 | R6/R1 |
| 24 | GET | `/admin-api/ims/content/ai-production/runs/{taskNo}` | DAG 节点执行记录 | R1/R4/R6 |
| 25 | POST | `/admin-api/ims/content/ai-job/submit` | 提交 ComfyUI AI Job（队列调度入口，V1-C1/C2） | R6/R1（内部链路） |
| 26 | GET | `/admin-api/ims/content/ai-job/{id}/status` | 查询 AI Job 状态（队列/进度） | 同上 |
| 27 | GET | `/admin-api/ims/content/review/queue` | 审核队列（分页） | R1/R4/R8（队列）/R6（本人提交） |
| 28 | GET | `/admin-api/ims/content/review/{reviewNo}` | 审核单详情 | 同上 |
| 29 | PUT | `/admin-api/ims/content/review/{reviewNo}/conclusion` | 提交审核结论 | R8（主责）/R4（裁决） |
| 30 | GET | `/admin-api/ims/content/review/first-pass-stats` | 一次通过率统计（BR-009） | R1/R4/R8 |
| 31 | GET | `/admin-api/ims/content/review/reject-analysis` | 打回原因分析 | R1/R4/R8 |
| 32 | POST | `/admin-api/ims/content/publish` | 创建发布单 | R6（执行）/R4 |
| 33 | GET | `/admin-api/ims/content/publish/list` | 发布单列表（分页） | R1/R4/R6/R8（只读）/R9 |
| 34 | PUT | `/admin-api/ims/content/publish/{id}/receipt` | 回填发布链接 | R6 |
| 35 | GET | `/admin-api/ims/content/publish/{id}/archive` | 归档包详情 | 同上 |
| 36 | GET | `/admin-api/ims/content/publish/pending` | 待发布/待回填督办列表 | R1/R4/R6 |

---

## 2. 接口明细

### 2.1 执行标准级 SOP（CONTENT-001）

#### 2.1.1 GET /admin-api/ims/content/sop/list — SOP 列表（分页）

**请求**（Query）：`PageParam` + `{ keyword?: string; contentType?: string; status?: EnableStatus }`

**响应** `data`：`PageResult<ContentSopVO>`

```typescript
interface ContentSopVO {
  id: number;
  sopCode: string;
  sopName: string;               // 如"带货短视频标准 SOP"
  contentType: string;           // 适用内容类型
  sopLevel: SopLevel;            // STANDARD（执行标准级）/ GUIDE（指导级）
  version: number;
  status: EnableStatus;
  nodeCount: number;             // 节点数摘要
  createdAt: string;
}
```

#### 2.1.2 POST /admin-api/ims/content/sop — 创建 SOP（含节点）

**请求**：

```typescript
interface ContentSopCreateReq {
  sopName: string;
  contentType: string;
  sopLevel: SopLevel;
  nodes: SopNodeReq[];           // 选题→脚本→拍摄/生成→剪辑→审核→发布 节点序列
}

interface SopNodeReq {
  nodeOrder: number;
  nodeName: string;
  /** 执行标准说明 */
  standardDesc: string;
  /** 交付物规格（格式/规格，JSON） */
  deliverableSpec: Record<string, unknown>;
  /** 质量检查清单（Checklist 数组） */
  qualityChecklist: Array<{ itemCode: string; itemDesc: string; required: boolean }>;
  ownerRole: string;             // 责任角色（R6/R8/R10 等）
  slaHours: number;              // 节点时效
}
```

**响应** `data`：`ContentSopVO`（version=1）。

#### 2.1.3 PUT /admin-api/ims/content/sop/{id} — 编辑（生成新版本）

**请求**：`ContentSopCreateReq` → **响应**：新 `ContentSopVO`（version+1）。**SOP 变更新版本，进行中项目沿用旧版本完成（SOP-R3）**。

#### 2.1.4 DELETE /admin-api/ims/content/sop/{id}

**请求**（Query）：`{ confirmText: 'DELETE' }` → **响应**：`data: null`（逻辑删除；有进行中项目挂接时提示沿用旧版本完成）。

#### 2.1.5 GET /admin-api/ims/content/sop/{id}/nodes — 节点详情

**响应** `data`：

```typescript
interface SopNodeVO extends SopNodeReq {
  id: number;
  sopId: number;
}
```

#### 2.1.6 POST /admin-api/ims/content/sop/node/{nodeId}/check — 质量清单校验提交

**请求**：

```typescript
interface SopNodeCheckReq {
  /** 内容项目 ID（挂接该 SOP 的项目） */
  contentProjectId: number;
  /** 逐项勾选结果 */
  checklistResults: Array<{ itemCode: string; passed: boolean; remark?: string }>;
  /** 交付物 fileKey（FileUpload 服务端上传回执 · 本期不上对象存储，见《全局开发规范》§6.3） */
  deliverableOssKeys: string[];
}
```

**响应**：`{ nodePassed: boolean; failedItems: string[] }`。未通过项打回上游节点留痕（SOP-R2：清单全通过 + 交付物上传才可节点完成；**错误码 1007** SOP 步骤不合规）。

### 2.2 选题计划（CONTENT-002）

#### 2.2.1 POST /admin-api/ims/content/topic — 提报选题

**请求**：

```typescript
interface ContentTopicCreateReq {
  title: string;
  description: string;
  sourceType: 'HOTSPOT' | 'TALENT' | 'BRAND' | 'ORIGINAL';   // 热点/达人/品牌/自主
  planPublishDate?: string;     // 立项时必填（TOP-R1）
  sopId?: number;               // 立项时必填（TOP-R1）
}
```

**响应** `data`：

```typescript
interface ContentTopicVO {
  id: number;
  topicNo: string;               // TP+日期+流水
  title: string;
  description: string;
  sourceType: 'HOTSPOT' | 'TALENT' | 'BRAND' | 'ORIGINAL';
  submitterUserId: number;
  submitterName: string;
  planPublishDate?: string;
  topicStatus: 'PENDING_REVIEW' | 'APPROVED_PROJECT' | 'REJECTED' | 'CANCELLED';   // 0 待评审 / 1 已立项 / 2 落选 / 3 已取消
  sopId?: number;
  sopName?: string;
  reviewOpinion?: string;
  createdAt: string;
}
```

#### 2.2.2 GET /admin-api/ims/content/topic/list — 选题列表（分页）

**请求**（Query）：`PageParam` + `{ topicStatus?: string; sourceType?: string; submitterUserId?: number; keyword?: string }` → **响应**：`PageResult<ContentTopicVO>`

#### 2.2.3 PUT /admin-api/ims/content/topic/{id} — 编辑选题

**请求**：`ContentTopicCreateReq`（待评审态）→ **响应**：`data: null`。

#### 2.2.4 PUT /admin-api/ims/content/topic/{id}/review — 评审（立项/落选）

**请求**：`{ action: 'APPROVE_PROJECT' | 'REJECT'; planPublishDate: string; sopId: number; reviewOpinion: string }`（立项时必填计划发布日与 SOP，TOP-R1，**错误码 1052**）→ **响应**：`data: null`。落选归档保留可复活（TOP-R2）；立项即创建内容项目挂 SOP 进入节点流转。

#### 2.2.5 GET /admin-api/ims/content/topic/gantt — 排期甘特数据

**请求**（Query）：`{ timeRange: [string, string]; accountId?: number }`

**响应** `data`：`{ items: Array<{ topicNo: string; title: string; planPublishDate: string; topicStatus: string; sopName?: string }> }`（排期冲突提示不阻断，TOP-R3）。

### 2.3 AI 辅助脚本（CONTENT-003）

#### 2.3.1 POST /admin-api/ims/content/script/generate — AI 生成候选脚本

**请求**：

```typescript
interface ScriptGenerateReq {
  topicId: number;
  /** 内容要求（选题描述 + 标准要求） */
  contentRequirement: string;
  scriptType: 'MONOLOGUE' | 'STORY' | 'SALES_PITCH';   // 口播 / 剧情 / 带货话术
  /** 候选版本数（2~3 版） */
  candidateCount?: number;
}
```

**响应** `data`：

```typescript
interface ScriptGenerateResp {
  candidates: ContentScriptVO[];   // 2~3 版候选
  /** 生成提示词快照（可复现，SCR-R3） */
  promptSnapshot: string;
}

interface ContentScriptVO {
  id: number;
  topicId: number;
  scriptType: 'MONOLOGUE' | 'STORY' | 'SALES_PITCH';
  /** 脚本内容（Markdown） */
  content: string;
  version: number;
  aiGenerated: boolean;          // true（AI 生成）；人工编辑后新版本 false
  promptSnapshot?: string;
  status: 'DRAFT' | 'FINALIZED'; // 0 草稿 / 1 定稿
  authorUserId: number;
  createdAt: string;
}
```

#### 2.3.2 GET /admin-api/ims/content/script/list — 脚本列表（分页）

**请求**（Query）：`PageParam` + `{ topicId?: number; scriptType?: string; status?: string }` → **响应**：`PageResult<ContentScriptVO>`

#### 2.3.3 PUT /admin-api/ims/content/script/{id} — 编辑脚本

**请求**：`{ content: string }` → **响应**：新版本 `ContentScriptVO`（版本对比留痕）。**AI 生成脚本必须人工编辑确认后才能定稿（SCR-R1）**。

#### 2.3.4 PUT /admin-api/ims/content/script/{id}/finalize — 定稿

**请求**：`{}` → **响应**：`data: null`。定稿版本锁定（SCR-R2），作为下游 AI 生产/拍摄节点输入。

#### 2.3.5 GET /admin-api/ims/content/script/{id}/versions — 版本历史

**响应** `data`：`{ versions: Array<{ id: number; version: number; aiGenerated: boolean; content: string; authorUserId: number; createdAt: string }> }`

### 2.4 AI 短视频自动化生产（CONTENT-004）

#### 2.4.1 POST /admin-api/ims/content/ai-production/task — 创建生产任务

**请求**：

```typescript
interface AiProductionTaskCreateReq {
  taskNo?: string;               // 响应返回系统生成（AIP+日期+流水）
  topicId?: number;
  scriptId?: number;
  /** 内容要求（选题/脚本/风格参数） */
  requirement: string;
  /** 关联 ComfyUI 工作流定义 ID（ims_content_workflow） */
  workflowId: number;
}
```

**响应** `data`：

```typescript
interface AiProductionTaskVO {
  id: number;
  taskNo: string;                // AIP+日期+流水
  topicId?: number;
  scriptId?: number;
  requirement: string;
  /** 系统生成的初始提示词（模板化文生图/图生视频） */
  promptInitial: string;
  /** 人工调整后的最终提示词 */
  promptFinal: string;
  workflowId: number;
  workflowCode: string;
  taskStatus: AiJobStatus;       // WAITING / GENERATING / PENDING_FINAL_REVIEW / REVIEW_PASSED / REVIEW_REJECTED / FAILED
  outputFileUrl?: string;        // 成片文件下载地址（服务端文件目录读链）
  reviewerUserId?: number;
  createdBy: number;
  createdAt: string;
}
```

**错误码**：1051（工作流不存在/未启用）、1052（选题未立项或脚本未定稿，SCR-R1 联动 → 1053）。

#### 2.4.2 GET /admin-api/ims/content/ai-production/task/page — AI 生产任务列表（分页）

**请求**（Query）：

```typescript
interface AiProductionTaskPageReq {
  pageNum: number;                // 页码（默认 1）
  pageSize: number;               // 每页条数（默认 20）
  /** 任务编号/关联选题标题关键字 */
  keyword?: string;
  /** 任务状态筛选（AiJobStatus） */
  taskStatus?: AiJobStatus;
}
```

**响应** `data`：

```typescript
{
  total: number;
  records: Array<AiProductionTaskVO & { topicTitle?: string; workflowName?: string }>;
}
```

（列表仅含索引字段；DAG 状态与产物详情走 2.4.3 任务详情端点。）

#### 2.4.3 GET /admin-api/ims/content/ai-production/task/{taskNo} — 任务详情（含 DAG 状态）

**响应** `data`：`AiProductionTaskVO` + `dagNodes: AiWorkflowRunVO[]`

```typescript
interface AiWorkflowRunVO {
  id: number;
  taskNo: string;
  nodeName: string;              // 分镜生成/视频合成/配音字幕/成片
  nodeType: 'COMFYUI' | 'LLM' | 'AUDIO';
  inputUrl?: string;
  outputUrl?: string;
  runStatus: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  retryCount: number;
  startedAt?: string;
  finishedAt?: string;
  errorMsg?: string;
}
```

#### 2.4.4 PUT /admin-api/ims/content/ai-production/task/{taskNo}/prompt — 修改提示词

**请求**：`{ promptFinal: string }` → **响应**：`data: null`。修改留版本（AIP-R1）。

#### 2.4.5 POST /admin-api/ims/content/ai-production/task/{taskNo}/run — 启动工作流

**请求**：`{}` → **响应**：`{ jobIds: number[]; message: string }`。内部提交 AI Job（见 2.4.8）；节点失败自动重试 2 次仍失败置失败并告警（AIP-R2）；**单任务全链路超时 60 分钟自动失败告警（AIP-R4，错误码 1056）**。

#### 2.4.6 PUT /admin-api/ims/content/ai-production/task/{taskNo}/review — 人工终审

**请求**：`{ pass: boolean; comment?: string }` → **响应**：`data: null`。**终审通过前成片不可发布（AIP-R5 硬约束，错误码 1054）**。

#### 2.4.7 POST /admin-api/ims/content/ai-production/task/{taskNo}/retry-node — 打回指定节点重生成

**请求**：`{ nodeName: string }` → **响应**：`data: null`。终审不通过可打回指定 DAG 节点重生成，非全链重跑（AIP-R3，**错误码 1055** 节点非法）。

#### 2.4.8 POST /admin-api/ims/content/ai-job/submit — 提交 ComfyUI AI Job（队列调度）

**请求**：

```typescript
interface AiJobSubmitReq {
  /** 关联生产任务 */
  taskNo: string;
  workflowId: number;
  nodeName: string;
  /** 工作流参数（按 ims_content_workflow.paramSchema 校验） */
  params: Record<string, unknown>;
  /** 优先级（V1-C2 五级：P0 生产阻塞 > P1 当日交付 > P2 常规 > P3 批量 > P4 试验） */
  priority: 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
}
```

**响应** `data`：

```typescript
interface AiJobVO {
  id: number;                    // jobId（状态查询用）
  taskNo: string;
  workflowId: number;
  nodeName: string;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
  queueStatus: 'WAITING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  gpuNode?: string;              // 执行节点
  resultFileKey?: string;        // 产物 fileKey（V1-C5 · 服务端相对路径）
  submittedAt: string;
}
```

**错误码**：5004（ComfyUI 队列满 / GPU 不可用）、1001（params 不符合 paramSchema）。

#### 2.4.9 GET /admin-api/ims/content/ai-job/{id}/status — 查询 AI Job 状态

**响应** `data`：`AiJobVO` + `{ progress?: number; queuePosition?: number; etaMinutes?: number }`（轮询/WebSocket 进度，V1-C1）。

**V1-C1~C6 约束落地**：经 ComfyUI HTTP API（`POST /prompt` 提交、`GET /history/{id}` 查询、`/ws` 进度）调用，禁止操作 ComfyUI 前端；GPU 利用率 > 90% 持续 5 分钟停止派发并告警；单 Job 默认超时 30 分钟重试 1 次；产物统一落**服务端文件目录**（临时区 24h 清理）；单节点并发 1，积压 > 100 暂停 P2 以下派发。

### 2.5 在线审核（CONTENT-005）

#### 2.5.1 GET /admin-api/ims/content/review/queue — 审核队列（分页）

**请求**（Query）：`PageParam` + `{ reviewerUserId?: number; overdueOnly?: boolean }`

**响应** `data`：`PageResult<ContentReviewVO>`（按发布排期排序，超期高亮）

```typescript
interface ContentReviewVO {
  id: number;
  reviewNo: string;              // RV+日期+流水
  contentProjectId: number;
  contentTitle: string;
  submitterUserId: number;
  submitterName: string;
  reviewerUserId?: number;
  reviewRound: number;           // 审核轮次
  checklistResult?: Record<string, boolean>;
  conclusion?: 'PASS' | 'REJECT_BACK' | 'TERMINATE';   // 1 通过 / 2 打回 / 3 驳回终止
  rejectItems?: Array<{ itemCode: string; reason: string }>;
  firstPass?: boolean;           // 一次通过（BR-009 统计）
  reviewedAt?: string;
  createdAt: string;
}
```

#### 2.5.2 GET /admin-api/ims/content/review/{reviewNo} — 审核单详情

**响应** `data`：`ContentReviewVO` + `checklist: Array<{ itemCode: string; itemDesc: string; passed?: boolean }>`（审核维度：合规/质量清单/品牌一致性）。

#### 2.5.3 PUT /admin-api/ims/content/review/{reviewNo}/conclusion — 提交审核结论

**请求**：

```typescript
interface ReviewConclusionReq {
  conclusion: 'PASS' | 'REJECT_BACK' | 'TERMINATE';
  checklistResult: Record<string, boolean>;
  /** 打回必须选择具体未通过项（REV-R2，错误码 1058） */
  rejectItems?: Array<{ itemCode: string; reason: string }>;
  /** 打回回到指定 SOP/DAG 节点 */
  backToNodeName?: string;
}
```

**响应**：`data: null`。**审核人不可审自己提交的内容（REV-R1，错误码 1057）**；第 3 轮仍打回自动升级运营总监裁决（REV-R3）；审核 SLA 12 小时超时督办（REV-R4）。

#### 2.5.4 GET /admin-api/ims/content/review/first-pass-stats — 一次通过率统计

**响应** `data`：`{ firstPassRate: number; total: number; trend: Array<{ date: string; rate: number }> }`（BR-009 目标 > 70%）。

#### 2.5.5 GET /admin-api/ims/content/review/reject-analysis — 打回原因分析

**响应** `data`：`{ byItem: Array<{ itemCode: string; itemDesc: string; count: number; ratio: number }> }`

### 2.6 发布归档（CONTENT-006）

#### 2.6.1 POST /admin-api/ims/content/publish — 创建发布单

**请求**：

```typescript
interface ContentPublishCreateReq {
  contentProjectId: number;
  accountId: number;             // 发布账号（08 联动）
  platform: PlatformType;
  planPublishAt: string;
  /** 文案/话题 */
  caption?: string;
  topicTags?: string[];
}
```

**前置校验**：仅审核通过（结论=PASS）内容可创建发布单（PUB-R1，**错误码 1054**）。

**响应** `data`：

```typescript
interface ContentPublishVO {
  id: number;
  publishNo: string;             // PB+日期+流水
  contentProjectId: number;
  accountId: number;
  accountNo: string;
  platform: PlatformType;
  planPublishAt: string;
  publishUrl?: string;           // 发布链接回执
  publishStatus: 'PENDING_PUBLISH' | 'PUBLISHED' | 'ARCHIVED' | 'PUBLISH_FAILED';   // 0 待发布 / 1 已发布 / 2 已归档 / 3 发布失败
  operatorUserId: number;
  archiveId?: number;
  createdAt: string;
}
```

#### 2.6.2 GET /admin-api/ims/content/publish/list — 发布单列表（分页）

**请求**（Query）：`PageParam` + `{ publishStatus?: string; accountId?: number; platform?: PlatformType; timeRange?: [string, string] }` → **响应**：`PageResult<ContentPublishVO>`

#### 2.6.3 PUT /admin-api/ims/content/publish/{id}/receipt — 回填发布链接

**请求**：`{ publishUrl: string; publishedAt: string }` → **响应**：`data: null`。发布后 24 小时内回填，超时督办（PUB-R2）；回填后自动触发归档打包（PUB-R3）。

#### 2.6.4 GET /admin-api/ims/content/publish/{id}/archive — 归档包详情

**响应** `data`：

```typescript
interface ContentArchiveVO {
  id: number;
  archiveNo: string;
  contentProjectId: number;
  /** 打包文件下载地址（服务端文件目录；源片+脚本+审核单+回执） */
  packageUrl: string;
  fileList: Array<{ fileName: string; fileType: 'VIDEO' | 'SCRIPT' | 'REVIEW' | 'RECEIPT'; fileKey: string }>;
  archivedAt: string;
}
```

归档包保留期 ≥ 2 年，删除需 R1 审批（PUB-R4）。

#### 2.6.5 GET /admin-api/ims/content/publish/pending — 待发布/待回填督办列表

**请求**（Query）：`PageParam` + `{ overdueOnly?: boolean }` → **响应**：`PageResult<{ publishNo: string; contentTitle: string; planPublishAt: string; operatorName: string; publishStatus: string; overdueHours: number }>`

---

## 3. 状态机与业务约束

### 3.1 状态机

**AI 生产任务（AiJobStatus，映射 PRD 5.23.2 TINYINT 0~5）**：

```
WAITING（待生成）──run 启动──▶ GENERATING（生成中，DAG 逐节点执行）
      │                          │ │
      │                    节点失败×2 ──▶ FAILED（告警，AIP-R2）
      │                          │ 成片产出
      │                          ▼
      │               PENDING_FINAL_REVIEW（待终审）
      │                    │              │
      │                终审通过         打回指定节点
      │                    ▼              │（retry-node，非全链重跑）
      │           REVIEW_PASSED           ▼
      │           （移交 CONTENT-006 发布）──▶ GENERATING（定向重生成）
      │
      └──60 分钟全链超时──▶ FAILED（1056 告警，AIP-R4）
```

**选题（topicStatus）**：`PENDING_REVIEW → APPROVED_PROJECT（立项：创建内容项目挂 SOP）/ REJECTED（落选归档，可复活）/ CANCELLED`

**脚本（status）**：`DRAFT（AI 候选+人工编辑，版本递增）→ FINALIZED（定稿锁定）`

**审核单（conclusion）**：`未结论 → PASS（发布准备）/ REJECT_BACK（回到指定节点，轮次+1）/ TERMINATE`；第 3 轮打回升 R4 裁决。

**发布单（publishStatus）**：`PENDING_PUBLISH → PUBLISHED（24h 回填链接）→ ARCHIVED（自动打包）/ PUBLISH_FAILED`

**内容项目总链（ContentStatus）**：`DRAFT → IN_PROGRESS（SOP 节点流转）→ PENDING_REVIEW → APPROVED → PUBLISHED → ARCHIVED`

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-008 | SOP 覆盖率 > 90%（挂接启用版本才可立项） | 2.2.4（sopId 必填）、SOP-R1 |
| BR-009 | 一次审核通过率 > 70% | 2.5.4 firstPass 统计 |
| BR-010 | ComfyUI 链路跑通 ≥ 1 条 | 2.4.x 全链 + 2.4.8/2.4.9 |
| SOP-R1~R4 | 挂接启用版/清单全过+交付物/旧版沿用/SLA 督办 | 2.1.x（错误码 1007/1051） |
| TOP-R1~R3 | 立项必填发布日+SOP/落选可复活/冲突不阻断 | 2.2.x（错误码 1052） |
| SCR-R1~R3 | 人工确认定稿/版本回溯/提示词快照 | 2.3.x（错误码 1053） |
| AIP-R1~R5 | 提示词留版/重试 2 次/定向打回/60 分钟超时/终审前禁发布 | 2.4.x（错误码 1054/1055/1056） |
| REV-R1~R4 | 回避/结构化打回/3 轮升级/12h SLA | 2.5.x（错误码 1057/1058） |
| PUB-R1~R4 | 审核通过才发布/24h 回填/自动归档/保留 2 年 | 2.6.x（错误码 1054） |
| V1-C1~C6 | ComfyUI API 桥接/五级队列/GPU 监控/超时重试/服务端文件目录产物/并发约束 | 2.4.8/2.4.9（错误码 5004） |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| SOP 管理页（QueryBar+表格） | SOP 列表查询 | GET /content/sop/list |
| SOP 编辑抽屉（节点序列编辑器） | 创建/编辑 SOP 及节点 | POST /content/sop、PUT /content/sop/{id} |
| SOP 详情抽屉-节点 Tab | 节点标准/交付物/清单查看 | GET /content/sop/{id}/nodes |
| 内容项目-节点执行抽屉 | 上传交付物 + 勾选质量清单提交 | POST /content/sop/node/{nodeId}/check |
| 选题池页（QueryBar+表格+提报抽屉） | 提报/列表/编辑选题 | POST/GET/PUT /content/topic* |
| 选题评审抽屉（R4） | 评审立项（选 SOP+发布日）/落选 | PUT /content/topic/{id}/review |
| 排期甘特看板 | 甘特视图渲染 | GET /content/topic/gantt |
| AI 脚本工作台（编辑器+版本对比） | 生成候选/编辑/定稿/版本历史 | POST /content/script/generate、PUT /content/script/{id}、PUT /content/script/{id}/finalize、GET /content/script/{id}/versions |
| 脚本列表页 | 脚本查询 | GET /content/script/list |
| AI 生产任务页（任务列表+详情抽屉） | 任务列表查询（关键字/状态筛选分页） | GET /content/ai-production/task/page |
| AI 生产任务页（任务列表+详情抽屉） | 创建任务/查看 DAG 状态 | POST /content/ai-production/task、GET /content/ai-production/task/{taskNo} |
| 任务详情-提示词编辑区 | 修改提示词（版本留痕） | PUT /content/ai-production/task/{taskNo}/prompt |
| 任务详情-启动按钮 | 启动工作流（提交 Job 队列） | POST /content/ai-production/task/{taskNo}/run（内部 → POST /content/ai-job/submit） |
| 任务详情-DAG 执行记录 Tab | 节点运行/重试/产物查看 | GET /content/ai-production/runs/{taskNo}、GET /content/ai-job/{id}/status |
| 任务详情-终审操作 | 人工终审（通过/打回节点） | PUT /content/ai-production/task/{taskNo}/review、POST .../retry-node |
| 审核队列页（R8 主责，超期高亮） | 队列查询 | GET /content/review/queue |
| 审核单详情抽屉（在线预览+清单勾选） | 提交结论（通过/打回/驳回） | PUT /content/review/{reviewNo}/conclusion |
| 审核统计看板 | 一次通过率/打回原因分析 | GET /content/review/first-pass-stats、GET /content/review/reject-analysis |
| 发布管理页（表格+发布抽屉） | 创建发布单/列表查询 | POST /content/publish、GET /content/publish/list |
| 发布单详情抽屉-回填操作 | 回填发布链接（触发自动归档） | PUT /content/publish/{id}/receipt |
| 归档包详情 | 查看/下载归档包 | GET /content/publish/{id}/archive |
| 发布督办列表 | 待发布/待回填查询 | GET /content/publish/pending |

（全文完）
