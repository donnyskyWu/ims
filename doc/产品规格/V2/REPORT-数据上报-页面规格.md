# REPORT - 数据上报 页面规格

> 依据：《IMS完整产品需求文档.md》v2.6.9 §09（走查 #10 续）、《IMS第二期PRD-V2.md》5.8~5.11（REPORT-001~004）、《共享技术规范-分期技术约束.md》V2-A1（周期任务自动生成填报待办）、《REPORT-数据上报-API契约.md》、《全局开发规范.md》第 4 章（权威枚举）、OPS `PRD-M1` ADR-051（作者选择器）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/report`。
> 归属期次：V2 第 15~18 周（V2.1 管理动作线上化批次）。
> **枚举口径说明**：填报单四态使用全局权威枚举 `SubmissionStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'`（契约 2.2.1 值域一致）；周期类型引用全局 `PeriodType = 'DAILY' | 'WEEKLY' | 'MONTHLY'`。

## 0. 模块总览

### 0.1 IMS 导航（完整 PRD v2.6.9 · 走查 #10 / #10 续）

| 侧栏 L1 组 | L2 | L3 子菜单 | 路由 | 说明 |
|------------|-----|-----------|------|------|
| **协同与成长** | **数据上报**（可展开） | 上报模板 · 填报单管理 · 完成率统计 | `/ims/report/template`、`/ims/report/submission`、`/ims/report/stat` | REPORT-001～004 |
| — | — | P2 填报（二级） | `/ims/report/submit/{taskId}` | 工作台「待填报任务」进入 |

**语义**：模板化指标/勾稽填报与审核（BR-106）；**不是** MEET 三段式工作日报（03 日报中心）。**API**：`/admin-api/ims/report/*`（见《REPORT-数据上报-API契约.md》18 个接口 + §2.2 归因字段）。**OPS**：M6 标准报表 RPT-001～008 只读查询，与本模块写入路径分离；**OPS 无作者×账号填报归因**，IMS 新建列 `author_id` / `account_id`。

### 0.2 作者×账号归因（走查 #10 续 · FR-REPORT-011～014）

| 字段 | 组件 | 必填 | 数据来源 | 校验 |
|------|------|------|----------|------|
| `authorId` | `<AuthorSelect />` | 是 | `author_user.id`；`GET /admin-api/ims/ip-group/author/page`（或 OPS 作者列表等价接口） | 1500 不存在 / 1501 已停用；1504 跨租户 |
| `accountId` | `<AccountSelect />` | 是 | M4 `oa_account.id`；M4 AccountSelect 契约 | 同上；**1127** 账号不在作者 SMALL IP 组已绑账号池 |

**页面落点**：P2 动态表单 **上方固定区**「归因上下文」（AuthorSelect → AccountSelect 级联）；P1 字段类型可声明 `AUTHOR`/`ACCOUNT`（与固定区同语义，fieldKey 建议 `_authorId`/`_accountId` 或业务键，禁止与 submission 列重复写入两次）；P3 列表/审核只读展示；P4 完成率/未交清单可选按作者/账号筛选。

**级联（2026-10-01 冻结）**：作者 onChange → 取作者 `ipGroupId` → `GET /admin-api/ims/ip-group/{groupId}/accounts` 填充 AccountSelect；**禁止**新增 `GET …/authors/{id}/accounts`；共池失败 **1127**。

**验收（FR-REPORT-011 · 1127）**：当所选 `accountId` **不属于**当前作者 IP 组账号池（与作者绑定池不一致，含跨组账号、仅绑在其他作者组下的账号）时，`POST /report/submit`（含 asDraft=false；契约 2.2.1 同规则）返回 **1127**；P2 归因区 AuthorSelect/AccountSelect **双字段红标** + 顶部错误条，**不**持久化违规组合。

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 上报模板配置 | `/ims/report/template` | 一级菜单页（列表 + 模板设计抽屉） | REPORT-001 |
| P2 填报页 | `/ims/report/submit/{taskId}` | 二级页面（动态表单，Web + H5 同构） | REPORT-002 |
| P3 填报单管理 | `/ims/report/submission` | 一级菜单页（列表 + 详情抽屉 + 审核抽屉） | REPORT-002/003 |
| P4 上报统计看板 | `/ims/report/stat` | 一级菜单页（Tab 看板） | REPORT-004 |

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；交互操作优先内联抽屉（Drawer），不跳转新页面；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红 / 中性灰）；
- 周次/月份展示用波浪号格式（周期标识 2025-W24 渲染为"2025 第 24~24 周"式周表述按模板周期类型展示）；
- R9 视角金额类字段脱敏 `"***"`（服务端按角色脱敏）；
- 枚举一律引用《全局开发规范.md》第 4 章：`SubmissionStatus`、`PeriodType`、`EnableStatus`。

---

## P1. 上报模板配置（REPORT-001）

