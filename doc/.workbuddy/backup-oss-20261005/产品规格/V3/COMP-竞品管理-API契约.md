# COMP - 竞品管理 API 契约

> **模块范围**：04 竞品管理（V3，第 31~38 周，P2）——COMP-001 竞品分析提交、COMP-002 审核入库、COMP-003 竞品资产库。上线后联动启用 V2 绩效"竞品分析提交率"指标（BR-110 → BR-206 解禁）。
> **权威依据**：《IMS第三期PRD-V3.md》5.1~5.3；BR-201~BR-203、BR-214；V3 里程碑 M3（第 31~38 周）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章（COMP 域 1171~1180）；字段 camelCase（`analysis_no → analysisNo`、`comp_name_std → compNameStd`）；周次波浪号格式。**合规强制**：仅采集公开数据，来源字段必填（BR-202 合规要素）。

---

## 1. API 总览表（共 16 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/comp/analysis` | 提交竞品分析 | R5/R6（本人提交） |
| 2 | GET | `/admin-api/ims/comp/analysis/list` | 提交列表（分页） | R1/R4（全量）/R5/R6（本人） |
| 3 | GET | `/admin-api/ims/comp/analysis/{analysisNo}` | 分析详情 | 同上 |
| 4 | PUT | `/admin-api/ims/comp/analysis/{analysisNo}` | 编辑（退回后） | R5/R6（本人，退回后） |
| 5 | GET | `/admin-api/ims/comp/analysis/pending` | 待办提交任务（月度） | R5/R6（本人） |
| 6 | GET | `/admin-api/ims/comp/analysis/submit-rate` | 提交率统计（BR-201） | R1/R4/R9（脱敏） |
| 7 | GET | `/admin-api/ims/comp/audit/queue` | 审核队列（初审/终审，分页） | R8（初审）/R4（终审） |
| 8 | PUT | `/admin-api/ims/comp/audit/{analysisNo}` | 提交审核结论（通过入库/退回） | R8/R4 |
| 9 | GET | `/admin-api/ims/comp/audit/records` | 审核记录（分页） | R1/R4/R8/提交人（本人状态） |
| 10 | GET | `/admin-api/ims/comp/audit/merge-preview` | 归并预览（命中既有档案提示） | R8/R4 |
| 11 | GET | `/admin-api/ims/comp/asset/list` | 竞品档案列表（多维检索，分页） | R1/R2/R3（财务维度）/R4/R5/R6/R8/R9（只读） |
| 12 | GET | `/admin-api/ims/comp/asset/{assetNo}` | 档案详情（含版本时间轴） | 同上 |
| 13 | GET | `/admin-api/ims/comp/asset/{assetNo}/versions` | 版本历史 | 同上 |
| 14 | PUT | `/admin-api/ims/comp/asset/{assetNo}/alias` | 别名映射维护（归并键扩展） | R4/R1 |
| 15 | GET | `/admin-api/ims/comp/asset/compare` | 多竞品对比报告 | 同 11 |
| 16 | GET | `/admin-api/ims/comp/asset/heat-rank` | 引用热度排行（BR-214） | 同 11 |

---

## 2. 接口明细

### 2.1 竞品分析提交（COMP-001）

#### 2.1.1 POST /admin-api/ims/comp/analysis — 提交竞品分析

**请求**：

```typescript
interface CompAnalysisSubmitReq {
  periodMonth: string;           // 分析所属月 yyyy-MM
  compName: string;              // 竞品对象名称
  compAccountId?: string;        // 竞品账号 ID（可选，第二归并键）
  /** 数据来源说明：必填（合规要素，仅公开数据，BR-202） */
  dataSource: string;
  /** 维度字段数据（销售/GMV/价格带/内容策略/投放策略等） */
  dimensionData: Record<string, string | number | null>;
  /** 结论与可借鉴点 */
  conclusion: string;
  /** 附件（截图/表格凭证，FileUpload OSS 直传回执） */
  attachments?: Array<{ fileName: string; ossKey: string }>;
}
```

**响应** `data`：

