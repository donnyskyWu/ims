# FLOW - 工作流管理 页面规格

> 依据：《IMS第二期PRD-V2.md》5.12~5.15（FLOW-001~004）、《共享技术规范-分期技术约束.md》V2-D1~D4（Flowable 7.x 嵌入式）、V2-A1（SLA 超时扫描集群化）、《FLOW-工作流管理-API契约.md》、《全局开发规范.md》第 4 章（权威枚举）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus + 自研画布（ECharts graph / LogicFlow）；API 前缀 `/admin-api/ims/flow`。
> 归属期次：V2 第 15~18 周（V2.1 管理动作线上化批次；FLOW-003 为 P2）。
> **引擎约束（V2-D2）**：模板/实例 API 均为 IMS 契约层封装，前端**不直连 Flowable 原生 REST**；nodeType 映射 BPMN 由后端完成。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 流程模板管理 | `/ims/flow/template` | 一级菜单页（列表 + 设计器抽屉/全屏） | FLOW-001 |
| P2 我的流程工作台 | `/ims/flow/task` | 一级菜单页（三 Tab 个人视图） | FLOW-002 |
| P3 流程看板 | `/ims/flow/board` | 一级菜单页（管理视角聚合看板） | FLOW-002 |
| P4 版本管理 | `/ims/flow/version/{templateId}` | 二级页面（版本列表 + Diff + 回滚） | FLOW-003 |
| P5 超时督办与统计 | `/ims/flow/timeout` | 一级菜单页（清单 + 统计看板） | FLOW-004 |

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；任务处理等交互优先内联抽屉（Drawer），不跳转新页面；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红 / 中性灰）；
- 周次/月份展示用波浪号格式；
- 枚举一律引用《全局开发规范.md》第 4 章：`FlowInstanceStatus`、`FlowNodeStatus`、`EnableStatus`。

---

## P1. 流程模板管理（FLOW-001）

### 1. 页面概述
- 路由路径：`/ims/flow/template`
- 页面级别：一级菜单页（模板列表 + 设计器：抽屉式起步、画布可全屏）
- 依赖模块：AUTH 人员/岗位/部门选择器（assigneeRule）、FLOW-003 版本管理（发布联动）、REPORT/MEET 等上游模块（流程消费方）
- 权限矩阵引用（PRD 4.2 FLOW-001）：R1 R/W/D（全量）、R4 R/W（业务域）、R2 R/W（行政域）、R3 R/W（财务域）；businessDomain 路由 ADMIN/FINANCE/BUSINESS/COMMON

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 模板名称 | 业务域 | 状态 | [查询][重置]      [创建模板]    |
+------------------------------------------------------------------+
| 模板列表表格:                                                     |
| 编号|模板名称|业务域|节点数|当前版本|状态|发布时间|创建人|操作        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
设计器(抽屉 90% 可全屏):
  左侧: 节点物料面板(审批/任务/抄送/定时 四类节点拖入)
  中央: 流程画布(节点卡片+连线: 串行/并行/条件分支)
  右侧: 节点属性面板(选中节点时):
    节点名称* | 节点类型 | 处理人规则*(人/岗位/部门/发起人直属上级)
    SLA 时限(小时) | 条件分支表达式(条件节点) | 表单字段编辑器
    并行组标记(parallelGroup)
  顶部: [预览流程图] [保存草稿] [发布]
发起流程抽屉(640px): 动态表单(按首节点 formFields 渲染) → [提交发起]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FlowTemplateCreateReq {
  templateName: string;             // 必填 ≤128 字
  businessDomain: FlowDomain;       // ADMIN / FINANCE / BUSINESS / COMMON
  nodes: FlowNodeConfig[];
  clientToken: string;
}
interface FlowNodeConfig {
  nodeOrder: number;                // 必填 连续
  nodeName: string;                 // 必填 ≤64 字
  nodeType: FlowNodeType;           // APPROVE / TASK / CC / TIMER
  assigneeRule: {                   // CC/TIMER 可空
    assignType: AssignRuleType;     // USER / POSITION / DEPT / INITIATOR_SUPERIOR
    targetIds?: number[];
    targetPositionCodes?: string[];
    targetDeptId?: number;
  };
  slaHours?: number;                // SLA 时限
  conditionExpr?: Array<{ expression: string; nextNodeOrder: number }>;   // 条件分支
  formFields?: Array<{ fieldKey: string; fieldLabel: string; fieldType: string; required: boolean }>;
  parallelGroup?: string;           // 并行/汇合标记（FLO-I-R1）
}
interface FlowInstanceStartReq {
  templateId: number;
  formData: Record<string, string | number | null>;   // 按首节点 formFields
  businessKey?: string;             // 幂等键
}

