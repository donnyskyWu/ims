# UX-M8-配置管理



> **版本**：v2.2 | 2026-10-02

> **关联 PRD**：[`PRD-M8-配置管理.md`](./PRD-M8-配置管理.md)

> **ADR**：[`ADR-014`](../adr/ADR-014-M8-配置管理数据模型.md)



---




## 0. OPS 设计 SSOT

> **设计规范**：[UX-OPS-设计规范.md](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[UX-OPS-页面原型索引.md](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[OPS-MENU-ROUTE-INDEX.md](../delivery/OPS-MENU-ROUTE-INDEX.md)

## 1. 页面清单

| 页面 | Football 路由 | standalone（历史） | FR | permission |
|------|---------------|-------------------|-----|------------|
| 内部采集配置 | `/ops/config/config-internal-collect` | `/config-internal-collect` | FR-M8-001 | `oa:config:internal-collect:list` |
| 外部采集配置 | `/ops/config/config-external-collect` | `/config-external-collect` | FR-M8-002 | `oa:config:external-collect:list` |
| 外部数据配置 | `/ops/config/config-external-data` | `/config-external-data` | FR-M8-003 | `oa:config:external-data:list` |
| 订单采集配置 | `/ops/config/config-order-collect` | `/config-order-collect` | FR-M8-004 | `oa:config:order-collect:list` |
| 阈值规则配置 | `/ops/config/config-threshold` | `/config-threshold` | FR-M8-005 | `oa:config:threshold:list` |
| AI 模型配置 | `/ops/config/config-ai-model` | `/config-ai-model` | FR-M8-006 | `oa:config:ai-model:list` |
| AI 提示词配置 | `/ops/config/config-ai-prompt` | `/config-ai-prompt` | FR-M8-007 | `oa:config:ai-prompt:list` |
| 元数据维护 | `/ops/config/config-metadata` | `/config-metadata` | FR-M8-008 | `oa:metadata:query` |

| 租户采集凭账号 | `/config-external-collect` 子 Tab 或 `/config-tenant-credential`（P1+） | FR-M8-002 / CFG-013a |



---



## 2. 内部采集配置 UX



### 2.1 布局（按 Tab 分支）



**平台类 Tab**（公众号/抖音/快手/视频号/服务号）：



```

[Alert 说明]

[平台 Tab: 公众号|抖音|快手|视频号|服务号|企微|个微]

[搜索: 账号名称 + 状态]

[新增配置]

[表格: ID | 平台账号 | 账号标识 | APPID | 直播号 | 状态 | 更新时间 | 操作]

[编辑弹窗: AccountSelect + 凭证字段]

```



**企业微信 Tab**：



```

[WeworkAppConfigPanel]  — 与账号管理·个人账号·企微应用配置同源

```



**个人微信 Tab**：



```

[奥创接口配置表单]  — 仅 apiUrl/appId/appSecret/token，无账号列表

```



### 2.2 组件复用



| 组件 | 用途 |

|------|------|

| `<AccountSelect />` | 平台 Tab 选 M4 平台账号 |

| `<WeworkAppConfigPanel />` | 企微 Tab 应用配置（共享 `PersonalAccountManage`） |



### 2.3 表单校验



平台 Tab：`accountId` 必选；APPSECRET 脱敏展示。



---



## 3. 外部采集配置 UX



### 3.1 Tab



外部账号 | 关键词配置



### 3.2 外部账号 Tab



列：ID | 平台(`dict_third_platform`) | 账号名称 | 账号标识 | 状态 | 更新时间 | 操作



工具栏：[新增] [批量导入 CSV] [批量删除]



### 3.3 关键词 Tab



列：ID | 平台(`dict_platform_type`) | 关键词 | 匹配类型 | 状态 | 操作



### 3.4 租户采集凭账号 Tab（P1+ · ADR-052）

列：平台 | profile | 展示名 | 连接状态 | 过期时间 | 状态 | 操作

表单：Cookie/Token（脱敏录入）、`expire_at`、探活按钮；**禁止**在外部账号行内嵌密钥。



---



## 4. 元数据维护 UX（FR-M8-008）

路由：`/config-metadata` · 组件 `MetadataManage.vue`

- 实体列表 + 新增/编辑/删除（删除仅超级管理员）
- 新增弹窗：未映射表下拉 `{tableName} ({tableComment})`；选中后默认填充实体名称
- 字段配置抽屉：`query_condition_type`、`dict_type`、`selector_config`

---



## 5. 订单采集配置 UX



列：ID | 名称 | 主机 | 端口 | 数据库名 | 表名 | 采集模式 | 连接状态 | 状态 | 操作(编辑/连接测试/启用/删除)



---



## 5. 阈值规则配置 UX



Tab：预警阈值 | 粉丝阈值 | 作品阈值 | 账号覆盖



各 Tab **独立表格列 + 独立弹窗字段**（非通用表单）：



| Tab | 弹窗关键字段 |

|-----|-------------|

| 预警 | 指标、平台、阈值类型、比较符、阈值、通知渠道 |

| 粉丝 | 平台、低粉/高粉、日增低粉/日增高粉 |

| 作品 | 平台、内容类型、指标、爆款/低分、判定模式 |

| 覆盖 | 平台 + `AccountSelect`、指标、覆盖值 |



---



## 6. AI 模型 / 提示词 UX

（概要见 §8.6–8.7 完整规格）

---

## 8. 页面级完整规格（2026-10-02 · DOC-UX-PAGE-FULL-01）

> **API 前缀**：`/admin-api/ops/config/**`（[`API-M8-配置管理.md`](../engineering/API-M8-配置管理.md)）· **布局**：默认 **A 标题 + B 筛选 + C 表格**（`ContentWrap` + `TableSearch`）。

### 8.1 内部采集配置 `/ops/config/config-internal-collect`

| 项 | 规格 |
|----|------|
| permission | `oa:config:internal-collect:list` |
| 布局 | **Tab 切换 B** + 平台类 **C 表格**；企微/个微为独立 Panel |
| Tab | 公众号/抖音/快手/视频号/服务号/企微/个微 |
| B（平台 Tab） | 账号名称 · 状态(`dict_config_status`) · [查询][重置] |
| C 列 | ID · 平台账号 · 账号标识 · APPID · 直播号 · 状态 · 更新时间 · 操作(编辑/删除) |
| A 按钮 | [新增配置] |
| 弹窗 | `AccountSelect` + 凭证字段（APPSECRET 脱敏·留空不改） |
| 企微 Tab | `WeworkAppConfigPanel`（与个人账号同源） |
| 个微 Tab | 奥创 `apiUrl`/`appId`/`appSecret`/`token` 表单 |
| 删除 | `ElMessageBox.confirm` |
| 状态 | `v-loading` · 空 `el-empty` |

### 8.2 外部采集配置 `/ops/config/config-external-collect`

| Tab | B 筛选 | C 列 | A / 弹窗 |
|-----|--------|------|----------|
| 外部账号 | 平台(`dict_third_platform`) · 名称 · 状态 | ID · 平台 · 账号名称 · 账号标识 · 状态 · 更新时间 · 操作 | [新增][批量导入 CSV][批量删除] · 编辑 dialog：平台/名称/标识/凭证(脱敏) |
| 关键词 | 平台(`dict_platform_type`) · 关键词 · 状态 | ID · 平台 · 关键词 · 匹配类型 · 状态 · 操作 | 编辑：关键词/匹配类型/状态 |
| 租户凭账号 P1+ | — | 平台 · profile · 展示名 · 连接状态 · 过期 · 状态 · 操作 | Cookie/Token 脱敏 · 探活 · **禁止**行内嵌密钥 |

### 8.3 外部数据配置 `/ops/config/config-external-data`

| 项 | 规格 |
|----|------|
| B | 数据源名称 · 状态(`dict_config_status`) |
| C 列 | 多选 · 名称 · 接口地址 · 请求方式(GET/POST tag) · 同步频率 · 状态 · 最后同步 · 操作(编辑/测试/启停/删除) |
| A | [新增数据源][删除选中] |
| dialog 字段 | `sourceName` · `apiUrl` · `requestMethod` · `syncFrequency` · `authType` · `apiKey`/Header（脱敏）· `status` |
| 测试连接 | 行内 [测试连接] → 独立 loading · 成功/失败 Message |
| API | `GET/POST/PUT/DELETE .../external-data/*` · `POST .../test-connection` |

### 8.4 订单采集配置 `/ops/config/config-order-collect`

| B | 名称 · 状态 |
| C 列 | ID · 名称 · 主机 · 端口 · 数据库 · 表名 · 采集模式 · 连接状态 · 状态 · 操作(编辑/连接测试/启用/删除) |
| dialog | JDBC 主机/端口/库/表/用户/密码(脱敏)/采集模式/状态 |
| 连接测试 | MessageBox 二次确认后探活 |

### 8.5 阈值规则 `/ops/config/config-threshold`

| Tab | C 列（摘要） | 弹窗关键字段 |
|-----|-------------|--------------|
| 预警阈值 | 指标 · 平台 · 阈值类型 · 比较符 · 阈值 · 通知渠道 · 状态 | 上列 + `dict_notify_channel` |
| 粉丝阈值 | 平台 · 低粉/高粉 · 日增低/高 | 四类阈值 InputNumber |
| 作品阈值 | 平台 · 内容类型 · 指标 · 爆款/低分 · 判定模式 | 枚举 + 阈值 |
| 账号覆盖 | 平台 · 账号(`AccountSelect`) · 指标 · 覆盖值 | 覆盖值 + 原因 |

各 Tab **独立表格 + 独立 dialog**；删除均 confirm。

### 8.6 AI 模型 `/ops/config/config-ai-model`

| 项 | 规格 |
|----|------|
| A 区 | 4×统计卡（总数/启用/连接正常/默认）+ [新增模型][删除选中] |
| B | 模型名称 · 类型(`dict_ai_model_type`) · 状态 |
| C 列 | 多选 · 名称 · 类型 · API 地址 · maxTokens · temperature · 状态 · 操作(编辑/测试/设默认/启停/删除) |
| dialog | `modelName` · `modelType` · `apiEndpoint` · `apiKey`(脱敏) · `maxTokens` · `temperature` · `isDefault` · `status` |
| 测试连接 | `el-dialog` 或行内 → `POST .../ai-model/test` · 展示 latency/错误信息 |
| 设默认 | confirm · 互斥默认 |

### 8.7 AI 提示词 `/ops/config/config-ai-prompt`

| 项 | 规格 |
|----|------|
| B Tab | 文案生成/数据分析/报告撰写/其他（筛选仍用 `dict_ai_scene`） |
| B 筛选 | 模板名称 · 场景 · 状态 |
| C 列 | 名称 · 场景 · 内容类型 · 文档类型 · 提示词摘要 · 版本 · 状态 · 更新时间 · 操作 |
| dialog | `templateName` · `scene` · `contentType` · `documentType` · `promptContent`（支持 **`{{变量}}` 占位符** 说明）· `version` · `status` |
| 变量 | 侧栏或 tooltip 列出可用占位符（与 M2 AI 排版增量对齐处引用） |

### 8.8 元数据维护 `/ops/config/config-metadata`

| 项 | 规格 |
|----|------|
| permission | `oa:metadata:query` · 删除需 `ROLE_OA_ADMIN` |
| B | 实体名称 · 实体编码 · 状态(`dict_metadata_entity_status`) |
| C 列 | 编码 · 名称 · 物理表 · 状态 · 更新时间 · 操作(字段维护/编辑/删除) |
| 新增 dialog | 未映射表下拉 `{tableName} ({comment})` → 自动填实体名 · 编码 · 状态 · 备注 |
| 编辑 dialog | 编码/物理表只读 · 名称 · 状态 · 备注 |
| **字段 drawer 72%** | 列：字段编码 · 列名 · 显示名(input) · 数据类型 · 查询条件类别(`dict_metadata_query_condition_type`) · 字典类型(select，`needsDictType`) · 排序 · [保存字段配置] |
| API | `metadata/list` · `unmapped-tables` · `fields/update` · [`API-M8`](../engineering/API-M8-配置管理.md) |

---

## 7. 通用规范



- 状态筛选：`dict_config_status`

- 外部账号平台：`dict_third_platform`；关键词平台：`dict_platform_type`

- 密码/API Key：脱敏 + 留空不修改

- 删除二次确认

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v2.2：§8 九页 12 项 Checklist 对齐 Vue · 元数据字段 drawer · AI 测试连接/提示词占位符 |
| 2026-06-11 | v2.1：Football 路由 §1 |


