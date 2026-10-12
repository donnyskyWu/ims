# IMS Python 完整开发计划

> **日期**：2026-10-05  
> **状态**：执行中。W0、W1 为本轮开工范围，其后各片按本表顺序，一片验收后再开下一片。  
> **事实源**：ADR-IMS-009、完整 PRD v2.6.35、全局开发规范、各模块页面规格与 API 契约、`doc/delivery` 的 SLICES / CHECKLIST / TESTCASES、原型 `doc/UI原型/IMS-完整系统-UI原型.html`。  
> **冲突**：ADR-IMS-009 > 本计划 > 完整 PRD > 规范 > 契约 > 页面规格 > 原型。原型决定导航与分区。契约没写的接口不做。

## 1. 已定口径

- 后端 Python 3.11、FastAPI、SQLAlchemy 2、Alembic。进程：`api` 与 `worker`。
- 前端 Vue 3、Vite、Element Plus、Pinia。同一套路由适配 PC（≥1024）与手机（390）。
- MySQL `127.0.0.1:3306`，账号 `root` / `root`。库：`ims`（自建表）、`opsbiz`（`oa_*`，只加列）。
- 用户表 `ims.ims_sys_user`。本地密码登录 + 钉钉 SSO 按手机号命中本地用户。上线用导入命令灌入 Football/OPS 用户并保留主键。
- 每片出口：CHECKLIST 全勾、该片 TESTCASES 的 P0 全过、Playwright 在 1440×900 与 390×844 走通主路径。失败只修该片再回归。
- 列表一律分页。空权限 / 待配置 / 未登记表 / 非法数据范围 → 1008。跨租户与不存在 → 1504「资源不可用」。

## 2. 不做

AIR 语义检索、Key、审计；SYS-008 租户套餐；独立数据权限菜单；跨租户切换；运行时读写 Football 用户；办公/直播设备类型的假增删改；培训 AI 真实出卷；OPS HTTP；对象存储；直连 Football 库。

## 3. 每片执行步骤

1. 打开该片 SLICES、PRD 对应节、页面规格、API 契约、原型页面 id。
2. 表不在登记册或契约中的，先补登记册再写代码。
3. 只改该片迁移、接口、页面。
4. `pytest`、该片 CHECKLIST、P0 用例。
5. Playwright 两个视口。失败则修复片，重跑该片和已完成主线里被碰到的场景。

## 4. 切片总表

**口径**：**W0–W9 主线约 41 项**（下表波次/切片行，含 B9、IPG、CONTENT 分片等）。**不含** [`IMS-任务进度计划表`](./IMS-任务进度计划表.md) 中 **sysTenant 租户套餐**（批次外）；**不含** Agent 在主线 IMPLEMENTED 之后按 **`#` 流水号** 登记的 **closure / 定向验证 / 规范** 等增量（见计划表末行 **#54** 及子行）。

