# FIN - 财务核算 页面规格

> 依据：《IMS第二期PRD-V2.md》5.16~5.19（FIN-001~004）、《共享技术规范-分期技术约束.md》V2-E1~E4（财务精度）、《FIN-财务核算-API契约.md》、《全局开发规范.md》第 4 章（权威枚举）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus + ECharts；API 前缀 `/admin-api/ims/fin`。
> 归属期次：V3 先行批次（第 28~33 周，由 V2 移入；先于 12 数据中心/19 人效交付）。
> **财务口径强制（全局 UI 约定）**：金额一律 DECIMAL(12,2) 两位小数 + **¥ 前缀 + 千分位**（`¥12,345.67`）；比例 DECIMAL(5,4) 展示为百分比（如 0.2000 → 20.00%）；`sessionCode` 引用 V1 19 位 IMS 编码（`IMS+yyyyMMdd+3 位平台码+4 位序列`）；金额写接口携带 `clientToken` 幂等（V2-E4）；R9 视角金额字段服务端脱敏 `"***"`；手机号前 3 后 4 脱敏（本模块联系人场景）。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 成本录入管理 | `/ims/fin/cost` | 一级菜单页（待录入清单 + 录入抽屉 + 完整率卡） | FIN-001 |
| P2 利润核算 | `/ims/fin/profit` | 一级菜单页（列表 + 详情抽屉 + 异常清单 Tab） | FIN-002 |
| P3 分成规则引擎 | `/ims/fin/share/rule` | 一级菜单页（规则列表 + 规则设计抽屉 + 试算） | FIN-003 |
| P4 分成单管理 | `/ims/fin/share/result` | 一级菜单页（双审列 + 审批抽屉 + 发放登记） | FIN-003 |
| P5 利润看板 | `/ims/fin/dashboard` | 一级菜单页（大屏聚合看板） | FIN-004 |
| P6 利润反查 | `/ims/fin/profit-trace` | L3 · **场次财务** 子菜单（DC-002 页面壳） | DC-002 |

**P6 说明（2026-10-01）**：交互与字段 **SSOT** = 《DC-数据中心-页面规格》**P2**；本模块仅声明 **菜单归属**（财务 R3 主入口）与权限 **`ims:fin:profit-trace:query`**；API 仍为 **`/admin-api/ims/dc/profit-trace/*`**。

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；交互操作优先内联抽屉（Drawer），不跳转新页面（P5 看板为独立大屏页）；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红 / 中性灰）；
- 金额列右对齐、¥ 前缀、千分位、两位小数；负数红色括号格式（红冲分录）；
- 周次/月份展示用波浪号格式；枚举一律引用《全局开发规范.md》第 4 章：`FinanceStatus`、`EntryCostStatus`、`ProfitCalcStatus`、`ShareResultStatus`、`EnableStatus`、`PlatformType`。

---

## P1. 成本录入管理（FIN-001）

### 1. 页面概述
- 路由路径：`/ims/fin/cost`
- 页面级别：一级菜单页，双 Tab：待录入清单 / 已录入管理 + 顶部完整率指标卡
- 依赖模块：V1 直播台账（已核准场次、GMV/退款只读带出，FIN-C-R2）、V1 冲话费记录（rechargeCost 联动）、ALERT（BR-118 48h 未录预警）
- 权限矩阵引用（PRD 4.2 FIN-001）：R1 R（全量）、R3 R/W/D（全量主责）、R4 R/W（全量）、R5 W（协录本团队场次）、R9 R（全量）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 指标卡: 已核准场次 N | 已录入 N | 完整率 xx% (BR-107 目标>95%)     |
|   | [超48h未录清单(红)]                                            |
+------------------------------------------------------------------+
| Tab: [待录入清单] [已录入管理]                                     |
+------------------------------------------------------------------+
| 待录入查询行: 平台 | 场次号 | 核准日期范围 | [查询][重置]            |
+------------------------------------------------------------------+
| 待录入表格: 场次号|场次标题|平台|GMV|退款|投放|核准时间|超48h|操作    |
| 已录入表格: 场次号|平台|成本合计|分成方式|录入状态|录入人|操作        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
成本录入抽屉(720px):
  只读带出区: 场次号 | 平台 | GMV* | 退款* (V1 数据同源,FIN-C-R2)
  录入区: 佣金率*(%) | 投放成本*(¥可带入V1汇总) | 冲话费摊销(¥) |
    固定成本(¥) | 样品成本(¥) |
    分成方式*(手工/引擎): 手工时 达人分成¥ + 实名人分成¥ 必填 |
  底部: 成本合计实时预览 ¥xx | [保存草稿][提交] [财务核准]
成本详情抽屉(70%): 成本明细 + 核准状态 + [更正单] [财务核准]
更正抽屉(720px): 预填原成本 → 修改项 Diff 预览(红冲/蓝补) + 原因*
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface PendingSessionReq {
  pageNo: number; pageSize: number;
  platform?: PlatformType;
  sessionCode?: string;
  approvedDateRange?: [string, string];
}
interface FinCostEntryReq {
  sessionCode: string;              // V1 19 位 IMS 编码
  commissionRate: number;           // DECIMAL(5,4)，如 0.0500（前端百分比输入换算）
  adCost: number;                   // ¥ 两位小数
  rechargeCost: number;
  fixedCost: number;
  sampleCost: number;
  shareCostType: ShareCostType;     // MANUAL / ENGINE
  shareDaren?: number;              // MANUAL 必填
  shareRealname?: number;           // MANUAL 必填
  remark?: string;
  asDraft?: boolean;                // true 存草稿
}
interface FinCostCorrectionReq {
  corrected: FinCostEntryReq;       // 全量提交，与原单 Diff 生成红冲+蓝补（V2-E3）
  correctionReason: string;         // 必填 ≤512 字
}

