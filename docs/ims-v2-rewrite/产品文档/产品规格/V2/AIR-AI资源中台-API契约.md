# AIR - AI 资源中台 API 契约

> **模块范围**：20 AI 资源中台（V2.2 批次，第 19~20 周 AIR-P0 先行）——SKILL-001~004 / EXPERT-001~003 / KNOW-001~00**6** / KEY-001~004 / MCP-001~003 / KB-001~00**3**，BR-019~035。**本期（v2.6.32）知识库为「文件管理期」**：KNOW-003 知识检索 与 KB-001 RAGFlow 底座 **已移出范围（不做）**；底座为 IMS 服务端文件目录（KB-003，`KbProvider=LOCAL`）。
> **权威依据**：《IMS-模块20-AI资源中台PRD-V1.md》V1.2.3；《共享技术规范-数据库与API.md》7.2（12 表）/8.1（MCP 网关例外行）/8.3；《全局开发规范.md》第 3.2 章 AIR 段（错误码口径）、第 4 章 AIR 段（权威枚举）。
> **全局约定**：管理端响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`secret_level → secretLevel`）。
> **端点边界**：管理端统一前缀 `/admin-api/ims/air/`（SSO Token 认证，走芋道权限体系）；**MCP 网关为独立端点 `/ims/mcp`**（非 admin-api 前缀，Key 自认证，响应遵循 MCP 协议格式而非 `{code:0}` 包装——共享规范 8.1 MCP 网关例外行）。两者并存、互不混用。
> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。

---

## 1. API 总览表（共 47 个端点：管理端 42 个注册路由 + MCP 网关 5 行（4 工具 + 1 初始化/tools/list）；v2.6.31 由 43 扩至 51，v2.6.32 收敛至 47）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/air/overview` | 模块统计卡（技能/专家/知识库/Key/调用） | R11/R1/R4/R9 |
| 2 | GET | `/admin-api/ims/air/skill/page` | 技能分页列表 | R11/R1/R4（本部门）/R9 |
| 3 | GET | `/admin-api/ims/air/skill/{id}` | 技能详情（含版本历史） | 同上 |
| 4 | POST | `/admin-api/ims/air/skill` | 新增技能（提交即进审核流） | R11（主责）/R1 |
| 5 | PUT | `/admin-api/ims/air/skill/{id}` | 编辑技能（生成新版本重审） | R11/R1 |
| 6 | POST | `/admin-api/ims/air/skill/{id}/audit` | 技能审核（通过/驳回/退回修改） | R11/R1 |
| 7 | PUT | `/admin-api/ims/air/skill/{id}/status` | 技能停用/启用 | R11/R1 |
| 8 | POST | `/admin-api/ims/air/skill/grant` | 技能授权（三维/全员可见） | R11/R1 |
| 9 | DELETE | `/admin-api/ims/air/skill/grant/{grantId}` | 收回技能授权 | R11/R1 |
| 10 | GET | `/admin-api/ims/air/expert/page` | 专家包分页列表 | R11/R1/R4（本部门）/R9 |
| 11 | GET | `/admin-api/ims/air/expert/{id}` | 专家包详情（含组装预览结构） | 同上 |
| 12 | POST | `/admin-api/ims/air/expert` | 新建专家包 | R11（主责）/R1 |
| 13 | PUT | `/admin-api/ims/air/expert/{id}` | 编辑专家包（新版本留档） | R11/R1 |
| 14 | POST | `/admin-api/ims/air/expert/grant` | 专家授权（三维/角色模板预置） | R11/R1/R4（本部门审批） |
| 15 | DELETE | `/admin-api/ims/air/expert/grant/{grantId}` | 收回专家授权 | R11/R1 |
| 16 | GET | `/admin-api/ims/air/kb/tree` | 知识目录树（库→分类，库内两级树） | R11/R1/R4/R9 |
| 17 | GET | `/admin-api/ims/air/kb/page` | 知识库/文档分页列表 | R11/R1/R4（本部门）/R9 |
| 18 | POST | `/admin-api/ims/air/kb` | 新建知识库 | R11（主责）/R1 |
| 19 | POST | `/admin-api/ims/air/kb/doc/upload` | 文件上传入库（服务端上传回执 `fileKey` 提交） | R11/R1/R8（本人提交审批） |
| 20 | POST | `/admin-api/ims/air/kb/doc/import-url` | URL 导入入库 | R11/R1/R8 |
| 21 | POST | `/admin-api/ims/air/kb/doc/import-text` | 粘贴文本入库（v2.6.31） | R11/R1/R8 |
| 22 | GET | `/admin-api/ims/air/kb/category/tree` | 分类树（库内两级树，KNOW-005） | R11/R1/R4/R9 |
| 23 | POST | `/admin-api/ims/air/kb/category` | 新增分类（KNOW-005） | R11/R1 |
| 24 | PUT | `/admin-api/ims/air/kb/category/{id}` | 重命名分类（KNOW-005） | R11/R1 |
| 25 | PUT | `/admin-api/ims/air/kb/category/sort` | 分类同级排序（KNOW-005） | R11/R1 |
| 26 | DELETE | `/admin-api/ims/air/kb/category/{id}` | 删除分类（条目改挂根，KNOW-005） | R11/R1 |
| 27 | GET | `/admin-api/ims/air/kb/transfer-source` | 系统资料转入·源条目（KNOW-006） | R11/R1/R8 |
| 28 | POST | `/admin-api/ims/air/kb/doc/import-from` | 系统资料转入入库（TRAIN/PERF/CONTENT，KNOW-006） | R11/R1/R8 |
| 29 | POST | `/admin-api/ims/air/kb/doc/audit` | 入库审批（通过→已发布） | R11/R1 |
| 30 | POST | `/admin-api/ims/air/kb/grant` | 知识库授权（三维） | R11/R1 |
| 31 | POST | `/admin-api/ims/air/key/generate` | 生成 Key（一次性明文响应） | R11/R1 |
| 32 | GET | `/admin-api/ims/air/key/page` | Key 分页列表（掩码） | R11/R1/R4（本部门）/R9 |
| 33 | POST | `/admin-api/ims/air/key/{id}/revoke` | 吊销 Key（不可恢复） | R11/R1 |
| 34 | POST | `/admin-api/ims/air/key/{id}/freeze` | 冻结 Key | R11/R1 |
| 35 | POST | `/admin-api/ims/air/key/{id}/unfreeze` | 解冻 Key | R11/R1 |
| 36 | POST | `/admin-api/ims/air/key/{id}/renew` | 换新 Key（旧 Key 宽限 24h） | R11/R1 |
| 37 | GET | `/admin-api/ims/air/key/config-snippet` | 客户端 MCP 配置 JSON（按 client 类型） | R11/R1/R8（本人） |
| 38 | PUT | `/admin-api/ims/air/key/whitelist` | Key 白名单维护（P1，受总开关约束） | R11/R1 |
| 39 | GET | `/admin-api/ims/air/mcp/audit-log` | MCP 调用审计日志（分页） | R9（主责）/R1/R11/R4（本部门） |
| 40 | GET | `/admin-api/ims/air/usage/stat` | 用量统计（按人/按工具/按日） | R9/R1/R11/R4 |
| 41 | GET | `/admin-api/ims/air/sys-param` | 模块系统参数查询 | R1 |
| 42 | PUT | `/admin-api/ims/air/sys-param` | 模块系统参数更新（含白名单总开关） | R1 |
| G1 | POST | `/ims/mcp` | MCP 初始化 / tools/list（Streamable HTTP + SSE） | Key 认证（`Authorization: Bearer air-xxx` 或 URL `?key=`） |
| G2 | POST | `/ims/mcp` | 工具调用 `skills.list` | Key 认证（按 ims_skill_grant 过滤） |
| G3 | POST | `/ims/mcp` | 工具调用 `skills.get` | Key 认证（未授权 403） |
| G4 | POST | `/ims/mcp` | 工具调用 `experts.list` | Key 认证（按 ims_expert_grant 过滤） |
| G5 | POST | `/ims/mcp` | 工具调用 `experts.assemble` | Key 认证（本期不返回 knowledge_context） |

