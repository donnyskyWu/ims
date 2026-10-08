# UX-OPS 页面原型索引

> **版本**：v1.2 | 2026-10-02  
> **路由 SSOT**：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)  
> **设计规范**：[`UX-OPS-设计规范.md`](./UX-OPS-设计规范.md)  
> **Penpot 模板**：无文件时填 `—`；有设计稿时填 `https://penpot.app/...`（本表 SSOT）

**线框约定**：区域 **A** = 页头 · **B** = 筛选 · **C** = 数据区（见设计规范 §2）

---

## 1. 全量菜单映射（type=2 页面）

| menu_id | 名称 | Football 路由 | UX 文档锚点 | 线框 A/B/C（摘要） | 截图 SSOT | Penpot |
| ---: | --- | --- | --- | --- | --- | --- |
| 6168 | 首页仪表盘 | `/ops/dashboard` | UX-M0 §2 | A:标题+刷新 · B:快捷入口 · C:指标卡+趋势 | `delivery-screenshots/04-dashboard.png` · `A00-dashboard.png` | — |
| 6111 | 外部账号分析 | `/ops/monitor/external-account` | UX-M7 §4.1 | A:标题 · B:平台/IP/日期 · C:汇总卡+趋势+表+抽屉 | （待补拍） | — |
| 6112 | 高粉账号分析 | `/ops/monitor/high-fans-account` | UX-M7 §4.2 | 同上 | （待补拍） | — |
| 6113 | 爆款作品分析 | `/ops/monitor/hot-works` | UX-M7 §4.3 | B 含爆款阈值说明 · C 排名表 | `11-monitor-hot-works.png` | — |
| 6114 | IP主题数据 | `/ops/monitor/ip-theme` | UX-M7 §4.4 | B IP 组 · C 主题维度表+图 | （待补拍） | — |
| 6115 | 低粉账号分析 | `/ops/monitor/low-fans-account` | UX-M7 §4.5 | 同高粉布局 | （待补拍） | — |
| 6116 | 低分作品分析 | `/ops/monitor/low-score` | UX-M7 §4.6 | B 完播率筛选 · C 低分列表 | （待补拍） | — |
| 6117 | 内容管理 | `/ops/production/content` | UX-M2 P-M2-006 | A:新建 · B:状态/IP/任务 · C:表格+抽屉创作 | `07-content.png` · `A12-content-list.png` | — |
| 6118 | 内容审核 | `/ops/production/content/review` | UX-M2 P-M2-008 | A:Tab 待审/已审 · B:筛选 · C:审核表 | `08-content-review.png` · `B02-content-review-list.png` | — |
| 6119 | 内容知识库 | `/ops/production/knowledge` | UX-M2 P-M2-009 | A:新建 · B:分类 · C:卡片/列表 | `17-knowledge.png` | — |
| 6120 | 公推模板库 | `/ops/production/layout-template` | UX-M2 P-M2-013 | A:导入 · B:名称 · C:模板表 | `18-layout-template.png` | — |
| 6121 | 计划管理 | `/ops/production/plan` | UX-M2 P-M2-011 | A:新建计划 · B:周期/IP · C:计划表 | `05-plan.png` | — |
| 6122 | SOP管理 | `/ops/production/sop` | UX-M2 P-M2-001 | A:新建 · C:DAG/列表 | `16-sop.png` | — |
| 6123 | SOP审核 | `/ops/production/sop/review` | UX-M2 §11 P-M2-017 | A:统计卡 · B:筛选 · C:队列表+审核抽屉 | （待补拍） | — |
| 6124 | 我的任务 | `/ops/production/task` | UX-M2 P-M2-003 | A:Tab 我的/全部 · B:状态 · C:任务表 | `06-task.png` · `A10-my-task-list.png` | — |
| 6194 | 工作任务管理 | `/ops/production/work-task` | UX-M2 §1.1 | A:三 Tab · B:周期/IP · C:登记/执行/矩阵 | `22-work-task.png` · `A06~A09` | — |
| 6125 | 自定义查询 | `/ops/analysis/custom-query` | UX-M6 P-M6-013 | A:保存查询 · B:维度度量 · C:结果表 | `21-custom-query.png` | — |
| 6126 | 数据报表 | `/ops/analysis/data-report` | UX-M6 P-M6-002~009 | A:报表 Tab · B:日期/IP · C:报表网格 | `15-data-report.png` | — |
| 6127 | 总体财务分析 | `/ops/analysis/financial-analysis` | UX-M6 P-M6-010 | B:财年 · C:财务图表 | （待补拍） | — |
| 6128 | 漏斗分析 | `/ops/analysis/funnel-analysis` | UX-M6 P-M6-011 | B:漏斗选择 · C:步骤转化图 | （待补拍） | — |
| 6129 | 指标管理 | `/ops/analysis/metric` | UX-M6 P-M6-001 | A:新建指标 · B:分类 · C:指标表 | `20-metric.png` | — |
| 6130 | 指标分析 | `/ops/analysis/metric-analysis` | UX-M6 | B:指标/日期 · C:趋势 | （待补拍） | — |
| 6131 | 数据大屏 | `/ops/analysis/screen` | UX-M6 P-M6-014 | 全屏 C:大屏组件 | （待补拍） | — |
| 6132 | 大屏配置 | `/ops/analysis/screen-config` | UX-M6 P-M6-015 | A:新建 · C:布局编辑器 | （待补拍） | — |
| 6133 | 采集日志 | `/ops/collect/log` | UX-M10 §3 | B:任务/时间 · C:日志表 | （待补拍） | — |
| 6134 | 私域桥接 | `/ops/collect/private-domain-bridge` | UX-M10 | B:桥接状态 · C:配置表 | （待补拍） | — |
| 6135 | 数据质量 | `/ops/collect/quality` | UX-M10 §4 | B:规则 · C:质量报告 | （待补拍） | — |
| 6136 | 采集任务 | `/ops/collect/task` | UX-M10 §2 | A:新增 · B:平台/方式 · C:任务表 | （待补拍） | — |
| 6140 | 消息管理 | `/ops/system-oa/system-message` | UX-M9 | C:消息列表 | （待补拍） | — |
| 6141 | 系统参数 | `/ops/system-oa/system-param` | UX-M9 | Tab:基础/钉钉/审核 | `12-system-param.png` · `12b` · `12c` | — |
| 6142 | 订单归因 | `/ops/performance/order-attribution` | UX-M3 P-M3-007 | B:订单/渠道 · C:归因表 | （待补拍） | — |
| 6143 | 考核执行 | `/ops/performance/perf-execution` | UX-M3 P-M3-003 | B:周期 · C:执行表 | （待补拍） | — |
| 6144 | 绩效结果 | `/ops/performance/perf-result` | UX-M3 P-M3-005 | B:人员 · C:结果表 | `13-perf-result.png` | — |
| 6145 | 考核模板 | `/ops/performance/perf-template` | UX-M3 P-M3-001 | A:新建 · C:模板表 | （待补拍） | — |
| 6146 | 账号成本 | `/ops/finance/account-cost` | UX-M5 P-M5-001 | A:录入 · C:成本表 | `14-account-cost.png` | — |
| 6147 | ROI分析 | `/ops/finance/roi-analysis` | UX-M5 P-M5-003 | B:周期 · C:ROI 图+表 | （待补拍） | — |
| 6148 | 公司管理 | `/ops/internal/company` | UX-M4 P-M4-001 | A:新建 · C:公司表 | `23-company.png` | — |
| 6149 | 平台账号 | `/ops/internal/internal-account` | UX-M4 §7 | A:Tab 平台 · B:名称 · C:账号表 | `10-internal-account.png` | — |
| 6151 | 手机管理 | `/ops/internal/phone` | UX-M4 P-M4-005 | C:设备表 | `25-phone.png` | — |
| 6152 | 实名人 | `/ops/internal/realname` | UX-M4 P-M4-003 | B:姓名 · C:脱敏列表 | `24-realname.png` | — |
| 6153 | 手机卡 | `/ops/internal/simcard` | UX-M4 P-M4-006 | C:卡表+侧滑账号 | `26-simcard.png` | — |
| 6154 | 账号分析 | `/ops/operations/account-analysis` | UX-M1 P-M1-003 | B:IP/运营 · C:分析图表 | （待补拍） | — |
| 6156 | 人效盘点 | `/ops/operations/efficiency` | UX-M1 P-M1-007 | B:周期 · C:人效表 | （待补拍） | — |
| 6157 | 粉丝分析 | `/ops/operations/fans-analysis` | UX-M1 P-M1-004 | B:账号/IP · C:粉丝趋势 | （待补拍） | — |
| 6158 | 内部作品分析 | `/ops/operations/internal-content` | UX-M1 P-M1-006 | B:平台/日期 · C:作品表 | （待补拍） | — |
| 6159 | IP组管理 | `/ops/operations/ip-group` | UX-M1 P-M1-001 | A:新建 · B:树 · C:详情 Tab | `09-ip-group.png` · `A01~A05` | — |
| 6160 | AI模型 | `/ops/config/config-ai-model` | UX-M8 | A:测试连接 · C:模型表 | （待补拍） | — |
| 6161 | AI提示词 | `/ops/config/config-ai-prompt` | UX-M8 | C:提示词表 | （待补拍） | — |
| 6162 | 外部采集配置 | `/ops/config/config-external-collect` | UX-M8 | C:配置表 | （待补拍） | — |
| 6163 | 外部数据配置 | `/ops/config/config-external-data` | UX-M8 | C:数据源表 | （待补拍） | — |
| 6164 | 内部采集配置 | `/ops/config/config-internal-collect` | UX-M8 | C:配置表 | （待补拍） | — |
| 6165 | 元数据维护 | `/ops/config/config-metadata` | UX-M8 | C:元数据树/表 | （待补拍） | — |
| 6166 | 订单采集配置 | `/ops/config/config-order-collect` | UX-M8 | C:配置表 | （待补拍） | — |
| 6167 | 阈值规则 | `/ops/config/config-threshold` | UX-M8 | C:规则表 | （待补拍） | — |
| 6175 | 全部任务 | `/ops/production/task/all` | UX-M2 §4.0 P-M2-018 | 默认 Tab 全部 · 多 UserSelect | `19-task-all.png` | — |

