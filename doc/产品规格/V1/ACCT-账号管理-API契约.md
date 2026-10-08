# ACCT - 账号管理 API 契约

> **模块范围**：08 账号管理（V1，第 5~9 周，补齐类）——ACCT-001 账号领用、ACCT-002 账号流转/收回、ACCT-003 离职归还、ACCT-004 冲话费管理、ACCT-005 领用记录时间线。
> **权威依据**：《IMS第一期PRD-V1.md》5.8~5.12；《共享技术规范-数据库与API.md》7.2/8.3。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》；字段 camelCase；关键写接口（冲话费）携带幂等 `clientToken` 请求头。

---

## 1. API 总览表（共 22 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/account/apply` | 发起领用申请 | R5/R6/R7（本人） |
| 2 | GET | `/admin-api/ims/account/apply/list` | 申请单列表（分页） | R1/R4/R9（脱敏）/R5/R6/R7（本人） |
| 3 | GET | `/admin-api/ims/account/apply/{id}` | 申请详情 | 同上 |
| 4 | PUT | `/admin-api/ims/account/apply/{id}/approve` | 审批（通过/拒绝） | R1/R4 |
| 5 | PUT | `/admin-api/ims/account/apply/{id}/confirm` | 交接确认生效 | R1/R4/申请人 |
| 6 | POST | `/admin-api/ims/account/transfer` | 发起流转/收回 | R4/R5（经手发起） |
| 7 | GET | `/admin-api/ims/account/transfer/list` | 流转单列表（分页） | R1/R4/R9（脱敏）/R5（本人经手） |
| 8 | PUT | `/admin-api/ims/account/transfer/{id}/confirm` | 新责任人确认生效 | 新责任人 |
| 9 | PUT | `/admin-api/ims/account/transfer/{id}/revoke` | 撤销流转单 | R1/R4 |
| 10 | POST | `/admin-api/ims/account/return/generate` | 生成离职归还单（事件触发/手动） | R1/R2（手动补建） |
| 11 | GET | `/admin-api/ims/account/return/list` | 归还单列表（分页） | R1/R2/R3/R4/R5（涉及只读）/R9 |
| 12 | GET | `/admin-api/ims/account/return/{id}` | 归还单详情（含明细） | 同上 |
| 13 | PUT | `/admin-api/ims/account/return/item/{itemId}` | 处理归还项 | R2（主责）/R1 |
| 14 | PUT | `/admin-api/ims/account/return/{id}/close` | 归还闭环（校验 BR-015） | R2/R1 |
| 15 | POST | `/admin-api/ims/account/recharge` | 登记充值记录（幂等 clientToken） | R3（主责） |
| 16 | GET | `/admin-api/ims/account/recharge/list` | 充值记录列表（分页） | R1/R3/R4/R9 |
| 17 | PUT | `/admin-api/ims/account/recharge/{id}` | 编辑记录 | R3 |
| 18 | POST | `/admin-api/ims/account/recharge/verify` | 触发月度核对 | R3 |
| 19 | GET | `/admin-api/ims/account/recharge/summary` | 成本汇总报表 | R1/R3/R4/R9 |
| 20 | GET | `/admin-api/ims/account/timeline/{accountId}` | 账号时间线 | R1/R2/R4/R9（脱敏）/R5/R6/R7（本人相关） |
| 21 | GET | `/admin-api/ims/account/timeline/{accountId}/export` | 导出交接凭证 PDF（异步导出） | 同上 |
| 22 | GET | `/admin-api/ims/account/timeline/events` | 事件明细查询（分页筛选） | 同上 |

（注：账号台账基础登记复用既有 08 账号登记能力，本契约仅覆盖补齐类流程接口；账号详情页内的"账号信息"由既有接口提供。）

---

## 2. 接口明细

### 2.1 账号领用（ACCT-001）

#### 2.1.1 POST /admin-api/ims/account/apply — 发起领用申请

**请求**：

```typescript
interface AccountApplyCreateReq {
  accountId: number;             // 账号池账号（status=IN_POOL）
  purpose: string;               // 用途说明
  planStart: string;             // ISO 8601
  planEnd: string;
}
```