### 1. 页面概述
- 路由路径：`/ims/report/template`
- 页面级别：一级菜单页（模板列表 + 模板设计抽屉 + 预览弹窗）
- 依赖模块：AUTH 岗位字典（按岗位指派）、AUTH 人员选择器（按人/轮值）、工作流 FLOW（填报任务分派联动）
- 权限矩阵引用（PRD 4.2 REPORT-001）：R1 R/W/D（全量）、R3 R/W（财务模板）、R4 R/W（业务模板）、R9 R；业务线路由 FINANCE/BUSINESS/ADMIN

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 模板名称 | 周期类型 | 业务线 | 状态 | [查询][重置] [创建模板]|
+------------------------------------------------------------------+
| 模板列表表格:                                                     |
| 编号|模板名称|周期|截止规则|填报人配置|业务线|版本|状态|创建时间|操作   |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
模板设计抽屉(880px): Tab: [基础与周期] [字段设计] [填报人]
  基础: 模板名称* | 业务线*(财务/业务/行政) | 周期类型*(每日/每周/每月)|
    截止规则*(按周期联动: 每日HH:mm / 周X HH:mm / 次月N日)
  字段设计: 字段可视化编辑器(动态行):
    字段键*|标签*|类型*(NUMBER/TEXT/ENUM/DATE/ATTACHMENT/AUTHOR/ACCOUNT)|必填|范围|枚举选项|勾稽规则
    勾稽: 目标字段*|操作符*(EQ/LTE/GTE)|错误提示*
  填报人: 指派方式*(按人/按岗位/按部门轮值) + 对应配置器
  底部: [预览校验] [保存] [保存并启用]
预览弹窗(640px): 按 fieldsSchema 渲染样例表单 + 校验结果(errors 定位)
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ReportTemplateCreateReq {
  templateName: string;             // 必填 ≤128 字
  businessLine: BusinessLine;       // 必填 FINANCE/BUSINESS/ADMIN
  fieldsSchema: ReportFieldSchema[];
  periodType: PeriodType;           // DAILY / WEEKLY / MONTHLY
  deadlineRule: string;             // 必填：'22:00' | 'FRIDAY_18:00' | 'NEXT_MONTH_5TH'
  assignees: TemplateAssignee[];
  status: EnableStatus;             // ENABLED / DISABLED
  clientToken: string;
}
interface ReportFieldSchema {
  fieldKey: string;                 // 必填 唯一
  fieldLabel: string;               // 必填 ≤64 字
  fieldType: FieldType;             // NUMBER/TEXT/ENUM/DATE/ATTACHMENT/AUTHOR/ACCOUNT
  required: boolean;
  range?: { min?: number; max?: number };   // NUMBER 范围校验
  options?: string[];               // ENUM 选项
  crossCheck?: {                    // 勾稽规则（RPT-T-R2）
    targetFieldKey: string;
    operator: CrossCheckOperator;   // EQ / LTE / GTE
    errorMsg: string;
  };
}
interface TemplateAssignee {
  assignType: AssignType;           // USER / POSITION / DEPT_ROTATION
  targetIds?: number[];             // USER
  targetCodes?: string[];           // POSITION
  rotationList?: Array<{ userId: number; order: number }>;   // DEPT_ROTATION 轮值
}
interface ReportTemplateEditReq extends ReportTemplateCreateReq {
  id: number;                       // 生成新版本 version+1（RPT-T-R1）
}
interface TemplatePreviewReq {
  version?: number;
  sampleData?: Record<string, unknown>;
}

// 响应类型
interface ReportTemplateVO {
  id: number;
  templateNo: string;               // RT+日期+流水
  templateName: string;
  fieldsSchema: ReportFieldSchema[];
  periodType: PeriodType;
  deadlineRule: string;
  assignees: TemplateAssignee[];
  version: number;
  status: EnableStatus;
  businessLine: BusinessLine;
  createdBy: number;
  createdAt: string;
}
interface TemplatePreviewResp {
  renderedFields: ReportFieldSchema[];
  validationResult: {
    passed: boolean;
    errors: Array<{ fieldKey: string; errorMsg: string }>;
  };
}

