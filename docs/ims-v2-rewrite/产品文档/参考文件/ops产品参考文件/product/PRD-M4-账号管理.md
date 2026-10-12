# PRD-M4-账号管理

> **业务域**：M4 账号管理
> **功能模块**：公司 + 实名人 + 手机 + 手机卡 + 平台账号 + 个人账号 + 三方关联
> **详细设计章节**：5.16、5.17、5.18、5.19、5.20、5.21、5.22
> **版本**：v1.5 | 2026-10-03
> **状态**：Draft（实现同步修订）
> **🔴 关键模块**（关联属性集中地）
> **全局规范**：[`docs/engineering/GLOBAL-CONVENTIONS.md`](./../engineering/GLOBAL-CONVENTIONS.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| 模块 | M4 账号管理 |
| 业务域 | 账号管理（INTERNAL） |
| 详细设计 | `## 5.16~5.22` |
| 父 PRD | `@完整PRD-v9.1-开发版.md` |
| 关联 UX | `docs/product/UX-M4-账号管理.md` |
| 关联 API | `docs/engineering/API-M4-账号管理.md` |
| 关联 STATE | `docs/engineering/STATE-M4-账号管理.md` |

---

## 1. 概述

### 1.1 一句话描述

账号管理的"实体中心"：管理**公司 → 实名人/手机/手机卡 → 平台账号**的完整资产链。**所有平台账号必须通过选择器绑定到实名人/手机/手机卡/公司**，禁止手动输入。

### 1.2 目标与指标

| 维度 | 目标 | 可量化指标 |
|------|------|------------|
| 资产盘点 | 100% 账号关联到实名人 | 账号绑定率 = 100% |
| 追踪能力 | 1 个手机号追踪所有关联账号 | 跨平台账号聚合查询 ≤ 1s |
| 合规 | 实名信息加密存储 | AES-256 加密率 = 100% |

### 1.3 术语表

| 术语 | 定义 |
|------|------|
| **公司** | 工商主体，拥有公众号容量、实名人、账号 |
| **实名人** | 账号的"真主"（身份证/护照/港澳通行证） |
| **手机** | 设备（含 IMEI/品牌/型号） |
| **手机卡** | SIM 卡（含 ICCID/运营商） |
| **平台账号** | 公众号/视频号/抖音/快手/小红书等 |
| **个人微信/企微** | 私域运营账号 |
| **中介人** | 实名人关联的引荐/代理机构人员 |
| **三方关联** | 个微 ↔ 视频号 ↔ 企微的映射 |

---

## 2. 用户与权限

### 2.1 角色 × 能力

| 能力 \ 角色 | 系统管理员 | 运营管理者 | 运营组长 | 数据分析师 | 财务 |
|------------|-----------|-----------|---------|-----------|------|
| 管理公司 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 管理实名人 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 管理手机 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 管理手机卡 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 管理平台账号 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 查看实名人（脱敏） | ✅（完整） | ✅（脱敏） | ❌ | ✅（脱敏） | ❌ |
| 查看中介人 | ✅（完整） | ✅（完整） | ✅（本组） | ✅（脱敏佣金） | ✅（脱敏佣金） |
| 查看三方关联 | ✅ | ✅ | ❌ | ✅ | ❌ |
| 跨平台账号查询 | ✅ | ✅ | ✅（本组） | ✅ | ❌ |

### 2.2 权限规则

- **公司管理**：仅系统管理员、运营管理者
- **实名人管理**：系统管理员、运营管理者（其他角色脱敏查看）
- **手机/手机卡管理**：系统管理员、运营管理者
- **平台账号管理**：系统管理员、运营管理者
- **敏感数据脱敏**：身份证号、手机号、ICCID、Cookie 等

---

## 3. 范围

### 3.1 In Scope（7 个 FR 模块）

| FR 编号 | 名称 | 优先级 | 详细设计 |
|---------|------|--------|---------|
| FR-M4-001 | 公司管理（含公众号容量） | P0 | 5.16 |
| FR-M4-002 | 实名人管理（含中介人） | P0 | 5.17 |
| FR-M4-003 | 手机管理 | P0 | 5.18 |
| FR-M4-004 | 手机卡管理（跨平台账号聚合） | P0 | 5.19 |
| FR-M4-005 | 平台账号管理（核心模块） | P0 | 5.20 |
| FR-M4-006 | 个人账号管理（个微/企微） | P0 | 5.21 |
| FR-M4-007 | 三方关联统计（个微↔视频号↔企微） | P0 | 5.22 |

### 3.2 Out of Scope

1. ❌ **不实现** 微信支付/小程序/小游戏账号
2. ❌ **不实现** 海外平台（Twitter/Facebook）
3. ❌ **不实现** 账号活跃度分析（属于 `## 5.32 作品监测`）

---

## 4. 功能需求

### FR-M4-001 公司管理（5.16）

#### 4.1.1 描述

管理公司工商信息，含公众号容量管理（标准/已注册/剩余/扩容）。

#### 4.1.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `company_name` | `<Input />` | - |
| `credit_code` | `<Input />` | 18 位统一社会信用代码 |
| `industry` | `<DictSelect dict-type="dict_industry" />` | 字典（V35） |
| `address` | `<Input />` | - |
| `legal_name` | `<Input />` | - |
| `legal_id_card` | `<Input />`（加密） | - |
| `mp_capacity_standard` | `<InputNumber />` | - |
| `mp_registered_count` | 自动统计 | `oa_account` |
| `mp_remaining` | 派生 | - |
| `expansion_history` | JSON 数组 | - |
| `status` | `<DictSelect dict-type="dict_company_status" />` | 字典 |

#### 4.1.3 业务规则

- **BR-M4-001**（剩余可注册）= `mp_capacity_standard - mp_registered_count`
- **BR-M4-002** 已注册数自动统计关联该公司的公众号（`platformType IN (WECHAT_OFFICIAL, WECHAT_SERVICE)`）
- **BR-M4-003** 剩余 < 阈值（默认 5）→ 预警
- **BR-M4-004** 扩容记录到 `expansion_history`

#### 4.1.4 验收标准

**AC-M4-001-1**（公司 CRUD）
- Given 系统管理员
- When 创建公司
- Then 校验通过 + 返回 id

**AC-M4-001-2**（公众号容量自动统计）
- Given 公司 A 已注册 3 个公众号
- When 查询 A
- Then `mp_registered_count=3`

**AC-M4-001-3**（剩余可注册派生）
- Given 容量 10，已注册 3
- When 查询
- Then `mp_remaining=7`

**AC-M4-001-4**（扩容记录）
- Given 扩容 5
- When 调用 `/expand`
- Then `expansion_history` 新增 `{date, from, to, operator}`

---

### FR-M4-002 实名人管理（5.17）⭐

#### 4.2.1 描述

管理各平台账号的实名人信息（含中介人）。

#### 4.2.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `real_name` | `<Input />` | - |
| `id_type` | `<DictSelect dict-type="dict_id_type" />` | 字典 |
| `id_card` | `<Input />`（加密） | - |
| `phone` | `<Input />`（脱敏） | - |
| `wechat` | `<Input />` | - |
| `gender` | `<DictSelect dict-type="dict_gender" />` | 字典 |
| `status` | `<DictSelect dict-type="dict_realname_status" />` | 字典 |

#### 4.2.3 中介人

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `intermediary_name` | `<Input />` | - |
| `intermediary_phone` | `<Input />` | - |
| `intermediary_wechat` | `<Input />` | - |
| `relation_type` | `<DictSelect />`（DIRECT/INTERMEDIARY/AGENCY） | 字典 |
| `commission_rate` | `<InputNumber :precision="2" />` | - |
| `remark` | `<TextArea />` | - |

#### 4.2.4 业务规则

- 一个实名人可关联多个中介人（1:N）
- 实名人被账号引用时，不可删除（错误码 1502）
- `commission_rate` 对数据分析师/财务**脱敏**（`****`）

#### 4.2.5 验收标准

**AC-M4-002-0**（实名人列表分页与脱敏）
- Given 实名人 ≥ 11 条
- When GET `/admin-api/ops/realname/list?pageNo=2&pageSize=10`
- Then 返回第二页；每条仅含 `idCardMasked` / `phoneMasked`，无明文证件号/手机号

**AC-M4-002-1**（实名人 CRUD）
- Given 系统管理员
- When 创建实名人
- Then id_card 自动 AES-256 加密存储

**AC-M4-002-2**（关联多个中介人）
- Given 实名人 X
- When 添加 2 个中介人
- Then 1 对多关系

**AC-M4-002-3**（被引用时不可删除）
- Given 实名人 X 被账号 A 引用
- When 调用 DELETE
- Then 错误码 1502

**AC-M4-002-4**（敏感字段脱敏）
- Given 数据分析师查看
- When 列表
- Then `id_card` 显示 `330101********1234`

**AC-M4-002-5**（中介人佣金脱敏）
- Given 数据分析师
- When 查看中介人
- Then `commission_rate=****`

---

### FR-M4-003 手机管理（5.18）

#### 4.3.1 数据项

> **偏差说明**（ADR-011）：手机资产表**不维护** `realname_id`；实名人关联见平台账号 FR-M4-005。

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `phone_number` | `<Input />`（新增必填；编辑脱敏只读） | 11 位全局唯一 |
| `phone_code` | `<Input />` | - |
| `phone_model` | `<Input />` | - |
| `keeper_id` | `<UserSelect />` | `sys_user`（**强关联**） |
| `wechat_bound` | `<Input />` | - |
| `status` | `<DictSelect dict-type="dict_phone_status" />` | 字典 |
| `device_number` | `<Input />` | 设备编号 |
| `phone_type` | `<DictSelect dict-type="dict_phone_type" />` | Android / iPhone（V85） |
| `is_aochuang` | `<DictSelect dict-type="dict_yes_no" />` | 是否奥创手机（V85） |
| `handler_name` | `<Input />` | 经手人（文本） |
| `purchase_batch` | `<Input />` | 购买批次 |
| `purchase_date` | `<DatePicker />` | 购买日期 |
| `purchase_time` | `<TimePicker />` | 购买时间 |
| `settings_screenshot_key` | `<ImageUpload />` | 设置页截图（V85） |
| `front_image_key` | `<ImageUpload />` | 正面照 |
| `back_image_key` | `<ImageUpload />` | 背面照 |

#### 4.3.2 变更 2026-06-15（V85 · ADR-024）

- 列表支持按 `phone_type` 筛选；影像字段列表缩略图 + 详情预览
- 保管人仍为 `keeper_id` + `<UserSelect />`（与 ADR-011 一致）
- 图片经 `POST /oa/file/upload` 上传，存 key、返 url

#### 4.3.3 验收标准

**AC-M4-003-1**（手机 CRUD）
- Given 创建手机，填写手机号 + 选择保管人
- When 提交
- Then `phone_number` 全局唯一 + `keeper_id` 持久化

**AC-M4-003-3**（保管人选择器）
- Given 新增手机
- When 点击保管人
- Then 弹出 `<UserSelect />`，禁止手输 userId

**AC-M4-003-2**（关联账号时不可删）
- Given 手机 X 被账号 A 引用
- When DELETE
- Then 错误码 1502

---

### FR-M4-004 手机卡管理（5.19）⭐

#### 4.4.1 描述

管理 SIM 卡，支持**以手机号为主键跨平台账号聚合**（v9.1 新增）。

#### 4.4.2 数据项

| 字段 | 控件 | 字典/实体 |
|------|------|----------|
| `phone_id` | `<PhoneSelect />`（**强关联**，优先） | `oa_phone` |
| `phone_number` | 后端由 `phone_id` 解析；API 直传为兜底 | 11 位全局唯一 |
| `is_primary` | `<DictSelect dict-type="dict_yes_no" />` | 字典 |
| `operator` | `<DictSelect dict-type="dict_sim_operator" />` | 字典 |
| `assigned_user_id` | `<UserSelect />` | `sys_user`（**强关联**） |
| `iccid` | `<Input />`（加密） | - |
| `package_name` | `<Input />` | - |
| `status` | `<DictSelect dict-type="dict_sim_status" />` | 字典（含 **损坏 DAMAGED**、**丢失 LOST**，V85） |

**表单辅助**（仅 UI，不入库）：实名人 `<RealNameSelect />` 用于筛选 `<PhoneSelect />` 可选范围（按实名人过滤手机资产）。

#### 4.4.2.1 变更 2026-06-15（V85 · ADR-024）

- `dict_sim_status` 新增 `DAMAGED`、`LOST`；`phone_id` 强关联逻辑不变

#### 4.4.3 业务规则

- **跨平台账号聚合**：通过手机号查询所有关联账号（公众号/视频号/抖音/快手/小红书/企微/个微）
- **详情侧滑**：点击列表"关联账号数" → 侧滑展示完整跨平台账号

#### 4.4.4 验收标准

**AC-M4-004-1**（手机卡 CRUD）

**AC-M4-004-2**（跨平台账号聚合）
- Given 手机号 13800001111
- When 调用 `/linked-accounts`
- Then 返回 1 个公众号 + 1 个抖音号 + 1 个企微 + ...

**AC-M4-004-3**（按平台筛选）
- Given 跨平台列表
- When 筛选 `platformType=WECHAT_OFFICIAL`
- Then 仅显示公众号

**AC-M4-004-4**（按运营商筛选）
- Given 跨平台列表
- When 筛选 `operator=移动`
- Then 仅显示中国移动卡关联的账号

---

### FR-M4-005 平台账号管理（5.20）⭐⭐

#### 4.5.1 描述

统一管理各平台账号。**所有关联属性必须用选择器**。

**列表筛选（与 API 对齐）**：分页列表 query 为 `platformType`、`accountName`、`companyId`、`realnameId`、`status`（见 API-M4 §5.1）。**Spec 历史**「列表按 `ipGroupId` / `accountType` 服务端筛选」当前 **未实现**；IP 组/账号类型在表单 CRUD 中仍必填/可选（见下表）。

#### 4.5.2 数据项（🔴 重点）

| 字段 | 控件 | 字典/实体 | 强关联 |
|------|------|----------|--------|
| `platform_type` | `<DictSelect dict-type="dict_platform_type" />` | 字典 | ✅ |
| `account_name` | `<Input />` | - | - |
| `account_id` | `<Input />`（平台内 ID） | - | - |
| `account_type` | `<DictSelect dict-type="dict_account_type" />` | 字典 | ✅ |
| `ip_group_id` | `<IpGroupTreeSelect />` | `oa_ip_group` | ✅ |
| `company_id` | `<CompanySelect />` | `oa_company` | ✅ **强关联** ⭐ |
| `realname_id` | `<RealNameSelect />` | `oa_realname` | ✅ **强关联** ⭐ |
| `phone_id` | `<PhoneSelect />` | `oa_phone` | ✅ **强关联** ⭐ |
| `sim_card_id` | `<SimCardSelect />` | `oa_sim_card` | ✅ **强关联** ⭐ |
| `intermediary_id` | `<RealNameSelect />` | `oa_realname` | ✅ **强关联** ⭐ |
| `cookie` | `<Input />`（AES-256 加密） | - | - |
| `status` | `<DictSelect dict-type="dict_account_status" />` | 字典 | - |

#### 4.5.2.1 公众号扩展字段（`platform_type=WECHAT_OFFICIAL` · V86 · ADR-025）

| 字段 | 控件 | 说明 |
|------|------|------|
| `trademark_name` | `<Input />` | 商标名称 |
| `email` | `<Input />` | 邮箱 |
| `password_encrypted` | 密码框 | AES-256 |
| `qualification_type` | `<DictSelect dict-type="dict_qualification_type" />` | 企业 / 个人 |
| `usage_status` | `<DictSelect dict-type="dict_wechat_usage_status" />` | 注册 / 认证 / 续费 |
| `original_account_name` | `<Input />` | 原公众号名称 |
| `cert_expiry_time` | 日期时间 | 认证到期 |
| `cert_count` | 只读 | 认证次数 |
| `linked_video_account_id` | `<AccountSelect />` | 关联视频号 |
| `video_account_registered_at` | 日期时间 | 视频号注册时间 |
| `admin_name` / `admin_user_id` | 文本 + `<UserSelect />` | 管理员 |
| `admin_id_card_encrypted` | `<Input />` | 管理员身份证 AES-256 |

**条件表单**：`qualification_type=ENTERPRISE` → 必填 `company_id`；`PERSONAL` → 展示实名人相关项、隐藏企业主体。

**续费认证记录**（子表 `oa_wechat_official_cert_renewal`）：续费时间、续费人（UserSelect）、续费金额（默认 300）；详情页表格 CRUD。

#### 4.5.2b 抖音 / 快手扩展（ADR-078 · 已实现）

| 字段 | 控件 | 说明 |
|------|------|------|
| `holder_user_id` | `<UserSelect />` | **持有人**（Football 用户 · V205）；与 Excel「持有人」同语义 |
| `operator_user_id` | `<UserSelect />` | **运营人**（V206） |
| `realname_id` | `<RealNameSelect />` | 合规实名人档案；可与持有人姓名并行建链 |
| `short_video_status` / `live_status` | `<Input />` | Excel 原文，非字典枚举 |
| `password_encrypted` | 密码框 | 列表 `hasPassword`；表单留空表示不改 |
| `ip_group_id` | `<IpGroupTreeSelect />` | 0928 导入「分配小组」 |

**AC-M4-005-13**（抖音/快手字段持久化）  
Given `platformType=DOUYIN`  
When 保存 `holderUserId` + `operatorUserId` + 双状态 + 密码  
Then DB `oa_account` 对应列写入；详情回显 enrich 姓名；密码不明文返回。

#### 4.5.3 业务规则

- **同平台 account_id 唯一**
- **Cookie AES-256 加密存储**
- **快手账号**需额外配置 `authorization_token` 和 `data_fields_mapping`
- **实名人/手机/手机卡/公司选择器约束**（GLOBAL-CONVENTIONS § 3.2）：
  - 只能选 `status=启用` 的实体
  - 跨租户不可选
  - 已绑定到其他账号的实名人/手机/手机卡：默认不可选，需"强制替换"

#### 4.5.4 验收标准

**AC-M4-005-1**（账号 CRUD）

**AC-M4-005-2**（🔴 强关联实名人）
- Given 创建账号
- When 点击"实名人"输入框
- Then 弹出 `<RealNameSelect />` 选择器
- And 选择器禁用手动输入

**AC-M4-005-3**（🔴 强关联手机）
- Given 创建账号
- When 选择"手机"
- Then 弹出 `<PhoneSelect />` 选择器

**AC-M4-005-4**（🔴 强关联手机卡）
- Given 创建账号
- When 选择"手机卡"
- Then 弹出 `<SimCardSelect />` 选择器

**AC-M4-005-5**（🔴 强关联公司）
- Given 创建账号
- When 选择"公司"
- Then 弹出 `<CompanySelect />` 选择器

**AC-M4-005-6**（🔴 中介人选择器）
- Given 创建账号
- When 选择"中介人"
- Then 弹出 `<RealNameSelect />`（复用实名人表）

**AC-M4-005-7**（🔴 字典值校验）
- Given 创建账号
- When 传 `platformType=INVALID`
- Then 错误码 1503

**AC-M4-005-8**（🔴 跨租户校验）
- Given 租户 A 传 `realnameId`（租户 B 的）
- Then 错误码 1504

**AC-M4-005-9**（停用实名人校验）
- Given 实名人 X 已停用
- When 创建账号选 X
- Then 错误码 1501

**AC-M4-005-10**（强制替换）
- Given 实名人 X 已绑定账号 A
- When 账号 B 选 X（启用"强制替换"）
- Then 账号 A 自动解绑

**AC-M4-005-11**（Cookie 加密）
- Given 提交 `cookie="xxx"`
- Then 数据库存储为密文

**AC-M4-005-12**（同平台唯一）
- Given 同平台 account_id 已存在
- When 再创建
- Then 错误码 2006（同平台 account_id 重复）

#### 4.5.5 采集 Tab（ADR-047 · Channel-A）

> **SSOT**：[ADR-047](../adr/ADR-047-M4-平台账号凭证SSOT与Collector映射.md) — 平台类内部采集凭证统一维护于 M4，M8 INTERNAL 平台 Tab 已退役。

平台账号详情新增 **「采集」Tab**（`WECHAT_OFFICIAL` / `WECHAT_VIDEO` / `DOUYIN` / `KUAISHOU` / `XIAOHONGSHU` / `BILIBILI`）：

| 能力 | 说明 |
|------|------|
| 凭证编辑 | Cookie、mp_token（公众号）、auth_token + field_mapping（快手）；AppId/AppSecret 仅档案，**不参与 MVP 采集** |
| 绑定采集服务 | 调用 M10 collector-bind API，写入 `oa_collector_account_bind` |
| 测试连接 / 同步凭证 | 探活与 credential 同步至 unify-collector-api |
| 批量绑定 | 租户内凭证齐全且未绑定账号一键 batch-import |
| 建任务 | frequency / cron 仍在 M10 采集任务模块，不在此 Tab 重复 CRUD |

#### 4.5.6 采集数据展示（ADR-049 · 2026-06-24）

平台账号详情页（`PlatformAccountDetail`）对 Channel-A 五平台 **只读展示** M10 采集结果：

| 能力 | 数据源 |
|------|--------|
| 作品/内容列表与统计 | `CollectedDataQueryService` → 各平台 M10 表 |
| 内容趋势 | `contentTrendByDay` |
| 粉丝数 / 作品数 | 采集表 + `oa_account_status_log` |

不在本页展示：企微日聚合（M1 微信分析 Tab）、奥创个微明细。

---

### FR-M4-006 个人账号管理（5.21）

#### 4.6.1 描述

管理个微/企微的私域运营数据，个微通过奥创接口采集。

#### 4.6.2 数据项

**个微**：

| 字段 | 控件 |
|------|------|
| `account_name` | `<Input />` |
| `wechat_id` | `<Input />` |
| `contact_phone` | `<Input />`（明文，手动填写联系号） |
| `phone_id` | `<PhoneSelect />`（可选，保留列；表单不强制） |
| `api_url` | `<Input />`（脱敏） |
| `app_id` | `<Input />`（脱敏） |
| `app_secret` | `<Input />`（脱敏） |
| `token` | `<Input />`（脱敏） |

**企微应用配置**（`oa_wework_account`）：

| 字段 | 控件 |
|------|------|
| `account_name` | `<Input />` |
| `corp_id` | `<Input />` |
| `agent_id` | `<Input />` |
| `secret` | `<Input />`（脱敏） |

**企微员工账号**（`oa_wework_employee`，S-08b）：

| 字段 | 控件 |
|------|------|
| `wework_account_id` | 关联当前企微应用配置（后端校验） |
| `nickname` | `<Input />` |
| `wework_user_id` | `<Input />` |
| `phone` | `<Input />` |
| `department` | `<Input />` |
| `position` | `<Input />` |
| `status` | `<el-select />`（ENABLED/DISABLED） |

#### 4.6.3 业务规则

- 奥创接口信息**只读展示**（脱敏）
- 企微凭证 AES-256 加密

#### 4.6.4 验收标准

**AC-M4-006-1**（个微 CRUD + contact_phone 持久化）
**AC-M4-006-2**（奥创接口脱敏）
**AC-M4-006-3**（企微应用配置 CRUD）
**AC-M4-006-4**（企微员工账号 CRUD + 关联应用配置）

---

### FR-M4-007 三方关联统计（5.22）

#### 4.7.1 描述

维护 个微 ↔ 视频号 ↔ 企微 的三方关联映射。

#### 4.7.2 业务规则

- 一个个微可关联 N 个视频号 + 1 个企微
- 关联需手动建立（无自动匹配）

#### 4.7.3 验收标准

**AC-M4-007-1**（创建关联）
**AC-M4-007-2**（查询关联图谱）
**AC-M4-007-3**（解除关联）

---

## 4.9 OPS 页面清单与页级锚点（UX v1.4 · 2026-10-03）

> 路由 SSOT：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md) · 字段/弹窗 SSOT：**UX-M4** §3–§9。  
> HTTP：`/admin-api/ops/internal/**`（[`API-M4-账号管理.md`](../engineering/API-M4-账号管理.md) §0）。

