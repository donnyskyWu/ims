# UX-M4-账号管理

> **版本**：v1.4 | 2026-10-02
> **关联 PRD**：[`PRD-M4-账号管理.md`](./PRD-M4-账号管理.md)
> **全局规范**：[`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md)

---


> **视觉规范参考**：[`开发规范/UI设计与开发规范.md`](../../开发规范/UI设计与开发规范.md)（仅原型/设计阶段）
> **实现技术栈**：[`TECH-CONSTRAINTS.md § 1.2`](../engineering/TECH-CONSTRAINTS.md)（Vue 3 + Element Plus）
> **决策记录**：[`ADR-002`](../../adr/ADR-002-前端规范源选择.md)


## 0. OPS 设计 SSOT

> **设计规范**：[UX-OPS-设计规范.md](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[UX-OPS-页面原型索引.md](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[OPS-MENU-ROUTE-INDEX.md](../delivery/OPS-MENU-ROUTE-INDEX.md)

## 1. 页面清单

| 页面 ID | 名称 | Football 路由（Hash `#` 后） | 组件 SSOT | 关联 FR |
|---------|------|------------------------------|-----------|---------|
| P-M4-001 | 公司管理列表 | `/ops/internal/company` | `ops/internal/CompanyManage` | FR-M4-001 |
| P-M4-002 | 公司详情 | 弹窗/跳转（列表「查看」） | `CompanyManage` | FR-M4-001 |
| P-M4-003 | 实名人管理列表 | `/ops/internal/realname` | `ops/internal/RealnameManage` | FR-M4-002 |
| P-M4-004 | 实名人详情（含中介人） | 列表弹窗/抽屉 | `RealnameManage` | FR-M4-002 |
| P-M4-005 | 手机管理 | `/ops/internal/phone` | `ops/internal/PhoneManage` | FR-M4-003 |
| P-M4-006 | 手机卡管理 | `/ops/internal/simcard` | `ops/internal/SimcardManage` | FR-M4-004 |
| P-M4-007 | 跨平台账号查询 | 手机卡侧滑 | `SimcardManage` | FR-M4-004 |
| P-M4-008 | 平台账号列表 | `/ops/internal/internal-account` | `ops/internal/InternalAccountManage` | FR-M4-005 |
| P-M4-009 | 平台账号详情/编辑 | Tab + 弹窗（同页） | `InternalAccountManage` | FR-M4-005 |
| P-M4-010 | 个人账号管理 | `/ops/internal/personal-account` | `ops/internal/PersonalAccountManage` | FR-M4-006 · **ADR-060 stub** |
| P-M4-011 | 三方关联图谱 | `/ops/internal/triple-rel`（隐藏菜单） | `TripleRelManage` | FR-M4-007 · **ADR-060 stub** |

> 菜单/路由全量索引：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)（2026-07-27）。

---

## 2. 通用约定

🔴 **所有关联属性必须用选择器**，禁用手动输入：

**导出（ADR-018，2026-06-13）**：内部管理 6 页（公司、实名人、手机、手机卡、平台账号、个人账号）均已接通 `exportToExcel` CSV 导出。

| 字段 | 控件 | 数据源 |
|------|------|--------|
| `realnameId` | `<RealNameSelect />` | 实名人表 |
| `phoneId` | `<PhoneSelect />` | 手机表 |
| `simCardId` | `<SimCardSelect />` | 手机卡表 |
| `companyId` | `<CompanySelect />` | 公司表 |
| `ipGroupId` | `<IpGroupTreeSelect />` | IP 组 |
| `intermediaryId` | `<RealNameSelect />` | 实名人表（复用） |

> ⚠️ 详情见 GLOBAL-CONVENTIONS § 3.2

---

## 3. P-M4-001 公司管理列表

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-NAME | `<Input />` | - |
| F-CREDIT-CODE | `<Input />` | - |
| TBL-COMPANY | 表格 | `oa_company` |
| COL-CAPACITY | 表格列 | 容量 / 已注册 / 剩余 |
| BTN-EXPAND | 链接 | "扩容" |
| BTN-MP-STATS | 链接 | "公众号统计" |

