# PERF - 绩效考试 API 契约

> **模块范围**：05 绩效考试（V2，第 23~26 周，V2.3 批次）——PERF-001 绩效指标配置、PERF-002 绩效自动计算、PERF-003 在线考试、PERF-004 排名与预警。前置依赖：02/03/09/10 模块跑满 1 个月观察期（第 23 周后方可计算绩效基线）。
> **走查 #12**：OPS M3 单条考核 `/ops/perf/record/*` 与执行态 UX 见《PERF-绩效考核-API契约.md》；本文 `/admin-api/ims/perf/calc/*` 为 **月度批量** 能力，状态与 OPS 四态 **BLOCKED** 统一（§3）。**（2026-10-05 补注：ADR-IMS-005 已冻结——本文 `resultStatus` 为独立四态，与 OPS record 大写七态不自动合并，见 §3 补注）**
> **权威依据**：《IMS第二期PRD-V2.md》5.20~5.23；BR-105、BR-110、BR-117；V2-B1~B4 绩效自动取数引擎约束。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`metric_code → metricCode`、`period_month → periodMonth`）；周次波浪号格式。**关键口径**：**快照不可变**——绩效结果按周期生成不可变快照，重算生成新版本（V2-B4）；"竞品分析提交率"指标 V2 一律禁用（BR-110，V3 上线 04 竞品后启用，BR-206 联动）；得分 DECIMAL(6,2)。

---

## 1. API 总览表（共 28 个接口）