| 页面 ID | 名称 | Football 路由 / 入口 | FR | PRD 锚点类型 |
|---------|------|----------------------|-----|--------------|
| P-M4-001 | 公司管理 | `/ops/internal/company` | FR-M4-001 | 可测 AC |
| P-M4-002 | 公司详情抽屉 | 列表 [详情] | FR-M4-001 | 可测 AC · 字段 **UX SSOT** §3.1 |
| P-M4-003 | 实名人 | `/ops/internal/realname` | FR-M4-002 | 可测 AC（§4.2 · AC-M4-002-0） |
| P-M4-004 | 实名人+中介人抽屉 | 列表 [详情] | FR-M4-002 | 可测 AC · 字段 **UX SSOT** §4.1 |
| P-M4-005 | 手机 | `/ops/internal/phone` | FR-M4-003 | 可测 AC（§4.3） |
| P-M4-006 | 手机卡 | `/ops/internal/simcard` | FR-M4-004 | 可测 AC（§4.4） |
| P-M4-007 | 跨平台账号侧滑 | 手机卡「关联账号数」 | FR-M4-004 | 可测 AC · **AC-M4-004-2** |
| P-M4-008 | 平台账号 | `/ops/internal/internal-account` | FR-M4-005 | 可测 AC（§4.5 · ADR-078） |
| P-M4-009 | 账号详情/替换抽屉 | Tab+行 [详情]/[替换] | FR-M4-005 | 可测 AC · 字段 **UX SSOT** §7 |
| P-M4-010 | 个人账号 | `/ops/internal/personal-account` | FR-M4-006 | **Spec-only stub**（ADR-060 · 无 Vue） |
| P-M4-011 | 三方关联 | `/ops/internal/triple-rel` | FR-M4-007 | **Spec-only stub**（ADR-060 · 无 Vue） |