// 响应类型
interface FlowTemplateVO {
  id: number;
  templateNo: string;               // FT+日期+流水
  templateName: string;
  businessDomain: FlowDomain;
  version: number;
  status: FlowTemplateStatus;       // DRAFT / PUBLISHED / DISABLED
  publishedAt?: string;
  nodes: FlowNodeConfig[];
  createdBy: number;
  createdAt: string;
}
interface FlowTemplatePreviewResp {
  nodes: Array<{
    nodeOrder: number; nodeName: string;
    nodeType: string; slaHours?: number;
    assigneePreview: string;        // 处理人规则解析预览文案
  }>;
  edges: Array<{ fromNodeOrder: number; toNodeOrder: number; conditionLabel?: string }>;
  graphType: 'SERIAL' | 'PARALLEL' | 'CONDITIONAL';
}
interface FlowInstanceVO {
  id: number;
  instanceNo: string;               // FI+日期+流水
  templateId: number;
  templateVersion: number;
  initiatorUserId: number;
  initiatorName: string;
  formData: Record<string, string | number | null>;
  currentNodes: Array<{
    nodeOrder: number; nodeName: string;
    assigneeUserId: number; assigneeName: string;
    slaDeadline?: string;
  }>;
  instanceStatus: FlowInstanceStatus;   // RUNNING/APPROVED/REJECTED/CANCELLED/TIMEOUT
  startedAt: string;
  finishedAt?: string;
}

// 枚举类型
type FlowDomain = 'ADMIN' | 'FINANCE' | 'BUSINESS' | 'COMMON';       // 行政/财务/业务/通用
type FlowNodeType = 'APPROVE' | 'TASK' | 'CC' | 'TIMER';             // 审批/任务/抄送/定时
type FlowTemplateStatus = 'DRAFT' | 'PUBLISHED' | 'DISABLED';
type AssignRuleType = 'USER' | 'POSITION' | 'DEPT' | 'INITIATOR_SUPERIOR';
// FlowInstanceStatus —— 全局权威枚举（实例粒度）
// FlowNodeStatus —— 全局权威枚举（任务粒度，P2 使用）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /flow/template/list`（R2 行政域/R3 财务域/R4 业务+通用域，服务端过滤）。失败重试。

#### 4.2 核心操作流程
**A. 创建模板（R1/R4/R2/R3 本域）**
1. [创建模板] → 设计器抽屉（90%，可全屏）：左侧节点物料（审批/任务/抄送/定时拖入画布）；
2. 画布编排：拖拽节点卡 + 连线（串行直线/并行分支/条件分支线带表达式标签）；选中节点 → 右侧属性面板配置：
   - 处理人规则四选一：按人（人员多选）/按岗位（岗位多选）/按部门（部门树选择）/发起人直属上级（动态解析 FLO-T-R2，INITIATOR_SUPERIOR 预览提示"运行时按发起人组织解析"）；
   - SLA 时限（小时，正整数）；条件节点 → 分支表达式编辑（表达式 → 目标节点下拉）；表单字段编辑器（key/label/type/required 动态行）；并行组标记（同 parallelGroup 的节点全部完成才汇合，FLO-I-R1）；
3. [预览流程图] → `GET /flow/template/{id}/preview`（保存草稿后可用）→ 画布只读渲染 + assigneePreview 文案；
4. [保存草稿] → `POST /flow/template`；[发布] → `POST /flow/template/{id}/publish`：DAG 校验（起止节点齐全/无环路，FLO-T-R1）失败 → 1131 错误行内定位到缺失/成环节点（画布节点红框）；成功 → 状态 PUBLISHED + 版本快照落库（联动 P4）。

**B. 编辑模板（FLO-T-R3）**
1. `DRAFT` 行 [编辑] → 设计器预填；`PUBLISHED` 行 [编辑] 提示"已发布模板修改须升版本"（1133）→ 引导复制为新版本草稿；
2. 新版本发布后：仅最新发布版本可发起新实例（FLO-V-R1），在途实例沿用原版本。

**C. 发起流程实例（按模板发起权限）**
1. 列表行 [发起流程]（PUBLISHED 且有发起权限）→ 发起抽屉：动态表单按首节点 formFields 渲染（必填校验）；
2. [提交发起]（businessKey 幂等）→ `POST /flow/instance` → 实例 RUNNING，首节点处理人收到待办（P2 联动）。

