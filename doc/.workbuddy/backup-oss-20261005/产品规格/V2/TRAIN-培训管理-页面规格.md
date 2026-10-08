# TRAIN - 培训管理 页面规格

> 依据：《IMS第二期PRD-V2.md》5.1~5.3（TRAIN-001~003）、完整 PRD v2.6.6 TRAIN-004（走查 #11）、《共享技术规范-分期技术约束.md》V2-A1（定时任务集群化）、《TRAIN-培训管理-API契约.md》§2.4、《ADR-IMS-004-TRAIN-AI试卷生成-待定.md》（已批准 · 2026-10-01）、《全局开发规范.md》第 4 章（权威枚举）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/train`。
> 归属期次：V2 第 15~18 周（V2.1 管理动作线上化批次）。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 岗位资料库 | `/ims/train/material` | 一级菜单页（左树右表） | TRAIN-001 |
| P2 学习任务管理 | `/ims/train/task` | 一级菜单页 | TRAIN-002 |
| P3 培训统计看板 | `/ims/train/stat` | 一级菜单页（Tab 看板） | TRAIN-003 |
| P4 学习中心 | `/ims/train/study/{taskId}` | 二级页面（H5 同构） | TRAIN-002 执行态 |

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布（QueryBar）；交互操作优先内联抽屉（Drawer），不跳转新页面；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红 / 中性灰）；
- 周次/周期展示用波浪号格式（如"第 15~18 周"）；
- 枚举一律引用《全局开发规范.md》第 4 章：`MaterialType`、`TrainTaskStatus`、`TrainStatus`、`EnableStatus`。

---

## P1. 岗位资料库（TRAIN-001）

### 1. 页面概述
- 路由路径：`/ims/train/material`
- 页面级别：一级菜单页，左侧分类树（岗位 → 类别两级）+ 右侧资料列表 + 顶部周更率指标卡
- 依赖模块：AUTH-003 岗位-角色供给规则（**岗位编码字典 · ADR-IMS-008**，岗位码语义不变）、FileUpload（OSS 直传 `businessScene: 'material'`）、AUTH-002 入职事件联动（TRN-M-R1 新员工自动可见）
- 权限矩阵引用（PRD 4.2 TRAIN-001）：R1 R/W/D（全量）、R2 R/W（全量主责）、R4 R（全量）、R5/R6/R7 R（本岗位已发布，服务端过滤）、R10 R（指派课程）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 指标卡: 本周应更新 N | 已更新 N | 周更新率 xx% (BR-101) | [未更新清单]|
+------------------------------------------------------------------+
| +------------------+ +----------------------------------------+  |
| | 分类树(240px)    | | 查询行: 标题 | 类型 | 状态 | [查询][重置] |  |
| | 岗位(可折叠)     | |         | [上传资料]            |  |
| |  └ 类别(N)       | +----------------------------------------+  |
| |  └ ...           | | 资料列表表格:                          |  |
| |                  | | 编号|标题|类型|版本|岗位|状态|更新人|更新时间|操作|
| +------------------+ +----------------------------------------+  |
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
上传抽屉(640px): 分类* | 标题* | 类型*(DOC/VIDEO/LINK) |
  FileUpload(DOC/VIDEO) / 外链URL(LINK) | 关联岗位* | [存草稿][发布]
详情抽屉(60%): 基础信息 + 版本历史列表 + 预览(视频播放/文档预览/外链跳转)
未更新清单抽屉(60%): BR-101 应更新未更新列表(编号/标题/负责人/最后更新)
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface MaterialPageReq {
  pageNo: number; pageSize: number;
  cateId?: number; title?: string;
  materialType?: MaterialType;
  status?: MaterialStatus;
  positionCode?: string;
}
interface MaterialUploadReq {
  title: string;                    // 必填 ≤128 字
  cateId: number;                   // 必填（类别级节点）
  materialType: MaterialType;       // 必填
  ossKey?: string;                  // DOC/VIDEO 必填（FileUpload OSS 直传回执）
  linkUrl?: string;                 // LINK 必填（URL 格式校验）
  positionCodes: string[];          // 必填非空（关联岗位，新员工自动可见）
  publish: boolean;                 // true 直接发布 / false 存草稿
}
interface MaterialUpdateReq extends MaterialUploadReq {
  id: number;                       // 更新生成新版本 version+1（TRN-M-R2）
}

