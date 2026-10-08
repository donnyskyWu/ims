# MEET - 会议/日报管理 API 契约

> **模块范围**：03 会议/日报管理（V2，第 15~18 周，V2.1 批次）——MEET-001 日报提交、MEET-002 日报逐级审阅、MEET-003 日报提交率统计、MEET-004 会议纪要管理。  
> **导航（PRD v2.6.5）**：日报 API 仅服务侧栏 **日报中心**；**09 数据上报** 使用 `/admin-api/ims/report/*`（见 REPORT 契约），禁止混路由。
> **权威依据**：《IMS第二期PRD-V2.md》5.4~5.7；BR-103/BR-104/BR-116；V2-A1（每日 17:00 待办生成、每日汇总任务集群化）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`submit_status → submitStatus`、`report_date → reportDate`）；周次波浪号格式。日报全局权威枚举 `ReportStatus = 'DRAFT' | 'SUBMITTED' | 'READ'`（`REVIEWED` 为历史表述，已统一为 READ，见 3.1 状态机说明）。

---

## 1. API 总览表（共 20 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/meet/daily` | 提交/保存日报（含草稿） | 日报人本人（R5/R6/R10 被要求时） |
| 2 | GET | `/admin-api/ims/meet/daily/{date}` | 本人某日日报 | 本人 |
| 3 | GET | `/admin-api/ims/meet/daily/list` | 日报列表（按权限过滤，分页） | R1（全量）/R2（本部门）/R4（下属+本部门）/本人 |
| 4 | PUT | `/admin-api/ims/meet/daily/{id}` | 编辑日报（提交前草稿；已提交走补充说明） | 本人 |
| 5 | GET | `/admin-api/ims/meet/daily/template` | 日报模板获取（三段式+自定义+周五周小结） | 全员 |
| 6 | GET | `/admin-api/ims/meet/review/queue` | 审阅队列（一级/二级，分页） | 各级审阅人（R5 直属下级 / R4 本部门） |
| 7 | PUT | `/admin-api/ims/meet/review/{reportId}` | 提交审阅动作（已读/点评/标记跟进） | 各级审阅人 |
| 8 | GET | `/admin-api/ims/meet/review/records` | 审阅记录查询（分页） | R1/R2/R4（本部门） |
| 9 | PUT | `/admin-api/ims/meet/review/follow-up/{itemId}` | 跟进项闭环回填 | 跟进项责任人 |
| 10 | GET | `/admin-api/ims/meet/stat/on-time-rate` | 按时提交率（BR-103） | R1/R2/R9（全量）/R4（本部门）/R5/R6（本人） |
| 11 | GET | `/admin-api/ims/meet/stat/monthly` | 月度提交率（BR-104 人月口径） | 同上 |
| 12 | GET | `/admin-api/ims/meet/stat/missed` | 未交/迟交清单（督办导出） | R1/R2/R4 |
| 13 | GET | `/admin-api/ims/meet/stat/review-timeliness` | 审阅及时性统计（一级 24h 完成率） | 同上 |
| 14 | POST | `/admin-api/ims/meet/minutes` | 登记会议/录入纪要 | R2（主责）/记录人 |
| 15 | GET | `/admin-api/ims/meet/minutes/list` | 纪要列表（分页） | R1/R2（全量）/R4（本部门）/参会人 |
| 16 | GET | `/admin-api/ims/meet/minutes/{id}` | 纪要详情（含决议与行动项） | 同上 |
| 17 | PUT | `/admin-api/ims/meet/minutes/{id}` | 编辑纪要（归档前） | R2/记录人 |
| 18 | PUT | `/admin-api/ims/meet/minutes/{id}/archive` | 归档 | R2 |
| 19 | PUT | `/admin-api/ims/meet/minutes/action-item/{itemId}` | 行动项回填闭环 | 行动项责任人 |
| 20 | GET | `/admin-api/ims/meet/minutes/archive-rate` | 留痕率统计（BR-116） | R1/R2/R4/R9 |

---

## 2. 接口明细

### 2.1 日报提交（MEET-001）

#### 2.1.1 POST /admin-api/ims/meet/daily — 提交/保存日报

**请求**：