**D. 停用（R1）**
- [停用] → ConfirmDialog warning："停用后不可发起新实例，在途实例按原版本继续运行" → 状态 DISABLED。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| templateName | Input | 否 | 空 | 模板名称模糊匹配 |
| businessDomain | Select | 否 | 空 | 行政/财务/业务/通用 |
| status | Select | 否 | 空 | 草稿/已发布/停用 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| templateNo | 模板编号 | 140 | — | 等宽字体（FT…） |
| templateName | 模板名称 | 自适应 | — | 行点击打开预览画布 |
| businessDomain | 业务域 | 90 | — | tag：行政(蓝)/财务(橙)/业务(绿)/通用(灰) |
| nodeCount | 节点数 | 80 | — | 数字；悬浮显示节点类型分布 |
| version | 当前版本 | 90 | — | V{n}；可点击跳 P4 版本管理 |
| status | 状态 | 90 | — | tag：草稿(灰)/已发布(绿)/停用(红) |
| publishedAt | 发布时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| createdBy | 创建人 | 100 | — | — |
| actions | 操作 | 210 | — | [发起流程][编辑][预览][停用][版本] 按状态/权限 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 模板设计器 | Drawer 90%（可全屏） | 三栏布局；节点nodeName 必填 ≤64；assigneeRule 必填（APPROVE/TASK 节点）；conditionExpr 分支须指向存在节点；parallelGroup 并行组须 ≥2 节点且同汇合；clientToken 防重 |
| 流程预览 | 画布只读模式 | 节点+连线渲染 + assigneePreview；graphType 标注（串行/并行/条件） |
| 发起流程抽屉 | Drawer 640px | formFields 动态渲染；必填校验；businessKey 幂等提示 |
| 发布确认弹窗 | Modal 400px | DAG 校验结果前置展示（通过/失败明细） |
| 停用确认弹窗 | Modal 400px | warning：在途实例沿用原版本说明 |

### 8. 错误处理
- 1131（DAG 校验失败：缺起止/环路）：画布错误节点红框 + 定位滚动；
- 1132（处理人规则非法，如 INITIATOR_SUPERIOR 无上级可解析）：属性面板行内提示；
- 1133（已发布不可直接编辑）：引导升版本流程；
- 1134（仅最新发布版本可发起）：发起入口仅对最新版本开放；
- 1136（无发起权限）：[发起流程] 按钮隐藏 + 兜底提示；
- 画布保存冲突（多人编辑）：保存时 409 提示刷新后重试。

### 9. BR 业务规则覆盖
- FLO-T-R1（起止齐全无环路，DAG 校验）：发布前置校验 + 1131 定位；
- FLO-T-R2（发起人直属上级动态解析）：assignType=INITIATOR_SUPERIOR + 运行时预览；
- FLO-T-R3（发布后修改走新版本）：1133 + 升版本引导（联动 FLOW-003）；
- V2-D2（不直连 Flowable REST）：本页全部走 IMS 契约层 API。

---

## P2. 我的流程工作台（FLOW-002）

### 1. 页面概述
- 路由路径：`/ims/flow/task`
- 页面级别：一级菜单页，三 Tab：我的待办 / 我发起的 / 我已处理（H5 同构，钉钉内可用）
- 依赖模块：工作台待办（流程任务待办推送）、P1 模板、P5 超时督办
- 权限矩阵引用（PRD 4.2 FLOW-002）：处理人本人（R5/R6/R8/R10 被指派）W；发起人本人 R；R1/R2/R3/R4 管理视角走 P3

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [我的待办(N)] [我发起的] [我已处理]                            |
+------------------------------------------------------------------+
| 查询行: 业务域(待办) | 实例状态(发起) | 处理结果(已处理) | [查询]   |
+------------------------------------------------------------------+
| 待办表格: 实例号|流程|节点|发起人|SLA截止(临期黄/超时红)|状态|操作    |
| 发起表格: 实例号|流程|版本|当前节点(处理人)|实例状态|发起时间|操作    |
| 已处理表格: 实例号|流程|节点|处理动作|意见|处理时长|处理时间         |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
任务处理抽屉(70%):
  Tab: [表单数据] [流转轨迹]
  底部操作: [通过] [退回] [转交]
  退回: 意见* + 退回目标节点(默认发起节点)
  转交: 目标人* + 转交原因*
实例详情抽屉(80%): 表单数据 + 流转轨迹时间轴 + 抄送记录 + [撤销]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface MyTodoReq {
  pageNo: number; pageSize: number;
  businessDomain?: FlowDomain;
}
interface MyInitiatedReq {
  pageNo: number; pageSize: number;
  instanceStatus?: FlowInstanceStatus;
}
interface MyHandledReq {
  pageNo: number; pageSize: number;
  taskStatus?: Exclude<FlowNodeStatus, 'PENDING'>;   // APPROVED/REJECTED/TRANSFERRED
}
interface FlowTaskHandleReq {
  action: 'APPROVE' | 'REJECT';
  comment?: string;                 // 退回建议填写
  rejectToNodeOrder?: number;       // 退回目标节点（默认发起节点）
  formDataPatch?: Record<string, string | number | null>;   // 节点表单补充
}
interface FlowTaskTransferReq {
  toUserId: number;                 // 必选 ≠ 当前处理人
  transferReason: string;           // 必填 ≤512 字
}
interface FlowInstanceRevokeReq {
  instanceNo: string;
}

