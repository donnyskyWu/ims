# TRAIN - 培训管理 API 契约

> **模块范围**：02 培训管理（V2，第 15~18 周，V2.1 批次）——TRAIN-001 岗位资料库、TRAIN-002 学习任务管理、TRAIN-003 学习完成率统计；TRAIN-004 AI 试卷生成见 **§2.4（ADR-IMS-004 已批准 · 2026-10-01）**。
> **权威依据**：《IMS第二期PRD-V2.md》5.1~5.3；《共享技术规范-数据库与API.md》8.1/8.3；V2-A1 定时任务集群化约束（每日汇总任务）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章；字段 camelCase（`material_no → materialNo`、`position_codes → positionCodes`）；周次波浪号格式。

---

## 1. API 总览表（共 18 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/train/material/cates` | 资料分类树（岗位 → 类别） | R1/R2/R4/R5/R6/R7（本岗位）/R10（指派课程） |
| 2 | POST | `/admin-api/ims/train/material` | 上传资料（文档/视频/链接） | R2（主责）/R1 |
| 3 | GET | `/admin-api/ims/train/material/list` | 资料列表（按岗位过滤，分页） | 同上 |
| 4 | PUT | `/admin-api/ims/train/material/{id}` | 更新资料（生成新版本） | R2/R1 |
| 5 | DELETE | `/admin-api/ims/train/material/{id}` | 下架资料 | R1/R2 |
| 6 | GET | `/admin-api/ims/train/material/weekly-update-metrics` | 每周更新率统计（BR-101） | R1/R2/R4 |
| 7 | POST | `/admin-api/ims/train/task` | 创建学习任务（指派） | R2（主责）/R1 |
| 8 | GET | `/admin-api/ims/train/task/list` | 任务列表（分页） | R1/R2/R4（本部门）/被指派人 |
| 9 | PUT | `/admin-api/ims/train/task/{id}` | 编辑任务（截止前） | R2/R1 |
| 10 | DELETE | `/admin-api/ims/train/task/{id}` | 删除任务 | R1 |
| 11 | PUT | `/admin-api/ims/train/task/{id}/progress` | 上报学习进度（视频时长/文档翻页） | 被指派人本人 |
| 12 | POST | `/admin-api/ims/train/task/{id}/confirm` | 完成确认（学时达标/问卷提交） | 被指派人本人 |
| 13 | GET | `/admin-api/ims/train/task/records` | 学习记录查询（分页） | R1/R2/R4（本部门）/本人/R10（被指派） |
| 14 | GET | `/admin-api/ims/train/stat/finish-rate` | 完成率指标（BR-102） | R1/R2/R9（全量）/R4（本部门）/R5/R6/R7（本人） |
| 15 | GET | `/admin-api/ims/train/stat/dept` | 部门完成率统计 | 同上 |
| 16 | GET | `/admin-api/ims/train/stat/rank` | 学习时长排行（部门/个人） | 同上 |
| 17 | GET | `/admin-api/ims/train/stat/overdue` | 逾期未完成清单（督办导出） | R1/R2/R4 |
| 18 | GET | `/admin-api/ims/train/stat/material-heat` | 资料热度（学习人次） | 同上 |

---

## 2. 接口明细

### 2.1 岗位资料库（TRAIN-001）

#### 2.1.1 GET /admin-api/ims/train/material/cates — 分类树

**响应** `data`：

```typescript
interface MaterialCateTreeVO {
  id: number;
  cateName: string;
  parentId: number | null;      // 岗位节点 → 类别节点两级
  positionCode?: string;        // 岗位编码（顶层节点）
  materialCount: number;        // 已发布资料数
  children: MaterialCateTreeVO[];
}
```

#### 2.1.2 POST /admin-api/ims/train/material — 上传资料

**请求**：

```typescript
interface MaterialUploadReq {
  title: string;
  cateId: number;
  materialType: 'DOC' | 'VIDEO' | 'LINK';          // PRD 5.1.2 material_type
  /** fileKey（FileUpload 组件直传回执，DOC/VIDEO 必填） */
  fileKey?: string;
  /** 外链地址（LINK 必填） */
  linkUrl?: string;
  /** 关联岗位编码列表（新员工自动可见本岗位资料包，TRN-M-R1） */
  positionCodes: string[];
  /** 直接发布或存草稿 */
  publish: boolean;
}
```

**响应** `data`：

```typescript
interface MaterialVO {
  id: number;
  materialNo: string;           // MT+日期+流水
  title: string;
  cateId: number;
  materialType: 'DOC' | 'VIDEO' | 'LINK';
  fileUrl?: string;             // 签名 URL（60 秒）
  linkUrl?: string;
  positionCodes: string[];
  version: number;
  status: 'DRAFT' | 'PUBLISHED' | 'OFFLINE';       // 0 草稿 / 1 已发布 / 2 已下架
  uploaderUserId: number;
  uploaderName: string;
  updatedAt: string;
}
```

