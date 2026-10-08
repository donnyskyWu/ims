# UX-M2-内容生产 — amphipoda 玩法对齐增量

> **版本**：v1.0 | 2026-08-31  
> **状态**：Accepted  
> **关联 PRD**：[PRD-M2-内容生产-amphipoda对齐增量](./PRD-M2-内容生产-amphipoda对齐增量.md)  
> **参考 UI**：`football-front/.../views/release/amphipoda.vue`（只读参照）

---

## 0. OPS 设计 SSOT

> **设计规范**：[`UX-OPS-设计规范.md`](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[`UX-OPS-页面原型索引.md`](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)（§1「Football 完整路由」优先于 standalone / 扁平路径）

## 1. 页面范围

| 页面 | 变更 |
|------|------|
| `ContentEditPanel` | **主改造**：玩法区替换单场选择器 |
| `AiContentDrawer` | 上下文展示改为 N 场摘要；逻辑不变 |
| 任务执行 → 创建/编辑内容 | 预填 N 场赛程 |
| 内容列表 | 赛事列显示「N 场」或首场摘要 |

**不变**：审核流、Football 上架状态展示、付费/免费双栏、公推模板、权限菜单。

---

## 2. 内容编辑 — 玩法区（替换原「关联赛事」+「方案分析类型」）

### 2.1 布局

```
┌─ 内容编辑 ─────────────────────────────────────┐
│ 标题 / 作者 / IP组 / 文档类型 …（现有）          │
├─ 赛事与玩法 ───────────────────────────────────┤
│ [竞足] [传足] [北单] [足球]     ← Tab          │
│ 日期 / 筛选 / 比赛列表（Tab 内）                 │
│ 已选 N 场 · 列表 + 玩法标签 + 主玩法 + 删除      │
│ [确定玩法] → 进入「已确认」态（panduan=true）   │
├─ 付费内容 / 免费内容（现有双栏）                 │
│ [AI 内容]  ← 玩法确认后可点                      │
└────────────────────────────────────────────────┘
```

### 2.2 Tab ↔ matchType

| Tab 标签 | matchType | 备注 |
|----------|-----------|------|
| 竞足 | 1 | 默认 |
| 传足 | 2 | 场次精确约束（radio 套餐） |
| 北单 | 3 | |
| 足球 | 4 | |

### 2.3 交互规则

| # | 规则 |
|---|------|
| U1 | 切换 Tab **清空**当前未确认玩法（与 amphipoda 一致） |
| U2 | 无场次时：AI 按钮 **disabled**，tooltip「请先选择比赛」 |
| U3 | 已选 ≥1 场：`matchScheme` 写入表单态；可 AI / 保存（玩法可选，ADR-077） |
| U4 | 至少 **1 场**即可 AI；`matchPlays` **可空**（ADR-077 D10 更新本条） |
| U5 | 传足 Tab：已选场次数须 **等于** 套餐要求场次数 |
| U6 | 删除场后若 0 场 → 回到未确认态 |

### 2.4 与原字段关系

| 原 UI | 新 UI |
|-------|-------|
| 单场 `MatchSelectDialog` | Tab + 多选列表 |
| `dict_scheme_type` 多选 | **隐藏**或折叠为「AI 辅助标签（可选）」 |
| 赛事单行 input | 已选场次卡片列表 |

---

## 3. 任务驱动 — 预填

### 3.1 合并执行任务（2+ 场）

```
任务执行页 → 创建内容
  → ContentEditPanel 打开
  → 玩法区预填 task.competitions[]（队名 + scheduleId）
  → matchPlays = 空
  → 顶部 Banner：「已从任务带入 N 场比赛，请为每场选择玩法后生成内容」
  → 用户手动点玩法 → 确定玩法 → AI
```

### 3.2 单场任务

预填 1 场，同样需手动选玩法。

---

## 4. AI 内容抽屉

### 4.1 信息参数区

| 标签 | 展示 |
|------|------|
| 赛事 | 「N 场」+ Tooltip 列出队名；或首场 + 「等 N-1 场」 |
| 作者 | 不变 |
| 方案分析类型 | 可选保留 dict 展示；**非**玩法 SSOT |

### 4.2 多轮润色

- 对话 UI **不变**（左侧历史 + 输入框）
- 用户感知：每轮独立等待 jingcai（loading 同现网）
- round≥2 时服务端自动带历史（用户无额外操作）

---

## 5. 列表与只读

| 场景 | 展示 |
|------|------|
| 内容列表「赛事」列 | `N场：曼联 VS 切尔西…` 或单场名 |
| 审核只读 | 玩法区只读展示 Tab + 场次 + 玩法摘要 |
| 存量无 matchScheme | 显示旧 `competitionName`；编辑时可补全 |

---

## 6. 错误与空态

| 场景 | 提示 |
|------|------|
| 无作者 | 「请先选择作者」（AI / jingcai 必填） |
| 无场次点 AI | 「请先选择比赛」（玩法不再作为 AI 前置，ADR-077） |
| 自动生成中/失败 | 内容编辑顶栏 Badge「生成中」/「失败」+ 原因 +「重试」（与任务执行页一致） |
| Football sync 失败 | 现有 ext 错误条 + 重试（不变） |
| jingcai 超时 | 「AI 生成超时，请重试」（600s） |

---

## 7. 组件复用策略

| 策略 | 说明 |
|------|------|
| P0 | 从 `views/release/amphipoda/components/*` **抽取**至 `#/components/ops/match-scheme/*` |
| P0 | OPS 与 amphipoda **共用**抽取后组件（避免双维护） |
| 禁止 | OPS 内联复制 1600 行 amphipoda.vue |

---

## 8. 线框引用

实现阶段对照现有截图目录：

- `docs/product/manual-screenshots/workflow/A12-content-list.png`
- `docs/product/manual-screenshots/workflow/A13-content-create-drawer.png`

新增走查项：N 场玩法区、合并任务预填 Banner（S-20 Gate 人工抽检）。
