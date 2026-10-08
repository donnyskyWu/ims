# GLOBAL-CONVENTIONS（全局规范）

> **项目级全局规范**：所有模块的**关联属性**、**数据字典**、**状态/类型/平台/方式**等枚举必须遵循本文档
> **版本**：v1.0 | 2026-06-07
> **状态**：✅ Accepted
> **优先级**：🔴 硬性（违反 → 阻断合并）
> **关联**：`docs/engineering/TECH-CONSTRAINTS.md`、`AGENTS.md`
> **订正记录**：2026-10-03 — §3 数据字典订正 2 项：`dict_perf_metric_type` 实为「基础指标/复合指标」（M6，原记 M3 绩效语境）；`dict_query_status` 现网硬编码 DRAFT/PUBLISHED（原记含「已停用」，字典映射待实现）。依据：现网 `football-front/apps/web-ele/src/mock/ops/dict.ts` + `views/ops/analysis/MetricManage.vue` + `CustomQuery.vue`。

---

## 1. 三大铁律

### 🔴 铁律一：关联属性必须用"选择器"，禁止手动填写

**适用范围**：所有指向另一实体的外键属性（如下拉、单选、多选、级联选择等）。

**正例**：
- 公众号 → 实名人：使用 `RealNameSelect` 选择器，从"实名人管理"中选
- 作者 → IP 组：使用 `IpGroupTreeSelect`（仅可选 SMALL）
- 主推号 → 平台账号：使用 `PlatformAccountSelect`（仅 OFFICIAL_ACCOUNT 类型）
- 作品监测 → 监测账号：使用 `AccountSelect`

**反例（禁止）**：
- ❌ 手动输入实名人姓名
- ❌ 手动输入 IP 组名（必须从树形选择）
- ❌ 手动输入平台账号 ID（必须从选择器）

**校验**：
- 前端：选择器组件禁用"自定义输入"
- 后端：API 入参接收 `id`（外键 ID），不接收 `name`；DTO 上用 `@NotNull Long xxxId` 强制要求 ID
- 测试：构造"传 name 不传 id"的请求 → 返回错误码

---

### 🔴 铁律二：枚举属性（方式/状态/类型/平台等）必须从数据字典选择

**适用范围**：所有有限集合的离散值属性，类型为：
- 方式（method / way / mode）
- 状态（status / state）
- 类型（type / category）
- 平台（platform / channel）
- 等级（level / grade）
- 性别、证件类型、来源、原因等

**正例**：
```yaml
作品类型:  # 字典 dict_content_type
  - 短视频
  - 文章
  - 图文
  - 直播
  - 音频

账号状态:  # 字典 dict_account_status
  - 正常
  - 异常
  - 封禁
  - 注销
```

**反例（禁止）**：
- ❌ 前端写死 `<option value="SHORT_VIDEO">短视频</option>`
- ❌ 后端写 `private static final String TYPE_VIDEO = "VIDEO";`
- ❌ 数据库用 `ENUM('A','B','C')`

**实现要求**：

1. **数据字典表** `sys_dict_type` + `sys_dict_data`（沿用 yudao 框架）
2. **字典项** 通过 `## 9. 系统管理` 的字典管理维护
3. **API** 提供 `GET /admin-api/oa/dict/data?type={dict_type}` 拉取字典项（ADR-006）
4. **前端** 使用 `<DictSelect dict-type="dict_content_type" />` 组件自动加载
5. **后端校验**：使用 `@InDict(type="dict_content_type")` 自研注解，校验入参必须在字典内

---

### 🔴 铁律三：实体关系必须在 ER 图中明确，禁止"魔法外键"

**适用范围**：所有跨实体的关联关系。

**要求**：
- 任何新增的外键字段，必须在 `docs/engineering/ER-DIAGRAM.md` 中体现
- 任何修改外键关系（如改"多对一"为"多对多"），必须先开 ADR
- 删除实体时，**先关闭所有外键引用**（或软删除）

---

## 2. 数据字典总表

> 所有字典 type 必须先在此登记，**未登记的字典 type 一律不得使用**。
> 维护方式：通过 `## 9. 系统管理 > 字典管理` 维护；新增字典 type 需开 ADR。

### 2.1 业务枚举字典

