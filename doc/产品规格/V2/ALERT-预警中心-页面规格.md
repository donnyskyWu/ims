# ALERT - 预警中心 页面规格（V2.3 批次，13 模块，框架先行 + 规则子集）

> **模块范围**：ALERT-001 预警规则配置 / ALERT-002 定时检查与推送 / ALERT-003 三级升级机制 / ALERT-004 去重合并与统计。
> **权威依据**：《IMS第二期PRD-V2.md》5.24~5.27、6.6 预警中心统一分发；《ALERT-预警中心-API契约.md》（20 接口，1165~1167 错误码段 + 1009 DSL 归并）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**（4 页）：P1 预警规则配置（Web）｜P2 预警记录与处置（Web + 工作台"我的预警"卡片）｜P3 升级中心（Web）｜P4 预警统计看板（Web）。
> **模块核心口径**：预警级别三级 `AlertLevel = 'L1'|'L2'|'L3'`（L1 提示/L2 警告/L3 严重）；**三级升级 30/60 分钟**（BR-113：一级责任人 30min → 二级部门负责人 60min → 三级 R4+R1；L3 严重级直接从二级起跳 ALR-E-R2；任一级响应即停止 ALR-E-R3）；**去重合并 dedupKey = 规则+对象，30 分钟窗口计数累加**（BR-114，窗口按规则可配 5~60 分钟 ALR-S-R1）；送达率 >99%（BR-111）、响应率 >90%（BR-112）。
> **V2 交付形态**：**框架先行 + 首批 4 条规则子集**（CERT_EXPIRE / ACCT_UNRETURN / LIVE_RISK / COLLECT_ERROR），其余规则注册占位（DISABLED + enableCondition 说明），随上游模块上线陆续启用；FIN_COST_MISS（成本未录入，V3 11 财务，BR-118）：随 11 财务上线（V3 第 33 周后）启用，当前注册但置 DISABLED。

## 0.1 导航（走查 #17 · SSOT = 完整 PRD v2.6.13）

**侧栏路径**：数据决策 → **预警中心**（可展开 L2）→ **预警规则 · 实时预警**（实时预警页内 Tab：**实时预警 / 处置记录 / 去重合并**）。  
**边界**：阈值 DSL 在 **16 数据采集 → 阈值规则**；本模块消费告警实例与处置。  
**兼容**：`go('alert')` → 实时预警；`go('alertHistory'|'alertDedup')` → 实时预警对应 Tab。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase（`rule_code → ruleCode`、`dedup_key → dedupKey`）。
- 枚举以《全局开发规范.md》第 4 章为唯一权威源。本模块引用：`AlertLevel`（L1/L2/L3）、`AlertEventStatus`（OPEN/CONFIRMED/RESOLVED/FALSE_ALARM）、`EnableStatus`（规则启停 ENABLED/DISABLED）。
- **V1 对齐说明**：V1 各模块原 `AlarmLevel INFO/WARN/CRITICAL` 已统一为全局 `AlertLevel = 'L1'|'L2'|'L3'`（V1 修订已落地）。
- 预警编号 alertNo = `AL+日期+流水`（code 样式渲染）。
- 权限矩阵引用 PRD 4.2 + 5.24~5.27.5：R1 超管（全量+启停+升级链路配置主责）、R3 财务（财务类规则）、R4 运营总监（业务类规则+响应处置）、R2 人事（记录/统计查看）、R9（统计脱敏）、预警目标人（本人相关 + 响应）。
- StatusTag 语义色：L1 → 蓝提示 / L2 → 橙警告 / L3 → 红严重；OPEN → 红点"未响应" / CONFIRMED → 橙"已确认" / RESOLVED → 绿"已处理" / FALSE_ALARM → 灰"误报"；pushStatus：PENDING 灰 / DELIVERED 绿 / PARTIAL_FAILED 橙 / FAILED 红。

---

## P1 预警规则配置（ALERT-001）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/alert/rule`（菜单：预警中心 → 规则配置） |
| 页面级别 | 二级（模块主页面） |
| 前置依赖 | V1 06/08/10/16 模块规则迁移并入；FIN_COST_MISS 随 11 财务上线（V3 第 33 周后，BR-118），当前注册置 DISABLED |
| 权限 | 查看：R1/R3（财务类）/R4（业务类）；新增/编辑：R1/R4（业务）/R3（财务）；启停：R1 |
| 用户 | 超管 R1（启停主责）/ 运营总监 R4 / 财务 R3 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 预警规则配置    [首批启用 4 条 | 占位待启用 {n} 条]                        │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [来源模块 Select:全部/06证件/08账号/10直播/16采集/11财务/ │
│  …][级别 Select:全部/L1/L2/L3][状态 Select:全部/已启用/未启用]            │
│  [搜索][重置]                                  [+ 注册规则(模块侧)]     │
├──────────────────────────────────────────────────────────────────────────┤
│ 规则表格                                                     共 {n} 条  │
│ ┌────────────┬──────┬────────┬────────────┬──────┬──────┬──────────┐    │
│ │规则编码/名称│来源  │触发方式│ 触发条件摘要│ 级别 │ 状态 │ 操作      │    │
│ ├────────────┼──────┼────────┼────────────┼──────┼──────┼──────────┤    │
│ │CERT_EXPIRE │06证件│定时    │到期≤7天     │ L2   │启用  │编辑 手动检│    │
│ │证件到期    │      │cron    │(days<=7)    │      │      │查 停用    │    │
│ │FIN_COST_   │11财务│定时    │核准后48h未录│ L2   │🔒未  │查看(只读)│    │
│ │MISS        │      │        │(hours>48)   │      │启用  │          │    │
│ │            │      │        │             │      │注²   │          │    │
│ │COMP_SUBMIT │04竞品│事件    │占位         │ L2   │🔒未  │查看(只读)│    │
│ │_RATE       │      │        │             │      │启用  │          │    │
│ │            │      │        │             │      │注¹   │          │    │
│ └────────────┴──────┴────────┴────────────┴──────┴──────┴──────────┘    │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ 底部操作区:  [升级链路配置(R1)] [命中统计]                                │
└──────────────────────────────────────────────────────────────────────────┘
注¹: enableCondition = "待 04 竞品管理上线"（占位规则锁态，不可启用）
注²: FIN_COST_MISS（成本未录入，V3 11 财务，BR-118）：随 11 财务上线（V3 第 33 周后）启用，当前注册但置 DISABLED（占位规则锁态，不可启用）
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
/** 预警级别：L1 提示 / L2 警告 / L3 严重 */
type AlertLevel = 'L1' | 'L2' | 'L3';
/** 触发方式（契约内联） */
type AlertTriggerType = 'EVENT' | 'SCHEDULED';
/** 通知对象动态目标（契约内联） */
type AlertDynamicTarget = 'RESPONSIBLE_PERSON' | 'DEPT_LEADER' | 'NONE';