### 3.1 公司详情页

| 区域 | 内容 |
|------|------|
| 基本信息 | 公司名、信用代码、行业、地址、法人 |
| 公众号容量 | 容量/已注册/剩余/阈值预警 |
| 扩容记录 | 时间线（`expansion_history`） |
| 关联账号 | 表格（通过 `company_id` 关联的所有平台账号） |

### 3.2 新建/编辑公司弹窗（520px · P-M4-001/P-M4-002）

| 控件 | 类型 | 字典/实体 | 必填 |
|------|------|----------|------|
| F-NAME | `<Input />` | 公司名称 | ✅ |
| F-CREDIT-CODE | `<Input />` | 统一社会信用代码 | ✅ |
| F-INDUSTRY | `<Input />` | 行业 | ❌ |
| F-ADDRESS | `<TextArea />` | 地址 | ❌ |
| F-LEGAL-PERSON | `<Input />` | 法人 | ❌ |
| F-MP-CAPACITY | `<InputNumber />` | 公众号容量上限 | ✅ |
| BTN-SAVE | 主按钮 | create/update → `POST/PUT /admin-api/ops/company/*` | — |

**行操作**：编辑（同弹窗）· 查看（详情抽屉 §3.1）· 扩容（`MessageBox.prompt` 增量 + confirm）· 公众号统计（跳转或抽屉图表）

**确认流**：删除公司 → `MessageBox.confirm`「将解除关联账号绑定」· 扩容 → 二次确认阈值

**空/加载/错**：列表 `v-loading` · 无数据 `el-empty` + [新建公司] · 1501 信用代码重复

---

## 4. P-M4-003 实名人管理列表

| 控件 | 类型 | 字典/实体 | 脱敏 |
|------|------|----------|------|
| F-NAME | `<Input />` | - | - |
| F-ID-TYPE | `<DictSelect dict-type="dict_id_type" />` | 字典 | - |
| F-STATUS | `<DictSelect dict-type="dict_realname_status" />` | 字典 | - |
| COL-REAL-NAME | 表格列 | - | ✅ |
| COL-ID-CARD | 表格列 | `idCardMasked` | ✅ 服务端掩码 |
| COL-PHONE | 表格列 | `phoneMasked` | ✅ 服务端掩码 |
| TBL-REALNAME | 表格 + `<Pagination />` | `oa_realname` | `pageNo`/`pageSize` |
| BTN-ADD | 按钮 | "新增实名人" | - |

### 4.1 实名人详情（弹窗/抽屉）

| 区域 | 内容 |
|------|------|
| 基本信息 | 姓名、证件类型、证件号（脱敏）、手机（脱敏）、微信 |
| 关联账号 | 表格（通过 `realname_id` 关联的所有平台账号） |
| 中介人列表 | 表格（姓名、电话、关系类型、佣金比例） |
| 操作 | 按钮"新增中介人"、"编辑"、"删除" |

### 4.2 中介人弹窗

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-INTERMEDIARY-NAME | `<Input />` | - |
| F-INTERMEDIARY-PHONE | `<Input />` | - |
| F-INTERMEDIARY-WECHAT | `<Input />` | - |
| F-RELATION-TYPE | `<Select />` | 固定值（DIRECT/INTERMEDIARY/AGENCY） |
| F-COMMISSION-RATE | `<InputNumber :precision="2" />` | -（数据分析师/财务脱敏） |
| F-REMARK | `<TextArea />` | - |

---

## 5. P-M4-005 手机管理

