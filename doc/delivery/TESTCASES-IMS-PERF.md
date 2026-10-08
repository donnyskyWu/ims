# TESTCASES-IMS-PERF — 绩效

## TC-P0-01

- **Given** R4 已登录
- **When** `GET /ops/perf/record/list`
- **Then** code=0 或 UI 含 七态字典


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-PERF-01 维护考核方案

### TC-IMS-PERF-01-01-01 P0 主路径

- **Given** PERF 四叶；OPS M3 对齐。
- **When** 用户按故事主路径操作（页面 `perfScheme`）
- **Then** 同周期同员工不重复（BR-031）；确认后只读。

## US-PERF-02 执行本期考核

### TC-IMS-PERF-02-01-01 P0 主路径

- **Given** PERF 四叶；OPS M3 对齐。
- **When** 用户按故事主路径操作（页面 `perfExec`）
- **Then** 同周期同员工不重复（BR-031）；确认后只读。

## US-PERF-03 员工查看考核结果

### TC-IMS-PERF-03-01-01 P0 主路径

- **Given** PERF 四叶；OPS M3 对齐。
- **When** 用户按故事主路径操作（页面 `perfResult`）
- **Then** 同周期同员工不重复（BR-031）；确认后只读。

## US-PERF-04 绩效考试组卷

### TC-IMS-PERF-04-01-01 P0 主路径

- **Given** PERF 四叶；OPS M3 对齐。
- **When** 用户按故事主路径操作（页面 `perfExam`）
- **Then** 同周期同员工不重复（BR-031）；确认后只读。

