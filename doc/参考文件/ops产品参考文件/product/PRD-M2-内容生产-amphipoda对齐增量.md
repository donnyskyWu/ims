# PRD-M2-内容生产 — amphipoda 玩法对齐增量

> **业务域**：M2 内容生产  
> **增量 FR**：FR-M2-011  
> **版本**：v1.0 | 2026-08-31  
> **状态**：**Accepted**（产品 Owner 2026-08-31 确认）  
> **父文档**：[`PRD-M2-内容生产.md`](./PRD-M2-内容生产.md)  
> **关联 ADR**：[ADR-076](../adr/ADR-076-OPS内容生产amphipoda玩法与matchScheme对齐.md) · [ADR-077](../adr/ADR-077-SOP内容生成节点文档类型与登记自动草稿AI.md)（空玩法 AI + 自动首写）

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| Slice | S-20 |
| 约束 | **仅改 OPS 前后端**；不改 member-server / jingcai 服务 |
| 权限 | 沿用现有内容生产菜单（不变） |

---

## 1. 概述

### 1.1 一句话

OPS 内容编辑页对齐 Football「发布方案」：**N 场绑定、竞彩玩法 JSON、Tab 切换、jingcai AI 生成/润色、Football 方案双写**。

### 1.2 目标

| 维度 | 目标 |
|------|------|
| 一致性 | OPS 保存的方案与 amphipoda 发布方案 **同构** `matchScheme` |
| 效率 | 合并执行任务 **一次预填全部赛程** |
| 质量 | AI 生成使用与发布方案 **同一 jingcai.article** 底层 |
| 流程 | SOP / 二级审核 / ext 桥接 **不变** |

---

## 2. 范围

### 2.1 In Scope

| 编号 | 名称 | 优先级 |
|------|------|--------|
| **FR-M2-011-1** | 内容编辑 — N 场 + 玩法选择 UI（amphipoda 全量 Tab） | P0 |
| **FR-M2-011-2** | 内容存储 — `matchScheme` / `matchType` SSOT | P0 |
| **FR-M2-011-3** | Football sync — 全量 `match_scheme` + `match_type` | P0 |
| **FR-M2-011-4** | AI — jingcai 首生成 + 润色（上下文注入） | P0 |
| **FR-M2-011-5** | 任务/合并组 — 预填 N 场赛程（玩法手动） | P0 |

### 2.2 Out of Scope

1. ❌ 修改 member-server / jingcai 服务代码  
2. ❌ OPS 主流程调用 member `generateAiScheme`  
3. ❌ 下架或改造 `#/release/amphipoda`（双入口并存，ADR-054 §7）  
4. ❌ 传足/北单 **自动**从任务推断玩法  
5. ❌ 一期不做 amphipoda 高级售卖字段（`visibleType` 等，ADR-054 §8.6）

---

## 3. 功能需求

### FR-M2-011-1 玩法选择 UI

#### 描述

`ContentEditPanel` 替换单场 `MatchSelectDialog` + `dict_scheme_type` 为主入口，嵌入与 amphipoda 等价的：

- Tab：竞足 / 传足 / 北单 / 足球（`matchType` 1/2/3/4）
- 每 Tab 下选 N 场、选玩法、设主玩法
- 删除场、编辑玩法、发布前校验（复用 amphipoda 校验语义）

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-011-1 | 用户选竞足 Tab | 选 2 场并分别选玩法 | `matchScheme` 含 2 项且各有 `matchPlays` |
| AC-M2-011-2 | 传足 Tab | 选场次 ≠ 套餐要求 | 提示场次不足/过多，**不可** AI 生成 |
| AC-M2-011-3 | 已选 ≥1 场无玩法 | 点 AI 生成 | **允许**调用 jingcai（ADR-077 D10；玩法可选）。无场次则不可生成 |

---

### FR-M2-011-2 数据存储

#### 描述

- 1 篇内容 ↔ **N 场**，SSOT = `match_scheme_json` + `match_type`
- `competition_id` / `competition_name` = **首场摘要**（列表展示、兼容旧 API）
- `scheme_type`（`dict_scheme_type`）**不再必填**；UI 可隐藏或仅 AI 润色辅助

