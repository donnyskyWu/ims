# CORP-公司资产 - 页面规格（IMS 导航重组 · OPS M4/M5 + IMS ASSET/CERT）

> **域**：一级侧栏 **公司资产** → 二级 **账号管理 / 资源管理 / 设备管理** → 三级叶子页（独立路由）  
> **交互 SSOT（并入 OPS 部分）**：`docs/product/UX-M4-账号管理.md`、`docs/product/PRD-M4-账号管理.md`、`ADR-IMS-003`  
> **IMS 增量 SSOT**：`MASTER-主数据-页面规格.md`、`ACCT-账号管理-页面规格.md`、`ASSET-资产管理-页面规格.md`、`CERT-证件档案-页面规格.md`  
> **虚拟资产扩展（字段/OCR/领用，非本走查导航）**：`docs/virtual-asset-hub/product/PRD-VA-MAINT-维护管理.md`  
> **API 契约**：同目录《CORP-公司资产-API契约.md》

---

## 0. 依据与禁止混淆

| 来源 | 引用要点 |
|------|----------|
| `docs/product/UX-M4-账号管理.md` | 公司/实名人/手机/手机卡/平台账号 **6 页** + 选择器铁律（1500/1501/1502） |
| `docs/product/UX-M4` P-M4-008 | 平台账号 **单列表** `/account/platform`；IMS 走查 #8 按 **平台拆 L3 路由**，列表 API 透传 + `platformType` 固定筛选 |
| `ADR-047` / `ACCT-平台账号采集Tab-OPS对齐.md` | Cookie/Collector bind **仅在平台账号详情 · 采集 Tab**；**禁止**与 16 竞品账号配置合并 |
| `一体化管理/COLLECT` | **竞品账号配置** = Channel-D 配置；**≠** 公司资产 · 账号管理 |
| `docs/virtual-asset-hub/BRD-虚拟资产中枢.md` | 公司/实名人/手机卡/账号档案命名与 VA-MAINT 对齐；VA 领用/预警 **不出** 本走查 L3 菜单 |

**IMS 相对 OPS 的信息架构差异（用户走查项 #8）**：OPS 账号域为「账号管理」下 **6 个并列菜单** + 平台账号 **1 页**；IMS 收成 **L1 公司资产** + **L2 三组** + **L3 按平台/实体拆分**。强关联字段、详情抽屉 Tab（含采集）以 **UX-M4 + ACCT 对齐文档** 为准，**不得**因拆路由而发明新 CRUD 字段。

**原「资源与账号」组（master/acct/asset/cert 四顶级）废止**：能力迁入本域；**08b 账号财务** 仍挂 **财务** 组，不并入公司资产。

---

## 0.1 侧栏信息架构

默认进入 **账号管理 → 抖音**（`caDouyin`）。

```
公司资产（L1 侧栏组）
├── 账号管理（L2 nav-sub-g）
│   ├── 公众号          /ims/corp/account/wechat-official
│   ├── 视频号          /ims/corp/account/wechat-channels
│   ├── 抖音            /ims/corp/account/douyin
│   ├── 快手            /ims/corp/account/kuaishou
│   └── 小红书          /ims/corp/account/xiaohongshu
├── 资源管理（L2 nav-sub-g）
│   ├── 公司管理        /ims/corp/resource/company
│   ├── 实名人管理      /ims/corp/resource/realname
│   ├── 手机卡管理      /ims/corp/resource/sim-card
│   └── 证件管理        /ims/corp/resource/certificate
└── 设备管理（L2 nav-sub-g）
    ├── 办公设备管理    /ims/corp/device/office
    ├── 直播设备管理    /ims/corp/device/live
    └── 手机设备管理    /ims/corp/device/phone
```

---

## L3 页面通用布局（骨架 / 原型）

每叶 **最低交互**（禁止 toast-only）：

```
[Alert：交互 SSOT 链至 UX-M4 / MASTER / ASSET / CERT · ADR-IMS-003]
[筛选条：实体相关字段 + 查询/重置/导出（OPS 已接通导出则透传）]
[表格 + 分页] 或 [空状态 + 引导文案]
[行操作：查看 → 抽屉 480~720px；平台账号含 Tab：基本信息 | 采集 | 领用时间线 | 关联资产]
[页脚 hint：下游 API 路径 + BLOCKED 标记]
```

---

## P-A1～P-A5 账号管理 · 按平台

| 页面 ID | 侧栏名称 | 路由 | platformType（dict） | OPS 对照 |
|---------|----------|------|----------------------|----------|
| P-A1 | 公众号 | `/ims/corp/account/wechat-official` | `WECHAT_OFFICIAL` | P-M4-008 列表 + 平台筛选 |
| P-A2 | 视频号 | `/ims/corp/account/wechat-channels` | `WECHAT_CHANNELS` | 同上 |
| P-A3 | 抖音 | `/ims/corp/account/douyin` | `DOUYIN` | 同上 + **采集 Tab**（ADR-047） |
| P-A4 | 快手 | `/ims/corp/account/kuaishou` | `KUAISHOU` | 同上 + 采集 Tab |
| P-A5 | 小红书 | `/ims/corp/account/xiaohongshu` | `XIAOHONGSHU` | 同上 |

