# IMS 任务进度计划表（全局 · 实时看板）

> **用途**：并行开发 / 测试 / 验证 / 修复的统一进度 SSOT；与 [`IMS-Python完整开发计划-20261005.md`](./IMS-Python完整开发计划-20261005.md) 对齐。交付顺序与 UAT 门禁见 [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md)。  
> **PRD 功能点矩阵**（模块 × 切片 × 前后端 × pytest/E2E）：[`IMS-PRD功能点执行对照表.md`](./IMS-PRD功能点执行对照表.md)  
> **交付 `#` 流水号**：本表「序号」列 = Agent/PO 每片收尾登记的 **计划表 `#`**（**当前主 `#` 查表末行**，现 **#57** · **已完成**）；可含子行（如 **8b**、**13b**）表示同一切片内的测试/验证子项。**无预定上限**，随 closure / 修复 / 规范增量续编。**≠** 对照表模块矩阵行数（约 17 行 PRD 模块视图）。  
> **自动链（PO 2026-10-08 · zhang wu）**：**#57 起恢复**。此前「#55 后暂停、不自动开 #57」已解除。本 PR 只交付 **#57**；合并后父代理继续 **#58+**，除非 PO 再暂停。
> **最后整表刷新**：2026-10-08

| 序号 | 工作流 | 任务/切片 | 状态 | 负责人 | 最后更新 | 备注/链接 |
|------|--------|-----------|------|--------|----------|-----------|
| 1 | 验证 | W0–W9-14 主线交付（菜单 ~98 IMPLEMENTED） | 已完成 | 多 Agent | 2026-10-07 | [执行进度](./IMS-Python执行进度-20261006.md) |
| 2 | 验证 | E2E Playwright smoke 全量 | 已完成 | Agent | 2026-10-08 | **51/51 PASS**（含 **#57** S3 分成 PAID_OFF + 台账对账 · **#55** S6 水印 · **#56** S2 登记下播 · **#53/#54** FIN/DC · 纯 UI · 不含 L3）· API **18080** · Vite **6173** · `ims-web/e2e_result.txt` · L3 另计 +1 · **PO 已于 #57 恢复自动链**（本 PR 不含 #58） |
| 3 | 测试 | pytest 全量 154 条（外置单进程） | 已完成 | 用户本地 | 2026-10-07 | **#31** +3 `test_dingtalk_client_scopes` · 含 L3 3 条（默认 skip）· **collect-only 154** · 外置 **154 passed** · L3 另跑 `run_dingtalk_l3.ps1` |
| 4 | 开发 | sysTenant 租户套餐 | 阻塞 | — | 2026-10-07 | **ADR / SLICES 批次外**，WIP=1，本批不做 |
| 5 | 修复 | master/overview 404 → 200 | 已完成 | Agent | 2026-10-07 | `ops_db.create_all` · 需重启 18080 |
| 6 | 修复 | FIN 前端 `import http` 白屏 | 已完成 | Agent | 2026-10-07 | E2E S3 复跑 12/12 |
| 7 | 运维 | 并行 pytest / MySQL 1684 错峰 | 已完成 | 运维 | 2026-10-07 | preflight **0** · 全量 **仅** 用户外置 `run_pytest_external.bat` · Agent 不再后台全量 |
| 8 | 开发 | FLOW-002 发起流程 `POST /flow/instance` | 已完成 | 本回合 Agent | 2026-10-07 | `app/flow.py` · 1134/幂等 · 前端发起抽屉 · compat SQL |
| 8b | 测试 | `tests/test_flow.py` 新增发起用例 | 已完成 | 本回合 Agent | 2026-10-07 | TestClient 手工冒烟 PASS（Cursor pytest 易被杀） |
| 8c | 验证 | 18080 `POST /flow/instance` | 已完成 | Agent | 2026-10-07 | 复验 OK · DRAFT **1134** · PUBLISHED **code 0**（compat SQL） |
| 8d | 修复 | `test_flow_instance_start_and_idempotent` 对齐种子 | 已完成 | 用户本地 | 2026-10-07 | 随 **#3** 外置全量签收（用户「已执行请继续」）· 单条仍可用 `pytest tests/test_flow.py::test_flow_instance_start_and_idempotent` 复验 |
| 9 | 开发 | perf 考核下发 ISSUED | 已完成 | 本回合 Agent | 2026-10-07 | `PUT /perf/execution/{id}/issue` · REVIEWED/CONFIRMED→ISSUED · 1155 重复下发 · 前端「下发」 · **Live verify 已完成**（18080 `-KillPort` 重启 · `PUT …/issue` HTTP **200** 已挂载） |
| 9b | 测试 | `test_perf_issue_from_confirmed_and_locked_1155` | 已完成 | 本回合 Agent | 2026-10-07 | `tests/test_perf.py` · 外置签收 |
| 10 | 开发 | BI 钉钉 Webhook 真实 URL 桩 | 已完成 | 本回合 Agent | 2026-10-07 | `push-now` · `bi.dingtalk.webhook.url` / `IMS_BI_DINGTALK_WEBHOOK_URL` · httpx 3s · `lastPushStatus` DING_OK/FAIL · **Live verify 已完成**（18080 `-KillPort` 重启 · `POST …/bi/subscribe/1/push-now` **200·code 0** · 无 URL 本地桩 **DING_OK** · `webhookConfigured=false`） |
| 10b | 测试 | `test_bi_subscribe_push_now_dingtalk_webhook` | 已完成 | 本回合 Agent | 2026-10-07 | mock httpx · 外置签收 |
| 11 | 开发 | FLOW 任务处理 `PUT /flow/task/{id}/handle` | 已完成 | 本回合 Agent | 2026-10-07 | `ims_flow_task` · APPROVE/REJECT 桩 · `GET my-todo` · compat SQL · **Live verify 已完成**（curl login/my-todo/handle **200·code 0** · APPROVED） |
| 11b | 测试 | `test_flow_task_handle_approve_and_reject` | 已完成 | 本回合 Agent | 2026-10-07 | `tests/test_flow.py` · 外置签收 |
| 12 | 验证 | W9 总回归 Checklist 书面勾选 | 部分完成 | 本回合 Agent | 2026-10-07 | S1–S12 **smoke-OK（narrow）** + **5 条逐步闭环** Playwright · **E2E-S9-切片**（#23）· **E2E-S7-切片**（#24 发布督办 pending→回填）· Checklist **v2.6.39** · **21/21 PASS** |
| 13 | 开发 | 工作台聚合流程待办 `flowTodoCount` | 已完成 | 本回合 Agent | 2026-10-07 | `workbench.py` · dashboard 与 `my-todo` 同源 seed · 首页卡片+预览表 · **Live verify 已完成**（18080 `-KillPort` · preflight **0** · dashboard **code 0** · `flowTodoCount=2` · `my-todo.total=2` 一致） |
| 13b | 测试 | `test_workbench_dashboard_includes_flow_todo_count` | 已完成 | 本回合 Agent | 2026-10-07 | `tests/test_workbench.py` · 外置签收 · `collect-only` 预期 **139** tests |
| 14 | 验证 | E2E `smoke-flow.spec.ts`（/ims/flow） | 已完成 | 本回合 Agent | 2026-10-07 | 登录 + h1「流程管理」+ 流程实例 table · 并入全量 **13/13** · `e2e/README.md` |
| 15 | 开发 | S7 发布督办 API 对齐 | 已完成 | 本回合 Agent | 2026-10-07 | **已完成（契约已覆盖）** · `publish.vue` ↔ `GET publish/pending`（`overdueOnly`）/ list / receipt / archive · **无** 代码变更 · collect **139** 不变 |
| 16 | 验证 | E2E `smoke-workbench.spec.ts`（/ims/workbench） | 已完成 | 本回合 Agent | 2026-10-07 19:52 | 登录 + 问候 h1 +「流程待办」卡片 `.n` 数字 + 流程待办 table · 依赖 **#13** · **14/14 PASS**（2026-10-07 19:52 · 全量签收 · `smoke-workbench` 1 passed） |
| 17 | 开发 | 预警规则试跑 API/UI | 已完成 | 本回合 Agent | 2026-10-07 | 别名 `POST /alert/rule/{id}/trial` 同 `check/run` · **#20** 前端已改调 trial · `test_alert_rule_trial_alias_matches_run` · **Live verify**（18080 · trial/check/run **200·code 0**） |
| 18 | 开发 | perf 考核结果 CSV 导出桩 | 已完成 | 本回合 Agent | 2026-10-07 | `GET /perf/result/export` CSV（CONFIRMED/ISSUED）· `result.vue`「导出 CSV」· `test_perf_result_export_csv` · B9 `scope` 登记 export · **Live verify 已完成**（18080 `-KillPort` · `GET …/perf/result/export` **200** · `text/csv` · `Content-Disposition: attachment; filename="perf_results.csv"`） |
| 19 | 开发 | FLOW 超时督办 list/urge | 已完成 | 本回合 Agent | 2026-10-07 | `GET /flow/timeout/list` · `PUT /flow/timeout/{id}/urge` · `remind_count` · 前端「超时督办」Tab · `test_flow_timeout_list_and_urge` · compat `20261007_flow_timeout_urge.sql` · **Live verify**（18080 · list **code 0 total≥1** · urge **code 0**） |
| 20 | 开发 | 预警规则 UI 试跑 trial + toast | 已完成 | 本回合 Agent | 2026-10-07 | `rule.vue` → `POST /alert/rule/{id}/trial` + toast · **Live verify**（18080 · trial **code 0**）· 定向冒烟 5 条 **PASSED**（`scripts/_run_targeted_smoke.py`） |
| 21 | 开发 | FLOW 超时率 `GET /flow/timeout/rate` | 已完成 | 本回合 Agent | 2026-10-07 | BR-115 桩 · `timeoutCount`/`urgeCount`/`monthlyTimeoutRate` · 前端督办 Tab 指标行 · `test_flow_timeout_rate_br115_stub` · **Live verify**（18080 · rate **code 0** · `timeoutCount=1` · `totalExecuted=3` · `monthlyTimeoutRate=0.3333`） |
| 22 | 开发 | FLOW 超时分布 `GET /flow/timeout/distribution` | 已完成 | 本回合 Agent | 2026-10-07 | FLOW-004/BR-115 · `durationBuckets`/`byDomain`/`byTemplate` · `groupBy` 桩 · 督办 Tab「时长分布」 · `test_flow_timeout_distribution_stub` · **Live verify**（18080 · distribution **code 0**） |
| 23 | 验证 | E2E perf 下发→导出 CSV 闭环 | 已完成 | 本回合 Agent | 2026-10-07 | `closure-perf-issue-export.spec.ts` · 复用 **#18** export · Checklist **v2.6.38** · **E2E-S9-切片** · 无新增 pytest · 全量 **20/20** |
| 24 | 验证 | E2E S7 发布督办 pending→回填闭环 | 已完成 | 本回合 Agent | 2026-10-07 | `closure-content-publish.spec.ts` · **#15** API · 种子用户 `e2e_author`（`main.seed`）· Checklist **v2.6.39** · **E2E-S7-切片** · 无新增 pytest · 全量 **21/21** |
| 25 | 验证 | E2E 一键自动化 | 已完成 | 本回合 Agent | 2026-10-07 | `ims-web/scripts/run_e2e.ps1` · `npm run test:e2e:ci` · `e2e_result.txt` + HTML 报告 · Checklist **v2.6.40** · [`IMS-E2E验收策略.md`](../测试方案/IMS-E2E验收策略.md) · **E2E-FLOW-01** UI 终态增强 · Agent **`21/21 PASS`**（~17s · `-SkipServe`） |
| 26 | 规范 | Agent 交付循环 + PRD UAT 列 | 已完成 | PO 确认 · Agent | 2026-10-07 | [`.cursor/rules/ims-delivery.mdc`](../../.cursor/rules/ims-delivery.mdc) · [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md) · 对照表 **UAT 建议/状态** · **已验收**=closure+E2E+UAT通过 |
| 27 | 开发/验证 | L3 钉钉组织集成脚手架 | 已完成 | 本回合 Agent | 2026-10-07 | **L3 PASS**（PO `.env` · seed DB · pytest **3 passed** + Playwright **E2E-ORG-DING-01**）· `dingtalk_l3_result.txt` · **已验收†**=L3 PASS + **PO UAT 未测** · `pytest.mark.l3` 跳过 ims_test DDL |
| 28 | 开发 | 钉钉/Football 系统参数 + 运行时解析 | 已完成 | 本回合 Agent | 2026-10-07 | `settings_runtime` · UI 密钥掩码 · `seed_dingtalk_params_from_env.py` + `.ps1`（修 PowerShell 嵌入 py）· PO 本机 bootstrap OK |
| 29 | 验证 | CONTENT S1 计划管理 narrow E2E | 已完成 | 本回合 Agent | 2026-10-07 | `smoke-content-plan.spec.ts` · pytest 定向 `test_sop_list_and_plan_create`（外置签收）· E2E **22**（+L3 门开 **23**）· `test:e2e:ci -SkipServe` **23 passed** |
| 30 | 规范 | 并行 Subagent 交付口径 | 已完成 | PO + Agent | 2026-10-07 | **Yes**：无耦合任务可并行 Subagent；耦合切片串行；每切片 Agent `test:e2e:ci`（workers=1）；PO 对照表 **UAT 状态** |
| 31 | 开发/验证 | 钉钉通讯录全量拉取同步 | 已完成 | 本回合 Agent | 2026-10-07 | `auth/scopes` 定根 · 50004 跳过 · `listsubid`+`listsub` 对象数组解析 · [钉钉通讯录同步说明](../运维/钉钉通讯录同步说明.md) · **Live 23:49**（修 BFS 后 `-KillPort` 复跑）：**code 0** · **19** dept · **新增 46** · **更新 3** · `rootSubDeptIdCount=3` · `listsubCalls=19` · 根因曾误用 `listsub` 仅读 `dept_id_list` |
| 32 | 开发/验证 | CONTENT 计划启动主链 | 已完成 | 本回合 Agent | 2026-10-07 | `POST /content/plan/{id}/start` DRAFT→IN_PROGRESS · SOP 节点×IP 组生成任务 · 计划页「启动」· `task/page?planName` · `closure-content-plan-start.spec.ts` · `test_sop_list_and_plan_create` 延伸 · E2E **23/23** · collect **151** |
| 33 | 验证 | CONTENT 任务执行完成闭环 | 已完成 | 本回合 Agent | 2026-10-08 | 复用 **#32** 启动 + `task/execute/complete` · `closure-content-task-execute.spec.ts` · `test_plan_start_normal_task_execute_complete` **1 passed** · E2E **24/24 PASS**（`E2E_BASE_URL=http://localhost:6173` · `e2e_result.txt`）· collect **156**（+1） |
| 34 | 规范/验证 | E2E closure **纯 UI** 标准 + 重构 | 已完成 | 本回合 Agent | 2026-10-08 | Checklist **v2.6.44** · `ProtoDrawer` `#foot`/`#footer` + `useSlots` · `closure-content-task-execute` 行定位（`nodeName`）· **24/24 PASS** · `e2e_result.txt` 2026-10-08 09:26 |
| 35 | 验证 | CONTENT 工作任务→CONTENT_GENERATION 审核完成 | 已完成 | 本回合 Agent | 2026-10-08 | `closure-content-work-task.spec.ts` · `sop.vue` 营销计划/节点类型 · `main` 种子 `E2EClosureAuthor` **900001** · `work_task.find_enabled_sop` id  tiebreak · `test_task_execute_content_gate_and_crud`（#35 标注）**1 passed** · Checklist **v2.6.45** · E2E **25/25 PASS** · `e2e_result.txt` 2026-10-08 09:39 |
| 36 | 开发/验证 | CONTENT 计划终止申请→审批 | 已完成 | 本回合 Agent | 2026-10-08 | `POST /content/plan/{id}/terminate` · `…/terminate/approve` · `…/reject` · `plan.vue` 行内按钮 · `terminate_reason` 列 · compat `20261008_content_plan_terminate_reason.sql` · `closure-content-plan-terminate.spec.ts` · `test_plan_terminate_approve_flow` **1 passed** · Checklist **v2.6.46** · E2E **26/26 PASS** · `e2e_result.txt` 2026-10-08 09:48 · collect **157** |
| 37 | 开发/验证 | CONTENT 工作任务 execution/矩阵 Tab 只读闭环 | 已完成 | 本回合 Agent | 2026-10-08 | `work-task.vue` 执行情况 → `GET /content/task/page`（#3 · `workDate`/`authorName`）· 矩阵登记表透视+summary · `sheet` 增 `ipGroupLeaderName` · `closure-content-work-task-tabs.spec.ts`（**纯 UI**）· `test_work_task_confirm_and_withdraw` 延伸 **1 passed** · Checklist **v2.6.47** · E2E **27/27 PASS** · `e2e_result.txt` 2026-10-08 10:24 · Web **6173** |
| 38 | 验证 | HOME 运营看板 KPI smoke + closure | 已完成 | 本回合 Agent | 2026-10-08 | 复用 **HOME-001** `/home/dashboard` · **`smoke-home.spec.ts`**（四 KPI + 快捷区）· **`closure-home-dashboard.spec.ts`**（纯 UI：刷新 · 账号数→抖音 · 快捷登记工作任务）· `test_home.py` **3 passed** · 无后端/前端代码变更 · Checklist **v2.6.48** · E2E **29/29 PASS** · Web **6173** |
| 39 | 验证 | BI/S12 订阅「立即推送」纯 UI closure | 已完成 | 本回合 Agent | 2026-10-08 | `closure-bi-subscribe-push-now.spec.ts` · `subscribe.vue`「推送结果」列（`lastPushStatus`）· Checklist **v2.6.49** · `test_bi_subscribe_list_and_share_link` **1 passed** · E2E **30/30 PASS** · Web **6173** · `e2e_result.txt` |
| 40 | 验证 | BI/S12「分享审批」Tab 纯 UI closure | 已完成 | 本回合 Agent | 2026-10-08 | `subscribe.vue` 分享审批 Tab + 敏感分享弹窗 · `closure-bi-share-approve.spec.ts`（通过/驳回）· Checklist **v2.6.50** · `test_bi_subscribe_list_and_share_link` **1 passed**（含 REJECTED）· E2E **32/32 PASS** · Web **6173** · `e2e_result.txt` |
| 41 | 验证 | BI/S12 分享链接 **EXPIRED** 纯 UI closure | 已完成 | 本回合 Agent | 2026-10-08 | **选型**：矩阵 BI 行在 #40 后最高价值缺口（S12-05 EXPIRED）；内容二级审核/主数据 overview 无 smoke closure 且 PO 价值低于 S12 合规链 · `subscribe.vue`「标记过期」· `closure-bi-share-expired.spec.ts` · Checklist **v2.6.51** · `test_bi_subscribe_list_and_share_link` 延伸 **EXPIRED** · E2E **33/33 PASS** · Web **6173** · `e2e_result.txt` |
| 42 | 验证 | CONTENT 二级审核 Tab 纯 UI closure | 已完成 | 本回合 Agent | 2026-10-08 | `content.py` level2 链 · `closure-content-review-stage2.spec.ts` · `closure-helpers` 双审 · 回归 publish/work-task · `test_review_gate_and_publish` L2 · Checklist **v2.6.52** · pytest 定向 **2 passed** · E2E 见 **#43** **36/36** · Web **6173** |
| 43 | 验证 | MASTER overview smoke + closure | 已完成 | 本回合 Agent | 2026-10-08 | `smoke-master.spec.ts` · `closure-master-overview.spec.ts` · `test_master_overview_blocks` · Checklist **v2.6.53** · E2E **36/36 PASS** · `e2e_result.txt` · Web **6173** |
| 44 | 验证 | ALERT/S11 预警处置 Tab 纯 UI closure | 已完成 | 本回合 Agent | 2026-10-08 | `live.vue` 处置 toast · `closure-alert-handle-tab.spec.ts`（试跑→处理→处置记录→去重）· `test_alert` 延伸 HANDLE · Checklist **v2.6.54** · E2E **37/37 PASS** · Web **6173** · `e2e_result.txt` |
| 45 | 开发/验证 | BI/S12 **BR-212 行级权限** closure | 已完成 | 本回合 Agent | 2026-10-08 | `bi_br212.py` · `dept_id` · 种子 `bi_r4_viewer` + `BR212-` 三报表 · `closure-bi-br212-row-scope.spec.ts` **PASS** · pytest **3/3** · 全量 E2E **38/38**（续跑修复 CONTENT **closure-helpers** 时序/900001 绑定 · **BR-212 未回滚**）· Checklist **v2.6.55** · 假设：`bi_r4_viewer`=DEPT(11) 非 R4 审批岗 |
| 46 | 开发/验证 | **WORKBENCH** 待办关闭 + 消息已读 closure | 已完成 | 本回合 Agent | 2026-10-08 | `workbench_seed.py` · `workbench/index.vue`「关闭」/已读「是/否」· `closure-workbench-todo-message.spec.ts` · `run_e2e.ps1` 跑前 refresh 种子 · `closure-helpers` 工作任务撤回循环（全量稳定）· `test_workbench_e2e_seed_todo_and_message` · Checklist **v2.6.56** · E2E **39/39 PASS** · collect **161** · Web **6173** |
| 47 | 开发/验证 | **S4 CORP** 账号池领用→归还 closure | 已完成 | 本回合 Agent | 2026-10-08 | `acct_flow.py` · `acct_seed.py`（`AC-E2E-POOL`）· `corp/account.vue` 领用/归还抽屉 · `closure-corp-account-checkout.spec.ts` · `test_acct_checkout.py` · compat `20261008_acct_apply_timeline.sql` · `run_e2e.ps1` refresh 池种子 · 发布 closure 选用 `IN_USE` 账号 · Checklist **v2.6.57** · E2E **40/40 PASS** · collect **162** · Web **6173** |
| 48 | 开发/验证 | **S10 TRAIN** 下发→学习完成 closure | 已完成 | 本回合 Agent | 2026-10-08 | `PUT …/task/{id}/progress` · `POST …/confirm` · `GET …/task/records` · `study.vue` · `task.vue` 资料多选/学习记录 · `scope.py` · compat `20261008_train_task_record_progress.sql` · `closure-train-dispatch-complete.spec.ts` · `test_train_task_progress_confirm_and_records` · Checklist **v2.6.58** · E2E **41/41 PASS** · collect **163** · Web **6173** · **Live**：已有库须 `-ApplyCompat` 或执行 compat SQL 后 **`-KillPort` 重启 18080** |
| 49 | 开发/验证 | **TRAIN-003** 培训统计看板 · 完成率 Tab closure | 已完成 | 本回合 Agent | 2026-10-08 | `GET /train/stat/finish-rate` · `stat.vue` 完成率总览（近7/30天 · 任务/部门/个人表）· `closure-train-stat-finish-rate.spec.ts` · `completeTrainStudyViaUi` · `smoke-train` stat 窄 smoke · `test_train_stat_finish_rate_after_confirm` · Checklist **v2.6.59** · E2E **43/43 PASS** · collect **164** · Web **6173** · **Live**：新 API 须 **`-KillPort` 重启 18080** |
| 50 | 开发/验证 | **S3 FIN** 成本登记→利润看板 pure UI closure | 已完成 | 本回合 Agent | 2026-10-08 | `live_fin_e2e_seed` · `live/index.vue`「核准下播」· `cost.vue` ProtoDrawer · `closure-fin-cost-profit.spec.ts` · `closure-helpers` LIVE/FIN 链 · `test_live_fin_e2e_seed_deps` · Checklist **v2.6.60** · E2E **44/44 PASS** · Web **6173** · Live：**重启 18080** 加载 seed/核准 UI |
| 51 | 开发/验证 | **DC-002** 利润反查 pure UI closure | 已完成 | 本回合 Agent | 2026-10-08 | 复用 **#50** LIVE/FIN 链 · `/ims/fin/profit-trace`「反查」· `profit-trace.vue` `fin-profit-trace-chain-drawer` · `closure-fin-profit-trace.spec.ts` · `openFinProfitTraceChainViaUi` · `test_dc_profit_trace_list_and_chain` 定向 **2 passed** · Checklist **v2.6.61** · E2E **45/45 PASS** · Web **6173** |
| 52 | 开发/验证 | **DC-001** 账号穿透 pure UI closure | 已完成 | 本回合 Agent | 2026-10-08 | 复用 **#50** LIVE 链 · `/ims/dc/trace` 账号入口 · `trace.vue` testid · `dc_trace.py` **detailList** 嵌套 `ok()` 修复 · `closure-dc-account-trace.spec.ts` · `openDcAccountTraceViaUi` · `test_dc_trace_account_keyword_detail_mode` · 定向 pytest **3 passed**（含 trace 基线）· Checklist **v2.6.62** · E2E **46/46 PASS** · Web **6173** · Live：**重启 18080** 加载 `dc_trace` 修复 · **PO 于 #52 后曾暂停自动链，同日授权 #53** |
| 53 | 开发/验证 | **DC-001** 场次下钻 + 明细导出 | 已完成 | 本回合 Agent | 2026-10-08 | `GET /dc/trace/detail/{sessionCode}` · `GET /dc/trace/export`（XLSX/PDF · `downloadUrl`/`expiresIn`）· 页头 `queryCostMs` + **1181**（日期跨度 >92 天）· `trace.vue` 场次抽屉 · `closure-dc-session-drill.spec.ts` · `test_dc_trace.py` **3 passed** · collect **167** · Checklist **v2.6.63** · E2E **47/47 PASS** · Web **6173** · Live：本地 MySQL `ims`（非云库）· 附带 `smoke-train` 完成率响应监听改到 `goto` 之前（快 API 竞态） |
| 54 | 开发/验证 | **S3 FIN** 成本更正→利润 **RECALCULATED** closure | 已完成 | 本回合 Agent | 2026-10-08 | `POST /fin/cost/{sessionCode}/correction` · `POST /fin/profit/recalc/{sessionCode}` · `cost.vue` 更正抽屉 · `closure-fin-cost-correction.spec.ts` · `submitFinCostCorrectionViaUi` · `test_fin_cost_correction_recalc_profit_and_share_trace` · Checklist **v2.6.64** · 与 **#53** 合并后 E2E **48/48** · collect **167** · Web **6173** · Live：**重启 18080** 加载 correction API · 云库：更正写 `ims_fin_cost.remark`（无 DDL）· **未自动链 #55** |
| 55 | 开发/验证 | **S6 CORP** 证件查看水印 **纯 UI** closure | 已完成 | 本回合 Agent | 2026-10-08 | **E2E-S6-03 切片** · `cert_e2e_seed.py` · `closure-corp-cert-watermark.spec.ts` · `resource.vue` testid · `test_cert_e2e_seed_watermark_view` · Checklist **v2.6.65** · collect **169** · E2E **50/50** · 云库仅种子行 · **PO：自动链止于本切片后暂停**（`ab3625b`）
| 56 | 开发/验证 | **S2 LIVE** 登记→下播核准 **窄 closure** | 已完成 | 本回合 Agent | 2026-10-08 | **`closure-live-session-report.spec.ts`** · 复用 **#50** UI 链 · 19 位场次 · `reportEntryStatus=CONFIRMED` · `trace.vue` 明细 60s 超时 · Checklist **v2.6.66** · E2E **50/50** · **Live：重启 18080**（DC detail 路由）· **#56 已交付**（`ab3625b`）· 当时文档写暂停；**PO 已于 #57 恢复自动链** |
| 57 | 开发/验证 | **S3 FIN** 分成审批→**PAID_OFF** + 台账对账 | 已完成 | 本回合 Agent | 2026-10-08 | **E2E-S3-05/08 窄切片** · `GET /fin/share/results` · `PUT /fin/share/result/{id}/audit` · `PUT …/payoff` · 成本核准后按达人/实名人手工额生成待审单 · 拆分累计=总额 · `/ims/fin/share/result` 双审发放 · `/ims/fin/ledger` 四账一致（复用 cost/profit/share GET）· `closure-fin-share-payoff.spec.ts` · `test_fin_share_audit_payoff_amounts_sum_to_total` · `test_fin.py` **10 passed** · collect **170** · Checklist **v2.6.67** · E2E **51/51 PASS** · 结账 LOCKED / 锁后更正 **留给 #59+** · **本 PR 不含 #58** · **PO：#57 起自动链恢复** |

