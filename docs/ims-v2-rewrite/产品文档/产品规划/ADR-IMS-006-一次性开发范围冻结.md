# ADR-IMS-006：IMS 一次性开发范围冻结

> **状态**：**已冻结**  
> **日期**：2026-10-01（用户拍板）  
> **SSOT 需求**：《IMS完整产品需求文档.md》（全文 3A 功能点清单 + §16～§17 导航 + 各模块章）  
> **关联**：本 ADR · 《IMS-技术设计总册-20261001.md》

---

## 1. 决策

IMS **一次性交付**完整 PRD 范围：**不得缩小**《IMS完整产品需求文档》v2.6.16+ 已列模块与功能点；未在 PRD 标注 Out of Scope / Deferred 的能力 **默认 In Scope**。

切流与栈约束不变：`ADR-IMS-001`（共享 OPS 业务库、停 OPS HTTP）、`ADR-IMS-002`（Go + 轻量 Vue）、`ADR-IMS-003`（OPS 并入 UX SSOT）。

---

## 2. In Scope（模块 × 来源）

| 编号 | 模块 | PRD 锚点 | 建设类型 |
|------|------|----------|----------|
| 00 | 首页工作台 | HOME-001、AUTH-004 | 并入+扩展 |
| 01 | 权限 / 系统 | AUTH-001～003、SYS-001～007 | 用户共享 + SYS 自建 |
| 06 | 证件 + 实名人 | MASTER/CERT | 并入+扩展 |
| 07 | 资产 + 公司/设备 | MASTER/ASSET、CORP 设备 L3 | 并入+扩展 |
| 08 | 账号 | MASTER/ACCT、CORP 账号 L3 | 并入+扩展 |
| 08b | 账号财务 | COST / M5 | 并入 |
| 10 | 直播 | LIVE-001～004 | IMS 新建 |
| 15 | 内容生产 | CONTENT-001～110、OPS M2 | 并入+扩展 |
| 16 | 数据采集 | OPS M8/M10 | 并入 |
| 18 | 作品监测 / 内部分析 / 竞品 | MON、INT、COMPA + COMP V3 库叶 | 并入+重组 IA |
| 17a | 指标与自定义查询 | BI0 / M6 | 并入 |
| 17b | 自助报表 / 大屏 | BI | 新建增量 |
| 17c | 查询工具 | QT-001～011 | 新建 |
| 02 | 培训 | TRAIN-001～004（含 AI 出卷 v1） | IMS 新建 |
| 03 | 会议 / 日报 | MEET-001～004 | IMS 新建 |
| 09 | 数据上报 | REPORT-001～004 | IMS 新建 |
| 05 | 绩效考试 | PERF + OPS M3 | 并入+扩展 |
| 13 | 预警 | ALERT + OPS 规则 | 新建框架+并入 |
| 14 | 工作流 | FLOW-001～004 | IMS 新建 |
| 11 | 场次财务 | FIN | IMS 新建（V3 先行） |
| 04 | 竞品管理流程 | COMP-001～003（工作台/待办入口） | 新建流程 |
| 12 | 穿透查询 | DC-001+ | IMS 新建 |
| 19a/b | IP 组 / 组织人效 | IPG、EFF | 并入+扩展 |
| 20 | AI 资源中台 | AIR 四叶 In Scope（知识库 v2.6.31 由 Deferred 恢复） | 新建+收编 OPS AI 配置 |

**OPS M0～M10** 能力均须在 IMS 内等价提供（IR-03），交互以 ADR-IMS-003 引用的 OPS UX/PRD 为准。

---

## 3. Explicit Non-Goals（仅 PRD 已写明）

| 项 | PRD 依据 |
|----|----------|
| C 端 App/H5 会员交易、Football 方案前台、支付清结算引擎 | §1.2 **不做** |
| 线下培训报名计划（未写入 V2 TRAIN） | §02 TRAIN IA |
| AIR **Key 管理 / 审计监控** 两菜单 | §20 走查 #14 **Deferred**（知识库 v2.6.31 已恢复交付） |
| 租户套餐、独立数据权限 L3 | §01 走查 #15 |
| Phase 2：M10 采集替代方案外的 **外部 SSO 登录页重构** | 阶段 Gate 协议 Out of Scope |
| 长期双写 OPS 进程 | ADR-IMS-001 / IR-03 |

**禁止**在本 ADR 外新增 Non-Goal 以砍 PRD 功能点；缺口用 **IMS 设计 SSOT**（契约/ADR）补齐，不得静默发明 HTTP。

---

## 4. 验收口径

- 模块 Slice：`一体化管理/delivery/` 下 SLICES + CHECKLIST 100% + TESTCASES P0 100%。  
- 整系统 Gate：仍按 `MASTER-EXECUTION-TRACKER` 阶段 S0～S7；本 ADR **不替代** Phase Gate，仅冻结 **产品范围**。

---

## 5. 引用

- 《IMS-技术设计总册-20261001.md》  
- 《IMS-PRD与原型完整性核验-20261001.md》§「2026-10-01 拍板」