| 字典 type | 名称 | 用途 | 关联模块 |
|-----------|------|------|----------|
| `dict_platform_type` | 平台类型 | 公众号/视频号/抖音/快手/小红书/服务号/企微/个微 | M1/M4/M7 |
| `dict_account_type` | 账号类型 | OFFICIAL_ACCOUNT(公众号/服务号) / DOUYIN / KUAISHOU / XIAOHONGSHU / WEWORK / WX_PERSONAL / VIDEO_ACCOUNT | M4 |
| `dict_account_status` | 账号状态 | 正常 / 异常 / 封禁 / 注销 | M1/M4 |
| `dict_account_role` | 账号角色 | 主号(PRIMARY) / 副号(SECONDARY) / 备用号(BACKUP) | M1 |
| `dict_ip_group_type` | IP 组类型 | 大组(BIG) / 小组(SMALL) | M1 |
| `dict_ip_group_status` | IP 组状态 | 启用 / 停用 | M1 |
| `dict_position` | 岗位 | OPS_LEADER / OPERATOR / ANCHOR / EDITOR / LIVE_OPERATOR / SALES | M1 |
| `dict_author_type` | 作者类型 | 直播(LIVE) / 短视频(SHORT_VIDEO) / 两者(BOTH) | M1 |
| `dict_author_status` | 作者状态 | 启用 / 停用 | M1 |
| `dict_content_type` | 内容类型 | 短视频 / 文章 / 图文 / 直播 / 音频 | M1/M6/M7 |
| `dict_content_import_type` | 补录类型 | API_EXCEPTION / ACCOUNT_BANNED / OFFLINE_PRACTICE / OTHER | M1 |
| `dict_data_source` | 数据来源 | API / IMPORT | M1/M6 |
| `dict_collect_method` | 采集方式 | 内部采集 / 外部采集 / 第三方API / 手工录入 | M10 |
| `dict_collect_status` | 采集状态 | 待执行 / 执行中 / 成功 / 失败 / 部分成功 | M10 |
| `dict_collect_frequency` | 采集频率 | 实时 / 每小时 / 每天 / 每周 / 每月 / 手动 | M10 |
| `dict_collect_source` | 采集源 | 公众号API / 视频号API / 抖音开放平台 / 快手开放平台 / 奥创接口 / 企微API / 个微API | M10 |
| `dict_quality_check_type` | 数据质量检查类型 | 完整性 / 准确性 / 一致性 / 时效性 / 唯一性 | M10 |
| `dict_quality_level` | 数据质量等级 | 优 / 良 / 中 / 差 | M10 |
| `dict_sop_node_type` | SOP 节点类型 | 内容生成(CONTENT_GENERATION) / 内容发布(CONTENT_PUBLISH) / 普通节点(NORMAL) | M2（ADR-016） |
| `dict_document_type` | 文档类型 | 短视频文案 / 新号引流 / 赛后复盘 / 正式方案 / 预热前瞻 | M2（ADR-016） |
| dict_content_body_format | 正文格式 | PLAIN(纯文本) / LAYOUT(富版式) | M2（ADR-019） |
| dict_layout_template_status | 公推模板状态 | DRAFT / ENABLED / DISABLED | M2（ADR-019） |
| dict_layout_template_source | 公推模板来源 | MANUAL / URL / DOCX / PASTE | M2（ADR-019） |
| `dict_sop_node_status` | SOP 节点状态 | 待办 / 进行中 / 已完成 / 已驳回 / 已跳过 | M2 |
| `dict_sop_status` | SOP 流程状态 | 草稿 / 审核中 / 已发布 / 已停用 | M2 |
| `dict_plan_status` | 计划状态 | 草稿(DRAFT) / 进行中(IN_PROGRESS) / 终止审批中(TERMINATE_PENDING) / 已终止(TERMINATED) | M2 |
| `dict_content_status` | 内容状态 | 草稿 / 已完成 / 待一级审核 / 待二级审核 / 待终审(遗留) / 待发布 / 已驳回 / 已发布 / 已下架 | M2（ADR-016/017/022） |
| `dict_content_review_result` | 审核结果 | 通过 / 驳回 / 需修改 | M2 |
| `dict_perf_metric_type` | 指标类型 | 基础指标(BASIC) / 复合指标(COMPOSITE) | M6（2026-10-03 订正：原记「数量/质量/营收/增长率/复合」为 M3 绩效语境误植，现网 `mock/ops/dict.ts` 与 `MetricManage.vue` 实为两项；字典当前**仅 M6 指标管理**使用） |
| `dict_perf_calc_method` | 算分方式 | 自动算分 / 人工算分 / 混合 | M3 |
| `dict_perf_status` | 绩效状态 | 草稿 / 计算中 / 已计算 / 已审核 / 已发放 | M3 |
| `dict_perf_period` | 考核周期 | 周 / 月 / 季 / 年 / 自定义 | M3 |
| `dict_company_status` | 公司状态 | 启用 / 停用 | M4 |
| `dict_realname_status` | 实名人状态 | 启用 / 停用 | M4 |
| `dict_phone_status` | 手机状态 | 在用 / 闲置 / 损坏 / 丢失 | M4 |
| `dict_phone_type` | 手机类型 | Android / iPhone | M4（V85） |
| `dict_sim_status` | 手机卡状态 | 在用 / 闲置 / 停机 / 注销 / **损坏** / **丢失** | M4（V85 扩展后两值） |
| `dict_qualification_type` | 资质类型 | 企业 / 个人 | M4（V86） |
| `dict_wechat_usage_status` | 公众号使用状态 | 注册 / 认证 / 续费 | M4（V86） |
| `dict_id_type` | 证件类型 | 身份证 / 护照 / 港澳通行证 / 台湾通行证 | M4 |
| `dict_cost_type` | 成本类型 | 购买成本 / 过程成本(人力) / 过程成本(设备) / 过程成本(运营) | M5 |
| `dict_cost_pay_method` | 付款方式 | 现金 / 转账 / 支付宝 / 微信 / 银行承兑 | M5 |
| `dict_cost_period` | 成本归属周期 | 一次性 / 月度 / 季度 / 年度 | M5 |
| `dict_report_type` | 报表类型 | 全平台账号视图 / 账号状态监控 / 短视频产出 / 直播时长 / 账号成本分摊 / ROI 分析 / IP团队人员配置 / 账号异常预警 | M6 |
| `dict_report_period` | 报表周期 | 实时 / 日 / 周 / 月 / 季 / 年 | M6 |
| `dict_funnel_type` | 漏斗类型 | 关注转化 / 阅读转化 / 互动转化 / 订单转化 / 自定义 | M6 |
| `dict_query_status` | 自定义查询状态 | 草稿(DRAFT) / 已发布(PUBLISHED)（**现网硬编码**，未接字典） | M6（2026-10-03 订正：原记「草稿 / 已发布 / 已停用」，现网 `CustomQuery.vue` 硬编码 DRAFT/PUBLISHED 两项；`oa_query.status` 的 N:1 字典映射**待实现**） |
| `dict_dashboard_type` | 大屏类型 | 实时大屏 / 业务大屏 / 汇报大屏 / 监控大屏 | M6 |
| `dict_monitor_level` | 监测等级 | 重点 / 普通 / 临时 | M7 |
| `dict_monitor_status` | 监测状态 | 启用 / 暂停 / 已结束 | M7 |
| `dict_alert_level` | 预警级别 | 高 / 中 / 低 / 提示 | M6/M7/M10 |
| `dict_alert_status` | 预警状态 | 待处理 / 处理中 / 已处理 / 已忽略 / 已关闭 | M6/M7 |
| `dict_alert_type` | 预警类型 | 阈值预警 / 漏斗预警 / 异常预警 / 自定义 | M6 |
| `dict_audit_module` | 审计模块 | IP组 / 作者 / 账号 / 作品 / 数据补录 / 财务 / 系统 | 通用 |
| `dict_audit_action` | 审计动作 | 创建 / 修改 / 删除 / 启用 / 停用 / 审核通过 / 审核驳回 / 撤回 / 导出 | 通用 |
| `dict_yes_no` | 是否 | 是 / 否 | 通用 |
| `dict_gender` | 性别 | 男 / 女 / 未知 | M4 |
| `dict_user_status` | 用户状态 | 启用 / 停用 / 锁定 | M9 |
| `dict_tenant_status` | 租户状态 | 正常 / 试用 / 已到期 / 已停用 | M9 |
| `dict_log_level` | 日志级别 | INFO / WARN / ERROR | M9 |
| `dict_log_module` | 日志模块 | OA / 系统 / 认证 / 第三方 | M9 |



