# FLOW - 工作流管理 API 契约

> **模块范围**：14 工作流管理（V2，第 15~18 周，V2.1 批次）——FLOW-001 模板设计器、FLOW-002 任务分派与看板、FLOW-003 版本管理（P2）、FLOW-004 超时提醒与统计。
> **权威依据**：《IMS第二期PRD-V2.md》5.12~5.15；BR-115；V2-D1~D4 工作流引擎选型（Flowable 7.x 嵌入式优先）；V2-A1（SLA 超时扫描任务集群化）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`assignee_rule → assigneeRule`、`sla_hours → slaHours`）；周次波浪号格式。

---

## 1. API 总览表（共 22 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/flow/template` | 创建流程模板 | R1/R4（业务）/R2（行政）/R3（财务） |
| 2 | GET | `/admin-api/ims/flow/template/list` | 模板列表（分页） | 同上 + 只读角色 |
| 3 | PUT | `/admin-api/ims/flow/template/{id}` | 编辑模板（草稿态） | 同 1 |
| 4 | POST | `/admin-api/ims/flow/template/{id}/publish` | 发布模板（DAG 校验） | 同 1 |
| 5 | GET | `/admin-api/ims/flow/template/{id}/preview` | 流程图预览数据 | R1/R4/R2/R3 |
| 6 | POST | `/admin-api/ims/flow/instance` | 发起流程实例 | 按模板配置的发起权限 |
| 7 | GET | `/admin-api/ims/flow/task/my-todo` | 我的待办（分页） | 处理人本人（R5/R6/R8/R10 被指派） |
| 8 | GET | `/admin-api/ims/flow/task/my-initiated` | 我发起的（分页） | 发起人本人 |
| 9 | GET | `/admin-api/ims/flow/task/my-handled` | 我已处理（分页） | 处理人本人 |
| 10 | PUT | `/admin-api/ims/flow/task/{id}/handle` | 处理任务（通过/退回） | 节点处理人 |
| 11 | PUT | `/admin-api/ims/flow/task/{id}/transfer` | 转交任务（一次一跳留痕） | 节点处理人 |
| 12 | GET | `/admin-api/ims/flow/instance/{instanceNo}` | 实例详情（含流转轨迹） | R1/本域看板/发起人/处理人 |
| 13 | GET | `/admin-api/ims/flow/instance/board` | 全局看板（进行中/超时/节点分布） | R1/R2/R3/R4（本域）/R9（只读） |
| 14 | PUT | `/admin-api/ims/flow/instance/{instanceNo}/revoke` | 撤销实例（进行中） | 发起人/R1 |
| 15 | GET | `/admin-api/ims/flow/version/list` | 版本列表 | R1/R4/R2/R3（本域） |
| 16 | GET | `/admin-api/ims/flow/version/diff` | 版本 Diff | 同上 |
| 17 | POST | `/admin-api/ims/flow/version/{templateId}/rollback` | 回滚（生成新版本指向旧配置） | R1 |
| 18 | GET | `/admin-api/ims/flow/version/snapshot` | 版本快照查询 | 同 15 |
| 19 | GET | `/admin-api/ims/flow/timeout/list` | 超时任务清单（分页） | R1/R2/R3/R4（本域）/处理人（本人） |
| 20 | GET | `/admin-api/ims/flow/timeout/rate` | 超时率统计（BR-115） | R1/R2/R3/R4/R9 |
| 21 | GET | `/admin-api/ims/flow/timeout/distribution` | 按模板/节点/人分布 | 同上 |
| 22 | PUT | `/admin-api/ims/flow/timeout/{id}/urge` | 手动督办 | R1/R2/R3/R4（本域） |

---

## 2. 接口明细

### 2.1 工作流模板设计器（FLOW-001）

#### 2.1.1 POST /admin-api/ims/flow/template — 创建模板

**请求**：

