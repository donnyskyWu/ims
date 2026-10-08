# INT-内部分析 - 页面规格（OPS M1 内部监测 · IMS 导航重组）

> **域**：日常运营 → **内部分析**（侧栏 `nav-sub-g`，与 **15 内容生产 / 16 数据采集 / 竞品分析** 同模式）  
> **交互 SSOT**：`docs/product/UX-M1-运营管理.md` P-M1-003～006、`docs/product/PRD-M1-运营管理.md` FR-M1-003～006、`docs/product/产品使用操作手册.md` §7.4 / §12、`ADR-IMS-003`  
> **API SSOT**：`docs/engineering/API-M1-运营管理.md` §4、`docs/engineering/API-M7-作品监测.md`（高/低粉、爆款/低分阈值消费）、同目录《INT-内部分析-API契约.md》  
> **与竞品分析分工**：**竞品分析**（走查 #6）= M7 **外部** `oa_external_*`；本模块 = **自有账号/作品**（M1 内部内容 + 账号分析 + M7 阈值标签）。

---

## 0. 依据与标签口径（§0 走查对齐 #7）

| 来源 | 引用要点 |
|------|----------|
| `docs/product/PRD-M1-运营管理.md` | **爆款**列：`isHit` 命中 **BR-003**（默认播放 ≥ 100w，可配置）；**低分**命中 **BR-004**（完播率 &lt; 20%） |
| `docs/engineering/API-M7-作品监测.md` | BR-003 / BR-004 阈值说明（M7 文档化；ADR-069 扩展内部 Channel-A 亦触发同款阈值预警） |
| `docs/adr/ADR-069-采集完成阈值预警触发.md` | **低粉**双定义：(a) M8 `lowFans` 绝对值；(b) 连续 7 日粉丝下降（`oa_follower_daily`） |
| `docs/delivery/OPS-MENU-ROUTE-INDEX.md` | OPS 原菜单：内部作品分析 `/ops/operations/internal-content`；账号/粉丝/作品分析在运营管理 |
| `一体化管理/COLLECT` 阈值 P4 | 爆款/低分/高低粉 **判定阈值只读引用** 数据采集 → 阈值规则 |

**IMS 相对 OPS 的信息架构差异（用户走查项 #7）**：OPS 为「内部作品分析」「账号分析」「粉丝分析」「作品分析」等 **并列菜单**；IMS 收成 **2 个叶子页 + 页内 Tab**（全部 / 爆款 / 低分 · 全部 / 高粉 / 低粉），Tab 名 **不得** 改写。

**18 作品监测（MON）**：仅保留 **IP 主题 / 行业** 聚合（UX-M7）；内部作品/账号 **不在** MON 单页重复 Tab。

---

## 0.1 侧栏信息架构

默认进入 **P1 内部作品**。

| 页面 ID | 侧栏名称 | 路由 | 页内 Tab | OPS 对照 |
|---------|----------|------|----------|----------|
| P1 | 内部作品 | `/ims/int-analysis/work` | **全部** · **爆款** · **低分** | P-M1-006 内部内容分析 + 作品分析爆款列 |
| P2 | 内部账号 | `/ims/int-analysis/account` | **全部** · **高粉** · **低粉** | P-M1-003 账号分析 + M7 高/低粉列表（自有监测账号） |

---

## P1 内部作品

### 布局

```
[Alert：阈值只读 · 链至 数据采集 → 阈值规则]
[Tab：全部 | 爆款 | 低分]   ← 切换过滤列表，非 toast
[筛选：平台 | IP 组 | 内容类型 | 日期范围 | 关键词] [查询] [重置] [导出]
[汇总卡：作品数 / 总播放 / 爆款数 / 低分数]（Tab=全部时展示）
[表格 + 分页]
```

### Tab → 过滤语义