// 响应类型
interface PendingSessionItem {
  sessionCode: string;
  platform: PlatformType;
  sessionTitle: string;
  gmv: number;                      // ¥
  refund: number;
  adCost: number;                   // V1 投放汇总（可带入可覆盖）
  approvedAt: string;
  hoursSinceApprove: number;
  isOver48h: boolean;               // BR-118 预警标记
}
interface FinCostVO {
  id: number;
  sessionCode: string;
  platform: PlatformType;           // V1 带出只读
  costGmv: number;                  // ¥ 只读（FIN-C-R2）
  costRefund: number;               // ¥ 只读
  commissionRate: number;
  commissionAmount: number;         // = GMV × 佣金率
  adCost: number; rechargeCost: number;
  fixedCost: number; sampleCost: number;
  shareDaren: number; shareRealname: number;
  shareCostType: ShareCostType;
  totalCost: number;                // 合计
  entryStatus: EntryCostStatus;     // DRAFT / SUBMITTED / CONFIRMED
  entryUserId: number; entryUserName: string;
  entryAt: string;
  clientToken: string;
}
interface FinCostConfirmResp {
  entryStatus: 'CONFIRMED';
  profitTaskId: string;
  message: string;                  // "5 分钟内自动完成利润计算"（FIN-P-R1）
}
interface FinCostCorrectionResp {
  correctionNo: string;
  redEntries: Array<{ item: string; amount: number }>;    // 红冲（负数）
  blueEntries: Array<{ item: string; amount: number }>;   // 蓝补
  recalcTriggered: boolean;         // 更正自动触发重算（FIN-P-R3）
}
interface CompleteRateResp {
  approvedSessionCount: number;
  costEnteredCount: number;
  completeRate: number;             // BR-107 目标 >95%
  unenteredOver48h: Array<{
    sessionCode: string; platform: string;
    approvedAt: string; hoursSinceApprove: number;
  }>;
}