| `dict_intermediary_relation` | 中介人关系类型 | DIRECT(直签) / INTERMEDIARY(中介代理) / AGENCY(机构合作) | M4 |
| `dict_ai_model` | AI 模型 | GPT-3.5 / GPT-4 / Claude / Gemini / 通义千问 | M2 / M8 |
| `dict_ai_model_type` | AI 模型类型 | 通义千问(QWEN) / 文心(ERNIE) / 智谱(GLM) / DeepSeek / Kimi / 豆包 / GPT / Claude / Gemini / 月之暗面 等 | M8（V69） |
| `dict_review_stage` | 审核阶段 | FIRST_REVIEW(初审) / SECOND_REVIEW(复审) / FINAL_REVIEW(终审) | M2 |
| `dict_sim_operator` | 运营商 | MOBILE(移动) / UNICOM(联通) / TELECOM(电信) | M4 |

#
| `dict_audit_status` | audit status | 详见 M9 审计状态 模块 | M9 |
| `dict_auth_status` | auth status | 详见 M10 凭据状态 模块 | M10 |
| `dict_auth_type` | auth type | 详见 M10 认证类型 模块 | M10 |
| `dict_collect_freq` | collect freq | 详见 M10 采集频率 模块 | M10 |
| `dict_collect_type` | collect type | 详见 M10 采集类型 模块 | M10 |
| `dict_config_type` | config type | 详见 M8 配置类型 模块 | M8 |
| `dict_currency` | currency | 详见 M5 币种 模块 | M5 |
| `dict_export_format` | export format | 详见 M6 导出格式 模块 | M6 |
| `dict_finance_status` | finance status | 详见 M5 财务状态 模块 | M5 |
| `dict_finance_type` | finance type | 详见 M5 财务类型 模块 | M5 |
| `dict_log_type` | log type | 详见 M9 日志类型 模块 | M9 |
| `dict_metric_type` | metric type | 详见 M6 指标类型 模块 | M6 |
| `dict_monitor_freq` | monitor freq | 详见 M7 监测频率 模块 | M7 |
| `dict_pay_method` | pay method | 详见 M5 支付方式 模块 | M5 |
| `dict_proxy_type` | proxy type | 详见 M10 代理类型 模块 | M10 |
| `dict_report_dim` | report dim | 详见 M6 报表维度 模块 | M6 |
| `dict_time_range` | time range | 详见 M6 时间范围 模块 | M6 |
| `dict_user_role` | user role | 详见 M9 用户角色 模块 | M9 |
| `dict_value_type` | value type | 详见 M8 值类型 模块 | M8 |
| `dict_voucher_type` | voucher type | 详见 M5 凭证类型 模块 | M5 |
| `dict_work_type` | work type | 详见 M7 作品类型 模块 | M7 |
| `dict_effective_range` | effective range | 详见 M8 生效范围 模块 | M8 |
| `dict_knowledge_category` | knowledge category | 详见 M8 知识分类 模块 | M8 |

