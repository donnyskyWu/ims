# COMP-竞品分析 - 页面规格（OPS M7 外部监测 · IMS 导航重组）

> **域**：日常运营 → **竞品分析**（侧栏 `nav-sub-g`，与 **15 内容生产 / 16 数据采集** 同模式）  
> **交互 SSOT**：`docs/product/UX-M7-作品监测.md`、`docs/product/PRD-M7-作品监测.md`、`docs/product/产品使用操作手册.md` §12.2、`ADR-IMS-003`  
> **API SSOT**：`docs/engineering/API-M7-作品监测.md`、同目录《COMP-竞品分析-API契约.md》  
> **禁止混淆**：**16 数据采集 → 竞品账号配置** = M8 Channel-D **配置**（`oa_collect_config`）；本模块 = M7 **消费已采集数据**（`oa_external_work` / `oa_external_account`），不得与采集配置合并菜单。  
> **V3 资产库（走查 #9）**：**竞品库**（COMP-003）作为本组 **第三叶** 并入侧栏，路由 `/ims/comp-analysis/library`；交互/API 仍以 `V3/COMP-竞品管理-页面规格.md` P3 + API 契约为 SSOT。**月度提交 / 审核工作台**（COMP-001/002）**不在**本组菜单，入口为工作台待办等。  
> **后端**：M7 只读 BFF（本规格 +《COMP-竞品分析-API契约》）与 V3 `/admin-api/comp/*` **分离**；合并仅为 IMS 导航 IA。

---

## 0. 依据与标签口径（§0 走查对齐）

| 来源 | 引用要点 |
|------|----------|
| `docs/product/PRD-M7-作品监测.md` §1.3 | **爆款** = BR-003（播放 ≥ 100w）；**低分** = BR-004（完播率 &lt; 20%）；**高粉** = 日增粉丝 ≥ 阈值；**低粉** = 连续 7 天粉丝下降（`oa_follower_daily`） |
| `docs/delivery/OPS-MENU-LIST.md` 6112~6116 | OPS 原菜单名：爆款作品分析、低分作品分析、高粉账号分析、低粉账号分析、外部账号分析 |
| `docs/delivery/OPS-MENU-ROUTE-INDEX.md` | OPS 路由：`/ops/monitor/hot-works`、`low-score`、`high-fans-account`、`low-fans-account`、`external-account` |
| `docs/product/产品使用操作手册.md` §12.2 | 阈值可在页内查询前确认；爆款/低分列表为空时属阈值过滤预期 |
| `docs/engineering/OPS-RBAC-DATA-SCOPE.md` | M7 列表：member 角色按 IP 组过滤 `external_work` / 外部账号 |
| `一体化管理/COLLECT` 阈值 P4 | 爆款/低分/高低粉 **判定阈值只读引用** 数据采集 → 阈值规则，本模块 **不重复配置** |

**IMS 相对 OPS 的信息架构差异（用户走查项 #6）**：OPS 为 5 个并列菜单页；IMS 收成 **2 个叶子页 + 页内 Tab**，Tab 语义与 OPS 单页等价，**不得**改标签名（全部 / 爆款 / 低分 / 高粉 / 低粉）。

---

## 0.1 侧栏信息架构

默认进入 **P1 竞品作品**。与 **18 作品监测** 分工：MON 仅 **IP 主题/行业**；内部作品/账号见 **内部分析**（走查 #7）；外部竞品 **只看本「竞品分析」**。

| 页面 ID | 侧栏名称 | 路由 | 页内 Tab | SSOT |
|---------|----------|------|----------|------|
| P1 | 竞品作品 | `/ims/comp-analysis/work` | **全部** · **爆款** · **低分** | 全部=IMS 读 `oa_external_work` · 爆款/低分=OPS monitor |
| P2 | 竞品账号 | `/ims/comp-analysis/account` | **全部** · **高粉** · **低粉** | OPS M7 外部/高粉/低粉 |
| P3 | **竞品库** | `/ims/comp-analysis/library` | 卡片列表 + 详情抽屉 + 审核操作 | V3 COMP-003 · `GET/PUT /comp/asset/*`；**≠** P1/P2 监测 Tab |

---

## P1 竞品作品

### 布局（对齐 UX-M7 §2~§3）

```
[Alert：阈值只读 · 链至 数据采集 → 阈值规则]
[Tab：全部 | 爆款 | 低分]   ← 切换过滤列表，非 toast
[筛选：平台 | IP 组 | 行业 | 日期范围 | 账号标识] [查询] [重置] [导出]
[汇总卡：作品数 / 总播放 / 爆款数 / 低分数]（Tab=全部时展示；子 Tab 可隐藏无关卡）
[图表区：趋势 + 排名]（P0 可占位，须留高度）
[表格 + 分页]
```