// 枚举类型
type BusinessLine = 'FINANCE' | 'BUSINESS' | 'ADMIN';   // 财务线/业务线/行政线
type FieldType = 'NUMBER' | 'TEXT' | 'ENUM' | 'DATE' | 'ATTACHMENT' | 'AUTHOR' | 'ACCOUNT';
type AssignType = 'USER' | 'POSITION' | 'DEPT_ROTATION';
type CrossCheckOperator = 'EQ' | 'LTE' | 'GTE';
// PeriodType / EnableStatus —— 全局权威枚举
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /report/template/list`；R3 限财务线、R4 限业务线（服务端过滤）。失败重试。

#### 4.2 核心操作流程
**A. 创建模板（R1/R3/R4 本线）**
1. [创建模板] → 抽屉三 Tab：
   - 基础与周期：名称、业务线、周期类型；截止规则按周期联动表单（每日→HH:mm；每周→周几+HH:mm；每月→次月 N 日）；
   - 字段设计：可视化字段行编辑器（动态增删/拖拽排序）：字段键（唯一性即时校验）、类型切换控件联动（NUMBER→范围输入、ENUM→选项列表、ATTACHMENT→FileUpload 约束）、必填开关；勾稽规则配置（目标字段下拉 + 操作符 + 错误提示，校验目标字段存在否则 1121）；
   - 填报人：指派方式三选一 → 按人（人员多选）/按岗位（岗位多选）/按部门轮值（人员排序编辑器）；
2. [预览校验] → `POST /report/template/{id}/preview` → 弹窗渲染样例表单 + 校验结果（errors 行内定位）；
3. [保存]（存 DISABLED 草稿态）或 [保存并启用]（ConfirmDialog："启用后系统将按周期自动生成填报待办"）→ `POST /report/template`。

**B. 编辑模板（新版本，RPT-T-R1）**
1. [编辑] → 抽屉预填 → 提交 `PUT /report/template/{id}` → version+1；
2. 提交提示"将生成新版本 V{n+1}，进行中填报单沿用旧版 V{n}"。

**C. 停用/删除（R1）**
1. [停用] → ConfirmDialog warning："有进行中填报单的模板仅支持停用（进行中单据沿用旧版）" → `DELETE /report/template/{id}`；
2. 停用后模板不再生成新周期待办；历史填报单可查。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| templateName | Input | 否 | 空 | 模板名称模糊匹配 |
| periodType | Select | 否 | 空 | 每日/每周/每月 |
| businessLine | Select | 否 | 空 | 财务/业务/行政线 |
| status | Select | 否 | 空 | 启用/停用 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| templateNo | 模板编号 | 140 | — | 等宽字体（RT…） |
| templateName | 模板名称 | 自适应 | — | 行点击打开设计抽屉（预填只读+编辑态） |
| periodType | 周期 | 90 | — | 每日/每周/每月 |
| deadlineRule | 截止规则 | 130 | — | 渲染文案（如"每日 22:00"/"次月 5 日"） |
| assigneesSummary | 填报人 | 140 | — | "按人 N 人"/"岗位 X"/"轮值 N 人" |
| businessLine | 业务线 | 90 | — | 财务/业务/行政 tag |
| version | 版本 | 70 | ✓ | V{n} |
| status | 状态 | 90 | — | tag：启用(绿)/停用(灰) |
| createdAt | 创建时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| actions | 操作 | 160 | — | [编辑][预览][停用] 按权限/状态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 模板设计抽屉 | Drawer 880px | 三 Tab；templateName 必填 ≤128；fieldKey 唯一必填、fieldLabel 必填；crossCheck 目标字段必须存在于字段列表（1121）；assignees 必填非空；clientToken 防重 |
| 填报预览弹窗 | Modal 640px | 样例表单动态渲染 + validationResult 错误行内红标定位 |

### 8. 错误处理
- 1121（勾稽规则引用不存在字段）：字段编辑器即时校验 + 提交拦截；
- 1001（参数校验）：表单即时校验；
- 停用有进行中单据：提示改为"仅停用"路径（不物理删除）；
- 401/403 通用处理。

### 9. BR 业务规则覆盖
- RPT-T-R1（字段变更新版本，在途单沿用旧版）：编辑提交提示 + 模板 version 列；
- RPT-T-R2（勾稽校验提交时强制）：字段设计器勾稽配置 + 预览校验 + P2 提交时 1122 强制；
- RPT-T-R3（**模板 + 周期 + 填报人 + 作者 + 账号** 唯一 · 2026-10-01）：P2 提交 1123 拦截；
- V2-A1（周期任务自动生成待办）：[保存并启用] 确认文案 + P2 待办数据源。

---

## P2. 填报页（REPORT-002，动态表单）

### 1. 页面概述
- 路由路径：`/ims/report/submit/{taskId}`（Web 二级页 + 钉钉 H5 同构，从工作台待填报待办进入）
- 页面级别：二级页面（动态表单 + 上期参考 + 附件 + 勾稽校验）
- 依赖模块：P1 模板 fieldsSchema（动态渲染）、FileUpload（ATTACHMENT 字段）、V2-A1 周期待办生成
- 权限矩阵引用（PRD 4.2 REPORT-002）：填报人本人（R2 行政/R3 财务/R5 直播/R6 内容/R10 被指派）W；R1 全量可查

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 填报: {模板名} | 周期 {period} | 截止 {dueTime} [剩余倒计时]        |
| [导入上期数据] (RPT-S-R3)                                         |
+------------------------------------------------------------------+
| 归因上下文(固定·FR-REPORT-011): AuthorSelect* → AccountSelect* 级联   |
| 动态表单区(按 fieldsSchema 渲染):                                  |
|   NUMBER: InputNumber + 范围校验 | TEXT: Input | ENUM: Select      |
|   DATE: DatePicker | ATTACHMENT: FileUpload | AUTHOR/ACCOUNT: 选择器 |
|   必填项红星；勾稽错误行内红标(errorMsg, 1122 定位)                 |
| ---------------------------------------------------------------- |
| 附件区: FileUpload 多文件 (Excel/截图凭证)                          |
+------------------------------------------------------------------+
| 底部固定: [存草稿] [提交填报]                                       |
| 草稿状态条: "草稿已保存 HH:mm" | 历史版本切换(退回重报后 v1/v2)      |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ReportSubmissionReq {
  templateId: number;
  period: string;                   // 2025-06-10 / 2025-W24 / 2025-06
  authorId: number;                 // 必填 author_user.id（JSON 字符串 snowflake）
  accountId: number;                // 必填 oa_account.id
  dataContent: Record<string, string | number | null>;
  attachments?: Array<{ fileName: string; fileKey: string }>;
  asDraft: boolean;                 // true 草稿 / false 正式提交（触发勾稽校验+进队列）
}

// 响应类型
interface ReportSubmissionVO {
  id: number;
  submissionNo: string;             // RS+日期+流水
  templateId: number;
  templateName: string;
  templateVersion: number;
  period: string;
  submitterUserId: number;
  submitterName: string;
  authorId: number;
  authorName: string;
  accountId: number;
  accountLabel: string;             // 平台 + 昵称（AccountSelect 回显）
  dataContent: Record<string, string | number | null>;
  attachments: Array<{ fileName: string; fileKey: string }>;
  submitStatus: SubmissionStatus;   // DRAFT/SUBMITTED/APPROVED/REJECTED
  isOnTime: boolean;                // RPT-S-R2 逾期标记迟交
  submittedAt?: string;
  version: number;                  // 退回重报递增（RPT-S-R1）
  createdAt: string;
}
interface PendingSubmitTask {
  taskId: number;
  templateId: number;
  templateName: string;
  period: string;
  dueTime: string;
  isNearDeadline: boolean;          // 截止前 1 小时高亮
  draftSubmissionNo?: string;       // 有草稿直接续填
}

// 枚举类型（全局权威枚举）
// SubmissionStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'
```

