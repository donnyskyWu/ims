# LIVE - 直播管理 页面规格

> 依据：《IMS第一期PRD-V1.md》5.16~5.19（LIVE-001~004）、《共享技术规范-数据库与API.md》第 7/8 章（场次 ID 编码 7.4.3、V1-E1~E5）、《共享技术规范-分期技术约束.md》。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/live`。  
> **IA 原则（2026-09-29 审计项 3）**：**场次中心**——主对象 = `ims_live_session`（场次 ID），非账号优先或分散台账；LIVE-001～002 的核心操作在 **单场详情 Tab** 完成。

## 0. 模块总览与关键口径

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| **P0 直播场次** | `/ims/live/sessions` | **一级菜单默认页**（场次列表 + 新建登记） | LIVE-001/002/004 聚合入口 |
| **P0-D 场次详情** | `/ims/live/sessions/:sessionCode` 或列表行打开 **90% Drawer** | 详情（Tab 见 §P0-D） | LIVE-001/002 + Football 只读 |
| P2 待录入督办 | `/ims/live/report/pending` | 二级菜单 / 场次列表快捷 Tab | LIVE-002 队列 |
| P3 直播风险告警 | `/ims/live/alarm` | 二级菜单 | LIVE-003 |
| P4 台账导出与补录 | `/ims/live/ledger` | 二级菜单（与 P0 同源查询 + 导出/历史补录） | LIVE-004 |
| P1 开播风控登记（兼容） | `/ims/live/register` | **重定向至 P0**（筛选「待风控/待放行」） | LIVE-001 |

**单场详情 Tab（P0-D，权威布局）**：

| Tab | 内容 | 数据来源 |
|-----|------|----------|
| 基本信息 | 场次 ID、账号、实名人、责任人、设备、计划/实际时间、场次状态 | IMS `ims_live_session` + 资产/人员选择器 |
| 直播数据 | `football_room_id`、同步态、上次拉取、**Football 直播间基本信息 + 计数**（`live_room`）、手工/下播快照对照 | **可读（2026-10-01 拍板 · 2026-10-05 v2.6.34 扩展计数）**：IMS **`GET …/metrics` + `POST …/football-sync`** 直连库表 **`live_room`**（键 = `football_room_id` → `live_room.id`，SSOT 见 API §2.1 / `LiveRoomDO`；房间 + 计数含 `viewer_count` 全部只读）· **不在本期**：单场 GMV/峰值 HTTP（由下播录入承载）· M6 作者×日期聚合 **非** 本 Tab 数据源 |
| 风控登记 | 登记信息编辑（开播前）、五类风控检查、风险分/级别、黄级审批、确认开播/取消 | LIVE-001 API |
| 下播与 GMV | 九项指标录入/草稿/提交、核准、更正单、衍生 ROAS 等 | LIVE-002 API |
| 关联 | 资产反向穿透、告警摘要（链至 P3） | ASSET + LIVE-003 |

> **场次 ID 口径说明**：PRD BR-011 原文为 `LV+yyyyMMdd+4 位流水`，共享技术规范 7.4.3 已定死为 **`IMS+yyyyMMdd(8位)+3 位平台码+4 位当日序列`**（共 19 位，声明后续不可变更）。页面规格以共享技术规范为准，前端校验正则：`^IMS\d{8}[A-Z]{3}\d{4}$`。此差异已反馈主理人。

通用 UI 约定：查询条件一行紧凑排布；**列表 → 场次详情 Drawer（Tab）** 为主路径；金额 DECIMAL(12,2) ¥ 两位小数；状态 tag 语义色；风险三色（绿=正常、黄=需审批、红=禁止）。

---

## P0. 直播场次列表（默认入口）

### 1. 页面概述
- 路由：`/ims/live/sessions`
- 级别：一级菜单默认页
- 依赖：ACCT、ASSET、CERT、AUTH；Football 只读（直播数据 Tab）
- 权限：同 LIVE-001/004 矩阵；R5/R7 服务端过滤本人/团队场次

### 2. ASCII 布局
```
+------------------------------------------------------------------+
| 统计卡: 今日待开播 | 直播中 | 待录入(24h) | 本月 GMV(已核准)        |
| 查询: 场次ID | 账号 | 责任人 | 平台 | 状态 | 风险级别 | 日期      |
|       [查询][重置]  [新建场次登记] [导出]                           |
+------------------------------------------------------------------+
| 表格: 场次ID | 账号 | 主题 | 平台 | 计划开播 | 状态 | 风险 | Football同步态 |
|       | 操作 [详情][风控][下播录入][…] 按状态+角色动态               |
+------------------------------------------------------------------+
| 分页                                                              |
+------------------------------------------------------------------+
行 [详情] → P0-D 场次详情 Drawer（默认 Tab=基本信息）
```

### 3. 表格列（摘要）
同原 P4 台账列，增加 `footballSyncStatus`（未关联/待拉取/已同步/失败/阻塞-无API）与 `entryStatus` 摘要。

### 4. 交互要点
- **新建场次登记**：打开登记 Drawer（复用原 P1 表单）→ 提交 → 自动风控 → 跳转该场次详情 **风控登记 Tab**。
- **详情 Tab「直播数据」（v2.6.34：全部取 `live_room` 只读）**：展示 `football_room_id`（= `live_room.id`）；只读区展示 **直播名称 / 作者（昵称·头像）/ 外部 live_id / 封面 / 状态（1 未开始·2 直播中·3 已结束·4 过期·5 暂停）/ 横竖屏 / 公开·付费·加密 / 开始·结束时间 / 推算时长**，以及 **观看地址 / 回放地址 / 推流地址**；**计数区**展示 **观看人数 `viewer_count` / 点赞数 / 预约人数**；[从 Football 同步] 调用 `POST …/football-sync`（**DB 重读 `live_room`**，不用 Feign/HTTP）。**GMV / 峰值在线 / 涨粉 / 退款 / 投放成本** 由 **下播录入（LIVE-002）** 承载，**本 Tab 不再出现「—」占位**（见 API §2）。未绑 room 时同步按钮提示先绑定。
- 原 P1/P2/P4 独立页能力均可在 P0-D 对应 Tab 完成；P2/P3/P4 保留队列表与导出专用入口。

---

## P0-D. 场次详情（Drawer / 子路由）

### Tab 与操作映射
| Tab | 主要按钮 | API（IMS） |
|-----|----------|------------|
| 基本信息 | 编辑（开播前）、取消 | GET/PUT `/live/register/{sessionCode}` |
| 直播数据 | 绑定 roomId、同步；房间/计数只读（`live_room`） | GET `/live/sessions/{sessionCode}/metrics`；POST `…/football-sync`（`live_room` 只读） |
| 风控登记 | 执行风控、审批、确认开播 | POST `…/risk-check`；PUT `…/approve`；PUT `…/start` |
| 下播与 GMV | 保存草稿、提交、核准、更正 | POST/PUT `/live/report/{sessionCode}` 等 |
| 关联 | 穿透资产、查看告警 | GET ledger 聚合 + `/live/alarm/records?sessionCode=` |

Drawer 宽 90%，可全屏；Footer 按钮随 **当前 Tab + 场次状态** 变化（非仅 Toast）。

---

## P1. 开播风控登记页（LIVE-001 · 兼容路由）

### 1. 页面概述
- 路由路径：`/ims/live/register`
- 页面级别：一级菜单页
- 依赖模块：ACCT 账号台账（关联账号）、ASSET 资产（设备资产多选）、CERT 证件（实名人证件强校验，LIVE-R2）、AUTH 工作台（审批待办）
- 权限矩阵引用（PRD 4.2）：R1 R/W/D（全量）、R4 R/W/D（全量审批）、R5 R/W（本人场次）、R7 R/W（本人场次）、R9 R（全量只读）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [待风控/待放行] [我登记的场次(全部)]                            |
| 查询行: 场次ID | 账号 | 责任人 | 风险级别 | 场次状态 | 日期范围      |
|         [查询] [重置]                        [发开播登记(R5/R7)]    |
+------------------------------------------------------------------+
| 表格: 场次ID | 直播账号 | 实名人 | 责任人 | 主题 | 平台 | 计划开播   |
|       | 风险分 | 风险级别 | 场次状态 | 操作[风控][审批放行][确认开播]|
|       | [编辑][取消][详情]                                        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
登记抽屉(720px):
  直播账号*(搜索,使用中) | 实名人*(人员选择,证件校验) | 责任人*(默认本人)|
  设备资产*(多选,在用资产) | 平台*(字典) | 主题*(≤256字) | 计划开播时间*|
  [提交登记→自动风控]
风控结果抽屉: 检查项清单(5项×通过/异常) + 风险分 + 级别结论 + 分支操作
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface LiveRegisterPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string; accountId?: number;
  responsibleUserId?: number;
  riskLevel?: RiskLevel; sessionStatus?: LiveSessionStatus;
  dateRange?: [string, string];
}
interface LiveRegisterCreateReq {
  accountId: number;                 // 必填，使用中账号
  realnamePersonId: number;          // 必填，实名人
  responsibleUserId: number;         // 必填，责任人（默认当前用户）
  deviceAssetIds: number[];          // 必填，至少 1 项设备资产
  platform: string;                  // 必填，平台码字典（DYS/KS/WX/TM/JD/OTA）
  topic: string;                     // 必填 ≤256 字
  planStartTime: string;             // 必填 ISO 8601
  clientToken: string;               // 幂等（V1-E3：重复请求返回同一 sessionCode）
}
interface LiveRegisterUpdateReq extends Partial<LiveRegisterCreateReq> {
  sessionCode: string;               // 开播前编辑
}
interface LiveApproveReq {
  sessionCode: string;
  approved: boolean;
  opinion: string;                   // 必填 ≤512 字
}
interface LiveCancelReq { sessionCode: string; reason: string; }   // 必填（LIVE-R5）

// 响应类型
interface LiveSessionItem {
  id: number;
  sessionCode: string;               // IMS20250610DYS0001
  accountId: number; accountNickname: string;
  realnamePersonName: string;
  responsibleUserName: string;
  platform: string;
  topic: string;
  planStartTime: string;
  sessionStatus: LiveSessionStatus;
  riskScore: number | null;
  riskLevel: RiskLevel | null;
  approverName: string | null;
  isSupplement: boolean;             // 历史补录标记（P4 联动）
}
interface RiskCheckResult {
  sessionCode: string;
  checks: {
    checkItem: RiskCheckItem;
    checkResult: 'PASS' | 'FAIL' | 'WARN';
    detail: string;                  // 如"证件 2025-07-01 到期，剩余 21 天"
    scoreWeight: number;
  }[];
  riskScore: number;                 // Σ 权重分（BR-014）
  riskLevel: RiskLevel;
  conclusion: string;                // 文案：绿色自动放行/黄色待审批/红色禁止
}

// 枚举类型
type LiveSessionStatus = 'PENDING_RISK_CHECK' | 'APPROVED' | 'LIVE' | 'ENDED' | 'CANCELLED';
// 待风控 / 已放行 / 直播中 / 已下播 / 已取消（全局规范第 4 章权威枚举）
type RiskLevel = 'GREEN' | 'YELLOW' | 'RED';     // <40 / 40~69 / ≥70（BR-014）
type RiskCheckItem = 'CERT_VALID' | 'ACCOUNT_STATUS' | 'BALANCE' | 'BLACKLIST' | 'DEVICE_OWNER';
// 证件有效性/账号状态/话费余额/黑名单词/设备归属（与 LIVE API 契约 3.1.2 RiskCheckItemVO.checkItem 大写值域一致）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /live/register/list`（R5/R7 服务端过滤本人场次）；失败重试。