### 列表列（摘要，与 UX-M4-008 一致）

账号编号、昵称、IP 组、实名人（脱敏）、公司、状态、采集绑定摘要、操作[详情][领用入口 **TBD**]

### 详情抽屉 Tab

| Tab | SSOT | 说明 |
|-----|------|------|
| 基本信息 | P-M4-009 | 选择器编辑；禁止手输关联 ID |
| 采集 | ADR-047、`ACCT-平台账号采集Tab-OPS对齐.md` | **≠** 数据采集 · 竞品账号配置 |
| 领用时间线 | ACCT-005 | 透传时间线 API |
| 关联资产 | ASSET-002 | 反向穿透入口 |

### 空状态

无该平台账号：提示先完成 **资源管理** 主数据建档 + 选择器创建平台账号。

---

## P-R1～P-R4 资源管理

| 页面 ID | 侧栏名称 | 路由 | OPS / IMS | 功能点 |
|---------|----------|------|-----------|--------|
| P-R1 | 公司管理 | `/ims/corp/resource/company` | UX-M4 P-M4-001/002 | MASTER-002；VA 扩展字段见 PRD-VA-M **可选分区** |
| P-R2 | 实名人管理 | `/ims/corp/resource/realname` | P-M4-003/004 | MASTER-001 |
| P-R3 | 手机卡管理 | `/ims/corp/resource/sim-card` | P-M4-006/007 | MASTER-004；卡级实名人 ADR-074 |
| P-R4 | 证件管理 | `/ims/corp/resource/certificate` | CERT P1 + VA P-VA-M-008 | CERT-001～003；**≠** 实名人详情内 Tab 替代本页 |

### P-R1 公司管理布局

筛选：名称、信用代码、状态 → 表格：名称、公众号容量（已用/总量）、状态 → [详情抽屉] 容量/扩容/关联账号。

### P-R2 实名人管理布局

筛选：姓名、证件类型、状态 → 表格：姓名（脱敏）、证件号（脱敏）、中介人、状态 → [详情抽屉] 中介人/关联账号摘要。

### P-R3 手机卡管理布局

筛选：号码、运营商、实名人、状态 → 表格：号码（脱敏）、实名人、绑定手机、月租、状态 → [详情抽屉] 跨平台关联账号（P-M4-007 侧滑语义）。

**新建/编辑**：`POST/PUT /ims/corp/resource/sim-card` 透传 OPS；写字段见《CORP-公司资产-API契约》§2.1（M4 §4.2 + `DATA-VA` §1.1 · ADR-074）。

### P-R4 证件管理布局

对齐 `CERT-证件档案-页面规格.md` P1：数字化率横幅、持有人/类型/有效期筛选、分级查看入口；**水印/文件代理未 SSOT 切片前列表可占位**。

---

## P-D1～P-D3 设备管理

| 页面 ID | 侧栏名称 | 路由 | SSOT | 说明 |
|---------|----------|------|------|------|
| P-D1 | 办公设备管理 | `/ims/corp/device/office` | ASSET-001 + **`dict_asset_type`** | 筛选 `assetType=OFFICE`（SYS-004 字典维护 · 2026-10-01 冻结） |
| P-D2 | 直播设备管理 | `/ims/corp/device/live` | ASSET-001 + **`dict_asset_type`** | 筛选 `assetType IN (LIVE, SHOOT)`（直播+拍摄合并 · 2026-10-01 冻结） |
| P-D3 | 手机设备管理 | `/ims/corp/device/phone` | UX-M4 P-M4-005 | MASTER-003 · `oa_phone`；**≠** 手机卡（P-R3） |

### P-D1/P-D2 列表

筛选：资产编号、名称、责任人、状态、`dict_asset_type` 标签 → 表格：编号、名称、类型（字典标签）、规格、状态、责任人 → [详情] 正向穿透 L1（ASSET-001）。**列表 API**：`GET /admin-api/ims/asset/ledger/page` + `assetType` 筛选（P-D2 = `LIVE`+`SHOOT` · 见 API 契约 §3）。**领用/归还**：平台账号详情与资产详情均保留 **领用入口**，跳转 `/ims/account/apply` 等（ACCT-001～004 · PRD Q3 2026-10-01 关闭：从账号或资产双向可达）。

### P-D3 手机设备管理布局

筛选：设备编号、型号、保管人、状态 → 表格：设备编号、型号、类型（Android/iPhone）、绑定实名人、状态 → [详情抽屉] 绑定账号列表（只读）。

---

## 权限与角色（摘要）

沿用 PRD §4.2 **MASTER/ACCT/ASSET/CERT** 矩阵；菜单权限码建议前缀 `ims:corp:*`（**BLOCKED** — 须 SYS-003 菜单 seed 与 OPS `ops:*` 映射表，见开放问题）。

---

## 原型

`一体化管理/UI原型/IMS-完整系统-UI原型.html` · `PAGES.ca*` / `cr*` / `cd*`：筛选 + 表格/空态 + 详情抽屉；**非** OPS 验收蓝本（ADR-IMS-003）。

---

## 开放问题（实现前须 ADR/产品确认）

见 PRD v2.6.3 §公司资产 · 走查 #8 开放问题表。