// 响应类型
interface MaterialCateTreeVO {
  id: number;
  cateName: string;
  parentId: number | null;          // 岗位节点 → 类别节点两级
  positionCode?: string;            // 岗位编码（顶层节点）
  materialCount: number;            // 已发布资料数
  children: MaterialCateTreeVO[];
}
interface MaterialVO {
  id: number;
  materialNo: string;               // MT+日期+流水
  title: string;
  cateId: number;
  materialType: MaterialType;
  fileUrl?: string;                 // 签名 URL（60 秒）
  linkUrl?: string;
  positionCodes: string[];
  version: number;
  status: MaterialStatus;
  uploaderUserId: number;
  uploaderName: string;
  updatedAt: string;
}
interface MaterialVersionItem {
  version: number;
  ossKey: string | null;            // 旧版本留档（TRN-M-R2）
  fileUrl?: string;                 // 60s 签名
  editorName: string;
  updatedAt: string;
}
interface WeeklyUpdateMetricsResp {
  weekStart: string;
  shouldUpdateCount: number;
  updatedCount: number;
  weeklyUpdateRate: number;          // BR-101 目标 = 100%
  unupdatedList: Array<{
    materialNo: string; title: string;
    lastUpdatedAt: string; ownerName: string;
  }>;
}

// 枚举类型（MaterialType 为全局权威枚举；MaterialStatus 为本域资料状态）
type MaterialStatus = 'DRAFT' | 'PUBLISHED' | 'OFFLINE';   // 草稿/已发布/已下架
// MaterialType = 'DOC' | 'VIDEO' | 'LINK' —— 引用全局规范第 4 章
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /train/material/cates`（分类树）+ `GET /train/material/list` + `GET /train/material/weekly-update-metrics`（周更率指标卡）；任一失败分区独立重试。普通学员（R5/R6/R7）进入页面默认定位本岗位树节点，且列表仅返回 `PUBLISHED` 资料（服务端过滤，TRN-M-R1）。

#### 4.2 核心操作流程
**A. 上传资料（R2 主责 / R1）**
1. [上传资料] → 抽屉：选分类（类别级，树级联选择）、标题、类型三选一；
2. 类型联动表单：DOC/VIDEO → FileUpload（OSS 直传，`businessScene: 'material'`，先取短时效凭证 ≤60s 再直传回执 ossKey）；LINK → 外链 URL 输入；
3. 关联岗位多选（必填非空）；[存草稿] 或 [发布]（ConfirmDialog 汇总：类型/岗位数/发布可见范围）→ `POST /train/material`；
4. 成功后刷新列表与树节点计数。

**B. 更新资料（新版本，TRN-M-R2）**
1. 已发布/已下架行 [编辑] → 抽屉预填当前版本内容 → 提交 `PUT /train/material/{id}` → `version` 自增，旧版本留档；
2. 详情抽屉"版本历史" Tab 列出全部历史版本（可预览、不可修改）。

**C. 下架资料（R1/R2）**
1. 行 [下架] → ConfirmDialog（warning）：提示"下架后学员不可见；若被进行中学习任务引用将提示不强删" → `DELETE /train/material/{id}` → 状态置 `OFFLINE`。

**D. 周更新率督办（BR-101）**
1. 指标卡"周更新率"低于 100% 时黄色高亮；[未更新清单] → 抽屉列出应更新未更新资料（编号/标题/负责人/最后更新时间），提供 [复制清单]（文本复制给负责人督办）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| cateId | TreeSelect（随左侧树点击联动） | 否 | 空 | 分类（选中后列表过滤） |
| title | Input | 否 | 空 | 资料标题模糊匹配 |
| materialType | Select | 否 | 空 | DOC/VIDEO/LINK |
| status | Select | 否 | 空 | 学员视图固定 PUBLISHED 不可改 |
| positionCode | Select | 否 | 空 | 岗位编码（R1/R2 可选） |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| materialNo | 资料编号 | 140 | — | 等宽字体（MT…） |
| title | 标题 | 自适应 | — | 行点击打开详情抽屉 |
| materialType | 类型 | 90 | — | 图标+文案：DOC 文档/VIDEO 视频/LINK 外链 |
| version | 版本 | 70 | ✓ 降序 | V{n} |
| positionCodes | 关联岗位 | 160 | — | 岗位编码 tag，>3 个显示"+N" |
| status | 状态 | 100 | — | tag：草稿(灰)/已发布(绿)/已下架(红) |
| uploaderName | 更新人 | 100 | — | — |
| updatedAt | 更新时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 170 | — | [详情][编辑][下架] 按角色/状态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 上传资料抽屉 | Drawer 640px | cateId 必选（类别级）；title 必填 ≤128 字；materialType 必选；DOC/VIDEO 时 ossKey 必填；LINK 时 linkUrl 必填 URL 格式；positionCodes 必填非空；publish 布尔切换 |
| 更新资料抽屉 | Drawer 640px | 同上传（预填）；提交提示"将生成新版本 V{n+1}，旧版本留档" |
| 资料详情抽屉 | Drawer 60% | 基础信息只读 + 版本历史列表（TRN-M-R2）+ 预览区（视频在线播放/文档在线预览，60s 签名 URL；LINK 直接外链跳转） |
| 未更新清单抽屉 | Drawer 60% | BR-101 督办清单；[复制清单] 导出文本 |
| 下架确认弹窗 | Modal 400px | ConfirmDialog warning 型；显示被引用中的任务数（若有） |

### 8. 错误处理
- 1101（分类不存在 / 资料不存在）：刷新分类树后重试；
- 1103（资料未发布对学员不可见）：提示并刷新列表（学员视图 TRN-M-R1 拦截）；
- 1001（参数校验失败）：表单项即时校验 + 提交时 ElMessage.error；
- 5005（OSS 上传失败）：FileUpload 组件内重试 3 次，仍失败提示"上传失败，请重试"；
- 401 静默跳 SSO；403 提示"无数据权限"（1008）。

### 9. BR 业务规则覆盖
- **BR-101（培训每周更新率 = 100%）**：顶部周更率指标卡 + 未更新清单抽屉为页面落点；周更率 <100% 黄色警示引导督办；
- TRN-M-R1（仅已发布资料对学员可见）：学员视图服务端过滤 + 状态筛选锁定 PUBLISHED；
- TRN-M-R2（更新生成新版本留档）：编辑抽屉提交提示 + 详情抽屉版本历史列表；
- TRN-M-R3（周更新率纳入统计）：指标卡数据源 weekly-update-metrics。

---

## P2. 学习任务管理（TRAIN-002）

### 1. 页面概述
- 路由路径：`/ims/train/task`
- 页面级别：一级菜单页（任务列表 + 创建抽屉 + 学习记录抽屉）
- 依赖模块：P1 资料库（资料多选）、AUTH 岗位字典（按岗位指派）、工作台待办（学习待办推送）、AUTH-002 入职事件（TRN-T-R3 自动指派）
- 权限矩阵引用（PRD 4.2 TRAIN-002）：R1 R/W/D（全量）、R2 R/W（全量）、R4 R/W（本部门）、R5/R6/R7 W（本人完成）、R10 W（被指派）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 任务名称 | 状态 | 确认方式 | [查询][重置]      |
|                                              [创建学习任务]      |
+------------------------------------------------------------------+
| 任务列表表格:                                                     |
| 编号|任务名称|资料数|指派范围|应完成|已完成|完成率|确认方式|截止时间|状态|操作|
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
创建任务抽屉(720px): 任务名称* | 资料多选*(已发布资料) |
  指派范围*(按人/按岗位) |
  按人: 人员多选 | 按岗位: 岗位多选(展开预览目标人数) |
  截止时间* | 确认方式*(学时达标/自测问卷) |
  问卷配置(DURATION 无/QUIZ: 题目+选项+答案+及格分)
学习记录抽屉(70%): 按任务展开被指派人明细
  用户|部门|进度|单资料进度|确认状态|得分|开始|完成|逾期
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface TrainTaskPageReq {
  pageNo: number; pageSize: number;
  taskName?: string;
  status?: TrainTaskStatus;
  confirmType?: ConfirmType;
}
interface TrainTaskCreateReq {
  taskName: string;                 // 必填 ≤128 字
  materialIds: number[];            // 必填非空（仅已发布资料）
  assignScope: AssignScope;         // BY_USER / BY_POSITION
  assignTargetUserIds?: number[];   // BY_USER 必填
  assignTargetPositionCodes?: string[];  // BY_POSITION 必填（展开预览目标人数）
  deadline: string;                 // 必填 ISO 8601，不得早于当前（1102）
  confirmType: ConfirmType;         // DURATION / QUIZ
  quiz?: QuizQuestion[];            // QUIZ 必填
  passScore?: number;               // QUIZ 必填
  clientToken: string;              // 幂等
}
interface QuizQuestion {
  question: string;                 // 必填 ≤256 字
  options: string[];                // 必填 ≥2 项
  answerIndex: number;              // 必填
}
interface TrainTaskEditReq extends TrainTaskCreateReq {
  id: number;                       // 仅 IN_PROGRESS 且截止前可编辑
}
interface TrainProgressReportReq {
  materialId: number;
  watchedSeconds?: number;          // 视频累计有效观看秒（快进不计，心跳区间去重）
  currentPage?: number;             // 文档当前页
  totalPages?: number;
  heartbeatAt: string;              // 前端 15 秒一次心跳
}
interface TrainConfirmReq {
  answers?: Array<{ questionIndex: number; answerIndex: number }>;  // QUIZ 作答
}
interface TrainRecordPageReq {
  pageNo: number; pageSize: number;
  taskId?: number; userId?: number; deptId?: number;
  confirmStatus?: ConfirmStatus;
  overdue?: boolean;
}

// 响应类型
interface TrainTaskVO {
  id: number;
  taskNo: string;                   // TT+日期+流水
  taskName: string;
  materialIds: number[];
  assignScope: AssignScope;
  assignedCount: number;            // 展开后应完成人次
  deadline: string;
  confirmType: ConfirmType;
  status: TrainTaskStatus;
  createdAt: string;
}
interface TrainTaskPageItem extends TrainTaskVO {
  finishRate: number;               // 已完成人次/应完成人次（BR-102）
}
interface TrainProgressVO {
  taskId: number; userId: number; materialId: number;
  progress: number;                 // 0~100
  materialProgress: Record<number, number>;   // materialId → 百分比
  confirmStatus: ConfirmStatus;
  startedAt: string; finishedAt?: string;
}
interface TrainRecordPageItem extends TrainProgressVO {
  taskNo: string; taskName: string;
  userName: string; deptName: string;
  isOverdue: boolean;
}

// 枚举类型
type AssignScope = 'BY_USER' | 'BY_POSITION';                     // 按人/按岗位
type ConfirmType = 'DURATION' | 'QUIZ';                           // 学时达标/自测问卷
type ConfirmStatus = 'NOT_CONFIRMED' | 'CONFIRMED';
// TrainTaskStatus = 'IN_PROGRESS' | 'FINISHED' —— 全局权威枚举（任务粒度）
// TrainStatus —— 全局权威枚举（学习记录粒度，P4 使用）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /train/task/list`（默认状态 IN_PROGRESS，finishRate 列降序）；失败重试。R4 本部门、被指派人仅见相关任务（服务端过滤）。

