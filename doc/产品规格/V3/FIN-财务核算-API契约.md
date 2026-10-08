# FIN - 财务核算 API 契约

> **模块范围**：11 财务核算（V3，第 28~33 周先行批次，由 V2 移入）——FIN-001 单场成本录入、FIN-002 利润自动计算、FIN-003 分成规则引擎、FIN-004 利润看板。消费 V1 直播台账（`ims_live_session`/下播数据/投放汇总），不新建直播上游台账。
> **权威依据**：《IMS第二期PRD-V2.md》5.16~5.19；BR-107~BR-109；V2-E1~E4 财务精度约束。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`session_code → sessionCode`、`share_daren → shareDaren`）。**财务口径强制**：金额 DECIMAL(12,2)（单位元、两位小数）；比例 DECIMAL(5,4)；BigDecimal 全链路（V2-E1）；`sessionCode` 引用 V1 19 位 IMS 编码（`IMS+yyyyMMdd+3 位平台码+4 位序列`，BR-011 修正口径）；多对象分成比例求和校验 = 1.0000（V2-E2）；红冲+蓝补更正模式（V2-E3）；金额变更幂等（clientToken 请求头）。周次波浪号格式。

---

## 1. API 总览表（共 26 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/fin/cost/pending-sessions` | 待录入场次清单（V1 台账已核准场次） | R3（主责）/R4/R1 |
| 2 | POST | `/admin-api/ims/fin/cost/{sessionCode}` | 提交成本录入（clientToken 幂等） | R3（主责）/R5（协录本团队） |
| 3 | GET | `/admin-api/ims/fin/cost/{sessionCode}` | 成本详情 | R1/R3/R4/R9（全量）/R5（本团队场次） |
| 4 | PUT | `/admin-api/ims/fin/cost/{sessionCode}` | 编辑成本（核准前） | R3/R5 |
| 5 | PUT | `/admin-api/ims/fin/cost/{sessionCode}/confirm` | 财务核准（触发利润计算） | R3 |
| 6 | POST | `/admin-api/ims/fin/cost/{sessionCode}/correction` | 成本更正单（红冲+蓝补） | R3 |
| 7 | GET | `/admin-api/ims/fin/cost/complete-rate` | 成本录入完整率（BR-107） | R1/R3/R4/R9 |
| 8 | GET | `/admin-api/ims/fin/profit/{sessionCode}` | 单场利润详情（三级口径） | R1/R3/R4/R9/R5（本团队）/R7（本人场次） |
| 9 | GET | `/admin-api/ims/fin/profit/list` | 利润列表（多维筛选，分页） | 同上 |
| 10 | POST | `/admin-api/ims/fin/profit/recalc/{sessionCode}` | 手动触发重算（新版本） | R3/R1 |
| 11 | GET | `/admin-api/ims/fin/profit/abnormal` | 异常净利率清单（2σ 偏离） | R1/R3/R4/R9 |
| 12 | GET | `/admin-api/ims/fin/profit/history/{sessionCode}` | 重算版本历史 | R1/R3/R4 |
| 13 | GET | `/admin-api/ims/fin/share/rules` | 分成规则列表（分页） | R1/R3/R4 |
| 14 | POST | `/admin-api/ims/fin/share/rule` | 创建分成规则 | R3（主责） |
| 15 | PUT | `/admin-api/ims/fin/share/rule/{id}` | 编辑规则（生成新版本） | R3 |
| 16 | DELETE | `/admin-api/ims/fin/share/rule/{id}` | 停用规则 | R3/R1 |
| 17 | POST | `/admin-api/ims/fin/share/simulate` | 规则试算（给定基数预估） | R3/R4 |
| 18 | GET | `/admin-api/ims/fin/share/results` | 分成单列表（分页） | R1/R3/R4/R7（本人分成单）/R9（脱敏） |
| 19 | PUT | `/admin-api/ims/fin/share/result/{id}/audit` | 分成单审批（双审之一） | R3（财务审）+ R4（业务审） |
| 20 | PUT | `/admin-api/ims/fin/share/result/{id}/payoff` | 发放登记 | R3 |
| 21 | GET | `/admin-api/ims/fin/dashboard/overview` | 总览指标（周期净利/净利率/GMV） | R1/R3/R4/R9（全量）/R5（本团队）/R7（本人场次） |
| 22 | GET | `/admin-api/ims/fin/dashboard/trend` | 趋势分析（环比/同比） | 同上 |
| 23 | GET | `/admin-api/ims/fin/dashboard/drilldown` | 多维下钻（平台/账号/IP 组/达人/责任人） | 同上 |
| 24 | GET | `/admin-api/ims/fin/dashboard/cost-structure` | 成本结构占比 | 同上 |
| 25 | GET | `/admin-api/ims/fin/dashboard/share-summary` | 分成汇总（各分成对象周期总额） | 同上 |
| 26 | GET | `/admin-api/ims/fin/dashboard/export` | 报表导出（Excel/PDF） | R1/R3/R4/R9 |

