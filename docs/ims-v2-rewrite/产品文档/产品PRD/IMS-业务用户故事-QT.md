# IMS 业务用户故事 — 查询工具

## 查询工具（US-QT）

**规格 SSOT**：《QT-查询工具-页面规格》QT-001；《QT-查询工具-API契约》§2～§3。  
**菜单**：数据决策 → 数据分析 → 查询工具（`/ims/analysis/query-tool`）。

### US-QT-01 配置分级下钻并保存草稿

- **角色**：数据分析师 R9  
- **业务目标**：把「从实体 A 逐层看到明细」的分析意图存成可复用模板，先不对外发布。  
- **前置条件**：COLLECT 元数据至少一个 **已映射** 实体；具备 `ims:analysis:query-tool:query`（或等价套餐菜单）。  
- **主路径**：进入查询工具 → **查询配置** Tab → 模式 **DRILL** → 根实体（只读 `GET …/collect/metadata/entity/{code}/fields`）→ 配置 L1～Ln 展示列与层间关联（≤5 层）→ 填写模板名称 → **保存草稿**（`POST …/analysis/query-tool/template/` 或 `PUT …/{templateCode}`，status=DRAFT）。  
- **成功结果**：**查询记录** Tab 出现一条 **草稿** 行；可继续编辑；切换 DRILL/TRACE 不清空对侧草稿（FR-QT-011 / U1）。  
- **异常**：未映射实体 → 1261 文案 + 链 **数据采集 → 元数据维护**；无写权限 → 1264。  
- **追溯**：FR-QT-003、006、008、011；AC-QT-003；TC-IMS-QT-001-01～02。

### US-QT-02 配置穿透路径并保存

- **角色**：运营总监 R4  
- **业务目标**：固定一条「从人员/账号/场次等入口沿关联链查到底」的穿透方案，供团队重复执行。  
- **前置条件**：DC 宽表 seed 可用；TRACE 入口类型六种之一（页面规格 §5 pathSteps）。  
- **主路径**：**查询配置** → 模式 **TRACE** → 搭建 `pathSteps[]`（实体 + 至下一层关联边）→ 配置入口类型与关键词（搜索 `GET …/dc/trace/entry`）→ **保存草稿**（TraceTemplate 载荷，同上 template CRUD）。  
- **成功结果**：查询记录中 **TRACE + 草稿**；编辑抽屉可回填 pathSteps（AC-QT-006）。  
- **异常**：入口无匹配 → 空列表提示调整关键词；run 时未选 entryId → 前端校验拦截。  
- **追溯**：FR-QT-004、006、011；AC-QT-004；TC-IMS-QT-002-01～02。

### US-QT-03 从查询记录编辑

- **角色**：R9  
- **业务目标**：在不动侧栏菜单的前提下，修正已保存模板名称或层级/穿透链。  
- **前置条件**：存在 DRAFT 模板；**已发布**须先取消发布（页面规格 U10 / 原型一致）。  
- **主路径**：**查询记录** → qbar 筛「草稿」→ 行 **编辑**（720px 抽屉或回填查询配置 Tab）→ 改 DrillTemplate/TraceTemplate → 保存（`PUT …/template/{templateCode}`）。  
- **成功结果**：列表 **更新时间** 刷新；草稿内容在 **执行** 时作为 `inlineTemplate` 或 `templateCode` 载入。  
- **异常**：对已发布直接编辑 → 提示「请先取消发布」；模板不存在 → 1263。  
- **追溯**：FR-QT-008、009、011；AC-QT-006；TC-IMS-QT-003-01～02。

### US-QT-04 发布为「数据分析」下的菜单（名称、谁可见）

