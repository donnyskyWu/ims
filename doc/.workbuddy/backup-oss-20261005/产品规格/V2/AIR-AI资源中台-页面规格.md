# AIR - AI 资源中台 页面规格

> 依据：《IMS-模块20-AI资源中台PRD-V1.md》V1.2.3（SKILL-001~004 / EXPERT-001~003 / KNOW-001~006 / KEY-001~004 / MCP-001~003 / KB-001~003，BR-019~035）、《共享技术规范-数据库与API.md》7.2/8.1、《AIR-AI资源中台-API契约.md》、《全局开发规范.md》第 4 章 AIR 段（权威枚举）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；管理端 API 前缀 `/admin-api/ims/air`；MCP 网关独立端点 `/ims/mcp`。
> 归属期次：V2.2 批次（第 19~20 周 AIR-P0 先行，配独立资源不占 V2 关键路径）；AIR-P1 衔接 V2.2/V2.3。
> **本期主导航（完整 PRD v2.6.32 / 走查 #14 订正）**：仅 P1、P2、**P3**、P6 出菜单；P4、P5 **Deferred**（下文规格不删，恢复菜单时按 AIR-P0/P1 批次交付）。
> **本期范围（v2.6.32）**：知识库 = **文件管理期**。**KNOW-003 知识检索** 与 **KB-001 RAGFlow 底座** 已移出范围（不做）；底座为 **IMS 本地对象存储（KB-003，`KbProvider=LOCAL`）**；不做向量化、无 `PARSING` 态、无底座健康卡/底座巡检、无检索演示。
> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 | 本期菜单 |
|------|------|------|-----------|----------|
| P1 技能库 | `/ims/air/skill` | 一级菜单页（分类页签 + 表格 + 审核链路） | SKILL-001/002/003/004 | ✅ In Scope |
| P2 专家库 | `/ims/air/expert` | 一级菜单页（卡片网格 + 组装预览） | EXPERT-001/002/003 | ✅ In Scope |
| P3 知识库 | `/ims/air/kb` | 一级菜单页（左目录树 + 右表格 + 分类管理/转入/上传） | KNOW-001/002/**003(已移除)**/004/005/006、**KB-002/003**（KB-001 已移除） | ✅ **In Scope（文件管理期）**：不做检索 |
| P4 Key 管理 | `/ims/air/key` | 一级菜单页（表格 + 一次性明文弹窗 + 配置卡） | KEY-001/002/003/004、MCP-002 | ⏸ Deferred |
| P5 审计监控 | `/ims/air/log` | 一级菜单页（调用日志 + 用量统计） | MCP-003、SKILL-004/EXPERT-003/KEY-003 的审计侧 | ⏸ Deferred |
| P6 模型与提示词 | 收编 OPS · 原型 `airCfg` | 一级菜单页（模型连接 / 提示词 Tab） | M8 收编 · 禁止两套 Key | ✅ In Scope |

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；交互操作优先内联抽屉（Drawer），不跳转新页面；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄或橙 / 失败红 / 中性灰）；
- 枚举一律引用《全局开发规范.md》第 4 章 AIR 段：`SkillStatus`、`AirAuditStatus`、`AirGrantType`、`AirGrantStatus`、`KnowledgeSecretLevel`、`KbProvider`、`ApiKeyStatus`、`McpToolName`，资产启停复用 `EnableStatus`（禁止重复定义）；
- 页面统计卡（技能/专家/知识库计数、启用中 Key、累计调用）五页复用，数据源 `/air/overview`。

---

## P1. 技能库（SKILL-001/002/003/004）

### 1. 页面概述
- 路由路径：`/ims/air/skill`
- 页面级别：一级菜单页：顶部统计卡 → 分类页签（内容生产/数据分析/运营支持/财务/人事行政）→ 查询行 → 技能列表表格
- 依赖模块：01 权限管理（组织/角色/人员主数据，BR-031）、13 预警中心（审核风险告警）、消息中心（驳回通知）
- 权限矩阵引用（PRD 1.3 / SKILL-001~003）：R11 R/W（主责，全量）、R1 R/W（网关与参数外的管理兜底）、R4/R5 本部门授权审批 R、R9 审计只读；技能分发（授权）仅 R11/R1；未过审技能对授权操作锁定（BR-025）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 统计卡: 技能/专家/知识库 N/N/N | 启用中 Key N | 累计调用 N |
+------------------------------------------------------------------+
| 分类页签: 全部 | 内容生产 | 数据分析 | 运营支持 | 财务 | 人事行政   |
| 查询行: 技能名称 | 状态 | 审核状态 | 责任人 | [查询][重置] [新增技能] |
+------------------------------------------------------------------+
| 技能列表表格:                                                     |
| 编号|名称|分类|版本|状态|审核状态|风险等级|责任人|授权人数|累计调用|操作|
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
新增/编辑抽屉(480px): 名称* | 分类* | 初始版本* | 维护责任人* |
  来源(市场/上传/URL)* | 能力说明* | SKILL.md 内容(提示词模板)* | [提交审核]
审核抽屉(560px): 基础信息 + 能力说明 + 自动扫描结果(依赖/危险命令/外联)
  + 风险报告(P0/P1/P2) + 审核意见(驳回必填) | [驳回][审核通过]
授权抽屉(520px): 技能信息 + 新增授权(类型 DEPT/ROLE/PERSON + 对象 + 有效期*)
  + [全员可见]快捷开关 + 现有授权列表
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface SkillPageReq {
  pageNo: number; pageSize: number;
  skillName?: string;
  category?: string;               // 分类页签
  status?: SkillStatus;
  auditStatus?: AirAuditStatus;
  ownerUserId?: number;
}
interface SkillCreateReq {
  skillName: string;               // 必填 ≤128 字
  category: string;                // 必填
  ver: string;                     // 必填，语义化版本（v1.0 起）
  source: 'MARKET' | 'UPLOAD' | 'URL';   // 来源：市场/上传/URL（SKILL-001）
  sourceRef?: string;              // UPLOAD 时 ossKey / URL 时地址 / MARKET 时市场标识
  desc: string;                    // 必填，能力说明
  mdContent: string;               // 必填，SKILL.md 全文（含提示词模板）
  ownerUserId: number;             // 必填
  clientToken: string;             // 幂等
}
interface SkillUpdateReq extends SkillCreateReq {
  id: number;                      // 更新生成新版本（ims_skill_ver 追加，md_hash 重算）
}
interface SkillAuditReq {
  id: number;
  approve: boolean;                // true 通过 / false 驳回
  auditNote?: string;              // 驳回时必填
}
interface SkillGrantReq {
  skillId: number;
  grantType: AirGrantType;         // DEPT / ROLE / PERSON（三维授权）
  grantId: number;                 // 部门 ID / 角色 ID / 人员 userId
  expireAt?: string;               // 授权有效期（可选，不填即长期）
  allStaff?: boolean;              // 「全员可见」快捷开关（SKILL-003）
}
interface SkillGrantRevokeReq {
  grantId: number;                 // 收回单条授权 → AirGrantStatus.REVOKED
}

// 响应类型
interface SkillVO {
  id: number;
  skillCode: string;               // SKL+4 位流水
  skillName: string;
  category: string;
  ver: string;
  status: SkillStatus;             // PENDING_AUDIT / PUBLISHED / DISABLED / REJECTED
  riskLevel?: 'P0' | 'P1' | 'P2';  // 安全扫描输出（SKILL-002）
  ownerUserId: number;
  ownerName: string;
  grantCount: number;              // ACTIVE 授权数
  callCount: number;               // 累计调用（ims_mcp_log 聚合）
  updatedAt: string;
}
interface SkillAuditVO {
  id: number;
  ver: string;
  auditStatus: AirAuditStatus;     // PENDING / APPROVED / REJECTED
  riskLevel: 'P0' | 'P1' | 'P2';
  scanResult: {
    dependencies: string[];        // 依赖清单
    dangerousCommands: string[];   // 危险命令检测结果
    outboundUrls: string[];        // 外联地址清单
  };
  auditNote?: string;
  auditedAt?: string;
  auditorName?: string;
}

