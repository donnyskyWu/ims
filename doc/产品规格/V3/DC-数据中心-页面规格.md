# DC - 穿透查询 页面规格（V3，12 模块，第 28~35 周）

> **版本**：v1.1.0（2026-09-29 · 用户走查 #13）
> **侧栏 IA（v2.6.13）**：**数据决策 → 数据分析 → 穿透查询**（模块 12 · code `DC`）；**仅 P1 入菜单**。DC-002/003 迁出本叶（见 PRD §5.4）；**P4 性能监控无菜单**，路由 **`/ims/dc/trace/perf`**（R1/R9）。
> **模块范围（菜单内）**：DC-001 账号穿透查询。**域外仍有效**：DC-002 API `/admin-api/ims/dc/profit-trace/*`（菜单 **11 场次财务 → 利润反查** · 路由 **`/ims/fin/profit-trace`** · perm `ims:fin:profit-trace:query`）、DC-003 `/dc/dashboard/*`（入口 **数据报表 · 大屏**，v2.6.27 走查 #21：大屏 = 报表类型 `DASHBOARD`，无独立「大屏配置」菜单）。
> **UX 参照（BLOCKED）**：产品期望对齐 OPS「**线索挖掘**」（选源头 → 关联关系逐层下钻 + 图/表同屏）。**本仓库无** 线索挖掘 PRD/UX/API；P1 以本文 + API 契约为 SSOT，逐层下钻 = 面包屑 + **节点/关联 chip 触发再次** `POST /dc/trace/query`（新 entryType/entryId），**禁止**发明 graph/lineage 专用 API。
> **权威依据**：《IMS第三期PRD-V3.md》5.4~5.6；《DC-数据中心-API契约.md》（18 接口，1181~1182 错误码段）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**：P1 穿透查询（Web 画布，**数据分析 L3**）｜P2 利润反查（Web，**菜单：11 财务**）｜P3 全链路数据看板（Web，**入口：数据报表 · 大屏**）｜P4 穿透性能监控（Web，R1/R9，无菜单）。

## 0.1 导航（走查 #21 · v2.6.27 · 与前 #13/#17 一致处保留）

**侧栏路径**：数据决策 → **数据分析** → **穿透查询**（L3；路由 `/ims/dc/trace` · P1；**页内无 Tab**）。  
**域外入口**：P2 → 11 场次财务；P3 → **数据报表 · 大屏**（报表类型 `DASHBOARD`）；P4 无菜单。与 **预览与下钻**、**ASSET 台账穿透** 菜单不合并。
> **模块核心口径**：**穿透性能 P95 < 3s（P99 < 8s，BR-205）**——聚合层预 join 宽表直查（V3-C2），queryCostMs 前端展示、超时降级提示（1181）；**只读分析域**——数据单向同步不回写（V3-A3），无任何写操作；**数据新鲜度 < 1h**（BR-210，"数据截至"时间戳常驻展示）；**场次 ID（19 位 IMS 编码）贯穿全链路为唯一锚点**（DC-T-R2）；穿透查询全量审计留痕（DC-T-R4）。
> **角色脱敏**：成本/利润字段按矩阵脱敏——R7（本人链路）/R9（全量）视角成本与利润相关金额字段服务端返回 null/`"***"`，前端原样渲染为 "—"。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase（`session_code → sessionCode`、`ip_group_id → ipGroupId`）。
- 枚举：`PlatformType`（全局权威）。本域为只读分析域，**无业务状态机**（仅看板 ENABLED/DISABLED、同步任务 SUCCESS/DELAYED/FAILED）。
- 金额：GMV/成本/利润 DECIMAL(14,2)，¥ 前缀千分位两位小数；**脱敏渲染约定**：null → "—"（R7/R9 受限字段，服务端脱敏）。
- sessionCode：19 位 IMS 编码（`IMS + yyyyMMdd + 3位平台码 + 4位序列`），code 样式渲染，全链路唯一锚点。
- 权限矩阵引用 PRD 5.4~5.6.5：R1/R2/R3/R4/R9 全量（R9 脱敏）、R5 本团队、R6 内容域（看板）、R7 本人链路（成本脱敏）；看板配置 R1/R4；穿透性能监控 R1/R9。
- 性能 UI 约定：所有穿透查询结果区右上角显示 `耗时 {queryCostMs}ms`（BR-205 埋点可视化）；> 3000ms 橙色警示。
- 读走从库（V3-D1~D3 读写分离，DAO 层约定，页面无感知；从库延迟超标自动切主库）。

---

