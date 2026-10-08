# 交付截图目录

**同步日期**：2026-09-20  
**采集环境**：`http://localhost:5777`（Football 壳 + 本地 Gateway `:48080`）  
**采集脚本**：[`../_capture_delivery_screenshots.py`](../_capture_delivery_screenshots.py)（Playwright；亦可 Cursor IDE Browser MCP 补拍）

## 主流程（与手册一致）

| 文件 | 页面 |
|------|------|
| `01-login.png` | 登录页 |
| `02-home-welcome.png` | 欢迎页 |
| `03-ops-sidebar.png` | 侧栏运营数据（仪表盘页） |
| `04-dashboard.png` | 首页仪表盘 |
| `05-plan.png` | 计划管理 |
| `05b-plan-create.png` | 新增计划（历史保留） |
| `06-task.png` | 我的任务 |
| `07-content.png` | 内容管理 |
| `08-content-review.png` | 内容审核 |
| `09-ip-group.png` | IP 组管理 |
| `10-internal-account.png` | 平台账号管理 |
| `11-monitor-hot-works.png` | 爆款作品分析 |
| `12-system-param.png` | 系统参数 · 基础 |
| `12b-system-param-dingtalk.png` | 系统参数 · 钉钉 |
| `12c-system-param-review.png` | 系统参数 · 内容审核 |
| `13-perf-result.png` | 绩效结果 |
| `14-account-cost.png` | 账号成本 |
| `15-data-report.png` | 数据报表 |

## 增量（IP 组 / 工作任务 / 审核）

`A*.png`、`B*.png` 为 2026-08-25 工作流专项截图，保留供 IP 组与工作任务手册引用。

## 重新采集

```powershell
cd "d:\self\sy\运营数据平台\202606\wd"
python docs/product/_capture_delivery_screenshots.py
python docs/product/_build_product_delivery_docx.py
```

前置：本地栈已启动（`.\scripts\start-ops-dev.ps1`），账号 `admin` / `admin123`，租户 `1`。
