# REPORT - 数据上报 API 契约

> **模块范围**：09 数据上报（V2，第 15~18 周，V2.1 批次）——REPORT-001 上报模板配置、REPORT-002 数据提交、REPORT-003 审核退回、REPORT-004 完成率统计。依赖 14 工作流（填报任务分派与审核流转）。  
> **导航（PRD v2.6.9）**：本契约 **不** 覆盖 MEET 工作日报（`/admin-api/ims/meet/daily/*`）；侧栏 **数据上报** 三叶分别映射 template / submission / stat 路由。
> **归因（v2.6.9 · 走查 #10 续）**：填报单须 `authorId`（`author_user.id`）+ `accountId`（`oa_account.id`）；OPS M6 标准报表 **无** 对应提交字段。
> **权威依据**：《IMS第二期PRD-V2.md》5.8~5.11；BR-106；V2-A1（周期任务自动生成填报待办）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`fields_schema → fieldsSchema`、`template_no → templateNo`）；周次波浪号格式。

---

## 1. API 总览表（共 18 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/report/template` | 创建上报模板 | R1/R3（财务线）/R4（业务线） |
| 2 | GET | `/admin-api/ims/report/template/list` | 模板列表（分页） | R1/R3（财务）/R4（业务）/R9 |
| 3 | PUT | `/admin-api/ims/report/template/{id}` | 编辑模板（生成新版本） | 同上 |
| 4 | DELETE | `/admin-api/ims/report/template/{id}` | 停用/删除模板 | R1 |
| 5 | POST | `/admin-api/ims/report/template/{id}/preview` | 模板填报预览（字段渲染校验） | 同 1 |
| 6 | POST | `/admin-api/ims/report/submit` | 保存/提交填报单（勾稽校验） | 填报人本人（R2/R3/R5/R6/R10 被指派） |
| 7 | GET | `/admin-api/ims/report/submit/{submissionNo}` | 填报单详情（含版本留痕） | R1（全量）/本线审核人/填报人本人 |
| 8 | GET | `/admin-api/ims/report/submit/list` | 填报单列表（分页） | 同上 |
| 9 | GET | `/admin-api/ims/report/submit/pending` | 待填报任务（工作台待办） | 填报人本人 |
| 10 | GET | `/admin-api/ims/report/submit/last-period` | 上期数据参考（带入） | 填报人本人 |
| 11 | GET | `/admin-api/ims/report/audit/queue` | 审核队列（按模板线路由，分页） | R8（初审）/R2/R3/R4（本线终审） |
| 12 | PUT | `/admin-api/ims/report/audit/{submissionId}` | 提交审核结论（通过/退回） | R8/R2/R3/R4 |
| 13 | GET | `/admin-api/ims/report/audit/records` | 审核记录（分页） | R1/本线 |
| 14 | GET | `/admin-api/ims/report/audit/diff` | 退回前后数据对比 | R1/R8/R2/R3/R4 |
| 15 | GET | `/admin-api/ims/report/stat/complete-rate` | 完成率（BR-106 质量口径） | R1/R2/R3/R4（本线）/R9/填报人（本人） |
| 16 | GET | `/admin-api/ims/report/stat/trend` | 周期完成率趋势 | 同上 |
| 17 | GET | `/admin-api/ims/report/stat/missed` | 未交清单（督办导出） | R1/R2/R3/R4 |
| 18 | GET | `/admin-api/ims/report/stat/quality` | 退回率/数据质量分析 | R1/R2/R3/R4/R9 |

---

## 2. 接口明细

### 2.1 上报模板配置（REPORT-001）

#### 2.1.1 POST /admin-api/ims/report/template — 创建模板

**请求**：

