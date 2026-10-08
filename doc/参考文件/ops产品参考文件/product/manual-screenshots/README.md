# 产品手册截图说明

> 生成于 2026-08-10（**2026-09-20** 主流程重采，登录联调通过后），环境：`http://127.0.0.1:5777`（Football 壳 + OPS）  
> Word 产出：`docs/product/产品使用操作手册.docx`  
> 构建脚本：`docs/product/_build_manual_docx.py`

## 结论（相对 v1.0 Markdown）

- 原手册 `产品使用操作手册.md` **无系统化截图**（仅文字 / 表格）。
- 本次补齐主要章节界面截图，并写入 Word。

## 已采集

| 文件 | 对应章节 / 页面 | URL |
|------|-----------------|-----|
| `01-login.png` | 登录页 | `/auth/login` |
| `02-home-welcome.png` | 登录后欢迎页 | `/welcome` |
| `03-ops-sidebar.png` | 侧栏「运营数据」展开 | `/welcome` |
| `04-dashboard.png` | 首页仪表盘 | `/ops/dashboard` |
| `05-plan.png` | 计划管理列表 | `/ops/production/plan` |
| `05b-plan-create.png` | 新增计划对话框 | `/ops/production/plan`（弹窗） |
| `06-task.png` | 我的任务 | `/ops/production/task` |
| `07-content.png` | 内容管理 | `/ops/production/content` |
| `08-content-review.png` | 内容审核 | `/ops/production/content/review` |
| `09-ip-group.png` | IP 组管理 | `/ops/operations/ip-group` |
| `10-internal-account.png` | 平台账号管理（账号代表页） | `/ops/internal/internal-account` |
| `11-monitor-hot-works.png` | 爆款作品分析（监测代表页） | `/ops/monitor/hot-works` |
| `12-system-param.png` | 系统参数 · 基础配置 | `/ops/system-oa/system-param` |
| `12b-system-param-dingtalk.png` | 系统参数 · 钉钉配置 | 同上 Tab |
| `12c-system-param-review.png` | 系统参数 · 内容审核 | 同上 Tab |
| `13-perf-result.png` | 绩效结果 | `/ops/performance/perf-result` |
| `14-account-cost.png` | 账号成本管理 | `/ops/finance/account-cost` |
| `15-data-report.png` | 数据报表 | `/ops/analysis/data-report` |
| `16-sop.png` | SOP 管理 | `/ops/production/sop` |
| `17-knowledge.png` | 内容知识库 | `/ops/production/knowledge` |
| `18-layout-template.png` | 公推模板库 | `/ops/production/layout-template` |
| `19-task-all.png` | 全部任务 | `/ops/production/task/all` |
| `20-metric.png` | 指标管理 | `/ops/analysis/metric` |
| `21-custom-query.png` | 自定义查询 | `/ops/analysis/custom-query` |
| `22-work-task.png` | 工作任务管理 | `/ops/production/work-task` |
| `23-company.png` | 公司管理 | `/ops/internal/company` |
| `24-realname.png` | 实名人管理 | `/ops/internal/realname` |
| `25-phone.png` | 手机管理 | `/ops/internal/phone` |
| `26-simcard.png` | 手机卡管理 | `/ops/internal/simcard` |

## 未单独截 / 跳过

| 页面 | 原因 |
|------|------|
| SOP 编辑画布 | 需进入模板编辑子页 |
| 平台账号 · 采集 Tab | 详情内 Tab，待专项补拍 |
| 人效盘点 / 粉丝分析等运营子页 | 以 IP 组为代表页覆盖运营管理 |
| 数据采集各页 | 手册第 17 章仅边界说明（Out of Scope），未截 |
| 外部 SSO / 独立登录页 | 本期不写 |

## 注意事项

- 演示环境多为「暂无数据」，属联调常态，不影响界面结构示意。
- 文档与截图中 **不要写入** client-secret、Cookie、真实 Token 等敏感值。
- 重新采集 PNG：`python docs/product/_capture_delivery_screenshots.py`（同步至本目录与 `delivery-screenshots/`）
- 重新生成 Word：`python docs/product/_build_manual_docx.py`

## 如何打开 Word

1. 资源管理器打开：`docs\product\产品使用操作手册.docx`
2. 或用 Microsoft Word / WPS / LibreOffice 直接打开该文件。
3. Markdown 原文仍保留：`docs\product\产品使用操作手册.md`
