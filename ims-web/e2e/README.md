# IMS Playwright E2E 窄路径对照

> 对照 `doc/测试方案/IMS-E2E测试用例Checklist.md` 十二条主线 **S1–S12**。  
> **PO 签收**看 **closure-***（acceptance）与 Checklist 步骤；**smoke-*** 仅为路由健康检查。策略：[`IMS-E2E验收策略.md`](../../doc/测试方案/IMS-E2E验收策略.md)。

| 主线 | 场景摘要 | smoke spec | 断言要点 |
|------|----------|------------|----------|
| **S1** | 员工全生命周期 | `smoke-auth-org.spec.ts` · **`closure-s1-lifecycle.spec.ts`（#73）** | smoke：组织页标题；#73：模拟入职可见 → 领用 → 调岗 diff → 离职冻结 → 归还/换证 |
| **S2** | 直播全链路 | `smoke-live.spec.ts` · **`closure-live-session-report.spec.ts`（#56）** | smoke：直播管理列表；closure：登记→风控→下播核准 · **CONFIRMED** |
| **S3** | 场次-成本-利润 | `smoke-fin.spec.ts` · **`closure-fin-cost-profit.spec.ts`（#50）** · **`closure-fin-share-payoff.spec.ts`（#57）** · **`closure-fin-period-lock.spec.ts`（#59）** | smoke：利润页标题；#50：成本核准 → 利润 **81400**；#57：分成双审发放 **PAID_OFF** → 台账 **四账一致**；#59：结账 **LOCKED** → 录入 **1142** → R4 后红冲 |
| **S4** | 账号领用流转 | `smoke-acct.spec.ts` | 登录 → `/ims/corp/account/douyin` 标题「抖音」+ 账号 table |
| **S4 (#47)** | 池领用/归还 closure | `closure-corp-account-checkout.spec.ts` | `AC-E2E-POOL` 领用三步→在用→归还→时间线 |
| **S4 (#58)** | 冲话费 + 凭证门禁 | `closure-corp-account-recharge.spec.ts` | 1000 无凭证成功 · 6000 无凭证 **1025** · 补凭证后 admin 隐藏 URL · `e2e_acct_r3` 可见 |
| **S4 (#60)** | 流转 + 他人领用 1021 | `closure-corp-account-transfer.spec.ts` | `AC-E2E-XFER` 领用至在用 · `e2e_acct_peer` 再领用 **1021** · 流转待确认 → 确认接收 · 责任人「流转同事」· 时间线 TRANSFER |
| **S4 (#62)** | 收回冻结 1022 | `closure-corp-account-recall.spec.ts` | `AC-E2E-RECALL` 领用至在用 ·「收回」直接 **冻结** · 再领用/再流转 **1022** · 时间线 FREEZE |
| **S4 (#64)** | 账实核对 1026 | `closure-corp-account-reconcile.spec.ts` | `AC-E2E-RECON` · 101.99/100 → **1.99%** 一致 · 102/100 → **2.00%** **1026** · 财务核查工单 |
| **S4 (#66)** | 解冻回池 | `closure-corp-account-unfreeze.spec.ts` | `AC-E2E-UNFREEZE` 收回冻结 → 解冻 **IN_POOL** · 时间线 UNFREEZE · 再领用成功 |
| **S4 (#70)** | 冲话费成本汇总 | `closure-corp-account-summary.spec.ts` | `AC-E2E-SUM` · 2026-04 **200.00** / 2 笔 · 账号 / 部门#70070 / 抖音 · 2026-03 **50.00** 单独成月 |
| **S4 (#123)** | 资产同步转移提示 | `closure-corp-account-asset-transfer.spec.ts` | `AC-E2E-ASSETX` 绑定办公设备后流转 · 弹窗「是否同步发起资产转移」· 仅转账号不阻断 · 新责任人工作台消息 · 确认后再提示 · 跳转办公设备 |
| **S5** | 资产采购领用 | `smoke-asset.spec.ts` · **`closure-asset-purchase-import.spec.ts`（#68）** · **`closure-asset-lifecycle.spec.ts`（#63）** · **`closure-asset-penetrate.spec.ts`（#65）** · **`closure-asset-reverse-entry.spec.ts`（#72）** | smoke：办公设备列表；#68：采购 CSV 部分成功 · 第 3 行 `assetName`；#63：登记→领用→使用→归还→报废；#65：实名人下 5 层 · 第 6 层 **1013** · 使用人在用/已归还/已报废；#72：按账号/场次反查 · 入口不存在 **1500** · 领用后「在用」 |
| **S6** | 证件录入预警 | `smoke-cert.spec.ts` · **`closure-corp-cert-watermark.spec.ts`（#55）** · **`closure-corp-cert-expire.spec.ts`（#61）** | smoke：证件列表；#55：水印 + 脱敏号；#61：T−30/T−7/T−0 黄/红/锁定 + 工作台提醒 |
| **S7** | 内容生产 AI | `smoke-content.spec.ts` | 登录 → `/ims/content/list` 标题「内容管理」+ table |
| **S8** | AI 资产分发 | `smoke-air-skill.spec.ts` | 登录 → `/ims/air/skill` 标题「技能库」+ table |
| **S9** | 绩效考核周期 | `smoke-perf.spec.ts` | 登录 → `/ims/perf/execution` 标题「执行考核」 |
| **S10** | 培训考试 | `smoke-train.spec.ts` | 登录 → `/ims/train/task` 标题「学习任务管理」+ table |
| **S11** | 预警闭环 | `smoke-alert.spec.ts` | 登录 → `/ims/alert/rule` 标题 |
| **S12** | 数据消费闭环 | `smoke-bi-report.spec.ts` | 登录 → `/ims/bi/report` 标题「报表中心」 |

**补充（非 S1–S12 主线编号）**

| 场景 | smoke spec | 断言要点 |
|------|------------|----------|
| **FLOW** | `smoke-flow.spec.ts` | 登录 → `/ims/flow` 标题「流程管理」+ 默认「流程实例」tab 下 table |
| **FLOW 超时督办** | `smoke-flow-timeout.spec.ts` | 登录 → `/ims/flow` · 点「超时督办」tab · BR-115 指标行「月度超时率」+ 督办 table 表头/空态 |
| **WORKBENCH** | `smoke-workbench.spec.ts` | 登录 → `/ims/workbench` 问候 h1 +「流程待办」卡片数字 + 流程待办 table |
| **WORKBENCH (#46)** | `closure-workbench-todo-message.spec.ts` | 未读 `E2E-WB-MSG` →「标为已读」→ 待办 `E2E-WB-CLOSE` →「关闭」→ 计数减 1 |
| **HOME 运营看板** | `smoke-home.spec.ts` | 登录 → `/ims/home` 标题「运营仪表盘」+ 四 KPI 卡片 `.n` 非空 +「快捷入口」 |
| **ALERT 试跑** | `smoke-alert-trial.spec.ts` | 登录 → `/ims/alert/rule` · 规则 table · 若有启用规则则点「试跑」+ toast「试跑成功」 |

**逐步闭环（acceptance · 非 narrow · 保留上述 smoke）**

| 场景 | closure spec | 断言要点 |
|------|--------------|----------|
| **E2E-FLOW-01** | `closure-flow-start-todo.spec.ts` | 发起 → 实例表「进行中」→ 我的待办「通过」→ 待办消失 · 实例「已通过」 |
| **E2E-FLOW-02** | `closure-flow-timeout-urge.spec.ts` | 超时督办 Tab · 时长分布 · 督办 → 提醒次数 +1 |
| **E2E-S11-01 切片** | `closure-alert-rule-trial.spec.ts` | 新建启用规则 → 试跑 toast → 命中 +1 |
| **E2E-S11-处置 (#44)** | `closure-alert-handle-tab.spec.ts` | UI 试跑 → live「处理」→ 处置记录 HANDLED · 去重 DEDUP-LIVE |
| **E2E-S11-01/05 (#81)** | `closure-alert-rule-guard.spec.ts` | 非法 DSL **1009** · 重复编码 **1165** · 误报 **FALSE_ALARM** · 再响应 **1167** |
| **E2E-S3-切片 · FIN (#50)** | `closure-fin-cost-profit.spec.ts` | 纯 UI · LIVE 核准下播 → 成本提交/核准 → 利润 **CALCULATED** · **81400** · BR-107 完整率卡 |
| **E2E-S3-05/08 · FIN (#57)** | `closure-fin-share-payoff.spec.ts` | 纯 UI · 复用 #50 链 → 分成单财务审+业务审 → **已发放** · 拆分 **4,000** = 总额 → 台账 **四账一致** |
| **E2E-S3-06/07 · FIN (#59)** | `closure-fin-period-lock.spec.ts` | 纯 UI · 独立期间结账 **LOCKED** · 录入 **1142** · 未批更正 **1155** · R4 通过后红冲投放成本 · 利润 **82,400.00** / **RECALCULATED** |
| **E2E-S4-05/06 · CORP (#58)** | `closure-corp-account-recharge.spec.ts` | 纯 UI · `AC-E2E-POOL` 冲话费 · 1000 无凭证成功 · 6000 无凭证 **1025** · 补凭证 · 仅 `e2e_acct_r3` 见凭证号 |
| **E2E-S4-02/03 · CORP (#60)** | `closure-corp-account-transfer.spec.ts` | 纯 UI · `AC-E2E-XFER` · 他人领用 **1021** · 流转确认后责任人变更 · 时间线 TRANSFER |
| **E2E-S4-04 · CORP (#62)** | `closure-corp-account-recall.spec.ts` | 纯 UI · `AC-E2E-RECALL` · 收回 **FROZEN** · 领用/流转 **1022** · 时间线 FREEZE |
| **E2E-S4-07 · CORP (#64)** | `closure-corp-account-reconcile.spec.ts` | 纯 UI · `AC-E2E-RECON` · **1.99%** 一致 · **2.00%** **1026** · 财务核查工单 |
| **E2E-S4-10 · CORP (#70)** | `closure-corp-account-summary.spec.ts` | 纯 UI · `AC-E2E-SUM` · 2026-04 合计 **¥200.00** / 2 笔 · 账号 / 部门#70070 / 抖音 · 2026-03 **¥50.00** 不进 4 月 |
| **E2E-S9-切片** | `closure-perf-issue-export.spec.ts` | UI 方案+考核 → 算分/确认 → UI 下发 → 结果页导出 CSV（BOM + ISSUED 行） |
| **E2E-S9-01/02 (#86)** | `closure-perf-metric-pack.spec.ts` | 纯 UI · 得分规则重叠 **1152** · 重复编码 **1151** · 权重合计 99/101 **1154** · 合计 100 绑定成功 · 启用 COMPETE_SUBMIT_RATE **1153** |
| **E2E-S7-01 · 选题立项** | `closure-content-topic.spec.ts` | 纯 UI 提报选题 → 缺 SOP/计划发布日 **1052** → 选择 SOP+内容要求立项 → **已立项** / 可出任务；落选保持不可出任务 |
| **E2E-S7-切片 · 选题状态空态 (#159)** | `closure-content-topic-status.spec.ts` | 纯 UI · 筛选无命中显示状态空态 → 看板四列空态 → 缺 SOP/计划发布日红框仍回 **1052** → 立项后进入已立项列 |
| **E2E-S7-切片 · 计划** | `closure-content-plan-start.spec.ts` | UI SOP+计划 → 启动 → IN_PROGRESS + 任务列表 |
| **E2E-S7-切片 · SOP/计划 (#101)** | `closure-content-sop-plan.spec.ts` | 纯 UI · DAG 保存 → 新版本 v2 → 逻辑删除 → 计划草稿 DRAFT |
| **E2E-S7-切片 · 计划终止 (#36)** | `closure-content-plan-terminate.spec.ts` | 启动后申请终止 → 批准 → TERMINATED + 任务 TERMINATED |
| **E2E-S7-切片 · 任务** | `closure-content-task-execute.spec.ts` | UI 启动计划 → 执行页工作说明 → DONE |
| **E2E-S7-切片 · 工作任务 (#35)** | `closure-content-work-task.spec.ts` | 工作任务登记确认 → CONTENT_GENERATION 执行/提审 → e2e_author 审过 → DONE |
| **E2E-S7-切片 · 矩阵出任务 (#103)** | `closure-content-s2-matrix.spec.ts` | 按用例 SOP 绑定 → 矩阵改红黑 → 确认出任务 → 撤回 |
| **E2E-S7-切片 · 发布** | `closure-content-publish.spec.ts` | author 立项送审 → admin 审过 → UI 发布单 → 督办 hint → 回填 |
| **E2E-S7-切片 · 查看版式 (#114)** | `closure-content-view-layout.spec.ts` | 纯 UI · 列表「查看」与审核抽屉同一只读 `layout_html` · 无版式回退正文 · 脚本不渲染 |
| **E2E-S7-切片 · 审核场次 (#117)** | `closure-content-review-sessions.spec.ts` | 纯 UI · 传足两场 matchScheme 提审 → 审核抽屉只读 Tab + 场次列表 + 玩法摘要「2场」 |
| **E2E-S7-切片 · AI 文案 (#124)** | `closure-content-ai-copy.spec.ts` | 列表编辑打开 AI 文案 → 生成预览 → 采纳后正文可见标记 |
| **HOME 看板 (#38)** | `closure-home-dashboard.spec.ts` | `/ims/home` KPI「数据延迟」→ 刷新 dashboard → 账号数下钻抖音 → 快捷「登记工作任务」 |
| **E2E-S5-01 (#68)** | `closure-asset-purchase-import.spec.ts` | 纯 UI 文件选择器上传 CSV · 部分成功 2 条待审核 · 第 3 行 `assetName` · 坏编号不在台账 · 时间线「采购入台账」 |
| **E2E-S5-05 (#72)** | `closure-asset-reverse-entry.spec.ts` | 纯 UI 绑定 `AC-E2E-FIN` / `IMS20261008DYE0072` · 不存在入口 **1500** · 领用后账号反查「在用」· 场次反查不含只绑账号的那台 |
| **E2E-S1-01/03/04 与 S1-05～11 子集 (#73)** | `closure-s1-lifecycle.spec.ts` | 事件由 `s1_lifecycle_seed` 在浏览器外入队 · 之后纯 UI：在职/工作台、领用 `AC-E2E-S1`、调岗 diff、冻结与 **1006**、归还和换证后名下在用为 0 |
| **E2E-S10 问卷组卷/判分/重答 (#79)** | `closure-train-quiz-retake.spec.ts` | 纯 UI · 手工组卷及格分超题数拦截 · 交卷判分 · 不及格重答覆盖为最新成绩 · 及格后 **CONFIRMED** |
| **E2E-S6-02 (#61)** | `closure-corp-cert-expire.spec.ts` | 纯 UI 录入 T−30/T−7/T−0 → 审核 → 扫描 → 黄/红/锁定 · 工作台三条提醒 |
| **E2E-S6-03 切片 (#55)** | `closure-corp-cert-watermark.spec.ts` | 证件「查看」→ 水印含 admin · 不出原图 |
| **E2E-S2 窄切片 (#56)** | `closure-live-session-report.spec.ts` | 登记→风控→下播核准 · 19 位场次 · 列表 CONFIRMED |
| **E2E-S12-01 场次下钻 (#53)** | `closure-dc-session-drill.spec.ts` | 账号穿透 → 场次明细抽屉（GMV/净利润/投流成本）→ 导出 XLSX → 宽日期 **1181** |
| **E2E-S12-切片 · push-now (#39)** | `closure-bi-subscribe-push-now.spec.ts` | UI 新建报表+订阅 →「立即推送」→ 快照 GMV · 推送结果/上次推送 |
| **E2E-S12-05 切片 · share-approve (#40)** | `closure-bi-share-approve.spec.ts` | UI 敏感分享 →「分享审批」Tab 通过/驳回 → 分享链接 Tab 状态 |
| **E2E-S12-05 EXPIRED · share-expired (#41)** | `closure-bi-share-expired.spec.ts` | UI 敏感分享审批通过 →「分享链接」Tab「标记过期」→「已过期」 |
| **E2E-S12-02 (#87)** | `closure-bi-drill-pack.spec.ts` | 设计器拖入表格 → 六维逐级下钻 → 末端 **1195** → 导出 xlsx → 单元格穿透来源模块详情 |
| **WORKBENCH · AUTH-004 (#46)** | `closure-workbench-todo-message.spec.ts` | 种子未读消息标已读 · 种子待办关闭 · dashboard 计数联动 |

### 纯 UI 门禁（closure · Checklist v2.6.44+）

PO 签收要求：**closure 链 100% 经 UI 点击造数**，不得在后端「偷偷」写库。

| 允许 | 禁止 |
|------|------|
| `/login` 表单登录（admin / `e2e_author` 等） | `page.evaluate(() => fetch('/admin-api/…'))` |
| 菜单导航、Drawer/Modal 填表、行内按钮 | Playwright 侧 TestClient / 直连 18080 造数 |
| UI 保存后 `waitForResponse` 读 **id / 单号**（由刚才的点击触发） | 在 evaluate 里换 token、多用户 API 编排 |
| 环境只读：`E2E_BASE_URL`、init 库已有主数据（如抖音账号列表） | 用 API 绕过缺失的前端表单（应先补 UI 或标 TODO） |

**推荐写法（content 计划链）**

```typescript
import { loginAdmin, createSopViaUi, prepareIpGroupWithAdminMember, createDraftPlanViaUi, startPlanRowViaUi } from './closure-helpers'

await loginAdmin(page)
const { sopId } = await createSopViaUi(page, { sopName: `E2E SOP ${Date.now()}`, nodeName: '脚本' })
const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })
await startPlanRowViaUi(page, planName)
```

**反例（勿再提交）**

```typescript
// ❌ API 种子 — v2.6.44 起禁止
const seeded = await page.evaluate(async () => {
  const res = await fetch('/admin-api/ims/content/plan', { method: 'POST', … })
  return res.json()
})
```

共用辅助：`smoke-helpers.ts`（narrow smoke 登录）；**closure** 用 `closure-helpers.ts`。`E2E_BASE_URL` 由 `playwright.config.ts` 注入（默认 `http://127.0.0.1:6173`）；Vite `server.host`/`port` 与之一致；后端代理默认 `IMS_API=http://127.0.0.1:18080`（`vite.config.ts`）。S1/S2/S4–S8/S10 与 **FLOW** / **WORKBENCH** 补充 spec 额外断言 `.tbl-wrap table` 可见且无未捕获 `pageerror`（WORKBENCH 另断言 `flowTodoCount` 卡片 `.n` 为数字）。

## 运行（PO / Agent：默认一键，无需手敲多条 npm）

```powershell
cd ims-web
npm run test:e2e:ci
# 等价于:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_e2e.ps1
```

脚本行为：

1. 探测 **18080** `/health`、**6173** Vite；未起则后台启动 API（KillPort + `python -m app.main`）与 `npm run dev`（超时 120s / 90s）。
2. admin 登录 preflight；失败提示运行 `ims-backend\scripts\init_ims_db.ps1`。
3. `npx playwright test --reporter=list,html` → `playwright-report/index.html`。worker 默认 **2**，失败自动重试 **1** 次（`playwright.config.ts`）。`IMS_E2E_WORKERS=1` 退回单 worker，`IMS_E2E_RETRIES=0` 关掉重试。
4. 摘要写入 **`e2e_result.txt`**（末行 `N passed`）。

API **18080**、Vite **6173**、seed 已就绪时优先复用，避免冷启动：`.\scripts\run_e2e.ps1 -SkipServe`。全量失败时同一命令再跑 1 次，不改断言；仍失败再排查。开发中途只跑定向 pytest 与相关 closure，全量留到推 main 前。

仅 Playwright（无 preflight，跨平台 CI 子步骤）：`npm run test:e2e:ci:playwright-only`

手工调试：

```bash
cd ims-web
npm run test:e2e          # 等同 playwright test（默认 workers=2；IMS_E2E_WORKERS=1 可退回）
npm run test:e2e:skip     # SKIP_E2E=1 跳过
```

## W9 总验收（后端 pytest 仍为用户外置 cmd）

### 后端 · `run_pytest.cmd`

1. 确认无并行 pytest（脚本会检测并退出）。
2. 在 `ims-backend` 下执行：`scripts\run_pytest.cmd`
3. 流程：重置 `ims_test` / `ims_ops_test` → 全量 pytest → 结果写入 `pytest_result.txt`。
4. **collect-only 快照**（不跑用例）：  
   `set IMS_DB=ims_test&& set IMS_OPS_DB=ims_ops_test&& python -m pytest --collect-only -q`  
   W9-10 后预期 **124**（122 + `test_bi_subscribe` 内 2 条）。

### IMPLEMENTED / WIP 快照（W9-10 后）

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（`menu.ts` 侧栏/隐藏路由） | **78** |
| 仍 WIP（`/ims/wip/*` · catalog 非 navParent） | **18** |

**新 API 后**：重启 **18080** 后端以加载 `/bi/subscribe/*`、`/bi/report/preview/*`。