```typescript
interface FlowTemplateCreateReq {
  templateName: string;
  businessDomain: 'ADMIN' | 'FINANCE' | 'BUSINESS' | 'COMMON';   // 行政/财务/业务/通用
  nodes: Array<{
    nodeOrder: number;
    nodeName: string;
    /** 节点类型（Flowable 嵌入式映射，V2-D1） */
    nodeType: 'APPROVE' | 'TASK' | 'CC' | 'TIMER';
    /** 处理人规则：人/岗位/部门/发起人直属上级（动态解析，FLO-T-R2） */
    assigneeRule: {
      assignType: 'USER' | 'POSITION' | 'DEPT' | 'INITIATOR_SUPERIOR';
      targetIds?: number[];
      targetPositionCodes?: string[];
      targetDeptId?: number;
    };
    slaHours?: number;           // SLA 时限
    /** 分支条件（条件分支节点，JSON 表达式由引擎解析） */
    conditionExpr?: Array<{ expression: string; nextNodeOrder: number }>;
    /** 节点表单字段定义 */
    formFields?: Array<{ fieldKey: string; fieldLabel: string; fieldType: string; required: boolean }>;
    /** 并行/汇合标记（FLO-I-R1：并行节点全部完成才进入汇合后节点） */
    parallelGroup?: string;
  }>;
}
```

**响应** `data`：

```typescript
interface FlowTemplateVO {
  id: number;
  templateNo: string;            // FT+日期+流水
  templateName: string;
  businessDomain: 'ADMIN' | 'FINANCE' | 'BUSINESS' | 'COMMON';
  version: number;
  status: 'DRAFT' | 'PUBLISHED' | 'DISABLED';   // 0 草稿 / 1 已发布 / 2 停用
  publishedAt?: string;
  nodes: FlowTemplateCreateReq['nodes'];
  createdBy: number;
  createdAt: string;
}
```

**错误码**：1131（DAG 校验失败：缺起止节点/存在环路，FLO-T-R1）、1132（处理人规则非法，如 INITIATOR_SUPERIOR 解析失败）、1001（参数校验）。

#### 2.1.2 GET /admin-api/ims/flow/template/list — 模板列表（分页）

**请求**（Query）：`PageParam` + `{ templateName?: string; businessDomain?: string; status?: 'DRAFT' | 'PUBLISHED' | 'DISABLED' }`

**响应** `data`：`PageResult<FlowTemplateVO>`（R2 限行政域、R3 限财务域、R4 限业务+通用域）。

#### 2.1.3 PUT /admin-api/ims/flow/template/{id} — 编辑模板

**请求**：`FlowTemplateCreateReq` → **响应** `data`：`FlowTemplateVO`。仅 `DRAFT` 状态可编辑；`PUBLISHED` 模板修改须走新版本（FLOW-003，FLO-T-R3）。

**错误码**：1133（已发布模板不可直接编辑，须升版本）。

#### 2.1.4 POST /admin-api/ims/flow/template/{id}/publish — 发布

**响应** `data`：`FlowTemplateVO`（状态 → `PUBLISHED`，触发 DAG 校验 + 版本快照落库）。

**错误码**：1131（DAG 校验失败）。

#### 2.1.5 GET /admin-api/ims/flow/template/{id}/preview — 流程图预览

**请求**（Query）：`{ version?: number }` → **响应** `data`：`{ nodes: Array<{ nodeOrder: number; nodeName: string; nodeType: string; slaHours?: number; assigneePreview: string }>; edges: Array<{ fromNodeOrder: number; toNodeOrder: number; conditionLabel?: string }>; graphType: 'SERIAL' | 'PARALLEL' | 'CONDITIONAL' }`（前端流程图渲染数据）。

#### 2.1.6 POST /admin-api/ims/flow/instance — 发起流程实例

**请求**：

```typescript
interface FlowInstanceStartReq {
  templateId: number;
  formData: Record<string, string | number | null>;   // 按首节点 formFields
  /** 幂等：重复提交防重（clientToken 请求头同效） */
  businessKey?: string;
}
```

**响应** `data`：

```typescript
interface FlowInstanceVO {
  id: number;
  instanceNo: string;            // FI+日期+流水
  templateId: number;
  templateVersion: number;
  initiatorUserId: number;
  initiatorName: string;
  formData: Record<string, string | number | null>;
  currentNodes: Array<{ nodeOrder: number; nodeName: string; assigneeUserId: number; assigneeName: string; slaDeadline?: string }>;
  instanceStatus: 'RUNNING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'TIMEOUT';   // FlowInstanceStatus
  startedAt: string;
  finishedAt?: string;
}
```