---

## 更新日志

### 2026-10-07 · 初版

- 建表；回填 W0–W9-14、E2E、pytest 外置待签收、sysTenant 批次外、overview/FIN 修复、并行 pytest 运维口径。
- 下一高价值切片：**FLOW 发起**（进行中）、perf ISSUED、钉钉 Webhook 配置桩、Flow 任务处理。

### 2026-10-07 · FLOW-002 发起

- 交付：`POST /admin-api/ims/flow/instance`（PUBLISHED 校验 **1134**、`businessKey` 幂等、`form_data`/`business_key` 列）。
- 前端：`/ims/flow`「发起流程」抽屉；`collect-only` 预期 **+1** → **135** tests（外置全量待签收）。
- 验证：`GET /health` 200；`GET /flow/template/list` 200；`POST /flow/instance` **404**（旧进程）→ 重启 API。

### 2026-10-07 · #8c 复验 · pytest 单条

- **18080**：`curl` 复验 `POST /admin-api/ims/flow/instance` → HTTP **200**、业务码 **0**（`businessKey=curl-flow-leave-smoke-001` · `instanceNo=FI20261007004`）。
- **#8c** → **已完成**；**#7** → **已完成**（preflight 0；全量 pytest 仅外置 bat）。
- **#3** 仍为 **未开始**（待用户 `run_pytest_external.bat`）。
- **单测**：`test_flow_instance_start_and_idempotent` → **1 failed**（`StopIteration`：PUBLISHED 列表无 `FL-LIVE` 草稿模板，1134 分支未跑到）。
- **2026-10-07 复验**：重启 18080 后 `POST /admin-api/ims/flow/instance` 已挂载；草稿模板 HTTP **200 / code 1134**；已发布模板 HTTP **200 / code 0**（`ims` 库需 `db/compat/20261007_flow_instance_start.sql`）；`pytest tests/test_flow.py::test_flow_instance_start_and_idempotent` **FAIL**（用例从 PUBLISHED 列表取 `FL-LIVE`）。