```typescript
interface ReportTemplateCreateReq {
  templateName: string;          // 如"直播日报-抖音"
  /** 字段定义（类型/校验/勾稽），RPT-T-R2 勾稽规则在提交时强制执行 */
  fieldsSchema: Array<{
    fieldKey: string;
    fieldLabel: string;
    fieldType: 'NUMBER' | 'TEXT' | 'ENUM' | 'DATE' | 'ATTACHMENT' | 'AUTHOR' | 'ACCOUNT';
    required: boolean;
    /** NUMBER 类型：范围校验 */
    range?: { min?: number; max?: number };
    options?: string[];          // ENUM 选项
    /** 勾稽规则（如：detailSum == summaryValue） */
    crossCheck?: {
      targetFieldKey: string;
      operator: 'EQ' | 'LTE' | 'GTE';
      errorMsg: string;
    };
  }>;
  periodType: 'DAILY' | 'WEEKLY' | 'MONTHLY';      // 1 每日 / 2 每周 / 3 每月
  /** 截止规则：'22:00' / 'FRIDAY_18:00' / 'NEXT_MONTH_5TH' */
  deadlineRule: string;
  /** 填报人配置（按人/按岗位/按部门+轮值） */
  assignees: Array<{
    assignType: 'USER' | 'POSITION' | 'DEPT_ROTATION';
    targetIds: number[];         // userId / 岗位编码按 string[] 见 targetCodes
    targetCodes?: string[];      // 岗位编码
    rotationList?: Array<{ userId: number; order: number }>;   // DEPT_ROTATION 轮值顺序
  }>;
  status: 'ENABLED' | 'DISABLED';                   // 0 停用 / 1 启用
}
```

**响应** `data`：

```typescript
interface ReportTemplateVO {
  id: number;
  templateNo: string;            // RT+日期+流水
  templateName: string;
  fieldsSchema: ReportTemplateCreateReq['fieldsSchema'];
  periodType: 'DAILY' | 'WEEKLY' | 'MONTHLY';
  deadlineRule: string;
  assignees: ReportTemplateCreateReq['assignees'];
  version: number;
  status: 'ENABLED' | 'DISABLED';
  /** 业务线路由：财务/业务/行政（审核队列路由依据） */
  businessLine: 'FINANCE' | 'BUSINESS' | 'ADMIN';
  createdBy: number;
  createdAt: string;
}
```

**错误码**：1121（字段勾稽规则引用不存在的字段）、1001（参数校验）。

#### 2.1.2 GET /admin-api/ims/report/template/list — 模板列表（分页）

**请求**（Query）：`PageParam` + `{ templateName?: string; periodType?: 'DAILY' | 'WEEKLY' | 'MONTHLY'; status?: 'ENABLED' | 'DISABLED'; businessLine?: 'FINANCE' | 'BUSINESS' | 'ADMIN' }`

**响应** `data`：`PageResult<ReportTemplateVO>`（R3 限财务线、R4 限业务线，服务端过滤）。

#### 2.1.3 PUT /admin-api/ims/report/template/{id} — 编辑模板（新版本）

**请求**：`ReportTemplateCreateReq` → **响应** `data`：`ReportTemplateVO`（`version` 自增）。模板启用后修改字段生成新版本，进行中填报单沿用旧版（RPT-T-R1）。

#### 2.1.4 DELETE /admin-api/ims/report/template/{id} — 停用/删除

**响应**：`data: null`。逻辑删除；有进行中填报单的模板仅支持停用（`DISABLED`）。

#### 2.1.5 POST /admin-api/ims/report/template/{id}/preview — 填报预览

**请求**：`{ version?: number; sampleData?: Record<string, unknown> }` → **响应** `data`：`{ renderedFields: ReportTemplateVO['fieldsSchema']; validationResult: { passed: boolean; errors: Array<{ fieldKey: string; errorMsg: string }> } }`（发布前字段渲染与校验规则自检）。

### 2.2 数据提交（REPORT-002）

#### 2.2.0 归因字段与选择器（走查 #10 续）

| 字段 | 类型 | 必填 | 前端组件 | 后端校验 |
|------|------|------|----------|----------|
| `authorId` | `number`（JSON 字符串） | 是 | `<AuthorSelect />` · 数据来自 `GET /admin-api/ims/ip-group/author/page` | 存在且启用；1504 租户；**非** `UserSelect` |
| `accountId` | `number`（JSON 字符串） | 是 | `<AccountSelect />` · M4 `oa_account` | 1500/1501/1504；且账号属于作者 SMALL IP 组已绑账号池，否则 **1127** |