#### 4.2 核心操作流程
**A. 发开播登记（R5/R7）**
1. [发开播登记] → 抽屉填写：账号选择器（使用中，显示实名人/余额提示）、实名人选择（选择后前端即调证件状态预检——证件锁定/过期直接红字警示，仍可提交但风控必判红，LIVE-R2）、设备资产多选（在用资产搜索）、平台（字典，影响场次 ID 平台码）、主题、计划开播时间；
2. 提交（clientToken 防重，V1-E3）→ 服务端生成场次 ID（V1-E1/E2，前端只读回显）→ 状态"待风控"；
3. 提交即自动执行风控检查 → 直接展示风控结果抽屉（见 B）。

**B. 风控结果与放行分支（BR-014）**
1. 风控结果抽屉：5 项检查逐条（证件有效性/账号状态/话费余额/黑名单词/设备归属），FAIL 红、WARN 黄、PASS 绿；
2. 风险分与级别大字展示，结论文案分支：
   - **绿色（<40）**：自动放行 → 状态"已放行"，提示"可直接确认开播"；
   - **黄色（40~69）**：生成审批待办推送运营总监（R4），本页状态"待风控"→ 审批；
   - **红色（≥70）**：禁止开播，抽屉红色结论"请整改后重新登记"，[重新登记] 按钮（复用登记抽屉，场场次 ID 不变——整改重跑风控，LIVE-R1：未放行不可开播）。
