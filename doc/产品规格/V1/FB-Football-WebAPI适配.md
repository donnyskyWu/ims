# Football WebAPI 适配规格（IMS 侧）

> 完整 PRD IR-02。证据：现网 OPS 已调通的 Feign/HTTP（`football-module-ops`）+ ADR-054/056/057 + MUST-HAVE。  
> IMS **禁止 OpenFeign**，用 `FootballWebApiClient` 打 **同一路径**。

## 1. 原则

- 只 HTTP；内网可调 `/rpc-api/**` 或 Gateway `/admin-api/**`（与现网 OPS 对端一致即可）。
- 超时/重试/outbox 见《全局开发规范-完整版补充》。
- 写失败：IMS 业务已保存则记补偿，不回滚（BR-303）。

## 2. 现网对照（2026-09-29 源码盘点）

### 2.0 盘点表（仅本文 §2 行 · 2026-10-01）

| 能力 | 文档状态 | 现网路径（本文） | IMS 缺口摘要 |
|------|----------|------------------|--------------|
| 方案创建 | ✅ 已文档化 | `POST /rpc-api/member/article/create` | 须 authorId |
| 方案更新 | ✅ 已文档化 | `PUT /rpc-api/member/article/update` | — |
| 上架/下架 | ✅ 已文档化 | `POST /rpc-api/member/article/status-change` | 无物理 delete |
| 方案按 id 读 | ⚠️ 未提供 RPC | — | enrichment 可空 |
| 订单运营列表 | ✅ 已文档化 | `POST /rpc-api/pay/order/page-for-ops` | authorId=Football 作者 id |
| 用户列表 | ✅ 已文档化 | `GET /admin-api/system/user/simple-list` | SSO 绑 mobile |
| 用户主键 / SSO | ✅ 已文档化 | `system_users.id` | ADR-056 |
| 选赛 | ✅ 已文档化 | `GET /admin-api/match/jc-match/list-by-date` | 联赛 flat 另路径 |
| 作者只读 | ✅ 已文档化 | AuthorApi / Admin 只读 | 无 CUD 要求 |
| 直播时长聚合（作者×日期） | ✅ **IMS DB 只读（不等 HTTP）** | 表 **`live_room`** · SQL **照抄现网** `RoomMapper.xml#getLiveRoomCount` | **2026-10-05 v2.6.34**：口径**照抄**现网（详见 **§2.2**）；**不等** Football 新 REST、**不用** Feign；落点 M6/BI0，**非** LIVE Tab |
| 直播单场 **基本信息** | ✅ **IMS DB 只读** | 表 **`live_room`** · `LiveRoomDO` | **2026-10-01**：不等 HTTP；见 §2 用户决策 |
| 直播单场**计数**（观看数 `viewer_count` / 点赞 / 预约人数） | ✅ **IMS DB 只读** | 表 **`live_room`**（计数列） | **2026-10-05 v2.6.34**：随基本信息一并只读取回，**不等 HTTP** |
| 直播单场 GMV / 峰值在线 / 涨粉 / 退款 / 投放成本 | ❌ **缺失 HTTP/列** | `live_room` 无此列 | 由 **下播录入（LIVE-002）** 承载；LIVE Tab 不阻塞、**不再显示「—」** |
| 鉴权 Header | ✅ 已文档化 | tenant-id + Token | IMS Client 统一 |

> **范围**：上表 **不**包含仓库内未写入本文的路径；扩展须先改 §2 明细行再实现。

