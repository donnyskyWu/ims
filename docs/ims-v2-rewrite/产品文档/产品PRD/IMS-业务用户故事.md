# IMS 业务用户故事（叙事 SSOT）

> **版本**：v1.6 ｜ 2026-10-05（AIR 知识库**语义检索整体移出范围（不做）**（完整 PRD v2.6.34）：KNOW-003 检索 / KB-001 RAGFlow / `knowledge_context` / 错误码 5007/5008 全部移除（**非延后**）；范围锁定文件管理，`KbProvider=LOCAL`，MCP 固定四工具）  
> **索引**：全量 L3 覆盖；QT 深度见分册《IMS-业务用户故事-QT.md》。

## 0. 编写方法（每条故事固定结构）

| 块 | 要求 |
|----|------|
| **故事 ID / 角色 / 业务目标** | 目标写业务结果，非按钮清单 |
| **前置条件** | 登录、权限、seed、依赖模块 |
| **主路径** | 用户语言步骤 + 已 grounding API |
| **成功结果** | 可见状态/数据落点 |
| **异常** | 权限、校验、BLOCKED 时用户可见表现 |
| **追溯** | FR/AC 与 `delivery/TESTCASES-IMS-*` |

## 1. 分册索引

| 分册 | 文件 | 故事数 |
|------|------|--------|
| A · 工作台与日常运营 | `产品PRD/IMS-业务用户故事-A-工作台与日常.md` | 5 |
| B · 内容·采集·分析 | `产品PRD/IMS-业务用户故事-B-内容采集分析.md` | 19 |
| C · 公司资产与财务 | `产品PRD/IMS-业务用户故事-C-资产与财务.md` | 15 |
| D · 协同与成长 | `产品PRD/IMS-业务用户故事-D-协同成长.md` | 16 |
| E · 数据决策 | `产品PRD/IMS-业务用户故事-E-数据决策.md` | 12 |
| F · 系统·权限·AIR | `产品PRD/IMS-业务用户故事-F-系统与AIR.md` | 15 |
| 查询工具 QT | `产品PRD/IMS-业务用户故事-QT.md` | 7 |

## 2. 全量故事索引