3. 场次 ID 提交后回显并锁定只读（BR-011/LIVE-R4：生成后不可变更）。

**C. 黄级审批放行（R4）**
1. R4 从工作台待办进入 → 行 [审批放行] → 审批抽屉（风控结果只读 + 审批意见必填）→ [通过放行]/[拒绝整改]；
2. 通过 → 状态"已放行"；拒绝 → 状态回"待风控"附意见，责任人收到整改通知。

**D. 确认开播（R5/R7 本人，状态=已放行）**
1. 行 [确认开播] → `PUT /live/register/{sessionCode}/start` → 状态"直播中"；
2. 确认后 LIVE-003 告警监控自动开启（服务端）。

**E. 编辑与取消（开播前）**
1. [编辑]（状态 ∈ 待风控/已放行，开播前，R5 本人/R4）：复用登记抽屉回填，保存重跑风控；
2. [取消]：必填取消原因（LIVE-R5 留痕不删除）→ 状态"已取消"。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 19 位场次 ID 精确 |
| accountId | AccountSelect | 否 | 空 | 直播账号 |
| responsibleUserId | PersonSelect | 否 | 空 | 责任人 |
| riskLevel | Select | 否 | 空 | 绿/黄/红 |
| sessionStatus | Select | 否 | 空 | 待风控/已放行/直播中/已下播/已取消 |
| dateRange | DateRangePicker | 否 | 今日 | 计划开播时间范围 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次 ID | 190 | — | 等宽字体；补录场次加"补录"灰 tag |
| accountNickname | 直播账号 | 140 | — | — |
| realnamePersonName | 实名人 | 100 | — | 证件异常时红色 |
| responsibleUserName | 责任人 | 100 | — | — |
| topic | 主题 | 自适应 | — | 省略 + tooltip |
| platform | 平台 | 80 | — | 平台码字典翻译 |
| planStartTime | 计划开播 | 150 | ✓ | yyyy-MM-dd HH:mm |
| riskScore | 风险分 | 80 | ✓ | 数字；null 显示"—"（待风控） |
| riskLevel | 风险级别 | 90 | — | tag：绿(绿)/黄(黄)/红(红) |
| sessionStatus | 场次状态 | 100 | — | tag：待风控(蓝)/已放行(青)/直播中(绿)/已下播(灰)/已取消(灰红) |
| actions | 操作 | 260 | — | [风控][审批放行][确认开播][编辑][取消][详情] 按状态+角色动态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 开播登记抽屉 | Drawer 720px | accountId 必填（使用中）；realnamePersonId 必填（选择后证件预检提示）；responsibleUserId 必填默认本人；deviceAssetIds 必填 ≥1；platform 必选；topic 必填 ≤256 字；planStartTime 必填（须晚于当前时间）；clientToken 防重；提交后场次 ID 只读回显 |
| 风控结果抽屉 | Drawer 720px | 只读：5 项检查清单 + 风险分/级别 + 结论；分支按钮（绿：[去确认开播]；黄：提示等待审批；红：[重新登记整改]） |
| 审批放行抽屉 | Drawer 560px | 只读风控结果 + opinion 必填 ≤512 字；[通过放行][拒绝整改] |
| 取消弹窗 | Modal 420px | reason 必填 ≤256 字 |

