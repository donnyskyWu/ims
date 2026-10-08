# TESTCASES-IMS-MEET — 会议日报

## TC-P0-01

- **Given** R4 已登录
- **When** `POST /meet/daily/submit`
- **Then** code=0 或 UI 含 日报提交


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-MEET-01 预约并记录会议

### TC-IMS-MEET-01-01 P0 主路径

- **Given** MEET 会议菜单。
- **When** 用户按故事主路径操作（页面 `meet`）
- **Then** 会议列表可见；参与人收到待办（若配置）。

## US-MEET-D01 撰写并提交我的日报

### TC-IMS-MEET-D01-01-01 P0 主路径

- **Given** MEET 日报四叶；与 REPORT 分离。
- **When** 用户按故事主路径操作（页面 `dailyMine`）
- **Then** 状态与工作台待办一致；退回后再现待办。

## US-MEET-D02 查看团队日报

### TC-IMS-MEET-D02-01-01 P0 主路径

- **Given** MEET 日报四叶；与 REPORT 分离。
- **When** 用户按故事主路径操作（页面 `dailyTeam`）
- **Then** 状态与工作台待办一致；退回后再现待办。

## US-MEET-D03 审阅下属日报

### TC-IMS-MEET-D03-01-01 P0 主路径

- **Given** MEET 日报四叶；与 REPORT 分离。
- **When** 用户按故事主路径操作（页面 `dailyReview`）
- **Then** 状态与工作台待办一致；退回后再现待办。

## US-MEET-D04 查看日报提交率

### TC-IMS-MEET-D04-01-01 P0 主路径

- **Given** MEET 日报四叶；与 REPORT 分离。
- **When** 用户按故事主路径操作（页面 `dailyStat`）
- **Then** 状态与工作台待办一致；退回后再现待办。

## US-FLOW-01 处理跨模块审批待办

### TC-IMS-FLOW-01-01 P0 主路径

- **Given** FLOW V2。
- **When** 用户按故事主路径操作（页面 `flow`）
- **Then** 单据状态更新；来源模块待办同步。

