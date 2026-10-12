# TESTCASES-IMS-COMP — 竞品分析

## TC-P0-01

- **Given** R4 已登录
- **When** `GET .../work/page`
- **Then** code=0 或 UI 含 segment ALL


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-COMP-01 浏览竞品作品全盘

### TC-IMS-COMP-01-01 P0 主路径

- **Given** COLLECT 外部数据；COMP P1。
- **When** 用户按故事主路径操作（页面 `compWork`）
- **Then** 全部 Tab 展示 segment=ALL；空库标准空态。

## US-COMP-02 分析竞品账号结构

### TC-IMS-COMP-02-01 P0 主路径

- **Given** COMP 账号 Tab。
- **When** 用户按故事主路径操作（页面 `compAccount`）
- **Then** Tab 过滤生效；分页正常。

## US-COMP-03 维护竞品库资产

### TC-IMS-COMP-03-01 P0 主路径

- **Given** V3 竞品库规格。
- **When** 用户按故事主路径操作（页面 `comp`）
- **Then** 库列表与 M7 消费数据一致。