> 说明：G1~G5 为 MCP 协议层工具端点行（统一 `POST /ims/mcp`，JSON-RPC 2.0 method 分发；`tools/list` 返回四工具定义），与 McpToolName **四工具**对齐；**豁免 `{code:0}` 包装**，按 MCP 协议错误格式返回，限流超限返回 HTTP 429（共享规范 8.1 例外行）。总览表计 **42 个管理端注册路由（#1~#42）+ 5 个网关端点行（G1~G5）**；G1~G5 逻辑上为 1 个物理端点 `POST /ims/mcp` 承载 4 个工具调用 + 1 个初始化/tools/list 能力。
>
> **v2.6.32 变更（文件管理期）**：删除原 #31 `POST /air/kb/ragflow-check`、#32 `GET /air/kb/ragflow-health`（底座巡检）与 MCP `knowledge.search`/`knowledge.get`（G6/G7）→ 管理端 **44 → 42**、总端点 **51 → 47**、MCP 工具 **6 → 4**。
> **v2.6.31 变更**：知识域由 9 端点扩为 17 端点（新增 import-text、分类 5 端点、transfer-source、import-from）；管理端路由 36 → 44。

---

## 2. 接口明细

### 2.1 技能域（/air/skill，SKILL-001/002/003/004）

#### 2.1.1 GET /admin-api/ims/air/overview — 模块统计卡

**响应** `data`：

```typescript
interface AirOverviewVO {
  skillCnt: number; expertCnt: number; kbCnt: number;   // 技能/专家/知识库总数
  publishedCnt: number;            // 三类资产已发布合计
  activeKeyCnt: number;            // 启用中 Key（ApiKeyStatus.ACTIVE）
  totalCallCnt: number;            // 累计调用（ims_mcp_log 聚合）
  todayCallCnt: number; p95Ms: number;                  // 今日调用 / P95
}
```

#### 2.1.2 GET /admin-api/ims/air/skill/page — 技能分页列表

**请求**（Query）：`PageParam` + `{ skillName?: string; category?: string; status?: SkillStatus; auditStatus?: AirAuditStatus; ownerUserId?: number }`

**响应** `data`：`PageResult<SkillVO>`（结构见页面规格 P1 第 3 节；R4 按授权对象含本部门过滤，R9 全量只读）。

#### 2.1.3 GET /admin-api/ims/air/skill/{id} — 技能详情（含版本历史）

**请求**（Path）：`{ id: number }`

**响应** `data`：

```typescript
interface SkillDetailVO extends SkillVO {
  versions: Array<{               // 版本历史（ims_skill_ver 倒序，最新在前）
    ver: string;                  // 语义化版本号
    mdHash: string;               // SKILL.md 内容哈希（防篡改对账）
    auditStatus: AirAuditStatus;  // 版本独立审核状态
    riskLevel: 'P0' | 'P1' | 'P2';
    createdAt: string; auditedAt?: string; auditNote?: string;
  }>;
  grants: Array<{                 // 当前生效授权（ims_skill_grant）
    grantId: number; grantType: AirGrantType; grantObjId: number;
    grantName: string; expireAt?: string; status: AirGrantStatus;
  }>;
  scanResult: { riskLevel: 'P0' | 'P1' | 'P2'; dependencies: string[]; dangerousCommands: string[]; outboundUrls: string[] };
}
```

**权限**：R11/R1 全量；R4 本部门（授权对象含本部门）；R9 全量只读。**错误码**：1002（不存在）、1008（无数据权限）。

#### 2.1.4 POST /admin-api/ims/air/skill — 新增技能（提交即进审核流，BR-025/026）