## 2.2 跨模块共用字典

| 字典 type | 名称 | 用途 | 关联模块 |
|-----------|------|------|----------|
| `dict_platform_type` | 平台类型 | 全部模块 | M1/M4/M6/M7/M10 |
| `dict_data_source` | 数据来源 | API/IMPORT 标识 | M1/M6/M7 |
| `dict_yes_no` | 是否 | 通用 | 全部 |
| `dict_audit_*` | 审计相关 | 操作审计 | 全部 |

---

## 3. 关联属性清单（实体关系图）

> 所有跨实体的关联通过本表登记，**未登记的关联一律不得新增**。

### 3.1 核心实体关系（11 类强关系）

| From 实体 | 字段 | To 实体 | 关系 | 必填 | 说明 |
|-----------|------|---------|------|------|------|
| `oa_ip_group` | `parent_id` | `oa_ip_group` | N:1 | 小组必填 | 小组必须挂在某大组下 |
| `oa_ip_group_member` | `ip_group_id` | `oa_ip_group` | N:1 | ✅ | 成员归属 IP 组 |
| `oa_ip_group_member` | `user_id` | `sys_user` | N:1 | ✅ | 成员为系统用户 |
| `oa_ip_group_account_rel` | `ip_group_id` | `oa_ip_group` | N:1 | ✅ | 账号-IP 组关联 |
| `oa_ip_group_account_rel` | `account_id` | `oa_account` | N:1 | ✅ | 关联账号 |
| `oa_ip_group_anchor_rel` | `ip_group_id` | `oa_ip_group` | N:1 | ✅ | 主播-IP 组关联 |
| `oa_ip_group_anchor_rel` | `anchor_user_id` | `sys_user` | N:1 | ✅ | 主播为系统用户 |
| `oa_author` | `ip_group_id` | `oa_ip_group` | N:1 | ✅ | 作者归属 IP 组（仅 SMALL） |
| `oa_author` | `primary_account_id` | `oa_account` | N:1 | ❌ | 主推号（OFFICIAL_ACCOUNT） |
| `oa_author` | `user_id` | `sys_user` | N:1 | ❌ | 作者系统用户 |
| `oa_ops_anchor_rel` | `ops_user_id` | `sys_user` | N:1 | ✅ | 运营人员 |
| `oa_ops_anchor_rel` | `anchor_user_id` | `sys_user` | N:1 | ✅ | 主播 |
| `oa_ops_anchor_rel` | `ip_group_id` | `oa_ip_group` | N:1 | ✅ | 关联 IP 组 |
| `oa_account` | `ip_group_id` | `oa_ip_group` | N:1 | ❌ | 账号归属 IP 组 |
| `oa_account` | `platform_type` | `dict_platform_type` | N:1 | ✅ | 平台类型（字典） |
| `oa_account` | `account_type` | `dict_account_type` | N:1 | ✅ | 账号类型（字典） |
| `oa_account` | `account_status` | `dict_account_status` | N:1 | ✅ | 状态（字典） |
| `oa_account` | `realname_id` | `oa_realname` | N:1 | ❌ | 绑定实名人（**强关联**）⭐ |
| `oa_account` | `phone_id` | `oa_phone` | N:1 | ❌ | 绑定手机（强关联）⭐ |
| `oa_account` | `sim_card_id` | `oa_sim_card` | N:1 | ❌ | 绑定手机卡（强关联）⭐ |
| `oa_account` | `company_id` | `oa_company` | N:1 | ❌ | 归属公司（强关联）⭐ |
| `oa_account` | `intermediary_id` | `oa_realname` | N:1 | ❌ | 中介人（实名人表，强关联）⭐ |
| `oa_content` | `account_id` | `oa_account` | N:1 | ✅ | 作品归属账号 |
| `oa_content` | `content_type` | `dict_content_type` | N:1 | ✅ | 内容类型（字典） |
| `oa_content_data_import` | `content_id` | `oa_content` | N:1 | ✅ | 补录关联作品 |
| `oa_content_data_import` | `import_type` | `dict_content_import_type` | N:1 | ✅ | 补录类型（字典） |
| `oa_content_daily` | `content_id` | `oa_content` | N:1 | ✅ | 作品每日数据 |
| `oa_content_daily` | `data_source` | `dict_data_source` | N:1 | ✅ | 数据来源（字典） |
| `oa_follower_daily` | `account_id` | `oa_account` | N:1 | ✅ | 粉丝每日数据 |
| `oa_realname` | `id_type` | `dict_id_type` | N:1 | ✅ | 证件类型（字典） |
| `oa_realname` | `gender` | `dict_gender` | N:1 | ❌ | 性别（字典） |
| `oa_realname` | `status` | `dict_realname_status` | N:1 | ✅ | 状态（字典） |
| `oa_company` | `status` | `dict_company_status` | N:1 | ✅ | 状态（字典） |
| `oa_phone` | `status` | `dict_phone_status` | N:1 | ✅ | 状态（字典） |
| `oa_sim_card` | `status` | `dict_sim_status` | N:1 | ✅ | 状态（字典） |
| `oa_sim_card` | `linked_account_id` | `oa_account` | N:1 | ❌ | 关联账号（强关联）⭐ |
| `oa_account_cost` | `account_id` | `oa_account` | N:1 | ✅ | 账号成本 |
| `oa_account_cost` | `cost_type` | `dict_cost_type` | N:1 | ✅ | 成本类型（字典） |
| `oa_account_cost` | `pay_method` | `dict_cost_pay_method` | N:1 | ✅ | 付款方式（字典） |
| `oa_account_cost` | `period` | `dict_cost_period` | N:1 | ✅ | 归属周期（字典） |
| `oa_perf_template` | `metric_type` | `dict_perf_metric_type` | N:1 | ✅ | 指标类型（字典） |
| `oa_perf_template` | `period` | `dict_perf_period` | N:1 | ✅ | 考核周期（字典） |
| `oa_perf_record` | `status` | `dict_perf_status` | N:1 | ✅ | 状态（字典） |
| `oa_sop_template` | `status` | `dict_sop_status` | N:1 | ✅ | 状态（字典） |
| `oa_sop_node` | `node_type` | `dict_sop_node_type` | N:1 | ✅ | 节点类型（字典） |
| `oa_sop_node` | `status` | `dict_sop_node_status` | N:1 | ✅ | 状态（字典） |
| `oa_content_plan` | `status` | `dict_plan_status` | N:1 | ✅ | 计划状态（字典） |
| `oa_content_plan` | `template_id` | `oa_sop_template` | N:1 | ❌ | SOP 模板（**强关联**）⭐ |
| `oa_content_plan` | `ip_group_id` | `oa_ip_group` | N:1 | ❌ | IP 组（**强关联**）⭐ |
| `oa_task` | `plan_id` | `oa_content_plan` | N:1 | ❌ | 计划关联任务 |
| `oa_task` | `competition_id` | 外部赛事 | N:1 | ❌ | 步骤分配赛事（ADR-016） |
| `oa_content` | `task_id` | `oa_task` | N:1 | ❌ | 任务-内容关联（0..1） |
| `oa_content` | `competition_id` | 外部赛事 | N:1 | ❌ | 关联赛事 |
| `oa_content` | `document_type` | `dict_document_type` | N:1 | ✅ | 文档类型（ARTICLE 时） |
| `oa_content_plan_step` | `competition_id` | 外部赛事 | N:1 | ❌ | 步骤赛事（**强关联**选择器） |
| oa_wechat_layout_template | document_type | dict_document_type | N:1 | 可空 | 模板适用文档类型 |
| oa_wechat_layout_template | status | dict_layout_template_status | N:1 | 是 | 模板状态（字典） |
| oa_wechat_layout_template | source_type | dict_layout_template_source | N:1 | 是 | 来源（字典） |
| oa_production_content | ody_format | dict_content_body_format | N:1 | 是 | 正文格式（字典） |
| oa_production_content | layout_template_id | oa_wechat_layout_template | N:1 | 可空 | 应用过的模板（非强绑定） |
| `oa_collect_task` | `source` | `dict_collect_source` | N:1 | ✅ | 采集源（字典） |
| `oa_collect_task` | `frequency` | `dict_collect_frequency` | N:1 | ✅ | 采集频率（字典） |
| `oa_collect_task` | `status` | `dict_collect_status` | N:1 | ✅ | 状态（字典） |
| `oa_data_quality_check` | `check_type` | `dict_quality_check_type` | N:1 | ✅ | 检查类型（字典） |
| `oa_data_quality_check` | `level` | `dict_quality_level` | N:1 | ✅ | 质量等级（字典） |
| `oa_alert` | `alert_type` | `dict_alert_type` | N:1 | ✅ | 预警类型（字典） |
| `oa_alert` | `level` | `dict_alert_level` | N:1 | ✅ | 预警级别（字典） |
| `oa_alert` | `status` | `dict_alert_status` | N:1 | ✅ | 预警状态（字典） |
| `oa_report` | `report_type` | `dict_report_type` | N:1 | ✅ | 报表类型（字典） |
| `oa_report` | `period` | `dict_report_period` | N:1 | ✅ | 报表周期（字典） |
| `oa_dashboard` | `dashboard_type` | `dict_dashboard_type` | N:1 | ✅ | 大屏类型（字典） |
| `oa_funnel` | `funnel_type` | `dict_funnel_type` | N:1 | ✅ | 漏斗类型（字典） |
| `oa_query` | `status` | `dict_query_status` | N:1 | ✅ | 查询状态（字典） |
| `oa_monitor_task` | `level` | `dict_monitor_level` | N:1 | ✅ | 监测等级（字典） |
| `oa_monitor_task` | `status` | `dict_monitor_status` | N:1 | ✅ | 监测状态（字典） |
| `oa_user` | `status` | `dict_user_status` | N:1 | ✅ | 用户状态（字典） |
| `oa_tenant` | `status` | `dict_tenant_status` | N:1 | ✅ | 租户状态（字典） |