**错误码**：1134（仅最新发布版本可发起新实例，FLO-V-R1）、1136（无该模板发起权限）。

### 2.2 任务分派与看板（FLOW-002）

#### 2.2.1 GET /admin-api/ims/flow/task/my-todo — 我的待办（分页）

**请求**（Query）：`PageParam` + `{ businessDomain?: string }` → **响应** `data`：`PageResult<FlowTaskVO>`

```typescript
interface FlowTaskVO {
  id: number;
  instanceNo: string;
  instanceStatus: 'RUNNING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'TIMEOUT';
  templateName: string;
  nodeOrder: number;
  nodeName: string;
  nodeType: 'APPROVE' | 'TASK' | 'CC' | 'TIMER';
  assigneeUserId: number;
  assigneeName: string;
  taskStatus: 'PENDING' | 'APPROVED' | 'REJECTED' | 'TRANSFERRED';   // 0 待处理/1 已通过/2 已退回/3 转交
  initiatorUserId: number;
  initiatorName: string;
  formData: Record<string, string | number | null>;
  slaDeadline?: string;
  isTimeout: boolean;
  handledAt?: string;
  comment?: string;
  startedAt: string;
}
```

#### 2.2.2 GET /admin-api/ims/flow/task/my-initiated — 我发起的（分页）

**请求**（Query）：`PageParam` + `{ instanceStatus?: string }` → **响应** `data`：`PageResult<FlowInstanceVO>`。

#### 2.2.3 GET /admin-api/ims/flow/task/my-handled — 我已处理（分页）

**请求**（Query）：`PageParam` + `{ taskStatus?: 'APPROVED' | 'REJECTED' | 'TRANSFERRED' }` → **响应** `data`：`PageResult<FlowTaskVO & { durationMinutes: number }>`（处理时效计入时效档案，FLO-O-R3 供绩效取数）。

#### 2.2.4 PUT /admin-api/ims/flow/task/{id}/handle — 处理任务

**请求**：

```typescript
interface FlowTaskHandleReq {
  action: 'APPROVE' | 'REJECT';
  comment?: string;
  /** 退回目标节点（REJECT 时可选，默认回发起节点） */
  rejectToNodeOrder?: number;
  /** 节点表单数据补充 */
  formDataPatch?: Record<string, string | number | null>;
}
```

**响应** `data`：`{ taskId: number; instanceNo: string; newStatus: string; nextNodes: Array<{ nodeOrder: number; nodeName: string; assigneeUserId: number }>; isInstanceFinished: boolean }`

**错误码**：1135（非该任务处理人）、1137（并行汇合约束：需其他并行分支完成后才流转）。

#### 2.2.5 PUT /admin-api/ims/flow/task/{id}/transfer — 转交任务

**请求**：`{ toUserId: number; transferReason: string }` → **响应**：`data: null`。转交一次一跳留痕（FLO-I-R2）；被转交人成为新处理人。

**错误码**：1135（非处理人）、1138（转交目标人无效或与当前处理人相同）。

#### 2.2.6 GET /admin-api/ims/flow/instance/{instanceNo} — 实例详情

**响应** `data`：`FlowInstanceVO & { traceLog: Array<{ nodeOrder: number; nodeName: string; assigneeUserId: number; assigneeName: string; action: string; comment?: string; actedAt: string; isTimeout: boolean }>; ccRecords: Array<{ nodeOrder: number; ccToUserId: number; ccToName: string; notifiedAt: string }> }`（完整流转轨迹）。

#### 2.2.7 GET /admin-api/ims/flow/instance/board — 全局看板

**请求**（Query）：`{ businessDomain?: string; dateRange?: [string, string] }` → **响应** `data`：`{ runningCount: number; timeoutCount: number; finishedCount: number; byTemplate: Array<{ templateName: string; runningCount: number; timeoutCount: number; avgDurationHours: number }>; byNode: Array<{ nodeName: string; pendingCount: number; timeoutCount: number }>; recentTimeout: FlowTaskVO[] }`（R2/R3/R4 限本域）。