### 1.1 隐藏 / 非菜单页

| 路由 | UX | 截图 | 说明 |
|------|-----|------|------|
| `/ops/internal/personal-account` | UX-M4 P-M4-010 | （待补拍） | 个人账号 · API ADR-060 stub |
| `/ops/internal/triple-rel` | UX-M4 P-M4-011 | — | 三方关联 · 隐藏菜单 |
| `/ops/production/content/edit` | UX-M2 P-M2-007 | `A13-content-create-drawer.png` | 主路径为列表抽屉 |

---

## 1.2 UX 覆盖摘要（2026-10-02 · DOC-UX-PAGE-FULL-02）

| 指标 | 数值 |
|------|------|
| 菜单 type=2 页面 | **55**（✅ **55/55** ≥85） |
| 二级面（Tab/抽屉/隐藏路由，独立 Spec 节） | **22**（✅ **22/22** ≥85） |
| **审计合计** | **77** |
| Checklist ≥85（完整） | **77** |
| 50–84（⚠️ 部分） | **0** |
| &lt;50（❌ 缺失） | **0** |
| **UX Checklist 可确认已全部完整** | **可确认：是（含 stub 标注）** — M4 个人账号/三方关联等 **无 Vue** 但有最小 Spec；现网缺口见覆盖审计 **§5.4** |
| **现网 Vue 100% 可还原** | **否** — 同 §5.4（质量规则 dialog · M2 SOP 时间轴等） |

