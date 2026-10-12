# ASSET - 资产管理 页面规格

> 依据：《IMS第一期PRD-V1.md》5.5~5.7（ASSET-001~003）、《共享技术规范-数据库与API.md》第 7/8 章、《共享技术规范-分期技术约束.md》1.2（穿透查询分层方案）。
> **完整版叠加**：公司/手机/卡 CRUD 见《MASTER-主数据-页面规格.md》；资产登记表只扩展列（IR-04）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/asset`。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 资产台账列表 | `/ims/asset/ledger` | 一级菜单页 | ASSET-001 入口 |
| P1-附 正向穿透详情 | 台账行下钻（抽屉/详情层，并入 P1） | 二级页面（Drawer 100% 或全屏详情） | ASSET-001 |
| P3 反向穿透查询 | `/ims/asset/reverse` | 一级菜单页 | ASSET-002 |
| P4 关联校验中心 | `/ims/asset/verify` | 一级菜单页 | ASSET-003 |

通用 UI 约定：查询条件一行紧凑排布；交互优先内联抽屉（Drawer）不跳转；敏感字段脱敏（成本金额 R9 角色见 ¥\*\*\*\*、实名人证件号前 3 后 4）；状态 tag 语义色；穿透结果 > 500 条分页 + 引导导出（V1-B3）。

**穿透技术口径（V1，9A 分层查询，前端须按层渐进渲染）**：
- L1 资产详情（单表）→ L2 绑定账号列表 → L3 实名人 → L4 使用场次 → L5 成本汇总；
- 每层独立接口独立加载，单层 P95 < 300ms，全链 P95 < 1.5s（V1-B4）；
- 前端骨架按层渲染：L1 先出，L2~L5 各自 loading，失败各层独立重试，不阻塞整体。

---

## P1. 资产台账列表（正向穿透入口）

### 1. 页面概述
- 路由路径：`/ims/asset/ledger`
- 页面级别：一级菜单页
- 依赖模块：已有资产登记数据（增量消费不重建）；ASSET-001 穿透；ACCT（账号责任人信息展示）
- 权限矩阵引用（PRD 4.2）：ASSET-001/002：R1 R（全量）、R2 R/W（全量）、R3 R（全量，成本只读）、R4 R（全量）、R5 R（关联账号资产）、R9 R（全量，成本脱敏）；R6/R7/R8/R10 不可见

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 资产编号 | 资产类型 | 责任人 | 状态 | [查询] [重置]  [导出台账] |
+------------------------------------------------------------------+
| 表格: 资产编号 | 资产名称 | 类型 | 规格 | 状态 | 当前责任人 | 绑定账号数 |
|       | 采购日期 | 操作[正向穿透][反向关联详情]                          |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
正向穿透（行操作）→ 打开 P2 穿透详情（全屏 Drawer 90%）
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AssetLedgerPageReq {
  pageNo: number; pageSize: number;
  assetCode?: string;
  assetType?: AssetType;
  ownerPersonId?: number;      // 责任人
  status?: AssetStatus;
}
interface AssetForwardDetailReq { assetId: number; }

// 响应类型（L1~L5 分层，各层独立接口）
interface AssetLedgerItem {           // L1
  assetId: number;
  assetCode: string;                  // 业务编码
  assetName: string;
  assetType: AssetType;
  spec: string;
  status: AssetStatus;                // 在用/已归还/已报废/待审核
  ownerPersonId: number;
  ownerPersonName: string;
  purchaseDate: string;
  bindCount: number;                  // 绑定账号数
}
interface AssetBindItem {             // L2 绑定账号列表
  bindId: number;
  accountId: number;
  accountNo: string;                  // 冗余字段（V1 分层冗余设计）
  nickname: string;
  platform: string;
  bindType: 'HOLD' | 'GUARANTEE' | 'CUSTODY';   // 持有/担保/代管
  bindStatus: 'ACTIVE' | 'RELEASED';
  effectiveTime: string;
}
interface VerifiedPersonItem {        // L3 实名人
  personId: number;                   // sys_user_id
  personName: string;
  deptName: string;
  idCardMasked: string;               // 前 3 后 4，服务端脱敏
}
interface AssetSessionItem {          // L4 使用场次
  sessionId: string;                  // 场次 ID（IMS+yyyyMMdd+平台码+序列）
  platform: string;
  title: string;
  liveDate: string;
  personRole: string;                 // 主播/中控/运营
}
interface AssetCostSummary {          // L5 成本汇总（V1 为 session 冗余累计）
  totalCost: number;                  // DECIMAL(12,2)
  totalRevenue: number;
  sessionCount: number;
}
interface AssetTraceNode {            // 关系图数据（trace 接口）
  nodeType: 'ASSET' | 'ACCOUNT' | 'PERSON' | 'SESSION' | 'COST';
  nodeId: string;
  label: string;
  children?: AssetTraceNode[];
}

// 枚举类型
type AssetType = 'PHONE' | 'COMPUTER' | 'CAMERA' | 'LIGHT' | 'STUDIO' | 'MATERIAL' | 'OTHER';
type AssetStatus = 'IN_USE' | 'RETURNED' | 'SCRAPPED' | 'PENDING_REVIEW';
// 在用 / 已归还 / 已报废 / 待审核（全局规范第 4 章权威枚举；列表展示四态）
```