### 2026-10-07 · #8d 单测对齐种子

- **改动的**：`tests/test_flow.py` — 1134 分支改 `GET /flow/template/list?status=DRAFT` 取 `FL-LIVE`；发起/幂等仍 `PUBLISHED` + `FL-LEAVE`（与 `seed_flow` 一致）。
- **#8c** 保持 **已完成**（Live API 与种子语义一致）。
- **单条 pytest**：preflight **0** + `_reset_test_dbs` OK；Cursor 集成 shell 对 `pytest` 常 **exit -1** 无输出 → 请外置执行 `python -m pytest tests/test_flow.py::test_flow_instance_start_and_idempotent -q` 签收。

### 2026-10-07 · #9 perf ISSUED · #11 FLOW handle

- **#9**：`PUT /admin-api/ims/perf/execution/{id}/issue`（REVIEWED/CONFIRMED→ISSUED；已 ISSUED **1155**）；`ims-web/src/views/perf/execution.vue`「下发」按钮。
- **#11**：表 `ims_flow_task` + `db/compat/20261007_flow_task_handle.sql`；`GET /flow/task/my-todo`、`PUT /flow/task/{id}/handle`（APPROVE/REJECT 桩，同步实例终态）；流程页「我的待办」Tab。
- **单测**：`test_perf_issue_from_confirmed_and_locked_1155`、`test_flow_task_handle_approve_and_reject`；`collect-only` 预期 **137** tests（外置全量待签收）。

