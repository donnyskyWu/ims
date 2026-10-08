# COMP - 竞品管理 页面规格（V3，04 模块，第 31~38 周）

> **模块范围**：COMP-001 竞品分析提交 / COMP-002 审核入库 / COMP-003 竞品资产库。  
> **IMS 导航（走查 #9）**：P3 **竞品资产库** 侧栏入口 = **日常运营 → 竞品分析 → 竞品库**（`/ims/comp-analysis/library`，alias 原 `/comp/asset`）；P1/P2 提交与审核 **仍** 为工作台/独立路由，**不**迁入竞品分析 L3。
> **权威依据**：《IMS第三期PRD-V3.md》5.1~5.3；《COMP-竞品管理-API契约.md》（16 接口，1171~1177 错误码段）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**（4 页）：P1 竞品分析提交页（H5 优先 + Web 同构）｜P2 审核入库工作台（Web）｜P3 竞品资产库（Web）｜P4 竞品对比与热度（Web）。
> **模块核心口径**：**合规强制**——仅采集公开数据、数据来源必填（BR-202 合规要素，缺失报 1171）；**归并键** = 标准化竞品名（去空格/统一大小写/别名映射）或账号 ID（BR-203），终审通过自动归并入库、版本累加；**提交率 > 95%**（BR-201，按人月，按期含 3 日内补交）；COMP 上线 + 首月数据完整后**解禁 V2 绩效竞品指标**（BR-206，联动 V2 PERF `COMPETE_SUBMIT_RATE`）。
> **V3 上线联动**：V2 PERF P1 的 `COMPETE_SUBMIT_RATE` 占位锁态在本模块上线后解除（BR-110 → BR-206）。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase（`analysis_no → analysisNo`、`comp_name_std → compNameStd`）。
- 枚举以《全局开发规范.md》第 4 章为唯一权威源。本模块引用：`PlatformType`（平台）、`CompeteStatus`（'TRACKING' 追踪中 / 'PAUSED' 暂停 / 'ARCHIVED' 归档）、`SubmitStatus` 竞品域四态——引用《全局开发规范.md》权威枚举 `CompAnalysisStatus`（'DRAFT'/'SUBMITTED'/'STORED'/'REJECTED'；域内联说明：**注意与 REPORT 域 SubmissionStatus（DRAFT/SUBMITTED/APPROVED/REJECTED）不同值集，COMP 域 STORED = 已入库**）。
- 编号样式：analysisNo = `CA+日期+流水`；assetNo = `CP+日期+流水`。
- 权限矩阵引用 PRD 5.1~5.3.5：R5/R6 运营/投放（本人提交）、R8 初审（数据质量）、R4 终审 + 档案维护、R3 财务维度查看、R1 删除/归档、R2/R9 只读。
- StatusTag 语义色：DRAFT 灰 / SUBMITTED 蓝 / STORED 绿 / REJECTED 红；TRACKING 绿 / PAUSED 橙 / ARCHIVED 灰。
- 附件：FileUpload 服务端上传（全局规范第 6 章），回执 `{fileName, fileKey}`。

---

# P1 竞品分析提交页（COMP-001，H5 优先 + Web 同构）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/comp/analysis/submit`（Web 菜单 + H5 `/h5/comp/submit`；工作台"竞品分析待办"卡片进入） |
| 页面级别 | 二级（模板表单页） |
| 前置依赖 | 月度待办已指派（GET pending）；V3 第 31 周后上线 |
| 权限 | 提交：R5/R6（本人）；查看列表：R1/R4（全量）/R5/R6（本人，服务端过滤）；编辑：本人，仅 DRAFT/REJECTED 态 |
| 用户 | 运营 R5 / 投放 R6（提交人） |

## 2. 页面布局（ASCII）

