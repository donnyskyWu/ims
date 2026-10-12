# LIVE - 直播管理 API 契约

> **模块范围**：10 直播管理（V1，第 9~12 周，全新）——LIVE-001 开播风控登记、LIVE-002 下播数据录入、LIVE-003 直播风险告警、LIVE-004 历史台账查询。
> **权威依据**：《IMS第一期PRD-V1.md》5.16~5.19；《共享技术规范-数据库与API.md》7.4.3（场次 ID 编码）、V1-E1~E5（生成器并发约束）、8.1/8.3。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》；字段 camelCase；**创建场次强制幂等 `clientToken` 请求头**。  
> **IA（场次中心）**：列表与聚合详情以 **场次** 为主键；下文 `register/list` 与 `ledger/list` 在实现层可共用查询，但产品默认暴露 **§3.0 场次列表/详情**。

---

## 2. Football 单场「基本信息」与指标边界（2026-10-01 拍板 · **2026-10-05 v2.6.34 修订：直播计数列纳入 `live_room` 只读**）

| 需求 | IMS 落点 | 现网 SSOT | 状态 |
|------|----------|-----------|------|
| 作者×日期直播时长/场次数 | 仅 M6 报表 / BI0；**非** IMS 单场 Tab | **DB 只读** `live_room` · **照抄**现网 `RoomMapper.xml#getLiveRoomCount` | **2026-10-05 拍板（照抄）**：IMS **不用 Feign、不等新 REST**；口径见 **§2.2**；M6/BI0 落点 |
| **单场 Football 直播间基本信息** | 详情 Tab「直播数据」· `GET …/metrics` · `POST …/football-sync` | **DB 只读** `live_room`（live-server 实体 `LiveRoomDO`，`@TableName("live_room")`） | **✅ 本期**：IMS Go 直连共用业务库（ADR-IMS-001），**禁止**为本场景新增 Feign |
| **单场观看数 / 点赞 / 预约人数等直播计数** | 详情 Tab「直播数据」· `GET …/metrics` | **DB 只读** `live_room`（计数列，见 §2.1） | **✅ 本期（v2.6.34）**：随 `live_room` 只读一并取回，**不再依赖任何 metrics OpenAPI** |
| 单场 GMV / 峰值在线 / 涨粉 / 退款 / 投放成本 | `ims_live_data_snapshot` + **下播录入（LIVE-002）** | `live_room` 无此列 | 由 LIVE-002 录入承载；**「直播数据」Tab 不再显示「—」占位** |
| 订单 GMV 交叉核对（可选） | 下播 Tab 只读提示 | `POST /rpc-api/pay/order/page-for-ops` | authorId 维度，非 room 级 |

### 2.1 SQL / 表 SSOT（单场基本信息）

| 项 | 约定 |
|----|------|
| 表名 | **`live_room`**（Football `football-module-live-server` · `dal/dataobject/live/LiveRoomDO.java`） |
| 关联键 | `ims_live_session.football_room_id` = **`live_room.id`**（字符串存储，查询时转 BIGINT） |
| 租户 | `live_room.tenant_id` = 当前租户；`deleted = 0` |
| 本期读取列（v2.6.34 扩展） | **房间**：`id`, `author_id`, `nickname`, `avatar`, `live_id`, `live_name`, `cover`, `status`（1 未开始/2 直播中/3 已结束/4 过期/5 暂停）, `start_time`, `end_time`, 横竖屏, 公开/付费/加密, 观看/回放/推流地址；**计数**：`viewer_count`（观看人数）、点赞、预约人数。（snake_case 以 `LiveRoomDO` 字段名为准） |
| 时长 | 表内**无** `duration_*` 列；`durationMinutes` 仅当 `start_time` 与 `end_time` 均非空时由服务端差值计算 |
| 非 SSOT（勿选） | `oa_douyin_live` / `oa_wechat_video_live`（M10 采集 · ADR-067）与 Football Admin 直播间 **非同一对象**；`LiveRoomReadService` **不读库**，仅 RPC 聚合 |

**实现约束**：
1. **`GET /admin-api/ims/live/sessions/{sessionCode}/metrics`**：合并 IMS 快照 + **`footballRoomBasic`**（上表列映射）；未绑定 `football_room_id` 时 `footballRoomBasic=null`，`syncStatus=UNLINKED`。
2. **`POST …/football-sync`**：按 `football_room_id` 再读 `live_room` 一行，更新 `football_sync_status`、`last_football_sync_at`；可选 upsert 快照元数据（**不含**臆造 GMV/峰值）。失败走 outbox（BR-303），不回滚场次主数据。
3. **禁止** Feign/`FootballWebApiClient` 拉取本场基本信息；**禁止**编造 `/rpc-api/live/room/{id}` 作为本期 SSOT。
4. 作者×日期 `liveCount`/`liveDuration` **不得**替代单场 Tab（口径见 §2.2，落点 M6/BI0）。

