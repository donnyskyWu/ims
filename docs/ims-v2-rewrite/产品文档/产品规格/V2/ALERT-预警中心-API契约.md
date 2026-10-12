# ALERT - 预警中心 API 契约

> **模块范围**：13 预警中心（V2，第 23~26 周，V2.3 批次，**框架先行 + 规则子集**）——ALERT-001 预警规则配置、ALERT-002 定时检查与推送、ALERT-003 三级升级机制、ALERT-004 去重合并与统计。
> **权威依据**：《IMS第二期PRD-V2.md》5.24~5.27；BR-111~BR-114；V2-C1~C5 预警规则引擎约束（JSON DSL）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`rule_code → ruleCode`、`dedup_key → dedupKey`）；周次波浪号格式。**关键口径**：预警级别三级 `AlertLevel = 'L1' | 'L2' | 'L3'`（L1 提示 / L2 警告 / L3 严重）；三级升级 30/60 分钟（BR-113，L3 直接从二级起跳）；去重合并 dedupKey = 规则+对象，30 分钟窗口计数累加（BR-114）；**错误码 1009（预警规则 DSL 非法）为共享规范原码，归并至本域 1165+ 使用**（全局规范第 3 章迁移表）。

---

## 1. API 总览表（共 20 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/alert/rule/list` | 规则列表（含未启用占位） | R1/R3（财务类）/R4（业务类） |
| 2 | POST | `/admin-api/ims/alert/rule` | 注册规则 | 同上 |
| 3 | PUT | `/admin-api/ims/alert/rule/{id}` | 编辑参数（阈值热更新） | 同上 |
| 4 | PUT | `/admin-api/ims/alert/rule/{id}/enable` | 启用/停用 | R1 |
| 5 | GET | `/admin-api/ims/alert/rule/hit-stats` | 规则命中统计 | R1/R3/R4/R9 |
| 6 | GET | `/admin-api/ims/alert/check/records` | 预警记录列表（分页） | R1/R2/R3/R4（全局）/目标人（本人相关） |
| 7 | GET | `/admin-api/ims/alert/check/{alertNo}` | 预警详情（含跳转来源单据） | 同上 |
| 8 | PUT | `/admin-api/ims/alert/check/{alertNo}/respond` | 响应处置（确认/处理/误报） | 预警目标人、R4 |
| 9 | GET | `/admin-api/ims/alert/check/my-alerts` | 我的预警（工作台） | 目标人本人 |
| 10 | GET | `/admin-api/ims/alert/check/delivery-stats` | 送达率统计（BR-111） | R1/R2/R3/R4/R9 |
| 11 | POST | `/admin-api/ims/alert/check/run/{ruleId}` | 手动触发检查 | R1/R3/R4 |
| 12 | GET | `/admin-api/ims/alert/escalate/timeline/{alertNo}` | 升级时间轴 | R1/R4/各级接收人 |
| 13 | PUT | `/admin-api/ims/alert/escalate/config` | 升级链路配置（时限/层级接收人） | R1 |
| 14 | GET | `/admin-api/ims/alert/escalate/pending` | 待升级/升级中预警（分页） | R1/R4 |
| 15 | GET | `/admin-api/ims/alert/escalate/response-stats` | 响应率统计（BR-112） | R1/R2/R3/R4/R9 |
| 16 | GET | `/admin-api/ims/alert/stats/overview` | 全局统计总览 | R1/R2/R3/R4/R9 |
| 17 | GET | `/admin-api/ims/alert/stats/response-rate` | 响应率（BR-112） | 同上 |
| 18 | GET | `/admin-api/ims/alert/stats/rule-rank` | 规则命中排行 | 同上 |
| 19 | GET | `/admin-api/ims/alert/stats/merge-logs` | 合并记录（分页） | R1/R2/R3/R4/R9 |
| 20 | GET | `/admin-api/ims/alert/stats/weekly-report` | 周报数据（推送管理层） | R1/R2/R3/R4 |

---

## 2. 接口明细

### 2.1 预警规则配置（ALERT-001）

#### 2.1.1 GET /admin-api/ims/alert/rule/list — 规则列表