### 3.2 关键强关联说明（⭐）

#### (1) 账号 ↔ 实名人/手机/手机卡/公司

- `oa_account.realname_id` → `oa_realname.id`：**必须从实名人管理列表中选择**（前端禁用手动输入）
- `oa_account.phone_id` → `oa_phone.id`：**必须从手机管理列表中选择**
- `oa_account.sim_card_id` → `oa_sim_card.id`：**必须从手机卡管理列表中选择**
- `oa_account.company_id` → `oa_company.id`：**必须从公司管理列表中选择**
- `oa_account.intermediary_id` → `oa_realname.id`：**中介人也是实名人，复用实名人表**

#### (2) 选择器约束

- 只能选 `status=启用` 的实体（停用/注销的不可选）
- 跨租户隔离：只能选本租户的实体
- 已绑定到其他账号的**手机/手机卡**：默认不可选，需提供"强制替换"操作
- **实名人**（ADR-062）：允许同时关联多个账号（1:N）；选择器不排除已绑定；后端不对 `realnameId` 返回 1502

---

## 4. 前端选择器组件约定

### 4.1 通用选择器组件

| 组件 | 用途 | 入参 | 出参 |
|------|------|------|------|
| `<RealNameSelect />` | 选实名人 | `status`, `gender`, `isIntermediary` | `realnameId` |
| `<PhoneSelect />` | 选手机 | `status` | `phoneId` |
| `<SimCardSelect />` | 选手机卡 | `status`, `phoneId`(联动) | `simCardId` |
| `<CompanySelect />` | 选公司 | `status` | `companyId` |
| `<AccountSelect />` | 选平台账号 | `platformType`, `accountType`, `ipGroupId` | `accountId` |
| `<IpGroupTreeSelect />` | 选 IP 组（树形） | `groupType`(可限定 SMALL/BIG) | `ipGroupId` |
| `<UserSelect />` | 选系统用户 | `status`, `position`, `ipGroupId` | `userId` |
| `<DictSelect dict-type="xxx" />` | 选字典项 | `dictType` | `value` |

