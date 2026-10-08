# CORP-公司资产 - API 契约（OPS M4 透传 / IMS BFF）

> **前缀（目标）**：`/admin-api/ims/corp`  
> **现网 OPS 路径（SSOT）**：`/admin-api/oa/account/*`、`/admin-api/oa/internal/*`（见 `docs/engineering/API-M4-账号管理.md`）  
> **响应包裹**：`{ code, msg, data }`；业务错误 **1500～1504**（GLOBAL-CONVENTIONS）  
> **禁止发明字段**：下列仅列已文档化下游；扩展须先改 OPS API 或 VA Spec。

---

## 1. 账号管理 · 按平台（P-A1～P-A5）

### 1.1 GET `/admin-api/ims/corp/account/page`

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| pageNo / pageSize | ✅ | 分页 |
| platformType | ✅ | L3 路由固定：`WECHAT_OFFICIAL` \| `WECHAT_CHANNELS` \| `DOUYIN` \| `KUAISHOU` \| `XIAOHONGSHU` |
| keyword | | 编号/昵称 |
| ipGroupId | | IP 组 |
| companyId | | 公司 |
| status | | 账号状态字典 |

**BFF → OPS**

| 状态 | 下游 |
|------|------|
| ✅ | `GET /admin-api/oa/account/platform/page`（或现网等价 list）+ **强制** `platformType` |
| **TBD** | IMS 路由 `/ims/corp/account/*` 与 OPS `/account/platform` **菜单拆分** 的权限码映射 |

**Response `data.list[]`（摘要）**

| 字段 | 说明 |
|------|------|
| id / accountNo | 账号主键（字符串 snowflake） |
| nickname | 昵称 |
| platformType | 平台 |
| ipGroupName | IP 组 |
| realNameMasked | 实名人脱敏 |
| companyName | 公司 |
| status | 状态 |
| collectBindSummary | 采集绑定摘要（只读） |

### 1.2 GET `/admin-api/ims/corp/account/{id}`

**下游**：OPS 平台账号详情（P-M4-009）

### 1.3 采集 Tab（ADR-047）

**禁止**在本模块新建 Cookie API；透传 OPS 账号采集接口，见 `ACCT-账号管理-API契约.md` 与 `ACCT-平台账号采集Tab-OPS对齐.md`。

### 1.4 领用/流转/冲话费

| 能力 | 状态 |
|------|------|
| ACCT-001～004 流程 API | **BLOCKED 导航** — Spec 已有 `/ims/account/apply` 等路由，走查 #8 **未** 规定 L2 入口；默认 **详情抽屉按钮** 跳转既有 ACCT 路由（待产品确认） |

---

## 2. 资源管理（P-R1～P-R4）

| IMS 路径 | 方法 | OPS 下游 | 状态 |
|----------|------|----------|------|
| `/corp/resource/company/page` | GET | `oa_company` list（M4 P-M4-001） | ✅ |
| `/corp/resource/company/{id}` | GET | 公司详情 | ✅ |
| `/corp/resource/realname/page` | GET | 实名人 list | ✅ |
| `/corp/resource/realname/{id}` | GET | 实名人详情 | ✅ |
| `/corp/resource/sim-card/page` | GET | `GET /admin-api/ops/sim-card/list` | ✅ |
| `/corp/resource/sim-card/{id}` | GET | 卡详情 + `GET …/sim-card/{id}/linked-accounts` | ✅ |
| `/corp/resource/sim-card` | POST | `POST /admin-api/ops/sim-card/create` | ✅ |
| `/corp/resource/sim-card/{id}` | PUT | `PUT /admin-api/ops/sim-card/update`（现网等价） | ✅ |
| `/corp/resource/certificate/page` | GET | IMS CERT `/ims/cert/archive` 等价 | ✅ IMS |
| `/corp/resource/certificate/{id}/view` | GET | 水印代理 CERT-003 | ✅ IMS |

### 2.1 SIM 写请求（透传 OPS · 禁止发明列）

**Create/Update Body** = `API-M4-账号管理.md` §4.2 **并集** `DATA-VA-虚拟资产扩展.md` §1.1 `oa_sim_card` 扩展列（**ADR-074** `realname_id` 可选）：

| 字段 | 来源 | 说明 |
|------|------|------|
| `phoneId` / `phoneNumber` | M4 §4.2 | 二选一；优先 `phoneId` |
| `isPrimary` | M4 | `dict_yes_no` |
| `operator` | M4 | `dict_sim_operator` |
| `assignedUserId` | M4 | `<UserSelect />` |
| `iccid` | M4 | AES-256 |
| `packageName` | M4 | 套餐名 |
| `status` | M4 | 启用状态 |
| `realnameId` | DATA-VA §1.1 · ADR-074 | `<RealNameSelect />` 可选 |
| `activatedAt` | DATA-VA §1.1 | 开卡日 |
| `monthlyRent` | DATA-VA §1.1 | 月租 |
| `paymentCycle` | DATA-VA §1.1 | `dict_payment_cycle` |
| `nextPaymentDate` | DATA-VA §1.1 | 下次缴费 |

**响应**：200 时可含 `warnings[]`（如 `REALNAME_MISMATCH` · `API-VA-MAINT` §1.1）；**不** 1502。

---

## 3. 设备管理（P-D1～P-D3）

| IMS 路径 | 方法 | 下游 | 状态 |
|----------|------|------|------|
| `/corp/device/phone/page` | GET | `oa_phone`（M4 P-M4-005） | ✅ |
| `/corp/device/phone/{id}` | GET | 手机详情 | ✅ |
| `/corp/device/office/page` | GET | **`GET /admin-api/ims/asset/ledger/page`** · Query `assetType=OFFICE`（`dict_asset_type`） | ✅（ASSET 既有台账 · 2026-10-01） |
| `/corp/device/live/page` | GET | 同上 · Query `assetType` **`LIVE` 与 `SHOOT` 各查一次合并** 或 `assetTypes=LIVE,SHOOT`（BFF 约定一种，禁止新表） | ✅ |
| `/corp/device/{assetId}/forward` | GET | ASSET-001 L1 穿透 | ✅ IMS |

---

## 4. 错误码

| code | 场景 |
|------|------|
| 1500 | 公司/实名人/手机/手机卡/IP 组**强关联实体不存在** |
| 1501 | 关联的实体**已停用/注销**（仅可选启用态实体，停用/注销不可选） |
| 1502 | 关联的实体**已被其他记录引用**（强关联阻挡删除） |
| 1503 | 字典枚举非法 |
| 1504 | 跨租户访问禁止 |

> **语义对齐**（2026-10-03）：本节 1500~1504 对齐现网 `GLOBAL-CONVENTIONS.md` §5.3 权威语义；选择器绑定的「不存在 / 已停用 / 已被引用」三态分别用 1500 / 1501 / 1502 区分，**不再**把「不存在」与「跨租户」合并为 1501。详见 [错误码映射表（附录）](../错误码映射表-附录.md) §3。

---

## 5. 禁止项

- **不得** 为走查骨架新增 fake CRUD（占位 list 返回空数组 + `BLOCKED` 文档即可）。
- **不得** 将 `oa_external_account`（竞品）或 COLLECT Channel-D 配置接入本模块 BFF。
