# API-M10-数据采集

> **版本**：v1.1 | 2026-06-24 | 2026-10-02
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 采集任务 API

### 1.1 GET `/admin-api/ops/collect/task/list`

| 参数 | 字典 |
|------|------|
| platformType | `dict_platform_type` |
| method | `dict_collect_method` |
| frequency | `dict_collect_frequency` |
| status | `dict_collect_status` |

### 1.2 POST `/admin-api/ops/collect/task/create`

**Channel-A 示例**：

```json
{
  "taskName": "公众号每日数据采集",
  "platformType": "WECHAT_OFFICIAL",
  "accountId": 123,            // 强关联
  "method": "INTERNAL",
  "source": "WECHAT_MP_API",
  "frequency": "DAILY",
  "cron": "0 0 2 * * ?",
  "dataType": null,
  "apiConfig": "{...}",
  "status": "ENABLED"
}
```

**Channel-D 示例**（`method=EXTERNAL`）：见 §8.1。

> **`dataType`**：省略或 `null` 表示按平台 **全量** 采集（ADR-049）；存库规范化后仍为 `null`。指定单一值时仅执行该类型（IT/API 保留；Channel-A 运营 UI 不暴露）。

**校验**：
- `platformType` `@InDict(type="dict_platform_type")`
- Channel-A：`accountId` `@NotNull`；Channel-D：`collectConfigId` `@NotNull` 且 `accountId` 必须为 null
- `method` `@InDict(type="dict_collect_method")`
- `source` `@InDict(type="dict_collect_source")`
- `frequency` `@InDict(type="dict_collect_frequency")`
- `status` `@InDict(type="dict_collect_status")`
- `apiConfig` AES-256 加密

> **Delta · ADR-061（假设 A1）**：Channel-A **租户统一任务**路径 — `isUnified=true` / `accountId=null`，成员经 `GET/POST …/task/{id}/members` 与账号 `collectEnabled` 同步；`POST /admin-api/ops/collect/task/ensure-unified` 自动创建。单账号任务创建规则不变。路径前缀在 football 为 `/admin-api/ops/collect/...`。
>
> **`GET …/task/{id}/members` 响应字段**：`accountId` · **`accountName`（展示名，必填语义：oa 平台账号取 `oa_account.account_name`，公众号 mp SSOT 取 `mp_account.name`）** · `platformType` · `collectEnabled` · `createTime`。UI 以名称为主、编号为辅。

### 1.3 PUT `/admin-api/ops/collect/task/update`

### 1.4 DELETE `/admin-api/ops/collect/task/{id}`

### 1.5 POST `/admin-api/ops/collect/task/{id}/run`

**业务**：
- 立即执行一次
- 同步调用（v1.0 简化）
- 记录到 `oa_collect_log`

### 1.6 GET `/admin-api/ops/collect/log`

| 参数 | 字典 |
|------|------|
| taskId | - |
| status | `dict_collect_status`（含 `PARTIAL`） |
| startDate / endDate | - |

### 1.7 GET `/admin-api/ops/collect/log/{id}`

返回日志详情，含结构化 `result`（V120 `result_json`）。

```json
{
  "id": 101,
  "taskId": 12,
  "status": "PARTIAL",
  "recordCount": 42,
  "platformType": "DOUYIN",
  "accountId": 9006,
  "result": {
    "summary": "4/4 types attempted, 3 succeeded",
    "dataType": "ALL",
    "typeResults": [
      {
        "dataType": "FOLLOWER_STATS",
        "success": true,
        "recordCount": 1,
        "targetTable": "oa_account_status_log"
      },
      {
        "dataType": "DOUYIN_VIDEO_LIST",
        "success": true,
        "recordCount": 15,
        "targetTable": "oa_douyin_video"
      }
    ]
  }
}
```

**业务**：
- 单类型执行：`typeResults` 为空，顶层 `dataType` / `recordCount` / `samples` 有效
- 全量执行：`dataType=ALL`，`typeResults` 逐类型明细；日志 `status` 按 ADR-049 Q3 判定

---

## 2. 数据质量 API

### 2.1 GET `/admin-api/ops/collect/quality/list`

### 2.2 POST `/admin-api/ops/collect/quality/create`

```json
{
  "checkName": "粉丝数非空检查",
  "checkType": "COMPLETENESS",
  "targetTable": "oa_follower_daily",
  "targetField": "follower_count",
  "rule": "follower_count IS NOT NULL",
  "level": "EXCELLENT"
}
```

**校验**：
- `checkType` `@InDict(type="dict_quality_check_type")`
- `level` `@InDict(type="dict_quality_level")`