### 2.2 作者×日期 直播时长聚合 SQL（**照抄现网** · 2026-10-05 拍板）

> **背景**：Football 侧"直播时长聚合"历史上**只有 Feign** `LiveRoomApi.getLiveRoomCount`（无对外 REST）。IMS **不等** Football 出 REST——直接以 **sqlc 只读** `live_room`，**逐字照抄**现网 `RoomMapper.xml#getLiveRoomCount`，保证与 OPS 报表**同口径**。

| 项 | 照抄口径（逐字，不得改写） |
|----|---------------------------|
| 表 | `live_room` |
| WHERE | `author_id = ?` **AND** `create_time BETWEEN ? AND ?`（**本 SQL 无 `deleted` 条件**） |
| 场次 | `liveCount = count(1)` |
| 时长 | `liveDuration = sum(TIMESTAMPDIFF(MINUTE, start_time, end_time))`（**分钟**） |
| 入参 | `authorId`（= `live_room.author_id` = `author_user.id`）；闭区间 `[start, end]` |
| 出参 DTO | `LiveRoomCountRespDTO{ liveCount, liveDuration }` |
| 消费方 | **M6 直播时长报表**、**BI0 `live-duration`**；**非** LIVE 单场 Tab |

**与小时口径的关系（防混用）**：现网另有 `RoomMapper.xml#selectLiveTrendStat`（`deleted = 0 AND status IN(2,3)`、按 `DATE` 分组、时长按**小时**），**仅 OPS 内部趋势看板使用**：

1. **作者×日期 场次/时长** → 一律用上表（**无 `deleted`、无 `status`**）。
2. 小时口径 **IMS 本期不消费**；如需"趋势"视图，**另立 ADR** 并写明与上表数差来源。
3. **一致性判据**：同 `(authorId, 日期区间)` 须与现网 `getLiveRoomCount` **逐值一致**；**禁止**自行加 `deleted=0`/`status` 过滤"修正"（该 SQL 本就**含**未开始/暂停房间）。

> 完整盘点与源码取证见《FB-Football-WebAPI-待盘点全路径对照表.md》「已关闭」表 · 直播时长聚合行。

---

## 1. 场次 ID 编码说明（权威，BR-011/DM-003）

> **编码规则（V1 定死，后续不得变更）**：`IMS + yyyyMMdd（8 位日期）+ 3 位平台码 + 4 位当日序列`，共 19 位字符串。
> 示例：`IMS20250401DYS0042`。

| 段 | 说明 |
|----|------|
| `IMS` | 固定系统标识，区别于其他系统单号 |
| `yyyyMMdd` | **场次创建日期**（北京时间，非直播日期） |
| 3 位平台码 | `DYS`=抖音直播、`KS`=快手、`WX`=视频号、`TM`=淘宝、`JD`=京东、`OTA`=其他（V1 建平台码字典表，可扩展，与 `PlatformType` 枚举一致） |
| 4 位当日序列 | 按平台自增 0001~9999，日切重置 |

**并发与幂等设计（V1-E1~E5，创建接口 3.1.1 强制遵循）**：
1. Redis `INCR` 原子序列，key 按 `日期+平台码` 维度，TTL 48h，日切自动重置；
2. 「场次 ID 生成器」独立组件统一签发，`ims_live_session.session_code` 唯一索引兜底（冲突重取一次序列，错误码 1005）；
3. 当日序列达 9999 → 降级 5 位序列并 P2 告警；
4. **`clientToken` 幂等**：创建场次请求头必带；同 token 重复请求返回**同一 sessionCode**（防重试跳号/重复）；
5. Redis 不可用降级 DB 行锁序列表，恢复后回补 Redis 计数。

---