#### 4.2 核心操作流程
**A. 创建学习任务（R2 主责 / R1）**
1. [创建学习任务] → 抽屉：任务名称、资料多选（仅已发布资料弹窗选择器，显示类型/版本/岗位）、指派范围切换；
2. 按人 → 人员多选（UserSelect · `system_users.id`）；按岗位 → **PositionSelect**（`positionCode` · AUTH-003/`dict_position`）并预览"预计指派 N 人"；
3. 截止时间（DatePick 防误选过去时间，提交校验 1102）、确认方式切换：DURATION（学时达标，无需配置）或 QUIZ（问卷题目编辑器：动态增删题/选项、设定答案与及格分）；
4. QUIZ 模式下工具栏 **[AI 生成试卷]** 打开 TRAIN-004 向导；采纳后填充 `quizEd`，可再手工改题；
5. 提交（ConfirmDialog 汇总：资料数/目标人数/截止/确认方式；clientToken 幂等）→ `POST /train/task` → 目标人工作台收到学习待办。

**B. 入职自动指派联动（TRN-T-R3）**
- 无页面操作：钉钉入职事件（V1 AUTH-002 user_add）自动生成岗位学习包任务（截止 = 入职日+14 天）；任务列表中此类任务行显示"自动指派"灰色角标，标注来源岗位编码。

