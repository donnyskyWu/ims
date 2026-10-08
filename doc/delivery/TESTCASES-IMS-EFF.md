# TESTCASES-IMS-EFF — 组织人效

## TC-P0-01

- **Given** R4 已登录
- **When** `GET /eff/board`
- **Then** code=0 或 UI 含 看板Tab


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-IPG-01 建立 IP 组并绑定成员与作者

### TC-IMS-IPG-01-01 P0 主路径

- **Given** 组织与用户已同步；IPG P1。
- **When** 用户按故事主路径操作（页面 `ipg`）
- **Then** 组启用；下游 AccountSelect / 数据范围可用（BR-305）。

## US-EFF-01 查看组织人效看板

### TC-IMS-EFF-01-01 P0 主路径

- **Given** EFF V3；依赖 IPG/任务/COST。
- **When** 用户按故事主路径操作（页面 `eff`）
- **Then** 三 Tab 可切换；卡片与列表有 seed。

