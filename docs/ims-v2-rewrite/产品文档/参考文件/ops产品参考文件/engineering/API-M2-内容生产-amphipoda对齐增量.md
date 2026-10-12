# API-M2-内容生产 — amphipoda 玩法对齐增量

> **版本**：v1.0 | 2026-08-31  
> **Base Path**：`/admin-api/ops`（Gateway 前缀以环境为准）  
> **关联 PRD**：[PRD-M2-内容生产-amphipoda对齐增量](../product/PRD-M2-内容生产-amphipoda对齐增量.md)  
> **关联 ADR**：[ADR-076](../adr/ADR-076-OPS内容生产amphipoda玩法与matchScheme对齐.md)

---

## 1. 数据模型增量

### 1.1 `oa_production_content` 新增列

| 列 | Java 字段 | 类型 | 说明 |
|----|-----------|------|------|
| `match_scheme_json` | `matchSchemeJson` | JSON | `List<MatchSchemeItemVO>`，Football 同构 |
| `match_type` | `matchType` | Integer | 1~5，见 PRD Tab 映射 |
| `competition_ids_json` | `competitionIdsJson` | JSON | `[{scheduleId,label}]` 快照，可选 |

**兼容字段**（保留）：

| 列 | 规则 |
|----|------|
| `competition_id` | 保存时 = `matchScheme[0].matchId` 字符串化 |
| `competition_name` | 保存时 = 首场 `homeName VS awayName` 或 className |
| `scheme_type` | 可选；不再校验为玩法 SSOT |

### 1.2 `MatchSchemeItemVO`（JSON 元素）

与 member `MatchBaseVO` 对齐（只读参照）：

```json
{
  "matchId": 123456789,
  "scheduleId": "123456789",
  "className": "英超",
  "homeName": "曼联",
  "awayName": "切尔西",
  "matchTime": 1725091200000,
  "matchPlays": [
    {
      "playId": 1,
      "result": "3",
      "resultType": 1,
      "type": 1,
      "opinion": 0
    }
  ],
  "mainPlayMethod": "胜平负"
}
```

---

## 2. 内容 API 变更

### 2.1 POST `/ops/content/create` · PUT `/ops/content/update`

**请求体增量** `ContentCreateReq` / `ContentUpdateReq`：

```json
{
  "matchType": 1,
  "matchScheme": [ /* MatchSchemeItemVO[] */ ],
  "competitionIdsJson": [
    { "scheduleId": "123", "label": "曼联 VS 切尔西" }
  ]
}
```

**校验**：

| 字段 | 规则 | 错误码 |
|------|------|--------|
| `matchType` | 1~5；`documentType=OFFICIAL_PLAN` 时 **必填** | 1501 |
| `matchScheme` | 正式方案：≥1 项；每项 `matchId` 数字字符串可解析 | 1501 |
| `matchScheme[].matchPlays` | **可空**（ADR-077：AI 不强制玩法）；保存草稿允许空 | — |
| 传足 `matchType=2` | 场次数 = 前端传足套餐值（同 amphipoda） | 1501 |

**响应** `ContentVO` 增量：

```json
{
  "matchType": 1,
  "matchScheme": [],
  "competitionIdsJson": [],
  "competitionId": "123456789",
  "competitionName": "曼联 VS 切尔西",
  "matchSummary": "2场"
}
```

### 2.2 GET `/ops/content/{id}` · GET `/ops/content/list`

- 返回 `matchType` / `matchScheme` / `matchSummary`
- 列表 `competitionName` 优先 `matchSummary`（如 `合并2场`）

---

## 3. Football sync（ADR-054 增量）

### 3.1 行为变更

`FootballArticleBridgeServiceImpl.buildMatchSchemeFromContent`：

- **Before**：stub `{matchId, matchTime, className}`
- **After**：`content.matchSchemeJson` 序列化为 `author_article.match_scheme`；`match_type` 取自 `content.matchType`（缺省 1）

**不变**：失败不阻断 create；`POST /ops/content/{id}/sync-football-scheme` 重试。

---

## 4. AI 内容 API 变更

### 4.1 POST `/ops/ai-content/generate`

**`AiContentContextDTO` 增量**：

```json
{
  "authorId": 1001,
  "authorName": "张三",
  "matchType": 1,
  "matchScheme": [ /* 与内容表同构 */ ],
  "matchName": "曼联 VS 切尔西 等2场",
  "schemeTypes": [],
  "historyRecord": "",
  "anchorStyle": "data",
  "productDescription": "",
  "contentLength": "MEDIUM",
  "documentType": "OFFICIAL_PLAN",
  "isPaywall": true
}
```

