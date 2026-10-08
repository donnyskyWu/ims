# CHECKLIST-IMS-DC — 穿透查询（P1）

> **关联**：[SLICES-IMS-DC-穿透查询](./SLICES-IMS-DC-穿透查询.md)

---

## 1. 范围

- [ ] 仅 DC-001 菜单叶；P2/P3/P4 不在本 Checklist
- [ ] **未**引用 OPS「线索挖掘」未文档化 API

## 2. P1 UI

- [ ] 六种 entryType 搜索联想
- [ ] 模式 GRAPH | DETAIL（+ AGGREGATE 若契约启用）
- [ ] 结果区展示 queryCostMs；>3000ms 警示
- [ ] 数据截至时间戳（BR-210）
- [ ] 节点/chip 下钻 → 再次 query（无新 REST）
- [ ] R7 成本字段渲染为 — / ***

## 3. API §2.1

- [ ] entry / query / detail / export 与契约 DTO 一致
- [ ] 1181 超时降级文案
- [ ] 1504 跨租户拒绝

## 4. 测试

- [ ] TESTCASES-IMS-DC P0 100%