// ===== 请求 =====
interface AlertRuleQueryReq extends PageParam {
  sourceModule?: string;
  level?: AlertLevel;
  enabled?: EnableStatus;
}

interface AlertRuleSaveReq {              // 编辑态剔除 ruleCode（口径不可改）
  ruleCode?: string;                     // 仅注册时可填
  ruleName: string;
  sourceModule: string;                  // 06/08/10/16/11…
  triggerType: AlertTriggerType;
  /** 触发条件 JSON DSL（参数化），示例:
   * { "source": "ims_fin_cost", "condition": { "field": "hours_since_approve", "op": "GT", "value": 48 } } */
  triggerConfig: Record<string, unknown>;
  checkCron?: string;                    // SCHEDULED 必填
  level: AlertLevel;
  notifyTargets: {
    roles?: string[];
    userIds?: number[];
    dynamicTarget: AlertDynamicTarget;
  };
  enabled?: EnableStatus;
}

interface AlertEscalationConfigReq {
  /** BR-113：一级 30 分钟、二级 60 分钟（自上一级计） */
  level1TimeoutMinutes: number;          // 默认 30
  level2TimeoutMinutes: number;          // 默认 60
  /** L3 严重级直接从二级开始升级（ALR-E-R2） */
  severeStartLevel: 2 | 3;               // 默认 2
  level1Receivers: { dynamicTarget: 'RESPONSIBLE_PERSON' };
  level2Receivers: { dynamicTarget: 'DEPT_LEADER'; extraUserIds?: number[] };
  level3Receivers: { roleCodes: string[] };   // 默认 ['R4', 'R1']
}

// ===== 响应 =====
interface AlertRuleVO extends AlertRuleSaveReq {
  id: number;
  enableCondition?: string;              // 占位规则说明（如"待 04 竞品管理上线"）
}