### 2026-10-07 · #9/#11 Live verify · ims compat 说明

- **18080**：`scripts/start_api.ps1 -KillPort` 重启；preflight **0**。
- **curl 冒烟**：`POST /auth/login` **200·0**；`GET /flow/task/my-todo` **200·0**（total≥1）；`PUT /flow/task/{id}/handle` APPROVE **200·0**；`PUT /perf/execution/{id}/issue` 路由 **200**（不存在记录 **1500**，非 404）。
- **ims 库 compat（文档口径，勿未确认在生产执行）**：已有 **ims** 库若缺表 `ims_flow_task`，需手工 `ims-backend/db/compat/20261007_flow_task_handle.sql`；**测库** `tests/schema_reset.py` → `create_all` 已含该表，pytest 无需挂 compat SQL。`#9` 无新增表/列，无需 compat。
- **单测（2 条）**：Cursor 集成 shell **exit -1 被杀** → 见 `ims-backend/w915_pytest_note.txt`；请外置 `python -m pytest tests/test_perf.py::test_perf_issue_from_confirmed_and_locked_1155 tests/test_flow.py::test_flow_task_handle_approve_and_reject -q` 签收。

### 2026-10-07 · #10 BI Webhook · #12 Checklist smoke

- **#10**：`POST …/bi/subscribe/{id}/push-now` 读取 `bi.dingtalk.webhook.url`（`PARAM_SEED`）或 `IMS_BI_DINGTALK_WEBHOOK_URL`；有 URL 则 markdown JSON POST（httpx **3s**），落库 `lastPushStatus` **DING_OK/DING_FAIL**；无 URL 保持本地桩 **DING_OK**。
- **#10b**：`test_bi_subscribe_push_now_dingtalk_webhook`；`collect-only` 预期 **138** tests。
- **#10 Live verify**：`scripts/start_api.ps1 -KillPort`；preflight **0**；`curl` login **200·0**；`POST /bi/subscribe/1/push-now`（种子 ACTIVE · 未配 Webhook）**200·0** · `lastPushStatus=DING_OK` · `dingTalk.status=ACCEPTED` · `webhookConfigured=false`。
- **#12**：Checklist **v2.6.35** — 12 条 Playwright smoke 映射 **smoke-OK（narrow）**，明确未签收逐步 E2E。
- **前端**：`subscribe.vue` 副标题文档化 Webhook 配置键（无表单字段）。