// 响应类型
interface FlowTaskVO {
  id: number;
  instanceNo: string;
  instanceStatus: FlowInstanceStatus;
  templateName: string;
  nodeOrder: number;
  nodeName: string;
  nodeType: FlowNodeType;
  assigneeUserId: number;
  assigneeName: string;
  taskStatus: FlowNodeStatus;       // PENDING/APPROVED/REJECTED/TRANSFERRED
  initiatorUserId: number;
  initiatorName: string;
  formData: Record<string, string | number | null>;
  slaDeadline?: string;
  isTimeout: boolean;
  handledAt?: string;
  comment?: string;
  startedAt: string;
}
interface MyHandledItem extends FlowTaskVO {
  durationMinutes: number;          // 处理时效（FLO-O-R3 绩效取数源）
}
interface FlowTaskHandleResp {
  taskId: number;
  instanceNo: string;
  newStatus: string;
  nextNodes: Array<{ nodeOrder: number; nodeName: string; assigneeUserId: number }>;
  isInstanceFinished: boolean;
}
interface FlowInstanceDetailVO extends FlowInstanceVO {
  traceLog: Array<{
    nodeOrder: number; nodeName: string;
    assigneeUserId: number; assigneeName: string;
    action: string;
    comment?: string;
    actedAt: string;
    isTimeout: boolean;
  }>;
  ccRecords: Array<{ nodeOrder: number; ccToUserId: number; ccToName: string; notifiedAt: string }>;
}
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载（`GET /flow/task/my-todo` / `my-initiated` / `my-handled`）；待办 Tab 徽标实时数。失败分区重试。

#### 4.2 核心操作流程
**A. 处理任务（节点处理人核心操作）**
1. 待办行 [处理] → 任务处理抽屉（70%）：
   - 表单数据 Tab：发起表单 + 前序节点补充数据（本节点 formFields 可编辑区，formDataPatch）；
   - 流转轨迹 Tab：已流转节点时间轴（处理人/动作/意见/耗时/超时标记）；
2. [通过] → `PUT /flow/task/{id}/handle`（action=APPROVE）→ 返回 nextNodes（下一节点处理人预览）→ 流转；若为终止节点 → isInstanceFinished → 通知发起人；
   - 并行分支：若其他并行分支未完成 → 1137 提示"等待并行分支 X 完成"（FLO-I-R1）；
3. [退回] → 意见（建议填写）+ 退回目标节点下拉（默认发起节点）→ action=REJECT → 任务回到目标节点处理人；
4. [转交] → 转交弹窗：目标人（人员选择，≠ 当前处理人）+ 转交原因必填 → `PUT /flow/task/{id}/transfer`（一次一跳留痕，FLO-I-R2）→ 被转交人成为新处理人，traceLog 记录 TRANSFERRED。

**B. 实例详情与撤销（发起人）**
1. 我发起的 Tab 行 [详情] → 实例详情抽屉（80%）：表单 + 完整流转轨迹 + 抄送记录（CC 节点通知留痕）；
2. [撤销]（RUNNING 状态，发起人/R1）→ ConfirmDialog warning："撤销后已完成节点留痕，实例进入已撤销" → `PUT /flow/instance/{instanceNo}/revoke` → 状态 CANCELLED（FLO-I-R3）。

**C. SLA 视觉提示**
- 待办行 slaDeadline：临期（80% 时限）黄色、超时红色（isTimeout）；TIMER 节点自动流转无人工操作。

### 5. 查询条件表

| Tab | 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|-----|--------|---------|------|--------|------|
| 待办 | businessDomain | Select | 否 | 空 | 业务域 |
| 发起 | instanceStatus | Select | 否 | 空 | RUNNING/APPROVED/REJECTED/CANCELLED/TIMEOUT |
| 已处理 | taskStatus | Select | 否 | 空 | 通过/退回/转交 |

### 6. 表格列定义

**我的待办**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| instanceNo | 实例号 | 140 | — | 等宽字体（FI…） |
| templateName | 流程 | 150 | — | — |
| nodeName | 当前节点 | 120 | — | 节点类型 icon（审批/任务/抄送） |
| initiatorName | 发起人 | 100 | — | — |
| slaDeadline | SLA 截止 | 150 | ✓ 升序 | 临期黄/超时红（isTimeout） |
| startedAt | 到达时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 130 | — | [处理][详情] |

**我发起的**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| instanceNo | 实例号 | 140 | — | 等宽字体 |
| templateName | 流程 | 150 | — | 附 V{templateVersion} |
| currentNodesSummary | 当前节点 | 180 | — | "节点名（处理人）"；并行多节点分行显示 |
| instanceStatus | 实例状态 | 100 | — | tag：进行中(蓝)/已完成(绿)/已退回(红)/已撤销(灰)/超时(橙) |
| startedAt | 发起时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| actions | 操作 | 130 | — | [详情][撤销（RUNNING）] |

