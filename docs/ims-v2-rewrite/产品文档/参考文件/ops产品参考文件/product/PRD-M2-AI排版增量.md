# PRD-M2-内容生产 — AI 排版增量

> **业务域**：M2 内容生产  
> **增量 FR**：FR-M2-012  
> **版本**：v1.2 | 2026-09-17  
> **状态**：**Accepted**（2026-09-08 产品决策关闭 OQ-M2-012-01~03；v1.2 同步一键排版 FOOTBALL_AI 与 V204 预设）  
> **父文档**：[`PRD-M2-内容生产.md`](./PRD-M2-内容生产.md)  
> **关联 ADR**：[ADR-028](../adr/ADR-028-M2-AI排版语义分段.md) · [ADR-020](../adr/ADR-020-M2-公推模板版式套用语义.md) · [ADR-027](../adr/ADR-027-M2-版式资源工作台.md)

---

## 0. 元信息

| 字段 | 值 |
|------|---|
| Slice | S-21a（已批准；详见 `docs/delivery/SLICES-M2-S21a-AI排版.md`） |
| 依赖 | S-14c（`LayoutMergeService` + apply/preview）、S-15~17（版式资源工作台）、M8 系统「AI 模型配置」OpenAI-compatible LLM |
| 权限 | 沿用 `oa:content:typeset`（ADR-027） |

---

## 1. 概述

### 1.1 一句话

内容创作者在 ARTICLE 编辑页，对已有正文执行 **AI 排版**：系统基于 **语义分段** 理解正文结构，按用户所选模板（或自动选模板）生成富版式 `layout_html`，**不改一字**。

AI 排版语义分段使用系统「AI 模型配置」中的 Chat Completion LLM；`jingcai.article` 保持为 AI 文案首生成/润色能力，二者职责分离且不互相 fallback。

### 1.2 目标

| 维度 | 目标 |
|------|------|
| 保真 | 排版前后 `body` 纯文本 **完全一致**（ADR-020） |
| 智能 | 识别标题、比赛头、推荐列表、分析段等 **语义块**，非规则链 |
| 灵活 | 用户 **可选** 公推模板库模板（`TEMPLATE_GUIDED`）；不选则 **AUTO** — football-layout 智能排版（内置两模板自动决策） |
| 一致 | 编辑/审核/查看同一套服务端渲染 |

### 1.3 非目标

- ❌ AI 改写、润色、补全正文  
- ❌ 135/秀米集成  
- ❌ 自然语言调字号/颜色（Phase 2）  
- ❌ 短视频等非 ARTICLE 类型  

---

## 2. 范围

### 2.1 In Scope

| 编号 | 名称 | 优先级 |
|------|------|--------|
| **FR-M2-012-1** | AI 排版 — 模板引导模式（`TEMPLATE_GUIDED`） | P0 |
| **FR-M2-012-2** | AI 排版 — 自动模式（`AUTO`） | P0 |
| **FR-M2-012-3** | 正文保真校验（Fidelity Gate） | P0 |
| **FR-M2-012-4** | 排版预览 + 确认应用 | P0 |
| **FR-M2-012-5** | football-layout 语义 taxonomy 对齐 | P0 |
| **FR-M2-012-6** | 映射降级 + styleHints（Phase 1.5+） | P0（降级）/ P1（styleHints） |
| **FR-M2-012-7** | 一键排版 — football-layout 规则预设（`FOOTBALL_AI`） | P0 |

### 2.2 Out of Scope

1. ❌ 替换/删除 ADR-027 规则链排版 UI（**保留 legacy 备选**；AI 排版为默认；产品后续按 AI 效果决策）  
2. ❌ 模板 CRUD 变更（仍走 FR-M2-005）  
3. ❌ 发布管线只发纯文本（仍 Phase 2 / M10）  

---

## 3. 用户故事