> 接口统计说明：PRD 5.22.6 的"题库管理"单行工程化展开为题目级 CRUD 3 个接口（创建/编辑/删除），考试域 11 个；总览表 28 行即 28 个接口。

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/perf/metric/list` | 指标列表（分页） | R1/R3（财务类）/R4 |
| 2 | POST | `/admin-api/ims/perf/metric` | 创建指标 | R4（主责）/R1/R3（财务类） |
| 3 | PUT | `/admin-api/ims/perf/metric/{id}` | 编辑指标（版本化） | 同上 |
| 4 | DELETE | `/admin-api/ims/perf/metric/{id}` | 删除（禁用） | R4/R1 |
| 5 | POST | `/admin-api/ims/perf/metric/bind-position` | 岗位指标集绑定（权重覆盖） | R4/R1 |
| 6 | POST | `/admin-api/ims/perf/metric/test-fetch` | 取数连通性测试（试取数） | R4/R1/R3 |
| 7 | GET | `/admin-api/ims/perf/metric/auto-coverage` | 自动取数覆盖率（BR-105） | R1/R4 |
| 8 | POST | `/admin-api/ims/perf/calc/run` | 手动触发计算（月度） | R4/R1 |
| 9 | GET | `/admin-api/ims/perf/calc/{period}` | 周期绩效结果列表（分页） | R1/R4（全量）/R9（脱敏） |
| 10 | GET | `/admin-api/ims/perf/calc/{period}/mine` | 本人绩效明细（发布后） | 员工本人 |
| 11 | PUT | `/admin-api/ims/perf/calc/detail/{id}/manual` | 人工补充指标值 | R4/R1 |
| 12 | PUT | `/admin-api/ims/perf/calc/{period}/approve` | 核准发布 | R4 |
| 13 | GET | `/admin-api/ims/perf/exam/questions` | 题库管理（分页） | R1/R2（主责）/R8 |
| 14 | POST | `/admin-api/ims/perf/exam/question` | 创建题目 | R2/R1 |
| 15 | PUT | `/admin-api/ims/perf/exam/question/{id}` | 编辑题目 | R2/R1 |
| 16 | DELETE | `/admin-api/ims/perf/exam/question/{id}` | 删除题目 | R1 |
| 17 | POST | `/admin-api/ims/perf/exam/paper` | 创建试卷（固定/随机组卷） | R2/R1 |
| 18 | PUT | `/admin-api/ims/perf/exam/paper/{id}/publish` | 发布试卷 | R2/R1 |
| 19 | POST | `/admin-api/ims/perf/exam/paper/{id}/assign` | 指派考生 | R2/R1 |
| 20 | POST | `/admin-api/ims/perf/exam/record/start` | 开始考试（生成答卷） | 被指派考生 |
| 21 | POST | `/admin-api/ims/perf/exam/record/submit` | 交卷（切屏计数随请求上报） | 考生本人 |
| 22 | PUT | `/admin-api/ims/perf/exam/record/{id}/grade` | 主观题阅卷 | R2/R8 |
| 23 | GET | `/admin-api/ims/perf/exam/record/scores` | 成绩列表（分页） | R1/R2/R4/R8（监考成绩）/考生（本人） |
| 24 | GET | `/admin-api/ims/perf/rank/period/{period}` | 周期排名看板 | R1/R2/R4（全量排名）/R9（脱敏） |
| 25 | GET | `/admin-api/ims/perf/rank/mine` | 本人排名与分档 | 员工本人 |
| 26 | GET | `/admin-api/ims/perf/rank/alerts` | 绩效预警清单（分页） | R1/R2/R4 |
| 27 | PUT | `/admin-api/ims/perf/rank/alert/{id}/handle` | 预警处置登记 | R4/R2 |
| 28 | GET | `/admin-api/ims/perf/rank/coaching-list` | 重点辅导名单（连续 2 月待改进） | R1/R4/部门负责人 |
---

---

## 2. 接口明细

### 2.1 绩效指标配置（PERF-001）

#### 2.1.1 GET /admin-api/ims/perf/metric/list — 指标列表（分页）

**请求**（Query）：`PageParam` + `{ metricName?: string; dataSource?: 'AUTO' | 'MANUAL' | 'EXAM'; status?: 'ENABLED' | 'DISABLED' }`

**响应** `data`：`PageResult<PerfMetricVO>`

```typescript
interface PerfMetricVO {
  id: number;
  metricCode: string;            // 如 TRAIN_FINISH_RATE
  metricName: string;
  /** 取数来源：1 系统自动 / 2 手工录入 / 3 考试成绩 */
  dataSource: 'AUTO' | 'MANUAL' | 'EXAM';
  /** 取数映射（模块/表/字段/口径），AUTO 指标必填 */
  sourceConfig?: {
    /** FIN 类指标在 V2.3 上线时置 DISABLED 锁态（FIN 模块已移 V3），随 11 财务上线（V3 第 33 周后）解禁（复用 BR-110 锁定机制） */
    module: 'TRAIN' | 'MEET' | 'REPORT' | 'LIVE' | 'FIN' | 'FLOW';
    metricExpression: string;    // 如 'finish_rate' / 'on_time_rate'
    periodType: 'MONTHLY';
  };
  /** 权重 DECIMAL(5,2)（岗位套用可覆盖，PER-M-R3） */
  weight: number;
  /** 得分规则：分段得分/线性映射 */
  scoreRule: {
    ruleType: 'SEGMENT' | 'LINEAR';
    segments?: Array<{ minValue: number; maxValue: number | null; score: number }>;
    linear?: { minMetric: number; maxMetric: number; minScore: number; maxScore: number };
  };
  status: 'ENABLED' | 'DISABLED';
  /** 状态说明：竞品分析提交率指标标注"V3 上线 04 后启用"（BR-110） */
  enableNote?: string;
  version: number;
}
```

**特殊指标**：`COMPETE_SUBMIT_RATE`（竞品分析提交率）V2 期间固定 `DISABLED`，`enableNote = '待 V3 竞品管理（04）上线后启用（BR-110/BR-206）'`（PER-M-R1，不入计算）。

#### 2.1.2 POST /admin-api/ims/perf/metric — 创建指标

**请求**：`Omit<PerfMetricVO, 'id' | 'version'>` → **响应** `data`：`PerfMetricVO`。

**错误码**：1151（指标编码已存在）、1152（得分规则非法：分段区间重叠或分数越界 [0,100]）、1001（参数校验）。

#### 2.1.3 PUT /admin-api/ims/perf/metric/{id} — 编辑指标

**请求**：同创建 → **响应** `data`：`PerfMetricVO`（`version` 自增）。指标口径变更走版本，历史周期按旧版本追溯（PER-M-R4）。

#### 2.1.4 DELETE /admin-api/ims/perf/metric/{id} — 删除（禁用）

**响应**：`data: null`（状态 → `DISABLED`；`COMPETE_SUBMIT_RATE` 不可启用，错误码 1153）。

#### 2.1.5 POST /admin-api/ims/perf/metric/bind-position — 岗位指标集绑定

**请求**：

```typescript
interface PerfPositionBindReq {
  positionCode: string;
  metricBindings: Array<{ metricId: number; weightOverride?: number }>;
}
```

**响应** `data`：`{ positionCode: string; boundCount: number; totalWeight: number }`。

**错误码**：1154（同岗位指标集权重合计 ≠ 100）。

#### 2.1.6 POST /admin-api/ims/perf/metric/test-fetch — 取数连通性测试

**请求**：`{ metricId: number; testPeriod: string }` → **响应** `data`：`{ fetchable: boolean; sampleValue?: number; errorReason?: string; elapsedMs: number }`（发布前验证取数连通性）。

#### 2.1.7 GET /admin-api/ims/perf/metric/auto-coverage — 覆盖率（BR-105）

**响应** `data`：`{ enabledMetricCount: number; autoMetricCount: number; autoCoverageRate: number; manualMetrics: Array<{ metricCode: string; metricName: string }> }`（BR-105：自动取数启用指标/启用指标总数，目标 > 80%）。

### 2.2 绩效自动计算（PERF-002）

#### 2.2.1 POST /admin-api/ims/perf/calc/run — 手动触发计算（月度）

**请求**：`{ periodMonth: string; scope?: { userIds?: number[]; deptIds?: number[] } }` → **响应** `data`：`{ calcTaskId: string; targetUserCount: number; message: string }`（每月 1 日凌晨自动触发，V2-A1 集群化调度；手动触发用于补算）。

**错误码**：1155（周期数据锁定后更正须 R4 审批——归并 FinanceStatus.LOCKED 语义）、1156（观察期不足：第 23 周前无基线数据）。

#### 2.2.2 GET /admin-api/ims/perf/calc/{period} — 周期绩效结果列表（分页）

**请求**（Query）：`PageParam` + `{ deptId?: number; resultStatus?: 'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED' | 'PENDING_MANUAL' }`

**响应** `data`：`PageResult<PerfResultVO>`

```typescript
interface PerfResultVO {
  id: number;
  periodMonth: string;           // yyyy-MM
  userId: number;
  userName: string;
  positionCode: string;
  deptName: string;
  /** 综合得分 = Σ(指标得分 × 权重)，BR-117，DECIMAL(6,2) */
  totalScore: number;
  rankInDept: number;
  resultStatus: 'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED' | 'PENDING_MANUAL';
  /** 指标版本与取数快照（不可变，V2-B4） */
  calcSnapshot: {
    metricVersions: Record<string, number>;
    fetchTime: string;
    engineVersion: string;
  };
  approvedBy?: number;
  approvedAt?: string;
}
```

**可见性**：发布前仅 R1/R4 可见（PER-C-R3）；R9 脱敏（分数保留、明细金额 `"***"`）。

#### 2.2.3 GET /admin-api/ims/perf/calc/{period}/mine — 本人绩效明细（发布后）

**响应** `data`：`PerfResultVO & { details: Array<{ metricCode: string; metricName: string; metricValue: number | null; metricScore: number; weight: number; dataStatus: 'AUTO' | 'MANUAL' | 'MISSING' }> }`。

**错误码**：1157（结果未发布，员工不可见）。

#### 2.2.4 PUT /admin-api/ims/perf/calc/detail/{id}/manual — 人工补充指标值

**请求**：`{ metricId: number; manualValue: number; supplementReason: string }` → **响应**：`data: null`。取数失败指标置"待人工"，不阻塞整体计算（PER-C-R1：缺项按 0 分计入并标记）。

**错误码**：1158（补充原因必填）。

#### 2.2.5 PUT /admin-api/ims/perf/calc/{period}/approve — 核准发布

**请求**：`{ approve: boolean; remark?: string; excludeUserIds?: number[] }` → **响应**：`{ publishedCount: number; pendingManualCount: number; publishedAt: string }`（R4 核准后发布，员工可见本人明细；发布后自动生成排名与分档，联动 PERF-004）。

### 2.3 在线考试（PERF-003）

#### 2.3.1 GET /admin-api/ims/perf/exam/questions — 题库（分页）

**请求**（Query）：`PageParam` + `{ knowledgeDomain?: string; questionType?: 'SINGLE' | 'MULTI' | 'JUDGE' | 'SHORT_ANSWER' }` → **响应** `data`：`PageResult<{ id: number; questionType: 'SINGLE' | 'MULTI' | 'JUDGE' | 'SHORT_ANSWER'; content: string; options?: string[]; answer: unknown; score: number; knowledgeDomain: string; createdAt: string }>`。

#### 2.3.2 POST /admin-api/ims/perf/exam/question — 创建题目

**请求**：`{ questionType: 'SINGLE' | 'MULTI' | 'JUDGE' | 'SHORT_ANSWER'; content: string; options?: string[]; answer: number | number[] | boolean | string; score: number; knowledgeDomain: string }` → **响应** `data`：`{ id: number }`（客观题 answer 判分依据；SHORT_ANSWER 走人工阅卷）。

#### 2.3.3 PUT /admin-api/ims/perf/exam/question/{id} — 编辑题目 / 2.3.4 DELETE — 删除

编辑请求同创建；删除响应 `data: null`（已被试卷引用的题目仅标记下架）。

#### 2.3.5 POST /admin-api/ims/perf/exam/paper — 创建试卷

**请求**：

```typescript
interface ExamPaperCreateReq {
  paperName: string;
  paperType: 'FIXED' | 'RANDOM';                   // 1 固定卷 / 2 随机组卷
  /** FIXED：固定题目列表 */
  questionIds?: number[];
  /** RANDOM：抽题策略（按知识域+题型+数量） */
  strategy?: Array<{
    knowledgeDomain: string;
    questionType: 'SINGLE' | 'MULTI' | 'JUDGE' | 'SHORT_ANSWER';
    count: number;
    scorePerQuestion: number;
  }>;
  totalScore: number;
  passScore: number;
  durationMinutes: number;       // 限时
}
```

**响应** `data`：`{ id: number; paperNo: string; status: 'DRAFT' | 'PUBLISHED' } & ExamPaperCreateReq`（EP+日期+流水）。

**错误码**：1159（总分校验失败：Σ题目分 ≠ totalScore）、1160（随机策略抽题数超过题库存量）。

#### 2.3.6 PUT /admin-api/ims/perf/exam/paper/{id}/publish — 发布试卷

**响应**：`data: null`（状态 → `PUBLISHED`）。

#### 2.3.7 POST /admin-api/ims/perf/exam/paper/{id}/assign — 指派考生

**请求**：`{ userIds: number[]; examWindow: { from: string; to: string } }` → **响应**：`{ assignedCount: number }`（考生工作台收到考试待办）。

#### 2.3.8 POST /admin-api/ims/perf/exam/record/start — 开始考试

**请求**：`{ paperId: number }` → **响应** `data`：

```typescript
interface ExamRecordVO {
  id: number;
  paperId: number;
  paperName: string;
  userId: number;
  /** 考题快照（随机卷每人不同，固定卷同题） */
  questions: Array<{ questionId: number; questionType: string; content: string; options?: string[]; score: number }>;
  startAt: string;
  deadline: string;              // startAt + durationMinutes
  switchScreenCount: number;     // 切屏计数（PER-E-R1：≥3 次强制交卷）
  examStatus: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'GRADED' | 'MAKEUP_EXAM';
}
```

**错误码**：1161（不在考试窗口内）、1162（重复开始：已有进行中答卷）。

#### 2.3.9 POST /admin-api/ims/perf/exam/record/submit — 交卷

**请求**：

```typescript
interface ExamSubmitReq {
  recordId: number;
  answers: Array<{ questionId: number; answer: number | number[] | boolean | string }>;
  /** 前端累计切屏次数（服务端校验：≥3 强制按已答计分，PER-E-R1） */
  switchScreenCount: number;
}
```

**响应** `data`：`{ recordId: number; examStatus: 'SUBMITTED' | 'GRADED'; objectiveScore: number; subjectiveScore: number | null; totalScore: number | null; forcedSubmit: boolean }`（客观题自动判分；主观题 48 小时内人工阅卷后 GRADED，PER-E-R2）。

**错误码**：1163（答卷非本人）、1164（已交卷不可重复提交）。

#### 2.3.10 PUT /admin-api/ims/perf/exam/record/{id}/grade — 主观题阅卷

**请求**：`{ gradings: Array<{ questionId: number; score: number; comment?: string }> }` → **响应**：`data: null`（阅卷完成 → `GRADED`，成绩计入 PERF-001 考试成绩类指标取数，PER-E-R4）。

#### 2.3.11 GET /admin-api/ims/perf/exam/record/scores — 成绩列表（分页）

**请求**（Query）：`PageParam` + `{ paperId?: number; userId?: number; examStatus?: string }` → **响应** `data`：`PageResult<{ id: number; paperId: number; paperName: string; userId: number; userName: string; score: number; objectiveScore: number; subjectiveScore: number; switchScreenCount: number; examStatus: string; isMakeup: boolean; startAt: string; submitAt: string }>`（考生仅可见本人成绩）。

**补考机制**：不及格可申请补考一次，补考成绩覆盖（标记 `MAKEUP_EXAM`，PER-E-R3）。

### 2.4 排名与预警（PERF-004）

#### 2.4.1 GET /admin-api/ims/perf/rank/period/{period} — 周期排名看板

**请求**（Query）：`{ deptId?: number }` → **响应** `data`：

```typescript
interface PerfRankVO {
  periodMonth: string;
  deptId: number;
  deptName: string;
  userId: number;
  userName: string;
  totalScore: number;
  rankNo: number;                // 部门内综合得分降序（BR-117）
  /** 分档：≥85 优秀 / 60~84 合格 / <60 待改进（分档线全局默认可按岗位组配置，PER-R-R1） */
  gradeLevel: 'EXCELLENT' | 'QUALIFIED' | 'IMPROVE';
  alertStatus: 'NONE' | 'ALERTED';
  consecutiveMonths: number;     // 连续待改进月数
}
```

`data`：`PageResult<PerfRankVO>`。排名隐私：员工本人仅可见本人排名与分档（2.4.2），管理者（R1/R2/R4）可见全量（PER-R-R4 排名隐私）。

#### 2.4.2 GET /admin-api/ims/perf/rank/mine — 本人排名与分档

**请求**（Query）：`{ periodMonth?: string }` → **响应** `data`：`PerfRankVO & { deptTotalCount: number; scoreDistribution: { excellent: number; qualified: number; improve: number } }`。

#### 2.4.3 GET /admin-api/ims/perf/rank/alerts — 绩效预警清单（分页）

**请求**（Query）：`PageParam` + `{ periodMonth?: string; handleStatus?: 'PENDING' | 'DONE' }` → **响应** `data`：`PageResult<{ id: number; periodMonth: string; userId: number; userName: string; deptName: string; totalScore: number; alertedAt: string; pushTargets: Array<'SELF' | 'SUPERIOR' | 'HR'>; handleStatus: 'PENDING' | 'DONE'; handleRemark?: string }>`（综合得分 < 60 触发预警推送本人+直属上级+HR，BR-117/PER-R-R2）。

#### 2.4.4 PUT /admin-api/ims/perf/rank/alert/{id}/handle — 预警处置登记

**请求**：`{ handleRemark: string; followUpPlan?: string }` → **响应**：`data: null`。

#### 2.4.5 GET /admin-api/ims/perf/rank/coaching-list — 重点辅导名单

**响应** `data`：`Array<PerfRankVO & { consecutiveMonths: number; lastTwoPeriods: Array<{ periodMonth: string; totalScore: number; gradeLevel: string }> }>`（连续 2 月待改进进入重点辅导名单，推送部门负责人+运营总监，PER-R-R3）。

---

## 3. 状态机与业务约束

> **补注（2026-10-05 · v2.6.34 · ADR-IMS-005 已冻结）**：`PerfResultVO.resultStatus` 为本域 **独立四态枚举** —— `CALCULATING`（批量计算中）/ `PENDING_MANUAL`（待人工补录）/ `PENDING_APPROVE`（待核准发布）/ `PUBLISHED`（已发布，对 R4/R9 可见）。该域与 OPS 单条考核记录 `dict_perf_status`（大写七态，写路径 SSOT = OPS `perf/record/*`）**不自动合并**：**禁止** `calculated→PENDING_APPROVE`、`confirmed→PUBLISHED` 等臆造等价；写路径分别 **单选**（批量核准仅 `PUT …/calc/{period}/approve`），读屏可 **双 Tab**（OPS 已确认 / IMS 已发布），**不得双写**。详见《ADR-IMS-005-绩效状态机待定.md》及《PERF-绩效考核-API契约.md》§2A。

### 3.1 状态机

**绩效结果（PerfResultVO.resultStatus）**：

```
CALCULATING ──计算完成──▶ PENDING_APPROVE ──R4 核准──▶ PUBLISHED（员工可见）
      │                        │                        │
      └─缺项转人工──▶ PENDING_MANUAL ──补充后──▶ PENDING_APPROVE
                               │
                               └──R4 驳回（数据修正后重算）
PUBLISHED ──更正（R4 审批）──▶ 重算生成新版本快照（旧快照审计保留，V2-B4）
```

**考试成绩（ExamRecordVO.examStatus）**：

```
NOT_STARTED ──开始（窗口内）──▶ IN_PROGRESS ──交卷/切屏≥3 强制交卷──▶ SUBMITTED
                                  │                                    │
                                  └──超时未交卷（按已答计）──────────────┤
                                                                       └──客观题判分 + 主观题人工阅卷（48h 内）──▶ GRADED
GRADED ──不及格申请补考（一次）──▶ MAKEUP_EXAM（成绩覆盖标记）
```

**排名分档（PerfRankVO.gradeLevel）**：`EXCELLENT（≥85）/ QUALIFIED（60~84）/ IMPROVE（<60，触发预警）`。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-105 | 自动取数覆盖率 > 80% | 2.1.7 |
| BR-110 | 竞品分析提交率指标 V2 剔除（禁用态） | 2.1.1/2.1.4 错误码 1153 |
| BR-117 | 综合得分 = Σ(指标得分×权重)；<60 触发预警 | 2.2.2 / 2.4.3 |
| PER-M-R1 | 禁用指标不入计算 | 2.2.1 计算引擎过滤 |
| PER-M-R2 | 覆盖率口径 | 2.1.7 |
| PER-M-R3 | 岗位权重覆盖不改全局定义 | 2.1.5 weightOverride |
| PER-M-R4 | 口径变更走版本，历史追溯 | 2.1.3 |
| PER-C-R1 | 缺项按 0 分计入并标记待人工 | 2.2.4 |
| PER-C-R2 | 入职/离职当月按在职天数折算 | 2.2.1 计算引擎 |
| PER-C-R3 | 核准前员工不可见 | 2.2.3 错误码 1157 |
| PER-C-R4 | 锁定后更正须 R4 审批留痕 | 2.2.1 错误码 1155 |
| PER-E-R1 | 切屏 ≥3 次强制交卷（按已答计） | 2.3.9 forcedSubmit |
| PER-E-R2 | 客观题自动判分，主观题 48h 人工阅卷 | 2.3.9 / 2.3.10 |
| PER-E-R3 | 补考一次，成绩覆盖标记 | 2.3.11 isMakeup |
| PER-E-R4 | 考试成绩作为指标取数来源 | 2.3.10（联动 PERF-001） |
| PER-R-R1 | 分档线 85/60 全局默认可配 | 2.4.1 gradeLevel |
| PER-R-R2 | 预警推送本人+上级+HR | 2.4.3 |
| PER-R-R3 | 连续 2 月待改进进辅导名单 | 2.4.5 |
| PER-R-R4 | 排名隐私（本人仅见本人） | 2.4.1/2.4.2 |
| V2-B1~B4 | 取数引擎：快照不可变、重算新版本（V2-B4） | 2.2.2 calcSnapshot |
| V2-A1 | 每月 1 日自动计算任务集群化（Redisson 锁） | 2.2.1 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 绩效指标配置页（QueryBar + 表格） | 指标列表查询（来源/状态筛选） | GET /perf/metric/list |
| 指标编辑抽屉 | 创建/编辑指标（取数映射+得分规则配置） | POST /perf/metric、PUT /perf/metric/{id} |
| 指标行操作 | 禁用（竞品指标锁定态说明） | DELETE /perf/metric/{id} |
| 岗位指标集绑定页 | 岗位绑定（权重覆盖编辑） | POST /perf/metric/bind-position |
| 指标编辑抽屉-试取数 | 取数连通性测试 | POST /perf/metric/test-fetch |
| 覆盖率指标卡 | 自动取数覆盖率（BR-105） | GET /perf/metric/auto-coverage |
| 绩效计算页 | 手动触发计算（月度补算，ConfirmDialog） | POST /perf/calc/run |
| 绩效结果列表页（发布前 R4 视角） | 周期结果列表（状态筛选） | GET /perf/calc/{period} |
| 绩效结果-人工补充抽屉 | 补充缺失指标值 | PUT /perf/calc/detail/{id}/manual |
| 绩效核准页 | 核准发布（排除待人工人员） | PUT /perf/calc/{period}/approve |
| 个人工作台-我的绩效 | 本人绩效明细（发布后） | GET /perf/calc/{period}/mine |
| 题库管理页（QueryBar + 表格） | 题库查询 / 创建 / 编辑 | GET /perf/exam/questions、POST /perf/exam/question、PUT /perf/exam/question/{id} |
| 组卷页（固定/随机策略配置） | 创建试卷 | POST /perf/exam/paper |
| 组卷行操作 | 发布 / 指派考生（考试窗口选择） | PUT /perf/exam/paper/{id}/publish、POST /perf/exam/paper/{id}/assign |
| 考试作答页（H5 同构，倒计时+切屏计数） | 开始考试 / 交卷 | POST /perf/exam/record/start、/submit |
| 阅卷工作台（主观题逐题评分） | 人工阅卷 | PUT /perf/exam/record/{id}/grade |
| 成绩列表页 | 成绩查询（考生/管理者双视角） | GET /perf/exam/record/scores |
| 排名看板页（管理者视角） | 周期排名（部门/分档 Tab） | GET /perf/rank/period/{period} |
| 个人工作台-我的排名 | 本人排名与分档（隐私视图） | GET /perf/rank/mine |
| 绩效预警页 | 预警清单 / 处置登记 | GET /perf/rank/alerts、PUT /perf/rank/alert/{id}/handle |
| 重点辅导名单页 | 连续待改进名单（双周期对比） | GET /perf/rank/coaching-list |

（全文完）