## 3. API 总览表（共 29 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 0a | GET | `/admin-api/ims/live/sessions/list` | **场次列表（P0 默认，与 ledger 同源筛选）** | 同 ledger/list |
| 0b | GET | `/admin-api/ims/live/sessions/{sessionCode}` | **场次聚合详情（登记+风控+报告+快照+同步态）** | 同 ledger/{sessionCode} |
| 0c | GET | `/admin-api/ims/live/sessions/{sessionCode}/metrics` | 直播数据 Tab：IMS 快照 + **`live_room` 基本信息**（DB 只读） | R1/R4/R5/R7/R9 |
| 0d | POST | `/admin-api/ims/live/sessions/{sessionCode}/football-sync` | 按 `football_room_id` **重读 `live_room`** 更新同步态/可选快照 | R4/R1 |
| 1 | POST | `/admin-api/ims/live/register` | 创建场次登记（生成场次 ID，幂等） | R5/R7（本人） |
| 2 | GET | `/admin-api/ims/live/register/list` | 登记场次列表（分页，P1 列表） | R1/R4/R9/R5（本人）/R7（本人） |
| 3 | GET | `/admin-api/ims/live/register/{sessionCode}` | 场次详情 | R1/R4/R5（本人）/R7（本人）/R9 |
| 4 | PUT | `/admin-api/ims/live/register/{sessionCode}` | 编辑（开播前） | R5（本人）/R4 |
| 5 | POST | `/admin-api/ims/live/register/{sessionCode}/risk-check` | 触发风控检查 | R5/R7（本人）/R4 |
| 6 | PUT | `/admin-api/ims/live/register/{sessionCode}/approve` | 黄级审批放行 | R4 |
| 7 | PUT | `/admin-api/ims/live/register/{sessionCode}/cancel` | 取消场次（留痕不删除） | R4/R1 |
| 8 | PUT | `/admin-api/ims/live/register/{sessionCode}/start` | 确认开播 | R5/R7（本人） |
| 9 | POST | `/admin-api/ims/live/report/{sessionCode}` | 提交下播数据 | R5/R7（本人场次） |
| 10 | GET | `/admin-api/ims/live/report/{sessionCode}` | 报告详情 | R1/R4/R9/R3（财务字段）/R5/R7 |
| 11 | PUT | `/admin-api/ims/live/report/{sessionCode}` | 编辑（未提交前） | R5/R7 |
| 12 | POST | `/admin-api/ims/live/report/{sessionCode}/correction` | 提交更正单 | R1（留痕更正） |
| 13 | PUT | `/admin-api/ims/live/report/{sessionCode}/confirm` | 核准 | R4 |
| 14 | GET | `/admin-api/ims/live/report/pending` | 待录入/督办列表（分页） | R1/R4/R5 |
| 15 | GET | `/admin-api/ims/live/alarm/rules` | 告警规则列表（分页） | R1/R4/R2（只读）/R5/R7/R9 |
| 16 | POST | `/admin-api/ims/live/alarm/rule` | 新建规则 | R1/R4 |
| 17 | PUT | `/admin-api/ims/live/alarm/rule/{id}` | 编辑规则（热更新，无需重启） | R1/R4 |
| 18 | DELETE | `/admin-api/ims/live/alarm/rule/{id}` | 删除规则 | R1/R4 |
| 19 | GET | `/admin-api/ims/live/alarm/records` | 告警记录列表（分页） | 同 15 |
| 20 | PUT | `/admin-api/ims/live/alarm/record/{id}/handle` | 告警处置 | R5/R7（本人场次）/R4 |
| 21 | GET | `/admin-api/ims/live/alarm/stats` | 告警统计看板 | R1/R4/R9 |
| 22 | GET | `/admin-api/ims/live/ledger/list` | 台账分页查询 | R1/R2/R3（财务字段）/R4/R5（团队）/R7（本人）/R9 |
| 23 | GET | `/admin-api/ims/live/ledger/{sessionCode}` | 台账聚合详情 | 同上 |
| 24 | POST | `/admin-api/ims/live/ledger/supplement` | 历史补录提交 | R4 |
| 25 | PUT | `/admin-api/ims/live/ledger/supplement/{id}/approve` | 补录审批 | R4 |
| 26 | GET | `/admin-api/ims/live/ledger/export` | 导出 Excel 台账（异步导出） | R1/R2/R4/R9 |

---

## 4. 接口明细

### 3.0 场次列表与聚合详情（P0 / P0-D）

#### 3.0.1 GET `/admin-api/ims/live/sessions/list`

**请求**：与 `3.4.1 ledger/list` Query 相同（`sessionCode`、`timeRange`、`accountId`、`sessionStatus`、`riskLevel`、`isSupplement` 等）。

**响应**：`PageResult<LiveSessionListVO>`，在 `LiveLedgerVO` 基础上增加：

```typescript
interface LiveSessionListVO extends LiveLedgerVO {
  footballRoomId?: string | null;
  footballSyncStatus: 'UNLINKED' | 'PENDING' | 'SYNCED' | 'FAILED';
  lastFootballSyncAt?: string | null;
  reportEntryStatus?: 'DRAFT' | 'SUBMITTED' | 'CONFIRMED' | null;
}
```