**请求**（Query）：`PageParam` + `{ sourceModule?: string; level?: AlertLevel; enabled?: 'ENABLED' | 'DISABLED' }`

**响应** `data`：`PageResult<AlertRuleVO>`

```typescript
interface AlertRuleVO {
  id: number;
  ruleCode: string;              // 如 CERT_EXPIRE / ACCT_UNRETURN / LIVE_RISK / COLLECT_ERROR / FIN_COST_MISS
  ruleName: string;
  /** 来源模块（06/08/10/16/11） */
  sourceModule: string;
  /** 触发方式：1 事件驱动（模块直接投递）/ 2 定时检查（cron 扫描） */
  triggerType: 'EVENT' | 'SCHEDULED';
  /** 触发条件与阈值（JSON DSL，参数化），结构示例：
   * { "source": "ims_fin_cost", "condition": { "field": "hours_since_approve", "op": "GT", "value": 48 } } */
  triggerConfig: Record<string, unknown>;
  /** 定时检查 cron 表达式（triggerType=SCHEDULED 必填） */
  checkCron?: string;
  level: AlertLevel;             // L1 提示 / L2 警告 / L3 严重
  /** 通知对象（角色/具体人/责任人动态） */
  notifyTargets: {
    roles?: string[];            // 如 ['R2', 'R4']
    userIds?: number[];
    dynamicTarget: 'RESPONSIBLE_PERSON' | 'DEPT_LEADER' | 'NONE';
  };
  enabled: 'ENABLED' | 'DISABLED';
  /** 启用条件说明（未接入规则占位，如"待 04 竞品管理上线"） */
  enableCondition?: string;
}
```

**首批启用规则子集（ALR-C-R1）**：`CERT_EXPIRE`（证件到期，V1 06 迁移并入）、`ACCT_UNRETURN`（账号未归还，V1 08）、`LIVE_RISK`（直播风险，V1 10 迁移）、`COLLECT_ERROR`（采集异常，V1 16），共 4 条；`FIN_COST_MISS`（成本未录入，V3 11 财务，BR-118）：随 11 财务上线（V3 第 33 周后）启用，当前注册但置 `DISABLED`。其余规则注册但置 `DISABLED`。

#### 2.1.2 POST /admin-api/ims/alert/rule — 注册规则

**请求**：`Omit<AlertRuleVO, 'id'>` → **响应** `data`：`AlertRuleVO`。

**错误码**：**1009**（预警规则 DSL 非法——triggerConfig 结构/操作符/字段不合法，共享规范 8.2 原码，本域归并使用）、1165（规则编码已存在）、1001（参数校验）。

#### 2.1.3 PUT /admin-api/ims/alert/rule/{id} — 编辑参数

**请求**：`Omit<AlertRuleVO, 'id' | 'ruleCode'>`（阈值/级别/通知对象可改）→ **响应** `data`：`AlertRuleVO`。阈值修改即时生效（热更新，ALR-C-R2）。

#### 2.1.4 PUT /admin-api/ims/alert/rule/{id}/enable — 启用/停用

**请求**：`{ enabled: 'ENABLED' | 'DISABLED' }` → **响应**：`data: null`。规则删除仅支持停用（历史预警数据引用不可断，ALR-C-R3）。

#### 2.1.5 GET /admin-api/ims/alert/rule/hit-stats — 命中统计

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`Array<{ ruleCode: string; ruleName: string; alertCount: number; responseRate: number; falseAlarmCount: number; lastHitAt?: string }>`。

### 2.2 定时检查与推送（ALERT-002）

#### 2.2.1 GET /admin-api/ims/alert/check/records — 预警记录列表（分页）

**请求**（Query）：`PageParam` + `{ ruleCode?: string; level?: AlertLevel; responseStatus?: AlertEventStatus; pushStatus?: 'PENDING' | 'DELIVERED' | 'PARTIAL_FAILED' | 'FAILED'; dateRange?: [string, string] }`

**响应** `data`：`PageResult<AlertEventVO>`