**C. 编辑 / 删除**
1. [编辑]：仅 `IN_PROGRESS` 且截止前可编辑（已产生的学习记录不回滚）；截止后按钮置灰 + tooltip"已过截止时间"；
2. [删除]（R1）：ConfirmDialog danger 型，提示"逻辑删除；已有完成记录的统计口径按删除时点冻结"。

**D. 学习记录查看**
1. 行 [学习记录] → 抽屉（70%）：`GET /train/task/records?taskId=` 展开被指派人明细；
2. 支持按确认状态/逾期筛选；逾期行红标 + overdueDays 列；与 P3 逾期督办共用数据源。

**E. 提醒与督办（TRN-T-R2）**
- 截止前 1 天未完成 → 系统推送待办提醒（无页面操作，列表中"即将到期"行黄色底纹提示）；
- 逾期后进入 P3 逾期未完成清单导出督办，仍可补学补确认（计入分母）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| taskName | Input | 否 | 空 | 任务名称模糊匹配 |
| status | Select | 否 | IN_PROGRESS | 进行中/已结束 |
| confirmType | Select | 否 | 空 | 学时达标/自测问卷 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| taskNo | 任务编号 | 140 | — | 等宽字体（TT…）；自动指派行叠加灰色角标 |
| taskName | 任务名称 | 自适应 | — | 行点击展开学习记录抽屉 |
| materialCount | 资料数 | 80 | — | 数字，悬浮显示资料名列表 |
| assignScope | 指派范围 | 100 | — | 按人/按岗位 |
| assignedCount | 应完成 | 90 | — | 人次 |
| finishedCount | 已完成 | 90 | — | 人次 |
| finishRate | 完成率 | 110 | ✓ 降序 | 百分比进度条；>90% 绿、70~90% 黄、<70% 红（BR-102 视觉阈值） |
| confirmType | 确认方式 | 100 | — | 学时达标/问卷 |
| deadline | 截止时间 | 150 | ✓ | yyyy-MM-dd HH:mm；<24h 黄标、已过红标 |
| status | 状态 | 90 | — | tag：进行中(蓝)/已结束(灰) |
| actions | 操作 | 180 | — | [学习记录][编辑][删除] 按状态/权限 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 创建任务抽屉 | Drawer 720px | taskName 必填 ≤128；materialIds 必填非空（仅已发布）；assignScope 必选且与目标列表匹配（1001 校验）；deadline 必填且晚于当前；QUIZ 时 quiz 题目 ≥1、每题选项 ≥2、passScore 必填；clientToken 防重 |
| 编辑任务抽屉 | Drawer 720px | 同创建（预填）；仅 IN_PROGRESS 且未过截止 |
| 学习记录抽屉 | Drawer 70% | 记录表格：用户/部门/进度/确认状态/得分/逾期红标；内部筛选条（confirmStatus/overdue） |
| 资料选择弹窗 | Modal 640px | 已发布资料分页多选；列：编号/标题/类型/版本/关联岗位 |
| **AI 生成试卷向导** | Drawer 720px · **≥4 步** | **TRAIN-004**（`POST …/quiz/ai-generate` 同步 · ADR-IMS-004）：① 勾选资料（`materialIds` 仅 PUBLISHED）→ ② 参数（题量 5~30、单选+判断、难度）→ ③ 生成中（≤90s）→ ④ 预览 **[采纳到问卷编辑器]**；失败 1112/1113 |
| 删除确认弹窗 | Modal 400px | danger 型；统计口径冻结提示 |

