# TESTCASES-IMS-QT — 查询工具

> **版本**：v1.0 ｜ 2026-10-01  
> **故事 SSOT**：`产品PRD/IMS-业务用户故事.md` US-QT-01～07  
> **API SSOT**：《QT-查询工具-API契约》§2～§3（禁止新增 REST）

---

## US-QT-01 配置分级下钻并保存草稿

### TC-IMS-QT-001-01 DRILL 保存草稿

- **Given** R9 已登录；COLLECT 存在已映射实体 `E1`  
- **When** 在查询配置 Tab 选 DRILL、配置 ≥2 层展示列并点击保存草稿（`POST /admin-api/ims/analysis/query-tool/template/`）  
- **Then** 返回 templateCode；查询记录 Tab 出现 status=DRAFT、mode=DRILL 的行

### TC-IMS-QT-001-02 未映射实体

- **Given** 根实体未映射  
- **When** 保存或执行前选该实体  
- **Then** UI 展示 1261 文案；可跳转 `/ims/collect/metadata`

---

## US-QT-02 配置穿透路径并保存

### TC-IMS-QT-002-01 TRACE 保存草稿

- **Given** R4 已登录；DC trace entry 可搜索  
- **When** 配置 pathSteps[] + 入口类型，保存 TraceTemplate 草稿  
- **Then** 查询记录存在 mode=TRACE、DRAFT 行；切换 DRILL 再切回 TRACE 草稿仍在（U1）

### TC-IMS-QT-002-02 入口搜索

- **Given** 有效 keyword  
- **When** `GET /admin-api/ims/dc/trace/entry?entryType=PERSON&keyword=`  
- **Then** code=0；列表供选 entryId

---

## US-QT-03 从查询记录编辑

### TC-IMS-QT-003-01 编辑草稿

- **Given** 存在 DRAFT 模板 `T1`  
- **When** 查询记录点编辑并 `PUT /admin-api/ims/analysis/query-tool/template/T1` 改名称  
- **Then** 列表名称与 updatedAt 更新

### TC-IMS-QT-003-02 已发布不可直接编辑

- **Given** 模板 status=PUBLISHED  
- **When** 点编辑  
- **Then** 提示先取消发布；不产生 PUT

---

## US-QT-04 发布为数据分析下菜单

### TC-IMS-QT-004-01 模板发布

- **Given** DRAFT 模板 `T1`  
- **When** `POST /admin-api/ims/analysis/query-tool/template/T1/publish`  
- **Then** status=PUBLISHED；查询记录状态列=已发布

### TC-IMS-QT-004-02 MenuSeed 挂 L3

- **Given** PUBLISHED 模板 `T1`；租户套餐含数据分析组  
- **When** `POST /admin-api/ims/analysis/query-tool/menu-seed` body 含 menuTitle、templateCode  
- **Then** 返回 menuId、routePath=`/ims/analysis/query-tool/run/T1`；记录菜单路径=已挂 L3

### TC-IMS-QT-004-03 草稿不可 seed

- **Given** status=DRAFT  
- **When** menu-seed  
- **Then** 1263 或等价业务错误

---

## US-QT-05 从新菜单执行

### TC-IMS-QT-005-01 同步 run DRILL

- **Given** PUBLISHED 模板；用户具 `ims:analysis:qt:run:{code}`  
- **When** `POST /admin-api/ims/analysis/query-tool/run` mode=DRILL、templateCode 有效  
- **Then** 响应 QueryResult.queryMode=SYNC；含 queryCostMs、rows；**不**返回 asyncTaskId/1262

### TC-IMS-QT-005-02 同步 run TRACE

- **Given** TRACE 模板与 entryId  
- **When** 同上 mode=TRACE  
- **Then** 单次 HTTP 完成；结果区可切换列表|图表（AC-QT-005）

### TC-IMS-QT-005-03 无 run 权限

- **Given** 用户无 run perm  
- **When** run  
- **Then** 1264

---

## US-QT-06 取消发布与菜单

### TC-IMS-QT-006-01 取消发布保留记录

- **Given** PUBLISHED 模板  
- **When** `POST …/template/{code}/unpublish`  
- **Then** status=DRAFT；列表仍有该行（AC-QT-007）

### TC-IMS-QT-006-02 撤销侧栏

- **Given** 已 menu-seed  
- **When** `DELETE …/analysis/query-tool/menu-seed/{code}`  
- **Then** 侧栏 L3 不可见；menuSeed=false；模板可为 DRAFT 或 PUBLISHED

---

## US-QT-07 删除记录

### TC-IMS-QT-007-01 删除草稿

- **Given** DRAFT 且无 menuSeed  
- **When** Confirm 后 `DELETE …/template/{code}`  
- **Then** 列表无该行

### TC-IMS-QT-007-02 已 seed 禁止删模板

- **Given** menuSeed=true  
- **When** DELETE template  
- **Then** 1265；提示先撤销侧栏