### 4. 交互流程

#### 4.1 页面加载
1. 骨架屏（查询行即显 + 表格占位行 ×10）→ `GET /asset/ledger/page`；
2. R5 角色请求自动携带数据范围（仅关联本人负责账号的资产，服务端过滤，前端不传参）；
3. 失败 → "加载失败，点击重试"；空数据 → 引导（见 8）。

#### 4.2 核心操作流程
**A. 正向穿透（行操作 [正向穿透]）**
1. 点击 → 打开穿透详情（Drawer 90% 宽或全屏层），不跳转路由；
2. 分层渐进加载：
   - 第 1 步：L1 资产基本信息卡（顶部固定）；
   - 第 2 步：L2 绑定账号列表（可展开行：每账号下钻其实名人与场次）；
   - 第 3 步：L3 实名人卡片区（点击人物 → 查看 L4 该人参与场次）；
   - 第 4 步：L4 场次列表（点击场次 → LIVE 台账详情联动）；
   - 第 5 步：L5 成本汇总卡（R9 角色金额脱敏 ¥\*\*\*\*；R3 可见；R5 不可见该层）；
3. 视图切换：[层级表格视图]（默认）/ [关系图视图]（树图渲染 AssetTraceNode）；
4. 查询审计：服务端记录 query_user_id（ASSET-F-R3），前端无感知；
5. 可选 [导出穿透报告 PDF]（见 8）。

**B. 导出台账**
- 顶部 [导出台账] → 当前筛选条件导出 Excel；R9 角色导出中成本列脱敏，导出行为留审计。

**C. 反向关联详情**
- 行操作 [反向关联] → 打开反向穿透抽屉（P3 页面的入口单实体模式，见 P3 规格复用）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| assetCode | Input | 否 | 空 | 资产编号精确/前缀匹配 |
| assetType | Select | 否 | 空 | 资产类型字典 |
| ownerPersonId | PersonSelect | 否 | 空 | 责任人（人员搜索选择器） |
| status | Select | 否 | 空 | 在用/已归还/已报废/待审核 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| assetCode | 资产编号 | 140 | — | 等宽字体 |
| assetName | 资产名称 | 160 | — | — |
| assetType | 类型 | 100 | — | 字典翻译 |
| spec | 规格 | 150 | — | 超 1 行省略 |
| status | 状态 | 90 | — | tag：在用(绿)/已归还(蓝)/已报废(红)/待审核(黄) |
| ownerPersonName | 当前责任人 | 110 | — | 离职冻结人员黄色名字 + 图标 |
| bindCount | 绑定账号数 | 100 | ✓ | 数字，0 时灰字 |
| purchaseDate | 采购日期 | 110 | ✓ | yyyy-MM-dd |
| actions | 操作 | 180 | — | [正向穿透][反向关联] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与逻辑 |
|-----------|------|-----------|
| 正向穿透详情 | Drawer 90%（可全屏） | 结构：顶部 L1 信息卡（资产编号/名称/类型/规格/状态/责任人/采购日期）→ Tab [层级视图][关系图]；层级视图为可展开多级表格（asset→account→person→session），成本汇总卡固定底部；每层独立 loading/失败重试；底部 [导出穿透报告 PDF]；全部只读无编辑表单 |
| 反向关联抽屉 | Drawer 720px | 单实体反向结果（见 P3），复用反向穿透结果组件 |

