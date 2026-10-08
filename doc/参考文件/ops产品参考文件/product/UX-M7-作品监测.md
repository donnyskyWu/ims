# UX-M7-作品监测

> **版本**：v1.3 | 2026-10-02
> **关联 PRD**：[`PRD-M7-作品监测.md`](./PRD-M7-作品监测.md)
> **关联 API**：[`API-M7-作品监测.md`](../engineering/API-M7-作品监测.md)

---

> **OPS UI/UX SSOT**：[`UX-OPS-设计规范.md`](./UX-OPS-设计规范.md) · [`UX-OPS-页面原型索引.md`](./UX-OPS-页面原型索引.md)  
> **实现技术栈**：[`TECH-CONSTRAINTS.md § 1.2`](../engineering/TECH-CONSTRAINTS.md)（Vue 3 + Element Plus）

## 0. OPS 设计 SSOT

> **Football 路由 SSOT**：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md) 6101 作品监测（`/ops/monitor/*`）。  
> **说明**：v1.1 扁平路径 `/monitor/external` 等已废弃；行业分析页 **无** 6100–6999 菜单项，标为 Spec 历史。

---

## 1. 页面清单

| 页面 ID | 名称 | Football 路由 | component | FR | permission |
|---------|------|---------------|-----------|-----|------------|
| P-M7-001 | 外部账号分析 | `/ops/monitor/external-account` | `ExternalAccountAnalysis` | FR-M7-001 | `oa:external-account:list` |
| P-M7-002 | 高粉账号分析 | `/ops/monitor/high-fans-account` | `HighFansAccountAnalysis` | FR-M7-002 | `oa:high-fans:list` |
| P-M7-003 | 爆款作品分析 | `/ops/monitor/hot-works` | `HotWorksAnalysis` | FR-M7-001 | `oa:hot-works:list` |
| P-M7-004 | IP 主题数据 | `/ops/monitor/ip-theme` | `IPThemeData` | FR-M7-002 | `oa:ip-theme:list` |
| P-M7-005 | 低粉账号分析 | `/ops/monitor/low-fans-account` | `LowFansAccountAnalysis` | FR-M7-002 | `oa:low-fans:list` |
| P-M7-006 | 低分作品分析 | `/ops/monitor/low-score` | `LowScoreAnalysis` | FR-M7-001 | `oa:low-score:list` |
| P-M7-007 | 行业分析（Spec 历史） | —（无菜单） | — | FR-M7-002 | — |

---

## 2. 通用布局（六页共用）

```
+-- A: 页头 ------------------------------------------------+
| 页面标题                              [导出 Excel]（若有） |
+-- B: 筛选 ------------------------------------------------+
| F-PLATFORM · F-IP · F-DATE-RANGE · F-INDUSTRY（部分页）   |
| [查询] [重置]                                              |
+-- C1: 汇总卡 ----------------------------------------------+
| 账号数 | 作品数 | 平均粉丝 | 爆款数 | 低分数               |
+-- C2: 图表 ------------------------------------------------+
| 左: 趋势折线/柱  ·  右: TOP 排名横向条                     |
+-- C3: 表格 + 分页 -----------------------------------------+
| 可排序列 · 操作「详情」→ 抽屉 480px                        |
+------------------------------------------------------------+
```

### 2.1 筛选控件

| 控件 ID | 组件 | dict-type / 说明 |
|---------|------|------------------|
| F-PLATFORM | `<DictSelect dict-type="dict_platform_type" />` | 平台 |
| F-IP | `<IpGroupTreeSelect scope="all" />` | IP 组 |
| F-INDUSTRY | `<Select />` | 固定行业枚举（外部账号/主题页） |
| F-DATE-RANGE | `<DateRangePicker />` | `startDate` / `endDate` → API |

### 2.2 详情抽屉（通用）

| 属性 | 值 |
|------|-----|
| 组件 | `el-drawer` RTL · `append-to-body` · 宽 **480–640px** |
| 触发 | 表格行 [详情] / 部分页行点击 |
| 凭证 | cookie/token **不**明文（GLOBAL-CONVENTIONS §5） |

### 2.3 P-M7-001 外部账号 · 抽屉下钻（Vue 对齐）

| 区块 | 字段 / 列 |
|------|-----------|
| 基本信息 | 账号名称 · 账号ID · 粉丝数 · 作品/文章/视频数（随 Tab：douyin/wechat/channels）· 抖音：总播放(估)/获赞/平均播放/互动率 · 公众号：阅读/平均阅读/互动率 · 视频号：播放/平均播放/互动率 |
| 作品子表 | 标题 · 播放/阅读 · 点赞 · 发布时间（`getExternalWorkList`，max-height 420） |
| **API** | 列表 Tab 数据：`GET /admin-api/ops/monitor/external/list` · 抽屉作品：`GET .../monitor/external/works`（query `accountId` + 平台 Tab） |
| 导出 | 页头 [导出 Excel] → 当前 Tab list 同源 + 客户端 Excel |

