# 阶段开发方法与规则

> **版本**：v1.0 | 2026-06-09  
> **性质**：本项目 **AI 驱动 + 阶段 Gate** 的执行 SSOT  
> **来源**：[`AI驱动产品开发方法论-产品经理指南.md`](../../AI驱动产品开发方法论-产品经理指南.md) + [`MASTER-EXECUTION-TRACKER.md`](../delivery/MASTER-EXECUTION-TRACKER.md) + [`QUALITY-GATES.md`](./QUALITY-GATES.md) + [`AI-IMPL-GUIDE.md`](./AI-IMPL-GUIDE.md)

---

## 1. 核心结论（一句话）

> **规格先行 → 切片实现 → 模块 Checklist → 阶段 Gate → 方可进入下一阶段。**  
> AI 是受 Spec 约束的执行者，不是会猜需求的同事；**Gate 未通过 = 禁止继续**。

---

## 2. 双层闸门模型

本项目同时运行 **两层闸门**，缺一不可：

```
┌─────────────────────────────────────────────────────────────┐
│ L1  规格闸门（AI 方法论 · 开发前）                            │
│     业务澄清 → PRD → 缺口扫描 → UX/API/SLICES → 人批准       │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ L2  实现闸门（Slice · 每片）                                 │
│     五段式 Prompt → 实现 → CHECKLIST → TESTCASES P0 → 合并   │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ L3  阶段 Gate（MASTER-EXECUTION-TRACKER · 每阶段）           │
│     模块 100% + Seed + 自动化 + 回归 → Gate 报告 → Sign-off  │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
                      解锁下一阶段 S{n+1}
```

| 层级 | 触发时机 | 通过标准 | SSOT 文档 |
|------|---------|---------|-----------|
| **L1 规格闸门** | 写代码前 | Open Questions 关闭；SLICES 已批准 | PRD · SLICES · ADR |
| **L2 Slice 闸门** | 每个 Slice 结束 | CHECKLIST 100%；P0 用例绿 | CHECKLIST-M* · TESTCASES-M* |
| **L3 阶段 Gate** | S0–S7 每阶段末 | MASTER-EXECUTION-TRACKER 对应 § 全绿 | MASTER-EXECUTION-TRACKER |

---

## 3. AI 方法论 → 本项目阶段映射

| AI 方法论七阶段 | 本项目落地 | 产物 |
|----------------|-----------|------|
| 1 业务澄清 | PRD 第 0 章 + In/Out of Scope | `完整PRD-v9.1-开发版.md` |
| 2 PRD-AI | 模块 PRD + FR/AC 编号 | `docs/product/PRD-M*.md` |
| 3 缺口扫描 | ADR + Open Questions 关闭 | `docs/adr/ADR-*.md` |
| 4 规格补齐 | UX + API + STATE + TECH | `docs/engineering/API-M*` 等 |
| 5 切片评审 | SLICES 批准 | `docs/delivery/SLICES-M*.md` |
| 6 分片实现 | **S0–S7 按 Gate 顺序 + Slice PDCA** | 代码 + 测试 |
| 7 验收发布 | **GATE-S7 + 九条 E2E** | Gate 报告 · UAT |

**本项目特有约束**（在 AI 方法论之上）：

- 阶段 **S0→S7 顺序不可逆**（依赖 M4 枢纽、seed-analytics 硬门槛等）
- **M10 / 外部 SSO** 为 Phase 2，不得在本期 Slice 中实现
- **鉴权**：Dev Token + DB 真实权限（[ADR-003](../adr/ADR-003-模拟鉴权与外部平台SSO对接.md)），禁止 Mock 权限逻辑

---

## 4. 阶段开发方法（PDCA × 切片 × Gate）

### 4.1 进入阶段前（Plan）

