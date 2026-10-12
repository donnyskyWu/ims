# PERF - 绩效考试 页面规格（V2.3 批次，05 模块）

> **模块范围**：PERF-001 绩效指标配置 / PERF-002 绩效自动计算 / PERF-003 在线考试 / PERF-004 排名与预警。
> **走查 #12 信息架构**：用户主路径「考核方案 → 执行考核 → 考核结果」见《PERF-绩效考核-页面规格.md》；本文件 P1/P2 对应工程化 **指标配置 / 批量计算核准** 页，P3 为 **在线考试**（菜单第四叶 `perfExam`）。
> **权威依据**：《IMS第二期PRD-V2.md》5.20~5.23、6.5 绩效月度闭环；《PERF-绩效考试-API契约.md》（28 接口，1151~1164 错误码段）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**（6 页）：P1 绩效指标配置（Web）｜P2 绩效计算与核准（Web）｜P3 在线考试管理（Web）｜P4 考试作答页（H5 同构）｜P5 排名与预警看板（Web）｜P6 我的绩效（H5/工作台卡片）。
> **模块核心口径**：**快照不可变**——绩效结果按周期生成不可变快照，重算生成新版本、旧快照审计保留（V2-B4）；**竞品分析提交率指标 V2 一律禁用**（BR-110，enableNote 锁定说明，V3 04 竞品上线后启用）；综合得分 = Σ(指标得分 × 权重)（BR-117，DECIMAL(6,2)）；得分 <60 触发预警推送本人+直属上级+HR。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase。
- 枚举以《全局开发规范.md》第 4 章为唯一权威源。本模块引用：`ExamStatus`、`PerfResultStatus`、`PerfGradeLevel`、`EnableStatus`（指标启停用 ENABLED/DISABLED）、`PaperStatus`（DRAFT/PUBLISHED）。
- **注意枚举粒度区分（全局规范第 4 章注释 5）**：`PerfGradeLevel`（EXCELLENT/QUALIFIED/IMPROVE，85/60 分数分档）与 `PerfGrade`（S~D 绩效等级）是两个不同枚举，本模块只用 `PerfGradeLevel`，**禁止混用**。
- 得分/分数：DECIMAL(6,2) 两位小数，不带 ¥ 前缀（非金额，全局仅金额字段加 ¥）。
- 权重：DECIMAL(5,2)，显示为 `xx%`（0~100）；岗位权重合计必须 = 100（错误码 1154）。
- 权限矩阵引用 PRD 4.2 + 各功能点 5.x.5：R1 超管（全量+删除）、R2 人事行政（题库/阅卷/预警处置主责）、R4 运营总监（指标配置主责、核准发布）、R8 监考（阅卷/监考成绩）、R9 财务（脱敏视图）、员工本人（发布后可见本人）。
- R9 脱敏口径：分数保留，指标明细中涉及金额的原始值（如 FIN 成本指标 metricValue）服务端返回 `"***"`。
- StatusTag 语义色：CALCULATING → processing 蓝；PENDING_APPROVE/PENDING_MANUAL → warning 橙；PUBLISHED → success 绿；IMPROVE/已预警 → error 红；EXCELLENT → success 绿；QUALIFIED → default 灰。

---

## P1 绩效指标配置（PERF-001）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/perf/metric`（菜单：绩效考试 → 指标配置） |
| 页面级别 | 二级（模块主页面，V2.3 批次第 23 周启用） |
| 前置依赖 | 02/03/09/10/11/14 模块跑满 1 个月观察期（P2 计算基线前置；P1 本身第 23 周即可配置） |
| 权限 | 查看：R1/R3（财务类）/R4；新增/编辑：R4（主责）/R1/R3（财务类）；删除（禁用）：R4/R1 |
| 用户 | HR（R2 只读）/ 运营总监（R4 主责）/ 超管 R1 / 财务 R3（财务类指标） |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 指标配置   [覆盖率卡: 自动取数覆盖率 86.4% ▲达标(>80%)  自动 19/启用 22] │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [指标名称输入框][取数来源 Select:全部/自动/手工/考试]    │
│                [状态 Select:全部/启用/禁用] [搜索][重置]    [+ 创建指标] │
├──────────────────────────────────────────────────────────────────────────┤
│ 指标表格                                                     共 28 条      │
│ ┌────┬──────────────┬────────┬───────────────┬──────┬──────┬────────┐   │
│ │编码│ 指标名称      │ 取数来源│ 取数映射       │ 权重 │ 状态 │ 操作    │   │
│ ├────┼──────────────┼────────┼───────────────┼──────┼──────┼────────┤   │
│ │TRN_│ 培训完成率    │ 自动   │ TRAIN/finish_ │ 15%  │启用  │编辑 试取│   │
│ │FR  │              │        │rate/月        │      │      │数 禁用  │   │
│ │MEE_│ 日报按时提交率│ 自动   │ MEET/on_time_ │ 10%  │启用  │…       │   │
│ │…   │              │        │rate/月        │      │      │        │   │
│ │COMP│ 竞品分析提交率│ 手工   │ —             │  —   │🔒禁用│编辑(只读)│   │
│ │_SB │              │        │               │      │注¹   │        │   │
│ └────┴──────────────┴────────┴───────────────┴──────┴──────┴────────┘   │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ 底部操作区:  [岗位指标集绑定]                                             │
└──────────────────────────────────────────────────────────────────────────┘
注¹: enableNote = "待 V3 竞品管理（04）上线后启用（BR-110/BR-206）"
     COMPETE_SUBMIT_RATE 行 Tag 为禁用锁图标 + Tooltip 显示 enableNote
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举，契约一致） =====
/** 指标取数来源（契约内联） */
type PerfDataSource = 'AUTO' | 'MANUAL' | 'EXAM';

// ===== 请求 =====
interface PerfMetricQueryReq extends PageParam {
  metricName?: string;
  dataSource?: PerfDataSource;
  status?: EnableStatus;   // 'ENABLED' | 'DISABLED'
}

interface PerfMetricSaveReq {
  metricCode: string;                    // 如 TRAIN_FINISH_RATE
  metricName: string;
  dataSource: PerfDataSource;
  sourceConfig?: {
    /** FIN 类指标在 V2.3 上线时置 DISABLED 锁态（FIN 模块已移 V3），随 11 财务上线（V3 第 33 周后）解禁（复用 BR-110 锁定机制） */
    module: 'TRAIN' | 'MEET' | 'REPORT' | 'LIVE' | 'FIN' | 'FLOW';
    metricExpression: string;            // 如 'finish_rate'
    periodType: 'MONTHLY';
  };                                     // AUTO 指标必填
  weight: number;                        // DECIMAL(5,2)
  scoreRule: {
    ruleType: 'SEGMENT' | 'LINEAR';
    segments?: Array<{ minValue: number; maxValue: number | null; score: number }>;
    linear?: { minMetric: number; maxMetric: number; minScore: number; maxScore: number };
  };
  status?: EnableStatus;
}

interface PerfPositionBindReq {
  positionCode: string;
  metricBindings: Array<{ metricId: number; weightOverride?: number }>;
}

interface PerfTestFetchReq {
  metricId: number;
  testPeriod: string;                    // yyyy-MM
}

// ===== 响应 =====
interface PerfMetricVO extends PerfMetricSaveReq {
  id: number;
  /** 竞品指标禁用说明（BR-110） */
  enableNote?: string;
  version: number;
}

interface PerfCoverageVO {
  enabledMetricCount: number;
  autoMetricCount: number;
  autoCoverageRate: number;              // BR-105 目标 > 80%
  manualMetrics: Array<{ metricCode: string; metricName: string }>;
}