### 4.2 选择器校验

- 必填：显示红 `*`；未选时提交报错
- 联动：上游选择变化时，下游选择器自动清空 + 重新拉取
- 显示：默认显示"名称 + 关键标识"（如"张三 (138****8000)"）
- 搜索：远端搜索（输入 ≥ 1 字符触发）
- 分页：单选不需要；多选支持"全选/反选/清空"

---

## 5. 后端校验约定

### 5.1 DTO 校验

```java
public class AccountCreateReq {
    @NotNull(message = "实名人不能为空")
    private Long realnameId;  // 强关联：必传 ID，不接收 name
    
    @NotNull(message = "平台账号不能为空")
    private Long platformType;  // 字典值
    
    @InDict(type = "dict_platform_type", message = "平台类型不合法")
    private String platform;
    
    @InDict(type = "dict_account_type", message = "账号类型不合法")
    private String accountType;
    
    // ...
}
```

### 5.2 业务校验（Service 层）

- 实名人/手机/手机卡/公司的 `status` 必须为启用
- 跨租户校验：实名人等必须属于当前 `tenant_id`
- 唯一性校验：同一实名人不能被多个账号绑定（除非"强制替换"）

### 5.3 错误码

| 错误码 | 含义 |
|--------|------|
| 1500 | 关联的实体不存在 |
| 1501 | 关联的实体已停用/注销 |
| 1502 | 关联的实体已被其他记录引用 |
| 1503 | 字典值不合法 |
| 1504 | 跨租户访问禁止 |

---

## 6. 字典项管理

### 6.1 字典项位置

- 表：`sys_dict_type`（字典类型）、`sys_dict_data`（字典项）
- 维护入口：`## 9. 系统管理 > 字典管理`
- API：`GET /admin-api/oa/dict/data?type={dictType}`（ADR-006）

### 6.2 字典项结构

