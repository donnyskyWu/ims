# ASSET - 资产管理 API 契约

> **模块范围**：07 资产管理（V1，第 5~9 周，补齐类）——ASSET-001 正向穿透查询、ASSET-002 反向穿透查询、ASSET-003 登记数据关联校验。
> **权威依据**：《IMS第一期PRD-V1.md》5.5~5.7；《共享技术规范-数据库与API.md》7.2/7.3/8.3。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》。字段一律 camelCase。本模块为查询校验类为主，台账登记复用既有 07 资产登记能力，仅消费不重复建设。

### 台账列表走既有 07 资产登记端点映射表

> 页面规格的资产台账列表（`/asset/ledger/page`）不由本契约定义，走**既有 07 系统资产登记端点**：`GET /admin-api/ims/asset/ledger/page`（分页：pageNum/pageSize/资产编码/类型/状态/责任人筛选，返回 `{code:0, data:{total, records:[...]}}`）。该端点**由既有系统提供、本契约不重复定义**；本契约仅覆盖其上的穿透/反查/校验能力。

---

## 1. API 总览表（共 12 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/asset/forward/detail/{assetId}` | 资产穿透详情（分层聚合，L1~L5） | R1/R2/R3/R4/R5（关联）/R9（成本脱敏） |
| 2 | GET | `/admin-api/ims/asset/forward/trace/{assetId}` | 穿透链路关系图数据 | 同上 |
| 3 | GET | `/admin-api/ims/asset/forward/export/{assetId}` | 导出穿透报告（异步导出） | R1/R2/R4 |
| 4 | GET | `/admin-api/ims/asset/reverse/by-person/{userId}` | 按人反查资产（分页） | R1/R2/R3/R4/R5（本人）/R9 |
| 5 | GET | `/admin-api/ims/asset/reverse/by-account/{accountId}` | 按账号反查资产（分页） | 同上 |
| 6 | GET | `/admin-api/ims/asset/reverse/by-session/{sessionId}` | 按场次反查资产（分页） | 同上 |
| 7 | GET | `/admin-api/ims/asset/reverse/export` | 导出反查结果（异步导出） | R1/R2/R4 |
| 8 | POST | `/admin-api/ims/asset/verify/run` | 手动触发关联校验 | R1/R2 |
| 9 | GET | `/admin-api/ims/asset/verify/batches` | 校验批次列表（分页） | R1/R2/R4/R9 |
| 10 | GET | `/admin-api/ims/asset/verify/errors` | 异常明细（分页） | R1/R2/R4/R9 |
| 11 | PUT | `/admin-api/ims/asset/verify/task/{id}` | 校验工单状态流转 | R1/R2 |
| 12 | GET | `/admin-api/ims/asset/verify/metrics` | 完整率/一致率指标看板 | R1/R2/R4/R9 |

**分层穿透补充端点**（V1-B1 穿透禁止单 SQL 关联 6+ 表，按层分步；前端渐进渲染）：`GET /asset/forward/detail/{assetId}` 支持分层参数 `?layers=L1,L2,L3`，或由前端直接消费 detail 聚合包按层渐进渲染。

---

## 2. 接口明细

### 2.1 正向穿透查询（ASSET-001）

#### 2.1.1 GET /admin-api/ims/asset/forward/detail/{assetId} — 资产穿透详情（聚合）

**请求**（Path + Query）：

```typescript
interface AssetForwardDetailReq {
  assetId: number;               // Path
  /** 是否附带 L4/L5 场次与成本层（前端渐进加载） */
  withSessionLayer?: boolean;
  withFinanceLayer?: boolean;
}
```

**响应** `data`（分层聚合包，单层 P95 < 300ms，整体 P95 < 1.5s，V1-B4）：