// 枚举引用（值域见《全局开发规范.md》第 4 章 AIR 段，禁止本域重复定义）
// SkillStatus = 'PENDING_AUDIT' | 'PUBLISHED' | 'DISABLED' | 'REJECTED' —— 引用全局规范
// AirAuditStatus = 'PENDING' | 'APPROVED' | 'REJECTED' —— 引用全局规范
// AirGrantType = 'DEPT' | 'ROLE' | 'PERSON' —— 引用全局规范
// AirGrantStatus = 'ACTIVE' | 'REVOKED' —— 引用全局规范
// EnableStatus = 'ENABLED' | 'DISABLED' —— 引用全局规范（资产启停复用）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /air/skill/page` + `GET /air/overview`（统计卡）；任一失败分区独立重试。分类页签切换在前端过滤 category 参数重新查询。

#### 4.2 核心操作流程
**A. 新增技能 → 强制审核 → 授权（BR-025/BR-026 主链路）**
1. [新增技能] → 抽屉：来源三选一联动表单（MARKET 市场标识 / UPLOAD FileUpload OSS 直传回执 ossKey / URL 地址），SKILL.md 内容编辑器；
2. [提交审核] → `POST /air/skill` → 状态置 `PENDING_AUDIT`（草稿语义并入待审核，提交即进审核流）；
3. 服务端自动执行安全扫描（依赖扫描/危险命令检测/外联地址检查，SKILL-002）→ 生成风险报告落 `ims_skill_ver`；
4. [审核] → 审核抽屉展示风险报告：**P0 风险 → [审核通过] 按钮禁用**，仅可驳回（驳回后 `REJECTED`，永久拒绝并记录，BR-025）；P1/P2 → 审核人判断，驳回需填写意见（退回修改重新提交）；
5. 审核通过 → `PUBLISHED` → 行操作出现 [授权]；未过审行 [授权] 按钮禁用并提示"未过审不得分发（BR-025）"；
6. 全流程目标 < 10 分钟（BR-026，审核自动项即时完成，仅人工复核耗时）。

**B. 技能授权（SKILL-003）**
1. [授权] → 抽屉：授权类型三选（DEPT/ROLE/PERSON，AirGrantType）+ 对象选择器（部门树/角色列表/人员搜索，数据源 01 权限管理）+ 有效期；
2. [全员可见] 开关：开启即写一条全组织范围授权（快捷方式，非独立枚举）；
3. 提交 `POST /air/skill/grant` → `AirGrantStatus.ACTIVE`，事件驱动同步至连接器（BR-024，生效延迟 < 5 分钟）；
4. 抽屉下方现有授权列表支持 [收回]（→ `REVOKED`，同样事件驱动同步）。

**C. 版本更新**
1. 已发布行 [编辑] → 抽屉预填当前版本 → 提交 `PUT /air/skill/{id}` → 新版本进 `PENDING_AUDIT` 重新审核（新版本未过审前，授权关系保持绑定旧已发布版本；过审后自动切绑新版本）。

**D. 停用/启用**
1. 已发布行 [停用] → ConfirmDialog（warning）→ `PUT /air/skill/{id}/status` → `DISABLED`，连接器 `skills.list/get` 即时不可见（授权记录保留）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| skillName | Input | 否 | 空 | 名称/编号模糊匹配 |
| category | 页签（全部/内容生产/…） | 否 | 全部 | 分类页签切换 |
| status | Select | 否 | 空 | SkillStatus 四值（PENDING_AUDIT 待审核/PUBLISHED 已发布/DISABLED 已停用/REJECTED 审核拒绝） |
| auditStatus | Select | 否 | 空 | AirAuditStatus 三值（PENDING/APPROVED/REJECTED） |
| ownerUserId | Select（人员搜索） | 否 | 空 | 维护责任人 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| skillCode | 技能编号 | 110 | — | 等宽字体，行点击打开详情抽屉 |
| skillName | 技能名称 | 自适应 | — | — |
| category | 分类 | 100 | — | — |
| ver | 版本 | 80 | ✓ 降序 | v{major.minor} |
| status | 状态 | 100 | — | tag：待审核(橙)/已发布(绿)/已停用(灰)/审核拒绝(红)（SkillStatus） |
| auditStatus | 审核状态 | 90 | — | tag（AirAuditStatus） |
| riskLevel | 风险等级 | 80 | — | P0 红/P1 橙/P2 灰；空为未扫描 |
| ownerName | 责任人 | 90 | — | — |
| grantCount | 授权人数 | 90 | — | 点击打开授权抽屉 |
| callCount | 累计调用 | 90 | ✓ | 千分位 |
| actions | 操作 | 170 | — | 按状态：[审核]（PENDING_AUDIT）/[编辑]/[授权]（PUBLISHED）/[停用]（PUBLISHED）/[启用]（DISABLED） |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 新增/编辑技能抽屉 | Drawer 480px | skillName 必填 ≤128 字；category 必选；ver 必填语义化版本；source 三选一联动（UPLOAD 时 ossKey 必填、URL 时 sourceRef 必填 URL 格式）；desc 必填；mdContent 必填非空；ownerUserId 必选；clientToken 幂等 |
| 技能审核抽屉 | Drawer 560px | 只读基础信息 + 扫描结果三清单 + 风险等级；auditNote 驳回必填；P0 风险时 [审核通过] 禁用（BR-025）；[驳回]（REJECTED 不可再提交）与 [退回修改]（驳回至草稿重提，仅 P1/P2）区分 |
| 技能授权抽屉 | Drawer 520px | grantType 三选（AirGrantType）联动对象选择器；grantId 必选（数据源 01 权限管理，BR-031）；expireAt 可选；allStaff 开关；现有授权列表（对象/类型/状态/有效期）支持 [收回]（→REVOKED）；提示"授权事件驱动同步，生效延迟 <5 分钟（BR-024）" |
| 技能详情抽屉 | Drawer 60% | 基础信息 + SKILL.md 预览（只读）+ 版本历史列表（ver/auditStatus/riskLevel/审核人/时间） |

### 8. 错误处理
- 5007 / 5008（原 RAGFlow 检索超时 / 组件不健康）：**已移除，号位作废**（检索功能整体移出，本页不触发）；
- 1001（参数校验失败）：表单项即时校验 + 提交时 ElMessage.error；
- 1008（无数据权限）：提示并刷新列表（R4/R5 仅本部门范围）；
- 401 静默跳 SSO；403 提示"无操作权限"；
- AIR 专属业务码：按全局规范 3.2 AIR 段声明口径**暂不启用**（启用前须先修订全局规范总表），管理端业务错误统一复用 1001/1008。

### 9. BR 业务规则覆盖
- **BR-025（技能须过审方可分发；P0 风险永久拒绝）**：审核抽屉 P0 拦截 + [授权] 按钮状态锁定 + REJECTED 永久态；
- **BR-026（安装到可分发 <10 分钟）**：新增即提交审核、自动扫描即时出报告，人工复核为唯一耗时项；
- **BR-024（权限变更事件驱动同步 <5 分钟）**：授权/收回操作提示与 `ims_air_event` 落库；
- **BR-031（组织/授权数据以 01 权限管理为准）**：授权对象选择器数据源约束；
- **BR-032（多主体预留 tenant_id/entity_id）**：后端落库口径，页面无感；
- SKILL-004（使用统计）：本页统计卡累计调用 + callCount 列为落点（明细在 P5）。

---

## P2. 专家库（EXPERT-001/002/003）

### 1. 页面概述
- 路由路径：`/ims/air/expert`
- 页面级别：一级菜单页：顶部统计卡 → 查询行 → 专家包卡片网格（3 列，方形头像 + 挂载 chip）
- 依赖模块：P1 技能库（挂载技能多选）、P3 知识库（挂载知识库多选）、01 权限管理（授权对象）
- 权限矩阵引用（PRD 1.3 / EXPERT-001~003）：R11 R/W（主责）、R1 R/W、R4/R5 本部门授权审批 R、R9 审计只读（EXPERT-003 会话留痕抽检在 P5）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 统计卡（五页复用）                                                 |
+------------------------------------------------------------------+
| 查询行: 专家名称 | 状态 | 责任人 | [查询][重置]          [导出]  |
+------------------------------------------------------------------+
| 专家包卡片网格(3 列):                                             |
| +------------+ +------------+ +------------+                     |
| |[头像] 名称  | |[头像] 名称  | |[头像] 名称  |                     |
| |编号·版本·tag| |...         | |...         |                     |
| |适用场景说明 | |            | |            |                     |
| |挂载技能 N|挂载知识库 N|累计组装 N                            |
| |技能 chip...| |            | |            |                     |
| |授权 N 人·负责人 | [组装预览][授权] |                          |
| +------------+ +------------+ +------------+                     |
新建/编辑抽屉(640px): 编码* | 名称* | 适用场景* | System Prompt*(TEXT) |
  挂载技能多选(仅已发布) | 挂载知识库多选(含密级提示) | 工具白名单多选(McpToolName)
