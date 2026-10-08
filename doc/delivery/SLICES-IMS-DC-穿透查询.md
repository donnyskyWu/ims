# SLICES-IMS-DC — 穿透查询（DC-001）

> **版本**：v1.0 | 2026-10-01  
> **规格 SSOT**：《DC-数据中心-页面规格.md》P1、《DC-数据中心-API契约.md》§2.1  
> **路由**：`/ims/dc/trace`（数据分析 → 穿透查询）  
> **BLOCKED**：线索挖掘 SSOT、DC-002/003 非本切片

---

## 1. 切片总览

| Slice | 目标 | API |
|-------|------|-----|
| S-IMS-DC-01 | 入口搜索 | `GET /dc/trace/entry` |
| S-IMS-DC-02 | 链路/明细查询 | `POST /dc/trace/query` |
| S-IMS-DC-03 | 场次明细与导出 | `GET detail/{sessionCode}`、`GET export` |
| S-IMS-DC-04 | 性能埋点展示 | queryCostMs；1181 超时提示 |

---

## 2. 约束

- 逐层下钻：**重复** `POST /dc/trace/query`（新 entryType/entryId）；**禁止** graph 专用 API
- 只读；R7/R9 成本脱敏

---

## 3. 依赖

- seed-analytics 宽表；V3 聚合层同步（规格 BR-210 新鲜度）