**请求**：

```typescript
interface SkillCreateReq {
  skillName: string;               // 必填 ≤128 字
  category: string;                // 必填
  ver: string;                     // 必填语义化版本
  source: 'MARKET' | 'UPLOAD' | 'URL';   // SKILL-001 三来源
  sourceRef?: string;              // UPLOAD=fileKey / URL=地址 / MARKET=市场标识
  desc: string;                    // 必填
  mdContent: string;               // 必填，SKILL.md 全文
  ownerUserId: number;             // 必填
  clientToken: string;             // 幂等
}
```

**响应** `data`：`SkillVO & { scanResult: { riskLevel: 'P0'|'P1'|'P2'; dependencies: string[]; dangerousCommands: string[]; outboundUrls: string[] } }`——提交后服务端自动执行安全扫描（SKILL-002），`ims_skill` 落 `PENDING_AUDIT`、`ims_skill_ver` 落 `PENDING`。

**错误码**：1001（参数校验：source 与 sourceRef 不匹配、版本号非法）。

#### 2.1.5 PUT /admin-api/ims/air/skill/{id} — 编辑技能（新版本重审）

**请求**：`SkillCreateReq`（同 2.1.3）→ **响应**：`SkillVO`（`ims_skill_ver` 追加新版本 `PENDING`，md_hash 重算；授权关系保持绑定旧已发布版本，新版本过审自动切绑）。

#### 2.1.6 POST /admin-api/ims/air/skill/{id}/audit — 技能审核（BR-025）

**请求**：

```typescript
interface SkillAuditReq {
  approve: boolean;                // true 通过 / false 驳回
  rejectMode?: 'REJECT' | 'RETURN';   // 驳回口径：REJECT=永久拒绝（P0 风险必用，SkillStatus.REJECTED）/ RETURN=退回修改（P1/P2 可用，回 PENDING_AUDIT 重审）
  auditNote?: string;              // 驳回/退回时必填
}
```

**响应** `data`：`{ id: number; status: SkillStatus; auditStatus: AirAuditStatus; auditedAt: string }`

**业务约束**：`riskLevel=P0` 时 `approve=true` 请求服务端拒绝（1001，msg 指明 BR-025 永久拒绝）；审核通过 → `PUBLISHED` 方可授权分发。

**错误码**：1001（P0 风险拦截/意见缺失/状态非法如重复审核）。

#### 2.1.7 PUT /admin-api/ims/air/skill/{id}/status — 技能停用/启用

**请求**（Body）：`{ status: 'ENABLED' | 'DISABLED' }`（EnableStatus，资产启停复用全局枚举；DISABLED → SkillStatus.DISABLED）→ **响应**：`data: null`。停用后连接器 `skills.list/get` 即时不可见。

#### 2.1.8 POST /admin-api/ims/air/skill/grant — 技能授权（SKILL-003，BR-024）

**请求**：

```typescript
interface SkillGrantReq {
  skillId: number;
  grantType: AirGrantType;         // DEPT / ROLE / PERSON
  grantId: number;                 // 部门/角色/人员 ID（主数据源 01 权限管理，BR-031）
  expireAt?: string;
  allStaff?: boolean;              // 全员可见快捷开关
}
```

**响应** `data`：`{ grantId: number; status: AirGrantStatus; syncEventId: string }`（`ims_air_event` 落事件，事件驱动同步生效延迟 <5 分钟，BR-024）。

**错误码**：1001（技能非 PUBLISHED 拦截，msg 指明 BR-025；授权对象不存在）、1008（无数据权限）。

#### 2.1.9 DELETE /admin-api/ims/air/skill/grant/{grantId} — 收回授权

**响应**：`data: null`（`AirGrantStatus.ACTIVE → REVOKED`，事件驱动同步；逻辑保留可审计）。

### 2.2 专家域（/air/expert，EXPERT-001/002/003）

#### 2.2.1 GET /admin-api/ims/air/expert/page — 专家包分页列表

**请求**（Query）：`PageParam` + `{ expertName?: string; status?: EnableStatus; ownerUserId?: number }` → **响应** `data`：`PageResult<ExpertVO>`（结构见页面规格 P2 第 3 节）。

#### 2.2.2 POST /admin-api/ims/air/expert — 新建专家包（EXPERT-001）

**请求**：

```typescript
interface ExpertSaveReq {
  expertCode: string;              // EXP+4 位流水
  expertName: string;              // 必填 ≤128 字
  scene: string;                   // 必填适用场景
  systemPrompt: string;            // 必填非空（TEXT）
  skillIds: number[];              // 仅 PUBLISHED 技能（服务端校验 BR-025 联动）
  kbIds: number[];                 // 挂载知识库（授权后受 BR-030 密级过滤）
  toolWhitelist: McpToolName[];    // ⊆ 四工具（本期）
  ownerUserId: number;
  clientToken?: string;
}
```

**响应** `data`：`ExpertVO`（`ims_expert` 落 skill_ids/kb_ids/tool_whitelist JSON）。

**错误码**：1001（挂载技能含非 PUBLISHED、toolWhitelist 非法值——msg 指明技能名/工具名）。

#### 2.2.3 PUT /admin-api/ims/air/expert/{id} — 编辑专家包

**请求**：`ExpertSaveReq` → **响应**：`ExpertVO`（ver 自增，旧版本留档可查）。

#### 2.2.4 GET /admin-api/ims/air/expert/{id} — 详情（含组装预览）

**响应** `data`：`ExpertVO & { assemblePreview: ExpertAssemblePreviewVO }`（system_prompt + 技能引用；**本期无检索，不返回 knowledgeContext 字段**；组装预览为只读结构，实际组装下发经 MCP `experts.assemble`，D2/BR-034：网关不执行模型）。

#### 2.2.5 POST /admin-api/ims/air/expert/grant — 专家授权（EXPERT-002，BR-024/030）