#### 3.0.2 GET `/admin-api/ims/live/sessions/{sessionCode}`

**响应**：同 `3.4.2 ledger/{sessionCode}`，并附加 `metricsSnapshot`、`footballSyncStatus`、`footballEnrichment`（可为 null）。

#### 3.0.3 GET `/admin-api/ims/live/sessions/{sessionCode}/metrics`

**响应** `data`：

```typescript
/** Football live_room 基本信息（DB SSOT · §2.1 · v2.6.34 扩展计数列） */
interface LiveFootballRoomBasicVO {
  roomId: string;           // live_room.id
  liveId?: string;          // live_room.live_id
  liveName?: string;        // live_room.live_name
  authorId?: string;        // live_room.author_id（JSON 字符串）
  authorNickname?: string;  // live_room.nickname
  authorAvatar?: string;    // live_room.avatar
  status?: number;          // 1 未开始 2 直播中 3 已结束 4 过期 5 暂停（见 LiveRoomDO）
  orientation?: string;     // 横竖屏
  payType?: string;         // 公开 / 付费 / 加密
  startTime?: string;
  endTime?: string;
  durationMinutes?: number; // 服务端由 start/end 推算；缺一则 null
  coverUrl?: string;        // live_room.cover
  playUrl?: string;         // 观看地址
  replayUrl?: string;       // 回放地址
  pushUrl?: string;         // 推流地址
  viewerCount?: number;     // live_room.viewer_count 观看人数
  likeCount?: number;       // 点赞数
  reservationCount?: number;// 预约人数
  sourceTable: 'live_room';
}

interface LiveSessionMetricsVO {
  sessionCode: string;
  footballRoomId?: string;
  syncStatus: 'UNLINKED' | 'PENDING' | 'SYNCED' | 'FAILED';
  lastSyncAt?: string;
  footballRoomBasic?: LiveFootballRoomBasicVO | null;
  snapshot?: {
    viewerCount?: number;
    peakOnline?: number;
    durationMinutes?: number;
    gmvFromPlatform?: number;
    source: 'MANUAL' | 'COLLECT';
    capturedAt: string;
  };
  /** v2.6.34：观看/点赞/预约计数已由 `live_room` 提供；以下仅剩由「下播录入（LIVE-002）」承载的项，Tab **不再显示「—」占位** */
  metricsByManualEntry?: {
    gmv: true;
    peakOnline: true;
    fansGrowth: true;
    refundAmount: true;
    adCost: true;
  };
}
```

#### 3.0.4 POST `/admin-api/ims/live/sessions/{sessionCode}/football-sync`

**请求**：`{ force?: boolean }`  
**行为**：校验 `football_room_id` → `SELECT` §2.1 列自 **`live_room`** → 更新 `football_sync_status`/`last_football_sync_at`；行不存在 → 业务码 **1041** 或 **1051**（房间不存在）。  
**禁止**：501/1050「等待 Football HTTP」作为本场基本信息路径。

### 3.1 开播风控登记（LIVE-001）

#### 3.1.1 POST /admin-api/ims/live/register — 创建场次登记（幂等）

**请求**（Header `clientToken` 强制）：

```typescript
interface LiveSessionCreateReq {
  accountId: number;             // 直播账号（08 联动）
  realnamePersonId: number;      // 实名人（证件强校验 CERT-002）
  responsibleUserId: number;     // 责任人（运营）
  deviceAssetIds: number[];      // 设备资产 ID 列表（07 联动）
  platform: PlatformType;        // 用于场次 ID 平台码段
  topic: string;                 // 直播主题
  planStartTime: string;         // 计划开播时间 ISO 8601
  planEndTime: string;
}
```

**响应** `data`：

```typescript
interface LiveSessionVO {
  id: number;
  /** 场次 ID（IMS+yyyyMMdd+平台码+序列，全局唯一、生成后不可变更） */
  sessionCode: string;
  accountId: number;
  accountNo: string;
  realnamePersonId: number;
  realnameName: string;
  responsibleUserId: number;
  deviceAssetIds: number[];
  platform: PlatformType;
  topic: string;
  planStartTime: string;
  planEndTime: string;
  sessionStatus: LiveSessionStatus;
  riskScore?: number;
  riskLevel?: RiskLevel;         // GREEN / YELLOW / RED
  approverUserId?: number;       // 黄/红级放行审批人
  createdAt: string;
}
```

**幂等语义**：同 `clientToken` 重复请求返回同一 sessionCode（V1-E3）。**错误码**：1005（场次 ID 冲突，生成器兜底重取）、1041（账号/实名人不存在）、1045（实名人证件过期/锁定直接判红，LIVE-R2/CERT-E-R3）。