### 2.3 POST `/admin-api/ops/collect/quality/{id}/run`

**业务**：
- 执行质量检查
- 返回合格率

### 2.4 GET `/admin-api/ops/collect/quality/log`

---

## 3. Collector 绑定 API（Channel-A · ADR-047）

> 凭证 SSOT 在 M4 `oa_account`；本组 API 负责 import / bind / 探活。详见 [ADR-047](../adr/ADR-047-M4-平台账号凭证SSOT与Collector映射.md)。

### 3.1 GET `/admin-api/ops/account/{oaAccountId}/collector-bind`

返回 `oa_collector_account_bind` 绑定状态（无 bind 时 `data` 为 `null`）。

| 字段 | 说明 |
|------|------|
| `oaAccountId` | M4 平台账号 ID |
| `collectorAccountId` | collector 侧 `acc_{platform}_{hash}` |
| `platformType` | `dict_platform_type` |
| `bindStatus` | `dict_collector_bind_status` |
| `connStatus` | `dict_conn_status` |

**权限**：`oa:account:list`

### 3.2 POST `/admin-api/ops/account/{oaAccountId}/collector-bind`

从 M4 凭证组装 credential → 调用 collector `POST /api/v1/accounts/import` → 写入 bind 行。

**业务**：MVP **不读** `app_secret_encrypted`（ADR-047 Q1）。

### 3.3 POST `/admin-api/ops/account/{oaAccountId}/collector-bind/sync`

凭证变更后同步至 collector（re-import / update credential）。

### 3.4 POST `/admin-api/ops/account/{oaAccountId}/collector-bind/test-connection`

探活：collector `GET /api/v1/accounts/health`，更新 `conn_status`。

**响应**：

```json
{
  "success": true,
  "connStatus": "CONNECTED",
  "collectorAccountId": "acc_wechat_mp_xxx",
  "message": "连接正常"
}
```

### 3.5 POST `/admin-api/ops/collector-bind/batch-import`

租户内批量绑定：扫描 Channel-A 支持平台、凭证齐全且尚无 bind 的 `oa_account`，逐条 import。

**权限**：`oa:account:list`

**响应**：

```json
{
  "scanned": 12,
  "imported": 3,
  "skipped": 8,
  "failed": 1,
  "items": [
    { "oaAccountId": 9006, "platformType": "DOUYIN", "result": "IMPORTED", "message": null }
  ]
}
```

| `result` | 含义 |
|----------|------|
| `IMPORTED` | 成功 import 并写入 bind |
| `SKIPPED` | 已有 bind 或凭证不完整 |
| `FAILED` | collector 或校验失败 |

### 3.6 扫码登录代理（ADR-050）