> **ADR-011**：无实名人字段/列；保管人 `<UserSelect />`。

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-PHONE-NUMBER | `<Input />`（新增）；编辑只读脱敏 | - |
| F-CODE | `<Input />` | 手机编码 |
| F-MODEL | `<Input />` | - |
| F-KEEPER | `<UserSelect />` | `sys_user` |
| F-WECHAT | `<Input />` | 绑定微信 |
| F-STATUS | `<DictSelect dict-type="dict_phone_status" />` | 字典 |
| F-DEVICE-NO | `<Input />` | 设备编号（V85） |
| F-PHONE-TYPE | `<DictSelect dict-type="dict_phone_type" />` | Android / iPhone |
| F-AOCHUANG | `<DictSelect dict-type="dict_yes_no" />` | 奥创手机 |
| F-HANDLER | `<Input />` | 经手人 |
| F-PURCHASE | 批次/日期/时间 | 采购信息区 |
| F-IMAGES | `<ImageUpload />` ×3 | 设置截图、正/背面照 |
| SRCH-PHONE-TYPE | 筛选 | 列表按手机类型 |
| TBL-PHONE | 表格 | `oa_phone` |
| COL-PHONE-NUMBER | 表格列 | 脱敏显示 |
| COL-KEEPER | 表格列 | 保管人姓名 |
| COL-IMAGES | 表格列 | 缩略图预览 |

> **变更 2026-06-15**（ADR-024）：表单分「基础 / 采购 / 影像」；保管人仍为 `<UserSelect />`。

---

## 6. P-M4-006 手机卡管理（⭐ 跨平台聚合）

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-REALNAME-FILTER | `<RealNameSelect />` | 仅筛选 `PhoneSelect` 范围（不入库） |
| F-PHONE | `<PhoneSelect />` | `oa_phone`（**强关联**） |
| F-ICCID | `<Input />` | ICCID |
| F-OPERATOR | `<DictSelect dict-type="dict_sim_operator" />` | 字典 |
| F-IS-PRIMARY | `<DictSelect dict-type="dict_yes_no" />` | 字典 |
| F-PACKAGE | `<Input />` | 套餐名称 |
| F-ASSIGNED | `<UserSelect />` | 归属人 `sys_user` |
| F-STATUS | `<DictSelect dict-type="dict_sim_status" />` | 含 DAMAGED/LOST（V85） |
| TBL-SIM | 表格 | `oa_sim_card` |
| COL-LINKED-COUNT | 表格列 | 关联账号数（可点击） |
| BTN-VIEW-LINKED | 链接 | "跨平台查询" |

### 6.1 跨平台账号详情（侧滑）

点击"关联账号数" → 侧滑面板展示该手机号关联的所有平台账号：

```
+---------------------------------------------+
| 13800001111 关联账号（8 个）                |
+---------------------------------------------+
| 平台筛选：[全部▾]  运营商：[全部▾]         |
+---------------------------------------------+
| 平台        | 账号名   | 状态   | 关联时间 |
| 公众号      | （具体值详见相应章节）
| 视频号      | （具体值详见相应章节）
| 抖音        | （具体值详见相应章节）
| ...                                         |
+---------------------------------------------+
```

---

## 7. P-M4-008/009 平台账号列表/详情（⭐⭐ 核心）