interface PerfTestFetchVO {
  fetchable: boolean;
  sampleValue?: number;
  errorReason?: string;
  elapsedMs: number;
}
```

### 4. 交互流程

**页面加载**：
1. 并行请求 `GET /admin-api/ims/perf/metric/list`（默认分页）+ `GET /admin-api/ims/perf/metric/auto-coverage`（覆盖率卡）。
2. 覆盖率卡：`autoCoverageRate` > 80% 显示绿色 ✓ "达标（BR-105 >80%）"；≤ 80% 橙色警示，点击展开 `manualMetrics` 清单（"以下启用指标未自动取数"）。
3. `COMPETE_SUBMIT_RATE` 行特殊渲染：状态 Tag 带锁图标，Tooltip 显示 enableNote；操作列仅"查看"（进入抽屉只读态），无禁用/启用入口（PER-M-R1/BR-110）。

**核心操作**：
- **创建指标**（R4/R1/R3 财务类）：点 [+ 创建指标] → 指标编辑抽屉（见 §7.1）。
- **编辑指标**：行操作"编辑" → 抽屉回填；保存后 `version` 自增（指标口径变更走版本，历史周期按旧版本追溯，PER-M-R4——保存成功 toast 提示"已生成新版本 v{n}，历史周期不受影响"）。
- **试取数**（R4/R1/R3）：行操作"试取数" → 抽屉内或独立小弹窗（见 §7.3）。
- **禁用**（R4/R1）：行操作"禁用" → ConfirmDialog "禁用后该指标不参与后续月度计算（PER-M-R1），确认？" → `DELETE /perf/metric/{id}`；对 `COMPETE_SUBMIT_RATE` 调用返回 1153 → toast 显示契约错误信息。
- **岗位指标集绑定**（R4/R1）：底部按钮 → 岗位绑定抽屉（见 §7.2）；保存时服务端校验权重合计 = 100，返回 1154 → 表单区红字提示"该岗位指标集权重合计 96%，须 = 100%"。

### 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| metricName | Input | string | 指标名称模糊匹配 |
| dataSource | Select | PerfDataSource | 全部（默认）/自动/手工/考试 |
| status | Select | EnableStatus | 全部（默认）/启用/禁用 |

QueryBar 单行紧凑布局，"搜索/重置"右置；+ 创建按钮位于 QueryBar 右端（R4/R1/R3 可见）。

### 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 指标编码 | metricCode | code 样式等宽字体 |
| 指标名称 | metricName | 文本 |
| 取数来源 | dataSource | Tag：AUTO=蓝"系统自动" / MANUAL=橙"手工录入" / EXAM=紫"考试成绩" |
| 取数映射 | sourceConfig | `TRAIN · finish_rate · 月`（MANUAL/EXAM 显示 "—"） |
| 权重 | weight | `15%` 右对齐 |
| 得分规则 | scoreRule | 概要文本："分段 3 段" / "线性 0→100" |
| 状态 | status | StatusTag；ENABLED 绿 / DISABLED 灰；COMPETE_SUBMIT_RATE 附锁图标 + Tooltip enableNote |
| 版本 | version | v1、v2… |
| 操作 | — | 编辑 / 试取数 / 禁用（按权限渲染；COMPETE 行仅"查看"） |

### 7. 抽屉/弹窗规格

### 7.1 指标编辑抽屉（Drawer，右滑 720px，含创建/编辑/查看三态）

- **布局**：Descriptions 式表单，分三组：
  1. **基本信息**：指标编码（创建可编辑/编辑只读）、指标名称、取数来源 Select、状态 Switch（COMPETE_SUBMIT_RATE 进入即只读态）。
  2. **取数映射**（dataSource = AUTO 时显示）：模块 Select（TRAIN/MEET/REPORT/LIVE/FIN/FLOW，FIN 项附锁态说明——FIN 类指标在 V2.3 上线时置 DISABLED 锁态（FIN 模块已移 V3），随 11 财务上线（V3 第 33 周后）解禁（复用 BR-110 锁定机制））、指标表达式 Input（占位 `finish_rate`）、周期固定 MONTHLY 只读；来源切 MANUAL/EXAM 时整组隐藏。
  3. **得分规则**：ruleType Radio（SEGMENT 分段 / LINEAR 线性）。
     - SEGMENT：可增删行表格 [minValue, maxValue(可空=∞), score]，删除行后校验区间不重叠、score ∈ [0,100]（前端预校验，服务端 1152 兜底）。
     - LINEAR：四输入 minMetric/maxMetric/minScore/maxScore。
  - 底部：[取消] [保存]；保存成功回传 PerfMetricVO（version 自增 toast）。
- **编辑态只读项**：metricCode（口径变更走版本而非改码）。

### 7.2 岗位指标集绑定抽屉（Drawer，右滑 640px）

- **结构**：
  1. 顶部：岗位 Select（positionCode，接口：组织服务已有岗位列表）。
  2. 中部：指标绑定表格 [指标名称 | 全局权重（只读）| 覆盖权重 InputNumber 0~100]——勾选行启用绑定，weightOverride 留空则用全局 weight（PER-M-R3：覆盖不改变全局定义，全局列始终显示原值）。
  3. 底部合计条：`Σ 权重 = {total}%`，≠ 100 时红色并禁用保存（对应错误码 1154 前端预校验）。
- 保存 → `POST /admin-api/ims/perf/metric/bind-position` → 成功 toast `已绑定 {boundCount} 项指标`。

### 7.3 试取数弹窗（Modal，480px）

- 内容：测试周期 MonthPicker（默认上月）→ [开始测试] → `POST /admin-api/ims/perf/metric/test-fetch`。
- 结果区：fetchable=true → 绿色 ✓ + `示例值 {sampleValue}（耗时 {elapsedMs}ms）`；false → 红色 ✗ + errorReason。
- 发布新指标前建议完成一次试取数（流程提示语，非强制）。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 表单参数校验失败 | 表单字段红字 + 焦点定位 |
| 1151 | 创建时指标编码已存在 | 编码字段下方红字"编码已存在" |
| 1152 | 得分规则非法（区间重叠/分数越界） | 抽屉内得分规则区红字提示具体原因 |
| 1153 | 对 COMPETE_SUBMIT_RATE 执行启用/删除 | toast 显示"竞品分析提交率指标 V2 锁定禁用（BR-110）" |
| 1154 | 岗位权重合计 ≠ 100 | 绑定抽屉合计条红色 + 保存禁用 |
| 网络/超时 | — | 全局兜底（规范第 5 章） |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-105（自动取数覆盖率 > 80%） | 覆盖率卡（达标/未达标双色 + manualMetrics 展开） |
| BR-110（竞品指标 V2 禁用） | COMPETE_SUBMIT_RATE 行锁态渲染、只读抽屉、1153 拦截 |
| PER-M-R1（禁用指标不入计算） | 禁用 ConfirmDialog 文案 |
| PER-M-R2（覆盖率口径） | 覆盖率卡数值 = autoMetricCount/enabledMetricCount |
| PER-M-R3（岗位权重覆盖不改全局） | 绑定抽屉双列（全局只读 + 覆盖可编辑） |
| PER-M-R4（口径变更走版本） | version 列 + 保存 toast |

---

## P2 绩效计算与核准（PERF-002）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/perf/calc`（菜单：绩效考试 → 计算与核准） |
| 页面级别 | 二级 |
| 前置依赖 | P1 指标配置完成；第 23 周后（观察期不足报 1156）；每月 1 日凌晨自动触发（V2-A1 集群化调度，Redisson 锁） |
| 权限 | 查看：R1/R4（全量）/R9（脱敏）；人工补充：R4/R1；核准发布：R4；手动触发：R4/R1 |
| 用户 | 运营总监（R4 核准主责）/ 超管 R1 / 财务 R9 脱敏 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 绩效计算与核准   [周期: 2025-05 ▾]   [手动触发计算] [核准发布]            │
├──────────────────────────────────────────────────────────────────────────┤
│ 状态统计条: 计算中 0 | 待人工补充 3 ⚠ | 待核准 42 | 已发布 0              │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [部门 Cascader][状态 Select:全部/计算中/待人工/待核准/   │
│                 已发布] [搜索][重置]                                      │
├──────────────────────────────────────────────────────────────────────────┤
│ 结果表格                                                     共 45 条    │
│ ┌──────┬────────┬──────────┬──────┬────────┬──────────────┬──────────┐   │
│ │ 员工  │ 部门    │ 岗位      │综合  │部门排名│ 状态          │ 操作      │   │
│ │      │        │          │得分  │        │              │          │   │
│ ├──────┼────────┼──────────┼──────┼────────┼──────────────┼──────────┤   │
│ │张三   │ 直播部  │ 主播      │ 87.50│   1    │待人工 ⚠(1项) │补充 详情  │   │
│ │李四   │ 直播部  │ 主播      │ 62.30│   5    │待核准        │ 详情      │   │
│ │王五   │ 内容部  │ 剪辑      │ —    │  —     │计算中 ⏳     │ —        │   │
│ └──────┴────────┴──────────┴──────┴────────┴──────────────┴──────────┘   │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
└──────────────────────────────────────────────────────────────────────────┘
点击"详情" → 结果详情抽屉（指标明细 + 快照信息 + 版本历史）
点击"核准发布" → 核准发布抽屉（全周期视角，含待人工人员排除清单）
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
/** 绩效结果状态——引用《全局开发规范.md》3.2 权威枚举（值域一致）：'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED' | 'PENDING_MANUAL' */
type PerfResultStatus = 'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED' | 'PENDING_MANUAL';
/** 明细取数状态（契约内联） */
type PerfDataStatus = 'AUTO' | 'MANUAL' | 'MISSING';