组装预览抽屉(640px): System Prompt 源码块 + 挂载技能 chip + 挂载知识库 chip(含密级) |
  提示: experts.assemble 纯组装下发(D2/BR-034) | [授权管理]
授权抽屉(520px): 同技能授权(三维 + 有效期 + 角色模板预置说明)
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ExpertPageReq {
  pageNo: number; pageSize: number;
  expertName?: string;
  status?: EnableStatus;           // 专家包启停复用 EnableStatus（草稿语义: 草稿=未发布版本）
  ownerUserId?: number;
}
interface ExpertSaveReq {
  id?: number;                     // 空=新建
  expertCode: string;              // 必填，EXP+4 位流水（编辑只读）
  expertName: string;              // 必填 ≤128 字
  scene: string;                   // 必填，适用场景说明
  systemPrompt: string;            // 必填非空（TEXT）
  skillIds: number[];              // 挂载技能（仅 PUBLISHED，服务端校验）
  kbIds: number[];                 // 挂载知识库（含密级，授权后受密级过滤 BR-030）
  toolWhitelist: McpToolName[];    // 工具白名单（本期四工具子集，McpToolName）
  ownerUserId: number;             // 必填
  clientToken?: string;
}
interface ExpertGrantReq {
  expertId: number;
  grantType: AirGrantType;
  grantId: number;
  expireAt?: string;
  roleTemplateId?: number;         // 角色模板预置（EXPERT-002，如「直播运营岗模板」默认带 3 个专家）
}

// 响应类型
interface ExpertVO {
  id: number;
  expertCode: string;
  expertName: string;
  scene: string;
  ver: string;
  status: EnableStatus;            // 引用全局规范（资产启停复用）
  skillIds: number[];
  kbIds: number[];
  toolWhitelist: McpToolName[];
  grantCount: number;
  assembleCount: number;           // 累计组装次数（ims_mcp_log 中 experts.assemble 聚合）
  ownerUserId: number;
  ownerName: string;
  updatedAt: string;
}
interface ExpertAssemblePreviewVO {    // 组装预览（对齐 MCP experts.assemble 出参结构）
  systemPrompt: string;
  skillRefs: Array<{ code: string; name: string; ver: string; md?: string }>;
  // knowledgeContext 字段已移除：本期不返回该字段（语义检索已整体移出范围）
  guidelines: string;
}

// 枚举引用
// AirGrantType / AirGrantStatus / KnowledgeSecretLevel / McpToolName / EnableStatus —— 均引用全局规范第 4 章
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /air/expert/page` + `GET /air/overview`；卡片网格渲染，未发布（草稿）卡片头像置灰降透明度。

#### 4.2 核心操作流程
**A. 专家创建/编辑（EXPERT-001）**
1. [新增专家] → 抽屉：基础信息 + System Prompt 编辑器（TEXT 域）+ 挂载技能多选（仅 PUBLISHED 技能）+ 挂载知识库多选（**本期仅作引用标记，不返回 `knowledge_context` 字段、不产生知识片段；BR-030 已不再生效（检索功能已移除）**）+ 工具白名单多选（McpToolName 四工具）；
2. 提交 `POST /air/expert` / `PUT /air/expert/{id}` → 新版本（ver 自增）；编辑产生新版本后旧版本留档可查。

**B. 组装预览（D2：纯 Prompt 组装，不执行）**
1. 卡片 [组装预览] → 抽屉：System Prompt 源码块（等宽字体）+ 挂载技能 chip（编号+名称）+ 挂载知识库 chip（含密级 tag）；
2. 底部固定提示："experts.assemble 仅下发组装包（system_prompt + 技能契约；**本期不返回 knowledge_context 字段**，无检索片段），网关不执行模型与 Skill（D2/BR-034）"；
3. [授权管理] 按钮直接切换到授权抽屉（内联切换不跳页）。

**C. 专家授权（EXPERT-002）**
1. [授权] → 抽屉：同技能三维授权（AirGrantType）；提交 `POST /air/expert/grant`；
2. 提示"授权含包内全部技能与知识库权限；**本期知识库仅文件管理、无检索片段**；BR-030 已不再生效（检索功能已移除）"；
3. 角色模板预置：R11 可在**角色管理**侧将专家包预置进**角色**（如「直播运营」角色默认带 3 个专家），人员到岗自动授权（事件驱动，BR-024）。**ADR-IMS-008**：角色为权限唯一载体，预置对象为角色（原「岗位模板」语义已收敛）。

**D. 停用/导出**
1. 卡片 [停用] → ConfirmDialog → `ENABLED → DISABLED`（连接器 experts.list 即时不可见）；
2. [导出] → 专家包台账 Excel 导出（EXP 侧 R9 可用）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| expertName | Input | 否 | 空 | 名称/编号/场景模糊匹配 |
| status | Select | 否 | 空 | EnableStatus 两值（已发布/草稿前端语义） |
| ownerUserId | Select（人员搜索） | 否 | 空 | 负责人 |

### 6. 表格（卡片）列定义

| 卡片区块 | 内容 | 格式化 |
|-----------|------|--------|
| 头部 | 方形头像（首字）+ 名称 + 编号·版本 + 状态 tag | 草稿卡片头像灰度降透明度 |
| 场景行 | 适用场景说明（两行截断） | — |
| 指标行 | 挂载技能 N / 挂载知识库 N / 累计组装 N | 组装数为蓝色高亮 |
| 技能 chip | 挂载技能名称 chip 列表 | 空显示"未挂载技能" |
| 底部 | 授权 N 人 · 负责人 + [组装预览][授权] | 草稿卡片 [授权] 禁用 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 新建/编辑专家抽屉 | Drawer 640px | expertCode 必填（编辑只读）；expertName 必填 ≤128 字；scene 必填；systemPrompt 必填非空；skillIds 仅可选 PUBLISHED 技能（服务端校验，BR-025 联动）；kbIds 多选（本期仅引用标记）；toolWhitelist ⊆ McpToolName 四值（本期） |
| 组装预览抽屉 | Drawer 640px | 只读；System Prompt 源码块 + 技能/知识库 chip（知识库 chip 带密级 tag）；D2/BR-034 固定提示；[授权管理] 内联切换 |
| 专家授权抽屉 | Drawer 520px | grantType（AirGrantType）+ grantId 必选（01 权限管理数据源）+ expireAt 可选；BR-030 密级降级提示 |

### 8. 错误处理
- 1001（参数校验失败）：表单即时校验（含 toolWhitelist 非法工具名拦截）；
- 1008（无数据权限）：提示并刷新；
- 401 静默跳 SSO；403 提示"无操作权限"；
- 挂载技能包含非 PUBLISHED 时服务端拒绝（复用 1001，msg 指明技能名）；
- AIR 专属业务码暂不启用（全局规范 3.2 AIR 段口径）。

### 9. BR 业务规则覆盖
- **BR-030（组装包知识片段密级过滤/降级摘要）**：知识库多选提示 + 授权抽屉固定提示（过滤执行在 MCP 网关侧）；
- **BR-034（网关不执行 LLM 与 Skill）**：组装预览抽屉 D2 固定提示；
- **BR-024（授权事件驱动同步 <5 分钟）**：授权提交后提示；
- **BR-031（授权对象主数据源 01）**：授权对象选择器约束；
- EXPERT-002（角色模板预置）：授权抽屉说明落点；
- EXPERT-003（会话审计）：本页 assembleCount 指标，留痕明细在 P5 审计监控页。

---

## P3. 知识库（KNOW-001/002/004/005/006、KB-002/003；KNOW-003、KB-001 已移除）

> **本期菜单**：✅ **In Scope（文件管理期，v2.6.32）**。页头工具条含 **新增知识库 · 分类管理 · 上传资料 · 从系统转入**；知识分类为 **库内两级树**（表 `ims_kb_category`）；**不做检索、无底座健康卡/底座巡检**——底座为 IMS 本地对象存储（KB-003，`KbProvider=LOCAL`）。

### 1. 页面概述
- 路由路径：`/ims/air/kb`
- 页面级别：一级菜单页：页头工具条（新增知识库 / 分类管理 / 上传资料 / 从系统转入）+ 左侧知识目录树（**知识库 → 分类/目录两级**，228px）+ 右侧查询行/表格
- 依赖模块：**IMS 本地对象存储（KB-003，知识文档正文 `oss_key`）**、FileUpload（OSS 直传）、01 权限管理（授权对象）、16 数据采集（存量知识批量导入通道）、**15 内容生产（内容记录来源 · CONTENT）/ 05 绩效（考核模板来源 · PERF）/ 培训管理（培训资料来源 · TRAIN）**
- 权限矩阵引用（PRD 1.3 / KNOW-001~006）：R11 R/W（主责）、R1 R/W、R4/R5 本部门授权审批 R、R9 审计只读

### 2. ASCII 页面布局
```
+--------------------------------------------------------------+
| 页头: [新增知识库][分类管理][上传资料][从系统转入]            |
+----------------------------------+-------------------------------+
| 知识目录树(228px,sticky)         | 查询行: 库编号/名称 | 关键词  |
| 库名 + 密级 tag                  |   | 密级 | 状态 | [查询][重置]|
|  └ 分类/目录节点(库内两级树)      +-------------------------------+
|  [＋新增分类] [✎重命名] [✕删除]   | 知识条目/知识库表格:           |
|  点选库/分类节点联动右侧过滤      | 编号|名称|分类|密级|文档数|    |
|                                  | 大小|状态|来源|责任人|       |
|                                  | 更新时间|授权|操作            |
+----------------------------------+-------------------------------+
|                                  | 分页: pageNo=1 pageSize=20    |
+----------------------------------+-------------------------------+
新建知识库抽屉(520px): 名称* | 描述 | 密级*(KnowledgeSecretLevel 四选) |
  Provider(固定 LOCAL 只读) | 责任人*