**我已处理**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| instanceNo | 实例号 | 140 | — | 等宽字体 |
| templateName | 流程 | 150 | — | — |
| nodeName | 处理节点 | 120 | — | — |
| taskStatus | 处理动作 | 100 | — | tag：通过(绿)/退回(红)/转交(青) |
| comment | 意见 | 自适应 | — | 省略展示 |
| durationMinutes | 处理时长 | 110 | — | "X 小时 Y 分钟"；超时任务红标（时效档案，FLO-O-R3） |
| handledAt | 处理时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 任务处理抽屉 | Drawer 70% | 双 Tab；底部三操作：通过（可附意见）；退回（comment 建议 + rejectToNodeOrder 下拉）；本节点 formFields 可编辑（formDataPatch 必填校验） |
| 转交弹窗 | Modal 480px | toUserId 必选且 ≠ 当前处理人（1138）；transferReason 必填 ≤512 |
| 实例详情抽屉 | Drawer 80% | 表单只读 + 流转轨迹时间轴（action/comment/actedAt/isTimeout）+ 抄送记录 + [撤销]（RUNNING 且发起人/R1） |
| 撤销确认弹窗 | Modal 400px | warning："已完成节点留痕，实例进入已撤销（FLO-I-R3）" |

### 8. 错误处理
- 1135（非该任务处理人）：提示并刷新待办；
- 1137（并行汇合约束）：提示"等待并行分支完成后自动流转"；
- 1138（转交目标无效/同人）：转交弹窗即时校验；
- 1139（非发起人撤销）：撤销按钮隐藏 + 兜底提示；
- 1140（实例已终态）：提示"实例已结束不可撤销"并刷新；
- 提交防重：handle/transfer 按钮 loading + 请求携带幂等（businessKey/taskId 版本号）。

### 9. BR 业务规则覆盖
- FLO-I-R1（并行全完成才汇合）：1137 提示 + 实例 currentNodes 并行多节点展示；
- FLO-I-R2（转交一次一跳留痕）：转交弹窗 + traceLog TRANSFERRED 记录；
- FLO-I-R3（撤销留痕）：撤销确认 + CANCELLED 状态保留轨迹；
- FLO-O-R3（处理时效档案）：已处理 Tab durationMinutes（绩效 PERF 取数源）；
- SLA 临期提醒（PRD 5.15：80% 时限预警一次、超时即时推送）：slaDeadline 三色视觉 + 钉钉推送联动。

---

## P3. 流程看板（FLOW-002 管理视角）

### 1. 页面概述
- 路由路径：`/ims/flow/board`
- 页面级别：一级菜单页（管理视角聚合看板，V1-B 类大屏聚合页保留独立页面）
- 依赖模块：`GET /flow/instance/board`、P2 实例详情、P5 超时督办
- 权限矩阵引用（PRD 4.2 FLOW-002）：R1 R（全量）、R2/R3/R4 R（本域）、R9 R（只读）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 业务域 | 日期范围 | [查询]                                  |
+------------------------------------------------------------------+
| 指标卡: 进行中 N | 超时 N(红) | 已完成 N | 超时率 xx%               |
+------------------------------------------------------------------+
| 左: 按模板分布表(模板|进行中|超时|平均耗时)                        |
| 右: 按节点分布表(节点|待处理|超时)                                  |
+------------------------------------------------------------------+
| 近期超时任务列表(跳 P5 督办)                                       |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FlowBoardReq {
  businessDomain?: FlowDomain;
  dateRange?: [string, string];
}

