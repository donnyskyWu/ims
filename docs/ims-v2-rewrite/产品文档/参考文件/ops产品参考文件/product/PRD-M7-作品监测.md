# PRD-M7-作品监测

> **业务域**：M7 作品监测
> **功能模块**：外部账号分析 + 监测
> **详细设计章节**：5.32、5.33
> **版本**：v1.2 | 2026-10-02
> **状态**：Draft（实现已对齐）
> **关联 UX**：[`UX-M7-作品监测.md`](./UX-M7-作品监测.md)（v1.3 · 2026-10-02）
> **关联 API**：[`API-M7-作品监测.md`](../engineering/API-M7-作品监测.md)（v1.2）
> **全局规范**：[`docs/engineering/GLOBAL-CONVENTIONS.md`](./../engineering/GLOBAL-CONVENTIONS.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| 模块 | M7 作品监测 |
| 业务域 | 作品监测（MONITOR） |
| 详细设计 | `## 5.32~5.33` |
| Football 路由 SSOT | [`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md) · 6101 作品监测 `/ops/monitor/*` |

---

## 1. 概述

### 1.1 一句话描述

监测**外部竞品平台**的账号动态、爆款作品、低分作品、高/低粉账号，提供 IP 主题维度的数据聚合；六张菜单分析页共用筛选 + 汇总卡 + 图表 + 表格 + **详情抽屉下钻**。

### 1.2 目标

- 替代 Excel 手动统计
- 1 分钟内发现竞品爆款
- 高/低粉账号精准预测

### 1.3 术语表

| 术语 | 定义 |
|------|------|
| **外部账号** | 竞品平台账号（非本系统 M4 自有 `oa_account`） |
| **高粉账号** | 粉丝增速 ≥ 阈值（与后端 `high-follower/list` 筛选一致，见 UX Tooltip / BR-002） |
| **低粉账号** | 粉丝连续 7 天下降 |
| **爆款作品** | BR-003 阈值（播放 ≥ 100w） |
| **低分作品** | BR-004 阈值（完播率 < 20%） |
| **IP 主题分析** | 按 IP 主题聚合外部数据 |
| **行业分析** | 按行业聚合（P-M7-007 Spec 历史，**无** OPS 菜单） |

---

## 2. 范围

### 2.1 In Scope（2 个 FR 模块）

| FR 编号 | 名称 | 优先级 | 详细设计 |
|---------|------|--------|---------|
| FR-M7-001 | 外部作品监测（外部账号 / 爆款 / 低分） | P0 | 5.32 |
| FR-M7-002 | 高/低粉账号 + IP 主题分析 | P0 | 5.33 |

### 2.2 Out of Scope

1. ❌ **不实现** 内部作品监测（属于 M6 `## 5.5 作品分析`）
2. ❌ **不实现** 竞品账号的实时数据抓取（依赖 M10 Channel-D + M8 外部配置）
3. ❌ **不实现** P-M7-007 行业分析菜单（无 6100–6999 注册；API 草案保留，见 UX §3.7）

### 2.3 用户与权限

| 角色 | 典型能力 |
|------|----------|
| 系统管理员 / 运营管理者 | 六页全部菜单 + 导出（若有） |
| 运营组长 / 数据分析 | 按数据权限可见 IP 组范围内外部监测数据 |
| 普通运营 | 只读列表/抽屉；无配置竞品账号（在 M8） |

| 页面 ID | permission（菜单/接口） |
|---------|-------------------------|
| P-M7-001 | `oa:external-account:list` |
| P-M7-002 | `oa:high-fans:list` |
| P-M7-003 | `oa:hot-works:list` |
| P-M7-004 | `oa:ip-theme:list` |
| P-M7-005 | `oa:low-fans:list` |
| P-M7-006 | `oa:low-score:list` |

无对应 permission → 隐藏菜单；403 不展示页面（UX §4）。

---

## 3. 页面清单与 UX 交叉引用（对齐 UX-M7 v1.3）

> 页面级字段、图表轴、抽屉字段 SSOT：**UX-M7** §2–§3；本节为 **FR + 可测 AC + API 路径**。

| 页面 ID | 名称 | Football 路由 | FR | UX |
|---------|------|---------------|-----|-----|
| P-M7-001 | 外部账号分析 | `/ops/monitor/external-account` | FR-M7-001 | UX §3.1 · §2.3 |
| P-M7-002 | 高粉账号分析 | `/ops/monitor/high-fans-account` | FR-M7-002 | UX §3.2 |
| P-M7-003 | 爆款作品分析 | `/ops/monitor/hot-works` | FR-M7-001 | UX §3.3 |
| P-M7-004 | IP 主题数据 | `/ops/monitor/ip-theme` | FR-M7-002 | UX §3.4 · §2.4 |
| P-M7-005 | 低粉账号分析 | `/ops/monitor/low-fans-account` | FR-M7-002 | UX §3.5 |
| P-M7-006 | 低分作品分析 | `/ops/monitor/low-score` | FR-M7-001 | UX §3.6 |
| P-M7-007 | 行业分析（Spec 历史） | —（无菜单） | FR-M7-002 | UX §3.7 |

> **P-M7-007**：**不计入** OPS 77 面（无 Football 菜单）；PRD 锚点 = **OOS / Spec-only**（**AC-M7-002-P007**），Gate 不验收。

**通用布局**（六页）：UX §2 — 页头 · 筛选 B · 汇总卡 C1 · 图表 C2 · 表格 C3 · 行 [详情] → `el-drawer` 480–640px（凭证不明文，GLOBAL-CONVENTIONS §5）。

**HTTP 前缀 SSOT**：`/admin-api/ops/monitor/**`（[`API-M7`](../engineering/API-M7-作品监测.md) §0）。

---

## 4. 功能需求

### FR-M7-001 外部作品监测（5.32）

#### 4.1.1 描述

监测外部竞品平台的账号动态、爆款/低分作品；覆盖 P-M7-001、P-M7-003、P-M7-006。

#### 4.1.2 数据项（筛选 · 六页共用子集）

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `platformType` | `<DictSelect dict-type="dict_platform_type" />` | 字典 |
| `ipGroupId` | `<IpGroupTreeSelect scope="all" />` | `oa_ip_group` |
| `industry` | `<Select />` | 固定行业枚举（部分页） |
| `startDate` / `endDate` | `<DateRangePicker />` | 默认近 30 天 |
| `accountId` | `<AccountSelect />` | 外部账号语义 · `oa_external_account.id` |

#### 4.1.3 业务规则

- 爆款阈值：BR-003 = 100w 播放（`GET .../monitor/hit/list`）
- 低分阈值：BR-004 = 完播率 < 20%（`GET .../monitor/low-score/list`）
- M7 列表读 `oa_external_work`；`account_id` = **`oa_external_account.id`**（非 M4 `oa_account`）
- 数据来源 Channel-D（ADR-052）；采集未启动 → `el-empty` + 提示开启 M8/M10
- seed demo 保留；**真实采集数据优先**（ADR-052 Q5）

#### 4.1.4 验收标准

**AC-M7-001-P001**（P-M7-001 外部账号列表 · 查询）
- Given 用户具备 `oa:external-account:list`
- When 打开 `/ops/monitor/external-account`，选择 `platformType` + 日期并点击查询
- Then `GET /admin-api/ops/monitor/external/list` 带筛选参数；C1 汇总卡与 C3 表格刷新（列见 UX §3.1）

**AC-M7-001-P001-D**（P-M7-001 抽屉下钻 · 作品子表）
- Given 列表有行数据
- When 点击 [详情] 或行点击
- Then 480px 抽屉展示账号基本信息（平台 Tab：douyin/wechat/channels 字段子集见 UX §2.3）；作品子表调用 `GET /admin-api/ops/monitor/external/works?accountId=`；max-height 420

**AC-M7-001-P001-E**（P-M7-001 导出）
- Given 页头存在 [导出 Excel]
- When 点击导出
- Then 与当前 Tab `external/list` 同源数据生成客户端 Excel（UX §2.3）

**AC-M7-001-P003**（P-M7-003 爆款作品）
- Given 用户具备 `oa:hot-works:list`
- When 打开 `/ops/monitor/hot-works` 并查询
- Then `GET /admin-api/ops/monitor/hit/list`；仅展示播放 ≥ 100w 作品；表格列含标题/账号/平台/播放量/点赞/发布日期/`dict_content_type`

**AC-M7-001-P003-D**（P-M7-003 抽屉）
- When 行 [详情]
- Then 抽屉展示作品标题/播放/点赞/链接（行数据或 GET，UX §2.4）

**AC-M7-001-P006**（P-M7-006 低分作品）
- Given 用户具备 `oa:low-score:list`
- When 打开 `/ops/monitor/low-score` 并查询
- Then `GET /admin-api/ops/monitor/low-score/list`；完播率 < 20%；C2 含完播率分布与低分趋势（UX §3.6）

**AC-M7-001-P006-D**（P-M7-006 抽屉）
- When 行 [详情]
- Then 抽屉展示完播率/时长/标题详情（UX §2.4）

**AC-M7-001-F**（筛选字典 · 跨页）
- When 提交含非法 `platformType`
- Then 后端 `@InDict` 拒绝，错误码 **1503**

---

### FR-M7-002 高/低粉账号 + IP 主题（5.33）

#### 4.2.1 描述

高/低粉账号榜单与 IP 主题聚合；覆盖 P-M7-002、P-M7-004、P-M7-005；P-M7-007 行业为 Out of Scope 菜单。

#### 4.2.2 业务规则

- 高粉：与后端 `high-follower/list` 阈值一致（UX 页头 Tooltip ↔ PRD BR-002）
- 低粉：连续低粉天数由后端计算；C2 低粉占比饼图（UX §3.5）
- IP 主题：行点击 → 抽屉内 **作品子表**（hit 字段子集）；C2 左 X=日期 Y=作品数/播放，右 TOP 主题横向条（UX §2.4）

#### 4.2.3 验收标准

**AC-M7-002-P002**（P-M7-002 高粉账号）
- Given `oa:high-fans:list`
- When 打开 `/ops/monitor/high-fans-account` 并查询
- Then `GET /admin-api/ops/monitor/high-follower/list`；表格含账号/平台/粉丝数/IP 组/运营人(`UserSelect` 回显)/上榜天数

**AC-M7-002-P002-D**（P-M7-002 抽屉）
- When [详情]
- Then 抽屉展示账号基础 + 近 7 日粉丝迷你趋势（若实现，UX §2.4）

**AC-M7-002-P005**（P-M7-005 低粉账号）
- Given `oa:low-fans:list`
- When 打开 `/ops/monitor/low-fans-account` 并查询
- Then `GET /admin-api/ops/monitor/low-follower/list`；列含持续低粉天数/最近发文

**AC-M7-002-P004**（P-M7-004 IP 主题）
- Given `oa:ip-theme:list`
- When 打开 `/ops/monitor/ip-theme` 并查询
- Then `GET /admin-api/ops/monitor/ip-theme/list`；行下钻 `GET /admin-api/ops/monitor/ip-theme/{id}` 抽屉内作品子表

**AC-M7-002-P007**（P-M7-007 行业 · 无菜单）
- Given 产品未注册 OPS 菜单
- When 用户仅能通过历史 Spec 访问
- Then **不**作为 P0 Gate 验收项；若实现则 API 草案 `GET /admin-api/ops/monitor/industry/{id}`（UX §3.7）

**AC-M7-002-S**（排序）
- When 用户点击表格 `sortable` 列
- Then 请求携带 `orderBy` / `orderAsc`（与 API-M7 对齐，UX §4）

---

## 5. 集成与数据

### 5.1 核心实体

| 实体 | 用途 |
|------|------|
| `oa_external_account` | 外部竞品账号快照（Channel-D 采集刷新） |
| `oa_external_work` | 外部竞品作品（M7 监测消费） |
| `oa_external_follower_daily` | 外部粉丝每日数据 |
| `oa_collect_config` | 外部竞品配置 SSOT（`scope=EXTERNAL`, `sub_type=account`） |
| `oa_ip_theme` | IP 主题（字典） |

### 5.2 关联属性

| 字段 | 选择器 |
|------|--------|
| `ipGroupId` | `<IpGroupTreeSelect />` |
| `platformType` | `<DictSelect dict-type="dict_platform_type" />` |

### 5.3 数据来源

- **Channel-D**（ADR-052）：M8 外部账号配置 → M10 `method=EXTERNAL` → `oa_external_*`
- M7 **不**经 M1 `CollectedDataQueryService`

---

## 6. 决策记录

| 编号 | 问题 | 决策 | 原因 |
|------|------|------|------|
| ADR-M7-001 | 爆款阈值是多少？ | 100w 播放（BR-003） | 业务经验 |
| ADR-M7-002 | 低分阈值 | 完播率 < 20%（BR-004） | 行业标准 |
| ADR-052 | 外部竞品数据来源 | Channel-D 落库 `oa_external_*`；与 Channel-A 隔离 | M10 EXTERNAL 切片 |

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.2：P-M7-001~007 页表 · 六菜单页可测 AC · 抽屉下钻 · 角色/permission · UX v1.3 / API `/ops/monitor` 链接 |
| 2026-06-11 | v1.1：抽屉详情 |
| 2026-06-07 | v1.0：初版 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES（页级 AC 与 UX P-M7-* 一一对应）。*
