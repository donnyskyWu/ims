# Football WebAPI 待盘点全路径对照表（IMS 引进版）

> **IMS 引进说明（2026-10-05）**：本文件**原出自 OPS 工作区**（`一体化管理/产品规格/V1/FB-Football-WebAPI-待盘点全路径对照表.md`），现**引进并落位于 IMS `产品规格/V1/`**，作为 Football 读路径盘点的**唯一对照入口**。
> - **SSOT 归属**：本表为**盘点台账**（记录"现网有什么、缺什么"）；**IMS 是否采用某路径**以 IMS 侧 《FB-Football-WebAPI适配.md》§2 + 各模块 API 契约 为准，二者冲突**以 IMS 侧为准**。
> - **与 IMS 铁律一致**：IR-02（Football 仅 HTTP WebAPI；唯一例外 = `live_room` 只读）、IR-03（验收后停 OPS）、§7A CI 硬门禁（禁 OPS HTTP）。本表所列 Feign/RPC 路径**仅供盘点取证**，**不得**在 IMS 代码中直接调用。
> - **落位索引**：序号 1（方案按 id 读）→ CONTENT 契约 §1/§2；序号 2/3（room 运营指标 HTTP）→ LIVE 契约 §2；序号 4（账号→authorId 映射）→ **MASTER 契约 §映射列 + IPG 契约 §关联作者（2026-10-05 定「加列」唯一化）**；「已关闭」表内**直播时长聚合** → LIVE 契约 §2.2 与 FB 适配 §2.2（2026-10-05 定「照抄」口径）。
> - **正文内相对路径**（如 `一体化管理/产品规格/V1/…`）为**原文 OPS 工作区路径**，在 IMS 侧对应 `产品规格/V1/…`。

> **生成依据**：`FB-Football-WebAPI适配.md` §2.0/§2.1/§2 明细（2026-10-01 盘点表）中仍为 **未提供 RPC / 缺失 HTTP / 缺失 HTTP·列 / Out of Scope 且无 REST** 的项；以及 IMS 规划文档中仍标注 **待盘点 / 未登记** 且与本表能力相关的数据流缺口。  
> **源码扫描范围**：`football-backend-saas/`、`football-front/apps/web-ele/src/api/`（2026-10-05）。  
> **说明**：已文档化且 SSOT 标记为 ✅ 的路径（方案写、订单 page-for-ops、用户 simple-list、选赛 jc-match、鉴权等）**不重复列入**主表。

---

## 主表（仍为待关闭项）

| 序号 | 业务能力 | 调用方/消费处 | 现文档状态 | 已发现的代码路径（Java 或 TS，没有则写未检出） | HTTP/Feign 方法与路径（没有则「无已文档化 HTTP」） | 备注 |
|------|----------|---------------|------------|--------------------------------------------------|-----------------------------------------------------|------|
| 1 | 方案按 id 读（详情 enrichment / Football 侧状态回显） | CONTENT-109/110 · `GET /admin-api/ims/content/{id}/fb-sync` 可选 enrichment；完整 PRD §11.3 摘要未列读路径 | ⚠️ **未提供 RPC**（IMS `FootballWebApiClient` 未收录；OPS 写契约刻意不含读） | **Java**：`football-backend-saas/football-module-member/football-module-member-api/src/main/java/football/module/member/api/article/ArticleApi.java`（`getArticleById`、`getArticleSimple`）；**Java（OPS  vendored 仅写）**：`football-backend-saas/football-module-ops/football-module-ops-server/src/main/java/football/module/ops/framework/common/biz/member/article/ArticleApi.java`（仅 create/update/status-change）；**TS**：未检出 OPS 侧 article-by-id 封装 | **Feign（member-server，未写入 IMS SSOT）**：`GET /rpc-api/member/article/getArticleById?id=`、`GET /rpc-api/member/article/getArticleSimple?id=`；**IMS Client**：无已文档化 HTTP | 适配表 §2.0：同步以 IMS `author_article_id` + 上次写结果为准；读失败不阻塞保存。member 实码存在读 RPC，是否纳入 IMS 须 ADR/改 SSOT 后补 Client |
| 2 | 直播单场运营指标（GMV / 峰值在线 / 观看等，按 room） | LIVE 详情 Tab「直播数据」运营指标列；`ims_live_data_snapshot` 手工/COLLECT；LIVE 契约 §2 | ❌ **缺失 HTTP/列**（`live_room` 无 GMV/峰值列；无 room 级 metrics REST） | **Java**：`football-backend-saas/football-module-live/football-module-live-server/src/main/java/football/module/live/dal/dataobject/live/LiveRoomDO.java`（表 `live_room`）；`LiveRoomApi.java` 仅聚合/状态类 RPC，**无**按 room 返回 GMV/峰值；**TS**：未检出 room metrics REST 客户端 | **Feign/RPC**：无按 `roomId` 返回 GMV/峰值的已文档化路径；**REST**：无已文档化 HTTP | 适配 §2.0/§2.1：**Out of Scope 本期**；UI「—」；下播录入承载。可选交叉核对仅 author 维度：`POST /rpc-api/pay/order/page-for-ops`（非 room 级） |
| 3 | 直播房间单场 **运营指标 HTTP**（与上项同边界，适配 §2 明细行） | 同上；原型 1050 提示（Football 单场 metrics HTTP 未发布） | ❌ **缺失 HTTP**（仍 Out of Scope） | 同序号 2 | 同序号 2 | 与序号 2 为同一能力在适配 §2 明细表的重复表述；关闭须 Football 新 REST 或改产品范围 |
| 4 | 平台账号 → Football `authorId`（订单 WebAPI / ROI 过滤键） | COST-002 账号 ROI · `POST /rpc-api/pay/order/page-for-ops` 的 `authorId`；`IMS-PRD与原型完整性核验-20261001.md` **D4**；开发就绪核验 §2.2 `accountExtId` | **未登记**（非 HTTP 路径缺口，参数映射 SSOT 缺失） | **Java**：`football-backend-saas/football-module-ops/football-module-ops-server/src/main/java/football/module/ops/controller/football/FootballOrderReadController.java`（Query `authorId`）；`.../api/dto/football/FootballOrderListVO.java`；**TS**：`football-front/apps/web-ele/src/api/ops/football-order.ts`；IMS 平台账号表 → `authorId` 列/规则：**未检出** | 订单列表 HTTP 已文档化：`GET /admin-api/ops/football-order/list`（经 Gateway 亦可 `GET /admin-api/ops/football-order/list`）；底层 Feign：`POST /rpc-api/pay/order/page-for-ops`。**映射规则本身**：无已文档化 HTTP | 适配 §2 强调 **authorId = Football 作者 id，非 oa 平台账号 id**；IMS 须在 MASTER/CORP 规格登记账号→作者映射列，否则 COST/CONTENT 写路径无法自动带参 |