```typescript
interface CompAnalysisVO {
  id: number;
  analysisNo: string;            // CA+日期+流水
  submitterUserId: number;
  submitterName: string;
  periodMonth: string;
  compName: string;
  compAccountId?: string;
  dataSource: string;
  dimensionData: Record<string, string | number | null>;
  conclusion: string;
  attachments: Array<{ fileName: string; ossKey: string }>;
  submitStatus: 'DRAFT' | 'SUBMITTED' | 'STORED' | 'REJECTED';   // 0 草稿/1 已提交/2 已入库/3 已退回
  /** 按期标记：提交截止 = 每月 25 日 22:00（可配）；按期含 3 日内补交（CMP-A-R1/R2） */
  isOnTime: boolean;
  submittedAt?: string;
  createdAt: string;
}
```

**错误码**：1171（数据来源必填——合规要素缺失）、1172（同一提交人同月同竞品重复提交）、1001（参数校验）。

#### 2.1.2 GET /admin-api/ims/comp/analysis/list — 提交列表（分页）

**请求**（Query）：`PageParam` + `{ submitterUserId?: number; periodMonth?: string; submitStatus?: 'DRAFT' | 'SUBMITTED' | 'STORED' | 'REJECTED' }`

**响应** `data`：`PageResult<CompAnalysisVO>`（R5/R6 限本人提交，服务端过滤）。

#### 2.1.3 GET /admin-api/ims/comp/analysis/{analysisNo} — 分析详情

**响应** `data`：`CompAnalysisVO & { auditRounds: Array<{ round: number; auditLevel: 'FIRST' | 'FINAL'; conclusion: 'STORED' | 'REJECTED'; rejectReason?: string; auditorName: string; auditedAt: string }> }`。

#### 2.1.4 PUT /admin-api/ims/comp/analysis/{analysisNo} — 编辑（退回后）

**请求**：`CompAnalysisSubmitReq` → **响应** `data`：`CompAnalysisVO`。仅 `DRAFT`/`REJECTED` 状态可编辑（退回修改重报，CMP-A-R3）。

#### 2.1.5 GET /admin-api/ims/comp/analysis/pending — 待办提交任务

**响应** `data`：`Array<{ periodMonth: string; dueTime: string; shouldCount: number; submittedCount: number; isNearDeadline: boolean }>`（按岗位指派，每人每月应提交份数可配，供 BR-201 统计）。

#### 2.1.6 GET /admin-api/ims/comp/analysis/submit-rate — 提交率（BR-201）

**请求**（Query）：`{ periodMonth?: string }` → **响应** `data`：`{ totalSubmitRate: number; byPerson: Array<{ userId: number; userName: string; deptName: string; shouldCount: number; onTimeCount: number; submitRate: number }>; target: number }`（BR-201：按期提交份数/应提交份数（按人月），目标 > 95%；数据同时供 V2 绩效取数，BR-206 解禁联动）。

### 2.2 审核入库（COMP-002）

#### 2.2.1 GET /admin-api/ims/comp/audit/queue — 审核队列（分页）

**请求**（Query）：`PageParam` + `{ auditLevel: 'FIRST' | 'FINAL' }` → **响应** `data`：`PageResult<CompAnalysisVO & { waitingHours: number; isTimeoutSla: boolean }>`（初审 SLA 48 小时，超时督办，CMP-B-R4）。

#### 2.2.2 PUT /admin-api/ims/comp/audit/{analysisNo} — 提交审核结论

**请求**：

```typescript
interface CompAuditReq {
  auditLevel: 'FIRST' | 'FINAL';       // 1 初审（R8）/ 2 终审（R4）
  conclusion: 'STORED' | 'REJECTED';   // 1 通过入库 / 2 退回
  /** 退回必填（结构化） */
  rejectReason?: string;
  rejectReasonTags?: string[];   // 如 ['来源不可靠', '字段缺失', '结论不明确']
}
```

**响应** `data`：`{ analysisNo: string; newStatus: 'SUBMITTED' | 'STORED' | 'REJECTED'; nextAction: 'TO_FINAL' | 'MERGE_STORED' | 'BACK_TO_SUBMITTER'; mergeInfo?: { assetNo: string; compNameStd: string; newVersion: number } }`

**错误码**：1173（退回必须填写原因）、1174（三要素校验：来源可靠+字段齐全+结论明确方可通过，BR-202）、1175（3 轮退回升级运营总监裁决）、1176（越级审核：初审未通过不可进终审）。

**联动**：终审通过触发归并入库（BR-203）——按归并键（标准化竞品名称/账号 ID）归并到竞品档案并版本累加；入库完成反馈提交人。

#### 2.2.3 GET /admin-api/ims/comp/audit/records — 审核记录（分页）