#### 3.1.2 GET /admin-api/ims/live/register/list — 登记场次列表（分页）

**请求**（Query）：

```typescript
interface LiveRegisterPageReq {
  pageNum: number;                // 页码（默认 1）
  pageSize: number;               // 每页条数（默认 20）
  sessionCode?: string;           // 场次 ID 精确
  accountId?: number;             // 直播账号
  responsibleUserId?: number;     // 责任人
  riskLevel?: RiskLevel;          // 风险级别（R5/R7 服务端自动过滤本人场次）
  sessionStatus?: LiveSessionStatus;
  dateRange?: [string, string];   // 计划开播时间范围
}
```

**响应** `data`：

```typescript
{
  total: number;
  records: LiveSessionVO[];
}
```

（列表仅含索引字段；风控检查明细走 3.1.3 场次详情端点。）

#### 3.1.3 GET /admin-api/ims/live/register/{sessionCode} — 场次详情

**响应** `data`：`LiveSessionVO` + `riskCheckResults: RiskCheckItemVO[]`

```typescript
interface RiskCheckItemVO {
  id: number;
  sessionId: number;
  /** 检查项：证件有效性/账号状态/话费余额/黑名单词/设备归属 */
  checkItem: 'CERT_VALID' | 'ACCOUNT_STATUS' | 'BALANCE' | 'BLACKLIST' | 'DEVICE_OWNER';
  checkResult: 'PASS' | 'FAIL' | 'WARN';
  scoreWeight: number;
  checkedAt: string;
}
```

#### 3.1.4 PUT /admin-api/ims/live/register/{sessionCode} — 编辑（开播前）

**请求**：`LiveSessionCreateReq`（sessionCode 不变）→ **响应**：`data: null`。仅 `PENDING_RISK_CHECK`/`APPROVED` 状态可编辑。

#### 3.1.5 POST /admin-api/ims/live/register/{sessionCode}/risk-check — 触发风控检查

**请求**：`{}` → **响应**：`{ riskScore: number; riskLevel: RiskLevel; checkResults: RiskCheckItemVO[] }`

**评分规则（BR-014）**：风险分 = Σ(各风控项权重分)；≥70 RED（禁止开播整改）、40~69 YELLOW（需审批放行）、<40 GREEN（正常放行）。**错误码**：1043（红色禁止开播）、1044（黄色需审批）、1045（证件过期直接判红）。

#### 3.1.6 PUT /admin-api/ims/live/register/{sessionCode}/approve — 黄级审批放行

**请求**：`{ approve: boolean; comment?: string }` → **响应**：`data: null`。审批留痕（approverUserId 落库）；仅 YELLOW 级可审批，RED 返回 1043。

#### 3.1.7 PUT /admin-api/ims/live/register/{sessionCode}/cancel — 取消场次

**请求**：`{ cancelReason: string }`（必填，ConfirmDialog requireReason）→ **响应**：`data: null`。取消留痕不删除（LIVE-R5）。

#### 3.1.8 PUT /admin-api/ims/live/register/{sessionCode}/start — 确认开播

**请求**：`{}` → **响应**：`data: null`。前置条件：sessionStatus=APPROVED（未放行场次不可开播，LIVE-R1）。

### 3.2 下播数据录入（LIVE-002）

#### 3.2.1 POST /admin-api/ims/live/report/{sessionCode} — 提交下播数据

**请求**：

```typescript
interface LiveReportSubmitReq {
  actualStart: string;
  actualEnd: string;
  durationMinutes: number;
  gmv: number;                   // DECIMAL(12,2)
  refundAmount: number;
  orderCount: number;
  viewerCount: number;
  peakOnline: number;
  newFans: number;
  adCost: number;                // 投放成本（冲话费联动）
  /** 成本明细（ims_live_cost） */
  costDetails?: LiveCostItem[];
}

interface LiveCostItem {
  costType: 'AD' | 'RECHARGE' | 'GIFT' | 'SAMPLE';
  amount: number;
  refRecordId?: number;          // 关联冲话费记录（ACCT-004 联动）
  remark?: string;
}
```

**响应** `data`：`LiveReportVO`