### 8. 错误处理
- 网络超时：列表区失败占位重试；穿透详情内各层独立重试不阻塞其他层；
- 无数据引导：空列表显示"暂无资产记录，可从已有资产登记数据同步或联系行政管理员录入"；
- 权限不足（1008/403）：菜单与操作按钮按矩阵隐藏；R5 访问非关联资产穿透 → 服务端返回 1008，前端提示"您无权查看该资产"；
- 导出失败（5005）：提示"报告生成失败，请稍后重试或联系管理员"；穿透结果 > 500 条（V1-B3）→ 提示"结果较多，已分页展示，建议导出（异步生成，完成后站内通知领取）"。

### 9. BR 业务规则覆盖
- **BR-003（资产关联完整率 > 98%）**：列表"绑定账号数"为 0 或责任人空的行灰标"待补关联"，卡片指标见 P4 校验中心；
- **BR-018（登记关联校验）**：穿透详情内 [发起关联校验] 按钮（R1/R2）调用 P4 校验，不一致项在层级表格中红色标记（联动 ASSET-003）。

---

## P1-附：正向穿透详情（已并入 P1 抽屉规格）

以 P1 第 7 节穿透详情抽屉为准（分层 L1~L5 渐进渲染、双视图、逐层重试、审计留痕、脱敏规则）。补充：
- 关系图视图：根节点=资产，向下依次账号→实名人→场次→成本；节点点击弹出浮层显示节点明细；节点过多（>100）自动折叠二级以下；
- 骨架顺序严格：L1 即刻渲染 → L2/L3 并行 → L4/L5 依赖前层结果，全部加载完顶部显示"穿透耗时 XXXms"（供性能观察，非用户必须）。

---

## P3. 反向穿透查询页

### 1. 页面概述
- 路由路径：`/ims/asset/reverse`
- 页面级别：一级菜单页（三种入口维度统一在一页）
- 依赖模块：ASSET 台账、ACCT 账号台账、LIVE 场次、AUTH 人员；ASSET-003 校验联动
- 权限矩阵引用：同 ASSET-002（R1/R2 全量、R3 只读、R4 全量、R5 本人负责、R9 全量成本脱敏）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 入口维度选择（Segmented）: [按责任人] [按账号] [按场次ID]            |
+------------------------------------------------------------------+
| 查询行（随维度切换）:                                               |
|   责任人维度: 人员选择器(必填) | 是否含历史已归还(Switch,默认开)     |
|   账号维度:   账号搜索器(必填)                                       |
|   场次维度:   场次ID输入(必填,格式校验 IMS+14位)                     |
|                                               [查询] [重置]  [导出] |
+------------------------------------------------------------------+
| 结果区（可展开层级表格）:                                             |
| 资产编号 | 资产名称 | 类型 | 绑定方式 | 资产状态 | 绑定时间 | 关联一致性 |
|   行可展开 → 资产详情卡 + 该资产关联的其他人/账号/场次                |
+------------------------------------------------------------------+
| 汇总条: 命中资产 N 条（在用 X / 已归还 Y / 已报废 Z） [发起关联校验]   |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AssetReverseByPersonReq {
  personId: number;                  // 必填
  includeHistory?: boolean;          // 默认 true（含历史已归还）
  pageNo: number; pageSize: number;
}
interface AssetReverseByAccountReq {
  accountId: number;                 // 必填
  pageNo: number; pageSize: number;
}
interface AssetReverseBySessionReq {
  sessionId: string;                 // 必填，19 位场次 ID
  pageNo: number; pageSize: number;
}
interface AssetVerifyTriggerReq {
  entryType: 'PERSON' | 'ACCOUNT' | 'SESSION';
  entryId: number | string;
}