// 枚举类型
type ShareCostType = 'MANUAL' | 'ENGINE';   // 手工/引擎
// EntryCostStatus = 'DRAFT' | 'SUBMITTED' | 'CONFIRMED' —— 全局权威枚举
// PlatformType —— 全局权威枚举
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /fin/cost/pending-sessions` + `GET /fin/cost/complete-rate`（指标卡）；已录入 Tab 懒加载成本列表。失败分区重试。

#### 4.2 核心操作流程
**A. 成本录入（R3 主责 / R5 协录本团队）**
1. 待录入行 [录入成本] → 录入抽屉：只读带出区（场次号/平台/GMV/退款，灰底 + "V1 数据同源"水印提示，FIN-C-R2）；投放成本自动带入 V1 汇总值（可覆盖）；
2. 录入区：佣金率百分比输入（0 < rate ≤ 1 换算 DECIMAL(5,4)）；金额字段 InputNumber 两位小数非负；分成方式切换：手工（达人/实名人分成必填）/ 引擎（留空由 FIN-003 计算）；
3. 底部成本合计实时预览（¥ 前缀千分位）；
4. [保存草稿] 或 [提交]（clientToken 幂等，V2-E4）→ `POST /fin/cost/{sessionCode}`；
5. 勾稽提示（1143）：分成金额与利润合计勾稽不平 → 错误明细行内定位。

**B. 财务核准（R3）**
1. SUBMITTED 状态行 [财务核准] → ConfirmDialog（汇总：场次/成本合计/提示"核准后 5 分钟内自动计算利润（FIN-P-R1）"）→ `PUT /fin/cost/{sessionCode}/confirm` → entryStatus=CONFIRMED → MQ 触发利润计算引擎；
2. 期间已结账（1142，FinanceStatus.LOCKED）：提示"财务期间已结账，录入/核准/更正均冻结"。

**C. 成本更正（FIN-C-R4，红冲+蓝补，V2-E3）**
1. CONFIRMED 行 [更正单] → 更正抽屉：预填原成本 → 修改字段 → Diff 预览区实时展示红冲（负数红括号）/蓝补分录；
2. 更正原因必填 → `POST /fin/cost/{sessionCode}/correction`（clientToken）→ 返回 correctionNo + 红冲蓝补明细 + recalcTriggered=true → 自动触发利润重算（版本+1，FIN-P-R3）。

**D. 超时预警督办（BR-118）**
1. 待录入清单 isOver48h 行红标 + 超时小时数；指标卡 [超 48h 未录清单] 抽屉督办（预警推送由 ALERT 引擎执行，页面显示"已预警"标记）。

### 5. 查询条件表

**待录入清单 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| platform | Select | 否 | 空 | PlatformType 六平台 |
| sessionCode | Input | 否 | 空 | 19 位 IMS 编码精确匹配 |
| approvedDateRange | DateRangePicker | 否 | 近 7 天 | V1 核准时间 |

**已录入管理 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 场次号 |
| platform | Select | 否 | 空 | 平台 |
| entryStatus | Select | 否 | 空 | 草稿/已提交/已核准 |

### 6. 表格列定义

**待录入清单**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次号 | 190 | — | 等宽字体（19 位 IMS 编码） |
| sessionTitle | 场次标题 | 自适应 | — | — |
| platform | 平台 | 90 | — | PlatformType tag |
| gmv | GMV | 130 | ✓ | ¥ 千分位两位（R9 视角 `***`） |
| refund | 退款 | 120 | — | ¥ 千分位 |
| adCost | 投放(带入) | 120 | — | ¥ 千分位 |
| approvedAt | 核准时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| isOver48h | 超 48h | 100 | — | tag：是(红)/否(灰)；悬浮"已过 N 小时" |
| actions | 操作 | 110 | — | [录入成本] |

**已录入管理**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次号 | 190 | — | 等宽字体 |
| platform | 平台 | 90 | — | tag |
| totalCost | 成本合计 | 140 | ✓ 降序 | ¥ 千分位 |
| shareCostType | 分成方式 | 100 | — | 手工(灰)/引擎(青) |
| entryStatus | 录入状态 | 110 | — | tag：草稿(灰)/已提交(蓝)/已核准(绿) |
| entryUserName | 录入人 | 100 | — | — |
| entryAt | 录入时间 | 150 | — | yyyy-MM-dd HH:mm |
| actions | 操作 | 150 | — | [详情][编辑(核准前)][更正单(已核准)][财务核准(已提交)] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 成本录入抽屉 | Drawer 720px | GMV/退款只读；commissionRate 必填 (0,1]；金额字段必填非负两位小数；MANUAL 时 shareDaren/shareRealname 必填；合计实时预览；clientToken 幂等 |
| 成本详情抽屉 | Drawer 70% | 全字段只读 + 状态/录入人 + 更正历史入口 |
| 成本更正抽屉 | Drawer 720px | 预填原值可改；Diff 红冲/蓝补实时预览；correctionReason 必填 ≤512；clientToken |
| 核准确认弹窗 | Modal 400px | 汇总成本合计 + "核准后 5 分钟内自动计算利润"提示 |
| 超 48h 未录清单抽屉 | Drawer 60% | BR-118 督办清单（场次/平台/核准时间/已过小时数红标） |

### 8. 错误处理
- 1141（场次不存在或非已核准）：提示并刷新待录入清单（FIN-C-R1）；
- 1142（期间已结账 LOCKED）：全局提示条"财务期间已结账，本期间写操作冻结"；
- 1143（分成勾稽不平）：错误明细行内定位；
- 1144（更正原因必填）：表单校验；
- 1001（金额格式/负数）：InputNumber min=0 即时校验；
- 网络重试：clientToken 幂等防重复录入（返回已有单据）。

### 9. BR 业务规则覆盖
- **BR-107（成本录入完整率 > 95%）**：顶部完整率指标卡（已核准 vs 已录入）+ 超 48h 未录督办清单；
- **BR-118（核准后 48h 未录成本触发预警）**：isOver48h 红标 + 督办清单（ALERT 联动）；
- FIN-C-R1（仅已核准场次可录）：1141 拦截 + 待录入清单数据源即"已核准"；
- FIN-C-R2（GMV/退款 V1 只读同源）：录入抽屉只读区灰底 + "V1 数据同源"提示；
- FIN-C-R4（修改走更正单留痕）：更正抽屉 + 红冲蓝补（V2-E3）。

---

## P2. 利润核算（FIN-002）

### 1. 页面概述
- 路由路径：`/ims/fin/profit`
- 页面级别：一级菜单页，双 Tab：利润列表 / 异常净利率（2σ）+ 三级口径切换
- 依赖模块：P1 成本核准（触发源）、FIN-003 引擎（利润完成生成分成单）、ALERT（异常预警）
- 权限矩阵引用（PRD 4.2 FIN-002）：R1 R/W（重算）、R3 R/W/D（主责）、R4 R、R9 R（全量）、R5 R（本团队）、R7 R（本人场次）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [利润列表] [异常净利率(2σ)]                                   |
+------------------------------------------------------------------+
| 查询行: 场次号 | 平台 | 日期范围 | 计算状态 | 维度 | [查询][重置]  |
| 口径切换: [毛利] [经营利润] [净利润] (FIN-P-R2 三级口径)           |
+------------------------------------------------------------------+
| 利润表格: 场次号|标题|平台|GMV|毛利|经营利润|净利润|净利率|版本|    |
|           计算状态|计算时间|操作                                    |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
利润详情抽屉(80%):
  三级利润瀑布图(GMV→退款→佣金→毛利→投放→冲话费→经营→固定→样品→分成→净利)
  计算快照(公式+参数, BR-108) | 重算版本历史时间轴
  底部: [手动触发重算(R3/R1)] 
异常 Tab: 同类均值|σ|偏离σ|净利率 红标行 + [去核实]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FinProfitPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string;
  platform?: PlatformType;
  dateRange?: [string, string];
  calcStatus?: ProfitCalcStatus;
  dimensionType?: ProfitDimension;  // ACCOUNT / IP_GROUP / DAREN / OWNER
}
interface FinRecalcReq { sessionCode: string; }

// 响应类型
interface FinProfitVO {
  id: number;
  sessionCode: string;
  grossProfit: number;              // 毛利 = GMV − 退款 − 佣金
  operatingProfit: number;          // 经营利润 = 毛利 − 投放 − 冲话费
  netProfit: number;                // 净利润（BR-108 全扣公式）
  netProfitRate: number;            // DECIMAL(5,2)
  calcRuleSnapshot: {
    formula: string;                // BR-108 表达式
    params: Record<string, number>;
  };
  calcVersion: number;              // 重算递增
  calcStatus: ProfitCalcStatus;     // PENDING/CALCULATED/RECALCULATED/ABNORMAL
  calculatedAt: string;
}
interface FinProfitPageItem extends FinProfitVO {
  platform: string;
  sessionTitle: string;
  gmv: number;
}
interface FinProfitAbnormalItem extends FinProfitVO {
  peerAvgRate: number; sigma: number; deviationSigma: number;
}
interface FinProfitHistoryItem {
  calcVersion: number;
  netProfit: number; grossProfit: number; operatingProfit: number;
  calcStatus: string;
  triggerType: 'AUTO_CORRECTION' | 'MANUAL';
  triggerReason: string;
  calculatedAt: string;
}

// 枚举类型
type ProfitDimension = 'ACCOUNT' | 'IP_GROUP' | 'DAREN' | 'OWNER';
// ProfitCalcStatus = 'PENDING' | 'CALCULATED' | 'RECALCULATED' | 'ABNORMAL' —— 全局权威枚举
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /fin/profit/list`（默认净利润口径列全部三级值均展示，口径切换影响排序/汇总）；R5 本团队、R7 本人场次服务端过滤；R9 金额 `***`。失败重试。