### 8. 错误处理
- 网络超时：提交防重（clientToken，V1-E3 保证重试不产生重复场次）；
- 场次 ID 冲突（1005）：服务端兜底自动重取序列，前端无感知（V1-E2）；
- 证件锁定拦截：登记提交成功但风控判红，结果抽屉红字定位到证件项（错误码 1004 关联提示），引导换证（跳 CERT-P2）；
- 账号状态变化：提交时 1003 类内联错误；
- 权限不足：按钮按矩阵隐藏。

### 9. BR 业务规则覆盖
- **BR-006（直播台账留痕率 100%）**：开播唯一入口 = 本页登记（未放行不可开播，LIVE-R1），每场必生成场次 ID 与风控记录；
- **BR-011（场次 ID 编码）**：19 位 `IMS+yyyyMMdd+平台码+序列`，提交后只读回显、不可变更（LIVE-R4）；幂等 clientToken（V1-E3）；
- **BR-013（证件到期锁定拦截）**：实名人证件锁定 → 风控直接判红（LIVE-R2），登记页选择实名人时前置红字预警；
- **BR-014（风险分三级）**：风控结果抽屉的分值/级别/结论与放行分支（绿自动/黄审批/红禁止整改）即 BR-014 全量页面落点。

---

## P2. 下播数据录入页（LIVE-002）

### 1. 页面概述
- 路由路径：`/ims/live/report`
- 页面级别：一级菜单页（默认视图=待录入督办列表）
- 依赖模块：LIVE-001（场次）、ACCT-004（投放成本/冲话费联动）、工作台督办、财务核准
- 权限矩阵引用：R1 R（全量）、R3 R（GMV/成本字段）、R4 R/W（全量+核准）、R5 R/W（本人场次+团队）、R7 W（本人场次）、R9 R（全量）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 场次ID | 责任人 | 录入状态(草稿/已提交/已核准/超时未录) |     |
|         下播日期范围 | [查询] [重置]                                |
+------------------------------------------------------------------+
| 表格: 场次ID | 账号 | 主题 | 实际起止 | 实际时长 | GMV | 录入状态 |  |
|       | 提交时间 | 超时标记 | 操作[录入/编辑][核准][更正][详情]       |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
录入抽屉(640px):
  实际开始* | 实际结束* | 实际时长(自动计算,分钟) | GMV* | 订单数* |
  观看人数* | 峰值在线* | 涨粉数* | 退款额* | 投放成本* |
  ---- 自动计算区(灰底只读): 客单价 | UV价值 | 投产比ROAS ----
  [保存草稿] [提交]
更正抽屉: 原数据(只读) + 更正字段 + 更正原因* → 生成更正单留痕
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface LiveReportPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string; responsibleUserId?: number;
  entryStatus?: EntryCostStatus;
  endRange?: [string, string];
}
interface LiveReportSubmitReq {
  sessionCode: string;
  actualStart: string;              // 必填
  actualEnd: string;                // 必填，晚于 actualStart
  gmv: number;                      // 必填 ≥0 DECIMAL(12,2)
  orderCount: number;               // 必填 ≥0
  viewerCount: number;              // 必填 ≥0
  peakOnline: number;               // 必填 ≥0
  newFans: number;                  // 必填 ≥0
  refundAmount: number;             // 必填 ≥0
  adCost: number;                   // 必填 ≥0
  clientToken: string;
}
interface LiveReportCorrectionReq {
  sessionCode: string;
  fields: Partial<LiveReportSubmitReq>;   // 更正字段
  reason: string;                  // 必填 ≤512 字
}
interface LiveReportConfirmReq { sessionCode: string; }

// 响应类型
interface LiveReportItem {
  sessionCode: string;
  accountNickname: string;
  topic: string;
  actualStart: string | null; actualEnd: string | null;
  durationMinutes: number | null;
  gmv: number | null;
  entryStatus: EntryCostStatus;
  submittedAt: string | null;
  overdue: boolean;                // 下播 24h 未提交（LIVE-D-R1）
  roas: number | null;
}
interface LiveReportDerived {
  avgOrderValue: number;           // GMV/订单数，自动计算 2 位
  uvValue: number;                 // GMV/观看人数
  roas: number;                    // GMV/总成本
}

// 枚举类型
type EntryCostStatus = 'DRAFT' | 'SUBMITTED' | 'CONFIRMED';
// 草稿 / 已提交 / 已核准（全局规范第 4 章权威枚举 EntryCostStatus；与 LIVE API 契约 3.2.2 entryStatus 状态机一致，LIVE 下播报告复用该三态）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /live/report/pending` + 历史列表；默认 Tab 聚焦"待录入"（下播未提交场次），超时项红标置顶；失败重试。

#### 4.2 核心操作流程
**A. 下播数据录入（R5/R7 本人）**
1. 下播后（状态已下播）责任人收到工作台待办 → [录入] 打开录入抽屉；
2. 实际起止时间选择 → 实际时长自动计算（分钟，只读）；
3. 必填 9 项指标（GMV/订单数/观看人数/峰值在线/涨粉数/退款额/投放成本，任一缺失提交禁用，LIVE-D-R2）；
4. 灰底自动计算区实时联动（客单价/UV 价值/ROAS，两位小数，LIVE-D-R4）；
5. [保存草稿]（状态草稿，可反复编辑）或 [提交]：
   - 提交成功 → 状态"已提交"，数据锁定只读（LIVE-D-R3，修改走更正单）；
   - 投放成本填写时提示"将关联冲话费记录核对（BR-017）"（服务端联动）；