---

## 2. 接口明细

### 2.1 单场成本录入（FIN-001）

#### 2.1.1 GET /admin-api/ims/fin/cost/pending-sessions — 待录入场次清单（分页）

**请求**（Query）：`PageParam` + `{ platform?: PlatformType; sessionCode?: string; approvedDateRange?: [string, string] }`

**响应** `data`：`PageResult<{ sessionCode: string; platform: PlatformType; sessionTitle: string; gmv: number; refund: number; adCost: number; approvedAt: string; hoursSinceApprove: number; isOver48h: boolean }>`（仅 V1 下播数据"已核准"场次，FIN-C-R1；核准后 48 小时未录入触发 BR-118 预警）。

#### 2.1.2 POST /admin-api/ims/fin/cost/{sessionCode} — 提交成本录入

**请求头**：`clientToken: string`（幂等强制，V2-E4，重试防重复录入）。

**请求**：

```typescript
interface FinCostEntryReq {
  sessionCode: string;           // V1 19 位 IMS 编码（如 IMS20250610DYS0001）
  /** 平台佣金率（DECIMAL(5,4)，如 0.0500 = 5%） */
  commissionRate: number;
  /** 投放成本（可从 V1 ims_live_cost 汇总带入，可覆盖） */
  adCost: number;
  /** 冲话费摊销（联动 V1 账号冲话费记录按场次分摊） */
  rechargeCost: number;
  /** 场次固定成本（场地/设备折旧/人力） */
  fixedCost: number;
  /** 样品成本 */
  sampleCost: number;
  /** 达人/实名人分成：手工录入或引擎计算 */
  shareCostType: 'MANUAL' | 'ENGINE';               // 1 手工 / 2 引擎
  shareDaren?: number;           // MANUAL 时必填
  shareRealname?: number;        // MANUAL 时必填
  remark?: string;
}
```

**响应** `data`：

```typescript
interface FinCostVO {
  id: number;
  sessionCode: string;
  platform: PlatformType;        // V1 场次带出，只读
  /** GMV/退款：V1 下播数据只读带出，不可在财务侧修改（FIN-C-R2 数据同源） */
  costGmv: number;
  costRefund: number;
  commissionRate: number;
  commissionAmount: number;      // = GMV × 佣金率（BigDecimal 计算）
  adCost: number;
  rechargeCost: number;
  fixedCost: number;
  sampleCost: number;
  shareDaren: number;
  shareRealname: number;
  shareCostType: 'MANUAL' | 'ENGINE';
  /** 成本合计 = commission + ad + recharge + fixed + sample + shares */
  totalCost: number;
  entryStatus: 'DRAFT' | 'SUBMITTED' | 'CONFIRMED';   // 0 草稿 / 1 已提交 / 2 已核准
  entryUserId: number;
  entryUserName: string;
  entryAt: string;
  /** 客户端幂等令牌（与请求头一致，重试返回已有单据） */
  clientToken: string;
}
```