### 4. 交互流程

#### 4.1 页面加载
1. 从工作台待办进入 → `GET /report/submit/pending` 上下文（模板/周期/截止）→ 有 draftSubmissionNo 则加载草稿续填；
2. 归因上下文：AuthorSelect + AccountSelect 预填（草稿/上期带入时一并恢复）；作者变更清空账号并 reload 级联选项；
3. 动态表单按 fieldsSchema 渲染（控件类型映射 + 必填星标 + 范围/枚举约束；AUTHOR/ACCOUNT 类型渲染为选择器）；
4. 顶部倒计时 = dueTime − 当前；isNearDeadline（<1h）黄色高亮；已逾期红色"迟交标记"提示（RPT-S-R2）。

#### 4.2 核心操作流程
**A. 导入上期数据（RPT-S-R3）**
1. [导入上期数据] → `GET /report/submit/last-period?templateId&period` → 上期 dataContent 预填表单（可覆盖修改）；无上期提示"无上期数据"。

**B. 填报与草稿保存**
1. 动态表单填写；ATTACHMENT 字段与附件区走 FileUpload（服务端上传回执 fileKey）；
2. [存草稿]（输入停 30 秒亦自动）→ `POST /report/submit`（asDraft=true）→ 状态条"草稿已保存 HH:mm"。

**C. 正式提交（勾稽校验）**
1. [提交填报] → 前端预校验（authorId/accountId + 必填/范围）→ `POST /report/submit`（asDraft=false）；
2. 服务端勾稽校验失败（1122）→ data.errors 明细逐字段行内红标 + 顶部汇总条"勾稽校验未通过 N 处"；
3. 成功 → 状态 SUBMITTED，进入对应业务线审核队列（R8 初审 → 本线终审）。

**D. 退回重报（RPT-S-R1）**
1. REJECTED 状态进入本页：正文预填被退回版本数据 + 顶部退回原因横幅（rejectReason + 结构化 tags）；
2. 修改后重新提交 → version+1；历史版本切换器（v1/v2/…）可回看对比；
3. 3 轮退回 → 系统升级业务线负责人裁决（P3 审核抽屉显示"已升级裁决"标记，RPT-A-R1）。

### 5. 查询条件表
无（填报执行页）。

### 6. 表格列定义
无（动态表单页）。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 提交确认弹窗 | Modal 360px | 必填/勾稽预校验汇总；逾期黄条"已过截止将标记迟交" |
| 版本历史弹窗 | Modal 640px | 退回重报版本列表（v1/v2…，含审核轮次与退回原因），可对比 |