6. 下播 24h 未提交（LIVE-D-R1）→ 超时红标 + 工作台督办 + 指标统计扣分（服务端）。

**B. 核准（R4）**
1. 已提交场次行 [核准] → `PUT /live/report/{sessionCode}/confirm` → 状态"已核准"，数据进入利润核算模型（DM 联动）。

**C. 更正（R1 留痕更正）**
1. 已提交/已核准场次 [更正] → 更正抽屉：展示原值，仅放开更正字段，原因必填；
2. 提交生成更正单（留痕）→ 原记录保留版本历史。

**D. 详情**
- 行 [详情] → 抽屉展示报告全字段 + 衍生指标 + 更正历史 + 关联场次信息（场次状态链路）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 场次 ID 精确 |
| responsibleUserId | PersonSelect | 否 | 空 | 责任人 |
| entryStatus | Select | 否 | 空 | 草稿/已提交/已核准 |
| endRange | DateRangePicker | 否 | 近 7 天 | 下播日期范围 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次 ID | 190 | — | 等宽字体 |
| accountNickname | 账号 | 130 | — | — |
| topic | 主题 | 自适应 | — | 省略 + tooltip |
| actualRange | 实际起止 | 220 | — | "HH:mm ~ HH:mm（183 分钟）"，未录显示"待录入"灰字 |
| gmv | GMV | 110 | ✓ | ¥ 两位小数；R3 视角重点列 |
| entryStatus | 录入状态 | 100 | — | tag：草稿(蓝)/已提交(青)/已核准(绿) |
| submittedAt | 提交时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| overdue | 超时 | 80 | — | 超时红标"超 24h" |
| actions | 操作 | 200 | — | [录入/编辑][核准][更正][详情] 按状态+角色 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 录入抽屉 | Drawer 640px | actualStart/actualEnd 必填且 end>start；9 项指标必填 ≥0（GMV/退款/成本两位小数 DECIMAL(12,2)，计数类整数）；派生指标只读自动计算；[保存草稿] 不校验必填、[提交] 全量校验（LIVE-D-R2）；clientToken 防重 |
| 更正抽屉 | Drawer 640px | 原值对照（左原右新）；更正字段白名单（同 9 项）；reason 必填；提交生成更正单 |
| 报告详情抽屉 | Drawer 720px | 只读全字段 + 衍生指标 + 更正版本时间线 |

### 8. 错误处理
- 网络超时：草稿本地暂存（表单不丢），提交防重；
- 必填缺失提交：按钮禁用 + 缺失字段红框定位；
- 核准冲突（他人已核准）：刷新提示；
- R3 视角：仅 GMV/成本列可见，其余列隐藏（服务端裁剪字段）；
- 权限不足：按钮隐藏。

### 9. BR 业务规则覆盖
- **BR-007（下播录入完整率 > 95%）**：必填 9 项强校验（LIVE-D-R2）+ 24h 超时督办红标（LIVE-D-R1）；
- **BR-017（冲话费账实核对）**：投放成本字段与冲话费记录联动核对提示（服务端），差异入核对视图；
- 提交后只读 + 更正单留痕（LIVE-D-R3）、派生指标两位小数（LIVE-D-R4）。

---

## P3. 直播风险告警页（LIVE-003）

### 1. 页面概述
- 路由路径：`/ims/live/alarm`
- 页面级别：一级菜单页，Tab：[告警记录] [规则管理] [统计看板]
- 依赖模块：16 数据采集已建事件流（数据源）、工作台/钉钉推送（通知）、LIVE-001 场次关联
- 权限矩阵引用：R1 R/W/D（全量规则）、R4 R/W（全量规则+全量处置）、R5 R（本人场次）+ 处置（本人场次告警）、R7 R（本人场次）、R9 R、R2 R（只读）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [告警记录] [规则管理] [统计看板]                                |
| 告警Tab 查询行: 场次ID | 告警级别(L1提示/L2警告/L3严重) | 处置状态 | 时间范围 |
|   [查询] [重置]                                                   |
| 告警Tab 表格: 告警ID | 场次ID | 规则名 | 级别 | 告警内容 | 发生时间 | |
|   处置状态 | 处置人 | 操作[处置][详情]（未处理30分钟升级标记）          |
| 规则Tab 表格: 规则名 | 类型(阈值/事件) | 规则摘要 | 级别 | 通知人 |    |
|   状态 | 操作[编辑][启停][删除]      [+新建规则]                     |
| 看板Tab: 按级别统计 | 按规则 TOP | 未处理趋势                        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
新建/编辑规则抽屉(640px): 规则名* | 类型*(阈值/事件) | 指标+操作符+阈值+窗口
| 级别* | 通知人*(角色/具体人) | 状态 | [保存]
处置抽屉: 告警详情(只读) + 处置动作*(已确认/已处理/误报) + 说明(建议必填)
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AlarmRecordPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string;
  alarmLevel?: AlertLevel;
  handleStatus?: AlarmHandleStatus;
  timeRange?: [string, string];
}
interface AlarmRuleSaveReq {
  ruleName: string;                // 必填 ≤64 字
  ruleType: 'THRESHOLD' | 'EVENT';
  ruleExpr: {                      // 结构化编辑，非手写 JSON
    metric: string;                // 指标编码（gmv_drop/viewer_drop/balance_low/…）
    operator: 'GT' | 'LT' | 'PCT_DROP' | 'HIT';
    threshold: number;
    window?: number;               // 分钟，阈值型
  };
  level: AlertLevel;
  notifyUsers: { roleIds?: number[]; userIds?: number[] };
  status: 'ENABLED' | 'DISABLED';
  clientToken?: string;
}
interface AlarmHandleReq {
  /** 处置动作（CONFIRMED/HANDLED/FALSE_ALARM，与契约 3.3.6 handleStatus 值域一致） */
  handleStatus: 'CONFIRMED' | 'HANDLED' | 'FALSE_ALARM';
  handleRemark?: string;            // 处置说明，≤512 字（处置说明建议必填，契约定义为可选）
}