#### 4.2 核心操作流程
**A. 利润列表查看**
1. QueryBar 筛选 + 维度筛选（账号/IP 组/达人/责任人）；三级口径切换 Radio（排序依据切换，FIN-P-R2）；
2. 行点击 → 利润详情抽屉（80%）。

**B. 利润详情（BR-108 透明化）**
1. 三级利润瀑布图（ECharts waterfall）：GMV → 逐项扣减 → 净利润，每级 hover 显示公式参数；
2. 计算快照区：formula + params 表格（BigDecimal 全链路，V2-E1 注释）；
3. 重算版本历史时间轴（`GET /fin/profit/history/{sessionCode}`）：每版本标注触发类型（成本更正自动/手动）与原因；
4. [手动触发重算]（R3/R1）→ ConfirmDialog："重算将生成新版本 V{n+1}，旧结果留痕" → `POST /fin/profit/recalc/{sessionCode}` → calcStatus=RECALCULATED（FIN-P-R3）。

**C. 异常净利率处理（FIN-P-R4）**
1. 异常 Tab：偏离 2σ 场次清单（deviationSigma 降序红标）；行 [去核实] → 利润详情抽屉 + 核实意见引导（ABNORMAL → 标记待核并已推送财务，ALERT 联动）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 19 位 IMS 编码 |
| platform | Select | 否 | 空 | PlatformType |
| dateRange | DateRangePicker | 否 | 近 30 天 | 场次日期 |
| calcStatus | Select | 否 | 空 | 待计算/已计算/已重算/异常待核 |
| dimensionType | Select | 否 | 空 | 账号/IP 组/达人/责任人 |

### 6. 表格列定义

**利润列表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次号 | 190 | — | 等宽字体；行点击打开详情 |
| sessionTitle | 场次标题 | 自适应 | — | — |
| platform | 平台 | 90 | — | tag |
| gmv | GMV | 130 | — | ¥ 千分位 |
| grossProfit | 毛利 | 120 | ✓ | ¥ 千分位 |
| operatingProfit | 经营利润 | 120 | ✓ | ¥ 千分位 |
| netProfit | 净利润 | 130 | ✓（默认口径） | ¥ 千分位；负数红括号 |
| netProfitRate | 净利率 | 90 | ✓ | 百分比两位；ABNORMAL 行橙色 |
| calcVersion | 版本 | 70 | — | V{n} |
| calcStatus | 计算状态 | 110 | — | tag：待计算(灰)/已计算(绿)/已重算(青)/异常待核(橙) |
| calculatedAt | 计算时间 | 150 | — | yyyy-MM-dd HH:mm |
| actions | 操作 | 110 | — | [详情][重算(R3/R1)] |

**异常净利率**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次号 | 190 | — | 等宽字体 |
| platform | 平台 | 90 | — | tag |
| netProfitRate | 净利率 | 110 | — | 百分比；红色（异常） |
| peerAvgRate | 同类均值 | 110 | — | 百分比 |
| sigma | 标准差 σ | 90 | — | 百分比 |
| deviationSigma | 偏离 σ | 100 | ✓ 降序 | "Nσ" 红色 |
| actions | 操作 | 110 | — | [去核实] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 利润详情抽屉 | Drawer 80% | 三级利润瀑布图 + 计算快照表 + 重算版本历史时间轴 + 底部 [手动触发重算] |
| 重算确认弹窗 | Modal 400px | "重算生成新版本，旧结果留痕（FIN-P-R3）"；期间 LOCKED 时拦截提示（1142） |

### 8. 错误处理
- 1145（成本未核准利润未计算）：详情入口提示"该场次成本尚未核准"；
- 1142（期间结账重算冻结）：重算按钮置灰 + tooltip；
- R7 越权查非本人场次：服务端过滤（1008）；
- R9 金额脱敏 `***` 渲染。

### 9. BR 业务规则覆盖
- **BR-108（净利润全扣公式）**：利润详情瀑布图 + calcRuleSnapshot 公式参数透明化（FIN-P-R1 自动计算 5 分钟提示在 P1 核准弹窗）；
- FIN-P-R2（三级口径同时落库）：三列展示 + 口径切换；
- FIN-P-R3（重算版本化留痕）：重算历史时间轴 + 版本列；
- FIN-P-R4（2σ 偏离待核预警）：异常 Tab + ALERT 联动标记。

---

## P3. 分成规则引擎（FIN-003 规则配置）

### 1. 页面概述
- 路由路径：`/ims/fin/share/rule`
- 页面级别：一级菜单页（规则列表 + 规则设计抽屉 + 阶梯配置器 + 试算抽屉）
- 依赖模块：V1 账号/IP 组字典（scope 范围选择）、PERF（无）、BigDecimal 试算
- 权限矩阵引用（PRD 4.2 FIN-003）：R1 R/W/D（全量）、R3 R/W/D（全量主责）、R4 R/W（审批视角）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 分成对象 | 状态 | [查询][重置]                  [创建规则] |
+------------------------------------------------------------------+
| 规则列表表格:                                                     |
| 规则名|分成对象|基数|比例方式|范围|优先级|版本|状态|生效期|操作       |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
规则设计抽屉(760px):
  规则名称* | 分成对象*(达人/实名人/团队) | 分成基数*(GMV/毛利/净利润)|
  比例方式*(固定/阶梯):
    固定: 比例输入(%)
    阶梯: 阶梯编辑器(动态行: 下限*|上限(末档空)|比例*%) 区间连续性校验|
  适用范围: 平台多选 | 账号多选 | IP组多选 (AND) |
  优先级*(冲突取高, FIN-S-R4) | 生效期*(from~to) |
  比例求和提示: 同场次多对象比例和须=1.0000 (V2-E2)
  底部: [试算] [保存] 