#### 2.2.8 PUT /admin-api/ims/flow/instance/{instanceNo}/revoke — 撤销实例

**响应**：`data: null`。仅 `RUNNING` 状态可撤销；已完成节点留痕（FLO-I-R3），实例状态 → `CANCELLED`。

**错误码**：1139（非发起人且非 R1，无权撤销）、1140（实例已终态不可撤销）。

### 2.3 模板版本管理（FLOW-003）

#### 2.3.1 GET /admin-api/ims/flow/version/list — 版本列表

**请求**（Query）：`{ templateId: number }` → **响应** `data`：`Array<{ templateId: number; version: number; changeDesc?: string; publishedBy: number; publishedByName: string; publishedAt: string; status: 'CURRENT' | 'HISTORICAL' | 'ROLLED_BACK' }>`。

#### 2.3.2 GET /admin-api/ims/flow/version/diff — 版本 Diff

**请求**（Query）：`{ templateId: number; fromVersion: number; toVersion: number }` → **响应** `data`：`{ nodeChanges: Array<{ changeType: 'ADDED' | 'REMOVED' | 'MODIFIED'; nodeOrder: number; nodeName: string; detail: Record<string, { oldValue?: unknown; newValue?: unknown }> }>; configChanges: Array<{ key: string; oldValue?: unknown; newValue?: unknown }> }`。

#### 2.3.3 POST /admin-api/ims/flow/version/{templateId}/rollback — 回滚

**请求**：`{ targetVersion: number; changeDesc: string }` → **响应** `data`：`{ newVersion: number; targetVersion: number }`。回滚生成新版本号（指向旧配置快照），不做物理回退（FLO-V-R2）；在途实例按原版本继续运行。

**错误码**：1134（版本约束拦截——目标版本不存在或为草稿版本；语义族扩展：1134 覆盖"仅最新发布版本可发起新实例"与"回滚目标版本非法"两类版本约束，段内归并避免跨段）。

#### 2.3.4 GET /admin-api/ims/flow/version/snapshot — 版本快照

**请求**（Query）：`{ templateId: number; version: number }` → **响应** `data`：`FlowTemplateVO`（版本全量快照，不可修改，FLO-V-R3）。

### 2.4 超时提醒与统计（FLOW-004）

#### 2.4.1 GET /admin-api/ims/flow/timeout/list — 超时任务清单（分页）

**请求**（Query）：`PageParam` + `{ businessDomain?: string; assigneeUserId?: number; templateName?: string }` → **响应** `data`：`PageResult<FlowTaskVO & { slaHours: number; timeoutAt: string; timeoutDurationMinutes: number; remindCount: number; isEscalated: boolean }>`（超时 24 小时未处理升级推送节点责任人上级+流程域负责人，FLO-O-R2）。

#### 2.4.2 GET /admin-api/ims/flow/timeout/rate — 超时率（BR-115）

**请求**（Query）：`{ statMonth?: string }` → **响应** `data`：`{ monthlyTimeoutRate: number; targetRate: number; byDomain: Array<{ businessDomain: string; timeoutRate: number }>; trend: Array<{ statMonth: string; timeoutRate: number }> }`（BR-115：超时节点数/执行节点总数（月度），目标 < 10%）。

#### 2.4.3 GET /admin-api/ims/flow/timeout/distribution — 分布统计

**请求**（Query）：`{ statMonth?: string; dimension: 'TEMPLATE' | 'NODE' | 'DEPT' | 'PERSON' }` → **响应** `data`：`Array<{ dimensionValue: string; timeoutCount: number; totalExecuted: number; timeoutRate: number; avgTimeoutMinutes: number }>`。

#### 2.4.4 PUT /admin-api/ims/flow/timeout/{id}/urge — 手动督办

**请求**：`{ urgeMessage?: string }` → **响应**：`data: null`。推送处理人（钉钉强提醒）+ `remindCount` 递增。

---

## 3. 状态机与业务约束

### 3.1 状态机

**流程实例（FlowInstanceVO.instanceStatus，全局枚举 FlowInstanceStatus）**：