| 能力 | 现网路径 | 调用方证据 | IMS 用法 | 缺口 |
|------|----------|------------|----------|------|
| 方案创建 | `POST /rpc-api/member/article/create` | `ArticleApi#createArticle`；对齐 Admin `/admin-api/member/article/create` | 内容保存同步草稿 `status=-1` | 无。须 `authorId` |
| 方案更新 | `PUT /rpc-api/member/article/update` | `ArticleApi#updateArticle` | 标题/付费正文/免费正文（free 仅非 null 覆盖） | 无 |
| 上架/下架 | `POST /rpc-api/member/article/status-change` `{id,status}` `0`下架 `1`上架 | `ArticleApi#statusChange`；`FootballArticleBridgeServiceImpl#shelfOn/Off` | **删除草稿/下架走本接口 status=0**。现网 **无** 物理删除 RPC | 无 delete；IMS 不删 Football 行 |
| 方案按 id 读 | — | MUST-HAVE：ArticleApi 只写；C-WP7 已去掉 getById | 同步状态以 IMS ext.`author_article_id` + 上次结果为准 | 不阻塞保存；详情 enrichment 可空 |
| 订单运营列表 | `POST /rpc-api/pay/order/page-for-ops` | `PayOrderApi#pageForOps` ADR-057 | ROI/归因只读。入参时间窗 + 可选 **`authorId`** | **营收维度是 Football 作者 id，不是 oa 平台账号 id** |
| 用户列表 | `GET /admin-api/system/user/simple-list` | 前端 `football-user.ts` | 对上 `mobile`（SSO **必须绑手机**） | 不按 ding id 过滤 |
| 用户主键 | `system_users.id` + `dingtalk_user_id`、`mobile` | ADR-056 | SSO 对上此人；**登录不调用** Football social-login | IMS 自建钉钉换票 |
| 选赛 | `GET /admin-api/match/jc-match/list-by-date` | `MatchProxyService`（现网已 HTTP，非 Feign） | 工作任务/计划赛事 | 联赛 `GET /app-api/match/filter/competitions/flat` |
| 作者只读 | 现网 OPS 不写作者；只读 AuthorApi/Football Admin | D-AUTHOR-01 | 作者页补充 | 不要求 CUD |
| 直播时长聚合（作者×日期） | **`live_room`**（live-server DB） | `LiveRoomReadService.getLiveRoomCount` · `RoomMapper.xml#getLiveRoomCount` · DTO `LiveRoomCountRespDTO` | IMS **sqlc 只读**、**照抄**现网 SQL（§2.2）；**不新增** Football REST、**不用** Feign | **2026-10-05 拍板（照抄）**：过滤 `author_id=? AND create_time BETWEEN ? AND ?`（**无 `deleted`**）；`liveCount=count(1)`、`liveDuration=sum(TIMESTAMPDIFF(MINUTE,start_time,end_time))` |
| 直播房间 / 单场 **基本信息** | **`live_room`**（live-server DB） | `LiveRoomDO` · Admin `live/room` | IMS `football_room_id` → **`live_room.id`**；**`GET/POST /admin-api/ims/live/sessions/{sessionCode}/metrics|football-sync`** 内 **sqlc 只读**，不用 Feign | **用户决策 2026-10-01**（ADR-IMS-001 共用业务库读路径） |
| 直播房间 / 单场 **运营指标** HTTP | live-server RPC 宿主 | `LiveRoomApi` 仅 `getLiveRoomCount` 等聚合/状态 | 无按 room 返回 GMV/峰值的 REST | **仍 Out of Scope**；**观看/点赞/预约已走 `live_room` 只读**；GMV/峰值等走 下播录入 + `ims_live_data_snapshot` 手工/COLLECT |

### 2.1 Football / live-server 盘点（2026-10-01 · 仓库源码）

| 层级 | 存在 | 说明 |
|------|------|------|
| Feign 契约 | ✅ | `football-module-ops/.../LiveRoomApi.java` · `@FeignClient(name=RpcConstants.LIVE_NAME)` |
| 响应 DTO | ✅ | `LiveRoomCountRespDTO`：`liveCount`、`liveDuration`（Integer · 分钟） |
| OPS 封装 | ✅ | `LiveRoomReadService.getLiveRoomCount(authorId, start, end)` · RPC 失败 soft-fail 零值 |
| M6 消费 | ✅ | `ReportServiceImpl` 直播时长报表 · `API-M6` §2.4 · `oa_ip_group_anchor_rel` 作者范围 |
| IMS 表 | ✅（规格） | `ims_live_session`、`ims_live_data_snapshot`、`ims_live_report` — **IMS 新建**，非 Football 表 |
| Football 直播表 | ✅ | **`live_room`** · `football-module-live-server/.../LiveRoomDO.java` |
| HTTP 对外 | ❌ | 无 room 级 metrics REST 写入本文 SSOT |
| 单场 room 基本信息 **+ 计数**（`viewer_count`/点赞/预约） | ✅ **IMS JDBC** | 不新增 Football HTTP；LIVE API 契约 §2.1（v2.6.34） |
| 鉴权 | Header `tenant-id` + 应用/用户 Token | 现网 Feign | Client 统一带 | 密钥只放 IMS 配置 |