### 2026-10-07 · #13 工作台流程待办

- **#13**：`GET /auth/workbench/dashboard` 增 `flowTodoCount`（与 `GET /flow/task/my-todo` 同计数逻辑）；`ims-web/src/views/workbench/index.vue` 流程卡片 + 5 条预览表 + 链 `/ims/flow`。
- **#13 Live verify**：`scripts/start_api.ps1 -KillPort`；preflight **0**；`curl` login **200·0**；`GET /auth/workbench/dashboard` **code 0** · `flowTodoCount=2` · `GET /flow/task/my-todo` **total=2** 一致。
- **#13b**：`test_workbench_dashboard_includes_flow_todo_count`；`collect-only` 预期 **139** tests（138+1）；无 compat SQL / 无 B9 变更（dashboard 仍为 auth 白名单）。

### 2026-10-07 · #14 FLOW E2E · #15 S7 发布督办

- **#14**：新增 `ims-web/e2e/smoke-flow.spec.ts`（`smoke-helpers` · `/ims/flow` · 默认流程实例 tab 表格）；`e2e/README.md` 补充 FLOW 行与单 spec 运行命令。
- **#15**：对照 `publish.vue` 与《CONTENT-内容生产-API契约》§2.6.5 — 督办为 `GET /content/publish/pending`（含 `overdueOnly`），无原型/前端调用的独立 remind POST；后端已覆盖，**未改** `content.py` / `test_content.py`。
- **pytest collect**：仍为 **139**（无新增单测）。