```typescript
interface AssetForwardDetailResp {
  /** L1 资产详情（单表） */
  asset: AssetLedgerVO;
  /** L2 绑定账号列表（asset_bind，含冗余编码） */
  bindAccounts: AssetBindVO[];
  /** L3 实名人（mapping + Redis 缓存 30min） */
  verifiedPersons: PersonBriefVO[];
  /** L4 参与场次（live_person + live_session） */
  liveSessions: LiveSessionBriefVO[];
  /** L5 财务汇总（V1 为 ims_live_session 冗余累计列，V2 切 finance_profit 预计算表） */
  financeSummary: {
    totalCost: number;           // 成本脱敏时返回 -1 并置 costMasked=true
    totalRevenue: number;
    costMasked: boolean;         // R9 等角色置 true，前端显示 "***"
  };
}

interface AssetLedgerVO {
  id: number;
  assetCode: string;             // 唯一业务编码
  assetType: string;             // 资产类型（设备/物料等字典）
  spec: string;
  status: AssetStatus;           // IN_USE / RETURNED / SCRAPPED / PENDING_REVIEW
  purchaseDate: string;          // yyyy-MM-dd
  subjectId: number;             // 多主体预留（V1=0，接口不透出）
}

interface AssetBindVO {
  bindId: number;
  assetId: number;
  assetCode: string;             // 冗余列（V1 分层冗余设计）
  accountId: number;
  accountNo: string;             // 冗余列
  platform: PlatformType;
  verifiedPersonId: number;
  bindType: 'HOLD' | 'GUARANTEE' | 'CUSTODY';  // 持有/担保/代管
  bindStatus: 'ACTIVE' | 'RELEASED';
  effectiveTime: string;
}

interface PersonBriefVO {
  userId: number;
  nickname: string;
  mobileMasked: string;          // 138****5678（ASSET-F-R2 脱敏）
  idCardMasked?: string;         // 110***********5678
  deptNames: string[];
}

interface LiveSessionBriefVO {
  sessionId: number;
  sessionCode: string;           // IMS+yyyyMMdd+平台码+序列
  platform: PlatformType;
  title: string;
  status: LiveSessionStatus;
  ownerPersonId: number;         // 冗余列
  actualStart?: string;
  actualEnd?: string;
}
```

**错误码**：1011（资产不存在）、1008（无数据权限）、1013（穿透层级超限）。

#### 2.1.2 GET /admin-api/ims/asset/forward/trace/{assetId} — 穿透链路关系图数据

**响应** `data`（供 TraceGraph 组件渲染，最多 5 层，ASSET-F-R1）：

```typescript
interface TraceGraphResp {
  nodes: Array<{
    id: string;                  // 形如 "asset:1001" / "person:88" / "session:2001"
    label: string;
    layer: 'ASSET' | 'PERSON' | 'ACCOUNT' | 'SESSION' | 'FINANCE';
    maskedLabel?: string;        // 敏感节点脱敏标签
  }>;
  edges: Array<{ from: string; to: string; relation: string }>;
}
```

#### 2.1.3 GET /admin-api/ims/asset/forward/export/{assetId} — 导出穿透报告

**请求**：Path `assetId`。`assetId=0` 时 Query `realnameId` 走实名人最深链，Query `layers` 与 `GET /asset/forward/trace/{assetId}` 相同。

**响应** `data`（#74）：

```typescript
{
  exportTaskId: string;
  message: string;          // 穿透报告已生成
  downloadUrl: string;      // 回执下载链接
  fileName: string;         // asset_forward_report.pdf
}
```

文件为 **PDF**（页面规格「导出穿透报告 PDF」）。正文先写标题「资产穿透报告」，其后每行与穿透抽屉一致：`实名人 · {label}`、`第N层 · {label}`。层级超限 **1013**，资产不存在 **1011**，实名人不存在 **1500**，文件落盘失败 **5005**。这些情况下不返回下载链接。每次导出记穿透审计（ASSET-F-R3）。

**回执下载**（同一导出资源，不是新业务接口）：`GET /admin-api/ims/asset/forward/export/file?token={exportTaskId}`，`Content-Type: application/pdf`，`Content-Disposition` 文件名 `asset_forward_report.pdf`。链接 300 秒、仅本人；过期 **1002**，他人 **1008**。字节同时写入服务端目录 `data/ims-files/asset/{yyyyMM}/`。

### 2.2 反向穿透查询（ASSET-002）

#### 2.2.1 GET /admin-api/ims/asset/reverse/by-person/{userId} — 按人反查资产

**请求**：Path `userId` + Query `PageParam` + `{ statusFilter?: AssetStatus; includeHistory?: boolean }`

**响应** `data`：`PageResult<ReverseAssetItemVO>`

```typescript
interface ReverseAssetItemVO {
  assetId: number;
  assetCode: string;
  assetType: string;
  status: AssetStatus;           // ASSET-B-R1：在用/已归还/已报废
  /** 绑定关系摘要 */
  bindType: 'HOLD' | 'GUARANTEE' | 'CUSTODY';
  effectiveTime: string;
  /** 离职人员冻结态标记（ASSET-B-R2） */
  frozen: boolean;
  frozenReason?: string;
  relatedAccountNo?: string;
}
```

同构端点：`/by-account/{accountId}`（按账号查绑定设备/物料）、`/by-session/{sessionId}`（按场次查涉及资产）。查询性能：万级资产 < 2 秒（ASSET-B-R3）。

#### 2.2.2 GET /admin-api/ims/asset/reverse/export — 导出反查结果

