# TESTCASES-IMS-BI — 数据报表

## TC-P0-01

- **Given** R4 已登录
- **When** `GET /bi/report/preview`
- **Then** code=0 或 UI 含 报表预览


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径；**2026-10-04 走查 #21 对齐**报表域 IA 重构）

## US-BI-01 浏览报表目录（报表管理）

### TC-IMS-BI-01-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17 / #21。
- **When** 用户按故事主路径操作（页面 `biList`：分类树 + 卡片/列表双视图；[+ 新建报表]/[编辑] 进设计器）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一；侧栏「数据报表」= **2 叶**。

## US-BI-02 设计报表布局（隐藏路由）

### TC-IMS-BI-02-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17 / #21。
- **When** 用户按故事主路径操作（页面 `biDesign` · 隐藏路由 `/ims/bi/report/designer`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一；设计器**不出侧栏**。

## US-BI-03 打开 M6 标准报表（报表中心）

### TC-IMS-BI-03-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17 / #21。
- **When** 用户按故事主路径操作（页面 `bi0Report` · 菜单名「报表中心」）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一。

## US-BI-04 配置数据大屏（报表类型 dashboard）

### TC-IMS-BI-04-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17 / #21。
- **When** 用户按故事主路径操作（页面 `biList` · 新建抽屉报表类型选「大屏」= `reportType=DASHBOARD`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一；`go('bi0Screen')` **归一化到 `biList`**（独立「大屏配置」菜单退役）。

## US-BI-05 预览报表结果

### TC-IMS-BI-05-01-01 P0 主路径

- **Given** BI/BI0 规格；走查 #17。
- **When** 用户按故事主路径操作（页面 `biPreview`）
- **Then** 列表/图表有 seed 或标准空态；筛选条统一。