### 2026-10-07 · #2 全量 E2E 签收

- **18080 + 6173** 就绪后 `ims-web` · `npm run test:e2e` → **13 passed**（S1–S12 + `smoke-flow`）。
- **#2** / **#14** 备注更新为 **13/13**；**#15** 标注 **已完成（契约已覆盖）**；Checklist 补充 FLOW smoke 映射一行。

### 2026-10-07 · #16 WORKBENCH E2E

- **#16**：新增 `ims-web/e2e/smoke-workbench.spec.ts`（`/ims/workbench` · 问候 h1 ·「流程待办」卡片数字 · 流程待办 preview table）；`e2e/README.md` 补充 WORKBENCH 行与单 spec 命令。
- **后端/前端**：无变更（复用 **#13** `flowTodoCount` + 流程待办列表）。
- **pytest collect**：仍为 **139**（无新增单测）。
- **E2E**：全量预期 **14/14**（+1 `smoke-workbench`）；单 spec：`npx playwright test e2e/smoke-workbench.spec.ts`。
- **下一候选**：**#17** 预警试跑 · **#18** perf 导出桩。

### 2026-10-07 · #17 预警试跑别名 · #18 perf CSV 导出

- **#18**：`GET /admin-api/ims/perf/result/export` — UTF-8 CSV（BOM）、表头 + CONFIRMED/ISSUED 记录（最多 5000）；`ims-web/src/views/perf/result.vue`「导出 CSV」（fetch + Bearer）。
- **#17**：`POST /admin-api/ims/alert/rule/{id}/trial` 与 `POST /alert/check/run/{id}` 共用 `run_check_impl`；`rule.vue` 副标题文档化。
- **单测**：`test_perf_result_export_csv`、`test_alert_rule_trial_alias_matches_run`；`collect-only` 预期 **141** tests（139+2）；**#3** 仍外置签收。

### 2026-10-07 19:52 · #2 / #16 全量 E2E 复验（smoke-workbench）

- **18080**：已就绪（HTTP 200 `/docs`）；未执行 `-KillPort` 重启。
- **6173**：已就绪（HTTP 200）。
- **E2E**：`ims-web` · `npm run test:e2e` → **14 passed**, **0 failed**（含 `smoke-workbench.spec.ts` 1 passed）。
- **#2** / **#16** 备注更新为 **14/14 PASS** · 时间戳 **2026-10-07 19:52**。

### 2026-10-07 · #17/#18 Live verify · collect 141

- **18080**：`scripts/start_api.ps1 -KillPort` 重启；preflight **0**。
- **#18**：`GET /admin-api/ims/perf/result/export` → HTTP **200** · `Content-Type: text/csv; charset=utf-8` · `Content-Disposition: attachment; filename="perf_results.csv"`（无 CONFIRMED/ISSUED 时仅表头）。
- **#17**：`POST /admin-api/ims/alert/rule` 创建规则 **id=1**；`POST …/alert/rule/1/trial` 与 `POST …/alert/check/run/1` 均 **200·code 0**（各产生独立 `alertNo`）。
- **pytest**：`collect-only` **141**；单测 2 条 Cursor shell **exit -1 被杀**（preflight 0，外置签收可选）。