// ===== 请求 =====
interface PerfResultQueryReq extends PageParam {
  deptId?: number;
  resultStatus?: PerfResultStatus;
}

interface PerfCalcRunReq {
  periodMonth: string;                   // yyyy-MM
  scope?: { userIds?: number[]; deptIds?: number[] };
}

interface PerfManualSupplementReq {
  metricId: number;
  manualValue: number;
  supplementReason: string;              // 必填（错误码 1158）
}

interface PerfApproveReq {
  approve: boolean;
  remark?: string;
  excludeUserIds?: number[];             // 排除待人工人员暂不发布
}

// ===== 响应 =====
interface PerfResultVO {
  id: number;
  periodMonth: string;                   // yyyy-MM
  userId: number;
  userName: string;
  positionCode: string;
  deptName: string;
  /** 综合得分 = Σ(指标得分×权重)（BR-117），DECIMAL(6,2)；CALCULATING 时为 null */
  totalScore: number | null;
  rankInDept: number | null;
  resultStatus: PerfResultStatus;
  /** 快照（不可变，V2-B4）：重算生成新版本，旧快照审计保留 */
  calcSnapshot: {
    metricVersions: Record<string, number>;
    fetchTime: string;
    engineVersion: string;
  };
  approvedBy?: number;
  approvedAt?: string;
}