```typescript
interface DailyReportSubmitReq {
  reportDate: string;            // yyyy-MM-dd（日报所属日期）
  contentDone: string;           // 今日完成
  contentPlan: string;           // 明日计划
  contentIssue: string;          // 问题与风险
  extraFields?: Record<string, string>;   // 自定义字段
  /** true=存草稿（前端定时自动保存），false=正式提交 */
  asDraft: boolean;
}
```

**响应** `data`：

```typescript
interface DailyReportVO {
  id: number;
  reportDate: string;
  userId: number;
  userName: string;
  deptName: string;
  contentDone: string;
  contentPlan: string;
  contentIssue: string;
  extraFields?: Record<string, string>;
  submitStatus: 'DRAFT' | 'SUBMITTED' | 'READ';              // 0 草稿 / 1 已提交 / 2 已审阅（REVIEWED 为历史表述，已统一为 READ，与全局权威枚举 ReportStatus 一致）
  /** 补充说明段（已提交后修改走此段，MEE-D-R2/PUT 编辑约束） */
  supplement?: string;
  submittedAt?: string;
  isOnTime: boolean;             // BR-103 按时标记（截止当日 22:00，MEE-D-R1）
  createdAt: string;
}
```

**错误码**：1111（一人一日一份，唯一索引 userId+reportDate，MEE-D-R3）、1001（参数校验）、1112（已提交不可再编辑正文，须走补充说明）。

#### 2.1.2 GET /admin-api/ims/meet/daily/{date} — 本人某日日报

**请求**（Path）：`date`（yyyy-MM-dd）→ **响应** `data`：`DailyReportVO | null`（无记录返回 null，前端展示待办状态）。

#### 2.1.3 GET /admin-api/ims/meet/daily/list — 日报列表（分页）

**请求**（Query）：`PageParam` + `{ userId?: number; deptId?: number; reportDateRange?: [string, string]; submitStatus?: 'DRAFT' | 'SUBMITTED' | 'READ' }`

**响应** `data`：`PageResult<DailyReportVO>`。数据权限：R1 全量、R2 本部门、R4 下属+本部门、R5/R6 本人（服务端强制过滤）。

#### 2.1.4 PUT /admin-api/ims/meet/daily/{id} — 编辑日报

**请求**：`DailyReportSubmitReq` → **响应** `data`：`DailyReportVO`。仅草稿态可编辑正文；已提交态仅允许追加 `supplement` 补充说明字段。

#### 2.1.5 GET /admin-api/ims/meet/daily/template — 日报模板

**响应** `data`：

```typescript
interface DailyTemplateResp {
  sections: Array<{ key: 'done' | 'plan' | 'issue' | 'weekly'; label: string; required: boolean }>;
  extraFields: Array<{ key: string; label: string; type: 'TEXT' | 'NUMBER' | 'SELECT'; options?: string[] }>;
  /** 周五自动带出周小结段（MEE-D-R4） */
  weekSummaryEnabled: boolean;
  /** 部门级截止时间覆盖（默认 22:00，MEE-D-R1） */
  deadlineTime: string;          // HH:mm
}
```

### 2.2 日报逐级审阅（MEET-002）

#### 2.2.1 GET /admin-api/ims/meet/review/queue — 审阅队列（分页）

**请求**（Query）：`PageParam` + `{ reviewLevel?: 1 | 2; reportDateRange?: [string, string] }`

**响应** `data`：`PageResult<DailyReportVO & { reviewLevel: 1 | 2; waitingHours: number; isTimeout: boolean }>`（一级超 24 小时标记超时，MEE-R-R1）。

#### 2.2.2 PUT /admin-api/ims/meet/review/{reportId} — 提交审阅动作

**请求**：

```typescript
interface DailyReviewReq {
  reviewLevel: 1 | 2;            // 1 直属上级 / 2 部门负责人
  action: 'READ' | 'COMMENT' | 'MARK_FOLLOW_UP';   // 1 已读 / 2 点评 / 3 标记跟进
  comment?: string;              // 点评内容（COMMENT/MARK_FOLLOW_UP 建议填写）
  followUpItems?: Array<{        // MARK_FOLLOW_UP 必填
    description: string;
    responsibleUserId: number;
    dueDate: string;
  }>;
}
```