**错误码**：1141（场次不存在或非已核准状态，FIN-C-R1）、1142（期间已结账不可录入，FinanceStatus.LOCKED，归并原 1010 语义）、1143（分成金额与利润合计勾稽不平）、1001（金额格式/负数校验）。

#### 2.1.3 GET /admin-api/ims/fin/cost/{sessionCode} — 成本详情

**响应** `data`：`FinCostVO`。

#### 2.1.4 PUT /admin-api/ims/fin/cost/{sessionCode} — 编辑成本（核准前）

**请求**：`FinCostEntryReq` → **响应** `data`：`FinCostVO`。仅 `DRAFT`/`SUBMITTED` 状态可编辑；核准后修改走更正单（2.1.6）。

#### 2.1.5 PUT /admin-api/ims/fin/cost/{sessionCode}/confirm — 财务核准

**响应** `data`：`{ entryStatus: 'CONFIRMED'; profitTaskId: string; message: string }`（核准后 5 分钟内自动完成利润计算，FIN-P-R1；触发条件事件由 MQ 投递计算引擎）。

#### 2.1.6 POST /admin-api/ims/fin/cost/{sessionCode}/correction — 成本更正单

**请求头**：`clientToken`（幂等）。

**请求**：

```typescript
interface FinCostCorrectionReq {
  /** 更正后成本项（全量提交，与原单 Diff 生成红冲+蓝补分录，V2-E3） */
  corrected: FinCostEntryReq;
  correctionReason: string;
}
```

**响应** `data`：`{ correctionNo: string; redEntries: Array<{ item: string; amount: number }>; blueEntries: Array<{ item: string; amount: number }>; recalcTriggered: boolean }`（更正自动触发利润重算并标记重算版本，FIN-P-R3）。

**错误码**：1144（更正原因必填）、1142（期间已结账）。