分类管理抽屉(520px): 库内两级树 新增/重命名/排序/删除分类
上传资料抽屉(560px): 方式切换 Tab【文件 | URL | 粘贴文本】→ kbId* + 分类 + 密级
从系统转入抽屉向导(720px,4 步): ①来源模块(TRAIN/PERF/CONTENT)
  → ②条目勾选(关键词/分类筛选+全选当页) → ③目标库+分类+密级 → ④提交入库
入库审批抽屉(560px): 知识库信息 + 待入库文档清单 + [驳回][审批通过]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface KbPageReq {
  pageNo: number; pageSize: number;
  kbId?: number;                   // 目录树选中联动
  keyword?: string;                // 名称/编号匹配
  secretLevel?: KnowledgeSecretLevel;
  docStatus?: 'DRAFT' | 'PENDING' | 'PUBLISHED';   // 知识文档入库状态（前端展示态；v2.6.32 去 PARSING 态）
}
interface KbCreateReq {
  kbName: string;                  // 必填 ≤128 字
  desc?: string;
  secretLevel: KnowledgeSecretLevel;   // 必填四选（PUBLIC/INTERNAL/CONFIDENTIAL/TOP_SECRET）
  ownerUserId: number;             // 必填
  clientToken?: string;
}
interface KbDocUploadReq {
  kbId: number;                    // 必选
  categoryId?: number;             // 目标分类（库内两级树；缺省挂根）
  ossKeys: string[];               // FileUpload OSS 直传回执（PDF/DOCX/MD/HTML/Excel，KNOW-002）
  secretLevel?: KnowledgeSecretLevel;   // 缺省继承库密级；不得低于库密级
}
interface KbDocImportUrlReq {
  kbId: number;
  categoryId?: number;             // 目标分类
  urls: string[];                  // URL 导入（必填 URL 格式）
  secretLevel?: KnowledgeSecretLevel;
}
interface KbDocImportTextReq {     // v2.6.31 新增：粘贴文本入库
  kbId: number;
  categoryId?: number;             // 目标分类
  title: string;                   // 必填 ≤128 字
  content: string;                 // 必填，纯文本/Markdown 正文
  secretLevel?: KnowledgeSecretLevel;
}
interface KbCategoryReq {          // v2.6.31 新增：知识分类（库内两级树，KNOW-005）
  kbId: number;                    // 必选
  parentId?: number;               // 0/空=根分类（一级）；否则挂二级
  categoryName: string;            // 必填 ≤64 字
  sortNo?: number;                 // 排序号，缺省追加末尾
}
interface KbCategorySortReq {      // 同级排序
  kbId: number;
  orderedIds: number[];            // 同级分类 ID 升序排列
}
interface KbDocTransferReq {       // v2.6.31 新增：系统资料转入（KNOW-006）
  sourceType: 'TRAIN' | 'PERF' | 'CONTENT';   // 来源模块：培训资料/绩效考核模板/内容记录
  sourceIds: number[];             // 按条目勾选的源记录 ID（KNOW-006 按条目转入）
  targetKbId: number;              // 必选目标知识库
  targetCategoryId?: number;       // 目标分类
  secretLevel?: KnowledgeSecretLevel;   // 缺省取源资料密级
  clientToken?: string;            // 幂等
}
interface KbDocAuditReq {
  docId: number;
  approve: boolean;                // true 通过 → PUBLISHED（正文入本地对象存储即发布） / false 驳回 → DRAFT
  auditNote?: string;              // 驳回必填
}
interface KbGrantReq {
  kbId: number;
  grantType: AirGrantType;
  grantId: number;
  expireAt?: string;
}
// KbSearchDemoReq —— 检索演示入参（v2.6.32 移除：本期不做检索，KNOW-003 已移除）

// 响应类型
interface KbTreeNodeVO {           // 库内两级树节点（KNOW-005，v2.6.31）
  categoryId: number;
  categoryName: string;
  parentId: number;                // 0=一级分类
  sortNo: number;
  docCount: number;
  children?: KbTreeNodeVO[];       // 二级分类
}
interface KbTreeVO {
  kbId: number;
  kbName: string;
  secretLevel: KnowledgeSecretLevel;
  docCount: number;
  children: KbTreeNodeVO[];        // 分类/目录（库内两级树，同步自 ims_kb_category）
}
interface KbTransferSourceItemVO { // 系统资料转入 · 源条目（KNOW-006，v2.6.31）
  sourceType: 'TRAIN' | 'PERF' | 'CONTENT';
  sourceId: number;                // 源记录 ID（回写 ims_kb_doc.source_ref）
  title: string;                   // 培训资料标题 / 考核模板名 / 内容记录标题
  category?: string;               // 源侧分类（岗位/考核类型/内容类型）
  secretLevel: KnowledgeSecretLevel;   // 源资料密级（转入默认值）
  updatedAt: string;
  imported?: boolean;              // 是否已转（去重提示）
}
interface KbVO {
  id: number;
  kbCode: string;                  // KB+4 位流水
  kbName: string;
  secretLevel: KnowledgeSecretLevel;
  docCount: number;
  totalSize: number | '—';         // 文档总大小（字节，千分位展示）；v2.6.32 替代原「向量块数」
  status: 'DRAFT' | 'PENDING' | 'PUBLISHED';
  provider: KbProvider;            // LOCAL（本期唯一实现，D1 决策）
  ownerUserId: number;
  ownerName: string;
  updatedAt: string;
}
// KbSearchDemoItemVO —— 检索结果项（v2.6.32 移除：本期不做检索，KNOW-003 已移除）
// RagflowHealthVO —— 底座健康快照（v2.6.32 移除：本期无 RAGFlow 底座，KB-001 已移除）