```typescript
interface LiveReportVO {
  id: number;
  sessionCode: string;
  actualStart: string;
  actualEnd: string;
  durationMinutes: number;
  gmv: number;
  refundAmount: number;
  orderCount: number;
  viewerCount: number;
  peakOnline: number;
  newFans: number;
  adCost: number;
  /** 自动计算列（LIVE-D-R4：四舍五入 2 位） */
  avgOrderValue: number;         // 客单价 = GMV/订单数
  roas: number;                  // 投产比 = GMV/总成本
  entryUserId: number;
  entryStatus: 'DRAFT' | 'SUBMITTED' | 'CONFIRMED';   // 0 草稿 / 1 已提交 / 2 已核准
  submittedAt?: string;
}
```

**错误码**：1046（必填项缺失，LIVE-D-R2）、1042（场次状态非已下播）。

#### 3.2.2 GET /admin-api/ims/live/report/{sessionCode} — 报告详情

**响应** `data`：`LiveReportVO`（R3 财务角色仅见 GMV/成本字段，R9 全量；成本字段脱敏见全局规范 5.2）。

#### 3.2.3 PUT /admin-api/ims/live/report/{sessionCode} — 编辑（未提交前）

**请求**：`LiveReportSubmitReq`（草稿态）→ **响应**：`data: null`。**提交后只读**，修改走更正单（LIVE-D-R3，错误码 1047）。

#### 3.2.4 POST /admin-api/ims/live/report/{sessionCode}/correction — 提交更正单

**请求**：`LiveReportSubmitReq` + `{ correctionReason: string }` → **响应**：`{ correctionId: number }`（留痕：新旧值对比记录）。

#### 3.2.5 PUT /admin-api/ims/live/report/{sessionCode}/confirm — 核准

**请求**：`{}` → **响应**：`data: null`。核准后数据进入利润核算模型（DM 联动）。

#### 3.2.6 GET /admin-api/ims/live/report/pending — 待录入/督办列表（分页）

**请求**（Query）：`PageParam` + `{ responsibleUserId?: number; overdueOnly?: boolean }`

**响应** `data`：`PageResult<{ sessionCode: string; topic: string; endedAt: string; responsibleUserName: string; submitted: boolean; overdueHours: number }>`（下播后 24 小时超时督办，LIVE-D-R1，错误码 1048 仅提示）。

### 3.3 直播风险告警（LIVE-003）

#### 3.3.1 GET /admin-api/ims/live/alarm/rules — 规则列表（分页）

**请求**（Query）：`PageParam` + `{ ruleType?: 'THRESHOLD' | 'EVENT'; status?: EnableStatus; keyword?: string }`

**响应** `data`：`PageResult<AlarmRuleVO>`

```typescript
interface AlarmRuleVO {
  id: number;
  ruleName: string;
  ruleType: 'THRESHOLD' | 'EVENT';
  /** 规则表达式（指标/阈值/窗口，如 { metric: 'gmvDrop', window: 10, threshold: 0.3 }） */
  ruleExpr: Record<string, unknown>;
  level: 1 | 2 | 3;              // 1 提示 / 2 警告 / 3 严重（映射 AlertLevel L1/L2/L3）
  notifyUsers: number[];
  status: EnableStatus;
}
```

#### 3.3.2 POST /admin-api/ims/live/alarm/rule — 新建规则

**请求**：`AlarmRuleVO`（去 id）→ **响应**：`AlarmRuleVO`。

#### 3.3.3 PUT /admin-api/ims/live/alarm/rule/{id} — 编辑规则（热更新）

**请求**：同创建 → **响应**：`data: null`。规则热更新无需重启（ALM-R4）。

#### 3.3.4 DELETE /admin-api/ims/live/alarm/rule/{id}

**请求**（Query）：`{ confirmText: 'DELETE' }` → **响应**：`data: null`（逻辑删除）。

#### 3.3.5 GET /admin-api/ims/live/alarm/records — 告警记录列表（分页）

**请求**（Query）：`PageParam` + `{ sessionCode?: string; alarmLevel?: 1 | 2 | 3; handleStatus?: 'UNHANDLED' | 'CONFIRMED' | 'HANDLED' | 'FALSE_ALARM'; timeRange?: [string, string] }`

**响应** `data`：`PageResult<AlarmRecordVO>`

```typescript
interface AlarmRecordVO {
  id: number;
  ruleId: number;
  ruleName: string;
  sessionCode: string;
  alarmLevel: 1 | 2 | 3;
  alarmContent: string;
  occurAt: string;
  handleStatus: 'UNHANDLED' | 'CONFIRMED' | 'HANDLED' | 'FALSE_ALARM';
  handlerUserId?: number;
  handleRemark?: string;
}
```

去重：同一规则同场次 10 分钟内合并（ALM-R2）；严重级 1 分钟内触达钉钉+短信兜底（ALM-R1）；未处理 30 分钟升级推送运营总监（ALM-R3）。