// 响应类型
interface FlowBoardResp {
  runningCount: number;
  timeoutCount: number;
  finishedCount: number;
  byTemplate: Array<{
    templateName: string;
    runningCount: number; timeoutCount: number;
    avgDurationHours: number;
  }>;
  byNode: Array<{ nodeName: string; pendingCount: number; timeoutCount: number }>;
  recentTimeout: FlowTaskVO[];
}
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /flow/flow/instance/board`（R2/R3/R4 本域服务端过滤）；失败重试；30 秒自动刷新（可暂停）。

#### 4.2 核心操作流程
- 指标卡点击 → 跳转 P5 超时清单（超时卡）或 P2 相关视图过滤；
- byTemplate 行点击 → 该模板实例列表（复用实例详情抽屉）；
- recentTimeout 行点击 → 任务详情（P2 处理抽屉只读）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| businessDomain | Select | 否 | 空 | 业务域 |
| dateRange | DateRangePicker | 否 | 近 30 天 | 实例发起时间 |

### 6. 表格列定义

**按模板分布**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| templateName | 模板 | 自适应 | — | 行点击展开实例列表 |
| runningCount | 进行中 | 90 | — | — |
| timeoutCount | 超时 | 80 | ✓ 降序 | >0 红色 |
| avgDurationHours | 平均耗时 | 110 | — | "X 小时" |

**按节点分布**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| nodeName | 节点 | 160 | — | — |
| pendingCount | 待处理 | 90 | — | — |
| timeoutCount | 超时 | 80 | ✓ 降序 | >0 红色 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 模板实例抽屉 | Drawer 70% | 该模板实例分页列表（复用 FlowInstanceVO 列） |

### 8. 错误处理
- 看板聚合超时：分区降级（指标卡保留，明细表重试）；
- 空数据：空态占位图。

### 9. BR 业务规则覆盖
- BR-115 视图前置：超时指标卡（与 P5 超时率共口径）；
- FLO-O-R2（超时 24h 升级推送）：recentTimeout 列表 isEscalated 标记（P5 详情）。

---

## P4. 版本管理（FLOW-003，P2 优先级）

### 1. 页面概述
- 路由路径：`/ims/flow/version/{templateId}`（从 P1 版本列跳入）
- 页面级别：二级页面（版本列表 + Diff 弹窗 + 快照抽屉 + 回滚）
- 依赖模块：P1 模板、`ims_flow_version_log`
- 权限矩阵引用（PRD 4.2 FLOW-003）：R1 R/W（回滚）；R4/R2/R3 R（本域）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 模板头: {模板名} | FT 编号 | 业务域 | 当前版本 V{n}                 |
+------------------------------------------------------------------+
| 版本列表表格:                                                     |
| 版本|变更说明|发布人|发布时间|状态|操作                              |
+------------------------------------------------------------------+
版本 Diff 弹窗(900px): 左右版本选择
  节点变更: ADD/REMOVE/MODIFIED 标记 + 属性旧值/新值对照
  配置变更: key-value 旧值/新值
版本快照抽屉(80%): 该版本流程图只读渲染 + 节点配置明细
回滚确认弹窗: 目标版本 + 变更说明* → 生成新版本号
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface VersionListReq { templateId: number; }
interface VersionDiffReq { templateId: number; fromVersion: number; toVersion: number; }
interface VersionRollbackReq {
  templateId: number;
  targetVersion: number;            // 必填
  changeDesc: string;               // 必填 ≤512 字
}
interface VersionSnapshotReq { templateId: number; version: number; }

// 响应类型
interface FlowVersionItem {
  templateId: number;
  version: number;
  changeDesc?: string;
  publishedBy: number; publishedByName: string;
  publishedAt: string;
  status: 'CURRENT' | 'HISTORICAL' | 'ROLLED_BACK';
}
interface VersionDiffResp {
  nodeChanges: Array<{
    changeType: 'ADDED' | 'REMOVED' | 'MODIFIED';
    nodeOrder: number; nodeName: string;
    detail: Record<string, { oldValue?: unknown; newValue?: unknown }>;
  }>;
  configChanges: Array<{ key: string; oldValue?: unknown; newValue?: unknown }>;
}
interface VersionRollbackResp {
  newVersion: number;               // 回滚生成新版本号（FLO-V-R2）
  targetVersion: number;
}
```

### 4. 交互流程

#### 4.1 页面加载
`GET /flow/version/list?templateId=`（版本降序）；失败重试。

#### 4.2 核心操作流程
**A. 版本 Diff 对比**
1. 任两版本行 [对比]（或顶部 from/to 版本选择）→ `GET /flow/version/diff` → Diff 弹窗：
   - 节点变更：ADDED（绿）/REMOVED（红删除线）/MODIFIED（黄）标记 + 属性旧值→新值对照表；
   - 配置变更：key-value 对照。

**B. 版本快照查看（FLO-V-R3 只读）**
1. 版本行 [快照] → 快照抽屉（80%）：该版本流程图只读渲染（复用 P1 预览组件）+ 节点配置明细；不可编辑（无保存按钮）。

**C. 回滚（R1，FLO-V-R2）**
1. 版本行 [回滚到此版本] → 确认弹窗：目标版本 + changeDesc 必填 → `POST /flow/version/{templateId}/rollback`；
2. 成功提示："已生成新版本 V{n+1}（指向 V{target} 配置），在途实例按原版本继续运行" → 版本列表刷新（新版本 status=CURRENT，被回滚版本标 ROLLED_BACK）。

### 5. 查询条件表
无（二级页面按 templateId 定位）。

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| version | 版本 | 80 | ✓ 降序 | V{n}；CURRENT 行加"当前"绿标 |
| changeDesc | 变更说明 | 自适应 | — | — |
| publishedByName | 发布人 | 100 | — | — |
| publishedAt | 发布时间 | 150 | — | yyyy-MM-dd HH:mm |
| status | 状态 | 110 | — | tag：当前(绿)/历史(灰)/已回滚(青) |
| actions | 操作 | 210 | — | [快照][对比][回滚到此版本（R1）] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 版本 Diff 弹窗 | Modal 900px | from/to 版本选择器；节点/配置双区对照；变更类型色标 |
| 版本快照抽屉 | Drawer 80% | 只读流程图 + 节点配置明细（无编辑入口，FLO-V-R3） |
| 回滚确认弹窗 | Modal 480px | targetVersion 只读回显；changeDesc 必填 ≤512；提示"生成新版本号，非物理回退" |

