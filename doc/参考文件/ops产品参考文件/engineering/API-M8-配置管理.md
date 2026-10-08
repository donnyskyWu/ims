# API-M8-配置管理

> **版本**：v1.2 | 2026-10-03（§0.1 PRD §2.3 历史 `/oa` 对照 · `/ops` SSOT）
> **PRD 映射**：`配置管理模块PRD.md` → 本契约（路径前缀 `/admin-api/ops/config`）
> **ADR**：[`ADR-014`](../adr/ADR-014-M8-配置管理数据模型.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

### 0.1 与 PRD §2.3 历史 `/oa/config` 的对照

[`PRD-M8-配置管理.md`](../product/PRD-M8-配置管理.md) §2.3 第四列「历史 `/oa` 别名」仅用于存量 Gateway 代理；**本文档 §1–§9 路径均相对于 `/admin-api/ops/config`**（或 §1 企微 `/admin-api/ops/internal/wework`）。新端点、前端 `src/api/ops/config/*.ts`、OpenAPI 导出 **禁止** 再写 `/admin-api/oa/config/**` 为 SSOT。

## 1. 内部采集 `/internal-collect`

| 方法 | 路径 | 说明 | PRD 映射 |
|------|------|------|----------|
| GET | `/list` | 列表；`platformType`/`configName`/`status`/`pageNo`/`pageSize`；响应含 `accountId`、`accountName`（join `oa_account`） | CFG-002 |
| POST | `/create` | 新增账号 | CFG-003 |
| PUT | `/update` | 编辑 | CFG-004 |
| PUT | `/toggle-status` | `{id, status}` 启用/禁用 | CFG-005 |
| DELETE | `/delete?id=` | 删除 | CFG-006 |

### Create/Update Body（INTERNAL）

```json
{
  "accountId": 9001,
  "configName": "账号名称",
  "accountIdentifier": "openid_xxx",
  "platformType": "DOUYIN",
  "appId": "wx123",
  "appSecret": "secret",
  "cookie": "仅快手",
  "authToken": "仅快手",
  "fieldMapping": "{\"fans\":\"fan_count\"}",
  "isLive": false,
  "status": "ENABLED",
  "remark": ""
}
```

校验：`platformType` `@InDict(dict_platform_type)`；`accountIdentifier` 必填；`status` `@InDict(dict_config_status)`。

### 奥创接口 `/internal-collect/aocreate`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/aocreate` | 获取（管理员） |
| POST | `/aocreate` | 创建/更新 |

Body: `apiUrl`, `appId`, `appSecret`, `token`（AES 存储，响应脱敏）。

### 企业微信应用配置（企微 Tab，非本 Controller）

企微 Tab 复用账号管理 API：

| 方法 | 路径 |
|------|------|
| GET | `/admin-api/ops/internal/wework/list` |
| POST | `/admin-api/ops/internal/wework/create` |
| PUT | `/admin-api/ops/internal/wework/update` |

数据表：`oa_wework_account`。前端组件：`WeworkAppConfigPanel`。

**种子**：`V50` 关联 `oa_account` 9001–9010；`V51` 清理无 `account_id` 的 V43 遗留内部配置。

---

## 2. 外部采集 `/external-collect`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | `subType=account` 外部账号 |
| POST | `/create` | 新增外部账号 |
| PUT | `/update` | 编辑 |
| DELETE | `/delete` | 删除 |
| POST | `/import` | CSV 批量导入（multipart） |

Body（account）: `configName`, `accountIdentifier`, `platformType` `@InDict(dict_third_platform)`, `status`, `subType=account`。

**种子**：V50 灌 4 条外部账号 + 5 条关键词。

### 关键词 `/external-collect/keyword`

| 方法 | 路径 |
|------|------|
| GET | `/keyword/list` |
| POST | `/keyword/create` |
| PUT | `/keyword/update` |
| DELETE | `/keyword/delete?id=` |

Body: `platform`, `keyword`, `matchType` `@InDict(dict_match_type)`, `status`。

---

## 3. 外部数据 `/external-source`

标准 CRUD：`list/create/update/delete`。字段 `configName`, `platformType`, `apiUrl`, `apiKey`, `status`。

---

## 4. 订单采集 `/order-collect`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 数据库配置列表 |
| POST | `/create` | 新增 |
| PUT | `/update` | 编辑 |
| DELETE | `/delete` | 删除 |
| POST | `/test-connection` | 连接测试（30s 超时） |

Body:

```json
{
  "configName": "订单库A",
  "dbHost": "127.0.0.1",
  "dbPort": 3306,
  "dbName": "order_db",
  "dbUsername": "root",
  "dbPassword": "pwd",
  "tableName": "pay_all_order",
  "syncMode": "INCREMENTAL",
  "status": "ENABLED"
}
```

`syncMode` `@InDict(dict_sync_mode)`。

---

## 5. 阈值 `/threshold`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | `thresholdCategory` 必填过滤 |
| POST | `/create` | 按 category 校验字段 |
| PUT | `/update` | 编辑 |
| DELETE | `/delete` | 删除 |

### ALERT 类

`metricName`, `platformType`, `thresholdType`, `compareOperator`, `thresholdValue`, `notifyMethods`, `status`。

### FANS 类

`platformType`, `lowFans`, `highFans`, `dailyLow`, `dailyHigh`, `status`。

### WORK 类

`platformType`, `contentType`, `metricName`, `hotValue`, `lowValue`, `judgeMode`, `status`。

### OVERRIDE 类

`overrideAccountId`（AccountSelect FK 校验 1501）, `metricName`, `overrideValue`, `status`。

---

## 6. AI 模型 `/ai-model`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 含统计 `stats` |
| POST | `/create` | 新增 |
| PUT | `/update` | 编辑；apiKey 留空不修改 |
| DELETE | `/delete` | 默认模型拒绝删除 |
| POST | `/test-connection` | `{id}` 异步测试 |
| PUT | `/set-default` | `{id}` 设默认 |

Body: `modelName`, `modelId`, `apiEndpoint`, `apiKey`, `temperature`, `maxTokens`, `timeout`, `isDefault`, `status`。

---

## 7. AI 提示词 `/ai-prompt`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | |
| GET | `/get?id=` | 详情（查看弹窗） |
| POST | `/create` | 版本 v1 |
| PUT | `/update` | 版本 +1 |
| DELETE | `/delete` | |

Body: `templateName`, `scene`/`type` `@InDict(dict_prompt_type)`, `promptContent`, `status`。

---

## 8. 元数据维护 `/metadata`（ADR-046 · FR-M8-008）

前缀：`/admin-api/ops/metadata`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/list` | `oa:metadata:query` | 实体分页列表 |
| GET | `/unmapped-tables` | `oa:metadata:query` | 未映射物理表；含 `tableComment` |
| GET | `/table-columns` | `oa:metadata:query` | 指定表列信息 |
| POST | `/create` | `oa:metadata:create` | 新建实体 |
| GET | `/{id}` | `oa:metadata:query` | 实体详情 |
| PUT | `/update` | `oa:metadata:update` | 更新实体 |
| DELETE | `/{id}` | **`ROLE_OA_ADMIN`** | 仅超级管理员 |
| PUT | `/{entityId}/fields` | `oa:metadata:update` | 批量保存字段配置 |
| GET | `/entity/{code}/fields` | `oa:metadata:query` | M6 指标/自定义查询读口 |

**`UnmappedTableVO`**：`tableName`、`suggestedEntityCode`、`suggestedEntityName`、`tableComment`（`INFORMATION_SCHEMA.TABLES.TABLE_COMMENT`）。

---

## 字典映射

| 字段 | dict-type |
|------|-----------|
| platformType | dict_platform_type |
| status | dict_config_status |
| matchType | dict_match_type |
| syncMode | dict_sync_mode |
| thresholdCategory | dict_threshold_category |
| thresholdType | dict_threshold_type |
| contentType | dict_content_type |
| judgeMode | dict_judge_mode |
| connStatus | dict_conn_status |
| scene/type | dict_prompt_type |
| notifyMethods | dict_notify_channel |

## 数据安全

- 凭证 AES-256；响应 `*Masked` 或 `****`
- 写操作 `@AuditLog`
- 跨租户 1504