**响应** `data`：`{ reviewId: number; reportId: number; reviewedAt: string; nextLevel: 1 | 2 | null }`（一级完成后 nextLevel=2 进入二级队列，MEE-R-R2）。

**错误码**：1113（越级审阅：二级队列仅一级完成后进入）、1114（非该日报的审阅人，无权限）。

#### 2.2.3 GET /admin-api/ims/meet/review/records — 审阅记录（分页）

**请求**（Query）：`PageParam` + `{ reportId?: number; reviewerUserId?: number; reviewLevel?: 1 | 2; action?: 'READ' | 'COMMENT' | 'MARK_FOLLOW_UP' }`

**响应** `data`：`PageResult<DailyReviewVO>`

```typescript
interface DailyReviewVO {
  id: number;
  reportId: number;
  reportDate: string;
  reviewerUserId: number;
  reviewerName: string;
  reviewLevel: 1 | 2;
  action: 'READ' | 'COMMENT' | 'MARK_FOLLOW_UP';
  comment?: string;
  followUpItems: Array<{
    itemId: number; description: string;
    responsibleUserId: number; responsibleName: string;
    dueDate: string; status: 'OPEN' | 'CLOSED';
  }>;
  reviewedAt: string;
}
```

#### 2.2.4 PUT /admin-api/ims/meet/review/follow-up/{itemId} — 跟进项闭环回填

**请求**：`{ closeRemark?: string; evidenceUrl?: string }` → **响应**：`data: null`。跟进项生成工作台待办（复用 V1 AUTH-004）并联动 14 工作流；责任人完成回填后闭环（MEE-R-R3）。

**错误码**：1115（非跟进项责任人，无权限回填）。

### 2.3 日报提交率统计（MEET-003）

#### 2.3.1 GET /admin-api/ims/meet/stat/on-time-rate — 按时提交率（BR-103）

**请求**（Query）：`{ dateRange?: [string, string]; deptId?: number }`

**响应** `data`：

```typescript
interface DailyOnTimeRateResp {
  /** BR-103：按时提交人数 / 应提交人数（日口径），目标 > 95% */
  totalOnTimeRate: number;
  byDept: Array<{ deptId: number; deptName: string; onTimeRate: number; submitRate: number }>;
  byPerson: Array<{ userId: number; userName: string; deptName: string; onTimeDays: number; submittedDays: number; shouldDays: number }>;
  trend: Array<{ date: string; onTimeRate: number }>;
}
```

#### 2.3.2 GET /admin-api/ims/meet/stat/monthly — 月度提交率（BR-104）

**请求**（Query）：`{ statMonth: string; deptId?: number }` → **响应** `data`：`PageResult<{ statMonth: string; userId: number; userName: string; deptName: string; shouldDays: number; onTimeDays: number; submittedDays: number; onTimeRate: number; submitRate: number }>`（按人月统计；应提交工作日排除请假/节假日，联动钉钉考勤，MEE-S-R1）。

#### 2.3.3 GET /admin-api/ims/meet/stat/missed — 未交/迟交清单

**请求**（Query）：`PageParam` + `{ dateRange?: [string, string]; deptId?: number; type?: 'MISSED' | 'LATE' }` → **响应** `data`：`PageResult<{ userId: number; userName: string; deptName: string; reportDate: string; status: 'MISSED' | 'LATE'; submittedAt?: string }>`（支持 Excel 导出督办；迟交计入提交率不计入按时率，BR-103/BR-104 分口径）。

#### 2.3.4 GET /admin-api/ims/meet/stat/review-timeliness — 审阅及时性

**请求**（Query）：`{ dateRange?: [string, string]; deptId?: number }` → **响应** `data`：`{ level1In24hRate: number; level2AvgHours: number; timeoutReviews: Array<{ reportId: number; reviewerName: string; waitingHours: number }>; lowRateDepts: Array<{ deptId: number; deptName: string; onTimeRate: number; consecutiveWeeks: number }> }`（按时率低于 90% 的部门连续 2 周推送负责人，MEE-S-R3）。

### 2.4 会议纪要管理（MEET-004）

#### 2.4.1 POST /admin-api/ims/meet/minutes — 登记会议/录入纪要

**请求**：