### 8. 错误处理
- 1102（截止时间早于当前）：DatePick 拦截 + 提交时 ElMessage.error；
- 1101（资料不存在或未发布）：刷新资料选择器；
- 1001（assignScope 与目标列表不匹配）：表单联动校验（切范围清空目标并提示）；
- 1105（非被指派人无权上报）：P4 学习中心提交时提示"仅被指派人可上报"；
- 1104（学时未达标/问卷未配置）：确认按钮置灰原因 tooltip；
- 网络超时：创建/确认携带 clientToken 防重；列表静默重试 3 次。

### 9. BR 业务规则覆盖
- **BR-102（学习完成率 > 90%，含逾期分母）**：任务列表 finishRate 列（含三色阈值）为实时落点；P3 看板为汇总落点；
- TRN-T-R1（视频按实际观看时长计进度，快进不计）：P4 心跳上报（服务端区间去重），本页记录抽屉 progress/materialProgress 展示；
- TRN-T-R2（截止前 1 天提醒，逾期督办）：列表"即将到期"黄底提示 + 逾期红标 + P3 逾期清单导出闭环；
- TRN-T-R3（入职自动指派，入职日+14 天）：任务列表"自动指派"角标与来源岗位标注。

---

## P3. 培训统计看板（TRAIN-003）

### 1. 页面概述
- 路由路径：`/ims/train/stat`
- 页面级别：一级菜单页，四 Tab 看板（完成率总览 / 部门统计 / 时长排行 / 逾期督办）+ 资料热度侧卡
- 依赖模块：`ims_train_stat_daily`（TRN-S-R1 每日凌晨汇总，V2-A1 Redisson 分布式锁集群化调度）、ALERT 预警中心（TRN-S-R3 低完成率推送联动）
- 权限矩阵引用（PRD 4.2 TRAIN-003）：R1 R（全量）、R2 R（全量）、R9 R（全量）、R4 R（本部门）、R5/R6/R7 R（本人）；无写操作（系统自动统计）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 日期范围: [近7天|近30天|自定义] (QueryBar 一行)                    |
+------------------------------------------------------------------+
| Tab: [完成率总览] [部门统计] [时长排行] [逾期督办]                 |
+------------------------------------------------------------------+
| 完成率总览: 指标卡: 总完成率 xx% (BR-102 目标>90%)                 |
|   按任务 Top10 柱状图 | 按部门完成率表 | 按个人完成率表(分页)       |
+------------------------------------------------------------------+
| 部门统计: 日汇总表(统计日期|部门|应完成|已完成|完成率|人均时长)     |
|   + 部门完成率趋势折线图                                          |
+------------------------------------------------------------------+
| 时长排行: 维度切换(部门/个人) | TopN 选择 | 排行榜表格             |
+------------------------------------------------------------------+
| 逾期督办: 任务|部门筛选 + 逾期未完成清单表格 + [导出 Excel]         |
+------------------------------------------------------------------+
| 资料热度侧卡: 学习人次 Top10(编号|标题|类型|人次|人均时长)          |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface TrainFinishRateReq {
  dateRange?: [string, string];     // 默认近 30 天
}
interface TrainDeptStatReq {
  statDateRange?: [string, string];
}
interface TrainRankReq {
  dimension: RankDimension;         // DEPT / PERSON
  dateRange?: [string, string];
  topN?: number;                    // 默认 10
}
interface TrainOverdueReq {
  pageNo: number; pageSize: number;
  taskId?: number; deptId?: number;
}