```
RUNNING ──终止节点全部通过──▶ APPROVED
   │    ──任一审批节点拒绝──▶ REJECTED
   │    ──发起人撤销（已完成节点留痕）──▶ CANCELLED
   └─────节点 SLA 超时（任务级标记，实例保持 RUNNING；整实例超时告警）──▶ TIMEOUT（实例级异常标记）
```

**任务（FlowTaskVO.taskStatus）**：

```
PENDING ──处理通过──▶ APPROVED（流转下一节点）
   │     ──退回──▶ REJECTED（回指定节点/发起节点）
   │     ──转交（一次一跳）──▶ TRANSFERRED（新任务 PENDING 指向被转交人）
```

**模板（FlowTemplateVO.status）**：`DRAFT → PUBLISHED → DISABLED`（发布后修改走新版本；回滚生成新版本号）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-115 | 节点超时率 < 10%（月度） | 2.4.2 |
| FLO-T-R1 | 起止节点齐全、无环路（DAG 校验） | 2.1.1/2.1.4 错误码 1131 |
| FLO-T-R2 | 处理人支持"发起人直属上级"动态解析 | 2.1.1 assigneeRule |
| FLO-T-R3 | 发布后修改走新版本，在途实例沿用原版 | 2.1.3 错误码 1133 |
| FLO-I-R1 | 并行节点全部完成才进汇合后节点 | 2.2.4 错误码 1137 |
| FLO-I-R2 | 转交一次一跳留痕 | 2.2.5 |
| FLO-I-R3 | 撤销留痕已完成节点 | 2.2.8 |
| FLO-V-R1 | 仅最新发布版本可发起新实例 | 2.1.6 错误码 1134 |
| FLO-V-R2 | 回滚生成新版本号，不物理回退 | 2.3.3 |
| FLO-V-R3 | 版本快照不可修改 | 2.3.4 |
| FLO-O-R1 | 超时率月度统计 | 2.4.2 |
| FLO-O-R2 | 超时 24h 升级推送（上级+域负责人） | 2.4.1 isEscalated |
| FLO-O-R3 | 超时完成时间差计入时效档案（绩效取数） | 2.2.3 durationMinutes |
| V2-D1~D4 | Flowable 7.x 嵌入式优先（D2：模板/实例 API 包一层 IMS 契约，前端不直连 Flowable 原生 REST） | 全模块（nodeType 映射 BPMN） |
| V2-A1 | SLA 超时扫描定时任务集群化（Redisson 锁） | 2.4.x 扫描任务 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 流程模板管理页（QueryBar + 表格） | 模板列表查询（业务域/状态筛选） | GET /flow/template/list |
| 模板设计器（画布拖拽编排 + 节点属性面板） | 创建/编辑模板（串行/并行/条件分支） | POST /flow/template、PUT /flow/template/{id} |
| 设计器-预览 | 流程图渲染预览 | GET /flow/template/{id}/preview |
| 设计器-发布 | 发布（DAG 校验失败内联提示） | POST /flow/template/{id}/publish |
| 流程发起页（动态表单按 formFields 渲染） | 发起流程实例 | POST /flow/instance |
| 个人工作台-我的待办（Tab：待办/发起/已处理） | 三视图列表加载 | GET /flow/task/my-todo、/my-initiated、/my-handled |
| 任务处理抽屉（DetailDrawer 内联） | 通过 / 退回（选退回节点）/ 转交 | PUT /flow/task/{id}/handle、/transfer |
| 实例详情页（流转轨迹时间轴） | 实例详情（轨迹+抄送记录） | GET /flow/instance/{instanceNo} |
| 实例详情-撤销 | 撤销进行中实例（ConfirmDialog） | PUT /flow/instance/{instanceNo}/revoke |
| 全局看板页 | 进行中/超时/节点分布看板 | GET /flow/instance/board |
| 版本管理页 | 版本列表 / Diff 对比 / 回滚 | GET /flow/version/list、/diff、POST /flow/version/{templateId}/rollback |
| 版本快照查看 | 版本快照只读展示 | GET /flow/version/snapshot |
| 超时督办页 | 超时清单查询 / 手动督办 | GET /flow/timeout/list、PUT /flow/timeout/{id}/urge |
| 超时统计看板 | 超时率 / 分布统计（BR-115） | GET /flow/timeout/rate、/distribution |

（全文完）