```
┌────────────────────────────────────────────────────────────────┐ H5 竖屏（Web 同构双栏）
│ ◆ 月度待办卡（GET pending）                                     │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ 2025-05 竞品分析待办                                        │ │
│ │ 应提交 2 份 · 已提交 1 份 · 截止 25 日 22:00                │ │
│ │ ⏰ 距截止 3 天（isNearDeadline 橙色高亮）                    │ │
│ │ [+ 新建分析] → 提交表单                                     │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ◆ 我的提交列表（本人，默认 Tab）                                 │
│ QueryBar(Web 单行): [周期 MonthPicker][状态 Select]             │
│ ┌──────────┬────────┬──────┬──────────┬────────┐              │
│ │分析编号   │竞品对象 │所属月│ 状态     │按期     │              │
│ │CA20250526│ 竞品A   │05月  │已入库    │ ✓按期  │              │
│ │…013      │ 竞品B   │05月  │已退回    │ —     │              │
│ └──────────┴────────┴──────┴──────────┴────────┘              │
│ 行点击 → 提交详情抽屉（审核轮次 + 退回原因 + 重报入口）          │
└────────────────────────────────────────────────────────────────┘
◆ 提交表单（Drawer 或独立页）:
┌──────────────────────────────────────────┐
│ ① 竞品对象: 名称 Input (失焦触发归并预览  │
│    GET merge-preview 命中提示)            │
│    账号 ID Input(选填) · 平台 Select      │
│ ② 合规要素: 数据来源说明 TextArea ⚠必填  │
│    (占位"仅可采集公开数据" + 合规提示条)  │
│ ③ 维度数据: 动态字段表单                  │
│    [销售额|GMV|价格带|内容策略|投放策略…]  │
│ ④ 结论与可借鉴点: TextArea ⚠必填          │
│ ⑤ 附件: FileUpload(截图/表格凭证,多选)    │
│ [存草稿] [提交进入审核]                    │
└──────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举 =====
/** 竞品分析提交状态（COMP 域内联，注意 ≠ REPORT 域 SubmissionStatus） */
type CompSubmitStatus = 'DRAFT' | 'SUBMITTED' | 'STORED' | 'REJECTED';

// ===== 请求 =====
interface CompAnalysisSubmitReq {
  periodMonth: string;                   // 分析所属月 yyyy-MM
  compName: string;
  compAccountId?: string;                // 第二归并键（可选）
  /** 数据来源说明：必填（合规要素，仅公开数据，BR-202） */
  dataSource: string;
  /** 维度字段数据（销售/GMV/价格带/内容策略/投放策略等） */
  dimensionData: Record<string, string | number | null>;
  conclusion: string;
  attachments?: Array<{ fileName: string; fileKey: string }>;
}

interface CompAnalysisQueryReq extends PageParam {
  submitterUserId?: number;
  periodMonth?: string;
  submitStatus?: CompSubmitStatus;
}

// ===== 响应 =====
interface CompAnalysisVO {
  id: number;
  analysisNo: string;                    // CA+日期+流水
  submitterUserId: number;
  submitterName: string;
  periodMonth: string;
  compName: string;
  compAccountId?: string;
  dataSource: string;
  dimensionData: Record<string, string | number | null>;
  conclusion: string;
  attachments: Array<{ fileName: string; fileKey: string }>;
  submitStatus: CompSubmitStatus;
  /** 按期标记：截止 = 每月 25 日 22:00（可配）；按期含 3 日内补交（CMP-A-R1/R2） */
  isOnTime: boolean;
  submittedAt?: string;
  createdAt: string;
}

interface CompAnalysisDetailVO extends CompAnalysisVO {
  auditRounds: Array<{
    round: number;
    auditLevel: 'FIRST' | 'FINAL';
    conclusion: 'STORED' | 'REJECTED';
    rejectReason?: string;
    auditorName: string;
    auditedAt: string;
  }>;
}

interface CompPendingVO {
  periodMonth: string;
  dueTime: string;
  shouldCount: number;
  submittedCount: number;
  isNearDeadline: boolean;
}

interface CompSubmitRateVO {
  totalSubmitRate: number;               // BR-201 目标 > 95%
  byPerson: Array<{
    userId: number;
    userName: string;
    deptName: string;
    shouldCount: number;
    onTimeCount: number;
    submitRate: number;
  }>;
  target: number;
}

interface CompMergePreviewVO {
  matched: boolean;
  assetNo?: string;
  compNameStd?: string;
  latestVersion?: number;
  matchedBy: 'NAME_STD' | 'ACCOUNT_ID' | 'ALIAS' | 'NONE';
  similarity: number;
}
```

## 4. 交互流程

**页面加载**：
1. 并行 `GET /comp/analysis/pending`（月度待办卡）+ `GET /comp/analysis/list`（本人列表，R5/R6 服务端限定本人；R1/R4 可切全量视角，筛选 submitterUserId）。
2. isNearDeadline=true 时待办卡橙色高亮 + 倒计时；过了 dueTime 显示红色"已逾期（仍可补交，3 日内计为按期）"。

**核心操作**：
- **新建分析**（R5/R6）→ 提交表单（§7.1）。
- **提交**：`POST /comp/analysis`；数据来源为空返回 1171 → 表单红字"数据来源必填（仅可采集公开数据，BR-202）"；同人同月同竞品重复返回 1172 → 提示"本月已提交过该竞品（{analysisNo}）"。
- **归并预览**（提交表单内，compName/compAccountId 失焦触发）：`GET /comp/audit/merge-preview`；matched=true → 表单区黄色 InfoBar "检测到既有档案 **{compNameStd}**（{assetNo}，当前版本 v{latestVersion}，匹配方式：{matchedBy}，相似度 {similarity}%）。提交通过审核后将归并至该档案，无需重复建档。"——**提示性质，不阻塞提交**（归并以终审入库为准，CMP-A-R4）。
- **退回重报**（CMP-A-R3）：列表 REJECTED 行点击 → 详情抽屉展示审核轮次与结构化退回原因 → [修改重报] → 表单回填（PUT `/comp/analysis/{analysisNo}`，仅 DRAFT/REJECTED 可编辑）。
- **提交率卡**（R1/R4/R9 视角，工作台或列表顶部）：`GET /comp/analysis/submit-rate` → 总提交率 >95% 达标绿；byPerson 明细（未达标人红色）；附提示"数据同时供绩效取数（BR-206）——本模块上线 + 首月数据完整后自动解禁 V2 绩效'竞品分析提交率'指标"。

