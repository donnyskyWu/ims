# IMS PRD 功能点执行对照表（矩阵 · W9 主线）

> **用途**：对照完整 PRD / 菜单 IMPLEMENTED / 切片计划 / pytest·E2E 签收，回答「PRD 功能点做到哪了」——**不复制 PRD 全文**，仅矩阵视图。**本表为 PRD 模块矩阵，不是计划表 `#` 清单**；关联交付 `#` 见各列「备注」与 [`IMS-任务进度计划表.md`](./IMS-任务进度计划表.md)。  
> **SSOT 链**：[`IMS-PRD与原型完整性核验-20261001.md`](../产品规划/IMS-PRD与原型完整性核验-20261001.md) · [`IMS-Python完整开发计划-20261005.md`](./IMS-Python完整开发计划-20261005.md) · [`IMS-Python执行进度-20261006.md`](./IMS-Python执行进度-20261006.md) · [`IMS-任务进度计划表.md`](./IMS-任务进度计划表.md) · [`IMS-E2E测试用例Checklist.md`](../测试方案/IMS-E2E测试用例Checklist.md) · **[Agent 交付循环](../开发规范/IMS-Agent交付循环.md)**  
> **最后刷新**：2026-10-08 · 菜单 **~100 IMPLEMENTED**（含隐藏路由 · **#57** 分成单/台账对账 · **#58** 冲话费在账号页抽屉，无新菜单 · **#59** 期间结账在成本页，无新菜单 · **#60** 账号流转在抖音账号页抽屉，无新菜单）· pytest collect 合并后见计划表 · E2E 合并复跑见 `e2e_result.txt`（Checklist **v2.6.70** · **#59** S3 结账 LOCKED + 锁后红冲 · **#60** S4 流转/1021 · **#57** S3 分成 PAID_OFF）· **#57/#58/#59 已完成** · **#60** 开发完成/待UAT（非已验收）· **#61** S6 证书到期预警 **进行中**（并行，非本片）

**图例**

| 后端 / 前端 | pytest | E2E |
|-------------|--------|-----|
| **已实现** 主路径 API + 页面可进 | 域内用例已 collect，外置全量待 **144 passed** 签收 | smoke **OK** 或 closure **OK** |
| **部分** 桩 / 阻断页 / 缺联调 / 未逐步 E2E | 部分覆盖或仅 TestClient 冒烟 | narrow smoke 或 closure 切片 |
| **未开始** 批次外或 PRD Gate 未开 | — | — |

**UAT 列（PO 门禁）**

| UAT 建议（Agent） | 含义 |
|-------------------|------|
| **可 UAT** | 本地默认资源 + smoke/closure 已覆盖主路径，PO 可手工签收 |
| **待补数据** | 功能在，但需补种子/业务数据或多角色场景 |
| **仅 API** | 页面桩或自动化偏 TestClient，PO 宜 curl/接口验收 |
| **阻塞** | 批次外、缺外部系统或 PRD Gate 未开 |

| UAT 状态（PO） | 含义 |
|----------------|------|
| **未测** | 默认 |
| **通过** | PO UAT 完成 |
| **阻塞** | 缺资源或业务决策 |

**已验收**（矩阵行级）：对应 **closure/Checklist OK** + **最新 E2E 全量 PASS** + **UAT 状态 = 通过**（narrow smoke alone **不算**）。**组织模块**另需 **L3 真钉钉**（`IMS_DINGTALK_L3=1` · `test_org_dingtalk_l3.py` / `run_dingtalk_l3.ps1`）**PASS** + PO UAT，见脚注 †。

---

## W9 主线模块矩阵

