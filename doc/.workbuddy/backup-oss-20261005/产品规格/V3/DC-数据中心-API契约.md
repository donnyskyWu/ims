# DC - 穿透查询 API 契约

> **版本**：v1.1.1（2026-10-04 · 一致性订正）
> **侧栏 IA**：用户菜单 **「穿透查询」** 仅调用 **§2.1**（DC-001）。§2.2~§2.3 仍有效，入口分别为 **11 财务** / **17a BI0**（非本 L1）。
> **逐层下钻（无新接口）**：走查 #13「关联关系逐步下钻」由前端在节点/chip 点击后，以目标节点的 `nodeType`→`entryType` 映射 + `nodeId`→`entryId` **再次调用** `POST /dc/trace/query`；**禁止**新增 graph/lineage/step API。OPS「线索挖掘」：**仓库无 SSOT**，不得引用未文档化端点。
> **与查询工具 TRACE 的关系（D2 · 2026-10-04）**：DC 页面（P1 穿透查询）为 **前端逐步** 下钻（本节口径，前端多次 POST）；**查询工具 TRACE 模式** 则由 **QT 服务端在一次 `query-tool/run` 内 for 循环** 代行相同 DC Service 方法（见《QT-查询工具-API契约》§3.2）。**DC 契约 `DcTraceQueryReq` 保持单步，不新增 `pathSteps`/`depth` 入参**——跨层链由 QT 服务端持有。
> **模块范围**：12 穿透查询（V3，第 28~35 周，P2）——DC-001 账号穿透查询、DC-002 利润反查、DC-003 全链路数据看板。**完全消费 V1（07/08/10）与 V3 先行（11，第 28~33 周）已积累数据，无上游台账新建**，仅建聚合层宽表与查询视图。
> **权威依据**：《IMS第三期PRD-V3.md》5.4~5.6；BR-205、BR-208~BR-210；V3-A1~A4（ODS/DWD/DWS 分层）、V3-C1~C4（穿透 P95<3s）、V3-D1~D4（读写分离）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章（DC 域 1181~1190）；字段 camelCase（`session_code → sessionCode`、`ip_group_id → ipGroupId`）；周次波浪号格式。**关键口径**：穿透查询 P95 < 3s（P99 < 8s，BR-205/V3-C1）；**聚合层只读**（业务数据单向同步，分析结果不回写，V3-A3）；数据新鲜度 < 1 小时（BR-210）；场次 ID 贯穿全链路为唯一锚点（19 位 IMS 编码）。

---

## 1. API 总览表（共 18 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/dc/trace/entry` | 入口搜索（六种穿透入口） | R1/R2/R3/R4/R9（全量）/R5（本团队）/R7（本人链路） |
| 2 | POST | `/admin-api/ims/dc/trace/query` | 穿透查询（返回链路图数据） | 同上 |
| 3 | GET | `/admin-api/ims/dc/trace/detail/{sessionCode}` | 场次明细下钻（含成本/利润） | 同上 |
| 4 | GET | `/admin-api/ims/dc/trace/aggregate` | 聚合模式（按人/账号/团队汇总） | 同上 |
| 5 | GET | `/admin-api/ims/dc/trace/export` | 链路报告导出 | 同上 |
| 6 | GET | `/admin-api/ims/dc/trace/perf-metrics` | 穿透性能统计（BR-205 验证） | R1/R9 |
| 7 | GET | `/admin-api/ims/dc/profit-trace/list` | 利润记录列表（多维筛选，分页） | R1/R3（主责）/R4/R9/R5（本团队）/R7（本人场次） |
| 8 | GET | `/admin-api/ims/dc/profit-trace/{sessionCode}` | 单场利润反查链路 | 同上 |
| 9 | GET | `/admin-api/ims/dc/profit-trace/aggregate` | 聚合反查（按人/账号/团队逐层下钻） | 同上 |
| 10 | GET | `/admin-api/ims/dc/profit-trace/abnormal` | 异常利润下钻清单 | 同上 |
| 11 | GET | `/admin-api/ims/dc/profit-trace/share-detail/{sessionCode}` | 分成明细反查 | R1/R3/R4/R9（脱敏） |
| 12 | GET | `/admin-api/ims/dc/dashboard/overview` | 经营总览指标卡 | R1/R3/R4/R9（全量脱敏）/R5（本团队）/R6（内容域）/R7（本人）/R2 |
| 13 | GET | `/admin-api/ims/dc/dashboard/health` | 链路健康度（BR-208 趋势） | 同上 |
| 14 | GET | `/admin-api/ims/dc/dashboard/dimension` | 维度切换数据 | 同上 |
| 15 | GET | `/admin-api/ims/dc/dashboard/list` | 看板列表 | 同上 |
| 16 | POST | `/admin-api/ims/dc/dashboard` | 创建看板（布局配置） | R1/R4 |
| 17 | PUT | `/admin-api/ims/dc/dashboard/{id}` | 编辑布局 | R1/R4 |
| 18 | GET | `/admin-api/ims/dc/dashboard/freshness` | 数据新鲜度（BR-210） | 同 12 |

