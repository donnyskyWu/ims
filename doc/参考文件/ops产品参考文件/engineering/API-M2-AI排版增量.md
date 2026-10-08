# API-M2-内容生产 — AI 排版增量

> **版本**：v1.1 | 2026-09-17 | 2026-10-02  
> **状态**：Accepted（2026-09-08；v1.2 同步 FOOTBALL_AI 一键排版与 V204 预设）  
> **Base Path**：`/admin-api/ops`（Gateway 前缀以环境为准；Football 单仓迁移后路径不变）  
> **关联 PRD**：[PRD-M2-AI排版增量](../product/PRD-M2-AI排版增量.md)  
> **关联 ADR**：[ADR-028](../adr/ADR-028-M2-AI排版语义分段.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 概述

新增 **AI 语义排版** 端点，与现有端点关系：

| 现有 | 本增量 |
|------|--------|
| `POST /content/{id}/apply-layout-template` | 无语义，顺序 merge；**保留** |
| `POST /content/{id}/apply-layout-template/preview` | 同上 preview；**保留** |
| ADR-027 typeset（规则链 / FOOTBALL_AI） | **一键排版**走 `/typeset` · `FOOTBALL_AI`；规则链 `AUTO`/`TEMPLATE` 为 legacy |
| 本增量 §9 | **一键排版**（无 LLM）与 §2 **AI 语义排版**（LLM）并列，不互相 fallback |

---

## 2. 端点（AI 语义排版 · LLM）

### 2.1 POST `/admin-api/ops/content/{id}/typeset/ai-semantic/preview`

**权限**：`@PreAuthorize("@ss.hasPermission('oa:content:typeset')")`

**业务**：

1. 校验 `contentType=ARTICLE`；校验内容数据权限
2. 解析 `body`：请求体 `body` 优先，否则拼接 `free_body` + `\n\n` + `content.body`（或 `paid_body` / `extractPlainText(layout_html)`）；仅一方非空则取该方；全空 → **2036**
3. `TEMPLATE_GUIDED`：校验 `templateId` 存在、ENABLED、类型匹配 → 否则 **1501**
4. `AUTO`：走 `FootballLayoutPipeline`（`docs/football-layout/SKILL.md` SSOT）— semantic-parser → `FootballTemplateDecider`（内置 `decision-scan` | `analysis-report`）→ 映射内置 seed `layout_schema`
5. 调用 `AiSemanticSegmentService` → Fidelity Gate → `SegmentSlotMapper`（失败 **默认降级**，见 §3.4）→ `LayoutMergeService`
6. **不写库**；返回预览 DTO

**请求体** `ContentAiSemanticTypesetPreviewReq`：

```json
{
  "mode": "TEMPLATE_GUIDED",
  "templateId": "501",
  "body": null,
  "paramOverrides": {
    "title_font_size": 22
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | String | ✅ | `TEMPLATE_GUIDED` \| `AUTO` |
| `templateId` | String | 条件 | `TEMPLATE_GUIDED` 时 **必填**（snowflake 字符串） |
| `body` | String | ❌ | 覆盖合并正文（免费+付费）；默认取内容 SSOT |
| `freeBody` | String | ❌ | 覆盖免费段；与 `body` 联用时可定位免费/付费切分点 |
| `paramOverrides` | Object | ❌ | 传入 `LayoutMergeService`（ADR-027） |

**响应** `ContentAiSemanticTypesetPreviewResp`：

```json
{
  "mode": "AUTO",
  "selectedTemplateId": "501",
  "selectedTemplateName": "决策扫读版",
  "selectedFootballTemplate": "decision-scan",
  "templateDecision": {
    "decisionScanScore": 12,
    "analysisReportScore": 0,
    "scoreGap": 12,
    "confidence": "HIGH",
    "selectionReason": "SCORE_THRESHOLD",
    "decisionReasons": [
      "DECISION_BODY_LE_1200:+3",
      "DECISION_SINGLE_MATCH:+2",
      "DECISION_HAS_RECOMMENDATION:+3",
      "DECISION_HAS_CONCLUSION:+2",
      "DECISION_ANALYSIS_PARAGRAPHS_LE_4:+2"
    ],
    "featureSummary": {
      "bodyCharCount": 800,
      "matchCount": 1,
      "analysisParagraphCount": 3,
      "recommendationCount": 1,
      "conclusionSegmentCount": 1,
      "deepDimensionCount": 0,
      "numericDataSegmentCount": 0,
      "oddsSegmentCount": 0,
      "subheadingCount": 1
    }
  },
  "segments": [
    {
      "index": 0,
      "segmentType": "ARTICLE_TITLE",
      "text": "周日焦点战深度分析",
      "slotRef": "slot-heading-1",
      "sourceLineStart": 0,
      "sourceLineEnd": 0,
      "styleHints": null
    }
  ],
  "fidelityCheck": {
    "passed": true,
    "plainTextBefore": "周日焦点战深度分析\n...",
    "plainTextAfter": "周日焦点战深度分析\n..."
  },
  "segmentationReport": {
    "segmentCount": 12,
    "segmentTypeCounts": {
      "ARTICLE_TITLE": 1,
      "MATCH_HEADER": 2,
      "RECOMMENDATION_LIST": 1,
      "ANALYSIS_PARAGRAPH": 6
    },
    "unmappedSegmentCount": 0
  },
  "mappingDegraded": false,
  "degradedSegments": [],
  "mappingWarnings": [],
  "layoutJson": { "version": 2, "blocks": [] },
  "layoutHtml": "<section>...</section>",
  "freeLayoutJson": { "version": 2, "blocks": [] },
  "freeLayoutHtml": "<section>...</section>"
}
```

| 响应字段 | 说明 |
|----------|------|
| `selectedFootballTemplate` | 仅 AUTO；`decision-scan` \| `analysis-report` |
| `templateDecision` | 仅 AUTO；确定性评分审计对象，字段与 §3.3 一致；TEMPLATE_GUIDED 返回 `null` |
| `mappingDegraded` | 是否有段降级到 paragraph/repeat 槽（OQ-M2-012-01 默认行为） |
| `degradedSegments` | 降级段列表 `{ index, originalSegmentType, fallbackSlotRef, reason }` |
| `mappingWarnings` | 人类可读 warning 字符串数组 |
| `layoutHtml` | 付费段 merge 结果；仅付费时等同全文 |
| `freeLayoutHtml` | 免费段 merge 结果；存在免费内容时返回 |

---

### 2.2 POST `/admin-api/ops/content/{id}/typeset/ai-semantic/apply`

**权限**：同 preview

**请求体** `ContentAiSemanticTypesetApplyReq`：

```json
{
  "mode": "TEMPLATE_GUIDED",
  "templateId": "501",
  "body": null,
  "paramOverrides": {},
  "overwrite": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `overwrite` | Boolean | ❌ | 默认 `false`；已有 LAYOUT 且 false → **2031** |

**业务**：

1. 执行与 preview 相同管线
2. 写库：
   - `layout_json` / `layout_html` ← 付费段 merge 结果
   - `free_body` ← 免费段 merge HTML（存在免费内容时）
   - `layout_template_id` ← `selectedTemplateId`（TEMPLATE_GUIDED 为请求 templateId；AUTO 为选中 id）
   - `body_format` ← `LAYOUT`（存在付费段时）
   - **`body` / `free_body` 纯文本 SSOT 不变**（保真铁律）
3. 本 AI apply 不执行 ADR-021 的 `body = extractPlainText(layout_html)` 回写，`body` 保持 apply 前原始字符串；同时强制 `normalize(extractPlainText(layout_html)) = normalize(body)`。用户后续手工编辑保存仍按 ADR-021 同步 `body`

**响应**：更新后的 `ContentRespVO`（与现有 content get 一致）

---

## 3. 数据模型

### 3.1 `SemanticSegment`

LLM 输出 + 服务端校验的结构；taxonomy SSOT：`docs/football-layout/shared/semantic-parser.md`。

```json
{
  "index": 0,
  "segmentType": "ARTICLE_TITLE",
  "text": "string",
  "slotRef": "string",
  "sourceLineStart": 0,
  "sourceLineEnd": 0,
  "metadata": {},
  "styleHints": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `index` | Integer | ✅ | 文档序，从 0 递增 |
| `segmentType` | String | ✅ | 见 §3.2 枚举 |
| `text` | String | ✅ | 该段纯文本；拼接后 = 全文 |
| `slotRef` | String | ❌ | 映射到的 `layout_schema` 槽位 id |
| `sourceLineStart` | Integer | ❌ | 溯源：body 行号起（含） |
| `sourceLineEnd` | Integer | ❌ | 溯源：body 行号止（含） |
| `metadata` | Object | ❌ | 扩展；如 `RECOMMENDATION_LIST` 的 `{ "items": [...] }` |
| `styleHints` | Array | ❌ | **Phase 1.5 / MVP+**；段内样式建议，merge 时注入 inline style，**不改 `text`** |

### 3.1.1 `styleHints` 项（Phase 1.5 / MVP+）

```json
{
  "start": 0,
  "end": 4,
  "hintType": "TEAM_NAME",
  "renderAs": "bold+accent"
}
```

| 字段 | 说明 |
|------|------|
| `start` / `end` | 在 `text` 内的字符偏移（半开区间 `[start,end)`） |
| `hintType` | `TEAM_NAME` \| `SCORE` \| `EMPHASIS` \| `KEYWORD` \| `CONCLUSION` 等；SSOT：`semantic-parser.md` §段内语义高亮 |
| `renderAs` | 模板相关 render token；由 `LayoutMergeService` 解析为 inline style/spans |

**铁律**：应用 `styleHints` 后 `extractPlainText(rendered)` 仍须与 concat(segments.text) 一致（仅增 markup，不改可见字符序列）。

### 3.2 `segmentType` 枚举

| 值 | 说明 |
|----|------|
| `ARTICLE_TITLE` | 文章标题 |
| `MATCH_HEADER` | 比赛头（如「周日215 挪超」） |
| `TEAM_VS` | 对阵行 |
| `MATCH_TIME` | 比赛时间行 |
| `MATCH_METADATA` | 元数据键值组 |
| `SUBHEADING` | 小标题 |
| `ANALYSIS_PARAGRAPH` | 分析段落 |
| `RECOMMENDATION_LIST` | 推荐三行列表 |
| `IMAGE_PLACEHOLDER` | 图片占位 |
| `DIVIDER` | 分割线 |
| `DISCLAIMER` | 免责声明 |
| `QUOTE` | 引用 |
| `ORDERED_LIST` | 有序列表 |
| `DECORATIVE_SLOGAN` | 装饰标语 |
| `PLAIN_PARAGRAPH` | 兜底段落 |
| `STAT_BAR` | 双色统计条（`analysis-report`）；text 为「标题 + 百分比对比行」 |
| `ODDS_TABLE` | 赔率表格（`analysis-report`）；text 为 pipe/逗号分隔行列 |
| `HIGHLIGHT` | 高亮框（`analysis-report` / `decision-scan`）；红左边框 + 浅红底；亦可通过 `ANALYSIS_PARAGRAPH` 内 `【…】`/`重点：`/`注意：` 自动识别 |

**校验**：`@InDict(type="dict_semantic_segment_type")` 或通过 M8 JSON schema 约束；**1503** 非法枚举。

### 3.3 AUTO 模式 — football-layout 管线（OQ-M2-012-02 Accepted）

**非** DB 模板库 catalog 扫描。`FootballLayoutPipeline` SSOT = `docs/football-layout/SKILL.md`：

```
body → semantic-parser (shared/semantic-parser.md)
     → FootballTemplateDecider (decision-scan | analysis-report)
     → resolveBuiltInSeedTemplate(selectedFootballTemplate) → layout_schema
     → SegmentSlotMapper → LayoutMergeService
```

**`FootballTemplateDecider` 输出**（内部 DTO；选择结果映射到 preview 顶层，评分审计字段映射到 `templateDecision`）：

```json
{
  "selectedFootballTemplate": "decision-scan",
  "selectedTemplateId": "501",
  "decisionScanScore": 12,
  "analysisReportScore": 0,
  "scoreGap": 12,
  "confidence": "HIGH",
  "selectionReason": "SCORE_THRESHOLD",
  "decisionReasons": [
    "DECISION_BODY_LE_1200:+3",
    "DECISION_SINGLE_MATCH:+2"
  ],
  "featureSummary": {
    "bodyCharCount": 800,
    "matchCount": 1,
    "analysisParagraphCount": 3,
    "recommendationCount": 1,
    "conclusionSegmentCount": 1,
    "deepDimensionCount": 0,
    "numericDataSegmentCount": 0,
    "oddsSegmentCount": 0,
    "subheadingCount": 1
  }
}
```

| `selectedFootballTemplate` | 内置 seed | 参照 |
|----------------------------|-----------|------|
| `decision-scan` | 决策扫读版 | `template-decision-scan.md` |
| `analysis-report` | 情报分析版 | `template-analysis-report.md` |
| `marketing` | 竞彩营销版 | V204 PRESET · `football-ai:marketing` |
| `clean-read` | 简洁通读版 | V204 PRESET · `football-ai:clean-read` |

> **注**：`marketing` / `clean-read` 主要用于 **§9 FOOTBALL_AI 一键排版**；AI 语义 AUTO 仍仅在 `decision-scan` / `analysis-report` 间决策。

#### 3.3.1 可观测特征

输入仅为 Fidelity Gate 已通过的 `SemanticSegment[]` 与原文，不增加请求字段：

| 字段 | 计算契约 |
|------|----------|
| `bodyCharCount` | CRLF→LF 后移除 Unicode 空白的 code point 数 |
| `matchCount` | `max(count(MATCH_HEADER), count(TEAM_VS))` |
| `analysisParagraphCount` | `count(ANALYSIS_PARAGRAPH)+count(PLAIN_PARAGRAPH)` |
| `recommendationCount` | `count(RECOMMENDATION_LIST)` |
| `conclusionSegmentCount` | 命中 `推荐|结论|看好|竞彩推荐|比分推荐|指数推荐|综合推荐` 的段数 |
| `deepDimensionCount` | 按 ADR-028 §2.4.1 六组关键词统计命中的不同维度数 |
| `numericDataSegmentCount` | 命中百分比/xG，或含数字且命中射门、射正、控球率、胜率、概率、积分、排名的段数 |
| `oddsSegmentCount` | 命中赔率、盘口、亚指、欧指、指数、水位、凯利、返还率的段数 |
| `subheadingCount` | `count(SUBHEADING)` |

同一段对同一特征最多计一次；匹配大小写不敏感。LLM 只能生成结构化分段，**不得**输出模板选择、分数或 `decisionReasons`。

#### 3.3.2 权重与选择

| 模板 | 命中条件 | 分值 | 固定 reason code |
|------|----------|-----:|------------------|
| decision-scan | `bodyCharCount <= 1200` / `1200 < count <= 2000` | +3 / +1 | `DECISION_BODY_LE_1200` / `DECISION_BODY_1201_2000` |
| decision-scan | `matchCount <= 1` | +2 | `DECISION_SINGLE_MATCH` |
| decision-scan | `recommendationCount >= 1` | +3 | `DECISION_HAS_RECOMMENDATION` |
| decision-scan | `conclusionSegmentCount >= 1` | +2 | `DECISION_HAS_CONCLUSION` |
| decision-scan | `analysisParagraphCount <= 4` | +2 | `DECISION_ANALYSIS_PARAGRAPHS_LE_4` |
| analysis-report | `bodyCharCount >= 2200` / `1400 <= count < 2200` | +3 / +1 | `ANALYSIS_BODY_GE_2200` / `ANALYSIS_BODY_1400_2199` |
| analysis-report | `matchCount >= 2` | +3 | `ANALYSIS_MULTI_MATCH` |
| analysis-report | `deepDimensionCount >= 3` / `=2` | +4 / +2 | `ANALYSIS_DEEP_DIMENSIONS_GE_3` / `ANALYSIS_DEEP_DIMENSIONS_2` |
| analysis-report | `numericDataSegmentCount >= 2` / `=1` | +3 / +1 | `ANALYSIS_NUMERIC_SEGMENTS_GE_2` / `ANALYSIS_NUMERIC_SEGMENTS_1` |
| analysis-report | `oddsSegmentCount >= 1` | +3 | `ANALYSIS_HAS_ODDS` |
| analysis-report | `analysisParagraphCount >= 6` | +2 | `ANALYSIS_PARAGRAPHS_GE_6` |
| analysis-report | `subheadingCount >= 4` | +2 | `ANALYSIS_SUBHEADINGS_GE_4` |

- 分差 `>=2`：高分模板胜出，`confidence=HIGH`、`selectionReason=SCORE_THRESHOLD`。
- 同分或分差 `=1`：固定 `decision-scan`，`confidence=LOW`、`selectionReason=LOW_CONFIDENCE_FALLBACK`；禁止 LLM tie-break、DB catalog 扫描或 legacy 规则链 fallback。
- `decisionReasons[]` 由命中的固定 reason code 与分值组成，顺序固定为上表顺序。`scoreGap` 为两分绝对差。
- 合法分段必定二选一；2042 仅表示选中标识无法解析到 ENABLED 内置 seed/schema。
- seed 解析必须附带当前 `tenant_id`；S-21a 初始 migration 延续既有 PRESET 口径，仅为 `tenant_id=1` 幂等建两款内置模板。其他租户不得复用 tenant 1 记录，缺少本租户 seed 时返回 2042。

| `selectionReason` | 说明 |
|-------------------|------|
| `SCORE_THRESHOLD` | 分差至少 2，选择高分模板 |
| `LOW_CONFIDENCE_FALLBACK` | 同分或分差 1，固定回退 `decision-scan` |

**TEMPLATE_GUIDED** 仍使用 DB `templateId` → `oa_wechat_layout_template.layout_schema`，不走 `FootballTemplateDecider`。

### 3.4 槽位映射降级（OQ-M2-012-01 Accepted）

| 场景 | MVP 默认行为 |
|------|-------------|
| 语义段无法映射目标槽 | **降级**到最近 `paragraph` / `repeat:true` 槽；`mappingDegraded=true`；`mappingWarnings` 记录；**不**抛 2041 |
| strict 模式（可选配置） | 未映射 → **2041**（非 MVP 默认） |

`degradedSegments[]` 项：

```json
{
  "index": 5,
  "originalSegmentType": "QUOTE",
  "fallbackSlotRef": "slot-paragraph-repeat",
  "reason": "NO_QUOTE_SLOT_IN_SCHEMA"
}
```

---

## 4. 服务组件（实现指引 · 本 Spec 不编码）

| 组件 | 职责 |
|------|------|
| `AiSemanticSegmentService` | 调当前租户系统「AI 模型配置」中的 `ENABLED + CONNECTED` OpenAI-compatible LLM，使用 M8 `AI_TYPESET_SEMANTIC` 提示词；输出 `SemanticSegment[]`（含可选 `styleHints`） |
| `TypesetFidelityGate` | `plainTextBefore === plainTextAfter` |
| `FootballLayoutPipeline` | AUTO 模式：semantic-parser → template-decision → 内置 seed schema |
| `FootballTemplateDecider` | AUTO：在 `decision-scan` / `analysis-report` 间二选一 |
| `SegmentSlotMapper` | segments → schema slotRef；失败默认降级（§3.4） |
| `LayoutMergeService` | **MVP 扩展** merge 入口：接受 segment 映射；`styleHints` 注入仅 Phase 1.5+ |

---

## 5. M8 提示词

| 场景 code | 说明 |
|-----------|------|
| `AI_TYPESET_SEMANTIC` | 输入：body +（可选）layout_schema 槽位摘要；输出：JSON `SemanticSegment[]` |

**模型与密钥**：

- 通过系统「AI 模型配置」管理 endpoint、model 与 API Key；连接测试真实调用 Chat Completion，成功后方可标记 `CONNECTED`。
- API Key 使用既有 AES-256 机制写入 `api_key_encrypted`；响应只返回 masked 值，禁止进入 seed、源码、日志或测试快照。
- 本场景不调用 `jingcai.article`；后者仅用于 AI 文案生成/润色，不作为语义分段 fallback。

约束写入 system prompt：

- 不得增删改原文任何字符
- 仅允许 §3.2 枚举
- 每段 `text` 必须是原文连续子串
- （Phase 1.5+）`styleHints` 仅标注偏移与高亮类型，**不得**改变 `text` 字符

---

## 6. 错误码

| 码 | 含义 | 触发 |
|----|------|------|
| **2036** | 正文为空 | body 解析后为空 |
| **2031** | 需确认覆盖 | apply + 已有 LAYOUT + `overwrite=false` |
| **2037** | 保真失败 | Fidelity Gate |
| **2039** | AI 分段失败 | LLM 超时/非法 JSON/枚举 |
| **2041** | 槽位映射失败 | strict 模式且段无法映射、未允许降级 |
| **2042** | 无可用内置模板 | AUTO 选中标识无法解析到 ENABLED seed/schema |
| **1501** | 模板无效 | templateId 不存在/停用/类型不匹配 |
| **1504** | 跨租户 | 内容或模板 tenant 不一致 |

---

## 7. 权限与校验

| 项 | 规则 |
|----|------|
| 权限码 | `oa:content:typeset` |
| 内容类型 | `content_type=ARTICLE`，否则 **1500** |
| templateId | `@NotNull` when `TEMPLATE_GUIDED`；存在性 **1501** |
| 租户 | 内容 + 模板同 `tenant_id` |
| 数据权限 | 复用 `ContentDataScopeSupport` |

---

## 8. 测试要点（API 层）

| ID | 场景 | 预期 |
|----|------|------|
| API-M2-012-01 | TEMPLATE_GUIDED preview | code=0；`fidelityCheck.passed=true` |
| API-M2-012-02 | AUTO preview | code=0；模板二选一；`templateDecision` 分数、原因与特征可复算 |
| API-M2-012-09 | AUTO 分差至少 2 | 选择高分模板；`confidence=HIGH` |
| API-M2-012-10 | AUTO 同分/分差 1 | 固定 decision-scan；`confidence=LOW`；无 LLM 二次决策 |
| API-M2-012-11 | AUTO seed 不可用 | code=2042 |
| API-M2-012-07 | 映射降级 | code=0；`mappingDegraded=true`；`degradedSegments` 非空 |
| API-M2-012-08 | styleHints render（Phase 1.5+） | HTML 含高亮；保真仍通过 |
| API-M2-012-03 | body 空 | code=2036 |
| API-M2-012-04 | 保真 mock 失败 | code=2037 |
| API-M2-012-05 | apply overwrite=false 二次 | code=2031 |
| API-M2-012-06 | 无权限 | code=403 |

---

---

## 9. 一键排版 — `POST /typeset` · `mode=FOOTBALL_AI`（ADR-027 §4.3）

**权限**：`oa:content:typeset`（与 AI 语义排版相同）

**端点**：

- `POST /admin-api/ops/content/typeset`（编辑态，无 content id）
- `POST /admin-api/ops/content/{id}/typeset`（可选带 id）

**请求体** `ContentTypesetReq`（扩展字段）：

```json
{
  "html": "<p>可选 HTML</p>",
  "body": "纯文本正文（优先）",
  "mode": "FOOTBALL_AI",
  "footballTemplate": "marketing",
  "paramOverrides": { "paidBoundary": true }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | String | ✅ | `FOOTBALL_AI` |
| `html` | String | 条件 | 与 `body` **至少一方非空** |
| `body` | String | 条件 | **body-first**：客户端已提取纯文本时优先使用，避免从 styled div 重新拆段 |
| `footballTemplate` | String | ❌ | `marketing` \| `clean-read` \| `decision-scan` \| `analysis-report`；空 = AUTO 决策（仅 decision-scan / analysis-report） |
| `paramOverrides` | Object | ❌ | 如 `paidBoundary: true`（付费引流版免费区末尾分界线） |

**响应** `ContentTypesetVO`（节选）：

| 字段 | 说明 |
|------|------|
| `html` | 渲染后完整 layout HTML |
| `layoutJson` | merge 输出实例（客户端写回编辑器时 preserve） |
| `selectedFootballTemplate` | 实际选用的内置标识 |
| `selectedTemplateId` / `selectedTemplateName` | 对应 PRESET 模板 id/名称 |
| `plainTextBefore` / `plainTextAfter` | 保真校验前后纯文本 |
| `templateDecision` | 仅 AUTO（`footballTemplate` 为空且选中 decision-scan/analysis-report） |

**管线**（无 LLM）：

```
body/html → SemanticSegmentHeuristicUpgrader
         → FootballLayoutPipeline.resolve(tenantId, body, segments, footballTemplate)
         → SegmentSlotMapper → LayoutMergeService.mergeSemantic
         → LayoutMergeFidelityGate（套用/写回前）
```

**与 §2 差异**：

| 项 | §2 AI 语义 | §9 FOOTBALL_AI |
|----|-----------|----------------|
| 分段 | LLM `AI_TYPESET_SEMANTIC` | 启发式规则 |
| 端点 | `/typeset/ai-semantic/*` | `/typeset` |
| 写库 | apply 端点写 content | 前端写回编辑器 / 统一 layout API |

**错误**：

| 码 | 触发 |
|----|------|
| 400 | `html` 与 `body` 均为空（Bean Validation） |
| 2013 / LAYOUT_APPLY_BODY_EMPTY | body 解析后为空 |
| LAYOUT_SCHEMA_INVALID | `LayoutMergeFidelityGate` 未通过 |

---

*Accepted · 2026-09-08 · v1.2 FOOTBALL_AI · 2026-09-17*