#### 2.1.7 GET /admin-api/ims/fin/cost/complete-rate — 完整率（BR-107）

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ approvedSessionCount: number; costEnteredCount: number; completeRate: number; unenteredOver48h: Array<{ sessionCode: string; platform: string; approvedAt: string; hoursSinceApprove: number }> }`（BR-107 目标 > 95%；未录入预警联动 ALERT BR-118）。

### 2.2 利润自动计算（FIN-002）

#### 2.2.1 GET /admin-api/ims/fin/profit/{sessionCode} — 单场利润详情

**响应** `data`：

```typescript
interface FinProfitVO {
  id: number;
  sessionCode: string;
  /** 三级利润口径同时落库（FIN-P-R2，看板切换用） */
  grossProfit: number;           // 毛利 = GMV − 退款 − 平台佣金
  operatingProfit: number;       // 经营利润 = 毛利 − 投放 − 冲话费
  netProfit: number;             // 净利润（BR-108 全扣公式）
  netProfitRate: number;         // DECIMAL(5,2)
  /** 计算时公式与参数快照（BigDecimal 全链路，V2-E1） */
  calcRuleSnapshot: {
    formula: string;             // BR-108 表达式
    params: Record<string, number>;
  };
  calcVersion: number;           // 重算递增
  calcStatus: 'PENDING' | 'CALCULATED' | 'RECALCULATED' | 'ABNORMAL';   // 0 待计算/1 已计算/2 已重算/3 异常待核
  calculatedAt: string;
}
```

**错误码**：1145（该场次成本未核准，利润未计算）。

#### 2.2.2 GET /admin-api/ims/fin/profit/list — 利润列表（分页）

**请求**（Query）：`PageParam` + `{ sessionCode?: string; platform?: PlatformType; dateRange?: [string, string]; calcStatus?: string; dimensionType?: 'ACCOUNT' | 'IP_GROUP' | 'DAREN' | 'OWNER' }`

**响应** `data`：`PageResult<FinProfitVO & { platform: string; sessionTitle: string; gmv: number }> `。R5 限本团队场次、R7 限本人场次（服务端过滤）。

#### 2.2.3 POST /admin-api/ims/fin/profit/recalc/{sessionCode} — 手动触发重算

**响应** `data`：`{ calcVersion: number; calcStatus: 'RECALCULATED'; message: string }`。重算生成新版本，旧结果版本留痕（FIN-P-R3；快照不可变）。

**错误码**：1145（成本未核准）、1142（期间已结账，重算冻结）。

#### 2.2.4 GET /admin-api/ims/fin/profit/abnormal — 异常净利率清单

**请求**（Query）：`PageParam` + `{ platform?: string }` → **响应** `data`：`PageResult<FinProfitVO & { peerAvgRate: number; sigma: number; deviationSigma: number }>`（净利率偏离同类均值 2 倍标准差标记待核并预警，FIN-P-R4；联动 ALERT 推送财务）。

#### 2.2.5 GET /admin-api/ims/fin/profit/history/{sessionCode} — 重算版本历史

**响应** `data`：`Array<{ calcVersion: number; netProfit: number; grossProfit: number; operatingProfit: number; calcStatus: string; triggerType: 'AUTO_CORRECTION' | 'MANUAL'; triggerReason: string; calculatedAt: string }>`。

### 2.3 分成规则引擎（FIN-003）

#### 2.3.1 GET /admin-api/ims/fin/share/rules — 规则列表（分页）

**请求**（Query）：`PageParam` + `{ shareTarget?: 'DAREN' | 'REALNAME' | 'TEAM'; status?: 'ENABLED' | 'DISABLED' }`

**响应** `data`：`PageResult<FinShareRuleVO>`

```typescript
interface FinShareRuleVO {
  id: number;
  ruleName: string;
  shareTarget: 'DAREN' | 'REALNAME' | 'TEAM';       // 1 达人 / 2 实名人 / 3 团队
  /** 分成基数 */
  baseType: 'GMV' | 'GROSS_PROFIT' | 'NET_PROFIT';  // 1 GMV / 2 毛利 / 3 净利润
  rateType: 'FIXED' | 'LADDER';                     // 1 固定比例 / 2 阶梯
  /** 固定比例（DECIMAL(5,4)，如 0.2000） */
  fixedRate?: number;
  /** 阶梯配置：基数分档 × 对应比例，逐档计算求和（BR-109） */
  ladderConfig?: Array<{ min: number; max: number | null; rate: number }>;
  /** 适用范围（按平台/账号/IP 组限定，多条件 AND） */
  scope: {
    platforms?: PlatformType[];
    accountIds?: number[];
    ipGroupIds?: number[];
  };
  priority: number;              // 冲突时高优先（FIN-S-R4）
  version: number;
  status: 'ENABLED' | 'DISABLED';
  effectiveRange: { from: string; to?: string };
}
```

#### 2.3.2 POST /admin-api/ims/fin/share/rule — 创建规则

**请求**：`Omit<FinShareRuleVO, 'id' | 'version' | 'status'>` → **响应** `data`：`FinShareRuleVO`。

**错误码**：1146（规则参数非法：fixedRate 超出 (0,1] 或阶梯区间重叠/比例非法）、1147（同范围同对象优先级冲突须显式确认）。**校验**：同一场次多分成对象比例求和 ≤ 1.0000，多对象集合求和必须 = 1.0000（V2-E2）。

#### 2.3.3 PUT /admin-api/ims/fin/share/rule/{id} — 编辑规则（新版本）

**请求**：同创建 → **响应** `data`：`FinShareRuleVO`（`version` 自增）。规则变更不影响已生成分成单（FIN-S-R5，重算需人工触发并留痕）。

#### 2.3.4 DELETE /admin-api/ims/fin/share/rule/{id} — 停用规则

**响应**：`data: null`（状态 → `DISABLED`，历史分成单引用不受影响）。

#### 2.3.5 POST /admin-api/ims/fin/share/simulate — 规则试算

**请求**：`{ ruleId?: number; draftRule?: Omit<FinShareRuleVO, 'id' | 'version' | 'status'>; simulateBase: number }` → **响应** `data`：`{ simulateBase: number; shareAmount: number; calcDetail: Array<{ range: string; rateApplied: number; amount: number }> }`（阶梯逐档求和明细，BigDecimal 计算）。

#### 2.3.6 GET /admin-api/ims/fin/share/results — 分成单列表（分页）

**请求**（Query）：`PageParam` + `{ sessionCode?: string; shareTarget?: string; status?: 'PENDING_AUDIT' | 'AUDITED' | 'PAID_OFF' | 'REVERSED' }`

**响应** `data`：`PageResult<FinShareResultVO>`

```typescript
interface FinShareResultVO {
  id: number;
  sessionCode: string;           // 引用 V1 19 位 IMS 编码
  ruleId: number;
  ruleName: string;
  shareTarget: 'DAREN' | 'REALNAME' | 'TEAM';
  targetRefId: number;           // 达人/实名人/团队 ID
  targetRefName: string;
  shareBase: number;             // 分成基数（按 baseType 取三级利润之一）
  shareAmount: number;           // 分成金额（BigDecimal 计算）
  calcDetail: Record<string, unknown>;   // 计算过程 JSON
  status: 'PENDING_AUDIT' | 'AUDITED' | 'PAID_OFF' | 'REVERSED';   // 0 待审/1 已审/2 已发放/3 已冲销
  auditedBy?: number;
  auditedAt?: string;
  paidOffAt?: string;
}
```

**说明**：R7 仅可见本人（targetRefId = 本人）分成单；R9 金额脱敏返回 `"***"`。

#### 2.3.7 PUT /admin-api/ims/fin/share/result/{id}/audit — 分成单审批

**请求**：`{ conclusion: 'APPROVE' | 'REJECT'; remark?: string; auditRole: 'FINANCE' | 'BUSINESS' }` → **响应** `data`：`{ status: 'PENDING_AUDIT' | 'AUDITED'; finAuditPassed: boolean; bizAuditPassed: boolean; bothPassed: boolean }`。

**错误码**：1148（双审未齐：须财务（R3）+ 运营总监（R4）双审后生效，FIN-S-R3）、1149（无该审批角色权限）。

#### 2.3.8 PUT /admin-api/ims/fin/share/result/{id}/payoff — 发放登记

**请求**：`{ payoffVoucher?: { fileName: string; fileKey: string }; payoffNote?: string }` → **响应**：`data: null`（状态 → `PAID_OFF`）。负向调整走冲销（`REVERSED`，红冲分录，V2-E3）。

### 2.4 利润看板（FIN-004）

#### 2.4.1 GET /admin-api/ims/fin/dashboard/overview — 总览指标

**请求**（Query）：`{ statPeriod: string; profitType?: 'GROSS' | 'OPERATING' | 'NET' }` → **响应** `data`：`{ totalGmv: number; totalCost: number; netProfit: number; netProfitRate: number; sessionCount: number; costStructureRatio: Record<string, number>; refreshedAt: string }`（缓存表小时级刷新，FIN-B-R1）。

#### 2.4.2 GET /admin-api/ims/fin/dashboard/trend — 趋势分析

**请求**（Query）：`{ dateRange: [string, string]; granularity: 'DAY' | 'WEEK' | 'MONTH'; profitType?: string }` → **响应** `data`：`Array<{ statPeriod: string; gmv: number; cost: number; netProfit: number; netProfitRate: number; momRate?: number; yoyRate?: number }>`。

#### 2.4.3 GET /admin-api/ims/fin/dashboard/drilldown — 多维下钻

**请求**（Query）：`{ statPeriod: string; dimensionType: 'PLATFORM' | 'ACCOUNT' | 'IP_GROUP' | 'DAREN' | 'OWNER'; dimensionValue?: string; drillToSession?: boolean }` → **响应** `data`：`Array<{ dimensionValue: string; dimensionLabel: string; totalGmv: number; totalCost: number; netProfit: number; sessionCount: number; children?: Array<FinProfitVO> }>`（下钻最深到场次明细，联动 V1 台账详情，FIN-B-R2）。

#### 2.4.4 GET /admin-api/ims/fin/dashboard/cost-structure — 成本结构

**请求**（Query）：`{ statPeriod: string; dimensionType?: string }` → **响应** `data`：`Array<{ costItem: 'COMMISSION' | 'AD' | 'RECHARGE' | 'FIXED' | 'SAMPLE' | 'SHARE_DAREN' | 'SHARE_REALNAME'; amount: number; ratio: number }>`。

#### 2.4.5 GET /admin-api/ims/fin/dashboard/share-summary — 分成汇总

**请求**（Query）：`{ statPeriod: string }` → **响应** `data`：`Array<{ shareTarget: string; targetRefId: number; targetRefName: string; totalAmount: number; sessionCount: number; paidOffAmount: number; pendingAmount: number }>`。

#### 2.4.6 GET /admin-api/ims/fin/dashboard/export — 报表导出

**请求**（Query）：`{ statPeriod: string; dimensionType?: string; format: 'XLSX' | 'PDF' }` → **响应** `data`：`{ downloadUrl: string; expiresIn: number }`（服务端鉴权下载链接）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**成本单（FinCostVO.entryStatus，映射 FinanceStatus 扩展）**：

```
DRAFT ──提交──▶ SUBMITTED ──财务核准──▶ CONFIRMED ──成本更正（红冲+蓝补）──▶ 触发重算
                    │                                        │
                    └──核准前编辑────────────────────────────┘（期间 LOCKED 时全部拦截，错误码 1142）