// 响应类型
interface TrainFinishRateResp {
  totalFinishRate: number;          // BR-102 总完成率
  byTask: Array<{
    taskNo: string; taskName: string;
    assignedCount: number; finishedCount: number; finishRate: number;
  }>;
  byDept: Array<{
    deptId: number; deptName: string;
    assignedCount: number; finishedCount: number; finishRate: number;
  }>;
  byPerson: Array<{                // 分页交互在前端切页（接口全量返回）
    userId: number; userName: string; deptName: string;
    assignedCount: number; finishedCount: number; finishRate: number;
  }>;
}
interface TrainDeptStatItem {
  statDate: string; deptId: number; deptName: string;
  assignedCount: number; finishedCount: number;
  finishRate: number; avgDurationMinutes: number;
}
interface TrainRankItem {
  rank: number;
  deptName?: string; userName?: string; userId?: number;
  totalDurationMinutes: number; finishRate: number;
}
interface TrainOverdueItem {
  taskId: number; taskNo: string; taskName: string;
  userId: number; userName: string; deptName: string;
  deadline: string; overdueDays: number; progress: number;
}
interface MaterialHeatItem {
  materialId: number; materialNo: string; title: string;
  materialType: MaterialType;
  studyCount: number; avgDurationMinutes: number;
}

