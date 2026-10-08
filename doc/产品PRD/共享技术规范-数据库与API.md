# 神鱼体育 IMS 一体化管理系统 — 共享技术规范（数据库与 API）

> 本文档为 IMS 三期 PRD 的共享技术规范，包含**第 7 章 数据库设计概要**与**第 8 章 API 路径规范**，将直接嵌入各期 PRD 文档。
>
> - 适用期次：V1（P0，第 1~14 周）／V2（P1，第 15~27 周）／V3（P2，第 28~38 周）
> - 技术栈基线：**已由 ADR-IMS-002 取代**（Go + sqlc + Vue3 Vite；**不用芋道**）。下文若仍写 Spring/芋道，一律视为过期实现描述。
> - 组织/权限唯一同步源：钉钉（SSO + 事件驱动）；IMS 自建 AUTH，不复用芋道 `sys_*` 作为菜单角色 SSOT
> - 命名规范：业务新建表 `ims_` 前缀；OPS 并入沿用现网 `oa_*`；IMS SYS 自管表（非芋道系统表）

---

# 第 7 章 数据库设计概要

## 7.1 表分类（三期总表）

IMS 全量数据表按业务域分为 8 大类，统一使用 `ims_` 前缀体系（区别于系统级 `sys_` 前缀表，**字段规范遵循《全局开发规范》§1/§7 与 ADR-IMS-002（Go + sqlc）**）。

| 分类 | 表数量 | 表名前缀 | 说明 | 归属期次 |
|------|--------|----------|------|----------|
| 组织与权限 | 6 | `ims_auth_` / `ims_sys_` / `ims_role_` / `ims_org_` | 钉钉同步映射、角色（**权限唯一载体**，含功能点 R/W/D 明细与数据范围）、角色-菜单、多主体预留 | V1 新建 |
| 资产管理 | 7 | `ims_asset_` | 资产台账、穿透层级、资产-实名人-账号关联 | V1 新建（含已完成部分增量） |
| 账号管理 | 5 | `ims_account_` | 账号台账、领用/流转/归还、冲话费、时间线 | V1 新建（含已完成部分增量） |
| 证件管理 | 4 | `ims_cert_` | 证件档案、存储索引、到期预警、水印分级 | V1 新建（含已完成部分增量） |
| 直播管理 | 5 | `ims_live_` | 直播场次（含场次 ID 主表）、排期、人员、数据回流 | V1 新建（全新） |
| 内容生产 | 6 | `ims_content_` | SOP、生产任务、ComfyUI 工作流、AI 生产链、素材库 | V1 新建（全新） |
| 培训/会议/日报/上报 | 13 | `ims_train_` / `ims_meeting_` / `ims_daily_` / `ims_report_` | 培训资料与学习任务、会议纪要、日报、数据上报 | V2 新建 |
| 工作流/绩效/预警 | 20 | `ims_flow_` / `ims_perf_` / `ims_exam_` / `ims_alert_` | 工作流模板与实例、绩效指标与结果、在线考试、预警规则与事件 | V2 新建 |
| 财务核算 | 5 | `ims_fin_` | 场次成本、利润、分成核算、看板缓存（共 5 张，含分成规则/分成单） | V3 先行批次新建（由 V2 移入，第 28~33 周） |
| 竞品/数据中心/分析/人效 | 18 | `ims_comp_` / `ims_dc_` / `ims_bi_` / `ims_eff_` / `ims_dws_` | 竞品分析库、穿透聚合宽表、自助报表、人员归属与人效盘点（数仓分层物理表 `ims_dws_ods_*`/`ims_dws_dwd_*` 见分期技术约束 V3-A1） | V3 新建 |
| AI 资源中台 | 12 | `ims_skill_` / `ims_expert_` / `ims_kb_` / `ims_air_` | 技能/专家/知识三类 AI 资产、人员 Key、MCP 连接器审计与用量（模块 20，PRD 见 IMS-模块20-AI资源中台PRD-V1） | V2.2 批次（并入第二期） |
| **复用已完成模块** | — | `sys_*`、既有表 | 16 数据采集、18 作品监测整体完成；07/08/06/17/19 部分完成的表仅做**增量消费**，不重复建设 | 不新建 |

**复用与增量消费约定**：

| 已完成模块 | 复用策略 |
|-----------|---------|
| 16 数据采集 | 直接消费其采集结果表（不改表结构），V2 数据上报（09）与 V3 数据中心（12）仅新增视图/同步任务 |
| 18 作品监测 | 直接消费监测指标，V3 数据分析（17）经 `ims_bi_` 报表层与 `ims_dws_*` 聚合层消费，不回写 |
| 07 资产（已建部分） | 保留既有台账表，V1 仅新增穿透层级表与关联表 |
| 08 账号（已建部分） | 保留既有账号表，V1 新增领用/流转/归还/冲话费/时间线表 |
| 06 证件（已建部分） | 保留既有档案表，V1 新增存储索引表、到期预警表、水印分级配置表 |
| 17 / 19（已建部分） | V3 在其上补自助报表表（`ims_bi_*`）、订阅表、人员归属表，不破坏既有结构 |