> OA 代理 unify-collector-api `POST/GET/DELETE /api/v1/auth/qrcode|poll`；凭证落 M4 SSOT。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/ops/account/{oaAccountId}/collector-bind/qr-login/start` | 返回 `sessionId`、`qrcodeBase64` |
| GET | `/admin-api/ops/account/{oaAccountId}/collector-bind/qr-login/poll?sessionId=` | `status`: pending/scanned/confirmed/expired/error |
| DELETE | `/admin-api/ops/account/{oaAccountId}/collector-bind/qr-login/cancel?sessionId=` | 取消会话 |

**支持平台**：`WECHAT_OFFICIAL`、`WECHAT_VIDEO`、`DOUYIN`、`KUAISHOU`、`XIAOHONGSHU`。

**poll confirmed**：写入 `oa_account` 凭证；若 poll 含 `account_id` 则直接 bind，否则尝试 `collector-bind` import。

**权限**：`oa:account:list`

## 4. Channel-A 采集源（`dict_collect_source`）

M10 任务 `source` + `method=INTERNAL` 经 `UnifiedCollectorAdapter` 路由至 unify-collector-api。

| `source` | `platform_type` | collector `platform` | MVP 凭证（M4） |
|----------|-----------------|----------------------|----------------|
| `WECHAT_MP_API` | `WECHAT_OFFICIAL` | `wechat_mp` | cookie + mp_token |
| `WECHAT_CHANNELS_API` | `WECHAT_VIDEO` | `wechat_channels` | cookie |
| `DOUYIN_OPEN_API` | `DOUYIN` | `douyin` | cookie |
| `KUAISHOU_OPEN_API` | `KUAISHOU` | `kuaishou` | cookie + auth_token + field_mapping |
| `XIAOHONGSHU_OPEN_API` | `XIAOHONGSHU` | `xiaohongshu` | cookie |
| `BILIBILI_OPEN_API` | `BILIBILI` | `bilibili` | cookie |

**不经 Channel-A bind**：`AOCHUANG_API`（奥创 · ADR-045）、`WECOM_API`（企微 · ADR-048）、`PERSONAL_WECHAT_API`（个微）— 见 ADR-045 / ADR-048。

任务创建时 `accountId` 强关联 M4 账号（企微 → `oa_wework_account.id`）；执行时 Channel-A：`oa_account_id` → bind → `collector_account_id`。

---

## 5. 平台默认 dataType（ADR-049）

`CollectPlatformDefaults` — `data_type` 为空时按序执行：

| `platform_type` | 默认 `source` | dataTypes（顺序） |
|-----------------|---------------|-------------------|
| `WECHAT_OFFICIAL` | `WECHAT_MP_API` | MP_FOLLOWER_STATS → MP_FOLLOWER_LIST → MP_ARTICLE_LIST → MP_ARTICLE_STATS → MP_ARTICLE_CONTENT |
| `WECHAT_VIDEO` | `WECHAT_CHANNELS_API` | FOLLOWER_STATS → WECHAT_VIDEO_LIST → WECHAT_VIDEO_STATS |
| `DOUYIN` | `DOUYIN_OPEN_API` | FOLLOWER_STATS → DOUYIN_FOLLOWER_LIST → DOUYIN_VIDEO_LIST → DOUYIN_VIDEO_STATS |
| `KUAISHOU` | `KUAISHOU_OPEN_API` | FOLLOWER_STATS → KUAISHOU_VIDEO_LIST → KUAISHOU_VIDEO_STATS |
| `XIAOHONGSHU` | `XIAOHONGSHU_OPEN_API` | FOLLOWER_STATS → XIAOHONGSHU_NOTE_LIST → XIAOHONGSHU_NOTE_STATS |
| `BILIBILI` | `BILIBILI_OPEN_API` | FOLLOWER_STATS only |
| `WEWORK` | `WECOM_API` | WECOM_DAILY_STATS |

创建/更新任务时 `method` / `source` 可由后端按上表补全（请求体可省略）。

---

## 6. Channel-A 落库表（V116 / V121 / V122）

| 表 | dataType | UK |
|----|----------|-----|
| `oa_wechat_mp_follower` | MP_FOLLOWER_LIST | tenant + account + openid |
| `oa_wechat_mp_article` | MP_ARTICLE_* | tenant + account + msgid_itemidx |
| `oa_douyin_follower` | DOUYIN_FOLLOWER_LIST | tenant + account + follower_id |
| `oa_douyin_video` | DOUYIN_VIDEO_* | tenant + account + video_id |
| `oa_wechat_video_work` | WECHAT_VIDEO_* | tenant + account + video_id |
| `oa_kuaishou_video` | KUAISHOU_VIDEO_* | tenant + account + video_id |
| `oa_xiaohongshu_note` | XIAOHONGSHU_NOTE_* | tenant + account + note_id |
| `oa_wework_daily_stats` | WECOM_DAILY_STATS | tenant + wework_account + stat_date |

粉丝日聚合写入 `oa_account_status_log`（`FOLLOWER_STATS` 哨兵路由）。

---

## 8. Channel-D 外部竞品 API（ADR-052 · GATE-EXT-P0）

> 完整 phased 契约见 [M10-EXTERNAL-四平台竞品采集-SLICE](../delivery/M10-EXTERNAL-四平台竞品采集-SLICE.md) §4。

### 8.1 采集任务 create/update（增量字段）

```json
{
  "taskName": "快手竞品-作品",
  "platformType": "KUAISHOU",
  "method": "EXTERNAL",
  "source": "UNIFY_COLLECTOR_EXTERNAL",
  "collectConfigId": 96001,
  "accountId": null,
  "credentialProfile": "default",
  "dataType": "EXT_KUAISHOU_USER_VIDEOS",
  "frequency": "DAILY",
  "status": "ENABLED"
}
```

**校验**：

| 规则 | 说明 |
|------|------|
| `method=EXTERNAL` | `collectConfigId` **必填**；`accountId` **必须 null** |
| `collectConfigId` | 须指向 `oa_collect_config` 且 `scope=EXTERNAL`, `sub_type=account`, `platform_type` 与任务一致 |
| 凭账号 | 由 `tenant_id` + `platform_type` + `credentialProfile` 解析 `oa_tenant_collector_credential`；**不在此 API 传 cookie** |
| `method=INTERNAL` | 沿用 §1.2（`accountId` 必填） |

### 8.2 新增 `dict_collect_data_type`（外部竞品 · phased）

| 值 | 平台 | Gate |
|----|------|------|
| `EXT_KUAISHOU_USER_VIDEOS` | 快手 | P0 |
| `EXT_WECHAT_MP_SEARCH` | 公众号 | P1 |
| `EXT_WECHAT_MP_ARTICLE_LIST` | 公众号 | P1 |
| `EXT_DOUYIN_USER_PROFILE` / `EXT_DOUYIN_USER_VIDEOS` | 抖音 | P2 |
| `EXT_WECHAT_VIDEO_*` | 视频号 | P3 |

### 8.3 落库表（V136+）

| 表 | 说明 |
|----|------|
| `oa_external_account` | 竞品账号快照；FK `collect_config_id` |
| `oa_external_work` | 竞品作品；`account_id` → `oa_external_account.id`；UK `(tenant_id, platform_type, platform_work_id)` |
| `oa_external_follower_daily` | 粉丝日聚合 |
| `oa_tenant_collector_credential` | 租户级运营凭账号（AES-256） |

### 8.4 Collector HTTP（Ops Client · P0）

| dataType | HTTP | 参数 |
|----------|------|------|
| `EXT_KUAISHOU_USER_VIDEOS` | `GET /api/v1/external/kuaishou/user-videos` | `user_id` ← M8 `account_identifier` |

---

## 7. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500~1504 | 全局 |
| 1503 | 字典值不合法 |
| 2021 | cron 表达式非法 |
| 2022 | 采集失败 |
| 2023 | 质量检查规则非法 |
| 2024 | Collector 绑定失败 / 凭证不完整 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

---

## 字典与数据安全（🔴 API 必含）

### 字典使用（dict-type）

| 字段 | dict-type | 取值约束 |
|------|-----------|----------|
| collect_freq | `dict_collect_freq` | 字典合法值，错误码 1503 |
| collect_type | `dict_collect_type` | 字典合法值，错误码 1503 |
| proxy_type | `dict_proxy_type` | 字典合法值，错误码 1503 |

### 数据安全

- **脱敏**：`Cookie（**AES-256 加密**）、账号密码（**AES-256 加密**）、API 密钥` 在 API 响应中按权限脱敏（前端展示如 `138****1234`）
- **加密**：所有凭证字段在数据库中以 **AES-256** 加密存储（key 由配置中心注入）
- **日志**：所有写操作记录 `sys_audit_log`（含 operatorId / operation / before / after）
- **传输**：HTTPS + JWT；敏感字段二次加密（前端公钥 + 后端私钥）

详见 [`GLOBAL-CONVENTIONS.md § 5`](./GLOBAL-CONVENTIONS.md) (数据安全)

---

## 字段字典映射表（🔴 API 必含）

下表列出 数据采集 模块所有需要走数据字典的字段。前端使用 `<DictSelect dict-type="..." />` 组件，后端 `@InDict` 注解校验。

| 字段 | dict-type | 取值范围 | 错误码（不合法时） |
|------|-----------|----------|--------------------|
| `collectType` | `dict_collect_type` | 视频/评论/账号/作品 | 1503 |
| `collectFreq` | `dict_collect_freq` | 5min/30min/1h/24h | 1503 |
| `proxyType` | `dict_proxy_type` | 无/HTTP/HTTPS/SOCKS | 1503 |
| `authType` | `dict_auth_type` | 无/账密/Cookie/扫码/Token | 1503 |
| `status` | `dict_collect_status` | 待运行/运行中/暂停/失败/已停止 | 1503 |

### 使用规范

1. **前端**：`<DictSelect v-model="form.collectType" dict-type="dict_collect_type" />`
2. **后端**：`@InDict("dict_collect_type") private String collectType;`
3. **字典维护**：在 M8 配置管理模块维护
4. **错误码**：字典值不在范围内 → 1503

详见 [`GLOBAL-CONVENTIONS.md § 2`](./GLOBAL-CONVENTIONS.md) (字典)

## 强关联字段 → 选择器映射（🔴 API 必含）

本模块涉及以下强关联字段，**前端必须使用对应选择器组件**：

| 字段 | 选择器组件 | 关联实体 | 错误码 |
|------|----------|---------|--------|
| `accountId` | `<AccountSelect />` | 平台账号（Channel-A） | 1501 / 1504 |
| `collectConfigId` | 外部竞品配置选择器 | `oa_collect_config`（EXTERNAL） | 1501 / 1504 |
| `proxyType` | `<DictSelect dict-type="dict_proxy_type" />` | 代理类型 | 1503 |
| `authType` | `<DictSelect dict-type="dict_auth_type" />` | 认证类型 | 1503 |
| `collectFreq` | `<DictSelect dict-type="dict_collect_freq" />` | 采集频率 | 1503 |