interface AlertHitStatVO {
  ruleCode: string;
  ruleName: string;
  alertCount: number;
  responseRate: number;
  falseAlarmCount: number;
  lastHitAt?: string;
}
```

### 4. 交互流程

**页面加载**：
1. `GET /admin-api/ims/alert/rule/list`（默认分页）；顶部统计卡（首批启用 4 / 占位数，含 FIN_COST_MISS 占位）由列表聚合。
2. 占位规则（DISABLED + enableCondition 非空）：状态 Tag 带锁图标 + Tooltip 显示 enableCondition；操作列仅"查看"（抽屉只读），无启用入口、无手动检查（服务端对占位规则返回 1165 段错误兜底）。

**核心操作**：
- **编辑规则**（R1/R4 业务/R3 财务）：行操作"编辑" → 规则编辑抽屉（§7.1）；ruleCode 只读（口径不可改）；**阈值修改即时热更新**（ALR-C-R2），保存成功 toast "阈值已即时生效（热更新）"。
- **注册规则**：入口文案注明"规则由各模块模块侧注册"（本页提供统一注册表单，POST `/alert/rule`）；triggerConfig DSL 非法返回 1009 → 抽屉触发条件区红字提示具体非法原因。
- **启停规则**（仅 R1）：启用/停用 Switch → `PUT /alert/rule/{id}/enable`；ConfirmDialog 文案"停用后规则停止检查与推送，历史预警数据保留（ALR-C-R3：规则仅停用不删除）"。
- **手动检查**（R1/R3/R4）：行操作"手动检查"（仅 ENABLED + SCHEDULED）→ ConfirmDialog → `POST /alert/check/run/{ruleId}` → toast `已创建检查任务（{ruleCode}）`，结果走统一去重合并流程（ALR-P-R3）。
- **命中统计**：底部按钮 → 命中统计弹窗（§7.3）。
- **升级链路配置**（仅 R1）：底部按钮 → 升级链路配置抽屉（§7.2）。

### 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| sourceModule | Select | string | 全部/06 证件/08 账号/10 直播/16 采集/11 财务/…（枚举来自规则数据） |
| level | Select | AlertLevel | 全部/L1/L2/L3 |
| enabled | Select | EnableStatus | 全部（默认）/已启用/未启用 |

### 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 规则编码 | ruleCode | code 样式 |
| 规则名称 | ruleName | 文本 |
| 来源模块 | sourceModule | Tag（模块名映射） |
| 触发方式 | triggerType | EVENT=蓝"事件驱动" / SCHEDULED=青"定时检查"，SCHEDULED 附 cron Tooltip |
| 触发条件摘要 | triggerConfig | DSL 摘要（如 `hours_since_approve > 48`）+ Tooltip 完整 JSON |
| 级别 | level | StatusTag：L1 蓝"提示"/L2 橙"警告"/L3 红"严重" |
| 通知对象 | notifyTargets | `角色 R2,R4 · 责任人` 摘要 |
| 状态 | enabled | ENABLED 绿 / DISABLED 灰；占位规则锁图标 + enableCondition Tooltip |
| 操作 | — | 编辑 / 手动检查（ENABLED+SCHEDULED）/ 停用（R1）；占位规则仅"查看" |

### 7. 抽屉/弹窗规格

### 7.1 规则编辑抽屉（Drawer，右滑 720px，含注册/编辑/查看三态）

- **布局**：
  1. **基本信息**：规则编码（注册可填/编辑只读）、规则名称、来源模块 Select、级别 Radio（L1/L2/L3）、触发方式 Radio（EVENT/SCHEDULED）。
  2. **触发条件（DSL 参数化编辑器）**：表单化三段——数据源 source Input（如 `ims_fin_cost`）+ 条件行 [field Input | op Select（GT/GTE/LT/LTE/EQ/NEQ）| value InputNumber]，多条件 AND 组合；底部"DSL 预览"折叠面板显示生成 JSON（专家核对）。占位规则查看态只显示 JSON 只读。
  3. **检查周期**（SCHEDULED）：cron Input + 下一次执行时间预览（前端 cron 解析，解析失败黄字提示但不阻塞——服务端校验兜底）。
  4. **通知对象**：角色多选 Checkbox（R2/R3/R4…）+ 具体人人员选择 + 动态目标 Radio（RESPONSIBLE_PERSON 责任人 / DEPT_LEADER 部门负责人 / NONE）。
- 保存 → `POST /alert/rule`（注册）或 `PUT /alert/rule/{id}`（编辑，热更新 toast）。
- **1009 DSL 非法**：触发条件区红字（服务端返回 msg 定位字段）。

### 7.2 升级链路配置抽屉（Drawer，右滑 640px，仅 R1）

- **布局**（对应 AlertEscalationConfigReq）：
  1. 升级时限：一级 InputNumber 分钟（默认 30）+ 二级 InputNumber 分钟（默认 60），附注 "自上一级计（BR-113）"。
  2. 严重级起跳：severeStartLevel Radio（2=从二级起跳【默认，ALR-E-R2】/ 3=从三级）。
  3. 各级接收人：一级=责任人（固定只读）；二级=部门负责人（固定）+ 附加人员选择；三级=角色多选（默认 R4 运营总监 + R1 系统管理员）。
  4. 底部提示：升级通知走钉钉强提醒（DING 或短信，ALR-E-R4）。
- 保存 → `PUT /admin-api/ims/alert/escalate/config` → toast "升级链路已更新"。

### 7.3 命中统计弹窗（Modal，800px，可切抽屉）

- 日期范围 RangePicker（默认近 30 天）→ `GET /alert/rule/hit-stats`。
- 表格：[规则 | 预警数 | 响应率 | 误报数 | 最近命中时间]；响应率 < 90% 橙色（BR-112 目标）。
- 误报数 ≥5 的行附橙色标记 + Tooltip "连续误报 ≥5 次建议复核阈值（ALR-S-R3）"。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 表单红字 |
| 1009（归并本域使用） | triggerConfig DSL 非法 | 抽屉触发条件区红字 + DSL 预览区标错 |
| 1165 | 规则编码已存在（注册时） | 编码字段红字 |
| 占位规则启用/手动检查 | 服务端拒绝 | toast 显示 enableCondition 说明 |
| 网络失败 | — | 全局兜底 |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-113（三级升级 30/60 分钟，L3 二级起跳） | 升级链路配置抽屉（默认值 + 提示文案） |
| BR-114（去重合并 30 分钟窗口） | 规则编辑抽屉合并窗口配置项（见 ALR-S-R1，随 triggerConfig 扩展字段 mergeWindowMinutes 5~60） |
| BR-118（成本 48h 未录入预警） | FIN_COST_MISS 规则行（注册置 DISABLED，随 11 财务上线（V3 第 33 周后）启用） |
| ALR-C-R1（首批 4 条子集，其余占位；FIN_COST_MISS 移至 V3 11 财务上线（第 33 周后）启用） | 顶部统计卡 + 占位规则锁态 |
| ALR-C-R2（阈值热更新） | 编辑保存 toast |
| ALR-C-R3（仅停用不删除） | 停用 ConfirmDialog 文案 |
| ALR-S-R1（合并窗口可配 5~60） | 规则编辑抽屉合并窗口 InputNumber（min 5 max 60，默认 30） |
| ALR-S-R3（误报 ≥5 建议复核阈值） | 命中统计弹窗标记 |

---

## P2 预警记录与处置（ALERT-002 + 工作台卡片）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/alert/records`（菜单：预警中心 → 预警记录）；工作台卡片"我的预警"（目标人视角） |
| 页面级别 | 二级 |
| 前置依赖 | 规则已启用并产生命中记录 |
| 权限 | 查看：R1/R2/R3/R4（全局）/目标人（本人相关，服务端过滤）；响应处置：预警目标人、R4 |
| 用户 | 管理层全局视角 + 目标人本人处置 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 预警记录    [送达率卡: 99.6% ✓达标(>99%)  失败 2 条 ▸失败明细]            │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [规则 Select:全部/各规则][级别 Select:全部/L1/L2/L3]      │
│  [响应状态 Select:全部/未响应/已确认/已处理/误报][推送状态 Select:        │
│  全部/待推送/已送达/部分失败/失败][日期 RangePicker] [搜索][重置]          │
├──────────────────────────────────────────────────────────────────────────┤
│ 记录表格                                                     共 {n} 条  │
│ ┌──────────┬────────┬──────┬────────────┬──────┬────────────┬─────────┐  │
│ │预警编号   │规则     │级别  │ 内容(截断)  │合并  │ 推送状态    │响应状态 │  │
│ │          │        │      │            │计数  │(通道回执)  │        │  │
│ ├──────────┼────────┼──────┼────────────┼──────┼────────────┼─────────┤  │
│ │AL20250526│FIN_COST│ L2 ⚠ │成本48h未录入│ ×3   │已送达       │未响应🔴 │  │
│ │…042      │_MISS   │      │(IMSS2025…042│     │钉钉✓工作台✓│ 32min  │  │
│ │          │        │      │)           │     │            │(升级中)│  │
│ └──────────┴────────┴──────┴────────────┴──────┴────────────┴─────────┘  │
│ 行点击/操作"详情" → 预警详情抽屉（含来源单据跳转 + 升级时间轴 + 响应）   │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
└──────────────────────────────────────────────────────────────────────────┘
工作台"我的预警"卡片（目标人 H5/Web 同构）：
┌────────────────────────────┐
│ 🔔 我的预警 (3 未读)        │ → GET /alert/check/my-alerts
│ ┌────────────────────────┐ │
│ │ L2 成本48h未录入  32min │ │ 级别Tag+内容+未响应时长
│ │ → 立即响应 → 来源单据   │ │
│ └────────────────────────┘ │
└────────────────────────────┘
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
/** 预警事件响应状态 */
type AlertEventStatus = 'OPEN' | 'CONFIRMED' | 'RESOLVED' | 'FALSE_ALARM';
/** 推送状态（契约内联） */
type AlertPushStatus = 'PENDING' | 'DELIVERED' | 'PARTIAL_FAILED' | 'FAILED';
/** 推送通道（契约内联） */
type AlertPushChannel = 'WORKBENCH' | 'DINGTALK' | 'SMS';