```typescript
interface MeetingMinutesCreateReq {
  meetingTitle: string;
  meetingDate: string;           // ISO 8601
  attendees: Array<{ userId?: number; userName: string; external?: boolean }>;
  summary: string;               // 纪要正文
  decisions?: Array<{ description: string }>;
  actionItems?: Array<{
    description: string;
    responsibleUserId: number;
    dueDate: string;
  }>;
  /** 可选：导入钉钉 AI 听记初稿（V1 已建能力）编辑后提交 */
  importFromAiMinutes?: string;  // 听记记录 ID
}
```

**响应** `data`：

```typescript
interface MeetingMinutesVO {
  id: number;
  minutesNo: string;             // MM+日期+流水
  meetingTitle: string;
  meetingDate: string;
  attendees: Array<{ userId?: number; userName: string; external?: boolean }>;
  summary: string;
  decisions: Array<{ description: string }>;
  actionItems: Array<{
    itemId: number; description: string;
    responsibleUserId: number; responsibleName: string;
    dueDate: string; status: 'OPEN' | 'CLOSED' | 'OVERDUE';
  }>;
  minutesStatus: 'REGISTERED' | 'MINUTES_RECORDED' | 'ARCHIVED';   // 0 会议已登记 / 1 纪要已录 / 2 已归档
  recorderUserId: number;
  recorderName: string;
  archivedAt?: string;
  createdAt: string;
}
```

**错误码**：1116（会后 24 小时内须录入纪要提醒、48 小时归档时限校验，MEE-M-R1 软约束提示不阻断）。

#### 2.4.2 GET /admin-api/ims/meet/minutes/list — 纪要列表（分页）

**请求**（Query）：`PageParam` + `{ meetingTitle?: string; meetingDateRange?: [string, string]; minutesStatus?: 'REGISTERED' | 'MINUTES_RECORDED' | 'ARCHIVED' }` → **响应** `data`：`PageResult<MeetingMinutesVO>`（R4 限本部门、参会人限本人参会记录）。

#### 2.4.3 GET /admin-api/ims/meet/minutes/{id} — 纪要详情

**响应** `data`：`MeetingMinutesVO`。

#### 2.4.4 PUT /admin-api/ims/meet/minutes/{id} — 编辑纪要

**请求**：`MeetingMinutesCreateReq` → **响应** `data`：`MeetingMinutesVO`。归档前可编辑（`MINUTES_RECORDED` 状态）；归档后不可修改（MEE-M-R3，更正走附录说明）。

**错误码**：1117（已归档纪要不可修改）。

#### 2.4.5 PUT /admin-api/ims/meet/minutes/{id}/archive — 归档

**响应**：`data: null`（`archivedAt` 落库，状态 → `ARCHIVED`）。归档后行动项仍继续跟踪至闭环。

#### 2.4.6 PUT /admin-api/ims/meet/minutes/action-item/{itemId} — 行动项回填闭环

**请求**：`{ closeRemark: string; evidenceUrl?: string }` → **响应**：`data: null`。行动项逾期 1 天推送责任人、3 天升级行政管理员（MEE-M-R2，联动 ALERT 推送通道）。

**错误码**：1118（非行动项责任人）。

#### 2.4.7 GET /admin-api/ims/meet/minutes/archive-rate — 留痕率（BR-116）

**请求**（Query）：`{ dateRange?: [string, string] }` → **响应** `data`：`{ totalMeetings: number; archivedCount: number; archiveRate: number; unarchivedList: Array<{ minutesNo: string; meetingTitle: string; meetingDate: string; recorderName: string; hoursSinceMeeting: number }> }`（BR-116 目标 = 100%）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**日报（DailyReportVO.submitStatus）**：

```
DRAFT ──提交──▶ SUBMITTED ──二级审阅完成──▶ READ
  │                 │                        │
  └──草稿自动保存────┘──补充说明（supplement 追加，不改正文）──┘
```

> 说明：全局权威枚举 `ReportStatus = 'DRAFT' | 'SUBMITTED' | 'READ'`；本模块按 PRD 5.4.2 的 0/1/2 三态映射为 `DRAFT / SUBMITTED / READ`（`READ` 即"已审阅"；`REVIEWED` 为历史表述，已统一为 READ，与全局权威枚举 ReportStatus 一致）。