```typescript
interface AlertEventVO {
  id: number;
  alertNo: string;               // AL+日期+流水
  ruleId: number;
  ruleCode: string;
  ruleName: string;
  /** 来源单据引用（点击直达，sourceRefType: 如 CERT/ACCOUNT/SESSION/COST） */
  sourceRefType: string;
  sourceRefId: string;
  level: AlertLevel;             // L1/L2/L3
  content: string;
  /** 去重合并：同一规则+同一对象 30 分钟窗口合并，计数累加（BR-114） */
  dedupKey: string;              // 规则编码 + 对象标识
  mergedCount: number;           // 合并累计命中次数
  notifyTargetUserIds: number[];
  pushStatus: 'PENDING' | 'DELIVERED' | 'PARTIAL_FAILED' | 'FAILED';
  /** 推送通道与回执（工作台+钉钉+短信兜底） */
  pushChannels: Array<{ channel: 'WORKBENCH' | 'DINGTALK' | 'SMS'; success: boolean; receiptAt?: string }>;
  responseStatus: AlertEventStatus;      // OPEN / CONFIRMED / RESOLVED / FALSE_ALARM
  respondedBy?: number;
  respondedAt?: string;
  occurredAt: string;
}
```

#### 2.2.2 GET /admin-api/ims/alert/check/{alertNo} — 预警详情

**响应** `data`：`AlertEventVO & { sourceJumpUrl: string; escalationTimeline: Array<{ level: 1 | 2 | 3; escalatedTo: number[]; escalatedAt: string; elapsedMinutes: number }> }`。

#### 2.2.3 PUT /admin-api/ims/alert/check/{alertNo}/respond — 响应处置

**请求**：

```typescript
interface AlertRespondReq {
  response: 'CONFIRM' | 'RESOLVE' | 'FALSE_ALARM';
  handleRemark: string;          // 处理说明
  /** FALSE_ALARM 时反馈误报原因（连续误报 ≥5 次建议复核阈值，ALR-S-R3） */
  falseAlarmReason?: string;
}
```

**响应** `data`：`{ alertNo: string; responseStatus: AlertEventStatus; escalationStopped: boolean }`（任一级响应即停止后续升级，ALR-E-R3）。

**错误码**：1166（非预警目标人，无权响应）、1167（预警已终态不可重复响应）。

#### 2.2.4 GET /admin-api/ims/alert/check/my-alerts — 我的预警

**响应** `data`：`Array<AlertEventVO & { isUnread: boolean }>`（工作台预警待办入口）。

#### 2.2.5 GET /admin-api/ims/alert/check/delivery-stats — 送达率（BR-111）

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ totalDelivered: number; totalShould: number; deliveryRate: number; failedAlerts: Array<{ alertNo: string; failedChannel: string; retryCount: number }>; target: number }`（BR-111 目标 > 99%；送达失败自动补发 1 次，仍失败标记失败并告警管理员，ALR-P-R2）。

#### 2.2.6 POST /admin-api/ims/alert/check/run/{ruleId} — 手动触发检查

**响应** `data`：`{ checkTaskId: string; ruleCode: string; message: string }`（复用定时检查引擎执行条件扫描，结果走统一去重合并流程）。

### 2.3 三级升级机制（ALERT-003）

#### 2.3.1 GET /admin-api/ims/alert/escalate/timeline/{alertNo} — 升级时间轴

**响应** `data`：

```typescript
interface AlertEscalationTimelineResp {
  alertNo: string;
  alertLevel: AlertLevel;
  occurredAt: string;
  timeline: Array<{
    escalationLevel: 1 | 2 | 3;
    escalatedTo: Array<{ userId: number; userName: string; roleLabel: string }>;
    escalatedAt: string;
    elapsedMinutes: number;      // 距预警产生时长
  }>;
  currentLevel: 1 | 2 | 3 | null;
  responseStatus: AlertEventStatus;
}
```

#### 2.3.2 PUT /admin-api/ims/alert/escalate/config — 升级链路配置

**请求**：

```typescript
interface AlertEscalationConfigReq {
  /** 升级时限（BR-113：一级 30 分钟、二级 60 分钟，自上一级计） */
  level1TimeoutMinutes: number;  // 默认 30
  level2TimeoutMinutes: number;  // 默认 60
  /** L3 严重级预警直接从二级开始升级（ALR-E-R2） */
  severeStartLevel: 2 | 3;       // 默认 2
  level1Receivers: { dynamicTarget: 'RESPONSIBLE_PERSON' };
  level2Receivers: { dynamicTarget: 'DEPT_LEADER'; extraUserIds?: number[] };
  level3Receivers: { roleCodes: string[] };   // 默认 ['R4', 'R1']（运营总监+系统管理员）
}
```

**响应**：`data: null`。升级通知走钉钉强提醒（DING 或短信，ALR-E-R4）。

#### 2.3.3 GET /admin-api/ims/alert/escalate/pending — 待升级/升级中预警（分页）

**请求**（Query）：`PageParam` + `{ currentLevel?: 1 | 2 | 3 }` → **响应** `data`：`PageResult<AlertEventVO & { currentLevel: 1 | 2 | 3; nextEscalateAt: string }>`。

#### 2.3.4 GET /admin-api/ims/alert/escalate/response-stats — 响应率（BR-112）

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ totalAlerts: number; respondedInTime: number; responseRate: number; avgResponseMinutes: number; target: number; byLevel: Array<{ level: AlertLevel; responseRate: number }> }`（BR-112 目标 > 90%）。

