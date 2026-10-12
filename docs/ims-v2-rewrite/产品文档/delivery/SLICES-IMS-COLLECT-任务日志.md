# SLICES-IMS-COLLECT — 采集任务与日志（M10）

> **版本**：v1.0 | 2026-10-01  
> **范围**：**仅** P5 采集任务、P5b 采集日志（核验 §8 Slice 4）  
> **规格 SSOT**：《COLLECT-数据采集-页面规格.md》§P5/P5b、《COLLECT-数据采集-API契约.md》§1  
> **凭证 SSOT**：ADR-047 · 《ACCT-平台账号采集Tab-OPS对齐.md》— **本切片不做** Cookie/bind UI

---

## 1. 切片总览

| Slice | 目标 | API |
|-------|------|-----|
| S-IMS-CL-01 | 任务列表与 CRUD | `/collect/task/page`、CRUD、`/run` |
| S-IMS-CL-02 | 统一任务成员 | `POST /collect/task/ensure-unified` |
| S-IMS-CL-03 | 日志列表与详情 | `/collect/log/page`、`/log/{id}` |

---

## 2. S-IMS-CL-01 任务

**路由**：`/ims/collect/task`  
**验收**：编辑抽屉 **无 Cookie**；单账号用 AccountSelect；Channel-D 用外部配置 id

---

## 3. S-IMS-CL-03 日志

**路由**：`/ims/collect/log`  
**验收**：`typeResults[]`；失败链至账号采集 Tab（accountId 深链）

---

## 4. 依赖

- S-IMS-C-01 平台账号与采集 Tab（bind 状态影响任务警告）
- M8 外部配置 seed（Channel-D 任务）