#### 3.3.6 PUT /admin-api/ims/live/alarm/record/{id}/handle — 告警处置

**请求**：`{ handleStatus: 'CONFIRMED' | 'HANDLED' | 'FALSE_ALARM'; handleRemark?: string }` → **响应**：`data: null`。

#### 3.3.7 GET /admin-api/ims/live/alarm/stats — 告警统计看板

**响应** `data`：`{ byLevel: Record<'1' | '2' | '3', number>; byHandleStatus: Record<string, number>; trend: Array<{ date: string; total: number; severe: number }> }`

### 3.4 历史台账查询（LIVE-004）

#### 3.4.1 GET /admin-api/ims/live/ledger/list — 台账分页查询

**请求**（Query）：`PageParam` + `{ sessionCode?: string; timeRange?: [string, string]; accountId?: number; responsibleUserId?: number; platform?: PlatformType; sessionStatus?: LiveSessionStatus; riskLevel?: RiskLevel; isSupplement?: boolean }`

**响应** `data`：`PageResult<LiveLedgerVO>`（万级场次 < 3 秒，LED-R2）

```typescript
interface LiveLedgerVO {
  id: number;
  sessionCode: string;
  platform: PlatformType;
  topic: string;
  accountNo: string;
  responsibleUserName: string;
  sessionStatus: LiveSessionStatus;
  riskLevel?: RiskLevel;
  /** 下播数据摘要（未录入为 null） */
  reportSummary?: {
    gmv: number;
    orderCount: number;
    durationMinutes: number;
    roas: number;
    entryStatus: 'DRAFT' | 'SUBMITTED' | 'CONFIRMED';
  };
  isSupplement: boolean;         // 补录标记
  supplementReason?: string;
  supplementOperatorName?: string;
  actualStart?: string;
  actualEnd?: string;
}
```

#### 3.4.2 GET /admin-api/ims/live/ledger/{sessionCode} — 台账聚合详情

**响应** `data`：`LiveSessionVO + { report: LiveReportVO | null; riskCheckResults: RiskCheckItemVO[]; costSummary: { totalCost: number; byType: Record<string, number> } }`（登记信息+风控+下播数据+成本一屏聚合）。

#### 3.4.3 POST /admin-api/ims/live/ledger/supplement — 历史补录提交

**请求**：

```typescript
interface LiveSupplementReq {
  /** 场次 ID 按编码规则补签发（日期段取历史日期，共享规范 7.7.1） */
  sessionCreate: LiveSessionCreateReq;
  sessionReport: LiveReportSubmitReq;   // 历史数据一并补录
  supplementReason: string;      // LED-R1 必填
}
```

**响应**：`{ supplementId: number; sessionCode: string; message: string }`（标记"补录"，不计入留痕率分母争议）。

#### 3.4.4 PUT /admin-api/ims/live/ledger/supplement/{id}/approve — 补录审批

**请求**：`{ approve: boolean; comment?: string }` → **响应**：`data: null`。审批通过后场次正式入台账。

#### 3.4.5 GET /admin-api/ims/live/ledger/export — 导出 Excel 台账

**请求**（Query）：同 3.4.1 筛选参数 → **响应**：`{ exportTaskId: string; message: string }`（异步导出，回执**下载链接** · 服务端文件目录，本期不上对象存储）。

---

## 5. 状态机与业务约束

### 4.1 状态机

**场次状态（LiveSessionStatus，映射 PRD 5.16.2 TINYINT 0~4）**：

```
PENDING_RISK_CHECK（待风控）──风险检查──▶ [评分判定]
     │                                      │
   编辑（开播前）                    ┌───────┼─────────┐
     │                            ▼       ▼         ▼
     │                        GREEN    YELLOW     RED
     │                          │        │     禁止开播（1043）
     │                       自动放行  R4 审批放行   │
     │                          └───┬────┘    整改后重新登记
     │                              ▼              │
     │                       APPROVED（已放行）◀────┘（新场次）
     │                              │
     │                        start 确认开播
     │                              ▼
     │                          LIVE（直播中）──LIVE-003 告警监控──┐
     │                              ▼                        │
     │                          ENDED（已下播）──LIVE-002 24h 录入┘
     │                              └──核准──▶ 数据进入成本利润模型（DM）
     │
     └──cancel（填原因）──▶ CANCELLED（留痕不删除，LIVE-R5）
```

**下播报告（entryStatus）**：`DRAFT →（提交，必填校验 1046）SUBMITTED →（R4 核准）CONFIRMED`；提交后只读，修改走更正单。