## 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| periodMonth | MonthPicker | string | 分析所属月 |
| submitStatus | Select | CompSubmitStatus | 全部（默认）/草稿/已提交/已入库/已退回 |
| submitterUserId（R1/R4） | 人员选择 | number | 全量视角按提交人过滤 |

## 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 分析编号 | analysisNo | code 样式（CA+日期+流水） |
| 竞品对象 | compName | 文本 + compAccountId 小字 |
| 所属月 | periodMonth | yyyy-MM |
| 提交人 | submitterName | 文本（全量视角） |
| 状态 | submitStatus | DRAFT 灰/SUBMITTED 蓝/STORED 绿/REJECTED 红 |
| 按期 | isOnTime | ✓ 绿"按期"/ ✗ 橙"补交（3 日内）"/ 红"迟交"；未提交态 "—" |
| 提交时间 | submittedAt | yyyy-MM-dd HH:mm |
| 操作 | — | 详情；REJECTED/DRAFT 态追加 [修改重报]（本人） |

## 7. 抽屉/弹窗规格

### 7.1 竞品分析提交表单（Drawer 右滑 720px / H5 全屏页）

- **五段式布局**（对应 ASCII §②~⑤）：
  1. **竞品对象**：名称 Input（失焦归并预览）+ 账号 ID Input（选填）+ 平台 Select（PlatformType）+ 所属月 MonthPicker（默认待办周期）。
  2. **合规要素**：数据来源说明 TextArea（**必填**，1171 预校验）+ 顶部合规提示条（蓝色 InfoBar："仅可采集公开数据（BR-202 合规要素），来源须可追溯"）。
  3. **维度数据**：动态字段表单（字段清单来自模板配置：销售额/GMV/价格带/内容策略/投放策略…；文本与数值双输入型）。
  4. **结论与可借鉴点**：TextArea（**必填**，三要素之一）。
  5. **附件**：FileUpload 多文件（截图/表格凭证，服务端上传回执）。
- 底部：[存草稿]（submitStatus=DRAFT 不进审核）[提交进入审核]；编辑态（REJECTED 重报）回填全部字段 + 顶部展示退回原因卡（rejectReason + rejectReasonTags 红色 Tag）。

### 7.2 提交详情抽屉（Drawer，右滑 720px）

- **结构**：
  1. 头部：analysisNo + 状态 Tag + 按期标记。
  2. **内容区**（Descriptions）：竞品对象/所属月/数据来源（合规要素高亮）/维度数据表（key-value 两列）/结论全文/附件列表（fileKey 预览下载）。
  3. **审核轮次区**（auditRounds 时间线）：每轮 `第 {round} 轮 · {初审 R8/终审 R4} · {通过/退回} · {auditorName} · {auditedAt}`；退回轮附 rejectReason + rejectReasonTags 红 Tag。
  4. 底部操作（本人 + DRAFT/REJECTED）：[修改重报]；SUBMITTED/STORED 只读。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 表单红字 |
| 1171 | 数据来源必填（合规要素缺失） | 表单红字 + 合规提示条闪烁 |
| 1172 | 同人同月同竞品重复提交 | Dialog 提示已存在单号，可跳转该单详情 |
| 编辑非本人/非可编辑态 | 403 | toast "仅 DRAFT/已退回状态可修改（CMP-A-R3）" |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-201（提交率 > 95%，按期含 3 日内补交） | 待办卡 isOnTime、提交率卡、byPerson 明细 |
| BR-202（合规：来源必填） | 1171 拦截 + 合规提示条 + 必填预校验 |
| BR-203（归并键预览提示） | 表单归并预览 InfoBar（不阻塞） |
| BR-206（绩效指标解禁联动） | 提交率卡联动提示文案 |
| CMP-A-R1（25 日 22:00 截止可配） | 待办卡截止时间与逾期态 |
| CMP-A-R2（按期含 3 日补交） | isOnTime 三态渲染 |
| CMP-A-R3（退回修改重报） | 详情抽屉退回原因卡 + 重报入口 |
| CMP-A-R4（同竞品多次提交归并） | 1172 提示 + 归并预览 |

---