## 7.2 核心表结构（三期核心表清单）

| 表名 | 说明 | 关键字段 | 归属期次 |
|------|------|----------|----------|
| `ims_auth_user_mapping` | 钉钉用户映射 | user_id(sys_user_id), dingtalk_user_id, union_id, dept_ids, sync_status, last_sync_time | V1 |
| `ims_sys_role` | 角色（**权限唯一载体** · ADR-IMS-008） | role_id, role_name, role_key, data_scope(ALL/DEPT/IP_GROUP/SELF), dingtalk_position(NULL 唯一), source(MANUAL/DINGTALK_AUTO), status(ENABLED/PENDING_CONFIG) | V1 |
| `ims_sys_role_menu` | 角色-菜单权限码 | role_id, menu_id, perm_code(兼容 `ops:*`) | V1 |
| `ims_role_perm_detail` | 角色 功能点×R/W/D 明细 | role_id, module_code, perm_code, perm_level(R/W/D/RW/RWD) | V1 |
| `ims_org_subject` | 多主体/租户预留表 | subject_id, subject_code, subject_name, status, is_default | V1（预留，不做功能） |
| `ims_asset_ledger` | 资产台账（含既有增量） | asset_id, asset_code, asset_type, spec, status, purchase_date, subject_id | V1 |
| `ims_asset_hierarchy` | 资产穿透层级 | asset_id, parent_asset_id, level, path | V1 |
| `ims_asset_bind` | 资产-账号-实名人关联 | bind_id, asset_id, account_id, verified_person_id, bind_type, bind_status, effective_time | V1 |
| `ims_account_ledger` | 账号台账 | account_id, platform, account_no, nickname, status, owner_person_id, subject_id | V1 |
| `ims_account_flow` | 领用/流转/归还记录 | flow_id, account_id, from_person_id, to_person_id, flow_type, flow_time, remark | V1 |
| `ims_account_charge` | 冲话费记录 | charge_id, account_id, amount, payer, voucher_url, charge_time | V1 |
| `ims_account_timeline` | 账号时间线（事件流） | event_id, account_id, event_type, event_time, event_detail(JSON), operator_id | V1 |
| `ims_cert_archive` | 证件档案 | cert_id, cert_no, cert_type, owner_person_id, valid_from, valid_until | V1 |
| `ims_cert_storage_index` | 证件存储索引 | cert_id, oss_bucket, oss_object_key, storage_status | V1 |
| `ims_cert_expire_task` | 到期预警任务 | task_id, cert_id, warn_level, notify_channel, next_run_time | V1 |
| `ims_cert_watermark_config` | 权限分级水印配置 | config_id, perm_level, watermark_text, opacity, position | V1 |
| `ims_live_session` | 直播场次主表 | session_id(场次 ID，编码规则见 7.4), subject_id, platform, title, plan_start, plan_end, actual_start, actual_end, status | V1 |
| `ims_live_schedule` | 直播排期 | schedule_id, session_id, live_date, time_slot, live_room_id | V1 |
| `ims_live_person` | 场次人员分工 | person_id, session_id, role_type(主播/中控/运营), verified_person_id | V1 |
| `ims_live_data_snapshot` | 场次数据回流快照 | snapshot_id, session_id, metric_code, metric_value, collect_time | V1 |
| `ims_content_sop` | 内容生产 SOP | sop_id, sop_code, sop_name, phase, standard_type(执行标准级), version | V1 |
| `ims_content_task` | 生产任务 | task_id, sop_id, session_id, assignee_id, status, deadline | V1 |
| `ims_content_workflow` | ComfyUI 工作流登记 | workflow_id, workflow_code, comfy_flow_path, param_schema(JSON), version | V1 |
| `ims_content_ai_job` | AI 生产任务 | job_id, workflow_id, task_id, priority, queue_status, gpu_node, result_file_key | V1 |
| `ims_content_material` | 素材库 | material_id, material_type, file_key, tag_ids | V1 |
| `ims_train_material` / `ims_train_material_cate` | 培训资料 / 资料分类 | material_no, cate_id, material_type, position_codes, version, status | V2 |
| `ims_train_task` / `ims_train_task_record` | 学习任务 / 学习记录 | task_no, assign_scope, deadline, confirm_type；record: progress, confirm_status | V2 |
| `ims_train_stat_daily` | 培训完成率统计（日） | stat_date, dept_id, assigned_count, finished_count | V2 |
| `ims_meeting_minutes` | 会议纪要 | minutes_id, meeting_no, title, attendees, review_status | V2 |
| `ims_daily_report` / `ims_daily_review` / `ims_daily_stat` | 日报 / 逐级审阅 / 提交率统计 | report_id, report_date, content, status；review: reviewer_id, read_status | V2 |
| `ims_report_template` / `ims_report_submission` / `ims_report_audit` / `ims_report_stat` | 上报模板 / 填报单 / 审核 / 完成率统计 | template_id, version, required_fields(JSON)；submission: period, due_time, submit_status | V2 |
| `ims_flow_template` / `ims_flow_node` | 工作流模板 / 节点定义 | template_id, version, form_schema(JSON)；node: node_type, assignee_rule | V2 |
| `ims_flow_instance` / `ims_flow_task` | 工作流实例 / 任务 | instance_id, template_id, biz_type, node_states(JSON) | V2 |
| `ims_flow_version_log` / `ims_flow_timeout_log` / `ims_flow_stat` | 工作流版本 / 超时 / 统计 | version_log: template_id, version；timeout_log: task_id, timeout_at | V2 |
| `ims_fin_cost` | 场次成本 | session_code(唯一索引), platform, commission_rate, ad_cost, recharge_cost, fixed_cost, sample_cost, entry_status | V3 先行批次（由 V2 移入） |
| `ims_fin_profit` | 场次利润（自动计算） | session_code, gross_profit, operating_profit, net_profit, net_profit_rate, calc_version, calc_status | V3 先行批次（由 V2 移入） |
| `ims_fin_share_rule` / `ims_fin_share_result` | 分成规则 / 分成单 | rule: share_target, base_type, rate_type, ladder_config, priority；result: share_base, share_amount, calc_detail, status | V3 先行批次（由 V2 移入） |
| `ims_fin_dashboard_cache` | 利润看板缓存 | stat_period, dimension_type, dimension_value, total_gmv, net_profit, refreshed_at | V3 先行批次（由 V2 移入） |
| `ims_perf_metric` | 绩效指标配置 | metric_code, metric_name, metric_type, source_config, score_rule, weight, version, status | V2 |
| `ims_perf_result` / `ims_perf_result_detail` | 绩效结果 / 明细 | period_month, user_id, total_score, rank_in_dept, result_status；detail: metric_id, metric_value, metric_score | V2 |
| `ims_exam_paper` / `ims_exam_question` / `ims_exam_record` | 试卷 / 题库 / 答卷 | paper: paper_type(FIXED/RANDOM), strategy, total_score；record: questions(JSON 快照), switch_screen_count, exam_status | V2 |
| `ims_perf_rank` / `ims_perf_alert` | 排名 / 绩效预警 | period_month, dept_id, rank_no, grade_level, alert_status, consecutive_months | V2 |
| `ims_alert_rule` / `ims_alert_record` | 预警规则 / 事件 | rule: dsl_content(JSON DSL), window, scope；record: level, escalate_status, dedup_key | V2 |
| `ims_alert_escalation_log` / `ims_alert_merge_log` / `ims_alert_stats` | 升级 / 去重合并 / 统计 | escalation_log: record_id, level, escalated_at；merge_log: dedup_key, merge_count | V2 |
| `ims_comp_analysis` / `ims_comp_audit` | 竞品分析提交 / 审核入库 | analysis_no, submitter_user_id, period_month, dimension_data, submit_status | V3 |
| `ims_comp_asset` / `ims_comp_asset_version` | 竞品资产库 / 版本 | comp_name, latest_version, status；version: version_no, merged_analysis_ids | V3 |
| `ims_dc_trace` / `ims_dc_trace_log` | 穿透聚合宽表 / 查询审计 | entry_type, entry_id, full_chain(JSON)；trace_log: query_user_id, result_rows, cost_ms | V3 |
| `ims_dc_dashboard_config` / `ims_dc_dashboard_cache` | 全链路看板配置 / 缓存 | config: dimension_set, refresh_freq；cache: dimension_type, metric 集, refreshed_at | V3 |
| `ims_dws_session_daily` | 场次日汇总（DWS 层） | stat_date, session_id, metric 集 | V3 |
| `ims_dws_person_monthly` | 人员月汇总（DWS 层） | stat_month, person_id, metric 集 | V3 |
| `ims_bi_report` / `ims_bi_report_widget` | 自助报表 / 图表组件 | report_id, dataset_ref, dim_codes, metric_codes, version；widget: chart_type, config | V3 |
| `ims_bi_query_log` / `ims_bi_subscription` / `ims_bi_share_link` | 查询日志 / 报表订阅 / 分享链接 | query_log: report_id, cost_ms, task_status；subscription: freq, channel；share_link: approval_status, expire_at | V3 |
| `ims_eff_person_relation` | 人员归属（多线归属） | user_id, relation_type, target_type, target_id, share_ratio, effective_from/to | V3 |
| `ims_eff_metric_config` / `ims_eff_result` | 人效指标 / 盘点结果 | metric_code, source_config, calc_expr；result: period_month, dimension_type, metric_value, rank_no, publish_status | V3 |
| `ims_skill` | 技能主表（AIR） | skill_id, skill_code, name, category, ver, status, source, risk_level, subject_id | V2.2 批次 |
| `ims_skill_ver` | 技能版本 | skill_ver_id, skill_id, ver, md_hash, md_content(MEDIUMTEXT), audit_status, risk_level | V2.2 批次 |
| `ims_skill_grant` | 技能授权 | grant_id, skill_id, grant_type(部门/角色/人员), grant_id_ref, status, granted_by | V2.2 批次 |
| `ims_expert` | 专家包（AIR） | expert_id, expert_code, name, system_prompt(TEXT), skill_ids(JSON), kb_ids(JSON), tool_whitelist(JSON), ver, status, subject_id | V2.2 批次 |
| `ims_expert_grant` | 专家授权 | grant_id, expert_id, grant_type, grant_id_ref, status, granted_by | V2.2 批次 |
| `ims_kb` | 知识库（AIR） | kb_id, name, desc, secret_level(公开/内部/机密/绝密), provider(默认 ragflow), ext_id, status, subject_id | V2.2 批次 |
| `ims_kb_doc` | 知识文档 | doc_id, kb_id, title, content_hash, source_type(上传/URL/采集), secret_level, audit_status, ext_id | V2.2 批次 |
| `ims_kb_grant` | 知识库授权 | grant_id, kb_id, grant_type, grant_id_ref, status, granted_by | V2.2 批次 |
| `ims_api_key` | 人员 AI 连接 Key | key_id, key_hash(SHA-256), user_id(sys_user), device_name, status(有效/冻结/吊销), last_used_at, qpm_limit, ip_whitelist(JSON) | V2.2 批次 |
| `ims_mcp_log` | MCP 调用审计 | log_id, key_id, user_id, tool, param_digest, result_code, cost_ms, created_at | V2.2 批次（日志表按月分区，保留 180 天） |
| `ims_air_usage` | 用量统计（日） | usage_id, user_id, tool, call_cnt, token_cnt, stat_date | V2.2 批次 |
| `ims_air_event` | AI 资产事件（钉钉同步） | event_id, event_type, payload(JSON), sync_status, created_at | V2.2 批次 |