// 枚举引用
// KnowledgeSecretLevel = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'TOP_SECRET' —— 引用全局规范
// KbProvider = 'LOCAL'（唯一值；原 RAGFLOW 检索期预留值已作废，值域仅 LOCAL）
// AirGrantType / AirGrantStatus —— 引用全局规范
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /air/kb/tree`（目录树）+ `GET /air/kb/page`；任一失败分区独立重试。目录树点选库节点 → 联动右侧表格按 kbId 过滤（树节点高亮）。

#### 4.2 核心操作流程
**A. 知识入库审批（KNOW-002：入库审批中 → 已发布）**
1. 员工经 **上传资料抽屉（文件 OSS 直传 / URL 导入 / 粘贴文本）** 或 **从系统转入（KNOW-006）** 提交 → 文档状态 `PENDING`（入库审批中）；
2. 行 [审批] → 抽屉：库信息 + 待入库文档清单；
3. [审批通过] → 状态 `PUBLISHED`（已发布，正文写入 IMS 本地对象存储 `oss_key`，可在模块内浏览/下载/管理）；
4. [驳回] → auditNote 必填 → 状态退回 `DRAFT`（草稿），修改后重新提交。

**B. 知识条目浏览与密级维护（KNOW-004）**
1. 表格行 [详情] → 抽屉展示条目标题/分类/来源/密级/正文（本地对象存储直链或预览）；
2. 密级仅作**元数据标记**（四级 KnowledgeSecretLevel），用于模块内视图与授权控制；**BR-027 摘要脱敏已不再生效（检索功能已移除）**；
3. 底部提示"本期为文件管理：不做检索与向量化；检索能力（KNOW-003/KB-001）已移出范围（不做）"。

**C. 知识库创建与授权**
1. [新建知识库] → 抽屉：密级四选（KnowledgeSecretLevel）+ Provider 固定 `LOCAL` 只读（KbProvider，D1 决策：本期本地对象存储；经 KnowledgeProvider 抽象保留切换位，KB-002）；
2. [授权] → 三维授权抽屉（同技能/专家）；提交后事件驱动同步（BR-024）。

**D. 知识库文档管理（KB-003 运维）**
1. 库/条目视图可查看文档总大小、更新时间；容量增长纳入 13 预警中心容量监控（对象存储生命周期策略）；
2. 无底座健康卡、无底座巡检（RAGFlow 底座与相关运维已移除，KB-001 已移除）。

**E. 知识分类管理（KNOW-005 · 库内两级树，v2.6.31 新增）**
1. 左树选中库 → [分类管理] → 抽屉展示该库「库内两级树」（库 → 一级分类 → 二级分类），支持 **[＋新增分类]**（选父级、填名称、排序）、**[✎ 重命名]**、**[⇅ 排序]**（同级拖拽/上下移，提交 `orderedIds`）、**[✕ 删除]**；
2. 删除含条目的分类 → 二次确认：「该分类下有 N 条知识，删除后条目将改挂根分类」；仅空分类可直接删除；
3. 分类变更即时保存，左树刷新；点选分类节点 → 右侧表格按 `kbId + categoryId` 联动过滤；知识上传/转入时可选目标分类；
4. 分类作用于 IMS 侧元数据与**模块内条目筛选**（`categoryId` 原检索期预留已移除，仅用于模块内筛选）；本期不映射外部底座分组。

**F. 系统资料转入知识库（KNOW-006 · 按条目勾选，v2.6.31 新增）**
1. 页头 [从系统转入] → **720px 抽屉向导（4 步）**：
   - ① **选来源模块**（培训资料 TRAIN-001 / 绩效考核模板 PERF 考核方案 / 内容记录 CONTENT 内容管理，单选）；
   - ② **按条目勾选**：拉取该模块条目列表（`GET /air/kb/transfer-source?sourceType=…`），支持关键词/分类筛选、全选当页、单条勾选；已在库中的条目显示「已转入」去重标记；
   - ③ **选目标**：目标知识库 + 目标分类（可选）+ 密级（缺省取源资料密级）；
   - ④ **提交入库**：`POST /air/kb/doc/import-from` → 转文档 `source_type` 记 `TRAIN`/`PERF`/`CONTENT`、`source_ref` 记源记录 ID（溯源），状态 `PENDING`（入库审批中）；
2. 提交后 toast 汇总「已提交 N 条转入，进入入库审批」；审批通过后按 KNOW-002 流程发布（正文入本地对象存储，**本期不解析向量化**）；
3. 幂等：同一 `sourceType + sourceId` 重复转入以 `clientToken` 去重（二次提交提示"已存在，是否覆盖"）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| kbId | TreeSelect（随左侧树点击联动） | 否 | 空 | 目录树选中库节点联动过滤 |
| categoryId | TreeSelect（库内两级树） | 否 | 空 | 选库后可选分类节点联动过滤（KNOW-005） |
| keyword | Input | 否 | 空 | 库编号/名称模糊匹配 |
| secretLevel | Select | 否 | 空 | KnowledgeSecretLevel 四值（公开/内部/机密/绝密） |
| status | Select | 否 | 空 | 全部/已发布/入库审批中/草稿 |
| sourceType | Select | 否 | 空 | 全部/文件/URL/文本/培训资料/绩效考核模板/内容记录（来源溯源筛选） |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| kbCode | 库编号 | 100 | — | 等宽字体，行点击打开库详情抽屉 |
| kbName | 知识库名称 | 自适应 | — | 密级为机密/绝密时名称旁附 grantsLimit 授权约束说明 |
| categoryName | 分类 | 110 | — | 显示库内分类路径（一级/二级）；未归入显示「根」 |
| secretLevel | 密级 | 90 | — | tag：公开(绿)/内部(蓝)/机密(橙)/绝密(红)（KnowledgeSecretLevel） |
| docCount | 文档数 | 80 | — | — |
| totalSize | 大小 | 90 | — | 千分位（字节→KB/MB）；v2.6.32 替代原「向量块」列 |
| status | 状态 | 100 | — | tag：已发布(绿)/入库审批中(橙)/草稿(灰) |
| sourceType | 来源 | 90 | — | tag：文件/URL/文本/培训资料/绩效考核模板/内容记录 |
| ownerName | 责任人 | 90 | — | — |
| updatedAt | 更新时间 | 140 | ✓ | yyyy-MM-dd HH:mm |
| grantCount | 授权 | 70 | — | 点击打开授权抽屉 |
| actions | 操作 | 150 | — | [审批]（PENDING）/[详情] |

> **知识条目视图**：选中某库/分类后，表格切换为**知识条目粒度**（标题 / 分类 / 来源 source_type / 密级 / 状态 / 更新时间 / 操作[详情]）；库粒度列（文档数/大小）在条目视图下隐藏。来源列对 TRAIN/PERF/CONTENT 显示来源模块 tag 并可跳源模块（新增 tab）。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 新建知识库抽屉 | Drawer 520px | kbName 必填 ≤128 字；secretLevel 必选四值（KnowledgeSecretLevel）；provider 固定 LOCAL 只读（KbProvider 唯一值，原 RAGFLOW 已作废）；ownerUserId 必选 |
| **上传资料抽屉** | Drawer 560px | **方式切换 Tab【文件 / URL / 粘贴文本】**：文件→ossKeys 必填非空（FileUpload OSS 直传，PDF/DOCX/MD/HTML/Excel）；URL→urls 必填 URL 格式；文本→title + content 必填；三者共用 kbId 必选 + categoryId 可选 + secretLevel 可选（缺省继承库密级，不得低于库密级） |
| **分类管理抽屉** | Drawer 520px | kbId 必选；库内两级树增删改（categoryName 必填 ≤64 字；parentId 选父级）；[⇅ 排序]（同级 orderedIds）；删除含条目分类二次确认「条目改挂根」 |
| **从系统转入抽屉向导** | Drawer **720px · 4 步** | ①sourceType 单选（TRAIN/PERF/CONTENT）；②sourceIds 至少勾选 1 条（关键词/分类筛选 + 全选当页）；③targetKbId 必选 + targetCategoryId 可选 + secretLevel 可选；④提交 → `POST /air/kb/doc/import-from`；clientToken 幂等 |
| 入库审批抽屉 | Drawer 560px | 只读库信息 + 待入库文档清单；auditNote 驳回必填；通过后进入 `PUBLISHED`（正文入本地对象存储）；密级作元数据标记（BR-027 摘要脱敏已不再生效，检索功能已移除） |
| 知识库授权抽屉 | Drawer 520px | 同技能授权（AirGrantType 三维 + 有效期） |
| 知识条目详情抽屉 | Drawer 560px | 条目标题/分类/来源/密级/正文（本地对象存储直链或预览）+ [下载]；v2.6.32 替代原「检索演示抽屉」 |

### 8. 错误处理
- **5007 / 5008（原 RAGFlow 检索超时 / 组件不健康）**：**已移除，号位作废**（无检索/无底座）；错误码映射表不再保留条目；
- 1001（参数校验失败）：表单即时校验（含密级不得低于库密级、转入未勾选条目、分类名重复）；
- 1008（无数据权限）：提示并刷新；
- 401 静默跳 SSO；403 提示"无操作权限"；
- 转入来源条目已存在（同 sourceType+sourceId）→ 提示"该条目已转入，是否覆盖"（幂等，不静默重复）；
- AIR 专属业务码暂不启用（全局规范 3.2 AIR 段口径）。

### 9. BR 业务规则覆盖
- **BR-027（机密/绝密不出库，仅标题+100字摘要+库内链接）**：**本期仅作元数据标记**，模块内按密级控制视图/授权；摘要脱敏已不再生效（检索功能已移除）；
- **BR-030（组装包片段密级过滤）**：本期无检索，`experts.assemble` 不返回 `knowledge_context` 字段；规则已不再生效（检索功能已移除）；
- **BR-024（授权事件驱动同步）**：授权抽屉提示；
- **BR-031（主数据源 01）**：授权对象选择器约束；
- KNOW-001（多知识库/目录/分类标签）：左侧目录树 + 密级筛选；
- KNOW-002（入库审批流）：审批抽屉 + PENDING→PUBLISHED 状态列；
- ~~KNOW-003（混合检索返回片段带原文链接与引用定位）~~：**已移除**，本期无检索演示；
- KNOW-004（四级密级）：KnowledgeSecretLevel 四值贯穿库/文档/分类；
- **KNOW-005（知识分类管理 · 库内两级树）**：分类管理抽屉 + 左树分类节点 + 分类过滤（v2.6.31）；
- **KNOW-006（系统资料转入 · 按条目勾选）**：从系统转入抽屉向导 + source_type 溯源（v2.6.31）；
- ~~KB-001（RAGFlow 自建底座）~~：**已移除**，本期无底座健康卡/巡检；
- **KB-002（Provider 抽象扩展位）**：provider 列固定 LOCAL + "KnowledgeProvider 抽象，底座替换对 MCP 客户端无感"说明；
- **KB-003（IMS 本地对象存储底座）**：知识文档正文 `oss_key`，审批通过即发布，模块内浏览/下载。

---

## P4. Key 管理（KEY-001/002/003/004、MCP-002）

> **本期菜单**：⏸ **Deferred**（走查 #14）。

### 1. 页面概述
- 路由路径：`/ims/air/key`
- 页面级别：一级菜单页：顶部统计卡 → 查询行 → Key 列表表格
- 依赖模块：01 权限管理（人员主数据与在职状态、钉钉离职事件 BR-023）、消息中心（90 天未用提醒 BR-022、失败锁定通知 BR-033）、13 预警中心（异常告警）
- 权限矩阵引用（PRD 1.3 / KEY-001~004）：R11 R/W（主责，生成/停用/吊销/换新）、R1 R/W（含系统参数总开关）、R4 本部门 R、R8 本人（领取 Key，经人员详情页入口）、R9 审计只读

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 统计卡（五页复用）                     [连接器配置] [生成 Key]   |
+------------------------------------------------------------------+
| 查询行: 人员姓名 | Key 状态 | 白名单 | [查询][重置]              |
+------------------------------------------------------------------+
| Key 列表表格:                                                     |
| 编号|归属人员|角色|Key 掩码|状态|设备用途|授权资源|累计调用|       |
| QPM 限额|白名单|最近调用|有效期|失效原因|操作                    |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
| 动态鉴权提示条: 每次调用实时校验在职与授权(缓存60s)；             |
| 离职事件即时吊销(BR-023)；明文仅生成时展示一次(BR-020)           |
+------------------------------------------------------------------+
生成抽屉(480px): 归属人员* | 设备用途* | QPM 限额* | 有效期至* |
  白名单(P1, 受总开关) + 一次性明文风险提示
生成成功弹窗(600px, 仅一次): Key 明文块(可选) + 归属/鉴权说明 +  |
  客户端配置卡(Cursor/Claude Desktop/WorkBuddy/通用 JSON) [复制]  |
连接器配置抽屉(600px): 端点 + 认证说明 + 4 工具清单(McpToolName) |
白名单抽屉(520px, P1): IP 段/设备指纹列表 + 增删（受总开关约束）  |
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ApiKeyPageReq {
  pageNo: number; pageSize: number;
  userName?: string;
  status?: ApiKeyStatus;           // ACTIVE / FROZEN / REVOKED
  whitelistOn?: boolean;
}
interface ApiKeyGenerateReq {
  userId: number;                  // 必选归属人员（一人默认一把，BR-019）
  deviceName: string;              // 必填，设备用途（默认「个人通用」；设备维度最多 3 把，BR-019）
  qpmLimit?: number;               // 缺省 60（BR-029 默认 QPM）
  expireAt: string;                // 必填
  ipWhitelist?: string[];          // P1：仅总开关开启时可填（BR-035）
  clientToken: string;             // 幂等
}
interface ApiKeyLifecycleReq {
  keyId: number;
  reason?: string;                 // 吊销原因（手工吊销时建议填写）
}
interface ApiKeyWhitelistReq {
  keyId: number;
  ipWhitelist: string[];           // IP 段列表；设备指纹同字段口径
}
interface ConfigSnippetReq {
  client: 'CURSOR' | 'CLAUDE_DESKTOP' | 'WORKBUDDY' | 'GENERIC';
}

// 响应类型
interface ApiKeyVO {
  id: number;
  keyMask: string;                 // air-****…****9f2c（明文不可再现，BR-020）
  userId: number;
  userName: string;
  roleName: string;
  deviceName: string;
  status: ApiKeyStatus;            // ACTIVE/FROZEN/REVOKED
  grantCount: number;              // 该人员可见资源数
  callCount: number;               // 累计调用
  qpmLimit: number;
  whitelistOn: boolean;            // 白名单是否开启（P1）
  lastUsedAt?: string;
  expireAt?: string;
  revokeReason?: string;           // 已吊销时显示（离职联动/手工/失败锁定）
  createdAt: string;
}
interface ApiKeyPlainVO {          // 生成成功一次性响应（仅此一次返回明文）
  keyId: number;
  plainKey: string;                // air- 前缀明文，仅本次响应携带
  configSnippets: Record<string, string>;   // client → mcpServers JSON 配置串
}
interface McpConfigVO {
  endpoint: string;                // https://…/ims/mcp（Streamable HTTP + SSE）
  authHint: string;                // Authorization: Bearer air-…（Header 优先，URL ?key= 兼容）
  tools: McpToolName[];            // 四工具（本期）
}

// 枚举引用
// ApiKeyStatus = 'ACTIVE' | 'FROZEN' | 'REVOKED' —— 引用全局规范
// McpToolName = 'skills.list' | 'skills.get' | 'experts.list' | 'experts.assemble'（固定四工具）—— 引用全局规范
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /air/key/page` + `GET /air/overview`；底部固定动态鉴权提示条（BR-021/023/020 口径）。

