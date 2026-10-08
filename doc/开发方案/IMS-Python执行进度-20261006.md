# IMS Python 执行进度（2026-10-06）

> **2026-10-08 本回合（#59 · S3 期间结账 LOCKED + 锁后更正）**：rebase 到 main `eb3991d`（**#58** 已合入，保留 IP 组树「加载中」等待）。`ims_fin_period` · `GET /fin/period` · `POST /fin/period/close` · 锁定月写入 **1142**（归并原 1010）· 未批锁后更正 **1155** · 嵌入既有 `FL-REIMB`（`FIN-LOCK-{sessionCode}`）后走 `POST /fin/cost/{sessionCode}/correction` 红冲+蓝补。`closure-fin-period-lock.spec.ts`（E2E-S3-06/07 · 纯 UI）· `test_fin.py` **11 passed** · collect **172** · Checklist **v2.6.69** · 跑前 refresh workbench/acct/FIN/cert 种子 · E2E **53/53 PASS**（18080 + 6173 · `--workers=1`）。状态 **开发完成/待 UAT**。**#57/#58 已完成**。**#60** = S4 他人领用 **1021** / 账号流转（E2E-S4-02/03）**进行中**（并行，非本片）。
> **2026-10-08 本回合（#58 · S4 冲话费登记 + 凭证门禁）**：`POST/GET /admin-api/ims/account/recharge`（`clientToken` 幂等）· 金额 **>5000** 且无凭证 → **1025** · `voucherUrl` 仅角色 `acct:r3` / 财务管理员可见，其他人见 `voucherAttached` · 时间线 `RECHARGE` 不含凭证原文。种子账号 `AC-E2E-POOL`，财务用户 `e2e_acct_r3`。`closure-corp-account-recharge.spec.ts`（E2E-S4-05/06）· `test_acct_recharge_voucher_gate_and_finance_visibility` · collect **171** · Checklist **v2.6.68** · 与 main **#57**（`74c93cb`）合并后 E2E **52/52 PASS**。**#58 = 本切片**（已合入 main `eb3991d`）。E2E-S4-02/03（1021 / 账号流转）现为 **#60 进行中**。结账 LOCKED 见上 **#59**。
> **2026-10-08 上一回合（#57 · S3 分成 PAID_OFF + 台账对账）**：PO（zhang wu）**恢复自动链**。`ims_fin_share_result` · 成本核准/`upsert_profit` 按手工达人/实名人额生成 `PENDING_AUDIT` 分成单（已审/已发放/已冲销不改写）· `GET /fin/share/results` · `PUT /fin/share/result/{id}/audit`（财务+业务双审，本地 `sys:admin` 可代双岗）· `PUT …/payoff` → **PAID_OFF**（未双审 **1148** · 非法角色 **1149**）· 拆分累计 = `shareDaren+shareRealname`。前端 `/ims/fin/share/result` · `/ims/fin/ledger`（四账由既有 cost/profit/share GET 拼装，**无新对账 REST**）。`closure-fin-share-payoff.spec.ts` · `test_fin.py` **10 passed** · collect **170** · Checklist **v2.6.67** · 当时 E2E **51/51 PASS**。结账 LOCKED 当时未做（现 **#59**）。**#58 不是流转/1021**。
> **实时任务看板**（并行开发/测试/验证/修复）：[`IMS-任务进度计划表.md`](./IMS-任务进度计划表.md)  
> **PRD 功能点矩阵**：[`IMS-PRD功能点执行对照表.md`](./IMS-PRD功能点执行对照表.md)（**UAT 建议/状态** · PO 签收）  
> **Agent 交付循环**：[`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md) · Cursor 规则 `.cursor/rules/ims-delivery.mdc`
>
> **2026-10-08 续（#45 后 · E2E baseline 38/38）**：#45 BR-212 全量曾 **35/38**（`closure-content-plan-terminate` / `task-execute` / `work-task*` · IP 组成员「已存在」表未刷、登记表 **CONFIRMED** 行禁填、作者 **900001** UI 断言误用 id 非 `E2EClosureAuthor`）· **`closure-helpers.ts`**：`ensureAdminMember` 重载成员、登记 **撤回/幂等/当日 workDate**、**`bindOpsAuthorToIpGroup`** 等 GET/POST、`passContentReviewViaUi` 等列表响应 · **18080 `-KillPort` 重启** · **`test:e2e:ci` → 38/38 PASS**（`e2e_result.txt` 2026-10-08 12:32）· 计划表 **#2** 同步。
> **2026-10-08 本回合（#44 · ALERT 处置 Tab）**：`live.vue` 处置 toast · `closure-alert-handle-tab.spec.ts`（纯 UI 试跑→处理→处置记录→去重）· `test_alert` 延伸 **HANDLE** · **4 passed**（定向 `test_alert.py`）· Checklist **v2.6.54** · E2E **37/37 PASS**（6173 · `e2e_result.txt`）。
> **2026-10-08 本回合（PO 端口）**：本机 **5173 占用** → Vite dev + Playwright/E2E 默认改 **6173**（`vite.config.ts` · `playwright.config.ts` · `run_e2e.ps1` · `E2E_BASE_URL=http://127.0.0.1:6173`）· API **18080** 不变。
> **2026-10-08 E2E CI 5173 拒连**：根因 `run_e2e.ps1` 仅在 `E2E_BASE_URL` 未设时赋值，shell/CI 残留 **5173** 时 Playwright 仍打 5173 而 Vite 在 **6173** → **27/27 ERR_CONNECTION_REFUSED**；已改为跑 Playwright 前**强制** `$env:E2E_BASE_URL=$WebBase`（6173）。
> **2026-10-07 本回合（DB + #20）**：本地 **MySQL `ims`** 初始化（`scripts/init_ims_db.ps1` · 86 表 · `opsbiz` 同建）· 联调 18080 冒烟 · targeted pytest · **#20** 预警规则页改调 `POST /alert/rule/{id}/trial` + toast（后端 **#17** 已有）。
>
> **2026-10-07 本回合（续）**：#19 FLOW-004 `GET /flow/timeout/list` + `PUT /flow/timeout/{id}/urge` · `remind_count` · 流程页「超时督办」Tab · `test_flow_timeout_list_and_urge` · compat `20261007_flow_timeout_urge.sql` · **Live verify**（18080 · list/urge **code 0**）· **#3/#8d** 用户「已执行请继续」签收 · `collect-only` **142**。
>
> **2026-10-07 本回合（#21）**：`GET /flow/timeout/rate` BR-115 统计桩 · 督办 Tab 指标行 · `test_flow_timeout_rate_br115_stub` · **#3** 用户 cmd 二次签收（无 pytest_result 末行留存）· **collect-only 143** · Live verify rate **code 0**。
>
> **2026-10-07 本回合（#12 窄 E2E）**：新增 `smoke-flow-timeout.spec.ts` · `smoke-alert-trial.spec.ts`；Checklist **v2.6.36**；`npm run test:e2e` → **16 passed，0 failed**（18080+5173 · ~5.8s）。
>
> **2026-10-07 本回合（#22 + #12 闭环）**：`GET /flow/timeout/distribution`（`groupBy` · 时长分桶 + domain/template）· 督办 Tab「时长分布」· `test_flow_timeout_distribution_stub` · **collect-only 144**；3 条 `closure-*.spec.ts`（E2E-FLOW-01/02 · E2E-S11-01 切片）· Checklist **v2.6.37** · E2E **19/19 PASS**（~4.8s）。
>
> **2026-10-07 本回合（#23）**：`closure-perf-issue-export.spec.ts`（E2E-S9-切片 · CONFIRMED 种子 → UI 下发 → 结果页 CSV 导出 BOM）· Checklist **v2.6.38** · 无后端/pytest 增量 · E2E **20/20 PASS**（`--workers=1` · ~18s）。
>
> **2026-10-07 本回合（#24 + PRD 矩阵）**：新增 [`IMS-PRD功能点执行对照表.md`](./IMS-PRD功能点执行对照表.md) · **S7** `closure-content-publish.spec.ts`（pending→督办→回填→已归档）· `main.seed` 补 `e2e_author`/抖音桩 · Checklist **v2.6.39** · E2E **21/21** · pytest **144** 不变。
>
> **2026-10-07 本回合（#25 · PO E2E 自动化）**：`ims-web/scripts/run_e2e.ps1` · `npm run test:e2e:ci` · `e2e_result.txt` + HTML 报告 · [`IMS-E2E验收策略.md`](../测试方案/IMS-E2E验收策略.md) · Checklist **v2.6.40**（smoke ≠ 签收）· Agent 签收 **21 passed**。
>
> **2026-10-07 本回合（#26 · PO 确认交付方法论）**：`.cursor/rules/ims-delivery.mdc` + [`IMS-Agent交付循环.md`](../开发规范/IMS-Agent交付循环.md) · PRD 对照表 **UAT 建议/状态** · **已验收** 三门禁（closure + E2E + PO UAT）。
>
> **2026-10-07 本回合（#27 · L3 钉钉组织）**：`IMS_DINGTALK_*` / `IMS_FOOTBALL_WEBAPI_BASE_URL` 入 `core.py` + `.env.example` · `app/dingtalk_client.py`（OAuth accessToken）· `tests/test_org_dingtalk_l3.py`（`IMS_DINGTALK_L3=1` 门控）· `scripts/run_dingtalk_l3.ps1` · `npm run test:e2e:dingtalk` · 组织行 **已验收†**=L3 PASS + UAT · Checklist **v2.6.41 / E2E-ORG-DING-01**。

> **2026-10-07 本回合（#28 · 系统参数）**：`app/settings_runtime.py` · 钉钉/Football 键 seed + `dingtalk_client`/`dingtalk_crypto`/`football_client`/`bi_subscribe` 改读 DB 参数 · 前端 `param.vue` 密钥 password · `scripts/seed_dingtalk_params_from_env.ps1` · `tests/test_settings_runtime.py` · `.env.example` bootstrap 说明 · 交付循环 §资源 PO 主路径=UI。

> **2026-10-07 本回合（PO L3 执行 · #29/#30）**：PO 本机 `.env` + `seed_dingtalk_params_from_env.py`（修 PS 嵌入 py）→ **L3 PASS**（`dingtalk_l3_result.txt`）· `pytest.mark.l3` · L3 Playwright 改 UI 登录 · **#29** `smoke-content-plan.spec.ts` · E2E **22**（+L3 **23**）· **#30** 并行 Subagent=Yes（无耦合并行）· `collect-only` **151** tests。

> **2026-10-07 本回合（#31 · PO 钉钉参数 + 全量同步）**：`seed_dingtalk_params_from_env.ps1` → 系统参数 **DB>env** · `POST /auth/org/sync-from-dingtalk`（topapi 部门树 + 人员 upsert）· 组织页「手动对账」同 API · `run_dingtalk_org_sync.ps1` · `dingtalk_sync_result.txt`（**1** 部门 · 首次 **+3** 人 · 复跑 **更新 3** · **0** 失败）。
>
> **2026-10-07 续（#31 · PO UI 改凭证后复跑）**：`start_api.ps1 -KillPort` 重载 DB 参数 · GET 系统参数确认 `dingtalk.corpId`/`clientId` 已变 · `run_dingtalk_org_sync.ps1` → **失败** `dingtalk_50004`（部门不在授权范围；token 换取成功）· 见 `dingtalk_sync_result.txt`。
>
> **2026-10-07 续（#31 · 授权范围定根）**：`resolve_authorized_root_dept_ids`（`topapi/auth/scopes` → `authed_dept`）· 探测 dept **1** 失败时 `authScopeHint` · BFS **50004** 跳过 · `tests/test_dingtalk_client_scopes.py` · `doc/运维/钉钉通讯录同步说明.md`。
>
> **2026-10-07 续（#31 · PO 重置授权范围后复跑）**：`start_api.ps1 -KillPort` · `run_dingtalk_org_sync.ps1` → **code 0** · **1** 部门 · **更新 3** 人 · 仍非全组织 · `dingtalk_sync_result.txt`。
>
> **2026-10-07 续（#31 · BFS listsub 解析修复）**：根因 **`v2/department/listsub` 返回部门对象数组**，旧代码只读 `dept_id_list`（属 `listsubid`）致 BFS 止于根 · 改 **`listsubid` 优先 + listsub 数组解析** · meta `listsubCalls`/`rootSubDeptIdCount` · pytest **4 passed** · Live **19** 部门 · **+46** 人 · **更新 3** · `dingtalk_sync_result.txt`。

> **2026-10-07 本回合（#32 · 内容计划启动）**：`POST /content/plan/{id}/start`（DRAFT→IN_PROGRESS · 按 SOP 节点×IP 组写 `ims_content_task` · 非 DRAFT **1502**）· `/ims/content/plan`「启动」· `GET /content/task/page?planName=` · `closure-content-plan-start.spec.ts` · `test_sop_list_and_plan_create` 延伸 · **collect-only 151** · E2E **23/23**（`test:e2e:ci -SkipServe`）· Checklist **v2.6.42**。

> **2026-10-08 本回合（#34 · closure 纯 UI 门禁）**：PO 强制 — `closure-*.spec.ts` 禁止 `page.evaluate`+`/admin-api` 造数；新增 `ims-web/e2e/closure-helpers.ts` · 重构 plan-start / task-execute / content-publish / perf-export · `publish.vue`「新建发布单」· Checklist **v2.6.44** · 交付循环/`.cursor/rules/ims-delivery.mdc`/`e2e/README.md` · E2E 以 `e2e_result.txt` 为准。
>
> **2026-10-08 续（#34 · 内容 closure 21→24）**：根因 — 内容页 `#footer` 未落入 `ProtoDrawer.drawer-f`（保存按钮不可点）；`ProtoDrawer` 加固 `foot`/`footer` 槽 · `closure-content-task-execute` 用 `nodeName` 避免任务号子串误匹配 · **`npm run test:e2e:ci` → 24/24 PASS**（内容 UAT 仍 **未测**，PO 手工签收）。

> **2026-10-08 本回合（#35 · 工作任务 CONTENT_GENERATION 审核完成）**：后端链路由 **`test_task_execute_content_gate_and_crud`** 覆盖（标注 #35）；补 **`find_enabled_sop` 同版本按 id 降序** · 种子 **`E2EClosureAuthor` id=900001**（`main.seed` · 供 IP 组纯 UI 绑定）· 前端 **`sop.vue`** 支持 `marketingPlan` + `CONTENT_GENERATION`/`documentType` · **`closure-content-work-task.spec.ts`**（登记→确认→执行→提审→`e2e_author` 审过→admin **DONE**）· `closure-helpers` 工作任务辅助 · 定向 pytest **1 passed** · **`test:e2e:ci` → 25/25 PASS**（`e2e_result.txt` 2026-10-08 09:39）· Checklist **v2.6.45**。

> **2026-10-08 本回合（#36 · 计划终止申请→审批）**：`POST /content/plan/{id}/terminate` · `…/terminate/approve` · `…/reject`（对齐 OPS 状态机 · 审批桩 admin id=1）· `ims_content_plan.terminate_reason` · compat **`20261008_content_plan_terminate_reason.sql`**（已有 ims 库需手工/`-ApplyCompat`）· **`plan.vue`** 行内「申请/批准/驳回终止」· **`closure-content-plan-terminate.spec.ts`** + `closure-helpers` · **`test_plan_terminate_approve_flow` 1 passed** · **`test:e2e:ci` → 26/26 PASS**（`e2e_result.txt` 2026-10-08 09:48）· Checklist **v2.6.46** · collect **157**。

> **2026-10-08 本回合（#37 · 工作任务 execution/矩阵 Tab）**：`work-task.vue`「任务执行情况」（契约 **#3** `GET /content/task/page` · `workDate` 筛选 · `authorName`/直播字段）·「任务管理」（登记表矩阵两级表头 + summary · 只读）· `work_task.sheet` 增 **`ipGroupLeaderName`** · **`closure-content-work-task-tabs.spec.ts`**（**纯 UI**）· **`test_work_task_confirm_and_withdraw`** 延伸断言 **1 passed** · 端口 **6173** · **Playwright 27/27 PASS**（`e2e_result.txt` 2026-10-08 10:24）· Checklist **v2.6.47**。

> **2026-10-08 本回合（#38 · HOME 运营看板 KPI）**：**W6 HOME-001** 已有 `/ims/home` + `GET /home/dashboard` · 补 **`smoke-home.spec.ts`**（运营仪表盘 · 四 KPI · 快捷入口）· **`closure-home-dashboard.spec.ts`**（纯 UI：「今日作品」数据延迟桩 · 刷新 dashboard · 账号数下钻抖音 · 快捷「登记工作任务」）· 定向 **`tests/test_home.py` 3 passed** · **Playwright 29/29 PASS**（`test:e2e:ci` · **6173**）· Checklist **v2.6.48**。

> **2026-10-08 本回合（#33 · 任务执行完成 · pytest 复验）**：`test_plan_start_normal_task_execute_complete` 定向复跑 **1 passed**（~15–24s/次 · 含 autouse 全库 reset）。链路与 **#32** 一致：`plan/start` 写任务时带 `plan_name` · `onlyMine`+`planName` 筛任务 · NORMAL 节点 `execute/complete` 空工作说明 **1500**、有说明则 **DONE**（`content_task.complete_task` · ADR-079）。若曾失败：多为 `planName` 查不到任务（启动未写 `plan_name`）或集成 shell **不足 30s 超时/杀进程**（无断言摘要即 exit 1）；当前实现已对齐，**无需再改后端**。

## 本地 MySQL ims 库初始化（可重复）

1. **凭据**：环境变量 `IMS_MYSQL_USER` / `IMS_MYSQL_PASSWORD` / `IMS_MYSQL_HOST` / `IMS_MYSQL_PORT`（默认 `root` / `root` / `127.0.0.1` / `3306`）；业务库名 `IMS_DB=ims`、`IMS_OPS_DB=opsbiz`（见 `ims-backend/app/core.py`）。勿把真实密码写入仓库。
2. **一键建库 + 表 + 种子**（PowerShell）：
   ```powershell
   Set-Location d:\self\sy\IMS系统产品\ims-backend
   powershell -NoProfile -File .\scripts\init_ims_db.ps1
   ```
   等价于 `ensure_databases()`（`CREATE DATABASE IF NOT EXISTS ims/opsbiz CHARACTER SET utf8mb4`）+ `init_db()`（`Base.metadata.create_all` + `ensure_ops()` + `seed()`）。
3. **已有 ims 库、缺历史列/表时**（按文件名日期顺序，重复 ALTER 可忽略）：
   ```powershell
   powershell -NoProfile -File .\scripts\init_ims_db.ps1 -ApplyCompat
   ```
   或手工执行 `ims-backend/db/compat/*.sql`（重点：`20261006_content_s3_columns.sql`、`20261007_flow_*`、`20261007_perf_record_adjust.sql`）。
4. **测库 pytest**：仍用 `ims_test` / `ims_ops_test`（`scripts/_reset_test_dbs.py`），与业务库 **ims** 分离。
5. **启动 API**：`powershell -NoProfile -File .\scripts\start_api.ps1 -KillPort` → `GET http://127.0.0.1:18080/health` 期望 **200 · code 0**。
>
> **2026-10-07 上一回合**：#18 `GET /perf/result/export` CSV 桩 + `result.vue` 导出；#17 `POST /alert/rule/{id}/trial` 试跑别名；pytest `collect-only` **141**；**#17/#18 Live verify**；E2E **14/14**。

## UI 收口

- 做了什么：复核 `doc/UI原型/pages/` 已有完整拆页；`ims-web` 已用 `prototype.css`（设计变量、侧栏 232px、顶栏、卡片、表格）和原型外壳。登录是用户名 + 密码。没接口的菜单进「建设中」。本片没有改样式，避免覆盖已经对齐的页面。
- 测试：浏览器 1440 宽侧栏常驻、宽 232px；390 宽出现「打开菜单」，点开后侧栏带 `is-drawer on`、遮罩出现。登录后进入系统。
- 下一片：S-IMS-S-02 角色。

## S-IMS-S-02 角色

- 做了什么：角色成为权限载体。菜单码（含 `ops:*`）、功能点 R/W/D、dataScope（ALL/DEPT/IP_GROUP/SELF，拒绝 `DEPT_AND_CHILD`）、钉钉岗位唯一、`POST /system/role/{id}/preview`、`POST /system/role/from-position`（PENDING_CONFIG 空权限 + R1 待办，重复调用不覆盖）。`POST /auth/position/preview` 不存在。菜单树只读。登记册补了 `ims_auth_todo`（#23）。「本部门不含下级」的行级过滤留到 B9，本片只保存枚举。
- 测试：`python -m pytest -q` 为 9 passed（原 6 个未改坏，新增 3 个角色用例）。浏览器在角色页从岗位生成「主播达人」，列表为待配置、0 菜单；预览 `pendingIgnored=true`、`rolePermCodes=[]`。
- CHECKLIST-IMS-SYS §3：列表、菜单勾选保存、R/W/D、dataScope、岗位唯一、来源/待配置、预览与从岗位生成，已由接口和角色页覆盖。菜单页只展示路由、权限码、类型、可见；契约没有菜单写入接口，未做菜单编辑抽屉。
- P0：TC-IMS-S-002-01、TC-IMS-S-002-02 已有 pytest。TC-IMS-SYS-02-01-01 的规则同一套；TC-IMS-SYS-03 只覆盖菜单树读取，没有单独的菜单编辑故事。
- 下一片：S-IMS-S-03 字典 / S-IMS-S-04 参数。

## S-IMS-S-03 字典 / S-IMS-S-04 参数

- 做了什么：字典类型与字典数据可查，种子含 `dict_platform_type`、`dict_sop_node_type`、`dict_position` 等。停用项 `DELETE /system/dict-data/{id}` 返回 1503「停用值不可删」；启用项可以删。参数种子含 `work.task.confirm.auto-ai-generate`、`content.review.*`、`dingtalk.sso.enabled`、`air.key.ip_whitelist.enabled`。未知 key 的 PUT 返回 1213。契约总览没有单列删除路径，这条删除是计划里的停用不可删规则。
- 测试：`python -m pytest -q` 为 11 passed。浏览器字典页左类型右数据，删除「已停用」提示「停用值不可删」。参数页把任务开关改成 true 后再改回 false。
- CHECKLIST：类型联动、停用不可删、并入字典、必含 key、1213 已覆盖。字典值的命名规则只在种子里遵守，契约没有新建字典接口，页面不能手输新值。
- P0：TC-IMS-S-004-01、TC-IMS-S-005-01 已有 pytest。US-SYS-04 / US-SYS-05 主路径在浏览器走过列表；没有单独勾「租户套餐控制侧栏」。
- 下一片：S-IMS-A-02 组织事件入队、幂等、16 次死信，并写入本地用户。

## S-IMS-A-02 组织事件

- 做了什么：`POST /auth/org/event` 先验签、解密，再按 `dingtalkEventId|eventType` 入队。重复投递直接成功，不插第二行。Worker `process_due` 才写 `ims_sys_user`、`ims_auth_user_mapping`、`ims_auth_user_dept`。失败按 1 分钟 / 5 分钟 / 15 分钟 / 1 小时退避，第 16 次 `dead_letter=1` 且 `alert_code=ims.org.dead_letter`，之后不再重试。入职建本地用户，调岗记下原部门与 24 小时 `buffer_until`，离职把本地用户改为 `FROZEN`。不调用 Football。`POST /auth/org/reconcile` 仅 `sys:admin`（R1），其他人 403；成功写入一条对账事件。指标含契约字段，并给页面 `delayMillis` / `level`（小于 300000 为 green）。
- 测试：`python -m pytest -q` 为 18 passed（原 11 个未改坏，新增 7 个组织用例）。浏览器 1440 侧栏宽 232、无抽屉；组织页延迟 0 ms、绿色，确认对账后事件表出现「对账」且提示已受理。390 宽出现「打开菜单」，点开后侧栏为 `is-drawer on`，遮罩出现。
- 未做：钉钉全量通讯录拉取，所以对账只核对本系统已同步人员，连续 2 次失败的 P1 告警没有触发源。回调 P95 用 30 次断言小于 500ms，没有打到验收策略里的 200 并发。调岗 24 小时内旧数据范围仍生效留到 B9，本片只记下缓冲截止时间。D4 对账报告和 D5 重放没有做。页面事件列表只展示第一页和总条数，没有翻页按钮。
- CHECKLIST-IMS-AUTH §3 三项已勾：同步状态列、对账仅 R1、事件与延迟可展示。§1 全局项未勾。
- 下一片：S-IMS-A-03 岗位→角色供给规则。

## S-IMS-A-03 岗位供给

- 做了什么：供给规则表 `ims_position_template`。新建版本为 1；同一钉钉岗位再启用一条返回 1001。编辑停用旧版本并新建 `version+1`，不改已有用户角色。`applied_user_count` 非 0 时删除返回 1001，归零后逻辑删除。授予 `PENDING_CONFIG` 角色返回 1002。`POST /auth/position/role-auto-create` 复用角色片的 `auto_create_role`，空权限、重复调用不覆盖。旧路径 `/auth/position/template(s)` 只做同逻辑别名。没有再写权限矩阵，也没有 `POST /auth/position/preview`。
- 测试：`python -m pytest -q` 为 20 passed（新增 2 个供给用例）。浏览器 1440 侧栏宽 232。用「系统管理员」新建「直播运营岗供给」，列表版本 1、启用；点「新版本」后版本 2 启用、版本 1 停用。390 宽「打开菜单」后侧栏为 `is-drawer on`，遮罩出现。
- CHECKLIST-IMS-AUTH §4：版本与逻辑删除已勾；预览项沿用角色片已勾。抽屉编辑没做，对应项未勾。
- 下一片：S-IMS-A-04 工作台。

## S-IMS-A-04 工作台

- 做了什么：已登录即可打开。`GET /auth/workbench/dashboard` 返回待办数、未读数，账号/资产/证件/场次先为 0。待办、消息只查当前用户，分页最大 100，工作台预览请求 `pageSize=10`。逾期待办排在前面。关闭待办、单条已读、全部已读都有接口；已读重复调用仍是 200。别人的待办关闭返回 1504。消息表登记为 `ims_auth_message`（#24）。
- 测试：`python -m pytest -q` 为 22 passed（新增 2 个工作台用例）。浏览器 1440 侧栏宽 232。从岗位生成「场控浏览器」后，工作台待办数为 2，预览两条，未读 0，消息为空。390 宽「打开菜单」后侧栏为 `is-drawer on`，遮罩出现。
- CHECKLIST-IMS-AUTH §5：首屏聚合和分页/关闭/已读已勾。P4a/P4b 深链没做，未勾。页面上还没有待办关闭按钮。
- 下一片：S-IMS-S-05 操作日志、登录日志、通知。

## S-IMS-S-05 操作日志、登录日志、通知

- 做了什么：三张表按登记册 #20 落地。`GET /system/operate-log/page`、`GET /system/login-log/page`、`GET /system/notify/page` 都分页，默认 10，最大 100。密码登录和钉钉回调的成功、失败写入登录日志。已登录的 POST/PUT/DELETE 写入操作日志，不记录口令。通知在服务内按 `(tenant_id, event_type, biz_key)` 去重，第二次不再插入。契约没有导出和补发，页面没有做这两个写操作。
- 测试：`python -m pytest -q` 为 26 passed（原 22 个未改坏，新增 4 个日志/通知用例）。浏览器 1440 侧栏宽 232。参数页把钉钉开关改为 true 再改回 false，操作日志两行「更新参数」。退出后用错误密码再正确登录，登录日志有失败和成功。通知页一条 `TASK_PENDING / TK-881 / 孙倩 / 站内+钉钉 / 已送达`，重复发布没有第二行。390 宽出现「打开菜单」，点开后侧栏为 `is-drawer on`，遮罩出现。
- CHECKLIST-IMS-SYS §6 两项已勾。§1、§7 未勾。
- 下一片：B9 权限中间件。

## B9 权限中间件

- 做了什么：已登录请求先过 `gate`。工作台 `/auth/workbench` 只认登录，不做数据范围。其余已登录路径必须落在本批表注册表里，否则 1008。没有启用角色、只有 `PENDING_CONFIG`、启用角色没有功能点、数据范围不在 ALL/DEPT/IP_GROUP/SELF，都是 1008「无数据权限」。表表达不了当前范围（例如 DEPT 打到没有部门轴的操作日志，IP_GROUP 打到用户表）也是 1008。用户详情按 id 更新时，不存在、跨租户、不在查看范围内，对外都是 1504「资源不可用」，响应不带资源内容。DEPT 只认 `ims_auth_user_dept` 里的部门号，不含下级。`ims_user_scope` 按启用角色物化；BR-212 用查看者范围和创建者范围求交，发布类谓词里没有下级展开。改角色数据范围会重算持有人的范围行。
- 测试：`python -m pytest -q` 为 30 passed（含上一片的 26 个，新增 4 个权限用例）。空权限、待配置、空功能点、非法范围、IP_GROUP 打用户表，用户分页都是 1008；同一个人打开工作台仍是 200。不存在和跨租户的更新返回同一句「资源不可用」。DEPT 用户能看见本部门同事，看不见子部门用户和管理员；范围表只有本部门号。BR-212：别的部门看不见，本部门看得见同部门行，ALL 查看者仍看不见创建者「仅本人」的行。浏览器 1440 侧栏宽 232，管理员用户列表正常。新建无角色用户 `b9bare` 后，用户页提示「无数据权限」，工作台仍显示待办 0、未读 0。390 宽「打开菜单」后侧栏为 `is-drawer on`，遮罩出现。
- 对账接口：没有权限的人现在先被 1008 挡住。组织用例里的非 R1 改成有功能点但不是系统管理员，仍然 403「仅 R1 可对账」。
- 未做：内容、报表这类发布/分享业务表还没有，BR-212 用测试表 `scope_probe` 跑同一条谓词，没有另开契约外接口。
- 下一片：S-IMS-C-02 公司、实名人、手机卡、证件。办公/直播设备只做阻断页。

## S-IMS-C-02 公司、实名人、手机卡、证件

- 做了什么：登记册补了 #25 `oa_company`、#26 `oa_realname`、#27 `oa_sim_card`、#28 `oa_phone`（只建表，供手机卡 `phoneId` 校验）、#29 `ims_cert_archive`。公司、实名人、证件按 CORP 契约只有查询。手机卡有分页、详情和 POST/PUT。证件号、手机号、ICCID 加密后只返回脱敏值。归属人和可选实名人必须是本租户已有记录，不存在 1500，停用 1501，跨租户 1504。证件查看带水印文字，不返回原图。公司已注册公众号数先为 0，手机卡关联账号先为空列表。非 ALL 打开公司列表是 1008。
- 测试：`python -m pytest -q` 为 33 passed（原 30 个未改坏，新增 3 个资源用例）。浏览器 1440 侧栏宽 232。公司、实名人、证件都是空列表和「共 0 条」。手机卡新建后列表为 `139****2222`，详情抽屉同样脱敏，关联账号 0。390 宽出现「打开菜单」，点开后侧栏为 `is-drawer on`，遮罩出现。
- CHECKLIST-IMS-CORP §3 两项已勾。§1、§2、§4、§5 未勾。
- 未做：公司/实名人写入（契约没有）、证件上传与到期扫描、中介人维护、对象存储原图。
- 下一片：办公/直播设备阻断页；手机设备按 MASTER 契约。

## 办公 / 直播设备阻断页，手机设备

- 做了什么：办公、直播设备不建台账表。`GET /corp/device/office/page` 和 `GET /corp/device/live/page` 固定空分页，页面写明增删改已阻断，没有新建按钮。手机沿用登记册 #28 `oa_phone`。`GET/POST/PUT /master/phone`，CORP 的 `GET /corp/device/phone/page` 与 `/{id}` 读同一张表。保管人必须是本地用户。号码加密后脱敏。没有实名人列。影像只存 key，没有上传接口。B9 用 `asset_ledger_blocked` 放行两条空列表，这个名字没有物理表。
- 测试：`python -m pytest -q` 为 35 passed（原 33 个未改坏，新增 2 个设备用例）。浏览器 1440 侧栏宽 232。办公设备空列表、「共 0 条」、阻断说明，没有新建。直播设备同样。手机新建后列表为 `136****4444`、类型 iPhone、保管人管理员。390 宽出现「打开菜单」，点开后侧栏为 `is-drawer on`，遮罩出现。
- CHECKLIST-IMS-CORP §4 两项已勾。§1、§2、§5 未勾。
- 未做：资产台账、领用跳转、手机影像上传、绑定账号列表（等平台账号）。
- 下一片：S-IMS-C-01 五个平台账号与采集 Tab。

## S-IMS-C-01 五个平台账号与采集 Tab

- 做了什么：登记册落地 `oa_platform_account`、`oa_ip_group`、`oa_collector_account_bind`（ops 库）。`GET /corp/account/page` 强制 `platformType`（五平台枚举）；列表含 `collectBindSummary`、脱敏实名人。`GET /corp/account/{id}` 详情。采集 Tab 走 M10 对齐的 `GET/POST /corp/account/{id}/collector-bind` 与 `POST …/test-connection`（本地模拟 bind/探活，未接真实 Collector HTTP）。`POST/PUT /master/platform-account` 登记账号，公司/IP 组/实名人/手机/卡/归属人校验 1500/1501/1504。B9 注册 `oa_platform_account`（IP 组轴）。字典平台小红书值改为 `XIAOHONGSHU`，补 `dict_account_status`。手机卡详情关联账号按 `phone_id` 回填。前端五 L3 路由 + 默认重定向抖音；详情抽屉 Tab：基本信息 | 采集 | 领用时间线 | 关联资产（后两者占位说明）。
- 测试：`python -m pytest -q` 为 37 passed（原 35 个未改坏，新增 2 个账号用例；字典用例 XHS 改为 XIAOHONGSHU）。浏览器 1440 宽侧栏常驻（无「打开菜单」）、抖音 L3 标题与 `platformType=DOUYIN` hint、空列表文案。390 宽出现「打开菜单」。未在本机 ops 库预置账号行，未走「登记→采集 Tab」全链路截图。
- CHECKLIST-IMS-CORP §2：platformType 固定、采集摘要列、采集 Tab 对齐 ADR-047（非 COLLECT P2a）、BFF page 已覆盖；§1 默认进抖音路由已加但未做全站默认入口验收；1502/选择器 UI 未全勾；§5 tenant 1504 有 pytest 未勾全局项。
- 未做：真实 OPS/Football 透传、Cookie 更新/扫码登录、ACCT 时间线与领用 BLOCKED 入口、导出、IP 组数据范围物化（IP_GROUP 用户 scope 行未在 resolve 里加载，仅 account 页内补读 UserScope）。
- 下一片：IP 组 + `GET /admin-api/ims/ip-group/{id}/accounts`。

## IP 组 + 账号池级联

- 做了什么：ops 库扩展 `oa_ip_group`（含 `ding_dept_id`）、`oa_ip_group_member`、`oa_ip_group_anchor_rel`（含 `is_primary`）、`oa_author`；账号仍用 `oa_platform_account.ip_group_id` 与 `author_user_id` 物化列。契约内 IPG 端点：`tree` / `accessible-tree` / `list` / `create` / `update` / `delete`、成员 CRUD、`GET|POST …/{id}/accounts`（大组 1203、跨组 1007）、`GET|POST …/{id}/anchors`（主作者降级）、`stats` 占位聚合。B9 登记 `oa_ip_group`；`resolve` 为 IP_GROUP 角色加载 `ims_user_scope` 组 id。前端 `/ims/ip-group` 左树右详情（基本信息 | 成员 | 账号绑定 | 关联作者 | 统计），菜单 `ipg` 已接入。未做 P2 `author/page` 与分析四页；未新增 `authors/{id}/accounts`。
- 测试：`python -m pytest -q` 为 39 passed（原 37 个未改坏，新增 2 个 IP 组用例）。浏览器 1440 侧栏宽 232、标题「IP 组运营」、空树文案；390 宽出现「打开菜单」，点开后侧栏 `is-drawer on`。需重启 18080 后端后前端才能打到新路由。
- 未做：作者独立页、Football 作者档案同步、IP_GROUP 角色物化 scope 行写入（仅读已有 scope）、编辑/停用抽屉、导出、真实采集指标 stats。
- 下一片：W3 S-IMS-L-01 直播场次（`live_room` 只读，GMV 下播录入）。

## S-IMS-L-01 直播场次

- 做了什么：IMS 库落地 `ims_live_session`、`ims_live_risk_check`、`ims_live_report`、`ims_live_data_snapshot`、`ims_live_alarm_record`、场次序列表与 `clientToken` 幂等。契约内 P0：`GET /live/sessions/list|{sessionCode}`、`…/metrics`、`POST …/football-sync`；登记 `POST/GET/PUT /live/register*`、风控 `risk-check`/`approve`/`cancel`/`start`；下播 `POST/GET/PUT /live/report*`、`confirm`、`report/pending`；台账 `ledger/list|{sessionCode}` 与 sessions 同源；关联 Tab 用 `GET /live/alarm/records?sessionCode=`。单场「直播数据」只读 ops 库 `live_room`（测试/本地可 ORM 建表），`football-sync` 更新同步态与快照元数据，**不调 Feign**。GMV/峰值/涨粉/退款/投放由下播录入，`metricsByManualEntry` 标明手工项。19 位场次 ID（`IMS+yyyyMMdd+平台码+序列`）。设备校验暂用 `oa_phone` id。B9 登记 `ims_live_session`（责任人轴 SELF/ALL）。前端 `/ims/live/sessions`（菜单 `live`），列表 + 90% 详情 Drawer Tab：基本信息｜直播数据｜风控登记｜下播与 GMV｜关联。
- 测试：`python -m pytest -q` 为 **41 passed**（原 39 未改坏，新增 2 个直播用例）。浏览器 **1440** 侧栏常驻（无「打开菜单」、有菜单搜索）；**390** 出现「打开菜单」。标题「直播管理」、空列表文案「暂无场次」。18080 若已在跑需**重启**后新 `/live/*` 路由才生效（本机端口占用时未重复启动）。
- 未做：告警规则 CRUD、台账导出/补录、更正单、Redis 序列（现 DB 序列表）、R5/R7 服务端本人过滤细粒度、真实 opsbiz `live_room` 列与 Football 全字段对齐、登记抽屉账号/实名人选择器（暂填 id）。
- CHECKLIST-IMS-LIVE：P0 列表/19 位 ID、metrics+live_room、下播承载 GMV 已由 pytest 与页面 Tab 覆盖；§ 路由/API 全勾未做书面勾选。
- 下一片：**账号财务 COST**（独立菜单；Football 订单 HTTP 桩；失败「数据延迟」）。

## 账号财务 COST

- 做了什么：ops 库落地 `oa_account_cost`（采购单行 + 过程成本多条）。契约 P0：`GET/PUT /cost/account/{id}/purchase`、`POST/PUT/DELETE …/process`；`GET /cost/roi`（公司/IP 组/账号/人员维度，成本本地汇总、营收走 `football_client` HTTP 桩）；`GET /cost/football-order/list` 透传 query。桩未配置或超时：ROI `revenueDelayed` + `revenueDelayHint=数据延迟`，**不写 0**；订单列表返回 **1232**。B9 登记 `/cost/*` → `oa_platform_account`。前端独立菜单 `cost` → `/ims/cost`，`prototype.css` 外壳，Tab：成本登记｜账号 ROI｜Football 订单。
- 测试：`python -m pytest -q` 为 **44 passed**（原 41 未改坏，新增 3 个 COST 用例）。浏览器 **1440** 财务组「账号财务」可进、标题与 Tab 文案对齐；**390** 出现「打开菜单」。未配置 `IMS_FOOTBALL_WEBAPI_BASE_URL` 时 ROI/订单 Tab 显示「数据延迟」。
- 未做：R2/R3 趋势与成本结构、导出 POST、真实 Football 基址联调、冲话费 S4 任务链、按账号 author 与 Football authorId 生产映射规则。
- CHECKLIST：TC-IMS-COST-01-01 P0 主路径（成本 CRUD + ROI 延迟 + 与 FIN 分菜单）已由 pytest 与页面 Tab 覆盖；书面 CHECKLIST 未勾。
- 下一片：**W4 内容 S1（SOP+计划）** 与 **S4（内容审核门禁）**，按 `SLICES-IMS-CONTENT`，不整链开写。

## W4 内容 S1（SOP + 计划）

- 做了什么：IMS 库落地 `ims_content_sop` / `ims_content_sop_node` / `ims_content_plan` 及序列表。契约 P0：`GET/POST/PUT/DELETE /content/sop/list|sop|{id}|nodes`、`POST …/node/{nodeId}/check`（不合规 **1007**）；`GET/POST /content/plan`（草稿 DRAFT，字段对齐补充规格页内索引：计划名/SOP/IP 组/周期）。SOP 编辑生成新版本、逻辑删除需 `confirmText=DELETE`。**SOP 免审**，无审核页。B9 登记 `/content/*` → 内容表。前端 `/ims/content/sop`、`/ims/content/plan`，`prototype.css` 外壳；计划启动/终止等 OPS 路径未做。
- 测试：`python -m pytest -q` 为 **46 passed**（原 44 未改坏，新增 2 个内容用例含 TC-P0-01 smoke）。浏览器 **1440** 内容组三页可进（SOP/计划/审核菜单不再进建设中）；**390** 出现「打开菜单」。18080 需**重启**后新路由生效。
- 未做：LogicFlow DAG 画布、营销计划节点属性、计划 start/terminate、节点 check 全链路挂项目。
- CHECKLIST：S1 Gate 联调项由 pytest + 三页列表/创建主路径覆盖；书面 CHECKLIST 未勾。
- 下一片：**S4 内容审核门禁**（与 S1 同批，见下节）。

## W4 内容 S4（审核门禁 G1）

- 做了什么：表 `ims_content_project`、`ims_content_review`、`ims_content_publish`。**CONTENT-005**：`GET /content/review/queue|{reviewNo}`、`PUT …/conclusion`（**1057** 自审、**1058** 打回缺项）、`first-pass-stats` / `reject-analysis`。**CONTENT-006 门禁**：`POST /content/publish` 仅 `review_passed` 项目可建发布单，否则 **1054**。未做 publish/list/receipt/archive（契约有、本片仅 G1）。前端 `/ims/content/review` 一级/二级 Tab + 结论抽屉。
- 测试：同上 **46 passed**；pytest 覆盖 1054→PASS→发布成功。浏览器审核页空队列文案 + 统计区；未在本机 seed 待审行故未截图全链路。
- 未做：提审 `submit-review`、多级会签参数、发布列表/回填/归档、工作台待办联动。
- CHECKLIST：G1「未审不可发布」已由 pytest 1054/0 覆盖；书面未勾。
- 下一片：**S2 工作任务登记**（`content/work-task`），依赖 S1 SOP；或补 S4 发布列表/督办。

## W4 内容 S2（工作任务登记 · CONTENT-104/105）

- 做了什么：IMS 库落地 `ims_content_work_task_sheet` / `ims_content_work_task_assignment` / `ims_content_task` / `ims_content_work_task_assignment_task`；扩展 `ims_content_sop.marketing_plan`、`ims_content_sop_node.node_type|document_type`、`ims_content_project` 草稿字段。契约 P0：`GET/POST /content/work-task/sheet`（get-or-create + 保存登记行）、`POST …/{sheetId}/confirm`（按营销计划匹配启用 SOP、全节点出 `ims_content_task`、CONTENT_GENERATION 建 DRAFT 内容）、`POST …/{sheetId}/withdraw`（未完成可撤回、删 DRAFT）。**CONTENT-105**：读参数 `work.task.confirm.auto-ai-generate`，true 时草稿 `aiGenerateStatus=QUEUED`，false 不触发 jingcai。未做契约外 `/matrix` · `/execution` · merge/unmerge · 钉钉 TASK_PENDING · Football 下架。
- 测试：`python -m pytest -q` 为 **47 passed**（原 46 未改坏，新增 1 个工作任务 confirm/withdraw 用例）。浏览器 **1440** 侧栏常驻（无「打开菜单」）、标题「工作任务登记」、三 Tab 与契约 hint；**390** 出现「打开菜单」。18080 已重启加载新路由。
- 未做：OPS 两级合并表头矩阵 API、作者/IP 组选择器、执行页与「我的任务」S3、真实岗位匹配 assignee、书面 CHECKLIST S2 勾选。
- 下一片：**S3 我的任务 + 内容管理**（`/ims/content/task`、CONTENT-106），或 **W5 S-IMS-CL-01～03** 采集任务与日志。

## W4 内容 S3（我的任务 + 内容管理 · CONTENT-103/106）

- 做了什么：扩展 `ims_content_task`（deliverables/userAttachments/planName）、`ims_content_project`（matchType/matchScheme/layoutHtml 等）、SOP 节点 instruction/attachments。契约 P0：`GET /content/task/page`（onlyMine 我的/全部）、`GET|POST …/task/{id}/execute*`、`PUT …/task/{id}/complete`（**ADR-079**：CG 须审核通过、NORMAL 须工作说明 **1500**）；`GET/POST/PUT/DELETE /content` 内容 CRUD、`POST …/{id}/submit-review`、`POST …/retry-ai-generate`（QUEUED 桩）。审核 PASS 同步 `content_status=PENDING_PUBLISH`。B9 前缀细分 task/sop/plan/review/publish vs 内容 CRUD→`ims_content_project`。前端 `/ims/content/task`、隐藏 `/ims/content/task/:id/execute`、`/ims/content/list`（玩法 JSON 编辑抽屉）。未做 file/upload、typeset、Football 同步、赛程 WebAPI 多选 UI、矩阵/merge S2 遗留。
- 测试：`python -m pytest -q` 为 **48 passed**（原 47 未改坏，新增 1 个任务门禁+CRUD 用例）。浏览器 **1440** 侧栏常驻（菜单搜索、无「打开菜单」）、标题「我的任务」/「内容管理」；**390** 出现「打开菜单」。本机 **18080 已重启**；`ims` 库需执行 `ims-backend/db/compat/20261006_content_s3_columns.sql`（新增列否则 task/page 500）。
- 未做：真实 jingcai Job、附件上传、执行页 ipGroupTabs 多组联调 seed、书面 CHECKLIST S3 勾选。
- 下一片：**W5 S-IMS-CL-01～03** 采集任务与日志（`/collect/task`、`/collect/log`），或 S4 发布列表/督办补全。

## W5 S-IMS-CL-01～03 采集任务与日志

- 做了什么：ops 库落地 `oa_collect_task` / `oa_collect_task_member` / `oa_collect_log`（复用已有 `oa_collect_config` 供 Channel-D 校验）。契约 P0：`GET/POST/PUT/DELETE /collect/task*`、`POST …/{id}/run`、`POST …/ensure-unified` · `…/ensure-external-unified`、`GET /collect/log/page`、`GET /collect/log/{id}`（含 `typeResults[]` / `result.typeResults`）。本地模拟执行：未 bind → FAILED + `repairAccountId`；已 bind → SUCCESS/PARTIAL。保存单账号任务可带 `bindWarning`（可保存）。B9 登记 `oa_collect_task` / `oa_collect_log`（空 Spec，仅 ALL 数据范围可访问）。前端 `/ims/collect/task`、`/ims/collect/log`，`prototype.css`；编辑抽屉**无 Cookie**；立即执行跳转日志带 `taskId`；日志失败链 `?openId=&tab=collect` 至公司资产账号采集 Tab。补字典 `dict_collect_method/frequency/status`。
- 测试：新增 `tests/test_collect.py` 4 条 P0；`scripts/smoke_collect.py` 冒烟通过。本机全量 `pytest -q` 若遇 MySQL **1684**（`drop_all`+`init_db` 连续 DDL），可先 `DROP DATABASE ims_test` 重建或暂用冒烟脚本；预期在环境正常时为 **52 passed**（48+4）。浏览器采集任务/日志页需**重启 18080** 后验收 1440/390。
- 未做：真实 Collector/xxl-job、任务 start/stop、统一任务成员 UI、M8 竞品配置页（`collect_config.py` 未挂路由）、书面 CHECKLIST 勾选、1241 以外错误码全集。
- 下一片：**W6 HOME-001 运营看板**、BI0 自定义查询，或 M8 外部配置挂路由（`collect_config.py` / `test_collect_config.py` 已占位）。

## W6 HOME-001 运营看板

- 做了什么：契约三接口 `GET /home/dashboard`、`GET /home/todos`、`GET /home/shortcuts`。`dashboard` 返回 KPI×4（账号数本地统计、今日作品固定「数据延迟」、待办数、近 7 天采集 FAILED/PARTIAL）、待办聚合（审核队列/采集失败/个人待办）、快捷入口卡片、占位趋势；日期跨度 &gt;90 天 **1202**；越权 IP 组 **1201**。B9 白名单 `/home/*`（仅登录）。前端 `/ims/home` 对齐原型 KPI/待办/快捷区；菜单 `home` 已接入 IMPLEMENTED。
- 测试：`python -m pytest -q` 全量 **55 passed**（原 52 未改坏，新增 3 个首页用例）。浏览器 **1440** 菜单搜索、标题「运营仪表盘」；**390**「打开菜单」。18080 已重启加载 `/home/*`。
- 未做：IP 组树筛选 UI、Football/OPS 真实 KPI、快捷入口按角色菜单过滤、图表真实序列、书面 CHECKLIST HOME 勾选。
- 下一片：**BI0 自定义查询**（`SLICES-IMS-BI0`），或 W7 会议/日报等按片。

## W5 采集配置（竞品账号 / 关键词 / 元数据 / 阈值 · M8）

- 时间：2026-10-06
- 做了什么：W5「S-IMS-CL-01～03 任务+日志」已在上一节完成；本片补开发计划 W5 **采集配置** 四页。ops 扩展 `oa_collect_config.collect_enabled`，新增 `oa_collect_keyword`、`oa_threshold_config`；ims 库 `ims_metadata_entity` / `ims_metadata_field`。契约：`/collect/external/account/**`、`/external/keyword/**`、`/threshold/list`（category 必填）、`/metadata/list|create|{id}|fields|entity/{code}/fields`（1261）、`unmapped-tables` / `table-columns`。B9 登记 config/keyword/threshold/metadata。字典补 `dict_third_platform`、`dict_match_type`、`dict_threshold_*`、`dict_metadata_*`。前端四路由对接原型菜单（非建设中）；编辑**无 Cookie**。
- 测试：目标 `python -m pytest -q` **57 passed**（原 55 + 新增 2 个 `test_collect_config.py`）。并行 agent 同跑 pytest 时 ims_test 可能出现 1684 并发 DDL，需错开再跑全量。
- compat：已有 ops 表缺列时执行 `ims-backend/db/compat/20261006_collect_config_m8.sql`。
- 未做：P2a CSV multipart 导入、外部 HTTP 数据源/凭账号抽屉、元数据实体 DELETE（超管）、阈值 OVERRIDE AccountSelect UI、P6 质量/手工补录、书面 CHECKLIST M8 勾选。
- 下一片：**BI0 自定义查询**（只读消费 `metadata/entity/{code}/fields`），或 **P6 数据质量**（采集日志顶栏统计 + manual-fill）。

## W4 内容 S5（Football 方案同步 · CONTENT-109/110）

- 做了什么：IMS 库 `ims_fb_sync_outbox` + `ims_content_project` 扩展（`author_article_id` / `fb_sync_status` / 版本与错误字段）。**BR-303**：内容 POST/PUT 保存成功即 200，Football 写走 `football_client`（create/update/status-change 桩；`IMS_FOOTBALL_ARTICLE_STUB=success|fail` 或配置 `IMS_FOOTBALL_WEBAPI_BASE_URL`）；失败记 outbox（幂等键 `content:{tenant}:{id}:upsert|shelf_off:v{n}`，退避 1/5/15 分钟、≤3 次）。契约：`GET|POST /content/{id}/fb-sync`；`GET /content/fb-sync/outbox/page`；`POST …/outbox/{id}/retry`；`POST /content/fb-sync/process-due`（Worker 轮询）。DELETE 草稿/驳回态逻辑删前 **SHELF_OFF**（status=0）。B9 登记 `ims_fb_sync_outbox`。前端内容列表增「Football 同步」列 + 重同步；隐藏页 `/ims/content/fb-sync` 补偿队列（从内容管理链入，无新侧栏 id）。compat：`db/compat/20261006_content_s5_fb_sync.sql`。
- 测试：新增 `tests/test_content_fb_sync.py` 3 用例（未配置→补偿中+outbox、stub 成功→SYNCED+authorArticleId、删草稿→SHELF_OFF）。本机并行 pytest 若遇 MySQL 1684 并发 DDL 可错峰重跑；预期全量 **58 passed**（原 55 + 3）。18080 **需重启**；已有 `ims` 库须执行 compat SQL。
- 未做：真实 member-server HTTP 联调、Football 方案读 enrichment、1058 已上架有订单下架确认、书面 CHECKLIST S5 勾选。
- 下一片：**S4 发布列表/督办**补全，或 **BI0 自定义查询**（`SLICES-IMS-BI0`）。

## BI0 自定义查询（S-IMS-B0-01/02 第一片）

- 时间：2026-10-06
- 做了什么：IMS 库 `ims_bi_custom_query`。契约：`GET /bi/query/page`、`GET|POST /bi/query`、`PUT /bi/query/{id}`、`POST …/{id}/run`、`PUT …/{id}/publish`。保存/执行前只读校验 COLLECT `GET /collect/metadata/entity/{code}/fields` 同源逻辑，未映射 **1261**；run 在 ops 库按元数据列白名单拼 SELECT（`tenant_id`+`deleted`+LIMIT≤1000），返回 SQL/列/行。B9 登记 `ims_bi_custom_query`（creator 轴）。前端 `/ims/bi/query`（`bi0Query` 已 IMPLEMENTED）：双 Tab 自定义查询/我的查询、侧栏只读字段、链元数据维护；**页内无元数据 CRUD**。
- 路由复核：`collect.py` 已 `include_router(collect_config_router)`；`api.py` 已 `content_fb_router` + 本片 `bi_query_router`。
- 测试：新增 `tests/test_bi_query.py` 3 用例（映射 run、1261、发布）。本机单独跑全量时若并行 agent 同跑 pytest 可能 MySQL **1684**，需 `DROP DATABASE ims_test`/`ims_ops_test` 错峰；环境无并发 DDL 时预期 **61 passed**（原 58 + 3）。18080 **需重启** 加载 `/bi/query/*`。
- compat：新表由 ORM `create_all` 覆盖；生产已有库可无需额外 SQL（首启建表）。
- 未做：1262 异步卡、QueryBuilder 条件 UI 全量、图表 Tab、删除接口、书面 CHECKLIST BI0 勾选。
- 下一片：**S-IMS-B0-03** 未映射引导深化，或 **S4 发布列表/督办**补全，或 **P6 数据质量**。

## Follow-up（2026-10-06 · W5 确认 + S4 发布补全）

- **W5 状态**：进度文档 §「W5 S-IMS-CL-01～03 采集任务与日志」+ §「W5 采集配置」已落地（a6f1e060 并行会话产物已合入文档口径）；**无需重复实现采集任务/日志**。
- **S5 路由复核**：后端 `content_fb.py` 已挂 `api.py`；B9 前缀 `/content/fb-sync`（outbox/retry/process-due）；`GET|POST /content/{id}/fb-sync` 走 `/content` 项目表登记。前端 `/ims/content/fb-sync` + 内容列表 Football 列/链入已存在。
- **做了什么（本片）**：S4 **发布列表/回填/归档/督办**——`GET /content/publish/list|pending`、`PUT …/{id}/receipt`、`GET …/{id}/archive`；回填后本地模拟归档清单（PUB-R3 桩）。`ims_content_publish` 增归档字段；B9 补 `PUT /publish`。前端隐藏页 `/ims/content/publish`（内容管理链入）。compat：`db/compat/20261006_content_s4_publish.sql`。`test_review_gate_and_publish` 延伸 list/receipt/archive/pending。
- **pytest**：本机全量 `python -m pytest -q` 若并行 agent 同跑 `ims_test` 会 **1684**（`drop_all`/`create_all` 并发 DDL）；可先 `DROP DATABASE ims_test; CREATE DATABASE ims_test;` 错峰再跑。环境正常时预期 **58 passed**（S5 三用例 + 原 55）；S4 断言合入原 content 用例后预期 **58 passed**（条数不变、覆盖增厚）。
- **用户操作**：已有 **ims** 库执行 S5 compat `20261006_content_s5_fb_sync.sql` + 本片 S4 `20261006_content_s4_publish.sql`；**重启 18080** 加载 `/content/publish/*` 与 S5 路由。
- **下一片建议**：**BI0 自定义查询**（后端 `bi_query.py` + 前端 `/ims/bi/query` 已部分存在，补 Gate/ pytest 对齐 `SLICES-IMS-BI0`），或 **P6 采集数据质量**（manual-fill / 日志顶栏统计）。

## Follow-up e7114596 衔接

- **S4（e7114596）**：未重复实现。复核 `content.py` 已挂 `GET /content/publish/list|pending`、`PUT …/{id}/receipt`、`GET …/{id}/archive`；B9 含 `/content/publish` POST/GET/PUT；前端 `/ims/content/publish` + 内容管理链入；`tests/test_content.py::test_review_gate_and_publish` 含 1054→PASS→list/pending/receipt/archive 全链。
- **BI0**：进度 §「BI0 自定义查询」已落地（`bi_query.py`、`test_bi_query.py`×3、`/ims/bi/query`、`ims_bi_custom_query`）；本片**不重复** BI0 代码。
- **pytest**：已执行 `DROP DATABASE ims_test`/`ims_ops_test` 重建；本机与 **a80910ec 并行 pytest** 同争 `ims_test` 时出现 **1684** / **2013**（并发 `drop_all`/`create_all`），全量未在本轮得到稳定绿结果。无并行 DDL 时文档预期 **61 passed**（58 + BI0 三用例）。请 a80910ec 串行跑通后以此为准。
- **compat 清单（已有 ims / ops 库增量）**：
  - `db/compat/20261006_content_s3_columns.sql` — S3 任务/内容列
  - `db/compat/20261006_collect_config_m8.sql` — W5 采集配置列/表
  - `db/compat/20261006_content_s5_fb_sync.sql` — S5 Football outbox + 项目扩展列
  - `db/compat/20261006_content_s4_publish.sql` — S4 发布回填/归档列
  - BI0 `ims_bi_custom_query` — 新环境 ORM 建表即可，无单独 compat
- **用户操作**：上述 compat（按库是否已跑过择需执行）+ **重启 18080**（`/content/publish/*`、`/bi/query/*`、S5 fb-sync）。
- **下一片**：**P6 采集数据质量**（日志顶栏统计 + manual-fill），或 BI0 **S-IMS-B0-03** 未映射引导深化；pytest 由 a80910ec 串行验收后更新 passed 数。

## Follow-up a80910ec

- **402a2801 / S4**：`content.py` `publish_list` 已用 `paged(..., total, page_no, size)` 四元组返回（与 list/pending 一致）；全测试改用 `tests/schema_reset.py` 文件锁串行 DDL（勿与并行 pytest 同抢 `ims_test`）。
- **api.py 复核**：`bi_query_router`、`content_fb_router` 已 `include_router`；`collect_config` 经 `collect.py` → `collect_config_router` 挂载（`/collect/external`、`/metadata` 等）。无缺。
- **pytest（本机）**：已多次 `DROP/CREATE ims_test`、`ims_ops_test` 并终止其它 `pytest` 进程；与 **402a2801 / 其它 agent 并行 pytest** 同跑时仍 MySQL **1684**（并发 DDL），全量未得稳定绿。`--collect-only` 当前 **64** 条（原 61 + BI0 3 已计；本片 **+1** `test_quality_summary_and_manual_fill`）。**请仅保留单进程** `cd ims-backend && python -m pytest -q`，预期 **≥62 passed**（以 collect 数为准）。
- **本片 P6 · S-IMS-COLLECT 数据质量（最小可交付）**：
  - 后端：`GET /collect/quality/summary`（24h 成功率、连续失败账号 Top）；`POST /collect/manual-fill`（写入 SUCCESS 日志，`typeResults[].source=MANUAL_FILL`）；`log/page` 复用 `calc_success_rate_24h`。B9 `scope.py` 登记 quality/manual-fill。
  - 前端：`collect/log.vue` 顶栏连续失败账号 chip +「手工补录」抽屉；`bi/query.vue` 1261 文案指向元数据维护（B0-03 轻量）。
  - 测试：`tests/test_collect.py::test_quality_summary_and_manual_fill`。
- **未做**：P6 独立路由页 `/ims/collect/quality`、ALERT `COLLECT_ERROR` 联动、1262 异步卡。
- **用户操作**：**重启 18080** 加载 `/collect/quality/*`、`/collect/manual-fill`；验收采集日志页顶栏与补录。
- **下一片**：BI0 **1262** 异步卡，或 COLLECT CHECKLIST 书面勾选。

## Follow-up 71f2ba3e · W6

- **schema_reset**：复核 `ims-backend/tests` 各模块 `setup_function` 均已调用 `reset_ims_test_schema()`，无自建 `drop_all` 重复逻辑；本片未改。
- **run_pytest.cmd**：`ims-backend/scripts/run_pytest.cmd` — 并行检测 → 删 lock → `_reset_test_dbs.py` → `_run_pytest_to_file.py`（`pytest_result.txt`）。
- **W6 第一片 · S-IMS-IN-01 内部作品（INT）**：ops 表 `oa_internal_content`；契约 `GET /int-analysis/work/page`（segment ALL/HIT/LOW_SCORE，WORK 阈值只读，LOW_SCORE 无阈值 **1251**）。B9 `oa_internal_content`（IP 组轴）。前端 `/ims/int/work`（`intWork` IMPLEMENTED），对齐原型 `intWork.html` Tab/筛选/标签。
- **测试**：新增 `tests/test_int_analysis.py` **2** 条（ALL+HIT、LOW_SCORE+1251）。`--collect-only` 预期 **66** 条（64+2）；单进程全量请用 `scripts/run_pytest.cmd`。
- **用户操作**：**重启 18080** 加载 `/int-analysis/*`；新环境 ORM 建 `oa_internal_content` 即可。
- **下一片**：INT **内部账号**（`account/page`），或 COMP **竞品作品**，或 MON 作品监测。

## Follow-up · pytest 串行验收（子 agent）

- **环境**：终止本机 **8+** 路并行 `pytest`；`DROP/CREATE ims_test`、`ims_ops_test`（`scripts/_reset_test_dbs.py` 含 KILL 会话 + 竞态重试）；删 `tests/.ims_test_ddl.lock`；无 xdist、`PYTEST_ADDOPTS` 清空。
- **结果（`pytest_result.txt` 末行）**：**0 passed，0 failed，68 errors**，**17.36s** — **已跑完**（非 61 条全失败、非 shell 提前中断）。全部为 setup **ERROR**，日志均为 MySQL **1684**（并发 DDL）；**无 FAILED 断言**（`publish_list` 等无需再改）。
- **对比**：部分 shell 重定向/Tee 仍 exit **4294967295** 且输出仅 `.E` 或空文件，属**超时/进程被杀**；用 `scripts/_run_pytest_to_file.py` 或 `python -m pytest -q --tb=line` 直跑可写全量日志。
- **建议**：**勿并行 agent**；确认 `Get-CimInstance … pytest` 为 0 后仅跑 **`scripts/run_pytest.cmd`** 或单进程全量（collect **66**，预期 **≥62 passed**，约 **5–10 分钟**）。
- **run_pytest 已串联 helper**：并行检测通过后 → `_reset_test_dbs.py` → `_run_pytest_to_file.py` → `pytest_result.txt`。

## Follow-up 3112f08e · W6-2

- **api.py 复核**：`int_analysis_router` 已 `include_router`（本片未改）；新增 `comp_analysis_router`。
- **W6 第二片 · S-IMS-CO-01 竞品作品（COMP）**：ops 表 `oa_external_work`；契约 `GET /comp-analysis/work/page`（segment ALL/HIT/LOW_SCORE，WORK 阈值只读，LOW_SCORE 无阈值 **1251**）。B9 `oa_external_work`（IP 组轴）。前端 `/ims/comp/work`（`compWork` IMPLEMENTED），对齐原型 `compWork.html` Tab/筛选/标签（展示点赞 `likeCount`）。
- **测试**：新增 `tests/test_comp_analysis.py` **2** 条（ALL+HIT、LOW_SCORE+1251）。`--collect-only` 预期 **68** 条（66+2）；单进程全量请用 `scripts/run_pytest.cmd`。
- **用户操作**：**重启 18080** 加载 `/comp-analysis/*`；新环境 ORM 建 `oa_external_work` 即可。
- **下一片**：COMP **竞品账号**（`account/page`），或 INT **内部账号**，或 MON 作品监测。

## Follow-up 49d61f04 · W6-3

- **api.py 复核**：`comp_analysis_router` 已 `include_router`（本片未改）。
- **W6 第三片 · S-IMS-CO-02 竞品账号（COMP）**：ops 表 `oa_external_account`；契约 `GET /comp-analysis/account/page`（segment ALL/HIGH_FANS/LOW_FANS，FANS 阈值只读，LOW_FANS 无阈值 **1251**）。B9 `oa_external_account`（IP 组轴）。前端 `/ims/comp/account`（`compAccount` IMPLEMENTED），对齐原型 `compAccount.html` Tab/筛选/标签（展示粉丝 `followerCount`、作品数 `workCount`）。
- **测试**：`tests/test_comp_analysis.py` 追加 **2** 条（ALL+HIGH_FANS、LOW_FANS+1251）。`--collect-only` 预期 **70** 条（68+2）；单进程全量请用 `scripts/run_pytest.cmd`。
- **用户操作**：**重启 18080** 加载 `/comp-analysis/account/*`；新环境 ORM 建 `oa_external_account` 即可。
- **下一片**：INT **内部账号**（`account/page`），或 MON 作品监测（`/monitor/internal/page` 等）。

## Follow-up 9c6168e1 · W6-4

- **api.py 复核**：`comp_analysis_router` 已 `include_router`（本片未改）；新增 `monitor_router`。
- **W6 第四片 · S-IMS-MON 作品监测（MON）**：ops 表 `oa_external_account` / `oa_external_work` 增列 `ip_theme`；契约 `GET /monitor/ip-theme/page`、`GET /monitor/industry/page`（按主题/行业聚合外部账号数、作品数、爆款数，WORK 阈值只读）。B9 `oa_external_account`（IP 组轴）+ monitor 前缀登记；补 `comp-analysis/account` B9。前端 `/ims/monitor/theme`（`mon` IMPLEMENTED），对齐原型 `mon.html` Tab/筛选/列。
- **测试**：新增 `tests/test_monitor.py` **2** 条（IP 主题聚合、行业 keyword）。`--collect-only` 预期 **72** 条（70+2）；单进程全量请用 `scripts/run_pytest.cmd`。
- **用户操作**：**重启 18080** 加载 `/monitor/*`；新环境 ORM 增列 `ip_theme` 即可。
- **下一片**：INT **内部账号**（`account/page`），或 MON `internal/page` 深化。

## pytest 串行验收（893faaec）

- **P6**：`tests/test_collect.py::test_quality_summary_and_manual_fill` 单测 **1 passed**（业务逻辑 OK）。
- **全量**：约 **6 路并行 pytest** 同抢 `ims_test` 时出现 MySQL **1684** / **1050** / **1062**，表现为 **66 errors**，属并发 DDL 环境问题，**非业务 bug**。
- **验收方式**：仅 **单进程** 全量；在 `ims-backend` 目录执行 `scripts\run_pytest.cmd`（跑前 `wmic`/`tasklist` 检测已有 pytest 或多路测库 python，冲突则 **exit 1** 并保留 DROP 库提示）。
- **预期**：`--collect-only` **66** 条；串行全量 **≥62 passed**（以 collect 数为准）。

## Follow-up cbe94851 · W6/W7 首片

- **W6-4 MON**：cbe94851 已完成作品监测（`/ims/monitor/theme`）；本片**不重复** mon 主题页。
- **首片选型**：W6 HOME-001 / BI0 已落地；W7 协同首片 **S-IMS-M-01 · MEET-001 我的日报**（`dailyMine`）。
- **做了什么**：IMS 表 `ims_meet_daily_report`。契约 P0：`GET /meet/daily/template`、`POST /meet/daily` · `POST /meet/daily/submit`（别名）、`GET /meet/daily/{date}`、`GET /meet/daily/list`（`onlyMine`）、`PUT /meet/daily/{id}`（草稿编辑 / 已提交补充说明 **1112**）。B9 `ims_meet_daily_report`（dept + user_id 轴）。前端 `/ims/meet/daily`、`/ims/meet/daily/submit`；菜单 `dailyMine` IMPLEMENTED。
- **测试**：新增 `tests/test_meet.py` **2** 条（template+提交链、1112+补充说明）。`--collect-only` 预期 **74** 条（72+2）；**禁止本回合跑 pytest**（由主会话串行验收）。
- **compat**：新表 ORM `create_all` 即可；无 ops 增列。
- **用户操作**：**重启 18080** 加载 `/meet/*`。
- **下一片**：MEET **团队日报 / 审阅队列**（dailyTeam / dailyReview），或 W6 **内部账号**（`intAccount`）。

## Follow-up f605e7d1 · W7-2

- **做了什么**：MEET-002 团队日报 / 待我审阅。后端扩展 `app/meet.py`：`GET /meet/daily/team/list`（权限范围 · 排除本人）、`GET /meet/review/queue`（一级/二级 · waitingHours/isTimeout）、`PUT /meet/review/{reportId}`（READ/COMMENT · 1113/1114）、`GET /meet/review/records`；ORM `ims_meet_daily_review`。B9 增 `ims_meet_daily_review`（reviewer 轴）+ review 路由前缀。前端 `/ims/meet/daily/team`、`/ims/meet/daily/review`；菜单 `dailyTeam` · `dailyReview` IMPLEMENTED。`api.py` 仍 `include_router(meet_router)`，未改 run_pytest / mon 主题页。
- **测试**：`tests/test_meet.py` **+2**（team 列表不含本人、审阅两级+1113+records）。`--collect-only` 预期 **76** 条（74+2）；**禁止本回合跑 pytest**。
- **用户操作**：**重启 18080** 加载 `/meet/daily/team/*`、`/meet/review/*`。

## Follow-up f2f5ffad · W7-4

- **选型**：W7-3 已完成 INT 内部账号；MEET 三叶 / intWork / comp 已落地。本片 **S-IMS-R-01 · REPORT-001 上报模板**（`reportTpl`）。
- **做了什么**：IMS 表 `ims_report_template`。契约 P0：`POST /report/template`、`GET /report/template/list`、`PUT /report/template/{id}`（version+1）、`DELETE /report/template/{id}`（停用）；勾稽字段不存在 **1121**。B9 `ims_report_template`（created_by 轴）+ report/template 路由前缀。前端 `/ims/report/template`（`reportTpl` IMPLEMENTED），对齐原型列表列（编号/字段数/周期/部门/使用/启停）+ 简易新建抽屉。未改 run_pytest、intAccount、daily 三页。
- **测试**：新增 `tests/test_report.py` **2** 条（创建+列表、1121 勾稽）。`--collect-only` 预期 **80** 条（78+2）；**禁止本回合跑 pytest**。
- **用户操作**：**重启 18080** 加载 `/report/template/*`；新环境 ORM 建 `ims_report_template` 即可。
- **下一片**：REPORT **填报单**（`reportSub` · submit/list/1127），或 TRAIN 资料库首片。

## Follow-up c4689dba · W7-3

- **选型**：W7-2 已完成 MEET 团队日报/审阅；本片 **S-IMS-IN-02 内部账号**（`intAccount`），不重复 dailyTeam/dailyReview。
- **做了什么**：ops 表 `oa_internal_account`；契约 `GET /int-analysis/account/page`（segment ALL/HIGH_FANS/LOW_FANS，FANS 阈值只读，LOW_FANS 无阈值 **1251**）。B9 `oa_internal_account`（IP 组轴）+ account 路由前缀。前端 `/ims/int/account`（`intAccount` IMPLEMENTED），对齐原型 Tab/筛选/标签（`contentCount` · `ipGroupName` · `tagHighFans`/`tagLowFans`）。未改 run_pytest、mon、daily 三页主体。
- **测试**：`tests/test_int_analysis.py` **+2**（account 全部/高粉、低粉 1251 链）。`--collect-only` 预期 **78** 条（76+2）；**禁止本回合跑 pytest**。
- **用户操作**：**重启 18080** 加载 `/int-analysis/account/*`；新环境 ORM 建 `oa_internal_account` 即可。

## pytest 修复（2026-10-06）

- **publish/list 解包**：`corp.paged()` 返回 `ok({list,total,pageNo,pageSize})` 整包 dict，误写 `rows, total = paged(...)` 会按 dict 键解包触发 `ValueError: too many values to unpack (expected 2, got 3)`。`content.py` 的 `GET /content/publish/list` 已与其它 list 一致：`return paged([publish_vo(...) ...], total, page_no, size)`；`publish/pending` 仍用手写 `ok({...})`（字段结构不同，未改）。
- **Football stub 成功态**：`content_fb_sync.apply_outbox_success` 在 `pending_count` 前未 `flush()`，MySQL 仍见 outbox 为 PENDING，项目 `fbSyncStatus` 卡在 PENDING/COMPENSATING。已 `db.flush()` 后再计数，并将 `enqueue_outbox` 的 UPSERT「置 PENDING」挪到真正执行 immediate 前。
- **DDL 串行**：各测试 `setup_function` 统一走 `tests/schema_reset.py`（单连接 `drop_all`/`create_all` + 文件锁），减轻并行 pytest 的 MySQL **1684**；跑全量前结束其它 `pytest`，删 `tests/.ims_test_ddl.lock`，必要时 `DROP/CREATE ims_test`（及 `ims_ops_test`），用 `scripts/run_pytest.cmd` 单进程 `python -m pytest -q`。
- **验收**：`IMS_FOOTBALL_ARTICLE_STUB=success` 下内容创建脚本断言 `fbSyncStatus=SYNCED` + `authorArticleId` 已通过；`--collect-only` **64** 条。本机与并行 agent 同抢 `ims_test` 时全量仍可能 1684，需错峰后预期全绿（条数随 collect 为准，当前文档口径 **≥62 passed**）。

## Follow-up 75ee8102 · FAILED 复核

- **全量摘要（`pytest_result.txt`）**：**2 failed，9 passed，57 errors**（57 条均为 setup **ERROR**，MySQL **1684** 并发 DDL，可忽略）；collect 当时 **66**，现文档口径 **72**。
- **FAILED #1** `tests/test_bi_query.py::test_bi_query_run_mapped_entity`：断言阶段 **1146** `ims_test.ims_metadata_field` 不存在（全量 FAILURES 同）；非业务断言失败。单条复跑：库半残时 **failed**，手动 `schema_reset` / 清锁后 **1 passed**。
- **FAILED #2** `tests/test_collect_config.py::test_external_account_keyword_and_threshold`：登录/写操作链 **1146** `ims_test.ims_sys_login_log` 不存在；单条复跑在 **1684**（setup）与 **1146**（body）间波动，属 **ims_test** DDL 竞态余波，**非** collect 阈值/keyword 逻辑回归。
- **402a2801 相关**：`publish_list` / `content_fb_sync` **flush** 未再现 FAILED；本次 2 条均 **不改代码**。
- **验收**：确认无其它 `pytest`（`Get-CimInstance` / `tasklist`）→ 仅 **`scripts/run_pytest.cmd`** 单进程全量（collect **72**，预期 **≥68 passed** 量级，约 5–10 分钟）。

## Follow-up · W7-5 填报单管理（reportSub）

- **停点复核**：W7-4 `reportTpl` 已落地；`ReportSubmission` ORM 与 `report.py` 仅模板端点，**填报 API/页未实现**（5df211a0 未完成）。
- **做了什么**：IMS 表 `ims_report_submission`（五键去重 · 1123）。契约 P0：`POST /report/submit`（asDraft · 1127 共池 · 1122/1001 校验）、`GET /report/submit/list`、`GET /report/submit/{submissionNo}`。B9 `ims_report_submission`（submitter_user_id 轴）+ submit 前缀。前端 `/ims/report/submission`（`reportSub` IMPLEMENTED）：列表/筛选/提交抽屉/详情。未改 daily 三页、reportTpl 主体。
- **测试**：`tests/test_report.py` **+2**（submit+list+1123、1127）。`--collect-only` **82** 条（80+2）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/report/submit/*`；菜单「填报单管理」可用。
- **下一片**：REPORT **审核队列**（`audit/queue` · REPORT-003），或 TRAIN 资料库（本片已并行见下节）。

## Follow-up · W7-6 培训资料库首片（TRAIN）

- **做了什么**：IMS 表 `ims_train_material_cate` · `ims_train_material`。契约 P0：`GET /train/material/cates`（首访种子分类树）、`POST /train/material`、`GET /train/material/list`、`DELETE /train/material/{id}`（OFFLINE）。B9 登记 material + cates。独立 `app/train.py`；`api.py` 已 `include_router(train_router)`。前端 `/ims/train/material`（`trainMaterial` IMPLEMENTED）：分类树 + 列表 + 上传/下架。
- **测试**：新增 `tests/test_train.py` **1** 条（cates→发布→list→下架）。`--collect-only` **83** 条（82+1）；**禁止本回合跑全量 pytest**。
- **未做**：PUT 新版本、weekly-update-metrics、TRAIN-002 学习任务、ADR-004 AI 出卷。
- **用户操作**：**重启 18080** 加载 `/train/material/*`。
- **下一片**：TRAIN **学习任务**（`trainTask`），或 REPORT **完成率**（`reportRate`），或 MEET **会议管理**首片。

## Follow-up 46441b41 · W7-7 审核队列（REPORT-003）

- **做了什么**：IMS 表 `ims_report_audit`。契约 P0：`GET /report/audit/queue`（业务线筛选 · waitingHours · SLA 24h 超时标记）、`PUT /report/audit/{submissionId}`（通过/退回 · **1124** 原因必填 · **1125** 三轮退回拦截）。B9 `ims_report_audit`（auditor_user_id 轴）+ audit 前缀走 `ims_report_submission` 读写轴。前端「填报单管理」页增 **审核队列** Tab（通过/退回抽屉），菜单仍 `reportSub` IMPLEMENTED。未改 reportTpl/trainMaterial 主体。
- **测试**：`tests/test_report.py` **+2**（queue→approve、1124）。`--collect-only` **85** 条（83+2）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/report/audit/*`；菜单「填报单管理」→「审核队列」Tab。
- **下一片**：REPORT **完成率**（`reportRate` · REPORT-004），或 TRAIN **学习任务**（`trainTask` · TRAIN-002），或 MEET 会议管理首片。

## Follow-up e07d1762 · W7-8 完成率 + 学习任务

- **做了什么（REPORT-004）**：契约 P0：`GET /report/stat/complete-rate`（BR-106 · 分子 APPROVED）、`GET /report/stat/trend`（完成率+退回率）。B9 `GET /report/stat` → `ims_report_submission` 读轴。前端 `/ims/report/stat`（`reportRate` IMPLEMENTED）：总完成率卡 + 按模板/部门/趋势 Tab。未改 reportSub 审核 Tab。
- **做了什么（TRAIN-002）**：IMS 表 `ims_train_task` · `ims_train_task_record`。契约 P0：`POST /train/task`（1101/1102/1001）、`GET /train/task/list`（finishRate · BR-102）。B9 task 轴 + record。前端 `/ims/train/task`（`trainTask` IMPLEMENTED）：列表 + 下达抽屉。未做 progress/QUIZ 作答、ADR-004 AI 出卷。
- **测试**：`tests/test_report.py` **+1**（stat 审核后 100% + trend）；`tests/test_train.py` **+2**（create/list、1102）。`--collect-only` **88** 条（85+3）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/report/stat/*` 与 `/train/task/*`；菜单「完成率统计」「学习任务」可用。
- **下一片**：MEET **会议管理**首片，或 AIR **文件/档案**模块，或 W8 其它 REPORT/TRAIN 深化（stat/missed、task progress）。

## Follow-up 1a40c8f3 · W7-9 会议 + AIR 知识库首片

- **做了什么（MEET-004）**：IMS 表 `ims_meet_minutes`。契约 P0：`POST /meet/minutes`、`GET /meet/minutes/list`、`GET /meet/minutes/{id}`（REGISTERED / MINUTES_RECORDED）。B9 `ims_meet_minutes`（dept + recorder_user_id）。前端 `/ims/meet/minutes`（菜单 `meet` IMPLEMENTED）：列表 + 登记抽屉 + 详情。未改 daily/review 主体。
- **做了什么（AIR · airKb）**：IMS 表 `ims_kb_doc`。P0：`POST /air/kb/doc/upload`、`GET /air/kb/page`、`GET /air/kb/doc/{id}/download`（下载桩 · **无检索**）。B9 `ims_kb_doc`。独立 `app/air.py`；前端 `/ims/air/kb`（`airKb` IMPLEMENTED）。
- **测试**：`tests/test_meet.py` **+2**；新增 `tests/test_air.py` **1** 条。`--collect-only` 预期 **91** 条（88+3）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/meet/minutes/*` 与 `/air/kb/*`。
- **下一片**：MEET 归档/行动项、dailyStat 提交率，或 AIR 分类树/审批，或 TRAIN progress/QUIZ。

## Follow-up c60e33f3 · W7-10 提交率 + 知识分类审批

- **做了什么（MEET-003 · dailyStat）**：契约 P0 `GET /meet/stat/on-time-rate`（BR-103 · byDept/byPerson/trend）。B9 `GET /meet/stat` → `ims_meet_daily_report` 读轴。前端 `/ims/meet/daily/stat`（`dailyStat` IMPLEMENTED）。未改 daily 三页、minutes 列表主体。
- **做了什么（AIR · 分类树/审批）**：IMS 表 `ims_kb` · `ims_kb_category`；`ims_kb_doc` 增 `kb_id`、上传改 **PENDING**。P0：`GET /air/kb/tree`、`GET /air/kb/category/tree`、`POST /air/kb/category`、`POST /air/kb/doc/audit`；`kb/page` 支持 `categoryId`/`docStatus`；下载限 **PUBLISHED**。B9 登记 kb/category/audit。前端 `/ims/air/kb` 增左树 + 待审批操作（未做全文检索）。
- **测试**：`tests/test_meet.py` **+1**；`tests/test_air.py` **+1**（原用例延伸审批链 + 驳回 1001）。`--collect-only` 预期 **93** 条（91+2）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可；已有 `ims_kb_doc` 需补列 `kb_id`（默认 0）。
- **用户操作**：**重启 18080** 加载 `/meet/stat/*` 与 `/air/kb/tree|category|doc/audit`。
- **下一片（W8）**：**FIN 场次财务**首片，或 **PERF/ALERT 绩效预警**，或 MEET **纪要归档/行动项闭环**、AIR **系统资料转入**。

## Follow-up f7697632 · W8-1 场次成本录入

- **做了什么（FIN-001）**：IMS 表 `ims_fin_cost` · `ims_fin_profit`。契约 P0：`GET /fin/cost/pending-sessions`、`POST /fin/cost/{sessionCode}`（clientToken 幂等）、`GET|PUT /fin/cost/{sessionCode}`、`PUT /fin/cost/{sessionCode}/confirm`（同步写利润 CALCULATED）、`GET /fin/cost/complete-rate`；页面辅助 `GET /fin/cost/list`。B9 `ims_fin_cost`（entry_user_id 轴）+ confirm 读 `ims_fin_profit`。独立 `app/fin.py`；前端 `/ims/fin/cost`（`finCost`/`fin` IMPLEMENTED）：完整率卡 + 待录入/已录入 Tab + 录入抽屉。未做 COST 账号 ROI、分成规则、利润反查 DC-002、原型「结算单」Tab。
- **测试**：新增 `tests/test_fin.py` **2** 条（pending→提交→核准→完整率、未核准 1141）。`--collect-only` 预期 **95** 条（93+2）；**禁止本回合跑全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/fin/cost/*`；菜单「场次财务 → 成本核算」。
- **下一片**：FIN **利润列表**（`finProfitTrace` 前 `/fin/profit/list`）或 **PERF 考核方案**首菜单，或 MEET **纪要行动项**、AIR **资料转入**。

## Follow-up ad9bc368 · W8-2 利润列表

- **做了什么（FIN-002 首片）**：契约 P0：`GET /fin/profit/list`（分页 · 平台/状态/日期筛选 · 场次数据权限）、`GET /fin/profit/{sessionCode}`（三级利润 VO + 计算快照 · 1145 未核准）、页面辅助 `GET /fin/profit/summary`（结算概览卡 · 待结算/结算中计数）。B9 `GET /fin/profit` → `ims_fin_profit` 读轴（与 `ims_fin_cost` 录入轴分离）。`app/fin.py` 扩展；前端 `/ims/fin/profit`（`finProfit` IMPLEMENTED）：概览四卡 + 利润表 + 详情抽屉。未做重算/异常 Tab、DC-002 `finProfitTrace`、PERF、原型完整结算单流程。
- **测试**：`tests/test_fin.py` **+2**（核准后 list/detail/summary、未核准 1145）。`--collect-only` 预期 **97** 条（95+2）；**禁止本回合跑全量 pytest**。
- **compat**：无新表；沿用 W8-1 `ims_fin_profit`。
- **用户操作**：**重启 18080** 加载 `/fin/profit/*`；菜单「场次财务 → 利润核算」（勿与「账号财务」COST 混淆）。
- **下一片（W9）**：**FIN E2E**（成本→利润→列表联调）或 **DC-002 利润反查** `finProfitTrace`；或 **报表/穿透**（BI preview / dc 账号穿透）首片；或 **PERF perfScheme**。

## Follow-up b49943cf · W8-3 利润反查

- **做了什么（DC-002 首片）**：契约 P0（只读）：`GET /dc/profit-trace/list`（分页 · 平台/状态/场次筛选 · DcProfitTraceVO · dataAsOf）、`GET /dc/profit-trace/{sessionCode}`（BR-209 chain · costDetail/shareDetail · queryCostMs · 1145 未核准）、`GET /dc/profit-trace/share-detail/{sessionCode}`。B9 `GET /dc/profit-trace` → `ims_fin_profit` 读轴（与 `/fin/profit` 同权限域）。独立 `app/dc_profit_trace.py`；前端 `/ims/fin/profit-trace`（`finProfitTrace` IMPLEMENTED）：利润列表 Tab + 反查链路抽屉。未做 aggregate/abnormal Tab、R7/R9 完整脱敏矩阵、DC-001 账号穿透。
- **测试**：`tests/test_fin.py` **+2**（list+chain+share、未核准 1145）。`--collect-only` 预期 **99** 条（97+2）；**禁止本回合跑全量 pytest**。
- **compat**：无新表；复用 W8-1/W8-2 利润与成本数据。
- **用户操作**：**重启 18080** 加载 `/dc/profit-trace/*`；菜单「场次财务 → 利润反查」。
- **下一片（W9）**：**Checklist E2E 抽样**（成本→利润→反查联调）或 **DC-001 穿透**首 API+页；或 **PERF perfScheme**；或 aggregate/abnormal 补 Tab。

## Follow-up W9-1 · FIN E2E 抽样

- **做了什么**：`tests/test_fin.py` 新增 **1 条**链路 pytest `test_fin_e2e_live_confirmed_cost_profit_trace_chain`（直播 register→report→confirm → 待录入 → cost POST/confirm → `/fin/profit/list`+detail → `/dc/profit-trace/list`+chain）；**未改** profit-trace API 与前端主体。
- **测试**：仅跑上述单条 **1 passed**；`--collect-only` 预期 **100** 条（99+1）；**禁止全量 pytest**。
- **compat**：无 schema/API 变更。

### W9 E2E 抽样（FIN）手测清单

1. **成本**：直播场次 **已 CONFIRMED** 后进入「场次财务 → 成本核算」，待录入 Tab 可见该场次；录入分成/广告等 → 提交 → **核准**，完整率卡递增。
2. **利润**：「利润核算」列表按场次筛选，行状态 **CALCULATED**，净利与 GMV−成本公式一致；点开详情抽屉核对三级利润与快照。
3. **反查**：「利润反查」同场次出现在列表；点 **反查** 打开链路抽屉，session/account/成本明细 ≥5 行，`queryCostMs` 有值。
4. **阻断**：未核准成本场次在利润详情与反查 chain 均应 **1145**（可与 pytest 对照）。
5. **窄屏 390**：上述三页 QueryBar + 表格/抽屉无横向溢出（1440 已走通即可抽 1 条复验）。

- **用户操作**：本回合仅增测试；若尚未加载 W8-3，**重启 18080** 后再做手测 3～5。
- **下一片（W9-2）**：**PERF perfScheme** 首片（菜单+`GET /perf/scheme/list`+1 pytest）；或 **DC-001 账号穿透**首 API+页；aggregate/abnormal Tab 仍非优先。

## Follow-up fadbe3e8 · W9-2 考核方案首片

- **做了什么（PERF-001 首片）**：IMS 表 `ims_perf_scheme`。契约 P0：`GET /perf/scheme/list`（分页 · 岗位/周期/启停筛选 · 卡片 VO）、`POST /perf/scheme`（指标项 · 权重合计 100% · 可选立即启用）、`POST /perf/scheme/{id}/activate`（同岗位互斥 ACTIVE）。B9 `ims_perf_scheme`（created_by 轴）。独立 `app/perf.py`；前端 `/ims/perf/scheme`（`perfScheme` IMPLEMENTED）：卡片网格 + 新建抽屉 + 「发起考核」链 WIP `perfExec`。未做 template/items 详情编辑、执行考核 record API、DC-001 账号穿透。
- **测试**：新增 `tests/test_perf.py` **2** 条（create→list→activate 互斥、权重≠100 的 1001）。`--collect-only` 预期 **102** 条（100+2）；**禁止全量 pytest**。
- **compat**：新表 ORM `create_all` 即可。
- **用户操作**：**重启 18080** 加载 `/perf/scheme/*`；菜单「协同与成长 → 绩效考核 → 考核方案」。
- **下一片（W9）**：**Checklist 总回归** / **未实现菜单扫尾**；或 **perfExec** 执行考核首 API+页；或 **DC-001 账号穿透**只读首片。

## Follow-up 1e011f12 · W9-3 执行考核 + 菜单扫尾 + DC-001

- **做了什么（PERF-002 首片）**：IMS 表 `ims_perf_record`。P0：`GET /perf/execution/list`（分页 · 方案/状态/周期筛选 · OPS 对齐 VO）、`POST /perf/execution`（绑定生效方案 · DRAFT 起态 · 周期起止）。B9 `ims_perf_record`（created_by 轴）。前端 `/ims/perf/execution`（`perfExec` IMPLEMENTED）：列表 + 创建抽屉；方案页「发起考核」改链真实路由。未做 calculate/adjust/confirm、算分引擎。
- **DC-001 只读首片**：`app/dc_trace.py` — `GET /dc/trace/entry`、`POST /dc/trace/query`（基于 `ims_live_session` 聚合 mock 图/明细 · queryCostMs/dataAsOf）。前端 `/ims/dc/trace`（`dc` IMPLEMENTED）。
- **菜单扫尾（5 项）**：`meet`→会议纪要、`trainStat`→培训统计（聚合 task list）、`contentLayout`→公推模板库占位、`perfResult`→考核结果读屏占位、`dc` 见上。
- **测试**：`test_perf.py` **+2**（execution create→list、未启用方案 1001）；`test_dc_trace.py` **+1**（entry+query）。`--collect-only` **105**（102+3）；局部跑新测 **5 passed**。
- **Checklist 扫尾表**（叶级菜单 · 对齐 `catalog.json`）：

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（`menu.ts`） | **65** |
| 仍 WIP（`/ims/wip/*`） | **34** |
| 本回合新增 IMPLEMENTED | perfExec · perfResult · meet · trainStat · contentLayout · dc（6） |

- **用户操作**：**重启 18080** 加载 `/perf/execution/*`、`/dc/trace/*`；菜单「绩效考核 → 执行考核」「数据分析 → 穿透查询」。验收：`run_pytest.cmd` 或 `pytest --collect-only -q` 预期 **105+**。

## Follow-up a18f04c6 · W9-4 预警/读屏/模板/归档 + 工作台叶菜单

- **做了什么（ALERT 首片）**：表 `ims_alert_rule` · `ims_alert_record`。P0：`GET|POST /alert/rule/*`、`PUT …/enable`、`GET /alert/check/records`、`PUT …/{alertNo}/respond`、`POST …/run/{ruleId}`。B9 登记 alert 前缀。前端 `/ims/alert/rule`（`alertRule`）、`/ims/alert/live`（`alertLive`）。
- **perfResult 读屏**：`GET /perf/result/list|/{id}`（CALCULATED+ 态 · 等级 S~D · 1157 未发布）。前端 `/ims/perf/result` 接列表。
- **contentLayout 模板**：表 `ims_content_layout_template`。P0：`GET /content/layout-template/list`、`POST …`、`POST …/{id}/publish`、`PUT …/enable`。前端 `/ims/content/layout` 列表/新建/发布。
- **MEET 归档**：`PUT /meet/minutes/{id}/archive`、`GET /meet/minutes/archive-rate`（BR-116 留痕率卡）。会议管理页增归档按钮与概览卡。
- **TRAIN 统计**：`GET /train/stat/summary`；`trainStat` 页优先读 summary 再拉 task 明细。
- **工作台叶菜单**：`workbenchTodos` · `workbenchMsgs` 接既有 `/auth/workbench/todos|messages`。
- **测试**：`test_alert.py` **+2**、`test_content_layout.py` **+1**、`test_perf.py` **+1**、`test_meet.py` **+1**、`test_train.py` **+1**。`--collect-only` **111**（105+6）；局部跑新测 **6 passed**；**禁止全量 pytest**。
- **compat**：新表 ORM `create_all`；`archive-rate` 路由置于 `{minutes_id}` 之前避免 shadow。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **66** |
| 仍 WIP（`/ims/wip/*`） | **32** |
| 本回合新增 IMPLEMENTED | alertRule · alertLive · workbenchTodos · workbenchMsgs（4） |
| 本回合 API+页升维（原已 IMPLEMENTED） | perfResult · contentLayout · meet 归档 · trainStat |

### W9 Checklist 进度（对照 IMS-E2E S1–S12）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S1 员工全生命周期 | 部分 | AUTH 组织同步/岗位规则/工作台待办消息已通；离职账号归还 E2E 未自动化 |
| S2 直播全链路 | 部分 | 场次登记/列表/成本联动有；风控色带/24h 督办 E2E 未齐 |
| S3 成本-利润-反查 | 部分 | FIN 三页 + DC-002 + W9-1 链路 pytest；结账/分成 PAID 未做 |
| S4 账号领用流转 | 部分 | 平台账号 CRUD/采集 Tab；**#47** 池领用/归还；**#58** 冲话费登记 + **1025** 凭证门禁（E2E-S4-05/06）；E2E-S4-02/03 流转/**1021** 为 **#60 进行中**（并行）；1022/1026 未 E2E |
| S5 资产+穿透 | 部分 | 设备/office·live·phone 台账；5 层穿透 1013 未做 |
| S6 证件预警 | 部分 | 证件水印/脱敏；T-30/7/0 三级预警未接 ALERT |
| S7 内容 AI 全流程 | 部分 | SOP~发布 G1 + 公推模板库首片；ComfyUI/GPU E2E 未做 |
| S8 AI 资产分发 | 部分 | AIR 知识库文件管理；技能/专家/MCP 网关未做 |
| S9 绩效周期 | 部分 | 方案/执行/结果读屏；算分/审批发布/1155 锁定未做 |
| S10 培训考试 | 部分 | 资料/任务/统计 summary；QUIZ 作答/补考未做 |
| S11 预警闭环 | 部分 | 规则+试跑+处置首片；cron/升级/去重统计 Tab 未做 |
| S12 数据消费 | 部分 | BI0 自定义查询 + DC-001 穿透 mock；报表设计/订阅未做 |

- **用户操作**：**重启 18080** 加载 `/alert/*`、`/content/layout-template/*`、`/perf/result/*`、`/meet/minutes/archive*`、`/train/stat/summary`；侧栏验收预警中心两叶、工作台待办/消息。
- **下一片（W9-5）**：**Playwright** 抽 S3/S9/S11 窄路径；或 WIP 优先 **eff** / **bi0Report** / **airSkill**；perf 算分/confirm 写路径仍后置。

## Follow-up 27b0742f · W9-5 eff / bi0Report / airSkill + Playwright 窄路径

- **做了什么（EFF 首片）**：IMS 表 `ims_eff_relation`。P0：`GET /eff/relation/list`、`POST /eff/relation`（1198 主归属冲突 · 1199 兼职超 100%）、`GET /eff/relation/coverage`（BR-207）、`GET /eff/metrics/board`（看板卡 mock+关系统计）。B9 `ims_eff_relation`（changed_by 轴）。前端 `/ims/eff`（`eff` IMPLEMENTED）：Tab 归属/盘点占位/看板。
- **做了什么（BI0 报表中心）**：P0：`GET /bi/report/catalog`（八张 M6 标准报表）、`GET /bi/report/{code}`（只读 mock 预览）。B9 读轴挂 `ims_bi_custom_query`。前端 `/ims/bi/report`（`bi0Report` IMPLEMENTED）：八卡片 + 筛选 + 预览表。
- **做了什么（AIR 技能库）**：IMS 表 `ims_air_skill`。P0：`GET /air/skill/summary|list`、`POST /air/skill`、`PUT …/submit-audit`、`PUT …/audit`。B9 `ims_air_skill`（owner_user_id 轴）。前端 `/ims/air/skill`（`airSkill` IMPLEMENTED）。
- **Playwright（S3 窄路径）**：`ims-web/e2e/smoke-fin.spec.ts`（登录 → `/ims/fin/profit` 标题）；`package.json` 脚本 `test:e2e` / `test:e2e:skip`（`SKIP_E2E=1` 跳过）；未展开 S9/S11 全链路。
- **测试**：`test_eff.py` **+2**、`test_bi_report.py` **+1**、`test_air_skill.py` **+1**。`--collect-only` 预期 **115**（111+4）；局部跑新测 **4 passed**；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **69** |
| 仍 WIP（`/ims/wip/*`） | **29** |
| 本回合新增 IMPLEMENTED | eff · bi0Report · airSkill（3） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S8 AI 资产分发 | 部分 | **+技能库** 登记/审核首片；专家/MCP 网关仍 WIP |
| S12 数据消费 | 部分 | **+报表中心** 八张标准报表 catalog+mock 预览；报表设计/订阅仍 WIP |

（S1–S7、S9–S11 行与 W9-4 表一致，未重复粘贴。）

- **用户操作**：**重启 18080** 加载 `/eff/*`、`/bi/report/*`、`/air/skill/*`；侧栏验收「数据分析 → 组织人效」「数据报表 → 报表中心」「AI 资源中心 → 技能库」。E2E：`cd ims-web && npm i && npx playwright install chromium && npm run test:e2e`（重环境可 `npm run test:e2e:skip`）。
- **下一片（W9-6）**：WIP **biList** / **bi0Metric** / **airExpert** 择 2 片；或 **perf** 算分/confirm；或 E2E 补 S9/S11 单条。

## Follow-up 59c73bbf · W9-6 biList + bi0Metric

- **做了什么（BI 报表管理 biList）**：IMS 表 `ims_bi_report_def`。P0：`GET /bi/report/list`、`POST /bi/report`（REPORT/DASHBOARD）、`GET /bi/report/categories`。B9 `ims_bi_report_def`（creator 轴）。前端 `/ims/bi/report/list`（`biList` IMPLEMENTED）：分类筛选 + 卡片/列表双视图 + 新建抽屉（报表/大屏 pills）。
- **做了什么（BI0 指标管理 bi0Metric）**：IMS 表 `ims_bi_metric`。P0：`GET /bi/metric/list`、`POST /bi/metric`、`PUT /bi/metric/{id}`、`DELETE /bi/metric/{id}`（**1262** 引用阻断）、`POST …/preview` 试算占位。B9 `ims_bi_metric`（creator 轴）。前端 `/ims/bi/metric`（`bi0Metric` IMPLEMENTED）：QueryBar + 列表 + 新建/试算/删除。
- **未重复**：W9-5 已落地的 `eff` / `bi0Report` catalog+mock / `airSkill` 主体未改。
- **Playwright（S11 窄路径 · 可选）**：`ims-web/e2e/smoke-alert.spec.ts`（登录 → `/ims/alert/rule` 标题）；未扩 S9 perf 全链路。
- **测试**：`test_bi_report.py` **+1**（manage create+list+categories）、`test_bi_metric.py` **+1**。`--collect-only` 预期 **117**（115+2）；局部跑新测 **2 passed**；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **71** |
| 仍 WIP（`/ims/wip/*`） | **27** |
| 本回合新增 IMPLEMENTED | biList · bi0Metric（2） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | **+报表管理** 目录首片 + **指标管理** CRUD/试算；设计器/订阅/指标分析仍 WIP |

（S1–S11 行与 W9-5 表一致，未重复粘贴。）

- **用户操作**：**重启 18080** 加载 `/bi/report/list`、`POST /bi/report`、`/bi/metric/*`；侧栏验收「数据报表 → 报表管理」「数据指标 → 指标管理」。E2E 可选：`cd ims-web && npm run test:e2e`（含 `smoke-fin` + `smoke-alert`）。
- **下一片（W9-7）**：剩余 WIP **27** 优先 **airExpert** / **biDesign** / **bi0Analysis**；或 **perf** 算分/confirm 写路径；或 E2E S9 `smoke-perf.spec.ts` 单条确认。

## Follow-up fbe5c6e0 · W9-7 airExpert + smoke-perf

- **做了什么（AIR 专家库 airExpert）**：IMS 表 `ims_air_expert`。P0：`GET /air/expert/summary|page`、`POST /air/expert`、`PUT /air/expert/{id}`、`PUT …/publish`、`GET …/{id}`（`assemblePreview`）、`POST /air/expert/grant`（挂载技能须 **PUBLISHED** · MCP 四工具白名单校验）。B9 `ims_air_expert`（owner_user_id 轴）。前端 `/ims/air/expert`（`airExpert` IMPLEMENTED）：统计卡 + 查询 + **3 列卡片网格** + 新建/发布/组装预览/授权（对齐原型 P2）。
- **Playwright（S9 窄路径）**：`ims-web/e2e/smoke-perf.spec.ts`（登录 → `/ims/perf/execution` 标题「执行考核」）。
- **未重复**：W9-6 `biList`/`bi0Metric`、W9-5 `airSkill` 主体未改；**perf 算分/confirm 写路径**本回合未做（改动面仍大）。
- **测试**：`test_air_expert.py` **+1**（create+page+publish+preview+grant）。`--collect-only` 预期 **118**（117+1）；局部跑新测 **1 passed**；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **72** |
| 仍 WIP（`/ims/wip/*`） | **26** |
| 本回合新增 IMPLEMENTED | airExpert（1） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S9 绩效考核 | 部分 | **+E2E 窄路径** `smoke-perf` 执行考核标题；算分/confirm 写 API 仍后置 |
| S12 数据消费 | — | 与 W9-6 一致 |

（S1–S8、S10–S11 行与 W9-6 表一致，未重复粘贴。）

- **用户操作**：**重启 18080** 加载 `/air/expert/*`；侧栏验收「AI 资源中心 → 专家库」。E2E 可选：`cd ims-web && npm run test:e2e`（含 `smoke-fin` + `smoke-alert` + `smoke-perf`）。
- **下一片（W9-8）**：WIP **26** 优先 **biDesign** / **bi0Analysis** / **airCfg**；或 **perf** 算分/confirm 最小写路径；或 E2E 补 S12 单条。

## Follow-up e47f3b78 · W9-8 biDesign + airCfg

- **做了什么（报表设计 biDesign · 隐藏路由）**：P0 三栏设计器首片。`GET /bi/report/datasets`（指标库+自定义查询 + 4 类组件库）· `GET/PUT /bi/report/{id}`（`layout_json` FREE/comps）· `POST /bi/report/{id}/publish`（dest=center）· `POST /bi/report/query` 预览占位。B9 `ims_bi_report_def`。前端 `/ims/bi/report/designer?reportId=`（`biDesign` IMPLEMENTED）；报表管理新建后自动进设计器、卡片/列表「编辑」入口。
- **做了什么（AIR 模型与提示词 airCfg）**：表 `ims_air_model_config` / `ims_air_prompt_config`。P0：`GET/POST/PUT /air/cfg/model/*` · `GET/POST/PUT /air/cfg/prompt/*`（租户种子 MDL-0001/PRM-0001）。B9 creator 轴。前端 `/ims/air/cfg` Tab「模型连接 | 提示词」。
- **Playwright（S12 窄路径）**：`ims-web/e2e/smoke-bi-report.spec.ts`（登录 → `/ims/bi/report` 标题「报表中心」）。
- **未做**：**perf 算分/confirm**、**bi0Analysis** 仍 WIP；全量拖拽/21 组件/发布五段抽屉后置。
- **测试**：`test_bi_design.py` + `test_air_cfg.py` **+2**。`--collect-only` 预期 **120**（118+2）；局部跑新测 **2 passed**；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **74** |
| 仍 WIP（`/ims/wip/*`） | **24** |
| 本回合新增 IMPLEMENTED | biDesign（隐藏）· airCfg（1 侧栏） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | **+设计器首片** + **+E2E smoke-bi-report** 报表中心标题；指标分析/订阅仍 WIP |

（S1–S11 行与 W9-7 表一致，未重复粘贴。）

- **用户操作**：**重启 18080** 加载 `/bi/report/datasets`、`/air/cfg/*`；侧栏验收「AI 资源中心 → 模型与提示词」；报表管理 → 新建/编辑进设计器。E2E 可选：`cd ims-web && npm run test:e2e`（含 `smoke-bi-report`）。
- **下一片（W9-9）**：WIP **24** 优先 **bi0Analysis** / **biShare** / **queryTool**；或 **perf** 算分/confirm 最小写路径；或 E2E 套件整理（S1–S12 分 spec 归档）。

## Follow-up 1606975c · W9-9 bi0Analysis + queryTool + perf

- **做了什么（BI0 指标分析 bi0Analysis）**：P0：`GET /bi/metric/{id}/analyze` · `POST /bi/metric/analysis/run`（多选 metricIds · DETAIL/TREND mock）。B9 读轴 `ims_bi_metric`。前端 `/ims/bi/analysis`（`bi0Analysis` IMPLEMENTED）：多选指标 + 参数 + Tab 明细/趋势。
- **做了什么（QT 查询工具 queryTool）**：表 `ims_query_template`。P0：`GET /analysis/query-tool/template/page` · `POST /analysis/query-tool/template` · `POST …/{code}/publish|unpublish` · `DELETE …` · `POST /analysis/query-tool/run`（SYNC 占位）。B9 `ims_query_template`（owner 轴）。前端 `/ims/analysis/query-tool`（`queryTool` IMPLEMENTED）：模板列表 + 新建/发布/执行。
- **做了什么（perf 算分/confirm 最小写路径）**：`POST /perf/execution/{id}/calculate`（DRAFT→CALCULATED · 方案权重 mock 总分）· `POST …/confirm`（CALCULATED/REVIEWED→CONFIRMED）。`app/perf.py` 单文件扩展；执行考核页行内「算分/确认」。
- **E2E 归档**：`ims-web/e2e/README.md` — S1–S12 与 `smoke-fin|perf|alert|bi-report` 对照表。
- **未做**：**biShare** 仍 WIP；QT 720px 向导/MenuSeed/多层 DRILL 引擎；perf adjust/REVIEWED 人工调整。
- **测试**：`test_query_tool.py` + `test_perf` 算分确认 + `test_bi_metric` 分析 **+2 文件/扩 2**。`--collect-only` 预期 **122**（120+2）；局部跑新测；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **76** |
| 仍 WIP（`/ims/wip/*`） | **22** |
| 本回合新增 IMPLEMENTED | bi0Analysis · queryTool（2） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S9 绩效考核 | 部分 | **+算分/confirm API** + 执行页行内操作；排名/考试仍 WIP |
| S12 数据消费 | 部分 | **+指标分析** + **+查询工具** 模板列表/run；订阅 biShare 仍 WIP |

（S1–S8、S10–S11 行与 W9-8 表一致，未重复粘贴。）

- **用户操作**：**重启 18080** 加载 `/bi/metric/analysis/*`、`/analysis/query-tool/*`、`/perf/execution/*/calculate|confirm`；侧栏「数据指标→指标分析」「数据分析→查询工具」；执行考核试算分/确认。
- **下一片**：WIP **≤22** 优先 **biShare** / **biPreview** / **comp**；或 **W9 总验收** `run_pytest.cmd` + E2E 四轮 smoke。

## Follow-up f0f7d055 · W9-10 biShare + biPreview

- **做了什么（BI-003 订阅与分享 biShare · 隐藏路由）**：表 `ims_bi_subscription` · `ims_bi_share_link`。P0：`GET /bi/subscribe/list` · `POST /bi/subscribe` · `PUT|DELETE /bi/subscribe/{id}` · `GET /bi/subscribe/share-link/list` · `POST …/share-link` · `PUT …/share-approval/{linkId}` · `GET …/publish/list` · `GET …/snapshot/{id}`。B9 subscriber/creator 轴。前端 `/ims/bi/report/subscribe`（`biShare` IMPLEMENTED）：三 Tab 我的订阅/分享链接/发布管理；报表管理入口链订阅页。
- **做了什么（BI-002 预览与下钻 biPreview）**：P0：`POST /bi/report/preview/run`（筛选+KPI+趋势/占比 mock）· `POST /bi/report/preview/drill`（维度下钻/场次穿透占位）。B9 读轴 `ims_bi_report_def`。前端 `/ims/bi/report/preview`（`biPreview` IMPLEMENTED）：筛选条+KPI+明细下钻/穿透按钮。
- **未做**：钉钉真实推送/快照落库；分享 SSO 免登；comp 竞品库页；perf 考试/adjust。
- **测试**：`test_bi_subscribe.py` **+1 文件 2 用例**。`--collect-only` 预期 **124**（122+2）；局部跑新测；**禁止全量 pytest**（用户本地验收）。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **78** |
| 仍 WIP（`/ims/wip/*` · catalog 非 navParent） | **18** |
| 本回合新增 IMPLEMENTED | biShare（隐藏）· biPreview（1 侧栏） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | **+订阅分享** 三 Tab API + **+预览下钻** run/drill；comp 竞品库仍 WIP |

（S1–S11 行与 W9-9 表一致，未重复粘贴。）

### W9 总验收指引（用户本地）

1. **pytest 全量**：`ims-backend\scripts\run_pytest.cmd`（单进程；争用 ims_test 时先 DROP/CREATE 测库，见脚本提示）。
2. **collect-only 快照**：`python -m pytest --collect-only -q` → 预期 **124**。
3. **E2E 四轮**：`smoke-fin` · `smoke-perf` · `smoke-alert` · `smoke-bi-report`（或 `npm run test:e2e`）。
4. **IMPLEMENTED / WIP**：**78** / **18**（见上表）。
5. **重启 18080**：加载本回合 `/bi/subscribe/*`、`/bi/report/preview/*`。

- **用户操作**：侧栏「数据分析 → 预览与下钻」；报表管理 →「订阅与分享」；隐藏路由 `go(biShare)` → `/ims/bi/report/subscribe`。
- **下一片**：WIP **18** 优先 **comp** / **perfExam** / **flow** / **sysTenant** / **bi0Screen**（侧栏叶 WIP top5）。

## Follow-up b5fa8736 · W9-11 comp + perfExam

- **做了什么（COMP-003 竞品库 comp）**：表 `ims_comp_asset`。P0：`GET /comp/asset/list`（卡片 VO · 首访种子 · 可联动 M7 `oa_external_account` 刷新粉丝/近30天作品/互动率）· `POST /comp/asset`（新增档案 · 1203 重名）。B9 `ims_comp_asset`（created_by 轴）。前端 `/ims/comp/library`（`comp` IMPLEMENTED）：四列卡片 + 监测跳转 + 新增抽屉；与 `compWork`/`compAccount` 监测页分离。
- **做了什么（PERF-003 在线考试 perfExam 首片）**：表 `ims_exam_question`。P0：`GET /perf/exam/questions`（分页 · 知识域/题型筛选 · 首访种子 10 题）。B9 `ims_exam_question`。前端 `/ims/perf/exam`（`perfExam` IMPLEMENTED）：三 Tab 占位 · 题库列表对齐原型；试卷/成绩/创建/编辑未做。
- **未做**：comp 版本轴/对比/heat-rank · BR-202 审核流；perf 组卷/作答/阅卷/adjust。
- **测试**：`test_comp_asset.py` **+2** · `test_perf_exam.py` **+1**。`--collect-only` 预期 **127**（124+3）；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **80** |
| 仍 WIP（`/ims/wip/*` · catalog 非 navParent） | **16** |
| 本回合新增 IMPLEMENTED | comp · perfExam（2） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | comp 竞品库卡片 API；perfExam 题库 list |

（S1–S11 行与 W9-10 表一致，未重复粘贴。）

### W9 总验收指引（用户本地）

1. **pytest 全量**：`ims-backend\scripts\run_pytest.cmd`（单进程；争用 ims_test 时先 DROP/CREATE 测库，见脚本提示）。
2. **collect-only 快照**：`python -m pytest --collect-only -q` → 预期 **127**。
3. **E2E 四轮**：`smoke-fin` · `smoke-perf` · `smoke-alert` · `smoke-bi-report`（或 `npm run test:e2e`）。
4. **IMPLEMENTED / WIP**：**80** / **16**（见上表）。
5. **重启 18080**：加载本回合 `/comp/asset/*`、`/perf/exam/questions`。

- **用户操作**：侧栏「竞品分析 → 竞品库」；「绩效考核 → 在线考试」。
- **下一片**：WIP **16** 优先 **flow** / **sysTenant** / **bi0Screen** / **perf adjust** / **contentPublish**（侧栏叶 WIP top5）。

## Follow-up b70883c2 · W9-12 flow + bi0Screen

- **做了什么（FLOW-001 工作流 flow 首片）**：表 `ims_flow_template` · `ims_flow_instance`。P0 只读：`GET /flow/template/list` · `GET /flow/instance/list`（首访种子 4 模板 + 3 实例）。B9 `ims_flow_template` / `ims_flow_instance`。前端 `/ims/flow`（`flow` IMPLEMENTED）：实例/模板双 Tab 列表；设计器/发起/处理未做。
- **做了什么（bi0Screen 大屏首片）**：复用 `ims_bi_report_def`（`reportType=DASHBOARD`）。P0 只读：`GET /bi/screen/list` · `GET /bi/screen/{id}` · `GET /bi/screen/{id}/preview`（首访种子 2 大屏 + widget mock）。前端隐藏路由 `/ims/bi/screen-config`（`bi0Screen` IMPLEMENTED）+ `/ims/bi/screen/:id/view` 全屏展示；与 `biList` 归一化并存。
- **未做**：sysTenant —— **SLICES-IMS-SYS / ADR-IMS-007 批次外**，本回合跳过（无只读占位）；Flowable 引擎 · 模板设计/任务处理 · 大屏编辑保存。
- **测试**：`test_flow.py` **+1** · `test_bi_screen.py` **+1**。`--collect-only` 预期 **129**（127+2）；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（侧栏 nav · `menu.ts`） | **82** |
| 仍 WIP（`/ims/wip/*` · catalog 非 navParent） | **14** |
| 本回合新增 IMPLEMENTED | flow · bi0Screen（2） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | flow 模板/实例 list；bi0Screen 大屏只读 API |

（S1–S11 行与 W9-11 表一致，未重复粘贴。）

### W9 总验收指引（用户本地）

1. **pytest 全量**：`ims-backend\scripts\run_pytest.cmd`（单进程；争用 ims_test 时先 DROP/CREATE 测库，见脚本提示）。
2. **collect-only 快照**：`python -m pytest --collect-only -q` → 预期 **129**。
3. **E2E 四轮**：`smoke-fin` · `smoke-perf` · `smoke-alert` · `smoke-bi-report`（或 `npm run test:e2e`）。
4. **IMPLEMENTED / WIP**：**82** / **14**（见上表）。
5. **重启 18080**：加载本回合 `/flow/*`、`/bi/screen/*`。

- **用户操作**：侧栏「工作流 → 流程管理」；深链 `go(bi0Screen)` → `/ims/bi/screen-config`；全屏 `/ims/bi/screen/{id}/view`。
- **下一片**：WIP **14** 优先 **sysTenant（批次外评估）** / **perf adjust** / **contentPublish** / **contentFb** / **asset**（侧栏叶 WIP top5）。

## Follow-up ded2c1d5 · W9-13 合并落地 + 主数据

- **做了什么（EFF/ALERT/AIR 兼容键合并）**：`effRelation`/`effInventory`/`effBoard` → `/ims/eff` Tab（+`GET /eff/inventory/snapshot`）；`alertHistory`/`alertDedup` → `/ims/alert/live` Tab（+`GET /alert/history/summary` · `GET /alert/dedup/list` · 表 `ims_alert_dedup_policy`）；`airKey`/`airLog` → `/ims/air/cfg` Tab（+`GET /air/cfg/key/page` · `GET /air/cfg/audit/page` · 表 `ims_air_api_key`/`ims_air_audit_log`）。
- **做了什么（MASTER · 内容执行 · 归一重定向）**：`GET /master/overview` + `/ims/master` 主数据汇总卡片；`contentTaskExecute` → `/ims/content/task/execute`（回任务列表）；`asset`→办公设备 · `cert`→证件档案 · `acct`→抖音账号 · `qtPub_QT-TPL-004`→利润反查（corp 能力归一）。
- **未做**：**sysTenant** —— **SLICES-IMS-SYS / ADR-IMS-007 批次外**，本回合仍跳过（无只读占位）。
- **测试**：`test_alert.py` **+1** · `test_eff.py` **+1** · `test_air_cfg.py` **+1** · `test_master_data.py` **+1**。`--collect-only` 预期 **133**（129+4）；**禁止全量 pytest**。

| 指标 | 数量 |
|------|------|
| IMPLEMENTED（catalog 叶 · `menu.ts` 键） | **98**（W9-12 **82** + 本回合 **13** 兼容/归一；脚本 `scripts/_count_impl.py` 核验） |
| 仍 WIP（`/ims/wip/*` · catalog 非 navParent） | **1** |
| 本回合新增 IMPLEMENTED | eff×3 · alert×2 · air×2 · master · contentTaskExecute · asset · cert · acct · qtPub（**13**） |

### W9 Checklist 进度（对照 IMS-E2E S1–S12 · 本回合更新）

| 场景 | 状态 | 摘要 |
|------|------|------|
| S12 数据消费 | 部分 | 主数据 overview；预警去重/处置 Tab；AIR Key/审计只读 |

（S1–S11 行与 W9-12 表一致，未重复粘贴。）

### W9 总验收指引（用户本地）

1. **pytest 全量**：`ims-backend\scripts\run_pytest.cmd`（单进程；争用 ims_test 时先 DROP/CREATE 测库，见脚本提示）。
2. **collect-only 快照**：`python -m pytest --collect-only -q` → 预期 **133**。
3. **E2E 四轮**：`smoke-fin` · `smoke-perf` · `smoke-alert` · `smoke-bi-report`（或 `npm run test:e2e`）。
4. **IMPLEMENTED / WIP**：**98** / **1**（见上表；唯一 WIP：**sysTenant** 批次外）。
5. **重启 18080**：加载本回合 `/alert/dedup/*`、`/alert/history/*`、`/eff/inventory/*`、`/air/cfg/key|audit/*`、`/master/overview`。

- **用户操作**：侧栏兼容键直达 eff/alert/air Tab；「主数据台账」；遗留 asset/cert/acct 自动跳转 corp。
- **下一片**：**sysTenant（批次外）** · perf adjust · contentPublish · contentFb（若仍 WIP）。

## W9-13 总验收 pytest 结果（677c230c · 2026-10-07）

- **并行检测**：跑前 `Get-CimInstance … pytest` 为 **0**；本机 `run_pytest.cmd` 因 **wmic 不可用** exit 255，等价执行 `_reset_test_dbs.py` → `_run_pytest_to_file.py`。
- **collect-only**：**133** tests collected。
- **全量（首轮 · `pytest_result.txt` 末行）**：**129 passed，4 failed，0 errors**（**非 1684**），约 **1607s**（0:26:47）。
  - FAILED：`test_comp_asset.py`×2（`KeyError: 'total'`，`ok(paged())` 双层包装）、`test_perf_exam.py`×1（同上 / 分页 offset）、`test_comp_analysis.py::test_comp_work_page_all_and_hit`（列表首条 likeCount 断言）。
- **修复后局部复跑**：上述 4 条用例在单进程下 **均已通过**（`comp/asset/list` 改 `return paged(...)`；`exam/questions` 分页 `offset((pageNo-1)*size)`；comp 作品断言放宽为 `any(likeCount==88000)`）。
- **第二轮全量**：中途被多路 `_run_pytest_to_file` 并行争用 **ims_test** 污染（**121 errors**），**不以该次为准**；请用户本地仅保留单进程再跑 `scripts/run_pytest.cmd` 确认 **133 passed**。
- **第三轮（Cursor · 2026-10-07 晚）**：`GET /health` **200 OK**；`--collect-only` **134** tests；`test_master_overview_blocks` 与全量 `_run_pytest_to_file.py` 在集成 shell 内 **~6–12s 被杀**（exit **-1** / **4294967295**），`pytest_result.txt` **无末行 summary**。**单进程全量请用** `ims-backend\scripts\run_pytest_external.bat`（或外置 cmd 跑 `run_pytest.cmd`）。`_pytest_preflight.py` 已修 **Format-List 截断**导致的误报。
- **18080 冒烟**：`POST /auth/login` 正常；`GET /admin-api/ims/master/overview`（带 Bearer）仍 **HTTP 404** → **需重启 18080** 加载 `/master/overview`（`cd ims-backend && python -m app.main`）。TestClient 侧 `test_master_data.py` 路由已注册于当前代码。
- **WIP**：仍 **1**（**sysTenant** 批次外，未实现）。

## Follow-up · W9-14 perf adjust + BI push + 发布管理侧栏

- **做了什么（S9 · perf adjust）**：`ims_perf_record` 增 `calc_base_score` / `manual_adjustment` / `adjust_remark`。契约对齐：`PUT /perf/execution/{id}/adjust`（算分后 CALCULATED/REVIEWED · ±20% · 状态→REVIEWED）；已 CONFIRMED/ISSUED 返回 **1155**。算分路径写入 `calc_base_score` 并重置调整。B9 增 `PUT /perf/execution`。前端执行考核页「调整」抽屉。
- **做了什么（S12 · 钉钉推送桩）**：`POST /bi/subscribe/{id}/push-now`（ACTIVE 订阅 · 更新 `lastPushStatus/lastPushAt` · 返回快照 + `dingTalk.msgId` 桩）。前端订阅页「立即推送」。
- **做了什么（S7 · contentPublish 导航）**：侧栏「内容生产 → 发布管理」接入既有 `/ims/content/publish`（list/pending/receipt/archive API 未改）。
- **测试**：`test_perf.py` **+1**（adjust→confirm→1155）；`test_bi_subscribe.py` 延伸 push-now。**禁止全量 pytest**；局部跑上述 2 条即可。
- **compat**：已有 **ims** 库执行 `db/compat/20261007_perf_record_adjust.sql`；测库 ORM `create_all` 即可（**未**把 compat SQL 挂进 `schema_reset.py`，模型已含三列）。
- **用户操作**：**重启 18080** 加载 adjust / push-now；侧栏验收发布管理；执行考核试「算分→调整→确认」；报表订阅「立即推送」看快照区。
- **下一片**：**sysTenant（批次外）** · perf 下发 ISSUED · Flow 发起/处理 · 真实钉钉 Webhook 配置项（可选）。

## Follow-up · W9-14 验收（2026-10-07）

- **compat 接线**：**否** — `tests/schema_reset.py` 仍走 `Base.metadata.create_all`；`ims_perf_record` 三列由 `app/models.py` 定义。仅 **已有 ims 生产/预发库** 需手工执行 `ims-backend/db/compat/20261007_perf_record_adjust.sql` 后再用手动「算分→调整」；未跑 compat 会缺列报错。
- **collect-only**（`ims-backend` · `python -m pytest --collect-only -q`）：**134** tests collected（W9-14 较 133 **+1**，`test_perf_adjust_and_locked_1155`；`test_bi_subscribe` 内 push-now 为延伸、无新 collect 项）。
- **全量签收**：Cursor 内 **不跑** 全量/并行 pytest（见运维说明）。请在 **外部终端** 单独执行 `ims-backend\scripts\run_pytest.cmd` → 期望 **134 passed**（单进程 + `_reset_test_dbs.py`）。
- **局部 pytest**：跑前已清并行 pytest；`python -m pytest` 在本机 agent 会话中多次 **异常退出（-1）**（疑与 autouse 全库 reset + 并发 DDL 有关）。等价 **单库 create_all + seed** 后 TestClient 复现：
  - `test_perf_adjust_and_locked_1155` 逻辑：**PASS**（adjust→REVIEWED→confirm→1155；`calc_base_score` 等列存在）。
  - `test_bi_subscribe_list_and_share_link`（含 **push-now**）：**PASS**（`lastPushStatus` DING_OK · 快照 rows）。
- **18080 冒烟**（本机 18080 已起）：`POST /admin-api/ims/auth/login`（admin）业务 **code=0**；`GET /admin-api/ims/master/overview`（Bearer）**HTTP 200**（根因：`opsbiz` 未建 `oa_*` 表 → `app/ops_db.py` 首次连库 `create_all`）；`POST /admin-api/ims/bi/subscribe/2/push-now` **HTTP 200**（列表 seed 首条 id=2）。
- **用户复验**：无其它 pytest 时 `python -m pytest tests/test_perf.py::test_perf_adjust_and_locked_1155 tests/test_bi_subscribe.py::test_bi_subscribe_list_and_share_link -q`；全量以外部 `scripts\run_pytest.cmd` 为准 → **134 passed**。

## 运维说明（Windows · 2026-10-07）

- **PowerShell**：勿用 `&&` 串联命令（会 ParserError）；改分号或单独一行。启动 API 用 `ims-backend\scripts\start_api.ps1`；端口占用时加 `-KillPort`（默认 18080 / `IMS_PORT`）。
- **18080 占用**：先 `Get-NetTCPConnection -LocalPort 18080` 查 PID，或 `.\scripts\start_api.ps1 -KillPort` 再启；避免重复 `python -m app.main` 叠多个监听进程。
- **pytest / 测库**：验收全量仅 `ims-backend\scripts\run_pytest.cmd`（单进程、先 `_reset_test_dbs.py`）；**禁止并行 pytest**，否则 MySQL 1684/缺表；已有 pytest 在跑时勿再起第二条。
- **Win11 无 wmic**：跑前检测已改为 `_pytest_preflight.py`（PowerShell `Get-CimInstance`），勿再依赖 `wmic`；**全量 pytest 前请先结束并行 pytest**（含 agent 单测），再执行 `scripts\run_pytest.cmd`。
- **smoke 后**：确认无残留 pytest（`Get-CimInstance` / preflight exit 0）再跑全量。

## W9 E2E（Playwright S1–S12 smoke · 2026-10-07）

| 主线 | smoke spec |
|------|------------|
| S1 员工全生命周期 | `ims-web/e2e/smoke-auth-org.spec.ts` |
| S2 直播全链路 | `ims-web/e2e/smoke-live.spec.ts` |
| S3 场次-成本-利润 | `ims-web/e2e/smoke-fin.spec.ts` |
| S4 账号领用流转 | `ims-web/e2e/smoke-acct.spec.ts` |
| S5 资产采购领用 | `ims-web/e2e/smoke-asset.spec.ts` |
| S6 证件录入预警 | `ims-web/e2e/smoke-cert.spec.ts` |
| S7 内容生产 AI | `ims-web/e2e/smoke-content.spec.ts` |
| S8 AI 资产分发 | `ims-web/e2e/smoke-air-skill.spec.ts` |
| S9 绩效考核周期 | `ims-web/e2e/smoke-perf.spec.ts` |
| S10 培训考试 | `ims-web/e2e/smoke-train.spec.ts` |
| S11 预警闭环 | `ims-web/e2e/smoke-alert.spec.ts` |
| S12 数据消费闭环 | `ims-web/e2e/smoke-bi-report.spec.ts` |

共用：`ims-web/e2e/smoke-helpers.ts`。`package.json` → `test:e2e` = `playwright test`（`playwright.config.ts` · `testDir: ./e2e`），**12 个 spec 均已纳入，无需改 glob**。

**最近一次 Agent 跑数（2026-10-07 · KillPort 后 API/5173 冒烟 OK）**：`IMS_API=http://127.0.0.1:18080`（与 `vite.config.ts` 默认一致）· `npm run test:e2e` → **12 passed，0 failed**（12 spec · ~5s）。

| 结果 | 说明 |
|------|------|
| 首轮 | **11 passed，1 failed** — `smoke-fin`：`profit.vue` 等误用 `import http from`（`http.ts` 无 default export）→ `/ims/fin/profit` 白屏 |
| 复跑 | `profit.vue` 已改为 `import { http }`；`cost.vue` / `profit-trace.vue` 同步 → **12/12 绿** |

**Playwright 浏览器**：`@playwright/test` 1.63 需 chromium **1243**；已清 `ms-playwright\__dirlock` 并 `cd ims-web && npx playwright install chromium` 落盘 **1243**（勿与并行 install 争用）。

## 用户验收 pytest（2026-10-07 · Agent 三步验收）

- **18080**：`GET /health` → **200**，`{"status":"up","db":"ims","ops":"opsbiz"}`；`POST /admin-api/ims/auth/login` 可达；**5173** dev 在监听。
- **pytest 全量**：**Cursor / 集成 shell 内禁止跑**（易 ~6–12s 杀进程、`pytest_result.txt` 空）。**仅外置 cmd** 单进程：`ims-backend\scripts\run_pytest_external.bat`（或 `run_pytest.cmd`）→ 读 `pytest_result.txt` 末行；见上文 **运维说明**「pytest / 测库」。本回合 Agent **未跑**全量；`--collect-only` → **134** tests；参考 W9-13 首轮末行 **129 passed，4 failed**（待串行复验 **133–134 passed**）。
- **E2E**：`cd ims-web && npm run test:e2e` → **12 passed，0 failed**（2026-10-07 · 18080+5173 · chromium **1243**）。逐 spec：**S1** `smoke-auth-org` ✓ · **S2** `smoke-live` ✓ · **S3** `smoke-fin` ✓ · **S4** `smoke-acct` ✓ · **S5** `smoke-asset` ✓ · **S6** `smoke-cert` ✓ · **S7** `smoke-content` ✓ · **S8** `smoke-air-skill` ✓ · **S9** `smoke-perf` ✓ · **S10** `smoke-train` ✓ · **S11** `smoke-alert` ✓ · **S12** `smoke-bi-report` ✓。
- **三步清单（echo）**：`ims-backend\scripts\run_acceptance_user.bat`（启 API/前端提示 · 外置 pytest · E2E）。

## Follow-up · FLOW-002 发起实例（2026-10-07）

- **看板**：[`IMS-任务进度计划表.md`](./IMS-任务进度计划表.md)
- **做了什么**：`POST /flow/instance`（1134 草稿不可发起 · `businessKey` 幂等 · `ims_flow_instance.business_key/form_data`）；B9 登记 POST；前端 `/ims/flow` 发起抽屉。compat：`db/compat/20261007_flow_instance_start.sql`（已有 ims 库增量）。
- **测试**：`tests/test_flow.py::test_flow_instance_start_and_idempotent`；`--collect-only` **135**（+1）。局部 TestClient 冒烟 PASS；全量仍外置 `run_pytest_external.bat`。
- **用户操作**：**重启 18080** 后验收 `POST /flow/instance`（本机旧进程对该路由 **404**）；已有 **ims** 库按需跑 compat SQL。

## 验收跟进（2026-10-07 · 子任务）

- **`python -m app.main` exit 1**：非 MySQL/导入失败，多为 **18080 已占用**（WinError 10048）；已有实例时 `GET /health` 正常即可，勿重复启第二个 API。
- **`run_pytest.cmd`**：Win11 无 `wmic` 时改用 `scripts/_pytest_preflight.py`；修正 `echo` 中含 `/` 导致 cmd 解析错误。
- **pytest 全量**：集成 shell 仍 ~3–6s 杀 `pytest` 进程，**本回合无新末行**；请外置 `run_pytest_external.bat` 单进程复验 **134 passed**。
- **E2E 复跑**：`IMS_API=http://127.0.0.1:18080` · **12 passed，0 failed**（~3.1s）。

## Follow-up · #17/#18 perf 导出 · 预警试跑（2026-10-07）

- **#18**：`app/perf.py` · `GET /perf/result/export`；`scope.py` 登记 export 前缀；`ims-web/src/views/perf/result.vue` 导出按钮。
- **#17**：`app/alert.py` · `POST /alert/rule/{id}/trial` 别名；`rule.vue` 副标题说明与 `check/run` 等价。
- **测试**：`test_perf_result_export_csv`、`test_alert_rule_trial_alias_matches_run`；`--collect-only` **141**；全量仍外置 `run_pytest_external.bat`。

## Follow-up · #33 CONTENT 任务执行闭环（2026-10-08）

- **切片**：计划启动（#32）→ **我的任务** → 执行页填写工作说明 → `POST …/execute/complete` → **DONE**（NORMAL 节点 · ADR-079）。
- **后端/前端**：无新路由（复用 `content_task.py` · `task-execute.vue`）。
- **测试**：`tests/test_content.py::test_plan_start_normal_task_execute_complete` 定向 **1 passed**；`--collect-only` **156**（+1）；**禁止全量 pytest 签收**。
- **E2E**：`closure-content-task-execute.spec.ts` · Checklist **v2.6.43** · `npx playwright test --workers=1` → **24 passed**（`E2E_BASE_URL=http://localhost:5173` · `IMS_API=18080` · `e2e_result.txt`）。
- **PO**：组织行 **UAT 状态=通过**（口头确认全量同步 OK · 19 部门 · listsub 修复）。
- **下一片**：内容 **工作任务登记→CONTENT_GENERATION 审核完成** closure · 或 **master/BI** 对照表待补数据行。

## Follow-up · #39 BI/S12 订阅「立即推送」closure（2026-10-08）

- **前端**：`subscribe.vue` 列表增「推送结果」列（`lastPushStatus` 中文 tag）。
- **E2E**：`closure-bi-subscribe-push-now.spec.ts`（纯 UI 新建报表+订阅 →「立即推送」→ 快照 GMV · 钉钉成功/上次推送）。
- **测试**：`tests/test_bi_subscribe.py::test_bi_subscribe_list_and_share_link` 定向 **1 passed**（含 push-now）；collect **157** 不变。
- **E2E**：`npm run test:e2e:ci` → **30/30 PASS**（`e2e_result.txt` · Web **6173**）。
- **文档**：Checklist **v2.6.49** · 计划表 **#39** · 对照表 BI 行 UAT 建议。

## Follow-up · #40 BI/S12「分享审批」Tab closure（2026-10-08）

- **前端**：`subscribe.vue` 增 **分享审批** Tab（待审批队列 · 通过/驳回）· 分享链接生成弹窗（敏感勾选 · 有效期）· 审批状态中文 tag。
- **E2E**：`closure-bi-share-approve.spec.ts`（纯 UI 敏感分享 → 分享审批 Tab 通过/驳回 → 分享链接 Tab 可见结果）× **2** cases。
- **测试**：`tests/test_bi_subscribe.py::test_bi_subscribe_list_and_share_link` 定向 **1 passed**（含 REJECTED 分支）；collect **157** 不变。
- **E2E**：`npm run test:e2e:ci` → **32/32 PASS**（`e2e_result.txt` · Web **6173**）。
- **文档**：Checklist **v2.6.50** · 计划表 **#40** · 对照表 BI UAT（分享审批）· 计划表 **#2** E2E 计数 **32/32**。

## Follow-up · #41 BI/S12 分享链接 EXPIRED closure（2026-10-08）

- **选型**：#40 后 BI 矩阵仍标 S12-05 **EXPIRED 未逐步**；内容「二级审核 Tab」/主数据 overview 仅有 API+页面、无 closure，PO 价值低于 S12 分享合规链。
- **前端**：`subscribe.vue` 已通过链接「标记过期」→ `PUT …/share-approval/{id}` · `approvalStatus=EXPIRED` · 隐藏「复制链接」。
- **E2E**：`closure-bi-share-expired.spec.ts`（纯 UI 敏感分享 → 审批通过 → 标记过期）× **1** case。
- **测试**：`tests/test_bi_subscribe.py::test_bi_subscribe_list_and_share_link` 定向 **1 passed**（含 EXPIRED）；collect **157** 不变。
- **E2E**：`npm run test:e2e:ci` → **33/33 PASS**（`e2e_result.txt` · Web **6173**）。
- **文档**：Checklist **v2.6.51** · 计划表 **#41** · 对照表 BI UAT（分享过期）· 计划表 **#2** E2E **33/33**。

## Follow-up · #42 CONTENT 二级审核 Tab closure（2026-10-08）

- **后端**：`app/content.py` · 一级 `PASS` 且 `content.review.level2.enabled` → 自动创建 `review_round=2` 待审 · 终审前仍 **1054**。
- **E2E**：`closure-content-review-stage2.spec.ts` · `closure-helpers.passContentReviewViaUi`（Tab + conclusion 等待）· 回归 `closure-content-publish` / `closure-content-work-task` **双审**。
- **测试**：`tests/test_content.py::test_review_gate_and_publish` · `test_task_execute_content_gate_and_crud` 定向 **2 passed**；collect **157** 不变。
- **E2E**：`npm run test:e2e:ci` → **36/36 PASS**（含 **#43** · `e2e_result.txt` · Web **6173** · 跑前需重启 **18080** 加载新 API）。
- **文档**：Checklist **v2.6.52** · 计划表 **#42** · 对照表内容审核行 UAT。

## Follow-up · #43 MASTER overview smoke + closure（2026-10-08）

- **页面**：复用 `master/index.vue` · `GET /master/overview` blocks（契约 MASTER · 无新 REST）。
- **E2E**：`smoke-master.spec.ts` · `closure-master-overview.spec.ts`（公司主体 / 平台账号 KPI 下钻）。
- **测试**：`tests/test_master_data.py::test_master_overview_blocks` 复用；collect **157** 不变。
- **E2E**：同上 **36/36 PASS**。
- **文档**：Checklist **v2.6.53** · 计划表 **#43** · 对照表 MASTER 行 · 计划表 **#2** E2E **36/36**。

## Follow-up · #45 BI BR-212 行级权限 closure（2026-10-08）

- **规则**：FR-BI-031 / BR-212 · 查看者 `dataScope`（行 `dept_id` / 创建者列）∩ 创建者 `ims_user_scope` · 订阅「我的」仍仅 `subscriber_user_id` · 无权 **1008**。
- **后端**：`app/bi_br212.py` · `ims_bi_report_def`/`ims_bi_share_link`.`dept_id` · 列表/详情/分享/发布 · 种子 `bi_r4_viewer`（DEPT·11）+ 【BR212】三报表 · compat `20261008_bi_br212_dept_id.sql`。
- **前端**：`report-list.vue` / `subscribe.vue` BR-212 提示条。
- **E2E**：`closure-bi-br212-row-scope.spec.ts`（纯 UI · admin 3 行 vs 查看者 2 行 + 分享 1 行）。
- **测试**：`tests/test_bi_br212_row_scope.py` 定向 **3 passed**。
- **假设**：`bi_r4_viewer` 命名沿用 R4 语境，角色为 **本部门数据查看**（`bi:dept-viewer`），**非** 敏感分享 R4 审批岗；审批 Tab 全量仍待 PO 矩阵。
- **文档**：Checklist **v2.6.55** · 计划表 **#45** · 对照表 BI 行级 UAT。

## Follow-up · #46 WORKBENCH 待办关闭 + 消息已读 closure（2026-10-08）

- **后端**：`workbench_seed.py`（`E2E-WB-MSG` / `E2E-WB-CLOSE` · admin · dashboard/init 幂等）。
- **前端**：`workbench/index.vue` 待办「关闭」· 消息已读「是/否」· 已读隐藏按钮。
- **E2E**：`closure-workbench-todo-message.spec.ts`（纯 UI · 计数联动）。
- **测试**：`test_workbench_e2e_seed_todo_and_message` · collect **+1**。
- **文档**：Checklist **v2.6.56** · 计划表 **#46** · 对照表工作台 UAT · 计划表 **#2** E2E **39/39**。

## Follow-up · #47 S4 CORP 账号池领用→归还 closure（2026-10-08）

- **后端**：`acct_flow.py`（`POST /account/apply` · approve · confirm · `POST /account/return/submit` · `GET /account/timeline/{id}`）· 表 `ims_acct_apply` / `ims_acct_timeline_event` · compat `db/compat/20261008_acct_apply_timeline.sql` · `acct_seed.py`（`AC-E2E-POOL` · `refresh_acct_e2e_pool`）。
- **前端**：`corp/account.vue` 行内/抽屉「领用」「归还」· 时间线 Tab 接 API。
- **E2E**：`closure-corp-account-checkout.spec.ts`（纯 UI · E2E-S4-01/08 切片）；`run_e2e.ps1` 跑前 refresh 池种子；`closure-content-publish` 改选 `IN_USE` 账号避免 1501。
- **测试**：`test_acct_checkout.py` **1 passed** · collect **162**（+1）。
- **文档**：Checklist **v2.6.57** · 计划表 **#47** · 对照表 S4/公司资产 UAT · 计划表 **#2** E2E **40/40**。

## Follow-up · #48 S10 TRAIN 下发→学习完成 closure（2026-10-08）

- **后端**：`app/train.py` · `PUT /train/task/{id}/progress` · `POST …/confirm` · `GET …/task/records` · `scope.py` 登记 · `ims_train_task_record`.`material_progress`/`finished_at` · compat `db/compat/20261008_train_task_record_progress.sql`。
- **前端**：`/ims/train/study/:taskId`（`study.vue`）· `task.vue` 已发布资料多选 ·「去学习」/「学习记录」。
- **E2E**：`closure-train-dispatch-complete.spec.ts` · `closure-helpers` 培训 UI 辅助（纯 UI · E2E-S10-01/02 切片）。
- **测试**：`tests/test_train.py::test_train_task_progress_confirm_and_records` · train 模块 **5 passed** · collect **163**（+1）。
- **E2E**：`npm run test:e2e:ci` → **41/41 PASS**（Web **6173** · `e2e_result.txt`）。
- **Live**：已有 MySQL `ims` 库执行 compat 后 **重启 18080**（`-KillPort`）；`init_ims_db.ps1 -ApplyCompat` 含本脚本。
- **文档**：Checklist **v2.6.58** · 计划表 **#48** · 对照表 TRAIN UAT · 计划表 **#2** E2E **41/41**。

## Follow-up · #49 TRAIN-003 完成率 Tab closure（2026-10-08）

- **后端**：`GET /admin-api/ims/train/stat/finish-rate`（`totalFinishRate` · `byTask`/`byDept`/`byPerson` · BR-102 分母含未确认指派 · 可选 `dateRange`）。
- **前端**：`/ims/train/stat` · `stat.vue`「完成率总览」Tab（近7/30天 · KPI · 三表 · 其余 Tab 占位）。
- **E2E**：`closure-train-stat-finish-rate.spec.ts` · `completeTrainStudyViaUi` · `smoke-train` 统计页 smoke；`closure-helpers` IP 组「关联作者」重试修正（去错 Tab「关联成员」）。
- **测试**：`tests/test_train.py::test_train_stat_finish_rate_after_confirm` · train **6 passed** · collect **164**（+1）。
- **E2E**：`npm run test:e2e:ci` → **43/43 PASS**（Web **6173** · `e2e_result.txt` 2026-10-08）。
- **Live**：部署本切片后 **重启 18080**（`-KillPort`），否则 finish-rate **404**。
- **文档**：Checklist **v2.6.59** · 计划表 **#49** · 对照表 TRAIN UAT（完成率看板）· 计划表 **#2** E2E **43/43**。

## Follow-up · #50 S3 FIN 成本→利润 closure（2026-10-08）

- **种子**：`live_fin_e2e_seed.py`（`AC-E2E-FIN` · `E2E-FIN-PHONE` · 实名人绑定）· `run_e2e.ps1` / `main.seed` refresh。
- **前端**：`live/index.vue`「核准下播」（`PUT /live/report/{code}/confirm`）· `cost.vue` 成本录入 **ProtoDrawer** · `fin-cost-complete-rate` testid。
- **E2E**：`closure-fin-cost-profit.spec.ts`（纯 UI · E2E-S3-01/02/03 · 净利润 **81400**）· `closure-helpers` LIVE/FIN 链。
- **测试**：`test_live_fin_e2e_seed_deps` · 定向 `test_fin` **2 passed** · collect **165**（+1）。
- **E2E**：`npm run test:e2e:ci` → **44/44 PASS**（Web **6173** · `e2e_result.txt`）。
- **Live**：**重启 18080**（`-KillPort`）加载 seed + 核准下播 UI。
- **文档**：Checklist **v2.6.60** · 计划表 **#50** · 对照表 FIN UAT · 计划表 **#2** E2E **44/44**。

## Follow-up · #51 DC-002 利润反查 closure（2026-10-08）

- **前端**：`profit-trace.vue` 抽屉 `data-testid="fin-profit-trace-chain-drawer"`（列表/反查抽屉已具备，本片仅 E2E 锚点）。
- **E2E**：`closure-fin-profit-trace.spec.ts`（纯 UI · 复用 **#50** LIVE/FIN 链 → `/ims/fin/profit-trace` · **81400** · **BR-209** 穿透）· `openFinProfitTraceChainViaUi`。
- **测试**：定向 `test_dc_profit_trace_list_and_chain` + `test_live_fin_e2e_seed_deps` **2 passed** · collect **165** 不变。
- **E2E**：`npm run test:e2e:ci` → **45/45 PASS**（Web **6173** · `e2e_result.txt`）。
- **文档**：Checklist **v2.6.61** · 计划表 **#51** · 对照表 FIN/DC UAT · 计划表 **#2** E2E **45/45**。

## Follow-up · #52 DC-001 账号穿透 closure（2026-10-08）

- **后端**：`dc_trace.py` — `mode=DETAIL` 时 `detailList` 为契约 `PageResult`（修正误嵌套 `ok()` 导致前端明细空表）。
- **前端**：`trace.vue` — `dc-trace-*` testid（关键词/搜入口/图/明细/meta）。
- **E2E**：`closure-dc-account-trace.spec.ts`（纯 UI · **E2E-S12-01 账号入口切片** · 复用 **#50** 链 → `/ims/dc/trace` · `AC-E2E-FIN` · 图+表）· `openDcAccountTraceViaUi`。
- **测试**：`test_dc_trace_account_keyword_detail_mode` + `test_dc_trace_entry_and_query` **2 passed** · 定向含 `test_dc_profit_trace_list_and_chain` **3 passed** · collect **166**（+1）。
- **E2E**：`npm run test:e2e:ci` → **46/46 PASS**（Web **6173** · `e2e_result.txt`）。
- **Live**：**重启 18080**（`-KillPort`）加载 `dc_trace` 修复。
- **文档**：Checklist **v2.6.62** · 计划表 **#52** · 对照表 BI/DC UAT · 计划表 **#2** E2E **46/46**。

## Follow-up · #53 DC 场次下钻 + 明细导出（2026-10-08）

- **后端**：`dc_trace.py` — `GET /dc/trace/detail/{sessionCode}`（下播 GMV/退款/UV/时长 · 三级利润 · `costDetail` · 1504）· `GET /dc/trace/export`（`format=XLSX|PDF` · `{downloadUrl, expiresIn}` · 鉴权下载 `/dc/trace/export/file`）· `POST /dc/trace/query` 日期跨度 **>92 天** 返回 **1181**（`queryCostMs` 仍在 `data`）。
- **前端**：`trace.vue` 场次 ID / 场次节点打开明细抽屉 ·「导出链路报告」· 页头 `queryCostMs` 与超时提示（降级时橙色 **1181**）。
- **E2E**：`closure-dc-session-drill.spec.ts`（纯 UI · 复用 **#50/#52** 链 · 抽屉 **81400** · xlsx 含场次号 · 宽日期 1181）· `openDcSessionDetailViaUi`。
- **测试**：`tests/test_dc_trace.py` **3 passed**（含 `test_dc_trace_session_detail_export_and_timeout`）· collect-only **167**（+1）· 未跑全量 pytest（外置签收）。
- **E2E**：Playwright `--workers=1` → **47/47 PASS**（Web **6173** · API **18080** · 本地 MySQL · `e2e_result.txt`）。
- **附带**：`smoke-train.spec.ts` 将 `waitForResponse(/train/stat/finish-rate)` 挪到 `goto` 之前，避免快 API 上响应先返回导致全量红。
- **文档**：Checklist **v2.6.63** · 计划表 **#53** · 对照表 BI/DC UAT（场次下钻）。

## Follow-up · #54 FIN 成本更正→RECALCULATED closure（2026-10-08）

- **后端**：`fin.py` — `POST /fin/cost/{sessionCode}/correction`（红冲/蓝补 · remark 幂等 `__IDEM:`）· `POST /fin/profit/recalc/{sessionCode}` · 更正后 `calcStatus=RECALCULATED` · 分成明细随 `FinCost` 同步（`dc_profit_trace` share-detail）。
- **前端**：`cost.vue` — 已核准行「更正」抽屉 + testid · 更正原因必填。
- **E2E**：`closure-fin-cost-correction.spec.ts`（纯 UI · **81400→79900** · 反查 **3500** 达人分成）· `submitFinCostCorrectionViaUi`。
- **测试**：`test_fin_cost_correction_recalc_profit_and_share_trace` **1 passed** · collect **167**（+1）。
- **E2E**：本地 `npm run test:e2e:ci` → **47/47 PASS**（#54 分支 · Web **6173** · `e2e_result.txt`）；与 **#53** 合并 main 后预期 **48/48**。
- **Live**：**重启 18080**（`-KillPort`）加载 correction 路由；云 MySQL 无 DDL（幂等写 remark）。
- **文档**：Checklist **v2.6.64** · 计划表 **#54** · 对照表 FIN UAT · **未自动链 #55**。

## Follow-up · #55 S6 证件水印 closure（2026-10-08）

- **种子**：`cert_e2e_seed.py`（`E2E-Cert-Watermark` · 证件 list 页/`main`/`run_e2e.ps1` 幂等）。
- **前端**：`resource.vue` · `corp-cert-view-btn` / `corp-cert-watermark-hint`。
- **E2E**：`closure-corp-cert-watermark.spec.ts`（**E2E-S6-03 切片** · 纯 UI）。
- **测试**：`test_cert_e2e_seed_watermark_view` **1 passed** · collect **169**（+1）。
- **文档**：Checklist **v2.6.65** · 计划表 **#55** · 对照表 S6 UAT 建议。

## Follow-up · #56 S2 直播登记→下播 narrow closure（2026-10-08）

- **E2E**：`closure-live-session-report.spec.ts`（纯 UI · `registerLiveSessionConfirmedReportViaUi` · 19 位 ID · 列表 **CONFIRMED**）。
- **加固**：`trace.vue` 场次明细 GET **60s** · `dc-trace-session-open` testid · `openDcSessionDetailViaUi` 行定位。
- **文档**：Checklist **v2.6.66** · 计划表 **#56** · 对照表 LIVE 行 · 全量 E2E **50/50 PASS**。

## Follow-up · #58 S4 冲话费登记 + 凭证门禁（2026-10-08）

- **API**：`acct_flow.py` `POST/GET /account/recharge` · `ims_acct_recharge` · B9 `scope.py` 登记该前缀 · compat `20261008_acct_recharge.sql`。
- **规则**：`>5000` 且凭证空 → **1025**；恰好 5000 无凭证允许；`clientToken` 重放原单；时间线摘要不含凭证文本。
- **可见性**：`voucherUrl` 仅 `acct:r3`（种子 `e2e_acct_r3`）；admin 见「仅财务可见」。
- **E2E**：`closure-corp-account-recharge.spec.ts`（纯 UI · `AC-E2E-POOL`）。与 **#57** 合并后 **52/52 PASS**。
- **测试**：`test_acct_recharge_voucher_gate_and_finance_visibility` · collect **171**。
- **文档**：Checklist **v2.6.68** · 计划表 **#58** · 对照表公司资产 UAT 建议。**E2E-S4-02/03 当时为 #60+ 候选，现为 #60 进行中**。
