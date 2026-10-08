# MASTER - 主数据 API 契约（OPS 并入）

> `/admin-api/ims/master` ｜ 选择器接口供全系统复用

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET/POST/PUT | `/master/company/page` `/company` | 公司 |
| 2 | GET/POST/PUT | `/master/person/page` `/person` | 实名人 |
| 3 | GET/POST/PUT | `/master/phone/page` `/phone` | 手机 |
| 4 | GET/POST/PUT | `/master/sim/page` `/sim` | 手机卡 |
| 5 | GET/POST/PUT | `/master/platform-account/page` `/platform-account` | 平台账号 |
| 6 | GET/POST/PUT | `/master/personal-account/page` `/personal-account` | 个人账号 |
| 7 | GET | `/master/selector/company` | 下拉 |
| 8 | GET | `/master/selector/person` | 下拉 |
| 9 | GET | `/master/selector/ip-group` | 下拉 |

写账号须校验绑定实体同租户（1504）。错误码 1221 选择器空；1222 公众号容量超限。

---

## 账号 → 作者（`authorId`）映射列（2026-10-05 拍板：「加列」唯一化）

> **要解决的问题**：COST-002 账号 ROI / CONTENT `createArticle` 等写路径**必须**带 **Football 作者 id**（`authorId`，**非** `oa` 平台账号 id，见《FB-Football-WebAPI适配》§2）。而账号经 IP 组可达**多个**作者（`oa_ip_group_anchor_rel` 为 **1:N** 关系表），**不唯一** → 必须先**唯一化**。
> **用户裁定（2026-10-05）**：**加列**解决——① 账号表关联 IP 组；② 经 IP 组关联作者，并把「作者」固化为**列**。**禁止**新造 `authors/{id}/accounts` 反查接口（REPORT 契约已明令禁止；级联统一走 `GET /admin-api/ims/ip-group/{id}/accounts` 范式）。

### 加列方案（IR-04：现网表**只加列**，不改语义、不删列）

| # | 表 | 新增列 | 语义 | 约束 |
|---|----|--------|------|------|
| **C1** | `oa_ip_group_anchor_rel`（IP 组↔作者关系表） | `is_primary TINYINT(1) NOT NULL DEFAULT 0` | **主作者标记**：该 IP 组的唯一"对外代表作者" | **每租户每 IP 组至多 1 条 `is_primary=1`**——MySQL 8 以生成列 `primary_uk = IF(is_primary=1, ip_group_id, NULL)` + `UNIQUE(tenant_id, primary_uk)` 实现 |
| **C2** | `oa_platform_account`（平台账号主表） | `author_user_id BIGINT NULL` | **账号 → 作者 的物化引用**（= `author_user.id`，ADR-051） | 可空；写账号时按下方「解析优先级」回填，亦允许人工指定 |

> **SSOT**：唯一化真值以 **C1（组内主作者）** 为准；**C2** 为账号级物化缓存，用于 COST/CONTENT 免二次解析。二者冲突时以 **C2 显式值**优先（人工干预最高优先级）。

### 解析优先级（`resolveAuthorId(account)`，服务端统一实现）

```
1. account.author_user_id 非空            → 直接采用（人工/已物化）
2. account.ip_group_id → oa_ip_group_anchor_rel 中 is_primary=1 的作者  → 采用
3. 组内作者数 = 1（无主作者）              → 采用该唯一作者
4. 组内作者数 = 0                          → 报错 1223（未配置映射）
5. 组内作者数 ≥ 2 且无 is_primary=1        → 报错 1223（映射不唯一，须人工指定主作者）
```

**铁律**：**禁止**"猜"作者（如取第一条/最小 id）——映射不唯一必须**显式报错**并引导主数据维护（IP 组详情 Tab 设主作者），避免 ROI/内容写错 authorId。

### 落点与错误码

| 项 | 约定 |
|----|------|
| 主数据维护入口 | IPG 契约 **§关联作者**——`POST /admin-api/ims/ip-group/{id}/anchors` 增 `isPrimary` 参数；组内至多 1 主作者（重复设为主 → 旧主自动降级，留痕） |
| 消费方 | COST-002 账号 ROI（`authorId` 过滤键）、CONTENT `createArticle`（`authorId` 必填）、MASTER 账号写接口 |
| 校验 | 写账号（`POST/PUT /master/platform-account`）时若无 `author_user_id` 且 IP 组内作者 **≥2 且无主作者** → 返回 **1223**（**不**静默置空） |
| **错误码 1223** | **账号→作者映射未配置 / 不唯一**（MASTER 段 1221~1223） |

> **与对照表对应**：《FB-Football-WebAPI-待盘点全路径对照表》主表**序号 4**（账号→`authorId` 映射）——本节的「加列」即该缺口的产品侧关闭方案；**不引入** Football 新 HTTP。