```json
{
  "dictType": "dict_platform_type",
  "dictLabel": "公众号",
  "dictValue": "WECHAT_OFFICIAL",
  "sort": 1,
  "status": 0,
  "colorType": "default",
  "remark": "微信公众号"
}
```

### 6.3 新增字典流程

1. 在 `## 9. 系统管理 > 字典管理` 新增字典 type
2. 在 `
| `dict_audit_status` | audit status | 详见 M9 审计状态 模块 | M9 |
| `dict_auth_status` | auth status | 详见 M10 凭据状态 模块 | M10 |
| `dict_auth_type` | auth type | 详见 M10 认证类型 模块 | M10 |
| `dict_collect_freq` | collect freq | 详见 M10 采集频率 模块 | M10 |
| `dict_collect_type` | collect type | 详见 M10 采集类型 模块 | M10 |
| `dict_config_type` | config type | 详见 M8 配置类型 模块 | M8 |
| `dict_currency` | currency | 详见 M5 币种 模块 | M5 |
| `dict_export_format` | export format | 详见 M6 导出格式 模块 | M6 |
| `dict_finance_status` | finance status | 详见 M5 财务状态 模块 | M5 |
| `dict_finance_type` | finance type | 详见 M5 财务类型 模块 | M5 |
| `dict_log_type` | log type | 详见 M9 日志类型 模块 | M9 |
| `dict_metric_type` | metric type | 详见 M6 指标类型 模块 | M6 |
| `dict_monitor_freq` | monitor freq | 详见 M7 监测频率 模块 | M7 |
| `dict_pay_method` | pay method | 详见 M5 支付方式 模块 | M5 |
| `dict_proxy_type` | proxy type | 详见 M10 代理类型 模块 | M10 |
| `dict_report_dim` | report dim | 详见 M6 报表维度 模块 | M6 |
| `dict_time_range` | time range | 详见 M6 时间范围 模块 | M6 |
| `dict_user_role` | user role | 详见 M9 用户角色 模块 | M9 |
| `dict_value_type` | value type | 详见 M8 值类型 模块 | M8 |
| `dict_voucher_type` | voucher type | 详见 M5 凭证类型 模块 | M5 |
| `dict_work_type` | work type | 详见 M7 作品类型 模块 | M7 |
| `dict_effective_range` | effective range | 详见 M8 生效范围 模块 | M8 |
| `dict_knowledge_category` | knowledge category | 详见 M8 知识分类 模块 | M8 |

## 2.2 节` 同步登记
3. 在相关模块 PRD 的"业务规则"中引用
4. 通知前端开发，新增选择器
5. 通知后端开发，新增 `@InDict` 注解

### 6.4 字典 value 命名规范

- 全大写 + 下划线
- 含义明确，避免歧义
- 删除字典 value：必须先检查所有引用 → 不可删除时改为"停用"（`status=1`）

---

## 7. 反模式（禁止）

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| ❌ 前端 `<option value="A">A</option>` 写死 | 字典值变更需改代码 | 使用 `<DictSelect />` |
| ❌ 后端 `enum class Status { ACTIVE, INACTIVE }` | 数据库迁移困难 | 改为 `varchar + 字典` |
| ❌ 字段存中文值（"正常"） | 国际化困难、统计困难 | 存字典 value（如 `0` / `NORMAL`） |
| ❌ 同一概念在不同模块用不同 value | 字典重复 | 统一在 `## 2 节` 登记 |
| ❌ 字段直接存"ID,ID,ID" 字符串 | 关系丢失 | 使用关联表 |
| ❌ 关联属性传 name | 数据脏 | 强制传 id |
| ❌ 实名人被停用但未校验其关联的账号 | 数据不一致 | Service 层校验 |
| ❌ 字典 value 重复定义 | 概念混乱 | 先查表再新增 |

---

## 8. 与现有模块的关联

- **M1 运营管理**：作者-IP 组、IP 组-账号/主播/成员、账号-实名人/手机/公司
- **M4 账号管理**：账号 ↔ 实名人/手机/手机卡/公司（最核心的强关联）
- **M5 财务管理**：成本类型、付款方式、归属周期 → 字典
- **M6 数据分析**：报表类型、漏斗类型、预警类型 → 字典
- **M7 作品监测**：监测等级、状态 → 字典
- **M10 数据采集**：采集方式/源/频率/状态 → 字典
- **M9 系统管理**：用户状态、租户状态 → 字典
- **全部模块**：审计动作、是否 → 字典

---

## 9. 字典初始化 SQL

> 部署时自动执行（`db/init_dict.sql`），确保所有字典 type + value 齐全