**请求**：

```typescript
interface ExpertGrantReq {
  expertId: number;
  grantType: AirGrantType;
  grantId: number;
  expireAt?: string;
  roleTemplateId?: number;         // 角色模板预置（如「直播运营岗模板」默认带 3 个专家）
}
```

**响应** `data`：`{ grantId: number; status: AirGrantStatus; syncEventId: string }`（授权含包内全部技能与知识库权限；**本期知识库仅文件管理、无检索片段**；BR-030 已不再生效（检索功能已移除））。

**错误码**：1001（授权对象不存在/专家未发布）、1008。

### 2.3 知识域（/air/kb，KNOW-001/002/004/005/006、KB-002/003；KNOW-003、KB-001 已移除）

> **本期（文件管理期）**：知识文档正文存 IMS 服务端文件目录（`file_key`，相对路径 · 本期不上对象存储，见《全局开发规范》§6.3），审批通过即 `PUBLISHED`，**无 `PARSING` 态、无检索端点、无底座巡检端点**。检索（KNOW-003）与 RAGFlow 底座（KB-001）已移出范围（不做）。

#### 2.3.1 GET /admin-api/ims/air/kb/tree — 知识目录树

**响应** `data`：`KbTreeVO[]`（**知识库 → 分类两级树**，`children: KbTreeNodeVO[]` 取自 `ims_kb_category`；v2.6.31 由「RAGFlow 数据集分组」改为 **IMS 侧库内两级树 SSOT**）。

#### 2.3.2 GET /admin-api/ims/air/kb/page — 知识库/文档分页列表

**请求**（Query）：`PageParam` + `{ kbId?: number; categoryId?: number; keyword?: string; secretLevel?: KnowledgeSecretLevel; sourceType?: string; docStatus?: 'DRAFT'|'PENDING'|'PUBLISHED' }` → **响应** `data`：`PageResult<KbVO>`（provider 固定 `LOCAL`，KbProvider；**v2.6.32 去 ext_id（RAGFlow 数据集 ID）与向量块数**）。

#### 2.3.3 POST /admin-api/ims/air/kb — 新建知识库（KNOW-001）

**请求**：

```typescript
interface KbCreateReq {
  kbName: string;                  // 必填 ≤128 字
  desc?: string;
  secretLevel: KnowledgeSecretLevel;   // 必填四选（PUBLIC/INTERNAL/CONFIDENTIAL/TOP_SECRET）
  ownerUserId: number;
  clientToken?: string;
}
```

**响应** `data`：`KbVO`（服务端经 KnowledgeProvider（**本期 LocalProvider**）建立 IMS 侧知识库；BR-032 多主体 tenant_id/entity_id 落库）。

**错误码**：1001（参数校验/密级非法值）。

#### 2.3.4 POST /admin-api/ims/air/kb/doc/upload — 文件上传入库（KNOW-002）

**请求**：

```typescript
interface KbDocUploadReq {
  kbId: number;
  categoryId?: number;             // 目标分类（库内两级树；缺省挂根）
  fileKeys: string[];              // FileUpload 服务端上传回执（fileKey 相对路径；PDF/DOCX/MD/HTML/Excel）
  secretLevel?: KnowledgeSecretLevel;   // 缺省继承库密级；不得低于库密级
}
```

**响应** `data`：`{ docIds: number[]; auditStatus: AirAuditStatus[] }`（全部 `PENDING`，进入入库审批流；content_hash/`file_key`/file_size/content_type 落 `ims_kb_doc`）。

**错误码**：1001（文件类型/密级低于库密级拦截）。

#### 2.3.5 POST /admin-api/ims/air/kb/doc/import-url — URL 导入入库

**请求**（Body）：`{ kbId: number; categoryId?: number; urls: string[]; secretLevel?: KnowledgeSecretLevel }` → **响应**：同 2.3.4。

#### 2.3.6 POST /admin-api/ims/air/kb/doc/import-text — 粘贴文本入库（v2.6.31 新增）

**请求**：

```typescript
interface KbDocImportTextReq {
  kbId: number;
  categoryId?: number;
  title: string;                   // 必填 ≤128 字
  content: string;                 // 必填，纯文本/Markdown 正文（落 source_type=TEXT）
  secretLevel?: KnowledgeSecretLevel;
}
```

**响应** `data`：同 2.3.4（`source_type=TEXT`）。

**错误码**：1001（title/content 空）。

#### 2.3.7 GET /admin-api/ims/air/kb/category/tree — 分类树（库内两级树，KNOW-005）

**请求**（Query）：`{ kbId: number }` → **响应** `data`：`KbTreeNodeVO[]`（一级分类含 `children` 二级；`docCount` 为分类下知识条目数）。

#### 2.3.8 POST /admin-api/ims/air/kb/category — 新增分类（KNOW-005）

```typescript
interface KbCategoryReq {
  kbId: number;                    // 必选
  parentId?: number;               // 0/空=一级分类；否则二级（仅两级）
  categoryName: string;            // 必填 ≤64 字
  sortNo?: number;                 // 缺省追加末尾
}
```

**响应** `data`：`{ categoryId: number; sortNo: number }`。**错误码**：1001（同名 / 超出两级深度）。

#### 2.3.9 PUT /admin-api/ims/air/kb/category/{id} — 重命名分类（KNOW-005）

**请求**（Body）：`{ kbId: number; categoryName: string }` → **响应** `data`：`{ categoryId: number }`。**错误码**：1001（同名）。

#### 2.3.10 PUT /admin-api/ims/air/kb/category/sort — 同级排序（KNOW-005）

**请求**（Body）：`{ kbId: number; orderedIds: number[] }`（同级分类 ID 升序）→ **响应** `data`：`{ updated: number }`。

#### 2.3.11 DELETE /admin-api/ims/air/kb/category/{id} — 删除分类（KNOW-005）

