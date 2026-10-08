# IMS E2E 验收策略（PO / Agent / CI）

> 版本 2026-10-07 · 配套 [`IMS-E2E测试用例Checklist.md`](./IMS-E2E测试用例Checklist.md) · 执行入口 **`ims-web/scripts/run_e2e.ps1`** · 完整交付环与 PO **UAT 状态** 列见 [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md)、[`IMS-PRD功能点执行对照表.md`](../开发方案/IMS-PRD功能点执行对照表.md)

## 角色分工

| 角色 | 动作 |
|------|------|
| **Agent / CI** | 一键跑 `run_e2e.ps1`（或 `npm run test:e2e:ci`），产出 `e2e_result.txt` + `playwright-report/index.html` |
| **PO** | 看 HTML 报告与 Checklist 编号；**签收 = closure / 未来 acceptance**，不是 narrow smoke |
| **开发** | 新功能闭环时补 **Given/When/Then** 对应用例 ID，优先扩 `closure-*` 或 `acceptance/*` |

## 两类自动化（勿混签）

| 类型 | 目录模式 | 证明什么 | 能否 PO 签收 |
|------|----------|----------|--------------|
| **Narrow smoke** | `smoke-*.spec.ts` | 登录 + 路由 + 列表/h1 可加载 | 否（健康检查 only） |
| **Acceptance E2E** | `closure-*.spec.ts` · 未来 `acceptance/*.spec.ts` | Checklist 步骤 + **可见 UI 结果**（表格行、状态 tag、toast/链接） | 是（切片签收） |
| **L3 外部联调** | `dingtalk-org-l3.spec.ts` · `tests/test_org_dingtalk_l3.py` | 真实钉钉 OAuth / 组织页 + API（需 PO `.env`） | **组织模块已验收†** 必要项；**不在**默认 21 spec |

## L3 层（组织 · 真钉钉）

| 门禁 | 条件 | 入口 |
|------|------|------|
| **E2E-ORG-DING-01**（stub） | `IMS_DINGTALK_L3=1` + `ims-backend/.env` 凭证 | `ims-backend/scripts/run_dingtalk_l3.ps1` 或 `npm run test:e2e:dingtalk` |
| pytest | 同上 | `tests/test_org_dingtalk_l3.py`（默认 **skip**） |
| Playwright | 同上；`playwright.config.ts` 在 `IMS_DINGTALK_L3≠1` 时 **ignore** `dingtalk-org-l3.spec.ts` | 与 pytest 同脚本编排 |

组织矩阵行 **已验收** = 默认 **21/21 PASS** + **L3 PASS** + PO **UAT 状态=通过**（见 PRD 对照表 †）。

## 一键执行（PO 无需手敲 npm）

```powershell
# 推荐：自动起 18080 + 6173（若未运行），再跑全量 21 spec
cd d:\self\sy\IMS系统产品\ims-web
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_e2e.ps1

# 或 ims-web 目录
npm run test:e2e:ci
```

服务已手动启动时：`.\scripts\run_e2e.ps1 -SkipServe`

L3 钉钉（不计入 21 spec）：

```powershell
cd d:\self\sy\IMS系统产品\ims-web
npm run test:e2e:dingtalk
```

## closure → Checklist 映射（当前 5 条）

| Spec | Checklist ID | Given | When | Then（可见） |
|------|--------------|-------|------|----------------|
| `closure-flow-start-todo.spec.ts` | **E2E-FLOW-01** | admin 已登录 · 有已发布模板 | UI 发起 → 我的待办「通过」 | 待办行消失 · 实例列表 **已通过** tag |
| `closure-flow-timeout-urge.spec.ts` | **E2E-FLOW-02** | 种子超时待办 | 督办 Tab · 点督办 | 提醒次数 +1 · 分布/指标可见 |
| `closure-alert-rule-trial.spec.ts` | **E2E-S11-01** 切片 | 规则页 | 新建启用 · 试跑 | toast 成功 · 命中 +1 |
| `closure-alert-handle-tab.spec.ts` | **E2E-S11-处置** 切片 (#44) | 试跑 OPEN 预警 | live「处理」· 处置/去重 Tab | toast · **HANDLED** · **DEDUP-LIVE** |
| `closure-perf-issue-export.spec.ts` | **E2E-S9** 切片 | CONFIRMED 考核 | UI 下发 · 导出 CSV | 下载含 BOM · ISSUED 行 |
| `closure-content-publish.spec.ts` | **E2E-S7** 切片 | 超计划发布单 | 督办 hint · 回填链接 | **已归档** · **已回填** 链接 |

## 失败排查

1. `e2e_result.txt` 末行 `N passed` 与 ExitCode  
2. 登录 preflight 失败 → `ims-backend/scripts/init_ims_db.ps1` 后重启 API  
3. admin 锁定 → 保持 **`--workers=1`**（已在脚本与 `playwright.config.ts` 固定）  
4. HTML 报告逐步截图与 trace（Playwright 默认 list + html）
