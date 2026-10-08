# PRD-M10-数据采集

> **业务域**：M10 数据采集
> **功能模块**：采集任务 + 数据质量
> **详细设计章节**：5.40、5.41（v9.1 编号，对应 5.36-5.37 位置）
> **版本**：v1.3 | 2026-10-02
> **状态**：Draft（Phase 2 Channel-A MVP 已实现 · 见 §2.3）
> **关联 UX**：[`UX-M10-数据采集.md`](./UX-M10-数据采集.md)（v1.3 · 2026-10-02）
> **关联 API**：[`API-M10-数据采集.md`](../engineering/API-M10-数据采集.md)
> **全局规范**：[`docs/engineering/GLOBAL-CONVENTIONS.md`](./../engineering/GLOBAL-CONVENTIONS.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| 模块 | M10 数据采集 |
| 业务域 | 数据采集（COLLECT） |
| 详细设计 | `## 5.40~5.41` |

---

## 1. 概述

### 1.1 一句话描述

**采集引擎核心**：从各平台/外部源/API/手工录入采集数据，支持定时调度、质量检查、失败重试。

### 1.2 目标

| 维度 | 目标 |
|------|------|
| 自动化 | 80% 数据自动采集 |
| 准确性 | 采集准确率 ≥ 99% |
| 实时 | 关键数据实时同步（≤ 5min） |
| 质量 | 数据质量检查 100% 覆盖 |

### 1.3 术语表

| 术语 | 定义 |
|------|------|
| **采集任务** | 一次数据拉取的配置 + 调度 |
| **采集方式** | 内部采集 / 外部采集 / 第三方 API / 手工录入 |
| **采集源** | 公众号 API / 视频号 API / 抖音开放平台 / 奥创接口 / 企微 API / 个微 API |
| **采集频率** | 实时 / 每小时 / 每天 / 每周 / 每月 / 手动 |
| **数据质量** | 完整性 / 准确性 / 一致性 / 时效性 / 唯一性 |
| **质量等级** | 优 / 良 / 中 / 差 |

---

## 2. 范围

### 2.1 In Scope（3 个 FR 模块）

| FR 编号 | 名称 | 优先级 | 详细设计 |
|---------|------|--------|---------|
| FR-M10-001 | 采集任务管理（含任务编辑 · 采集日志） | P0 | 5.40 |
| FR-M10-002 | 数据质量检查（规则 + 质量日志 · UX Spec） | P1 | 5.41 |
| FR-M10-003 | 私域桥接审核 | P0 | UX-M10 §8 |

### 2.2 Out of Scope

1. ✅ **已实现** XXL-JOB（基于 `football-spring-boot-starter-job` + `@XxlJob` + `@TenantJob` 多租户循环；详见 [ADR-070](../adr/ADR-070-Ops抓取统一XXL-JOB调度.md)，撤销 ADR-001 §2/§4 XXL-JOB 禁令）
2. ❌ **不实现** RabbitMQ 异步（使用 Spring `@Async`）
3. ❌ **不实现** MinIO 对象存储（本地文件系统）
4. ⚠️ **FR-M10-002 实现边界**（与 UX v1.3 **不矛盾**）：**In Scope** = P-M10-004 质量页 **列表/日志只读 + Spec 目标弹窗字段**；**Out of Scope 本期后端** = 规则 CRUD 完整弹窗与定时跑批（现网新增/编辑可为 `ElMessage.info` 占位，见 UX §5.1 · OPS-UX-PAGE-COVERAGE §5.4）
5. ❌ **不实现** 奥创 Channel-B 任务执行（`WECHAT_PERSONAL` 任务 dataTypes 为空）
6. ❌ **不实现** 采集数据自动写入 `oa_content_daily`（M1 为只读桥接，见 [ADR-049](../adr/ADR-049-M10-全量采集与展示桥接.md)）

### 2.3 页面清单与 UX 交叉引用（对齐 UX-M10 v1.3）

> HTTP 前缀 SSOT：`/admin-api/ops/collect/**`（勿写 `/oa/collect` 为主路径）。

| 页面 ID | 名称 | Football 路由 | FR | UX |
|---------|------|---------------|-----|-----|
| P-M10-001 | 采集任务列表 | `/ops/collect/task` | FR-M10-001 | UX §2 |
| P-M10-002 | 采集任务编辑 | `/ops/collect/task/:id`（`id=0` 新增） | FR-M10-001 | UX §3 |
| P-M10-003 | 采集日志 | `/ops/collect/log` | FR-M10-001 | UX §4 |
| P-M10-004 | 数据质量检查 | `/ops/collect/quality` | FR-M10-002 | UX §5 |
| P-M10-005 | 私域桥接 | `/ops/collect/private-domain-bridge` | FR-M10-003 | UX §8 |
| D-M10-001 | 质量规则编辑 dialog | P-M10-004 页内 [新增/编辑] | FR-M10-002 | **UX SSOT** §5.1 · 现网 Toast 占位 |

### 2.4 用户与权限

| 页面 | permission |
|------|------------|
| P-M10-001/002 | `oa:collect:task:list` |
| P-M10-003 | `oa:collect:log:list` |
| P-M10-004 | `oa:collect:quality:list` |
| P-M10-005 | `oa:collect:bridge:list` |

角色：系统管理员 / 运营管理者可启停任务、审核桥接；普通运营只读日志与质量日志（无任务写权限时隐藏 A 区按钮，UX §2.2）。

### 2.5 Phase 2 已实现（2026-06-24 · 文档同步）

> SSOT：[ADR-047](../adr/ADR-047-M4-平台账号凭证SSOT与Collector映射.md) · [ADR-048](../adr/ADR-048-M10-企微采集通道草案.md) · [ADR-049](../adr/ADR-049-M10-全量采集与展示桥接.md)

| 能力 | 说明 |
|------|------|
| Channel-A 六平台路由 | `UnifiedCollectorAdapter` + M4 collector-bind（ADR-047） |
| 平台全量采集 | `data_type` 空 → 按平台顺序执行全部 `dict_collect_data_type`（ADR-049 Q1） |
| 多平台落库 | V116/V121/V122：`oa_wechat_mp_article`、抖音/视频号/快手/小红书作品与粉丝表 |
| 任务 UX 简化 | 编辑页不暴露 method/source/dataType；展示只读「采集范围」（ADR-049 Q2） |
| 日志多类型 | `PARTIAL` + `result.typeResults[]`（ADR-049 Q3） |
| 企微 Channel-C | `WeComAdapter` + `oa_wework_daily_stats`（ADR-048） |
| M1/M4 展示桥接 | `CollectedDataQueryService` 只读合并（ADR-049 Q4） |

### 2.6 Channel-D 外部竞品采集（2026-07-08 · GATE-EXT-P0 立项）

> SSOT：[ADR-052](../adr/ADR-052-Ops外部竞品四平台采集通道.md) · [M10-EXTERNAL-四平台竞品采集-SLICE](../delivery/M10-EXTERNAL-四平台竞品采集-SLICE.md)

| 能力 | 说明 |
|------|------|
| **Channel-D · EXTERNAL** | `ExternalCollectorAdapter`；竞品账号来自 M8 `oa_collect_config`（`scope=EXTERNAL`） |
| **任务主体** | `collect_config_id` 必填；`account_id` **必须 null**（禁止复用 M4 bind） |
| **运营凭账号** | 租户级 `oa_tenant_collector_credential`；任务经 `credential_profile`（默认 `default`）引用，**禁止**任务/配置内嵌 Cookie |
| **落库** | `oa_external_account`（快照）· `oa_external_work`（作品）· `oa_external_follower_daily`（粉丝日聚合） |
| **展示** | M7 `MonitorService` 读 `oa_external_*`；**不**经 M1 `CollectedDataQueryService` |
| **分平台 Gate** | P0 快手 `EXT_KUAISHOU_USER_VIDEOS` → P1 公众号 → P2 抖音 → P3 视频号 |

**P0 首 shippable**：M8 配置 1 条快手竞品 → M10 任务 `method=EXTERNAL` → run SUCCESS → M7 爆款作品列表可见。

---

## 3. 功能需求

### FR-M10-001 采集任务管理（5.40）

#### 4.1.1 描述

管理数据采集任务：配置 + 调度 + 执行 + 监控 + 重试。

#### 4.1.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `task_name` | `<Input />` | - |
| `platform_type` | `<DictSelect dict-type="dict_platform_type" />` | 字典 |
| `account_id` | `<AccountSelect />` | `oa_account`（Channel-A **强关联** ⭐） |
| `collect_config_id` | `<ExternalCollectConfigSelect />` | `oa_collect_config`（`method=EXTERNAL` 时 **必填**） |
| `credential_profile` | `<Input />` 可空 | 租户凭账号 profile，默认 `default` |
| `method` | Channel-A：后端默认 `INTERNAL`；Channel-D：`EXTERNAL` | `dict_collect_method` |
| `source` | 后端按 `platformType` 默认（运营 UI 不编辑） | 字典 |
| `data_type` | 存库 `null` = 全量采集；运营 UI 不编辑 | `dict_collect_data_type` |
| `frequency` | `<DictSelect dict-type="dict_collect_frequency" />` | 字典 |
| `cron` | `<Input />`（cron 表达式） | - |
| `api_config` | `<TextArea />`（API 配置 JSON） | -（加密） |
| `status` | `<DictSelect dict-type="dict_collect_status" />` | 字典 |
| `last_run_at` | `<DateTimePicker />` | -（只读） |
| `next_run_at` | `<DateTimePicker />` | -（只读） |

#### 4.1.3 业务规则

- **调度**：xxl-job（基于 `football-spring-boot-starter-job`），JobHandler 用 `@XxlJob("xxx")` + `@TenantJob` 多租户循环（[ADR-070](../adr/ADR-070-Ops抓取统一XXL-JOB调度.md) · 撤销 ADR-001 §2/§4 XXL-JOB 禁令）；cron 表达式在 xxl-job-admin 任务管理配置
- 异步：Spring `@Async`，不依赖 RabbitMQ
- 失败重试：3 次指数退避（xxl-job-admin 任务重试配置）
- 凭证：Channel-A 凭证 SSOT 在 M4 `oa_account`（ADR-047）；任务 `apiConfig` 仍支持 AES-256 加密 JSON
- **全量采集**：`data_type` 为空时，`CollectPlatformDefaults` 按平台顺序串行执行全部 dataType（ADR-049）
- **日志状态**：多类型执行时，部分成功 → `PARTIAL`；全部成功 → `SUCCESS`；全部失败 → `FAILED`
- **企微任务**：`platform_type=WEWORK` 时 `account_id` → `oa_wework_account.id`（ADR-048）
- **Channel-D 任务**（ADR-052）：`method=EXTERNAL` → `collect_config_id` 指向 M8 外部账号配置；`account_id=null`；凭账号由 `oa_tenant_collector_credential` 按租户+平台+profile 解析
- **Channel-D 与 Channel-A 隔离**：竞品数据写入 `oa_external_*`，**不**写入 `oa_douyin_video` 等自有表

#### 4.1.4 验收标准

**AC-M10-001-P001**（P-M10-001 任务列表 · 分页查询）
- Given 用户具备 `oa:collect:task:list`
- When 打开 `/ops/collect/task` 并筛选任务名/平台/方式/频率/状态
- Then `GET /admin-api/ops/collect/task/page` 返回表格列（任务名 tag 统一/外部统一、最近执行、成功/失败计数，UX §2.3）

**AC-M10-001-P001-U**（统一任务 · ADR-061/068）
- When 点击 [确保统一任务] / [确保外部统一任务]
- Then 分别 `POST /admin-api/ops/collect/task/ensure-unified` · `POST .../ensure-external-unified`；页顶 Alert 说明 23:00 / 22:00 调度（UX §2.2）

**AC-M10-001-P001-R**（行操作）
- When 对非 `isUnified` 且非 `isExternalUnified` 任务点击启动/停止/立即执行
- Then `POST /admin-api/ops/collect/task/{id}/start|stop|run`；删除前 `MessageBox.confirm` · `DELETE .../delete`

**AC-M10-001-P002**（P-M10-002 任务编辑）
- Given 从列表进入 `CollectTaskEdit` · `/ops/collect/task/:id`
- When 保存 Channel-A 单账号任务（`F-ACCOUNT` `<AccountSelect />` · 企微 `WeworkAccountSelect`）
- Then `POST /admin-api/ops/collect/task/create` 或 `PUT .../update`；隐藏字段 `method=INTERNAL` · `dataType` null=全量（UX §3）

**AC-M10-001-P003**（P-M10-003 采集日志）
- Given `oa:collect:log:list`
- When 筛选任务/状态/执行时间并查询，或行点击
- Then `GET /admin-api/ops/collect/log/page`；80% drawer 详情 `GET /admin-api/ops/collect/log/{id}` 含 `result.typeResults[]`（PARTIAL/SUCCESS/FAILED，ADR-049）

**AC-M10-001-2**（字典校验）
- `platformType` / `method` / `source` / `frequency` / `status` 均 `@InDict`

**AC-M10-001-3**（强关联）
- Channel-A：`accountId` 用 `<AccountSelect />`；Channel-D：`collect_config_id` 必填且 `account_id` null（ADR-052）

**AC-M10-001-4**（定时调度）
- 启动后 ops-server 在 xxl-job-admin「执行器管理」可见新 appname **`football-ops-executor`**（`xxl.job.executor.appname` 显式写死，**禁止**引用 `${spring.application.name}`）；`@XxlJob("collectCronScanJobHandler")` + `@TenantJob` 在「任务管理」注册成功；触发后 `@TenantJob` AOP 多租户循环生效（[ADR-070](../adr/ADR-070-Ops抓取统一XXL-JOB调度.md)）；`MonitorAlertScanner` 同步迁移到 `@XxlJob("monitorAlertScanJobHandler")`（ADR-069 P1 stub 同步改造，见 [ADR-070 §4.4](../adr/ADR-070-Ops抓取统一XXL-JOB调度.md)）

**AC-M10-001-5**（失败重试）
- 失败 3 次后状态 = FAILED

**AC-M10-001-6**（凭证加密）
- `apiConfig` 数据库存储为密文

**AC-M10-001-7**（Channel-D 快手 P0）
- Given M8 已配置快手竞品 `account_identifier`=user_id
- When 创建任务 `method=EXTERNAL`、`collect_config_id`、 `dataType=EXT_KUAISHOU_USER_VIDEOS` 并执行
- Then `oa_external_work` 有新行；M7 外部爆款列表 `is_external=1` 可见

---

### FR-M10-002 数据质量检查（5.41）

#### 4.2.1 描述

对采集的数据进行质量检查（完整性/准确性/一致性/时效性/唯一性）。

#### 4.2.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `check_name` | `<Input />` | - |
| `check_type` | `<DictSelect dict-type="dict_quality_check_type" />` | 字典 |
| `target_table` | `<Input />` | - |
| `target_field` | `<Input />` | - |
| `rule` | `<TextArea />`（规则表达式） | - |
| `level` | `<DictSelect dict-type="dict_quality_level" />` | 字典 |

#### 4.2.3 业务规则

- **完整性**：必填字段非空率
- **准确性**：数据值在合理范围
- **一致性**：跨表数据一致
- **时效性**：数据新鲜度（采集时间 - 数据时间）
- **唯一性**：主键/唯一键不重复

#### 4.2.4 验收标准

**AC-M10-002-P004**（P-M10-004 质量页 · 只读列表）
- Given `oa:collect:quality:list`
- When 打开 `/ops/collect/quality`
- Then 左栏 `GET /admin-api/ops/collect/quality/check/page`（或 API-M10 §2.1 等价路径）展示规则表；右栏 `GET .../quality/log/page` 展示质量日志；通过率 &lt;90% 标红（UX §5）

**AC-M10-002-P004-D**（规则编辑 · Spec 目标 / 现网占位）
- When 点击 [新增规则] 或行 [编辑]
- Then **Spec 目标**：dialog 字段 name/checkType/level/tableName/ruleExpression/enabled（UX §5.1）；**现网允许** `ElMessage.info` 占位且不阻塞列表（§2.2 第 4 项）

**AC-M10-002-2**（字典校验）
- `checkType` · `level` 均 `@InDict`（`dict_quality_check_type` · `dict_quality_level`）

**AC-M10-002-3**（质量等级）
- 优（≥95%）、良（80-94%）、中（60-79%）、差（<60%）

---

### FR-M10-003 私域桥接（UX-M10 §8）

#### 4.3.1 描述

审核私域身份桥接记录：来源/目标身份匹配结果待人工确认或驳回；菜单 `/ops/collect/private-domain-bridge`。

#### 4.3.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `reviewStatus` | `<DictSelect dict-type="dict_private_domain_review_status" />` | 默认筛选 `PENDING` |
| `sourceType` | `<DictSelect dict-type="dict_private_domain_identity_type" />` | 字典 |
| `matchMethod` | `<DictSelect dict-type="dict_private_domain_match_method" />` | 字典 |

#### 4.3.3 验收标准

**AC-M10-003-P005**（P-M10-005 列表）
- Given `oa:collect:bridge:list`
- When 打开 `/ops/collect/private-domain-bridge` 并按审核状态筛选
- Then `GET /admin-api/ops/collect/private-domain-bridge/page`；表格列含来源/目标类型与标签、匹配方式、置信度、审核状态（UX §8）

**AC-M10-003-P005-C**（确认 / 驳回）
- Given 行 `reviewStatus=PENDING`
- When 点击 [确认] 或 [驳回] 并经 `MessageBox.confirm`
- Then `POST /admin-api/ops/collect/private-domain-bridge/confirm` 或 `.../reject`；成功后刷新列表并保持筛选

**AC-M10-003-E**（空态）
- When 无待审记录
- Then `el-empty`「暂无待审核桥接记录」（UX §8）

---

## 4. 集成与数据

### 4.1 核心实体

| 实体 | 用途 | 关联 |
|------|------|------|
| `oa_collect_task` | 采集任务 | `oa_account` 或 `oa_wework_account`（企微） |
| `oa_collect_log` | 采集日志（含 `result_json`） | `oa_collect_task` |
| `oa_collector_account_bind` | Channel-A 双 ID 映射 | `oa_account`（ADR-047） |
| `oa_wechat_mp_article` / `oa_wechat_mp_follower` | 公众号采集快照 | `oa_account` |
| `oa_douyin_follower` / `oa_douyin_video` | 抖音采集快照 | `oa_account` |
| `oa_wechat_video_work` | 视频号作品 | `oa_account` |
| `oa_kuaishou_video` | 快手作品 | `oa_account` |
| `oa_xiaohongshu_note` | 小红书笔记 | `oa_account` |
| `oa_wework_daily_stats` | 企微日聚合 | `oa_wework_account`（ADR-048） |
| `oa_data_quality_check` | 质量检查规则 | - |
| `oa_data_quality_log` | 质量日志 | `oa_data_quality_check` |
| 私域桥接记录表 | 桥接审核（以 API-M10 / 实现为准） | - |

### 4.2 关联属性

| 字段 | 选择器 |
|------|--------|
| `accountId` | `<AccountSelect />` |
| `platformType` | `<DictSelect dict-type="dict_platform_type" />` |
| `method` | `<DictSelect dict-type="dict_collect_method" />` |
| `source` | `<DictSelect dict-type="dict_collect_source" />` |
| `frequency` | `<DictSelect dict-type="dict_collect_frequency" />` |
| `status` | `<DictSelect dict-type="dict_collect_status" />` |
| `checkType` | `<DictSelect dict-type="dict_quality_check_type" />` |
| `level` | `<DictSelect dict-type="dict_quality_level" />` |

---

### 4.3 Ops ↔ unify-collector-api 集成（环境配置 · 非新 FR）

Ops Channel-A 经 `UnifiedCollectorApiClient` 调用远程采集服务。**非**新增采集能力，仅为部署/联调可配置：

| 项 | 说明 |
|----|------|
| 配置键 | `oa.unified-collector.base-url` ← 环境变量 **`COLLECTOR_BASE_URL`** |
| Token | `oa.unified-collector.api-token` ← **`COLLECTOR_API_TOKEN`** |
| 本地 profile | `application-local.yaml` 默认 `http://127.0.0.1:8000`；`start-integration-oa.ps1` 可通过 `Import-OpsCollectorRemoteEnv` 从 `ops-test-remote.env` 注入远程地址（**仅** collector env，不切换 DB） |
| 生产 | `application-prod.yaml` / Nacos `nacos-ops-server-prod.yaml` 必设 `COLLECTOR_BASE_URL` |
| 健康检查 | `GET {COLLECTOR_BASE_URL}/livez` → 200 |
| 错误提示 | `CollectorErrorMessages` / `UnifiedCollectorApiClient` 失败时展示已配置的 base-url |

联调 SSOT：[OPS-TEST-DB.md § Unified Collector](../delivery/OPS-TEST-DB.md#unified-collector本地-profile--远程采集) · [OPS-DEV-DEPLOY-GUIDE.md §4](../delivery/OPS-DEV-DEPLOY-GUIDE.md)

---

| 编号 | 问题 | 决策 | 原因 |
|------|------|------|------|
| ~~ADR-M10-001~~（已被 ADR-070 撤销） | ~~任务调度依赖 XXL-JOB 吗？~~ | ~~不依赖，Spring `@Scheduled`~~ | ~~中间件简化（ADR-001）~~ |
| ADR-M10-002 | 异步处理依赖 RabbitMQ 吗？ | 不依赖，Spring `@Async` | 中间件简化（ADR-001） |
| ADR-M10-003 | 凭证存储？ | 本地 + AES-256 | 中间件简化（ADR-001） |
| ADR-047 | Channel-A 凭证 SSOT？ | M4 `oa_account` + bind 表 | 消除 M8 双 SSOT |
| ADR-048 | 企微采集？ | `WeComAdapter` 直连 | 不经 collector bind |
| ADR-049 | 单任务多 dataType？ | 空 data_type = 全量顺序执行 | 降低运营配置成本 |
| **ADR-061** | Channel-A 默认一账号一任务？ | **否（假设 A1）**：租户级 **一条**统一任务 + `oa_collect_task_account` 成员；账号 `collect_enabled` 控制入退 | 降低运营配置成本；见 [ADR-061](../adr/ADR-061-租户级统一采集任务.md) |
| **ADR-070** | Ops 抓取调度是否引入 XXL-JOB？ | **是**：撤销 ADR-001 §2/§4 XXL-JOB 禁令；Ops 抓取类调度（采集 cron 扫描 + 阈值兜底）走 `football-spring-boot-starter-job` + `@XxlJob` + `@TenantJob` 多租户循环；executor appname = **`football-ops-executor`**（显式写死；不复用 `${spring.application.name}`）；admin accessToken 沿用 mp 默认；失败重试 1/5/15min 三段；ADR-069 P1 stub 全租户遍历同步迁移 | 与 Football 同源 7 个 service 一致；多租户语义由 `TenantJobAspect` AOP 自动接管；2026-08-17 §6 Q1–Q6 全部决议 |

> **附注（ADR-061）**：§4.1.2 `account_id` 强关联适用于历史/单账号任务；**统一任务** `account_id=NULL`，成员表挂多账号。调度 cron 默认来自 `sys_param.collect.schedule.cron`（23:00）。

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.3：FR-M10-003 私域桥接 · P-M10-001~005 页表与可测 AC · 澄清 FR-M10-002 In/Out（与 UX 质量页一致） · `/ops/collect` API 链接 |
| 2026-08-26 | v1.2 | ADR-061/070 等 |
| 2026-06-24 | v1.0 | Channel-A MVP |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES（P-M10-* 与 AC 一一对应）。*