试算抽屉(640px): 试算基数输入¥ → 逐档明细表(区间|适用比例|金额) + 合计
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FinShareRuleCreateReq {
  ruleName: string;                 // 必填 ≤64 字
  shareTarget: ShareTarget;         // DAREN / REALNAME / TEAM
  baseType: ShareBaseType;          // GMV / GROSS_PROFIT / NET_PROFIT
  rateType: RateType;               // FIXED / LADDER
  fixedRate?: number;               // FIXED 必填 (0,1]
  ladderConfig?: LadderConfig[];    // LADDER 必填
  scope: {
    platforms?: PlatformType[];
    accountIds?: number[];
    ipGroupIds?: number[];
  };
  priority: number;                 // 必填
  effectiveRange: { from: string; to?: string };
  clientToken: string;
}
interface LadderConfig {
  min: number;                      // 分档下限
  max: number | null;               // 末档为 null（无穷）
  rate: number;                     // (0,1]
}
interface FinShareSimulateReq {
  ruleId?: number;
  draftRule?: Omit<FinShareRuleVO, 'id' | 'version' | 'status'>;
  simulateBase: number;             // 试算基数 ¥
}

// 响应类型
interface FinShareRuleVO {
  id: number;
  ruleName: string;
  shareTarget: ShareTarget;
  baseType: ShareBaseType;
  rateType: RateType;
  fixedRate?: number;
  ladderConfig?: LadderConfig[];
  scope: {
    platforms?: PlatformType[];
    accountIds?: number[];
    ipGroupIds?: number[];
  };
  priority: number;
  version: number;
  status: EnableStatus;             // ENABLED / DISABLED
  effectiveRange: { from: string; to?: string };
}
interface FinShareSimulateResp {
  simulateBase: number;
  shareAmount: number;              // ¥ BigDecimal
  calcDetail: Array<{ range: string; rateApplied: number; amount: number }>;
}

// 枚举类型
type ShareTarget = 'DAREN' | 'REALNAME' | 'TEAM';        // 达人/实名人/团队
type ShareBaseType = 'GMV' | 'GROSS_PROFIT' | 'NET_PROFIT';
type RateType = 'FIXED' | 'LADDER';                       // 固定/阶梯
// EnableStatus —— 全局权威枚举
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /fin/share/rules`；失败重试。

#### 4.2 核心操作流程
**A. 创建/编辑规则（R3 主责）**
1. [创建规则] → 设计抽屉：名称/分成对象/分成基数三选一/比例方式切换：
   - 固定：比例百分比输入（换算 (0,1]，1146 校验）；
   - 阶梯：阶梯编辑器动态行（下限/上限/比例），区间连续性即时校验（区间重叠 → 1146 拦截行内红标；末档上限留空=∞）；
2. 适用范围（平台/账号/IP 组多选 AND 组合）；优先级（数字越大越优先，FIN-S-R4）；
3. 保存时同范围同对象优先级冲突 → 1147 弹窗"存在同范围同对象优先级冲突规则，确认强制保存？"显式确认；
4. 同场次多对象比例求和提示条：实时提示当前启用的多对象规则比例和（=1.0000 校验提示，V2-E2）；
5. 提交（clientToken）→ `POST /fin/share/rule` / 编辑 `PUT`（version+1，FIN-S-R5 提示"规则变更不影响已生成分成单，重算需人工触发"）。

**B. 规则试算（BR-109 透明化，R3/R4）**
1. [试算] → 试算抽屉：输入试算基数（¥）→ `POST /fin/share/simulate` → 逐档明细表（区间/适用比例/金额）+ 合计金额；未保存的草稿规则也可试算（draftRule）。

**C. 停用规则（R3/R1）**
- [停用] → ConfirmDialog warning："历史分成单引用不受影响（FIN-S-R5）" → 状态 DISABLED。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| shareTarget | Select | 否 | 空 | 达人/实名人/团队 |
| status | Select | 否 | 空 | 启用/停用 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| ruleName | 规则名称 | 160 | — | 行点击打开设计抽屉（预填） |
| shareTarget | 分成对象 | 100 | — | 达人(紫)/实名人(青)/团队(蓝) tag |
| baseType | 分成基数 | 110 | — | GMV/毛利/净利润 |
| rateTypeSummary | 比例方式 | 140 | — | "固定 20.00%"/"阶梯 N 档"（悬浮阶梯明细） |
| scopeSummary | 适用范围 | 140 | — | "平台×N+账号×M"摘要，悬浮明细 |
| priority | 优先级 | 80 | ✓ 降序 | 数字 |
| version | 版本 | 70 | — | V{n} |
| status | 状态 | 90 | — | tag：启用(绿)/停用(灰) |
| effectiveRange | 生效期 | 200 | — | from ~ to（波浪号） |
| actions | 操作 | 160 | — | [编辑][试算][停用] 按状态/权限 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 规则设计抽屉 | Drawer 760px | ruleName 必填 ≤64；fixedRate (0,1]；ladderConfig 区间连续不重叠且比例 (0,1]（1146）；priority 必填；effectiveRange.from 必填；比例求和提示条（V2-E2）；clientToken |
| 试算抽屉 | Drawer 640px | simulateBase 必填 ≥0 两位小数；结果逐档明细 + 合计 ¥ |
| 冲突确认弹窗 | Modal 400px | 1147 同范围同对象优先级冲突，显式确认强制保存 |
| 停用确认弹窗 | Modal 400px | warning：历史分成单不受影响 |

### 8. 错误处理
- 1146（规则参数非法：比例越界/阶梯区间重叠）：行内红标 + 拦截；
- 1147（优先级冲突）：确认弹窗显式放行；
- 1001（参数校验）：表单即时校验；
- 试算超时：BigDecimal 服务端计算，前端仅展示（无浮点误差，V2-E1）。

### 9. BR 业务规则覆盖
- **BR-109（分成 = 基数×比例，阶梯逐档求和）**：阶梯编辑器 + 试算抽屉逐档明细（BigDecimal）；
- FIN-S-R1（BigDecimal 计算）：全链路约定（禁 float/double）；
- FIN-S-R4（规则冲突取优先级最高）：priority 列 + 1147 冲突确认；
- FIN-S-R5（规则变更不影响已生成单）：编辑/停用提示；
- V2-E2（多对象比例求和 = 1.0000）：设计抽屉实时求和提示。

---

## P4. 分成单管理（FIN-003 结果侧）

### 1. 页面概述
- 路由路径：`/ims/fin/share/result`
- 页面级别：一级菜单页（分成单列表 + 审批抽屉双审进度 + 发放登记）
- 依赖模块：P2 利润计算完成自动生成（FIN-S-R2）、FileUpload（发放凭证）、V2-E3 冲销
- 权限矩阵引用（PRD 4.2 FIN-003）：R1 R（全量）、R3 R/W（财务审+发放）、R4 R/W（业务审）、R7 R（本人分成单）、R9 R（脱敏）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 场次号 | 分成对象 | 状态 | [查询][重置]                     |
+------------------------------------------------------------------+
| 分成单表格:                                                       |
| 场次号|规则|分成对象|对象名|基数|分成金额|双审进度|状态|操作          |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
审批抽屉(70%):
  Tab: [分成明细] [计算过程] [审批留痕]
  分成明细: 场次|规则|基数|金额(阶梯明细)
  计算过程: calcDetail JSON 树形展示
  底部: [财务审核通过(R3)] [业务审核通过(R4)] [驳回]
  双审进度条: 财务审✓/✗ — 业务审✓/✗ (FIN-S-R3 双审生效)
发放登记弹窗: 发放凭证上传(FileUpload) + 备注 → [确认发放]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FinShareResultPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string;
  shareTarget?: ShareTarget;
  status?: ShareResultStatus;
}
interface FinShareAuditReq {
  conclusion: 'APPROVE' | 'REJECT';
  remark?: string;                  // 驳回建议填写 ≤512 字
  auditRole: AuditRole;             // FINANCE(R3) / BUSINESS(R4)
}
interface FinSharePayoffReq {
  payoffVoucher?: { fileName: string; ossKey: string };   // FileUpload 回执
  payoffNote?: string;
}

// 响应类型
interface FinShareResultVO {
  id: number;
  sessionCode: string;              // V1 19 位 IMS 编码
  ruleId: number;
  ruleName: string;
  shareTarget: ShareTarget;
  targetRefId: number;
  targetRefName: string;
  shareBase: number;                // 分成基数（按 baseType 取三级利润之一）¥
  shareAmount: number;              // ¥ BigDecimal
  calcDetail: Record<string, unknown>;
  status: ShareResultStatus;        // PENDING_AUDIT/AUDITED/PAID_OFF/REVERSED
  auditedBy?: number;
  auditedAt?: string;
  paidOffAt?: string;
}
interface FinShareAuditResp {
  status: ShareResultStatus;
  finAuditPassed: boolean;
  bizAuditPassed: boolean;
  bothPassed: boolean;              // 双审齐 → AUDITED（FIN-S-R3）
}

// 枚举类型
type AuditRole = 'FINANCE' | 'BUSINESS';   // 财务审(R3)/业务审(R4)
// ShareResultStatus = 'PENDING_AUDIT' | 'AUDITED' | 'PAID_OFF' | 'REVERSED' —— 全局权威枚举
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /fin/share/results`；R7 仅本人（targetRefId=本人）分成单；R9 金额 `***`。失败重试。