| PRD 模块 / 功能点（摘要） | 计划切片 | 后端 | 前端 | pytest | E2E | UAT 建议 | UAT 状态 | 备注 |
|---------------------------|----------|------|------|--------|-----|----------|----------|------|
| **系统基座** · 登录/JWT/健康检查 · 用户/角色/字典/参数 · 操作/登录日志/通知 · B9 fail-closed | W0 · W1 · B9 | 已实现 | 已实现 | 已实现 | S1 smoke · FLOW/WORKBENCH 补充 | 可 UAT | 未测 | [执行进度 §S-IMS-S-01～05 · B9](./IMS-Python执行进度-20261006.md) · `#8` FLOW 发起 |
| **组织** · 钉钉事件入队/死信 · 岗位供给 · 对账 R1 · **全量拉取同步** | W1 · S-IMS-A-02/03 · **#27 L3 · #31** | 已实现 | 已实现 | 已实现 + **L3 PASS** + **#31 sync** | S1 smoke · **E2E-ORG-DING-01 OK** | **可 UAT（全量拉取验证组织树与用户数）**：组织页/同步脚本复跑 · 对照钉钉后台部门树与人数 · 授权范围见 `auth/scopes` · [同步说明](../运维/钉钉通讯录同步说明.md) | **通过** | PO **2026-10-08** 口头确认全量同步 OK（**19** 部门 · listsub 修复）· **listsub 对象数组解析**（#31）· `dingtalk_sync_result.txt` |
| **工作台** · dashboard 待办/消息 · **流程待办聚合** `flowTodoCount` · **待办关闭/消息已读** | W1 · A-04 · **#13/#46** | 已实现 | 已实现 | `#13b` · **`test_workbench_e2e_seed_todo_and_message`（#46）** | `smoke-workbench` · **`closure-workbench-todo-message`（#46）** | **可 UAT（工作台 · #46）**：`/ims/workbench` 见 `E2E-WB-MSG` →「标为已读」未读减 1 · `E2E-WB-CLOSE` →「关闭」待办消失 | 未测 | 与 `my-todo` 同源计数 · 种子幂等（dashboard 触发） |
| **内容 · S7 发布督办** · 审核门禁 1054 · **发布 list/pending/receipt/archive** · 督办 overdue 提示 | W4 S4/S3 · W9-14 导航 · #15/#24 | 已实现 | 已实现（`/ims/content/publish`） | `test_review_gate_and_publish`（含二级链） | S7 smoke + **`closure-content-publish`**（双审） | 可 UAT | 未测 | ComfyUI/GPU **未做**；E2E-S7-01～06 全量未逐步 |
| **内容 · 审核 · 二级 Tab** · `/ims/content/review` · ADR-017 level2 链 | W4 · **#42** | 已实现 | 已实现 | `test_review_gate_and_publish` L2 断言 | **`closure-content-review-stage2`** | **可 UAT（二级审核 · #42）**：提审 → 一级通过 →「二级审核」Tab 见轮次 **2** → 二级通过 → Tab 空态「暂无待审」 | 未测 | 系统参数 `content.review.level2.enabled` 默认 true |
| **内容 · 生产主链** · SOP/计划/任务/审核/AI 桩 | W4 · **#29/#32/#33/#34/#35/#36/#37/#42** | 部分 | 部分 | 部分 | S7 smoke + **`closure-content-plan-start`（#32）** + **`closure-content-plan-terminate`（#36）** + **`closure-content-task-execute`（#33）** + **`closure-content-work-task`（#35）** + **`closure-content-work-task-tabs`（#37）** + **`closure-content-review-stage2`（#42）** · **#34** 纯 UI | **可 UAT（计划轨）**：SOP/计划 → 启动 → 执行页工作说明 → **DONE**（#32/#33）。**可 UAT（计划终止 · #36）**：执行中计划 →「申请终止」→ `TERMINATE_PENDING` → admin「批准终止」→ 计划 **TERMINATED** · 关联未完成任务 **TERMINATED**（可选测「驳回终止」恢复 `IN_PROGRESS`）。**可 UAT（工作任务轨 · #35）**：SOP 设 `LIVE_PUBLIC`+`CONTENT_GENERATION` → 工作任务登记 → **一级+二级审核** → **DONE**。**可 UAT（工作任务 Tab · #37）**：登记确认后「任务执行情况」列表可见节点/赛事 ·「任务管理」矩阵 summary/表体可见营销计划与赛事。发布督办见 **#34** closure | 未测 | **#37** execution/矩阵 Tab 已 closure · ComfyUI/GPU 未做 |
| **主数据 MASTER** · `/ims/master` overview KPI · 跳转资源管理 | W9-13 · **#43** | 已实现 | 已实现 | `test_master_overview_blocks` | **`smoke-master`** · **`closure-master-overview`** | **可 UAT（主数据台账 · #43）**：侧栏「主数据台账」→ 六块 KPI 数字加载 → 点击「公司主体」→ 公司页 · 返回 overview →「平台账号」→ 抖音账号池 | 未测 | 与 corp 资源路由一致 · 无新 REST |
| **流程 FLOW** · 发起实例 · 我的待办 handle · **超时 list/urge/rate/distribution** | W7 · #8/#11/#19/#21/#22 | 已实现 | 已实现 | 已实现 | smoke-flow · smoke-flow-timeout · **closure-flow×2** | 可 UAT | 未测 | Checklist **E2E-FLOW-01/02** 闭环 |
| **绩效 PERF** · 方案/执行/算分/调整/确认 · **下发 ISSUED** · **结果 CSV 导出** | W7 · #9/#18 | 已实现 | 已实现 | 已实现 | S9 smoke · **closure-perf-issue-export** | 可 UAT | 未测 | E2E-S9-01～08 全量未逐步 |
| **预警 ALERT** · 规则 CRUD · **试跑 trial** · **实时预警处置/处置记录/去重 Tab** | W7 · #17/#20 · **#44** | 已实现 | 已实现 | 已实现 | smoke-alert · smoke-alert-trial · **closure-alert-trial** · **`closure-alert-handle-tab`（#44）** | **可 UAT（预警处置 · #44）**：规则页试跑 → `/ims/alert/live`「处理」→ toast ·「处置记录」见 **HANDLED** + 汇总卡 ·「去重合并」见 **DEDUP-LIVE** | 未测 | 钉钉推送/1166 非目标人 **未逐步** |
| **BI / 数据消费** · BI0 自定义查询 · 报表/指标/订阅 · **钉钉 push-now 桩** · **分享审批 Tab** · **BR-212 行级** · **DC-001 账号穿透** · **场次下钻/导出** | W6/W8 · **#10/#39/#40/#41/#45/#52/#53** | 部分 | 部分 | 已实现（bi/ dc） | S12 smoke + **`closure-bi-subscribe-push-now`（#39）** + **`closure-bi-share-approve`（#40）** + **`closure-bi-share-expired`（#41）** + **`closure-bi-br212-row-scope`（#45）** + **`closure-dc-account-trace`（#52 · DC-001）** + **`closure-dc-session-drill`（#53）** | **可 UAT（订阅推送 · #39）**：新建订阅 →「立即推送」见快照 GMV ·「钉钉成功」/上次推送。**可 UAT（分享审批 · #40）**：敏感分享 → 审批通过/驳回 → 分享链接 Tab 状态。**可 UAT（分享过期 · #41）**：已通过链接 →「标记过期」→「已过期」· 无「复制链接」。**可 UAT（行级权限 · #45）**：admin 报表管理搜 `BR212-` 见 3 行 · `bi_r4_viewer` / `Admin@123` 见 2 行 · 分享 Tab 仅 `BR212-dept11-A` 链接。**可 UAT（账号穿透 · #52）**：侧栏「穿透查询」→ 入口类型账号 · 搜 `AC-E2E-FIN` → 选入口 → 关系图含实名人/账号/场次 · 明细表见本场次 · 页头 `queryCostMs`/数据截至。**可 UAT（场次下钻 · #53）**：同链点场次 ID → 抽屉见 GMV **100,000** / 净利润 **81,400** / 投流成本 →「导出链路报告」下载 xlsx → 日期拉到 2020–2026 再查，页头橙色 **1181** 且仍显示 `queryCostMs` | 未测 | 真实 Webhook 可选；**BR-212** 报表 query/下钻全链路仍 P1；六入口中资产/责任人/IP 组 **未做**；**DC-002 利润反查** 见 FIN 行 **#51** |
| **运营看板 HOME** · 与个人工作台分菜单 | W6 · **#38** | 已实现 | 已实现 | `test_home.py` | **`smoke-home`** · **`closure-home-dashboard`** | **可 UAT**：`/ims/home` 四 KPI（账号数/今日作品延迟桩/待办/采集异常）· 刷新 · 账号数→抖音池 · 快捷→工作任务登记 | 未测 | 与 workbench 分菜单；Football 真实作品 KPI **仍桩** |
| **公司资产 · 账号池领用/归还 · 冲话费 · 账号流转** · `/ims/corp/account/*` · ACCT apply/confirm/return · transfer · recharge · 时间线 Tab | W2 CORP · **#47/#58/#60** | 切片已实现 | 已实现（领用/归还/冲话费/流转抽屉） | **`test_acct_checkout`**（含 **#58** 1025 · **#60** 1021/流转） | S4 smoke + **`closure-corp-account-checkout`（#47）** + **`closure-corp-account-recharge`（#58 · E2E-S4-05/06）** + **`closure-corp-account-transfer`（#60 · E2E-S4-02/03）** | **可 UAT（池领用 · #47）**：抖音页搜 `AC-E2E-POOL` →「领用」→ 提交/审批/交接 → 状态「在用」· 责任人 admin →「归还」→「已归还」· 详情「领用时间线」见 APPLY/RETURN。**可 UAT（冲话费 · #58）**：同页「冲话费」→ 金额 1000 无凭证提交成功 → 列表 1000.00；金额 6000 无凭证见 **1025** → 补凭证后成功；admin 列表「仅财务可见」；`e2e_acct_r3` / `Admin@123` 可见凭证号。**可 UAT（流转 · #60）**：搜 `AC-E2E-XFER` → admin 领用至「在用」→ 退出后用 `e2e_acct_peer` / `Admin@123` 再点「领用」见 **1021** → 换回 admin「流转」选「流转同事」· 原因「业务调整」→ 同事登录「确认接收」→ 责任人变为「流转同事」· 时间线见 **TRANSFER** | 未测 | 收回冻结 **1022** / 账实核对 **1026** **未做**；流转未接工作台待办与资产同步提示；已有 ims 库需 compat `20261008_acct_transfer.sql` / `20261008_acct_recharge.sql` 或重启 API `ensure_acct_schema` · **#60 开发完成/待UAT，非已验收** |
| **培训 TRAIN** · 资料/任务 · **progress/confirm/records** · 学习中心 · **TRAIN-003 完成率 Tab** | W7 · **#48/#49** | 切片已实现 | 已实现（`task`/`study`/`stat`） | **`test_train_task_progress_confirm_and_records`** · **`test_train_stat_finish_rate_after_confirm`（#49）** | S10 smoke + **`closure-train-dispatch-complete`（#48）** + **`closure-train-stat-finish-rate`（#49）** | **可 UAT（培训下发 · #48）**：资料→任务→学习中心 **CONFIRMED** → 学习记录。**可 UAT（完成率看板 · #49）**：`/ims/train/stat`「完成率总览」· 近30天 · 总完成率 KPI · 按任务/部门/个人表（纯 UI 链：学完后再进看板见该任务 **100%**） | 未测 | 部门统计/排行/逾期/资料热度 Tab **待接 API**；考试/补考 **未做** |
| **财务 FIN** · **FIN-001/002/003 分成单** · **成本更正/重算** · **期间结账/锁后更正** · **DC-002 利润反查** · **台账对账** · BR-107/108/209 | W8 · **#50/#51/#54/#57/#59** | 切片已实现 | 已实现（`/ims/fin/cost` · `/ims/fin/profit` · **`/ims/fin/profit-trace`** · **`/ims/fin/share/result`** · **`/ims/fin/ledger`**） | **`test_fin_*`** · **`test_fin_cost_correction_recalc_profit_and_share_trace`（#54）** · **`test_fin_share_audit_payoff_amounts_sum_to_total`（#57）** · **`test_fin_period_close_locks_writes_then_r4_red_correction`（#59）** · **`test_dc_profit_trace_list_and_chain`（#51）** · **`test_live_fin_e2e_seed_deps`（#50）** | S3 smoke + **`closure-fin-cost-profit`（#50）** + **`closure-fin-profit-trace`（#51）** + **`closure-fin-cost-correction`（#54 · E2E-S3-04）** + **`closure-fin-share-payoff`（#57 · E2E-S3-05/08）** + **`closure-fin-period-lock`（#59 · E2E-S3-06/07）** | **可 UAT（成本→利润 · #50）**：LIVE 核准下播 → 成本核准 → 利润 **CALCULATED** · **81400**。**可 UAT（利润反查 · #51）**：同链 → 利润反查「反查」→ **BR-209**。**可 UAT（更正重算 · #54）**：已核准成本 →「更正」改投放/达人分成 + 原因 → 利润 **RECALCULATED** · **79900** · 反查抽屉达人分成 **3500**。**可 UAT（分成发放 · #57）**：同 #50 链 → 场次财务「分成单」搜场次 → 财务审+业务审 →「发放登记」→ **已发放** · 拆分合计 **4,000.00** = 总额 →「台账对账」见 **四账一致**（成本 **16,600** · 净利润 **81,400** · 分成 **4,000**）。**可 UAT（结账锁定 · #59）**：成本页填一个未用过的 `yyyy-MM` →「结账」→ 状态 **LOCKED** → 该月新场次「录入」提交见 **财务期间已结账**（**1142**，原 1010 已移除；成本已核准为 **1141**）→ 已核准场次「更正」先见须 **R4**（**1155**）→「申请锁后更正」→「审批通过」→ 投放改为更小金额提交 → 红冲行「投放成本」→ 利润列表 **82,400.00** · 详情 **RECALCULATED** | 未测 | 结账 LOCKED / 锁后更正为 **#59**（已合入 main `6fa2a88` · 开发完成/待 UAT）；分成规则 CRUD **未做**；聚合/异常 Tab **未做**；已有 ims 库需 compat `20261008_fin_period.sql` 或重启 API `create_all` |
| **直播 LIVE** · 场次登记/风控/下播 · **S2 窄 closure** | W2 · **#56** | 已实现 | 已实现（`/ims/live/sessions`） | `test_live.py` 等 | S2 smoke + **`closure-live-session-report`（#56 · E2E-S2 窄切片）** | **可 UAT（登记→下播 · #56）**：新建场次 → 风控 → 下播 GMV/退款 → 核准 → 列表 `reportEntryStatus=CONFIRMED` · 19 位 `IMS…DYS…` | 未测 | E2E-S2-01/02/06 切片；黄红风控/补录 **未逐步** |
| **证件 CORP-R** · 索引分页 · **查看水印** | W2 · **#55** | 已实现（page/view） | 已实现（`/ims/corp/resource/certificate`） | **`test_cert_e2e_seed_watermark_view`（#55）** | S6 smoke + **`closure-corp-cert-watermark`（#55 · E2E-S6-03 切片）** | **可 UAT（证件水印 · #55）**：搜 `E2E-Cert-Watermark` →「查看」→ 脱敏号 + 水印含 admin · 无原图 | 未测 | 契约无上传 UI；到期预警 **#61 进行中**（E2E-S6-02 · 并行分支，非本片） |
| **直播 / 账号 / 资产 / 采集 / 会议 / 上报** 等 W2–W7 其余 | W2–W7 | 大部分已实现 | **~98 IMPLEMENTED** | 域内用例齐全 | S4/S5 等 smoke | 可 UAT | 未测 | Football/OPS 真实 KPI **待补数据**；详见 [执行进度](./IMS-Python执行进度-20261006.md) |
| **sysTenant 租户套餐** | 批次外 | 未开始 | WIP | — | — | 阻塞 | 未测 | [计划表 #4](./IMS-任务进度计划表.md) **阻塞·本批不做** |

**† 组织 L3 签收**：**系统参数**（`dingtalk.*`）为主；`dingtalk.l3Enabled=true` 或 `IMS_DINGTALK_L3=1` + `scripts/run_dingtalk_l3.ps1` 或 `npm run test:e2e:dingtalk`；可选 bootstrap `scripts/seed_dingtalk_params_from_env.ps1`；全量人员 **`POST /auth/org/sync-from-dingtalk`**（R1）· `scripts/run_dingtalk_org_sync.ps1` · 组织页「手动对账」；**全量同步前提**：开放平台 **通讯录授权范围** 覆盖同步根部门（见 `auth/scopes` / PO 清单）；Checklist **E2E-ORG-DING-01**。

---

## Checklist 主线 vs 自动化（S1–S12）

| 主线 | PRD 优先级 | narrow smoke | 逐步闭环 / 切片 |
|------|------------|--------------|-----------------|
| S1 员工生命周期 | P0 | OK | 未 |
| S2 直播 | P0 | OK | **closure 登记→下播核准（#56 · E2E-S2 窄切片）** |
| S3 场次-成本-利润 | P0 | OK | **closure 成本→利润（#50）** · **closure 利润反查（#51）** · **closure 更正重算（#54 · E2E-S3-04）** · **closure 分成 PAID_OFF + 台账对账（#57 · E2E-S3-05/08）** · **closure 结账 LOCKED + 锁后红冲（#59 · E2E-S3-06/07）** · E2E-S3-01/02/03/04/05/06/07/08/09 切片 |
| S4 账号领用 | P0 | OK | **closure 池领用/归还（#47）** · **closure 冲话费凭证门禁（#58 · E2E-S4-05/06）** · **closure 流转 + 他人领用 1021（#60 · E2E-S4-02/03）** · E2E-S4-01/02/03/05/06/08 切片 |
| S5 资产 | P1 | OK | 未 |
| S6 证件 | P1 | OK | **closure 水印查看（#55 · E2E-S6-03 切片）** · **E2E-S6-02 到期预警为 #61 进行中**（并行，非本片） |
| **S7 内容 AI 全流程** | P1 | OK（内容管理 list） | **closure 发布督办（#24）** · **closure 计划启动（#32）** |
| S8 AI 资产 | P0 | OK | 未（检索用例已作废） |
| S9 绩效 | P0 | OK | **closure 下发→导出 OK** |
| S10 培训 | P1 | OK | **closure 下发→学习完成（#48）** · **closure 完成率 Tab（#49）** · E2E-S10-01/02 切片 |
| S11 预警 | P1 | OK + trial smoke | **closure 试跑 OK** · **closure 处置 Tab（#44）** |
| S12 数据消费 | P0 | OK | **closure push-now（#39）** · **closure 分享审批（#40）** · **closure 分享过期（#41）** · **closure 账号穿透（#52 · DC-001）** · **closure 场次下钻/导出（#53）** · E2E-S12-01 账号入口 + 场次下钻切片 |

---

## 如何更新本表

1. 新切片交付：改 [执行进度](./IMS-Python执行进度-20261006.md) + [计划表](./IMS-任务进度计划表.md) 一行。  
2. 新菜单 IMPLEMENTED：对照 `ims-web/src/nav/menu.ts` 与 [PRD 核验 §3](../产品规划/IMS-PRD与原型完整性核验-20261001.md)。  
3. E2E 签收：改 Checklist 版本行 + 本表 E2E 列 + 计划表 **#2 / #12 / #25**；Agent 跑 **`ims-web/scripts/run_e2e.ps1`**，PO 看 `playwright-report/`。  
4. UAT：Agent 更新 **UAT 建议**；PO 验收后填 **UAT 状态**；行级 **已验收** 见上文图例 · [交付循环](../开发规范/IMS-Agent交付循环.md)。