```

**利润（FinProfitVO.calcStatus）**：

```
PENDING（成本核准后 5 分钟内）──自动计算──▶ CALCULATED ──成本更正/手动重算──▶ RECALCULATED（版本+1）
                                              │
                                              └──净利率 2σ 偏离──▶ ABNORMAL（待核+预警）
```

**分成单（FinShareResultVO.status）**：

```
PENDING_AUDIT ──财务审（R3）+业务审（R4）双审通过──▶ AUDITED ──发放登记──▶ PAID_OFF
      │                                              │
      └──任一环节驳回──────────────────────────────────┴──冲销──▶ REVERSED（红冲分录）
```

**分成规则（FinShareRuleVO.status）**：`ENABLED ↔ DISABLED`（变更生成新版本，历史分成单不受影响）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-107 | 成本录入完整率 > 95%（联动 V1 BR-006/007） | 2.1.7 |
| BR-108 | 净利润 = GMV−退款−佣金−投放−冲话费−固定−样品−达人分成−实名人分成 | 2.2.1 calcRuleSnapshot |
| BR-109 | 分成 = 基数×比例（阶梯逐档求和） | 2.3.5 simulate |
| BR-118 | 核准后 48h 未录成本触发预警 | 2.1.1 isOver48h（联动 ALERT） |
| FIN-C-R1 | 仅已核准场次可录成本 | 2.1.2 错误码 1141 |
| FIN-C-R2 | GMV/退款 V1 只读带出（数据同源） | 2.1.2 FinCostVO 只读字段 |
| FIN-C-R3 | 48h 未录入预警 | 同 BR-118 |
| FIN-C-R4 | 成本提交后修改走更正单留痕 | 2.1.6 |
| FIN-P-R1 | 核准后 5 分钟内自动计算 | 2.1.5（MQ 事件触发） |
| FIN-P-R2 | 三级利润口径同时落库 | 2.2.1 |
| FIN-P-R3 | 重算版本化，旧结果留痕 | 2.2.3 / 2.2.5 |
| FIN-P-R4 | 净利率 2σ 偏离标记待核 | 2.2.4 |
| FIN-S-R1 | 分成金额 = 基数 × 比例（BigDecimal） | 2.3.x |
| FIN-S-R2 | 利润计算完成自动生成分成单 | 2.3.6（引擎联动） |
| FIN-S-R3 | 分成单双审（财务+运营总监） | 2.3.7 错误码 1148 |
| FIN-S-R4 | 规则冲突取优先级最高 | 2.1 规则引擎（priority） |
| FIN-S-R5 | 规则变更不影响已生成分成单 | 2.3.3 |
| FIN-B-R1 | 看板小时级刷新缓存 | 2.4.1 refreshedAt |
| FIN-B-R2 | 下钻最深到场次明细 | 2.4.3 drillToSession |
| FIN-B-R3 | 看板数据权限同角色矩阵 | 2.4.x 服务端过滤 |
| V2-E1 | 金额 DECIMAL(12,2)、BigDecimal 全链路（禁 float/double） | 全模块 |
| V2-E2 | 分成比例 DECIMAL(5,4)，多对象求和 = 1.0000 | 2.3.2 校验 |
| V2-E3 | 更正红冲+蓝补（不做物理修改） | 2.1.6 / 2.3.8 |
| V2-E4 | 金额写接口 clientToken 幂等 | 2.1.2 / 2.1.6 请求头 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 待录入成本页（QueryBar + 表格，48h 超时高亮） | 待录入场次清单查询 | GET /fin/cost/pending-sessions |
| 成本录入抽屉（DetailDrawer，GMV/退款只读展示） | 录入各成本项（clientToken 幂等） | POST /fin/cost/{sessionCode} |
| 成本详情抽屉 | 成本详情查看 / 核准前编辑 | GET /fin/cost/{sessionCode}、PUT /fin/cost/{sessionCode} |
| 成本详情-核准按钮 | 财务核准（触发利润计算提示） | PUT /fin/cost/{sessionCode}/confirm |
| 成本更正抽屉 | 提交更正单（红冲蓝补明细展示） | POST /fin/cost/{sessionCode}/correction |
| 完整率指标卡 | 录入完整率看板（BR-107 未录清单督办） | GET /fin/cost/complete-rate |
| 利润列表页（多维筛选 + 口径切换 Tab） | 利润列表查询 | GET /fin/profit/list |
| 利润详情抽屉 | 单场三级利润 + 计算快照 | GET /fin/profit/{sessionCode} |
| 利润详情-重算按钮 | 手动触发重算（ConfirmDialog） | POST /fin/profit/recalc/{sessionCode} |
| 利润详情-版本历史 | 重算版本历史时间轴 | GET /fin/profit/history/{sessionCode} |
| 异常净利率页 | 异常清单（2σ 偏离标记） | GET /fin/profit/abnormal |
| 分成规则管理页 | 规则列表 / 创建 / 编辑（阶梯配置器） | GET /fin/share/rules、POST /fin/share/rule、PUT /fin/share/rule/{id} |
| 规则试算抽屉 | 给定基数试算（阶梯逐档明细） | POST /fin/share/simulate |
| 分成单管理页（双审状态列） | 分成单列表查询 | GET /fin/share/results |
| 分成单审批抽屉 | 财务审 / 业务审（双审进度展示） | PUT /fin/share/result/{id}/audit |
| 分成单发放登记 | 发放登记（凭证上传） | PUT /fin/share/result/{id}/payoff |
| 利润看板-总览区 | 周期指标卡 + 成本结构饼图 | GET /fin/dashboard/overview、/cost-structure |
| 利润看板-趋势区 | 环比/同比趋势图 | GET /fin/dashboard/trend |
| 利润看板-下钻区 | 维度下钻（至场次明细） | GET /fin/dashboard/drilldown |
| 利润看板-分成汇总 | 各对象周期分成总额 | GET /fin/dashboard/share-summary |
| 看板导出 | 报表导出（Excel/PDF） | GET /fin/dashboard/export |

（全文完）