**会议纪要（MeetingMinutesVO.minutesStatus）**：

```
REGISTERED（会议已登记）──录入纪要──▶ MINUTES_RECORDED ──归档──▶ ARCHIVED（不可修改）
                                        │
                                        └──行动项持续跟踪 OPEN → CLOSED / OVERDUE
```

**跟进项/行动项（status）**：`OPEN → CLOSED（回填闭环）/ OVERDUE（逾期督办）`

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-103 | 按时提交率 > 95%（日口径） | 2.3.1 |
| BR-104 | 提交率按人月统计（实际天数/应工作日） | 2.3.2 |
| BR-116 | 会议纪要留痕率 = 100%（48 小时归档） | 2.4.7 |
| MEE-D-R1 | 截止默认当日 22:00（部门可配） | 2.1.1 isOnTime / 2.1.5 deadlineTime |
| MEE-D-R2 | 逾期补交标记迟交，分口径统计 | 2.3.3 |
| MEE-D-R3 | 一人一日一份（唯一索引） | 2.1.1 错误码 1111 |
| MEE-D-R4 | 周五自动带出周小结段 | 2.1.5 模板 |
| MEE-R-R1 | 一级审阅 24 小时内完成 | 2.2.1 isTimeout / 2.3.4 |
| MEE-R-R2 | 逐级：一级完成才进二级 | 2.2.2 错误码 1113 |
| MEE-R-R3 | 跟进项生成待办闭环 | 2.2.4（联动 AUTH-004 与 FLOW） |
| MEE-M-R1 | 24h 录纪要、48h 归档 | 2.4.1 / 2.4.5 |
| MEE-M-R2 | 行动项逾期 1 天推送、3 天升级行政 | 2.4.6（联动 ALERT） |
| MEE-M-R3 | 归档后不可修改 | 2.4.4 错误码 1117 |
| MEE-S-R1 | 应提交工作日排除请假/节假日（联动考勤） | 2.3.2 shouldDays |
| V2-A1 | 每日 17:00 待办生成 / 汇总任务集群化（Redisson 锁） | 2.3.x 统计任务 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 日报提交页（移动端优先，钉钉 H5 同构） | 填写三段式日报（草稿自动保存/提交） | POST /meet/daily |
| 日报提交页-模板渲染 | 加载日报模板（周五带出周小结段） | GET /meet/daily/template |
| 日报提交页-当日回显 | 查看本人某日日报（含草稿恢复） | GET /meet/daily/{date} |
| 日报管理页（QueryBar 一行排布 + 表格） | 日报列表查询（部门/状态/日期筛选） | GET /meet/daily/list |
| 日报编辑 | 修改草稿 / 已提交追加补充说明 | PUT /meet/daily/{id} |
| 审阅工作台（我的审阅队列 Tab） | 加载一级/二级审阅队列 | GET /meet/review/queue |
| 审阅抽屉（DetailDrawer 内联） | 已读 / 点评 / 标记跟进项 | PUT /meet/review/{reportId} |
| 审阅记录页 | 审阅记录查询（留痕） | GET /meet/review/records |
| 工作台-跟进项待办 | 跟进项完成回填 | PUT /meet/review/follow-up/{itemId} |
| 日报统计看板 | 按时率 / 月度提交率 / 审阅及时性 | GET /meet/stat/on-time-rate、/monthly、/review-timeliness |
| 未交督办页 | 未交/迟交清单导出 | GET /meet/stat/missed |
| 会议纪要登记页（表单 + 参会人选择器） | 登记会议/录入纪要（可导入听记初稿） | POST /meet/minutes |
| 会议纪要列表页 | 纪要列表查询 | GET /meet/minutes/list |
| 纪要详情抽屉 | 查看决议/行动项 / 编辑（归档前）/ 归档 | GET /meet/minutes/{id}、PUT /meet/minutes/{id}、PUT /meet/minutes/{id}/archive |
| 工作台-行动项待办 | 行动项回填闭环 | PUT /meet/minutes/action-item/{itemId} |
| 留痕率指标卡 | 纪要留痕率统计（BR-116） | GET /meet/minutes/archive-rate |

（全文完）