**响应** `data`：`AccountApplyVO`

```typescript
interface AccountApplyVO {
  id: number;
  applyNo: string;               // AP+日期+流水
  accountId: number;
  accountNo: string;
  platform: PlatformType;
  applicantUserId: number;
  purpose: string;
  planStart: string;
  planEnd: string;
  approverUserId?: number;
  applyStatus: ApplyStatus;      // 0 待审批 / 1 已领用 / 2 拒绝 / 3 已归还
  handoverDetail?: HandoverDetail;
  createdAt: string;
}

type ApplyStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'RETURNED';

interface HandoverDetail {
  passwordReset: boolean;        // 只存"已重置"事实，APP-R4 密码不明文
  mobileRebound?: boolean;       // 绑定手机变更事实
  remark?: string;
}
```

**错误码**：1021（账号已被领用，APP-R1）、1022（账号冻结态）、1001（参数校验失败）。

#### 2.1.2 GET /admin-api/ims/account/apply/list — 申请单列表（分页）

**请求**（Query）：`PageParam` + `{ applyStatus?: ApplyStatus; applicantUserId?: number; accountId?: number; timeRange?: [string, string] }`

**响应** `data`：`PageResult<AccountApplyVO>`

#### 2.1.3 GET /admin-api/ims/account/apply/{id} — 申请详情

**响应** `data`：`AccountApplyVO`（含审批轨迹列表 `approvalTracks: Array<{ step: number; approverName: string; action: string; comment?: string; actedAt: string }>`）。

#### 2.1.4 PUT /admin-api/ims/account/apply/{id}/approve — 审批

**请求**：

```typescript
interface AccountApplyApproveReq {
  action: 'APPROVE' | 'REJECT';
  comment?: string;
}
```

**响应**：`data: null`。审批流：直属上级 → 运营总监；超 24 小时未处理工作台升级提醒（APP-R2）。审批通过后需走 2.1.5 交接确认才生效。

#### 2.1.5 PUT /admin-api/ims/account/apply/{id}/confirm — 交接确认生效

**请求**：`HandoverDetail`（密码已重置等事实记录）→ **响应**：`data: null`。生效即账号责任人变更 + 时间线写入（ACCT-005 联动）。

### 2.2 账号流转/收回（ACCT-002）

#### 2.2.1 POST /admin-api/ims/account/transfer — 发起流转/收回

**请求**：

```typescript
interface AccountTransferCreateReq {
  accountId: number;
  transferType: 'TRANSFER' | 'RECALL';   // 1 流转 / 2 收回
  toUserId?: number;            // 流转目标（收回单为空）
  reasonType: 'TRANSFER_POSITION' | 'PRE_RESIGN' | 'VIOLATION' | 'BUSINESS_ADJUST';
  remark?: string;
}
```

**响应** `data`：`AccountTransferVO`

```typescript
interface AccountTransferVO {
  id: number;
  transferNo: string;           // TR+日期+流水
  accountId: number;
  accountNo: string;
  fromUserId: number;
  toUserId?: number;            // 收回单为空
  transferType: 'TRANSFER' | 'RECALL';
  reasonType: string;
  remark?: string;
  status: 'PENDING_CONFIRM' | 'EFFECTIVE' | 'REVOKED';   // 0 待确认 / 1 生效 / 2 撤销
  createdAt: string;
  effectiveAt?: string;
}
```

**错误码**：1023（单据状态非法）、1022（账号冻结）。

#### 2.2.2 GET /admin-api/ims/account/transfer/list — 流转单列表（分页）

**请求**（Query）：`PageParam` + `{ status?: string; transferType?: string; fromUserId?: number; toUserId?: number }` → **响应**：`PageResult<AccountTransferVO>`

#### 2.2.3 PUT /admin-api/ims/account/transfer/{id}/confirm — 新责任人确认