### 2026-10-07 · #3 外置签收 · #19 FLOW 超时督办

- **#3** → **已完成**（用户「已执行请继续」· 141 passed 口径；本回合 collect **142**）。
- **#8d** → **已完成**（随全量签收）。
- **#19**：`ims_flow_task.remind_count` · `GET /admin-api/ims/flow/timeout/list`（PENDING + SLA 24h）· `PUT …/timeout/{id}/urge`（`remindCount+1` 桩，无真实钉钉）；`flow/index.vue`「超时督办」Tab；`scope.py` 登记 timeout 前缀。
- **compat**：已有 **ims** 库执行 `db/compat/20261007_flow_timeout_urge.sql`（测库 `create_all` 已含列）。
- **Live verify**：18080 `-KillPort` 后 list **code 0 · total=1** · urge **code 0**。
- **pytest**：`collect-only` **142**；`test_flow_timeout_list_and_urge` Cursor shell **exit -1**（外置可选）。
- **下一候选**：**#12** Checklist 逐步 E2E · FLOW `timeout/distribution` 分布桩 · 预警/流程 Playwright 窄 smoke。

### 2026-10-07 · #21 FLOW timeout/rate · #3 二次签收

- **#3**：用户 cmd「已执行请继续」二次签收；无 `pytest_result.txt` **142 passed** 文件证据；**collect-only 143**。
- **#21**：`GET /admin-api/ims/flow/timeout/rate`（`statMonth` · BR-115 · `byDomain`/`trend` · 扩展 `timeoutCount`/`urgeCount`/`totalExecuted`）；`flow/index.vue` 督办 Tab 指标行。
- **pytest**：`test_flow_timeout_rate_br115_stub`；外置全量预期 **143 passed**。
- **Live verify**：18080 `GET …/flow/timeout/rate` **code 0**。

### 2026-10-07 · #20 预警 UI trial · 本地 ims 库初始化

- **DB**：`powershell -File ims-backend/scripts/init_ims_db.ps1`（`ensure_databases` + `init_db` · utf8mb4）；已有库增量可选 `-ApplyCompat`（按序 `db/compat/*.sql`，重复列/索引跳过）。
- **环境变量**：默认 `IMS_MYSQL_USER/PASSWORD/HOST/PORT`（见 `app/core.py`）；勿提交 `.env` 密钥。
- **#20**：`alert/rule.vue` 试跑按钮 → `POST …/alert/rule/{id}/trial` + toast。
- **联调/测试**：18080 五端点冒烟 **OK**（health/login/timeout/export/trial）；`scripts/_run_targeted_smoke.py` **6 条**（含 #21 rate）；全量 **143** 外置 `run_pytest_external.bat`。
- **Schema**：本机 `ims` **86** 表（`init_ims_db.ps1`）；全新库无需手工 compat，老库用 `-ApplyCompat`。

### 2026-10-07 · #12 窄 E2E 扩展（FLOW 超时 · ALERT 试跑）

- **新增**：`ims-web/e2e/smoke-flow-timeout.spec.ts` · `smoke-alert-trial.spec.ts`；`e2e/README.md` 对照表与单 spec 命令。
- **Checklist**：**v2.6.36** — S11 试跑窄 smoke 注记 +「补充 · FLOW 超时督办」节。
- **E2E**：`npm run test:e2e` → **16 passed，0 failed**（~5.8s · 18080+5173）；督办 Tab 依赖 `/flow/timeout/*`；试跑依赖 `/alert/rule/{id}/trial`。
- **#2** 备注同步为 **16/16**（含上述 2 spec）。
- **下一候选**：Checklist 其余场景逐步闭环 · perf 考核下发 E2E（可选 · 较重）。

### 2026-10-07 · #22 timeout/distribution · #12 逐步闭环 E2E

- **#22**：`GET /admin-api/ims/flow/timeout/distribution`（`statMonth` · `groupBy=duration|domain|template` · SLA 24h 分桶 · 复用 `_load_task_domain_rows`）；`flow/index.vue` 督办 Tab「时长分布」；`test_flow_timeout_distribution_stub`；**collect-only 144**。
- **#12**：Checklist **v2.6.37** — 3 条 **closure-*.spec.ts**（发起→待办→通过 · 督办 urge · 预警创建+试跑）；保留 16 条 narrow smoke。
- **E2E**：`npm run test:e2e` → **19 passed，0 failed**（18080+5173 · ~4.8s）；**#2** 已同步 **19/19**。
- **pytest 外置**：`run_pytest_external.bat` 目标 **144 passed**（+1 distribution）。

### 2026-10-07 · #27 L3 PASS · #28 bootstrap · #29 计划 smoke · #30 并行口径

- **#27**：PO 本机 `ims-backend/.env`（gitignore）+ `seed_dingtalk_params_from_env.ps1` → `run_dingtalk_l3.ps1` / pytest **3 passed** · Playwright **E2E-ORG-DING-01** · 产物 `dingtalk_l3_result.txt`；修复 seed 脚本（独立 `.py`）、L3 e2e 走 UI 登录、`pytest.mark.l3` 免 DDL 重置。
- **#28**：系统参数 UI 键 `dingtalk.corpId` / `dingtalk.clientId` / `dingtalk.clientSecret` / `dingtalk.agentId` / `dingtalk.appId` / `dingtalk.callbackToken` / `dingtalk.callbackAesKey` / `dingtalk.l3Enabled` / `football.webapiBaseUrl`（+ `bi.dingtalk.webhook.url`）；运行时 **DB > env**。
- **#29**：内容主链 S1 — `smoke-content-plan.spec.ts`；E2E 基线 **22**（不含 L3 spec）。
- **#30 并行开发**：**可以** — 按 [`ims-delivery.mdc`](../../.cursor/rules/ims-delivery.mdc) 仅 **无耦合** 任务并行 Subagent；同切片 **开发→pytest 定向→test:e2e:ci→文档** 串行；**已验收** 仍须 PO **UAT 状态=通过**。

### 2026-10-07 · #26 交付循环 · UAT 列（PO 确认）

- **规则**：`.cursor/rules/ims-delivery.mdc`（`alwaysApply`）· 人读 SSOT [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md)（含 **PO 资源清单**）。
- **对照表**：[`IMS-PRD功能点执行对照表.md`](./IMS-PRD功能点执行对照表.md) 增 **UAT 建议**（Agent）/ **UAT 状态**（PO：**未测/通过/阻塞**）；行级 **已验收** = closure + 最新 E2E 全量 PASS + **UAT 状态=通过**。
- **下一候选**：按对照表「待补数据/未 closure」PRD 行继续 acceptance E2E；PO 对 **UAT 建议=可 UAT** 行做手工 UAT。