#### 4.2 核心操作流程
**A. 生成 Key（KEY-001：一次性明文 + 客户端配置复制，MCP-002）**
1. [生成 Key] → 抽屉：归属人员选择（01 权限管理数据源）+ 设备用途（默认「个人通用」）+ QPM 限额（缺省 60，BR-029）+ 有效期 + 白名单（P1，总开关 `air.key.ip_whitelist.enabled` 关闭时置灰不可填，D3/BR-035）；
2. 风险提示条："明文 Key 仅在生成时展示一次，关闭后不可再次查看（服务端只存哈希，BR-020）；丢失只能换新"；
3. [生成 Key] → 二次确认（ConfirmDialog 风险确认，PRD 4.2）→ `POST /air/key/generate`；
4. **生成成功弹窗（仅一次）**：Key 明文块（等宽字体全选样式）+ 归属/动态鉴权/离职自动吊销说明 + **客户端接入配置卡**（Cursor / Claude Desktop / WorkBuddy / 通用 JSON 四 Tab，各为 `mcpServers` JSON 配置串）[复制 Key] [复制客户端配置] 一键复制；
5. 服务端校验：一人默认一把（已有 ACTIVE Key 时提示确认/换新）；设备维度最多 3 把（BR-019）；
6. 关闭弹窗后列表仅显示掩码 `air-****…****9f2c`。

**B. 生命周期操作（KEY-002：停用/启用/吊销，二次确认）**
1. [停用] → ConfirmDialog（warning）："停用期间所有 MCP 调用返回 401，恢复后即刻生效" → `POST /air/key/{id}/freeze` → `FROZEN`；
2. [启用] → ConfirmDialog → `POST /air/key/{id}/unfreeze` → `ACTIVE`（按当前在职状态与授权实时鉴权，BR-021）；
3. [吊销] → 危险确认弹窗（danger 型 + 红色警示）："吊销不可恢复，所有调用立即 401。离职联动吊销无需手工操作（BR-023）" → `POST /air/key/{id}/revoke` → `REVOKED`（失效原因列显示：离职联动/管理员手工/失败锁定 BR-033）；
4. 已吊销行操作区替换为失效原因文案（灰字），不可恢复（如需接入重新生成，BR-020 丢失只能换新）；
5. 90 天未用自动冻结：离职/闲置由后台事件驱动，页面体现为状态与失效原因（冻结前 7 天消息中心提醒，BR-022）。