| ID | 角色 | 故事 | 优先级 |
|----|------|------|--------|
| US-M2-012-1 | 内容创作者 | 我写完足球分析正文后，希望一键 AI 排版成公众号风格，且 **不改动我的原文** | P0 |
| US-M2-012-2 | 内容创作者 | 我想 **指定某套模板** 排版，让 AI 按该模板的版式结构分段映射 | P0 |
| US-M2-012-3 | 内容创作者 | 我不确定用哪套模板，希望系统 **按正文语义自动选择** 决策扫读版或情报分析版并排版（football-layout 智能排版） | P0 |
| US-M2-012-4 | 审核人 | 我审核时看到的排版效果与创作者 AI 排版后一致 | P0 |
| US-M2-012-5 | 运营管理者 | 团队排版风格统一，且基于标准模板库而非每人手工调样式 | P1 |
| US-M2-012-6 | 内容创作者 | 我写完正文后，希望 **不调用 LLM** 也能一键套用竞彩/通读/分析/引流四套公众号预设 | P0 |

---

## 4. 功能需求

> **入口区分（v1.2）**：**「AI 排版」** = LLM 语义分段（`/typeset/ai-semantic/*`，FR-M2-012-1~6）；**「一键排版」** = 规则分段 + football-layout 内置 PRESET（`POST /typeset` · `mode=FOOTBALL_AI`，FR-M2-012-7）。二者共用 `LayoutMergeService` 与正文保真铁律，**不**互相 fallback。

### FR-M2-012-1 模板引导模式（TEMPLATE_GUIDED）

#### 描述

用户在 AI 排版入口 **从公推模板库选择模板**（`templateId`），系统：

1. 读取模板 `layout_schema`（槽位/块结构）
2. LLM 将正文解析为 `SemanticSegment[]`（taxonomy 见 ADR-028 §2.4）
3. 将各段映射到 schema 槽位
4. `LayoutMergeService` 生成 `layout_json` / `layout_html`

#### 前置条件

- 内容 `content_type=ARTICLE`
- 正文非空（`body` 或从 `layout_html` 提取的纯文本）
- 模板 `status=ENABLED` 且 `document_type` 与内容匹配（或模板 `document_type` 为空）

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-1 | ARTICLE 有 body，用户选 ENABLED 模板 | 执行 AI 排版 preview | 返回 `layoutHtml`；`fidelityCheck.passed=true` |
| AC-M2-012-2 | preview 成功 | 用户确认 apply | `body` **字符串不变**；`body_format=LAYOUT`；`layout_template_id=templateId` |
| AC-M2-012-3 | 模板 `document_type` 与内容不匹配 | 请求 TEMPLATE_GUIDED | 错误 **1501** |
| AC-M2-012-4 | body 为空 | 请求 AI 排版 | 错误 **2036** |

---

### FR-M2-012-2 自动模式（AUTO）

#### 描述

用户 **不选模板**（`templateId` 为空），系统走 **`docs/football-layout/SKILL.md` 管线 SSOT**：

1. **语义解析** — LLM + `shared/semantic-parser.md` → `SemanticSegment[]`
2. **模板决策** — `FootballTemplateDecider` 在 **内置两模板** 间二选一（基于内容语义，**非** DB 模板库 catalog 扫描）：
   - `decision-scan`（决策扫读版）
   - `analysis-report`（情报分析版）
3. **参数 + 映射 + merge** — 对应内置 seed 模板的 `layout_schema` → `LayoutMergeService` → 输出

响应须含 `selectedTemplateId` / `selectedTemplateName` / `selectedFootballTemplate`（`decision-scan` | `analysis-report`）供 UI 展示。

最终模板由服务端按 ADR-028 §2.4.1 的固定特征、权重与阈值评分，LLM 不直接选择模板。分差不足 2（同分或差 1）时固定回退 `decision-scan` 并标记低置信度。

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-5 | 正文为足球分析类 | AUTO preview | 返回 `selectedFootballTemplate` ∈ {`decision-scan`,`analysis-report`} + `layoutHtml` |
| AC-M2-012-6 | 语义解析失败，或选中内置 seed/schema 不可用 | AUTO preview | 分段失败 **2039**；seed/schema 不可用 **2042** |
| AC-M2-012-7 | AUTO apply 成功 | 写库 | `layout_template_id` = 对应内置 seed 模板 id |
| AC-M2-012-19 | 两模板评分分差 ≥2 | AUTO preview | 选择高分模板；返回可复算分数、特征与固定原因码；`confidence=HIGH` |
| AC-M2-012-20 | 两模板同分或分差为 1 | AUTO preview | 固定选择 `decision-scan`；`confidence=LOW`；不调用 LLM 二次决策 |

