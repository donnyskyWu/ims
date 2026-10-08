# TESTCASES-IMS-ALERT — 预警

## TC-P0-01

- **Given** R4 已登录
- **When** `GET /alert/rules`
- **Then** code=0 或 UI 含 规则列表


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-ALERT-01 配置并启用预警规则

### TC-IMS-ALERT-01-01 P0 主路径

- **Given** ALERT 首批规则。
- **When** 用户按故事主路径操作（页面 `alertRule`）
- **Then** 启用规则可在实时 Tab 产生 OPEN 事件。

## US-ALERT-02 值班处置实时预警

### TC-IMS-ALERT-02-01 P0 主路径

- **Given** 规则已启用；上游有信号。
- **When** 用户按故事主路径操作（页面 `alertLive`）
- **Then** status=RESOLVED/FALSE_ALARM；dedup 合并计数。