// 响应类型
interface AlarmRecordItem {
  id: number;
  sessionCode: string;
  ruleName: string;
  alarmLevel: AlertLevel;
  alarmContent: string;            // 如"场观 5 分钟内骤降 42%"
  occurAt: string;
  handleStatus: AlarmHandleStatus;
  handlerName: string | null;
  escalated: boolean;              // 30 分钟未处理已升级（ALM-R3）
}
interface AlarmRuleItem {
  id: number;
  ruleName: string;
  ruleType: 'THRESHOLD' | 'EVENT';
  ruleExprSummary: string;         // "场观骤降 > 30%（窗口 5 分钟）"
  level: AlertLevel;
  notifySummary: string;
  status: 'ENABLED' | 'DISABLED';
}

// 枚举类型
type AlertLevel = 'L1' | 'L2' | 'L3';
// L1=提示 L2=警告 L3=严重（全局规范第 4 章 AlertLevel 权威枚举；页面展示中文，传输用枚举值；传输层 1/2/3 由请求封装转换，PRD 5.18 TINYINT 1/2/3 映射）
type AlarmHandleStatus = 'UNHANDLED' | 'CONFIRMED' | 'HANDLED' | 'FALSE_ALARM';
// 未处理 / 已确认 / 已处理 / 误报（LIVE 风险告警域本地枚举，与全局 AlertEventStatus 语义映射：UNHANDLED≡OPEN、HANDLED≡RESOLVED；LIVE API 契约传输层即本值域，不引用 AlertEventStatus）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /live/alarm/records`；未处理告警以红点角标显示在 Tab 上；严重级告警页面顶部横幅滚动展示（若本人责任范围）；失败重试。

#### 4.2 核心操作流程
**A. 告警处置（R5/R7 本人场次、R4 全量）**
1. 行 [处置] → 抽屉：告警详情只读（场次链接可跳台账详情）；
2. 处置动作三选一（`handleStatus`）：CONFIRMED 已确认（已知晓处理中）/ HANDLED 已处理（附处理结果说明）/ FALSE_ALARM 误报（说明误报依据）；
3. 处置说明（handleRemark，建议必填）→ `PUT /live/alarm/record/{recordId}/handle`（recordId 为路径参数）→ 状态更新闭环；
4. 未处理 30 分钟（ALM-R3）→ 服务端升级推送运营总监，行内"已升级"标记；
5. 同规则同场次 10 分钟内去重合并（ALM-R2，服务端），列表显示合并计数（如"×3"）。

**B. 规则管理（R1/R4）**
1. [+新建规则] → 抽屉：结构化表达式编辑（指标下拉 + 操作符 + 阈值 + 窗口），非手写 DSL（保存时服务端校验，错误码 1009）；
2. 常用指标：GMV 异常波动（PCT_DROP）、场观骤降（PCT_DROP）、话费余额（LT 阈值）、账号异常状态（EVENT）、违禁词命中（EVENT/HIT）；
3. 保存热更新即时生效（ALM-R4，无需重启）；
4. [启停] 切换、[删除] 确认弹窗。

**C. 统计看板**
- 按级别分布饼图、按规则命中 TOP10、近 7 天未处理趋势折线（本页内展示，不跳转）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 场次 ID |
| alarmLevel | Select | 否 | 空 | L1 提示/L2 警告/L3 严重 |
| handleStatus | Select | 否 | 空 | 未处理/已确认/已处理/误报 |
| timeRange | DateRangePicker | 否 | 近 24h | 发生时间 |

### 6. 表格列定义

告警记录：

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| id | 告警 ID | 90 | — | 等宽字体 |
| sessionCode | 场次 ID | 190 | — | 等宽，可点击跳台账详情 |
| ruleName | 规则名 | 140 | — | — |
| alarmLevel | 级别 | 90 | — | tag：L1 提示(蓝)/L2 警告(黄)/L3 严重(红) |
| alarmContent | 告警内容 | 自适应 | — | 合并计数"×3"后缀 |
| occurAt | 发生时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| handleStatus | 处置状态 | 100 | — | tag：未处理(红)/已确认(蓝)/已处理(绿)/误报(灰) |
| escalated | 升级 | 70 | — | 已升级橙标 |
| actions | 操作 | 130 | — | [处置][详情] |

