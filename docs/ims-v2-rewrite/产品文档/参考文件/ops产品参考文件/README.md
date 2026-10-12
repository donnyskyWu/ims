# 运营数据分析平台 - AI 驱动开发文档体系

> **项目**：运营数据分析平台（oa-module）
> **方法论**：[AI 驱动产品开发方法论](./AI驱动产品开发方法论-产品经理指南.md)
> **PRD 单一事实源**：[完整PRD-v9.2-开发版.md](../完整PRD-v9.2-开发版.md)（业务摘要：[PRD-业务版-v9.2.md](./product/PRD-业务版-v9.2.md)）
> **AI 规则**：[AGENTS.md](../AGENTS.md)
> **当前状态**：v9.2 + M2/M4 OPS 实现同步（2026-10-02）
> **更新时间**：2026-10-02
> **OPS 文档对齐报告**：[`delivery/OPS-DOC-SYNC-20261002.md`](./delivery/OPS-DOC-SYNC-20261002.md)  
> **OPS UX SSOT**：[`product/UX-OPS-设计规范.md`](./product/UX-OPS-设计规范.md) · [`product/UX-OPS-页面原型索引.md`](./product/UX-OPS-页面原型索引.md)

---

## 1. 文档体系（按方法论 L0~L5 分层）

### L0 业务澄清（BRD）

> 一期暂无独立 BRD 文件，业务背景已合并到主 PRD `## 1. 产品概述`。
> 后续按需补充：`docs/product/BRD-{专题}.md`

### L1 PRD-AI（产品需求规格）

