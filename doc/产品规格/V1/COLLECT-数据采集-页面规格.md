# COLLECT - 数据采集 页面规格（OPS M8/M10 并入）

> 完整 PRD §16。前缀：`/admin-api/ims/collect`（配置/元数据/阈值对齐 OPS `API-M8`；任务/日志对齐 `API-M10`）  
> **交互 SSOT**：`docs/product/UX-M10-数据采集.md`、`docs/product/UX-M8-配置管理.md`（外部账号/关键词/阈值/元数据）、`ADR-IMS-003`、`ADR-047`、`ADR-052`、`ADR-061`  
> **禁止**：在「内部配置」或外部账号**配置行**内维护抖音/快手/视频号 **平台账号 Cookie**（凭证 SSOT = **账号详情 · 采集 Tab**，见 `ACCT-平台账号采集Tab-OPS对齐.md`）

## 0. 信息架构（侧栏二级目录「数据采集」）

与 **15 内容生产** 相同模式：`nav-sub-g` 可展开分组，默认进入 **P5 采集任务**。

| 页面 ID | 侧栏名称 | 路由 | OPS 对照 | 用户走查项 |
|---------|----------|------|----------|------------|
| P5 | 采集任务 | `/ims/collect/task` | UX-M10 P-M10-001/002 | ✅ |
| P5b | 采集日志 | `/ims/collect/log` | UX-M10 P-M10-003 | ✅ |
| P2a | 竞品账号配置 | `/ims/collect/external/account` | UX-M8 §3.2 外部账号 Tab | ✅（外部配置·账号） |
| P2b | 竞品关键字配置 | `/ims/collect/external/keyword` | UX-M8 §3.3 关键词 Tab | ✅（外部配置·关键词） |
| P4m | 元数据维护 | `/ims/collect/metadata` | UX-M8 §4 元数据 | ✅ |
| P4 | 阈值规则 | `/ims/collect/threshold` | UX-M8 §5 阈值 | ✅ |

**说明**：产品口中的「外部采集配置」= **P2a + P2b 两个独立路由**，禁止再压成「外部账号 | 关键词 | 数据源」单页多 Tab。

### 0.1 元数据 vs BI0（17a）

| 维度 | COLLECT · P4m | BI0 · 自定义查询 |
|------|---------------|------------------|
| 职责 | **维护**实体映射、字段、`query_condition_type`、字典/选择器绑定 | **消费**已映射实体做 QueryBuilder / 指标 |
| 导航归属 | **数据采集 → 元数据维护**（用户走查 SSOT） | 指标报表 → 自定义查询/指标管理 |
| API | `GET/POST/PUT …/collect/metadata/**`（透传 OPS M8 语义） | 只读 `entity/{code}/fields` 引用同一套映射 |
| 交叉链接 | P4m 页脚链到 BI0 自定义查询；BI0 P4 未映射时链回 P4m | BI0 规格 **不再** 将元数据列为 BI 主导航页 |

### 0.2 移出主导航（仍保留能力 / 路由）

| 原占位 | 处置 | 路由（管理员） |
|--------|------|----------------|
| P6 数据质量 | 从侧栏移除；**采集日志**页顶统计卡 + 「手工补录」入口保留 UX-M10 P-M10-004 能力 | `/ims/collect/quality` |
| P2c 外部数据源 | 并入 **竞品账号配置** 工具栏「外部 HTTP 数据源」抽屉（M8 FR-M8-003），非并列 Tab | `/ims/collect/external/source` |
| P2t 租户采集凭账号 | **竞品账号配置**页工具栏独立入口（ADR-052）；供 Channel-D `credential_profile` 引用 | `/ims/collect/external/credential` |
| P1 内部（企微/奥创） | M8 例外；链自 **采集任务**编辑页「企业微信 / 个微」平台说明 + 系统管理员菜单 | `/ims/collect/internal` |
| P3 订单采集 | PRD 未列入用户五类；**WebAPI 拉单**配置收至系统参数/二期，禁止 JDBC（1243） | `/ims/collect/order`（隐藏菜单） |

---

## P5 采集任务（Channel-A/B/C/D 调度入口）

### 布局

```
[筛选：任务名 | 平台 | 方式 | 频率 | 状态] [查询] [重置] [新增任务]
[表格]
[分页]
```

### 表格列

| 列 | 说明 |
|----|------|
| 任务名称 | `oa_collect_task.name` |
| 平台 | `dict_platform_type` |
| 任务类型 | **单账号** / **统一任务** / **外部配置**（`isUnified` / `method=EXTERNAL`） |
| 绑定对象 | 单账号：`AccountSelect` 回显；统一：成员数 + 「查看成员」；外部：`collect_config_id` 回显 |
| 采集范围 | 只读 tag 列表（平台默认 dataTypes） |
| cron | 表达式 |
| 上次执行 / 下次执行 | 只读 |
| 状态 | 启用/停用（`dict_collect_status`） |
| 操作 | [启动] [停止] [立即执行] [查看日志] · 非统一任务：[编辑] [删除] · 统一任务：[成员] / 外部统一：[外部成员] |