| 字段 | 规则 |
|------|------|
| `matchScheme` | jingcai 路径：**必填** ≥1 场；每场 plays 映射见 §5 |
| `matchScheme[].matchPlays` | **可空**（ADR-077 D10；自动 Job 与手工 AI） |
| `matchName` | 摘要展示；≥2 场时 `首场 等N场` |
| `schemeTypes` | **可选**；仅润色 requirements 辅助 |
| `authorId` | jingcai 路径 **必填** |
| `documentType` | `@InDict dict_document_type`；自动 Job 必带 |
| `isPaywall` | **仅请求上下文，不落库**（ADR-077 D9/D11）。可放在 `context` 或与现网 E2E 一样放在 generate **请求体顶层**（与 `documentType` 并列）。`OFFICIAL_PLAN` → `true`；其它 → `false`。自动首写：true → `paid_body`，false → `free_body` | 

**润色（roundCount≥2）** — OPS 组包规则（不改 jingcai 服务）：

```
writing.requirements += [
  "【历史对话】\n用户：...\n助手：...（最近3轮）",
  "【当前正文】\n{上一轮 assistant HTML，截断4000字}",
  "【本次修改要求】\n{message}"
]
params.events = 当前 context.matchScheme 映射（与首生成相同）
```

**降级**：`sys_param ai.content.chat-via-jingcai=false` → 现有 M8 多轮 messages（不变）。

### 4.2 作者 persona

OPS `JingcaiArticleRequestBuilder` 增量：

- 只读查 `oa_author` / Football author `persona` → `author.authorProfile`
- persona 为空：警告日志；**不阻断**（与现网 OPS jingcai 行为一致；质量弱于发布方案）

---

## 5. jingcai.events 映射（OPS 实现 SSOT）

参照 member `ArticleAiSchemeServiceImpl`（只读），OPS 实现等价逻辑：

| matchPlay.resultType | playType |
|---------------------|----------|
| 1 | 胜平负 |
| 2 | 比分 |
| 3 | 让球胜平负 |
| 4 | 半全场 |
| 5 | 进球数 |
| 6 | 大小球 |

**Event 字段**：

| 字段 | 来源 |
|------|------|
| matchName | `className` |
| teamName | `homeName VS awayName` |
| matchTime | 格式 `yyyy-MM-dd HH:mm`（Asia/Shanghai） |
| plays | `matchPlays` 映射 |

---

## 6. 任务 API 增量（消费方）

### 6.1 GET `/ops/task/{id}/execute`

已有 `competitions[]`（合并组）。内容创建前端消费：

```json
{
  "competitions": [
    { "competitionId": "123", "competitionName": "曼联 VS 切尔西" },
    { "competitionId": "456", "competitionName": "阿森纳 VS 利物浦" }
  ]
}
```

→ 映射为 `competitionIdsJson` + 玩法区预填（无 matchPlays）。

---

## 7. Flyway

```sql
-- Vxxx__m2_content_match_scheme.sql
ALTER TABLE oa_production_content
  ADD COLUMN match_scheme_json JSON NULL COMMENT 'Football matchScheme SSOT' AFTER competition_name,
  ADD COLUMN match_type TINYINT NULL COMMENT '1竞足2传足3北单4足球5临场' AFTER match_scheme_json,
  ADD COLUMN competition_ids_json JSON NULL COMMENT 'N场scheduleId快照' AFTER match_type;
```

**存量**：不回填；首次编辑保存时写入。

---

## 8. 错误码

| 码 | 场景 |
|----|------|
| 1501 | matchType/matchScheme 校验失败 |
| 1502 | 不变（task 唯一内容等） |
| BAD_REQUEST | jingcai 失败 / 作者 ID 空 |

---

## 9. 不在本 Slice 的 API

- ❌ 新增 member `generate-ai-scheme` 代理
- ❌ 修改 jingcai `/api/v1/tasks` 契约
- ❌ 修改 Gateway 路由

---

## 10. 关联 STATE

见 [`STATE-M2-内容生产-amphipoda对齐增量.md`](./STATE-M2-内容生产-amphipoda对齐增量.md)

---

## 11. ADR-077 增量（2026-09-02）

- 工作任务 confirm **afterCommit** 调用本 generate：组包字段 **仅** `authorId` / `matchScheme` / `matchName` / `documentType` / `isPaywall`，不新增其它 payload。
- 自动 Job 与手工重试 **同一** generate 内部组包（`WorkTaskConfirmJingcaiJob`）。
- Slice D 失败重试薄接口：`POST /ops/content/{id}/retry-ai-generate`（无新请求字段；重置 `QUEUED` 后再入队 Job）。
- `isPaywall` 不是表列。