interface PerfResultDetailVO extends PerfResultVO {
  details: Array<{
    metricCode: string;
    metricName: string;
    metricValue: number | null;          // R9 视角金额类原始值可能为 "***"
    metricScore: number;
    weight: number;
    dataStatus: PerfDataStatus;
  }>;
}
```

### 4. 交互流程

**页面加载**：
1. 顶部周期 MonthPicker（默认上一自然月）切换即刷新；加载 `GET /admin-api/ims/perf/calc/{period}`（path 参数为周期，Query 传分页+筛选）。
2. 状态统计条为当前周期各状态计数（由列表全量聚合，`pageSize` 拉满一次或独立统计参数，前端缓存）。
3. `CALCULATING` 行 totalScore/rankInDept 显示 "—"，操作列置灰，行尾 ⏳；30 秒轮询刷新直到离开计算中状态。

**核心操作**：
- **手动触发计算**（R4/R1）：ConfirmDialog 输入周期（默认上月）+ 可选范围（人员/部门）→ `POST /perf/calc/run` → toast `已创建计算任务（{targetUserCount} 人）`，列表切回 CALCULATING 轮询态。每月 1 日凌晨由 V2-A1 定时任务自动触发，此处为补算入口。观察期不足返回 1156 → Dialog 提示"第 23 周前无基线数据，暂不可计算"。
- **人工补充**（R4/R1）：待人工行操作"补充" → 补充抽屉（§7.1）；缺项指标按 0 分计入并标记，补充后状态回 PENDING_APPROVE（PER-C-R1）。
- **核准发布**（R4）：抽屉（§7.2）→ `PUT /perf/calc/{period}/approve`。发布后员工可见本人明细（1157 解除）、自动生成排名与分档（联动 P5）。
- **结果详情**：任何状态可点"详情" → 抽屉（§7.3），PUBLISHED 结果整抽屉只读（**快照只读**：所有指标明细、快照信息不可编辑，仅在快照头部展示版本号与引擎版本；更正须 R4 审批走重算新版本——顶部提示条文案）。
- **重算/更正**（V2-B4）：R4 在详情抽屉点 [申请重算]（PUBLISHED 状态才显示）→ ConfirmDialog "重算将生成新版本快照，原 v{n} 快照审计保留，确认？" → `POST /perf/calc/run`（scope 限定该周期）→ 新版本进入 CALCULATING；数据锁定后更正返回 1155 → 提示"须 R4 审批并留痕（PER-C-R4）"。
- **R9 视角**：金额类指标原始值 metricValue 显示 `"***"`（服务端脱敏），得分正常显示。

### 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| deptId | Cascader | number | 部门树单选 |
| resultStatus | Select | PerfResultStatus | 全部（默认）/计算中/待人工/待核准/已发布 |

### 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 员工 | userName | 文本 |
| 部门 | deptName | 文本 |
| 岗位 | positionCode | code 样式 |
| 综合得分 | totalScore | 右对齐两位小数；CALCULATING → "—"；PENDING_MANUAL 且有缺项 → 得分后缀橙点 Tooltip "含 {n} 项缺项按 0 分计入（PER-C-R1）" |
| 部门排名 | rankInDept | `第 {n} 名`；CALCULATING → "—" |
| 状态 | resultStatus | StatusTag（见全局约定色）；PENDING_MANUAL 附缺项数徽标 |
| 核准时间 | approvedAt | yyyy-MM-dd HH:mm，未核准 "—" |
| 操作 | — | 补充（仅 PENDING_MANUAL，R4/R1）/ 详情 |

### 6.1 状态 Tag 说明（ADR-IMS-005 · 已冻结 · 2026-10-05 补注）

本页（`resultStatus`）为 **IMS 批量域独立四态 Tag**，**不映射** OPS 单条 `dict_perf_status` Tag：

| resultStatus | Tag 文案 | 语义色 |
|--------------|----------|--------|
| `CALCULATING` | 计算中 | processing 蓝 |
| `PENDING_MANUAL` | 待人工 | warning 橙（附缺项数徽标） |
| `PENDING_APPROVE` | 待核准 | warning 橙 |
| `PUBLISHED` | 已发布 | success 绿 |

> **与 record 不自动合并**：**禁止** `calculated→PENDING_APPROVE`、`confirmed→PUBLISHED` 臆造等价；写路径 **单选**（批量核准仅 `PUT /perf/calc/{period}/approve`），读屏可 **双 Tab**（OPS 已确认 / IMS 已发布），**不得双写**。
> 若同页并展示 OPS record 结果，OPS 侧须用 **7 态** `<DictLabel dict-type="dict_perf_status" />`，**不得**压成四态。详见《PERF-绩效考核-API契约.md》§2A。

### 7. 抽屉/弹窗规格

### 7.1 人工补充抽屉（Drawer，右滑 560px）

- 头部：员工姓名 + 周期；缺项指标列表（dataStatus = MISSING 的明细）。
- 每缺项一行：指标名称（只读）+ 指标值 InputNumber（可负数/两位小数，按指标性质）+ 补充原因 Input（**必填**，错误码 1158 前端预校验：留空禁用保存）。
- 保存逐项调用 `PUT /admin-api/ims/perf/calc/detail/{id}/manual`（detail id = PerfResultVO.id + metricId 组合传参，与契约一致）→ 成功后行状态 Tag 变 MANUAL、缺项徽标减一；全部补齐后结果状态回 PENDING_APPROVE，toast 提示。

### 7.2 核准发布抽屉（Drawer，右滑 720px，仅 R4）

- **布局**：
  1. 周期摘要：目标人数 / 待人工 {n} 人 / 待核准 {m} 人 / 综合分均值。
  2. 待人工人员清单（自动勾选进 excludeUserIds，可手动调整勾选）：文案"以下人员存在缺项，默认排除本次发布，补充后再发布"。
  3. 审批意见 remark TextArea（驳回时必填）。
  4. 底部：[驳回（数据修正后重算）] [核准发布]。
- 核准 → `approve: true` → 返回 `{publishedCount, pendingManualCount, publishedAt}` → 成功 Dialog "已发布 {publishedCount} 人，{pendingManualCount} 人待人工补充" → 列表状态刷新、触发 P5 排名生成与预警推送。
- 驳回 → `approve: false` → 结果回 CALCULATING，remark 留痕显示于详情抽屉审核记录区。

### 7.3 结果详情抽屉（Drawer，右滑 800px）

- **结构**：
  1. 快照头部（Descriptions）：周期 / 指标版本集（metricVersions 摘要 `TRN_FR v2、MEE_R1 v1…`）/ 取数时间 fetchTime / 计算引擎 engineVersion / 结果状态 Tag。
  2. **只读提示条**（PUBLISHED）：黄色 InfoBar "本结果为不可变快照（V2-B4）。更正须 R4 审批后重算生成新版本，旧版本审计保留。" + R4 可见 [申请重算] 按钮。
  3. 指标明细表：[指标名称 | 原始值（R9 金额类 "***"）| 得分 | 权重 | 取数状态 Tag（AUTO 蓝/MANUAL 橙/MISSING 红）| 贡献分 = score×weight]；底部合计行 = totalScore。
  4. 审核记录：approvedBy/approvedAt、驳回/重算历史（版本时间线：v1 → v2 各自状态与时间）。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 表单红字 |
| 1155 | 锁定后更正（周期数据锁定） | Dialog "绩效月数据已锁定，更正须运营总监审批并留痕（PER-C-R4）" |
| 1156 | 观察期不足（第 23 周前） | Dialog "观察期不足：第 23 周前无基线数据" |
| 1158 | 补充原因必填 | 抽屉内红字 + 禁用保存（预校验）；服务端返回时同提示 |
| 1157 | 员工访问未发布明细 | P6 侧拦截（见 P6 §8） |
| 网络轮询失败 | CALCULATING 轮询 | 静默重试，连续 3 次失败显示"计算状态获取失败，请手动刷新" |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-117（综合得分 = Σ(指标得分×权重)） | 明细表贡献分列 + 合计行 = totalScore |
| PER-C-R1（缺项按 0 分计入并标记待人工） | 缺项徽标 + 补充抽屉 + 0 分后缀提示 |
| PER-C-R2（入离职当月按在职天数折算） | 计算引擎（服务端），详情抽屉快照头部可展示折算说明（有则显示） |
| PER-C-R3（核准前员工不可见） | 1157 拦截（P6）、列表权限 R1/R4/R9 |
| PER-C-R4（锁定后更正 R4 审批留痕） | 1155 Dialog + 审核记录 |
| V2-B4（快照不可变、重算新版本） | 详情抽屉只读提示条 + [申请重算] + 版本时间线 |
| V2-A1（每月 1 日集群化调度） | 手动触发入口为补算定位，自动任务说明文案 |

---

## P3 在线考试管理（PERF-003 管理侧）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/perf/exam`（菜单：绩效考试 → 在线考试） |
| 页面级别 | 二级（三 Tab：题库管理 / 试卷管理 / 成绩管理） |
| 前置依赖 | 无（与 P1/P2 可并行建设） |
| 权限 | 题库/试卷查看：R1/R2（主责）/R8；新增/编辑：R2（主责）/R1；删除：R1；阅卷：R2/R8；成绩查看：R1/R2/R4/R8/考生本人 |
| 用户 | 人事行政（R2 主责）/ 超管 R1 / 监考 R8 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 在线考试管理                                                              │
│ ┌─[题库管理]─┬─[试卷管理]─┬─[成绩管理]─────────────────────────┐          │
│ │                                                            │          │
│ │  ◆ Tab1 题库管理                                           │          │
│ │  QueryBar(单行): [知识域 Input][题型 Select:全部/单选/多选/  │          │
│ │   判断/简答] [搜索][重置]                    [+ 创建题目]   │          │
│ │  题目表格: [题型Tag|题干(截断)|选项数|分值|知识域|创建时间|  │          │
│ │            操作: 编辑 删除]                                 │          │
│ │                                                            │          │
│ │  ◆ Tab2 试卷管理                                           │          │
│ │  QueryBar: [试卷名称 Input]                  [+ 创建试卷]  │          │
│ │  试卷表格: [试卷编号EP|名称|组卷方式|总分/及格线|限时|状态   │          │
│ │            (DRAFT草稿/PUBLISHED已发布)|指派人数|操作:       │          │
│ │            发布(R2/R1,草稿态) 指派考生 成绩跳转]            │          │
│ │                                                            │          │
│ │  ◆ Tab3 成绩管理                                           │          │
│ │  QueryBar: [试卷 Select][考生 Input][状态 Select]          │          │
│ │  成绩表格: [考生|试卷|总分(客观+主观)|切屏次数|状态         │          │
│ │            (SUBMITTED待阅/GRADED已判分/MAKEUP补考)|补考标记│          │
│ │            |开始/交卷时间|操作: 阅卷(SUBMITTED且含简答题)]  │          │
│ └────────────────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
type QuestionType = 'SINGLE' | 'MULTI' | 'JUDGE' | 'SHORT_ANSWER';
type PaperType = 'FIXED' | 'RANDOM';
type PaperStatus = 'DRAFT' | 'PUBLISHED';
/** 考试状态——引用《全局开发规范.md》3.2 权威枚举（值域一致） */
type ExamStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'GRADED' | 'MAKEUP_EXAM';

// ===== 请求 =====
interface QuestionQueryReq extends PageParam {
  knowledgeDomain?: string;
  questionType?: QuestionType;
}

interface QuestionSaveReq {
  questionType: QuestionType;
  content: string;
  options?: string[];                    // SINGLE/MULTI 必填
  answer: number | number[] | boolean | string;  // 客观判分依据；SHORT_ANSWER 为参考答案 string
  score: number;
  knowledgeDomain: string;
}

interface ExamPaperCreateReq {
  paperName: string;
  paperType: PaperType;
  questionIds?: number[];                // FIXED
  strategy?: Array<{                     // RANDOM
    knowledgeDomain: string;
    questionType: QuestionType;
    count: number;
    scorePerQuestion: number;
  }>;
  totalScore: number;
  passScore: number;
  durationMinutes: number;
}

interface PaperAssignReq {
  userIds: number[];
  examWindow: { from: string; to: string };  // ISO 8601
}

interface GradeReq {
  gradings: Array<{ questionId: number; score: number; comment?: string }>;
}

interface ScoreQueryReq extends PageParam {
  paperId?: number;
  userId?: number;
  examStatus?: ExamStatus;
}