---

## 2. 接口明细

### 2.1 账号穿透查询（DC-001）

#### 2.1.1 GET /admin-api/ims/dc/trace/entry — 入口搜索

**请求**（Query）：`{ keyword: string; entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP'; limit?: number }`

**响应** `data`：`Array<{ entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP'; entryId: string; entryLabel: string; platform?: PlatformType; hint: string }>`（六种入口：实名人/账号/资产/场次 ID/责任人/IP 组）。

#### 2.1.2 POST /admin-api/ims/dc/trace/query — 穿透查询

> **单步入参（D2）**：本接口为 **单步** 穿透（一次 entryType/entryId → 一层图/表）。**多步穿透链不由本接口承载**：DC 页由前端逐步调用；查询工具 TRACE 由 QT 服务端在一次 run 内 for 循环调用本接口的同一 Service 方法。**禁止**为本接口新增 `pathSteps`/`depth` 参数。

**请求**：

```typescript
interface DcTraceQueryReq {
  entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP';
  entryId: string;               // 实名人 userId / 账号 ID / 资产 ID / 场次 ID（19 位 IMS 编码）等
  mode: 'GRAPH' | 'DETAIL';
  /** 明细模式分页 */
  pageNo?: number;
  pageSize?: number;
  dateRange?: [string, string];
}
```

**响应** `data`：

```typescript
interface DcTraceGraphResp {
  /** 聚合层预 join 宽表直查（V3-C2：避免在线多表实时穿透） */
  queryCostMs: number;           // 性能埋点（P95 < 3s 验证，BR-205）
  /** 数据截止时间（BR-210 新鲜度 < 1h） */
  dataAsOf: string;
  nodes: Array<{
    nodeType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'COST' | 'PROFIT';
    nodeId: string;
    nodeLabel: string;
    platform?: PlatformType;
    /** 节点聚合指标（成本/利润字段按角色矩阵脱敏，R7/R9 返回 null） */
    metrics?: {
      sessionCount?: number;
      gmv?: number | null;
      netProfit?: number | null;
      totalCost?: number | null;
    };
  }>;
  edges: Array<{ fromNodeId: string; toNodeId: string }>;
  /** 明细模式：场次级明细列表 */
  detailList?: PageResult<{
    sessionCode: string;         // 19 位 IMS 编码（链路唯一锚点）
    sessionTitle: string;
    platform: PlatformType;
    realnamePersonId: number;
    realnameName: string;
    accountId: number;
    accountNo: string;
    assetIds: number[];
    gmv: number | null;
    netProfit: number | null;
    statPeriod: string;
  }>;
}
```

**错误码**：1181（穿透查询超时降级——返回慢查询提示，引导缩小范围）、1008（无数据权限，入口不在本人数据范围内）。

**审计**：每次穿透查询留痕（查询人/入口/耗时，DC-T-R4）。

#### 2.1.3 GET /admin-api/ims/dc/trace/detail/{sessionCode} — 场次明细下钻

**请求**（Path）：`sessionCode`（19 位 IMS 编码）→ **响应** `data`：

```typescript
interface DcSessionDetailResp {
  sessionCode: string;
  sessionTitle: string;
  platform: PlatformType;
  /** V1 台账：下播数据 */
  liveData: { gmv: number; refund: number; uv: number | null; durationMinutes: number | null };
  /** V3 财务：三级利润（三级口径，BR-108） */
  profit: { grossProfit: number | null; operatingProfit: number | null; netProfit: number | null; netProfitRate: number | null; calcVersion: number };
  /** V3 财务：成本明细 */
  costDetail: Array<{ costItem: string; amount: number | null }>;   // R7/R9 脱敏 null
  /** 链路人员 */
  persons: Array<{ userId: number; userName: string; roleType: string }>;
  account: { accountId: number; accountNo: string; nickname: string };
  assetIds: number[];
  dataAsOf: string;
}
```

#### 2.1.4 GET /admin-api/ims/dc/trace/aggregate — 聚合模式

