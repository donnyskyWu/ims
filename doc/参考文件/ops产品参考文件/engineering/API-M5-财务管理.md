# API-M5-财务管理

> **版本**：v1.1 | 2026-06-07 | 2026-10-02
> **关联 PRD**：[`PRD-M5-财务管理.md`](../product/PRD-M5-财务管理.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 账号成本 API

> **前端聚合**（2026-06-11）：`AccountCostManage` 并行调用账号列表 API + 本节 cost/list，按 `accountId` 汇总 `PURCHASE` 与过程成本；平台筛选在账号列表侧完成。

### 1.1 GET `/admin-api/ops/finance/cost/list`

### 1.2 POST `/admin-api/ops/finance/cost/create`

**请求体**：

```json
{
  "accountId": 123,           // 强关联
  "costType": "PURCHASE",     // 字典
  "amount": 1000.00,
  "payMethod": "WECHAT",
  "payDate": "2026-06-07",
  "period": "ONCE",
  "remark": "...",
  "attachmentId": 456
}
```

**校验**：
- `accountId` `@NotNull`
- `costType` `@InDict(type="dict_cost_type")`
- `amount` `@NotNull @DecimalMin("0.01")`
- `payMethod` `@InDict(type="dict_cost_pay_method")`
- `period` `@InDict(type="dict_cost_period")`

### 1.3 PUT `/admin-api/ops/finance/cost/update`

### 1.4 DELETE `/admin-api/ops/finance/cost/{id}`

---

## 2. ROI API

### 2.1 GET `/admin-api/ops/finance/roi/analysis`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| startDate | Date | ✅ | - |
| endDate | Date | ✅ | - |
| ipGroupId | Long | ❌ | - |
| accountId | Long | ❌ | - |
| dimension | String | ❌ | 固定（IP_GROUP/ACCOUNT/PERSON） |

**响应**：

```json
{
  "totalRevenue": 1000000.00,
  "totalCost": 238000.00,
  "roi": 4.20,
  "details": [
    {"name": "八卦一组", "revenue": 500000, "cost": 100000, "roi": 5.00}
  ]
}
```

### 2.2 GET `/admin-api/ops/finance/roi/trend`

### 2.3 GET `/admin-api/ops/finance/roi/breakdown`

**响应**（成本结构）：

```json
{
  "purchase": 100000.00,
  "process": 138000.00,
  "byType": [
    {"type": "PURCHASE", "typeLabel": "购买成本", "amount": 100000, "percentage": 42.02},
    {"type": "PROCESS_HUMAN", "typeLabel": "人力成本", "amount": 100000, "percentage": 42.02}
  ]
}
```

### 2.4 POST `/admin-api/ops/finance/roi/export`

---

## 3. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500~1504 | 全局关联 |
| 2003 | 字典值不合法 |
| 2015 | 金额非法 |
| 2016 | 日期范围非法 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*

---

## 字典与数据安全（🔴 API 必含）

### 字典使用（dict-type）

| 字段 | dict-type | 取值约束 |
|------|-----------|----------|
| finance_type | `dict_finance_type` | 字典合法值，错误码 1503 |
| pay_method | `dict_pay_method` | 字典合法值，错误码 1503 |
| currency | `dict_currency` | 字典合法值，错误码 1503 |
| voucher_type | `dict_voucher_type` | 字典合法值，错误码 1503 |
| finance_status | `dict_finance_status` | 字典合法值，错误码 1503 |

### 数据安全

- **脱敏**：`金额、银行卡号、收款人身份证号` 在 API 响应中按权限脱敏（前端展示如 `138****1234`）
- **加密**：所有凭证字段在数据库中以 **AES-256** 加密存储（key 由配置中心注入）
- **日志**：所有写操作记录 `sys_audit_log`（含 operatorId / operation / before / after）
- **传输**：HTTPS + JWT；敏感字段二次加密（前端公钥 + 后端私钥）

详见 [`GLOBAL-CONVENTIONS.md § 5`](./GLOBAL-CONVENTIONS.md) (数据安全)

---

## 字段字典映射表（🔴 API 必含）

下表列出 财务管理 模块所有需要走数据字典的字段。前端使用 `<DictSelect dict-type="..." />` 组件，后端 `@InDict` 注解校验。

| 字段 | dict-type | 取值范围 | 错误码（不合法时） |
|------|-----------|----------|--------------------|
| `recordType` | `dict_finance_type` | 收入/支出/转账/退款 | 1503 |
| `payMethod` | `dict_pay_method` | 微信/支付宝/银行卡/对公转账 | 1503 |
| `currency` | `dict_currency` | CNY/USD/EUR | 1503 |
| `voucherType` | `dict_voucher_type` | 发票/收据/合同 | 1503 |
| `status` | `dict_finance_status` | 待审/已审/已支付/已驳回 | 1503 |
| `auditStatus` | `dict_audit_status` | 未审/初审/复审/终审 | 1503 |

### 使用规范

1. **前端**：`<DictSelect v-model="form.recordType" dict-type="dict_finance_type" />`
2. **后端**：`@InDict("dict_finance_type") private String recordType;`
3. **字典维护**：在 M8 配置管理模块维护
4. **错误码**：字典值不在范围内 → 1503

详见 [`GLOBAL-CONVENTIONS.md § 2`](./GLOBAL-CONVENTIONS.md) (字典)