// ===== 响应（节选） =====
interface ExamQuestionVO {
  id: number;
  questionType: QuestionType;
  content: string;
  options?: string[];
  answer: unknown;                       // 列表脱敏：仅编辑抽屉回显
  score: number;
  knowledgeDomain: string;
  createdAt: string;
}

interface ExamPaperVO extends ExamPaperCreateReq {
  id: number;
  paperNo: string;                       // EP+日期+流水
  status: PaperStatus;
}

interface ExamScoreVO {
  id: number;
  paperId: number;
  paperName: string;
  userId: number;
  userName: string;
  score: number | null;                  // 含主观题未阅时可能为 null
  objectiveScore: number;
  subjectiveScore: number | null;
  switchScreenCount: number;             // ≥3 标红（PER-E-R1）
  examStatus: ExamStatus;
  isMakeup: boolean;                     // PER-E-R3 补考覆盖标记
  startAt: string;
  submitAt?: string;
}
```

### 4. 交互流程

**页面加载**：默认 Tab1 题库，`GET /admin-api/ims/perf/exam/questions`。Tab 切换各自加载（Tab2 试卷列表、Tab3 成绩列表）。

**核心操作**：
- **创建/编辑题目**（R2/R1）：题目编辑抽屉（§7.1）；客观题 answer 按题型动态控件（单选 Radio 映射 options 下标 / 多选 Checkbox 数组 / 判断 Switch true/false / 简答 TextArea 参考答案）。
- **删除题目**（R1）：ConfirmDialog → `DELETE /perf/exam/question/{id}`；已被试卷引用的题目服务端仅标记下架 → toast "该题已被试卷引用，已标记下架（不再进入新试卷抽题池）"。
- **创建试卷**（R2/R1）：组卷抽屉（§7.2）；保存校验 Σ题目分 = totalScore（错误码 1159 前端实时合计条）、随机策略抽题数 ≤ 题库存量（1160，前端按题库统计预校验）。
- **发布试卷**（R2/R1）：草稿行操作"发布" → ConfirmDialog "发布后不可修改题目结构，考生将按窗口作答" → `PUT /perf/exam/paper/{id}/publish`；状态 Tag → PUBLISHED。
- **指派考生**（R2/R1）：指派抽屉（§7.3）→ `POST /perf/exam/paper/{id}/assign` → toast "已指派 {assignedCount} 人，考生工作台已收到考试待办"。
- **阅卷**（R2/R8）：成绩表 SUBMITTED 且试卷含简答题行操作"阅卷" → 阅卷抽屉（§7.4）→ `PUT /perf/exam/record/{id}/grade`；阅卷完成 → GRADED，成绩计入 PERF-001 考试类指标取数（PER-E-R4，抽屉底部提示语）。
- **成绩跳转**：试卷行"成绩"按钮 → 切 Tab3 并预置 paperId 筛选。
- **考生视角**：Tab3 对考生角色仅返回本人成绩（服务端过滤），无他人行。

### 5. 查询条件表

| Tab | 字段 | 组件 | 说明 |
|-----|------|------|------|
| 题库 | knowledgeDomain | Input | 知识域模糊 |
| 题库 | questionType | Select | 全部/单选/多选/判断/简答 |
| 试卷 | paperName | Input | 试卷名称模糊 |
| 成绩 | paperId | Select | 试卷下拉（考试卷列表） |
| 成绩 | userId | Input | 考生姓名/工号（人选择器） |
| 成绩 | examStatus | Select | 全部/未开始/进行中/已交卷/已判分/补考 |

### 6. 表格列定义

**Tab1 题库**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 题型 | questionType | Tag：单选蓝/多选紫/判断青/简答橙 |
| 题干 | content | 截断 40 字 + Tooltip 全文 |
| 分值 | score | 右对齐 |
| 知识域 | knowledgeDomain | Tag 灰 |
| 创建时间 | createdAt | yyyy-MM-dd |
| 操作 | — | 编辑（R2/R1）/ 删除（R1） |

**Tab2 试卷**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 试卷编号 | paperNo | code 样式（EP+日期+流水） |
| 试卷名称 | paperName | 文本 |
| 组卷方式 | paperType | FIXED="固定卷" / RANDOM="随机组卷" |
| 总分/及格线 | totalScore/passScore | `100 / 60` |
| 限时 | durationMinutes | `{n} 分钟` |
| 状态 | status | DRAFT 灰"草稿" / PUBLISHED 绿"已发布" |
| 指派人数 | — | 数字 |
| 操作 | — | 发布（草稿态，R2/R1）/ 指派考生 / 成绩 |

**Tab3 成绩**：见 §3 ExamScoreVO；总分列 = `objectiveScore + subjectiveScore`（subjective 为 null 时显示 `客观 {x} · 待阅`）；切屏次数 ≥3 红色加 Tooltip "切屏 ≥3 次强制交卷，按已答计分（PER-E-R1）"；isMakeup=true 行首 Tag "补考"（PER-E-R3）。

### 7. 抽屉/弹窗规格

### 7.1 题目编辑抽屉（Drawer，右滑 640px）

- 题型 Select → 联动：SINGLE/MULTI 显示选项列表（可增删，≥2 项）+ 答案选择控件；JUDGE 显示 Switch；SHORT_ANSWER 显示参考答案 TextArea。
- 分值 InputNumber（>0，两位小数）；知识域 Input（可 datalist 复用已有域）。
- 保存 → `POST /perf/exam/question`（创建，返回 id）/ `PUT /perf/exam/question/{id}`（编辑）。

### 7.2 组卷抽屉（Drawer，右滑 880px，两步）

- **Step1 基本信息**：试卷名称、组卷方式 Radio（FIXED/RANDOM）、总分（实时合计只读）、及格线、限时分钟。
- **Step2 题目配置**：
  - FIXED：题库穿梭框/选择表格（按知识域+题型筛选，勾选 questionIds）；底部合计条 `Σ = {sum} 分`，≠ totalScore 红色禁用保存（1159 预校验）。
  - RANDOM：策略行表格 [知识域 | 题型 | 抽题数 | 每题分值 | 小计]；每行校验 `抽题数 ≤ 该(域,题型)题库存量`（1160 预校验，不足时红字"题库存量仅 {n} 题"）。
- 保存 → `POST /perf/exam/paper` → 返回 paperNo，toast "试卷已创建（{paperNo}），当前为草稿"。

### 7.3 指派考生抽屉（Drawer，右滑 640px）

- 试卷信息摘要（只读）+ 考生多选人员树/搜索（userIds）+ 考试窗口 RangePicker（from/to）。
- 窗口校验：from < to、from ≥ 当前时间。
- 保存 → `POST /perf/exam/paper/{id}/assign`。

### 7.4 阅卷抽屉（Drawer，右滑 800px）

- 头部：考生 + 试卷 + 客观得分（只读）。
- 简答题逐题卡：题干 + 考生作答（只读）+ 参考答案（折叠）+ 评分 InputNumber（0~该题分值）+ 评语 Input。
- 底部合计：主观分实时合计；[提交阅卷] → `PUT /perf/exam/record/{id}/grade` → 状态 GRADED。
- 提示条："阅卷成绩将自动计入 '考试成绩' 类绩效指标取数（PER-E-R4）"。主观题须 48 小时内完成（PER-E-R2）——SUBMITTED 超 48h 的行在列表置顶 + 橙色"超时待阅"徽标。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 表单校验 | 字段红字 |
| 1159 | 总分校验失败 | 组卷抽屉合计条红色 + 禁用保存 |
| 1160 | 随机策略抽题数超存量 | 策略行红字"题库存量仅 {n} 题" |
| 1163/1164 | 交卷侧（P4）| 见 P4 §8 |
| 引用题目删除 | 服务端标记下架 | toast 信息提示（非错误） |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| PER-E-R1（切屏 ≥3 强制交卷按已答计） | 成绩列切屏次数红色 + Tooltip |
| PER-E-R2（客观自动/主观 48h 人工阅卷） | 阅卷抽屉 + 超时待阅徽标 |
| PER-E-R3（补考一次，成绩覆盖标记） | isMakeup Tag "补考"；补考申请入口在 P4 |
| PER-E-R4（成绩计入指标取数） | 阅卷抽屉提示条；P1 考试类指标 dataSource=EXAM |

---

## P4 考试作答页（PERF-003 考生侧，H5 同构）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/h5/exam`（工作台考试待办卡片进入；携带 paperId） |
| 页面级别 | H5 全屏作答页（移动端优先，同构渲染） |
| 前置依赖 | 被指派 + 当前时间在考试窗口内（否则 1161） |
| 权限 | 被指派考生本人（1163 非本人拦截） |
| 用户 | 考生 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────┐  H5 竖屏
│ ┌──────────────────────────┐ │
│ │ ⏳ 12:34  单选 3/20  ◉◉○○ │ │  顶部: 倒计时(红<5min) 题型进度 答题卡
│ ├──────────────────────────┤ │
│ │ 3. 下列哪项符合直播 SOP   │ │
│ │    A. 开播前 30 分钟调试  │ │
│ │    B. ...                 │ │
│ │    C. ...                 │ │
│ │    D. ...                 │ │
│ ├──────────────────────────┤ │
│ │ [上一题]        [下一题]  │ │
│ ├──────────────────────────┤ │
│ │ ⚠ 切屏 1/3 次警告条(可收敛)│ │  切屏计数 ≥2 时常驻红色
│ ├──────────────────────────┤ │
│ │        [ 交 卷 ]          │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
答完最后一题或点交卷 → 交卷确认弹窗（含未答题数提示）
```

### 3. TypeScript 类型定义

```typescript
// 复用全局 ExamStatus；契约 ExamRecordVO：