### 编辑抽屉（对齐 UX-M10 §3、§7）

| 控件 | 必填 | 说明 |
|------|------|------|
| 任务名称 | ✅ | |
| 平台 | ✅ | |
| 账号 | 单账号 Channel-A ✅ | `<AccountSelect />`；统一任务隐藏 |
| 外部竞品配置 | Channel-D ✅ | 外部配置选择器；`account_id` 必须 null |
| credential_profile | Channel-D 可空 | 默认 `default`；凭账号见 P2t |
| 统一任务成员 | 统一任务 ✅ | 成员表 + `collectEnabled`；`ensure-unified` |
| 频率 + cron | ✅ | |
| 状态 | ✅ | |
| ~~Cookie~~ | ❌ | **禁止**；凭证在账号采集 Tab |

**立即执行**：`POST …/task/{id}/run` → 跳转 P5b 并带 `taskId` 筛选。

---

## P5b 采集日志

| 控件 | 说明 |
|------|------|
| 任务 | 下拉全部任务 |
| 账号 | `<AccountSelect />`（按行错误下钻） |
| 状态 | 含 `PARTIAL` |
| 日期范围 | |
| 顶栏 | 24h 成功率 / 连续失败账号（→ P6 或 ALERT） |
| 表格 | 任务、账号、平台、状态、耗时、错误摘要、操作[详情] |
| 详情抽屉 | `typeResults[]` 折叠；失败「Cookie 失效 / 未绑定 Collector」→ 链接 **账号采集 Tab** |

---

## P2a 竞品账号配置（外部账号 · Channel-D 主体）

**独立页面**（非 Tab）。对齐 UX-M8 §3.2。  
**ADR-047 边界**：本页仅维护 **外部竞品采集主体**（`oa_collect_config` / Channel-D）；**平台自有账号** Cookie、扫码、Collector bind 仅在 **公司资产 → 平台账号详情 · 采集 Tab**（《ACCT-平台账号采集Tab-OPS对齐.md》）。与 ACCT 规格 **交叉链接** 验收。

```
[Alert：配置行不嵌 Cookie · 凭账号见「租户采集凭账号」]
[搜索：账号名称 | 平台 | 状态]
[新增] [批量导入 CSV] [批量删除] [租户采集凭账号] [外部 HTTP 数据源…]
[表格：ID | 平台(dict_third_platform) | 账号名称 | 账号标识 | 状态 | 更新时间 | 操作]
```

编辑弹窗：平台、标识、启用状态；**禁止** Cookie 字段（ADR-052）。

---

## P2b 竞品关键字配置

**独立页面**。对齐 UX-M8 §3.3。

```
[搜索：关键词 | 平台 | 状态]
[新增] [批量删除]
[表格：ID | 平台(dict_platform_type) | 关键词 | 匹配类型 | 状态 | 操作]
```

---

## P2t 租户采集凭账号（子入口，非侧栏）

从 P2a 工具栏进入。列：平台 | profile | 展示名 | 连接状态 | 过期时间 | 状态 | 操作；表单 Cookie/Token 脱敏 + 探活。

---

## P4m 元数据维护

路由 `/ims/collect/metadata` · 对齐 UX-M8 §4 / `MetadataManage.vue`：

- 实体列表 + 新增/编辑/删除（删除仅超级管理员）
- 新增：未映射表下拉 `{tableName} ({tableComment})`
- 字段配置抽屉：`query_condition_type`、`dict_type`、`selector_config`
- 页脚：**自定义查询**须先在此映射实体（链 BI0 P4）

---

## P4 阈值规则

对齐 UX-M8 §5。**消费方**：本模块采集结果、**13 预警中心**（ALERT）、**18 作品监测**（MON 爆款/低分/高低粉）。

页内 Tab（阈值类别，非「外部配置」式混 Tab）：

| Tab | 弹窗关键字段 |
|-----|-------------|
| 预警阈值 | 指标、平台、阈值类型、比较符、阈值、通知渠道 |
| 粉丝阈值 | 平台、低粉/高粉、日增低粉/日增高粉 |
| 作品阈值 | 平台、内容类型、指标、爆款/低分、判定模式 |
| 账号覆盖 | 平台 + `AccountSelect`、指标、覆盖值 |

账号级覆盖优先于全局。ALERT 规则 `COLLECT_ERROR` / 监测类规则 **引用** 此处配置，不在 ALERT 重复维护阈值数值。

---

## P1 内部采集（例外 · 无侧栏）

