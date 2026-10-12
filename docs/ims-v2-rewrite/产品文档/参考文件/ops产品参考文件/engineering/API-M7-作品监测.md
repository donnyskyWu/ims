# API-M7-作品监测

> **版本**：v1.2 | 2026-10-02
> **关联 UX**：[`UX-M7-作品监测.md`](../product/UX-M7-作品监测.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 外部账号 API

### 1.1 GET `/admin-api/ops/monitor/external/list`

### 1.2 GET `/admin-api/ops/monitor/hit/list`

**爆款作品**（BR-003 = 100w 播放）

### 1.3 GET `/admin-api/ops/monitor/low-score/list`

**低分作品**（BR-004 = 完播率 < 20%）

### 1.4 GET `/admin-api/ops/monitor/high-follower/list`

### 1.5 GET `/admin-api/ops/monitor/low-follower/list`

### 1.6 GET `/admin-api/ops/monitor/ip-theme/{id}`

### 1.7 GET `/admin-api/ops/monitor/industry/{id}`

---

## 2. 通用请求参数

| 参数 | 字典 |
|------|------|
| platformType | `dict_platform_type` |
| contentType | `dict_content_type` |
| ipGroupId | - |
| industry | 固定值 |
| startDate / endDate | - |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

---

## 字典与数据安全（🔴 API 必含）

### 字典使用（dict-type）

| 字段 | dict-type | 取值约束 |
|------|-----------|----------|
| monitor_freq | `dict_monitor_freq` | 字典合法值，错误码 1503 |
| alert_level | `dict_alert_level` | 字典合法值，错误码 1503 |
| work_type | `dict_work_type` | 字典合法值，错误码 1503 |

### 数据安全

- **脱敏**：`被监测账号的 cookie（加密存储）` 在 API 响应中按权限脱敏（前端展示如 `138****1234`）
- **加密**：所有凭证字段在数据库中以 **AES-256** 加密存储（key 由配置中心注入）
- **日志**：所有写操作记录 `sys_audit_log`（含 operatorId / operation / before / after）
- **传输**：HTTPS + JWT；敏感字段二次加密（前端公钥 + 后端私钥）

详见 [`GLOBAL-CONVENTIONS.md § 5`](./GLOBAL-CONVENTIONS.md) (数据安全)

---

## 字段字典映射表（🔴 API 必含）

下表列出 作品监测 模块所有需要走数据字典的字段。前端使用 `<DictSelect dict-type="..." />` 组件，后端 `@InDict` 注解校验。

| 字段 | dict-type | 取值范围 | 错误码（不合法时） |
|------|-----------|----------|--------------------|
| `monitorFreq` | `dict_monitor_freq` | 5min/30min/1h/24h | 1503 |
| `alertLevel` | `dict_alert_level` | 低/中/高/紧急 | 1503 |
| `workType` | `dict_work_type` | 视频/图文/直播/动态 | 1503 |
| `contentType` | `dict_content_type` | 短视频/文章/直播（与 M1 内部作品一致） | 1503 |
| `alertType` | `dict_alert_type` | 流量异常/评论异常/删除/限流 | 1503 |

### 使用规范

1. **前端**：`<DictSelect v-model="form.monitorFreq" dict-type="dict_monitor_freq" />`
2. **后端**：`@InDict("dict_monitor_freq") private String monitorFreq;`
3. **字典维护**：在 M8 配置管理模块维护
4. **错误码**：字典值不在范围内 → 1503

详见 [`GLOBAL-CONVENTIONS.md § 2`](./GLOBAL-CONVENTIONS.md) (字典)