**错误码**：1101（分类不存在）、1103（资料未发布状态对学员不可见，TRN-M-R1 仅查询场景拦截）、1001（参数校验）。

#### 2.1.3 GET /admin-api/ims/train/material/list — 资料列表（分页）

**请求**（Query）：`PageParam` + `{ cateId?: number; title?: string; materialType?: 'DOC' | 'VIDEO' | 'LINK'; status?: 'DRAFT' | 'PUBLISHED' | 'OFFLINE'; positionCode?: string }`

**响应** `data`：`PageResult<MaterialVO>`。普通学员（R5/R6/R7）仅返回本岗位、`PUBLISHED` 状态资料（服务端过滤）。

#### 2.1.4 PUT /admin-api/ims/train/material/{id} — 更新资料（新版本）

**请求**：`MaterialUploadReq`（同 2.1.2）→ **响应**：`MaterialVO`（`version` 自增）。

**业务约束**：更新生成新版本，旧版本留档可查（TRN-M-R2）；版本快照不可修改。

#### 2.1.5 DELETE /admin-api/ims/train/material/{id} — 下架资料

**响应**：`data: null`。下架后学员不可见（状态 `OFFLINE`），被进行中学习任务引用时提示且不强删。

#### 2.1.6 GET /admin-api/ims/train/material/weekly-update-metrics — 每周更新率（BR-101）

**请求**（Query）：`{ weekStart?: string }`（默认本周一）

**响应** `data`：`{ shouldUpdateCount: number; updatedCount: number; weeklyUpdateRate: number; unupdatedList: Array<{ materialNo: string; title: string; lastUpdatedAt: string; ownerName: string }> }`（BR-101 目标 = 100%，未更新进入督办）。

### 2.2 学习任务管理（TRAIN-002）

#### 2.2.1 POST /admin-api/ims/train/task — 创建学习任务

**请求**：

```typescript
interface TrainTaskCreateReq {
  taskName: string;
  materialIds: number[];
  assignScope: 'BY_USER' | 'BY_POSITION';           // 1 按人 / 2 按岗位
  /** BY_USER: userId 列表；BY_POSITION: 岗位编码列表（批量展开目标人） */
  assignTargetUserIds?: number[];
  assignTargetPositionCodes?: string[];
  deadline: string;              // ISO 8601
  confirmType: 'DURATION' | 'QUIZ';                 // 1 学时达标 / 2 自测问卷
  /** QUIZ 模式必填：问卷题目与及格分 */
  quiz?: Array<{
    question: string;
    options: string[];
    answerIndex: number;
  }>;
  passScore?: number;
}
```

**响应** `data`：

```typescript
interface TrainTaskVO {
  id: number;
  taskNo: string;                // TT+日期+流水
  taskName: string;
  materialIds: number[];
  assignScope: 'BY_USER' | 'BY_POSITION';
  assignedCount: number;         // 展开后应完成人次
  deadline: string;
  confirmType: 'DURATION' | 'QUIZ';
  status: 'IN_PROGRESS' | 'FINISHED';               // 0 进行中 / 1 已结束
  createdAt: string;
}
```

**错误码**：1102（截止时间早于当前时间）、1101（资料不存在或未发布）、1001（参数校验：assignScope 与目标列表不匹配）。

**联动**：入职事件（V1 AUTH-002 钉钉通讯录 user_add）自动指派岗位学习包（截止 = 入职日 + 14 天，TRN-T-R3），无需人工创建。

#### 2.2.2 GET /admin-api/ims/train/task/list — 任务列表（分页）

**请求**（Query）：`PageParam` + `{ taskName?: string; status?: 'IN_PROGRESS' | 'FINISHED'; confirmType?: 'DURATION' | 'QUIZ' }`

**响应** `data`：`PageResult<TrainTaskVO & { finishRate: number }>`（完成率 = 已完成人次 / 应完成人次，BR-102）。

#### 2.2.3 PUT /admin-api/ims/train/task/{id} — 编辑任务

**请求**：`TrainTaskCreateReq` → **响应**：`TrainTaskVO`。仅 `IN_PROGRESS` 且截止前可编辑；已产生的学习记录不回滚。

#### 2.2.4 DELETE /admin-api/ims/train/task/{id} — 删除任务

**响应**：`data: null`。逻辑删除；已有完成记录的任务删除后统计口径按删除时点冻结（完成率历史不受影响）。