// ===== 请求 =====
interface AlertRecordQueryReq extends PageParam {
  ruleCode?: string;
  level?: AlertLevel;
  responseStatus?: AlertEventStatus;
  pushStatus?: AlertPushStatus;
  dateRange?: [string, string];
}

interface AlertRespondReq {
  response: 'CONFIRM' | 'RESOLVE' | 'FALSE_ALARM';
  handleRemark: string;                  // 处理说明（必填）
  /** FALSE_ALARM 时反馈误报原因 */
  falseAlarmReason?: string;
}

// ===== 响应 =====
interface AlertEventVO {
  id: number;
  alertNo: string;                       // AL+日期+流水
  ruleId: number;
  ruleCode: string;
  ruleName: string;
  /** 来源单据引用（点击直达） */
  sourceRefType: string;                 // CERT / ACCOUNT / SESSION / COST …
  sourceRefId: string;
  level: AlertLevel;
  content: string;
  /** BR-114：去重合并 = 规则编码 + 对象标识，30 分钟窗口计数累加 */
  dedupKey: string;
  mergedCount: number;                   // 合并累计命中次数
  notifyTargetUserIds: number[];
  pushStatus: AlertPushStatus;
  pushChannels: Array<{ channel: AlertPushChannel; success: boolean; receiptAt?: string }>;
  responseStatus: AlertEventStatus;
  respondedBy?: number;
  respondedAt?: string;
  occurredAt: string;
}

interface AlertDetailVO extends AlertEventVO {
  sourceJumpUrl: string;                 // 来源单据跳转
  escalationTimeline: Array<{
    level: 1 | 2 | 3;
    escalatedTo: number[];
    escalatedAt: string;
    elapsedMinutes: number;
  }>;
}