---

## 已关闭（不再列入主表「待盘点」）

| 能力 | 关闭方式 | SSOT |
|------|----------|------|
| 直播单场 **基本信息**（room 元数据） | **IMS 共用业务库只读** `live_room`，不经 Feign/HTTP | `FB-Football-WebAPI适配.md` §2.0（2026-10-01 用户决策）；`LIVE-直播管理-API契约.md` §2；实体 `LiveRoomDO.java` |
| 直播时长聚合（作者 × 日期：场次 + 时长分钟） | **IMS 共用业务库只读** `live_room`，按 `RoomMapper.xml#getLiveRoomCount` 等价聚合；**不等** Football 新 REST、**不用** IMS Feign | `FB-Football-WebAPI适配.md` §2.0（2026-10-05）；M6/BI0 `live-duration`；现网 Feign 宿主 SQL：`football-module-live-server/src/main/resources/mapper/live/RoomMapper.xml` · DTO `LiveRoomCountRespDTO`（`liveCount` 场次 · `liveDuration` 分钟）。**过滤**：`author_id = ?` 且 `create_time BETWEEN dateTime[0] AND dateTime[1]`（**本 SQL 无 `deleted` 条件**）。**指标**：`liveCount = count(1)`；`liveDuration = sum(TIMESTAMPDIFF(MINUTE, start_time, end_time))` |
| 方案创建/更新/下架、订单 page-for-ops、用户 simple-list、选赛 jc-match、鉴权 Header | ✅ 已文档化 | `FB-Football-WebAPI适配.md` §2.0 |
| Football 订单列表（无 `{id}` 详情） | 2026-10-02 盘点结论：列表行即 SSOT，**无**详情 HTTP | `COST-账号财务-API契约.md` §2 F2 · 页面规格 P2 |

---

## 引用文件（本次已打开核对）

- `一体化管理/产品规格/V1/FB-Football-WebAPI适配.md`
- `一体化管理/产品规格/V1/LIVE-直播管理-API契约.md`
- `一体化管理/产品规格/V1/COST-账号财务-API契约.md` · `COST-账号财务-页面规格.md`
- `一体化管理/产品规划/IMS-PRD与原型完整性核验-20261001.md`
- `一体化管理/审查报告/IMS完整版开发就绪核验-2026-09-29.md`
- `football-backend-saas/football-module-member/football-module-member-api/.../ArticleApi.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../ArticleApi.java`
- `football-backend-saas/football-module-live/football-module-live-api/.../LiveRoomApi.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../live/room/LiveRoomApi.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../LiveRoomReadService.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../ReportController.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../PayOrderApi.java`
- `football-backend-saas/football-module-pay/football-module-pay-api/.../PayOrderApi.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../FootballOrderReadController.java`
- `football-backend-saas/football-module-live/football-module-live-server/.../LiveRoomDO.java`
- `football-backend-saas/football-module-live/football-module-live-server/src/main/resources/mapper/live/RoomMapper.xml`（`getLiveRoomCount`）
- `football-backend-saas/football-module-live/football-module-live-api/.../dto/LiveRoomCountRespDTO.java`
- `football-backend-saas/football-module-ops/football-module-ops-server/.../RpcConstants.java`
- `football-front/apps/web-ele/src/api/ops/football-order.ts`
- `football-front/apps/web-ele/src/api/ops/report.ts`
- `football-front/apps/web-ele/src/api/ops/football-user.ts`