**请求**：`{ accept: boolean; remark?: string }` → **响应**：`data: null`。TRF-R1：确认后生效；收回后账号进入"账号池-冻结"态，需管理员解冻（TRF-R2）；生效联动资产绑定转移提示（是否同步转资产，前端 ConfirmDialog 提供选项）。

#### 2.2.4 PUT /admin-api/ims/account/transfer/{id}/revoke — 撤销

**请求**：`{ remark: string }` → **响应**：`data: null`。仅待确认态可撤销。

### 2.3 离职归还（ACCT-003）

#### 2.3.1 POST /admin-api/ims/account/return/generate — 生成归还单

**请求**：

```typescript
interface ReturnOrderGenerateReq {
  userId: number;                // 离职人
  dingtalkResignDate: string;    // yyyy-MM-dd
  /** 手动补建标记 */
  manual: boolean;
}
```

**响应** `data`：`ReturnOrderVO`（系统汇总名下账号、资产、证件生成明细项）。

```typescript
interface ReturnOrderVO {
  id: number;
  returnNo: string;              // RT+日期+流水
  userId: number;
  userNickname: string;
  dingtalkResignDate: string;
  status: 'IN_PROGRESS' | 'CLOSED' | 'EXCEPTION_SUSPENDED';   // 0 进行中 / 1 已闭环 / 2 异常挂起
  items: ReturnItemVO[];
  closedAt?: string;
  createdAt: string;
}

interface ReturnItemVO {
  id: number;                    // itemId
  returnOrderId: number;
  itemType: 'ACCOUNT' | 'ASSET' | 'CERT';
  itemId: number;
  itemSnapshot: string;          // 摘要（账号编号/资产编码/证件类型）
  itemStatus: 'PENDING' | 'RETURNED' | 'TRANSFERRED' | 'DISPUTED';   // 0 待归还 / 1 已归还 / 2 转交 / 3 争议
  handlerUserId?: number;
  remark?: string;
}
```

D+0 自动生成（RET-R1，钉钉离职事件触发）；D+7 未闭环冻结 + 升级行政负责人（RET-R2）。

#### 2.3.2 GET /admin-api/ims/account/return/list — 归还单列表（分页）

**请求**（Query）：`PageParam` + `{ status?: string; userId?: number; timeRange?: [string, string] }` → **响应**：`PageResult<ReturnOrderVO>`（列表不含 items 全量，仅 itemCount 汇总）。

#### 2.3.3 GET /admin-api/ims/account/return/{id} — 归还单详情

**响应** `data`：`ReturnOrderVO`（含全部 items）。

#### 2.3.4 PUT /admin-api/ims/account/return/item/{itemId} — 处理归还项

**请求**：`{ itemStatus: 'RETURNED' | 'TRANSFERRED' | 'DISPUTED'; transferToUserId?: number; remark?: string }` → **响应**：`data: null`。争议项走异常流程行政管理员裁决（RET-R4）。

#### 2.3.5 PUT /admin-api/ims/account/return/{id}/close — 归还闭环

**请求**：`{}` → **响应**：`data: null`。闭环条件：全部 item ∈ {已归还, 转交}（RET-R3 / BR-015），不满足返回 1024；闭环后联动 AUTH-002 关闭权限、解除冻结。

### 2.4 冲话费管理（ACCT-004）

#### 2.4.1 POST /admin-api/ims/account/recharge — 登记充值记录（幂等）

**请求**（Header `clientToken` 强制）：

```typescript
interface RechargeCreateReq {
  accountId: number;
  amount: number;                // DECIMAL(12,2)，元
  channel: string;               // 充值渠道字典
  voucherUrl?: string;           // 凭证下载地址（RC-R3：amount>5000 必填，FileUpload 服务端上传回执 fileKey）
  rechargeDate: string;          // yyyy-MM-dd
}
```

**响应** `data`：

```typescript
interface RechargeRecordVO {
  id: number;
  accountId: number;
  accountNo: string;
  amount: number;
  channel: string;
  voucherUrl?: string;
  rechargeDate: string;
  verifyStatus: 'UNVERIFIED' | 'MATCHED' | 'DIFF';   // 0 未核对 / 1 一致 / 2 差异
  verifyDiff?: number;
  operatorUserId: number;
  createdAt: string;
}
```