> **表名口径说明**：业务表以本 7.2 清单为准（表名与各期 PRD 5.x 命名一致）；分期技术约束 V3-A1 中的 `ims_dws_ods_*` / `ims_dws_dwd_*` 为数仓 ODS/DWD 层**物理分层命名规则**（聚合层同步/清洗表），不属于本清单业务表，两者用途不同、不冲突。

## 7.3 核心关联关系总览

### 7.3.1 内嵌外键关联（逻辑外键，InnoDB 不建物理外键，由应用层保证）

| 主表 | 外键字段 | 关联表 | 说明 |
|------|----------|--------|------|
| `ims_asset_bind` | asset_id | `ims_asset_ledger` | 资产绑定 |
| `ims_asset_bind` | account_id | `ims_account_ledger` | 账号绑定 |
| `ims_asset_bind` | verified_person_id | `ims_auth_user_mapping`（→ sys_user） | 实名人 |
| `ims_account_flow` | account_id | `ims_account_ledger` | 领用/流转/归还 |
| `ims_live_person` | session_id | `ims_live_session` | 场次人员 |
| `ims_live_person` | verified_person_id | `ims_auth_user_mapping` | 场次实名人 |
| `ims_content_task` | session_id | `ims_live_session` | 内容任务挂场次 |
| `ims_fin_cost/ims_fin_profit` | session_code | `ims_live_session` | 成本/利润挂场次（V3 先行批次） |
| `ims_live_data_snapshot` | session_id | `ims_live_session` | 数据回流 |
| `ims_perf_result` | user_id + period_month | `ims_auth_user_mapping` | 绩效取数 |
| `ims_api_key` | user_id | `sys_user`（经 ims_auth_user_mapping） | AI 连接 Key 绑定人员（离职事件触发吊销） |
| `ims_mcp_log` | key_id | `ims_api_key` | 调用审计回溯 Key |
| `ims_skill_ver` / `ims_skill_grant` | skill_id | `ims_skill` | 技能版本与授权 |
| `ims_expert_grant` | expert_id | `ims_expert` | 专家授权 |
| `ims_kb_doc` / `ims_kb_grant` | kb_id | `ims_kb` | 知识文档与授权（正文存 IMS 服务端文件目录，IMS 存元数据；v2.6.34 起无 RAGFlow） |