### 8. 错误处理
- 1122（勾稽校验失败）：行内红标 + 明细定位（可点击滚动到字段）；
- 1123（重复填报）：提示"本周期已提交"，自动切换回显模式；
- 1127（作者与账号 IP 组共池校验失败）：归因区红标 + 顶部条；
- 1500/1501/1504（作者/账号不存在或已停用/跨租户）：归因区拦截；
- 1001（必填/范围）：即时校验；
- H5 弱网：草稿 localStorage 缓存恢复；
- FileUpload 失败（5005）：组件内重试 3 次。

### 9. BR 业务规则覆盖
- **BR-106 数据源头**：提交 → 审核 → APPROVED 计入分子（质量口径，P4 落点）；
- RPT-S-R1（退回重报版本留痕可对比）：版本切换器 + P3 Diff 视图；
- RPT-S-R2（逾期标记迟交计入分母）：倒计时 + 迟交提示；
- RPT-S-R3（上期数据带入可覆盖）：[导入上期数据]（含 authorId/accountId）；
- RPT-S-R4（作者×账号强关联）：固定归因区 + 1127/1500/1501 后端校验（FR-REPORT-011）；
- RPT-T-R2（勾稽提交时强制）：1122 行内定位；
- 截止前 1 小时未提交钉钉推送（PRD 5.9.1）：isNearDeadline 高亮联动。

---

## P3. 填报单管理页（REPORT-002 列表 + REPORT-003 审核）

### 1. 页面概述
- 路由路径：`/ims/report/submission`
- 页面级别：一级菜单页，三 Tab：填报单列表 / 审核队列 / 审核记录
- 依赖模块：P2 填报页、P4 统计、工作流（审核流转）
- 权限矩阵引用（PRD 4.2 REPORT-002/003）：R1 R/W/D 全量；R8 W（初审）；R2/R3/R4 W/D（本线终审）；R9 R（脱敏）；填报人本人 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [填报单列表] [审核队列] [审核记录]                             |
+------------------------------------------------------------------+
| 填报单列表查询行: 模板 | 周期 | 填报人 | 作者 | 账号 | 状态 | [查询][重置]  |
+------------------------------------------------------------------+
| 填报单表格:                                                       |
| 单号|模板|周期|填报人|作者|账号|版本|状态|按时|提交时间|审核轮次|操作    |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
| 审核队列 Tab: 业务线筛选 | 队列表格(等待时长超24h红标)               |
| 审核抽屉(70%): 填报数据全字段表(标签-值) + 附件预览                 |
|   底部: [通过] [退回]                                              |
|   退回: 原因* + 结构化原因标签(勾选) [数据对比(退回前后Diff)]        |
| 审核记录 Tab: 单号|审核人|轮次|结论|退回原因|时间                    |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface SubmissionPageReq {
  pageNo: number; pageSize: number;
  templateId?: number; period?: string;
  submitterUserId?: number;
  authorId?: number;
  accountId?: number;
  submitStatus?: SubmissionStatus;
}
interface AuditQueueReq {
  pageNo: number; pageSize: number;
  businessLine?: BusinessLine;
}
interface ReportAuditReq {
  conclusion: 'APPROVED' | 'REJECTED';    // 通过 / 退回
  rejectReason?: string;             // 退回必填 ≤512 字
  rejectReasonTags?: string[];       // 结构化原因勾选
}
interface AuditRecordPageReq {
  pageNo: number; pageSize: number;
  submissionId?: number; auditorUserId?: number;
  conclusion?: 'APPROVED' | 'REJECTED';
}
interface AuditDiffReq {
  submissionId: number;
  fromVersion: number; toVersion: number;
}

// 响应类型
interface AuditQueueItem extends ReportSubmissionVO {
  waitingHours: number;
  isTimeoutSla: boolean;             // 审核时效 24h 超时（RPT-A-R3）
}
interface AuditResultResp {
  submissionId: number;
  auditRound: number;
  newStatus: SubmissionStatus;
  nextAction: 'COMPLETED' | 'BACK_TO_SUBMITTER';
}
interface AuditRecordVO {
  id: number; submissionId: number; submissionNo: string;
  auditorUserId: number; auditorName: string;
  auditRound: number;
  conclusion: 'APPROVED' | 'REJECTED';
  rejectReason?: string;
  rejectReasonTags?: string[];
  auditedAt: string;
}
interface AuditDiffResp {
  fieldsDiff: Array<{
    fieldKey: string; fieldLabel: string;
    oldValue: string | number | null;
    newValue: string | number | null;
    changed: boolean;                // 变更行高亮
  }>;
}
interface SubmissionDetailVO extends ReportSubmissionVO {
  auditRounds: Array<{
    round: number;
    conclusion: 'APPROVED' | 'REJECTED';
    rejectReason?: string;
    auditorName: string;
    auditedAt: string;
  }>;
}

// 枚举类型（全局权威枚举）
// SubmissionStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载；审核队列 Tab 徽标 = 本线待审数；R9 视角金额类字段服务端脱敏 `"***"`。失败分区重试。