**请求**（Query）：`{ kbId: number; moveToRoot?: boolean }`（含条目时须显式 `moveToRoot=true`，条目改挂根分类）→ **响应** `data`：`{ categoryId: number; movedDocCount: number }`。

**错误码**：1001（`moveToRoot` 缺失且分类非空）。

#### 2.3.12 GET /admin-api/ims/air/kb/transfer-source — 系统资料转入 · 源条目查询（KNOW-006）

**请求**（Query）：`{ sourceType: 'TRAIN'|'PERF'|'CONTENT'; keyword?: string; sourceCategory?: string; pageNo?: number; pageSize?: number }`
- `TRAIN` → 培训资料库（TRAIN-001，`ims_train_material`，路由 `/ims/train/material`）
- `PERF` → 绩效考核模板（PERF 考核方案，`/ims/perf/scheme`）
- `CONTENT` → 内容记录（CONTENT 内容管理，`/ims/content/list`）

**响应** `data`：`PageResult<KbTransferSourceItemVO>`（`imported` 标记已转入去重）。

#### 2.3.13 POST /admin-api/ims/air/kb/doc/import-from — 系统资料转入入库（KNOW-006）

**请求**：

```typescript
interface KbDocTransferReq {
  sourceType: 'TRAIN' | 'PERF' | 'CONTENT';
  sourceIds: number[];             // 按条目勾选（至少 1 条）
  targetKbId: number;              // 必选
  targetCategoryId?: number;
  secretLevel?: KnowledgeSecretLevel;   // 缺省取源资料密级
  clientToken?: string;            // 幂等：同 sourceType+sourceId 去重
}
```

**响应** `data`：`{ docIds: number[]; auditStatus: AirAuditStatus[] }`（落 `source_type=TRAIN/PERF/CONTENT` + `source_ref=sourceId`；全部 `PENDING`）。

**错误码**：1001（sourceIds 空 / 目标库必填）、403（无源模块读权限）。

#### 2.3.14 POST /admin-api/ims/air/kb/doc/audit — 入库审批（入库审批中 → 已发布）

**请求**：

```typescript
interface KbDocAuditReq {
  docId: number;
  approve: boolean;                // true → PUBLISHED（正文写入服务端文件目录 file_key 即发布；无解析/向量化中间态）
  auditNote?: string;              // 驳回必填 → DRAFT
}
```

**响应** `data`：`{ docId: number; auditStatus: AirAuditStatus; docStatus: 'DRAFT'|'PUBLISHED' }`

**错误码**：1001（重复审批/意见缺失）。

#### 2.3.15 POST /admin-api/ims/air/kb/grant — 知识库授权（BR-024）

**请求**（Body）：`{ kbId: number; grantType: AirGrantType; grantId: number; expireAt?: string }` → **响应** `data`：`{ grantId: number; status: AirGrantStatus; syncEventId: string }`。机密/绝密库授权后，密级控制模块内视图与授权范围（**原检索期 BR-027 连接器侧全文拦截已移除**）。

> **v2.6.32 移除的端点**：原 2.3.16 `POST /air/kb/ragflow-check`（底座健康巡检）、2.3.17 `GET /air/kb/ragflow-health`（底座健康查询）——**本期无 RAGFlow 底座**，KB-001 已移除。

### 2.4 Key 域（/air/key，KEY-001/002/003/004、MCP-002）

#### 2.4.1 POST /admin-api/ims/air/key/generate — 生成 Key（KEY-001，BR-019/020）

**请求**：

```typescript
interface ApiKeyGenerateReq {
  userId: number;                  // 归属人员（主数据源 01，BR-031）
  deviceName: string;              // 设备用途（默认「个人通用」）
  qpmLimit?: number;               // 缺省 60（BR-029）
  expireAt: string;                // 必填
  ipWhitelist?: string[];          // P1：仅总开关开启时可填（BR-035）
  clientToken: string;             // 幂等
}
```

**响应** `data`（**仅此一次返回明文**，BR-020）：

```typescript
interface ApiKeyPlainVO {
  keyId: number;
  plainKey: string;                // air- 前缀明文；服务端仅存 SHA-256 key_hash
  configSnippets: Record<'CURSOR'|'CLAUDE_DESKTOP'|'WORKBUDDY'|'GENERIC', string>;
                                  // 各客户端 mcpServers JSON 配置串（MCP-002 接入引导）
}
```

**业务约束**：一人默认一把 ACTIVE Key（已有时须走换新，BR-019）；设备维度最多 3 把；生成即写 `ims_air_event`（事件总线可追踪）。

**错误码**：1001（设备超 3 把/一人多把默认约束，msg 指明 BR-019；白名单总开关关闭时携带 ipWhitelist）。

#### 2.4.2 GET /admin-api/ims/air/key/page — Key 分页列表（掩码）

**请求**（Query）：`PageParam` + `{ userName?: string; status?: ApiKeyStatus; whitelistOn?: boolean }` → **响应** `data`：`PageResult<ApiKeyVO>`（keyMask 掩码；R4 本部门过滤、R8 本人仅见自己）。

#### 2.4.3 POST /admin-api/ims/air/key/{id}/revoke — 吊销（BR-023 联动）

**请求**（Body）：`{ reason?: string }` → **响应**：`data: null`。`ApiKeyStatus → REVOKED`，即时生效不可恢复；钉钉离职事件自动触发本动作（与 BR-015 离职归还同批事件处理，无需人工）。

#### 2.4.4 POST /admin-api/ims/air/key/{id}/freeze — 冻结 / unfreeze — 解冻（BR-022/033）

**请求**（Body）：`{ reason?: string }` → **响应**：`data: null`。`ACTIVE ↔ FROZEN`；触发源：手动 / 90 天未用（BR-022，冻结前 7 天消息中心提醒）/ 认证失败 10 次锁定（BR-033，通知本人与 R9）。

#### 2.4.5 POST /admin-api/ims/air/key/{id}/renew — 换新（BR-020）