规则管理：

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| ruleName | 规则名 | 160 | — | — |
| ruleType | 类型 | 90 | — | tag：阈值(蓝)/事件(紫) |
| ruleExprSummary | 规则摘要 | 自适应 | — | 人话文案 |
| level | 级别 | 90 | — | tag 同上 |
| notifySummary | 通知人 | 160 | — | "责任人+运营总监" 摘要 |
| status | 状态 | 80 | — | tag：启用(绿)/停用(灰) |
| actions | 操作 | 160 | — | [编辑][启停][删除] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 规则新建/编辑抽屉 | Drawer 640px | ruleName 必填 ≤64 字；ruleType 必选；metric/operator/threshold 必填（阈值型 threshold ≥0，窗口 1~60 分钟）；level 必选；notifyUsers 至少选择角色或具体人；保存即时生效提示（ALM-R4） |
| 告警处置抽屉 | Drawer 560px | 只读告警详情；handleStatus 必选三选一（CONFIRMED/HANDLED/FALSE_ALARM）；handleRemark ≤512 字（建议必填） |
| 规则删除确认弹窗 | Modal 360px | 输入规则名确认 |
| 告警详情抽屉 | Drawer 560px | 只读：告警全文 + 关联场次信息 + 处置历史 |

### 8. 错误处理
- 网络超时：列表与抽屉独立重试；
- 规则表达式非法（1009）：抽屉内阈值/窗口字段红框提示；
- 处置冲突（他人已处置）：刷新状态提示；
- 权限不足：规则 Tab 仅 R1/R4 可见，告警记录按本人场次过滤。

### 9. BR 业务规则覆盖
- **BR-006（直播风险事前+事中拦截）**：告警规则（GMV 波动/场观骤降/话费/账号/违禁词）事中监控为留痕体系的运行时保障；
- ALM-R1（L3 严重级 1 分钟触达钉钉+短信）、ALM-R2（10 分钟去重合并 ×N 展示）、ALM-R3（30 分钟升级运营总监"已升级"标记）、ALM-R4（规则热更新保存即生效）均在本页落点。
- 告警级别全局对齐：本页 `AlertLevel`（L1/L2/L3）与全局规范 `AlertLevel`、LIVE API 契约 `alarmLevel: 1|2|3`（数字传输）一致——前端渲染统一字符串枚举 L1/L2/L3，传输层 1/2/3 由请求封装转换（PRD 5.18 TINYINT 1/2/3 映射）。

---

## P4. 直播台账查询页（LIVE-004）

### 1. 页面概述
- 路由路径：`/ims/live/ledger`
- 页面级别：一级菜单页（全量台账 + 聚合详情抽屉 + 历史补录）
- 依赖模块：LIVE-001/002（数据源）、ASSET 反向穿透（场次维度）、财务字段（R3 视角）
- 权限矩阵引用：R1 R（全量）、R2 R、R3 R（财务字段）、R4 R（全量）+ 补录发起/审批、R5 R（本人场次+团队）、R7 R（本人场次）、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 场次ID | 时间区间 | 账号 | 责任人 | 平台 | 状态 | 风险级别 |  |
|         是否补录 | [查询] [重置]              [历史补录(R4)] [导出] |
+------------------------------------------------------------------+
| 表格: 场次ID | 日期 | 平台 | 账号 | 责任人 | 主题 | 状态 | 风险级别 | |
|       | GMV | 时长 | 观看数 | 补录标记 | 操作[穿透详情][补录审批]     |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx  （万级场次查询 < 3s, LED-R2）|
+------------------------------------------------------------------+
台账聚合详情抽屉(全屏/90%): 
  Tab: [登记信息(含风控结果)] [下播数据] [成本汇总] [关联资产(反向穿透)]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface LiveLedgerPageReq {
  pageNo: number; pageSize: number;
  sessionCode?: string;
  timeRange?: [string, string];
  accountId?: number; responsibleUserId?: number;
  platform?: string;
  sessionStatus?: LiveSessionStatus;
  riskLevel?: RiskLevel;
  isSupplement?: boolean;
}
interface LiveSupplementReq {
  // 补录登记（登记+数据一次提交）
  register: LiveRegisterCreateReq;      // 复用登记结构（补录标记自动置位）
  report: LiveReportSubmitReq;          // 复用下播数据结构
  supplementReason: string;             // 必填 ≤256 字（LED-R1）
  clientToken: string;
}
interface LiveSupplementApproveReq { supplementId: number; approved: boolean; opinion: string; }

// 响应类型
interface LiveLedgerItem {
  sessionCode: string;
  liveDate: string;                 // 实际开播日期
  platform: string;
  accountNickname: string;
  responsibleUserName: string;
  topic: string;
  sessionStatus: LiveSessionStatus;
  riskLevel: RiskLevel | null;
  gmv: number | null;               // R3/R1/R4/R9 可见
  durationMinutes: number | null;
  viewerCount: number | null;
  isSupplement: boolean;
}
interface LiveLedgerDetail {
  register: LiveSessionItem;             // 登记信息
  riskCheck: RiskCheckResult | null;     // 风控结果
  report: LiveReportItem | null;         // 下播数据（含衍生指标）
  costSummary: { totalCost: number; adCost: number; rechargeCost: number; sampleCost: number } | null;
  supplementInfo: { reason: string; approverName: string; approvedAt: string } | null;
}

// 枚举类型
// 复用 LiveSessionStatus / RiskLevel / EntryCostStatus（全局规范权威枚举）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /live/ledger/list`；R5 团队范围、R7 本人范围（服务端过滤）；查询性能目标 < 3s（LED-R2）；失败重试。