# P1 穿透查询（DC-001）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | **`/ims/dc/trace`**（菜单：**穿透查询**，无二级子菜单） |
| 页面级别 | 二级（模块主页面，画布型） |
| 前置依赖 | V3 数仓聚合层（DWS/ADS 宽表）已同步（V3-A1~A4）；前置模块 07/08/10/11 数据积累 |
| 权限 | 查看（全只读）：R1/R2/R3/R4/R9（全量，R7/R9 成本脱敏）/R5（本团队）/R7（本人链路）；无写操作 |
| 用户 | 管理层（链路核查）/ 财务 R3 / 运营 R5（本团队链路排查） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 穿透查询            数据截至 2025-05-26 14:00（BR-210 <1h ✓绿）           │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 入口搜索区（GET /dc/trace/entry）                                       │
│ ┌──────────────────────────────────────────────────────────────┐        │
│ │ 🔍 输入关键词（实名人/账号/资产/场次ID/责任人/IP组）  [穿透查询] │        │
│ │ 下拉联想: [👤实名人 张三·主播] [📱账号 DY12345·抖音]           │        │
│ │           [📦资产 ZC00123] [🎬场次 IMSS202505260320042]        │        │
│ │           [👤责任人 李四] [🌐IP组 华东一组]   (entryType Tag)   │        │
│ └──────────────────────────────────────────────────────────────┘        │
├──────────────────────────────────────────────────────────────────────────┤
│ 模式切换: [链路图 GRAPH] [明细列表 DETAIL] [聚合 AGGREGATE]  日期范围:   │
│ [RangePicker]                       查询耗时: 286ms ✓ (P95<3s 达标)    │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 链路图画布（POST /dc/trace/query, mode=GRAPH）                          │
│   ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐        │
│   │实名人│───▶│账号  │───▶│场次  │───▶│成本  │───▶│利润  │        │
│   │张三  │    │DY123│    │IMS… │    │¥xx  │    │¥xx  │        │
│   │     │    │     │    │42场  │    │     │    │     │        │
│   └─────┘    └─────┘    └──┬──┘    └─────┘    └─────┘        │
│        ┌───────────────┐  │                                      │
│        │资产 ZC00123×3 │──┘（节点=可点击下钻；节点下方聚合指标）      │
│        └───────────────┘                                          │
│   节点点击 → 联动侧栏；场次节点点击 → 场次明细抽屉（§7.1）              │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 明细模式（mode=DETAIL）：场次明细表（分页）                             │
│ [场次ID|场次名称|平台|实名人|账号|关联资产|GMV|净利润|数据周期]           │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 聚合模式（GET /dc/trace/aggregate）：维度选择[按人/账号/团队/IP组]      │
│ 汇总表: [维度值|场次数|GMV|总成本|净利润|涉及人数]                        │
├──────────────────────────────────────────────────────────────────────────┤
│ 底部: [导出链路报告 XLSX/PDF]（GET /dc/trace/export）                    │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（契约内联） =====
/** 六种穿透入口 */
type DcEntryType = 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP';
/** 查询模式 */
type DcTraceMode = 'GRAPH' | 'DETAIL';
/** 聚合维度 */
type DcAggregateBy = 'PERSON' | 'ACCOUNT' | 'TEAM' | 'IP_GROUP';
/** 链路图节点类型 */
type DcNodeType = 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'COST' | 'PROFIT';

// ===== 请求 =====
interface DcEntrySearchReq {
  keyword: string;
  entryType?: DcEntryType;               // 可选限定
  limit?: number;                        // 默认 10
}

interface DcTraceQueryReq {
  entryType: DcEntryType;
  entryId: string;                       // userId / 账号ID / 资产ID / 19位场次编码等
  mode: DcTraceMode;
  pageNo?: number;
  pageSize?: number;
  dateRange?: [string, string];
}

interface DcAggregateReq {
  entryType: string;
  entryId: string;
  aggregateBy: DcAggregateBy;
  dateRange?: [string, string];
}

// ===== 响应 =====
interface DcEntryVO {
  entryType: DcEntryType;
  entryId: string;
  entryLabel: string;
  platform?: PlatformType;
  hint: string;                          // 补充提示（如"主播 · 华东团队"）
}