// 枚举类型
type RankDimension = 'DEPT' | 'PERSON';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /train/stat/finish-rate` + `GET /train/stat/material-heat`（默认近 30 天）；Tab 切换懒加载对应接口（部门统计/排行/逾期督办）；失败分区重试。数据范围按角色服务端过滤（R4 本部门、R5/R6/R7 本人、R9 全量）。

#### 4.2 核心操作流程
**A. 完成率总览（BR-102）**
1. 指标卡展示总完成率（目标 >90%，达标绿/未达标红）；下方三视图：按任务 Top10 柱状图（finishRate 排序）、按部门完成率表（低于 85% 黄标）、按个人完成率表（前端分页）；
2. 日期范围切换（近 7 天/近 30 天/自定义）→ 重新请求。

**B. 部门统计（TRN-S-R3 联动）**
1. 日汇总表（statDate 降序）+ 部门完成率趋势折线图（ECharts）；
2. 部门完成率连续 2 周低于 85% 的部门行红色标记 + "已推送负责人"标签（预警联动展示，推送动作由 ALERT 引擎执行）。

**C. 时长排行**
1. 维度切换（部门/个人）+ TopN（10/20/50）→ `GET /train/stat/rank`；
2. 排行榜表格：名次/名称/总时长（分钟，格式"X 小时 Y 分钟"）/完成率。

**D. 逾期督办（TRN-T-R2）**
1. 任务/部门筛选 + 逾期未完成清单表格（overdueDays 降序，红标）；
2. [导出 Excel] → 异步导出（OSS 回执链接下载，提示"导出任务已提交"）。

**E. 资料热度侧卡**
- 学习人次 Top10（点击行跳 P1 资料详情抽屉），供 R2 优化资料库内容参考。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| dateRange | DateRangePicker | 否 | 近 30 天 | 总览/热度共用；quickRanges 近7天/近30天/本月 |
| statDateRange | DateRangePicker | 否 | 近 30 天 | 部门统计 Tab |
| dimension | RadioGroup | 是 | DEPT | 时长排行维度 |
| topN | Select | 否 | 10 | 10/20/50 |
| taskId | Select | 否 | 空 | 逾期督办任务筛选 |
| deptId | TreeSelect | 否 | 空 | 逾期督办部门筛选 |

### 6. 表格列定义

**完成率总览-按部门表 / 按个人表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| deptName / userName | 部门/姓名 | 140 | — | 个人表附部门列 |
| assignedCount | 应完成 | 90 | — | 人次 |
| finishedCount | 已完成 | 90 | — | 人次 |
| finishRate | 完成率 | 120 | ✓ 降序 | 进度条 + 三色阈值（>90 绿/70~90 黄/<70 红） |

**部门统计表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| statDate | 统计日期 | 110 | ✓ 降序 | yyyy-MM-dd |
| deptName | 部门 | 140 | — | 连续 2 周 <85% 红标（TRN-S-R3） |
| assignedCount / finishedCount | 应完成/已完成 | 170 | — | 人次 |
| finishRate | 完成率 | 110 | — | 进度条 |
| avgDurationMinutes | 人均时长 | 110 | — | "X 小时 Y 分钟" |

**逾期督办表**

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| taskNo | 任务编号 | 140 | — | 等宽字体 |
| taskName | 任务名称 | 自适应 | — | — |
| userName | 学员 | 100 | — | — |
| deptName | 部门 | 120 | — | — |
| deadline | 截止时间 | 150 | — | yyyy-MM-dd HH:mm |
| overdueDays | 逾期天数 | 90 | ✓ 降序 | 红色数字 |
| progress | 进度 | 110 | — | 进度条 |
| actions | 操作 | 100 | — | [去督办]（跳 P2 学习记录抽屉） |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 部门明细抽屉 | Drawer 60% | 点击部门行展开：该部门日汇总明细 + 趋势小图（TRN-S-R3 预警标记明细） |
| 导出进度提示 | ElMessage | 异步导出提交提示 + 完成通知（OSS 链接） |

> 本页以看板为主，交互密度低；部门明细复用 P2 学习记录抽屉跳转。

### 8. 错误处理
- 日期范围非法（起 > 止）：DateRangePicker 拦截；
- R4/R5/R6/R7 越权查全量：服务端过滤（1008 无数据权限提示）；
- 汇总任务延迟（V2-A1 定时调度失败 5006）：看板顶部黄条"统计数据截至 X 日，昨日汇总任务延迟，已通知管理员"；
- 图表渲染失败（数据空）：空态占位图（"暂无统计数据"）。

### 9. BR 业务规则覆盖
- **BR-102（学习完成率 > 90%）**：完成率总览 Tab 指标卡 + 三维分布（任务/部门/人）为 BR-102 的看板落点，含逾期分母口径注释；
- TRN-S-R1（每日凌晨汇总，V2-A1 集群化）：部门统计 Tab 数据源说明（`ims_train_stat_daily`），页面顶部展示数据截至日期；
- TRN-S-R2（完成率口径含逾期）：逾期行/逾期天数字段确保分母含逾期；
- TRN-S-R3（部门连续 2 周低于 85% 推送负责人）：部门表红标 + "已推送负责人"标签（联动 ALERT）；
- TRN-T-R2（逾期督办导出）：逾期督办 Tab + Excel 异步导出。

---

## P4. 学习中心（TRAIN-002 执行态，H5 同构）

### 1. 页面概述
- 路由路径：`/ims/train/study/{taskId}`（Web 二级页 + 钉钉 H5 同构，H5 路由 `/app-api` 免登后同页）
- 页面级别：二级页面（任务资料清单 + 学习播放器 + 完成确认）
- 依赖模块：工作台学习待办（点击进入）、P1 资料预览（OSS 签名 URL 60s）、P2 学习记录
- 权限矩阵引用：被指派人本人（R5/R6/R7/R10）；1105 拦截非被指派人

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 任务头: 任务名 | 截止时间(倒计时) | 确认方式 | 总进度 xx%           |
+------------------------------------------------------------------+
| +------------------------+ +---------------------------------+  |
| | 资料清单(220px)        | | 学习区(自适应)                    |  |
| | 资料1 [进度 60%]       | | 视频: 播放器(时长累计,快进不计)    |  |
| | 资料2 [✓ 完成]        | | 文档: 翻页阅读器                  |  |
| | 资料3 [未开始]         | | 外链: [打开外链] + 学习时长计时    |  |
| | ...                    | +---------------------------------+  |
| +------------------------+ 底部: [完成确认](DURATION 达标可点)     |
|                          | QUIZ: 问卷作答(题目/选项/提交判分)     |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型（见 P2: TrainProgressReportReq / TrainConfirmReq）
// 响应类型
interface StudyTaskResp {
  taskId: number; taskNo: string; taskName: string;
  deadline: string;
  confirmType: ConfirmType;
  quiz?: QuizQuestion[];            // 不含 answerIndex（判分服务端）
  passScore?: number;
  materials: Array<{
    materialId: number;
    title: string;
    materialType: MaterialType;
    fileUrl?: string;               // 60s 签名，进入学习区时按需刷新
    linkUrl?: string;
    totalPages?: number;
    requiredMinutes?: number;       // DURATION 达标学时（分钟）
  }>;
  progress: TrainProgressVO;        // 当前人进度（断点续学）
}
interface QuizGradeResp {
  confirmStatus: ConfirmStatus;
  confirmScore?: number;
  isPassed: boolean;
  finishedAt: string;
}

// 枚举（同 P2；TrainStatus 学习记录粒度用于待办/结果态展示）
```

### 4. 交互流程

#### 4.1 页面加载
1. 从工作台学习待办或 P2 任务进入 → `GET /train/task/{id}`（StudyTaskResp，含断点续学进度 materialProgress）；
2. 左侧资料清单按进度着色（完成绿/进行中蓝/未开始灰）；默认定位第一个未完成资料；
3. 视频播放器 seek 至上次观看位置；文档阅读器翻至上次页码。

#### 4.2 核心操作流程
**A. 视频学习（TRN-T-R1）**
1. 播放 → 前端每 15 秒心跳 `PUT /train/task/{id}/progress`（watchedSeconds 累计有效秒数）；
2. 拖拽快进时段不计时长（服务端按心跳区间去重，播放器端同时禁用倍速刷时长提示）；
3. 达到 requiredMinutes → 资料标记完成。

**B. 文档学习**
1. 翻页 → 心跳上报 currentPage/totalPages；翻完全页视为完成。