#### 4.2 核心操作流程
**A. 多维查询与导出**
1. 查询条件组合（场次 ID/时间/账号/责任人/平台/状态/风险级别/补录标记）；
2. [导出] → 当前条件导出 Excel 台账；R3 视角导出仅财务字段列；导出留审计。

**B. 台账聚合详情（穿透详情抽屉）**
1. 行 [穿透详情] → 大抽屉四 Tab：
   - 登记信息：场次基本信息 + 风控 5 项结果与放行记录；
   - 下播数据：9 项指标 + 衍生指标 + 更正历史；
   - 成本汇总：投放/充值/样品成本（R3/R1/R4/R9 可见，其他角色 Tab 隐藏）；
   - 关联资产：反向穿透（ASSET-002 session 维度，复用资产模块穿透组件）；
2. 抽屉内场次 ID、责任人、账号均可点击下钻（人员 → AUTH 人员详情；账号 → ACCT 台账）。

**C. 历史补录（R4）**
1. [历史补录] → 大抽屉两步表单：第一步登记信息（复用 P1 登记表单，计划时间填历史时间）+ 下播数据（复用 P2 录入表单）+ 补录说明必填（LED-R1）；
2. 提交 → 生成补录单（is_supplement=1）→ 状态"待审批"；
3. R4 审批（补录审批操作）→ 通过入库（场次 ID 按历史日期补签发，平台码对应）；拒绝 → 退回修改；
4. 补录场次标记"补录"灰 tag，不计入留痕率分母考核争议（PRD 5.19 说明，台账区分展示）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sessionCode | Input | 否 | 空 | 场次 ID 精确 |
| timeRange | DateRangePicker | 否 | 本月 | 开播日期区间 |
| accountId | AccountSelect | 否 | 空 | 账号 |
| responsibleUserId | PersonSelect | 否 | 空 | 责任人 |
| platform | Select | 否 | 空 | 平台码字典 |
| sessionStatus | Select | 否 | 空 | 场次状态 |
| riskLevel | Select | 否 | 空 | 风险级别 |
| isSupplement | Select | 否 | 空 | 全部/正常/补录 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sessionCode | 场次 ID | 190 | — | 等宽字体；补录加灰 tag"补录" |
| liveDate | 日期 | 110 | ✓ | yyyy-MM-dd |
| platform | 平台 | 80 | — | 字典翻译 |
| accountNickname | 账号 | 130 | — | — |
| responsibleUserName | 责任人 | 100 | — | 可点击下钻 |
| topic | 主题 | 自适应 | — | 省略 + tooltip |
| sessionStatus | 状态 | 100 | — | tag 同 P1 |
| riskLevel | 风险级别 | 90 | — | tag 三色 |
| gmv | GMV | 110 | ✓ | ¥ 两位小数（R3/R1/R4/R9 可见，其他隐藏列） |
| durationMinutes | 时长 | 90 | ✓ | "3 小时 5 分" |
| viewerCount | 观看数 | 100 | ✓ | 千分位 |
| actions | 操作 | 180 | — | [穿透详情]（+补录待审批行 [补录审批]） |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 台账聚合详情抽屉 | Drawer 90% 可全屏 | 四 Tab 只读聚合；成本 Tab 按角色显示；关联资产 Tab 复用 ASSET 反向穿透组件 |
| 历史补录抽屉 | Drawer 90% | 步骤一：登记表单（复用 P1 校验）+ 数据表单（复用 P2 必填校验）；步骤二：supplementReason 必填 ≤256 字 + 提交审批 |
| 补录审批抽屉 | Drawer 560px | 补录内容只读 + opinion 必填 + [通过][拒绝] |
| 导出确认弹窗 | Modal 360px | 导出范围（当前筛选）确认 |

### 8. 错误处理
- 网络超时：列表重试；导出异步（大结果落服务端文件目录并通知领取，复用 V1-B3 约定）；
- 查询超 3s：前端提示优化建议（缩小时间区间）；
- 补录校验失败：步骤定位红框；
- 权限不足：列级裁剪（R3）与 Tab 级裁剪（成本 Tab）。

### 9. BR 业务规则覆盖
- **BR-006（台账留痕率 100%）**：台账全量聚合（登记+风控+数据+成本）与 BR-006 指标看板同源（LED-R3）；补录场次不计分母（is_supplement 标记展示）；
- **BR-011（场次 ID）**：台账场次 ID 只读，补录场次 ID 按编码规则以历史日期补签发；
- **BR-014**：台账风险级别列留存历史风控结论；
- LED-R1（补录需说明+审批）：补录表单 reason 必填 + R4 审批流。

---

## 模块通用备注
- 本模块 4 个一级页面，抽屉/弹窗共 13 个（登记、风控结果、审批放行、取消、录入、更正、报告详情、规则编辑、处置、告警详情、台账聚合详情、历史补录、补录审批）+ 确认弹窗若干。
- 全模块复用全局权威枚举：`LiveSessionStatus`（PENDING_RISK_CHECK/APPROVED/LIVE/ENDED/CANCELLED）、`RiskLevel`、`EntryCostStatus`、`AlertLevel`（=全局 AlertLevel，L1/L2/L3）、`AlarmHandleStatus`（UNHANDLED/CONFIRMED/HANDLED/FALSE_ALARM）；
- 场次 ID 19 位口径（IMS+yyyyMMdd+平台码+序列）与 PRD BR-011 的 LV 口径差异已在文档头声明，以共享技术规范为准。