### Tab → 过滤语义

| Tab | 列表语义 | 后端 |
|-----|----------|------|
| 全部 | 已采集 **全部** 外部竞品作品（`oa_external_work`） | IMS BFF 读库（ADR-001）· API §1.1 `segment=ALL` · **非** hit∪low 客户端并集 |
| 爆款 | 命中 BR-003 / 阈值 `HIT_THRESHOLD` | OPS `GET …/monitor/hit/list` |
| 低分 | 命中 BR-004 / 阈值 `LOW_SCORE` | OPS `GET …/monitor/low-score/list` |

### 表格列（与 OPS 爆款/低分页一致，camelCase）

| 列 | 说明 |
|----|------|
| 作品标题 | `title` |
| 竞品账号 | `accountName`（须回显采集快照名，禁止 `账号 #id`） |
| 平台 | `dict_platform_type` |
| 发布时间 | `publishTime` |
| 播放 / 互动 | `playCount`、`likeCount` 等（按 OPS 现网列） |
| 标签 | Tab=爆款 → 爆款 tag；Tab=低分 → 低分 tag |
| 操作 | [详情] → 抽屉 480px 只读摘要 |

### 空状态

- Tab=爆款/低分且无行：**「当前筛选下无命中作品，可调整阈值或日期范围」** + 链至 COLLECT 阈值页。
- Tab=**全部**（`segment=ALL`）：调用 `GET …/comp-analysis/work/page?segment=ALL`（IMS BFF · 2026-10-01 设计 SSOT）；列表与爆款/低分 **同列**，额外展示 `isHit`/`isLowScore` 标签（服务端按 COLLECT 阈值规则计算，只读）。

**验收（COMP-P1-ALL）**：Tab=全部 可分页展示全量外部作品；空库时走标准空状态（非 BLOCKED 文案）。

---

## P2 竞品账号

```
[Tab：全部 | 高粉 | 低粉]
[筛选：平台 | IP 组 | 行业 | 日期范围] [查询] [重置] [导出]
[汇总卡：账号数 / 平均粉丝 / 高粉数 / 低粉数]
[表格 + 分页]
```

| Tab | 语义 | 后端 |
|-----|------|------|
| 全部 | 外部竞品账号快照列表 | OPS `GET …/monitor/external/list` |
| 高粉 | 日增/粉丝达高粉阈值 | OPS `GET …/monitor/high-follower/list` |
| 低粉 | 连续下降等低粉规则 | OPS `GET …/monitor/low-follower/list` |

### 表格列

| 列 | 说明 |
|----|------|
| 账号名称 | `accountName` / `displayName` |
| 平台 | `platformType` |
| 粉丝数 | `followerCount` |
| 作品数 | `workCount` |
| 最近同步 | `lastSyncedAt` |
| 标签 | 高粉/低粉/正常 |
| 操作 | [详情] 抽屉 |

---

## 交叉链接

| 自 | 至 | 文案 |
|----|-----|------|
| P1/P2 顶栏 | `/ims/collect/threshold` | 阈值规则 |
| P1/P2 顶栏 | `/ims/collect/external/account` | 竞品账号配置（采集源） |
| P2 行操作 | COLLECT 竞品账号配置 | 仅当账号无数据时引导补配置 + 任务 |
| P3 顶栏 | P1 竞品作品 | 「查看监测数据」跳转（同组，非 toast） |
| P1/P2 行/顶栏 | P3 竞品库 | 账号已在库时可选跳转档案详情（assetNo，V3 契约） |

---

## P3 竞品库（V3 COMP-003 · 导航并入 #9）

> 字段级布局、审核 BR-202、归并 BR-203 **不重复**，见 `V3/COMP-竞品管理-页面规格.md` §P3。

```
[Alert：BR-202 待审核/驳回计数 · 链至审核工作台 /comp/audit（工作台入口，非本组 L3）]
[卡片网格：竞品名 · 平台 · 粉丝 · 趋势 sparkline · 审核态 Tag]
[操作：新增竞品 · 导出对比 · 卡片点击 → 详情抽屉 · 待审核行内 通过/驳回]
```

- **默认权限**：R4 终审/R1 档案维护可见全库；R9 只读；与 V3 PRD 5.3 矩阵一致。
- **实现**：页面组件可复用 V3 P3；路由 alias `/comp/asset` → `/ims/comp-analysis/library`（网关层，非业务 API 合并）。

---

## 权限（沿用 OPS M7）