---

### FR-M2-012-3 正文保真（Fidelity Gate）

#### 描述

任意模式在 merge 前 **必须** 通过保真校验（ADR-028 §2.3）。失败则 **整单拒绝**，不部分应用。

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-8 | LLM 分段拼接文本 ≠ 原 body | preview/apply | 错误 **2037**；不写库 |
| AC-M2-012-9 | 保真通过 | apply | 数据库 `body` 字段与排版前一致 |

---

### FR-M2-012-4 预览与确认应用

#### 描述

- **Preview**：返回排版后 HTML + 分段摘要 + 保真结果；**不写库**
- **Apply**：用户确认后写入；若已有 `body_format=LAYOUT` 且 `overwrite=false` → **2031**

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-10 | 无现有版式 | preview → apply | 编辑器展示新 `layout_html` |
| AC-M2-012-11 | 已有 LAYOUT | apply `overwrite=false` | **2031** |
| AC-M2-012-12 | 已有 LAYOUT | apply `overwrite=true` | 覆盖 `layout_json/html`；`body` 仍不变 |

---

### FR-M2-012-5 football-layout 语义对齐

#### 描述

LLM 输出 `segmentType` 枚举与 `docs/football-layout/shared/semantic-parser.md` 对齐（ADR-028 §2.4 映射表）。MVP 优先支持足球分析类正文（比赛头、对阵、推荐列表等）。

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-13 | 正文含「竞彩推荐/比分推荐/指数推荐」三行 | AI 排版 | 识别为 `RECOMMENDATION_LIST` 并渲染为列表块 |
| AC-M2-012-14 | 正文首行为短标题 | AI 排版 | 识别为 `ARTICLE_TITLE`，映射 heading 槽 |
| AC-M2-012-15 | 某语义段无法映射目标槽位 | AI 排版 preview | **降级**到最近 paragraph/repeat 槽；`mappingDegraded=true`；不拒绝整单（MVP 默认） |
| AC-M2-012-16 | 启用 styleHints（Phase 1.5+） | AI 排版 | 段内高亮注入 render；`body` 纯文本不变 |

---

### FR-M2-012-6 映射降级与段内样式（OQ-M2-012-01）

#### 描述

**MVP 默认**：语义段无法映射模板槽位时，**降级**到最近 `paragraph` / `repeat:true` 槽；服务端记录 warning；preview 展示 degraded mapping 摘要。

**Phase 1.5 / MVP+（可选）**：`SemanticSegment.styleHints` — AI 基于 layout 上下文（队名、比分、 emphasis 等）建议段内 inline 样式；merge 时注入，**不得**改变 `text`（ADR-020 段内样式注入）。

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-17 | 段类型与槽位不匹配 | preview | `degradedSegments` 非空；仍返回 `layoutHtml` |
| AC-M2-012-18 | styleHints 含队名高亮 | merge + render | HTML 含 span 高亮；concat(segments.text) === body |

---

### FR-M2-012-7 一键排版 — football-layout 规则预设（FOOTBALL_AI）

#### 描述

内容编辑页工具栏 **「一键排版」**（`WechatQuickTypesetDialog`），对已有正文执行 **无 LLM** 的规则分段 + 内置 PRESET 渲染：

1. 客户端优先传 `body`（纯文本 SSOT）；`html` 与 `body` **至少一方非空**（`@AssertTrue`）
2. `POST /typeset` · `mode=FOOTBALL_AI`；可选 `footballTemplate` 覆盖内置模板标识
3. 服务端：`SemanticSegmentHeuristicUpgrader` 启发式分段 → `FootballLayoutPipeline` → `LayoutMergeService.mergeSemantic`
4. 四套 UI 预设（V204 seed）：

