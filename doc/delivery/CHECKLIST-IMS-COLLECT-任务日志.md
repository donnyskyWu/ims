# CHECKLIST-IMS-COLLECT — 任务与日志

> **关联**：[SLICES-IMS-COLLECT-任务日志](./SLICES-IMS-COLLECT-任务日志.md)

---

## 1. 范围

- [ ] 仅 P5/P5b；**未**在任务/日志页实现平台 Cookie 维护
- [ ] P2a 竞品账号配置 **无** Cookie 字段（ADR-052）

## 2. P5 任务

- [ ] 筛选：任务名/平台/方式/频率/状态
- [ ] 列含绑定对象、cron、上次/下次执行
- [ ] 新增/编辑：单账号 AccountSelect；统一任务成员；Channel-D `collect_config_id` 且 account_id null
- [ ] 编辑抽屉 **禁止** Cookie 控件
- [ ] 未 bind 账号保存任务 → 警告（可保存，执行失败符合 UX-M10）
- [ ] `POST /task/{id}/run` → 跳转日志带 taskId

## 3. P5b 日志

- [ ] 筛 task/account/状态/日期；含 PARTIAL
- [ ] 顶栏 24h 成功率（或占位接 quality API）
- [ ] 详情 `typeResults[]` 折叠
- [ ] Cookie 失效/未绑定 → 深链 **账号采集 Tab**（非 P2a）

## 4. API 对齐

- [ ] 契约 §1 六接口可用或 BFF 透传 OPS M10
- [ ] 1241～1250 错误码映射

## 5. 测试

- [ ] TESTCASES-IMS-COLLECT P0 100%
