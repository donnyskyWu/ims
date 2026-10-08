# TESTCASES-IMS-BI0 — 自定义查询（P0）

---

### TC-IMS-B0-001-01 已映射实体查询

- **Given** seed 实体 E 已在 P4m 映射  
- **When** 选 E 执行 run  
- **Then** 200；结果列与 fields 配置一致

### TC-IMS-B0-001-02 未映射实体

- **When** 选未映射实体 code  
- **Then** 1261；UI 展示跳转 P4m

### TC-IMS-B0-001-03 保存并发布

- **When** 保存查询并 PUT publish  
- **Then** 发布态可被引用；列表状态更新

### TC-IMS-B0-001-04 无元数据 CRUD

- **When** 在 P4 页找「新增实体」  
- **Then** **无**；仅链至 COLLECT


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-BI0-01 维护指标定义

### TC-IMS-BI0-01-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17。
- **When** 用户按故事主路径操作（页面 `bi0Metric`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一。

## US-BI0-02 指标分析看板

### TC-IMS-BI0-02-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17。
- **When** 用户按故事主路径操作（页面 `bi0Analysis`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一。

## US-BI0-03 自定义 SQL 查询

### TC-IMS-BI0-03-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17。
- **When** 用户按故事主路径操作（页面 `bi0Query`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一。