**请求**（Query）：`PageParam` + `{ analysisNo?: string; auditorUserId?: number; conclusion?: string }` → **响应** `data`：`PageResult<{ id: number; analysisNo: string; auditRound: number; auditLevel: 'FIRST' | 'FINAL'; conclusion: string; rejectReason?: string; auditorUserId: number; auditorName: string; auditedAt: string }>`。

#### 2.2.4 GET /admin-api/ims/comp/audit/merge-preview — 归并预览

**请求**（Query）：`{ compName: string; compAccountId?: string }` → **响应** `data`：`{ matched: boolean; assetNo?: string; compNameStd?: string; latestVersion?: number; matchedBy: 'NAME_STD' | 'ACCOUNT_ID' | 'ALIAS' | 'NONE'; similarity: number }`（提交/入库前命中既有档案提示，避免重复建档）。

### 2.3 竞品资产库（COMP-003）

#### 2.3.1 GET /admin-api/ims/comp/asset/list — 档案列表（分页）

**请求**（Query）：`PageParam` + `{ compNameStd?: string; platform?: PlatformType; latestVersionRange?: [string, string]; submitterUserId?: number; dimensionField?: { key: string; value: string } }`

**响应** `data`：`PageResult<CompAssetVO>`

```typescript
interface CompAssetVO {
  id: number;
  assetNo: string;               // CP+日期+流水
  /** 标准化竞品名（归并键，唯一索引：去空格/统一大小写/别名映射，CMP-C-R1） */
  compNameStd: string;
  compAccountId?: string;        // 第二归并键
  platform: PlatformType;
  baseInfo: Record<string, string | number | null>;   // 基本信息
  latestVersion: number;
  /** 引用计数（BR-214）：被报表/看板/穿透查询引用次数 */
  referenceCount: number;
  /** 资产状态：追踪中/暂停/归档（CompeteStatus） */
  status: CompeteStatus;         // 'TRACKING' | 'PAUSED' | 'ARCHIVED'
  createdAt: string;
  updatedAt: string;
}
```

#### 2.3.2 GET /admin-api/ims/comp/asset/{assetNo} — 档案详情

**响应** `data`：`CompAssetVO & { versionTimeline: Array<{ version: number; sourceAnalysisNo: string; dimensionData: Record<string, string | number | null>; conclusion: string; archivedAt: string; isValid: boolean }>; aliasList: string[] }`（版本时间序列可对比；版本只增不改，错误数据走"标记无效"，CMP-C-R2）。

#### 2.3.3 GET /admin-api/ims/comp/asset/{assetNo}/versions — 版本历史

**请求**（Query）：`{ version?: number }` → **响应** `data`：`Array<{ version: number; sourceAnalysisNo: string; dimensionData: Record<string, string | number | null>; conclusion: string; archivedAt: string; isValid: boolean; markedInvalidReason?: string }>`。

#### 2.3.4 PUT /admin-api/ims/comp/asset/{assetNo}/alias — 别名映射维护

**请求**：`{ addAliases?: string[]; removeAliases?: string[] }` → **响应**：`data: null`。别名映射扩展归并键（同一竞品不同叫法后续提交自动归并到同一档案）。

**错误码**：1177（别名与既有其他档案归并键冲突）。

#### 2.3.5 GET /admin-api/ims/comp/asset/compare — 多竞品对比报告

**请求**（Query）：`{ assetNos: string[]; dimensionKeys?: string[]; version?: 'LATEST' }` → **响应** `data`：`{ assetNos: string[]; dimensionMatrix: Array<{ dimensionKey: string; values: Array<string | number | null> }>; conclusions: Array<{ assetNo: string; compNameStd: string; conclusion: string }>; generatedAt: string }`（多竞品多维横向对比，可导出）。

#### 2.3.6 GET /admin-api/ims/comp/asset/heat-rank — 引用热度排行

**请求**（Query）：`{ topN?: number; dateRange?: [string, string] }` → **响应** `data`：`Array<{ rank: number; assetNo: string; compNameStd: string; platform: string; referenceCount: number; recentReferrers: Array<{ refType: 'REPORT' | 'DASHBOARD' | 'TRACE' | 'SHARE'; refName: string; refAt: string }> }>`（引用计数在报表/看板/穿透引用时累加，CMP-C-R3；热度排行纳入资产价值评估，BR-214）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**竞品分析提交（CompAnalysisVO.submitStatus）**：