// 响应类型
interface AssetReverseItem {
  assetId: number;
  assetCode: string;
  assetName: string;
  assetType: AssetType;
  bindType: 'HOLD' | 'GUARANTEE' | 'CUSTODY';
  assetStatus: AssetStatus;           // 复用全局枚举；反向三态展示=在用/已归还/已报废（ASSET-B-R1）
  bindTime: string;
  bindAccountId?: number;
  consistencyFlag?: 'CONSISTENT' | 'INCONSISTENT' | 'UNVERIFIED';   // 校验结果
  frozen?: boolean;                  // 离职人员结果冻结态（ASSET-B-R2）
}
interface AssetReverseSummary {
  total: number; inUse: number; returned: number; scrapped: number;
  frozenPerson: boolean;
}

// 枚举类型
type ReverseEntryType = 'PERSON' | 'ACCOUNT' | 'SESSION';
type ConsistencyFlag = 'CONSISTENT' | 'INCONSISTENT' | 'UNVERIFIED';
```

### 4. 交互流程

#### 4.1 页面加载
无默认查询结果；页面加载即渲染维度选择器与空态引导（"请选择入口维度并输入查询条件"）。

#### 4.2 核心操作流程
**A. 反向查询**
1. 选择入口维度 → 对应查询行组件切换；
2. 输入必填入口 → [查询]；
3. 结果区展示层级表格 + 汇总条；资产状态区分在用/已归还/已报废三色 tag（ASSET-B-R1）；
4. 离职人员查询 → 顶部黄色横幅"该人员离职归还未闭环，资产展示冻结态"（ASSET-B-R2），冻结资产行灰显 + 锁图标；
5. 行展开 → 该资产完整关联上下文（其他绑定人/账号/场次）。

**B. 发起关联校验（可选，R1/R2 可见）**
1. [发起关联校验] → `POST /asset/verify/run`（携带当前查询入口）→ loading；
2. 返回后结果表 consistencyFlag 列更新：不一致项整行红框 + [查看差异]（跳 P4 或打开差异抽屉）。

**C. 导出**
- [导出] 导出当前结果 Excel（脱敏规则同正向）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| entryType | Segmented | 是 | PERSON | 入口维度 |
| personId | PersonSelect | 维度=责任人时必填 | 空 | 人员搜索 |
| accountId | AccountSelect | 维度=账号时必填 | 空 | 账号搜索（平台+昵称+编号） |
| sessionId | Input | 维度=场次时必填 | 空 | 19 位格式校验：`^IMS\d{8}[A-Z]{3}\d{4}$` |
| includeHistory | Switch | 否 | 开 | 仅责任人维度显示 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| assetCode | 资产编号 | 140 | — | 等宽字体 |
| assetName | 资产名称 | 160 | — | — |
| assetType | 类型 | 100 | — | 字典翻译 |
| bindType | 绑定方式 | 100 | — | 持有/担保/代管 |
| assetStatus | 资产状态 | 100 | — | tag：在用(绿)/已归还(蓝)/已报废(红)；冻结行整体灰显 |
| bindTime | 绑定时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| consistencyFlag | 关联一致性 | 110 | — | tag：一致(绿)/不一致(红)/未校验(灰) |
| expand | 展开 | 40 | — | 行展开显示关联上下文 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与逻辑 |
|-----------|------|-----------|
| 资产关联上下文抽屉（行展开内嵌） | 行内展开区 | 展示该资产绑定关系全景：责任人（含历史）、关联账号、参与场次、成本摘要（按角色脱敏）；只读 |
| 校验差异详情弹窗 | Modal 640px | 不一致项明细：记录 ID、不一致字段对比（左登记值/右穿透值）、[转异常工单]（跳 P4） |

### 8. 错误处理
- 网络超时：结果区失败重试；
- 入口不存在（1002）：表单字段下方内联错误"人员/账号/场次不存在"；
- 场次 ID 格式错误：前置正则校验拦截，不发请求；
- 权限不足：R5 查非本人负责 → 1008 提示；
- 查询性能保护：万级资产量 < 2s（ASSET-B-R3），超时前端提示"查询超时，请缩小范围"。

### 9. BR 业务规则覆盖
- **BR-018（登记数据关联校验）**：反向结果"关联一致性"列 + 发起校验按钮 + 不一致转工单，是 BR-018 的页面落点；
- **BR-015（离职归还强制闭环）**：离职人员反向查询冻结态展示（ASSET-B-R2），闭环后自动恢复正常（服务端状态驱动，前端按 frozen 渲染）。

---

## P4. 关联校验中心页（ASSET-003）

### 1. 页面概述
- 路由路径：`/ims/asset/verify`
- 页面级别：一级菜单页，含"指标看板 / 批次列表 / 工单处理"三区
- 依赖模块：ASSET-001/002（校验数据源）、AUTH 工作台（工单督办待办）
- 权限矩阵引用：ASSET-003：R1 R/W/D（全量）、R2 R/W（全量）、R4 R、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 指标看板区: [资产关联完整率 98.6%(目标>98%)] [校验一致率 99.2%(目标>98%)] |
|            [待处理异常工单 N] [本周批次 N]      [手动触发校验]        |
+------------------------------------------------------------------+
| Tab: [批次列表] [异常工单]                                        |
| 批次Tab 查询行: 批次号 | 校验类型 | 状态 | 时间范围 | [查询][重置]     |
| 批次Tab 表格: 批次号 | 校验类型 | 校验总数 | 异常数 | 任务状态 |       |
|   修复责任人 | 批次时间 | 操作[查看明细][派发工单]                    |
| 异常工单Tab 表格: 工单号 | 批次号 | 关联对象(资产/账号/人) | 不一致字段  |
|   | 状态(待派发/修复中/已闭环/逾期) | 修复责任人 | 限期 | 操作[处理][复审] |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface VerifyBatchPageReq {
  pageNo: number; pageSize: number;
  batchNo?: string; verifyType?: VerifyType; taskStatus?: VerifyTaskStatus;
  timeRange?: [string, string];
}
interface VerifyRunReq { verifyType?: VerifyType; clientToken: string; }   // 手动触发
interface VerifyTaskUpdateReq {
  taskId: number;
  action: 'DISPATCH' | 'REPAIRING' | 'RECHECK' | 'CLOSE';
  ownerUserId?: number;     // 派发时必填
  remark?: string;
}

// 响应类型
interface VerifyMetricsResp {
  assetIntegrityRate: number;      // BR-003 完整率 0~1
  consistencyRate: number;         // BR-018 一致率 0~1
  pendingTaskCount: number;
  weekBatchCount: number;
  trend: { date: string; integrityRate: number; consistencyRate: number }[];   // 近 30 天趋势
}
interface VerifyBatchItem {
  id: number; batchNo: string;
  verifyType: VerifyType;
  totalCount: number; errorCount: number;
  taskStatus: VerifyTaskStatus;
  ownerUserId: number; ownerName: string;
  batchTime: string;
}
interface VerifyErrorItem {
  id: number; taskId: number;
  batchNo: string;
  refType: 'asset_account' | 'asset_person' | 'asset_session';
  refLabel: string;                 // 资产编号/账号编号/姓名
  inconsistentFields: { field: string; registeredValue: string; actualValue: string }[];
  taskStatus: VerifyTaskStatus;
  ownerName: string;
  deadline: string;
  overdue: boolean;
}

// 枚举类型
type VerifyType = 'asset_account' | 'asset_person' | 'asset_session';
type VerifyTaskStatus = 'PENDING_DISPATCH' | 'REPAIRING' | 'CLOSED';
```

