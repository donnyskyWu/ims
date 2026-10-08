# IMS 系统产品 — 项目长期记忆

> 本文件记录跨会话复用的项目约定与关键事实。最后更新：2026-10-05

## 一、文档 SSOT 与版本纪律

| 角色 | 文件 |
|------|------|
| 需求 SSOT | `产品PRD/IMS完整产品需求文档.md`（版本以**文首版本行**为唯一准，2026-10-05 时为 **v2.6.34**） |
| 叙事 SSOT | `产品PRD/IMS-业务用户故事.md` **v1.6**（89 条 L3 故事，分册 A～F + QT；F 分册含 US-AIR-01~05，已按「语义检索整体移出」改写） |
| 权限模型 | **ADR-IMS-008**（角色=权限唯一载体）；`产品规划/ADR-IMS-008-角色与岗位权限模型收敛.md` |
| 交互 SSOT（OPS 并入域） | **现网 OPS 的 `UX-M*.md`**，不是 IMS 原型（ADR-IMS-003） |
| 错误码 SSOT | `产品规格/全局开发规范.md` §3 + `产品规格/全局开发规范-完整版补充.md` §4 + 现网 `GLOBAL-CONVENTIONS.md` §5.3；**统一索引 = `产品规格/错误码映射表-附录.md`（2026-10-03 新建）** |
| 技术设计 | `产品规划/IMS-技术设计总册-20261001.md` |
| 交付过程包 | `delivery/`（19 模块 × SLICES/CHECKLIST/TESTCASES） |

**治理纪律**：改 PRD 版本后，必须同步 ①根 `README.md` 索引 ②`IMS-走查交付状态-*` ③`IMS-PRD与原型完整性核验-*` 的文档头版本号。**报告型滞后**（规格已修但核验报告仍说「冲突待解决」）是本项目反复出现的问题，订正规格时必须一并订正报告。

## 二、架构铁律（不可动摇）

