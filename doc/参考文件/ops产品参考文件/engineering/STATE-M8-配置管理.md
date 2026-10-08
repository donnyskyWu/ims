# STATE-M8-配置管理

> **版本**：v2.1 | 2026-06-11
> **ADR**：[`ADR-014`](../adr/ADR-014-M8-配置管理数据模型.md)

---

## 1. 配置启用状态

`dict_config_status`：ENABLED ↔ DISABLED。无复杂状态机。

## 2. 连接状态

`dict_conn_status`：DISCONNECTED → CONNECTED（测试成功后更新）。

适用：订单采集、AI 模型。

## 3. AI 默认模型

- 同时仅一条 `is_default=1`
- 设新默认时取消旧默认
- 默认模型不可删除

## 4. 提示词版本

新增 v1；每次编辑 version 数字 +1（v2, v3…）。

## 5. 阈值优先级

账号覆盖 > 全局阈值（粉丝/作品/预警各自独立）。

## 6. 业务规则

- **BR-M8-001**：INTERNAL 账号标识租户内唯一（建议）
- **BR-M8-002**：奥创配置每租户一条
- **BR-M8-003**：跨租户 → 1504
- **BR-M8-004**：默认 AI 模型删除 → 业务错误
- **BR-M8-005**：CSV 导入 ≤5MB
- **BR-M8-006**：内部采集平台 Tab 的 `accountId` 必须关联 M4 `oa_account`（与账号管理·平台账号同源）；列表 join 展示 `accountName`
- **BR-M8-007**：企业微信 Tab 不走 `oa_collect_config`，复用 `oa_wework_account` + `/oa/internal/wework/*`
- **BR-M8-008**：个人微信 Tab 仅展示 `oa_aocreate_api`，无内部采集账号列表
- **BR-M8-009**：外部账号列表过滤 `subType=account`；平台枚举 `dict_third_platform`（非 `dict_platform_type`）

---

## 字典引用

| 字段 | dict-type |
|------|-----------|
| status | dict_config_status |
| connStatus | dict_conn_status |
| thresholdCategory | dict_threshold_category |
| syncMode | dict_sync_mode |
| matchType | dict_match_type |
| externalPlatform | dict_third_platform（外部账号 Tab） |
| internalPlatform | dict_platform_type（内部平台 Tab / 关键词） |