**C. 外链学习**
1. [打开外链]（新窗口）→ 页内计时器累计停留时长心跳上报。

**D. 完成确认**
1. DURATION 模式：全部资料完成后 [完成确认] 按钮激活（未达标置灰 + tooltip 差多少学时）→ `POST /train/task/{id}/confirm`；
2. QUIZ 模式：问卷作答（全部题目必答）→ 提交 → 服务端判分返回 QuizGradeResp：isPassed → 完成态绿色庆祝反馈；未达 passScore → 提示得分与及格分，可重答（记录最新成绩）。

**E. 超期补救**
- 已逾期任务仍可进入学习与确认（标记 isOverdue，计入分母），页面头部红色横幅"本任务已逾期 N 天，补学仍计入完成率统计"。

### 5. 查询条件表
无（学习执行页，无查询）。

### 6. 表格列定义
无（资料清单为侧栏列表，非数据表格）。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 问卷作答区 | 内嵌表单（非弹窗） | 每题必答（单选）；提交前 ConfirmDialog"提交后将判分，未及格可重答" |
| 完成确认弹窗 | Modal 360px | DURATION：确认达成学时；QUIZ：展示得分/及格分/通过与否 |

### 8. 错误处理
- 1105（非被指派人）：提示"仅被指派人可学习本任务"并跳回工作台；
- 心跳上报失败：本地缓存进度，网络恢复后补报（幂等按 heartbeatAt 区间）；
- 1104（学时未达标）：按钮置灰 + 差距提示；
- 60s 签名 URL 过期：进入学习区/播放器报 403 时静默刷新 URL 重试 1 次；
- H5 弱网：页面顶部离线提示条，恢复后自动续传。

### 9. BR 业务规则覆盖
- **BR-102（学习完成率 > 90%）**：本页为分子（完成确认）的唯一产生入口，确认后 finishRate 实时联动 P2/P3；
- TRN-T-R1（视频实际观看时长，快进不计）：15 秒心跳 + 服务端区间去重，双端防刷；
- TRN-T-R2（逾期仍可补学）：超期横幅 + isOverdue 标记（分母含逾期）；
- TRN-T-R3（入职自动指派）：新员工从工作台待办直达本页，断点续学降低流失。

---

## 附录 A. 模块级约定

1. **枚举引用**：全模块复用全局权威枚举 `MaterialType`、`TrainTaskStatus`（任务粒度）、`TrainStatus`（学习记录粒度）；本域内联枚举 `MaterialStatus`/`AssignScope`/`ConfirmType`/`ConfirmStatus`/`RankDimension` 仅模块内使用，值域与 TRAIN-API 契约一致；
2. **错误码段**：1101~1110 TRAIN 段（1101 分类/资料不存在、1102 截止时间非法、1103 资料不可见、1104 确认条件未满足、1105 非被指派人）；
3. **权限过滤**：R4 本部门、R5/R6/R7 本岗位/本人、R10 被指派/指派课程 —— 全部服务端过滤，前端仅隐藏入口不承担鉴权；
4. **与 ALERT 联动**：TRN-S-R3 部门低完成率推送、BR-118 类成本预警由预警引擎执行，本模块仅展示"已推送"标记；
5. **周次表述**：本模块交付窗口为第 15~18 周（V2.1 批次），TRN-S-R1 汇总任务纳入 V2-A1 集群化调度（Redisson 分布式锁防重复执行）。

## 附录 B. BR/TRN 规则 ↔ 页面落点总表

| 规则 | 约束摘要 | 页面落点 |
|------|----------|----------|
| BR-101 | 培训每周更新率 = 100% | P1 周更率指标卡 + 未更新清单抽屉 |
| BR-102 | 学习完成率 > 90%（含逾期分母） | P2 finishRate 列 / P3 完成率总览 / P4 完成确认入口 |
| TRN-M-R1 | 仅已发布资料对学员可见 | P1 学员视图服务端过滤 |
| TRN-M-R2 | 更新生成新版本留档 | P1 编辑抽屉 + 版本历史 Tab |
| TRN-M-R3 | 周更新率纳入统计 | P1 weekly-update-metrics |
| TRN-T-R1 | 视频实际观看时长，快进不计 | P4 15 秒心跳 + 区间去重 |
| TRN-T-R2 | 截止前 1 天提醒，逾期督办 | P2 即将到期黄底/逾期红标 + P3 逾期督办导出 |
| TRN-T-R3 | 入职自动指派（+14 天） | P2 自动指派角标 / P4 新人待办直达 |
| TRN-S-R1 | 每日凌晨汇总（V2-A1） | P3 部门统计数据截至标注 |
| TRN-S-R2 | 完成率口径含逾期 | P3/P4 逾期标记与口径注释 |
| TRN-S-R3 | 部门连续 2 周 <85% 推送负责人 | P3 部门表红标 + 已推送标签 |

（全文完）