#### 4.2 核心操作流程
**A. 分成单查看**
1. 行点击 → 审批抽屉（70%）：分成明细（场次/规则/基数/金额 + 阶梯明细）、计算过程（calcDetail 树形 JSON）、审批留痕时间轴。

**B. 双审（FIN-S-R3，财务 R3 + 运营总监 R4）**
1. PENDING_AUDIT 行 [审批] → 审批抽屉底部按当前登录角色显示对应按钮：
   - 财务审核（R3）/ 业务审核（R4）各自 [通过] / [驳回]（remark 建议）；
   - 双审进度条：财务审 ✓/— 与 业务审 ✓/—；单边通过后 status 保持 PENDING_AUDIT，bothPassed=true 时 → AUDITED（生效）；
2. 任一环节驳回 → 提示驳回流转（冲销通道）；
3. 1148 兜底：非双审角色提交拦截；1149：无该审批角色权限。

**C. 发放登记（R3）**
1. AUDITED 行 [发放登记] → 弹窗：FileUpload 上传发放凭证（`businessScene: 'voucher'`）+ 备注 → `PUT /fin/share/result/{id}/payoff` → 状态 PAID_OFF。

**D. 冲销（REVERSED，V2-E3）**
- 负向调整/驳回后红冲：状态 REVERSED 行展示红冲分录明细（负数红括号金额）；新单补发后原单标"已冲销（新单已补）"。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 19 位 IMS 编码 |
| shareTarget | Select | 否 | 空 | 达人/实名人/团队 |
| status | Select | 否 | 空 | 待审/已审/已发放/已冲销 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次号 | 190 | — | 等宽字体；行点击打开审批抽屉 |
| ruleName | 规则 | 140 | — | — |
| shareTarget | 分成对象 | 100 | — | tag（同 P3） |
| targetRefName | 对象名 | 120 | — | R7 视角固定为本人 |
| shareBase | 分成基数 | 130 | — | ¥ 千分位（R9 `***`） |
| shareAmount | 分成金额 | 130 | ✓ 降序 | ¥ 千分位（R9 `***`） |
| auditProgress | 双审进度 | 140 | — | "财务✓/业务✗"双色 icon（PENDING_AUDIT 时） |
| status | 状态 | 100 | — | tag：待审(蓝)/已审(绿)/已发放(青)/已冲销(灰红) |
| actions | 操作 | 170 | — | [审批(待审)] [发放登记(已审)] [冲销明细(已冲销)] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 审批抽屉 | Drawer 70% | 三 Tab；底部按角色双审按钮（FINANCE/BUSINESS）；驳回 remark ≤512；双审进度条 |
| 发放登记弹窗 | Modal 480px | payoffVoucher 可选（FileUpload OSS 直传）；payoffNote ≤256 |
| 冲销明细弹窗 | Modal 640px | 红冲分录表（item + 负数金额红括号）+ "新单已补"关联链接 |