### 7.3.2 独立关联表（多对多）

| 关联表 | 连接的两端 | 说明 |
|--------|-----------|------|
| `ims_asset_bind` | 资产 ↔ 账号 ↔ 实名人（三元关联，bind_type 区分持有/担保/代管） | 穿透查询核心 |
| `ims_live_person` | 场次 ↔ 实名人（role_type 区分主播/中控/运营） | 分成计算依据 |
| `ims_fin_share_rule` ↔ `ims_live_person`（按分成对象/基数匹配） | 场次人员分成 | 利润分成 |
| `ims_eff_person_relation` | 人员 ↔ 归属目标（IP 组/团队/账号，share_ratio 加权） | 人效盘点 |

### 7.3.3 完整关联链路文本图

```
「实名人 → 账号 → 资产 → 场次 → 成本 → 利润」全链路（成本/利润/分成自 V3 先行批次起由 `ims_fin_*` 承载）：

ims_auth_user_mapping (实名人)
        │ 1
        │        （ims_asset_bind 三元关联表）
        │ N
ims_account_ledger (账号) ──N── ims_account_flow (领用/流转/归还)
        │ 1                       ims_account_charge (冲话费)
        │        （ims_asset_bind）  ims_account_timeline (时间线)
        │ N
ims_asset_ledger (资产) ── ims_asset_hierarchy (穿透层级: parent/path/level)
        │ N
        │        （经 asset_bind.account_id → account → session 间接 + live_person 直接挂人）
        │
ims_live_session (场次, session_id 为编码主键) ── ims_live_schedule (排期)
        │ 1                              ── ims_live_person (场次人员↔实名人)
        │ N
        ├── ims_live_data_snapshot (场次数据回流)
        │
        ├── ims_fin_cost (成本, DECIMAL(12,2)，V3 先行批次)
        │
        │            ▼ 利润引擎预计算（FIN-002）
        └── ims_fin_profit (三级利润 = 毛利/经营/净利)
                     │ 按 ims_fin_share_rule + live_person 分成对象拆分
                     ▼
              ims_fin_share_result（分成结果挂 person_id 回到实名人）
```