### 4. 交互流程

#### 4.1 页面加载
1. 骨架屏 → 并行 `GET /asset/verify/metrics` + `GET /asset/verify/batches`；
2. 指标卡未达标（<98%）红色高亮 + tooltip 说明目标值。

#### 4.2 核心操作流程
**A. 手动触发校验（R1/R2）**
1. [手动触发校验] → 弹窗选择校验类型（全选默认）→ `POST /asset/verify/run`（clientToken 幂等）；
2. 定时任务为每周一凌晨全量 + 每日增量（VERIFY-R1），手动触发作为补偿；按钮防重复（执行中禁用）；
3. 完成后批次列表刷新 + 消息提示"校验完成，共发现 N 处异常"。

**B. 异常工单流转**
1. 批次行 [查看明细] → 异常工单 Tab 过滤该批次；
2. [处理] 打开工单处理抽屉：
   - 待派发：指定修复责任人（人员选择，必填）+ 限期（默认 3 个工作日，VERIFY-R2）→ DISPATCH；
   - 修复中：责任人上传修复说明（文字，必填 ≤512 字）→ RECHECK，进入复审；
   - 复审（R1/R2）：[复核通过闭环] / [退回继续修复]；
3. 逾期工单（超过限期）红框 + 自动升级部门负责人（VERIFY-R2，服务端），前端逾期 badge 显示。