**请求**（Query）：`{ entryType: 'PERSON' | 'ACCOUNT' | 'SESSION'; entryId: number; accountNo?: string; sessionCode?: string }`。`entryId>0` 时按主键解析（使用人 / 账号 / 场次）。账号 `entryId=0` 时用 `accountNo`，场次 `entryId=0` 时用 `sessionCode`，与现有反查入口一致。

**响应** `data`（#74）：`{ exportTaskId: string; message: string; downloadUrl: string; fileName: string }`。文件为 **xlsx**，`fileName=asset_reverse_report.xlsx`。行与反查表一致：首行汇总「命中 N 条（在用 X / 已归还 Y / 已报废 Z）」，表头「资产编号 / 名称 / 状态 / 绑定 / 账号」，状态与绑定用页面中文（待审核 / 在用 / 已归还 / 已报废，持有 / 担保 / 代管）。使用人不存在、账号不存在、场次不存在 → **1500**。入口类型不对、场次编号格式不对或场次编号为空 → **1001**。落盘失败 **5005**。

**回执下载**：`GET /admin-api/ims/asset/reverse/export/file?token={exportTaskId}`，`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`。过期 **1002**，他人 **1008**。字节同时写入 `data/ims-files/asset/{yyyyMM}/`。

### 2.3 登记数据关联校验（ASSET-003）

#### 2.3.1 POST /admin-api/ims/asset/verify/run — 手动触发校验

**请求**：

```typescript
interface AssetVerifyRunReq {
  /** 校验范围类型 */
  verifyTypes: Array<'asset_account' | 'asset_person' | 'asset_session'>;
  /** 全量 or 增量 */
  scope: 'FULL' | 'INCREMENT';
}
```

**响应**：`{ batchNo: string; triggeredAt: string }`。定时校验：每周一凌晨全量 + 每日增量（VERIFY-R1）。

#### 2.3.2 GET /admin-api/ims/asset/verify/batches — 校验批次列表（分页）

**请求**（Query）：`PageParam` + `{ verifyType?: string; taskStatus?: VerifyTaskStatus; timeRange?: [string, string] }`

```typescript
type VerifyTaskStatus = 'PENDING_DISPATCH' | 'REPAIRING' | 'CLOSED';  // 0 待派发 / 1 修复中 / 2 已闭环
```

**响应** `data`：`PageResult<AssetVerifyBatchVO>`

```typescript
interface AssetVerifyBatchVO {
  id: number;
  batchNo: string;
  verifyType: 'asset_account' | 'asset_person' | 'asset_session';
  totalCount: number;
  errorCount: number;
  /** 异常明细（记录 ID + 不一致字段），量大仅返回摘要+明细走 /errors */
  errorDetailSummary?: string;
  taskStatus: VerifyTaskStatus;
  ownerUserId?: number;          // 修复责任人
  createdAt: string;
}
```

#### 2.3.3 GET /admin-api/ims/asset/verify/errors — 异常明细（分页）

**请求**（Query）：`PageParam` + `{ batchNo: string }`

**响应** `data`：`PageResult<{ id: number; batchNo: string; recordId: number; recordType: string; inconsistentFields: string[]; description: string }>`

#### 2.3.4 PUT /admin-api/ims/asset/verify/task/{id} — 工单状态流转

**请求**：`{ taskStatus: VerifyTaskStatus; ownerUserId?: number; remark?: string }` → **响应**：`data: null`。异常工单 3 个工作日内闭环，逾期升部门负责人（VERIFY-R2）。

#### 2.3.5 GET /admin-api/ims/asset/verify/metrics — 完整率/一致率指标

**响应** `data`：

```typescript
interface AssetVerifyMetricsResp {
  /** BR-003 目标 > 98% */
  relationCompleteRate: number;
  /** BR-018 目标 > 98% */
  consistencyRate: number;
  trend: Array<{ date: string; completeRate: number; consistencyRate: number }>;
}
```

### 2.4 采购批量入台账（#68 · E2E-S5-01）

复用既有 `POST /asset/ledger` 的登记口径，不另建资产资源。办公设备 / 直播设备页「采购导入」上传 CSV。

#### 2.4.1 POST /admin-api/ims/asset/ledger/import — 采购 CSV 入台账

**请求**：`multipart/form-data`，字段 `file`（CSV，UTF-8 或 GBK）。表头必含资产名称与采购日期，列名可用英文或中文：

