# TESTCASES-IMS-TRAIN — 培训

## TC-P0-01

- **Given** R4 已登录
- **When** `POST /train/material`
- **Then** code=0 或 UI 含 资料发布


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-TRAIN-01 发布培训资料

### TC-IMS-TRAIN-01-01-01 P0 主路径

- **Given** TRAIN 三叶。
- **When** 用户按故事主路径操作（页面 `trainMaterial`）
- **Then** 任务 completed；AI 卷 source=AI_DRAFT 有审计标记。

## US-TRAIN-02 派发学习任务

### TC-IMS-TRAIN-02-01-01 P0 主路径

- **Given** TRAIN 三叶。
- **When** 用户按故事主路径操作（页面 `trainTask`）
- **Then** 任务 completed；AI 卷 source=AI_DRAFT 有审计标记。

## US-TRAIN-03 查看培训完成率

### TC-IMS-TRAIN-03-01-01 P0 主路径

- **Given** TRAIN 三叶。
- **When** 用户按故事主路径操作（页面 `trainStat`）
- **Then** 任务 completed；AI 卷 source=AI_DRAFT 有审计标记。