**请求**（Body）：`{ deviceName?: string; expireAt?: string; qpmLimit?: number }` → **响应**：`ApiKeyPlainVO`（同 2.4.1 一次性明文；旧 Key 宽限 24h 后自动 REVOKED）。

#### 2.4.6 GET /admin-api/ims/air/key/config-snippet — 客户端配置 JSON（MCP-002）

**请求**（Query）：`{ client: 'CURSOR'|'CLAUDE_DESKTOP'|'WORKBUDDY'|'GENERIC'; keyId?: number }` → **响应** `data`：`{ snippet: string; endpoint: string; authHint: string }`（mcpServers JSON 配置串；R8 查询本人 Key 时 keyId 限本人）。

#### 2.4.7 PUT /admin-api/ims/air/key/whitelist — 白名单维护（KEY-004，P1，BR-035）

**请求**（Body）：`{ keyId: number; ipWhitelist: string[] }` → **响应**：`data: null`。**受系统参数 `air.key.ip_whitelist.enabled` 总开关控制（默认关闭）**：总开关开启时白名单外调用返回 403 并告警；关闭时配置仅预存不生效。

**错误码**：1001（IP 段格式非法）。

### 2.5 审计与用量域（/air/mcp、/air/usage，BR-028/029）

#### 2.5.1 GET /admin-api/ims/air/mcp/audit-log — 调用审计日志（BR-028）

**请求**（Query）：`PageParam` + `{ keyword?: string; tool?: McpToolName; result?: 'SUCCESS'|'FAIL'; keyId?: number; dateRange?: [string, string] }` → **响应** `data`：`PageResult<McpLogVO>`（数据源 `ims_mcp_log`，按月分区保留 180 天；R9 全量、R4 本部门、R11 本模块资产维度）。

#### 2.5.2 GET /admin-api/ims/air/usage/stat — 用量统计

**请求**（Query）：`{ by: 'PERSON'|'TOOL'|'DAY'; dateRange?: [string, string] }` → **响应** `data`：

```typescript
// by=DAY
Array<{ statDate: string; callCnt: number; tokenCnt: number }>;    // 来源 ims_air_usage（日聚合）
// by=PERSON
Array<{ userId: number; userName: string; deptName: string; callCnt: number; tokenCnt: number }>;
// by=TOOL（SKILL-004/EXPERT-003 口径：成功率与平均耗时）
Array<{ tool: McpToolName; callCnt: number; failCnt: number; avgCostMs: number }>;
```

### 2.6 系统参数域（/air/sys-param，D3）

#### 2.6.1 GET /admin-api/ims/air/sys-param — 模块系统参数查询

**响应** `data`：`Array<{ paramKey: string; paramValue: string; remark?: string }>`（含 `air.key.ip_whitelist.enabled`（默认 false，D3/BR-035）、`air.kb.provider`（**默认 LOCAL**，V1.2.3 D1；原 RAGFLOW 已作废）等；参数中心复用 01 模块）。

#### 2.6.2 PUT /admin-api/ims/air/sys-param — 模块系统参数更新

**请求**（Body）：`{ params: Array<{ paramKey: string; paramValue: string }> }` → **响应**：`data: null`。仅 R1；白名单总开关开启/关闭即时生效并写 `ims_air_event`。

### 2.7 MCP 网关（独立端点 /ims/mcp，MCP-001，BR-021/023/024/028/029/033/034/035）

> **协议与豁免**：Streamable HTTP + SSE 兼容；JSON-RPC 2.0（`initialize` / `tools/list` / `tools/call`）；**豁免 `{code:0}` 包装**，结果与错误均按 MCP 协议格式返回（共享规范 8.1 例外行）。认证：Header `Authorization: Bearer air-xxx` 优先，URL `?key=air-xxx` 兼容（Cursor 等客户端 Header 支持差异兜底）。
> **网关不执行 LLM 与 Skill（D2/BR-034）**：experts.assemble 只做 Prompt 组装下发，执行一律在客户端完成。

#### 2.7.1 鉴权链路（每次调用，BR-021）

```
验签（查 key_hash → keyId）→ Key 状态（REVOKED/FROZEN → 401）
→ 白名单校验（总开关开启时，白名单外 → 403 + 告警，BR-035）
→ 人员在职状态（离职 → 403，BR-023）
→ 资源授权校验（ims_*_grant，缓存 60s 不快照，BR-021/024）
→ QPM 限流（超限 → HTTP 429 + 告警，BR-029）
→ 执行工具 → 密级过滤输出（BR-027/030，**本期无检索片段，已不再生效（检索功能已移除）**）
→ 写 ims_mcp_log 审计（BR-028）→ 返回
```

认证失败连续 10 次（10 分钟内）自动冻结该 Key 并通知本人与 R9（BR-033）。

#### 2.7.2 tools/list — 四工具定义（McpToolName）

**响应**（MCP 协议格式，节选）：**固定四工具** `skills.list / skills.get / experts.list / experts.assemble`（值域与《全局开发规范.md》第 4 章 McpToolName 逐字一致），各含 name/description/inputSchema。

#### 2.7.3 skills.list — 本人可见技能

**入参**：`{ category?: string; keyword?: string }` → **出参**：`Array<{ code: string; name: string; desc: string; ver: string }>`（按 `ims_skill_grant` 过滤，仅 `AirGrantStatus.ACTIVE` 且技能 `PUBLISHED`）。

#### 2.7.4 skills.get — 技能全文

**入参**：`{ code: string }` → **出参**：`{ code: string; ver: string; mdContent: string; usageNote: string }`（SKILL.md 全文 + 使用说明；未授权返回 403）。

#### 2.7.5 experts.list — 本人可见专家

**入参**：`—` → **出参**：`Array<{ code: string; name: string; scene: string; ver: string; toolWhitelist: McpToolName[] }>`（按 `ims_expert_grant` 过滤）。