穿透查询（V1 关键约束）即沿该链路反查：给定资产 → 找到关联账号 → 找到实名人 → 找到其参与场次 → 汇总成本与利润。详见分期技术约束文档中「穿透查询性能设计」。

## 7.4 数据模型独立交付物说明（V1）

V1 交付一份独立《IMS 数据模型设计文档》（含 ER 图、主键/外键字典），本节给出其核心规范：

### 7.4.1 主键规范

- 所有表主键统一为 `BIGINT(20)` 自增 `id`（芋道 Snowflake ID），业务编码另设唯一索引列（如 `asset_code`、`account_no`）。
- 唯一业务编码列统一加 `UNIQUE KEY`，编码规则集中定义于字典附录。

### 7.4.2 外键字典

外键不建物理约束（便于迁移与分库），应用层校验 + 字典登记：

| 字段 | 引用表 | 说明 |
|------|--------|------|
| account_id | ims_account_ledger | 各流转/冲值/时间线/绑定表 |
| asset_id | ims_asset_ledger | 绑定、层级、索引表 |
| verified_person_id | sys_user（经 ims_auth_user_mapping 映射钉钉） | 一律存 sys_user_id，钉钉 ID 仅存映射表 |
| session_id | ims_live_session | 数据快照、内容任务、财务、分析 |
| subject_id | ims_org_subject | 多主体预留字段（见 7.5） |

### 7.4.3 场次 ID 编码规则（V1 定死，后续不得变更）

格式：**`IMS` + `yyyyMMdd`（8 位日期）+ `3 位平台码` + `4 位当日序列`**，共 19 位字符串。

```
示例：IMS 20250401  DYS  0042  →  IMS20250401DYS0042
      │      │        │     │
      │      │        │     └── 当日按平台自增序列（0001~9999，日切重置）
      │      │        └──────── 平台码（3 位字典：DYS=抖音直播, KS=快手, WX=视频号,
      │      │                    TM=淘宝, JD=京东, OTA=其他，V1 建平台码字典表，可扩展）
      │      └───────────────── 场次创建日期（北京时间，非直播日期）
      └──────────────────────── 固定系统标识，区别于其他系统单号
```

**并发设计要点**（详细方案见分期技术约束 V1 章节）：

1. 日期+平台码维度维护 Redis 序列计数器（`INCR`，原子自增），TTL 48 小时；
2. 落库前由「场次 ID 生成器」统一签发，`ims_live_session.session_id` 列加唯一索引兜底；
3. 当日序列达到 9999 时回退为「日期+平台码+5 位序列」降级策略并告警（单日单平台超 9999 场次极小概率）；
4. 幂等：创建场次接口携带 `client_token`，生成器按 token 去重，防止重试导致跳号或重复。

## 7.5 多租户/多主体设计

### 7.5.1 字段与取值规范

| 规范项 | 约定 |
|--------|------|
| 字段名 | `tenant_id BIGINT NOT NULL DEFAULT 0`，遵循芋道租户规范 |
| 取值 | V1 单主体阶段统一 `0`（默认主体）；未来多主体启用后 `ims_org_subject.subject_id` 提供主体维度 |
| 预留范围 | `ims_asset_ledger`、`ims_account_ledger`、`ims_live_session`、`ims_fin_*`、`ims_content_*` 等**核心业务表全部预留 `tenant_id` 列**（单主体也预留，不做功能） |
| 隔离策略 | 芋道 `TenantLineInnerInterceptor` 自动拼接租户条件，V1 阶段租户过滤开关**关闭**（全表 tenant_id=0），启用时无需改表 |
| 注意事项 | 逻辑外键字典（7.4.2）中的引用关系在多主体启用后必须保证同主体内闭合，禁止跨主体引用 |

### 7.5.2 全表 tenant_id 预留清单（DM-002）