**C. 换新（KEY-002）**
1. [换新] → ConfirmDialog："旧 Key 宽限 24 小时后失效，新 Key 立即生效" → `POST /air/key/{id}/renew` → 生成流程同 A（一次性明文弹窗）。

**D. 连接器配置查看（MCP-002）**
1. [连接器配置] → 抽屉：网关端点（`POST https://…/ims/mcp`，Streamable HTTP + SSE 兼容）+ 认证方式说明（Header Bearer 优先，URL `?key=` 兼容；QPM 超限 429，鉴权失败 401）+ 四工具清单（McpToolName）+ D2/BR-034 固定提示（**本期无检索，BR-027 已不再生效（检索功能已移除）**）；
2. [生成新 Key] 快捷入口。

**E. 白名单维护（KEY-004，P1）**
1. 白名单列 [已开启] chip → 抽屉：IP 段/设备指纹列表增删 → `PUT /air/key/whitelist`；
2. 总开关关闭（默认，D3/BR-035）时抽屉顶部提示"总开关 air.key.ip_whitelist.enabled 未开启，白名单配置暂不生效"，配置可预存。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| userName | Input | 否 | 空 | 归属人员姓名模糊匹配 |
| status | Select | 否 | 空 | ApiKeyStatus 三值（启用/冻结/已吊销） |
| whitelistOn | Select | 否 | 空 | 全部/未开启/已开启（P1） |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| id | Key 编号 | 90 | — | 等宽字体 |
| userName | 归属人员 | 100 | — | 附角色小字 |
| keyMask | Key（掩码） | 150 | — | 等宽灰字 air-****…****（明文不可再现，BR-020） |
| status | 状态 | 90 | — | tag：启用(绿)/冻结(橙)/已吊销(红)（ApiKeyStatus） |
| deviceName | 设备用途 | 110 | — | — |
| grantCount | 授权资源 | 90 | — | 该人员可见技能/专家/知识库数 |
| callCount | 累计调用 | 90 | — | 千分位 |
| qpmLimit | QPM 限额 | 90 | — | 次/分钟（BR-029） |
| whitelistOn | 白名单 | 90 | — | 未开启灰字 / 已开启 chip（P1） |
| lastUsedAt | 最近调用 | 140 | ✓ | yyyy-MM-dd HH:mm；空显示"从未"（90 天冻结监控） |
| expireAt | 有效期 | 110 | — | 已吊销显示 — |
| actions | 操作 | 170 | — | [停用]（ACTIVE）/[启用]（FROZEN）/[吊销][换新][配置]（非 REVOKED）；REVOKED 显示失效原因灰字 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 生成 Key 抽屉 | Drawer 480px | userId 必选；deviceName 必填（默认个人通用；设备维度 ≤3 把服务端校验 BR-019）；qpmLimit 可选缺省 60；expireAt 必填；ipWhitelist 仅总开关开启时可填（BR-035）；一次性明文风险提示条固定展示 |
| 生成成功弹窗 | Modal 600px（仅一次） | Key 明文块（user-select:all）；四客户端配置 Tab（Cursor/Claude Desktop/WorkBuddy/通用 JSON，各 mcpServers JSON 串）；[复制 Key]/[复制客户端配置]；关闭即不可再现（BR-020） |
| 停用/启用确认弹窗 | Modal 400px | ConfirmDialog warning 型；停用提示"所有 MCP 调用返回 401" |
| 吊销确认弹窗 | Modal 440px | danger 型红色警示："吊销不可恢复；依赖此 Key 的外部工具立即断连；离职联动无需手工操作（BR-023）" |
| 换新确认弹窗 | Modal 400px | "旧 Key 宽限 24h 后失效，新 Key 立即生效" |
| 连接器配置抽屉 | Drawer 600px | 端点/认证/四工具清单（McpToolName）只读 + [生成新 Key] 入口；D2/BR-034 固定提示 |
| 白名单抽屉（P1） | Drawer 520px | ipWhitelist 列表增删（IP 段/设备指纹）；总开关关闭时提示"配置预存暂不生效（BR-035）" |

### 8. 错误处理
- 1001（参数校验失败）：表单即时校验 + 设备超 3 把/一人多把默认约束拦截（msg 指明 BR-019）；
- 1008（无数据权限）：提示并刷新（R4 仅本部门）；
- 401 静默跳 SSO；403 提示"无操作权限"；
- 复制失败降级：剪贴板 API 不可用时提示手动选中文本复制；
- AIR 专属业务码暂不启用（全局规范 3.2 AIR 段口径）；MCP 网关侧 429/401/403 由网关返回（本页不涉及）。

### 9. BR 业务规则覆盖
- **BR-019（一人默认一把；设备 ≤3 把）**：生成抽屉服务端校验 + 失败提示；
- **BR-020（仅一次明文；丢失只能换新）**：生成成功弹窗一次性响应 + 掩码列 + 换新流程；
- **BR-021（动态鉴权，缓存 60s）**：底部提示条 + 启用确认弹窗文案；
- **BR-022（90 天未用自动冻结，前 7 天提醒）**：lastUsedAt 列 + FROZEN 失效原因（消息中心联动）；
- **BR-023（离职事件立即吊销）**：吊销弹窗文案 + REVOKED 失效原因"离职联动"；
- **BR-029（默认 QPM 60，超限 429 告警）**：qpmLimit 缺省值 + 列展示；
- **BR-033（失败 10 次/10 分钟自动冻结并通知）**：FROZEN 失效原因"认证失败锁定"（事件驱动，页面体现）；
- **BR-035（白名单总开关默认关）**：白名单置灰逻辑 + 抽屉提示；
- KEY-003（限额与审计）：qpmLimit 可调（R11/R1）+ 累计调用列（日志明细在 P5）；
- KEY-004（IP/设备白名单）：白名单抽屉（P1）；
- MCP-002（接入引导）：客户端配置卡四 Tab 一键复制。

---

## P5. 审计监控（MCP-003、SKILL-004/EXPERT-003/KEY-003 审计侧）

> **本期菜单**：⏸ **Deferred**（走查 #14）。

### 1. 页面概述
- 路由路径：`/ims/air/log`
- 页面级别：一级菜单页：顶部统计卡 → 查询行 → MCP 调用日志表格 + 用量统计（近 7 天）卡
- 依赖模块：ims_mcp_log（调用审计，180 天分区保留）、ims_air_usage（日用量）、13 预警中心（慢调用/错误率告警）
- 权限矩阵引用（PRD 1.3 / BR-028）：R9 审计主责 R（全量）、R1 R（网关运维视角）、R11 R（本模块资产审计）、R4 本部门 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 统计卡（五页复用）                                  [导出日志]  |
+------------------------------------------------------------------+
| 查询行: 工具名/人员 | 结果 | Key 编号 | [查询][重置]             |
+------------------------------------------------------------------+
| MCP 调用日志表格:                                                 |
| 时间|MCP 工具(McpToolName)|调用人|Key 编号|结果|耗时|鉴权说明    |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
+--------------------------------------------------------------+
| 用量统计卡(近 7 天): 柱状图(按日调用次数) + 日期轴            |
| 提示: 审计日志全量落 ims_mcp_log(180 天)；失败重点跟踪        |
| 401 鉴权失败（本期无检索，5007/5008 已移除）            |
+--------------------------------------------------------------+
日志详情抽屉(60%): 调用上下文(人员/Key/工具/参数摘要/结果码/  |
  耗时/鉴权链路说明) —— BR-028 全量留痕口径
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface McpLogPageReq {
  pageNo: number; pageSize: number;
  keyword?: string;                // 工具名/人员姓名匹配
  tool?: McpToolName;              // 四工具过滤（本期）
  result?: 'SUCCESS' | 'FAIL';
  keyId?: number;
  dateRange?: [string, string];
}
interface UsageStatReq {
  by: 'PERSON' | 'TOOL' | 'DAY';   // 按人/按工具/按日
  dateRange?: [string, string];    // 默认近 7 天
}