- IR-01：IMS 独立应用，网关 `/admin-api/ims/`；业务数据源 = **现网 OPS 业务库**，不搬库。
- IR-02：Football **仅 HTTP WebAPI**（禁 Feign / RPC / JDBC）；唯一例外 = **`live_room` 表只读**（ADR-IMS-001 共用业务库）。
  - **v2.6.34（B2）**：LIVE 单场「直播数据」Tab **全部**取 `live_room` 只读——房间（`id/author_id/昵称/头像/live_id/名称/封面/status`1~5`/横竖屏/公开·付费·加密/起止时间/观看·回放·推流地址）+ **计数（预约/点赞/`viewer_count`）**；GMV/峰值/涨粉/退款/投放 由 **LIVE-002 下播录入** 承载，Tab **不再显示「—」**。原「Football 单场 metrics OpenAPI BLOCKED」**已解除**。
- **全局分页铁律（v2.6.34）**：**所有管理/列表页必须有分页组件**（《全局开发规范》§2.5）；`PageParam{pageNo,pageSize}` / `PageResult<T>{list,total,pageNo,pageSize}`（`pageNo` 从 1、`pageSize` 默认 10）；**禁** `page`/`size`/`limit`/`offset`。原型共用 `tbl()` 自动注入 `pager()`。
- IR-03：IMS 验收后**停 OPS**，禁止调用 OPS 服务。
- IR-04：现网表**只加列**，禁删列；新建用 `ims_` 前缀。
- ADR-IMS-002：**Go + 轻量 Vue，不用芋道**。
- **ADR-IMS-008：角色（SYS-002）= 权限唯一载体**（2026-10-04 拍板）：角色吸收「菜单权限码 + 功能点 R/W/D（新 `ims_role_perm_detail`）+ dataScope 数据范围 + 钉钉岗位绑定（`ims_sys_role.dingtalk_position`）」；**岗位模板（AUTH-003）降级为「钉钉岗位 → 角色 自动供给规则」**（保留版本管理 POS-R2 · 字段 `grant_role_ids`）；`ims_position_template_perm` **DEPRECATED**。**钉钉同步岗位若无匹配角色 → 自动建角色**，8 条护栏 G1-G8：G1 失败关闭（空权限≠放行）· G2 `source=DINGTALK_AUTO` · G3 `status=PENDING_CONFIG` · G4 推送 R1 待办 · G5 1:1 唯一（POS-R1）· G6 幂等 upsert（按 `dingtalkPosition`）· G7 岗位消失且无用户时归档（POS-R3）· G8 全量审计。**岗位≠角色**：来源/基准/版本/触发/外部契约不同，只收敛「权限明细载体」，不合并概念。
- ADR-IMS-047：**凭证铁律**——抖音/快手/视频号 Cookie、扫码、Collector bind 只在「公司资产 → 平台账号详情 · 采集 Tab」；配置行/外部账号行**禁止**嵌 Cookie。
- 用户主键 = `system_users.id`（ADR-056）；租户 `tenant_id` 全表（ADR-007）。
- **AIR：模块 20「AI 资源中台」= 四叶**（2026-10-04 v2.6.31 由三叶扩）：技能库 `airSkill` / 专家库 `airExpert` / **知识库 `airKb`（由 Deferred 恢复 In Scope）** / 模型与提示词 `airCfg`；**Key 管理 `airKey` / 审计监控 `airLog` 仍 Deferred**（无菜单、`go()` 重定向 `airSkill`）。知识库含 **KNOW-005 知识分类管理**（库内两级树 `ims_kb_category`）+ **KNOW-006 系统资料转入**（TRAIN/PERF/CONTENT 按条目勾选）+ **手动上传三方式**（文件/URL/粘贴文本）。知识域端点 9→17，AIR 总端点 43→51。**AIR 交互 SSOT 仍为原型 `PAGES.air*`/OPS UX（AIR 未并入 OPS）**。
  - **v2.6.34 语义检索「整体移出本期范围（不做）」（2026-10-05）**：**KNOW-003 知识检索 / KB-001 RAGFlow 底座 / `experts.assemble.knowledge_context` / 错误码 5007-5008（号位作废）全部移除**（**非「延后」**）；知识库本期**只做文件管理**（库/分类/条目元数据/入库审批/授权/系统转入/手动上传）。底座 Provider `KbProvider` **仅 `LOCAL`**（IMS 侧对象存储，`ims_kb_doc` 含 `oss_key/file_size/content_type`）；状态机 PENDING→PUBLISHED（无 `PARSING`）；**端点 admin 42 / 总 47**；**MCP 工具固定 4**（`skills.list`/`skills.get`/`experts.list`/`experts.assemble`）。`KnowledgeProvider` 抽象保留供未来扩展，**本期不引入任何检索底座**。
  - *(历史)* v2.6.32~33 曾表述为「收窄为文件管理期、检索**延后**至检索期」——**已废弃，一律以 v2.6.34「移出范围」为准**。
- **CONTENT 内容生产 = 7 子菜单**（2026-10-05 v2.6.33 回正）：SOP管理 / 计划管理 / 工作任务登记 / 我的任务 / 内容管理 / 公推模板库 / 内容审核。原型此前多挂 2 项（9 项），本次**回正为 PRD §15 / §5.5 原表 7 项**。
  - **SOP 审核整体移除**：无「SOP审核」菜单/页面/队列；**模板免审**（保存新版本即可，直接启用/停用）。原型删除 `MODS.contentSopReview`、`PAGES.contentSopReview`、`SOP_REVIEWS`、`sopReview*` 系列函数/种子、`R8.modules` 提及；`contentSopTab` 去「待审核任务」按钮与行内「提交审核」。
  - **「全部任务」= 「我的任务」页内 Tab**（`setTab('contentTask','全部任务')`），**无独立菜单**；原型删除 `MODS.contentTaskAll`/`PAGES.contentTaskAll` 及路由。
  - 对应 OPS 功能点 P-M2-017（SOP 模板审核）、P-M2-018（全部任务独立菜单）**已移除**。
- **CONTENT 计划管理不含营销计划维护**（2026-10-03 落地）：计划管理（`/ims/content/plan` · P-M2-011）仅 **计划向导/列表**（CONTENT-102）；**营销计划是 SOP 模板属性**（`marketing_plan` 启用态同租户 1:1 · ADR-074 D2），在 **SOP 管理** 维护。**权威依据**：OPS `UX-M2` **§9 本身无营销计划区**——凡「A 区营销计划」类加戏均为**过度对齐**，须以 UX 原文章节为准。原 CONTENT-101「营销计划绑定 SOP」已并入 CONTENT-100。

### 二·补 · 2026-10-05 二次确认落地（B3 / B9 / B5）

- **B3 级联范式**：并入域「实体 → 账号」级联**统一沿用 IP 组账号池**——`GET /admin-api/ims/ip-group/{id}/accounts` 为**全系统唯一数据源**（REPORT 等域选作者 → 读 `ipGroupId` → 调该端点过滤 `AccountSelect`）；**禁止**新造 `…/{entity}/accounts` 聚合接口（`authors/{id}/accounts` 被 REPORT 契约**明令禁止**）；共池失败 **1127**。落点：`V1/IPG-IP组运营-API契约.md`（IPG-003 注）。
- **B9 统一权限中间件**：全业务表 `tenant_id` 行级隔离 + BR-305 四级数据范围（**权威口径以 PRD 为准**：`ALL`/`DEPT`/`IP_GROUP`/`SELF` =「全部 / 本部门 / IP 组 / 仅本人」；**「本部门」不含下级**，无 `DEPT_AND_CHILD`）+ BR-212 发布/分享双重过滤（创建者 ∩ 查看者）**统一在中间件一处执行**；模块**禁自实现**；**fail-closed**（空权限≠放行）；跨租户 **1504**。落点：`V1/SYS-系统管理-页面规格.md` **§P2A**。
  - **⚠️ 已发现的规格错误（2026-10-05 核实，待订正）**：`V1/SYS-系统管理-页面规格.md` §P2A 第 2 条把四级写成 `ALL`/`DEPT_AND_CHILD`/`DEPT`/`本人(SELF)`，**多出 `DEPT_AND_CHILD`、漏掉 `IP_GROUP`**，与 PRD 第 117 行 BR-305 及 OPS `PRD-M0-首页.md:63`（核心证据：BR-006 = 角色+部门+IP组+人员 4 级）不符。**用户 2026-10-05 拍板：以 PRD BR-305 为准，本部门不含下级。** 订正 §P2A 时同步核查 `全局开发规范.md` §4 枚举与中间件实现。
- **B5 CI 禁 OPS HTTP 门禁**：并入域直连 `oa_*` 同库，CI 静态扫描**禁 OPS host / `ops.` base-url**（白名单仅 Football WebAPI），命中即阻断合并；验收后停 OPS、禁长期双写。落点：`全局开发规范.md` **§7A**。

## 三、错误码冲突裁决（2026-10-03 已裁决并落地，详见附录 §5）

1. **`1271~1273` 双占 → 已裁决**：`1271/1272/1273` 归还 **Football WebAPI 段**；QT 查询工具改用 **1263/1264/1265**（`1263` 模板不存在、`1264` 无 run 权限、`1265` 已挂 MenuSeed 不可删）；原 `1278`(MenuSeed 撤销) → `1265`。
   - **`1261~1270` 定义为「BI0 / 分析域共用段」**（BI0 与 QT 同属数据分析域）：1261~1262 = BI0；1263~1265 = QT；1266~1270 = 分析域预留。**此口径已写入附录 §2 与完整版补充 §4**。
   - 受影响文件均已同步：`V3/QT-查询工具-API契约.md`、`产品PRD/IMS-业务用户故事-QT.md`(6处)、`delivery/TESTCASES-IMS-QT.md`(3处)、`ADR-IMS-002:35`。
2. **`1500/1501/1502` 语义漂移 → 已裁决（按域分流）**：权威语义 = `1500 不存在 / 1501 已停用注销 / 1502 已被引用 / 1503 字典非法 / 1504 跨租户`（GLOBAL-CONVENTIONS §5.3）。**1500~1504 为跨域通用码，可与 §2 专段并存**。
   - **并入域保留现网用法**（BR-307「提示不倒退」）：M2 内容/任务门禁、IPG、内容计划仍用 1500 作通用校验、1501 指「不存在」。
   - **IMS 自建域对齐权威语义**：已改 `V1/CORP-公司资产-API契约.md` §4、`V1/CONTENT-OPS并入补充-页面规格.md`、`V2/REPORT-*`、`PRD` 用户故事-C/D、`PRD:804`、`CORP/MASTER 页面规格`、`delivery/*CORP*`。

3. **`5007/5008` 号位作废（v2.6.34 已决）**：原 `5007` RAGFlow 检索超时 / `5008` RAGFlow 组件不健康，随 **AIR 语义检索整体移出范围**一并**移除、号位作废**（不再是「检索期启用」）。`全局开发规范.md` §3 + `错误码映射表-附录.md` 已标注「已移除」。前端 Axios 拦截器映射区间相应为 `5001~5006`。

**判例纪律**：错误码类问题必须**全链路**排查（契约 + 页面规格 + PRD 用户故事 + delivery 测试用例 + ADR + 索引报告），只改契约会把不一致「搬个家」。修订后必须跑一次「反向引用 Grep」。

## 四、字典/枚举权威（2026-10-03 订正）

**铁律：枚举值以现网源码为准，文档可能滞后。**

- `dict_perf_metric_type`（M6 指标类型）= **BASIC 基础指标 / COMPOSITE 复合指标**（仅 2 项），来源 `mock/ops/dict.ts:142`。原 `GLOBAL-CONVENTIONS` 记「数量/质量/营收/增长率/复合」为 M3 语境**误植**，已订正。`CALCULATED`/`DERIVED` 属 M3 绩效执行域（`types/ops/perfExecution.ts`），**非** M6 指标类型。
- `dict_query_status` = 现网**硬编码** DRAFT/PUBLISHED（未接字典），`oa_query.status` 的 N:1 映射待实现；PRD-M6 AC-M6-005-3 已订正。
- **指标管理（P-M6-001）**：非 COMPOSITE 走 `MetricBuilder` 复合组件（数据源/计算方式/计算字段/汇总字段/关联表/查询条件/字段列表侧栏）；弹窗 **960px**；**预览为内联面板（≤20 行）**，非二级弹窗；类型列走 `DictLabel`；表单含 F-UNIT 单位。
- **指标分析（P-M6-016）**：**只读消费**（无 CRUD）；多选指标 + `MetricConditionInput` 动态参数；C-Tab = 「指标明细」/「**指标趋势**」（**非**「对比视图」，文档曾滞后）。
- **自定义查询（P-M6-013）**：执行成功**自动折叠**配置区；结果面板**在页 Tab 外**渲染（避免嵌套 tabs）；执行 90% 宽 / 编辑 960px dialog；发布需 confirm；页 Tab name = `builder`/`saved`。

**上游副本注意**：`参考文件/ops产品参考文件/` 是 OPS 的**本地副本**；订正后上游原文 `D:/self/sy/运营数据平台/202606/wd/docs/` 仍为旧值，需另行同步（属另一工作区，2026-10-03 未动）。

## 五、整系统 Gate 现状

- 故事层 87/87 闭环；但整系统**「按 PRD 3A 全量开写」不可**，仅支持**模块级 Slice Gate**（B1：CONTENT 按 **5 切片** S1 SOP+计划 → S2 登记+矩阵 → S3 我的任务+内容 → S4 审核门禁 G1 → S5 Football 同步，每片独立 Gate）。
- **2026-10-05 二次确认（逐条拍板，均采纳推荐项）**：B1 = **S1 规格先行 + S4 审核门禁并行**（门禁优先）；B3 = **统一 IP 组级联范式**；B8 = **本期按 ADR-IMS-005 实现**；B9 + B5 = **权限中间件 + CI 禁 OPS 门禁两项本期落地**。
- 剩余待办（策略已定、待开工）：CONTENT S1/S4 切片开写、PERF 状态映射实现、权限中间件与 CI 门禁落地。**已解除**：Football 直播 metrics（B2 → `live_room` 只读）、AIR 知识检索（B6 移出）、B3 级联（统一范式）。

## 六、2026-10-05（R-E）四项裁定 —— 存储 / 唯一化 / 双契约 / 直播口径

- **直播时长聚合 = 照抄现网**（不重造）：`live_room` 只读，`author_id=? AND create_time BETWEEN ? AND ?`（**无 `deleted`**）；`liveCount=count(1)`、`liveDuration=sum(TIMESTAMPDIFF(MINUTE,start_time,end_time))`。**与 `selectLiveTrendStat`（`deleted=0` 且 `status IN(2,3)`、小时、按 `DATE` 分组）两条口径不混用**——后者 IMS 本期**不消费**。落点 **M6 / BI0**，非 LIVE 单场 Tab。见 FB 适配 §2.2 + LIVE 契约 §2.2。
- **账号→作者唯一化 = 加列**：`oa_ip_group_anchor_rel.is_primary`（主作者，每租户每 IP 组至多 1）+ `oa_platform_account.author_user_id`（物化）。解析优先级：账号列 → 组主作者 → 组内唯一作者 → 否则 **1223**（未配置 / 不唯一，**禁"猜"**）。级联读统一 `GET /ip-group/{id}/accounts`，**禁** `authors/{id}/accounts`。
- **CONTENT 双契约 = 方案甲（范围权）**：主契约 = **字段权**（DTO SSOT）；补充契约 = **范围权**（OPS 主路径端点清单）。裁决：**端点是否在范围内查补充契约，字段长什么样查主契约**。
- **文件存储 = 本期不上对象存储**：《全局开发规范》**§6.3** 铁律——统一 IMS **服务端文件目录**（`ims.file.storage.root`），DB 存 `fileKey` 相对路径，读链 `GET /admin-api/ims/file/{fileKey}`，`StorageProvider`/`LocalStorageProvider` 抽象保留；`oss_key`→`file_key`；**5005 = 文件上传/落盘失败**。产品规格 / PRD / delivery / 测试方案已全量同步。
- Football 全路径对照表已**引进** `产品规格/V1/FB-Football-WebAPI-待盘点全路径对照表.md`（IMS 引进版）。断点方案 §0.5 + 决策清单 D8~D11 已登记。

## 七、2026-10-05 开发启动裁定（Sprint 0 收尾 + AUTH/SYS 首批）

**用户拍板**：可开发，但按**模块级 Slice Gate** 分批推进（**非**整系统「按 PRD 3A 全量开写」）；本轮**暂不建仓、只出方案**；首批 = Sprint 0 收尾 + AUTH/SYS 骨架；组织 = 标准 SOP（PM→架构→工程→QA），团队 `software-ims`，交付目录 `开发方案/`。

**关键事实**：`D:/self/sy/` 全域**无 IMS 代码工程**（无 `go.mod`/`package.json`），开发需从零建仓。

**Sprint 0 八项现况 = 5 关 / 2 未关 / 1 待拍**：
- ✅ 已关：用户 FK 规范（ADR-056 摘要）、Football 全路径对照表、并入域升格规格、错误码映射表、19 模块 delivery 过程包
- ❌ 未关：① `产品PRD/IMS第一期PRD-V1.md` **第 83 / 2009 / 2482 行**「已完成模块只增量 / 不重复建设」冲突句未删（与 ADR-001 + 完整 PRD 冲突，会致选错表）；② **表映射登记册**（源表→IMS 表 1:1 + 加列清单）不存在
- ⚠️ 待拍：双财务入口 / 删除已上架内容规则

**四项架构级裁决（2026-10-05，架构师产出并经用户确认）**：
1. **BR-305 数据范围 = `ALL` / `DEPT` / `IP_GROUP` / `SELF`**（全部/本部门/IP 组/仅本人）；**删除 `DEPT_AND_CHILD`**，「本部门」**不含下级**；`IP_GROUP` 是与部门**并列的四级之一**（**非独立轴**）；`tenant_id` 才是**正交强制轴**；BR-212 为发布/分享**额外交集**。待订正：`SYS-页面规格` §P2A 第 2 条 + §P2 功能点 3、`SYS-API契约` 行 12/34、`AUTH-页面规格` 行 7、`ADR-008` §2 line 28、`CHECKLIST-IMS-SYS` 行 24、`全局开发规范` §4 新增 `DataScope` 单源。
2. **角色权限表以 ADR-IMS-008 §5 为准**：`ims_sys_role`（`data_scope`/`dingtalk_position`/`source`/`status`）+ `ims_sys_role_menu` + **新建 `ims_role_perm_detail`**（R/W/D 明细）；`ims_position_template` 收敛为供给规则（`grant_role_ids`）；`ims_position_template_perm` **DEPRECATED**；**`ims_auth_role_matrix` / `ims_auth_data_scope` 作废（不建表）**。待订正 6 行：共享技术规范 §7.1:16 / §7.2:49-50、V1 PRD:2027-2028、V2 PRD:1857-1858、V3 PRD:1409-1410。
3. **`system_users` 归属 Football `shenyu-system`**：IMS 走 **Football HTTP 读**（simple-list，IR-02 白名单），**非同库直读**；IMS **不回写用户主表**，只写 `ims_auth_user_mapping` / `ims_sys_user_role`。IR-06「共用运营用户表（OPS 库）」措辞须精确为「**共用主键口径，物理表在 Football system**」。
4. **菜单 = IMS 自建 `ims_sys_menu`，id 对齐 `system_menu.id`**；套餐门控仍**只读** Football `system_tenant_package_menu`；上线前 **menuId 对账**为硬门槛。字典/参数 IMS 自建（`ims_sys_dict_type` / `ims_sys_dict_data` / `ims_sys_param`），`dictValue` 与现网兼容。

**U-1~U-5 裁决**：U-1 `ims_sys_user_role`（IMS 自建）· **U-2（用户拍板）：SYS-001「创建用户」= 仅建 IMS 侧映射 + 绑角色，Football 建号不在 IMS 范围** · U-3 菜单 id「现网取原 id + IMS 新增预留段 + 上线对账」· U-4 `IP_GROUP` 经 `oa_ip_group` 成员关系解析并缓存登录上下文 · U-5 **Sprint 0 为硬前置**（登记册定稿 + V1 PRD grep 命中 0 才开写，与 B5 同法）。

**架构任务分解**：T01 工程骨架与横切基座 → T02 AUTH-001 SSO + B9 中间件骨架 → T03 SYS 域 → T04 AUTH 域（组织同步/岗位供给/工作台）→ T05 B9 全链加固 + 集成回归 + Sprint 0 口径落地；拆 **15 子任务**映射 9 个 Slice（S-IMS-A-01~04 / S-IMS-S-01~05）。**批次外**：SYS-006 日志 / SYS-007 通知 / SYS-008 租户套餐（待 menuId 对账）。

**已知时序耦合**：T02 中间件 与 T03 角色存在「登录上下文 vs 权限定义」耦合 → **T02 先落骨架 + fail-closed + 1504，T05 收口 BR-212 交集与 `scope_registry` 全表登记**。

**团队纪律执行**：工程师曾申请自接 QA 任务（#4），**被拒**——测试策略必须 QA 独立产出，实现方自测自证 = 橡皮图章。
