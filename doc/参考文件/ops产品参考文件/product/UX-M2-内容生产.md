# UX-M2-内容生产

> **版本**：v1.9 | 2026-10-02
> **关联 PRD**：[`PRD-M2-内容生产.md`](./PRD-M2-内容生产.md)
> **全局规范**：[`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md)

---


> **视觉规范参考**：[`开发规范/UI设计与开发规范.md`](../../开发规范/UI设计与开发规范.md)（仅原型/设计阶段）
> **实现技术栈**：[`TECH-CONSTRAINTS.md § 1.2`](../engineering/TECH-CONSTRAINTS.md)（Vue 3 + Element Plus）
> **决策记录**：[`ADR-002`](../../adr/ADR-002-前端规范源选择.md)


## 0. OPS 设计 SSOT

> **设计规范**：[UX-OPS-设计规范.md](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[UX-OPS-页面原型索引.md](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[OPS-MENU-ROUTE-INDEX.md](../delivery/OPS-MENU-ROUTE-INDEX.md)

## 1. 页面清单

| 页面 ID | 名称 | 路由 | 关联 FR |
|---------|------|------|---------|
| P-M2-001 | SOP 模板列表 | `/ops/production/sop` | FR-M2-001 |
| P-M2-002 | SOP 模板编辑（DAG 画布） | `/ops/production/sop`（`:id` 深链/抽屉） | FR-M2-001 |
| P-M2-003 | 任务列表（含「我的任务」默认 Tab） | `/ops/production/task` | FR-M2-002 |
| P-M2-004 | 任务详情 | `/ops/production/task/:id` | FR-M2-002 |
| P-M2-005 | ~~我的任务~~（已合并至 P-M2-003 Tab） | — | FR-M2-002 |
| P-M2-006 | 内容列表（弹窗创作/查看） | `/ops/production/content` | FR-M2-003 |
| P-M2-007 | 内容创作/编辑（**路由保留**，菜单隐藏；主路径为弹窗） | `/ops/production/content/edit` | FR-M2-003 |
| P-M2-008 | 内容审核 | `/ops/production/content/review` | FR-M2-003 |
| P-M2-009 | 知识库列表 | `/ops/production/knowledge` | FR-M2-004 |
| P-M2-010 | 知识详情 | `/ops/production/knowledge/:id` | FR-M2-004 |
| P-M2-011 | 计划管理 | `/ops/production/plan` | FR-M2-009 |
| P-M2-012 | 任务执行 | `/ops/production/task/:id/execute` | FR-M2-002 |
| P-M2-013 | 公推模板库列表 | `/ops/production/layout-template` | FR-M2-005 |
| P-M2-014 | 公推模板导入向导 | `/ops/production/layout-template`（导入弹窗/向导） | FR-M2-005 |
| P-M2-015 | 公推模板编辑/预览 | `/ops/production/layout-template/:id/edit` | FR-M2-005 |
| P-M2-016 | 工作任务管理 | `/ops/production/work-task` | FR-M2-010 |
| P-M2-017 | SOP 模板审核 | `/ops/production/sop/review` | FR-M2-001 |
| P-M2-018 | 全部任务（菜单独立入口） | `/ops/production/task/all` | FR-M2-002 |

> **Football 路由 SSOT**：内容生产子模块统一 `#/ops/production/*`（非 legacy `/prod/*` 或扁平 `/content`）。索引：[`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md)。

---

## 1.1 P-M2-016 工作任务管理（FR-M2-010 · 2026-10-02）

**组件**：`ops/production/work-task/index.vue` · API `#/api/ops/workTask.ts`

| Tab | 名称 | 行为 |
|-----|------|------|
| register | 任务登记 | IP 组长；`getLedIpGroups` + 日期；表格行选；字段：赛事（多选）、作者、**发布账号** `publishAccountId`、营销计划、直播/时间、销售平台；保存/行级 confirm/withdraw；**合并执行** / 取消合并 |
| execution | 任务执行情况 | 筛选后 GET `/ops/work-task/execution`；节点粒度列表；可从已确认行赛事链入 |
| matrix | 任务管理 | 区间矩阵 + summary；列头 `{author}【{ipGroup}-{leader}】` |

**空态**：非组长 →「您不是 IP 组长，无法登记任务」。

---

## 2. P-M2-001 SOP 模板列表

| 控件 | 类型 | 文案/默认值 | 字典/实体 |
|------|------|------------|----------|
| F-NAME | `<Input />` | "模板名称" | - |
| F-CONTENT-TYPE | `<DictSelect dict-type="dict_content_type" />` | "内容类型" | 字典 |
| F-PLATFORM | `<DictSelect dict-type="dict_platform_type" />` | "平台类型" | 字典 |
| BTN-ADD | 按钮 | "新增模板" | - |
| BTN-EDIT | 链接 | "编辑" | - |
| BTN-DELETE | 链接 | "删除" | - |
| BTN-ACTIVATE | 链接 | "启用" | - |
| TBL-TPL | 表格 | - | `oa_sop_template` |

---

## 3. P-M2-002 SOP 模板编辑（DAG 画布）

> **版本**：v1.1 | 2026-06-11

### 3.1 布局（实现：栅格 4+14+6）

```
+------------------------------------------------------------------+
| 面包屑 | [保存] [返回] | 自动布局 | 适配视图 | 校验DAG | 撤销/重做 |
+------------------------------------------------------------------+
| 节点库 (lg:4)     |  LogicFlow 画布 (lg:14)  | 属性面板 (lg:6) |
| 拖拽节点模板      |  DAG 可视化 + 连线        | 节点名/岗位/审核  |
+------------------------------------------------------------------+
```

| 列 | 宽度 | 内容 |
|----|------|------|
| 左 | `el-col :lg="4"` | 节点模板拖拽列表 |
| 中 | `el-col :lg="14"` | LogicFlow 画布 |
| 右 | `el-col :lg="6"` | 选中节点属性（`dict_position`） |

**保存**：`persistNodes` 调用 `createSopNode` / `updateSopNode`；新节点 ID remap 后刷新边。

**缺口**：删除节点仅前端移除；无 `DELETE /sop/node` API（刷新恢复）。

### 3.2 节点编辑弹窗

| 控件 | 类型 | 字典/实体 | 必填 |
|------|------|----------|------|
| F-NODE-NAME | `<Input />` | - | ✅ |
| F-EXEC-ROLE | `<DictSelect dict-type="dict_position" />` | `dict_position` | ✅ |
| F-NEED-REVIEW | `<Switch />` | - | ✅（默认 false） |
| F-REVIEW-ROLE | `<DictSelect dict-type="dict_position" />` | `dict_position` | 条件（need_review=1 时必填） |
| F-PREDECESSORS | `<SelectMultiple />`（多选同模板其他节点） | `oa_sop_node` | ❌ |
| F-PARALLEL-GROUP | `<Input />` | - | ❌ |
| F-SLA-HOURS | `<InputNumber />` | - | ❌ |
| F-NODE-TYPE | `<DictSelect dict-type="dict_sop_node_type" />` | `dict_sop_node_type` | ✅（ADR-016） |
| F-NODE-DOC-TYPE | `<DictSelect dict-type="dict_document_type" />` | `dict_document_type` | ✅（仅 `CONTENT_GENERATION`，ADR-077） |

**`dict_sop_node_type` 选项**：内容生成 / 内容发布 / 普通节点。`F-NODE-DOC-TYPE` 在节点类型=内容生成时显示且必填。

### 3.3 状态

| 状态 | 表现 |
|------|------|
| 保存失败（DAG 环） | 红色 Banner："节点 X 与 Y 形成环" |
| 保存成功 | Toast "保存成功" + 画布刷新 |
| 节点无 `executor_role` | "请选择执行岗位" |

---

## 4. P-M2-003/004 任务列表/详情

**默认 Tab**：「我的任务」（`activeTab=my`），次 Tab「全部任务」。

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| TAB-MY | Tab | 「我的任务」（默认） |
| TAB-ALL | Tab | 「全部任务」 |
| F-IP | `<IpGroupTreeSelect />` | `oa_ip_group` |
| F-STATUS | `<DictSelect dict-type="dict_sop_node_status" />` | 字典 |
| F-EXECUTOR | `<UserSelect />` | `sys_user`（全部任务 Tab） |
| TBL-TASK | 表格 | `oa_task` |
| COL-SCHEDULE | 列 | `scheduled_start` / `scheduled_end`（计划起止） |
| BTN-EXECUTE | 链接 | 「执行」（仅「我的任务」Tab + 可执行态） |
| BTN-SUBMIT-REVIEW | 链接 | 「提交审核」：① 内容生成 + 关联内容 `DRAFT`/`REJECTED` → 内容 `submit-review`；② 非内容生成且 SOP `need_review=1` → 任务级审核（须先填工作说明，ADR-079） |
| BTN-COMPLETE | 链接 | 「完成」：非内容生成须工作说明；内容生成仅当内容审核通过（ADR-079） |

### 4.0 P-M2-018 全部任务（menu 6175 · `/ops/production/task/all`）

与 P-M2-003 **同一组件族**（`ops/production/task/all.vue` 或 task 页 `defaultTab=all`）：

| 项 | 规范 |
|----|------|
| 默认 Tab | 「全部任务」（非「我的任务」） |
| 筛选 | 较 P-M2-003 多 `F-EXECUTOR` `<UserSelect />` · 其余 IP/状态同 §4 |
| 行操作 | 无「执行」入口（仅我的任务 Tab）；保留「查看详情」 |
| 数据范围 | 具备 `oa:task:list` 全量；否则后端 1504 空列表 |
| API | `GET /admin-api/ops/task/list` · `scope=all` query |

---

### 4.1 P-M2-004 任务详情（抽屉 · 与执行页共用）

| 项 | 规格 |
|----|------|
| 入口 | 我的任务 / 全部任务列表 · 状态为只读态（`isTaskViewOnlyStatus`）→ 行操作「查看」 |
| 容器 | `el-drawer` 70% 宽 · 标题「任务详情 - {planName\|nodeName}」 |
| 组件 | `TaskExecutePanel` · `embedded` + **`readonly=true`**（与 P-M2-012 执行抽屉同组件） |
| 路由 | 无独立 menu 页；历史 Spec `/ops/production/task/:id` **未单独建路由** |

**抽屉内区域（现网）**

| 区域 | 内容 |
|------|------|
| IP 组 Tab | 多 IP 组任务时顶部 card tabs 切换 `taskId` |
| 基本信息 | `ElDescriptions`：任务名称、节点名称、IP 组、赛事、备注（工作任务来源时一行摘要）、状态 `dict_sop_node_status` |
| 操作区 | 内容生成/发布：关联内容摘要、LayoutViewer 预览、只读「查看内容」 |
| 工作说明 | 只读 textarea + 附件列表（SOP 参考附件 + 交付附件） |
| 底栏 | 仅 [返回]（无保存/完成） |

**Spec 目标 vs 现网（边缘 §11）**

| 项 | 状态 |
|----|------|
| SOP **全节点** `el-timeline`（已完成/进行中/待执行/已驳回） | **未实现** — 仅当前节点上下文 |
| 独立审核记录时间轴 | **未实现** — 审核态见列表/内容状态 |

**API**：`GET /admin-api/ops/task/execute?taskId=`（同执行页 `getTaskExecute`）

**空/加载/错**：`v-loading` · task 不存在 1504/404 → Toast + 关闭抽屉

### 4.2 SLA 超时展示

- 任务超时 → 节点标红 + 显示超时时长
- 顶部 Banner："您有 X 个超时任务"

---

## 4.3 P-M2-012 任务执行页（需求 4–5）

**路由**：`/ops/production/task/:id/execute` · **入口**：我的任务 → 状态=待执行 →「执行」

```
+----------------------------------------------------------+
| 任务基本信息（名称、节点、IP组、赛事、状态；不展示 SLA；工作任务来源时同区仅一行「备注」：赛事-营销计划-是否直播（直播时间）-销售平台； 合并组多场多段） |
+----------------------------------------------------------+
| 执行说明（只读，`oa_sop_node.instruction_text`）                        |
| 附件列表只读（`attachment_urls` JSON；上传见 BLK-M2-007）                            |
+----------------------------------------------------------+
| [node_type=内容生成]                                     |
|   关联内容摘要 / 「进入内容创作」→ /ops/production/content/edit?taskId= |
| [node_type=内容发布] 占位（BLK-M2-009）                  |
| [node_type=普通节点] 交付说明输入区                      |
+----------------------------------------------------------+
| [保存]  [完成]                                           |
+----------------------------------------------------------+
```

| 控件 | 类型 | 说明 |
|------|------|------|
| BTN-CONTENT-EDIT | 按钮 | 打开 `ContentEditDialog`（`taskId`）；非路由菜单 |
| BTN-SAVE | 按钮 | 保存执行页草稿字段 |
| BTN-COMPLETE | 按钮 | 完成；非内容生成须工作说明；内容生成须内容审核通过（ADR-079） |
| BTN-CONTENT-SUBMIT-REVIEW | 按钮 | 内容生成且关联内容 `DRAFT`/`REJECTED`：「提交审核」→ `POST /ops/content/{id}/submit-review` |

| 状态 | 表现 |
|------|------|
| 无关联内容 | 提示「请先进入内容创作」（工作任务 confirm 后通常已有 DRAFT，ADR-077） |
| 内容可提交审核 | 展示「提交审核」（`DRAFT`/`REJECTED`） |
| 内容未审核通过 | 完成按钮禁用 + Tooltip「内容须审核通过后方可完成任务」 |
| 非内容生成未填工作说明 | 完成禁用或提交时 1500「请填写工作说明」 |
| 完成成功 | Toast + 返回我的任务列表 |
| AI 生成中 | Badge「生成中」（`aiGenerateStatus=QUEUED/GENERATING`） |
| AI 失败 | Badge「失败」+ 原因 + 按钮「重试」（ADR-077） |

---

## 5. P-M2-006/007 内容列表/编辑

### 5.1 内容列表

**路由**：`/ops/production/content` · **组件**：`ops/production/content/index.vue`（列表）+ `ContentEditDialog` / `ContentEditPanel`  
**权限**：`oa:content:list` · 写操作 `oa:content:create|update|delete` · 批量 `oa:content:batch-*`（ADR-081）

**布局 A/B/C**：

```
A | 标题「内容管理」  [新增内容] [导出] [批量提交审核] [批量删除] [批量转知识库]
B | 标题 · 平台 · 内容类型 · 状态 · 账号 · 是否AI生成 · [查询][重置]
C | el-table + Pagination（pageNum/pageSize）
```

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-TITLE | `<Input />` | 标题模糊 → `title` |
| F-PLATFORM | `<DictSelect dict-type="dict_platform_type" />` | `platformType` |
| F-CONTENT-TYPE | `<DictSelect dict-type="dict_content_type" />` | `contentType` |
| F-STATUS | `<DictSelect dict-type="dict_content_status" />` | `status` |
| F-ACCOUNT | `<AccountSelect />` | `accountId` |
| F-AI-GENERATED | `<DictSelect dict-type="dict_yes_no" />` | `aiGenerated` |
| TBL-CONTENT | 表格 | 列：标题、类型、平台/账号、状态 Tag、赛事摘要、AI 生成态、创建人、更新时间 |
| BTN-ADD | 按钮 | 「新增内容」→ 打开 `ContentEditDialog` |
| BTN-EXPORT | 按钮 | 导出 CSV（ADR-018） |
| BTN-BATCH-DELETE | 按钮 | 「批量删除」：勾选行中 `DRAFT`/`REJECTED`（ADR-081） |
| BTN-BATCH-SUBMIT | 按钮 | 「批量提交审核」：勾选行中 `DRAFT`/`REJECTED`（ADR-081） |
| BTN-BATCH-TRANSFER | 按钮 | 「批量转知识库」：勾选行中可转知识库（ADR-081） |
| BTN-VIEW | 链接 | 只读弹窗 + 审核流程 steps |
| BTN-SUBMIT | 链接 | 「提交审核」（DRAFT / REJECTED） |
| COL-AI-GEN | 列 / Badge | 「生成中」/「失败」+ 失败可「重试」（ADR-077 `aiGenerateStatus`） |

> **无**独立侧栏菜单「内容创作」；`/ops/production/content/edit` 路由保留供深链。

### 5.2 内容编辑（`ContentEditPanel` / `ContentEditDialog`）

**模式 A — 独立创作**（弹窗）：提交审核；无封面字段。

**模式 B — 任务驱动**（执行页弹窗或带 `taskId`）：

| 控件 | 类型 | 字典/实体 | 必填 |
|------|------|----------|------|
| F-TASK-ID | 隐藏 | `oa_task` | ✅（模式 B） |
| F-IP-GROUP | 只读 | 任务 IP 组 | ✅ |
| F-COMPETITION | `<MatchSelectDialog />` | 外部赛事 | 可选 |
| F-TITLE | `<Input />` | - | ✅ |
| F-CONTENT-TYPE | `<DictSelect dict-type="dict_content_type" />` | 字典 | ✅ |
| F-DOCUMENT-TYPE | `<DictSelect dict-type="dict_document_type" />` | 字典 | 条件（`ARTICLE`） |
| F-SCRIPT-REF | 只读区 | 同赛事短视频文案 | 条件（`SHORT_VIDEO`） |
| F-BODY | **`<RichTextEditor />`**（ARTICLE）或 `<Textarea />`（其他） | layout_html + body 摘要 | 条件 |
| F-LAYOUT-STRUCT | **`<LayoutEditor />`**（右侧，LAYOUT 时） | layout_json | 条件（ARTICLE+已套用模板） |
| F-LAYOUT-TPL | `<LayoutTemplateSelect />` | `oa_wechat_layout_template` | 条件（`ARTICLE`） |
| BTN-QUICK-TYPESET | 按钮 | 「一键排版」→ `WechatQuickTypesetDialog`（FOOTBALL_AI 四套预设） | 条件（`ARTICLE`） |
| BTN-AI-TYPESET | 按钮 | 「AI 排版」→ `AiTypesettingDialog`（LLM 语义） | 条件（`ARTICLE`） |
| BTN-APPLY-TPL | 按钮 | 「选择版式模板」→ 选择器 + 二次确认 | 条件（`ARTICLE`） |
| F-GENERATED-VIDEO | 预览 | AI 生成视频 URL | 条件（短视频） |
| F-FINAL-VIDEO | `<Input />` | 最终视频 URL | ❌ |
| BTN-GENERATE | 按钮 | AI 弹窗（选 M8 模型+提示词，真实 LLM） | - |
| BTN-SAVE | 按钮 | 「保存」→ `DRAFT` | - |
| BTN-SUBMIT-REVIEW | 按钮 | 「提交审核」（非「确认」） | - |

**模式 A 额外字段**：

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-IP-GROUP | `<Select />` 用户所属 IP 组 | **必填** |
| F-PLATFORM | `<DictSelect multiple />` | 可选 |
| F-ACCOUNT | `<AccountSelect multiple />` | 可选，联动 platform + ip_group |
| F-AI | `<Switch />` + AI 弹窗 | - |

**只读/待审核**（`PENDING_*`）：表单 disabled；展示审核流程 `el-steps`（角色+用户）。

**联动**：
- `content_type=ARTICLE` → 显示 `document_type` + **版式模板区**
- `content_type=SHORT_VIDEO` → 文案引用区
- 切换 IP 组 → 刷新作者信息
- 应用模板后 → 富文本编辑器即时显示 `layout_html`；`body_format=LAYOUT`；`body` 为纯文本摘要（ADR-021）

> **FR-135（2026-06-14）**：ARTICLE 正文主区为 TipTap 富文本；左右分栏，右侧为版式结构编辑（套用模板后可见）。

**变更 2026-06-15（FR-143 / FR-147 · ADR-021）**：

| 控件/行为 | 说明 |
|-----------|------|
| BTN-MAXIMIZE | 正文区「全屏/还原」；全屏时隐藏版式侧栏 |
| BTN-LAYOUT-COLLAPSE | 「展开/收起版式结构」；**默认收起** |
| F-LAYOUT-STRUCT | 收起或全屏时主区 24 栅格；展开时 14+10 分栏 |
| RTE-TOOLBAR | 对齐公众号编辑器：字号/颜色/高亮/对齐/列表/引用/表格/图片上传与宽度 |
| WECHAT-PASTE | 粘贴走 `normalizeWechatPasteHtml`；保存走 `sanitizeWechatExportHtml` |
| IMG-WIDTH | 编辑态 `ResizableImage`；查看态 `LayoutViewer` + `ensureImageWidthStyles` 一致 |

**只读/待审核**（`PENDING_*`）：`LayoutEditor` **readOnly**；无 `layout_json` 时 fallback 渲染 `body` 纯文本

### 5.2.1 版式模板选择器（`LayoutTemplateSelectDialog`）

| 控件 | 说明 |
|------|------|
| F-DOC-TYPE-FILTER | 按当前内容 `document_type` 过滤（+ 通用模板 document_type 为空） |
| TBL-TPL | 卡片/表格：缩略图、名称、document_type 标签、来源（手动/链接/Word） |
| BTN-PREVIEW | 抽屉预览 `layout_html` |
| BTN-APPLY | 应用（若已有版式 → `MessageBox.confirm`） |
| FREE-ONLY | 行为 | 仅免费区有正文、付费区为空 → preview/apply **只写免费栏**（`detectTemplateMergeTarget`） |

### 5.3 AI 辅助创作弹窗

- 选择 **M8 已启用 AI 模型**（`GET /config/ai-model/list` enabled）
- 选择 **匹配提示词**（按 `contentType` / `documentType`）
- 「生成」→ 调 `POST /ops/ai-content/generate`（或 `POST /ops/content/{id}/generate`）→ 写入 `body`

---

## 6. P-M2-008 内容审核（ADR-017）

**Tab**：一级审核 / 二级审核（随 `review-config` 动态显示；均未开启时提示直接发布）。

| 控件 | 类型 | 说明 |
|------|------|------|
| TAB-L1 | Tab | 一级审核队列 |
| TAB-L2 | Tab | 二级审核队列 |
| TBL-REVIEW | 表格 | 待审内容 |
| BTN-VIEW | 链接 | 只读抽屉 + 正文（**`LayoutViewer`** 渲染 layout_html）+ 审核流程 steps |
| BTN-APPROVE / REJECT | 按钮 | 仅待审态、有权限时 |

**审核详情抽屉**（`BTN-VIEW` / 行内审核）：720px · 只读 `LayoutViewer` 渲染 `layout_html` · `el-steps` 审核流程 · 底部「通过」「驳回」+ 意见 `textarea` · 驳回须 `MessageBox.confirm`  
**API**：列表 `GET /admin-api/ops/content/review/list` · 通过/驳回 `POST .../approve` / `.../reject`（见 API-M2 §3.6）

审核流程 steps 描述格式：`{角色名}：{用户1、用户2}`。

**空/加载/错**：`v-loading` · 队列为空 `el-empty`「暂无待审内容」· 1500–1504 → `ElMessage.error`

---

## 7. P-M2-009/010 知识库

| 项 | 规格 |
|----|------|
| Football 路由 | `/ops/production/knowledge` |
| Vue | `ops/production/knowledge/index.vue` |
| permission | `oa:knowledge:list`（写：`oa:knowledge:create|update|delete`） |
| 布局 | **B** `TableSearch` + **A** 操作条 + **C** 列表或卡片 + 分页 |

### 7.0 列表筛选（B）

| 控件 | 类型 | query |
|------|------|-------|
| F-KEYWORD | Input | `keyword` 标题/标签 |
| F-CATEGORY | Select | `case`/`template`/`industry`/`experience`（提交映射后端 `CASE_LIB` 等） |
| F-IS-PUBLIC | Switch | 是否仅公开（筛选） |

### 7.0.1 视图切换（A）

| 控件 | 行为 |
|------|------|
| BTN-ADD | 「新增知识」→ 800px 编辑 dialog |
| VIEW-MODE | `el-radio-group`：**列表视图** `list` \| **卡片视图** `card`（默认 list） |
| 卡片视图 | `el-row` 卡片：分类 tag · 标题 · 前 3 标签 · 阅读/收藏数；点击卡片 = 打开详情 |

### 7.0.2 列表列（C · list 模式）

| 列 | 说明 |
|----|------|
| 标题 | `title` |
| 分类 | tag（案例库/模板库/行业资料/运营经验） |
| 标签 | 多 tag |
| 是否公开 | 图标 View/Lock |
| 创建者 / 创建时间 | |
| 操作 | 查看 · 编辑 · 删除（删除 `MessageBox.confirm`） |

### 7.0.3 编辑 dialog 字段

| 字段 | 控件 |
|------|------|
| title | Input 1–100 |
| category | Radio 四分类 |
| tags | 原生 tag 输入，最多 10 个 |
| isPublic | Switch |
| content | Textarea 12 行（HTML 富文本字符串） |

**API**：`GET /ops/knowledge/list` · `GET /ops/knowledge/{id}` · `POST /ops/knowledge/create` · `PUT /ops/knowledge/update` · `DELETE /ops/knowledge/delete` · `POST /ops/knowledge/{id}/like`

### 7.1 P-M2-010 知识详情（600px 抽屉 · 非独立路由）

| 区域 | 内容 |
|------|------|
| A | 标题 + [编辑] [删除] [返回列表]（权限门控） |
| C-元数据 | 分类、标签、是否公开、创建人、更新时间 |
| C-正文 | Markdown/富文本只读区；附件列表可下载 |
| 编辑弹窗 | 同列表字段；`F-CATEGORY` 固定枚举 Select；保存 `PUT /admin-api/ops/knowledge/update` |

**空/错**：`id` 不存在 → `el-result` 404 + 返回列表 · 加载 skeleton

---

## 8. P-M2-013~015 公推模板库（FR-M2-005 · 草案）

> **菜单**：内容生产 → **公推模板库**（与「知识库」并列，**非**知识库「模板库」分类）

### 8.1 P-M2-013 模板列表

**路由**：`/ops/production/layout-template`

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-NAME | `<Input />` | 模板名称 |
| F-DOC-TYPE | `<DictSelect dict-type="dict_document_type" />` | 可筛「通用」（空） |
| F-STATUS | `<DictSelect dict-type="dict_layout_template_status" />` | 启用/停用 |
| F-SOURCE | `<DictSelect dict-type="dict_layout_template_source" />` | 手动/链接/Word |
| BTN-ADD | 按钮 | 「新建模板」→ P-M2-015 |
| BTN-IMPORT | 按钮 | 「导入」→ P-M2-014 |
| BTN-EDIT | 链接 | 编辑 |
| BTN-PREVIEW | 链接 | 只读预览抽屉 |
| BTN-DISABLE | 链接 | 停用（二次确认） |
| TBL-TPL | 表格 | 名称、document_type、来源、更新人、更新时间、状态 |

**权限**：无 CRUD 权限者 **不展示** BTN-ADD/EDIT/DISABLE（仍可只读列表，**待产品确认**）

### 8.2 P-M2-014 导入向导（独立路由页）

| 项 | 规格 |
|----|------|
| 入口 | 列表 [导入向导] → `LayoutTemplateImport` |
| Vue | `ops/production/layout-template/import.vue` |
| 布局 | `el-page-header` 返回 + 顶栏 disclaimer Alert（ADR-020 套用 vs 预览） |

**Tab 导入方式（非 el-steps 三步条）**

| Tab name | 标签 | 输入 |
|----------|------|------|
| `url` | 公众号链接 | URL + 可选模板名 · [开始导入]（反爬失败提示改 MHTML/HTML） |
| `mhtml` | MHTML 上传 | `.mhtml` 单文件 · 可选模板名 · 覆盖模板 ID（可选）· Shenyu H5 自动 Profile |
| `html` | 粘贴 HTML | 富文本/源码粘贴区 + 模板名 |

| 状态 | 表现 |
|------|------|
| 导入中 | `importing` loading · URL 异步 Job 可关页后在列表查看 |
| 成功 | Toast + 跳转编辑或列表 |
| 失败 | Alert 引导换 Tab |

**API**：以 `#/api/ops/layoutTemplate` 导入端点为准（link/mhtml/html 三类）。

### 8.3 P-M2-015 模板编辑 / 预览（独立路由）

**编辑** `ops/production/layout-template/edit.vue` · 路由 `LayoutTemplateEdit`（`id=0` 新建）

| 字段 / 区 | 说明 |
|-----------|------|
| templateName | Input · PRESET 源只读 |
| documentType | `DictSelect dict_document_type` 可空=通用 |
| status | 只读 DictLabel |
| description | Textarea |
| 版式 Tab | **富文本编辑** `RichTextEditor` \| **结构编辑** `LayoutSchemaEditor`（ADR-021 双向 sync） |
| 按钮 | 保存 · 发布/停用/启用 · PRESET → [复制后编辑] |

**预览** `layout-template/preview.vue` · 路由 `LayoutTemplatePreview`

- 全页（非 drawer）：`el-descriptions` 元数据 + `LayoutViewer` 卡片（`previewHtml`/`layoutHtml`）
- 列表行 [预览] 跳转此页（非列表内抽屉）

> **FR-147**：富文本 Tab 与内容创作同 `RichTextEditor` 组件族。

### 8.4 内容查看/审核 — 版式渲染（跨 P-M2-006/008）

| 场景 | 组件 | 数据 |
|------|------|------|
| 有 `layout_html` | `<LayoutViewer readOnly />` | `layout_html` |
| 仅 `body` 纯文本 | `<pre>` 或 `<Textarea disabled />` | `body` |
| 列表摘要 |  strip HTML 前 80 字 | `layout_html` 优先 |

---

## 9. P-M2-011 计划管理

**路由**：`/plan` · **实现**：`views/production/plan/index.vue`

### 9.1 列表页

| 控件 | 类型 | 字典/实体 |
|------|------|----------|
| F-PLAN-NAME | `<Input />` | - |
| F-STATUS | `<DictSelect dict-type="dict_plan_status" />` | 字典 |
| BTN-ADD | 按钮 | "新增计划" |
| TBL-PLAN | 表格 | `oa_content_plan` |
| COL-PROGRESS | `<Progress />` | 按任务完成率 |
| BTN-START | 链接 | 草稿 → "启动" |
| BTN-TERMINATE | 链接 | 进行中 → "申请终止" |
| BTN-APPROVE-TERM | 链接 | 终止审批中 → "批准终止"（组长） |
| BTN-REJECT-TERM | 链接 | 终止审批中 → "驳回终止"（组长） |
| BTN-DELETE | 链接 | 草稿 → "删除" |

### 9.2 新增计划弹窗（960px）

```
+----------------------------------------------------------+
| 基本信息                                                  |
| 计划名称 [__]     日期范围 [daterange]                    |
| SOP 模板 [select]  IP 组 [IpGroupTreeSelect]             |
| 关联赛事 [MatchSelectDialog]（外部 API）               |
| 计划描述 [textarea]                                       |
+----------------------------------------------------------+
| SOP 步骤分配（选模板后自动加载节点）                       |
| # | 步骤名称 | 节点类型 | 赛事（多选） | 执行岗位 | 执行人（单选） | 开始 | 结束 |
+----------------------------------------------------------+
| [取消]  [保存草稿]                                        |
+----------------------------------------------------------+
```

| 控件 | 类型 | 字典/实体 | 必填 |
|------|------|----------|------|
| F-PLAN-NAME | `<Input />` max 100 | - | ✅ |
| F-DATE-RANGE | `<DatePicker type="daterange" />` | - | ✅ |
| F-TEMPLATE | `<Select />`（启用模板） | `oa_sop_template` | ✅ |
| F-IP-GROUP | `<IpGroupTreeSelect />` | `oa_ip_group` | ✅ |
| F-COMPETITIONS | `<MatchSelectDialog multiple />` | 外部赛事 `scheduleId` | ✅（≥1） |
| F-DESCRIPTION | `<TextArea />` max 500 | - | ❌ |
| F-STEP-COMPETITION | `<Select multiple />` | 计划赛事池 | ✅（每节点 ≥1） |
| F-STEP-ASSIGNEE | `<UserSelect />`（单选） | `sys_user` | ✅（每节点 1 人） |
| F-STEP-START/END | `<DateTimePicker />` | 默认计划日期 | ❌ |

**联动**：
- 选 SOP 模板 → 拉取节点列表填充步骤表
- 改日期范围 → 未填写的步骤起止时间默认同步

### 9.3 详情抽屉

只读展示：计划名称、模板、IP 组、日期、状态、赛事列表、描述、**生成的任务记录表**（含 scheduled_start/end、executor_role）。

### 9.4 状态与提示

| 状态 | 表现 |
|------|------|
| 保存成功 | Toast "计划已保存为草稿" |
| 启动确认 | 二次确认："启动后关联任务将出现在任务列表" |
| 申请终止 | `prompt` 输入终止原因 |
| 批准终止 | 二次确认（组长） |
| 驳回终止 | 二次确认（组长）；计划回到进行中 |
| 步骤未分配执行人 | 警告 "请为每个 SOP 步骤分配执行人" |

---

## 11. P-M2-017 SOP 模板审核（`/ops/production/sop/review`）

**组件**：`ops/production/sop/review.vue` · **权限**：`oa:sop:list` + 审核写权限（与 SOP 模板同域）

**布局**：

```
A | （无独立页头按钮）— 顶部 4 卡：待审核 / 今日通过 / 今日驳回 / 平均审核时长(h)
B | 模板名称 · 提交人 · 状态(dict_review_status) · 提交时间范围 · [查询][重置]
C | 审核队列表 + Pagination（pageNo/pageSize）
```

| 列 | 说明 |
|----|------|
| 模板名称 | `templateName` |
| 适用类型 | `DictLabel dict_content_type` |
| 提交人 / 提交时间 | — |
| 优先级 | Tag（高/中/低配色） |
| 状态 | `dict_review_status` |
| 操作 | 查看 · 通过 · 驳回（仅 `PENDING`） |

**审核详情抽屉**（60% 宽）：`el-descriptions` 基本信息 · 节点表（节点名、执行岗位、SLA、是否需审核）· 待审时底部意见 `textarea` + [通过][驳回][取消]

**交互**：

- 列表「通过/驳回」→ `MessageBox.confirm` → `POST /admin-api/ops/sop/template/review`（或等价 approve/reject 端点，以 API-M2 §1 为准）
- 抽屉内提交与列表快捷操作互斥（同一 `assignmentId`/`templateId`）
- 加载 `v-loading` · 空队列 `el-empty`

**边缘**：统计卡数据来自 summary API；若后端未实现则显示 `—` 且不阻塞列表

---

## 10. 跨页通用约定

- **关联属性强制选择**：所有 `*_id` 字段必须用选择器
- **字典字段**：状态/类型/平台一律 `<DictSelect />`
- **岗位字段**：`<DictSelect dict-type="dict_position" />`
- **IP 组筛选**：列表页支持 IP 组树形选择器
- **面包屑**：仅 `Layout.vue` 顶栏一处；页面内不再重复 `el-breadcrumb`（2026-06-13）

---

## CHANGELOG

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-14 | v1.4 | 公推模板、计划管理 |
| 2026-10-02 | v1.9 | DOC-UX-PAGE-FULL-02：§4.1 任务详情抽屉 · §7 卡片视图 · §8.2–8.3 导入/编辑/预览路由 |
| 2026-10-02 | v1.8 | P-M2-017 SOP 审核 · P-M2-018 全部任务 · §5.1 列表 B/C · §6 审核抽屉 · §7.1 知识详情 |
| 2026-10-02 | v1.6 | P-M2-001~015 路由与 OPS-MENU-ROUTE-INDEX 对齐 |
| 2026-10-02 | v1.5 | P-M2-016 工作任务三 Tab；Football `/ops/production/*` 路由注记 |

---

*下一步：API Spec / STATE / SLICES / CHECKLIST / TESTCASES。*