// 响应类型
interface McpLogVO {
  id: number;
  createdAt: string;
  tool: McpToolName;               // 四工具（本期）
  userId: number;
  userName: string;
  keyId: number;
  keyCode: string;                 // Key 编号（掩码关联）
  resultCode: 'SUCCESS' | number;  // 失败携带错误码（401/403/429…；5007/5008 已移除）
  costMs: number;
  authNote: string;                // 鉴权链路说明（动态鉴权/密级拦截/限额拦截等上下文）
  paramDigest?: string;            // 参数摘要（详情抽屉）
}
interface UsageStatVO {
  statDate: string;
  callCnt: number;
  tokenCnt?: number;
}
interface UsageByPersonVO {
  userId: number; userName: string; deptName?: string;
  callCnt: number; tokenCnt: number;
}
interface UsageByToolVO {
  tool: McpToolName; callCnt: number; failCnt: number; avgCostMs: number;
}

// 枚举引用
// McpToolName = 'skills.list' | 'skills.get' | 'experts.list' | 'experts.assemble'（固定四工具）—— 引用全局规范
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /air/mcp/audit-log` + `GET /air/usage/stat?by=DAY`（近 7 天柱状图）；失败分区独立重试。

#### 4.2 核心操作流程
**A. 审计日志查询与导出（BR-028）**
1. 查询行过滤（工具/人员/结果/Key 编号/日期区间）→ 分页表格；失败行红色 tag 附错误码（`失败·{code}`）；
2. 行点击 → 日志详情抽屉：调用上下文全量（人员/Key/工具/参数摘要/结果码/耗时/鉴权链路说明）；
3. [导出日志] → Excel 导出（R9 审计留档；日志保留 180 天，超期分区清理导出前提示）；
4. 重点跟踪提示：失败调用聚焦 **401 鉴权失败**（停用/吊销 Key 样例）（**本期无检索，5007/5008 已移除**）。

**B. 用量统计（近 7 天）**
1. 柱状图按日展示调用次数（数据源 ims_air_usage）；hover 显示当日次数；
2. 维度切换（按人/按工具，KEY-003/SKILL-004 口径）：按人 → 人/部门/次数/Token；按工具 → 工具/次数/失败数/平均耗时。

**C. 连接器监控（MCP-003）**
1. 在线客户端数/QPS/错误率/慢调用告警接入 13 预警中心（**本期无底座健康巡检**——RAGFlow 巡检已移除）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| keyword | Input | 否 | 空 | 工具名/人员姓名匹配 |
| tool | Select | 否 | 空 | McpToolName 四值（本期） |
| result | Select | 否 | 空 | 全部/成功/失败 |
| keyId | Input（Key 编号） | 否 | 空 | 按 Key 过滤 |
| dateRange | DateRange | 否 | 空 | 180 天范围内 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| createdAt | 时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm:ss |
| tool | MCP 工具 | 140 | — | 等宽蓝色（McpToolName） |
| userName | 调用人 | 100 | — | — |
| keyCode | Key | 100 | — | 等宽编号 |
| resultCode | 结果 | 120 | — | 成功绿 tag / 失败红 tag 附错误码 |
| costMs | 耗时 | 90 | ✓ | {n} ms；>1500ms 黄色 |
| authNote | 鉴权说明 | 自适应 | — | 灰字上下文说明 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 日志详情抽屉 | Drawer 60% | 只读调用上下文：人员/Key/工具（McpToolName）/参数摘要/结果码/耗时/鉴权链路说明（BR-028 全量留痕口径） |
| 用量统计卡 | 页内卡片 | 近 7 天柱状图（按日调用次数）+ 日期轴；维度切换（按人/按工具） |

### 8. 错误处理
- 5007 / 5008（原 RAGFlow 检索超时 / 组件不健康）：**已移除，号位作废**（无检索/无底座）；
- 1001（参数校验失败）：查询条件即时校验；
- 1008（无数据权限）：R4 仅本部门、普通员工不可见本页（提示并返回）；
- 401 静默跳 SSO；403 提示"无操作权限"；
- AIR 专属业务码暂不启用（全局规范 3.2 AIR 段口径）。

### 9. BR 业务规则覆盖
- **BR-028（每次调用全量审计留痕，保留 180 天）**：日志表格 + 详情抽屉（人员/Key/工具/参数摘要/结果）+ 导出与保留期提示；
- **BR-029（QPM 超限 429 并告警）**：失败行 429 错误码展示（网关侧执行，审计留痕）；
- **BR-021/023（动态鉴权/离职即时 403）**：鉴权说明列与 401 失败样例提示；
- **BR-027（密级拦截）**：鉴权说明列预留"密级拦截"上下文（`knowledge.get` 403 样例），**已不再生效（检索功能已移除）**；
- SKILL-004（技能使用统计）：按工具维度（含 skills.list/get）用量与平均耗时；
- EXPERT-003（会话审计/组装包下发记录抽检）：experts.assemble 日志明细（paramDigest 含 message 摘要）；
- KEY-003（全量调用日志/Token 限额）：按人用量统计（callCnt/tokenCnt）；
- MCP-003（连接器监控）：在线客户端数/QPS/错误率/慢调用聚焦，告警联动 13 预警中心（**无底座健康巡检**）。

---

## P6. 模型与提示词（OPS M8 收编 · 本期 In Scope）

### 1. 页面概述
- 路由：收编 OPS 配置表（`oa_ai_model_config` / `oa_ai_prompt_config` 扩展为 AIR 连接器）；完整原型键 `airCfg`
- 页面级别：一级菜单页 · Tab「模型连接 | 提示词」
- 依赖：《全局开发规范-完整版补充》§6 · 禁止与 Key 管理两套明文 Key；内容生成默认 **jingcai 环境变量**（非本页录入）
- 权限：R11 / R1（与技能库管理兜底一致）

### 2. 交互要点
- **模型连接**：列表 CRUD · vendor/model/useCase · CONNECTED 状态（AI 排版语义须 Chat 模型）
- **提示词**：按场景/文档类型/版本维护；与 OPS 现网字段对齐，**不得**在本期发明新 REST（沿用 OPS 或 SYS 参数已有端点，具体以切片 ADR 为准）

---

## 附录 A. BR-019~BR-035 全量落页勾稽表（以 PRD V1.2.3 第 3 章为准）

| BR | 规则摘要 | 主落页 | 辅助落页 |
|----|---------|--------|---------|
| BR-019 | 一人默认一把 Key；设备 ≤3 把；Key 绑定唯一人员 | P4 生成抽屉（服务端校验） | — |
| BR-020 | 仅一次明文（存哈希）；丢失只能换新 | P4 生成成功弹窗/掩码列/换新 | — |
| BR-021 | 动态鉴权（在职+授权实时校验，缓存 60s） | P4 提示条/启用确认 | P5 鉴权说明列 |
| BR-022 | 90 天未用自动冻结，前 7 天提醒 | P4 lastUsedAt/失效原因 | 消息中心（跨模块） |
| BR-023 | 钉钉离职事件立即吊销 | P4 吊销弹窗/失效原因 | P5 401 样例 |
| BR-024 | 权限变更事件驱动同步 <5 分钟 | P1/P2/P3 授权抽屉提示 | 01 权限管理（跨模块） |
| BR-025 | 技能过审方可分发；P0 风险永久拒绝 | P1 审核抽屉/授权锁定 | P2 挂载技能校验 |
| BR-026 | 技能安装到可分发 <10 分钟 | P1 提交即审 + 自动扫描 | — |
| BR-027 | 机密/绝密不出库（标题+100字摘要+库内链接） | P3 密级元数据标记（**拦截已移除**） | P4/P5 固定提示（已移除） |
| BR-028 | 每次调用全量审计留痕，保留 180 天 | P5 日志表格/详情抽屉 | — |
| BR-029 | 默认 QPM 60，超限 429 告警，可按人调整 | P4 qpmLimit | P5 429 留痕 |
| BR-030 | experts.assemble 片段密级过滤/降级摘要 | P2 挂载提示（**本期不返回 knowledge_context**） | P3 说明（已移除） |
| BR-031 | 组织/授权数据以 01 权限管理为准 | P1/P2/P3/P4 授权对象数据源 | — |
| BR-032 | 多主体预留 tenant_id/entity_id | 后端落库（页面无感） | — |
| BR-033 | 失败 10 次/10 分钟自动冻结并通知 | P4 失效原因"失败锁定" | P5 失败日志 |
| BR-034 | 网关不执行 LLM/Skill（纯组装下发） | P2 组装预览提示 | P4 连接器配置提示 |
| BR-035 | 白名单总开关默认关；白名单外 403 告警 | P4 白名单置灰/抽屉 | P5 403 留痕 |

（全文完）