| 故事 ID | 一句话需求 | 页面 key | 用例文件 |
|---------|------------|----------|----------|
| US-HOME-01 | 一屏掌握今日运营关键数与快捷入口，决定是否下钻模块。 | `home` | `TESTCASES-IMS-AUTH.md` |
| US-HOME-02 | 在一个入口处理今日待办与系统消息，不必逐模块找队列。 | `workbench` | `TESTCASES-IMS-AUTH.md` |
| US-IPG-01 | 建立可授权、可统计的 IP 组，供内容/账号/人效共用。 | `ipg` | `TESTCASES-IMS-EFF.md` |
| US-LIVE-01 | 登记一场直播并同步 Football 直播间基本信息，完成风控与台账。 | `live` | `TESTCASES-IMS-LIVE.md` |
| US-MON-01 | 配置作品监测用的主题/行业标签，供 MON 与内部分析筛选。 | `mon` | `TESTCASES-IMS-INT.md` |
| US-CONTENT-01 | 从工作任务下发到提审、审核通过，形成可发布内容。 | `contentWork` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-02 | 沉淀可复用的 SOP，供计划与任务引用。 | `contentSop` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-03 | 按周期编排内容计划并关联 SOP/作者。 | `contentPlan` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-04 | 在「我的任务」列表定位指派任务并进入执行。 | `contentTask` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-08 | 在全页完成玩法区与附件填写并提交审核。 | `contentTaskExecute` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-05 | 管理已审核通过的内容条目与版本。 | `contentList` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-06 | 为任务选择公推版式模板，保证出片规范。 | `contentLayout` | `TESTCASES-IMS-CONTENT.md` |
| US-CONTENT-07 | 按队列完成内容审核，保证合规发布。 | `contentReview` | `TESTCASES-IMS-CONTENT.md` |
| US-COLLECT-01 | 让指定外部账号进入 Channel-D 采集范围。 | `collectExtAccount` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-COLLECT-02 | 按关键字抓取外部作品补充账号盘。 | `collectExtKeyword` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-COLLECT-03 | 按 schedule 或立即执行抓取并可在日志追溯。 | `collectTask` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-COLLECT-04 | 定位失败批次并跳转修复凭证。 | `collectLog` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-COLLECT-05 | 让查询工具/自定义查询能消费已映射实体。 | `collectMetadata` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-COLLECT-06 | 统一内外部分析爆款/低分阈值来源。 | `collectThreshold` | `TESTCASES-IMS-COLLECT-任务日志.md` |
| US-INT-01 | 只看内部作品盘，与竞品域分离。 | `intWork` | `TESTCASES-IMS-INT.md` |
| US-INT-02 | 掌握内部账号粉丝与作品聚合。 | `intAccount` | `TESTCASES-IMS-INT.md` |
| US-COMP-01 | 从全部作品到爆款/低分掌握外部盘。 | `compWork` | `TESTCASES-IMS-COMP.md` |
| US-COMP-02 | 按高粉/低粉看外部账号盘。 | `compAccount` | `TESTCASES-IMS-COMP.md` |
| US-COMP-03 | CRUD 竞品库条目，与 M7 只读监测分离。 | `comp` | `TESTCASES-IMS-COMP.md` |
| US-CORP-A01 | 维护 公众号 账号主数据供直播/采集/上报选择。 | `caWechatOfficial` | `TESTCASES-IMS-CORP.md` |
| US-CORP-A02 | 维护 视频号 账号主数据供直播/采集/上报选择。 | `caWechatChannels` | `TESTCASES-IMS-CORP.md` |
| US-CORP-A03 | 维护 抖音 账号主数据供直播/采集/上报选择。 | `caDouyin` | `TESTCASES-IMS-CORP.md` |
| US-CORP-A04 | 维护 快手 账号主数据供直播/采集/上报选择。 | `caKuaishou` | `TESTCASES-IMS-CORP.md` |
| US-CORP-A05 | 维护 小红书 账号主数据供直播/采集/上报选择。 | `caXhs` | `TESTCASES-IMS-CORP.md` |
| US-CORP-R01 | 维护签约公司主体供账号/合同引用。 | `crCompany` | `TESTCASES-IMS-CORP.md` |
| US-CORP-R02 | 维护实名人档案并与账号/手机卡关联。 | `crRealname` | `TESTCASES-IMS-CORP.md` |
| US-CORP-R03 | 登记 SIM 并与实名人/设备绑定。 | `crSim` | `TESTCASES-IMS-CORP.md` |
| US-CORP-R04 | 维护证件类型与有效期预警输入。 | `crCert` | `TESTCASES-IMS-CORP.md` |
| US-CORP-D01 | 按 dict_asset_type=OFFICE 登记设备供 LIVE 关联。 | `cdOffice` | `TESTCASES-IMS-CORP.md` |
| US-CORP-D02 | 按 dict_asset_type=LIVE+SHOOT 登记设备供 LIVE 关联。 | `cdLive` | `TESTCASES-IMS-CORP.md` |
| US-CORP-D03 | 按 dict_asset_type=PHONE 登记设备供 LIVE 关联。 | `cdPhone` | `TESTCASES-IMS-CORP.md` |
| US-COST-01 | 按账号查看营收与成本，与场次利润菜单分离（BR-302）。 | `cost` | `TESTCASES-IMS-DC-穿透查询.md` |
| US-FIN-01 | 核准单场成本项，为利润反查提供输入。 | `finCost` | `TESTCASES-IMS-DC-穿透查询.md` |
| US-FIN-02 | 从场次/利润视角反查成本与分成。 | `finProfitTrace` | `TESTCASES-IMS-DC-穿透查询.md` |
| US-MEET-01 | 创建会议并关联参与人，与日报域分离。 | `meet` | `TESTCASES-IMS-MEET.md` |
| US-MEET-D01 | 完成并提交我的日报 | `dailyMine` | `TESTCASES-IMS-MEET.md` |
| US-MEET-D02 | 掌握团队日报 | `dailyTeam` | `TESTCASES-IMS-MEET.md` |
| US-MEET-D03 | 审阅下属日报 | `dailyReview` | `TESTCASES-IMS-MEET.md` |
| US-MEET-D04 | 掌握日报提交率 | `dailyStat` | `TESTCASES-IMS-MEET.md` |
| US-REPORT-01 | 填报并提交运营数据 | `reportSub` | `TESTCASES-IMS-REPORT.md` |
| US-REPORT-02 | 维护上报模板 | `reportTpl` | `TESTCASES-IMS-REPORT.md` |
| US-REPORT-03 | 查看上报完成率 | `reportRate` | `TESTCASES-IMS-REPORT.md` |
| US-TRAIN-01 | 发布培训资料 | `trainMaterial` | `TESTCASES-IMS-TRAIN.md` |
| US-TRAIN-02 | 派发学习任务 | `trainTask` | `TESTCASES-IMS-TRAIN.md` |
| US-TRAIN-03 | 查看培训完成率 | `trainStat` | `TESTCASES-IMS-TRAIN.md` |
| US-PERF-01 | 维护考核方案 | `perfScheme` | `TESTCASES-IMS-PERF.md` |
| US-PERF-02 | 执行本期考核 | `perfExec` | `TESTCASES-IMS-PERF.md` |
| US-PERF-03 | 员工查看考核结果 | `perfResult` | `TESTCASES-IMS-PERF.md` |
| US-PERF-04 | 绩效考试组卷 | `perfExam` | `TESTCASES-IMS-PERF.md` |
| US-FLOW-01 | 在工作流中心处理非 SOP 替代的审批单。 | `flow` | `TESTCASES-IMS-MEET.md` |
| US-BI-01 | 浏览报表目录（报表管理） | `biList` | `TESTCASES-IMS-BI.md` |
| US-BI-02 | 设计报表布局（设计器·隐藏路由） | `biDesign` | `TESTCASES-IMS-BI.md` |
| US-BI-03 | 打开 M6 标准报表（报表中心） | `bi0Report` | `TESTCASES-IMS-BI.md` |
| US-BI-04 | 配置数据大屏（报表类型 dashboard；`bi0Screen` 归一化到 `biList`） | `biList` | `TESTCASES-IMS-BI.md` |
| US-BI0-01 | 维护指标定义 | `bi0Metric` | `TESTCASES-IMS-BI0-自定义查询.md` |
| US-BI0-02 | 指标分析看板 | `bi0Analysis` | `TESTCASES-IMS-BI0-自定义查询.md` |
| US-BI0-03 | 自定义 SQL 查询 | `bi0Query` | `TESTCASES-IMS-BI0-自定义查询.md` |
| US-BI-05 | 预览报表结果 | `biPreview` | `TESTCASES-IMS-BI.md` |
| US-DC-01 | 从 entry 起点沿关联查到底（只读）。 | `dc` | `TESTCASES-IMS-DC-穿透查询.md` |
| US-EFF-01 | 按 IP 组/人员看产出与人效指标。 | `eff` | `TESTCASES-IMS-EFF.md` |
| US-ALERT-01 | 启用规则使上游信号产生预警实例。 | `alertRule` | `TESTCASES-IMS-ALERT.md` |
| US-ALERT-02 | 看见预警并完成确认/处理/误报闭环。 | `alertLive` | `TESTCASES-IMS-ALERT.md` |
| US-QT-01 | 配置分级下钻并保存草稿 | `FR-QT-001` | `queryTool` |
| US-QT-02 | 配置穿透路径并保存 | `FR-QT-002` | `queryTool` |
| US-QT-03 | 从查询记录编辑 | `FR-QT-003` | `queryTool` |
| US-QT-04 | 发布为数据分析下菜单 | `FR-QT-004` | `queryTool` |
| US-QT-05 | 从新菜单执行查询 | `FR-QT-005` | `queryTool` |
| US-QT-06 | 取消发布并撤销侧栏 | `FR-QT-006` | `queryTool` |
| US-QT-07 | 删除草稿模板 | `FR-QT-007` | `queryTool` |
| US-AIR-01 | 选用 AI 技能完成任务 | `airSkill` | `TESTCASES-IMS-AIR.md` |
| US-AIR-02 | 从专家库匹配专家策略 | `airExpert` | `TESTCASES-IMS-AIR.md` |
| US-AIR-03 | 配置模型与提示词 | `airCfg` | `TESTCASES-IMS-AIR.md` |
| US-AIR-04 | 维护知识库与知识分类 | `airKb` | `TESTCASES-IMS-AIR.md` |
| US-AIR-05 | 从系统资料转入知识库 / 手动上传资料 | `airKb` | `TESTCASES-IMS-AIR.md` |
| US-AUTH-01 | 钉钉组织同步与对账 | `authOrg` | `TESTCASES-IMS-AUTH.md` |
| US-AUTH-02 | 岗位-角色供给规则与权限预览 | `authPosition` | `TESTCASES-IMS-AUTH.md` |
| US-SYS-01 | 维护系统用户 | `sysUser` | `TESTCASES-IMS-SYS.md` |
| US-SYS-02 | 配置角色菜单 | `sysRole` | `TESTCASES-IMS-SYS.md` |
| US-SYS-03 | 维护 IMS 菜单树 | `sysMenu` | `TESTCASES-IMS-SYS.md` |
| US-SYS-04 | 维护业务字典 | `sysDict` | `TESTCASES-IMS-SYS.md` |
| US-SYS-05 | 维护系统参数 | `sysParam` | `TESTCASES-IMS-SYS.md` |
| US-SYS-06 | 审计操作日志 | `sysLog` | `TESTCASES-IMS-SYS.md` |
| US-SYS-07 | 配置通知渠道 | `sysNotify` | `TESTCASES-IMS-SYS.md` |
| US-SYS-08 | 分配套户套餐 | `sysTenant` | `TESTCASES-IMS-SYS.md` |

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-10-04 | v1.5：AIR 知识库收窄为**文件管理期**（对应完整 PRD v2.6.32）——US-AIR-04/05 标注 KNOW-003 检索 / KB-001 RAGFlow 底座延后至检索期，Provider 改 `LOCAL`（IMS 服务端文件目录），MCP 六工具→四工具 |
| 2026-10-05 | v1.6：对应完整 PRD v2.6.34——AIR 知识库语义检索**整体移出范围（不做）**（KNOW-003 / KB-001 / knowledge_context / 5007-5008 移除，非延后）；范围锁定文件管理，KbProvider=LOCAL，MCP 四工具 |
| 2026-10-04 | v1.4：AIR 知识库开放（完整 PRD v2.6.31）——新增 US-AIR-04/05，AIR 由三叶扩为四叶 |
| 2026-10-01 | v1.1：L3 全量故事 + 分册；核验见 `产品规划/IMS-故事用例对照核验-20261001.md` |
| 2026-10-01 | v1.0：QT 07 + 17 模块各 1 条 |
