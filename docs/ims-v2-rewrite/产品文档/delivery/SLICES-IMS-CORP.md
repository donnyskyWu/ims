# SLICES-IMS-CORP — 公司资产

> **版本**：v1.0 | 2026-10-01  
> **规格 SSOT**：《CORP-公司资产-页面规格.md》《CORP-公司资产-API契约.md》《ACCT-平台账号采集Tab-OPS对齐.md》  
> **BLOCKED**：办公/直播设备分页（`dict_asset_type`）、领用 L3 入口 Q3、VA 扩展列

---

## 1. 切片总览

| Slice | 目标 | 依赖 |
|-------|------|------|
| S-IMS-C-01 | 平台账号 5 L3 + 详情含采集 Tab | ADR-047 · M4 OPS |
| S-IMS-C-02 | 资源管理 R1～R4 | MASTER/UX-M4 |
| S-IMS-C-03 | 设备管理三 L3（只读/空态） | **BLOCKED** API 就绪前仅 IA+空态 |

---

## 2. S-IMS-C-01 平台账号

**路由**：`/ims/corp/account/{platform}`  
**API**：`GET /corp/account/page`（platformType 固定）、详情、采集 Tab 下游 OPS  
**验收**：AccountSelect 铁律；采集 Tab ≠ COLLECT P2a

---

## 3. S-IMS-C-02 资源

公司/实名人/手机卡/证件 — 透传 OPS internal/* 或 MASTER 契约

---

## 4. S-IMS-C-03 设备（条件）

**BLOCKED 写路径**：直至 CORP API §设备 BLOCKED 解除；Checklist 仅验收空态与 hint