interface AlertDeliveryStatsVO {
  totalDelivered: number;
  totalShould: number;
  deliveryRate: number;                  // BR-111 目标 > 99%
  failedAlerts: Array<{ alertNo: string; failedChannel: string; retryCount: number }>;
  target: number;
}
```

### 4. 交互流程

**页面加载**：
1. 并行 `GET /alert/check/records`（分页）+ `GET /alert/check/delivery-stats`（送达率卡，默认近 7 天）。
2. 送达率卡：>99% 绿 ✓ "达标（BR-111 >99%）"；≤99% 红 ✗ + [失败明细] 展开 failedAlerts（alertNo / 失败通道 / 补发次数；送达失败自动补发 1 次、仍失败告警管理员——ALR-P-R2 文案）。

**核心操作**：
- **预警详情**：行点击或"详情" → `GET /alert/check/{alertNo}` → 详情抽屉（§7.1，DetailDrawer 内联优先）。
- **响应处置**（目标人/R4）：详情抽屉内 [立即响应] → 响应弹窗（§7.2）→ `PUT /alert/check/{alertNo}/respond`：
  - CONFIRM → responseStatus = CONFIRMED（升级停止）；
  - RESOLVE → RESOLVED（升级停止）；
  - FALSE_ALARM → FALSE_ALARM（误报反馈至规则阈值复核链路，ALR-S-R3）。
  - 返回 `{alertNo, responseStatus, escalationStopped}`；escalationStopped=true → toast "响应成功，后续升级已停止（ALR-E-R3）"。
- **来源单据跳转**：详情抽屉 [跳转来源单据] → `sourceJumpUrl`（CERT 证件档案 / ACCOUNT 账号详情 / SESSION 直播场次 / COST 成本录入单——复用 V1/V2 各模块既有详情页路由）。
- **工作台卡片**：目标人登录 → `GET /alert/check/my-alerts`（含 isUnread）；未读红点；点击卡片项直接打开详情抽屉（复用）；30 秒轮询未读数（有 OPEN 时）。
- **合并计数展示**：mergedCount > 1 的行显示 `×{n}` 徽标 Tooltip "同规则+同对象 30 分钟窗口内合并 {n} 次，计数累加（BR-114）"。

### 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| ruleCode | Select | string | 全部（默认）/规则列表 |
| level | Select | AlertLevel | 全部/L1/L2/L3 |
| responseStatus | Select | AlertEventStatus | 全部/未响应/已确认/已处理/误报 |
| pushStatus | Select | AlertPushStatus | 全部/待推送/已送达/部分失败/失败 |
| dateRange | RangePicker | [string,string] | 发生时间范围 |

### 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 预警编号 | alertNo | code 样式（AL+日期+流水） |
| 规则 | ruleCode/ruleName | `FIN_COST_MISS 成本未录入` 两行式 |
| 级别 | level | L1 蓝/L2 橙/L3 红（附图标 ⚠/⛔） |
| 内容 | content | 截断 40 字 + Tooltip；括号内 sourceRefId 高亮 |
| 合并计数 | mergedCount | >1 → `×{n}` 徽标 + Tooltip（BR-114） |
| 来源单据 | sourceRefType | Tag + [跳转] 链接图标 |
| 发生时间 | occurredAt | yyyy-MM-dd HH:mm |
| 推送状态 | pushStatus | StatusTag；Hover 展开通道回执列表（钉钉✓/工作台✓/短信✗ + receiptAt） |
| 响应状态 | responseStatus | OPEN 红"未响应"（附未响应时长，超 30min 橙"升级中"）/CONFIRMED 橙/RESOLVED 绿/FALSE_ALARM 灰 |
| 操作 | — | 详情 / 响应（OPEN 且为目标人/R4） |

### 7. 抽屉/弹窗规格

### 7.1 预警详情抽屉（DetailDrawer，右滑 720px）

- **结构**：
  1. **头部**：alertNo + 级别大 Tag + 响应状态 Tag + dedupKey/合并计数（mergedCount，BR-114）。
  2. **内容区**（Descriptions）：规则、来源单据（sourceRefType+sourceRefId + [跳转来源单据] 主按钮 sourceJumpUrl）、预警内容全文、发生时间、通知目标人（notifyTargetUserIds 姓名串）。
  3. **推送回执区**：pushChannels 表 [通道（工作台/钉钉/短信）| 状态 ✓/✗ | 回执时间]；PARTIAL_FAILED/FAILED 附红色"已自动补发 1 次（ALR-P-R2）"。
  4. **升级时间轴区**（有 escalationTimeline 时显示）：纵向 Timeline——每节点 `二级 · 部门负责人 · 距产生 32 分钟`（escalatedAt/elapsedMinutes），当前等待节点高亮 `下一级升级：{nextEscalateAt}`；响应后终止线标记"响应停止（ALR-E-R3）"。L3 预警首节点直接显示二级（ALR-E-R2 二级起跳）。
  5. **响应记录**：respondedBy/respondedAt/响应结果（终态时）。
  6. **底部操作**（OPEN + 目标人/R4）：[立即响应]；终态（RESOLVED/FALSE_ALARM/CONFIRMED 已流转）整抽屉只读。
- 数据来源：`GET /alert/check/{alertNo}`（含 timeline 与 jumpUrl）。

### 7.2 响应弹窗（Modal，520px）

- 三选一 Radio：CONFIRM 确认 / RESOLVE 处理完成 / FALSE_ALARM 误报。
- 处理说明 handleRemark TextArea（**必填**）。
- 选 FALSE_ALARM → 追加"误报原因" Input（falseAlarmReason，选填但推荐；附提示"误报反馈将用于规则阈值复核，连续误报 ≥5 次建议管理员复核阈值（ALR-S-R3）"）。
- 提交 → `PUT /alert/check/{alertNo}/respond` → 成功关闭弹窗刷新；1166/1167 拦截见 §8。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | handleRemark 必填 | 弹窗红字 + 禁用提交（预校验） |
| 1166 | 非预警目标人无权响应 | toast "仅预警目标人或运营总监可响应" |
| 1167 | 预警已终态不可重复响应 | toast + 详情抽屉刷新为只读态 |
| 送达失败告警 | ALR-P-R2 兜底 | 送达率卡失败明细（管理员视角红条） |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-111（送达率 >99%，补发 1 次） | 送达率卡 + 失败明细 + 补发文案 |
| BR-113（升级链展示） | 详情抽屉升级时间轴（30/60 分钟节点） |
| BR-114（去重合并 30 分钟计数累加） | mergedCount 徽标 + dedupKey 展示 |
| ALR-P-R1（严重级 1 分钟内送达，钉钉>短信） | 推送回执区通道排序与说明文案 |
| ALR-P-R2（失败补发 1 次告警管理员） | 送达率卡失败明细 |
| ALR-P-R3（去重合并先于推送） | 详情抽屉合并信息在推送区之前展示（信息架构） |
| ALR-E-R3（响应停止升级） | respond 返回 escalationStopped toast + 时间轴终止线 |
| ALR-S-R2（合并预警更新计数与最新时间） | mergedCount 行 + occurredAt 更新说明 |
| ALR-S-R3（误报反馈复核） | 响应弹窗 FALSE_ALARM 分支文案 |

---

## P3 升级中心（ALERT-003）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/alert/escalate`（菜单：预警中心 → 升级中心） |
| 页面级别 | 二级（两区：待升级清单 + 响应率统计；升级链路配置入口在 P1） |
| 前置依赖 | 存在 OPEN 状态预警进入升级链 |
| 权限 | 查看：R1/R4（全量）/各级接收人（本人相关）；升级链路配置：R1（入口在 P1 §7.2）；响应率：R1/R2/R3/R4/R9 |
| 用户 | R1 系统管理员（链路运维）/ R4 运营总监（三级接收人）/ 各级接收人 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 升级中心   [响应率卡: 93.2% ✓达标(>90%)  平均响应 14 分钟  分级别:       │
│            L1 95% / L2 91% / L3 89% ⚠]                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 待升级 / 升级中预警（GET /alert/escalate/pending）                      │
│ QueryBar(单行): [当前升级级别 Select:全部/一级/二级/三级] [搜索][重置]     │
│ ┌──────────┬──────┬────────────┬──────────────┬────────────┬─────────┐   │
│ │预警编号   │级别  │ 规则        │当前升级级别  │下一级升级于 │ 操作     │   │
│ ├──────────┼──────┼────────────┼──────────────┼────────────┼─────────┤   │
│ │AL2025…042│ L2 ⚠ │FIN_COST_   │ 二级(部门负责│ 14:32(再 28│ 详情     │   │
│ │          │      │MISS        │ 人已通知)    │ min→三级)  │         │   │
│ │AL2025…031│ L3 ⛔ │COLLECT_    │ 三级(R4+R1已 │ —(终级等待 │ 详情     │   │
│ │          │      │ERROR       │ 通知)        │ 响应)      │         │   │
│ └──────────┴──────┴────────────┴──────────────┴────────────┴─────────┘   │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 响应率趋势图（折线，按日）   [日期范围 RangePicker]                      │
│ L1/L2/L3 三线 + 目标线 90%（BR-112 虚线）                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3. TypeScript 类型定义

