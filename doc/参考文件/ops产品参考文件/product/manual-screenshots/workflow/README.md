# 业务线操作手册截图（workflow）

> 生成于 **2026-08-25** · Playwright：`football-front/apps/web-ele/tests/product-manual-workflow.spec.ts`  
> 手册正文：[`../OPS业务操作手册-IP组与工作任务.md`](../OPS业务操作手册-IP组与工作任务.md)

## 业务线 A · IP 组 + 组长登记 + 执行创作

| 文件 | 说明 |
|------|------|
| `A00-dashboard.png` | 首页仪表盘 |
| `A01-ip-group-tree.png` | IP 组管理 · 树形结构 |
| `A02-ip-group-create-dialog.png` | 新建大组对话框 |
| `A03-ip-group-detail.png` | IP 组详情头 |
| `A04-ip-group-members.png` | 成员管理 Tab |
| `A05-ip-group-anchors.png` | 关联作者 Tab |
| `A06-work-task-register.png` | 工作任务 · 任务登记 |
| `A07-work-task-register-loaded.png` | 登记单已加载 |
| `A08-work-task-match-picker.png` | 赛事选择器 |
| `A09-work-task-matrix.png` | 任务管理矩阵（组长视角） |
| `A10-my-task-list.png` | 我的任务 |
| `A11-task-execute.png` | 任务执行页 |
| `A12-content-list.png` | 内容管理 |
| `A13-content-create-drawer.png` | 新增内容抽屉 |

## 业务线 B · 运营主管管理 + 审核

| 文件 | 说明 |
|------|------|
| `B01-manager-work-task-matrix.png` | 任务管理矩阵（主管视角） |
| `B02-content-review-list.png` | 内容审核列表 |
| `B03-content-review-detail.png` | 审核详情 |
| `B04-system-param-review-config.png` | 系统参数 · 内容审核配置 |

## 复采命令

```powershell
.\scripts\start-ops-dev.ps1 -Beta
cd football-front/apps/web-ele
npx playwright test tests/product-manual-workflow.spec.ts --project=chromium
```