# P2 审核入库工作台（COMP-002）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/comp/audit`（菜单：竞品管理 → 审核入库） |
| 页面级别 | 二级（两 Tab：审核队列 / 审核记录） |
| 前置依赖 | 有 SUBMITTED 状态提交单 |
| 权限 | 初审队列：R8；终审队列：R4；审核记录：R1/R4/R8/提交人（本人状态）；审核操作：R8（初审）/R4（终审） |
| 用户 | R8 初审员（数据质量核查）/ R4 运营总监（终审） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 审核入库工作台                                                            │
│ ┌─[审核队列]─┬─[审核记录]──────────────────────────────────┐             │
│ │                                                        │             │
│ │  ◆ Tab1 审核队列（GET /comp/audit/queue）               │             │
│ │  级别切换: [初审(R8)/终审(R4)] Radio（按登录角色默认）    │             │
│ │  QueryBar: [提交人 Input][所属月 Select] [搜索][重置]   │             │
│ │  队列表格:                                               │             │
│ │  ┌──────────┬────────┬──────┬────────┬────────┬──────┐ │             │
│ │  │分析编号   │竞品对象 │提交人│ 状态   │SLA     │操作  │ │             │
│ │  ├──────────┼────────┼──────┼────────┼────────┼──────┤ │             │
│ │  │CA…013    │竞品B    │赵六  │待初审  │⏰46h⚠  │审核  │ │             │
│ │  │          │        │      │        │(48h内) │      │ │             │
│ │  └──────────┴────────┴──────┴────────┴────────┴──────┘ │             │
│ │  SLA 超时行(isTimeoutSla) 置顶红色边框 + "超时督办"Tag   │             │
│ │                                                        │             │
│ │  ◆ Tab2 审核记录（GET /comp/audit/records）             │             │
│ │  QueryBar: [分析编号 Input][审核人 Input][结论 Select]  │             │
│ │  记录表: [分析编号|轮次|级别|结论|退回原因|审核人|时间]   │             │
│ └────────────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────────────┘
点击"审核" → 审核抽屉（质量要素核查清单 + 归并预览 + 通过/退回）
```

## 3. TypeScript 类型定义

```typescript
// ===== 请求 =====
interface CompAuditQueueReq extends PageParam {
  auditLevel: 'FIRST' | 'FINAL';
  submitterUserId?: number;
  periodMonth?: string;
}

interface CompAuditReq {
  auditLevel: 'FIRST' | 'FINAL';          // 1 初审 R8 / 2 终审 R4
  conclusion: 'STORED' | 'REJECTED';     // 通过入库 / 退回
  rejectReason?: string;                 // 退回必填（1173）
  rejectReasonTags?: string[];           // ['来源不可靠','字段缺失','结论不明确']
}

interface CompAuditRecordQueryReq extends PageParam {
  analysisNo?: string;
  auditorUserId?: number;
  conclusion?: string;
}

// ===== 响应 =====
interface CompAuditQueueItem extends CompAnalysisVO {
  waitingHours: number;
  isTimeoutSla: boolean;                 // 初审 SLA 48 小时（CMP-B-R4）
}