### 2.4 其他监测页 · 抽屉 / 下钻

| 页面 | 抽屉内容 | API |
|------|----------|-----|
| P-M7-003 爆款 | 作品标题/播放/点赞/链接（行数据或 get） | `GET .../monitor/hit/list` |
| P-M7-004 IP 主题 | 主题摘要 + **作品子表**（hit 字段子集） | `GET .../ip-theme/list` · `GET .../ip-theme/{id}` |
| P-M7-002/005 高/低粉 | 账号基础 + 近 7 日粉丝迷你趋势（若实现） | `.../high-follower/list` · `.../low-follower/list` |
| P-M7-006 低分 | 完播率/时长/标题详情 | `.../low-score/list` |

**图表轴（P-M7-004 补）**：C2 左图 X=日期 Y=作品数/播放 · 右图 TOP 主题横向条（`theme_name`/`avg_play`）。

---

## 3. 分页字段与 API

> HTTP 前缀 SSOT：`/admin-api/ops/monitor/**`（[`API-M7`](../engineering/API-M7-作品监测.md) · `MonitorController`）

### 3.1 P-M7-001 外部账号分析

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/external/list` |
| **表格列** | 账号名 · 平台(`dict_platform_type`) · 粉丝数 · 作品数 · 近7日增粉 · 行业 · 更新时间 |
| **图表** | C2 粉丝趋势（折线）· TOP10 粉丝柱形 |
| **抽屉** | 外部账号详情 · `GET .../external/get?id=`（若实现）或行数据展开 |
| **筛选联动** | `platformType` · `ipGroupId` · `industry` · 日期 |

### 3.2 P-M7-002 高粉账号分析

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/high-follower/list` |
| **阈值** | 页头 Tooltip：高粉定义见 PRD BR-002（与后端筛选一致） |
| **表格列** | 账号 · 平台 · 粉丝数 · 所属 IP 组 · 运营人(`UserSelect` 回显) · 上榜天数 |
| **图表** | 粉丝分布 histogram · TOP 排名 |

### 3.3 P-M7-003 爆款作品分析

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/hit/list` |
| **业务规则** | 爆款 = 播放 ≥ 100w（BR-003 · API-M7 §1.2） |
| **表格列** | 标题 · 账号 · 平台 · 播放量 · 点赞 · 发布日期 · 内容类型(`dict_content_type`) |
| **截图 SSOT** | [`delivery-screenshots/11-monitor-hot-works.png`](./delivery-screenshots/11-monitor-hot-works.png) |

### 3.4 P-M7-004 IP 主题数据

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/ip-theme/list` · 详情 `GET .../ip-theme/{id}` |
| **表格列** | 主题名 · IP 组 · 作品数 · 平均播放 · 爆款占比 |
| **下钻** | 行点击 → 抽屉内作品子表（同 monitor hit 字段子集） |

### 3.5 P-M7-005 低粉账号分析

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/low-follower/list` |
| **表格列** | 账号 · 平台 · 粉丝数 · IP 组 · 持续低粉天数 · 最近发文 |
| **图表** | 低粉账号占比饼图 |

### 3.6 P-M7-006 低分作品分析

| 区域 | 内容 |
|------|------|
| **API** | `GET /admin-api/ops/monitor/low-score/list` |
| **业务规则** | 低分 = 完播率 < 20%（BR-004） |
| **表格列** | 标题 · 账号 · 完播率 · 播放量 · 时长 · 发布日期 |
| **图表** | 完播率分布 · 低分趋势 |

### 3.7 P-M7-007 行业分析（Spec 历史 / 无菜单）

| 项 | 说明 |
|----|------|
| API 草案 | `GET /admin-api/ops/monitor/industry/{id}` |
| 状态 | **未**在 OPS-MENU 注册；实现以 Vue/Controller 为准时再开 FR |

---

## 4. 交互与权限

| 行为 | 规则 |
|------|------|
| 查询 | B 区「查询」刷新 C1–C3；重置清空 B 并默认近 30 天 |
| 排序 | 表格 `sortable` 列 → query `orderBy` / `orderAsc`（与 API 对齐） |
| 导出 | 若有按钮 → 调用 list 同源接口 + 客户端 Excel（或 export 端点 ⚠️ 未文档化） |
| 空态 | 无数据 `el-empty`；筛选过窄提示调整日期 |
| 403 | 无 `oa:*-account:list` 权限隐藏菜单 |

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.3：§2.3–2.4 抽屉下钻/作品子表/export API · IP 主题图表轴 |
| 2026-10-02 | v1.2：Football `/ops/monitor/*` 路由 · 六页字段/图表/API · 原型索引交叉引用 |
| 2026-06-11 | v1.1：抽屉详情 |
| 2026-06-07 | v1.0：初版 |

---

## 全局规范引用

> 强关联 · 字典 · 错误码 1500–1504 · 脱敏：[`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md)