### 7.1 列表

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-PLATFORM | `<DictSelect dict-type="dict_platform_type" />` | 字典 |
| F-ACCOUNT-NAME | `<Input />` | 账号名模糊（**API list query**） |
| F-REALNAME | `<RealNameSelect />` | `oa_account_realname`（**API list query**） |
| F-COMPANY | `<CompanySelect />` | `oa_company`（**API list query**） |
| F-STATUS | `<DictSelect dict-type="dict_account_status" />` | 字典（**API list query**） |
| F-ACCOUNT-TYPE | `<DictSelect dict-type="dict_account_type" />` | 字典 · **Spec 历史 / 当前未传 list API** |
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` · **Spec 历史 / 当前未传 list API**（Tab 内或客户端过滤） |
| TBL-ACCOUNT | 表格 | `oa_internal_account` |

### 7.2 详情（弹窗/抽屉）

| 区域 | 内容 |
|------|------|
| 基本信息 | 账号名、平台、IP 组、状态 |
| 🔴 强关联 | 实名人、手机、手机卡、公司、中介人（**全部选择器**） |
| 公众号扩展（WECHAT_OFFICIAL） | 商标、邮箱、密码、资质类型、使用状态、认证到期、视频号关联、管理员（UserSelect）、身份证（脱敏） |
| 条件表单 | 企业 → 公司必选；个人 → 隐藏企业、展示实名人区 |
| 续费认证 | 表格：续费时间/续费人/金额；「新增续费」弹窗（ADR-025） |
| **采集 Tab**（ADR-047 · ADR-050） | 绑定状态、凭证（Cookie/Token）、**扫码登录**、测试连接、批量绑定未绑定账号；见 [ADR-047](../../adr/ADR-047-M4-平台账号凭证SSOT与Collector映射.md) |
| **粉丝列表 Tab**（`WECHAT_OFFICIAL`） | 分页表格：头像、昵称、OpenID（截断）、关注时间、同步时间；数据来自 `oa_wechat_mp_follower`；空态引导至「采集」Tab 执行 `MP_FOLLOWER_LIST` |
| 凭证 | Cookie / authorization_token（脱敏） |
| 关联 | 关联的内容/粉丝/作品数据 |

### 7.3 编辑弹窗

🔴 **关键交互**：

| 控件 | 类型 | 强校验 |
|------|------|--------|
| F-PLATFORM | `<DictSelect />` | ✅ 联动账号类型 |
| F-ACCOUNT-TYPE | `<DictSelect />` | ✅ 联动实名人/手机选择器 |
| F-ACCOUNT-NAME | `<Input />` | - |
| F-ACCOUNT-ID | `<Input />` | ✅ 同平台唯一 |
| F-IP | `<IpGroupTreeSelect />` | ✅ |
| **F-REALNAME** | **`<RealNameSelect />`** | 🔴 禁用手动输入 |
| **F-PHONE** | **`<PhoneSelect />`** | 🔴 禁用手动输入 |
| **F-SIM-CARD** | **`<SimCardSelect />`** | 🔴 禁用手动输入 |
| **F-COMPANY** | **`<CompanySelect />`** | 🔴 禁用手动输入 |
| **F-INTERMEDIARY** | **`<RealNameSelect />`** | 🔴 禁用手动输入 |
| F-COOKIE | `<Input />`（密码框） | -（加密） |
| F-STATUS | `<DictSelect dict-type="dict_account_status" />` | - |

### 7.3b 抖音 / 快手 Tab（`InternalAccountManage` · ADR-078）

平台 Tab 为 **抖音** 或 **快手** 时，列表额外列：`shortVideoStatus`、`liveStatus`、`holderUserName`、`operatorUserName`；表单区：

| 控件 | 字段 | 说明 |
|------|------|------|
| `<RealNameSelect />` | `realnameId` | 合规实名人 |
| `<UserSelect />` | `holderUserId` | 持有人（≠实名人语义） |
| `<UserSelect />` | `operatorUserId` | 运营人 |
| `<Input type="password" show-password />` | `password` | 已设时 placeholder「已设置，留空不改」 |
| `<Input />` ×2 | `shortVideoStatus` / `liveStatus` | Excel 原文 |

### 7.4 强制替换弹窗

当选择的实名人已被其他账号绑定时弹出：

```
+---------------------------------------------+
| ⚠️ 该实名人已被以下账号绑定：              |
| - 账号 A（2025-01-15 创建）                |
| 强制替换后：                                |
| - 账号 A 将自动解除绑定                    |
| - 替换操作将记录到审计日志                  |
+---------------------------------------------+
| [取消]    [确认替换]                        |
+---------------------------------------------+
```

---

## 8. P-M4-010 个人账号管理（Phase 2 · **未实现**）

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/internal/personal-account`（**隐藏菜单**） |
| 组件 SSOT（目标） | `ops/internal/PersonalAccountManage.vue` |
| **现网** | `football-front` **无对应 Vue 文件**；菜单/路由可配置但打开为空或 404 — **ADR-060 Closed-Accept stub** |
| permission（目标） | `oa:personal-account:list`（以 seed 为准） |
| API SSOT | [`API-M4` §6](../engineering/API-M4-账号管理.md) · `/admin-api/ops/internal/personal-account/**` **契约 only** |