1. 确认 **上一 Gate 已 ✅**（查 [`MASTER-EXECUTION-TRACKER`](../delivery/MASTER-EXECUTION-TRACKER.md) §1）
2. 读取本阶段模块的 **5 份 Spec**：PRD · API · STATE · SLICES · TESTCASES
3. 确认本阶段 **Seed 包**计划（如 S1 末 seed-assets）
4. AI 输出 **实现计划**（文件列表 + Slice 顺序），人确认后再写代码

### 4.2 阶段内开发（Do）

- **一次只做一片 Slice**（新会话或清晰边界，避免上下文污染）
- 使用 [`AI-IMPL-GUIDE.md`](./AI-IMPL-GUIDE.md) **五段式 Prompt**
- 用 `@docs/...` 引用 Spec，**禁止**在聊天中重复粘贴长 PRD
- Spec 未写明 → **停止**，输出「阻塞问题清单」，**禁止推断补全**
- 每片完成后：**Slice CHECKLIST** → **TESTCASES P0** → 再开下一片

### 4.3 阶段末验收（Check）

按 [`MASTER-EXECUTION-TRACKER`](../delivery/MASTER-EXECUTION-TRACKER.md) 对应 GATE-S{n} 章节逐项勾选：

```
开发交付 100%
  → 模块 CHECKLIST-M* 100%
  → TESTCASES-M* P0 100%
  → SeedVerificationIT + 人工抽检
  → 自动化（mvn verify / playwright）
  → 上一阶段 P0 回归仍绿
  → 填写 Gate 报告 + Sign-off
  → 更新进度表 §1 → ✅
```

### 4.4 不通过时（Act）

| 情况 | 动作 |
|------|------|
| Slice 失败 | 开「修复 Slice」，带 FR/AC + 复现步骤 + 限定文件范围 |
| Gate 任一项 ❌ | 登记阻塞表 §13，**整段 Gate 重跑**，不得带伤进下一阶段 |
| Spec 错误 | **先改 Spec + ADR**，再改代码（Spec 优先于代码） |

---

## 5. 规则提炼（强制执行）

### 5.1 规格与范围（L1）

| ID | 规则 |
|----|------|
| **R-S01** | Spec 未明确的内容 **不得实现**；必须输出阻塞问题清单 |
| **R-S02** | 未在 Spec 中的 API / 字段 / 页面 / 按钮 **不得新增** |
| **R-S03** | Out of Scope（含 M10、登录页、外部 SSO）**不得在本期实现** |
| **R-S04** | Open Questions 未关闭 **不得开始对应 Slice** |
| **R-S05** | SLICES 未经批准 **不得开始实现** |
| **R-S06** | 业务决策变更 **必须先写 ADR**，再改 Spec，最后改代码 |

### 5.2 切片实现（L2）

| ID | 规则 |
|----|------|
| **R-I01** | **一片一会话**；禁止单次 Prompt 跨多个 Slice |
| **R-I02** | 实现前必须 `@` 引用 PRD / API / SLICES / TECH-CONSTRAINTS |
| **R-I03** | 使用五段式 Prompt（见 AI-IMPL-GUIDE） |
| **R-I04** | 改动不得超出当前 Slice 范围；禁止顺手改无关模块 |
| **R-I05** | Slice 完成 = CHECKLIST 100% + TESTCASES P0 100% |
| **R-I06** | 5 大铁律必守：选择器 / 字典 / 租户 / AES / 错误码 1500–1504 |
| **R-I07** | 高风险的权限、状态机、计费逻辑 **优先 TDD**（先测后实现） |
| **R-I08** | Bug 修复必须引用 FR/AC + 限定文件 + 跑回归用例 |

### 5.3 阶段 Gate（L3）