```typescript
// 复用 P2 AlertEventVO / AlertLevel / AlertEventStatus；契约补充：

interface AlertPendingVO extends AlertEventVO {
  currentLevel: 1 | 2 | 3;
  nextEscalateAt: string;
}

interface AlertResponseStatsVO {
  totalAlerts: number;
  respondedInTime: number;
  responseRate: number;                  // BR-112 目标 > 90%
  avgResponseMinutes: number;
  target: number;
  byLevel: Array<{ level: AlertLevel; responseRate: number }>;
}

interface AlertResponseTrendVO {
  statDate: string;
  responseRate: number;
  alertCount: number;
}

// 升级时间轴（复用 GET /alert/escalate/timeline/{alertNo}）
interface AlertEscalationTimelineResp {
  alertNo: string;
  alertLevel: AlertLevel;
  occurredAt: string;
  timeline: Array<{
    escalationLevel: 1 | 2 | 3;
    escalatedTo: Array<{ userId: number; userName: string; roleLabel: string }>;
    escalatedAt: string;
    elapsedMinutes: number;              // 距预警产生时长
  }>;
  currentLevel: 1 | 2 | 3 | null;
  responseStatus: AlertEventStatus;
}
```

### 4. 交互流程

**页面加载**：
1. 并行 `GET /alert/escalate/pending`（分页）+ `GET /alert/escalate/response-stats`（默认近 30 天）+ `GET /alert/stats/response-rate`（趋势图）。
2. 响应率卡：>90% 绿 ✓ "达标（BR-112 >90%）"；≤90% 红 ✗；分级别 byLevel 中任一 <90% 单独橙色警示（L3 优先展示）。

**核心操作**：
- **升级详情**：行操作"详情" → `GET /alert/escalate/timeline/{alertNo}` → 升级时间轴抽屉（§7.1，含接收人姓名与角色标签）。
- **链路干预**：详情内可跳转 P2 预警详情抽屉（复用响应操作）；R4 可代响应（1166 逻辑对 R4 放行）。
- **待升级刷新**：pending 列表 30 秒轮询（存在"下一级升级于 X 分钟内"的行时），倒计时列每分钟更新。
- **响应率趋势**：日期范围切换重新拉取；三级别折线 + 90% 目标虚线。

### 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| currentLevel | Select | 1\|2\|3 | 全部（默认）/一级/二级/三级 |
| 日期范围（统计区） | RangePicker | [string,string] | 响应率卡与趋势图共用，默认近 30 天 |

### 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 预警编号 | alertNo | code 样式，点击开时间轴抽屉 |
| 级别 | level | L1 蓝/L2 橙/L3 红 |
| 规则 | ruleCode/ruleName | 两行式 |
| 当前升级级别 | currentLevel | 一级=责任人（蓝）/二级=部门负责人（橙）/三级=R4+R1（红）；附接收人摘要 Tooltip |
| 下一级升级于 | nextEscalateAt | 倒计时 `14:32（再 28 min → 三级）`；三级终态显示 "终级等待响应" |
| 响应状态 | responseStatus | OPEN 红（升级链持续中） |
| 操作 | — | 详情（跳 P2 详情抽屉复用响应操作） |

### 7. 抽屉/弹窗规格

### 7.1 升级时间轴抽屉（Drawer，右滑 640px）

- 头部：alertNo + 预警级别 Tag + 响应状态 + occurredAt。
- **纵向 Timeline**（每节点）：
  - `一级 · 责任人 · 产生即通知 · 张三（直播运营）`（elapsedMinutes=0）
  - `二级 · 部门负责人 · 距产生 {elapsedMinutes} 分钟 · 李四（部门负责人）`（>30 分钟触发，BR-113）
  - `三级 · 运营总监+系统管理员 · 距产生 {elapsedMinutes} 分钟 · 王五（R4）、系统管理员（R1）`
  - L3 预警：一级节点显示"跳过（严重级直接二级起跳，ALR-E-R2）"灰色虚节点。
  - 当前等待节点呼吸高亮 + `下一级升级于 {nextEscalateAt}`。
  - 已响应：末尾绿色终止节点 "已响应 · 升级链停止（ALR-E-R3）· {respondedAt}"。
- 底部：[查看预警详情] → 跳 P2 详情抽屉（响应操作复用）。
- 数据：`GET /alert/escalate/timeline/{alertNo}`（escalatedTo 含 userName/roleLabel）。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 权限（非接收人/非 R1/R4） | pending/时间轴 403 | 空态 + "仅升级链路接收人与管理员可查看" |
| 轮询失败 | 30 秒轮询 | 静默重试，连续 3 次失败提示手动刷新 |
| 时间轴为空 | 预警未进入升级链（已响应） | 抽屉仅显示 "0 分钟内已响应，未进入升级" |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-112（响应率 >90% 时限内） | 响应率卡 + 分级别 + 趋势目标线 |
| BR-113（30/60 分钟三级升级） | pending 倒计时列 + 时间轴节点（elapsedMinutes） |
| ALR-E-R2（L3 二级起跳） | pending L3 行首节点即二级；时间轴虚节点"跳过一级" |
| ALR-E-R3（响应停止升级） | 时间轴绿色终止节点 |
| ALR-E-R4（升级 DING 强提醒） | 时间轴节点附钉钉强提醒图标 + 说明文案 |

---