#### 2.2.5 PUT /admin-api/ims/train/task/{id}/progress — 上报学习进度

**请求**：

```typescript
interface TrainProgressReportReq {
  materialId: number;
  /** 视频模式：累计有效观看秒数（拖拽快进不计，服务端按心跳区间去重，TRN-T-R1） */
  watchedSeconds?: number;
  /** 文档模式：当前页码 / 总页数 */
  currentPage?: number;
  totalPages?: number;
  /** 心跳上报（前端 15 秒一次），服务端聚合进度 */
  heartbeatAt: string;
}
```

**响应** `data`：

```typescript
interface TrainProgressVO {
  taskId: number;
  userId: number;
  materialId: number;
  progress: number;              // 0~100
  materialProgress: Record<number, number>;   // 单资料进度（materialId → 百分比）
  confirmStatus: 'NOT_CONFIRMED' | 'CONFIRMED';
  startedAt: string;
  finishedAt?: string;
}
```

**错误码**：1105（非被指派人无权上报进度）。

#### 2.2.6 POST /admin-api/ims/train/task/{id}/confirm — 完成确认

**请求**：

```typescript
interface TrainConfirmReq {
  /** QUIZ 模式：问卷作答（服务端判分） */
  answers?: Array<{ questionIndex: number; answerIndex: number }>;
}
```

**响应** `data`：`{ confirmStatus: 'CONFIRMED'; confirmScore?: number; isPassed: boolean; finishedAt: string }`

**错误码**：1104（DURATION 模式学时未达标、QUIZ 模式问卷未配置）、1105（非被指派人）。

#### 2.2.7 GET /admin-api/ims/train/task/records — 学习记录查询（分页）

**请求**（Query）：`PageParam` + `{ taskId?: number; userId?: number; deptId?: number; confirmStatus?: 'NOT_CONFIRMED' | 'CONFIRMED'; overdue?: boolean }`

**响应** `data`：`PageResult<TrainProgressVO & { taskNo: string; taskName: string; userName: string; deptName: string; isOverdue: boolean }>`。R4 限本部门、R5/R6/R7/R10 限本人（服务端过滤）。

### 2.3 学习完成率统计（TRAIN-003）

#### 2.3.1 GET /admin-api/ims/train/stat/finish-rate — 完成率指标（BR-102）

**请求**（Query）：`{ dateRange?: [string, string] }`

**响应** `data`：

```typescript
interface TrainFinishRateResp {
  /** BR-102：已完成学习人次 / 应完成学习人次（含逾期分母），目标 > 90% */
  totalFinishRate: number;
  byTask: Array<{ taskNo: string; taskName: string; assignedCount: number; finishedCount: number; finishRate: number }>;
  byDept: Array<{ deptId: number; deptName: string; assignedCount: number; finishedCount: number; finishRate: number }>;
  byPerson: Array<{ userId: number; userName: string; deptName: string; assignedCount: number; finishedCount: number; finishRate: number }>;
}
```

#### 2.3.2 GET /admin-api/ims/train/stat/dept — 部门统计

**请求**（Query）：`{ statDateRange?: [string, string] }` → **响应** `data`：`Array<{ statDate: string; deptId: number; deptName: string; assignedCount: number; finishedCount: number; finishRate: number; avgDurationMinutes: number }>`（来源 `ims_train_stat_daily`，TRN-S-R1 每日凌晨汇总，任务纳入 V2-A1 集群化调度）。

#### 2.3.3 GET /admin-api/ims/train/stat/rank — 学习时长排行

**请求**（Query）：`{ dimension: 'DEPT' | 'PERSON'; dateRange?: [string, string]; topN?: number }` → **响应** `data`：`Array<{ rank: number; deptName?: string; userName?: string; userId?: number; totalDurationMinutes: number; finishRate: number }>`

#### 2.3.4 GET /admin-api/ims/train/stat/overdue — 逾期未完成清单

**请求**（Query）：`PageParam` + `{ taskId?: number; deptId?: number }` → **响应** `data`：`PageResult<{ taskId: number; taskNo: string; taskName: string; userId: number; userName: string; deptName: string; deadline: string; overdueDays: number; progress: number }>`（支持 Excel 导出督办，TRN-T-R2 逾期进入督办并计入完成率分母）。

#### 2.3.5 GET /admin-api/ims/train/stat/material-heat — 资料热度

**请求**（Query）：`{ dateRange?: [string, string]; topN?: number }` → **响应** `data`：`Array<{ materialId: number; materialNo: string; title: string; materialType: 'DOC' | 'VIDEO' | 'LINK'; studyCount: number; avgDurationMinutes: number }>`