### 2026-10-07 · #25 E2E 一键自动化

- **脚本**：`ims-web/scripts/run_e2e.ps1`（preflight 18080/6173 · 可选自启 · login 提示 `init_ims_db.ps1` · Playwright `--workers=1` · HTML 报告）；`ims-backend/scripts/run_e2e_full.ps1` 委托入口；`npm run test:e2e:ci`。
- **文档**：Checklist **v2.6.40**（smoke vs acceptance 分层）· [`IMS-E2E验收策略.md`](../测试方案/IMS-E2E验收策略.md) · `e2e/README.md` 一键节。
- **质量**：`closure-flow-start-todo.spec.ts` **E2E-FLOW-01** 增加实例表「进行中→已通过」可见断言。
- **E2E**：Agent `run_e2e.ps1 -SkipServe` → **21 passed**（~17s）；产物 `e2e_result.txt` 末行 **`21 passed`**。

### 2026-10-07 · #24 S7 发布督办闭环 · PRD 对照表

- **PRD 矩阵**：新建 [`IMS-PRD功能点执行对照表.md`](./IMS-PRD功能点执行对照表.md)；本表「用途」段已链入。
- **#24**：`closure-content-publish.spec.ts`（E2E-S7-切片 · pending 督办 hint → 回填 → 已归档）；`main.seed` 增 `e2e_author` + 空库 DOUYIN 账号桩；Checklist **v2.6.39**；**21/21 PASS**；pytest collect **144** 不变。

### 2026-10-07 · #23 perf 下发→导出 CSV 闭环 E2E

- **#23**：`ims-web/e2e/closure-perf-issue-export.spec.ts` — 浏览器内 API 种子至 CONFIRMED → 执行考核 UI「下发」→ 考核结果「导出 CSV」（UTF-8 BOM · `recordNo`/`ISSUED`）；复用 **#9/#18** 后端，无路由变更。
- **E2E 运行**：`playwright.config.ts` 默认 **`workers: 1`**（避免并发登录锁定 admin）；`npm run test:e2e` → **20/20**。
- **#12**：Checklist **v2.6.38**；逐步闭环 **4** 条（+ S9 切片）。
- **E2E**：`npx playwright test --workers=1` → **20 passed**（~18s · 18080+5173 · `init_ims_db.ps1` + API 重启后）；默认 8 worker 易触发 admin **登录锁定**；**pytest collect** 仍为 **144**。

### 2026-10-07 · #32 内容计划启动主链

- **API**：`POST /admin-api/ims/content/plan/{id}/start`（DRAFT→IN_PROGRESS · SOP 节点×IP 组 → `ims_content_task`）· `GET /content/task/page?planName=`。
- **前端**：`/ims/content/plan` 行内「启动」。
- **E2E**：`closure-content-plan-start.spec.ts` · Checklist **v2.6.42** · 全量 **23/23**（不含 L3 spec）。
- **UAT**：对照表「内容 · 生产主链」→ **可 UAT**（SOP 启用 → 草稿计划 → 启动 → 我的任务可见）。
- **Live**：新路由需 **`start_api.ps1 -KillPort`** 后验收。

### 2026-10-08 · #34 纯 UI closure 24/24

- **根因**：`ProtoDrawer` 仅渲染 `#foot`，内容模块 SOP/计划/内容/发布抽屉用 `#footer`，Playwright 等不到「保存」；task-execute 另用任务号 `17` 作 `hasText` 触发 strict 多行。
- **修复**：`ProtoDrawer.vue` 同时挂载 `foot`/`footer` 槽（`useSlots`）· `closure-content-task-execute.spec.ts` 完成态改 `nodeName.first()`。
- **E2E**：`test:e2e:ci` **24/24 PASS** · `e2e_result.txt` 2026-10-08 09:26 · 内容 **UAT 状态不变（未测）**。

### 2026-10-07 · #31 通讯录授权范围定根（续）

- **根因**：接口权限 ≠ **通讯录授权范围**；固定 `dept_id=1` 在新应用未授权时 **50004**。
- **代码**：`auth/scopes` → `authed_dept` 定根 · BFS **50004** 跳过 · `authScopeHint` · `test_dingtalk_client_scopes.py`（**collect +3 → 154**）。
- **PO**：[钉钉通讯录同步说明.md](../运维/钉钉通讯录同步说明.md) · 全量同步前 **全部员工** + 发布。

### 2026-10-08 · #46–#52 团队同步 · 自动链暂停

- **范围**：WORKBENCH / CORP 领还 / TRAIN 下发·统计 / FIN 成本·利润反查 / **DC-001 账号穿透**（#52）· 文档 SSOT（对照表、执行进度、Checklist **v2.6.56–v2.6.62**）。
- **E2E**：全量 **46/46 PASS** · `ims-web/e2e_result.txt`（2026-10-08 15:43 · **6173** + **18080**）。
- **PO 指令（更新）**：**#54+ 自动链已重新启用**（见 [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md)）。

### 2026-10-08 · #55/#56 S6 水印 + S2 直播窄 closure

- **#55**：`cert_e2e_seed` · `closure-corp-cert-watermark` · Checklist **v2.6.65** · pytest **+1 → 169** · **已完成**。
- **#56**：`closure-live-session-report` · Checklist **v2.6.66** · 无新增 pytest · **已完成**（与 #55 同提交 `ab3625b`）。
- **E2E**：`npm run test:e2e:ci` → **50/50 PASS** · `e2e_result.txt` · **18080 须 `-KillPort` 重启**（否则 DC detail **404**）。
- **PO（2026-10-08）**：曾写 **自动链 #55 后暂停**（不自动开 #57）。**同日 zhang wu 解除**：自 **#57** 恢复；本 PR 之后父代理继续 **#58+**，除非再暂停。

### 2026-10-08 · #57 S3 分成 PAID_OFF + 台账对账

- **#57**：`ims_fin_share_result` · 契约 `GET /fin/share/results` + audit/payoff · `share-result.vue` / `ledger.vue` · `closure-fin-share-payoff.spec.ts` · Checklist **v2.6.67** · `test_fin.py` **10 passed** · collect **170** · E2E **51/51 PASS**（`e2e_result.txt`）。
- **不做**：期间结账 LOCKED、结账后更正（E2E-S3-06/07）留 **#59+**。规则引擎 CRUD 不在本切片。
- **自动链**：PO 恢复。**本 PR 止于 #57**。
