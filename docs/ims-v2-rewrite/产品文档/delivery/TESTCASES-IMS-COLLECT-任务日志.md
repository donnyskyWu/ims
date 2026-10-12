# TESTCASES-IMS-COLLECT — 任务与日志（P0）

---

## P5 任务

### TC-IMS-CL-001-01 创建单账号任务

- **Given** 已 bind 的 AccountSelect 账号  
- **When** POST 任务含 cron + 启用  
- **Then** 列表可见；`GET /task/page` 筛选项生效

### TC-IMS-CL-001-02 无 Cookie 字段

- **When** 打开任务编辑抽屉  
- **Then** **无** Cookie/Token 表单项

### TC-IMS-CL-001-03 立即执行

- **When** `POST /task/{id}/run`  
- **Then** 产生日志行；前端可带 taskId 打开 P5b

### TC-IMS-CL-001-04 Channel-D

- **When** 外部配置任务保存  
- **Then** body 含 collect_config_id；account_id 为 null

---

## P5b 日志

### TC-IMS-CL-002-01 详情 typeResults

- **Given** 日志 id  
- **When** `GET /log/{id}`  
- **Then** 返回 typeResults 数组；UI 可折叠展示

### TC-IMS-CL-002-02 失败深链

- **Given** 错误摘要含未绑定 Collector  
- **When** 用户点修复链接  
- **Then** 跳转公司资产账号详情 · 采集 Tab（带 accountId）

---

## ADR-047 边界

### TC-IMS-CL-003-01 竞品账号配置

- **When** 打开 `/ims/collect/external/account` 编辑  
- **Then** 无 Cookie 字段；Alert 指向 ACCT 采集 Tab


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-COLLECT-01 配置竞品账号采集

### TC-IMS-COLLECT-01-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectExtAccount`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

## US-COLLECT-02 配置竞品关键字采集

### TC-IMS-COLLECT-02-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectExtKeyword`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

## US-COLLECT-03 创建并执行采集任务

### TC-IMS-COLLECT-03-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectTask`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

## US-COLLECT-04 追溯采集日志

### TC-IMS-COLLECT-04-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectLog`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

## US-COLLECT-05 维护元数据实体映射

### TC-IMS-COLLECT-05-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectMetadata`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

## US-COLLECT-06 配置监测阈值规则

### TC-IMS-COLLECT-06-01-01 P0 主路径

- **Given** COLLECT 菜单；Cookie 仅公司资产账号详情采集 Tab（ADR-047）。
- **When** 用户按故事主路径操作（页面 `collectThreshold`）
- **Then** 配置/任务/日志态与规格一致；凭证修复后任务可成功。