| UI 预设 | `footballTemplate` | 内置 PRESET tag | 说明 |
|---------|-------------------|-----------------|------|
| 竞彩营销版 | `marketing` | `football-ai:marketing` | 圆角分析卡、无首行缩进、`#e94560` 强调 |
| 简洁通读版 | `clean-read` | `football-ai:clean-read` | 无头图/卡片，导语 + 长文通读 |
| 赛事分析版 | *(空 = AUTO)* | `decision-scan` / `analysis-report` | 由 `FootballTemplateDecider` 二选一（同 FR-M2-012-2） |
| 付费引流版 | `marketing` + `paramOverrides.paidBoundary=true`（仅免费区） | 同竞彩营销 | 免费区末尾插入付费分界线 |

5. 存在 **免费区 + 付费区** 时，分别对两区调用 typeset 并写回对应编辑器；仅免费区有正文时只更新免费栏（free-only apply）
6. HTML 实体解码（`OpsHtmlTextHelper`）与 Unicode 保真：`escapeHtml` 不得破坏中文标点等可见字符

#### 与 FR-M2-012-2 关系

| 维度 | AI 排版 AUTO（LLM） | 一键排版 赛事分析版（FOOTBALL_AI） |
|------|---------------------|----------------------------------|
| 分段 | LLM + `AI_TYPESET_SEMANTIC` | 启发式规则分段 |
| 模板决策 | `FootballTemplateDecider` | 同左（`footballTemplate` 为空时） |
| 端点 | `/typeset/ai-semantic/*` | `/typeset` |

#### 验收标准

| AC | Given | When | Then |
|----|-------|------|------|
| AC-M2-012-21 | ARTICLE 有 body | 选「竞彩营销版」一键排版 | 返回 `layoutHtml`；`selectedFootballTemplate=marketing` |
| AC-M2-012-22 | 仅免费区有正文 | 一键排版任意预设 | 只更新 `free_body` / 免费编辑器；付费区不变 |
| AC-M2-012-23 | `html` 与 `body` 均为空 | POST typeset | 校验失败（400） |
| AC-M2-012-24 | 客户端已传 `body` | FOOTBALL_AI typeset | 优先用 `body`，不从 styled HTML 重新拆段（body-first） |
| AC-M2-012-25 | merge 后用户正文丢失 | preview/apply | `LayoutMergeFidelityGate` 拒绝；不写库 |

---

## 5. 与 FR-M2-005 关系

| 能力 | FR-M2-005 | FR-M2-012 |
|------|-----------|-----------|
| 模板库 CRUD | ✅ | 消费 |
| 手动选模板 + merge（无语义） | ✅ apply-layout-template | 不替代 |
| AI 语义分段 + 映射 | ❌ Phase 2（OQ-v2-05/10） | ✅ 本增量 |
| 正文保真 | ✅ ADR-020 | ✅ 继承 |

**推荐工作流**：AI 生成正文（FR-M2-003/ADR-053）→ **AI 排版**（本 FR）→ 人工微调 → 提交审核。

---

## 6. 开放问题（已关闭）

| 编号 | 问题 | 决策 | 状态 |
|------|------|------|------|
| **OQ-M2-012-01** | 2041 映射失败是否允许降级 | **Accepted**：默认降级到 paragraph/repeat 槽 + warning + preview degraded；可选 `styleHints` 段内样式（Phase 1.5 / MVP+） | ✅ |
| **OQ-M2-012-02** | AUTO 模式含义 | **Accepted**：AUTO = football-layout SKILL.md 管线（内置两模板 + semantic-parser + template-decision）；TEMPLATE_GUIDED = 公推模板库 DB | ✅ |
| **OQ-M2-012-03** | 是否隐藏 ADR-027 规则链 | **Accepted**：保留 **备选/legacy**；AI 排版为主 | ✅ |

---

*Accepted · 2026-09-08 · v1.2 一键排版 FOOTBALL_AI · 2026-09-17*
