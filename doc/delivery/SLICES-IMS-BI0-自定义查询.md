# SLICES-IMS-BI0 — 自定义查询（P4）

> **版本**：v1.0 | 2026-10-01  
> **规格 SSOT**：《BI0-指标查询报表-页面规格.md》§3、《BI0-指标查询报表-API契约.md》#4～6  
> **元数据 SSOT**：COLLECT P4m · `/collect/metadata/entity/{code}/fields`  
> **路由**：`/ims/bi/query`（数据分析组下「自定义查询」L3，走查 #17）

---

## 1. 切片总览

| Slice | 目标 | API |
|-------|------|-----|
| S-IMS-B0-01 | QueryBuilder 列表/编辑 | GET/POST/PUT `/bi/query` |
| S-IMS-B0-02 | 执行与发布 | POST `/bi/query/{id}/run`、PUT publish |
| S-IMS-B0-03 | 未映射实体引导 | 1261 → 链 COLLECT P4m |

---

## 2. 依赖

- COLLECT P4m 至少一实体 seed（seed-analytics）
- **非**本切片：八张标准报表、指标管理 P1/P2

---

## 3. 验收要点

- 只读消费实体字段；**禁止**页内元数据 CRUD
- 1262 超时异步卡（规格允许 P1 接线）
