# TESTCASES-IMS-LIVE — 直播管理

## TC-P0-01

- **Given** R4 已登录
- **When** `POST /live/register`
- **Then** code=0 或 UI 含 19位场次ID


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-LIVE-01 登记直播场次并完成 Football 同步

### TC-IMS-LIVE-01-01 P0 主路径

- **Given** 公司资产账号/设备可选；LIVE-001～002。
- **When** 用户按故事主路径操作（页面 `live`）
- **Then** 列表 19 位场次 ID；直播数据 Tab 展示 sync 态、**房间基本信息 + 计数（含观看人数 `viewer_count`）取自 `live_room` DB 只读**；GMV/峰值等不由 HTTP 冒充（走 **下播录入 LIVE-002**）。

