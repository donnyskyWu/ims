# CHECKLIST-IMS-BI0 — 自定义查询

> **关联**：[SLICES-IMS-BI0-自定义查询](./SLICES-IMS-BI0-自定义查询.md)

---

## 1. 范围

- [ ] 仅 P4 `/ims/bi/query`
- [ ] 元数据维护仍在 COLLECT P4m
- [x] W9-6：`bi0Metric` → `/ims/bi/metric`（`GET/POST/PUT/DELETE /bi/metric/*` · 试算 preview · 1262 引用阻断）

## 2. UI（对齐 UX-M6 P-M6-005 / 规格 §3）

- [ ] QueryBar + 已保存查询列表
- [ ] Builder：实体选择、条件、展示列
- [ ] 执行结果：列表|图表 Tab（对齐 BI0 原型深度要求）
- [ ] 发布供大屏 QUERY / 17b 引用（PUT publish）
- [ ] 1261 未映射 → 页脚链 P4m

## 3. API

- [ ] `/bi/query` CRUD
- [ ] `/bi/query/{id}/run` 返回分页结果 + 耗时
- [ ] `/bi/query/{id}/publish` 状态变更
- [ ] 只读读口 `/collect/metadata/entity/{code}/fields` 或 `/bi/metadata` 契约一致

## 4. 全局

- [ ] tenant 1504；权限 R1/R3/R4/R9 矩阵
- [ ] TESTCASES-IMS-BI0 P0 100%