interface DcTraceGraphResp {
  /** 性能埋点（BR-205：P95 < 3s 验证） */
  queryCostMs: number;
  /** 数据截止时间（BR-210 新鲜度 < 1h） */
  dataAsOf: string;
  nodes: Array<{
    nodeType: DcNodeType;
    nodeId: string;
    nodeLabel: string;
    platform?: PlatformType;
    /** 节点聚合指标（R7/R9 成本利润字段服务端脱敏 null） */
    metrics?: {
      sessionCount?: number;
      gmv?: number | null;
      netProfit?: number | null;
      totalCost?: number | null;
    };
  }>;
  edges: Array<{ fromNodeId: string; toNodeId: string }>;
  detailList?: PageResult<{
    sessionCode: string;                 // 19 位 IMS 编码（链路唯一锚点）
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

interface DcSessionDetailResp {
  sessionCode: string;
  sessionTitle: string;
  platform: PlatformType;
  /** V1 台账：下播数据 */
  liveData: { gmv: number; refund: number; uv: number | null; durationMinutes: number | null };
  /** V3 财务：三级利润（BR-108 口径） */
  profit: {
    grossProfit: number | null;
    operatingProfit: number | null;
    netProfit: number | null;
    netProfitRate: number | null;
    calcVersion: number;                 // V3 FIN 重算版本对齐（DC-P-R2）
  };
  /** 成本明细（R7/R9 脱敏 null → 渲染 "—"） */
  costDetail: Array<{ costItem: string; amount: number | null }>;
  persons: Array<{ userId: number; userName: string; roleType: string }>;
  account: { accountId: number; accountNo: string; nickname: string };
  assetIds: number[];
  dataAsOf: string;
}

interface DcTraceAggregateVO {
  dimensionValue: string;
  dimensionLabel: string;
  sessionCount: number;
  gmv: number | null;
  totalCost: number | null;
  netProfit: number | null;
  personCount: number;
}
```

## 4. 交互流程

**页面加载**：
1. 顶部"数据截至"时间戳：`GET /dc/dashboard/freshness` 复用（或由 query 响应 dataAsOf 更新）；延迟 <1h 绿 ✓，>1h 红告警（BR-210）。
2. 入口搜索框聚焦输入 → 防抖 300ms → `GET /dc/trace/entry`（keyword）→ 下拉联想（六类入口混合，entryType Tag 区分：实名人/账号/资产/场次/责任人/IP 组）。

**核心操作**：
- **选源头**：六种 entryType  pills 或联想下拉（`GET /dc/trace/entry`）；选中后写入面包屑第 0 层「源头：{label}」。
- **按关联下钻（走查 #13）**：当前焦点节点下方展示 **可选关联关系** chip（如「持有账号」「绑定资产」「参与场次」「归集成本」「核算利润」）；点击 chip → 以目标节点为 **新 entryId** 再次 `POST /dc/trace/query`（mode 保持），面包屑追加「关联：{关系名} → {节点标签}」；点击面包屑前缀 → 截断 path 并重查对应层。
- **穿透查询**：选中联想项（或回车取第一项）→ `POST /dc/trace/query`（entryType+entryId，mode 按视图）：
  - **分栏（默认）**：左 **链路图** + 右 **明细表** 同屏联动（节点点击高亮表行；表行点击聚焦图节点）。
  - **链路图模式**：nodes+edges 渲染层级画布；节点下方聚合指标（¥ 千分位；脱敏 null → "—"）；**`耗时 {queryCostMs}ms`**，>3000ms 橙色（BR-205）。
  - **明细模式**：分页场次明细表（sessionCode 锚点列）。
  - 1181 超时降级 → 顶部橙色提示条；1008 → toast 并清空画布。
- **节点下钻**：画布节点点击 → 更新焦点 + 可选关联 chip；**场次节点** → 场次明细抽屉（§7.1）。
- **聚合模式**：切 Tab → `GET /dc/trace/aggregate`（aggregateBy 切换刷新）→ 汇总表；行点击可再穿透（以该维度值为入口重新 query，聚合与明细双模式 BR-209 口径）。
- **导出**：底部 [导出链路报告]（XLSX/PDF 二选一）→ `GET /dc/trace/export` → 返回 服务端鉴权下载链接 → 前端直接下载。
- **审计留痕**：每次穿透查询服务端自动留痕（查询人/入口/耗时，DC-T-R4），页面无感知（P4 可查）。

## 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| keyword | 搜索联想框 | string | 六类入口混合联想（GET entry） |
| mode | Tab | DcTraceMode | 链路图/明细列表/聚合三 Tab |
| dateRange | RangePicker | [string,string] | 场次日期范围（缩小范围保性能） |
| aggregateBy | Radio | DcAggregateBy | 聚合 Tab 下：按人/账号/团队/IP 组 |

## 6. 表格列定义

**明细模式**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 场次 ID | sessionCode | code 样式 19 位，点击开明细抽屉 |
| 场次名称 | sessionTitle | 文本 |
| 平台 | platform | PlatformType Tag |
| 实名人 | realnameName | 文本 |
| 账号 | accountNo | code 小字 |
| 关联资产 | assetIds | `{n} 项` Tooltip 展开资产编码 |
| GMV | gmv | ¥ 千分位；null "—" |
| 净利润 | netProfit | ¥ 千分位（负数红括号）；null "—"（R7/R9） |
| 数据周期 | statPeriod | yyyy-MM-dd |

**聚合模式**：维度值/维度标签、场次数、GMV ¥、总成本 ¥（脱敏 "—"）、净利润 ¥、涉及人数；行点击再穿透。

## 7. 抽屉/弹窗规格

### 7.1 场次明细下钻抽屉（DetailDrawer，右滑 880px）

- **结构**（对应 DcSessionDetailResp）：
  1. **头部**：sessionCode（code 样式，19 位锚点）+ sessionTitle + platform Tag + `数据截至 {dataAsOf}`。
  2. **下播数据区**（V1 台账）：GMV / 退款 / UV / 时长（Descriptions 4 项，¥ 千分位）。
  3. **三级利润区**（V3 财务 BR-108）：毛利 ¥ / 经营利润 ¥ / 净利润 ¥ / 净利率 %；附 `计算版本 v{calcVersion}`（利润以 V3 FIN 当前版本为准，DC-P-R2——重算后旧版本仅审计可见，本页只展示当前版）。
  4. **成本明细区**（V3 ims_fin_cost 引用）：[成本项 | 金额 ¥]；R7/R9 视角 amount=null 行金额渲染 "—"（脱敏）。
  5. **链路人员区**：persons（userName+roleType Tag）+ 账号信息（accountNo+nickname）+ 关联资产编码列表。
- 数据：`GET /dc/trace/detail/{sessionCode}`。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1181 | 穿透超时降级 | 顶部橙色提示条 + 建议缩小日期范围 |
| 1008 | 无数据权限（入口不在本人范围） | toast 提示，清空画布 |
| dataAsOf > 1h | 新鲜度告警 | 顶部时间戳红色 + "同步延迟告警（BR-210）" |
| 画布渲染失败 | 数据异常 | 空态 + 重试按钮 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-205（P95<3s） | queryCostMs 展示 + >3s 橙色 + 1181 降级 |
| BR-208（完整率，看板侧） | P3 健康度区（本页联动下钻） |
| BR-209（反查路径） | 链路图节点序（实名人→账号→资产/场次→成本→利润） |
| BR-210（新鲜度 <1h） | 顶部数据截至时间戳 |
| DC-T-R1（聚合层预 join） | 页面说明（性能保障来源文案） |
| DC-T-R2（场次 ID 唯一锚点） | sessionCode 全链路展示 |
| DC-T-R4（审计留痕） | 服务端自动，P4 可查 |
| 9.2 安全（脱敏） | R7/R9 null → "—" 渲染约定 |

---

# P2 利润反查（DC-002）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | **`/ims/fin/profit-trace`**（L3：**场次财务 → 利润反查**；**不在** 数据分析侧栏） |
| API | `/admin-api/ims/dc/profit-trace/*`（不变） |
| 页面级别 | 二级（三 Tab：利润列表 / 聚合下钻 / 异常清单） |
| 前置依赖 | V3 FIN-002 利润计算数据（第 28~33 周先行）+ 聚合层同步（M0a：07/08/10 第 28~30 周；M0b：FIN 数据第 31~32 周接入）——FIN 数据接入前 DC-002 允许降级空态 |
| 权限 | 查看：R1/R3（主责）/R4/R9（脱敏）/R5（本团队）/R7（本人场次）；分成明细仅 R1/R3/R4/R9（1182 拦截其他角色）；R3 可标记待核（联动 V3 FIN 复核） |
| 用户 | 财务 R3（主责）/ 管理层 |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 利润反查    数据截至 14:00 ✓   ┌─[利润列表]─┬─[聚合下钻]─┬─[异常清单]─┐  │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ Tab1 利润列表（GET /dc/profit-trace/list）                              │
│ QueryBar(单行): [统计周期 MonthPicker][平台 Select][账号 Input][IP组     │
│  Select][责任人人员选择][计算状态 Select] [搜索][重置]                     │
│ ┌──────────┬──────┬─────────────┬─────────┬──────┬─────────┬──────┐     │
│ │场次ID     │场次  │净利润        │毛利     │版本  │异常     │操作  │     │
│ ├──────────┼──────┼─────────────┼─────────┼──────┼─────────┼──────┤     │
│ │IMSS2025… │直播A │ ¥12,340.00  │¥18,200 │ v3   │—       │反查  │     │
│ │IMSS2025… │直播B │ ¥-890.00 🔴 │¥1,200  │ v3   │⚠2.3σ   │反查  │     │
│ └──────────┴──────┴─────────────┴─────────┴──────┴─────────┴──────┘     │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ Tab2 聚合下钻（GET /dc/profit-trace/aggregate）                          │
│ 维度: [按人/账号/团队/IP组/月份] Radio  ▸ 层级展开树表:                     │
│ [团队▸ 直播一部 ▸ 张三 ▸ 场次列表]（children 逐层展开到 sessionCode）      │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ Tab3 异常清单（GET /dc/profit-trace/abnormal，联动 V3 FIN-002（第 28~33 周先行）） │
│ [场次ID|净利润|同行均值率|σ|偏离|异常成本项⚠|→ 直达异常成本项]            │
└──────────────────────────────────────────────────────────────────────────┘
点击"反查" → 反查链路抽屉（BR-209 路径图 + 成本/分成明细）
```

## 3. TypeScript 类型定义

```typescript
// ===== 请求 =====
interface DcProfitQueryReq extends PageParam {
  statPeriod?: string;
  platform?: PlatformType;
  accountId?: number;
  ipGroupId?: number;
  responsibleUserId?: number;
  calcStatus?: string;
}

interface DcProfitAggregateReq {
  aggregateBy: 'PERSON' | 'ACCOUNT' | 'TEAM' | 'IP_GROUP' | 'MONTH';
  dimensionValue?: string;
  dateRange?: [string, string];
}

interface DcAbnormalQueryReq extends PageParam {
  platform?: string;
  dateRange?: [string, string];
}

// ===== 响应 =====
interface DcProfitTraceVO {
  sessionCode: string;                   // 反查锚点（19 位）
  sessionTitle: string;
  platform: PlatformType;
  /** 三级利润（V3 FIN-002 口径（第 28~33 周先行），DECIMAL(14,2)） */
  netProfit: number | null;
  grossProfit: number | null;
  operatingProfit: number | null;
  /** V3 FIN 重算版本对齐（旧版本仅审计可见，DC-P-R2） */
  calcVersion: number;
  statPeriod: string;
  isAbnormal: boolean;                   // 联动 V3 FIN-002 异常标记（第 28~33 周先行）
}

interface DcProfitTraceChainResp {
  sessionCode: string;
  /** BR-209 反查路径：利润 → 场次 → 账号/资产/责任人/实名人 → 成本明细 */
  chain: {
    profit: DcProfitTraceVO;
    session: { sessionCode: string; sessionTitle: string; liveDate: string; platform: PlatformType };
    account: { accountId: number; accountNo: string; nickname: string };
    assets: Array<{ assetId: number; assetCode: string }>;
    responsibleUser: { userId: number; userName: string };
    realnamePersons: Array<{ userId: number; userName: string; roleType: string }>;
    costDetail: Array<{ costItem: string; amount: number | null }>;
  };
  queryCostMs: number;                   // 同 BR-205
  dataAsOf: string;
}

interface DcAbnormalVO extends DcProfitTraceVO {
  peerAvgRate: number;
  sigma: number;
  deviationSigma: number;                // 偏离 σ 倍数
  abnormalCostItem?: string;             // 直达异常成本项
}

interface DcShareDetailVO {
  shareTarget: 'DAREN' | 'REALNAME' | 'TEAM';
  targetRefId: number;
  targetRefName: string;
  shareBase: number | null;
  shareAmount: number | null;
  status: string;
}
```

## 4. 交互流程

**页面加载**：默认 Tab1 `GET /dc/profit-trace/list`；顶部数据截至时间戳（同 P1）。

**核心操作**：
- **单场反查**：列表行"反查" → `GET /dc/profit-trace/{sessionCode}` → 反查链路抽屉（§7.1，BR-209 路径完整展开）；抽屉头部显示 `耗时 {queryCostMs}ms`。
- **聚合下钻**：Tab2 维度 Radio 切换 → `GET /dc/profit-trace/aggregate` → 树表逐层展开（children：团队→人/账号→场次）；场次叶节点点击 → 打开反查链路抽屉（复用）。
- **异常下钻**：Tab3 `GET /dc/profit-trace/abnormal` → 异常清单（isAbnormal 联动 V3 FIN-002，第 28~33 周先行）；行点击 → 反查链路抽屉**自动展开并高亮 abnormalCostItem** 成本行（直达到异常成本项）。
- **分成明细**：反查链路抽屉内 [分成明细] Tab → `GET /dc/profit-trace/share-detail/{sessionCode}`；非 R1/R3/R4/R9 角色返回 1182 → Tab 显示锁定态"分成明细仅财务与总监及以上可见（DC-P-R4）"。
- **R3 标记待核**：异常行操作 [标记待核] → 联动 V3 FIN-002 复核流程（跳转 V3 FIN P2 复核，复用重算入口；本页只发起不承载复核）。

## 5. 查询条件表

| Tab | 字段 | 组件 | 说明 |
|-----|------|------|------|
| Tab1 | statPeriod | MonthPicker | 统计周期 |
| Tab1 | platform | Select | PlatformType |
| Tab1 | accountId / ipGroupId / responsibleUserId | Input / Select / 人员选择 | 账号 / IP 组 / 责任人 |
| Tab1 | calcStatus | Select | V3 FIN ProfitCalcStatus 引用 |
| Tab2 | aggregateBy | Radio | 按人/账号/团队/IP 组/月份 |
| Tab3 | platform / dateRange | Select / RangePicker | 异常筛选 |

## 6. 表格列定义

**Tab1 利润列表**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 场次 ID | sessionCode | code 样式 19 位 |
| 场次名称 | sessionTitle | 文本 |
| 平台 | platform | Tag |
| 净利润 | netProfit | ¥ 千分位，负数红括号；null "—" |
| 毛利 / 经营利润 | grossProfit/operatingProfit | ¥ 千分位（小字双列） |
| 计算版本 | calcVersion | `v{n}`（Tooltip "利润以 V3 FIN 当前计算版本为准，重算后旧版本仅审计可见"） |
| 统计周期 | statPeriod | yyyy-MM |
| 异常标记 | isAbnormal | ⚠ 红色"异常"（联动 V3 FIN-002，第 28~33 周先行）；Tab3 专列 σ 偏离 |
| 操作 | — | 反查；异常行追加 [标记待核]（R3） |

**Tab2 聚合树表**：维度标签 | 净利润 ¥ | 毛利 ¥ | 场次数 | 展开箭头（children 层级）；叶节点为场次行。

**Tab3 异常清单**：场次 ID、净利润（红）、同行均值率（peerAvgRate %）、σ（sigma）、偏离（deviationSigma `+2.3σ` 橙/`≥3σ` 红）、异常成本项（abnormalCostItem 红色 Tag）、操作（直达反查）。

## 7. 抽屉/弹窗规格

### 7.1 反查链路抽屉（Drawer，右滑 920px）

- **结构**（DcProfitTraceChainResp）：
  1. **头部**：sessionCode + sessionTitle + `耗时 {queryCostMs}ms` + `数据截至 {dataAsOf}`。
  2. **反查路径图（BR-209）**：水平步骤链 `利润 ¥{netProfit} → 场次 {sessionCode} → 账号 {accountNo} → 资产 ×{n} → 责任人 {userName} → 实名人 {persons}`，每节点可点击高亮联动下方明细区。
  3. **成本明细区**（Tab）：[成本项 | 金额 ¥]；**abnormalCostItem 行红色高亮**（异常下钻直达）；R7/R9 脱敏 "—"。
  4. **分成明细区**（Tab，权限 R1/R3/R4/R9）：[分成对象（DAREN 达人/REALNAME 实名人/TEAM 团队 Tag）| 对象名称 | 分成基数 ¥ | 分成金额 ¥ | 状态]；1182 → 锁定态。
  5. **场次信息区**（Tab）：liveDate/platform/三级利润/版本（复用 P1 §7.1 布局摘要）。
- 数据：`GET /dc/profit-trace/{sessionCode}`（链路）+ `GET /dc/profit-trace/share-detail/{sessionCode}`（分成 Tab 懒加载）。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1182 | 分成明细无权限 | Tab 锁定态文案 |
| 1181 | 反查超时降级 | 抽屉顶部橙色提示 |
| 1008 | 数据权限 | toast |
| 空数据（FIN 未计算周期） | — | 空态"该周期暂无利润数据（V3 财务计算完成后同步，延迟 < 1h）"——FIN 数据接入（M0b，第 31~32 周）前允许降级空态 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-205（反查性能同 P95<3s） | 抽屉耗时展示 |
| BR-209（反查路径） | 反查链路抽屉路径图（完整六段路径） |
| BR-210（新鲜度） | 顶部时间戳 + 空态文案 |
| DC-P-R1（聚合与明细双模式） | Tab1/Tab2 |
| DC-P-R2（FIN 版本对齐） | calcVersion 列 + Tooltip |
| DC-P-R3（性能同 BR-205） | queryCostMs |
| DC-P-R4（分成权限） | 1182 锁定态 |
| V3 FIN-002 联动（异常标记/复核） | Tab3 异常清单 + [标记待核] 跳转 |

---

# P3 全链路数据看板（DC-003）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | **`/ims/dc/dashboard`**（入口：**数据报表 · 大屏**（`reportType=DASHBOARD`）；支持大屏模式全屏） |
| 页面级别 | 二级（聚合看板 + 配置管理） |
| 前置依赖 | 聚合层小时级刷新（V3-A2 同步任务） |
| 权限 | 查看：R1/R3/R4/R9（脱敏）/R5（本团队）/R6（内容域）/R7（本人）/R2 只读；看板配置：R1/R4 |
| 用户 | 管理层（经营总览）/ 大屏展示场景 |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 全链路数据看板  [周期: 2025-05 ▾][看板 Select: 经营总览(默认)▾] [🔄手动   │
│ 刷新] 数据截至 2025-05-26 14:00（1h内 ✓） [大屏模式] [看板管理(R1/R4)]  │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 经营总览指标卡（GET /dc/dashboard/overview）                            │
│ ┌────────┬────────┬────────┬────────┬────────┬────────┐                 │
│ │ 总GMV   │ 总成本  │ 净利润  │ 场次数  │ 账号数  │ 资产数  │                 │
│ │¥xxx万  │¥xxx万  │¥xxx万  │ 1,284  │  356   │  892   │                 │
│ └────────┴────────┴────────┴────────┴────────┴────────┘                 │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 链路健康度区（GET /dc/dashboard/health，BR-208）                        │
│ ┌──────────────────┬──────────────┬──────────────┐                      │
│ │资产关联完整率 98.6%│账号线上化率   │台账留痕率     │                      │
│ │(目标>98% ✓绿)     │ 92%          │ 96%          │                      │
│ │ 趋势折线(30天)    │              │              │                      │
│ └──────────────────┴──────────────┴──────────────┘                      │
│ 完整率 <98% → 整卡红色告警(DC-D-R3) + isAlarm 提示条                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 维度下钻区（GET /dc/dashboard/dimension）                                │
│ 维度切换: [平台/账号/IP组/团队/实名人] Radio                              │
│ ┌────────┬────────┬────────┬────────┐                                   │
│ │维度值    │ GMV    │ 净利润  │ 场次数  │ ▸（children 二级下钻）           │
│ ├────────┼────────┼────────┼────────┤   行/单元格点击 → 下钻            │
│ │抖音     │¥xxx万  │¥xx万   │  520   │ ▸ 抖刷号A ▸ … ▸ 场次明细          │
│ └────────┴────────┴────────┴────────┘   （复用 DC-001/DC-002，DC-D-R2）│
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 同步任务状态（GET /dc/dashboard/freshness，BR-210）                     │
│ [任务名|最近运行|状态 SUCCESS绿/DELAYED橙>1h告警/FAILED红|延迟分钟]       │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 请求 =====
interface DcOverviewReq {
  statPeriod: string;
  dimensionType?: 'PLATFORM' | 'IP_GROUP' | 'TEAM';
}

interface DcDimensionReq {
  statPeriod: string;
  dimensionType: 'PLATFORM' | 'ACCOUNT' | 'IP_GROUP' | 'TEAM' | 'REALNAME';
  drillTo?: string;                      // 下钻目标维度值
}

interface DcDashboardSaveReq {
  dashboardName: string;
  layoutConfig: Array<{
    widgetKey: string;
    widgetType: 'METRIC_CARD' | 'TREND_CHART' | 'RANK_LIST' | 'HEALTH_PANEL';
    position: { x: number; y: number; w: number; h: number };
    config: Record<string, unknown>;
  }>;
  refreshCron?: string;
}

// ===== 响应 =====
interface DcOverviewResp {
  totalGmv: number | null;
  totalCost: number | null;
  netProfit: number | null;
  sessionCount: number;
  accountCount: number;
  assetCount: number;
  dataAsOf: string;                      // BR-210 / DC-D-R1
  refreshedAt: string;
}

interface DcHealthResp {
  assetRelationCompleteRate: number;     // BR-208，目标 > 98%
  target: 98;
  isAlarm: boolean;                      // DC-D-R3 红色告警
  trend: Array<{ statDate: string; completeRate: number }>;
  accountDigitizationRate: number;
  ledgerTraceRate: number;
}

interface DcDimensionVO {
  dimensionValue: string;
  dimensionLabel: string;
  gmv: number | null;
  netProfit: number | null;
  sessionCount: number;
  children?: Array<{ dimensionValue: string; gmv: number | null; netProfit: number | null; sessionCount: number }>;
}

interface DcFreshnessResp {
  businessToDwsDelayMinutes: number;
  target: 60;
  isAlarm: boolean;
  syncTaskStatus: Array<{ taskName: string; lastRunAt: string; status: 'SUCCESS' | 'DELAYED' | 'FAILED'; delayMinutes: number }>;
  dataAsOf: string;
}

interface DcDashboardVO {
  id: number;
  dashboardName: string;
  ownerUserId: number;
  ownerName: string;
  status: 'ENABLED' | 'DISABLED';
  refreshCron: string;
  refreshedAt: string;
}
```

## 4. 交互流程

**页面加载**：
1. 看板 Select（`GET /dc/dashboard/list`，默认第一个 ENABLED 看板）+ 并行 `GET /dc/dashboard/overview` + `health` + `dimension` + `freshness`。
2. 顶部常驻 `数据截至 {dataAsOf}`（DC-D-R1 小时级刷新 + 时间戳）；延迟 >1h → 红色告警 + isAlarm 提示条（BR-210）。

**核心操作**：
- **周期/看板切换**：statPeriod MonthPicker / 看板下拉切换 → 重新拉取 overview+dimension。
- **手动刷新**：[🔄] 强制重新请求（缓存数据后台按 refreshCron 刷新，手动仅刷新展示）。
- **健康度告警**：assetRelationCompleteRate < 98（isAlarm）→ 健康卡整卡红色 + 顶部告警条"资产关联完整率 {x}%，低于目标 98%（BR-208/DC-D-R3），请核查资产-账号-场次关联"；趋势折线（近 30 天）Hover 查看每日值。
- **维度下钻**：dimensionType Radio 切换 → dimension 数据表格；行/children 展开逐层下钻（平台→账号→场次）；**最深场次层点击 → 跳转 P1 穿透查询（携带 sessionCode 自动开明细抽屉）或 P2 反查**（复用 DC-001/DC-002 能力，不重复建设，DC-D-R2）。
- **大屏模式**：[大屏] 全屏切换（指标卡放大布局，隐藏操作区，保留数据截至时间戳）。
- **看板管理**（R1/R4）：[看板管理] → 看板配置抽屉（§7.1）：创建/编辑布局（widget 拖拽画布：METRIC_CARD 指标卡/TREND_CHART 趋势图/RANK_LIST 排行/HEALTH_PANEL 健康面板；position 网格）→ `POST /dc/dashboard` / `PUT /dc/dashboard/{id}`。

## 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| statPeriod | MonthPicker | string | 统计周期（顶部） |
| dashboardId | Select | number | 看板切换（列表接口） |
| dimensionType | Radio | string | 维度下钻区：平台/账号/IP 组/团队/实名人 |

## 6. 表格列定义

**维度下钻表**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 维度值 | dimensionLabel | 文本 + 展开箭头（有 children） |
| GMV | gmv | ¥ 千分位（null "—"） |
| 净利润 | netProfit | ¥ 千分位，负数红括号 |
| 场次数 | sessionCount | 数字 |
| 操作 | — | 下钻（有 children 展开子级；场次级跳穿透/反查） |

**同步任务表**：任务名、最近运行、状态（SUCCESS 绿/DELAYED 橙 + >1h 告警/FAILED 红）、延迟分钟。

## 7. 抽屉/弹窗规格

### 7.1 看板配置抽屉（Drawer，右滑 960px，R1/R4）

- **左右布局**：左 30% 组件库（四类 widget 模板列表，可拖入画布）；右 70% 网格画布（position x/y/w/h，拖拽缩放）；每个 widget 点击右侧属性面板（config：数据源指标 key/日期范围/图表参数）。
- 顶部：看板名称 Input + refreshCron Input（小时级刷新策略，默认每 1h）。
- 保存 → `POST /dc/dashboard`（创建，返回 id）或 `PUT /dc/dashboard/{id}`（编辑布局）→ toast + 刷新看板列表。
- 布局配置变更不影响分享（缓存数据按新布局刷新后生效）。

## 8. 错误处理

| 场景 | 处理 |
|------|------|
| 同步任务 FAILED | 任务表红色 + 提示"同步失败，断点续传中（V3-A2）；当前展示最后成功快照 {dataAsOf}" |
| isAlarm（完整率/新鲜度） | 顶部红色告警条（自动展示，无需操作） |
| 看板无 ENABLED | 空态"暂无启用看板，请联系管理员配置（R1/R4）" |
| 数据权限（R5/R7 越界维度） | 服务端预过滤，前端不渲染越界维度（DC-D-R4） |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-208（资产关联完整率 >98% 全链路口径） | 健康度卡 + isAlarm 红色告警 + 趋势 |
| BR-210（新鲜度 <1h） | 数据截至时间戳 + 同步任务表 + DELAYED 告警 |
| DC-D-R1（小时级刷新 + 时间戳） | 顶部时间戳常驻 + refreshCron 配置 |
| DC-D-R2（下钻复用 DC-001/002） | 维度下钻场次级跳转 |
| DC-D-R3（<98% 红色告警） | 健康卡整卡红 |
| DC-D-R4（缓存按人预过滤） | 服务端过滤说明 |
| V3-A2（同步任务调度 + 断点续传） | 同步任务表状态展示 |
| V3-A3（只读不回写） | 全页无写操作（仅看板配置元数据写） |

---

# P4 穿透性能监控（DC-001 附页，R1/R9）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | **`/ims/dc/trace/perf`**（**无菜单** · R1/R9；亦由 P1 顶部耗时徽标点击进入） |
| 页面级别 | 三级（运维监控页） |
| 前置依赖 | 穿透查询使用产生埋点；V3-C3 每日自动压测任务运行 |
| 权限 | R1/R9 |
| 用户 | 系统管理员 R1（性能保障验证） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 穿透性能监控（BR-205 验证）    [日期范围 RangePicker: 默认近7天]           │
├──────────────────────────────────────────────────────────────────────────┤
│ 核心指标卡（GET /dc/trace/perf-metrics）:                                 │
│ ┌───────────┬───────────┬──────────┬───────────┬─────────────┐          │
│ │ P95       │ P99       │ 查询总量  │ 目标 P95  │ 每日压测     │          │
│ │ 1,842ms ✓ │ 5,230ms ✓│ 12,840   │ 3,000ms   │ ✅ 通过(V3-C3)│          │
│ └───────────┴───────────┴──────────┴───────────┴─────────────┘          │
│ P95/P99 超标 → 对应卡红色 + 告警条                                        │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 慢查询清单（slowQueries）                                               │
│ ┌──────────┬──────────────┬────────┬──────────┐                          │
│ │查询ID     │穿透入口       │耗时     │发生时间   │                          │
│ ├──────────┼──────────────┼────────┼──────────┤                          │
│ │Q2025…    │张三(实名人)    │8,120ms │05-26 13:2│  >3000ms 红色            │
│ └──────────┴──────────────┴────────┴──────────┘                          │
│ 压测说明条: 每日自动执行 10 条典型穿透用例（V3-C3），P95 超标自动告警      │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
interface DcPerfMetricsResp {
  p95Ms: number;
  p99Ms: number;
  targetP95Ms: 3000;                     // BR-205 目标
  queryCount: number;
  slowQueries: Array<{ queryId: string; entryLabel: string; costMs: number; occurredAt: string }>;
  dailyPressureTestPassed: boolean;      // V3-C3 每日自动压测
}
```

## 4. 交互流程

**页面加载**：`GET /dc/trace/perf-metrics`（dateRange 默认近 7 天）。
- p95Ms > 3000 → P95 卡红色 + 顶部告警条"穿透 P95 超标（BR-205 目标 < 3000ms），已自动告警并出具慢查询清单"。
- dailyPressureTestPassed=false → 压测卡红色"今日压测未通过"。
- 慢查询行点击 → 跳 P1 并带入对应入口（复现查询）。

## 5~6. 查询条件表 / 表格列定义

查询条件：dateRange RangePicker（默认近 7 天）。慢查询表：查询 ID（code 样式）、穿透入口、耗时（>3000ms 红）、发生时间。

## 7. 抽屉/弹窗规格

无抽屉。

## 8. 错误处理

无业务错误码（只读监控）；接口失败常规 toast。

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-205（P95<3s/P99<8s 验证） | P95/P99 指标卡 + 目标对比 + 超标红 |
| V3-C3（每日压测 10 条用例） | dailyPressureTestPassed 状态卡 |
| DC-T-R4（查询审计留痕） | 慢查询清单（审计数据消费） |

---

# 附录 A：模块级约定

1. **只读分析域（V3-A3）**：全模块无业务写操作（仅看板布局配置为元数据写）；业务数据单向同步，分析结果不回写业务表；R3"标记待核"为跳转 V3 FIN 发起，非本域写。
2. **性能三件套（BR-205/V3-C1~C3）**：聚合层预 join 宽表直查（避免在线多表实时穿透）；所有穿透结果展示 queryCostMs（>3s 橙色）；1181 超时降级提示缩小范围；P4 每日压测验证页（R1/R9）。
3. **场次 ID 锚点（DC-T-R2）**：sessionCode 19 位 IMS 编码贯穿 P1/P2/P3 全部页面与抽屉；跨模块跳转（V1 LIVE / V3 FIN / DC）统一携带 sessionCode。
4. **脱敏渲染（9.2）**：R7/R9 视角成本与利润金额 null → "—"；分成明细 1182 锁定态；不做前端脱敏（一律服务端）。
5. **新鲜度（BR-210）**：所有页面顶部常驻 `数据截至 {dataAsOf}`；>1h 红色告警；同步任务状态表（DELAYED/FAILED）在 P3 展示（V3-A2 断点续传说明）。
6. **版本对齐（DC-P-R2）**：利润数据一律取 V3 FIN 当前计算版本（calcVersion 展示），重算旧版本仅审计可见（不在分析页展示）。
7. **读写分离（V3-D1~D3）**：DAO 层约定读走从库（延迟超标切主库），页面无感知；仅 P4 监控页可观测。
8. **画布组件**：链路图采用图可视化组件（力导向/层级混合布局），节点类型六类（PERSON/ACCOUNT/ASSET/SESSION/COST/PROFIT）统一图标与配色（成本红/利润绿/人员蓝/账号紫/资产青/场次橙）。
9. **大屏模式**：P3 支持全屏大屏布局（隐藏操作区、指标卡放大、保留数据截至时间戳）。

# 附录 B：BR / DC 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-205 | 穿透 P95<3s / P99<8s | P1/P2 耗时展示、1181 降级、P4 监控页 |
| BR-208 | 资产关联完整率 >98%（全链路口径） | P3 健康度卡 + isAlarm 红告警 |
| BR-209 | 反查路径（利润→场次→…→成本） | P2 反查链路抽屉路径图 |
| BR-210 | 聚合层新鲜度 <1h | 全页数据截至时间戳 + P3 同步任务表 |
| DC-T-R1 | 聚合层预 join | P1 页面说明 + 性能保障来源 |
| DC-T-R2 | 场次 ID 唯一锚点 | sessionCode 全链路展示与跳转 |
| DC-T-R3 | 新鲜度 <1h | 同 BR-210 |
| DC-T-R4 | 审计留痕 | 服务端自动 + P4 慢查询清单 |
| DC-P-R1 | 聚合与明细双模式 | P2 Tab1/Tab2 |
| DC-P-R2 | FIN 版本对齐（V3 FIN 第 28~33 周先行） | calcVersion 列 + Tooltip |
| DC-P-R3 | 反查性能同 BR-205 | 抽屉耗时展示 |
| DC-P-R4 | 分成明细权限 | 1182 锁定 Tab |
| DC-D-R1 | 小时级刷新 + 时间戳 | P3 时间戳 + refreshCron |
| DC-D-R2 | 下钻复用 DC-001/002 | P3 维度下钻跳转 |
| DC-D-R3 | 完整率 <98% 红告警 | P3 健康卡 |
| DC-D-R4 | 缓存按人预过滤 | 服务端过滤说明 |
| V3-A2 | 同步延迟告警/断点续传 | P3 同步任务表 |
| V3-A3 | 只读不回写 | 全模块无写操作 |
| V3-C2 | 宽表直查 + 兜底 | P1 实现约束说明 |
| V3-C3 | 每日压测 10 用例 | P4 压测状态卡 |
| V3-D1~D3 | 读写分离从库 | DAO 约定 + P4 可观测 |

（全文完）