**C. 指标看板**
- 指标卡点击 → 展开近 30 天趋势折线（同页面下方展开区，不跳转）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| batchNo | Input | 否 | 空 | 批次号精确 |
| verifyType | Select | 否 | 空 | 资产↔账号 / 资产↔人员 / 资产↔场次 |
| taskStatus | Select | 否 | 空 | 待派发/修复中/已闭环 |
| timeRange | DateRangePicker | 否 | 近 30 天 | 批次时间 |

### 6. 表格列定义

批次列表：

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| batchNo | 批次号 | 160 | — | 等宽字体 |
| verifyType | 校验类型 | 140 | — | 字典翻译 |
| totalCount | 校验总数 | 90 | — | 千分位 |
| errorCount | 异常数 | 90 | — | >0 红色加粗 |
| taskStatus | 任务状态 | 110 | — | tag：待派发(黄)/修复中(蓝)/已闭环(绿) |
| ownerName | 修复责任人 | 110 | — | 未派发显示"—" |
| batchTime | 批次时间 | 160 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 160 | — | [查看明细][派发工单] |

异常工单：

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| taskId | 工单号 | 120 | — | 等宽字体 |
| refLabel | 关联对象 | 180 | — | 资产编号/账号/姓名 |
| inconsistentFields | 不一致字段 | 自适应 | — | "责任人、绑定账号" 逗号串，tooltip 展开对比详情 |
| taskStatus | 状态 | 110 | — | tag 同上；逾期加红色"逾期 N 天"角标 |
| ownerName | 修复责任人 | 110 | — | — |
| deadline | 限期 | 110 | ✓ | yyyy-MM-dd；逾期红色 |
| actions | 操作 | 140 | — | [处理][复审] 按状态显示 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 工单处理抽屉 | Drawer 560px | 只读头：工单号/批次/关联对象/不一致字段对比表（登记值 vs 穿透值）；表单区按状态：待派发 → ownerUserId（必填）+ deadline（必填，默认+3 工作日）；修复中 → fixRemark（必填 ≤512 字）；复审 → 复审意见（必填）；提交逻辑见 4.2-B |
| 手动触发校验弹窗 | Modal 420px | verifyType 复选（默认全选）；执行说明文案；确认后按钮防重 |
| 趋势展开区 | 内联展开 | 近 30 天完整率/一致率双折线，无表单 |

### 8. 错误处理
- 网络超时：看板与列表独立重试；
- 触发校验失败（5006 调度失败）：提示"调度繁忙，请稍后重试"；
- 派发人员不存在/无权限：内联表单错误；
- 空数据：看板显示"暂无校验数据，请先触发一次校验"引导按钮。

### 9. BR 业务规则覆盖
- **BR-003（资产关联完整率 > 98%）**：指标看板首卡常显完整率及目标线，未达标红色；
- **BR-018（登记关联校验 > 98%，不一致转工单）**：批次/工单全流程（校验→派发→限期修复→复审闭环→一致率统计）即 BR-018 页面闭环；VERIFY-R2 逾期升级通过工作台待办 + 站内信送达部门负责人。

---

## 模块通用备注
- 本模块 3 个一级页面 + 1 个穿透详情大抽屉（P2 并入 P1），共 6 个抽屉/弹窗（正向穿透详情、反向上下文展开、差异弹窗、工单处理、触发校验弹窗、趋势展开区）。
- 穿透分层渲染（L1~L5）为前端强制约定：禁止一次性串行阻塞加载，必须逐层独立请求独立渲染（对应 V1-B1/B3/B4）。
- 所有查询行为服务端审计留痕（ASSET-F-R3），前端无需额外埋点。