### 8. 错误处理
- 1134（版本约束拦截——回滚目标版本不存在或为草稿版本，段内语义族归并）：回滚弹窗校验提示；
- Diff 版本相同：选择器互斥校验；
- 快照查询失败：提示并返回版本列表。

### 9. BR 业务规则覆盖
- FLO-V-R1（仅最新发布版本可发起新实例）：版本列表 CURRENT 标记 + P1 发起入口联动；
- FLO-V-R2（回滚生成新版本号非物理回退）：回滚确认文案 + 返回 newVersion；
- FLO-V-R3（快照不可修改）：快照抽屉只读。

---

## P5. 超时督办与统计（FLOW-004）

### 1. 页面概述
- 路由路径：`/ims/flow/timeout`
- 页面级别：一级菜单页，双 Tab：超时督办清单 / 超时统计（BR-115）
- 依赖模块：V2-A1 SLA 超时扫描定时任务（Redisson 锁集群化）、ALERT 推送（升级通道）、PERF（时效档案取数）
- 权限矩阵引用（PRD 4.2 FLOW-004）：R1 R/W（督办配置）、R2/R3/R4 R（本域）、R9 R（全量）、处理人（本人超时）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [超时督办清单] [超时统计]                                     |
+------------------------------------------------------------------+
| 督办清单查询行: 业务域 | 处理人 | 模板 | [查询][重置]               |
+------------------------------------------------------------------+
| 督办清单表格:                                                     |
| 实例号|流程|节点|处理人|SLA时限|超时时间|超时时长|提醒次数|已升级|操作 |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
| 超时统计 Tab: 指标卡: 月度超时率 xx% (BR-115 目标<10%)             |
|   域分布条形图 | 月度趋势折线                                       |
|   分布维度切换(模板/节点/部门/人) + 分布表                          |
+------------------------------------------------------------------+
手动督办弹窗: 督办消息(默认模板可改) → 钉钉强提醒
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface TimeoutListReq {
  pageNo: number; pageSize: number;
  businessDomain?: FlowDomain;
  assigneeUserId?: number;
  templateName?: string;
}
interface TimeoutRateReq { statMonth?: string; }
interface TimeoutDistReq {
  statMonth?: string;
  dimension: 'TEMPLATE' | 'NODE' | 'DEPT' | 'PERSON';
}
interface TimeoutUrgeReq {
  taskId: number;
  urgeMessage?: string;             // 默认模板文案可修改
}

// 响应类型
interface TimeoutTaskItem extends FlowTaskVO {
  slaHours: number;
  timeoutAt: string;
  timeoutDurationMinutes: number;
  remindCount: number;
  isEscalated: boolean;             // 超 24h 已升级（FLO-O-R2）
}
interface TimeoutRateResp {
  monthlyTimeoutRate: number;       // BR-115：超时节点数/执行节点总数（月度）
  targetRate: number;               // 10%
  byDomain: Array<{ businessDomain: string; timeoutRate: number }>;
  trend: Array<{ statMonth: string; timeoutRate: number }>;
}
interface TimeoutDistItem {
  dimensionValue: string;
  timeoutCount: number; totalExecuted: number;
  timeoutRate: number; avgTimeoutMinutes: number;
}
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载（清单/统计）；数据范围本域/本人服务端过滤。失败分区重试。

#### 4.2 核心操作流程
**A. 超时督办清单**
1. 清单表格（timeoutDurationMinutes 降序）；isEscalated 行显示"已升级（上级+域负责人）"橙色角标（FLO-O-R2）；
2. 行 [督办] → 手动督办弹窗（urgeMessage 默认模板可改）→ `PUT /flow/timeout/{id}/urge` → 钉钉强提醒 + remindCount+1；
3. 行 [查看任务] → 跳 P2 任务处理抽屉（处理人视角）。

**B. 超时统计（BR-115）**
1. 指标卡月度超时率（目标 <10%，达标绿/未达标红）；
2. 域分布条形图 + 月度趋势折线（近 6 个月）；统计月选择；
3. 分布维度切换（模板/节点/部门/人）→ `GET /flow/timeout/distribution` → 分布表（timeoutRate 降序，超 10% 行黄标）。

### 5. 查询条件表

**督办清单 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| businessDomain | Select | 否 | 空 | 业务域 |
| assigneeUserId | UserSelect | 否 | 空 | 处理人 |
| templateName | Input | 否 | 空 | 模板名称模糊匹配 |

**统计 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| statMonth | MonthPicker | 否 | 本月 | 统计月 |
| dimension | RadioGroup | 是 | TEMPLATE | 模板/节点/部门/人 |

### 6. 表格列定义