| 列 | 英文 | 中文 | 规则 |
|----|------|------|------|
| 资产编号 | assetCode | 资产编号 / 编号 | 可空则生成；库内或本文件内重复 → 该行 **1012**，字段 `assetCode` |
| 资产名称 | assetName | 资产名称 / 名称 | 必填，空 → 该行 **1001**，字段 `assetName` |
| 资产类型 | assetType | 资产类型 / 类型 | 空则 `OFFICE`；不在 `dict_asset_type` → 该行 **1503**，字段 `assetType` |
| 规格 | spec | 规格 | 超过 128 → 该行 **1001**，字段 `spec` |
| 采购日期 | purchaseDate | 采购日期 | 必填，`yyyy-MM-dd`，否则该行 **1001**，字段 `purchaseDate` |

文件为空、无法识别编码、缺必填列、没有数据行、超过 200 行 → **1001**，不入库。

**响应** `data`（业务码 **0**，含部分成功）：

```typescript
interface AssetPurchaseImportResp {
  batchNo: string;          // PB + 时间戳
  fileName: string;
  total: number;
  successCount: number;
  failCount: number;
  /** 成功与失败并存。已成功行不因后续失败行回滚（G7 例外） */
  partial: boolean;
  errors: Array<{
    rowNo: number;          // 文件行号，表头为第 1 行
    field: 'assetCode' | 'assetName' | 'assetType' | 'spec' | 'purchaseDate';
    fieldLabel: string;
    code: number;
    message: string;
    assetCode: string;
  }>;
  imported: Array<{
    id: number;
    assetCode: string;
    assetName: string;
    status: 'PENDING_REVIEW';
    purchaseDate: string;
    purchaseBatchNo: string;
  }>;
}
```

成功行：`ims_asset_ledger.status=PENDING_REVIEW`，`purchase_batch_no=batchNo`，时间线 `REGISTER` / 说明「采购入台账」。批次头写入 `ims_asset_purchase_batch.error_detail`。

---

## 3. 状态机与业务约束

### 3.1 状态机

**资产状态（AssetStatus，反向穿透三态，ASSET-B-R1）**：

```
PENDING_REVIEW（登记待审）──领用──▶ IN_USE（在用）──使用（状态不变，须有 USE）──▶ 归还 ──▶ RETURNED ──报废──▶ SCRAPPED
```

#63 生命周期：在用再领用 **1012**；未使用就归还、或未归还就报废、或终态再领用 → **1015**。直接从在用报废不在本切片。冻结展示仍属离职闭环，本切片不做。

#65 穿透（办公设备页，不新开路由）：`ims_asset_hierarchy.level` 从实名人向下计资产层。登记可带 `realnameId` 或 `parentAssetCode`（仍走 `POST /asset/ledger`）。`GET /asset/forward/trace/{assetId}`：`assetId>0` 返回该资产上行至实名人的链路；`assetId=0` 且 `realnameId` 取该实名人最深链路。任一层 `level>5`，或 `layers` 超出 L1–L5 → **1013**。`GET /asset/ledger/{id}` 与 `GET /asset/forward/detail/{assetId}` 的 `holders` 按领用/归还/报废给出使用人三态。`GET /asset/reverse/by-person/{userId}` 按当前责任人或历史领用事件列出资产及当前状态。

#72 账号 / 场次反查（办公/直播设备页「账号/场次反查」，不新开路由）：`ims_asset_bind`。`POST /asset/ledger` 可选 `accountId` 或 `accountNo`、`sessionCode`（`IMS`+8 位日期+3 位平台码+4 位序号）、`bindType`（`HOLD`/`GUARANTEE`/`CUSTODY`，默认 `HOLD`）。账号不存在或场次不存在 → **1500**（本系统 **1002** 表示会话无效，入口缺失不用 1002）。场次编号格式不对或场次不属于所填账号 → **1001**。只填场次时账号取该场次的账号。成功时时间线 `REGISTER` 说明含「绑定账号」「绑定场次」。`GET /asset/reverse/by-account/{accountId}`：`accountId=0` 时用查询参数 `accountNo`。`GET /asset/reverse/by-session/{sessionId}` 接受场次主键或场次编号。结果带资产状态与汇总 `inUse`/`returned`/`scrapped`。绑定在归还后仍保留，以便已归还资产继续被反查。关联校验不在本片。导出见 #74。

#74 导出（办公设备页，不新开路由）：`GET /asset/forward/export/{assetId}` 生成与抽屉链路一致的 PDF。`GET /asset/reverse/export` 生成与使用人 / 账号 / 场次反查表一致的 xlsx。第 6 层或 `layers` 超出 L1–L5 → **1013**。资产不存在 **1011**。使用人、账号、场次或实名人不存在 **1500**。办公设备正向穿透抽屉有「导出穿透报告」，账号/场次反查抽屉增加「按使用人」和「导出」。