interface CompAuditResultVO {
  analysisNo: string;
  newStatus: CompSubmitStatus;
  nextAction: 'TO_FINAL' | 'MERGE_STORED' | 'BACK_TO_SUBMITTER';
  mergeInfo?: { assetNo: string; compNameStd: string; newVersion: number };
}
```

## 4. 交互流程

**页面加载**：默认 Tab1，`auditLevel` 按登录角色默认（R8 → FIRST，R4 → FINAL）；`GET /comp/audit/queue`。SLA 超时（isTimeoutSla）行置顶排序 + 红框 + "超时督办" Tag（waitingHours > 48，CMP-B-R4）。

**核心操作**：
- **审核**：行操作"审核" → 审核抽屉（§7.1）：
  - 初审通过 → conclusion=STORED + auditLevel=FIRST → nextAction=TO_FINAL → 进入终审队列；初审退回 → REJECTED 回提交人。
  - 终审通过 → **自动归并入库**（BR-203/CMP-B-R2）：返回 mergeInfo（命中档案 assetNo/newVersion 或新建档案）→ 成功 Dialog "已归并入库：{compNameStd}（{assetNo}）版本 v{newVersion}，已通知提交人"；终审退回 → REJECTED。
  - 退回未填原因返回 1173 → 抽屉红字；三要素不齐返回 1174 → 抽屉核查清单红字定位；3 轮退回返回 1175 → Dialog "该单已 3 轮退回，升级运营总监裁决（CMP-B-R3）"；初审未通过试图终审返回 1176 → 拦截。
- **审核记录**：Tab2 `GET /comp/audit/records`；提交人视角仅见本人单据审核状态（服务端过滤）。

## 5. 查询条件表

| Tab | 字段 | 组件 | 说明 |
|-----|------|------|------|
| 队列 | auditLevel | Radio | 初审（R8）/终审（R4），按角色锁定可选项 |
| 队列 | submitterUserId / periodMonth | Input / MonthPicker | 提交人 / 所属月 |
| 记录 | analysisNo | Input | 分析编号精确 |
| 记录 | auditorUserId | Input | 审核人 |
| 记录 | conclusion | Select | 全部/通过入库/退回 |

## 6. 表格列定义

**Tab1 审核队列**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 分析编号 | analysisNo | code 样式 |
| 竞品对象 | compName | 文本 |
| 提交人 | submitterName | 文本 |
| 所属月 | periodMonth | yyyy-MM |
| 状态 | submitStatus | SUBMITTED 蓝（初审队列）/ 待终审（终审队列） |
| 等待时长 | waitingHours | `{n}h`；isTimeoutSla → 红色 + "超时督办" Tag，行红框置顶 |
| 操作 | — | 审核（R8/R4 对应队列） |

**Tab2 审核记录**：分析编号、轮次（auditRound `第 {n} 轮`）、级别（FIRST 初审 R8 / FINAL 终审 R4）、结论（STORED 绿/REJECTED 红）、退回原因（rejectReason + tags）、审核人、审核时间。

## 7. 抽屉/弹窗规格

### 7.1 审核抽屉（Drawer，右滑 800px）

- **三段式**：
  1. **提交内容区**（复用 P1 §7.2 详情渲染，只读）：全部字段 + 附件预览。
  2. **质量要素核查清单**（BR-202 三要素，Checkbox 三项 + 归并预览）：
     - ☐ 来源可靠（dataSource 可追溯）
     - ☐ 字段齐全（dimensionData 核心字段非空）
     - ☐ 结论明确（conclusion 有效）
     - 归并预览卡（自动调用 `GET /comp/audit/merge-preview`）：命中 → "将归并至 **{compNameStd}**（{assetNo}）→ v{latestVersion+1}"；未命中 → "将新建档案"。
     - 通过（conclusion=STORED）时**三项须全部勾选**（前端预校验，对应 1174）；任一未勾选只能选退回。
  3. **审核结论区**：Radio 通过入库 / 退回；退回时展开 rejectReason TextArea（**必填** 1173 预校验）+ rejectReasonTags 多选 Tag（来源不可靠/字段缺失/结论不明确）。
- 提交 → `PUT /comp/audit/{analysisNo}` → 按返回 nextAction 分支提示（TO_FINAL/MERGE_STORED/BACK_TO_SUBMITTER）。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 红字 |
| 1173 | 退回未填原因 | 抽屉红字 + 禁用提交 |
| 1174 | 三要素不齐 | 核查清单红字定位未勾项 |
| 1175 | 3 轮退回升级 R4 裁决 | Dialog 提示 |
| 1176 | 越级审核 | 拦截 toast |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-202（三要素入库） | 审核抽屉核查清单（勾选强制）+ 1174 |
| BR-203（终审通过归并入库版本累加） | 归并预览卡 + MERGE_STORED 结果 Dialog |
| CMP-B-R1（三要素齐全方可通过） | 同上 |
| CMP-B-R2（终审触发归并） | 审核流分支 |
| CMP-B-R3（3 轮退回升级 R4） | 1175 Dialog |
| CMP-B-R4（初审 SLA 48h） | 队列超时行置顶红框 + 督办 Tag |

---

# P3 竞品资产库（COMP-003）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/comp/asset`（菜单：竞品管理 → 竞品资产库） |
| 页面级别 | 二级（模块主页面） |
| 前置依赖 | 有入库档案（COMP-002 归并生成） |
| 权限 | 查看：R1/R2/R3（财务维度）/R4/R5/R6/R8/R9（只读）；档案维护与别名映射：R4/R1；归档：R1 |
| 用户 | 全角色只读检索 + R4/R1 维护 |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 竞品资产库    [档案总数 {n} | 追踪中 {m} | 引用总次数 {k}]               │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [标准化名称 Input][平台 Select:全部/抖音/快手/…][提交人  │
│  人员选择][维度字段: key Select + value Input 组合]  [搜索][重置]         │
├──────────────────────────────────────────────────────────────────────────┤
│ 档案表格                                                     共 {n} 条  │
│ ┌──────────┬──────────┬──────┬──────┬──────┬────────┬──────────┐        │
│ │档案编号   │标准化名称 │平台  │最新版│引用数│ 状态    │ 操作      │        │
│ ├──────────┼──────────┼──────┼──────┼──────┼────────┼──────────┤        │
│ │CP20250102│竞品A(标准)│抖音  │ v6   │ 23   │追踪中  │详情 对比  │        │
│ │          │          │      │      │      │        │别名维护   │        │
│ └──────────┴──────────┴──────┴──────┴──────┴────────┴──────────┘        │
│ 分页: ‹ 1 ›   每页 [10▾] 条        多选行 → [加入对比(≤5)]              │
└──────────────────────────────────────────────────────────────────────────┘
行点击 → 档案详情抽屉（版本时间轴 + 维度数据对比视图 + 别名列表）
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
/** 竞品档案状态 */
type CompeteStatus = 'TRACKING' | 'PAUSED' | 'ARCHIVED';

// ===== 请求 =====
interface CompAssetQueryReq extends PageParam {
  compNameStd?: string;
  platform?: PlatformType;
  latestVersionRange?: [string, string];
  submitterUserId?: number;
  dimensionField?: { key: string; value: string };
}

interface CompAliasReq {
  addAliases?: string[];
  removeAliases?: string[];
}

