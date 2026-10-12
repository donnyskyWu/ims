# MEET - 会议/日报管理 页面规格

> 依据：《IMS第二期PRD-V2.md》5.4~5.7（MEET-001~004）、《共享技术规范-分期技术约束.md》V2-A1（每日 17:00 待办生成、汇总任务集群化）、《MEET-会议日报管理-API契约.md》、《全局开发规范.md》第 4 章（权威枚举）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/meet`。
> 归属期次：V2 第 15~18 周（V2.1 管理动作线上化批次）。
> **枚举口径说明**：全局权威枚举 `ReportStatus = 'DRAFT' | 'SUBMITTED' | 'READ'`。本页面规格**前端渲染与类型引用统一以 `ReportStatus`（含 `READ`）为准**；契约历史表述 `REVIEWED` 已统一为 `READ`（与全局权威枚举一致）。

## 0. 模块总览

### 0.1 IMS 导航（完整 PRD v2.6.5 · 走查 #10）

| 侧栏 L1 组 | L2 | L3 子菜单 | 路由 | 说明 |
|------------|-----|-----------|------|------|
| **协同与成长** | **会议** | — | `/ims/meet/minutes` | MEET-004 纪要（与日报分路由） |
| **协同与成长** | **日报中心**（可展开） | 我的日报 · 团队日报 · 待我审阅 · 提交率统计 | `/ims/meet/daily`（列表/审阅按叶分视图）、`/ims/meet/stat` | MEET-001～003；**≠** 09 数据上报 |
| — | — | P1 提交（二级） | `/ims/meet/daily/submit` | 工作台「填写日报」待办进入 |

**API**：`/admin-api/ims/meet/daily/*`、`/meet/review/*`、`/meet/stat/*`（见《MEET-会议日报管理-API契约.md》）。**深链**：历史 `go('report')` 误挂 09 的单页 → 重定向 **我的日报**。

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 日报提交页 | `/ims/meet/daily/submit` | 二级页面（移动端优先，钉钉 H5 同构） | MEET-001 |
| P2 日报管理页 | `/ims/meet/daily` | 一级菜单页（列表 + 审阅队列 + 记录） | MEET-001/002 |
| P3 日报统计看板 | `/ims/meet/stat` | 一级菜单页（Tab 看板） | MEET-003 |
| P4 会议纪要管理 | `/ims/meet/minutes` | 一级菜单页（列表 + 登记抽屉 + 详情抽屉） | MEET-004 |

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；交互操作优先内联抽屉（Drawer），不跳转新页面；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红 / 中性灰）；
- 周次/月份展示用波浪号格式；手机号等敏感字段脱敏（本模块不涉及金额）；
- 枚举一律引用《全局开发规范.md》第 4 章：`ReportStatus`、`ReviewAction`。

---

## P1. 日报提交页（MEET-001，移动端优先）

### 1. 页面概述
- 路由路径：`/ims/meet/daily/submit`（Web 表单页 + 钉钉 H5 同构，从工作台日报待办进入）
- 页面级别：二级页面（三段式表单 + 周五周小结段 + 草稿自动保存）
- 依赖模块：V1 AUTH-004 工作台（每日 17:00 日报待办，V2-A1 集群化调度）、钉钉考勤（MEE-S-R1 应提交工作日）、钉钉推送（截止前 1 小时提醒）
- 权限矩阵引用（PRD 4.2 MEET-001）：日报人本人（R5/R6 全员视角、R10 被要求时）W（本人）；查看 R1（全量可查，走 P2）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 日报 2025-06-12（周四）| 截止 22:00 | [剩余 4h12m 倒计时]           |
+------------------------------------------------------------------+
| [今日完成]*    textarea 自适应(≥1字符)                            |
| [明日计划]*    textarea 自适应                                    |
| [问题与风险]*  textarea 自适应                                    |
| （周五时自动出现 [周小结]* 段，MEE-D-R4）                          |
| （自定义字段区：模板 extraFields 动态渲染 TEXT/NUMBER/SELECT）      |
| ---------------------------------------------------------------- |
| 补充说明区（已提交后展示，只读正文 + supplement 追加编辑，MEE-D-R2）|
+------------------------------------------------------------------+
| 底部固定: [存草稿] [提交日报]                                      |
| 草稿状态条: "草稿已自动保存 18:42"                                 |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface DailyReportSubmitReq {
  reportDate: string;               // yyyy-MM-dd（日报所属日期）
  contentDone: string;              // 今日完成 必填
  contentPlan: string;              // 明日计划 必填
  contentIssue: string;             // 问题与风险 必填
  weekSummary?: string;             // 周五周小结段（模板带出时必填）
  extraFields?: Record<string, string>;
  asDraft: boolean;                 // true=草稿自动保存 / false=正式提交
}
interface DailyReportEditReq extends DailyReportSubmitReq {
  id: number;
  supplement?: string;              // 已提交态仅允许追加补充说明
}

// 响应类型
interface DailyReportVO {
  id: number;
  reportDate: string;
  userId: number;
  userName: string;
  deptName: string;
  contentDone: string;
  contentPlan: string;
  contentIssue: string;
  weekSummary?: string;
  extraFields?: Record<string, string>;
  submitStatus: ReportStatus;       // DRAFT / SUBMITTED / READ（契约已统一为 READ）
  supplement?: string;              // 补充说明段（已提交后修改走此段）
  submittedAt?: string;
  isOnTime: boolean;                // BR-103 按时标记（默认截止当日 22:00）
  createdAt: string;
}
interface DailyTemplateResp {
  sections: Array<{ key: 'done' | 'plan' | 'issue' | 'weekly'; label: string; required: boolean }>;
  extraFields: Array<{ key: string; label: string; type: 'TEXT' | 'NUMBER' | 'SELECT'; options?: string[] }>;
  weekSummaryEnabled: boolean;      // 周五自动带出周小结段
  deadlineTime: string;             // HH:mm（部门级覆盖，默认 22:00）
}

// 枚举类型（全局权威枚举）
// ReportStatus = 'DRAFT' | 'SUBMITTED' | 'READ'
```

### 4. 交互流程

#### 4.1 页面加载
1. 从工作台待办/H5 进入 → 并行 `GET /meet/daily/template`（模板）+ `GET /meet/daily/{today}`（当日回显，null 则空白表单）；
2. 有草稿 → 恢复草稿内容并标注"上次保存于 X 时间"；
3. 已提交 → 正文只读 + 展示提交时间/按时标记 + 补充说明区可编辑（MEE-D-R2）；
4. 周五 → 模板 weekSummaryEnabled 自动带出"周小结"必填段（MEE-D-R4）；
5. 顶部倒计时 = deadlineTime − 当前时间；已逾期显示红色"已过截止（迟交标记）"。

#### 4.2 核心操作流程
**A. 填写与草稿自动保存**
1. 三段必填（done/plan/issue）+ 周五周小结段；自定义字段按模板 extraFields 动态渲染并校验；
2. 输入停 30 秒自动 `POST /meet/daily`（asDraft=true）→ 状态条"草稿已自动保存 HH:mm"；
3. [提交日报] → ConfirmDialog（汇总：日期/必填段完整性/截止倒计时）→ `POST /meet/daily`（asDraft=false）→ 状态 SUBMITTED，进入直属上级一级审阅队列（MEET-002 联动）。

**B. 逾期补交（MEE-D-R2）**
- 截止后提交 → isOnTime=false，提交成功提示"已提交（迟交标记）：计入提交率，不计入按时率"；仍可正常提交。

**C. 已提交追加补充说明**
- 已提交日报底部 [补充说明] 输入 → `PUT /meet/daily/{id}`（仅 supplement 字段可改，1112 拦截正文修改）。

**D. 提醒联动（无页面操作）**
- 每日 17:00 待办生成（V2-A1）；截止前 1 小时未提交钉钉推送提醒。

### 5. 查询条件表
无（提交表单页；date 由待办携带）。

### 6. 表格列定义
无（表单页）。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 提交确认弹窗 | Modal 360px | 必填完整性校验；逾期时黄条提示"已过截止将标记迟交" |
| 历史日报抽屉 | Drawer 60% | 提交页右上角历史图标 → 本人近 7 天日报列表（状态 tag + 按时/迟交标记），点击回显只读 |

### 8. 错误处理
- 1111（一人一日一份，userId+reportDate 唯一索引）：提示"今日日报已存在"，自动切换为回显模式；
- 1112（已提交不可编辑正文）：正文区置灰 + tooltip"已提交，修改请使用补充说明"；
- 1001（参数校验）：textarea 必填即时校验；
- H5 弱网：草稿本地缓存（localStorage），网络恢复后自动补存；
- 401 静默跳 SSO（H5 免登重试一次）。

### 9. BR 业务规则覆盖
- **BR-103（按时提交率 > 95%）**：倒计时 + isOnTime 按时/迟交标记为本规则数据源头；
- MEE-D-R1（截止默认 22:00 部门可配）：deadlineTime 模板下发驱动倒计时；
- MEE-D-R2（逾期补交标记迟交分口径）：提交成功提示 + P3 统计分口径；
- MEE-D-R3（一人一日一份）：1111 拦截 + 自动回显；
- MEE-D-R4（周五周小结）：模板 weekSummaryEnabled 联动渲染必填段。

---

## P2. 日报管理页（MEET-001 列表 + MEET-002 审阅）

### 1. 页面概述
- 路由路径：`/ims/meet/daily`
- 页面级别：一级菜单页，三 Tab：日报列表 / 我的审阅队列 / 审阅记录
- 依赖模块：P1 提交页、AUTH 组织（人员/部门选择器）、工作台待办（审阅待办、跟进项待办）
- 权限矩阵引用（PRD 4.2 MEET-001/002）：R1 R（全量）/D、R2 R（本部门）、R4 R + 审阅 W/D（本部门终审）；审阅队列按"直属下级（一级）/部门负责人（二级）"判定

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [日报列表] [我的审阅队列] [审阅记录]                           |
+------------------------------------------------------------------+
| 日报列表查询行: 人员 | 部门 | 日期范围 | 状态 | [查询][重置]        |
+------------------------------------------------------------------+
| 日报表格: 日期|姓名|部门|完成摘要|状态|按时|提交时间|审阅|操作        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
| 我的审阅队列: 级别筛选(一级/二级) | 日期范围                        |
| 队列表格: 日期|姓名|部门|完成摘要|等待时长(超24h红标)|[审阅]         |
| 审阅抽屉(70%): 日报全文(三段+自定义+周小结+补充说明)                |
|   底部操作: [已读] [点评] [标记跟进]                               |
|   标记跟进: 跟进项列表(描述*|责任人*|期限*) 动态增删               |
| 审阅记录 Tab: 日报ID|审阅人|级别|动作|批注|跟进项|时间              |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface DailyReportPageReq {
  pageNo: number; pageSize: number;
  userId?: number; deptId?: number;
  reportDateRange?: [string, string];
  submitStatus?: ReportStatus;
}
interface ReviewQueueReq {
  pageNo: number; pageSize: number;
  reviewLevel?: 1 | 2;
  reportDateRange?: [string, string];
}
interface DailyReviewReq {
  reviewLevel: 1 | 2;               // 1 直属上级 / 2 部门负责人
  action: ReviewAction;             // READ / COMMENT / MARK_FOLLOW_UP
  comment?: string;                 // COMMENT/MARK_FOLLOW_UP 建议填写 ≤512 字
  followUpItems?: Array<{           // MARK_FOLLOW_UP 必填
    description: string;
    responsibleUserId: number;
    dueDate: string;
  }>;
}
interface ReviewRecordPageReq {
  pageNo: number; pageSize: number;
  reportId?: number; reviewerUserId?: number;
  reviewLevel?: 1 | 2;
  action?: ReviewAction;
}
interface FollowUpCloseReq {
  closeRemark?: string;
  evidenceUrl?: string;
}

// 响应类型
interface ReviewQueueItem extends DailyReportVO {
  reviewLevel: 1 | 2;
  waitingHours: number;             // 一级超 24 小时红标（MEE-R-R1）
  isTimeout: boolean;
}
interface DailyReviewResp {
  reviewId: number; reportId: number;
  reviewedAt: string;
  nextLevel: 1 | 2 | null;           // 一级完成 → nextLevel=2 进二级队列
}
interface DailyReviewVO {
  id: number;
  reportId: number;
  reportDate: string;
  reviewerUserId: number; reviewerName: string;
  reviewLevel: 1 | 2;
  action: ReviewAction;
  comment?: string;
  followUpItems: Array<{
    itemId: number; description: string;
    responsibleUserId: number; responsibleName: string;
    dueDate: string; status: FollowUpStatus;
  }>;
  reviewedAt: string;
}

// 枚举类型（全局权威枚举）
// ReportStatus = 'DRAFT' | 'SUBMITTED' | 'READ'（READ 即"已审阅"，契约已统一为 READ）
// ReviewAction = 'READ' | 'COMMENT' | 'MARK_FOLLOW_UP'
type FollowUpStatus = 'OPEN' | 'CLOSED';   // 契约值域（OVERDUE 由计算标记）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载：日报列表 `GET /meet/daily/list`（数据权限：R1 全量/R2 本部门/R4 下属+本部门/R5R6 本人，服务端过滤）；审阅队列 Tab 徽标显示待审数。失败分区重试。

#### 4.2 核心操作流程
**A. 日报列表查看**
1. QueryBar 筛选（人员/部门/日期范围/状态）；行点击 → 日报详情抽屉（60%，只读全文 + 审阅时间线）；
2. "按时"列 tag：按时绿 / 迟交黄 / 未交红（未交行为 stat/missed 督办数据源预览）；
3. 删除（R1）：逻辑删除 ConfirmDialog danger。

**B. 审阅（MEET-002 核心，各级审阅人）**
1. 我的审阅队列 Tab：一级（直属下级日报）/二级（部门负责人）筛选；waitingHours 超 24h 红标（MEE-R-R1）；
2. 行 [审阅] → 审阅抽屉（70%）：日报全文（三段+自定义+周小结+补充说明）+ 审阅操作区：
   - [已读]：`PUT /meet/review/{reportId}`（action=READ）→ 一级完成后 nextLevel=2 流入二级队列（MEE-R-R2 逐级）；
   - [点评]：comment 必填建议 → action=COMMENT；
   - [标记跟进]：跟进项编辑器（动态增删行：描述/责任人人员选择/期限）→ action=MARK_FOLLOW_UP → 跟进项生成工作台待办（MEE-R-R3，复用 AUTH-004 联动 FLOW）；
3. 提交后队列刷新、徽标递减。

**C. 跟进项闭环（责任人）**
1. 从工作台跟进项待办进入 → 跟进项详情（来源日报/描述/期限）→ 回填 closeRemark/evidenceUrl → `PUT /meet/review/follow-up/{itemId}` → status=CLOSED；
2. 逾期跟进项红色标记 + 剩余天数提示。

**D. 审阅记录查询（留痕）**
- 审阅记录 Tab：谁/何时/级别/动作/批注/跟进项全景；支持按日报/审阅人/动作筛选。

### 5. 查询条件表

**日报列表 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| userId | UserSelect | 否 | 空 | 人员（按权限范围） |
| deptId | DeptTreeSelect | 否 | 空 | 部门 |
| reportDateRange | DateRangePicker | 否 | 近 7 天 | 日报所属日期 |
| submitStatus | Select | 否 | 空 | 草稿/已提交/已审阅 |

**审阅队列 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| reviewLevel | RadioGroup | 否 | 1 | 一级/二级 |
| reportDateRange | DateRangePicker | 否 | 近 3 天 | 提交日期 |

**审阅记录 Tab**

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| reportId | Input | 否 | 空 | 日报 ID |
| reviewerUserId | UserSelect | 否 | 空 | 审阅人 |
| reviewLevel | Select | 否 | 空 | 一级/二级 |
| action | Select | 否 | 空 | 已读/点评/标记跟进 |

### 6. 表格列定义

**日报列表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| reportDate | 日期 | 110 | ✓ 降序 | yyyy-MM-dd |
| userName | 姓名 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| contentDoneSummary | 完成摘要 | 自适应 | — | 前 50 字省略 |
| submitStatus | 状态 | 100 | — | tag：草稿(灰)/已提交(蓝)/已审阅(绿) |
| isOnTime | 按时 | 90 | — | tag：按时(绿)/迟交(黄)/未交(红) |
| submittedAt | 提交时间 | 150 | — | yyyy-MM-dd HH:mm |
| actions | 操作 | 150 | — | [详情][审阅(审阅人)] 按角色 |

**审阅队列**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| reportDate | 日期 | 110 | ✓ 降序 | yyyy-MM-dd |
| userName | 姓名 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| contentDoneSummary | 完成摘要 | 自适应 | — | 前 50 字省略 |
| reviewLevel | 级别 | 80 | — | 一级/二级 tag |
| waitingHours | 等待时长 | 110 | ✓ | "X 小时"；超 24h 红色（MEE-R-R1） |
| actions | 操作 | 100 | — | [审阅] |

**审阅记录**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| reportId | 日报 ID | 100 | — | 可点击打开日报详情抽屉 |
| reportDate | 日期 | 110 | — | — |
| reviewerName | 审阅人 | 100 | — | — |
| reviewLevel | 级别 | 80 | — | 一级/二级 |
| action | 动作 | 110 | — | 已读/点评/标记跟进 |
| comment | 批注 | 自适应 | — | 省略展示 |
| followUpCount | 跟进项 | 90 | — | "N 项（M 已闭环）" |
| reviewedAt | 审阅时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 日报详情抽屉 | Drawer 60% | 只读全文（三段+周五周小结+自定义字段+补充说明）+ 底部审阅时间线（一级/二级时间与动作） |
| 审阅抽屉 | Drawer 70% | 日报全文只读 + 操作区：READ 一键；COMMENT 时 comment ≤512 字；MARK_FOLLOW_UP 时 followUpItems 必填非空（每行 description 必填 ≤256、responsibleUserId 必选、dueDate 必填不早于当日） |
| 跟进项回填抽屉 | Drawer 480px | closeRemark ≤512 字；evidenceUrl URL 格式校验；提交后闭环 |
| 删除确认弹窗 | Modal 400px | R1 逻辑删除 danger 确认 |

### 8. 错误处理
- 1113（越级审阅）：二级队列仅一级完成后进入；非法提交提示"该日报尚未完成一级审阅"；
- 1114（非该日报审阅人）：提示无权限并刷新队列；
- 1115（非跟进项责任人）：提示"仅跟进项责任人可回填"；
- 队列数据权限：服务端过滤（1008）；
- 网络超时：审阅提交防重（按钮 loading + 30s 超时提示重试）。

### 9. BR 业务规则覆盖
- **BR-103/BR-104 数据源头**：列表 isOnTime 列与 P3 统计共口径；
- MEE-R-R1（一级 24h 内完成）：队列 waitingHours 超 24h 红标 + P3 审阅及时性统计；
- MEE-R-R2（逐级，一级完成才进二级）：nextLevel 联动 + 1113 拦截；
- MEE-R-R3（跟进项生成待办闭环）：标记跟进 → 工作台待办 → 回填闭环全链路；
- 审阅留痕：审阅记录 Tab 全字段留痕展示。

---

## P3. 日报统计看板（MEET-003）

### 1. 页面概述
- 路由路径：`/ims/meet/stat`
- 页面级别：一级菜单页，四 Tab 看板（按时率总览 / 月度提交率 / 未交督办 / 审阅及时性）
- 依赖模块：`ims_daily_stat` 每日汇总（V2-A1 集群化）、钉钉考勤（MEE-S-R1 应提交工作日）、ALERT 推送（MEE-S-R3 督办联动）
- 权限矩阵引用（PRD 4.2 MEET-003）：R1 R（全量）、R2 R（全量）、R9 R（全量）、R4 R（本部门）、R5/R6 R（本人）；无写操作

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 日期范围/统计月 | 部门 | [查询]                             |
+------------------------------------------------------------------+
| Tab: [按时率总览] [月度提交率] [未交督办] [审阅及时性]              |
+------------------------------------------------------------------+
| 按时率总览: 指标卡: 总按时率 xx% (BR-103 目标>95%)                 |
|   趋势折线(按日) | 按部门表(按时率/提交率) | 按人表(分页)           |
+------------------------------------------------------------------+
| 月度提交率: 人月统计表(月份|姓名|部门|应交天数|按时天数|提交天数|    |
|   按时率|提交率)  + 部门汇总条形图                                  |
+------------------------------------------------------------------+
| 未交督办: 类型筛选(未交/迟交) + 清单表格 + [导出 Excel]             |
+------------------------------------------------------------------+
| 审阅及时性: 一级24h完成率 | 二级平均时长 | 超时审阅清单 | 低率部门   |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface OnTimeRateReq {
  dateRange?: [string, string];
  deptId?: number;
}
interface MonthlyStatReq {
  statMonth: string;                // yyyy-MM 必填
  pageNo: number; pageSize: number;
  deptId?: number;
}
interface MissedPageReq {
  pageNo: number; pageSize: number;
  dateRange?: [string, string];
  deptId?: number;
  type?: MissedType;
}
interface ReviewTimelinessReq {
  dateRange?: [string, string];
  deptId?: number;
}

// 响应类型
interface DailyOnTimeRateResp {
  totalOnTimeRate: number;          // BR-103 日口径
  byDept: Array<{ deptId: number; deptName: string; onTimeRate: number; submitRate: number }>;
  byPerson: Array<{
    userId: number; userName: string; deptName: string;
    onTimeDays: number; submittedDays: number; shouldDays: number;
  }>;
  trend: Array<{ date: string; onTimeRate: number }>;
}
interface MonthlyStatItem {
  statMonth: string; userId: number; userName: string; deptName: string;
  shouldDays: number;               // 应提交工作日（排除请假/节假日）
  onTimeDays: number; submittedDays: number;
  onTimeRate: number; submitRate: number;
}
interface MissedItem {
  userId: number; userName: string; deptName: string;
  reportDate: string;
  status: MissedType;               // MISSED / LATE
  submittedAt?: string;
}
interface ReviewTimelinessResp {
  level1In24hRate: number;
  level2AvgHours: number;
  timeoutReviews: Array<{ reportId: number; reviewerName: string; waitingHours: number }>;
  lowRateDepts: Array<{ deptId: number; deptName: string; onTimeRate: number; consecutiveWeeks: number }>;
}

// 枚举类型
type MissedType = 'MISSED' | 'LATE';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → Tab 懒加载对应接口；按时率总览默认近 7 天；月度 Tab 默认本月。数据范围按角色服务端过滤（R4 本部门、R5/R6 本人）。

#### 4.2 核心操作流程
**A. 按时率总览（BR-103）**
1. 指标卡总按时率（目标 >95% 达标绿/未达标红）+ 按日趋势折线（ECharts）；
2. 按部门表：onTimeRate <90% 黄标、连续低率（MEE-S-R3 数据）红标 + "已推送负责人"标签；按人表（前端分页）。

**B. 月度提交率（BR-104 人月口径）**
1. 月份选择（必填）→ 人月统计表：应交天数（MEE-S-R1 排除请假/节假日，行悬浮显示"含请假 X 天、节假日 Y 天"）；
2. 部门汇总条形图；迟交计入 submittedDays 不计入 onTimeDays（分口径注释展示）。

**C. 未交督办（导出）**
1. 类型筛选（未交/迟交）+ 清单表格（dateRange 默认本周）；
2. [导出 Excel] → 异步导出（下载链接，提示"导出任务已提交"）。

**D. 审阅及时性**
1. 指标卡：一级 24h 完成率、二级平均时长；
2. 超时审阅清单（waitingHours 降序红标）+ 低率部门表（consecutiveWeeks ≥2 红标，MEE-S-R3 已推送标记）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| dateRange / statMonth | DateRangePicker / MonthPicker | 月度 Tab 必填 | 近 7 天 / 本月 | 按时率用范围、月度用月 |
| deptId | DeptTreeSelect | 否 | 空 | 部门 |
| type | Select | 否 | 空 | 未交/迟交（督办 Tab） |

### 6. 表格列定义

**按时率总览-按部门 / 按人表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| deptName / userName | 部门/姓名 | 140 | — | — |
| onTimeRate | 按时率 | 120 | ✓ 降序 | 进度条 + <90% 黄标 / <80% 红标 |
| submitRate | 提交率 | 120 | — | 进度条 |
| onTimeDays / shouldDays | 按时/应交天数 | 130 | — | 按人表 |

**月度提交率表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| statMonth | 月份 | 90 | — | yyyy-MM |
| userName | 姓名 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| shouldDays | 应交天数 | 90 | — | 悬浮显示请假/节假日明细 |
| onTimeDays | 按时天数 | 90 | — | — |
| submittedDays | 提交天数 | 90 | — | 含迟交（分口径注释） |
| onTimeRate | 按时率 | 100 | ✓ 降序 | 进度条 |
| submitRate | 提交率 | 100 | — | 进度条 |

**未交督办表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| userName | 姓名 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| reportDate | 日报日期 | 110 | ✓ 降序 | yyyy-MM-dd |
| status | 类型 | 90 | — | tag：未交(红)/迟交(黄) |
| submittedAt | 补交时间 | 150 | — | 迟交显示实际提交时间 |
| actions | 操作 | 100 | — | [去督办]（跳 P2 或工作台推送） |

**审阅及时性-超时审阅清单**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| reportId | 日报 ID | 100 | — | 可点击 |
| reviewerName | 审阅人 | 100 | — | — |
| waitingHours | 等待时长 | 110 | ✓ 降序 | "X 小时"红色 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 部门明细抽屉 | Drawer 60% | 部门行点击：该部门按日趋势 + 成员明细表 |
| 导出进度提示 | ElMessage | 异步导出提交 + 下载链接完成通知 |

### 8. 错误处理
- 月份未选（月度 Tab）：MonthPicker 必填提示；
- 考勤联动失败（钉钉接口超时 5003）：月度表顶部黄条"应交天数暂按当月工作日计算，考勤数据延迟同步"；
- 汇总任务延迟（5006）：看板黄条"数据截至 X 日"；
- 空数据：空态占位图。

### 9. BR 业务规则覆盖
- **BR-103（按时提交率 > 95%，日口径）**：按时率总览指标卡 + 趋势/部门/人三维；
- **BR-104（提交率按人月统计）**：月度提交率 Tab（shouldDays 排除请假/节假日）；
- MEE-S-R1（应提交工作日联动考勤）：shouldDays 悬浮明细；
- MEE-S-R2（按时率/提交率分口径）：列拆分 + 迟交分口径注释；
- MEE-S-R3（按时率 <90% 部门连续 2 周推送负责人）：低率部门表红标 + 已推送标记。

---

## P4. 会议纪要管理（MEET-004）

### 1. 页面概述
- 路由路径：`/ims/meet/minutes`
- 页面级别：一级菜单页（列表 + 登记抽屉 + 详情抽屉 + 行动项闭环 + 留痕率指标卡）
- 依赖模块：钉钉 AI 听记（V1 已建，初稿导入可选）、AUTH 人员选择器、工作台待办（行动项）、ALERT 推送（MEE-M-R2 逾期升级）
- 权限矩阵引用（PRD 4.2 MEET-004）：R1 R/W/D（全量）、R2 R/W（全量主责）、R4 R/W（本部门）、参会人 R（本人参会）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 指标卡: 本期会议 N | 已归档 N | 留痕率 xx% (BR-116 目标=100%) |     |
|   [未归档清单(超48h红标)]                                          |
+------------------------------------------------------------------+
| 查询行: 会议主题 | 会议时间范围 | 纪要状态 | [查询][重置] [登记会议]|
+------------------------------------------------------------------+
| 纪要列表表格:                                                     |
| 编号|会议主题|会议时间|参会人|行动项|状态|记录人|归档时间|操作         |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
登记/录入抽屉(720px): 会议主题* | 会议时间* | 参会人*(人员多选+外部人)|
  纪要正文* | 决议事项(动态列表) | 行动项(描述*|责任人*|期限*)         |
  [导入钉钉听记初稿](可选,编辑后提交)
详情抽屉(70%): Tab: [纪要正文] [决议事项] [行动项跟踪] [操作留痕]
  行动项: 描述|责任人|期限|状态(OPEN/CLOSED/OVERDUE)|[回填闭环]
  底部: [编辑(归档前)] [归档]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface MeetingMinutesCreateReq {
  meetingTitle: string;             // 必填 ≤128 字
  meetingDate: string;              // 必填 ISO 8601
  attendees: Array<{ userId?: number; userName: string; external?: boolean }>;  // 必填非空
  summary: string;                  // 必填 纪要正文
  decisions?: Array<{ description: string }>;
  actionItems?: Array<{
    description: string;            // 必填
    responsibleUserId: number;      // 必选
    dueDate: string;                // 必填
  }>;
  importFromAiMinutes?: string;     // 听记记录 ID（可选初稿导入）
  clientToken: string;
}
interface MeetingMinutesEditReq extends MeetingMinutesCreateReq {
  id: number;                       // 归档前可编辑
}
interface ActionItemCloseReq {
  closeRemark: string;              // 必填 ≤512 字
  evidenceUrl?: string;             // URL 格式校验
}
interface MinutesPageReq {
  pageNo: number; pageSize: number;
  meetingTitle?: string;
  meetingDateRange?: [string, string];
  minutesStatus?: MinutesStatus;
}

// 响应类型
interface MeetingMinutesVO {
  id: number;
  minutesNo: string;                // MM+日期+流水
  meetingTitle: string;
  meetingDate: string;
  attendees: Array<{ userId?: number; userName: string; external?: boolean }>;
  summary: string;
  decisions: Array<{ description: string }>;
  actionItems: Array<{
    itemId: number; description: string;
    responsibleUserId: number; responsibleName: string;
    dueDate: string;
    status: ActionItemStatus;       // OPEN / CLOSED / OVERDUE
  }>;
  minutesStatus: MinutesStatus;
  recorderUserId: number;
  recorderName: string;
  archivedAt?: string;
  createdAt: string;
}
interface ArchiveRateResp {
  totalMeetings: number;
  archivedCount: number;
  archiveRate: number;              // BR-116 目标 = 100%
  unarchivedList: Array<{
    minutesNo: string; meetingTitle: string; meetingDate: string;
    recorderName: string; hoursSinceMeeting: number;
  }>;
}

// 枚举类型
type MinutesStatus = 'REGISTERED' | 'MINUTES_RECORDED' | 'ARCHIVED';   // 已登记/纪要已录/已归档
type ActionItemStatus = 'OPEN' | 'CLOSED' | 'OVERDUE';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /meet/minutes/list` + `GET /meet/minutes/archive-rate`（留痕率指标卡）；失败分区重试。R4 本部门、参会人限本人参会记录（服务端过滤）。

#### 4.2 核心操作流程
**A. 登记会议/录入纪要（R2 主责 / 记录人）**
1. [登记会议] → 抽屉：主题/时间/参会人（内部人员多选 + 外部人员手工添加 external 标记）；
2. 可选 [导入钉钉听记初稿] → 选择听记记录 → summary 预填初稿文本（可编辑）；
3. 决议事项动态列表（增删行）；行动项编辑器（描述/责任人人员选择/期限，期限不早于当日）；
4. 提交（ConfirmDialog 汇总：参会人数/决议数/行动项数；clientToken）→ `POST /meet/minutes` → 行动项生成工作台待办；24h 内录入提醒为软约束（1116 提示不阻断）。

**B. 编辑与归档（MEE-M-R1/M3）**
1. [编辑]：仅 `MINUTES_RECORDED` 状态（归档前）→ 预填抽屉 → `PUT /meet/minutes/{id}`；`ARCHIVED` 行按钮隐藏（1117 拦截兜底）；
2. [归档]：ConfirmDialog 提示"归档后不可修改，行动项继续跟踪" → `PUT /meet/minutes/{id}/archive` → archivedAt 落库；
3. 会后 48h 未归档 → 指标卡 [未归档清单] 红标（hoursSinceMeeting >48）督办 BR-116。

**C. 行动项闭环（责任人，MEE-M-R2）**
1. 从工作台行动项待办或详情抽屉行动项 Tab → [回填闭环] → closeRemark 必填 + 可选 evidenceUrl → status=CLOSED；
2. 逾期 1 天系统推送责任人、3 天升级行政管理员（ALERT 联动，页面展示"已推送/已升级"标记）；OVERDUE 行红标。

**D. 留痕率督办（BR-116）**
- 指标卡留痕率 <100% 黄色警示 → [未归档清单] 抽屉列出未归档纪要（编号/主题/会议时间/记录人/已过小时数，>48h 红标）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| meetingTitle | Input | 否 | 空 | 主题模糊匹配 |
| meetingDateRange | DateRangePicker | 否 | 近 30 天 | 会议时间 |
| minutesStatus | Select | 否 | 空 | 已登记/纪要已录/已归档 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| minutesNo | 纪要编号 | 140 | — | 等宽字体（MM…） |
| meetingTitle | 会议主题 | 自适应 | — | 行点击打开详情抽屉 |
| meetingDate | 会议时间 | 150 | ✓ 降序 | yyyy-MM-dd HH:mm |
| attendeesCount | 参会人 | 90 | — | "N 人"，悬浮列表（外部人标灰） |
| actionItemsCount | 行动项 | 110 | — | "N 项（M 已闭环）"；有 OVERDUE 红点 |
| minutesStatus | 状态 | 110 | — | tag：已登记(灰)/纪要已录(蓝)/已归档(绿) |
| recorderName | 记录人 | 100 | — | — |
| archivedAt | 归档时间 | 150 | — | yyyy-MM-dd HH:mm；>48h 未归档红标 |
| actions | 操作 | 170 | — | [详情][编辑][归档] 按状态/权限 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 登记/录入抽屉 | Drawer 720px | meetingTitle 必填 ≤128；meetingDate 必填；attendees 必填非空；summary 必填；actionItems 每行 description 必填、responsibleUserId 必选、dueDate ≥ 当日；clientToken 防重；听记导入按钮可选 |
| 纪要详情抽屉 | Drawer 70% | 四 Tab：纪要正文（只读）/决议事项/行动项跟踪（状态+回填入口）/操作留痕（创建/编辑/归档时间线）；底部 [编辑][归档]（按状态） |
| 行动项回填抽屉 | Drawer 480px | closeRemark 必填 ≤512；evidenceUrl URL 校验 |
| 未归档清单抽屉 | Drawer 60% | BR-116 督办清单；hoursSinceMeeting >48 红标 |
| 归档确认弹窗 | Modal 400px | warning："归档后不可修改（MEE-M-R3），行动项继续跟踪至闭环" |
| 听记导入弹窗 | Modal 480px | 听记记录列表选择（标题/时间）→ 导入编辑 |

### 8. 错误处理
- 1116（24h/48h 时限）：软约束提示条，不阻断提交；
- 1117（已归档不可修改）：编辑入口隐藏 + 提示"已归档，更正请联系管理员走附录说明"；
- 1118（非行动项责任人）：提示"仅行动项责任人可回填"；
- 听记接口超时（5003）：导入弹窗提示"钉钉听记暂不可用，可稍后重试或手工录入"；
- 401/403 通用处理同全局规范。

### 9. BR 业务规则覆盖
- **BR-116（会议纪要留痕率 = 100%，48h 归档）**：顶部留痕率指标卡 + 未归档清单督办（>48h 红标）；
- MEE-M-R1（24h 录纪要、48h 归档）：1116 软提示 + 未归档清单小时数计算；
- MEE-M-R2（行动项逾期 1 天推送、3 天升级行政）：OVERDUE 红标 + 已推送/已升级标记（ALERT 联动）；
- MEE-M-R3（归档后不可修改）：状态机拦截 + 1117；
- 听记初稿导入（V1 能力复用）：导入 → 编辑 → 提交链路。

---

## 附录 A. 模块级约定

1. **枚举引用**：全局权威枚举 `ReportStatus`（DRAFT/SUBMITTED/READ，`READ` 即"已审阅"，契约历史表述 `REVIEWED` 已统一为 READ）、`ReviewAction`；模块内联枚举 `FollowUpStatus`/`MissedType`/`MinutesStatus`/`ActionItemStatus` 值域与 MEET-API 契约一致；
2. **错误码段**：1111~1120 MEET 段（1111 日报重复、1112 正文不可改、1113 越级审阅、1114 非审阅人、1115 非跟进项责任人、1116 归档时限软约束、1117 已归档、1118 非行动项责任人）；
3. **权限过滤**：R2/R4 本部门、参会人本人、审阅人队列判定 —— 全部服务端过滤；
4. **H5 同构**：P1 日报提交页为移动端优先（钉钉 H5 免登），P2~P4 为管理后台 Web 页；
5. **联动 V2-A1**：每日 17:00 日报待办生成、每日汇总统计任务均纳入集群化调度（Redisson 分布式锁）。

## 附录 B. BR/MEE 规则 ↔ 页面落点总表

| 规则 | 约束摘要 | 页面落点 |
|------|----------|----------|
| BR-103 | 按时提交率 > 95%（日口径） | P1 倒计时/isOnTime / P2 按时列 / P3 总览 |
| BR-104 | 提交率按人月统计 | P3 月度提交率 Tab |
| BR-116 | 纪要留痕率 = 100%（48h 归档） | P4 留痕率指标卡 + 未归档清单 |
| MEE-D-R1 | 截止默认 22:00 部门可配 | P1 deadlineTime 倒计时 |
| MEE-D-R2 | 逾期补交标记迟交分口径 | P1 迟交提示 / P3 督办 Tab |
| MEE-D-R3 | 一人一日一份 | P1 1111 拦截自动回显 |
| MEE-D-R4 | 周五周小结段 | P1 模板联动必填段 |
| MEE-R-R1 | 一级审阅 24h 内 | P2 队列红标 / P3 及时性 |
| MEE-R-R2 | 逐级审阅 | P2 nextLevel 联动 + 1113 |
| MEE-R-R3 | 跟进项待办闭环 | P2 标记跟进 → 回填闭环 |
| MEE-M-R1~R3 | 24h/48h 时限、逾期升级、归档锁定 | P4 登记提醒/清单/状态机 |
| MEE-S-R1~R3 | 考勤口径/分口径统计/低率推送 | P3 三个 Tab |

（全文完）