以下 47 张 `ims_` 业务表**全部**预留 `tenant_id` 列（V1 建表即写入，默认 0，不做任何功能逻辑）：

| 分组 | 表 |
|------|-----|
| V1 核心台账 | `ims_org_subject`（主体定义表，多主体启用时唯一非 0 租户来源）、`ims_auth_user_mapping`、`ims_asset_ledger`、`ims_asset_hierarchy`、`ims_asset_bind`、`ims_account_ledger`、`ims_account_flow`、`ims_account_charge`、`ims_cert_archive`、`ims_live_session`、`ims_live_schedule`、`ims_live_person`、`ims_content_sop`、`ims_content_task` |
| V2 流程与绩效 | `ims_flow_template`、`ims_flow_instance`、`ims_report_template`、`ims_report_submission`、`ims_daily_report`、`ims_train_material`、`ims_train_task`、`ims_perf_metric`、`ims_perf_result`、`ims_exam_paper`、`ims_exam_record`、`ims_alert_rule`、`ims_alert_record`、`ims_live_data_snapshot`（下播数据回流） |
| V2.2 批次（AIR） | `ims_skill`、`ims_expert`、`ims_kb`、`ims_api_key` |
| V3 先行批次（财务，由 V2 移入） | `ims_fin_cost`、`ims_fin_profit`、`ims_fin_share_rule`、`ims_fin_share_result` |
| V3 数据与外延 | `ims_comp_asset`、`ims_comp_analysis`、`ims_dc_trace`、`ims_bi_report`、`ims_bi_share_link`、`ims_bi_subscription`、`ims_eff_person_relation`、`ims_eff_metric_config`、`ims_eff_result`、`ims_dws_session_daily`、`ims_dws_person_monthly` |

> 未列出的其余 `ims_` 表（关联表、明细表、字典表）同样遵循「建表即预留」原则，无一例外。

### 7.5.3 多主体启用前置校验（DM-002 · 启用时执行）

多主体从「预留」切换到「启用」前，必须通过以下校验（顺序执行，任一失败即阻断切换）：

1. **存量数据归零校验**：`SELECT COUNT(*) FROM <每张预留表> WHERE tenant_id <> 0` 必须为 0；
2. **主体定义就绪**：`ims_org_subject` 已完成主体建档且 `subject_id` 无冲突（唯一索引校验）；
3. **跨主体引用扫描**：按 7.4.2 逻辑外键字典跑全量闭合校验，输出跨主体引用清单必须为空；
4. **审计留痕开启**：多主体切换动作本身写入 `ims_audit_log`（操作人、时间、切换前后状态）；
5. **灰度开关**：先对单个主体开放（芋道租户过滤开关按主体粒度启用），验证查询/写入隔离后再全量。

### 7.5.4 开发红线

- ❌ 禁止任何业务代码硬编码 `tenant_id = 0` 条件（必须依赖拦截器，否则启用后成为跨主体漏洞）；
- ❌ 禁止在 V1/V2/V3 任何 API 请求参数中暴露 `tenantId`（由登录态会话推导，不接受客户端传入）；
- ✅ 所有新增表 DDL 评审时必须勾查「tenant_id 已预留」项，缺失即打回。

## 7.6 审计字段规范

所有 `ims_` 业务表统一包含以下六字段（与芋道 BaseDO 对齐）：

| 字段 | 类型 | 规范 |
|------|------|------|
| creator | VARCHAR(64) | 创建者（sys_user_id 或钉钉同步任务标记 `dingtalk-sync`） |
| create_time | DATETIME | 创建时间，ISO 8601，默认 CURRENT_TIMESTAMP |
| updater | VARCHAR(64) | 最后更新者 |
| update_time | DATETIME | 最后更新时间，自动更新 |
| deleted | BIT(1) | 逻辑删除位：0=未删，1=已删；唯一索引列需与 deleted 组合处理（deleted=1 时唯一列拼接 id 后缀或改用组合唯一索引 `(biz_code, deleted)`，按芋道规范） |
| tenant_id | BIGINT | 租户/主体预留，默认 0（见 7.5） |

## 7.7 数据迁移规范

### 7.7.1 迁移范围清单

| 类别 | 内容 | 期次要求 |
|------|------|----------|
| **V1 必迁（一次性迁完）** | 人员（含钉钉映射初始全量）、资产台账（含既有 07 部分数据归并）、账号-资产-实名人关联关系 | 第 1~14 周内完成，上线前校验通过 |
| **可后补** | 历史直播场次（场次 ID 按编码规则补签发，日期段取历史日期） | V2 上线前补齐近 6 个月 |
| **不迁** | 历史成本、历史利润、历史分成数据 | 明确不迁移，财务核算自 V2 起从 0 开始记账 |

### 7.7.2 迁移校验规则