// ===== 响应 =====
interface CompAssetVO {
  id: number;
  assetNo: string;                       // CP+日期+流水
  /** 标准化竞品名（归并键，唯一索引：去空格/统一大小写/别名映射 CMP-C-R1） */
  compNameStd: string;
  compAccountId?: string;                // 第二归并键
  platform: PlatformType;
  baseInfo: Record<string, string | number | null>;
  latestVersion: number;
  /** 引用计数（BR-214）：被报表/看板/穿透查询引用次数 */
  referenceCount: number;
  status: CompeteStatus;
  createdAt: string;
  updatedAt: string;
}

interface CompAssetDetailVO extends CompAssetVO {
  versionTimeline: Array<{
    version: number;
    sourceAnalysisNo: string;
    dimensionData: Record<string, string | number | null>;
    conclusion: string;
    archivedAt: string;
    isValid: boolean;
    markedInvalidReason?: string;
  }>;
  aliasList: string[];
}
```

## 4. 交互流程

**页面加载**：`GET /comp/asset/list`（默认分页）+ 顶部统计卡（列表聚合）。

**核心操作**：
- **档案详情**：行点击 → `GET /comp/asset/{assetNo}` → 详情抽屉（§7.1）。
- **版本历史**：详情抽屉内 [查看完整版本历史] → `GET /comp/asset/{assetNo}/versions`（支持按 version 筛选）；**版本只增不改**（CMP-C-R2），错误数据走"标记无效"（isValid=false 灰显 + 删除线 + markedInvalidReason Tooltip；服务端操作，页面只读展示）。
- **别名维护**（R4/R1）：详情抽屉 [别名映射维护] → 别名编辑弹窗（§7.2）→ `PUT /comp/asset/{assetNo}/alias`；冲突返回 1177 → 红字"该别名已属于档案 {assetNo}"。
- **加入对比**：表格行多选（≤5）→ [加入对比] → 跳 P4 对比页（assetNos 传参）。
- **归档**（R1，详情抽屉）：仅 ARCHIVED 可选；有引用（referenceCount>0）时归档 ConfirmDialog 附警示"该档案被引用 {n} 次，归档后保留可查（CMP-C-R4 禁止删除）"。

## 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| compNameStd | Input | string | 标准化名称模糊 |
| platform | Select | PlatformType | 全部/抖音/快手/视频号/… |
| submitterUserId | 人员选择 | number | 按来源提交人 |
| dimensionField | key Select + value Input | {key,value} | 维度字段检索（key 列表来自模板字段） |

## 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 档案编号 | assetNo | code 样式（CP+日期+流水） |
| 标准化名称 | compNameStd | 加粗；Hover 显示 aliasList（"别名：竞品A、JingPinA…"） |
| 账号 ID | compAccountId | code 小字 |
| 平台 | platform | PlatformType Tag |
| 最新版本 | latestVersion | `v{n}` |
| 引用次数 | referenceCount | 数字（BR-214），>0 可点击跳 P4 热度详情 |
| 状态 | status | TRACKING 绿"追踪中" / PAUSED 橙"暂停" / ARCHIVED 灰"归档" |
| 最近更新 | updatedAt | yyyy-MM-dd |
| 操作 | — | 详情 / 对比（勾选）/ 别名维护（R4/R1） |

## 7. 抽屉/弹窗规格

### 7.1 档案详情抽屉（Drawer，右滑 880px）

- **结构**：
  1. **头部**：assetNo + compNameStd 大标题 + 状态 Tag + platform Tag + 引用计数徽标。
  2. **基本信息**（Descriptions）：baseInfo key-value + compAccountId + 创建/更新时间 + aliasList Tag 组。
  3. **版本时间轴对比区**（核心）：
     - 版本时间线（纵向）：每节点 `v{n} · 来源 {sourceAnalysisNo} · {archivedAt}`；isValid=false 节点灰显删除线 + markedInvalidReason Tooltip。
     - **维度对比视图**：任选 2~3 版本（Checkbox）→ 维度字段横向对比表 [维度 key | v3 值 | v5 值 | v6 值]（时间序列可对比，PRD 5.3.1）；各版本 conclusion 摘要行。
  4. **底部操作**：[查看完整版本历史]（versions 接口分页）/ [别名映射维护]（R4/R1）/ [归档]（R1）/ [加入对比]。
- 数据：`GET /comp/asset/{assetNo}`（含 versionTimeline + aliasList）。

### 7.2 别名映射维护弹窗（Modal，520px，R4/R1）

- 当前别名 Tag 列表（可逐个 ✕ 移除 → removeAliases）+ 新增别名 Input + [添加]（→ addAliases）。
- 保存 → `PUT /comp/asset/{assetNo}/alias` → toast "别名映射已更新，后续同名提交将自动归并（CMP-C-R1）"。
- 1177 冲突 → 新增输入框红字显示归属档案编号。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1177 | 别名与既有档案归并键冲突 | 弹窗红字定位 |
| 归档有引用档案 | 服务端拒绝（CMP-C-R4） | ConfirmDialog 预警示 + 失败 toast |
| 1001 | 参数校验 | 常规 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-203（归并键标准化） | compNameStd 唯一 + aliasList Hover + 别名维护 |
| BR-214（引用计数） | 引用次数列 + 徽标 |
| CMP-C-R1（归并键标准化规则） | 别名维护 toast 文案 |
| CMP-C-R2（版本只增不改，错误标记无效） | 时间轴 isValid 灰显删除线 |
| CMP-C-R4（有引用禁删仅归档） | 归档警示弹窗 |

---

# P4 竞品对比与热度（COMP-003 延伸）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/comp/compare`（档案库"加入对比"跳入）与 `/comp/heat`（菜单：竞品管理 → 引用热度） |
| 页面级别 | 二级（两功能区：对比报告 / 热度排行） |
| 前置依赖 | P3 档案存在 |
| 权限 | 同 P3（查看全角色只读） |
| 用户 | 决策层（横向对比）/ 资产价值评估（BR-214） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ◆ 竞品对比报告（GET /comp/asset/compare）                                 │
│ 对比对象(≤5): [CP20250102 竞品A ✕][CP20250103 竞品B ✕][+ 添加档案]        │
│ 维度选择: [全选|销售额|GMV|价格带|内容策略|投放策略…] Checkbox            │
│ ┌────────┬─────────┬─────────┬─────────┐                                │
│ │ 维度    │ 竞品A    │ 竞品B   │ 竞品C   │  dimensionMatrix 横向对比     │
│ ├────────┼─────────┼─────────┼─────────┤                                │
│ │ 销售额  │ ¥xx万   │ ¥xx万   │ —      │                                │
│ │ GMV    │ …      │ …      │ …      │                                │
│ ├────────┴─────────┴─────────┴─────────┤                                │
│ │ 结论: 竞品A … / 竞品B … (各行)        │                                │
│ └───────────────────────────────────────┘                                │
│ [导出报告] (前端导出 xlsx/pdf)                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 引用热度排行（GET /comp/asset/heat-rank, TopN=20，BR-214）             │
│ [日期范围 RangePicker]                                                    │
│ ┌────┬──────────┬──────┬────────┬──────────────────────┐                │
│ │排名│ 竞品      │平台  │引用数  │ 最近引用来源          │                │
│ ├────┼──────────┼──────┼────────┼──────────────────────┤                │
│ │ 1  │竞品A     │抖音  │  23    │ 报表·直播月报 · 2h前 │                │
│ └────┴──────────┴──────┴────────┴──────────────────────┘                │
│ recentReferrers: REPORT报表/DASHBOARD看板/TRACE穿透/SHARE分享 Tag+时间   │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 请求 =====
interface CompCompareReq {
  assetNos: string[];                    // ≤5
  dimensionKeys?: string[];
  version?: 'LATEST';
}