interface ExamRecordVO {
  id: number;
  paperId: number;
  paperName: string;
  userId: number;
  /** 考题快照（随机卷每人不同，固定卷同题） */
  questions: Array<{
    questionId: number;
    questionType: QuestionType;
    content: string;
    options?: string[];
    score: number;
  }>;
  startAt: string;
  deadline: string;                      // startAt + durationMinutes
  switchScreenCount: number;             // ≥3 强制交卷（PER-E-R1）
  examStatus: ExamStatus;
}

interface ExamSubmitReq {
  recordId: number;
  answers: Array<{ questionId: number; answer: number | number[] | boolean | string }>;
  /** 前端累计切屏次数（服务端校验兜底） */
  switchScreenCount: number;
}

interface ExamSubmitVO {
  recordId: number;
  examStatus: 'SUBMITTED' | 'GRADED';
  objectiveScore: number;
  subjectiveScore: number | null;
  totalScore: number | null;
  forcedSubmit: boolean;                 // true = 切屏 ≥3 强制交卷
}
```

### 4. 交互流程

**进入考试**：
1. 待办卡片点击 → `POST /admin-api/ims/perf/exam/record/start`（携带 paperId）→ 返回 ExamRecordVO（含每人考题快照：RANDOM 卷每人题目不同）。
2. 错误码 1161 → H5 Dialog "不在考试窗口内（{from} ~ {to}）"；1162 → Dialog "已有进行中的答卷，继续作答？"（是 → 拉取进行中 record 恢复）。
3. 倒计时从 deadline 反推；**到 0 自动按已答交卷**（状态机"超时未交卷按已答计"）。

**作答交互**：
- 题型渲染：单选 Radio / 多选 Checkbox / 判断 Switch / 简答 TextArea；答题卡圆点标记已答/未答。
- **切屏计数（PER-E-R1）**：`visibilitychange` + `blur` 监听，切回时调用本地计数 + 顶部警告条 "已切屏 {n}/3 次"；n=2 常驻红色警告 "再切屏 1 次将强制交卷"；**第 3 次切回时直接调交卷**（forcedSubmit，按已答计分），交卷结果 Dialog 红色提示"切屏达 3 次，已按已答题目强制交卷"。
- 客户端计数随交卷请求上报 `switchScreenCount`，服务端校验兜底。

**交卷**：
- [交卷] → 确认弹窗（"未答 {n} 题，确认交卷？"）→ `POST /perf/exam/record/submit` → 结果页：客观分即时显示、简答题显示"待人工阅卷（48 小时内）"；forcedSubmit=true 时结果页横幅说明。
- 错误码 1163（非本人）/ 1164（重复提交）→ Dialog 提示后返回待办列表。

**补考（PER-E-R3）**：GRADED 且总分 < passScore 的结果页显示 [申请补考]（仅一次）；补考答卷 examStatus = MAKEUP_EXAM，新成绩覆盖旧成绩并标记。

### 5~6. 查询条件表 / 表格列定义

不适用（H5 作答页无查询表格；答题卡进度即"列表"形态）。

### 7. 抽屉/弹窗规格

- **交卷确认弹窗**（Modal H5 居中）：已答/未答统计 + [继续作答] [确认交卷]。
- **强制交卷结果弹窗**：红色警示 + 已答计分说明 + [查看成绩]。
- **补考确认弹窗**：黄色提示"补考仅一次，新成绩将覆盖原成绩（PER-E-R3）"。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1161 | 不在窗口内 | Dialog 后返回待办 |
| 1162 | 重复开始 | Dialog"已有进行中答卷"→ 恢复作答 |
| 1163 | 答卷非本人 | Dialog 拦截 |
| 1164 | 已交卷重复提交 | Dialog 拦截，防双击交卷（按钮 loading + 提交后禁用） |
| 断网 | 作答中 | 本地暂存 answers 到 localStorage，恢复后回填；倒计时以 deadline 为准不受刷新影响 |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| PER-E-R1（切屏 ≥3 强制交卷） | 切屏计数警告条 + 第 3 次强制交卷流程 |
| PER-E-R2（客观自动判分） | 交卷即显客观分；主观"待阅 48h" |
| PER-E-R3（补考一次覆盖） | 结果页补考入口 + 确认弹窗 |

---

## P5 排名与预警看板（PERF-004）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/perf/rank`（菜单：绩效考试 → 排名与预警） |
| 页面级别 | 二级（三 Tab：排名看板 / 预警清单 / 重点辅导名单） |
| 前置依赖 | P2 核准发布后自动生成（本页数据随发布联动刷新） |
| 权限 | 查看：R1/R2/R4（全量排名）/R9（脱敏）；预警处置：R4/R2；辅导名单：R1/R4/部门负责人 |
| 用户 | 管理层（排名决策）/ R2（预警处置）/ 部门负责人（辅导名单） |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 排名与预警   [周期: 2025-05 ▾] [部门 Select:全部/各部门]                   │
│ ┌─[排名看板]─┬─[预警清单]─┬─[重点辅导名单]──────────────────┐            │
│ │                                                          │            │
│ │  ◆ Tab1 排名看板                                         │            │
│ │  分档统计卡: 优秀 8 | 合格 32 | 待改进 5（含预警 3）       │            │
│ │  排名表格: [排名|员工|部门|综合得分|分档Tag|预警状态|       │            │
│ │            连续待改进月数|操作: 详情(跳P6管理员视角)]      │            │
│ │  注: 员工本人仅可见本人排名（PER-R-R4），全量视图仅        │            │
│ │      R1/R2/R4/R9 可见                                    │            │
│ │                                                          │            │
│ │  ◆ Tab2 预警清单（BR-117 <60 分）                         │            │
│ │  QueryBar: [处置状态 Select:全部/待处置/已处置]           │            │
│ │  预警表格: [周期|员工|部门|得分|预警时间|推送对象(本人+    │            │
│ │            上级+HR Tag)|处置状态|操作: 处置登记]           │            │
│ │                                                          │            │
│ │  ◆ Tab3 重点辅导名单（连续 2 月待改进）                    │            │
│ │  辅导表格: [员工|部门|连续月数|近两周期得分对比(火花线)|   │            │
│ │            操作: 辅导详情]  推送: 部门负责人+运营总监      │            │
│ └──────────────────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3. TypeScript 类型定义