#### 4.2 核心操作流程
**A. 填报单列表查看**
1. QueryBar 筛选；行点击 → 详情抽屉（70%）：数据全字段表 + 附件预览 + 审核轮次时间线（auditRounds）+ 版本历史；
2. 状态 tag 四态；审核轮次列 ≥2 时显示"已退回 N 次"黄色角标。

**B. 审核（REPORT-003 核心）**
1. 审核队列 Tab（按模板业务线路由：R8 初审 / R2 行政 / R3 财务 / R4 业务终审）；waitingHours 超 24h 红标（RPT-A-R3）；
2. 行 [审核] → 审核抽屉（70%）：填报数据全字段表（数值型字段高亮勾稽关系）+ 附件在线预览（Excel/截图）；
   - [通过]：`PUT /report/audit/{submissionId}`（conclusion=APPROVED）→ nextAction=COMPLETED → 状态 APPROVED，计入 BR-106 分子（RPT-A-R2）；
   - [退回]：原因必填（1124 拦截）+ 结构化原因标签多选（数据来源不明/勾稽不平/附件缺失等）→ 状态 REJECTED → 填报人收到修改重报待办；
3. [数据对比]：REJECTED 重报后再审时 → `GET /report/audit/diff`（fromVersion/toVersion 选择）→ Diff 弹窗变更行高亮（RPT-S-R1）；
4. 3 轮退回：第 3 次退回提交被拦截（1125）→ 系统升级业务线负责人裁决，抽屉显示"已升级裁决"状态与裁决人。

**C. 审核记录查询**
- 审核记录 Tab：全量留痕（单号/审核人/轮次/结论/退回原因与标签/时间）；支持筛选。

### 5. 查询条件表

**填报单列表 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| templateId | Select（模板下拉） | 否 | 空 | 按权限范围模板 |
| period | Input | 否 | 空 | 周期标识（2025-06-10/2025-W24/2025-06） |
| submitterUserId | UserSelect | 否 | 空 | 填报人 |
| authorId | AuthorSelect | 否 | 空 | 作者（FR-REPORT-014） |
| accountId | AccountSelect | 否 | 空 | 平台账号 |
| submitStatus | Select | 否 | 空 | 四态 |

**审核队列 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| businessLine | Select | 否 | 本线默认 | 财务/业务/行政（R1 全选） |

**审核记录 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| submissionId | Input | 否 | 空 | 填报单 ID |
| auditorUserId | UserSelect | 否 | 空 | 审核人 |
| conclusion | Select | 否 | 空 | 通过/退回 |

### 6. 表格列定义

**填报单列表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| submissionNo | 填报单号 | 140 | — | 等宽字体（RS…） |
| templateName | 模板 | 150 | — | — |
| period | 周期 | 110 | — | 按周期类型渲染（日期/周/月） |
| submitterName | 填报人 | 100 | — | — |
| authorName | 作者 | 100 | — | AuthorSelect 回显 |
| accountLabel | 账号 | 130 | — | 平台 · 昵称 |
| version | 版本 | 70 | ✓ | V{n}；≥2 黄色角标"退回 N 次" |
| submitStatus | 状态 | 100 | — | tag：草稿(灰)/已提交(蓝)/已通过(绿)/已退回(红) |
| isOnTime | 按时 | 90 | — | tag：按期(绿)/迟交(黄) |
| submittedAt | 提交时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| auditRoundCount | 审核轮次 | 90 | — | "N 轮" |
| actions | 操作 | 150 | — | [详情][审核（队列权限）] |

**审核队列**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| submissionNo | 填报单号 | 140 | — | 等宽字体 |
| templateName | 模板 | 150 | — | 业务线 tag 附带 |
| period | 周期 | 110 | — | — |
| submitterName | 填报人 | 100 | — | — |
| waitingHours | 等待时长 | 110 | ✓ | "X 小时"；超 24h 红（RPT-A-R3） |
| actions | 操作 | 100 | — | [审核] |

**审核记录**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| submissionNo | 填报单号 | 140 | — | 可点击 |
| auditorName | 审核人 | 100 | — | — |
| auditRound | 轮次 | 70 | — | 第 N 轮 |
| conclusion | 结论 | 90 | — | tag：通过(绿)/退回(红) |
| rejectReason | 退回原因 | 自适应 | — | + 结构化 tags |
| auditedAt | 审核时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 填报单详情抽屉 | Drawer 70% | 数据全字段表（label-value）+ 附件预览 + 审核轮次时间线 + 版本史 |
| 审核抽屉 | Drawer 70% | 数据表 + 附件预览 + 底部结论区：通过一键；退回 rejectReason 必填 ≤512（1124）+ rejectReasonTags 多选；Diff 入口 |
| 数据对比弹窗 | Modal 720px | fromVersion/toVersion 选择 → fieldsDiff 表格变更行高亮（旧值删除线/新值绿） |