- **角色**：R4（具备发布与 MenuSeed 权限）  
- **业务目标**：让业务同事从侧栏直接进入某条已发布查询，而不每次进查询工具找记录。  
- **前置条件**：模板 status=**PUBLISHED**（行内 **发布** → `POST …/template/{templateCode}/publish`）；套餐 seed 含数据分析组（ADR-IMS-007）。  
- **主路径**：查询记录 → 已发布行 → **发布到侧栏**（或配置 Tab **发布为侧栏 L3**）→ 填菜单标题（≤16 字，默认模板名）→ 可选 permCode（默认 `ims:analysis:qt:run:{templateCode}`）→ 提交 `POST …/analysis/query-tool/menu-seed`（parent 固定 **数据分析** 组）。  
- **成功结果**：侧栏 **数据分析** 下新增 L3，路由 `/ims/analysis/query-tool/run/{templateCode}`；记录列 **菜单路径** 显示「已挂 L3」；仅具备对应 perm 的用户可见。  
- **异常**：草稿不可 seed → 1263；MenuSeed 冲突 → 1266~1270（分析段预留，待切片登记）；租户套餐未含菜单 → 用户侧栏不可见（SYS-008）。  
- **追溯**：FR-QT-007、010；API §3.3；TC-IMS-QT-004-01～03。

### US-QT-05 从新菜单打开并执行，看到列表/图表

- **角色**：运营 R5（被分配 run 权限）  
- **业务目标**：用发布好的查询回答日常问题（下钻表或穿透结果）。  
- **前置条件**：MenuSeed 已挂或从查询记录 **执行**；模板 PUBLISHED。  
- **主路径**：侧栏新 L3（或查询记录 **执行** 跳转配置 Tab 并预载）→ 填运行时条件（TRACE 选源头行 / DRILL 选首层行）→ **执行** → 单次 `POST …/analysis/query-tool/run`（**同步**，无 1262 轮询）→ **QueryResultPanel** 切换 **列表 | 图表**，查看 `queryCostMs`。  
- **成功结果**：当前层 rows/图表展示；DRILL 可「下钻下一层」更新面包屑；TRACE 服务端逐步 DC，前端一次 run。  
- **异常**：无 run 权限 → 1264；超时 → 1181/同步超时提示（**禁止** QT 走 1262 job）；>3000ms 橙色（TRACE · BR-205）。  
- **追溯**：FR-QT-005、006；AC-QT-005、008；TC-IMS-QT-005-01～03。

### US-QT-06 取消发布后菜单消失、记录仍在

- **角色**：R4  
- **业务目标**：下线对外模板态，但保留配置以便修改；侧栏入口与模板态解耦。  
- **前置条件**：存在 PUBLISHED 模板；若已 MenuSeed，须理解 **unpublish 不自动删菜单**（API §3.1、§3.3）。  
- **主路径**：查询记录 → **取消发布**（`POST …/template/{templateCode}/unpublish`）→ 若曾挂菜单 → **撤销侧栏**（`DELETE …/menu-seed/{templateCode}`）或发布时勾选「同时下线菜单」。  
- **成功结果**：模板 status=**DRAFT**，记录仍在列表；侧栏 L3 消失；已挂菜单列变为「未挂菜单」。  
- **异常**：仅 unpublish 未删 seed → 侧栏仍可进 run 页（须显式撤销）；误操作可重新发布 + 再 seed。  
- **追溯**：FR-QT-009、010；AC-QT-007；TC-IMS-QT-006-01～02。

### US-QT-07 删除记录

- **角色**：R9（本人草稿）或 R1  
- **业务目标**：清理错误或废弃模板，避免查询记录堆积。  
- **前置条件**：模板为 DRAFT，或已撤销 MenuSeed（已 seed 禁止 DELETE → 1265）。  
- **主路径**：查询记录 → 选草稿行 → **删除** → ConfirmDialog → `DELETE …/template/{templateCode}`。  
- **成功结果**：列表少一条；侧栏无残留（若从未 seed）。  
- **异常**：已挂 MenuSeed 删除 → 1265 + 提示先撤销侧栏；无权限 → 1264。  
- **追溯**：FR-QT-009；AC-QT-008；TC-IMS-QT-007-01～02。