### 2.2 直播时长聚合（作者×日期）SQL 口径 —— **照抄现网**（2026-10-05 拍板）

> **结论**：IMS **照抄**现网 `RoomMapper.xml#getLiveRoomCount` 口径，**不等** Football 出 REST、**不走** Feign/RPC，走 IMS **sqlc 只读** `live_room`。

| 项 | 照抄口径（逐字，不得改写） |
|----|---------------------------|
| 表 | `live_room`（`football-module-live-server`） |
| WHERE | `author_id = ?` **AND** `create_time BETWEEN ? AND ?`（**本 SQL 无 `deleted` 条件**） |
| 场次 | `liveCount = count(1)` |
| 时长 | `liveDuration = sum(TIMESTAMPDIFF(MINUTE, start_time, end_time))`（单位**分钟**；`start_time`/`end_time` 为空则该行差值为 NULL，按现网行为） |
| 入参 | `authorId`（= Football 作者 id = `live_room.author_id` = `author_user.id`）；`dateTime[0]`/`dateTime[1]` 为闭区间 |
| DTO | `LiveRoomCountRespDTO{ liveCount, liveDuration }`（服务端同名出参） |
| 消费方 | **M6 直播时长报表**、**BI0 `live-duration`**（**非** LIVE 单场 Tab） |

**与另一条口径的消费关系（重要）**：现网 `live_room` 另有**小时口径** `RoomMapper.xml#selectLiveTrendStat`（`deleted = 0 AND status IN(2,3)`、按 `DATE` 分组、时长按**小时**）。二者**不可混用**：

1. **作者×日期 场次/时长** → 一律用本 §2.2（照抄 `getLiveRoomCount`，**无 `deleted`、无 `status` 过滤**）。
2. 该小时口径仅用于 OPS 内部趋势看板，**IMS 本期不消费**；若未来需要"趋势"视图，须另立 ADR 并写明与 §2.2 的数差来源。
3. **一致性判据**：同一 `(authorId, 日期区间)`，IMS 结果须与现网 `getLiveRoomCount` **逐值一致**（含"未开始/暂停"房间**计入**，因该 SQL 不筛 status）；**禁止**自行加 `deleted=0` / `status` 过滤去"修正"。

**最小写字段（创建方案）**：`authorId, title, content, status(-1), price, privilegeTypes, refundType, matchType, schedulePublishStatus`（现网默认 price=88、privilegeTypes=[2]、refundType=0、matchType=1、schedulePublishStatus=0）。

## 3. Client 方法（IMS 内部）

```typescript
interface FootballWebApiClient {
  createArticle(dto: ArticleSaveDTO): Promise<string>; // author_article.id
  updateArticle(dto: ArticleSaveDTO): Promise<void>;
  changeArticleStatus(articleId: string, status: 0 | 1): Promise<void>;
  pageOrdersForOps(req: { startTime: string; endTime: string; authorId?: string; status?: number; pageNo: number; pageSize: number }): Promise<{ list: OrderRow[]; total: number }>;
  listSystemUsers(keyword?: string): Promise<UserSimple[]>;
  listJcMatchesByDate(date: string): Promise<MatchBrief[]>;
  /** Out of Scope：单场 GMV/峰值 HTTP；基本信息**与计数（viewer_count/点赞/预约）**走 IMS 读 live_room，非 Client */
  // pullLiveRoomMetrics?(…): Promise<…>;
}
```

禁止 `@FeignClient`、禁止 `@DS("member"|"pay"|"match"|"system")`。

## 4. 明确不建

- 文章物理删除 API（用下架）。
- 订单 JDBC / 复制 `pay_all_order`。
- 用户表复制到 OPS 库。