**AC-M4-P001**（P-M4-001 公司列表）
- Given `oa:company:list`
- When 打开 `/ops/internal/company` 并 [新增公司]
- Then `GET /admin-api/ops/internal/company/page`；公众号容量字段校验与 **AC-M4-001-*** 一致（UX §3）

**AC-M4-P002**（P-M4-002 公司抽屉）
- When 点击行 [详情]
- Then 480px 抽屉展示主体信息与公众号容量子表；编辑提交 `PUT .../company/update`（控件字段见 UX §3.1，**不在此重复**）

**AC-M4-P004**（P-M4-004 实名人抽屉）
- When 打开实名人 [详情]
- Then 抽屉含中介人子表 CRUD；身份证/手机脱敏展示（**AC-M4-002-0** · UX §4.1）

**AC-M4-P009**（P-M4-009 平台账号抽屉）
- When 在抖音/快手 Tab 打开 [详情] 或 [替换实名人]
- Then 抽屉展示 ADR-078 双状态与 `holderUserId`/`operatorUserId`；替换走 confirm + 专用 API（UX §7 · §7.3b）

**AC-M4-P010**（P-M4-010 个人账号 · stub）
- Given Phase 1 Gate
- When 访问 `/ops/internal/personal-account`
- Then **不**作为 P0 现网验收；Spec 契约见 UX §8 · API-M4 §6 **`/ops/internal/personal-account/**`**；实现归属 Phase 2（ADR-060）