```typescript
// ===== 枚举（全局权威枚举） =====
/** 分档（注意：≠ PerfGrade S~D 等级枚举，禁混用） */
type PerfGradeLevel = 'EXCELLENT' | 'QUALIFIED' | 'IMPROVE';
/** 预警处置状态（契约内联） */
type AlertHandleStatus = 'PENDING' | 'DONE';

// ===== 请求 =====
interface PerfRankQueryReq {
  periodMonth: string;                   // path 参数 {period}
  deptId?: number;
}

interface PerfAlertQueryReq extends PageParam {
  periodMonth?: string;
  handleStatus?: AlertHandleStatus;
}

interface PerfAlertHandleReq {
  handleRemark: string;                  // 必填
  followUpPlan?: string;                 // 辅导/改进计划
}

// ===== 响应 =====
interface PerfRankVO {
  periodMonth: string;
  deptId: number;
  deptName: string;
  userId: number;
  userName: string;
  totalScore: number;
  rankNo: number;                        // 部门内综合得分降序（BR-117）
  /** ≥85 优秀 / 60~84 合格 / <60 待改进（分档线 85/60 全局默认可按岗位组配置 PER-R-R1） */
  gradeLevel: PerfGradeLevel;
  alertStatus: 'NONE' | 'ALERTED';
  consecutiveMonths: number;             // 连续待改进月数
}

interface PerfAlertVO {
  id: number;
  periodMonth: string;
  userId: number;
  userName: string;
  deptName: string;
  totalScore: number;
  alertedAt: string;
  pushTargets: Array<'SELF' | 'SUPERIOR' | 'HR'>;   // PER-R-R2
  handleStatus: AlertHandleStatus;
  handleRemark?: string;
}

interface CoachingVO extends PerfRankVO {
  consecutiveMonths: number;             // ≥2
  lastTwoPeriods: Array<{ periodMonth: string; totalScore: number; gradeLevel: string }>;
}
```

### 4. 交互流程

**页面加载**：
1. 周期/部门切换 → `GET /admin-api/ims/perf/rank/period/{period}`（Query: deptId）→ Tab1 排名表 + 分档统计卡。
2. Tab2 → `GET /admin-api/ims/perf/rank/alerts`；Tab3 → `GET /admin-api/ims/perf/rank/coaching-list`。

**核心操作**：
- **排名详情**：行操作"详情" → 管理员视角跳 P2 结果详情抽屉（复用）。
- **预警处置**（R4/R2）：Tab2 行操作"处置登记" → 处置抽屉（§7.1）→ `PUT /admin-api/ims/perf/rank/alert/{id}/handle` → handleStatus → DONE。
- **辅导详情**：Tab3 行操作 → 抽屉（§7.2）展示近两周期得分对比 + 部门负责人/运营总监推送记录说明。
- 排名发布后自动更新：P2 核准成功 toast 引导跳转本页（"排名与分档已生成，前往查看"）。

### 5. 查询条件表

| Tab | 字段 | 组件 | 说明 |
|-----|------|------|------|
| 公共 | periodMonth | MonthPicker | 顶部周期（path 参数） |
| 公共 | deptId | Select | 全部（默认）/各部门 |
| Tab2 | periodMonth | MonthPicker | 同上联动 |
| Tab2 | handleStatus | Select | 全部（默认）/待处置/已处置 |

### 6. 表格列定义

**Tab1 排名看板**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 排名 | rankNo | 前三名金银铜徽标；其余数字 |
| 员工 | userName | 文本（R9 视角正常，敏感由服务端控制） |
| 部门 | deptName | 文本 |
| 综合得分 | totalScore | 右对齐两位小数；<60 红色 |
| 分档 | gradeLevel | EXCELLENT 绿"优秀 ≥85" / QUALIFIED 灰"合格" / IMPROVE 红"待改进 <60" |
| 预警状态 | alertStatus | NONE "—" / ALERTED 红 Tag"已预警" |
| 连续待改进 | consecutiveMonths | ≥2 橙色加粗 `连续 {n} 月`（联动 Tab3） |

**Tab2 预警清单**：周期、员工、部门、得分（红）、预警时间、推送对象（SELF="本人"/SUPERIOR="直属上级"/HR="HR" 多 Tag）、处置状态（PENDING 橙/DONE 绿）、操作（处置登记，R4/R2，PENDING 态）。

**Tab3 辅导名单**：员工、部门、连续月数、近两周期对比（`2025-04 55.2 → 2025-05 52.8` 趋势红色↓）、操作（辅导详情）。

### 7. 抽屉/弹窗规格

### 7.1 预警处置登记抽屉（Drawer，右滑 560px，R4/R2）

- 头部：员工 + 周期 + 得分 + 推送对象回显（本人+直属上级+HR，PER-R-R2）。
- 处置说明 handleRemark TextArea（**必填**，前端预校验禁用保存）。
- 后续辅导计划 followUpPlan TextArea（选填）。
- 保存 → `PUT /admin-api/ims/perf/rank/alert/{id}/handle` → toast "处置已登记"。

### 7.2 辅导详情抽屉（Drawer，右滑 640px）

- 员工信息 + 连续待改进月数 + 近两周期明细（lastTwoPeriods 表格：周期/得分/分档）。
- 推送说明区（只读）：自动推送部门负责人 + 运营总监（PER-R-R3）。
- 若该员工已有 Tab2 处置记录，展示 handleRemark / followUpPlan 关联回显。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验 | 常规红字 |
| 周期未发布 | rank 数据为空 | 空态插画 + "本期绩效尚未核准发布，发布后自动生成排名" |
| 非管理员访问全量排名 | 服务端 403 | 员工自动跳转 P6"我的绩效"（PER-R-R4 排名隐私） |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-117（<60 预警推送本人+上级+HR） | Tab2 预警清单 + pushTargets Tag + 处置闭环 |
| PER-R-R1（分档线 85/60 可配置） | 分档 Tag 附分档线文案（全局默认） |
| PER-R-R2（预警推送三对象） | 处置抽屉推送对象回显 |
| PER-R-R3（连续 2 月待改进辅导名单） | Tab3 + 连续月数列 + 双周期对比 |
| PER-R-R4（排名隐私） | 权限拦截 + 403 跳转 P6 |
| BR-110（竞品维度 V2 剔除） | 页面说明文案"V2 排名不含竞品分析维度（BR-110）" |

---

## P6 我的绩效（PERF-002/004 员工侧，H5/工作台卡片）

### 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/h5/perf/mine`（工作台"我的绩效"卡片进入） |
| 页面级别 | H5 页面（移动端优先）+ 工作台卡片摘要 |
| 前置依赖 | 本周期绩效已核准发布（未发布 1157 拦截） |
| 权限 | 员工本人（数据服务端限定本人） |
| 用户 | 全员员工 |

### 2. 页面布局（ASCII）