### 8. 错误处理
- 1124（退回必须填原因）：结论区必填校验；
- 1125（3 轮退回升级拦截）：提示"已退回 3 轮，本单已升级业务线负责人裁决"；
- 1126（非本线审核人）：提示无权限并刷新队列；
- 附件预览失败（下载 403）：静默刷新签名 URL 重试 1 次；
- R9 脱敏：金额类字段 `"***"`（服务端完成，前端仅渲染）。

### 9. BR 业务规则覆盖
- RPT-A-R1（退回必填原因；3 轮退回升级）：退回校验 + 1125 升级流；
- RPT-A-R2（审核通过进统计口径）：APPROVED 状态即 BR-106 分子（P4 呈现）；
- RPT-A-R3（审核时效 24h）：队列红标 + P4 slowAudits；
- RPT-S-R1（版本留痕可对比）：Diff 弹窗 + 详情版本史。

---

## P4. 上报统计看板（REPORT-004）

### 1. 页面概述
- 路由路径：`/ims/report/stat`
- 页面级别：一级菜单页，三 Tab 看板（完成率与趋势 / 未交督办 / 数据质量）
- 依赖模块：`ims_report_stat` 周期汇总（V2-A1 集群化）、ALERT（低完成率督办联动）
- 权限矩阵引用（PRD 4.2 REPORT-004）：R1/R2/R3/R4（本线）、R9 R（全量）、填报人（本人）；无写操作

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 统计周期 | 模板 | 部门 | [查询]                             |
+------------------------------------------------------------------+
| Tab: [完成率与趋势] [未交督办] [数据质量]                           |
+------------------------------------------------------------------+
| 完成率与趋势: 指标卡: 总完成率 xx% (BR-106 目标>95%,质量口径)       |
|   周期趋势折线(完成率+退回率双线) | 按模板表 | 按部门表              |
+------------------------------------------------------------------+
| 未交督办: 模板/部门筛选 + 清单表格(未交/迟交/待审核) + [导出 Excel]  |
+------------------------------------------------------------------+
| 数据质量: 总退回率指标卡 | 按模板退回率表(>20%黄标提示RPT-C-R3)      |
|   退回原因 Top 标签 | 审核时效慢清单                                |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface CompleteRateReq {
  statPeriod?: string;              // 统计周期
  templateId?: number; deptId?: number;
}
interface TrendReq {
  dateRange?: [string, string];
  templateId?: number;
}
interface MissedListReq {
  pageNo: number; pageSize: number;
  statPeriod?: string; templateId?: number; deptId?: number;
}
interface QualityReq {
  statPeriod?: string;
}

// 响应类型
interface ReportCompleteRateResp {
  totalCompleteRate: number;        // BR-106 分子=APPROVED（质量口径 RPT-C-R1）
  byTemplate: Array<{
    templateId: number; templateName: string;
    shouldCount: number; submittedCount: number;
    onTimeCount: number; approvedCount: number;
    completeRate: number;
  }>;
  byDept: Array<{
    deptId: number; deptName: string;
    shouldCount: number; approvedCount: number;
    completeRate: number;
  }>;
}
interface TrendItem {
  statPeriod: string;
  shouldCount: number; submittedCount: number; approvedCount: number;
  completeRate: number; rejectRate: number;   // 低于 90% 督办（RPT-C-R2）
}
interface ReportMissedItem {
  userId: number; userName: string; deptName: string;
  templateName: string; period: string; dueTime: string;
  status: 'MISSED' | 'LATE' | 'PENDING_AUDIT';
}
interface QualityResp {
  totalRejectRate: number;
  byTemplate: Array<{
    templateId: number; templateName: string;
    rejectRate: number; avgAuditRounds: number;
    topRejectReasons: Array<{ tag: string; count: number }>;
  }>;
  slowAudits: Array<{ auditorName: string; avgHours: number; timeoutCount: number }>;
}
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载；完成率默认本周期；数据范围按本线/本人服务端过滤；R9 全量脱敏。失败分区重试。

#### 4.2 核心操作流程
**A. 完成率与趋势（BR-106）**
1. 指标卡总完成率（目标 >95%，质量口径注释"分子 = 审核通过单数"）；
2. 趋势折线双线（完成率 + 退回率），completeRate <90% 数据点黄标（RPT-C-R2 自动督办，页面标"已督办"）；
3. 按模板表 / 按部门表（完成率降序，未达标行黄标）。

**B. 未交督办（导出）**
1. 清单表格：MISSED（未交红）/LATE（迟交黄）/PENDING_AUDIT（待审核蓝）三态 tag；
2. [导出 Excel] → 异步导出（下载链接，提示"导出任务已提交"）。

**C. 数据质量（RPT-C-R3）**
1. 指标卡总退回率；按模板退回率表：rejectRate >20% 行黄标 + 行内提示"建议检查字段设计合理性"；
2. 退回原因 Top 标签云（结构化 tags 统计）；审核时效慢清单（avgHours 降序、timeoutCount 红标）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| statPeriod / dateRange | PeriodPicker / DateRangePicker | 否 | 本周期 | 按周期类型联动 |
| templateId | Select | 否 | 空 | 模板（本线范围） |
| deptId | DeptTreeSelect | 否 | 空 | 部门 |