| 波次 | 切片 | 交付 | 验收与 E2E |
|------|------|------|------------|
| W0 | 工程骨架 | 删 Go 工程；Python API/Worker；双库；统一响应与错误码；健康检查；原型八组导航空壳；禁 OPS HTTP 扫描 | `/health` 的 `code=0`；1440 与 390 能打开壳并开关侧栏 |
| W1 | S-IMS-A-01 | 本地登录、钉钉回调命中本地手机号、JWT 2h/7d、失败锁定、会话 ≤3 | CHECKLIST-IMS-AUTH 登录项；P0；S1 登录步骤 |
| W1 | S-IMS-S-01 | 用户分页、新建、修改、停用、1211、手机脱敏、导入命令 | CHECKLIST-IMS-SYS 用户项 |
| W1 | S-IMS-S-02 | 角色为权限唯一载体：菜单码、R/W/D、dataScope、钉钉岗位、Diff 预览 | 角色 P0；`/auth/position/preview` 不存在 |
| W1 | S-IMS-S-03 / S-04 | 字典（停用不可删 1503）、参数（未知 key 1213） | 字典与参数 P0 |
| W1 | S-IMS-A-02 | 组织事件验签入队、幂等、16 次死信；同步写入本地用户 | 组织 P0 |
| W1 | S-IMS-A-03 | 岗位→角色供给；自动建 PENDING_CONFIG 空权限角色 | 供给规则 P0 |
| W1 | S-IMS-A-04 | 工作台，认证级白名单；待办/消息各 10 条 | 工作台 P0 |
| W1 | S-IMS-S-05 | 操作日志、登录日志、通知 | SYS-006/007 P0 |
| W1 | B9 | 中间件 fail-closed；`ims_user_scope` 上 BR-212 交集 | 五条硬指标；注册表覆盖本批表 |
| W2 | S-IMS-C-02 | 公司、实名人、手机卡、证件。人员选择器只查本地用户 | CORP 资源项；S6 证件步骤 |
| W2 | S-IMS-C-01 | 五个平台账号与采集 Tab | 账号 P0；S4 领用步骤 |
| W2 | S-IMS-C-03 | 办公/直播设备阻断页（分页+空态）；手机设备按 MASTER 契约 | 阻断项在清单注明 |
| W2 | IPG | IP 组、成员、`GET /ip-group/{id}/accounts` | IPG 契约用例 |
| W3 | S-IMS-L-01 | 直播场次；`live_room` 只读；GMV 下播录入 | CHECKLIST-IMS-LIVE；E2E S2 |
| W3 | COST | 账号成本与 ROI 独立菜单；营收取 Football 订单 HTTP，失败显示「数据延迟」 | 成本 P0；S4 冲话费步骤 |
| W4 | CONTENT S1 | SOP + 计划。先确认规格评审 | CHECKLIST 中 S1 项 |
| W4 | CONTENT S4 | 内容审核门禁，未审不可发布 | S4 项，可与 S1 并行 |
| W4 | CONTENT S2 | 工作任务登记、作者×赛事矩阵 | S2 项 |
| W4 | CONTENT S3 | 我的任务、内容管理、公推模板库 | S3 项；S7 已包含步骤 |
| W4 | CONTENT S5 | Football 方案同步与补偿队列 | S5 项 |
| W5 | S-IMS-CL-01～03 | 采集任务、统一成员、采集日志 | COLLECT checklist |
| W5 | 采集配置 | 竞品账号、关键字、元数据、阈值 | 对应页面契约 |
| W5 | S-IMS-IN-01 | 内部作品、内部账号 | INT checklist |
| W5 | S-IMS-CO-01 | 竞品作品、竞品账号、竞品库 | COMP checklist |
| W6 | HOME-001 | 运营看板，与个人工作台分开 | 首页验收 |
| W6 | 指标 | 指标管理、指标分析 | BI0 指标项 |
| W6 | S-IMS-B0-01～03 | 自定义查询列表、执行发布、未映射引导 | BI0 checklist |
| W7 | S-IMS-M-01 | 会议；日报四叶 | MEET checklist |
| W7 | S-IMS-R-01 | 上报模板、填报单、完成率 | REPORT checklist |
| W7 | S-IMS-T-01 | 培训资料、学习任务、完成率。AI 出卷保持阻断说明 | TRAIN checklist；S10 |
| W7 | S-IMS-P-01 | 考核方案、执行、结果、在线考试。状态按 ADR-IMS-005 | PERF checklist；S9 |
| W7 | FLOW | 审批发起、流转、催办 | FLOW 契约 |
| W7 | ALERT | 预警规则、实时预警 | ALERT checklist；S11 |
| W7 | S-IMS-AI-01～04 | 技能库、专家库、知识库文件管理、模型与提示词 | AIR checklist；S8 不含检索 |
| W8 | FIN | 成本核算、利润反查 | S3 |
| W8 | S-IMS-DC-01～04 | 穿透查询入口、链路、明细导出、耗时展示 | DC checklist；S12 穿透部分 |
| W8 | S-IMS-BI-01 | 报表管理、设计器、报表中心、预览下钻 | BI checklist |
| W8 | S-IMS-QT-01 | 查询工具 | QT checklist |
| W8 | S-IMS-E-01 | 组织人效页内 Tab | EFF checklist；S5/S12 相关步骤 |
| W9 | 总回归 | S1～S12 在 1440 与 390 各一轮 | `测试方案/IMS-E2E测试用例Checklist.md` |

未单独列出的菜单（作品监测等）随同组切片交付，路由与原型 `MODS` 一致，不另发明页面。

## 5. 本轮代码范围

W0 与 W1 的登录、用户主数据先行落地。角色、字典、参数、组织同步、岗位供给、工作台、日志和 B9 按上表继续，每片签收后再进入 W2。