### 8. 错误处理
- 1148（双审未齐）：单边通过提示"等待另一角色审核后生效"；
- 1149（无审批角色权限）：按钮隐藏 + 兜底提示；
- R7 越权：服务端过滤；
- 凭证上传失败（5005）：FileUpload 重试 3 次。

### 9. BR 业务规则覆盖
- **BR-109 结果侧**：分成金额列 + 阶梯明细（与 P3 规则共引擎）；
- FIN-S-R2（利润完成自动生成分成单）：列表数据源（引擎联动 P2）；
- FIN-S-R3（双审生效）：双审进度条 + bothPassed 状态机；
- V2-E3（红冲+蓝补更正）：REVERSED 状态 + 冲销明细。

---

## P5. 利润看板（FIN-004）

### 1. 页面概述
- 路由路径：`/ims/fin/dashboard`
- 页面级别：一级菜单页（大屏聚合看板，独立页面，非抽屉模式）
- 依赖模块：`ims_fin_dashboard_cache`（小时级缓存，FIN-B-R1）、V1 台账详情（下钻终点，FIN-B-R2）、P2 利润明细
- 权限矩阵引用（PRD 4.2 FIN-004）：R1/R3/R4/R9 R（全量）、R5 R（本团队）、R7 R（本人场次）；导出 R1/R3/R4/R9

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 统计周期 | 口径(毛利/经营/净利) | [查询]        [导出报表] |
+------------------------------------------------------------------+
| 指标卡: GMV ¥xx | 总成本 ¥xx | 净利润 ¥xx | 净利率 xx% | 场次 N    |
|   (缓存刷新时间 refreshedAt, FIN-B-R1)                            |
+------------------------------------------------------------------+
| 左: 趋势图(日/周/月粒度, 环比/同比, ECharts 双轴)                 |
|     粒度切换: [日][周][月]                                        |
| 右: 成本结构饼图(佣金/投放/冲话费/固定/样品/达人分成/实名人分成)    |
+------------------------------------------------------------------+
| 下钻区: 维度 Tab(平台/账号/IP组/达人/责任人) 表格可逐级展开        |
|   展开最深: 场次明细行(点击→V1 台账详情抽屉, FIN-B-R2)             |
+------------------------------------------------------------------+
| 分成汇总区: 各对象周期总额表(对象|总额|场次数|已发放|待发放)        |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface FinOverviewReq {
  statPeriod: string;               // 必填 统计周期
  profitType?: 'GROSS' | 'OPERATING' | 'NET';
}
interface FinTrendReq {
  dateRange: [string, string];      // 必填
  granularity: 'DAY' | 'WEEK' | 'MONTH';
  profitType?: 'GROSS' | 'OPERATING' | 'NET';
}
interface FinDrilldownReq {
  statPeriod: string;
  dimensionType: DrillDim;          // PLATFORM/ACCOUNT/IP_GROUP/DAREN/OWNER
  dimensionValue?: string;
  drillToSession?: boolean;
}
interface FinExportReq {
  statPeriod: string;
  dimensionType?: string;
  format: 'XLSX' | 'PDF';
}

// 响应类型
interface FinOverviewResp {
  totalGmv: number; totalCost: number;
  netProfit: number; netProfitRate: number;
  sessionCount: number;
  costStructureRatio: Record<string, number>;
  refreshedAt: string;              // 缓存刷新时间（FIN-B-R1）
}
interface FinTrendItem {
  statPeriod: string;
  gmv: number; cost: number;
  netProfit: number; netProfitRate: number;
  momRate?: number; yoyRate?: number;
}
interface FinDrilldownItem {
  dimensionValue: string; dimensionLabel: string;
  totalGmv: number; totalCost: number;
  netProfit: number; sessionCount: number;
  children?: FinProfitVO[];         // drillToSession 时场次明细
}
interface FinCostStructureItem {
  costItem: CostItem;               // 佣金/投放/…/实名人分成
  amount: number; ratio: number;
}
interface FinShareSummaryItem {
  shareTarget: string;
  targetRefId: number; targetRefName: string;
  totalAmount: number; sessionCount: number;
  paidOffAmount: number; pendingAmount: number;
}
interface FinExportResp {
  downloadUrl: string;              // OSS 60s 签名 URL
  expiresIn: number;
}

// 枚举类型
type DrillDim = 'PLATFORM' | 'ACCOUNT' | 'IP_GROUP' | 'DAREN' | 'OWNER';
type CostItem = 'COMMISSION' | 'AD' | 'RECHARGE' | 'FIXED' | 'SAMPLE' | 'SHARE_DAREN' | 'SHARE_REALNAME';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 overview + trend（默认本月/日粒度/净利润口径）+ cost-structure + share-summary；指标卡右上角显示"缓存时间 refreshedAt（小时级刷新）"；R5/R7 数据范围服务端过滤；R9 金额 `***`。失败分区重试。

#### 4.2 核心操作流程
**A. 周期与口径切换**
1. 统计周期选择 + 口径三选一（毛利/经营利润/净利润，FIN-P-R2）→ 重新请求（概览/趋势/下钻联动）。

**B. 趋势分析**
1. 粒度切换（日/周/月）；双轴图（GMV/成本柱 + 净利率折线）；环比/同比数据点 hover 展示；
2. 周粒度 X 轴标签用波浪号周表述（如"第 25~25 周"区间样式）。