#### 验收标准

| AC | Then |
|----|------|
| AC-M2-011-4 | create/update 持久化完整 `matchScheme` JSON |
| AC-M2-011-5 | 回显编辑页正确还原 Tab、场次、玩法、主玩法 |
| AC-M2-011-6 | 存量仅 `competition_id` 的内容可打开；保存前不强制补玩法（只读浏览） |

---

### FR-M2-011-3 Football 双写

#### 描述

保持 ADR-054 模式：create/update → `FootballArticleBridgeService` → `author_article`。

- `match_scheme`：**全量 JSON**（非 stub）
- `match_type`：与编辑页 Tab 一致
- sync 失败不阻断 OPS 保存（§9.2 不变）

#### 验收标准

| AC | Then |
|----|------|
| AC-M2-011-7 | 保存后 ext.`author_article_id` 对应行 `match_scheme` 非 stub |
| AC-M2-011-8 | 更新玩法后 resync 覆盖 Football 侧玩法 |
| AC-M2-011-14 | OPS 内容 **无** `matchScheme`（null/未填） | Football sync | Feign 传 `matchScheme=[]`；member 校验通过；OPS 保存不阻断 |

---

### FR-M2-011-4 AI 生成与润色

#### 描述

- **首生成 + 润色**：均走 OPS `POST /ops/ai-content/generate` → jingcai.article（默认）
- 首生成：`events[]` = 当前 `matchScheme` 全量映射
- 润色（round≥2）：OPS 将 `conversationHistory` + 上一轮 assistant 正文写入 `writing.requirements`
- 采纳：ADR-054 §6.2 用户选写入付费/免费栏。**例外**：工作任务 confirm 自动首写见 [ADR-077](../adr/ADR-077-SOP内容生成节点文档类型与登记自动草稿AI.md) D11
- 请求上下文可带 `isPaywall`（不落库）；`matchPlays` 可空
- 降级：`sys_param ai.content.chat-via-jingcai=false` → M8 直连 LLM（已有）

#### 验收标准

| AC | Then |
|----|------|
| AC-M2-011-9 | 2 场已选玩法 → 首生成 jingcai 请求含 2 个 Event |
| AC-M2-011-10 | 第 2 轮润色 → requirements 含第 1 轮对话摘要 |
| AC-M2-011-11 | 无 `authorId` → 400「作者 ID 不能为空」 |

---

### FR-M2-011-5 任务与合并组预填

#### 描述

- 自任务创建内容：`task.competition_ids_json`（或合并组全部赛事）→ **预填 N 行赛程**
- **不预填** `matchPlays`；用户进入编辑页 **手动选玩法**
- 合并执行任务：须带齐组内 **全部** 赛事

#### 验收标准

| AC | Then |
|----|------|
| AC-M2-011-12 | 合并 2 场 task → 内容编辑预填 2 场队名/scheduleId |
| AC-M2-011-13 | 预填 ≥1 场后即可 AI（玩法可空，ADR-077）；无场次不可 AI |

---

## 4. 非功能

| 项 | 要求 |
|----|------|
| 租户 | 全表 `tenant_id` 隔离 |
| 鉴权 | 现有内容生产权限 |
| 性能 | jingcai 轮询沿用现有 600s 超时 |
| 兼容 | 旧内容可读；新流程强制 matchScheme 才 AI/上架（见 UX） |

---

## 5. 依赖

| 依赖 | 说明 |
|------|------|
| ADR-076 | 架构 SSOT |
| ADR-054 | 双写 / 双正文 |
| ADR-075 | 合并组 `competition_ids_json` |
| M8 | AI 降级路径 |
| Gateway | 赛程只读 API（已有） |

---

## 6. 关联文档

- UX：[`UX-M2-内容生产-amphipoda对齐增量.md`](./UX-M2-内容生产-amphipoda对齐增量.md)
- API：[`API-M2-内容生产-amphipoda对齐增量.md`](../engineering/API-M2-内容生产-amphipoda对齐增量.md)
- Slice：[`SLICES-M2-S20-amphipoda对齐.md`](../delivery/SLICES-M2-S20-amphipoda对齐.md)