**请求**（Query）：`{ entryType: string; entryId: string; aggregateBy: 'PERSON' | 'ACCOUNT' | 'TEAM' | 'IP_GROUP'; dateRange?: [string, string] }` → **响应** `data`：`Array<{ dimensionValue: string; dimensionLabel: string; sessionCount: number; gmv: number | null; totalCost: number | null; netProfit: number | null; personCount: number }>`（聚合与明细双模式，BR-209 口径）。

#### 2.1.5 GET /admin-api/ims/dc/trace/export — 链路报告导出

**请求**（Query）：`{ entryType: string; entryId: string; format: 'XLSX' | 'PDF' }` → **响应** `data`：`{ downloadUrl: string; expiresIn: number }`（OSS 60 秒签名 URL）。

#### 2.1.6 GET /admin-api/ims/dc/trace/perf-metrics — 穿透性能统计

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ p95Ms: number; p99Ms: number; targetP95Ms: 3000; queryCount: number; slowQueries: Array<{ queryId: string; entryLabel: string; costMs: number; occurredAt: string }>; dailyPressureTestPassed: boolean }`（V3-C3：每日自动压测 10 条典型穿透用例，P95 超标自动告警并出具慢查询清单）。

### 2.2 利润反查（DC-002）

#### 2.2.1 GET /admin-api/ims/dc/profit-trace/list — 利润记录列表（分页）

**请求**（Query）：`PageParam` + `{ statPeriod?: string; platform?: PlatformType; accountId?: number; ipGroupId?: number; responsibleUserId?: number; calcStatus?: string }`

**响应** `data`：`PageResult<DcProfitTraceVO>`

```typescript
interface DcProfitTraceVO {
  sessionCode: string;           // 反查锚点（19 位 IMS 编码）
  sessionTitle: string;
  platform: PlatformType;
  /** 三级利润（V3 FIN-002 口径（第 28~33 周先行），DECIMAL(14,2)） */
  netProfit: number | null;
  grossProfit: number | null;
  operatingProfit: number | null;
  /** 利润计算版本（V3 FIN 重算版本对齐，重算后旧版本仅审计可见，DC-P-R2） */
  calcVersion: number;
  statPeriod: string;
  isAbnormal: boolean;           // 联动 V3 FIN-002 异常标记（第 28~33 周先行）
}
```

#### 2.2.2 GET /admin-api/ims/dc/profit-trace/{sessionCode} — 单场利润反查链路

**响应** `data`：

```typescript
interface DcProfitTraceChainResp {
  sessionCode: string;
  /** BR-209 反查路径：利润 → 场次 ID → 账号/资产/责任人/实名人 → 成本明细 */
  chain: {
    profit: DcProfitTraceVO;
    session: { sessionCode: string; sessionTitle: string; liveDate: string; platform: PlatformType };
    account: { accountId: number; accountNo: string; nickname: string };
    assets: Array<{ assetId: number; assetCode: string }>;
    responsibleUser: { userId: number; userName: string };
    realnamePersons: Array<{ userId: number; userName: string; roleType: string }>;
    costDetail: Array<{ costItem: string; amount: number | null }>;      // V3 ims_fin_cost 引用（第 28~33 周先行）
  };
  queryCostMs: number;           // 同 BR-205 性能约束
  dataAsOf: string;
}
```

#### 2.2.3 GET /admin-api/ims/dc/profit-trace/aggregate — 聚合反查

**请求**（Query）：`{ aggregateBy: 'PERSON' | 'ACCOUNT' | 'TEAM' | 'IP_GROUP' | 'MONTH'; dimensionValue?: string; dateRange?: [string, string] }` → **响应** `data`：`Array<{ dimensionValue: string; dimensionLabel: string; netProfit: number | null; grossProfit: number | null; sessionCount: number; children?: Array<DcProfitTraceVO> }>`（聚合后逐层下钻到场次，DC-P-R1 聚合与明细双模式）。

#### 2.2.4 GET /admin-api/ims/dc/profit-trace/abnormal — 异常利润下钻清单

**请求**（Query）：`PageParam` + `{ platform?: string; dateRange?: [string, string] }` → **响应** `data`：`PageResult<DcProfitTraceVO & { peerAvgRate: number; sigma: number; deviationSigma: number; abnormalCostItem?: string }>`（联动 V3 FIN-002 异常标记（第 28~33 周先行），直达到异常成本项）。

#### 2.2.5 GET /admin-api/ims/dc/profit-trace/share-detail/{sessionCode} — 分成明细反查

**响应** `data`：`Array<{ shareTarget: 'DAREN' | 'REALNAME' | 'TEAM'; targetRefId: number; targetRefName: string; shareBase: number | null; shareAmount: number | null; status: string }>`（V3 ims_fin_share_result 引用（第 28~33 周先行）；分成明细反查仅 R1/R3/R4/R9（脱敏）可见，DC-P-R4）。

**错误码**：1182（无分成明细查看权限）。

### 2.3 全链路数据看板（DC-003）

#### 2.3.1 GET /admin-api/ims/dc/dashboard/overview — 经营总览

**请求**（Query）：`{ statPeriod: string; dimensionType?: 'PLATFORM' | 'IP_GROUP' | 'TEAM' }` → **响应** `data`：

```typescript
interface DcDashboardOverviewResp {
  totalGmv: number | null;
  totalCost: number | null;
  netProfit: number | null;
  sessionCount: number;
  accountCount: number;
  assetCount: number;
  /** 数据截至时间戳（BR-210，DC-D-R1 小时级刷新） */
  dataAsOf: string;
  refreshedAt: string;
}
```

#### 2.3.2 GET /admin-api/ims/dc/dashboard/health — 链路健康度

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ assetRelationCompleteRate: number; target: 98; isAlarm: boolean; trend: Array<{ statDate: string; completeRate: number }>; accountDigitizationRate: number; ledgerTraceRate: number }>`（资产关联完整率按全链路口径计算（BR-208，V1 BR-003 升级），低于 98% 看板红色告警，DC-D-R3）。