**错误码**：1025（凭证必填）、1001（金额格式）、幂等冲突返回原单（同 clientToken）。

#### 2.4.2 GET /admin-api/ims/account/recharge/list — 充值记录列表（分页）

**请求**（Query）：`PageParam` + `{ accountId?: number; verifyStatus?: string; month?: string; channel?: string }` → **响应**：`PageResult<RechargeRecordVO>`

#### 2.4.3 PUT /admin-api/ims/account/recharge/{id} — 编辑记录

**请求**：`RechargeCreateReq` → **响应**：`data: null`（未核对状态才可编辑）。

#### 2.4.4 POST /admin-api/ims/account/recharge/verify — 触发月度核对

**请求**：`{ month: string; accountIds?: number[] }` → **响应**：`{ verifyTaskId: string; message: string }`。差异率 ≥ 2% 生成财务核查工单（RC-R2 / BR-017，错误码 1026）；每月 5 日前完成上月核对（RC-R1）。

#### 2.4.5 GET /admin-api/ims/account/recharge/summary — 成本汇总报表

**请求**（Query）：`{ month: string; groupBy: 'ACCOUNT' | 'DEPT' | 'PLATFORM' }`

**响应** `data`：

```typescript
interface RechargeSummaryResp {
  groupBy: 'ACCOUNT' | 'DEPT' | 'PLATFORM';
  rows: Array<{ dimKey: string; dimLabel: string; totalAmount: number; recordCount: number; diffAmount: number }>;
}
```

### 2.5 领用记录时间线（ACCT-005）

#### 2.5.1 GET /admin-api/ims/account/timeline/{accountId} — 账号时间线

**请求**（Query）：`{ eventTypes?: TimelineEventType[]; timeRange?: [string, string] }`

```typescript
type TimelineEventType = 'REGISTER' | 'APPLY' | 'TRANSFER' | 'RETURN' | 'RECHARGE' | 'FREEZE' | 'UNFREEZE' | 'CANCEL';
```

**响应** `data`（事件倒序，TL-R3）：

```typescript
interface AccountTimelineResp {
  accountId: number;
  accountNo: string;
  events: TimelineEventVO[];     // 倒序数组（单账号事件量可控，不分页；跨账号检索走 /events）
}

interface TimelineEventVO {
  id: number;
  accountId: number;
  eventType: TimelineEventType;
  refNo?: string;                // 关联单据号（AP/TR/RT 单号）
  refId?: number;
  operatorUserId: number;
  operatorName: string;
  eventTime: string;
  /** 事件时账号状态快照（责任人等） */
  snapshot: Record<string, unknown>;
}
```

**约束**：事件只增不改（TL-R1 审计不可篡改）；单据操作事务内同步写入（TL-R2）。

#### 2.5.2 GET /admin-api/ims/account/timeline/{accountId}/export — 导出交接凭证

**响应**：`{ exportTaskId: string; message: string }`（异步导出 PDF，回执下载链接 · 服务端文件目录）。

#### 2.5.3 GET /admin-api/ims/account/timeline/events — 事件明细查询（分页）

**请求**（Query）：`PageParam` + `{ accountId?: number; eventType?: TimelineEventType; operatorUserId?: number; timeRange?: [string, string] }` → **响应**：`PageResult<TimelineEventVO>`

---

## 3. 状态机与业务约束

### 3.1 状态机

**领用申请单（ApplyStatus）**：

```
PENDING_APPROVAL ──审批拒绝──▶ REJECTED（归档）
       │
     审批通过（两级：直属上级→运营总监）
       ▼
PENDING_HANDOVER（交接执行：重置密码等）──confirm──▶ APPROVED（已领用，责任人变更+时间线）
       │                                              │
       │                                        归还/收回（TRANSFER/RETURN 流程）
       ▼                                              ▼
                                              RETURNED
```

**流转单（TransferVO.status）**：`PENDING_CONFIRM →（新责任人确认）EFFECTIVE /（撤销）REVOKED`