```sql
-- 平台类型
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_platform_type', '公众号', 'WECHAT_OFFICIAL', 1, 0),
('dict_platform_type', '服务号', 'WECHAT_SERVICE', 2, 0),
('dict_platform_type', '视频号', 'WECHAT_VIDEO', 3, 0),
('dict_platform_type', '抖音', 'DOUYIN', 4, 0),
('dict_platform_type', '快手', 'KUAISHOU', 5, 0),
('dict_platform_type', '小红书', 'XIAOHONGSHU', 6, 0),
('dict_platform_type', '企业微信', 'WEWORK', 7, 0),
('dict_platform_type', '个人微信', 'WX_PERSONAL', 8, 0);

-- 账号类型
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_account_type', '公众号/服务号', 'OFFICIAL_ACCOUNT', 1, 0),
('dict_account_type', '抖音号', 'DOUYIN_ACCOUNT', 2, 0),
('dict_account_type', '视频号', 'VIDEO_ACCOUNT', 3, 0),
('dict_account_type', '快手号', 'KUAISHOU_ACCOUNT', 4, 0),
('dict_account_type', '小红书号', 'XIAOHONGSHU_ACCOUNT', 5, 0),
('dict_account_type', '企微号', 'WEWORK_ACCOUNT', 6, 0),
('dict_account_type', '个微号', 'WX_PERSONAL_ACCOUNT', 7, 0);

-- 账号状态
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_account_status', '正常', 'NORMAL', 1, 0),
('dict_account_status', '异常', 'ABNORMAL', 2, 0),
('dict_account_status', '封禁', 'BANNED', 3, 0),
('dict_account_status', '注销', 'CANCELLED', 4, 0);

-- 内容类型
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_content_type', '短视频', 'SHORT_VIDEO', 1, 0),
('dict_content_type', '文章', 'ARTICLE', 2, 0),
('dict_content_type', '图文', 'GRAPHIC', 3, 0),
('dict_content_type', '直播', 'LIVE', 4, 0),
('dict_content_type', '音频', 'AUDIO', 5, 0);

-- 补录类型
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_content_import_type', '接口异常录入', 'API_EXCEPTION', 1, 0),
('dict_content_import_type', '封号补录', 'ACCOUNT_BANNED', 2, 0),
('dict_content_import_type', '线下补录', 'OFFLINE_PRACTICE', 3, 0),
('dict_content_import_type', '其他补录', 'OTHER', 4, 0);

-- 数据来源
INSERT INTO sys_dict_data (dict_type, dict_label, dict_value, sort, status)
VALUES
('dict_data_source', 'API 采集', 'API', 1, 0),
('dict_data_source', '人工补录', 'IMPORT', 2, 0);

-- ...（其余 45+ 字典同理）
```

> **完整 SQL 见** `db/init_dict.sql`（部署脚本）

---

## 10. 字典变更流程

### 10.1 新增字典项

1. 产品经理提交"字典新增单"（含：字典 type、value、label、说明）
2. 开发在字典管理后台新增
3. 前端自动生效（`<DictSelect />` 自动拉取）
4. 后端自动生效（`@InDict` 校验通过）

### 10.2 修改字典项 value

- 🔴 **禁止直接修改 value**：会导致历史数据无法识别
- 正确做法：
  1. 旧 value 标记"停用"（`status=1`）
  2. 新增 value（新值）
  3. 数据迁移（如果需要）
  4. 通知所有相关方

### 10.3 字典 value 命名冲突

- 同一字典 type 内 value 必须唯一
- 跨字典 type 不要求唯一（如 `NORMAL` 在 `dict_account_status` 和 `dict_user_status` 中可同时存在）

---

## 11. 测试覆盖

### 11.1 选择器测试

- 所有关联属性必须能用选择器选择
- 选择器禁用手动输入（构造"传 name"的请求 → 失败）
- 选择器联动（如选了 IP 组后，账号选择器只显示该 IP 组下的）

### 11.2 字典测试

- 所有字典 value 在测试数据库中初始化
- 传入不存在的 value → 失败
- 字典停用 value → 不可选

### 11.3 强关联测试

- 删除被引用的实名人 → 拒绝
- 停用被引用的实名人 → 拒绝
- 实名人被账号 A 绑定后，账号 B 不能再绑定 → 拒绝

---

## 11.5 系统参数 · 内容审核（M9 / M2，ADR-017）

| 参数键 | 说明 |
|--------|------|
| `content.review.level1.enabled` | 一级审核开关 |
| `content.review.level2.enabled` | 二级审核开关 |
| `content.review.level1.role` | 一级审核角色 code；`OPS_LEADER` = IP 组长范围 |
| `content.review.level2.role` | 二级审核角色 code |

## 11.6 前端导出（ADR-018）

分析/管理页「导出 Excel」= 客户端 `exportToExcel` 生成 **UTF-8 BOM CSV**；不要求后端 `/export` endpoint（Phase 1）。

---

## 12. ADR 模板

新增字典 / 修改关联时，使用以下模板开 ADR：

```markdown
# ADR-{N}：{决策标题}

## 背景
{为什么要新增/修改}

## 决策
{具体内容}

## 影响
{对哪些模块有影响}

## 替代方案
{其他考虑}
```

---

*本文件是项目级"宪法"，与 PRD 冲突时开 ADR 修订。*