| ID | 规则 |
|----|------|
| **R-G01** | **S0→S7 顺序不可逆**；禁止跳阶段 |
| **R-G02** | **上一 Gate 未 ✅，禁止启动下一阶段开发** |
| **R-G03** | 涉及模块必须 **CHECKLIST-M* 100%** |
| **R-G04** | **TESTCASES-M* P0 必须 100% 通过** |
| **R-G05** | 每阶段 **seed-* 必验证**（SeedVerificationIT + 抽检） |
| **R-G06** | 新 Gate 通过后，**历史 P0 冒烟不得回退** |
| **R-G07** | Gate 失败项记入阻塞表；修复后 **整段 Gate 重跑** |
| **R-G08** | Gate 通过必须归档 **`gates/GATE-S{n}-报告-{日期}.md`** 并更新进度表 |
| **R-G09** | **硬门槛**：S1 末 M4 五选择器 100%；S6 前 seed-analytics 就绪 |
| **R-G10** | S3 起前端联调 **`VITE_USE_MOCK=false` + Dev Token** |

### 5.4 鉴权与数据（横切）

| ID | 规则 |
|----|------|
| **R-A01** | 用户/租户/权限 **从 DB 读取**（seed-auth）；禁止 Mock 权限逻辑 |
| **R-A02** | 禁止业务代码 **硬编码 userId / tenantId** |
| **R-A03** | `@PreAuthorize` **必须生效**；Dev Token 仅替代登录来源 |
| **R-A04** | M6 报表/大屏数据来自 **seed-analytics**，不得依赖 M10 |

---

## 6. 阶段 × 必做动作速查

| 阶段 | 模块 | 必过 Gate 项 | 硬门槛 |
|------|------|-------------|--------|
| **S0** | Auth · Seed 框架 | AUTH-004 · HelloWorld 200 | — |
| **S1** | M4 | CHECKLIST-M4 §10 五选择器 | ★ 五选择器 100% |
| **S2** | M8 · M9 | AUTH-001~005 · seed-auth | — |
| **S3** | M1 | seed-ops · 真实 API | 切 Mock off |
| **S4** | M2 | seed-content · 三审 E2E | — |
| **S5** | M3 | seed-perf · 归因链 | — |
| **S6** | M5·M6·M7 | seed-analytics 先于 M6 | ★ 报表非空 |
| **S7** | M0 | 九条 E2E · UAT | 全量发布 |

---

## 7. 反模式（禁止）

| 反模式 | 后果 | 对应规则 |
|--------|------|---------|
| 整份 PRD 一次做完 | 全面偏差 | R-I01 |
| 细节后面再补 | AI 固化错误假设 | R-S01 |
| Gate 未过开下一阶段 | 错误级联放大 | R-G01 · R-G02 |
| 模块无 Checklist 即合并 | 输出不可信 | R-G03 |
| 跳过 Seed 验证 | 报表/联调空数据 | R-G05 |
| Mock 权限 / 硬编码用户 | Phase 2 全量重写 | R-A01 · R-A02 |
| 修 Bug 不引 AC | 修 A 坏 B | R-I08 |
| Spec 与代码不同步 | 人与 AI 失忆 | R-S06 |

---

## 8. 文档与规则索引

| 类型 | 路径 |
|------|------|
| 本文（方法 SSOT） | `docs/engineering/PHASE-DEV-METHOD.md` |
| 进度与 Gate Checklist | `docs/delivery/MASTER-EXECUTION-TRACKER.md` |
| 排期与范围 | `docs/delivery/BACKEND-WORK-PLAN-v1.2-已批准.md` |
| AI 五段式 Prompt | `docs/engineering/AI-IMPL-GUIDE.md` |
| 质量门控 | `docs/engineering/QUALITY-GATES.md` |
| Cursor 规则 | `.cursor/rules/phase-gate-protocol.mdc` |
| Cursor 规则 | `.cursor/rules/spec-driven-impl.mdc` |
| 产品经理方法论 | `AI驱动产品开发方法论-产品经理指南.md` |

---

## 9. 每次开工自检（30 秒）

- [ ] 当前阶段 Gate 前置已 ✅？
- [ ] 本 Slice 已在 SLICES 中批准？
- [ ] 5 份 Spec 已 `@` 引用？
- [ ] Out of Scope 已确认不碰？
- [ ] 完成后知悉：CHECKLIST → P0 → Gate 报告？

---

*维护：Gate 规则变更时同步更新本文 §5 与 `.cursor/rules/`。*