1. **数量校验**：源表/Excel 台账行数 = 目标表 `deleted=0` 行数，误差 0 容忍；
2. **抽样比对**：每类数据随机抽 5%（≥50 条）逐字段比对，关键字段（资产编码、账号编号、钉钉 userId、手机号）全量比对；
3. **关联完整性**：`ims_asset_bind` 中每个 asset_id/account_id/verified_person_id 必须能在对应主表命中，孤儿记录进「待补录池」并出清单；
4. **幂等可重跑**：迁移脚本以「源主键+批次号」去重，支持断点重跑；
5. **回滚预案**：迁移前对目标表做全量备份快照，校验不通过回滚并修复后重迁；
6. **审计留痕**：迁移数据 creator 统一标记 `data-migration`，create_time 保留源数据原时间（若有）。

---

# 第 8 章 API 路径规范

## 8.1 全局规范

| 规范项 | 约定 |
|--------|------|
| 统一前缀 | `/admin-api/ims/`（管理端）；如后续开放移动端另设 `/app-api/ims/`，V1 不建设 |
| 风格 | RESTful：GET 查询 / POST 创建 / PUT 更新 / DELETE 删除（逻辑删除） |
| 分页参数 | `pageNo`（页码，1 起）+ `pageSize`（每页，默认 10，最大 100） |
| 响应格式 | `{"code": 0, "msg": "success", "data": {...}}`；非 0 即异常，data 可为 null |
| 时间格式 | ISO 8601（`yyyy-MM-dd'T'HH:mm:ssXXX`），金额单位元、两位小数（DECIMAL(12,2)） |
| 认证 | 钉钉 SSO 换发 IMS JWT（Authorization: Bearer），请求级鉴权走 IMS AUTH（Go），不走芋道 |
| 幂等 | 写接口支持 `client_token` 请求头，关键资源（场次创建、冲话费）强制校验 |
| MCP 网关例外 | AIR 模块对外端点 `/ims/mcp` 不走 SSO Token，使用 `air-` 前缀 API Key（Bearer/URL 参数）自认证；响应遵循 MCP 协议格式而非 `{"code":0}` 包装；限流超限返回 HTTP 429 |

## 8.2 错误码规划

| 区间 | 类别 | 示例 |
|------|------|------|
| 0 | 成功 | — |
| 1001~1999 | 业务错误 | 1001 参数校验失败；1002 资产不存在；1003 账号已被领用；1004 证件已到期；1005 场次 ID 冲突；1006 钉钉同步失败；1007 SOP 步骤不合规；1008 无数据权限；1009 预警规则 DSL 非法；1010 财务期间已结账 |
| 401/403 | 认证/授权 | Token 失效 / 无权限（沿用 HTTP 语义） |
| 5001~5999 | 系统错误 | 5001 DB 异常；5002 Redis 异常；5003 钉钉接口超时；5004 ComfyUI 队列满；5005 文件落盘失败；5006 定时任务调度失败；5007/5008 已移除（原 RAGFlow 检索超时/组件不健康；v2.6.34 号位作废） |

## 8.3 各期各模块 API 前缀分配表

所有模块 API 为：`/admin-api/ims/{module}/{resource}`。

### V1（第 1~14 周）

| 模块 | 前缀 | 典型端点 |
|------|------|----------|
| 01 权限 | `/auth` | GET /auth/user/sync-status、POST /auth/role/matrix、GET /auth/data-scope |
| 07 资产 | `/asset` | GET /asset/ledger/page、GET /asset/{id}/penetrate（穿透）、POST /asset/bind |
| 08 账号 | `/account` | POST /account/flow/apply（领用）、POST /account/flow/transfer、POST /account/flow/return、POST /account/charge、GET /account/{id}/timeline |
| 06 证件 | `/cert` | POST /cert/archive、GET /cert/{id}/file（带水印）、GET /cert/expire/warnings |
| 10 直播 | `/live` | POST /live/session（生成场次 ID）、GET /live/session/page、POST /live/schedule、GET /live/session/{id}/data |
| 15 内容 | `/content` | GET /content/sop/page、POST /content/task、POST /content/ai-job/submit、GET /content/ai-job/{id}/status |
| 数据模型 | `/model` | GET /model/entity/page（模型字典查询，独立交付物的在线版） |
| 钉钉集成 | 见 8.4 | — |

### V2（第 15~27 周）

| 模块 | 前缀 | 典型端点 |
|------|------|----------|
| 02 培训 | `/train` | POST /train/material、POST /train/task、PUT /train/task/{id}/progress |
| 03 会议/日报 | `/meet` / `/report` | POST /meet/minutes、PUT /meet/daily（日报提交/审阅，与 09 上报共用 `/report` 按子域划分：`/report/template` 等） |
| 09 数据上报 | `/report` | POST /report/template、POST /report/submit、POST /report/audit |
| 14 工作流 | `/flow` | POST /flow/template、POST /flow/instance/start |
| 05 绩效 | `/perf` | GET /perf/metric/page、POST /perf/calc/run、POST /perf/exam/paper |
| 13 预警 | `/alert` | POST /alert/rule、GET /alert/record/page、POST /alert/record/{id}/escalate |
| 定时任务 | `/schedule`（内部） | GET /schedule/job/status（心跳监控查询） |

