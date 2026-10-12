# UX-M2-内容生产 — AI 排版增量

> **版本**：v1.3 | 2026-09-17  
> **状态**：Accepted（2026-09-08；v1.2 入口修订 2026-09-09；v1.3 一键排版四套预设 2026-09-17）  
> **关联 PRD**：[PRD-M2-AI排版增量](./PRD-M2-AI排版增量.md)  
> **关联 ADR**：[ADR-028](../adr/ADR-028-M2-AI排版语义分段.md) · [ADR-027](../adr/ADR-027-M2-版式资源工作台.md)  
> **页面**：`ContentEditPanel` → 编辑器工具栏「AI 排版」按钮 → `AiTypesettingDialog` 弹窗

---

## 0. OPS 设计 SSOT

> **设计规范**：[`UX-OPS-设计规范.md`](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[`UX-OPS-页面原型索引.md`](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)（§1「Football 完整路由」优先于 standalone / 扁平路径）

## 1. 页面范围

| 页面/组件 | 变更 |
|-----------|------|
| `ContentEditPanel` | 工具栏：**「一键排版」**（规则预设）+ **「AI 排版」**（LLM 语义）；均位于「付费全屏」之后 |
| `WechatQuickTypesetDialog` | v1.3：**「一键排版」**主弹窗；四套 football-layout 预设，无 LLM |
| `AiTypesettingDialog` | v1.2：**「AI 排版」**弹窗；LLM 语义分段 + AUTO/TEMPLATE_GUIDED |
| `LayoutResourceSidebar` | v1.2 **移除「一键排版」Tab**，仅保留样式/模板 Tab |
| 内容审核 `LayoutViewer` | **不变**（只读渲染 apply 后的 `layout_html`） |

**不变**：模板库 CRUD、样式库 Tab、手动「选择版式模板」按钮（FR-M2-005）、AI 内容抽屉（ADR-053）。

---

## 2. 编辑器工具栏「AI 排版」弹窗（v1.2）

### 2.1 布局（原 ADR-027/028 工作台 Tab 3，v1.2 迁至弹窗）

```
工具栏：[免费全屏] [付费全屏] [一键排版] [AI 排版] [展开/收起版式工作台]
                              ↑ 规则预设（无 LLM）  ↑ LLM 语义排版
┌─ AI 排版（AiTypesettingDialog 弹窗）───────────┐
│ ◉ AI 排版（推荐）    ○ 规则排版（备选/legacy）   │  ← Segmented；默认 AI
├───────────────────────────────────────────────┤
│ 智能选版说明（只读）                             │  ← AUTO 固定；football-layout 内置两模板
│        AI 按正文语义自动选择决策扫读版或情报分析版   │
├───────────────────────────────────────────────┤
│ [AI 排版预览]                                   │
├───────────────────────────────────────────────┤
│ （预览后展开）                                  │
│ ┌─ 对比 ─────────────────────────────────┐   │
│ │ [排版前]  [排版后]     ← el-tabs          │   │
│ │  iframe / LayoutViewer 渲染              │   │
│ └────────────────────────────────────────┘   │
│ 分段摘要：标题×1 · 比赛头×2 · 推荐列表×1 …      │
│ AUTO 时显示：已选版式「决策扫读版」/「情报分析版」  │
│ （低置信度时）提示：内容特征接近，已使用决策扫读版   │
│ （mappingDegraded 时）⚠ 部分段落已降级映射        │
│ [取消]  [应用排版]                              │
└───────────────────────────────────────────────┘
```

### 2.2 控件定义

| 控件 ID | 类型 | 说明 |
|---------|------|------|
| `SEG-TYPESET-MODE` | `el-segmented` | `AI`（默认）/ `RULE`（ADR-027 规则链，**备选/legacy**） |
| `TXT-AUTO-TEMPLATE-INFO` | 只读 `el-alert` | AI 排版固定 `AUTO`；**不展示**公推模板库选择器（`TEMPLATE_GUIDED` 仅 API 保留，UI 不暴露） |
| `BTN-AI-PREVIEW` | Primary 按钮 | 「AI 排版预览」；loading 调 preview API |
| `TAB-COMPARE` | `el-tabs` | 排版前 / 排版后 |
| `VIEW-BEFORE` | `LayoutViewer` 或纯文本 | 当前 `layout_html`；无版式时显示 `body` 纯文本 |
| `VIEW-AFTER` | `LayoutViewer` | preview 返回的 `layoutHtml` |
| `TXT-SEGMENT-SUMMARY` | 只读文本 | `segmentationReport` 人类可读摘要 |
| `TXT-SELECTED-TEMPLATE` | 只读 | AUTO 且 preview 成功后显示 football-layout 模板名（决策扫读版 / 情报分析版） |
| `TXT-TEMPLATE-CONFIDENCE` | `el-alert` info | AUTO 且 `templateDecision.confidence=LOW` 时显示「内容特征接近，已使用决策扫读版；可手动选择其他模板重新预览」 |
| `TXT-MAPPING-DEGRADED` | `el-alert` warning | `mappingDegraded=true` 时显示降级摘要 |
| `BTN-AI-APPLY` | Primary | preview 成功后 enabled；已有版式 → confirm |
| `BTN-CANCEL` | Default | 关闭预览区 |

---

## 2.3 工具栏「一键排版」弹窗（v1.3 · `WechatQuickTypesetDialog`）

```
┌─ 一键排版 ─────────────────────────────────────┐
│ 选择风格（卡片列表，默认「竞彩营销版」）           │
│  ○ 竞彩营销版  ○ 简洁通读版                      │
│  ○ 赛事分析版  ○ 付费引流版                      │
├───────────────────────────────────────────────┤
│ [排版预览 iframe]                               │
│ ℹ 规则分段 + football-layout 内置模板，无需 AI   │
├───────────────────────────────────────────────┤
│ [取消]  [使用此排版]                             │
└────────────────────────────────────────────────┘
```

| 控件 ID | 说明 |
|---------|------|
| `CARD-QUICK-STYLE` | 四套预设；选中后自动刷新预览 |
| `VIEW-PREVIEW` | 调用 `POST /typeset` · `mode=FOOTBALL_AI`；付费/免费分区预览 |
| `BTN-QUICK-APPLY` | 写回对应编辑器；有免费+付费时分别 typeset |

| # | 规则 |
|---|------|
| Q1 | 与 AI 排版相同：`ARTICLE` 且非只读；标题或任一侧正文非空方可打开 |
| Q2 | **不调用 LLM**；预览失败提示重试，不 fallback 到 AI 排版 |
| Q3 | 「赛事分析版」不传 `footballTemplate`，由后端 AUTO 在决策扫读版/情报分析版间二选一；预览区展示已选模板名 |
| Q4 | 「付费引流版」仅对 **免费区** 传 `paramOverrides.paidBoundary=true` |
| Q5 | 应用后通过 `layoutSync` 同步 `layout_json` / `layout_html`；正文纯文本 SSOT 不变 |

---

## 3. 交互规则（AI 排版弹窗）

| # | 规则 |
|---|------|
| U1 | 仅 `content_type=ARTICLE` 且非只读时显示「一键排版」「AI 排版」按钮（v1.2 起工作台 Tab 已移除） |
| U2 | `body`（或 `layout_html` 提取纯文本）与 `free_body` 均为空 → `BTN-AI-PREVIEW` **disabled**，tooltip「请先输入正文」 |
| U3 | AI 排版 **固定 AUTO**；不展示公推模板库选择器；预览后展示已选 football-layout 内置版式名 |
| U4 | Preview 成功后才展示对比区与「应用排版」 |
| U5 | 已有 `body_format=LAYOUT` 点「应用排版」→ `MessageBox.confirm`「将覆盖当前版式，正文文字不会改动」 |
| U6 | Apply 成功 → 主编辑器刷新付费 `layout_html`；有免费内容时同步刷新免费编辑器；`body_format=LAYOUT`；Toast「AI 排版已应用到免费/付费内容」 |
| U7 | Preview/Apply 失败 **2037** → Alert「排版结果与原文不一致，已拒绝；请重试或联系管理员」 |
| U8 | **2039** →「AI 分段失败，请稍后重试」 |
| U9 | **2042** →「内置 football-layout 版式不可用，请稍后重试或联系管理员」 |
| U10 | Preview 进行中弹窗 **不可关闭**（防中断） |
| U11 | `mappingDegraded=true` → 展示 `TXT-MAPPING-DEGRADED`；仍允许 apply（用户知悉降级） |
| U12 | AUTO 返回 `confidence=LOW` → 展示 `TXT-TEMPLATE-CONFIDENCE`；仍允许 apply；提示可调整正文后重新 preview |

---

## 4. 流程

### 4.1 TEMPLATE_GUIDED（用户选模板）

```
用户选模板 → 点「AI 排版预览」
  → POST preview { mode: TEMPLATE_GUIDED, templateId }
  → 展示对比 + 分段摘要
  → 用户点「应用排版」
  → POST apply { ... overwrite }
  → 编辑器刷新
```

### 4.2 AUTO（不选模板 · football-layout 智能排版）

```
模板选择器留空 → 点「AI 排版预览」
  → POST preview { mode: AUTO }
  → 后端：semantic-parser → template-decision（decision-scan | analysis-report）
  → 展示对比 + 「已选版式：决策扫读版/情报分析版」+ 分段摘要
  → （若有）降级映射 warning
  → apply 同上
```

### 4.3 与 AI 内容抽屉衔接

```
AiContentDrawer 采纳正文 → body 有内容
  → 用户点工具栏「AI 排版」
  → （可选）选模板 → 预览 → 应用
```

---

## 5. 规则排版（Legacy · ADR-027 · 备选）

选择 `SEG-TYPESET-MODE = RULE` 时，展示 ADR-027 原有 UI：

- 规则勾选（`oa_typesetting_rule`）
- `mode=TEMPLATE` / 规则链 `AUTO`（**非** AI AUTO / football-layout 管线）

**默认** landing 在 AI 排版。规则链 **保留为备选**；产品后续按 AI 效果决定是否下线。

---

## 6. 空态与错误

| 场景 | 展示 |
|------|------|
| 正文为空 | 按钮 disabled + tooltip |
| 无 ENABLED 模板（TEMPLATE_GUIDED） | 模板选择器提示无可用模板 |
| AUTO 2042 | 选中的内置 seed/schema 不可用；preview 返回 2042 + U9 文案 |
| mappingDegraded | warning alert + 仍可 apply |
| 无 `oa:content:typeset` 权限 | 「AI 排版」按钮隐藏或编辑器只读 |
| 内容非 ARTICLE | 不展示「AI 排版」按钮 |

---

## 7. 无障碍与性能

| 项 | 约定 |
|----|------|
| Preview loading | 按钮 loading + 「AI 正在分析正文结构…」 |
| 超时 | >60s 提示「处理时间较长，请稍后重试」 |
| 对比区 | 排版后可滚动；移动端侧栏全屏（沿用 ADR-021 全屏逻辑） |

---

*Accepted · 2026-09-08 · v1.2 入口修订 · 2026-09-09 · v1.3 一键排版四套预设 · 2026-09-17*
