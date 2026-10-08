# CHECKLIST-IMS-DC — 穿透查询（P1）

> **关联**：[SLICES-IMS-DC-穿透查询](./SLICES-IMS-DC-穿透查询.md)

---

## 1. 范围

- [ ] 仅 DC-001 菜单叶；P2/P3/P4 不在本 Checklist
- [ ] **未**引用 OPS「线索挖掘」未文档化 API

## 2. P1 UI

- [ ] 六种 entryType 搜索联想
- [ ] 模式 GRAPH | DETAIL（+ AGGREGATE 若契约启用）
- [x] 结果区展示 queryCostMs；>3000ms 警示（#52/#53）
- [x] 数据截至时间戳（BR-210）（#52）
- [ ] 节点/chip 下钻 → 再次 query（无新 REST）（非场次节点仍待做）
- [x] 场次节点/明细行 → `GET /dc/trace/detail/{sessionCode}`（#53）
- [ ] R7 成本字段渲染为 — / ***（SELF 范围 API 已脱敏；角色矩阵 UI 未单测）

## 3. API §2.1

- [x] entry / query / detail / export 与契约 DTO 一致（#52 entry+query · #53 detail+export）
- [x] 1181 超时降级文案（日期跨度 >92 天）
- [x] 1504 场次不存在/不可见拒绝（与利润反查同口径）

## 4. 测试

- [ ] TESTCASES-IMS-DC P0 100%