#### 2.3.3 GET /admin-api/ims/dc/dashboard/dimension — 维度切换

**请求**（Query）：`{ statPeriod: string; dimensionType: 'PLATFORM' | 'ACCOUNT' | 'IP_GROUP' | 'TEAM' | 'REALNAME'; drillTo?: string }` → **响应** `data`：`Array<{ dimensionValue: string; dimensionLabel: string; gmv: number | null; netProfit: number | null; sessionCount: number; children?: Array<{ dimensionValue: string; gmv: number | null; netProfit: number | null; sessionCount: number }> }>`（下钻路径复用 DC-001/DC-002 能力，最深到场次明细，DC-D-R2）。

#### 2.3.4 GET /admin-api/ims/dc/dashboard/list — 看板列表

**响应** `data`：`Array<{ id: number; dashboardName: string; ownerUserId: number; ownerName: string; status: 'ENABLED' | 'DISABLED'; refreshCron: string; refreshedAt: string }>`。

#### 2.3.5 POST /admin-api/ims/dc/dashboard — 创建看板

**请求**：`{ dashboardName: string; layoutConfig: Array<{ widgetKey: string; widgetType: 'METRIC_CARD' | 'TREND_CHART' | 'RANK_LIST' | 'HEALTH_PANEL'; position: { x: number; y: number; w: number; h: number }; config: Record<string, unknown> }>; refreshCron?: string }` → **响应** `data`：`{ id: number; dashboardName: string }`（指标卡/图表自定义布局，管理员与运营总监，DC-D-R1）。

#### 2.3.6 PUT /admin-api/ims/dc/dashboard/{id} — 编辑布局

**请求**：同创建（不含 name 可选）→ **响应**：`data: null`。

#### 2.3.7 GET /admin-api/ims/dc/dashboard/freshness — 数据新鲜度

**响应** `data`：`{ businessToDwsDelayMinutes: number; target: 60; isAlarm: boolean; syncTaskStatus: Array<{ taskName: string; lastRunAt: string; status: 'SUCCESS' | 'DELAYED' | 'FAILED'; delayMinutes: number }>; dataAsOf: string }`（BR-210：业务台账 → 聚合层延迟 < 1 小时（T+1 深度汇总））。

---

## 3. 状态机与业务约束

### 3.1 状态机

本模块为**只读分析域**（无业务状态机）。仅看板配置有启用态：