**C. 多维下钻（FIN-B-R2）**
1. 维度 Tab（平台/账号/IP 组/达人/责任人）→ `GET /fin/dashboard/drilldown` → 表格逐级展开（dimensionValue 树形展开）；
2. 展开最深场次明细行（drillToSession=true）→ 行点击 → **V1 直播台账详情抽屉**（跨模块联动，不跳出系统）。

**D. 分成汇总**
- 各对象周期总额表：总额（¥）/场次数/已发放/待发放（金额列，R9 `***`）。

**E. 报表导出**
1. [导出报表] → 格式选择（Excel/PDF）+ 当前周期与维度 → `GET /fin/dashboard/export` → 返回 OSS 60s 签名 URL 直接下载（同步下载，较数据量小）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| statPeriod | PeriodPicker | 是 | 本月 | 统计周期（日/周/月） |
| profitType | RadioGroup | 是 | NET | 毛利/经营/净利口径 |
| granularity | RadioGroup | 是 | DAY | 趋势粒度（趋势区） |
| dateRange | DateRangePicker | 是 | 本月 | 趋势范围 |

### 6. 表格列定义

**下钻区（维度 Tab）**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| dimensionLabel | 维度值 | 180 | — | 树形展开箭头（可逐级下钻） |
| totalGmv | GMV | 130 | — | ¥ 千分位 |
| totalCost | 总成本 | 130 | — | ¥ 千分位 |
| netProfit | 净利润 | 130 | ✓ 降序 | ¥ 千分位；负数红括号 |
| sessionCount | 场次数 | 90 | — | 数字 |
| actions | 操作 | 120 | — | 场次明细行点击 → V1 台账抽屉 |

**分成汇总表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| targetRefName | 分成对象 | 140 | — | shareTarget tag 附带 |
| totalAmount | 周期总额 | 130 | ✓ 降序 | ¥ 千分位 |
| sessionCount | 场次数 | 90 | — | — |
| paidOffAmount | 已发放 | 130 | — | ¥ 千分位 |
| pendingAmount | 待发放 | 130 | — | ¥ 千分位（>0 黄标） |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| V1 台账详情抽屉 | 复用 V1 LIVE-004 详情组件 | 场次下钻终点（FIN-B-R2），跨模块复用 |
| 导出格式弹窗 | Modal 360px | XLSX/PDF 单选 + 当前筛选回显 |

### 8. 错误处理
- 缓存刷新延迟：指标卡 refreshedAt 标注 + "数据截至"提示（FIN-B-R1 小时级）；
- 下钻层级越权（R5/R7）：服务端过滤；
- 导出签名 URL 过期（60s）：过期提示重新发起；
- 空数据：空态占位图。

### 9. BR 业务规则覆盖
- **BR-108 看板侧**：净利润指标卡 + 趋势（全扣公式结果消费方）；
- FIN-B-R1（小时级缓存刷新）：refreshedAt 标注；
- FIN-B-R2（下钻最深场次明细，联动 V1 台账）：drilldown 树形展开 + V1 详情抽屉复用；
- FIN-B-R3（数据权限同角色矩阵）：R5 本团队/R7 本人/R9 脱敏服务端过滤；
- FIN-P-R2（三级口径切换）：口径 RadioGroup 联动全部区块。

---

## 附录 A. 模块级约定

1. **枚举引用**：全局权威枚举 `EntryCostStatus`（DRAFT/SUBMITTED/CONFIRMED）、`ProfitCalcStatus`（PENDING/CALCULATED/RECALCULATED/ABNORMAL）、`ShareResultStatus`（PENDING_AUDIT/AUDITED/PAID_OFF/REVERSED）、`EnableStatus`、`PlatformType`；模块内联枚举 `ShareCostType`/`ShareTarget`/`ShareBaseType`/`RateType`/`AuditRole`/`DrillDim`/`CostItem` 值域与 FIN-API 契约一致；
2. **错误码段**：1141~1150 FIN 段（1141 场次非已核准、1142 期间已结账 LOCKED、1143 分成勾稽不平、1144 更正原因必填、1145 成本未核准、1146 规则参数非法、1147 优先级冲突、1148 双审未齐、1149 无审批角色权限）；
3. **金额规范（V2-E1）**：全模块 DECIMAL(12,2) 两位小数、¥ 前缀千分位；比例 DECIMAL(5,4) 百分比展示；BigDecimal 全链路（前端禁浮点运算展示换算误差，计算结果以服务端为准）；
4. **幂等（V2-E4）**：成本录入/更正、分成审批、发放登记等金额写接口全部携带 clientToken；
5. **红冲蓝补（V2-E3）**：更正/冲销不做物理修改，负数红括号渲染约定；
6. **数据同源（FIN-C-R2）**：GMV/退款一律 V1 只读带出，财务侧不可改。

## 附录 B. BR/FIN/V2-E 规则 ↔ 页面落点总表

| 规则 | 约束摘要 | 页面落点 |
|------|----------|----------|
| BR-107 | 成本录入完整率 > 95% | P1 完整率指标卡 + 超 48h 清单 |
| BR-108 | 净利润全扣公式 | P2 瀑布图 + 快照 / P5 指标卡 |
| BR-109 | 分成 = 基数×比例（阶梯求和） | P3 阶梯配置 + 试算 / P4 金额与明细 |
| BR-118 | 48h 未录成本预警 | P1 isOver48h 红标（ALERT 联动） |
| FIN-C-R1~R4 | 已核准可录/只读同源/48h 预警/更正留痕 | P1 全流程 |
| FIN-P-R1~R4 | 5min 自动算/三级口径/版本留痕/2σ 待核 | P2 详情 + 异常 Tab |
| FIN-S-R1~R5 | BigDecimal/自动生成/双审/优先级/不影响已生成 | P3 规则 + P4 双审 |
| FIN-B-R1~R3 | 小时缓存/下钻至场次/权限矩阵 | P5 看板 |
| V2-E1~E4 | 精度/求和 1.0000/红冲蓝补/幂等 | 全模块（金额渲染 + clientToken） |

（全文完）