> 期次口径说明：11 财务核算（`/fin`）已由 V2 移至 V3 先行批次（见 V3 段）；AIR（模块 20）为 V2.2 批次（并入第二期），前缀见下段。

### V2.2 批次（AIR 模块 20，并入第二期，第 19~20 周起 AIR-P0 先行）

管理端走统一前缀 `/admin-api/ims/air/`；对外 MCP 网关为**独立端点**，不走管理端前缀与 SSO Token 认证（Key 自成体系）。

| 模块 | 前缀 | 典型端点 |
|------|------|----------|
| 20.1 技能 | `/air/skill` | GET /air/skill/page、POST /air/skill、POST /air/skill/{id}/audit、POST /air/skill/grant |
| 20.2 专家 | `/air/expert` | GET /air/expert/page、POST /air/expert、POST /air/expert/grant |
| 20.3 知识 | `/air/kb` | GET /air/kb/page、POST /air/kb/doc/upload、POST /air/kb/doc/import-url、POST /air/kb/doc/audit、POST /air/kb/grant |
| 20.4 Key | `/air/key` | POST /air/key/generate、POST /air/key/{id}/revoke、POST /air/key/{id}/freeze、GET /air/key/config-snippet?client=cursor、GET /air/key/whitelist、POST /air/key/whitelist |
| 用量/审计 | `/air/usage` / `/air/mcp` | GET /air/usage/stat?by=person、GET /air/mcp/audit-log |
| 系统参数 | `/air/sys-param` | GET /air/sys-param、PUT /air/sys-param（含 air.key.ip_whitelist.enabled、air.kb.provider） |
| **MCP 网关** | `/ims/mcp`（独立，非 admin-api） | MCP Streamable HTTP + SSE；认证：Header `Authorization: Bearer air-xxx` 优先，URL `?key=` 兼容；工具：skills.list / skills.get / experts.list / experts.assemble（固定四工具；knowledge.search/get v2.6.34 已移除） |

### V3（第 28~38 周）

| 模块 | 前缀 | 典型端点 |
|------|------|----------|
| 04 竞品 | `/comp` | POST /comp/analysis、GET /comp/analysis/list、GET /comp/asset/list |
| 12 穿透查询 | `/dc` | GET /dc/trace/entry、POST /dc/trace/query、GET /dc/profit-trace/list、GET /dc/dashboard/overview |
| 17 数据分析 | `/bi` | POST /bi/report（自助报表定义）、POST /bi/report/{id}/drill、POST /bi/subscription |
| 19 组织人效 | `/eff` | GET /eff/relation/list、GET /eff/relation/coverage、POST /eff/metrics/calc |
| 11 财务核算 | `/fin` | POST /fin/cost/{sessionCode}、GET /fin/profit/{sessionCode}、POST /fin/share/simulate、GET /fin/dashboard/overview |

> 前缀口径说明：本表前缀已与各期 PRD 5.x 及 API 契约对齐（旧口径对照：04 `/competitor` → `/comp`、12 `/dw` → `/dc`、17 `/analysis` → `/bi`、19 `/efficiency` → `/eff`；11 财务由 V2 `/finance` 移入并改 `/fin`，第 28~33 周先行交付）。

## 8.4 钉钉集成 API 规范

钉钉为唯一组织/权限同步源，集成通道分三类：

### 8.4.1 SSO 回调

| 端点 | 说明 |
|------|------|
| `GET /sso/dingtalk/callback?authCode=xxx&state=xxx` | IMS 自建钉钉 SSO 回调；用 authCode 换 userid → **必须已绑 mobile** → HTTP 对上 `system_users.id` → 查/写 `ims_auth_user_mapping`；state 防 CSRF，有效期 5 分钟 |

### 8.4.2 事件订阅回调

| 端点 | 说明 |
|------|------|
| `POST /callback/dingtalk/event` | 接收钉钉事件推送（通讯录变更：user_add/user_modify/user_leave、部门变更、角色变更）；必须按钉钉规范先返回加密 echo 校验；事件解析后写入**重试队列**（见 V1 技术约束：重试队列+幂等+全量对账补偿） |
| 幂等键 | `dingtalk_event_id + event_type`，已处理事件直接返回成功 |

### 8.4.3 全量对账补偿接口

| 端点 | 说明 |
|------|------|
| `POST /callback/dingtalk/reconcile` | 触发全量对账补偿（管理端手动触发或每日 02:00 定时触发）：拉取钉钉全量部门+人员 → 与 `ims_auth_user_mapping` 比对 → 差异修正（新增/更新/标记离职）→ 输出对账报告 |
| `GET /callback/dingtalk/reconcile/report` | 查询最近一次对账结果（差异数、修正数、失败明细） |
| `POST /callback/dingtalk/retry-queue/replay` | 重放失败事件队列（按事件时间区间） |

---

*本文档为共享技术规范，与《共享技术规范-分期技术约束.md》配套使用；各期 PRD 引用本文档第 7、8 章时不再重复内容。*
