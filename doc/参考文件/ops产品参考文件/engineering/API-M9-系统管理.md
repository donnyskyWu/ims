# API-M9-系统管理

> **版本**：v1.1 | 2026-06-11 | 2026-10-02（ADR-013 部门 + 钉钉同步）
> **关联 ADR**：[`ADR-009`](../adr/ADR-009-API路径前缀分配.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)
>
> **规范路径**：`/admin-api/ops/system/*` · 旧 `/admin-api/system/*` 仍作兼容别名（S-R23）

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 部门 API（ADR-013，前缀 `/admin-api/ops/system/dept`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/tree` | `oa:dept:list` | 部门树 |
| POST | `/create` | `oa:dept:create` | 本地创建 |
| PUT | `/update` | `oa:dept:update` | 本地更新 |
| DELETE | `/delete?id=` | `oa:dept:delete` | 有子部门或用户 → 1502 |
| POST | `/sync-dingtalk` | `oa:dept:sync-dingtalk` | 全量同步钉钉部门 |
| POST | `/sync-dingtalk-users` | `oa:user:sync-dingtalk` | 按已同步部门拉取钉钉用户 |

**数据模型** `sys_dept`：`tenant_id`, `parent_id`, `name`, `ding_dept_id`, `sort`, `status`

兼容别名：`/admin-api/system/dept/*`

---

## 2. 用户 API

### 2.1 GET `/admin-api/ops/system/user/list`

| 参数 | 字典 |
|------|------|
| status | `dict_user_status` |
| deptId | `sys_dept.id`（左侧树选中筛选） |
| position | `dict_position` |
| username / realName | 模糊搜索 |

### 2.2 POST `/admin-api/ops/system/user/create`

```json
{
  "username": "zhangsan",
  "nickname": "张三",
  "email": "zhangsan@xxx.com",
  "phone": "13800001111",
  "position": "OPS_LEADER",
  "deptId": 10,
  "dingUserId": "ding_xxx",
  "ipGroupId": 1,
  "status": 1
}
```

**校验**：
- `position` `@InDict(type="dict_position")`
- `status` `@InDict(type="dict_user_status")`
- `deptId` 可选，存在且同租户
- `dingUserId` 可选，`(tenant_id, ding_user_id)` 唯一

**钉钉同步规则**（手动触发）：
- 部门：以 `ding_dept_id + tenant_id` 幂等 upsert
- 用户：以 `ding_user_id` upsert；`username = ding_user_id`；新用户默认 `OPS_OPERATOR`；不删除已有本地用户

---

## 3. 角色 API

### 3.1 GET `/admin-api/ops/system/role/list`

### 3.2 POST `/admin-api/ops/system/role/assign-permission`

---

## 4. 租户 API

### 4.1 GET `/admin-api/ops/system/tenant/list`

### 4.2 POST `/admin-api/ops/system/tenant/create`

---

## 5. 字典 API（⭐）

### 5.1 GET `/admin-api/ops/system/dict/type?type={type}`

**响应**：

```json
{
  "dictType": "dict_platform_type",
  "dictName": "平台类型",
  "items": [
    {"value": "WECHAT_OFFICIAL", "label": "公众号", "sort": 1, "status": 0, "colorType": "default"}
  ]
}
```

### 5.2 GET `/admin-api/ops/system/dict/type-list`

字典 type 列表（用于下拉选择 dict_type）

### 5.3 POST `/admin-api/ops/system/dict/create`

```json
{
  "dictType": "dict_value_placeholder",
  "dictName": "xxx",
  "items": [
    {"dictLabel": "xxx", "dictValue": "（具体值详见相应章节）
  ]
}
```

**校验**：
- `dictType` 命名 `dict_value_placeholder`
- `dictValue` 命名 `（具体值详见相应章节）
- `dictType` 唯一

### 5.4 PUT `/admin-api/ops/system/dict/update`

### 5.5 DELETE `/admin-api/ops/system/dict/{id}`

**业务**：停用后可删；启用且被引用 → 错误码 1502

---

## 6. 日志 API

### 6.1 GET `/admin-api/ops/system/log/operation`

| 参数 | 字典 |
|------|------|
| module | `dict_log_module` |
| level | `dict_log_level` |

### 6.2 GET `/admin-api/ops/system/log/login`

---

## 7. 头部个人中心 / 消息中心 API

### 7.1 GET `/admin-api/ops/system/user/profile`

返回当前登录用户只读资料：`id`、`username`、`nickname`、`email`、`phoneMasked`、`position`、`deptName`、`roleNames`、`status`。不返回密码、token、明文手机号等敏感字段。

### 7.2 GET `/admin-api/ops/system/message/unread-count`

返回当前登录用户未读站内消息数。收件人匹配当前登录用户的 `userId` / `username` / `nickname` / `email`，并限定同租户、`status=SENT`、`read_time IS NULL`。

### 7.3 GET `/admin-api/ops/system/message/unread`

| 参数 | 说明 |
|------|------|
| pageNo | 默认 1 |
| pageSize | 默认 10 |

返回当前登录用户未读消息分页，响应项沿用 `MessageVO`，新增 `read`、`readTime`。

### 7.4 PUT `/admin-api/ops/system/message/read?id=`

将当前登录用户有权查看的消息标记为已读，写入 `sys_message.read_time`。

---

## 9. 业务通知与钉钉推送（ADR-026 · V88）

### 9.1 配置项（`application.yml` / `application-dev-local.yml`）

| 前缀 | 键 | 说明 |
|------|-----|------|
| `oa.dingtalk` | `enabled`, `client-id`, `client-secret`, `corp-id`, `agent-id` | 工作通知主通道 |
| `oa.dingtalk.robot` | `enabled`, `webhook-url`, `secret` | 可选降级 |
| `oa.notification` | `platform-base-url`, `monitor-scan-cron` | 跳转链接与扫描周期 |

### 9.2 事件去重

插入 `sys_notification_event` 成功后才调用 `send()`；重复 `biz_key` 返回 `DuplicateKeyException` 并跳过。

### 9.3 开发态诊断

`GET /admin-api/ops/dev/dingtalk-status`（若已实现）返回工作通知/机器人是否可用及 skip 原因。

---

## 8. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500~1504 | 全局 |
| 1502 | 字典被引用 |
| 2019 | 字典 type 重复 |
| 2020 | 字典 value 重复 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

---

## 字典与数据安全（🔴 API 必含）

### 字典使用（dict-type）

| 字段 | dict-type | 取值约束 |
|------|-----------|----------|
| user_role | `dict_user_role` | 字典合法值，错误码 1503 |
| user_status | `dict_user_status` | 字典合法值，错误码 1503 |
| log_type | `dict_log_type` | 字典合法值，错误码 1503 |

### 数据安全

- **脱敏**：`用户密码（BCrypt 加密）、手机号、邮箱` 在 API 响应中按权限脱敏（前端展示如 `138****1234`）
- **加密**：所有凭证字段在数据库中以 **AES-256** 加密存储（key 由配置中心注入）
- **日志**：所有写操作记录 `sys_audit_log`（含 operatorId / operation / before / after）
- **传输**：HTTPS + JWT；敏感字段二次加密（前端公钥 + 后端私钥）

详见 [`GLOBAL-CONVENTIONS.md § 5`](./GLOBAL-CONVENTIONS.md) (数据安全)

---

## 字段字典映射表（🔴 API 必含）

下表列出 系统管理 模块所有需要走数据字典的字段。前端使用 `<DictSelect dict-type="..." />` 组件，后端 `@InDict` 注解校验。

| 字段 | dict-type | 取值范围 | 错误码（不合法时） |
|------|-----------|----------|--------------------|
| `userStatus` | `dict_user_status` | 启用/停用/锁定 | 1503 |
| `userRole` | `dict_user_role` | 超管/管理员/运营/编辑/查看 | 1503 |
| `logType` | `dict_log_type` | 登录/操作/异常/审计 | 1503 |
| `logLevel` | `dict_log_level` | DEBUG/INFO/WARN/ERROR | 1503 |

### 使用规范

1. **前端**：`<DictSelect v-model="form.userStatus" dict-type="dict_user_status" />`
2. **后端**：`@InDict("dict_user_status") private String userStatus;`
3. **字典维护**：在 M8 配置管理模块维护
4. **错误码**：字典值不在范围内 → 1503

详见 [`GLOBAL-CONVENTIONS.md § 2`](./GLOBAL-CONVENTIONS.md) (字典)