### 6. 表格列定义

**按模板表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| templateName | 模板 | 180 | — | 业务线 tag 附带 |
| shouldCount | 应提交 | 90 | — | — |
| submittedCount | 已提交 | 90 | — | 含迟交 |
| onTimeCount | 按时 | 80 | — | — |
| approvedCount | 审核通过 | 100 | — | BR-106 分子 |
| completeRate | 完成率 | 120 | ✓ 降序 | 进度条；<90% 黄标 |

**未交督办表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| userName | 填报人 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| templateName | 模板 | 160 | — | — |
| period | 周期 | 110 | — | 按周期类型渲染 |
| dueTime | 截止时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| status | 状态 | 100 | — | tag：未交(红)/迟交(黄)/待审核(蓝) |
| actions | 操作 | 100 | — | [去督办]（跳 P2/P3 或工作台推送） |

**数据质量-按模板表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| templateName | 模板 | 180 | — | — |
| rejectRate | 退回率 | 110 | ✓ 降序 | >20% 黄标 + 提示 icon |
| avgAuditRounds | 平均轮次 | 100 | — | "N 轮" |
| topRejectReasons | 主要退回原因 | 自适应 | — | 标签 + 计数 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 模板明细抽屉 | Drawer 60% | 模板行点击：该模板周期明细 + 趋势小图 |
| 导出进度提示 | ElMessage | 异步导出提交 + 下载链接完成通知 |

### 8. 错误处理
- 周期参数非法：PeriodPicker 联动拦截；
- 汇总任务延迟（5006）：看板黄条"数据截至 X 周期"；
- 空数据：空态占位图；
- R9 脱敏字段：`"***"` 渲染。

### 9. BR 业务规则覆盖
- **BR-106（每日上报完成率 > 95%，质量口径）**：完成率指标卡（分子=APPROVED）+ 三维分布 + 趋势；
- RPT-C-R1（质量口径非仅提交）：指标卡口径注释 + approvedCount 列独立展示；
- RPT-C-R2（低于 90% 自动督办）：趋势点黄标 + "已督办"标记（ALERT 联动）；
- RPT-C-R3（退回率 >20% 提示字段设计检查）：数据质量 Tab 黄标提示；
- RPT-S-R2（迟交计入分母）：未交督办 LATE 状态与分母口径。

---

## 附录 A. 模块级约定

1. **枚举引用**：全局权威枚举 `SubmissionStatus`（四态）、`PeriodType`、`EnableStatus`；模块内联枚举 `BusinessLine`/`FieldType`/`AssignType`/`CrossCheckOperator` 值域与 REPORT-API 契约一致；
2. **错误码段**：1121~1130 REPORT 段（1121 勾稽引用字段不存在、1122 勾稽校验失败、1123 重复填报、1124 退回缺原因、1125 三轮退回升级）；
3. **权限过滤**：业务线路由（FINANCE→R3 / BUSINESS→R4 / ADMIN→R2）、R9 脱敏、填报人本人 —— 全部服务端执行；
4. **H5 同构**：P2 填报页移动端优先（钉钉 H5 免登），其余管理后台 Web 页；
5. **周次格式**：period=2025-W24 渲染为"2025 第 24 周"相关表述，区间一律波浪号。

## 附录 B. BR/RPT 规则 ↔ 页面落点总表

| 规则 | 约束摘要 | 页面落点 |
|------|----------|----------|
| BR-106 | 完成率 > 95%（质量口径） | P4 指标卡 / P3 APPROVED 状态 |
| RPT-T-R1 | 字段变更新版本，在途沿用 | P1 编辑提示 / P2 templateVersion |
| RPT-T-R2 | 勾稽校验强制 | P1 勾稽配置 / P2 1122 行内定位 |
| RPT-T-R3 | 一模板一周期一份 | P2 1123 拦截 |
| RPT-S-R1 | 退回重报版本留痕 | P2 版本切换 / P3 Diff 弹窗 |
| RPT-S-R2 | 逾期标记迟交分母 | P2 倒计时 / P4 LATE |
| RPT-S-R3 | 上期数据带入 | P2 [导入上期数据] |
| RPT-S-R4 | 作者×账号强关联 | P2 归因区 / P3 列 / 1127 |
| RPT-A-R1 | 退回必填原因；3 轮升级 | P3 退回校验 + 1125 |
| RPT-A-R2 | 通过进统计口径 | P3→P4 分子链路 |
| RPT-A-R3 | 审核时效 24h | P3 队列红标 / P4 slowAudits |
| RPT-C-R1~R3 | 质量口径/低率督办/高退回提示 | P4 三 Tab |

（全文完）