Tab：**企业微信应用** | **个微奥创**（UX-M8 §2 企微/个微分支）。  
页顶 Alert：「自有平台账号凭证请在 **账号管理 → 详情 → 采集** 维护并绑定 Collector。」

---

## P6 数据质量（无侧栏）

成功率、连续失败 Top、手工补录（`POST /collect/manual-fill`）；连续失败触发 ALERT `COLLECT_ERROR`。

---

## 与账号模块分工

| 作业 | 页面 |
|------|------|
| 填 Cookie / 扫码 / bind / 测试连接 | 账号详情 · **采集 Tab** |
| 配 cron、跑任务、看日志 | P5 / P5b |
| 外部竞品主体 | P2a；关键词 | P2b |
| 映射实体供查询/指标 | P4m |
| 阈值 | P4（ALERT/MON 只读消费） |

---

## OPS 前后端对照（2026-10-02）

> **现网前缀**：`/admin-api/ops/collect/**` · `/admin-api/ops/config/**` · `/admin-api/ops/metadata/**`  
> **Vue 根路径**：`football-front/apps/web-ele/src/views/ops/` · **API**：`#/api/ops/collect.ts` · `config.ts` · `metadata.ts`

| IMS 子菜单 | Vue SFC | Java Controller | 顶栏/行内按钮 → API |
|------------|---------|-----------------|---------------------|
| 采集任务 | `collect/task.vue` · `task-edit.vue` | `collect/CollectTaskController` | 确保统一 `POST /ops/collect/task/ensure-unified` · 外部统一 `POST …/ensure-external-unified` · 新增 `POST …/create` · 启动 `POST …/{id}/start` · 停止 `POST …/{id}/stop` · 立即执行 `POST …/{id}/run`（180s 超时） · 删 `DELETE …/delete?id=` · 成员 `GET …/{id}/members` |
| 采集日志 | `collect/log.vue` · `log-detail.vue` | `collect/CollectTaskController`（log 段） | 分页 `GET /ops/collect/log/page` · 详情 `GET …/log/{id}`（含 `typeResults[]` · ADR-049） |
| 竞品账号配置 | `config/ExternalCollectConfig.vue`（账号 Tab） | `config/ExternalCollectConfigController`（`collectApi('external-collect')`） | CRUD `/ops/config/external-collect/*` · 导入 `POST …/import` |
| 竞品关键字 | 同上（关键词 Tab） | 同上 | `GET/POST/PUT/DELETE /ops/config/external-collect/keyword/*` |
| 元数据维护 | `config/MetadataManage.vue` | `metadata/MetadataController` | `GET /ops/metadata/list` · `unmapped-tables` · `create/update` · 字段批量 `PUT …/fields` |
| 阈值规则 | `config/ThresholdConfig.vue` | `config/ThresholdConfigController` | `GET/POST/PUT/DELETE /ops/config/threshold/*`（`thresholdCategory` 必填） |

**P5 工具栏（对齐 `task.vue`）**：`[确保统一任务]` `[确保外部统一任务]` `[新增单账号任务]`；统一/外部统一行 **不可** 编辑删除，仅成员管理。

---

## 错误码

1241~1250；127x Football 订单拉取失败；1261 自定义查询实体未映射（链 P4m）。

---

## 操作序列（OPS → 原型 · 2026-10-02）

原型页：`collectTask` · `collectLog` · handler `colJob*` / `colLogDetail`。

| 步骤 | 用户操作 | OPS 参照 | API / 状态 |
|------|----------|----------|------------|
| 1 | 「确保统一任务」 | `collect/task.vue` 工具栏 | `POST /ops/collect/task/ensure-unified` → 追加 `COL_JOBS` 统一行 |
| 2 | 行「启动/停止」 | `collect/task.vue` `handleStart` · `handleStop` | `POST /ops/collect/task/{id}/start` · `POST …/stop` → `COL_JOBS[].status` RUNNING·STOPPED |
| 3 | 「立即执行」 | run 按钮 | `POST /ops/collect/task/{id}/run`（`API-M10` §1.5）→ 写入 `COL_LOGS` 并跳转日志 |
| 4 | 日志「查看详情」 | `collect/log-detail.vue` | `GET /ops/collect/log/{id}` · 抽屉展示 `typeResults` |
| 5 | 单账号任务「删除」 | 非统一行 | `DELETE /ops/collect/task/{id}` → 从 `COL_JOBS` 移除 |

**本地源码（wd 已检入）**：`football-front/apps/web-ele/src/views/ops/collect/task.vue` · `log.vue` · `log-detail.vue` · `task-edit.vue`；API 封装 `#/api/ops/collect.ts`。wd 内 ops Java Controller 未全量检入，路径与契约见 `docs/engineering/API-M10-数据采集.md`。