**告警记录（handleStatus）**：`UNHANDLED → CONFIRMED / HANDLED / FALSE_ALARM`（30 分钟未处理升级推送）。

### 4.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-006 | 直播台账留痕率 = 100% | 3.1.x 强制登记 + 未放行不可开播 |
| BR-007 | 下播录入完整率 > 95% | 3.2.1 必填校验（错误码 1046） |
| BR-011 | 场次 ID 编码全局唯一不可变 | 第 1 章编码说明 + 3.1.1 |
| BR-014 | 风险评分三级放行 | 3.1.5（≥70 红 / 40~69 黄 / <40 绿） |
| LIVE-R1 | 未放行不可开播 | 3.1.8 前置校验（1042） |
| LIVE-R2 | 实名人证件过期直接判红 | 3.1.1/3.1.5（1045） |
| LIVE-R4 | 场次 ID 不可变更 | 3.1.4 编辑不含 sessionCode |
| LIVE-R5 | 取消留痕不删除 | 3.1.7（cancelReason 必填） |
| LIVE-D-R1~R4 | 24h 督办/必填/更正单/两位小数 | 3.2.x |
| ALM-R1~R4 | 1 分钟触达/10 分钟去重/30 分钟升级/热更新 | 3.3.x |
| LED-R1~R3 | 补录审批/3 秒响应/指标同源 | 3.4.x |
| V1-E1~E5 | Redis 序列/唯一索引/幂等/降级 | 3.1.1（clientToken） |

---

## 6. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| **P0 场次列表** | 多维场次查询 | GET `/live/sessions/list`（或 alias `ledger/list`） |
| **P0-D 详情-基本信息** | 聚合详情 | GET `/live/sessions/{sessionCode}` |
| **P0-D 详情-直播数据** | 查看 `live_room` 基本信息 / 触发 DB 同步 | GET `…/metrics`；POST `…/football-sync` |
| 场次登记页/工作台入口（DetailDrawer 表单） | 发起场次登记（选账号/实名人/设备/平台/时间） | POST /live/register |
| 场次登记页（QueryBar+表格，Tab 待风控/我登记的） | 登记场次列表查询（场次/账号/责任人/风险级别/状态筛选） | GET /live/register/list（兼容；新 UI 优先 sessions/list） |
| 场次详情抽屉（含风控结果 Tab） | 查看详情/风控检查项明细 | GET /live/register/{sessionCode} |
| 场次详情抽屉-编辑（开播前） | 编辑登记信息 | PUT /live/register/{sessionCode} |
| 场次详情抽屉-风控按钮 | 触发风控检查（评分/级别/明细渲染） | POST /live/register/{sessionCode}/risk-check |
| 场次详情抽屉-审批操作（R4） | 黄级审批放行（ConfirmDialog） | PUT /live/register/{sessionCode}/approve |
| 场次详情抽屉-取消（ConfirmDialog requireReason） | 取消场次（留痕） | PUT /live/register/{sessionCode}/cancel |
| 场次详情抽屉-开播确认 | 确认开播（状态→直播中） | PUT /live/register/{sessionCode}/start |
| 下播录入抽屉（表单必填校验） | 提交下播数据（含成本明细） | POST /live/report/{sessionCode} |
| 下播报告详情抽屉 | 查看/编辑（草稿态）报告 | GET/PUT /live/report/{sessionCode} |
| 报告详情-更正操作（R1） | 提交更正单（留痕对比） | POST /live/report/{sessionCode}/correction |
| 报告详情-核准（R4） | 核准进入核算 | PUT /live/report/{sessionCode}/confirm |
| 待录入督办列表页 | 待录入/超时督办查询 | GET /live/report/pending |
| 告警规则管理页（表格+规则抽屉） | 规则 CRUD（热更新提示） | GET/POST/PUT/DELETE /live/alarm/rule* |
| 告警记录页（QueryBar+表格） | 记录查询/筛选 | GET /live/alarm/records |
| 告警记录操作 | 处置（确认/处理/误报） | PUT /live/alarm/record/{id}/handle |
| 告警统计看板 | 分级/处置状态趋势 | GET /live/alarm/stats |
| 直播台账页（QueryBar 一行筛选+表格，独立页面） | 多维台账查询 | GET /live/ledger/list |
| 台账行-聚合详情 | 一屏聚合（登记+风控+数据+成本） | GET /live/ledger/{sessionCode} |
| 台账页-历史补录（DetailDrawer） | 补录提交（填说明）→ R4 审批 | POST /live/ledger/supplement、PUT /live/ledger/supplement/{id}/approve |
| 台账页-导出按钮 | 异步导出 Excel | GET /live/ledger/export |

（全文完）