### 2.4 TRAIN-004 AI 自动生成培训试卷（IMS 设计 SSOT · ADR-IMS-004）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 19 | POST | `/admin-api/ims/train/quiz/ai-generate` | 同步生成草稿（单选+判断） |
| 20 | POST | `/admin-api/ims/train/quiz/ai-adopt` | 可选：draftId → quiz 结构供任务保存 |

**请求/响应**见《ADR-IMS-004-TRAIN-AI试卷生成-待定.md》§3。**采纳**后写入 `POST/PUT …/train/task` 的 `quiz[]` + `passScore`。**错误码**：1111～1114（AIR/资料/超时）。

**任务 `quiz` 项结构（与手工一致）**：

```typescript
quiz: Array<{
  type: 'SINGLE' | 'TRUE_FALSE';
  question: string;
  options?: string[];
  answerIndex?: number;
  answerBoolean?: boolean;
}>;
```

---

## 3. 状态机与业务约束

### 3.1 状态机

**资料（MaterialVO.status）**：

```
DRAFT ──发布──▶ PUBLISHED ──下架──▶ OFFLINE
                   │                     │
                   └──更新（新版本，version+1）──┘
```

**学习任务（TrainTaskVO.status）**：

```
IN_PROGRESS ──截止时间到达──▶ FINISHED（完成率分母冻结）
```

**学习记录（confirmStatus）**：

```
NOT_CONFIRMED ──学时达标/问卷通过──▶ CONFIRMED（finishedAt 落库）
NOT_CONFIRMED ──逾期──▶ 仍可补学补确认（标记逾期，计入分母）
```

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-101 | 培训每周更新率 = 100% | 2.1.6 weekly-update-metrics |
| BR-102 | 学习完成率 > 90%（含逾期分母） | 2.2.2 / 2.3.1 |
| TRN-M-R1 | 仅已发布资料对学员可见 | 2.1.3 服务端过滤 |
| TRN-M-R2 | 资料更新新版本留档 | 2.1.4（version 自增） |
| TRN-M-R3 | 每周更新率纳入统计 | 2.1.6 |
| TRN-T-R1 | 视频按实际观看时长计进度，快进不计 | 2.2.5（心跳区间去重） |
| TRN-T-R2 | 截止前 1 天提醒，逾期督办 | 2.3.4 overdue |
| TRN-T-R3 | 入职自动指派（入职日+14 天） | 2.2.1 联动 V1 AUTH-002 |
| TRN-S-R1 | 每日凌晨汇总（V2-A1 集群化调度） | 2.3.2（ims_train_stat_daily） |
| TRN-S-R3 | 部门完成率连续 2 周低于 85% 推送负责人 | 2.3.2（联动 ALERT） |
| V2-A1 | 定时任务 Redisson 分布式锁，防集群重复调度 | 2.3.2 统计汇总任务 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 岗位资料库页（左侧分类树 + 右侧列表） | 分类树加载 / 资料列表查询 | GET /train/material/cates、GET /train/material/list |
| 资料上传抽屉（DetailDrawer + FileUpload 服务端上传） | 上传文档/视频（先服务端上传再提交元信息）/ 配置外链 | POST /train/material |
| 资料详情抽屉 | 编辑资料（生成新版本，展示版本史） | PUT /train/material/{id} |
| 资料列表行操作 | 下架（ConfirmDialog 二次确认） | DELETE /train/material/{id} |
| 资料更新率指标卡 | 每周更新率看板（BR-101 未更新清单督办） | GET /train/material/weekly-update-metrics |
| 学习任务管理页（QueryBar 一行排布 + 表格） | 任务列表查询（完成率列） | GET /train/task/list |
| 任务创建抽屉（表单 + 资料多选 + 目标选择器） | 创建任务（按人/按岗位） | POST /train/task |
| 任务行操作 | 编辑 / 删除 | PUT /train/task/{id}、DELETE /train/task/{id} |
| 个人工作台-学习中心（H5 同构） | 学习执行：视频播放器（心跳上报）/ 文档翻页 | PUT /train/task/{id}/progress |
| 学习中心-完成确认 | 问卷作答提交 / 学时达标确认 | POST /train/task/{id}/confirm |
| 学习记录页 | 记录查询（按人/部门/逾期筛选） | GET /train/task/records |
| 培训统计看板 | 完成率总览 / 部门统计 / 时长排行 / 资料热度 | GET /train/stat/finish-rate、/dept、/rank、/material-heat |
| 逾期督办页 | 逾期未完成清单导出 | GET /train/stat/overdue |
| AI 生成试卷向导（P2） | 选资料 → 参数 → 生成预览 → 采纳写入 `quiz` | **§2.4 BLOCKED**（原型 Mock only） |

（全文完）