明细矩阵：[`OPS-UX-PAGE-COVERAGE-20261002.md`](../delivery/OPS-UX-PAGE-COVERAGE-20261002.md) · Checklist 定义：[`UX-OPS-设计规范.md §8`](./UX-OPS-设计规范.md)

---

## 2. Spec 级线框示例（结构化 md）

### 2.1 P-M1-001 IP 组管理 `#/ops/operations/ip-group`

```
A | 标题「IP 组管理」                    [+ 新建大组]
B | （左）el-tree 大组/小组  （右）无独立 B — 筛选在 Tab 内
C | Tab: 基本信息 | 成员 | 账号 | 关联作者 | 统计
    成员 Tab: UserSelect + dict_position · 表格分页
```

### 2.2 P-M2-016 工作任务 `#/ops/production/work-task`

```
A | Tab: 登记 | 执行 | 矩阵
B | 周期周选择 · IpGroupTreeSelect(scope=led) · UserSelect
C | 登记: 可编辑表 · 行级 confirm/withdraw · 合并执行
    执行: 只读执行视图 · 矩阵: WorkTaskMatrixTable
```

### 2.3 P-M4-008 平台账号 `#/ops/internal/internal-account`

```
A | 平台 Tab（微信/抖音/快手/…）         [+ 新建账号]
B | accountName 模糊 · 状态 DictSelect
C | 表格 · 行内双状态(ADR-078) · 抽屉详情/替换
```

---

## 3. 截图采集

见 [`delivery-screenshots/README.md`](./delivery-screenshots/README.md)。Shell 侧栏总览：`03-ops-sidebar.png`。

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.2：§1.2 同步 **77/77** · 可确认：是（含 stub 标注） |
| 2026-10-02 | v1.1：§1.2 覆盖摘要 · 链 OPS-UX-PAGE-COVERAGE |
| 2026-10-02 | v1.0：71 菜单项映射 · Penpot 占位 · A/B/C 线框 |