**AC-M4-P011**（P-M4-011 三方关联 · stub）
- Given Phase 1 Gate
- When 访问 `/ops/internal/triple-rel`
- Then **不**作为 P0 现网验收；Spec 契约见 UX §9 · API-M4 §7；实现归属 Phase 2（ADR-060）

---

## 5. 集成与数据

### 5.1 核心实体

| 实体 | 用途 | 关键关联 |
|------|------|---------|
| `oa_company` | 公司 | `oa_account`（1:N） |
| `oa_account_realname` | 实名人 | `oa_account`（1:N）、`oa_account_intermediary`（1:N） |
| `oa_account_phone` | 手机 | `oa_account`（1:N） |
| `oa_sim_card` | 手机卡 | `oa_account`（1:N，通过手机号匹配） |
| `oa_internal_account` | 平台账号 | `oa_company`、`oa_realname`、`oa_phone`、`oa_sim_card`、`oa_ip_group` |
| `oa_personal_wechat_account` | 个微 | `oa_account_phone` |
| `oa_wework_account` | 企微 | - |
| `oa_account_wechat_video_wework_rel` | 三方关联 | 上述 3 个 |

### 5.2 关联属性（🔴 关键）

| 字段 | 关联 | 选择器 | 详见 |
|------|------|--------|------|
| `oa_internal_account.realname_id` | `oa_account_realname.id` | `<RealNameSelect />` | GLOBAL-CONVENTIONS § 3.2(1) |
| `oa_internal_account.phone_id` | `oa_account_phone.id` | `<PhoneSelect />` | 同上 |
| `oa_internal_account.sim_card_id` | `oa_sim_card.id` | `<SimCardSelect />` | 同上 |
| `oa_internal_account.company_id` | `oa_company.id` | `<CompanySelect />` | 同上 |
| `oa_internal_account.intermediary_id` | `oa_account_realname.id` | `<RealNameSelect />` | 同上 |
| `oa_internal_account.ip_group_id` | `oa_ip_group.id` | `<IpGroupTreeSelect />` | 同上 |
| `oa_internal_account.platform_type` | `dict_platform_type` | `<DictSelect />` | GLOBAL-CONVENTIONS § 2.1 |
| `oa_internal_account.account_type` | `dict_account_type` | `<DictSelect />` | 同上 |
| `oa_internal_account.status` | `dict_account_status` | `<DictSelect />` | 同上 |