### 2.4 去重合并与统计（ALERT-004）

#### 2.4.1 GET /admin-api/ims/alert/stats/overview — 全局统计总览

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ totalAlertCount: number; byLevel: Record<AlertLevel, number>; responseRate: number; deliveryRate: number; falseAlarmRate: number; escalateRate: number; avgResponseMinutes: number }`（预警健康度四指标：送达率/误报率/升级率/响应率）。

#### 2.4.2 GET /admin-api/ims/alert/stats/response-rate — 响应率趋势

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`Array<{ statDate: string; responseRate: number; alertCount: number }>`。

#### 2.4.3 GET /admin-api/ims/alert/stats/rule-rank — 规则命中排行

**请求**（Query）：`{ dateRange?: [string, string]; topN?: number }` → **响应** `data`：`Array<{ rank: number; ruleCode: string; ruleName: string; alertCount: number; mergedSavingsCount: number; responseRate: number }>`（合并节省数 = 被去重合并掉的重复推送数）。

#### 2.4.4 GET /admin-api/ims/alert/stats/merge-logs — 合并记录（分页）

**请求**（Query）：`PageParam` + `{ ruleCode?: string; dateRange?: [string, string] }` → **响应** `data`：`PageResult<{ id: number; masterAlertNo: string; mergedAlertNos: string[]; mergedCount: number; mergeWindowMinutes: number; masterOccurredAt: string; lastMergedAt: string }>`（合并窗口默认 30 分钟，按规则可配 5~60 分钟，ALR-S-R1；合并预警内容更新计数与最新发生时间，ALR-S-R2）。

#### 2.4.5 GET /admin-api/ims/alert/stats/weekly-report — 周报数据

**请求**（Query）：`{ weekStart?: string }` → **响应** `data`：`{ weekRange: [string, string]; totalAlerts: number; topRules: Array<{ ruleCode: string; alertCount: number }>; responseRate: number; deliveryRate: number; escalatedAlerts: Array<{ alertNo: string; level: AlertLevel; currentLevel: 1 | 2 | 3 }>; suggestions: string[] }`（周报推送管理层，V2-A1 集群化调度）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**预警事件（AlertEventVO.responseStatus，全局枚举 AlertEventStatus）**：

```
OPEN（产生）──确认──▶ CONFIRMED ──处理完成──▶ RESOLVED
   │                    │
   │                    └──误报──▶ FALSE_ALARM（误报反馈至规则阈值复核）
   │
   └──未响应：升级链（BR-113）
        L1 责任人 30min 未响应 → 二级（部门负责人）60min 未响应 → 三级（R4+R1）
        L3 严重级直接从二级起跳（ALR-E-R2）；任一级响应即停止（ALR-E-R3）
