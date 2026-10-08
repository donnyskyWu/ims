# INT-内部分析 - API 契约（OPS M1/M7 透传 / IMS BFF）

> **前缀（目标）**：`/admin-api/ims/int-analysis`  
> **现网 OPS 路径（SSOT）**：`/admin-api/oa/internal-content/*`、`/admin-api/oa/account-analysis/*`、`/admin-api/oa/monitor/*`（见 `API-M1` §4、`API-M7`）  
> **响应包裹**：`{ code, msg, data }`；分页 `{ list, total, pageNo, pageSize }`（与 OPS 一致时保留 `page`/`pageNum` 兼容层 optional）  
> **阈值未配置**：沿用 **1251**（COLLECT 阈值缺失，只读引用）  
> **禁止发明字段**：下列 Response 仅列 OPS 已文档化或走查必显字段；扩展须先改 OPS API 文档。

---

## 1. 内部作品

### 1.1 GET `/admin-api/ims/int-analysis/work/page`

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| pageNo / pageSize | ✅ | 分页 |
| segment | ✅ | `ALL` \| `HIT` \| `LOW_SCORE` — Tab 全部 / 爆款 / 低分 |
| platformType | | `dict_platform_type` |
| ipGroupId | | IP 组 |
| contentType | | `dict_content_type` |
| startDate / endDate | | 可选；空=全量（对齐 M1 UI 默认） |
| keyword | | 标题关键词 |

**Segment 路由（BFF → OPS）**

| segment | OPS 下游 | 状态 |
|---------|----------|------|
| `ALL` | `GET /admin-api/oa/internal-content/list` | ✅ 现网（`API-M1` §4.4） |
| `HIT` | `GET /admin-api/oa/content-analysis/list` + `isHit=true` | ✅ 现网（`API-M1` §4.3 `/list` 参数） |
| `LOW_SCORE` | **IMS BFF**（非 M7 透传） | ✅ 设计 SSOT（2026-10-02）— **`GET /admin-api/ops/monitor/low-score/list` 仅外部盘**（`LowScoreAnalysis.vue` → `getLowScoreWorkList` · `mapExternalWork` · 数据权限同 `oa_external_work`，见 `OPS-DATA-PERMISSION-IMPLEMENTATION-PLAN` §6116）；**禁止**用于内部分析 Tab。内部低分：与 `ALL` 同源 **`GET /admin-api/ops/internal-content/list`**（`API-M1` §4.4 · 页面规格 §P1「Channel-A + 补录」）+ 服务端按 COLLECT **`LOW_SCORE` / BR-004** 阈值过滤（对齐 `segment=HIT` 透传 `content-analysis/list?isHit=true` 模式）；`segment=ALL` 列表额外返回 `isLowScore`（阈值只读，不持久化新列） |

**Response `data.list[]`（摘要，字段以 OPS VO 为准）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 内容 ID |
| title | string | 标题 |
| accountName | string | 账号展示名 |
| platformType | string | 平台 |
| publishTime | string | 发布/统计时间 |
| readCount / playCount | number | 播放类指标（平台差异） |
| isHit | boolean | 爆款（segment=ALL 时） |
| isLowScore | boolean | 低分（segment=ALL 时；BFF 按 COLLECT `LOW_SCORE` 阈值计算，同源 internal-content 列表字段） |

### 1.2 GET `/admin-api/ims/int-analysis/work/{id}/trend`

**下游**：`GET /admin-api/oa/internal-content/{id}/trend`（默认近 7 日，见 M1）

---

## 2. 内部账号

### 2.1 GET `/admin-api/ims/int-analysis/account/page`

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| pageNo / pageSize | ✅ | |
| segment | ✅ | `ALL` \| `HIGH_FANS` \| `LOW_FANS` |
| platform | | M1 账号分析 platform Tab 枚举 |
| ipGroupId / keyword / accountStatus / realnameId / operatorUserId | | 同 `API-M1` §4.1 `/list` |

**Segment 路由**

| segment | OPS 下游 | 状态 |
|---------|----------|------|
| `ALL` | `GET /admin-api/oa/account-analysis/list` | ✅ 现网 |
| `HIGH_FANS` | `GET /admin-api/oa/monitor/high-follower/list` | ✅ 现网（`API-M7` §1.4） |
| `LOW_FANS` | `GET /admin-api/oa/monitor/low-follower/list` | ✅ 现网（`API-M7` §1.5） |

**产品 TBD**：高/低粉监测 list 与 `account-analysis/list` 的 **账号集合关系**（去重/并集）未在 PRD 写死；BFF 默认 **不合并**，按 segment 直透 OPS。

**Response `data.list[]`（摘要）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 账号 ID |
| accountName | string | |
| platformType | string | |
| ipGroupName | string | |
| followerCount | number | |
| contentCount | number | |
| tagHighFans / tagLowFans | boolean | 展示用（**禁止**持久化新列；由阈值判定或 OPS 现网字段） |

---

## 3. 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/ims/int-analysis/work/export` | 对齐 M1 `POST …/internal-content/export` 或 content-analysis export |
| POST | `/admin-api/ims/int-analysis/account/export` | 对齐 M1 `POST …/account-analysis/export` |

**BLOCKED**：IMS 统一 export 路径未在 OPS 全量文档化；实现前 **禁止** 新增未文档化 export 字段。

---

## 4. 页面 ↔ API 映射

| 页面 | Tab | API |
|------|-----|-----|
| P1 内部作品 | 全部 | `GET …/work/page?segment=ALL` |
| P1 内部作品 | 爆款 | `… segment=HIT` |
| P1 内部作品 | 低分 | `… segment=LOW_SCORE`（BFF · internal-content + 阈值过滤） |
| P2 内部账号 | 全部 | `GET …/account/page?segment=ALL` |
| P2 内部账号 | 高粉 | `… segment=HIGH_FANS` |
| P2 内部账号 | 低粉 | `… segment=LOW_FANS` |