// ===== 响应 =====
interface CompCompareVO {
  assetNos: string[];
  dimensionMatrix: Array<{ dimensionKey: string; values: Array<string | number | null> }>;
  conclusions: Array<{ assetNo: string; compNameStd: string; conclusion: string }>;
  generatedAt: string;
}

interface CompHeatRankVO {
  rank: number;
  assetNo: string;
  compNameStd: string;
  platform: string;
  referenceCount: number;
  recentReferrers: Array<{
    refType: 'REPORT' | 'DASHBOARD' | 'TRACE' | 'SHARE';
    refName: string;
    refAt: string;
  }>;
}
```

## 4. 交互流程

**页面加载**：P3 跳入携带 assetNos（1~5 个）；对比区 `GET /comp/asset/compare`（version=LATEST）；热度区 `GET /comp/asset/heat-rank`（topN=20，默认近 30 天）。

**核心交互**：
- **对比对象增删**：[+ 添加档案] → 档案选择弹窗（复用 P3 列表，单选追加，≤5 上限提示）；移除 ✕ 后低于 1 个对象时对比区空态。
- **维度筛选**：dimensionKeys Checkbox → 重新拉取（matrix 只含勾选维度）。
- **导出报告**：[导出] → 前端组装 dimensionMatrix + conclusions → xlsx/pdf 导出（本地生成，不走服务端）。
- **热度排行**：日期范围切换刷新；行点击 → 跳 P3 档案详情抽屉；recentReferrers Tag 展开（refType 四类 + refName + refAt 相对时间）。

## 5. 查询条件表

| 区域 | 字段 | 组件 | 说明 |
|------|------|------|------|
| 对比 | assetNos | 档案多选（≤5） | 跳入携带/弹窗追加 |
| 对比 | dimensionKeys | Checkbox 组 | 模板维度字段 |
| 热度 | dateRange | RangePicker | 默认近 30 天 |

## 6. 表格列定义

**对比矩阵**：首列维度 key，其后每竞品一列（表头 compNameStd + assetNo 小字）；空值 "—"；金额类维度 ¥ 前缀（两位小数）。**结论区**：每竞品一行结论摘要。

**热度排行**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 排名 | rank | 前三徽标 |
| 竞品 | compNameStd | 加粗，行点击跳档案详情 |
| 平台 | platform | Tag |
| 引用数 | referenceCount | 数字（BR-214，纳入资产价值评估） |
| 最近引用来源 | recentReferrers | 最近 3 条：refType Tag（REPORT/DASHBOARD/TRACE/SHARE）+ refName + refAt 相对时间；Hover 展开全部 |

## 7. 抽屉/弹窗规格

- **档案选择弹窗**（Modal 640px）：复用 P3 档案列表（单选模式 + 搜索），确认追加至对比组（≤5）。
- 无其他抽屉；对比详情复用 P3 档案详情抽屉。

## 8. 错误处理

| 场景 | 处理 |
|------|------|
| assetNos 为空 | 对比区空态插画 "请从竞品资产库选择 1~5 个档案进行对比" |
| assetNos > 5 | 追加按钮禁用 + tooltip "最多 5 个对比对象" |
| 对比请求失败 | 常规 toast，保留已选对象可重试 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-214（引用计数与热度排行，资产价值评估） | 热度排行区 + recentReferrers |
| CMP-C-R3（引用计数在报表/看板/穿透引用时累加） | refType 四类来源展示（引用行为由各模块触发，本页只读统计） |

---

# 附录 A：模块级约定

1. **合规强制（BR-202/9.2）**：仅采集公开数据；dataSource 必填（1171 前端预校验 + 服务端兜底）；提交表单常驻合规提示条；审核三要素"来源可靠"为第一要素。
2. **归并键（BR-203/CMP-C-R1）**：标准化名称（去空格/统一大小写/别名映射）或账号 ID；提交表单归并预览**只提示不阻塞**；终审通过自动归并（mergeInfo 反馈入库结果）；别名维护扩展归并键（1177 冲突校验）。
3. **版本不可变（CMP-C-R2）**：档案版本只增不改；错误数据"标记无效"（isValid=false 灰显删除线），无任何前端编辑版本入口。
4. **COMP 域提交状态值集**：DRAFT/SUBMITTED/STORED/REJECTED——**STORED = 已入库**，与 REPORT 域 SubmissionStatus（APPROVED）不同名不同义，规格中显式标注避免混用。
5. **BR-206 联动（绩效解禁）**：COMP 上线 + 首月数据完整后，V2 PERF 域 `COMPETE_SUBMIT_RATE` 指标由 DISABLED 锁态转 ENABLED（V2 PERF P1 的 enableNote 锁态 UI 自动解除）；本模块提交率卡含联动提示文案；跨期联动落点归 V2 PERF 规格（此处仅提示）。
6. **两级审核 + SLA**：初审 R8（48h SLA，超时督办置顶）→ 终审 R4（归并入库）；3 轮退回升级 R4 裁决（1175）；退回必填结构化原因（reason + tags，1173）。
7. **H5 同构**：P1 提交页为移动端优先（运营随时填报）；P2/P3/P4 为 Web 管理后台。
8. **对比导出**：本地导出（前端组装 xlsx/pdf），不新增服务端接口。

# 附录 B：BR / CMP 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-201 | 提交率 > 95%（按人月，按期含 3 日补交） | P1 待办卡/提交率卡 |
| BR-202 | 入库三要素（来源+字段+结论） | P1 合规提示条 + P2 核查清单（1174） |
| BR-203 | 归并键归并 + 版本累加 | P1 预览 / P2 归并入库 Dialog / P3 版本时间轴 |
| BR-214 | 引用计数与热度排行 | P3 引用列、P4 热度排行 |
| BR-206 | 绩效指标解禁联动 | P1 提交率卡提示（落点 V2 PERF） |
| CMP-A-R1 | 截止 25 日 22:00 可配 | P1 待办卡 |
| CMP-A-R2 | 按期含 3 日补交 | P1 isOnTime 三态 |
| CMP-A-R3 | 退回修改重报 | P1 详情抽屉 + 重报入口 |
| CMP-A-R4 | 同竞品多次提交归并 | P1 1172 提示 + 预览 |
| CMP-B-R1 | 三要素方可通过 | P2 清单勾选强制 |
| CMP-B-R2 | 终审触发归并 | P2 审核流分支 |
| CMP-B-R3 | 3 轮退回升级 R4 | P2 1175 Dialog |
| CMP-B-R4 | 初审 SLA 48h | P2 超时置顶红框 |
| CMP-C-R1 | 归并键标准化 | P3 compNameStd + 别名维护 |
| CMP-C-R2 | 版本只增不改/标记无效 | P3 isValid 灰显 |
| CMP-C-R3 | 引用计数累加 | P4 refType 来源展示 |
| CMP-C-R4 | 有引用禁删仅归档 | P3 归档警示 |
| 9.2 合规 | 仅公开数据 | P1 合规提示条 + 必填 |

（全文完）