| 能力 | 角色 |
|------|------|
| 列表/导出 | 运营管理者、数据分析师、本组运营（数据范围 IP 组） |
| 配置跳转 | 具 `collect` 外部配置权限者 |

权限码 IMS 期 **透传映射** OPS：`oa:hot-works:list`、`oa:low-score:list`、`oa:high-fans:list`、`oa:low-fans:list`、`oa:external-account:list`（见 OPS 菜单 seed）。

---

## 阻塞问题（产品 / 工程）

| # | 问题 | 影响 |
|---|------|------|
| B1 | ~~OPS 无全部作品 HTTP~~ | **✅ 2026-10-01**：IMS BFF `segment=ALL` 读库（API 契约 §1.1 · ADR-001） |
| B2 | IMS 前缀 `/admin-api/ims/comp-analysis/*` Go 适配层未实现，切流前可直连 `/admin-api/oa/monitor/*`（ADR-IMS-001 双轨） | 实现切片前确认网关 rewrite |
| B3 | IP 主题 / 行业分析仍归 **18 作品监测**，是否迁入竞品分析 **未在走查 #6 范围** | 保持 MON，避免 scope 膨胀 |

---

## OPS 前后端对照（2026-10-02）

> **现网前缀**：`/admin-api/ops/monitor/**`（前端 `/ops/monitor/...`）  
> **Java**：`football/module/ops/controller/monitor/MonitorController.java`  
> **Vue 根路径**：`football-front/apps/web-ele/src/views/ops/` · **API**：`#/api/ops/monitor.ts`

| IMS Tab | 过滤语义 | Vue SFC（OPS 单列菜单 → IMS Tab） | GET API（OPS） |
|---------|----------|-----------------------------------|----------------|
| P1 · 爆款 | BR-003 / 播放阈值 | `content/HotWorksAnalysis.vue` | `/ops/monitor/hit/list` |
| P1 · 低分 | BR-004 / 完播阈值 | `content/LowScoreAnalysis.vue` | `/ops/monitor/low-score/list` |
| P1 · 全部 | `oa_external_work` 全量（无独立 OPS HTTP） | （IMS BFF 读库；Tab 交互可复用 Hot/Low 筛选壳） | — · IMS `segment=ALL` 见 API 契约 |
| P2 · 全部 | 外部账号盘 | `account/ExternalAccountAnalysis.vue` | `/ops/monitor/external/list` |
| P2 · 高粉 | 高粉账号 | `account/HighFansAccountAnalysis.vue` | `/ops/monitor/high-follower/list` |
| P2 · 低粉 | 低粉账号 | `account/LowFansAccountAnalysis.vue` | `/ops/monitor/low-follower/list` |

**页内按钮（Vue）**：TableSearch 查询/重置；**导出**（`Download` · 各 Analysis 页 `handleExport`）；行 **详情** 抽屉（只读摘要）。**不**提供 CRUD（配置 → COLLECT P2a/P2b）。

**MON 扩展（非竞品分析菜单）**：`GET /ops/monitor/ip-theme/{id}` · `…/industry/{id}` → `content/IPThemeData.vue` / 监测单页。

**V3 竞品库**：无 OPS M7 Controller；SSOT 仍为 `V3/COMP-竞品管理-API契约.md`（`/admin-api/comp/asset/*` 等）。

---

## 操作序列（OPS → 原型 · 2026-10-02）

原型页：`compWork` · `compAccount` · `compWorkDetail` · `compAccountDetail`。

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | Tab「爆款/低分/全部」 | `HotWorksAnalysis.vue` / `LowScoreAnalysis.vue` | `GET /ops/monitor/hit/list` · `…/low-score/list` · 全部=IMS BFF |
| 2 | 查询/重置/导出 | 各 Analysis 页 `TableSearch` + `handleExport` | 列表刷新 · 导出文件 |
| 3 | 行「详情」 | 详情抽屉只读 | 摘要 KV · 无 CRUD |
| 4 | 竞品账号 Tab + 平台 Tab | `HighFansAccountAnalysis.vue` 等 | `GET /ops/monitor/high-follower/list` 等 |
| 5 | 详情 →「采集配置」 | 交叉链 M8 | 跳转 `collectExtAccount`（配置 SSOT 非本模块） |

**本地源码（wd 已检入）**：`football-front/apps/web-ele/src/views/ops/content/HotWorksAnalysis.vue` · `LowScoreAnalysis.vue` · `account/HighFansAccountAnalysis.vue` · `LowFansAccountAnalysis.vue` · `ExternalAccountAnalysis.vue` · `FansAccountAnalysis.vue`；API `#/api/ops/monitor.ts`。
