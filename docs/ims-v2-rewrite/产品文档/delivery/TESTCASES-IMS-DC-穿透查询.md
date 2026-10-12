# TESTCASES-IMS-DC — 穿透查询（P0）

---

### TC-IMS-DC-001-01 入口搜索

- **When** `GET /dc/trace/entry?keyword=DY&entryType=ACCOUNT`  
- **Then** 返回候选 list；UI 可选中

### TC-IMS-DC-001-02 穿透查询

- **When** `POST /dc/trace/query` mode=GRAPH 合法 entryId  
- **Then** nodes 非空（seed）；queryCostMs 有值

### TC-IMS-DC-001-03 逐层下钻

- **Given** 图上一节点 N  
- **When** 点击 chip 下钻  
- **Then** 前端以 N 的 type/id 再 POST query；**无** lineage 专用接口

### TC-IMS-DC-001-04 场次明细

- **When** `GET /dc/trace/detail/{sessionCode}`  
- **Then** 19 位 sessionCode 可解析；利润字段按角色脱敏

### TC-IMS-DC-001-05 性能

- **When** seed 规模 query  
- **Then** P95 目标 <3s（环境允许时验收；否则记录 queryCostMs）


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-COST-01 查看账号 ROI 与成本

### TC-IMS-COST-01-01 P0 主路径

- **Given** COST 规格；Football page-for-ops authorId。
- **When** 用户按故事主路径操作（页面 `cost`）
- **Then** 金额 ¥ 两位；与 FIN 场次利润不混显。

## US-FIN-01 场次成本核算

### TC-IMS-FIN-01-01 P0 主路径

- **Given** FIN-001；场次 seed。
- **When** 用户按故事主路径操作（页面 `finCost`）
- **Then** 核准态写入；与 LIVE 下播 GMV 口径标注。

## US-FIN-02 利润反查链路

### TC-IMS-FIN-02-01 P0 主路径

- **Given** DC-002 API grounding。
- **When** 用户按故事主路径操作（页面 `finProfitTrace`）
- **Then** 权限 ims:fin:profit-trace:query；脱敏矩阵生效。

## US-DC-01 穿透查询逐层下钻

### TC-IMS-DC-01-01 P0 主路径

- **Given** DC 宽表；DC-001。
- **When** 用户按故事主路径操作（页面 `dc`）
- **Then** queryCostMs 展示；>3000ms 橙色；R7 成本脱敏。