| 模块 | 文档 | 详细设计 | 状态 |
|------|------|----------|------|
| 运营管理 | [PRD-M1-运营管理.md](./product/PRD-M1-运营管理.md) | 5.1~5.7 | ✅ 试点完成 |
| 内容生产 | [PRD-M2-内容生产.md](./product/PRD-M2-内容生产.md) + [工作任务 PRD](./product/PRD-M2-工作任务管理.md) | [5.8~5.12](../完整PRD-v9.2-开发版.md#5-功能详细设计) | ✅ M2 + FR-M2-010 已对齐代码 |
| 绩效核算 | PRD-M3-绩效核算.md | 5.13~5.16 | 📋 待生成 |
| 账号管理 | [PRD-M4-账号管理.md](./product/PRD-M4-账号管理.md) | 5.17~5.23 | ✅ v1.3 实现同步（ADR-078） |
| 财务管理 | PRD-M5-财务管理.md | 5.24~5.25 | 📋 待生成 |
| 数据分析 | PRD-M6-数据分析.md | 5.26~5.32 | 📋 待生成 |
| 作品监测 | PRD-M7-作品监测.md | 5.33~5.37 | 📋 待生成 |
| 配置管理 | PRD-M8-配置管理.md | （内嵌） | 📋 待生成 |
| 系统管理 | PRD-M9-系统管理.md | （内嵌） | 📋 待生成 |
| 数据采集 | PRD-M10-数据采集.md | 5.40~5.41 | 📋 待生成 |
| 首页 | PRD-M0-首页.md | 5.0 | 📋 待生成 |

### L2 UX Spec（页面矩阵 + 状态矩阵）

| 模块 | 文档 | 状态 |
|------|------|------|
| **OPS 跨模块** | [UX-OPS-设计规范.md](./product/UX-OPS-设计规范.md) · [UX-OPS-页面原型索引.md](./product/UX-OPS-页面原型索引.md) | ✅ 2026-10-02 |
| 运营管理 | [UX-M1-运营管理.md](./product/UX-M1-运营管理.md) | ✅ 试点完成 |
| 内容生产 | [UX-M2-内容生产.md](./product/UX-M2-内容生产.md)（含 P-M2-016 工作任务） | ✅ 2026-10-02 修订 |
| 账号管理 | [UX-M4-账号管理.md](./product/UX-M4-账号管理.md) | ✅ 2026-10-02 修订 |
| 其他 | ... | 📋 待生成 |

### L3 技术规格

| 文档 | 状态 |
|------|------|
| [TECH-CONSTRAINTS.md](./engineering/TECH-CONSTRAINTS.md) | ✅ |
| [API-M1-运营管理.md](./engineering/API-M1-运营管理.md) | ✅ 试点完成 |
| [API-M2-内容生产.md](./engineering/API-M2-内容生产.md) · [API-M2-工作任务管理.md](./engineering/API-M2-工作任务管理.md) | ✅ M2 路径 SSOT 2026-10-02 |
| [API-M4-账号管理.md](./engineering/API-M4-账号管理.md) | ✅ v1.2 2026-10-02 |
| [STATE-M1-运营管理.md](./engineering/STATE-M1-运营管理.md) | ✅ 试点完成 |
| 其他模块 API / STATE | 📋 待生成 |

### L4 切片计划（SLICES）

| 文档 | 切片数 | 状态 |
|------|--------|------|
| [SLICES-M1-运营管理.md](./delivery/SLICES-M1-运营管理.md) | 11 片 | ✅ 试点完成 |
| 其他模块 | - | 📋 待生成 |

### L5 验收包

| 文档 | 状态 |
|------|------|
| [CHECKLIST-M1-运营管理.md](./delivery/CHECKLIST-M1-运营管理.md) | ✅ 试点完成 |
| [TESTCASES-M1-运营管理.md](./delivery/TESTCASES-M1-运营管理.md) | ✅ 试点完成 |
| 其他模块 | 📋 待生成 |

### ADR（架构/产品决策记录）

存放于 `docs/adr/`，命名：`ADR-NNN-描述.md`

| 编号 | 标题 | 状态 |
|------|------|------|
| ADR-001 | 中间件简化（移除 Redis/RabbitMQ/MinIO/XXL-JOB） | ✅ |
| ADR-M1-001 | 补录数据与 API 冲突时优先用哪个 | ✅ |
| ADR-M1-002 | IP 组删除保护策略 | ✅ |
| ADR-M1-003 | 人效盘点时间维度 | ✅ |
| 其他 | ... | 📋 待补充 |

---

## 2. 试点模块（M1 运营管理）文档清单

| 层级 | 文档 | 路径 | 状态 |
|------|------|------|------|
| L1 | PRD-AI | [PRD-M1-运营管理.md](./product/PRD-M1-运营管理.md) | ✅ |
| L2 | UX 规格 | [UX-M1-运营管理.md](./product/UX-M1-运营管理.md) | ✅ |
| L3 | API 规格 | [API-M1-运营管理.md](./engineering/API-M1-运营管理.md) | ✅ |
| L3 | 状态机规格 | [STATE-M1-运营管理.md](./engineering/STATE-M1-运营管理.md) | ✅ |
| L3 | 技术约束 | [TECH-CONSTRAINTS.md](./engineering/TECH-CONSTRAINTS.md) | ✅ |
| L4 | 切片计划 | [SLICES-M1-运营管理.md](./delivery/SLICES-M1-运营管理.md) | ✅ |
| L5 | 开发自检 | [CHECKLIST-M1-运营管理.md](./delivery/CHECKLIST-M1-运营管理.md) | ✅ |
| L5 | 测试用例 | [TESTCASES-M1-运营管理.md](./delivery/TESTCASES-M1-运营管理.md) | ✅ |
| - | AI 规则 | [AGENTS.md](../AGENTS.md) | ✅ |

**试点完成度**：M1 模块 8 个文档齐全。

---

## 3. 工作流（参考方法论 § 4）

```
1. 业务澄清（BRD/PRD § 1）
   ↓
2. PRD-AI 起草（PRD-*.md）
   ↓
3. AI 反问与缺口扫描（PRD § 9 Open Questions）
   ↓
4. UX/AC/数据规格补齐（UX-*.md / API-*.md / STATE-*.md）
   ↓
5. 切片与闸门评审（SLICES-*.md 签字）
   ↓
6. 分片驱动 AI 实现（按 Slice，五段式 Prompt）
   ↓
7. 验收测试与发布（CHECKLIST + TESTCASES）
   ↓
[不通过] → 回到 3
[通过] → 下一片 / 交付归档
```

---

## 4. 下一步建议

### 4.1 立即可做

- [ ] 阅读 [AGENTS.md](../AGENTS.md) 了解 AI 操作规则
- [ ] 阅读 [TECH-CONSTRAINTS.md](./engineering/TECH-CONSTRAINTS.md) 了解技术栈
- [ ] 跑通 M1 模块的 SLICES-S-01（IP 组树 + 详情骨架）
- [ ] 用五段式 Prompt 让 AI 实现 S-01

### 4.2 一周内完成

- [ ] 生成 M2（内容生产）全套 8 个文档
- [ ] 生成 M4（账号管理）全套 8 个文档
- [ ] 完成 M1 的 S-01 ~ S-04 切片实现

### 4.3 两周内完成

- [ ] 生成剩余 8 个模块（PRD / UX / API / STATE / SLICES / CHECKLIST / TESTCASES）
- [ ] 完成 M1 全部 11 个切片实现
- [ ] 启动集成测试

### 4.4 三周内完成

- [ ] 集成测试通过
- [ ] UAT 验收
- [ ] 发布预发环境

---

## 5. 文档维护规范

### 5.1 更新时机

| 情况 | 更新内容 |
|------|----------|
| PRD 内容变更 | 同步更新 UX / API / STATE / TESTCASES |
| 新增/删除功能 | 更新 SLICES（增删切片） |
| 状态机变化 | 更新 STATE-*.md + CHECKLIST |
| API 接口变更 | 更新 API-*.md + TESTCASES |
| 业务规则变化 | 更新 PRD § 4 业务规则 + ADR |
| 技术决策变化 | 新增/更新 ADR |

### 5.2 命名规范

- PRD / UX / API / STATE / SLICES / CHECKLIST / TESTCASES 文件名：`{类型}-M{模块编号}-{模块名}.md`
  - 例：`PRD-M1-运营管理.md`、`API-M4-账号管理.md`
- ADR 文件名：`ADR-NNN-{描述}.md`（NNN 为 3 位序号）
- 通用规范：使用中文文件名，避免特殊字符

### 5.3 同步机制

每次 PRD/UX/API 变更，需在同一 PR 中同步更新关联文档，并在 PR 描述中列出：
- 变更文件清单
- 影响范围（哪些 AC、哪些切片）
- 回归测试范围

---

## 6. 联系与反馈

- **产品经理**：许清楚
- **技术负责人**：齐活林
- **方法论作者**：齐活林

---

*文档体系 v1.0 | 最后更新 2026-10-02 | L1 SSOT：完整PRD-v9.2-开发版.md*
