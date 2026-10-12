# TESTCASES-IMS-REPORT — 数据上报

## TC-P0-01

- **Given** R4 已登录
- **When** `POST /report/submit`
- **Then** code=0 或 UI 含 1127去重


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-REPORT-01 填报并提交运营数据

### TC-IMS-REPORT-01-01-01 P0 主路径

- **Given** REPORT 三叶；author+account 必填。
- **When** 用户按故事主路径操作（页面 `reportSub`）
- **Then** 提交后进审核；作者变更清空账号下拉。

## US-REPORT-02 维护上报模板

### TC-IMS-REPORT-02-01-01 P0 主路径

- **Given** REPORT 三叶；author+account 必填。
- **When** 用户按故事主路径操作（页面 `reportTpl`）
- **Then** 提交后进审核；作者变更清空账号下拉。

## US-REPORT-03 查看上报完成率

### TC-IMS-REPORT-03-01-01 P0 主路径

- **Given** REPORT 三叶；author+account 必填。
- **When** 用户按故事主路径操作（页面 `reportRate`）
- **Then** 提交后进审核；作者变更清空账号下拉。