#### 2.7.6 experts.assemble — 专家组装包下发（D2/BR-034）

**入参**：`{ code: string; message: string }` → **出参**：

```typescript
interface ExpertAssemblePackage {
  systemPrompt: string;
  skillRefs: Array<{ code: string; md: string }>;
  // knowledgeContext 字段已移除：本期不返回该字段（语义检索已整体移出范围）
  guidelines: string;
}
```

**说明**：**本期（文件管理期）无检索，不返回 `knowledgeContext` 字段**；BR-030（片段密级过滤/降级摘要）已移除（检索功能整体移出）。组装包下发后由**客户端 LLM 执行**，网关不运行任何模型（BR-034）。

> **v2.6.32 移除的 MCP 工具**：原 2.7.7 `knowledge.search`（知识检索）、2.7.8 `knowledge.get`（文档内容）——**本期不做检索**，KNOW-003 已移除。

---

## 3. BR 映射表与状态机

### 3.1 BR 映射表（BR-019~035，以 PRD V1.2.3 第 3 章为准，逐条勾稽）

| BR | 规则摘要 | API 落点 |
|----|---------|----------|
| BR-019 | 一人默认一把 Key；设备 ≤3 把；Key 绑定唯一人员 | 2.4.1 generate 服务端校验 |
| BR-020 | 仅一次明文（存哈希）；丢失只能换新 | 2.4.1/2.4.5（plainKey 一次性响应）、2.4.2 掩码 |
| BR-021 | 动态鉴权（在职+授权实时校验，缓存 60s） | 2.7.1 鉴权链路 |
| BR-022 | 90 天未用自动冻结，前 7 天提醒 | 2.4.4 freeze（触发源说明） |
| BR-023 | 钉钉离职事件立即吊销 | 2.4.3 revoke + 2.7.1 在职校验（403） |
| BR-024 | 权限变更事件驱动同步 <5 分钟 | 2.1.8/2.2.5/2.3.15 grant（syncEventId → ims_air_event） |
| BR-025 | 技能过审方可分发；P0 风险永久拒绝 | 2.1.6 audit（P0 拦截）+ 2.1.8 grant 状态校验 |
| BR-026 | 技能安装到可分发 <10 分钟 | 2.1.4 提交即扫描（自动项即时） |
| BR-027 | 机密/绝密不出库（标题+100字摘要+库内链接） | **本期仅密级元数据标记**；连接器侧全文拦截已移除（原 2.7.7/2.7.8） |
| BR-028 | 每次调用全量审计留痕，保留 180 天 | 2.7.1 写 ims_mcp_log、2.5.1 audit-log |
| BR-029 | 默认 QPM 60，超限 429 告警，可按人调整 | 2.4.1 qpmLimit 缺省 + 2.7.1 限流 |
| BR-030 | assemble 片段密级过滤/降级摘要 | 2.7.6 knowledgeContext（**本期不返回**；已不再生效（检索功能已移除）） |
| BR-031 | 组织/授权数据以 01 权限管理为准 | 2.1.8/2.2.5/2.3.15/2.4.1 授权对象主数据约束 |
| BR-032 | 多主体预留 tenant_id/entity_id | 2.3.3 等落库口径（含 ims_kb_category，BR-016 口径） |
| BR-033 | 失败 10 次/10 分钟自动冻结并通知 | 2.7.1 认证失败锁定 |
| BR-034 | 网关不执行 LLM/Skill（纯组装下发） | 2.7.6（D2） |
| BR-035 | 白名单总开关默认关；白名单外 403 告警 | 2.4.7 whitelist + 2.7.1 白名单校验 + 2.6.2 总开关 |

### 3.2 状态机

**技能（ims_skill.status，SkillStatus）**：

```
PENDING_AUDIT ──审核通过──▶ PUBLISHED ──停用──▶ DISABLED ──启用──▶ PUBLISHED
      │                        │
      ├──退回修改（P1/P2）──▶ PENDING_AUDIT（重新提交）
      └──永久拒绝（P0 风险）──▶ REJECTED（终态，不可再提交，BR-025）
PUBLISHED ──编辑新版本──▶ 新版本 PENDING_AUDIT（旧版本授权保持，过审切绑）
```

**知识文档（ims_kb_doc.audit_status，AirAuditStatus + 入库状态）**：

```
PENDING（入库审批中，来源=FILE/URL/TEXT/TRAIN/PERF/CONTENT）──审批通过──▶ PUBLISHED（已发布，正文入服务端文件目录）
PENDING ──驳回（意见必填）──▶ DRAFT（草稿，修改后重新提交）
```

> **v2.6.32**：去原 `PARSING`（RAGFlow 解析向量化）中间态——审批通过即 `PUBLISHED`。

**人员 Key（ims_api_key.status，ApiKeyStatus）**：

```
ACTIVE ──手动冻结 / 90 天未用(BR-022) / 失败锁定(BR-033)──▶ FROZEN ──解冻──▶ ACTIVE
ACTIVE ──换新──▶ 新 ACTIVE（旧 Key 宽限 24h 后 REVOKED）
ACTIVE/FROZEN ──手动吊销 / 离职事件(BR-023)──▶ REVOKED（终态，不可恢复）
```

**授权（grant 表 status，AirGrantStatus）**：

```
ACTIVE ──收回──▶ REVOKED（逻辑保留可审计；事件驱动同步至连接器，BR-024）
```

### 3.3 错误码口径（全局规范 3.2 AIR 段声明）

- **AIR 模块不设业务错误码段**：RAGFlow 相关系统错误 **5007（检索超时）/ 5008（组件不健康）已移除，号位作废**（无检索/无底座）；
- MCP 网关端点豁免 `{code:0}` 包装：按 MCP 协议错误格式返回，限流超限返回 **HTTP 429**；鉴权/权限失败 **401/403** 沿用 HTTP 语义；
- 管理端 `/air/*` 业务错误复用通用码 **1001（参数校验失败）/ 1008（无数据权限）**；
- SKILL-/EXPERT-/KNOW-/KEY-/MCP-/KB- 功能点的专属业务码**暂不启用**，如需启用须先修订全局规范总表（建议预留段位避免与 PERF/ALERT/COMP 现有占用冲突）。