**级联（前端 · 2026-10-01 冻结）**：选作者 → 读作者 `ipGroupId` → `GET /admin-api/ims/ip-group/{groupId}/accounts` 过滤 AccountSelect；**禁止**新增 `authors/{id}/accounts` 聚合 API。

#### 2.2.1 POST /admin-api/ims/report/submit — 保存/提交填报单

**请求**：

```typescript
interface ReportSubmissionReq {
  templateId: number;
  period: string;                // 2025-06-10 / 2025-W24 / 2025-06
  authorId: number;              // author_user.id（FR-REPORT-011）
  accountId: number;             // oa_account.id
  /** 填报数据（按模板 schema），服务端按 fieldsSchema 做必填/范围/勾稽校验 */
  dataContent: Record<string, string | number | null>;
  attachments?: Array<{ fileName: string; ossKey: string }>;   // Excel/截图凭证
  asDraft: boolean;              // true=草稿保存，false=正式提交（触发校验+进审核队列）
}
```

**响应** `data`：

```typescript
interface ReportSubmissionVO {
  id: number;
  submissionNo: string;          // RS+日期+流水
  templateId: number;
  templateName: string;
  templateVersion: number;
  period: string;
  submitterUserId: number;
  submitterName: string;
  authorId: number;
  authorName: string;
  accountId: number;
  accountLabel: string;
  dataContent: Record<string, string | number | null>;
  attachments: Array<{ fileName: string; ossKey: string }>;
  submitStatus: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';   // 0 草稿/1 已提交/2 审核通过/3 已退回
  isOnTime: boolean;             // BR-106 按期标记（逾期标记迟交，仍计入分母）
  submittedAt?: string;
  version: number;               // 退回重报递增（历史留痕，RPT-S-R1）
  createdAt: string;
}
```

**错误码**：1122（勾稽校验失败，返回 `data.errors` 明细）、1123（RPT-T-R3 去重：**模板 + 周期 + 填报人 + 作者 + 账号** 唯一 · 2026-10-01 冻结）、1127（作者与账号 IP 组共池校验失败）、1500/1501/1504（作者/账号不存在或已停用/跨租户）、1001（必填/范围/归因缺失）。

#### 2.2.2 GET /admin-api/ims/report/submit/{submissionNo} — 填报单详情

**响应** `data`：`ReportSubmissionVO & { auditRounds: Array<{ round: number; conclusion: 'APPROVED' | 'REJECTED'; rejectReason?: string; auditorName: string; auditedAt: string }> }`。

#### 2.2.3 GET /admin-api/ims/report/submit/list — 填报单列表（分页）

**请求**（Query）：`PageParam` + `{ templateId?: number; period?: string; submitterUserId?: number; authorId?: number; accountId?: number; submitStatus?: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' }`

**响应** `data`：`PageResult<ReportSubmissionVO>`（R9 脱敏返回金额类字段 `"***"`）。

#### 2.2.4 GET /admin-api/ims/report/submit/pending — 待填报任务

**响应** `data`：`Array<{ taskId: number; templateId: number; templateName: string; period: string; dueTime: string; isNearDeadline: boolean; draftSubmissionNo?: string }>`（系统按周期自动生成填报待办，RPT-S-R3 上期数据带入参考）。

#### 2.2.5 GET /admin-api/ims/report/submit/last-period — 上期数据参考

**请求**（Query）：`{ templateId: number; period: string }` → **响应** `data`：`ReportSubmissionVO | null`（上一周期本人填报单，可覆盖带入）。

### 2.3 审核退回（REPORT-003）

#### 2.3.1 GET /admin-api/ims/report/audit/queue — 审核队列（分页）

**请求**（Query）：`PageParam` + `{ businessLine?: 'FINANCE' | 'BUSINESS' | 'ADMIN' }`