```
看板：ENABLED ↔ DISABLED（缓存数据按 refreshCron 小时级刷新，页面展示"数据截至"时间戳）
同步任务：SUCCESS → DELAYED（>1h 告警）→ FAILED（断点续传，V3-A2）
```

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-205 | 穿透 P95 < 3s（P99 < 8s，六种入口任意穿透） | 2.1.2 queryCostMs / 2.1.6 |
| BR-208 | 资产关联完整率 > 98%（全链路复核口径） | 2.3.2 health |
| BR-209 | 利润反查：利润→场次→账号/资产/责任人/实名人→成本明细 | 2.2.2 / 2.2.3 |
| BR-210 | 聚合层新鲜度 < 1 小时（T+1 深度汇总） | 2.3.7 freshness |
| DC-T-R1 | 聚合层预 join，避免在线多表实时穿透 | 2.1.2 实现约束 |
| DC-T-R2 | 场次 ID 为链路唯一锚点（19 位 IMS 编码） | 全模块 sessionCode |
| DC-T-R3 | 数据新鲜度 < 1h | 同 BR-210 |
| DC-T-R4 | 穿透查询审计留痕 | 2.1.2 审计 |
| DC-P-R1 | 反查聚合与明细双模式 | 2.2.3 |
| DC-P-R2 | 利润以 V3 FIN（第 28~33 周先行）计算版本为准（旧版本仅审计可见） | 2.2.1 calcVersion |
| DC-P-R3 | 反查性能同 BR-205 | 2.2.2 queryCostMs |
| DC-P-R4 | 分成明细仅 R1/R3/R4/R9（脱敏）可见 | 2.2.5 错误码 1182 |
| DC-D-R1 | 看板小时级刷新 + "数据截至"时间戳 | 2.3.1 dataAsOf |
| DC-D-R2 | 下钻复用 DC-001/002，不重复建设 | 2.3.3 |
| DC-D-R3 | 完整率 < 98% 红色告警 | 2.3.2 isAlarm |
| DC-D-R4 | 缓存数据按人预过滤 | 2.3.x 服务端过滤 |
| V3-A1 | ODS/DWD/DWS/ADS 分层（宽表直查） | 2.1.2 聚合层实现 |
| V3-A2 | 同步延迟 > 1h 告警；同步任务纳入 V2 集群化调度 | 2.3.7 |
| V3-A3 | 数仓层只读，不回写业务表 | 全模块（只读域） |
| V3-A4 | 四类核心维度 ID DWD 层统一清洗 | 聚合层构建约束 |
| V3-C2 | 链路末端 DWS/ADS 直查 + DWD 映射缓存 + V1 分层渐进兜底 | 2.1.2 实现约束 |
| V3-C3 | 每日自动压测 10 条典型用例 | 2.1.6 dailyPressureTestPassed |
| V3-D1~D3 | 读写分离：报表/穿透/大屏读走从库（延迟 < 3s，超标切回主库） | 全模块（DAO 层标注，V3-D4 V2 预备） |
| 9.2 安全 | 穿透/利润反查全量审计；成本/利润按矩阵脱敏（R7/R9 受限） | 全模块服务端脱敏 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 穿透查询页（入口搜索框 + 链路图画布） | 入口搜索（实名人/账号/资产/场次/责任人/IP 组） | GET /dc/trace/entry |
| 穿透查询页-链路图 | 全链路穿透（链路图渲染，节点点击下钻） | POST /dc/trace/query |
| 场次明细下钻抽屉（DetailDrawer） | 场次明细（下播数据+成本+利润三级） | GET /dc/trace/detail/{sessionCode} |
| 穿透查询页-聚合/明细切换 | 聚合模式（按人/账号/团队汇总） | GET /dc/trace/aggregate |
| 穿透报告导出 | 链路报告导出（Excel/PDF） | GET /dc/trace/export |
| 穿透性能监控页 | P95/P99 统计与慢查询清单（BR-205 验证） | GET /dc/trace/perf-metrics |
| 利润反查列表页（QueryBar + 表格） | 利润记录列表（多维筛选） | GET /dc/profit-trace/list |
| 利润反查链路页（反查路径图） | 单场反查链路展开 | GET /dc/profit-trace/{sessionCode} |
| 利润聚合下钻区 | 聚合反查（按人/账号/团队逐层下钻） | GET /dc/profit-trace/aggregate |
| 异常利润页 | 异常下钻清单（直达异常成本项） | GET /dc/profit-trace/abnormal |
| 分成明细抽屉 | 分成明细反查（权限受限提示） | GET /dc/profit-trace/share-detail/{sessionCode} |
| 数据看板-总览区 | 经营总览指标卡（周期切换） | GET /dc/dashboard/overview |
| 数据看板-健康度区 | 链路健康度（BR-208 趋势，<98% 红色告警） | GET /dc/dashboard/health |
| 数据看板-维度下钻区 | 维度切换下钻（最终到场次明细/穿透链路） | GET /dc/dashboard/dimension |
| 看板管理页（R1/R4） | 看板列表 / 创建 / 布局编辑 | GET /dc/dashboard/list、POST /dc/dashboard、PUT /dc/dashboard/{id} |
| 看板-新鲜度标识 | 数据截至时间展示（BR-210 延迟告警） | GET /dc/dashboard/freshness |

（全文完）