**归还单（ReturnOrderVO.status）**：

```
IN_PROGRESS ──全部 item ∈ {RETURNED, TRANSFERRED}──close──▶ CLOSED（权限关闭、解冻）
     │        │
     │     争议项（DISPUTED）──行政裁决──▶ 恢复处理
     ▼
EXCEPTION_SUSPENDED（D+7 未闭环：冻结+升级）
```

**账号状态（AccountStatus，全局枚举）**：`IN_POOL ⇄ IN_USE ⇄ FROZEN → CANCELLED`（领用生效 IN_POOL→IN_USE；收回 IN_USE→FROZEN；解冻 FROZEN→IN_POOL；离职未闭环 IN_USE→FROZEN）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-004 | 领用线上化率 = 100% | 2.1.x 全流程线上单据 |
| BR-012 | 领用后 15 天无使用记录提醒 | 2.1.5 生效后定时任务触发（工作台待办） |
| BR-015 | 离职归还闭环前冻结 | 2.3.1/2.3.5（错误码 1024） |
| BR-016 | 多主体字段预留（tenantId 接口不透出） | 全部 VO 不含 tenantId |
| BR-017 | 冲话费月度核对差异率 < 2% | 2.4.4 verify（错误码 1026） |
| APP-R1~R4 | 单责任人/24h 升级/15 天提醒/密码不存明文 | 2.1.x（HandoverDetail 仅存事实） |
| TRF-R1~R3 | 新责任人确认/收回冻结/时间线计入 | 2.2.x |
| RET-R1~R4 | D+0 生成/D+7 冻结升级/闭环条件/争议裁决 | 2.3.x |
| RC-R1~R3 | 每月 5 日前核对/差异工单/凭证必填 | 2.4.x |
| TL-R1~R3 | 只增不改/事务内写入/倒序+区间过滤 | 2.5.x |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 工作台-发起领用入口（DetailDrawer 表单） | 提交领用申请 | POST /account/apply |
| 账号领用管理页（QueryBar+表格） | 申请单列表/筛选 | GET /account/apply/list |
| 领用单详情抽屉 | 查看详情/审批轨迹 | GET /account/apply/{id} |
| 领用单详情抽屉-审批操作（ConfirmDialog） | 通过/拒绝审批 | PUT /account/apply/{id}/approve |
| 领用单详情抽屉-交接确认 | 填写交接事实（密码已重置等）确认生效 | PUT /account/apply/{id}/confirm |
| 流转管理页（表格+发起流转抽屉） | 发起流转/收回、列表查询 | POST /account/transfer、GET /account/transfer/list |
| 待确认流转抽屉 | 新责任人确认/撤销 | PUT /account/transfer/{id}/confirm、/revoke |
| 离职归还管理页（表格） | 归还单列表/详情（明细项） | GET /account/return/list、GET /account/return/{id} |
| 离职归还操作 | 手动补建归还单（ConfirmDialog） | POST /account/return/generate |
| 归还单详情抽屉-明细项操作 | 逐项处理（归还/转交/争议） | PUT /account/return/item/{itemId} |
| 归还单详情抽屉-闭环按钮 | 归还闭环（校验不通过红字提示） | PUT /account/return/{id}/close |
| 冲话费管理页（QueryBar+表格） | 充值记录列表 | GET /account/recharge/list |
| 冲话费登记抽屉（FileUpload 凭证） | 登记充值（>5000 元凭证必填前端校验） | POST /account/recharge |
| 冲话费操作 | 编辑记录/触发月度核对/成本汇总 | PUT /account/recharge/{id}、POST /account/recharge/verify、GET /account/recharge/summary |
| 账号详情页-时间线 Tab（Timeline 组件） | 时间线浏览/类型筛选/跳转原单据 | GET /account/timeline/{accountId} |
| 账号详情页-时间线导出 | 导出交接凭证 PDF | GET /account/timeline/{accountId}/export |
| 事件明细独立检索页 | 跨账号事件分页筛选 | GET /account/timeline/events |

（全文完）