**响应** `data`：`PageResult<ReportSubmissionVO & { waitingHours: number; isTimeoutSla: boolean }>`（按模板业务线路由；审核时效 SLA 24 小时，超时推送审核人，RPT-A-R3）。

#### 2.3.2 PUT /admin-api/ims/report/audit/{submissionId} — 提交审核结论

**请求**：

```typescript
interface ReportAuditReq {
  conclusion: 'APPROVED' | 'REJECTED';    // 1 通过 / 2 退回
  /** 退回必填（结构化原因可选） */
  rejectReason?: string;
  rejectReasonTags?: string[];   // 如 ['数据来源不明', '勾稽不平', '附件缺失']
}
```

**响应** `data`：`{ submissionId: number; auditRound: number; newStatus: 'APPROVED' | 'REJECTED'; nextAction: 'COMPLETED' | 'BACK_TO_SUBMITTER' }`

**错误码**：1124（退回必须填写原因）、1125（3 轮退回后升级业务线负责人裁决，本次退回被拦截转升级流）、1126（非本线审核人无权限，RPT-A-R1 权限拦截）。

#### 2.3.3 GET /admin-api/ims/report/audit/records — 审核记录（分页）

**请求**（Query）：`PageParam` + `{ submissionId?: number; auditorUserId?: number; conclusion?: 'APPROVED' | 'REJECTED' }` → **响应** `data`：`PageResult<{ id: number; submissionId: number; submissionNo: string; auditorUserId: number; auditorName: string; auditRound: number; conclusion: 'APPROVED' | 'REJECTED'; rejectReason?: string; rejectReasonTags?: string[]; auditedAt: string }>`。

#### 2.3.4 GET /admin-api/ims/report/audit/diff — 退回前后数据对比

**请求**（Query）：`{ submissionId: number; fromVersion: number; toVersion: number }` → **响应** `data`：`{ fieldsDiff: Array<{ fieldKey: string; fieldLabel: string; oldValue: string | number | null; newValue: string | number | null; changed: boolean }> }`（退回修改后再提交历史版本留痕可对比，RPT-S-R1）。

### 2.4 完成率统计（REPORT-004）

#### 2.4.1 GET /admin-api/ims/report/stat/complete-rate — 完成率（BR-106）

**请求**（Query）：`{ statPeriod?: string; templateId?: number; deptId?: number }`

**响应** `data`：

```typescript
interface ReportCompleteRateResp {
  /** BR-106：按时提交报表数 / 应提交报表数，目标 > 95%；分子 = 审核通过的填报单（质量口径，RPT-C-R1） */
  totalCompleteRate: number;
  byTemplate: Array<{ templateId: number; templateName: string; shouldCount: number; submittedCount: number; onTimeCount: number; approvedCount: number; completeRate: number }>;
  byDept: Array<{ deptId: number; deptName: string; shouldCount: number; approvedCount: number; completeRate: number }>;
}
```

#### 2.4.2 GET /admin-api/ims/report/stat/trend — 周期趋势

**请求**（Query）：`{ dateRange?: [string, string]; templateId?: number }` → **响应** `data`：`Array<{ statPeriod: string; shouldCount: number; submittedCount: number; approvedCount: number; completeRate: number; rejectRate: number }>`（低于 90% 的线自动督办，RPT-C-R2）。

#### 2.4.3 GET /admin-api/ims/report/stat/missed — 未交清单

**请求**（Query）：`PageParam` + `{ statPeriod?: string; templateId?: number; deptId?: number }` → **响应** `data`：`PageResult<{ userId: number; userName: string; deptName: string; templateName: string; period: string; dueTime: string; status: 'MISSED' | 'LATE' | 'PENDING_AUDIT' }>`（支持 Excel 导出督办）。

#### 2.4.4 GET /admin-api/ims/report/stat/quality — 数据质量分析