**督办清单**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| instanceNo | 实例号 | 140 | — | 等宽字体 |
| templateName | 流程 | 150 | — | — |
| nodeName | 超时节点 | 120 | — | — |
| assigneeName | 处理人 | 100 | — | — |
| slaHours | SLA 时限 | 90 | — | "N 小时" |
| timeoutAt | 超时时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| timeoutDurationMinutes | 超时时长 | 110 | — | "X 小时 Y 分钟"红色 |
| remindCount | 提醒次数 | 90 | — | 数字 |
| isEscalated | 升级状态 | 110 | — | tag：已升级(橙)/未升级(灰) |
| actions | 操作 | 130 | — | [督办][查看任务] |

**分布表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| dimensionValue | 维度值 | 自适应 | — | 模板名/节点名/部门/人（随 dimension） |
| timeoutCount | 超时数 | 90 | — | — |
| totalExecuted | 执行总数 | 100 | — | 分母 |
| timeoutRate | 超时率 | 110 | ✓ 降序 | 进度条；>10% 黄标 |
| avgTimeoutMinutes | 平均超时时长 | 130 | — | "X 小时 Y 分钟" |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 手动督办弹窗 | Modal 480px | urgeMessage 可编辑 ≤256 字（默认模板文案）；确认后 remindCount 递增提示 |

### 8. 错误处理
- 督办推送失败（钉钉超时 5003）：提示"钉钉推送失败已入补发队列"（9.3 可用性兜底）；
- 统计月无数据：空态占位图；
- 扫描任务延迟（5006）：清单顶部黄条"超时扫描任务延迟，数据截至 X 时间"。

### 9. BR 业务规则覆盖
- **BR-115（节点超时率 < 10%，月度）**：超时统计指标卡 + 分布表（超 10% 黄标）为规则看板落点；
- FLO-O-R1（超时率月度统计口径=超时节点数/执行节点总数）：指标卡口径注释 + totalExecuted 分母列；
- FLO-O-R2（超时 24h 升级推送上级+域负责人）：isEscalated 标记 + 升级说明 tooltip；
- FLO-O-R3（超时完成时间差计入时效档案）：timeoutDurationMinutes 字段（PERF 取数）；
- V2-A1（SLA 超时扫描集群化）：扫描任务说明 + 数据截至提示。

---

## 附录 A. 模块级约定

1. **枚举引用**：全局权威枚举 `FlowInstanceStatus`（实例粒度 RUNNING/APPROVED/REJECTED/CANCELLED/TIMEOUT）、`FlowNodeStatus`（任务粒度 PENDING/APPROVED/REJECTED/TRANSFERRED）；模块内联枚举 `FlowDomain`/`FlowNodeType`/`FlowTemplateStatus`/`AssignRuleType` 值域与 FLOW-API 契约一致；
2. **错误码段**：1131~1140 FLOW 段（1131 DAG 校验、1132 处理人规则非法、1133 已发布不可编辑、1134 版本约束拦截（发起须最新发布版 + 回滚目标版本非法，语义族归并）、1135 非处理人、1136 无发起权限、1137 并行汇合、1138 转交无效、1139 撤销权限、1140 终态不可撤销）；
3. **引擎封装（V2-D1~D4）**：前端仅消费 `/admin-api/ims/flow/*` IMS 契约层，nodeType→BPMN 映射在后端完成；实例状态持久化服务重启不丢（MQ 至少一次 + 幂等，9.3）；
4. **H5 同构**：P2 我的流程工作台三 Tab 钉钉 H5 可用（待办处理移动化）；
5. **SLA 扫描**：纳入 V2-A1 集群化调度（Redisson 分布式锁防重复扫描）。

## 附录 B. BR/FLO 规则 ↔ 页面落点总表

| 规则 | 约束摘要 | 页面落点 |
|------|----------|----------|
| BR-115 | 节点超时率 < 10%（月度） | P5 统计指标卡 + 分布表 |
| FLO-T-R1 | DAG 校验（起止/无环路） | P1 发布校验 + 1131 定位 |
| FLO-T-R2 | 发起人直属上级动态解析 | P1 assigneeRule INITIATOR_SUPERIOR |
| FLO-T-R3 | 发布后修改走新版本 | P1 1133 + P4 版本链路 |
| FLO-I-R1 | 并行全完成才汇合 | P2 1137 提示 + currentNodes 并行展示 |
| FLO-I-R2 | 转交一次一跳留痕 | P2 转交弹窗 + traceLog |
| FLO-I-R3 | 撤销留痕已完成节点 | P2 撤销确认 + CANCELLED 轨迹保留 |
| FLO-V-R1~R3 | 最新版发起/回滚新号/快照只读 | P1 发起入口 / P4 回滚与快照 |
| FLO-O-R1~R3 | 超时率口径/24h 升级/时效档案 | P5 全 Tab / P2 durationMinutes |
| V2-D1~D4 | Flowable 封装不直连 | 全模块 API 层约定 |

（全文完）