```
DRAFT ──提交──▶ SUBMITTED ──初审通过（R8）──▶ （终审队列）
  │                 │                            │
  └──草稿保存────────┘──退回（须填原因）──▶ REJECTED ──修改重报──▶ SUBMITTED
                    │                            │（3 轮退回 → 升级 R4 裁决）
                    └──终审通过（R4）──▶ STORED（归并入库：命中档案版本累加 / 新建档案）
```

**竞品档案（CompAssetVO.status，CompeteStatus）**：`TRACKING ↔ PAUSED → ARCHIVED`（有引用时禁止删除，仅归档，CMP-C-R4）。

**版本有效性**：`isValid: true → false（标记无效，附原因；不可物理删除）`。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-201 | 提交率 > 95%（按人月；按期含 3 日内补交） | 2.1.6 |
| BR-202 | 入库三要素：来源可靠+字段齐全+结论明确 | 2.2.2 错误码 1174 |
| BR-203 | 归并键 = 标准化名称/账号 ID；版本累加 | 2.2.4 / 2.2.2 mergeInfo |
| BR-214 | 引用计数与热度排行 | 2.3.6 |
| CMP-A-R1 | 截止每月 25 日 22:00（可配），逾期可补交 | 2.1.1 isOnTime |
| CMP-A-R2 | 按期含 3 日内补交 | 2.1.6 口径 |
| CMP-A-R3 | 退回可修改重报 | 2.1.4 |
| CMP-A-R4 | 同一竞品多次提交归并（以入库为准） | 2.2.2 归并入库 |
| CMP-B-R1 | 三要素齐全方可通过 | 同 BR-202 |
| CMP-B-R2 | 终审通过触发归并入库 | 2.2.2 |
| CMP-B-R3 | 3 轮退回升级 R4 裁决 | 2.2.2 错误码 1175 |
| CMP-B-R4 | 初审 SLA 48 小时 | 2.2.1 isTimeoutSla |
| CMP-C-R1 | 归并键标准化（去空格/大小写/别名映射） | 2.3.1 compNameStd |
| CMP-C-R2 | 版本只增不改，错误走标记无效 | 2.3.3 isValid |
| CMP-C-R3 | 引用计数累加 | 2.3.6 |
| CMP-C-R4 | 有引用禁止删除，仅归档 | 2.3.1 status 约束 |
| BR-206 | 04 上线 + 首月数据完整后绩效指标解禁 | 2.1.6（联动 V2 PERF 域 COMPETE_SUBMIT_RATE 指标 ENABLED） |
| 9.2 合规 | 仅公开数据，来源必填 | 2.1.1 dataSource |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 竞品分析提交页（模板表单 + FileUpload 附件） | 提交竞品分析（维度数据+结论+凭证） | POST /comp/analysis |
| 个人工作台-竞品待办 | 月度待办提交任务（临期高亮） | GET /comp/analysis/pending |
| 提交列表页（QueryBar + 表格） | 提交列表查询 | GET /comp/analysis/list |
| 提交详情抽屉 | 详情查看（审核轮次）/ 退回后编辑 | GET /comp/analysis/{analysisNo}、PUT /comp/analysis/{analysisNo} |
| 提交率指标卡 | 提交率统计（BR-201，绩效解禁联动提示） | GET /comp/analysis/submit-rate |
| 审核工作台（队列 Tab：初审/终审） | 审核队列加载（SLA 超时标记） | GET /comp/audit/queue |
| 审核抽屉 | 通过入库 / 退回（结构化原因）/ 归并预览提示 | PUT /comp/audit/{analysisNo}、GET /comp/audit/merge-preview |
| 审核记录页 | 审核记录查询 | GET /comp/audit/records |
| 竞品资产库页（多维检索 QueryBar） | 档案列表查询 | GET /comp/asset/list |
| 档案详情抽屉 | 详情（版本时间轴对比视图） | GET /comp/asset/{assetNo} |
| 档案版本页 | 版本历史查看 | GET /comp/asset/{assetNo}/versions |
| 档案维护（R4/R1） | 别名映射维护 | PUT /comp/asset/{assetNo}/alias |
| 竞品对比报告页 | 多竞品多维横向对比 | GET /comp/asset/compare |
| 热度排行页 | 引用热度排行（BR-214） | GET /comp/asset/heat-rank |

（全文完）