### 3.4 数据表引用清单（13 张，表名与共享规范 7.2 AIR 段逐字一致；v2.6.31 新增 ims_kb_category）

| 表名 | 说明 | 主要落点 API |
|------|------|--------------|
| ims_skill | 技能主表（skill_code/name/category/ver/status/source/risk_level/subject_id） | 2.1.x |
| ims_skill_ver | 技能版本（ver/md_hash/md_content/audit_status/risk_level） | 2.1.3/2.1.4/2.1.5、2.7.4 |
| ims_skill_grant | 技能授权（grant_type/grant_id_ref/status/granted_by） | 2.1.7/2.1.8、2.7.3/2.7.4 |
| ims_expert | 专家包（expert_code/system_prompt/skill_ids/kb_ids/tool_whitelist/ver/status） | 2.2.x、2.7.5/2.7.6 |
| ims_expert_grant | 专家授权 | 2.2.5、2.7.5/2.7.6 |
| ims_kb | 知识库（secret_level/provider(默认 local)/status） | 2.3.x |
| **ims_kb_category** | **知识分类（库内两级树：kb_id/parent_id/name/sort_no/doc_cnt/tenant_id）** | **2.3.7~2.3.11**（v2.6.31 新增） |
| ims_kb_doc | 知识文档（content_hash/**file_key(服务端相对路径)**/**file_size**/**content_type**/**category_id**/**source_type(FILE/URL/TEXT/TRAIN/PERF/CONTENT)**/**source_ref**/secret_level/audit_status；**v2.6.32 去 ext_id**） | 2.3.4~2.3.6、2.3.13/2.3.14 |
| ims_kb_grant | 知识库授权 | 2.3.15 |
| ims_api_key | 人员 Key（key_hash(SHA-256)/user_id/device_name/status/last_used_at/qpm_limit/ip_whitelist） | 2.4.x、2.7.1 |
| ims_mcp_log | 调用审计（key_id/user_id/tool/param_digest/result_code/cost_ms；按月分区保留 180 天） | 2.5.1、2.7.1（写入） |
| ims_air_usage | 用量统计日表（user_id/tool/call_cnt/token_cnt/stat_date） | 2.5.2 |
| ims_air_event | AI 资产事件（event_type/payload/sync_status；对接钉钉事件总线） | 2.1.8/2.2.5/2.3.15/2.4.x/2.6.2（syncEventId） |

### 3.5 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 五页统计卡 | 模块总览加载 | GET /air/overview |
| 技能库页 | 列表查询 / 详情 | GET /air/skill/page、GET /air/skill/{id} |
| 新增/编辑技能抽屉 | 提交审核（自动扫描） | POST /air/skill、PUT /air/skill/{id} |
| 技能审核抽屉 | 通过/驳回/退回修改 | POST /air/skill/{id}/audit |
| 技能授权抽屉 | 授权/收回/全员可见 | POST /air/skill/grant、DELETE /air/skill/grant/{grantId} |
| 技能行操作 | 停用/启用 | PUT /air/skill/{id}/status |
| 专家库卡片网格 | 列表/详情（组装预览） | GET /air/expert/page、GET /air/expert/{id} |
| 新建/编辑专家抽屉 | 保存（新版本留档） | POST /air/expert、PUT /air/expert/{id} |
| 专家授权抽屉 | 授权/收回（含角色模板） | POST /air/expert/grant、DELETE /air/expert/grant/{grantId} |
| 知识目录树 | 树加载（库→分类两级，库内两级树） | GET /air/kb/tree |
| 知识库表格 | 列表查询 | GET /air/kb/page |
| 新建知识库抽屉 | 创建（LocalProvider 建档） | POST /air/kb |
| 上传资料抽屉（文件/URL/文本） | 提交入库审批 | POST /air/kb/doc/upload、POST /air/kb/doc/import-url、POST /air/kb/doc/import-text |
| 分类管理抽屉 | 分类增删改排序（库内两级树） | GET /air/kb/category/tree、POST /air/kb/category、PUT /air/kb/category/{id}、PUT /air/kb/category/sort、DELETE /air/kb/category/{id} |
| 从系统转入抽屉向导 | 源条目查询 + 按条目转入（TRAIN/PERF/CONTENT） | GET /air/kb/transfer-source、POST /air/kb/doc/import-from |
| 入库审批抽屉 | 审批（→已发布） | POST /air/kb/doc/audit |
| 知识库授权抽屉 | 授权 | POST /air/kb/grant |
| 知识条目详情抽屉 | 条目浏览/下载（服务端文件目录） | GET /air/kb/page（条目视图） |
| Key 生成抽屉/成功弹窗 | 生成（一次性明文+配置卡） | POST /air/key/generate |
| Key 表格 | 列表（掩码） | GET /air/key/page |
| Key 行操作 | 吊销/冻结/解冻/换新 | POST /air/key/{id}/revoke、/freeze、/unfreeze、/renew |
| 连接器配置抽屉 | 配置 JSON 获取 | GET /air/key/config-snippet |
| 白名单抽屉（P1） | 白名单维护 | PUT /air/key/whitelist |
| 审计监控日志表格/详情 | 日志查询 | GET /air/mcp/audit-log |
| 用量统计卡 | 按日/按人/按工具 | GET /air/usage/stat |
| 系统参数（R1，无独立页） | 参数查询/更新 | GET /air/sys-param、PUT /air/sys-param |
| 外部工具（Cursor 等） | MCP 四工具调用 | POST /ims/mcp（独立网关，Key 认证） |

（全文完）