| Tab | 列表语义 | 后端 |
|-----|----------|------|
| 全部 | 租户内 **内部** 作品（Channel-A + 补录，`oa_internal_content` / M1 列表） | OPS `GET …/internal-content/list` |
| 爆款 | `isHit=true` / 命中 BR-003 | OPS `GET …/content-analysis/list?isHit=true` **或** 列表列过滤（见 API） |
| 低分 | 命中 BR-004 / 阈值 `LOW_SCORE` | IMS BFF：`internal-content/list` + COLLECT 阈值（**非** M7 `low-score/list` · 该 API 仅外部 `oa_external_work`）→ 见 API §1.1 |

### 表格列（摘要）

| 列 | 说明 |
|----|------|
| 作品标题 | `title` |
| 账号 | 绑定 `platform_account` 展示名 |
| 平台 | `dict_platform_type` |
| 播放 / 互动 | `readCount` / `playCount` 等（与 OPS 内部内容页一致） |
| 标签 | 爆款 / 低分 / 正常 |
| 操作 | [详情] → 抽屉 480px + 默认近 7 日趋势（`/internal-content/{id}/trend`） |

### 空状态

- Tab=爆款/低分且无行：提示调整阈值或日期 + 链至 COLLECT 阈值页。
- 数据补录入口：**不在**本页主导航；链自详情或 OPS 等价「数据补录」（`POST …/internal-content/import`）。

---

## P2 内部账号

```
[Tab：全部 | 高粉 | 低粉]
[筛选：平台 Tab | IP 组 | 关键词 | 账号状态] [查询] [重置] [导出]
[汇总卡：账号数 / 平均粉丝 / 高粉数 / 低粉数]
[表格 + 分页]
```

| Tab | 语义 | 后端 |
|-----|------|------|
| 全部 | 自有平台账号列表 | OPS `GET …/account-analysis/list` |
| 高粉 | 日增/粉丝达高粉阈值（M8 + M7） | OPS `GET …/monitor/high-follower/list`（**产品 TBD**：与 M1 账号列表去重策略见 API） |
| 低粉 | ADR-069 低粉双定义 | OPS `GET …/monitor/low-follower/list` |

### 表格列

| 列 | 说明 |
|----|------|
| 账号名称 | `accountName` |
| 平台 | `platformType` |
| IP 组 | `ipGroupName` |
| 粉丝数 | `followerCount` |
| 作品数 | `contentCount` |
| 标签 | 高粉 / 低粉 / 正常 |
| 操作 | [详情] 抽屉（粉丝/作品子 Tab 对齐 P-M1-003） |

---

## 交叉链接

| 自 | 至 | 文案 |
|----|-----|------|
| P1/P2 顶栏 | `/ims/collect/threshold` | 阈值规则 |
| P1/P2 顶栏 | `/ims/acct` | 账号台账（凭证在采集 Tab） |
| P2 | `/ims/int-analysis/work` | 查看该账号作品（带 accountId query） |

---

## 权限（沿用 OPS M1 + M7 监测）

| 能力 | 角色 |
|------|------|
| 列表/导出 | 运营管理者、数据分析师、本 IP 组运营（`OPS-RBAC` 数据范围） |

权限码 IMS 期 **透传映射**：`oa:internal-content:list`、`oa:account-analysis:list`、`oa:hot-works:list`、`oa:low-score:list`、`oa:high-fans:list`、`oa:low-fans:list`（按 Tab 对应）。

---

## 阻塞问题（产品 / 工程）

| # | 问题 | 影响 |
|---|------|------|
| ~~B1~~ | ~~内部低分下游~~ | **✅ 2026-10-02 关闭**：低分走 IMS BFF + `internal-content/list`；M7 `low-score/list` 明确 **仅竞品/外部** |
| B2 | 高/低粉 list 与 M1 账号分析列表 **合并展示规则** 未在 PRD 写死 | BFF 去重策略需产品确认或接受 OPS 现网双入口 |
| B3 | IMS 前缀 `/admin-api/ims/int-analysis/*` Go BFF 未实现 | 切流前可双轨 `/admin-api/oa/*`（ADR-IMS-001） |
