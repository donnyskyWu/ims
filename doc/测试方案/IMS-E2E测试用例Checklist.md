# IMS E2E 测试用例 Checklist

> 版本 V1.0 ｜ 编制日期 2026-09-19 ｜ 依据：三期 PRD v1.2.0 业务流程 + UI 原型（19 个页面模块 + Tab/抽屉细分）+ 分期交付节奏
> 编号体系：E2E-{场景}-{两位序号}；工具：Playwright（复用 UI 原型路由）；执行环境：E2E 测试环境（真实钉钉测试企业 + GPU 节点）
> 12 条主线场景全部要求自动化；每条场景含「前置数据剧本 + 主流程 + 断言点 + 后置清理」
>
> **自动化分层（PO 签收口径 · v2.6.44）**
> - **Narrow smoke**（`ims-web/e2e/smoke-*.spec.ts`）：登录 + 单路由/Tab + 表格或 h1 — **仅健康检查**，不等于本节逐步用例签收。
> - **Acceptance E2E**（`closure-*.spec.ts` · 规划 `acceptance/*.spec.ts`）：按下方步骤表驱动，断言 **可见 UI 结果**（行文本、状态 tag、toast、链接）；Agent/CI 默认 **`ims-web/scripts/run_e2e.ps1`** 或 `npm run test:e2e:ci`；策略见 [`IMS-E2E验收策略.md`](./IMS-E2E验收策略.md)。
> - **纯 UI 门禁（closure · v2.6.44 起强制）**：closure 链 **禁止 API 造数**（不得 `page.evaluate` 内 `fetch('/admin-api/…')`、不得 Playwright 侧 TestClient 直调后端）。允许：**登录前** 的 env 无关操作（如读 `E2E_BASE_URL`）。**前置业务数据**须经 UI 菜单 → 表单/按钮创建（唯一名 `Date.now()`）；读取 UI 动作触发的网络响应体取 id/**单号**（`waitForResponse`）**允许**，不算 API 种子。共享辅助见 `ims-web/e2e/closure-helpers.ts` · 反例见 `ims-web/e2e/README.md`。
> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。S8 中检索相关用例已作废。
> **v2.6.35（2026-10-07）**：Playwright **S1–S12 narrow smoke**（12/12 PASS，`ims-web/e2e/smoke-*.spec.ts`）— 各场景仅「登录 + 单路由 h1/表格」；**smoke-OK ≠ 本节逐步 E2E 闭环**，全链路仍待预发/钉钉测试企业签收。  
> **补充（2026-10-07）**：FLOW 窄 smoke · `smoke-flow.spec.ts` → `/ims/flow`（非 S1–S12 编号）；WORKBENCH · `smoke-workbench.spec.ts` → `/ims/workbench`（`flowTodoCount` 卡片）；`npm run test:e2e` 合计 **14/14 PASS**。  
> **v2.6.36（2026-10-07 · #12 窄 E2E 扩展）**：`smoke-flow-timeout.spec.ts`（FLOW #19/#21 ·「超时督办」Tab · BR-115「月度超时率」+ 督办 table）；`smoke-alert-trial.spec.ts`（ALERT #20 · `/ims/alert/rule` · 可选「试跑」+ toast）；`npm run test:e2e` **16/16 PASS**（仍 **narrow**，非逐步闭环）。  
> **v2.6.37（2026-10-07 · #12 逐步闭环切片）**：新增 **3** 条多步 Playwright（**不替代** 16 narrow smoke）— `closure-flow-start-todo.spec.ts`（**E2E-FLOW-01** 发起→我的待办→APPROVE）、`closure-flow-timeout-urge.spec.ts`（**E2E-FLOW-02** 督办 urge→`remindCount+1` + #22 时长分布可见）、`closure-alert-rule-trial.spec.ts`（**E2E-S11-01** UI 创建启用规则→试跑→`hitCount+1`）；`npm run test:e2e` 预期 **19/19 PASS**。
> **v2.6.38（2026-10-07 · #23 perf 导出闭环）**：`closure-perf-issue-export.spec.ts`（**E2E-S9-切片** · API 种子至 CONFIRMED → UI「下发」→ 考核结果「导出 CSV」· UTF-8 BOM + `recordNo`/`ISSUED`）；`npm run test:e2e` 预期 **20/20 PASS**。
> **v2.6.39（2026-10-07 · #24 S7 发布督办闭环）**：`closure-content-publish.spec.ts`（**E2E-S7-切片** · `e2e_author` 立项/送审 → admin 审核通过 → 超计划发布单 → `/ims/content/publish` 督办 hint → UI「回填」→ 已归档/已回填）；`npm run test:e2e` 预期 **21/21 PASS**（`--workers=1`）。
> **v2.6.40（2026-10-07 · #25 E2E 一键自动化）**：`ims-web/scripts/run_e2e.ps1` · `npm run test:e2e:ci` · 产出 `e2e_result.txt` + `playwright-report/`；**E2E-FLOW-01** 增强实例表「进行中→已通过」可见断言；smoke 与 closure 分层见文首说明。  
> **v2.6.41（2026-10-07 · #27 L3 钉钉组织）**：**E2E-ORG-DING-01**（L3 层 · 非默认 21 spec）— `IMS_DINGTALK_L3=1` + PO `.env` → `run_dingtalk_l3.ps1` / `test_org_dingtalk_l3.py` + `dingtalk-org-l3.spec.ts`；组织 PRD 行 **已验收** 需 L3 PASS + UAT。
> **v2.6.42（2026-10-07 · #32 计划启动闭环）**：`closure-content-plan-start.spec.ts`（**E2E-S7-切片** · SOP+草稿计划 → `/ims/content/plan`「启动」→ `IN_PROGRESS` + 任务分页含 `planName`）；`npm run test:e2e:ci` 预期 **23/23 PASS**（+ L3 门开 **24** · `--workers=1`）。
> **v2.6.43（2026-10-08 · #33 任务执行闭环）**：`closure-content-task-execute.spec.ts`（**E2E-S7-切片** · 计划启动后 `/ims/content/task` → 执行页工作说明 → **DONE**）；`npm run test:e2e:ci` 预期 **24/24 PASS**（+ L3 门开 **25** · `--workers=1`）。
> **v2.6.44（2026-10-08 · #34 纯 UI closure 标准）**：PO 门禁 — 全部 `closure-*.spec.ts` **100% UI 点击造数**（移除 `page.evaluate`+`/admin-api` 种子）。本回合重构 **4** 条：`closure-content-plan-start` · `closure-content-task-execute` · `closure-content-publish`（+ 发布页「新建发布单」）· `closure-perf-issue-export`；**3** 条原已纯 UI（flow×2 · alert）。`npm run test:e2e:ci` 以 `e2e_result.txt` 为准。
> **v2.6.45（2026-10-08 · #35 工作任务 CONTENT_GENERATION 闭环）**：`closure-content-work-task.spec.ts`（**E2E-S7-切片** · UI 公推 SOP+IP 组/作者绑定（种子作者 id **900001**）→ 工作任务登记确认 → 我的任务 **CONTENT_GENERATION** 执行 → 内容编辑/提审 → `e2e_author` 审核通过 → admin 任务 **DONE**）；`npm run test:e2e:ci` 预期 **25/25 PASS**（+ L3 门开 **26** · `--workers=1`）。
> **v2.6.46（2026-10-08 · #36 计划终止闭环）**：`closure-content-plan-terminate.spec.ts`（**E2E-S7-切片** · 纯 UI 启动计划 → `/ims/content/plan`「申请终止」→ `TERMINATE_PENDING` → admin「批准终止」→ 计划 **TERMINATED** · 全部任务页关联任务 **TERMINATED**）；`npm run test:e2e:ci` 预期 **26/26 PASS**（+ L3 门开 **27** · `--workers=1`）。
> **v2.6.47（2026-10-08 · #37 工作任务 execution/矩阵 Tab）**：`closure-content-work-task-tabs.spec.ts`（**E2E-S7-切片** · 纯 UI 登记确认 →「任务执行情况」查询见节点/赛事 →「任务管理」矩阵 summary/表体）；Vite/E2E 默认 **6173**；`npm run test:e2e:ci` 预期 **27/27 PASS**（+ L3 门开 **28** · `--workers=1`）。
> **v2.6.48（2026-10-08 · #38 HOME 运营看板 KPI）**：`smoke-home.spec.ts`（补充 **HOME** 窄 smoke · 四 KPI + 快捷区）；`closure-home-dashboard.spec.ts`（**HOME 切片** · 纯 UI 刷新 · 账号 KPI 下钻 · 快捷入口）；`npm run test:e2e:ci` 预期 **29/29 PASS**（+ L3 门开 **30** · `--workers=1`）。
> **v2.6.49（2026-10-08 · #39 BI 订阅立即推送）**：`closure-bi-subscribe-push-now.spec.ts`（**E2E-S12-切片** · 纯 UI 新建报表+订阅 →「立即推送」→ 快照 GMV · 推送结果/上次推送可见）；`npm run test:e2e:ci` 预期 **30/30 PASS**（+ L3 门开 **31** · `--workers=1`）。
> **v2.6.50（2026-10-08 · #40 BI 分享审批）**：`closure-bi-share-approve.spec.ts`（**E2E-S12-05 切片** · 纯 UI 敏感分享 →「分享审批」Tab 通过/驳回 → 分享链接 Tab「已通过」/「已驳回」可见）；`npm run test:e2e:ci` 预期 **32/32 PASS**（+ L3 门开 **33** · `--workers=1`）。
> **v2.6.51（2026-10-08 · #41 BI 分享过期）**：`closure-bi-share-expired.spec.ts`（**E2E-S12-05 EXPIRED 切片** · 纯 UI 敏感分享审批通过 →「分享链接」Tab「标记过期」→「已过期」· 无「复制链接」）；`npm run test:e2e:ci` 预期 **33/33 PASS**（+ L3 门开 **34** · `--workers=1`）。
> **v2.6.52（2026-10-08 · #42 内容二级审核 Tab）**：`closure-content-review-stage2.spec.ts`（**E2E-S7 切片** · 纯 UI 提审 → 一级通过 →「二级审核」Tab 轮次 2 → 二级通过 → 空态）；后端 ADR-017 `content.review.level2.enabled` 一级 PASS 链式入队；`npm run test:e2e:ci` 预期 **35/35 PASS**（+ L3 门开 **36** · `--workers=1`）。
> **v2.6.53（2026-10-08 · #43 主数据 overview）**：`smoke-master.spec.ts` · `closure-master-overview.spec.ts`（**MASTER 切片** · `/ims/master` 六 KPI · 公司/平台账号 router-link 下钻）；`npm run test:e2e:ci` 预期 **36/36 PASS**（+ L3 门开 **37** · `--workers=1`）。
> **v2.6.63（2026-10-08 · #53 DC 场次下钻 + 明细导出）**：`closure-dc-session-drill.spec.ts`（**E2E-S12-01 场次下钻切片** · 纯 UI · 复用 **#52** 账号穿透 → 场次明细抽屉 GMV/净利润/投流成本 · 导出 `dc_trace_report.xlsx` 含场次号 · 页头 `queryCostMs` · 宽日期 **1181** 橙色提示）；`trace.vue` 抽屉/导出 · `dc_trace.py` `GET /dc/trace/detail/{sessionCode}` · `GET /dc/trace/export`；`npm run test:e2e:ci` 预期 **47/47 PASS**（+ L3 门开 **48** · `--workers=1`）。  
> **v2.6.69（2026-10-08 · #59 S3 期间结账 LOCKED + 锁后更正）**：`closure-fin-period-lock.spec.ts`（**E2E-S3-06/07** · 纯 UI · 独立 `yyyy-MM`「结账」→ **LOCKED** · 该月录入拦截 **1142**（归并原 1010）· 未批更正 **1155** · `FL-REIMB` 审批通过后红冲「投放成本」· 利润 **82,400.00** · 详情 **RECALCULATED**）；`GET /fin/period` · `POST /fin/period/close` · `cost.vue`；与 **#58** 合并后 `npm run test:e2e:ci` **53/53 PASS**（`e2e_result.txt` · API 18080 · Vite 6173 · `--workers=1`）。**#60**（E2E-S4-02/03）并行进行中，不是本片。  
> **v2.6.68（2026-10-08 · #58 S4 冲话费登记 + 凭证门禁）**：`closure-corp-account-recharge.spec.ts`（**E2E-S4-05/06** · 纯 UI · `AC-E2E-POOL`「冲话费」· **1000** 无凭证成功 · **6000** 无凭证 **1025** · 补凭证后成功 · admin「仅财务可见」· `e2e_acct_r3` 可见凭证号）；`POST/GET /account/recharge` · `account.vue`；**E2E-S4-02/03**（1021 / 流转）现为 **#60 进行中**（并行）；与 **#57** 合并后当时 `npm run test:e2e:ci` **52/52 PASS**（`e2e_result.txt` · API 18080 · Vite 6173 · `--workers=1`）。  
> **v2.6.67（2026-10-08 · #57 S3 分成 PAID_OFF + 台账对账）**：`closure-fin-share-payoff.spec.ts`（**E2E-S3-05/08 窄切片** · 纯 UI · 复用 **#50** 链 → `/ims/fin/share/result` 财务审+业务审 → **已发放** · 拆分合计 **4,000.00** = 总额 → `/ims/fin/ledger` **四账一致** · 成本 **16,600.00** · 净利润 **81,400.00**）；`fin.py` share results/audit/payoff · `share-result.vue` · `ledger.vue`（对账页复用既有 GET，无新 REST）；结账 LOCKED **未做**；`npm run test:e2e:ci` **51/51 PASS**（`e2e_result.txt` · API 18080 · Vite 6173 · `--workers=1`）。  
> **v2.6.66（2026-10-08 · #56 S2 直播登记→下播 narrow closure）**：`closure-live-session-report.spec.ts`（**E2E-S2 窄切片** · 纯 UI · 登记→风控→下播提交/核准 · `IMS…DYS…` 19 位 · 列表 `reportEntryStatus=CONFIRMED`）；`npm run test:e2e:ci` 预期 **50/50 PASS**（+ L3 门开 **51** · `--workers=1`）。  
> **v2.6.65（2026-10-08 · #55 S6 证件水印 closure）**：`closure-corp-cert-watermark.spec.ts`（**E2E-S6-03 切片** · 纯 UI · 搜 `E2E-Cert-Watermark` →「查看」→ 脱敏号 + admin 水印 · 无原图）；`cert_e2e_seed.py` · `resource.vue`；`npm run test:e2e:ci` 预期 **49/49 PASS**（+ L3 **50** · `--workers=1`）。  
> **v2.6.64（2026-10-08 · #54 FIN 成本更正→重算 closure）**：`closure-fin-cost-correction.spec.ts`（**E2E-S3-04** · 纯 UI · 复用 **#50** 链 → **CALCULATED 81400** → `/ims/fin/cost`「更正」投放 **6000** + 达人分成 **3500** → `/ims/fin/profit` **RECALCULATED** · **79900** · V≥2 → 利润反查抽屉达人 **3,500.00**）；`fin.py` correction/recalc · `cost.vue` testid · `submitFinCostCorrectionViaUi`；合并 **#53+#54** 后 `npm run test:e2e:ci` 预期 **48/48 PASS**（+ L3 门开 **49** · `--workers=1`）。  
> **v2.6.62（2026-10-08 · #52 DC-001 账号穿透 closure）**：`closure-dc-account-trace.spec.ts`（**E2E-S12-01 切片（账号入口）** · 纯 UI · 复用 **#50** LIVE 链 → `/ims/dc/trace` 搜 `AC-E2E-FIN` · 关系图 **ACCOUNT/PERSON/SESSION** · 明细表命中本场次 · `queryCostMs`/数据截至可见）；`trace.vue` testid · `dc_trace.py` **DETAIL** `detailList` DTO 修正 · `openDcAccountTraceViaUi`；`npm run test:e2e:ci` 预期 **46/46 PASS**（+ L3 门开 **47** · `--workers=1`）。  
> **v2.6.61（2026-10-08 · #51 DC-002 利润反查 closure）**：`closure-fin-profit-trace.spec.ts`（**E2E-S3-09 / TC-IMS-FIN-02-01** · 纯 UI · 复用 **#50** 链 → `/ims/fin/profit-trace` 列表 **81400** ·「反查」抽屉 **BR-209** · 账号 `AC-E2E-FIN` · 成本/分成明细可见）；`profit-trace.vue` testid · `closure-helpers` `openFinProfitTraceChainViaUi`；`npm run test:e2e:ci` 预期 **45/45 PASS**（+ L3 门开 **46** · `--workers=1`）。  
> **v2.6.60（2026-10-08 · #50 S3 FIN 成本→利润 closure）**：`closure-fin-cost-profit.spec.ts`（**E2E-S3-01/02/03 切片** · 纯 UI · LIVE「核准下播」→ `/ims/fin/cost` 提交/核准 → `/ims/fin/profit` **CALCULATED** · 净利润 **81400** · BR-107 完整率卡）；`live_fin_e2e_seed`（`AC-E2E-FIN`）· `live/index.vue` 核准下播 · `cost.vue` ProtoDrawer；`npm run test:e2e:ci` 预期 **44/44 PASS**（+ L3 门开 **45** · `--workers=1`）。  
> **v2.6.59（2026-10-08 · #49 TRAIN-003 完成率 Tab）**：`closure-train-stat-finish-rate.spec.ts`（**E2E-S10-02 延伸** · 纯 UI #48 链 → `/ims/train/stat`「完成率总览」· `GET /train/stat/finish-rate` · 任务 **100%**）；`stat.vue` · `smoke-train` stat 窄 smoke；`npm run test:e2e:ci` 预期 **43/43 PASS**（+ L3 门开 **44** · `--workers=1`）。  
> **v2.6.58（2026-10-08 · #48 S10 培训下发/完成）**：`closure-train-dispatch-complete.spec.ts`（**E2E-S10-01/02 切片** · 纯 UI 资料发布 → 下达任务 → 学习中心进度/确认 **CONFIRMED** → 学习记录可见）；`train.py` progress/confirm/records · `study.vue`；compat `20261008_train_task_record_progress.sql`；`npm run test:e2e:ci` 预期 **41/41 PASS**（+ L3 门开 **42** · `--workers=1`）。  
> **v2.6.57（2026-10-08 · #47 S4 账号池领用/归还）**：`closure-corp-account-checkout.spec.ts`（**E2E-S4-01/08 切片** · 纯 UI `AC-E2E-POOL` 申请→审批→交接→**在用**→归还→**已归还** · 时间线 APPLY/RETURN）；`acct_flow.py` · `acct_seed.py` · `corp/account.vue`；`run_e2e.ps1` 跑前 refresh 池种子；`npm run test:e2e:ci` 预期 **40/40 PASS**（+ L3 门开 **41** · `--workers=1`）。  
> **v2.6.56（2026-10-08 · #46 工作台待办/消息）**：`closure-workbench-todo-message.spec.ts`（`E2E-WB-MSG` 标已读 · `E2E-WB-CLOSE` 关闭 · 未读/待办预览计数）；`workbench/index.vue` 待办「关闭」；`workbench_seed.py`；`npm run test:e2e:ci` 预期 **39/39 PASS**（+ L3 门开 **40** · `--workers=1`）。  
> **v2.6.55（2026-10-08 · #45 BI BR-212 行级）**：`closure-bi-br212-row-scope.spec.ts`（admin vs `bi_r4_viewer` · 【BR212】报表 3/2 行 · 分享 Tab 1 行）；`bi_br212.py` + `dept_id`；`npm run test:e2e:ci` 预期 **38/38 PASS**（+ L3 门开 **39** · `--workers=1`）。  
> **v2.6.54（2026-10-08 · #44 预警处置 Tab）**：`closure-alert-handle-tab.spec.ts`（**E2E-S11-切片** · 纯 UI 试跑 → live「处理」→「处置记录」**HANDLED** + 汇总 ·「去重合并」**DEDUP-LIVE**）；`live.vue` 处置 toast。

## 主线场景总览

| # | 场景 | 覆盖 BR | 期次 | 优先级 | smoke（2026-10-07） |
|---|------|---------|------|--------|---------------------|
| S1 | 员工全生命周期（入职→在岗→离职闭环） | BR-001/002/015/023 | V1+V2.2 | P0 | smoke-OK · `smoke-auth-org.spec.ts` |
| S2 | 直播场次全链路（登记→风控→开播→下播→数据） | BR-011/014/007 | V1 | P0 | smoke-OK · **`closure-live-session-report.spec.ts`（#56 · E2E-S2 窄切片）** · `smoke-live.spec.ts` |
| S3 | 场次-成本-利润-分成全链路 | BR-107/108/118/209 | V3 先行 | P0 | smoke-OK · **`closure-fin-cost-profit.spec.ts`（#50）** · **`closure-fin-profit-trace.spec.ts`（#51 · DC-002）** · **`closure-fin-share-payoff.spec.ts`（#57 · E2E-S3-05/08）** · `smoke-fin.spec.ts` |
| S4 | 账号领用-流转-归还-冲话费 | BR-017/1024 | V1 | P0 | smoke-OK · **`closure-corp-account-checkout.spec.ts`（#47 · E2E-S4-01/08）** · **`closure-corp-account-recharge.spec.ts`（#58 · E2E-S4-05/06）** · `smoke-acct.spec.ts` |
| S5 | 资产采购-领用-归还-报废 + 穿透 | BR-003~005 | V1 | P1 | smoke-OK · `smoke-asset.spec.ts` |
| S6 | 证件录入-到期预警-水印访问 | BR-013 | V1 | P1 | smoke-OK · `smoke-cert.spec.ts` |
| S7 | 内容生产 AI 自动化全流程 | BR-016 | V1 | P1 | smoke-OK · `smoke-content.spec.ts` |
| S8 | AI 资产分发链路（技能→专家包→Key→MCP 调用） | BR-019~035 | V2.2 | P0 | smoke-OK · `smoke-air-skill.spec.ts` |
| S9 | 绩效考核周期（指标→计算→发布→员工查看） | BR-101~110 | V2 | P0 | smoke-OK · `smoke-perf.spec.ts` |
| S10 | 培训-考试-补考周期 | BR-104~106 | V2 | P1 | smoke-OK · **`closure-train-dispatch-complete.spec.ts`（#48）** · **`closure-train-stat-finish-rate.spec.ts`（#49）** · `smoke-train.spec.ts` |
| S11 | 预警规则配置-触发-处置闭环 | BR-111~113 | V2 | P1 | smoke-OK · `smoke-alert.spec.ts` |
| S12 | 数据消费闭环（穿透查询-自助报表-订阅分享） | BR-204/205/212 | V3 | P0 | smoke-OK · **`closure-dc-account-trace.spec.ts`（#52 · DC-001 账号入口）** · **`closure-dc-session-drill.spec.ts`（#53 · 场次下钻/导出）** · `smoke-bi-report.spec.ts` |

---

## S1 员工全生命周期（P0）

> smoke-OK（narrow）：组织架构同步列表页可加载；**未**覆盖钉钉事件/SSO/离职闭环逐步。

前置剧本：钉钉测试企业 + 空白部门 + 岗位模板「主播运营」。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-ORG-DING-01 | L3：`IMS_DINGTALK_L3=1` · OAuth gettoken + 组织页/API 冒烟 | **L3 PASS**（`run_dingtalk_l3.ps1`）；真云回调/5 分钟 SLA 仍属 **E2E-S1-01** 扩展 |
| E2E-S1-01 | 钉钉企业加入新员工（触发事件） | 5 分钟内 IMS 用户可见；岗位模板权限自动生效；工作台可见 |
| E2E-S1-02 | 员工登录钉钉→SSO 进 IMS | 免登成功；Token 2h（refresh 7d）；并发第 4 会话 1003 |
| E2E-S1-03 | 在岗操作（领账号/领资产/录证件） | 各台账责任人=该员工 |
| E2E-S1-04 | 钉钉调岗（换部门） | 旧部门数据不可见；新部门数据可见；权限 diff 正确 |
| E2E-S1-05 | 钉钉移除员工（离职事件） | 触发 S1 剩余闭环步骤 |
| E2E-S1-06 | 检查权限失效 | IMS 登录 403；在途单据全部进入待处理清单 |
| E2E-S1-07 | 账号归还闭环 | 归还单创建→审批→RETURNED；未闭环前关权限返回 1024 |
| E2E-S1-08 | 资产归还闭环 | 同上 ASSET 侧；时间线完整 |
| E2E-S1-09 | 证件回收 | CertStatus=RECYCLED；水印原图不可访问 |
| E2E-S1-10 | AIR Key 吊销（若 V2.2 已上线，回归时执行） | 离职后 MCP 调用 403；60s 缓存窗口内生效 |
| E2E-S1-11 | 终态检查 | 员工所有关联（账号/资产/证件/Key）状态终态正确；审计全量可查 |

## S2 直播场次全链路（P0）

> smoke-OK（narrow）：直播管理列表页可加载。  
> **闭环-OK（Playwright · v2.6.66 · #56 窄切片）**：`closure-live-session-report.spec.ts` — 登记 → 风控 → 下播提交/核准 · 19 位场次 ID · 列表 **CONFIRMED**；**未**覆盖 E2E-S2-03～05/07～09（黄红/开播/补录等）。

前置剧本：实名人（证件有效）+ 账号 IN_USE + 平台 DYS。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S2-01 | 登记开播（选账号/实名人/平台/时间） | 场次 ID 19 位、平台码 DYS、状态 PENDING_RISK_CHECK |
| E2E-S2-02 | 风控评分（构造绿色数据） | < 40 绿放行 APPROVED |
| E2E-S2-03 | 构造黄色（40~69） | 需审批放行；审批后 APPROVED |
| E2E-S2-04 | 构造红色（≥70 或实名人证件过期） | 禁止开播 1043/1045 |
| E2E-S2-05 | 开播→LIVE | 状态流转；直播中列表可见 |
| E2E-S2-06 | 下播→24h 内录数据 | 必填缺失拦截 1046；补齐提交成功 |
| E2E-S2-07 | 已提交数据修改 | 只读拦截 1047；走更正单流程 |
| E2E-S2-08 | 构造另一场次超 24h 未录 | 督办事件生成（工作台+预警） |
| E2E-S2-09 | 补录场景 | 缺说明拦截 1049；带说明+审批通过 |

## S3 场次-成本-利润-分成全链路（P0，V3 先行）

> smoke-OK（narrow）：利润页可加载。  
> **闭环-OK（Playwright · v2.6.69）**：**E2E-S3-切片** — `closure-fin-cost-profit.spec.ts`（#50 · **CALCULATED**）+ `closure-fin-profit-trace.spec.ts`（#51 · **DC-002**）+ `closure-fin-cost-correction.spec.ts`（#54 · **E2E-S3-04** · **RECALCULATED**）+ `closure-fin-share-payoff.spec.ts`（#57 · **E2E-S3-05/08** · **PAID_OFF** · 四账一致）+ `closure-fin-period-lock.spec.ts`（#59 · **E2E-S3-06/07** · **LOCKED** · **1142** · R4 后红冲）。

前置剧本：S2 完成的场次 + 分成规则（多级比例合计 100%）。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S3-01 | 成本录入（DRAFT→SUBMITTED） | 场次 ID 自动关联；金额校验 |
| E2E-S3-02 | 成本核准（CONFIRMED） | 5 分钟内利润自动计算完成 |
| E2E-S3-03 | 利润查看 | ProfitCalcStatus=CALCULATED；收入−成本数值正确（人工复算一致） |
| E2E-S3-09 | 利润反查（DC-002） | `/ims/fin/profit-trace` 列表命中；反查抽屉 chain·成本/分成明细；queryCostMs 可见（**#51 closure**） |
| E2E-S3-04 | 成本更正→重算 | RECALCULATED；分成单同步更新（**#54 closure** · 反查抽屉 shareAmount） |
| E2E-S3-05 | 分成单审批→PAID_OFF | ShareResultStatus 流转；金额拆分累计=总额（**#57 closure** · 待审→已审→已发放 · 4,000=总额） |
| E2E-S3-06 | 期间结账 | LOCKED；结账后录入拦截 **1142**（归并原 1010）（**#59 closure** · 期间条 **LOCKED** · 录入错误「财务期间已结账」） |
| E2E-S3-07 | 结账后更正 | R4 审批流（FLOW 嵌入）；审批过才可更正（**#59 closure** · 未批 **1155** · 通过后红冲「投放成本」· 利润详情 **RECALCULATED**） |
| E2E-S3-08 | 台账对账页 | 场次×成本×利润×分成四账一致（**#57 closure** · `/ims/fin/ledger` **四账一致**） |

## S4 账号领用-流转-归还-冲话费（P0）

> smoke-OK（narrow）：抖音账号池列表页可加载。  
> **闭环-OK（Playwright · v2.6.68）**：**E2E-S4-切片** — `closure-corp-account-checkout.spec.ts`（**#47** · 池内 `AC-E2E-POOL` · 领用→审批→交接→**IN_USE** · 归还→**RETURNED** · 时间线）+ `closure-corp-account-recharge.spec.ts`（**#58** · **E2E-S4-05/06** · ≤5000 无凭证成功 · >5000 无凭证 **1025** · 补凭证后仅财务可见 URL）；**未**覆盖 E2E-S4-02/03/04/07。**E2E-S4-02/03**（1021 他人领用 / 账号流转）为 **#60 进行中**（并行分支，非 #59）。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S4-01 | 从账号池领用 | 状态 IN_USE；责任人写入 |
| E2E-S4-02 | 他人领用同账号 | 1021 拦截 |
| E2E-S4-03 | 流转给他人 | 审批流；责任人变更；时间线追加 |
| E2E-S4-04 | 收回冻结 | FROZEN；领用/流转被 1022 拦截 |
| E2E-S4-05 | 冲话费（< 5000 无凭证） | 提交成功（**#58 closure** · 列表 **1000.00**） |
| E2E-S4-06 | 冲话费（> 5000 无凭证） | 1025 拦截；补凭证通过；仅财务角色可见（**#58 closure** · admin「仅财务可见」· `e2e_acct_r3` 见凭证号） |
| E2E-S4-07 | 账实核对（构造 1.99%/2.00% 差异） | 1026 边界行为 |
| E2E-S4-08 | 归还 | RETURNED；时间线完整闭环 |

## S5 资产全生命周期 + 穿透（P1）

> smoke-OK（narrow）：办公设备列表页可加载；**未**覆盖采购/穿透逐步。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S5-01 | 采购入台账→批量导入 | 行级错误定位；部分成功 |
| E2E-S5-02 | 领用→使用→归还→报废 | AssetStatus 全流转 |
| E2E-S5-03 | 正向穿透（实名人→资产 5 层内） | 链路返回；> 5 层 1013 |
| E2E-S5-04 | 反向穿透（资产→使用人，三态） | 在用/已归还/已报废区分 |

## S6 证件录入-预警-水印（P1）

> smoke-OK（narrow）：证件管理列表页可加载。  
> **闭环-OK（Playwright · v2.6.65 · #55 切片）**：`closure-corp-cert-watermark.spec.ts` — **E2E-S6-03** 查看水印 + 脱敏号；**未**覆盖 E2E-S6-01/02/04（录入/到期预警/频次拦截）。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S6-01 | 录入证件→审核生效 | CertStatus 流转；重复录入 1032 |
| E2E-S6-02 | 构造 T−30/T−7/T−0 到期 | 黄/红/锁定三级预警+工作台提醒 |
| E2E-S6-03 | 查看证件（有权限角色） | 水印图（人名+尾号+时间戳）；原图接口 1034 |
| E2E-S6-04 | 1 小时 11 次访问 | 第 11 次 1035 拦截 |

## S7 内容生产 AI 自动化全流程（P1）

> smoke-OK（narrow）：内容管理列表页可加载；**未**覆盖 ComfyUI/GPU 逐步。  
> **闭环-OK（Playwright · v2.6.53）**：**E2E-S7-切片** — `closure-content-publish.spec.ts`（发布督办 pending→回填→已归档 · **双审**）；`closure-content-review-stage2.spec.ts`（**#42** · 二级审核 Tab）；`closure-content-plan-start.spec.ts`（草稿计划 UI「启动」→ `IN_PROGRESS` + 任务含 `planName`）；`closure-content-plan-terminate.spec.ts`（**#36** · 申请终止 → 批准 → 计划/任务 **TERMINATED**）；`closure-content-task-execute.spec.ts`（计划轨 · 我的任务 → 执行页 → **DONE**）；`closure-content-work-task.spec.ts`（**#35** · 工作任务登记 → CONTENT_GENERATION → **双审** → **DONE**）；`closure-content-work-task-tabs.spec.ts`（**#37** · 工作任务 execution/矩阵 Tab）；**MASTER** · `closure-master-overview.spec.ts`（**#43**）；**未**覆盖 E2E-S7-01～06 全量逐步。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S7-01 | 选择 SOP+内容要求立项 | TOP-R1 校验 |
| E2E-S7-02 | 脚本定稿→提交 AI 生产 | AiJobStatus=WAITING→GENERATING |
| E2E-S7-03 | ComfyUI 产出（真实 GPU） | PENDING_FINAL_REVIEW；产物 服务端文件目录归档 |
| E2E-S7-04 | 人工终审通过→发布 | PUBLISHED；未通过→REVIEW_REJECTED 不可发布 1054 |
| E2E-S7-05 | 审核人=提交人 | 1057 回避拦截 |
| E2E-S7-06 | 构造 60 分钟超时 | 1056 失败态+重新发起 |

## S8 AI 资产分发链路（P0，V2.2）

> smoke-OK（narrow）：技能库列表页可加载；**未**覆盖 Key/MCP/限额逐步。

前置剧本：技能+知识（各密级）+ 知识库文档已入库（文件管理期，不做向量化）。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S8-01 | 创建技能→审核→发布 | SkillStatus 流转；网关 skills.list 可见 |
| ~~E2E-S8-02~~ **已作废** | ~~上传知识→密级 CONFIDENTIAL→审核→入库向量化~~ | ~~KB 文档检索可命中~~（语义检索已移除） |
| E2E-S8-03 | 组装专家包（技能+知识+提示词） | experts.assemble 产物结构正确 |
| E2E-S8-04 | 授权（DEPT/ROLE/PERSON 三类） | 未授权者调用 403 |
| E2E-S8-05 | 生成 API Key（air- 前缀） | 仅展示一次明文；库内哈希 |
| ~~E2E-S8-06~~ **已作废** | ~~外部 MCP 客户端调用 knowledge.search~~ | ~~命中内容；密级过滤（CONFIDENTIAL 对无授权 Key 不可见）~~（语义检索已移除） |
| ~~E2E-S8-07~~ **已作废** | ~~TOP_SECRET 知识检索~~ | ~~输出被完全过滤（拦截 100%）~~（语义检索已移除） |
| E2E-S8-08 | 连续调用 61 次/分钟 | 第 61 次 429+告警 |
| E2E-S8-09 | Key 调整限额后生效 | QPM 新值生效 |
| E2E-S8-10 | 停用技能 | 网关即时不可见 |
| E2E-S8-11 | 查看审计报表 | 全量调用日志（工具/耗时/Token/过滤命中） |

## S9 绩效考核周期（P0，V2）

> smoke-OK（narrow）：执行考核列表页可加载；**未**覆盖计算/发布/锁定逐步。  
> **闭环-OK（Playwright · v2.6.38）**：**E2E-S9-切片** — `closure-perf-issue-export.spec.ts`（CONFIRMED 种子 → UI 下发 ISSUED → 结果页导出 CSV · BOM 表头）；**未**覆盖 E2E-S9-01~08 全量逐步。

前置剧本：指标集（含人工补充项）+ 培训/日报/上报数据就绪。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S9-01 | 配置指标集（权重合计 100） | 99/101 时 1154 拦截 |
| E2E-S9-02 | 尝试启用 COMPETE_SUBMIT_RATE | 1153 拦截（V2 禁用） |
| E2E-S9-03 | 发起月度计算 | CALCULATING→PENDING_APPROVE；多源数据取数正确 |
| E2E-S9-04 | 人工补充指标值（缺原因） | 1158 拦截；补原因通过 |
| E2E-S9-05 | 审批发布 | PUBLISHED |
| E2E-S9-06 | 员工查看结果 | 已发布可见；发布前 1157 |
| E2E-S9-07 | 锁定周期后更正 | 1155 拦截→R4 审批链路 |
| E2E-S9-08 | 绩效等级分布 | S~D 分档边界（85/60）正确 |

## S10 培训-考试-补考周期（P1）

> smoke-OK（narrow）：学习任务列表页可加载；**未**覆盖考试/补考逐步。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S10-01 | 创建资料→下发任务 | 学习记录生成 · **切片-OK（#48）** 见 `closure-train-dispatch-complete.spec.ts` |
| E2E-S10-02 | 完成学习 | TrainStatus=COMPLETED；完成率统计正确 · **切片-OK（#48）** 学习中心 **CONFIRMED** + 学习记录抽屉 · **完成率看板-OK（#49）** `closure-train-stat-finish-rate.spec.ts` |
| E2E-S10-03 | 组卷（随机策略超额） | 1160 拦截；Σ分≠总分 1159 |
| E2E-S10-04 | 考试窗口外进入 | 1161 |
| E2E-S10-05 | 答题→交卷→评分 | ExamStatus 流转；他人答卷 1163；重复交卷 1164 |
| E2E-S10-06 | 不及格补考 | MAKEUP_EXAM；成绩覆盖规则 |

## S11 预警配置-触发-处置闭环（P1）

> smoke-OK（narrow）：预警规则列表页可加载（`smoke-alert.spec.ts`）；**+窄 E2E** `smoke-alert-trial.spec.ts`（#20 · 启用规则「试跑」→ toast「试跑成功」· 无启用规则时仅列表断言）；**未**覆盖钉钉触发/处置逐步。  
> **闭环-OK（Playwright · v2.6.37）**：**E2E-S11-01** 主路径切片 — `closure-alert-rule-trial.spec.ts`（新建规则+启用→试跑→toast+`hitCount+1`）；**未**覆盖非法 DSL 1009 / 重复编码 1165。  
> **闭环-OK（Playwright · v2.6.54 · #44）**：**E2E-S11-处置切片** — `closure-alert-handle-tab.spec.ts`（试跑 OPEN → live「处理」→ 处置记录 **HANDLED** · 去重策略表）；**未**覆盖 E2E-S11-04 全状态链 / 1166 / 1167。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S11-01 | 配置规则（合法 DSL） | 保存成功；非法 DSL 1009；重复编码 1165 · **闭环-OK（Playwright）** 合法创建+试跑见 `closure-alert-rule-trial.spec.ts` |
| E2E-S11-02 | 构造触发数据 | 事件生成→推送目标人（钉钉通道） |
| E2E-S11-03 | 非目标人尝试响应 | 1166 |
| E2E-S11-04 | 目标人确认→解决 | OPEN→CONFIRMED→RESOLVED · **切片-OK（#44）** live「处理」→ **HANDLED** 见 `closure-alert-handle-tab.spec.ts` |
| E2E-S11-05 | 误报关闭 | FALSE_ALARM 终态；重复响应 1167 |
| E2E-S11-06 | 统计页 | 响应时长/解决率正确 |

## 补充 · FLOW 超时督办（非 S 编号 · P1）

> smoke-OK（narrow · #12）：`smoke-flow-timeout.spec.ts` — 登录 → `/ims/flow` →「超时督办」Tab → 指标行含「月度超时率」/超时节点统计（`GET /flow/timeout/rate`）+ 督办 table 表头或「暂无超时待办」；**未**覆盖 urge 钉钉/全链路 FLOW。  
> **闭环-OK（Playwright · v2.6.37）**：**E2E-FLOW-01** `closure-flow-start-todo.spec.ts`（发起实例→我的待办可见→APPROVE）；**E2E-FLOW-02** `closure-flow-timeout-urge.spec.ts`（督办 urge→`remindCount+1` · `GET /flow/timeout/distribution` 时长分布）；**未**覆盖钉钉真实推送 / 多节点流转。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-FLOW-01 | 发起→我的待办→审批通过 | 实例 RUNNING→APPROVED；待办消失 · **闭环-OK** `closure-flow-start-todo.spec.ts` |
| E2E-FLOW-02 | 超时督办 urge | `remindCount+1`；分布 API/UI 可见 · **闭环-OK** `closure-flow-timeout-urge.spec.ts` |

## S12 数据消费闭环（P0，V3）

> smoke-OK（narrow）：报表中心页可加载；**未**覆盖穿透/订阅定时推送/分享行级权限逐步。  
> **closure 切片（#39）**：`closure-bi-subscribe-push-now.spec.ts` — UI 订阅「立即推送」→ 快照 + 推送结果/上次推送可见（本地钉钉 Webhook **桩** · 非 E2E-S12-04 定时触达）。  
> **closure 切片（#40）**：`closure-bi-share-approve.spec.ts` — UI 敏感分享 →「分享审批」Tab 通过/驳回 → 分享链接 Tab 状态可见。  
> **closure 切片（#41）**：`closure-bi-share-expired.spec.ts` — UI 已通过分享 →「标记过期」→「已过期」。  
> **closure 切片（#45 · v2.6.55）**：`closure-bi-br212-row-scope.spec.ts` — admin vs `bi_r4_viewer` 可见【BR212】报表/分享行集不同（**非** 下钻/query 全链路 BR-212）。  
> **closure 切片（#52 · v2.6.62）**：`closure-dc-account-trace.spec.ts` — 纯 UI **账号入口**穿透（**非** 六入口全量 · **非** P95 预发）。

前置剧本：10 万行级压测数据集 + S3 已完成的场次数据。

| 编号 | 步骤 | 断言点 |
|------|------|--------|
| E2E-S12-push-now | 订阅页新建 ACTIVE 订阅 →「立即推送」 | 快照区 GMV · 行「钉钉成功」· 上次推送时间更新 · **闭环-OK** `closure-bi-subscribe-push-now.spec.ts` |
| E2E-S12-01 | 六入口穿透查询（各一） | 链路互达完整；P95 < 3s（预发执行）；**账号入口切片-OK** `closure-dc-account-trace.spec.ts`（#52 · `AC-E2E-FIN`）；**场次下钻+导出切片-OK** `closure-dc-session-drill.spec.ts`（#53 · 明细抽屉 · XLSX · `queryCostMs`/1181） |
| E2E-S12-02 | 自助报表拖拽→下钻 | DrillDimension 六维逐一下钻成功 |
| E2E-S12-03 | 大数据集查询 | < 30s；> 10s 自动转异步（通知领取） |
| E2E-S12-04 | 看板订阅 DAILY | 定时推送触达 |
| E2E-S12-05 | 分享审批流 | PENDING→APPROVED/REJECTED · **切片-OK** `closure-bi-share-approve.spec.ts`（#40）；EXPIRED · **切片-OK** `closure-bi-share-expired.spec.ts`（#41）；行级权限 BR-212 · **切片-OK** `closure-bi-br212-row-scope.spec.ts`（#45 · 报表列表+分享 Tab） |

---

## 执行与回归策略

| 阶段 | 执行场景 | 说明 |
|------|----------|------|
| V1 提测（第 12~14 周） | S1(01~09)/S2/S4/S5/S6/S7 | AIR 相关步骤跳过（S1-10） |
| V2 提测（第 24~27 周） | S9/S10/S11 + V1 场景全量回归 | — |
| AIR-P0 验收（第 19~20 周） | S8(01~07) | P1 项（限额/白名单）后续补 |
| AIR-P1 验收（第 23~24 周前后） | S8(08~11) + S8 全量回归 | — |
| FIN 先行验收（第 33 周） | S3 全量 + S1 回归 | 人工财务复算 ≥ 3 组 |
| V3 全量（第 40~42 周） | S12 + 全部场景回归 | 预发性能联动 |

> 全部场景断言点同时校验 UI 层（页面路由/抽屉交互参照 UI 原型 19 个页面模块（Tab/抽屉细分））与接口层（响应 code/数据落库）；失败截图+网络日志自动归档至缺陷单。
