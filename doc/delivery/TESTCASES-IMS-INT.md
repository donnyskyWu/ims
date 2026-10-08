# TESTCASES-IMS-INT — 内部分析

## TC-P0-01

- **Given** R4 已登录
- **When** `GET .../work/page`
- **Then** code=0 或 UI 含 内部作品


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-MON-01 维护 IP 主题与行业监测维度

### TC-IMS-MON-01-01 P0 主路径

- **Given** MON P1；M7 阈值只读 COLLECT。
- **When** 用户按故事主路径操作（页面 `mon`）
- **Then** 列表可筛；与内部分析/竞品阈值引用一致。

## US-INT-01 查看内部作品表现

### TC-IMS-INT-01-01 P0 主路径

- **Given** M1/M7 数据；INT P1。
- **When** 用户按故事主路径操作（页面 `intWork`）
- **Then** 分页有数；Tab 切换即过滤。

## US-INT-02 查看内部账号表现

### TC-IMS-INT-02-01 P0 主路径

- **Given** INT P2。
- **When** 用户按故事主路径操作（页面 `intAccount`）
- **Then** 列表与权限内数据一致。