**请求**（Query）：`{ statPeriod?: string }` → **响应** `data`：`{ totalRejectRate: number; byTemplate: Array<{ templateId: number; templateName: string; rejectRate: number; avgAuditRounds: number; topRejectReasons: Array<{ tag: string; count: number }> }>; slowAudits: Array<{ auditorName: string; avgHours: number; timeoutCount: number }> }`（退回率 > 20% 的模板提示检查字段设计合理性，RPT-C-R3）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**填报单（ReportSubmissionVO.submitStatus）**：

```
DRAFT ──提交（勾稽校验）──▶ SUBMITTED ──审核通过──▶ APPROVED（计入 BR-106 分子）
  │                          │
  └──草稿保存────────────────┘──退回（须填原因）──▶ REJECTED ──修改重报（version+1）──▶ SUBMITTED
                                                 （3 轮退回 → 升级业务线负责人裁决）
```

**模板（ReportTemplateVO.status）**：`ENABLED ↔ DISABLED`（有进行中填报单时仅可停用）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-106 | 每日上报完成率 > 95%（分子=审核通过，质量口径） | 2.4.1 |
| RPT-T-R1 | 字段变更生成新版本，在途单沿用旧版 | 2.1.3 |
| RPT-T-R2 | 勾稽校验（明细合计=汇总值）提交时强制 | 2.2.1 错误码 1122 |
| RPT-T-R3 | 一模板一周期一填报人一份 | 2.2.1 错误码 1123 |
| RPT-S-R1 | 退回重报版本留痕可对比 | 2.2.2 / 2.3.4 |
| RPT-S-R2 | 逾期标记迟交，计入完成率分母 | 2.2.1 isOnTime |
| RPT-S-R3 | 上期数据自动带入参考 | 2.2.4 / 2.2.5 |
| RPT-S-R4 | 作者×账号强关联（选择器+1127） | 2.2.0 / 2.2.1 |
| RPT-A-R1 | 退回必须填原因；3 轮退回升级 | 2.3.2 错误码 1124/1125 |
| RPT-A-R2 | 审核通过进统计口径 | 2.4.1 |
| RPT-A-R3 | 审核时效 24 小时 | 2.3.1 isTimeoutSla |
| RPT-C-R1~R3 | 质量口径/低于 90% 督办/退回率 20% 提示 | 2.4.x |
| V2-A1 | 周期任务自动生成填报待办（集群化调度） | 2.2.4 pending 任务生成 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 上报模板配置页（QueryBar + 表格） | 模板列表查询（周期/业务线/状态筛选） | GET /report/template/list |
| 模板设计抽屉（字段 Schema 可视化编辑器） | 创建/编辑模板（字段+校验+勾稽+填报人） | POST /report/template、PUT /report/template/{id} |
| 模板设计抽屉-预览 | 填报预览（字段渲染与校验自检） | POST /report/template/{id}/preview |
| 模板行操作 | 停用（ConfirmDialog） | DELETE /report/template/{id} |
| 个人工作台-待填报 | 待填报任务列表（临期高亮） | GET /report/submit/pending |
| 填报页（动态表单按 fieldsSchema 渲染 + FileUpload 附件） | 填报（草稿保存/提交，勾稽校验提示） | POST /report/submit |
| 填报页-上期参考 | 加载上期数据带入（可覆盖） | GET /report/submit/last-period |
| 填报单管理页 | 填报单列表查询 | GET /report/submit/list |
| 填报单详情抽屉 | 详情查看（含审核轮次与版本史） | GET /report/submit/{submissionNo} |
| 审核工作台（队列 Tab） | 审核队列加载（SLA 超时标记） | GET /report/audit/queue |
| 审核抽屉（数据+附件+结论表单） | 通过 / 退回（结构化原因选择） | PUT /report/audit/{submissionId} |
| 审核抽屉-数据对比 | 退回前后版本 Diff | GET /report/audit/diff |
| 审核记录页 | 审核记录查询 | GET /report/audit/records |
| 完成率统计看板 | 完成率 / 趋势 / 质量分析 | GET /report/stat/complete-rate、/trend、/quality |
| 未交督办页 | 未交清单导出 | GET /report/stat/missed |

（全文完）