## P4 预警统计看板（ALERT-004）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/alert/stats`（菜单：预警中心 → 统计看板） |
| 页面级别 | 二级（聚合看板：总览卡 + 排行 + 合并记录 + 周报） |
| 前置依赖 | 预警运行产生统计数据（每日汇总，V2-A1 集群化调度） |
| 权限 | 查看：R1/R2/R3/R4/R9（全量）；周报：R1/R2/R3/R4 |
| 用户 | 管理层（健康度监控）/ 周报消费者 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 预警统计看板    [日期范围 RangePicker: 默认近30天]                         │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 健康度四指标卡（GET /alert/stats/overview）                             │
│ ┌─────────┬─────────┬─────────┬─────────┐                               │
│ │ 送达率   │ 响应率   │ 误报率   │ 升级率   │  + 预警总量 / 级别分布      │
│ │ 99.6% ✓ │ 93.2% ✓ │  2.1%   │  6.8%   │    1,284 条 L1:800 L2:412  │
│ │(>99%)   │(>90%)   │         │         │    L3:72                    │
│ └─────────┴─────────┴─────────┴─────────┘                               │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 规则命中排行（GET /alert/stats/rule-rank, TopN=10）                     │
│ [排名|规则|预警数|合并节省数|响应率]  合并节省数 = 被去重合并掉的重复推送   │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 合并记录（GET /alert/stats/merge-logs，分页表）                         │
│ QueryBar: [规则 Select][日期范围] [合并主预警编号|被合并编号数|窗口分钟|  │
│  主预警时间|最近合并时间]                                                 │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 预警周报（GET /alert/stats/weekly-report）                              │
│ [周期切换: 2025-W21 ▾]  周区间 05-19~05-25（波浪号规格同全局周格式）       │
│ 摘要: 总量 / Top规则 / 响应率 / 送达率 / 升级预警清单 / 优化建议          │
│ 周报由 V2-A1 定时推送管理层（本页为在线查看）                              │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3. TypeScript 类型定义

```typescript
// 复用 AlertLevel / EnableStatus；契约补充：

interface AlertOverviewVO {
  totalAlertCount: number;
  byLevel: Record<AlertLevel, number>;
  responseRate: number;
  deliveryRate: number;
  falseAlarmRate: number;
  escalateRate: number;
  avgResponseMinutes: number;
}

interface AlertRuleRankVO {
  rank: number;
  ruleCode: string;
  ruleName: string;
  alertCount: number;
  mergedSavingsCount: number;             // 被去重合并掉的重复推送数（BR-114 节省效果）
  responseRate: number;
}

interface AlertMergeLogVO {
  id: number;
  masterAlertNo: string;
  mergedAlertNos: string[];
  mergedCount: number;
  mergeWindowMinutes: number;             // 默认 30，按规则可配 5~60（ALR-S-R1）
  masterOccurredAt: string;
  lastMergedAt: string;
}

interface AlertWeeklyReportVO {
  weekRange: [string, string];
  totalAlerts: number;
  topRules: Array<{ ruleCode: string; alertCount: number }>;
  responseRate: number;
  deliveryRate: number;
  escalatedAlerts: Array<{ alertNo: string; level: AlertLevel; currentLevel: 1 | 2 | 3 }>;
  suggestions: string[];
}
```

### 4. 交互流程

**页面加载**：日期范围切换 → 并行 `GET /alert/stats/overview` + `GET /alert/stats/rule-rank`（topN=10）+ `GET /alert/stats/merge-logs`（分页）。周报区默认当前自然周 `GET /alert/stats/weekly-report`（weekStart 可切历史周）。

**核心交互**：
- **健康度四指标卡**：送达率（BR-111 >99% 达标线）、响应率（BR-112 >90%）、误报率（无硬阈值，>5% 橙色提示结合 ALR-S-R3）、升级率（无硬阈值，异常升高提示检查响应流程）。
- **级别分布**：L1/L2/L3 三段横向条形图；L3 数量可点击 → 跳 P2 预警记录预置 level=L3 筛选。
- **排行联动**：规则行点击 → 跳 P2 预置 ruleCode 筛选；合并节省数列 Tooltip "该规则通过去重合并节省 {n} 次重复推送（BR-114）"。
- **合并记录**：主预警编号点击 → 跳 P2 详情抽屉；mergedAlertNos 折叠展开完整编号列表。
- **周报**：周期 Select（近 8 周）；escalatedAlerts 行点击跳 P3 升级时间轴；suggestions 列表只读展示（引擎建议文案）。

### 5. 查询条件表

| 区域 | 字段 | 组件 | 说明 |
|------|------|------|------|
| 总览/排行/合并 | dateRange | RangePicker | 默认近 30 天 |
| 合并记录 | ruleCode | Select | 全部（默认）/规则列表 |
| 周报 | weekStart | WeekPicker | 周起始日，默认本周 |

### 6. 表格列定义

**规则命中排行**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 排名 | rank | 1~10，前三徽标 |
| 规则 | ruleCode/ruleName | 两行式，可点击联动 P2 |
| 预警数 | alertCount | 数字 |
| 合并节省数 | mergedSavingsCount | 数字 + Tooltip（BR-114 节省说明） |
| 响应率 | responseRate | 百分比；<90% 橙色（BR-112） |

**合并记录**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 主预警编号 | masterAlertNo | code 样式，点击跳 P2 详情 |
| 被合并预警 | mergedAlertNos | `{n} 条` 折叠展开编号列表 |
| 合并次数 | mergedCount | 数字 |
| 合并窗口 | mergeWindowMinutes | `{n} 分钟`（30 默认，5~60 可配） |
| 主预警时间 | masterOccurredAt | yyyy-MM-dd HH:mm |
| 最近合并 | lastMergedAt | yyyy-MM-dd HH:mm |

**周报区**：摘要卡（总量/响应率/送达率）+ Top 规则列表 + 升级预警清单表 [编号|级别|当前升级级别]（行点击跳 P3）+ 优化建议列表。

### 7. 抽屉/弹窗规格