```

**推送状态（pushStatus）**：`PENDING → DELIVERED / PARTIAL_FAILED →（补发 1 次）→ FAILED（告警管理员）`。

**规则（enabled）**：`ENABLED ↔ DISABLED`（仅停用不删除；阈值热更新即时生效）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-111 | 预警送达率 > 99%（补发 1 次） | 2.2.5 |
| BR-112 | 预警响应率 > 90%（时限内确认/处理） | 2.3.4 / 2.4.2 |
| BR-113 | 三级升级 30/60 分钟；L3 从二级起跳 | 2.3.2 配置 |
| BR-114 | 去重合并：同规则+同对象 30 分钟窗口合并计数 | 2.2.1 dedupKey / 2.4.4 |
| BR-118 | 成本 48h 未录入预警（随 V3 11 财务上线（第 33 周后）启用，当前注册置 DISABLED） | 2.1.1 FIN_COST_MISS |
| ALR-C-R1 | 首批 4 条规则子集，其余占位 | 2.1.1 说明 |
| ALR-C-R2 | 阈值修改即时热更新 | 2.1.3 |
| ALR-C-R3 | 规则仅停用不删除 | 2.1.4 |
| ALR-P-R1 | 严重级 1 分钟内送达（钉钉>短信兜底） | 2.2.1 pushChannels |
| ALR-P-R2 | 送达失败补发 1 次，仍失败告警管理员 | 2.2.5 |
| ALR-P-R3 | 去重合并判定先于推送 | 2.2.1 |
| ALR-E-R1~R4 | 升级时限/严重级起跳/响应停止/DING 强提醒 | 2.3.x |
| ALR-S-R1~R3 | 合并窗口可配 5~60 分钟/内容更新计数/误报反馈 | 2.4.4 / 2.2.3 |
| V2-C1~C5 | 规则引擎 JSON DSL（校验错误码 1009 归并本域）、检查任务集群化调度（V2-A1） | 2.1.2 / 2.2.6 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 预警规则配置页（QueryBar + 表格） | 规则列表查询（模块/级别/启停筛选） | GET /alert/rule/list |
| 规则编辑抽屉（阈值参数化编辑器） | 注册/编辑规则（DSL 参数化表单） | POST /alert/rule、PUT /alert/rule/{id} |
| 规则行操作 | 启用/停用（未接入规则占位说明） | PUT /alert/rule/{id}/enable |
| 规则命中统计页 | 命中统计查看 | GET /alert/rule/hit-stats |
| 预警记录页（QueryBar + 表格） | 预警记录列表查询 | GET /alert/check/records |
| 预警详情抽屉（DetailDrawer 内联） | 详情查看（来源单据跳转链接） | GET /alert/check/{alertNo} |
| 预警详情-响应操作 | 确认 / 处理完成 / 标记误报 | PUT /alert/check/{alertNo}/respond |
| 个人工作台-我的预警 | 未读预警列表 | GET /alert/check/my-alerts |
| 送达率指标卡 | 送达率看板（失败明细） | GET /alert/check/delivery-stats |
| 规则行操作-手动检查 | 手动触发检查（ConfirmDialog） | POST /alert/check/run/{ruleId} |
| 预警详情-升级时间轴 | 升级时间轴可视化 | GET /alert/escalate/timeline/{alertNo} |
| 升级链路配置页（R1） | 时限/层级接收人配置 | PUT /alert/escalate/config |
| 待升级预警页 | 待升级/升级中清单查询 | GET /alert/escalate/pending |
| 响应率统计看板 | 响应率 / 趋势（BR-112） | GET /alert/escalate/response-stats、GET /alert/stats/response-rate |
| 预警统计总览页 | 全局统计（级别分布/健康度四指标） | GET /alert/stats/overview |
| 规则命中排行页 | 排行（合并节省数） | GET /alert/stats/rule-rank |
| 合并记录页 | 去重合并记录查询 | GET /alert/stats/merge-logs |
| 周报页 | 周报数据查看（推送管理层） | GET /alert/stats/weekly-report |

（全文完）