#75 登记关联校验（ASSET-003，办公设备页，不新开路由）：`POST /asset/ledger` 在写入前校验实名人、账号、场次。不存在 **1500**；账号已停用（非 `IN_USE`/`IN_POOL`）、场次已取消或其他不允许状态、实名人已停用 **1501**；场次编号格式不对、场次不属于该账号、账号或场次不属于所选实名人 **1001**。`POST /asset/verify/run` 按 `asset_person` / `asset_account` / `asset_session` 扫描台账并记批次；未关联实名人或账号记异常，未绑定场次不算场次异常。`PUT /asset/verify/task/{id}` 只允许 `PENDING_DISPATCH → REPAIRING → CLOSED`，批次不存在或跳跃 **1014**。`GET /asset/forward/detail/{assetId}` 默认带回场次层 `liveSessions` 与成本层 `financeSummary`（优先 `ims_fin_profit`，否则下播报告 GMV / 投放成本）；`withSessionLayer=false` 或 `withFinanceLayer=false` 时对应层为空。角色键 `R9` 时 `costMasked=true` 且 `totalCost=-1`。

#68 采购入台账（办公/直播设备页「采购导入」，不新开路由）：`POST /asset/ledger/import`。合法行待审核入台账并记 `purchaseBatchNo`；非法行返回文件行号与字段；`partial=true` 时已入库行不回滚。见 §2.4。

**校验工单（VerifyTaskStatus）**：`PENDING_DISPATCH →（派发）REPAIRING →（修复复审）CLOSED`；逾期（3 工作日）自动升级推送。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-003 | 资产关联完整率 > 98% | 2.3.5 metrics.completeRate |
| BR-018 | 登记关联校验一致率 > 98%，不一致入异常工单 | 2.3.x 全部 |
| ASSET-F-R1 | 穿透 ≤ 5 层、单次 < 3s | 2.1.1/2.1.2 分层结构 |
| ASSET-F-R2 | 敏感字段按角色脱敏（成本金额/证件号） | PersonBriefVO 脱敏字段 + costMasked |
| ASSET-F-R3 | 穿透查询审计留痕 | 2.1.1 后端审计写入 |
| ASSET-B-R1 | 反向结果三态区分 | ReverseAssetItemVO.status |
| ASSET-B-R2 | 离职人员结果冻结态展示 | frozen/frozenReason |
| ASSET-B-R3 | 万级资产 < 2s | 索引约束（V1-B2：关联字段必建索引） |
| V1-B1~B4 | 分层/冗余/预计算/缓存/P95 | 2.1.1 响应结构即分层设计 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 办公/直播设备台账（#63） | 登记 / 领用 / 使用 / 归还 / 报废 | POST /asset/ledger、POST /asset/ledger/{id}/checkout\|use\|return\|scrap；列表 GET /asset/ledger/page，办公页 BFF `GET /corp/device/office/page?assetType` 固定 OFFICE，直播页合并 LIVE+SHOOT |
| 办公/直播设备台账（#68） | 采购 CSV 批量入台账；行级错误；部分成功 | POST /asset/ledger/import |
| 资产台账列表页（走既有 07 资产登记端点，见头部映射表） | 台账列表查询（分页/筛选） | GET /asset/ledger/page |
| 资产台账列表页（复用既有 07 登记列表） | 行点击打开穿透详情抽屉（DetailDrawer 渐进渲染 L1→L5） | GET /asset/forward/detail/{assetId} |
| 资产穿透详情抽屉-关系图 Tab | 渲染穿透链路图（TraceGraph） | GET /asset/forward/trace/{assetId} |
| 资产穿透详情抽屉-操作按钮 | 导出穿透报告（ConfirmDialog → 异步导出提示） | GET /asset/forward/export/{assetId} |
| 反向穿透查询页（QueryBar 选择入口维度：人员/账号/场次） | 按人/账号/场次查询资产 | GET /asset/reverse/by-person/{userId} 等 3 个端点 |
| 反向穿透结果区 | 不一致项标红（联动 ASSET-003）、导出 | GET /asset/reverse/export |
| 关联校验页（批次 Tab，QueryBar+表格） | 批次列表/异常明细查询 | GET /asset/verify/batches、GET /asset/verify/errors |
| 关联校验页-操作 | 手动触发校验（ConfirmDialog） | POST /asset/verify/run |
| 关联校验页-工单抽屉 | 派发/流转工单状态 | PUT /asset/verify/task/{id} |
| 关联校验指标看板 | 完整率/一致率趋势图 | GET /asset/verify/metrics |

（全文完）
