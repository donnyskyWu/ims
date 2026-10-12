# TESTCASES-IMS-CONTENT — 内容生产

> **故事 SSOT**：`产品PRD/IMS-业务用户故事-B-内容采集分析.md` US-CONTENT-*

## TC-P0-01（遗留 smoke）

- **Given** R4 已登录
- **When** `GET /content/sop/list`
- **Then** code=0 或 UI 含 SOP列表

---

> **业务故事映射**（2026-10-01 · P0 主路径）

## US-CONTENT-01 工作任务到审核通过闭环

### TC-IMS-CONTENT-01-01 P0 主路径

- **Given** SOP/计划已配置；CONTENT-OPS 补充规格。
- **When** 用户按故事主路径操作（页面 `contentWork`）
- **Then** 任务已审；内容管理可见终稿；打回待办再现。

## US-CONTENT-02 维护 SOP 模板

### TC-IMS-CONTENT-02-01 P0 主路径

- **Given** CONTENT SOP 菜单可见。
- **When** 用户按故事主路径操作（页面 `contentSop`）
- **Then** SOP 列表状态正确；计划页可引用已发布 SOP。

## US-CONTENT-03 制定内容计划

### TC-IMS-CONTENT-03-01 P0 主路径

- **Given** 存在已发布 SOP。
- **When** 用户按故事主路径操作（页面 `contentPlan`）
- **Then** 计划列表可见；可下发工作任务。

## US-CONTENT-04 执行人处理我的任务

### TC-IMS-CONTENT-04-01 P0 主路径

- **Given** 存在待执行工作任务。
- **When** 用户按故事主路径操作（页面 `contentTask`）
- **Then** 跳转任务执行全页；列表状态为执行中/待提审。

## US-CONTENT-08 任务执行全页填写并提审

### TC-IMS-CONTENT-08-01 P0 主路径

- **Given** 从 my task 进入；CONTENT 执行页规格 ADR-IMS-003 §5。
- **When** 用户按故事主路径操作（页面 `contentTaskExecute`）
- **Then** 任务 status=待审；审核队列可见。

## US-CONTENT-05 内容库维护终稿

### TC-IMS-CONTENT-05-01 P0 主路径

- **Given** 至少一条已审内容 seed。
- **When** 用户按故事主路径操作（页面 `contentList`）
- **Then** 列表分页；状态与审核结果一致。

## US-CONTENT-06 公推模板库选用版式

### TC-IMS-CONTENT-06-01 P0 主路径

- **Given** Layout 模板 seed。
- **When** 用户按故事主路径操作（页面 `contentLayout`）
- **Then** 模板可选列表；任务执行页可载入版式。

## US-CONTENT-07 审核员队列处理

### TC-IMS-CONTENT-07-01 P0 主路径

- **Given** 待审任务存在。
- **When** 用户按故事主路径操作（页面 `contentReview`）
- **Then** 任务状态更新；工作台待办清除。