> **审计结论**：以下为目标 UX（Spec 驱动 Phase 2）；**不得**按已实现验收。Checklist 满分指 **文档完整 + stub 行为写清**。

### 8.1 布局（目标）

Tab：**个微** | **企微** · 布局 A/B/C 标准 OPS 页。

### 8.2 个微 Tab（目标）

**筛选 B**：名称 · 微信号 · 联系电话 · 状态

**表格 C**：`oa_personal_wechat_account` — 名称 · 微信号 · 手机 · 状态 · 更新时间

**行操作**：编辑弹窗 · 停用（confirm）

**弹窗字段**：F-NAME · F-WECHAT-ID · F-CONTACT-PHONE（ADR-010 明文存储策略）· F-STATUS

**详情只读区（奥创）**：api_url / app_id / app_secret / token — 全部 `****` 脱敏展示；配置写入 `POST .../api-config`

### 8.3 企微 Tab（目标）

**应用配置** `oa_wework_account`：名称 · corpId · agentId · secret（脱敏）

**员工子表** `oa_wework_employee`：昵称 · 企微 ID · 手机 · 部门 · 岗位 · 状态 · [新增员工] dialog CRUD

### 8.4 空 / 错 / 边缘

| 场景 | Spec |
|------|------|
| 未实现访问 | 路由占位页 `el-result`「个人账号管理 Phase 2 未上线」+ 返回内部管理首页 |
| 导出 | ADR-018 CSV（与其它内部 6 页一致，实现后接通） |

---

## 9. P-M4-011 三方关联图谱（Phase 2 · **未实现**）

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/internal/triple-rel`（**隐藏菜单**） |
| 组件 SSOT（目标） | `ops/internal/TripleRelManage.vue` |
| **现网** | **无 Vue 实现** · ADR-060 stub |
| API SSOT | [`API-M4` §7](../engineering/API-M4-账号管理.md) · `GET /ops/internal/triple-rel/list` 等 **契约 only** |

### 9.1 筛选 + 表格（目标）

| 控件 | 类型 |
|------|------|
| F-USER | `<UserSelect />`（Football 用户 SSOT · ADR-056） |
| TBL-REL | 表格列：用户 · 个微账号 · 视频号（可多个）· 企微主体 · 更新时间 |

**行操作**：查看图谱 · 解除关联（confirm）

### 9.2 图谱视图（目标 · 抽屉或独立区）

垂直链路示意：个微 → 视频号列表 → 企微（只读，数据来自 §7 API `personalWechat` / `channels` / `wework` 嵌套 VO）

### 9.3 未实现占位

同 §8.4：`el-result` + 说明 Phase 2；**禁止** mock 假数据冒充生产。

---

## 10. 跨页通用约定

- **强关联选择器**：禁用手动输入（前端 + 后端双重校验）
- **敏感数据脱敏**：身份证/手机/ICCID/Cookie 中间 4 位 → `****`
- **审计日志**：所有 CRUD 记录到 `sys_audit_log`
- **空/错/加载**：三态完整

---

## CHANGELOG

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-07 | v1.0 | 初稿（standalone 路由） |
| 2026-10-02 | v1.4 | §8–9 个人账号/三方 **未实现** stub 最小 Spec + 无 Vue 抽检结论 |
| 2026-10-02 | v1.3 | §3.2 公司新建/编辑弹窗 · 扩容/删除确认流 |
| 2026-10-02 | v1.2 | §7.1 列表筛选与 API list query 对齐；`ipGroupId`/`accountType` 标 Spec 历史 |
| 2026-10-02 | v1.1 | Football `/ops/internal/*` 路由与组件 SSOT；实名人分页掩码；抖音/快手 Tab 字段 |

---

*下一步：API Spec / STATE / SLICES / CHECKLIST / TESTCASES。*

**原型**：本期以本文 + [`开发规范/UI设计与开发规范.md`](../../开发规范/UI设计与开发规范.md) 为准；Penpot/Figma 无独立 OPS M4 库，变更请同步本 md。