### 5.3 跨平台账号聚合

- 输入：手机号
- 输出：所有 `oa_internal_account` 中 `phone_id` 或 `sim_card_id` 关联的账号
- 性能：≤ 1s（索引 + 缓存）

---

## 6. 非功能需求

| 维度 | 要求 |
|------|------|
| 性能 | 跨平台账号聚合 ≤ 1s |
| 性能 | 列表分页（1000 条）≤ 500ms |
| 安全 | AES-256 加密（身份证/Cookie/ICCID/凭证） |
| 安全 | 敏感数据脱敏（中间 4 位 → `****`） |
| 审计 | 所有 CRUD 记录审计日志 |
| 数据 | 100% 账号关联到实名人 |

---

## 7. 决策记录

| 编号 | 问题 | 决策 | 原因 | 日期 |
|------|------|------|------|------|
| ADR-M4-001 | 实名人/手机/手机卡是直接字段还是关联表？ | 关联表（1:N） | 历史/变更/复用 | 2026-06-07 |
| ADR-M4-002 | 中介人单独表还是与实名人合并？ | 单独表 | 1 对多、敏感分级 | 2026-06-07 |
| ADR-M4-003 | 是否强制实名人绑定？ | 强制 | 合规要求 | 2026-06-07 |
| ADR-M4-004 | 已绑定实名人被其他账号选择时如何处理？ | 默认禁止 + "强制替换" | 数据一致性 | 2026-06-07 |
| ADR-010 | 个微联系号 `contact_phone` | 明文手动输入，与 `phone_id` 并存 | 运营联系号与设备资产解耦 | 2026-06-11 |
| ADR-011 | 手机表是否绑实名人？ | 否；保管人 UserSelect | 避免与平台账号重复关联 | 2026-06-11 |
| ADR-024 | 手机影像/采购/类型/奥创 | V85 扩展字段 + sim DAMAGED/LOST | 运营资产追溯 | 2026-06-15 |
| ADR-025 | 公众号认证续费 | V86 扩展字段 + 续费子表 | 合规与费用留痕 | 2026-06-15 |

---

## 8. 开放问题

| 编号 | 问题 | 负责人 | 截止 | 状态 |
|------|------|--------|------|------|
| OQ-M4-001 | 跨平台账号聚合是否要排除已注销账号？ | 产品 | 2026-06-15 | 待定 |
| OQ-M4-002 | 中介人"佣金比例"是否需要审核流程？ | 产品/财务 | 2026-06-20 | 待定 |

---

## CHANGELOG

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-15 | v1.2 | 公众号扩展、采集 Tab |
| 2026-10-03 | v1.5 | §4.9 P-M4-001~011 页级锚点（含 stub Spec-only · 抽屉 UX SSOT） |
| 2026-10-02 | v1.4 | 平台账号 list query 与 Controller 对齐；`ipGroupId` 列表筛选标为 Spec 历史 |
| 2026-10-02 | v1.3 | ADR-078 抖音/快手字段 FR+AC；实名人列表分页脱敏 AC；持有人/运营人 vs 实名人语义 |

---

*下一步：UX Spec / API Spec / STATE / SLICES / CHECKLIST / TESTCASES。*