```
┌──────────────────────────────┐  H5
│ ┌──────────────────────────┐ │
│ │ 2025-05 我的绩效          │ │  周期切换（仅已发布周期可选）
│ │  综合得分  87.50          │ │  大数字
│ │  分档 [优秀 ≥85]          │ │  PerfGradeLevel Tag
│ │  部门排名 第 1 / 12       │ │  rank/mine: 本部门人数
│ │  部门分布: 优8 合32 改5   │ │  scoreDistribution 三段条
│ ├──────────────────────────┤ │
│ │ 指标明细（快照只读）       │ │
│ │  培训完成率   96%  → 95分 │ │  每行: 指标名 原始值 得分
│ │  日报按时率   100% → 100分│ │  权重 · 贡献分 · 状态Tag
│ │  ...                      │ │
│ │  合计 87.50 = Σ(得分×权重) │ │
│ ├──────────────────────────┤ │
│ │ [历史绩效趋势图(折线)]     │ │  近 6 周期 totalScore
│ └──────────────────────────┘ │
└──────────────────────────────┘
工作台卡片（Web 侧同构摘要）：本期得分 + 分档 Tag + [查看明细] 
```

### 3. TypeScript 类型定义

复用 P2 `PerfResultDetailVO`（`GET /admin-api/ims/perf/calc/{period}/mine`）与 P5 `PerfRankVO & { deptTotalCount, scoreDistribution }`（`GET /admin-api/ims/perf/rank/mine`）：

```typescript
interface MyPerfVO extends PerfResultVO {
  details: Array<{
    metricCode: string;
    metricName: string;
    metricValue: number | null;
    metricScore: number;
    weight: number;
    dataStatus: PerfDataStatus;
  }>;
}

interface MyRankVO extends PerfRankVO {
  deptTotalCount: number;
  scoreDistribution: { excellent: number; qualified: number; improve: number };
}
```

### 4. 交互流程

**页面加载**：
1. 并行 `GET /perf/rank/mine`（默认最近已发布周期）+ `GET /perf/calc/{period}/mine`。
2. 未发布周期：mine 接口返回 1157 → 页面空态"本期绩效尚未发布，发布后可见（PER-C-R3）"。
3. 周期切换器仅列出已发布周期（服务端下发可选周期）。

**交互**：
- 指标明细整块**只读**（快照不可变 V2-B4——页面无任何编辑入口，页脚灰色说明"绩效结果为周期快照，如有疑问请联系 HR/运营总监"）。
- 历史趋势图：近 6 周期折线（前端基于周期切换累计查询或复用 mine 历史接口数据）；<60 点标红。
- 若本人处于预警/辅导名单：页面顶部出现橙色提示卡"本期得分低于 60，已通知您与直属上级"（不含他人信息，PER-R-R4 隐私）。

### 5~6. 查询条件表 / 表格列定义

不适用（本人单条视图；指标明细为只读列表：指标名称 | 原始值 | 得分 | 权重 | 贡献分 | 取数状态 Tag）。

### 7. 抽屉/弹窗规格

无抽屉；预警提示卡为 inline Alert（可折叠）。

### 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1157 | 结果未发布 | 空态页 + 说明文案 |
| 周期无数据 | 新员工入职当月 | 空态"本期无绩效记录（入职/离职当月按在职天数折算，PER-C-R2）" |

### 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| PER-C-R3（发布后员工可见本人明细） | 1157 空态 + 发布后通知链路（P2 核准 → 工作台卡片刷新） |
| BR-117（本人得分展示） | 大数字 + 明细合计 = Σ |
| PER-R-R4（排名隐私，仅见本人+部门分布） | 排名区仅本人 rank + deptTotalCount + 分布统计（无他人明细） |
| V2-B4（快照只读） | 全页无编辑入口 + 页脚说明 |

---

## 附录 A：模块级约定

1. **快照不可变（V2-B4）**：P2 详情抽屉、P6 我的绩效中所有已发布结果只读；更正路径 = R4 审批 → `POST /perf/calc/run` 重算 → 生成新版本快照，旧版本审计保留（版本时间线展示）。前端不得提供任何对 PUBLISHED 结果的编辑入口。
2. **竞品指标锁定（BR-110）**：`COMPETE_SUBMIT_RATE` 在 P1 全链路锁态（只读抽屉、无启停入口、1153 兜底）；V2 排名与计算不含该维度；V3 04 竞品上线后由 COMP 侧联动启用（BR-206，本规格不实现）。
3. **枚举纪律**：只用 `PerfGradeLevel`（分数分档），**禁止混入 `PerfGrade`（S~D 等级）**；`ExamStatus`、`PerfResultStatus` 引用《全局开发规范.md》3.2 权威枚举（值域一致：ExamStatus 五态 / PerfResultStatus 四态）。
4. **得分精度**：DECIMAL(6,2) 两位小数，无 ¥ 前缀；权重显示 `xx%`；贡献分 = 得分 × 权重（两位小数）。
5. **R9 脱敏**：分数/排名正常显示，金额类指标原始值（FIN 来源 metricValue）服务端返回 `"***"`，前端原样渲染；FIN 类指标在 V2.3 上线时置 DISABLED 锁态（FIN 模块已移 V3），随 11 财务上线（V3 第 33 周后）解禁（复用 BR-110 锁定机制）。
6. **脱敏/隐私双层**：R9 视角脱敏金额；员工视角只可见本人（PER-C-R3/PER-R-R4），403/1157 由前端统一转空态或跳转 P6。
7. **H5 同构**：P4 考试作答（倒计时/切屏计数/答题卡）、P6 我的绩效为移动端优先；P1/P2/P3/P5 为 Web 管理后台。
8. **自动任务（V2-A1）**：每月 1 日凌晨自动计算（Redisson 分布式锁防重复）；前端"手动触发"定位为补算入口，观察期不足（1156）须文案解释。
9. **切屏防作弊（PER-E-R1）**：visibilitychange/blur 双监听本地计数，第 3 次切回强制交卷；计数随交卷请求上报，服务端校验兜底（前端计数仅为体验层，非安全边界）。

## 附录 B：BR / PER 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-105 | 自动取数覆盖率 > 80% | P1 覆盖率卡 |
| BR-110 | 竞品指标 V2 禁用 | P1 锁态、P2 计算过滤说明、P5 说明文案 |
| BR-117 | 综合得分公式 / <60 预警 | P2 明细合计、P5 预警清单、P6 大数字 |
| PER-M-R1 | 禁用指标不入计算 | P1 禁用弹窗 |
| PER-M-R2 | 覆盖率口径 | P1 覆盖率卡 |
| PER-M-R3 | 岗位权重覆盖不改全局 | P1 绑定抽屉双列 |
| PER-M-R4 | 口径变更走版本 | P1 version + toast |
| PER-C-R1 | 缺项 0 分计并标记待人工 | P2 缺项徽标 + 补充抽屉 |
| PER-C-R2 | 入离职当月折算 | P6 空态文案（计算服务端） |
| PER-C-R3 | 核准前员工不可见 | P2 权限、P6 1157 空态 |
| PER-C-R4 | 锁定后更正 R4 审批留痕 | P2 1155 Dialog + 审核记录 |
| PER-E-R1 | 切屏 ≥3 强制交卷 | P4 切屏流程、P3 成绩红标 |
| PER-E-R2 | 客观自动 / 主观 48h 人工阅卷 | P4 结果页、P3 阅卷抽屉 + 超时徽标 |
| PER-E-R3 | 补考一次覆盖标记 | P4 补考入口、P3 isMakeup Tag |
| PER-E-R4 | 考试成绩入指标取数 | P3 阅卷提示条、P1 EXAM 来源 |
| PER-R-R1 | 分档线 85/60 可配置 | P5 分档 Tag 文案 |
| PER-R-R2 | 预警推送本人+上级+HR | P5 预警清单 pushTargets |
| PER-R-R3 | 连续 2 月待改进辅导名单 | P5 Tab3 |
| PER-R-R4 | 排名隐私 | P5 403 跳转、P6 仅本人视图 |
| V2-B4 | 快照不可变、重算新版本 | P2 详情只读 + 版本时间线、P6 只读 |
| V2-A1 | 每月 1 日集群化调度 | P2 手动触发定位说明 |

（全文完）