本页无独立抽屉；所有详情跳转复用 P2 预警详情抽屉 / P3 升级时间轴抽屉。

### 8. 错误处理

| 错误码/场景 | 处理 |
|------------|------|
| 1001 参数校验 | 常规红字 |
| 周报无数据（新周期） | 空态 "本周期周报尚未生成（每日汇总，周一推送管理层）" |
| 级别分布点击筛选跳转失败 | P2 页面容错为全量列表 |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-111（送达率 >99%） | 健康度卡达标线 |
| BR-112（响应率 >90%） | 健康度卡 + 排行响应率列 + 周报摘要 |
| BR-114（去重合并 30 分钟） | 合并记录表（窗口列）+ 排行"合并节省数" |
| ALR-S-R1（窗口 5~60 可配） | 合并记录窗口列展示（配置入口在 P1 规则编辑抽屉） |
| ALR-S-R2（合并更新计数与时间） | mergedCount + lastMergedAt 列 |
| ALR-S-R3（误报反馈复核） | 误报率卡 >5% 提示 |
| V2-A1（统计与周报集群化调度） | 周报区"每日汇总/周一推送"说明 |

---

## 附录 A：模块级约定

1. **三级升级口径（BR-113）**：一级责任人 30 分钟 → 二级部门负责人 60 分钟（**自上一级计**）→ 三级 R4+R1；L3 严重级直接从二级起跳（ALR-E-R2）；任一级响应即停止（ALR-E-R3）；升级通知走钉钉强提醒 DING/短信（ALR-E-R4）。时限/接收人配置仅 R1（P1 §7.2 升级链路配置抽屉）。
2. **去重合并口径（BR-114）**：dedupKey = 规则编码 + 对象标识；30 分钟窗口（默认，按规则 5~60 可配 ALR-S-R1）；合并判定先于推送（ALR-P-R3）；合并预警更新计数与最新发生时间（ALR-S-R2）。
3. **送达兜底链（BR-111/ALR-P-R1~R2）**：通道优先级 工作台+钉钉 > 短信兜底；严重级 1 分钟内送达；失败自动补发 1 次，仍失败标记 FAILED 并告警管理员。
4. **规则生命周期**：仅停用不删除（ALR-C-R3，历史预警数据引用不可断）；阈值热更新即时生效（ALR-C-R2）；占位规则（enableCondition 非空）全链路锁态、不可启用/手动检查。
5. **V2 首批规则子集（ALR-C-R1）**：CERT_EXPIRE（06 证件到期，V1 迁移）、ACCT_UNRETURN（08 账号未归还，V1）、LIVE_RISK（10 直播风险，V1 迁移）、COLLECT_ERROR（16 采集异常，V1），共 4 条；FIN_COST_MISS（11 成本 48h 未录入，BR-118）已随 11 财务移入 V3——随 11 财务上线（V3 第 33 周后）启用，当前注册但置 DISABLED。其余注册占位随上游模块上线启用。
6. **枚举纪律**：`AlertLevel = L1/L2/L3`（全局权威，V1 的 INFO/WARN/CRITICAL 已统一）；`AlertEventStatus = OPEN/CONFIRMED/RESOLVED/FALSE_ALARM`；错误码 1009（DSL 非法）为共享规范原码、本域归并使用。
7. **详情内联优先**：预警详情走 DetailDrawer（不跳页），来源单据跳转才离开（sourceJumpUrl 复用 V1/V2 各模块既有详情路由）。
8. **定时任务**：检查引擎/每日汇总/周报推送均 V2-A1 集群化调度（Redisson 锁）；前端"手动检查"为补触发入口，结果走统一去重合并流程。
9. **响应闭环**：CONFIRM/RESOLVE/FALSE_ALARM 三态；误报反馈进入规则阈值复核链路（连续 ≥5 次建议复核，ALR-S-R3）。

## 附录 B：BR / ALR 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-111 | 送达率 > 99%（补发 1 次） | P2 送达率卡、P4 健康度卡 |
| BR-112 | 响应率 > 90% | P3 响应率卡+趋势、P4 健康度卡/排行/周报 |
| BR-113 | 三级升级 30/60 分钟；L3 二级起跳 | P1 升级链路配置、P3 pending 倒计时/时间轴 |
| BR-114 | 去重合并 30 分钟窗口计数累加 | P2 mergedCount、P4 合并记录/合并节省数 |
| BR-118 | 成本 48h 未录入预警 | P1 FIN_COST_MISS 规则行（注册置 DISABLED，随 V3 11 财务上线（第 33 周后）启用） |
| ALR-C-R1 | 首批 4 条子集，其余占位 | P1 统计卡+占位锁态 |
| ALR-C-R2 | 阈值热更新 | P1 编辑 toast |
| ALR-C-R3 | 仅停用不删除 | P1 停用弹窗文案 |
| ALR-P-R1 | 严重级 1 分钟送达 | P2 推送回执区 |
| ALR-P-R2 | 失败补发 1 次告警管理员 | P2 失败明细、P3 |
| ALR-P-R3 | 去重合并先于推送 | P2 详情信息架构 |
| ALR-E-R2 | L3 从二级起跳 | P3 时间轴虚节点 |
| ALR-E-R3 | 响应停止升级 | P2 respond toast、P3 终止节点 |
| ALR-E-R4 | 升级 DING 强提醒 | P3 时间轴图标说明 |
| ALR-S-R1 | 合并窗口 5~60 可配 | P1 规则编辑、P4 窗口列 |
| ALR-S-R2 | 合并更新计数与时间 | P2 mergedCount、P4 lastMergedAt |
| ALR-S-R3 | 误报 ≥5 建议复核阈值 | P1 命中统计标记、P2 误报弹窗、P4 误报率提示 |
| V2-C1~C5 | 规则引擎 JSON DSL（1009） | P1 DSL 参数化编辑器 + 预览 |
| V2-A1 | 检查/汇总/周报集群化调度 | P1 手动检查、P4 周报说明 |

（全文完）
