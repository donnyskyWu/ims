# COMP-竞品分析 - API 契约（OPS M7 透传 / IMS BFF）

> **前缀（目标）**：`/admin-api/ims/comp-analysis`  
> **现网 OPS 路径（SSOT）**：`/admin-api/oa/monitor/*`（`docs/engineering/API-M7-作品监测.md`）  
> **响应包裹**：`{ code, msg, data }`；分页 `{ list, total, pageNo, pageSize }`（与 OPS 一致时保留 `pageNum` 兼容层 optional）  
> **阈值未配置**：沿用 **1251**（COLLECT 阈值缺失，MON/COMP 只读引用）  
> **错误码段 1171~1180**：保留给 **V3 竞品管理提交/审核**（`COMP-竞品管理-API契约.md`）；本模块 **只读列表不使用 1171~1180**。

---

## 1. 竞品作品

### 1.1 GET `/admin-api/ims/comp-analysis/work/page`

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| pageNo / pageSize | ✅ | 分页 |
| segment | ✅ | `ALL` \| `HIT` \| `LOW_SCORE` — 对应页内 Tab 全部 / 爆款 / 低分 |
| platformType | | `dict_platform_type` |
| ipGroupId | | IP 组 |
| industry | | 行业固定值 |
| startDate / endDate | | 发布或统计日期 |
| accountIdentifier | | 外部账号标识 |

**Segment 路由（BFF → OPS）**

| segment | OPS 下游 | 状态 |
|---------|----------|------|
| `HIT` | `GET /admin-api/oa/monitor/hit/list` | ✅ 现网 |
| `LOW_SCORE` | `GET /admin-api/oa/monitor/low-score/list` | ✅ 现网 |
| `ALL` | **IMS 设计 SSOT**（2026-10-01） | OPS **无**「全部竞品作品」独立 HTTP（UX-M7 仅 `/monitor/hit` 与 `/monitor/low-score` 分列菜单）。IMS BFF **直连共享 OPS 库** `oa_external_work`：与 `MonitorServiceImpl.hitList` 相同 `buildBaseWrapper`（租户 + IP 组数据权限，见 `OPS-DATA-PERMISSION-IMPLEMENTATION-PLAN` §6113），**不**套用 BR-003/BR-004 阈值过滤；排序默认 `publish_time DESC`。字段 VO 对齐 `ExternalWorkVO`（与 hit/low 列表一致） |

**Response `data.list[]`（字段以 OPS `ExternalWorkVO` 为准，仅列走查必显）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | `oa_external_work.id` |
| title | string | 作品标题 |
| accountName | string | 竞品账号展示名 |
| platformType | string | 平台 |
| publishTime | string | ISO / 毫秒时间戳（前端 normalize） |
| playCount | number | 播放 |
| likeCount | number | 点赞 |
| isHit | boolean | 爆款标记（segment=ALL 时） |
| isLowScore | boolean | 低分标记（segment=ALL 时） |

---

## 2. 竞品账号

### 2.1 GET `/admin-api/ims/comp-analysis/account/page`

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| pageNo / pageSize | ✅ | |
| segment | ✅ | `ALL` \| `HIGH_FANS` \| `LOW_FANS` |
| platformType / ipGroupId / industry / startDate / endDate | | 同 UX-M7 §2 |

**Segment 路由**

| segment | OPS 下游 |
|---------|----------|
| `ALL` | `GET /admin-api/oa/monitor/external/list` |
| `HIGH_FANS` | `GET /admin-api/oa/monitor/high-follower/list` |
| `LOW_FANS` | `GET /admin-api/oa/monitor/low-follower/list` |

**Response `data.list[]`（摘要）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | `oa_external_account.id` |
| accountName | string | 展示名 |
| platformType | string | |
| followerCount | number | |
| workCount | number | |
| lastSyncedAt | string | 最近采集同步 |

---

## 3. 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/ims/comp-analysis/work/export` | query 同 1.1；遵循 ADR-018 CSV 模式 |
| GET | `/admin-api/ims/comp-analysis/account/export` | query 同 2.1 |

**BLOCKED**：OPS 是否已有对等 export HTTP — 未在 API-M7 文档化；IMS 实现前 **禁止** 新增未文档化 export 字段。

### 1.2 OPS runtime 端点（MonitorController · 2026-10-02）

| segment / 场景 | 方法 | 现网 OPS 路径 | 前端封装 |
|----------------|------|---------------|----------|
| 爆款作品 | GET | `/admin-api/ops/monitor/hit/list` | `monitor.ts` → `getHitWorkList` |
| 低分作品 | GET | `/admin-api/ops/monitor/low-score/list` | `getLowScoreWorkList` |
| 外部账号（全部） | GET | `/admin-api/ops/monitor/external/list` | `getExternalWorkList` |
| 高粉账号 | GET | `/admin-api/ops/monitor/high-follower/list` | `getHighFollowerAccountList` |
| 低粉账号 | GET | `/admin-api/ops/monitor/low-follower/list` | `getLowFollowerAccountList` |

Vue：`content/HotWorksAnalysis.vue` · `LowScoreAnalysis.vue` · `account/HighFansAccountAnalysis.vue` · `LowFansAccountAnalysis.vue` · `ExternalAccountAnalysis.vue`。

---

## 4. 页面 ↔ API 映射

| 页面 | Tab | API |
|------|-----|-----|
| P1 竞品作品 | 全部 | `GET …/work/page?segment=ALL`（IMS BFF · `oa_external_work`） |
| P1 竞品作品 | 爆款 | `… segment=HIT` |
| P1 竞品作品 | 低分 | `… segment=LOW_SCORE` |
| P2 竞品账号 | 全部 | `GET …/account/page?segment=ALL` |
| P2 竞品账号 | 高粉 | `… segment=HIGH_FANS` |
| P2 竞品账号 | 低粉 | `… segment=LOW_FANS` |

---

## 5. V3 竞品库（导航并入 · API 不合并）

| 页面 | 说明 | SSOT |
|------|------|------|
| P3 竞品库 | IMS 路由 `/ims/comp-analysis/library` | `V3/COMP-竞品管理-API契约.md` · 前缀 `/admin-api/comp/asset/*` 等 **16 接口** |
| COMP-001/002 | 月度提交、审核队列 | 同上契约 · `/comp/analysis/*`、`/comp/audit/*` · **无**本 BFF 前缀 |

**BLOCKED（#9 范围外）**：是否提供 IMS 统一网关将 `/ims/comp-analysis/library/*` rewrite 至 `/comp/asset/*` — 待 ADR-IMS-001 切流清单确认；**禁止**为导航合并新增合并 REST 资源。
