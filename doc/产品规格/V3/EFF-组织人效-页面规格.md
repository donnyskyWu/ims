# EFF - 组织人效 页面规格（V3 增量，19 模块，第 32~38 周）

> **模块范围**：EFF-001 人员归属关系 / EFF-002 人效指标盘点。
> **模块定性**：**补齐类**——IP 组管理已完成（✅ 不重复建设），本次仅补齐人员归属与人效盘点。
> **权威依据**：《IMS第三期PRD-V3.md》5.10~5.11；《EFF-组织人效-API契约.md》（15 接口，EFF 域错误码 1198/1199，与 BI 共段 1191~1199：BI 占 1191~1197、EFF 占 1198/1199）；《全局开发规范.md》第 4 章权威枚举、第 6 章通用组件。
> **页面清单**（4 页）：P1 归属关系管理（Web）｜P2 人效指标配置与盘点（Web）｜P3 人效看板（Web，组织对比）｜P4 我的人效（工作台卡片 + H5）。
> **模块核心口径**：**在职唯一主归属（BR-213/EFF-R1）**——主归属 shareRatio=100 唯一（冲突 1198）；兼职分摊合计 ≤ 100%（超限 1199）；**归属变更时间段留痕（EFF-R2）**——调岗/转兼职/终止生成新时间段记录、历史保留，人效按时间段归属计算；**覆盖率 = 100% 方可发布（BR-207/EFF-M-R4）**——未覆盖阻断发布并每日督办；盘点每月 2 日自动触发（绩效计算后执行，前置依赖，V2-A1 集群化调度）；计算失败转人工兜底不阻塞发布（V3 9.3）；人效裁决发布前仅 R1/R2/R4 可见（EFF-M-R3，模式同 V2 绩效快照）。

## 0.1 导航（走查 #17 · SSOT = 完整 PRD v2.6.13）

**侧栏路径**：数据决策 → **数据分析** → **组织人效**（**单 L3**；页内 Tab：归属关系 / 人效盘点 / 人效看板）。  
**边界**：IP 组 CRUD = **日常运营 · 19a IP 组**（废止 eff 内 IP 组 Tab）。P4 工作台卡片 **无侧栏**。  
**兼容**：`go('eff')` → 组织人效 · 看板 Tab；`go('effRelation'|'effInventory'|'effBoard')` → 同页对应 Tab；`go('effIpg')` → `ipg`。

---

## 全局约定（本模块适用）

- 响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；字段 camelCase（`relation_type → relationType`、`share_ratio → shareRatio`）。
- 枚举（契约内联）：`EffRelationType`（PRIMARY 主归属/PART_TIME 兼职）、`EffTargetType`（IP_GROUP/TEAM/ACCOUNT）、`EffRelationStatus`（ACTIVE 生效/HISTORICAL 历史）、`EffChangeAction`（TRANSFER 调岗/TO_PART_TIME 转兼职/TERMINATE 终止）、`EffDimensionType`（PERSON/TEAM/IP_GROUP/DEPT）、`EffPublishStatus`（CALCULATING/PENDING_APPROVE/PUBLISHED）、EnableStatus（指标 ENABLED/DISABLED）。
- 分摊比例：DECIMAL(5,2)，显示 `xx%`（主归属固定 100%）；合计 ≤ 100 实时校验。
- 权限矩阵引用 PRD 5.10~5.11.5：R2 人事行政（归属主责）、R4 运营总监（裁决发布）、R1、R3（成本/利润维度）、R9（脱敏）、R5/R6/R7（本人/团队，发布后）。
- StatusTag 语义色：PRIMARY 蓝"主归属"/PART_TIME 紫"兼职"；ACTIVE 绿/HISTORICAL 灰删除线；CALCULATING 蓝/PENDING_APPROVE 橙/PUBLISHED 绿。
- 人效指标金额类（人均 GMV/净利润）¥ 前缀千分位两位小数；R9 视角成本/利润类指标服务端脱敏 null → "—"。

---

# P1 归属关系管理（EFF-001）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/eff/relation`（菜单：组织人效 → 归属关系） |
| 页面级别 | 二级（模块主页面） |
| 前置依赖 | 钉钉组织同步（V1 AUTH）在职人员数据；IP 组管理已完成（复用目标选择） |
| 权限 | 查看：R1/R2/R4/R9/R5/R6（本人归属）/R7（本人归属）；建立/变更：R2（主责）/R1；删除（误操作）：R1 |
| 用户 | 人事行政 R2（主责维护）/ 超管 R1 |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 归属关系管理   [覆盖率卡: 96.8% ⚠ 未覆盖 3 人 → 查看清单(BR-207 督办)]   │
├──────────────────────────────────────────────────────────────────────────┤
│ QueryBar(单行): [人员人员选择][归属类型 Select:全部/主归属/兼职][目标类型 │
│  Select:全部/IP组/团队/账号][状态 Select:全部/生效/历史] [搜索][重置]     │
│                                            [+ 建立归属(R2/R1)]          │
├──────────────────────────────────────────────────────────────────────────┤
│ 归属关系表                                                   共 {n} 条  │
│ ┌──────┬────────┬──────┬──────────┬──────┬──────────┬──────┬────────┐   │
│ │人员   │部门     │类型  │ 归属目标  │分摊  │ 生效期间  │状态  │ 操作    │   │
│ ├──────┼────────┼──────┼──────────┼──────┼──────────┼──────┼────────┤   │
│ │张三   │直播一部 │主归属│IP组·华东一组│100%│01-01~    │生效  │变更 时间│   │
│ │      │        │      │          │    │(至今)     │      │线       │   │
│ │张三   │直播一部 │兼职  │IP组·华南二组│20% │03-01~   │生效  │…       │   │
│ │李四   │内容部   │主归属│团队·剪辑A组 │100%│02-15~   │历史  │时间线   │   │
│ │      │        │      │          │    │05-31     │(删除线)│        │   │
│ └──────┴────────┴──────┴──────────┴──────┴──────────┴──────┴────────┘   │
│ 分页: ‹ 1 ›   每页 [10▾] 条                                              │
└──────────────────────────────────────────────────────────────────────────┘
覆盖率卡点击 → 未覆盖督办弹窗（§7.3）
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（契约内联） =====
type EffRelationType = 'PRIMARY' | 'PART_TIME';
type EffTargetType = 'IP_GROUP' | 'TEAM' | 'ACCOUNT';
type EffRelationStatus = 'ACTIVE' | 'HISTORICAL';
type EffChangeAction = 'TRANSFER' | 'TO_PART_TIME' | 'TERMINATE';

// ===== 请求 =====
interface EffRelationQueryReq extends PageParam {
  userId?: number;
  relationType?: EffRelationType;
  targetType?: EffTargetType;
  targetId?: number;
  status?: EffRelationStatus;
}

interface EffRelationCreateReq {
  userId: number;
  relationType: EffRelationType;
  targetType: EffTargetType;
  targetId: number;
  shareRatio: number;                    // PRIMARY 固定 100
  effectiveFrom: string;                 // yyyy-MM-dd
}

interface EffRelationChangeReq {
  /** 变更动作：调岗（换目标）/ 转兼职 / 失效 */
  action: EffChangeAction;
  newTargetId?: number;                  // TRANSFER 必填
  newShareRatio?: number;                // TO_PART_TIME 必填
  effectiveDate: string;                 // 旧关系 effectiveTo 封口日
  changeReason?: string;
}

// ===== 响应 =====
interface EffRelationVO {
  id: number;
  userId: number;
  userName: string;
  deptName: string;
  relationType: EffRelationType;
  targetType: EffTargetType;
  targetId: number;
  targetName: string;
  /** 分摊比例：主归属 = 100；兼职合计 ≤ 100（BR-213） */
  shareRatio: number;
  effectiveFrom: string;                 // 时间段留痕
  effectiveTo?: string;
  status: EffRelationStatus;
  changedBy: number;
  changedByName: string;
  changedAt: string;
}

interface EffRelationTimelineResp {
  userId: number;
  userName: string;
  timeline: Array<{
    relationId: number;
    relationType: EffRelationType;
    targetName: string;
    targetType: string;
    shareRatio: number;
    effectiveFrom: string;
    effectiveTo?: string;
    status: EffRelationStatus;
    changedByName: string;
    changedAt: string;
  }>;
  /** 当前生效归属概览（主+兼职） */
  currentRelations: EffRelationVO[];
  totalShareRatio: number;               // 合计 ≤ 100 校验展示
}

interface EffCoverageVO {
  activeEmployeeCount: number;
  coveredCount: number;
  coverageRate: number;                  // BR-207 目标 = 100%
  target: 100;
  isBlocking: boolean;                   // 阻断盘点发布
}

interface EffUncoveredVO {
  userId: number;
  userName: string;
  deptName: string;
  positionName: string;
  onboardingDate: string;
  uncoveredDays: number;                 // 未覆盖天数（督办）
}
```

## 4. 交互流程

**页面加载**：
1. 并行 `GET /eff/relation/list`（分页）+ `GET /eff/relation/coverage`（覆盖率卡）。
2. 覆盖率卡：=100% 绿 ✓ "达标（BR-207）"；<100% 橙 ⚠ `覆盖率 {rate}%（未覆盖 {n} 人）`+ [查看清单] → 未覆盖督办弹窗（§7.3）。
3. R5/R6/R7 登录 → 列表服务端过滤为本人归属记录（无管理操作）。

**核心操作**：
- **建立归属**（R2/R1）：[+ 建立归属] → 归属建立抽屉（§7.1）→ `POST /eff/relation`：
  - 主归属冲突（该人员已有 ACTIVE 主归属）返回 **1198** → 抽屉红字"该人员已有生效主归属（BR-213 在职唯一主归属）"，并展示既有主归属信息；
  - 兼职分摊合计超 100% 返回 **1199** → 红字"该人员兼职分摊合计 {sum}% 超 100%"（前端实时合计预校验，见抽屉）；
  - PRIMARY 类型 shareRatio 强制 100（前端锁定只读，1001 预校验）。
- **变更归属**（R2/R1）：行操作"变更" → 变更抽屉（§7.2）→ `PUT /eff/relation/{id}`：变更生成新时间段记录（旧关系 effectiveTo 封口、历史保留，人效按时间段归属计算，EFF-R2）。
- **删除（误操作）**（仅 R1）：行操作"删除" → ConfirmDialog 红色警示 "仅限误操作场景物理删除；正常人员变动请走【变更】（时间段留痕，EFF-R2）" → `DELETE /eff/relation/{id}`。
- **时间线**：行操作"时间线" → `GET /eff/relation/timeline/{userId}` → 时间线抽屉（§7.4）。

## 5. 查询条件表

| 字段 | 组件 | 类型 | 说明 |
|------|------|------|------|
| userId | 人员选择 | number | 按人员 |
| relationType | Select | EffRelationType | 全部（默认）/主归属/兼职 |
| targetType | Select | EffTargetType | 全部/IP 组/团队/账号 |
| targetId | 目标选择 | number | 目标类型选定后联动 |
| status | Select | EffRelationStatus | 全部（默认）/生效/历史 |

## 6. 表格列定义

| 列 | 字段 | 渲染 |
|----|------|------|
| 人员 | userName | 文本（同人多行分组底色） |
| 部门 | deptName | 文本 |
| 归属类型 | relationType | PRIMARY 蓝 Tag"主归属" / PART_TIME 紫 Tag"兼职" |
| 归属目标 | targetType/targetName | `IP组 · 华东一组`（类型前缀 + 名称） |
| 分摊比例 | shareRatio | `100%` / `20%` 右对齐 |
| 生效期间 | effectiveFrom/effectiveTo | `01-01 ~ 至今`（ACTIVE）或 `02-15 ~ 05-31`（HISTORICAL 灰） |
| 状态 | status | ACTIVE 绿"生效" / HISTORICAL 灰"历史"（行删除线样式） |
| 变更人/时间 | changedByName/changedAt | 小字两行 |
| 操作 | — | 变更（ACTIVE，R2/R1）/ 时间线 / 删除（R1 误操作） |

## 7. 抽屉/弹窗规格

### 7.1 归属建立抽屉（Drawer，右滑 560px，R2/R1）

- **表单**：人员选择（搜索联想）→ 展示该人员**当前归属概览卡**（既有主归属 + 兼职列表 + 合计比例 `当前合计 {totalShareRatio}%`，信息来自 timeline 接口 currentRelations）；归属类型 Radio（主归属/兼职）；目标类型 Select（IP 组/团队/账号——复用 IP 组管理既有数据）→ 目标选择器联动；分摊比例 InputNumber（PRIMARY 锁定 100 只读；PART_TIME 输入后**实时合计预校验** `{现有合计 + 本次} ≤ 100%`，越界红色禁用保存，对应 1199）；生效起始日 DatePicker（默认今日）。
- 保存 → `POST /eff/relation`；1198/1199 分支红字定位。

### 7.2 归属变更抽屉（Drawer，右滑 560px，R2/R1）

- **头部**：当前关系摘要（人员/类型/目标/比例/生效起）。
- **变更动作** Radio：
  - TRANSFER 调岗：新目标选择器（同类型内换目标）；
  - TO_PART_TIME 转兼职：新分摊比例 InputNumber（实时合计校验）；
  - TERMINATE 终止：无附加字段（离职场景走 V1 事件自动失效 EFF-R4，此处为手动终止）。
- 变更生效日 DatePicker + 变更原因 Input（选填）。
- **时间段预览**：底部实时预览 `旧关系：…~{effectiveDate}（封口）` + `新关系：{effectiveDate}~（生效）`——直观展示时间段留痕语义（EFF-R2）。
- 保存 → `PUT /eff/relation/{id}` → toast "变更已生效，历史归属保留（时间段留痕）"。

### 7.3 未覆盖督办弹窗（Modal，720px，R1/R2）

- `GET /eff/relation/uncovered` 分页表：[人员 | 部门 | 岗位 | 入职日期 | **未覆盖天数**（>7 天红色）]。
- 头部提示："覆盖率须达 100% 方可通过盘点发布（BR-207/EFF-M-R4）；未覆盖人员每日督办"。
- 行操作 [去建立归属] → 打开 §7.1 抽屉并预填该人员。
- 支持导出清单（前端 xlsx）。

### 7.4 归属时间线抽屉（Drawer，右滑 640px）

- **头部**：人员姓名 + 部门 + **当前生效概览**（主归属 Tag + 兼职 Tag 组 + 合计 `{totalShareRatio}%` ≤100 校验色）。
- **纵向 Timeline**（timeline 数组）：每节点 `{类型 Tag} {目标名} {shareRatio}% · {effectiveFrom} ~ {effectiveTo|至今} · {status Tag}`；HISTORICAL 节点灰显；节点附变更人/时间小字。
- 只读（回溯视图，人效按时间段归属计算的依据展示）。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 参数校验（PRIMARY 必须 100） | 抽屉红字（前端锁定预校验） |
| 1198 | 主归属冲突（唯一主归属） | 抽屉红字 + 既有主归属信息展示 |
| 1199 | 兼职分摊合计 >100% | 实时合计预校验 + 服务端兜底红字 |
| 人员离职后变更 | 服务端拒绝 | toast "离职人员归属已自动失效（EFF-R4）" |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-207（覆盖率 100% + 督办） | 覆盖率卡 + 未覆盖督办弹窗（+P2 发布阻断联动） |
| BR-213（唯一主归属 + 分摊 ≤100） | 1198/1199 + 实时合计校验 |
| EFF-R1（在职唯一主归属） | 建立抽屉冲突展示 |
| EFF-R2（变更时间段留痕） | 变更抽屉时间段预览 + 时间线抽屉 |
| EFF-R3（覆盖率口径与督办） | 覆盖率卡口径文案 |
| EFF-R4（离职自动失效） | 删除弹窗警示文案 + 错误处理 |

---

# P2 人效指标配置与盘点（EFF-002）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/eff/metrics`（菜单：组织人效 → 指标盘点） |
| 页面级别 | 二级（两 Tab：指标配置 / 盘点报告） |
| 前置依赖 | P1 归属数据；当月绩效已发布（每月 2 日盘点前置，EFF-M-R2） |
| 权限 | 指标配置：R4/R1/R2；盘点报告发布前：R1/R2/R4；裁决发布：R4；看板：见 P3 |
| 用户 | 运营总监 R4（裁决）/ 人事 R2 / 超管 R1 |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 人效指标盘点                                                              │
│ ┌─[指标配置]─┬─[盘点报告]────────────────────────────────┐               │
│ │                                                        │               │
│ │  ◆ Tab1 指标配置（GET /eff/metrics/list）               │               │
│ │  QueryBar: [指标名称 Input][状态 Select] [+ 创建指标]   │               │
│ │  [指标编码|名称|取数映射|计算表达式|状态|操作: 编辑]     │               │
│ │                                                        │               │
│ │  ◆ Tab2 盘点报告（GET /eff/metrics/{period}/report）    │               │
│ │  顶部: [周期 MonthPicker][手动触发盘点][裁决发布(R4)]   │               │
│ │  状态条: 计算中 {n} | 待裁决 {m} | 已发布 {k}           │               │
│ │  覆盖率前置卡: 96.8% ⚠ → 发布按钮禁用 + 阻断提示        │               │
│ │  QueryBar: [维度 Select:人员/团队/IP组/部门]            │               │
│ │  报告表: [维度|指标|指标值(¥)|维度内排名|环比|发布状态]  │               │
│ └────────────────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
// ===== 枚举（契约内联） =====
type EffDimensionType = 'PERSON' | 'TEAM' | 'IP_GROUP' | 'DEPT';
type EffPublishStatus = 'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED';

// ===== 请求 =====
interface EffMetricQueryReq extends PageParam {
  metricName?: string;
  status?: EnableStatus;
}

interface EffMetricSaveReq {
  metricCode: string;                    // 如 EFF_GMV_PER_CAPITA
  metricName: string;
  /** 取数映射（10/15/11 台账字段+口径） */
  sourceConfig: {
    module: 'LIVE' | 'CONTENT' | 'FINANCE';
    metricExpression: string;            // 如 'SUM(gmv)'
  };
  /** 计算表达式（如 人均GMV = ΣGMV×分摊比例 / 在职人数） */
  calcExpr: string;
  status?: EnableStatus;
}

interface EffRunReq {
  periodMonth: string;
  scope?: { dimensionTypes?: EffDimensionType[] };
}

interface EffApproveReq {
  approve: boolean;
  remark?: string;
}

interface EffReportQueryReq extends PageParam {
  dimensionType?: EffDimensionType;
}

// ===== 响应 =====
interface EffMetricConfigVO extends EffMetricSaveReq {
  id: number;
}

interface EffRunResp {
  batchId: string;
  targetDimensionCount: number;
  message: string;                       // 每月 2 日自动触发（绩效后执行）
}

interface EffResultVO {
  id: number;
  periodMonth: string;
  dimensionType: EffDimensionType;
  dimensionId: number;
  dimensionLabel: string;
  metricId: number;
  metricCode: string;
  metricName: string;
  metricValue: number;                   // 金额类 ¥ 千分位
  rankNo: number;                        // 维度内排名
  momChangeRate?: number;                // 环比上期
  publishStatus: EffPublishStatus;
  /** 归属分摊与取数快照（EFF-M-R1 周期分段加权） */
  calcSnapshot: Record<string, unknown>;
}
```

## 4. 交互流程

**页面加载**：默认 Tab1 指标配置 `GET /eff/metrics/list`；Tab2 切换时按周期加载报告。

**核心操作（Tab1 指标配置）**：
- **创建/编辑指标**（R4/R1/R2）：抽屉（§7.1）→ `POST /eff/metrics/metric` / `PUT /eff/metrics/metric/{id}`；指标编码已存在返回 1001（参数校验族——编码重复） → 编码红字；表达式非法（非白名单台账字段/四则运算）1001 → 编辑器红字。**编辑生效于下一盘点周期（历史盘点快照不受影响）**——保存 toast 提示。

**核心操作（Tab2 盘点报告）**：
- **周期切换**：MonthPicker → `GET /eff/metrics/{period}/report`（dimensionType 筛选）。
- **手动触发盘点**（R4/R1/R2，补算定位）：ConfirmDialog（周期 + 可选维度范围）→ `POST /eff/metrics/run` → toast `盘点任务 {batchId} 已创建（{targetDimensionCount} 个维度）`；**前置依赖校验**：当月绩效结果未发布返回 1199 段内复用 → Dialog "人效盘点依赖当月绩效结果发布（EFF-M-R2：每月 2 日绩效计算后执行），请先完成绩效核准"。
- **裁决发布**（R4）：报告区顶部 [裁决发布]（PENDING_APPROVE 状态时可用）→ 裁决抽屉（§7.2）→ `PUT /eff/metrics/{period}/approve`：
  - **覆盖率阻断（BR-207/EFF-M-R4）**：发布前实时校验 `GET /eff/relation/coverage`；coverageRate < 100 → 发布按钮禁用 + 红色提示条 "覆盖率 {rate}% 未达 100%，阻断发布（BR-207）→ [查看未覆盖清单]"（跳 P1 §7.3 督办弹窗）；服务端兜底返回 1198（覆盖率拦截，与主归属冲突共用 1198 拦截族时以 msg 区分语义）。
  - 发布成功 → PUBLISHED → toast "已发布 {publishedCount} 项，人效看板已更新" → 员工可见本人维度（P4 联动）。
  - 驳回 → approve=false → 退回修正（CALCULATING，remark 留痕）。
- **CALCULATING 轮询**：30 秒轮询刷新至离开计算中状态（每月 2 日 V2-A1 自动触发）；计算失败转人工兜底不阻塞发布流程（V3 9.3）——失败项在报告中标"人工兜底"Tag，可继续裁决发布其余项。
- **可见性**：发布前仅 R1/R2/R4 可见（EFF-M-R3）；R5/R6/R7 访问报告 Tab 服务端返回空/引导至 P4。

## 5. 查询条件表

| Tab | 字段 | 组件 | 说明 |
|-----|------|------|------|
| Tab1 | metricName / status | Input / Select | 指标名 / 启停 |
| Tab2 | periodMonth | MonthPicker | 盘点周期（path 参数） |
| Tab2 | dimensionType | Select | 人员/团队/IP 组/部门 |

## 6. 表格列定义

**Tab1 指标配置**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 指标编码 | metricCode | code 样式（EFF_ 前缀） |
| 指标名称 | metricName | 文本（人均 GMV/人均净利润/人均场次/人均内容产出/人均涨粉） |
| 取数映射 | sourceConfig | `LIVE · SUM(gmv)`（模块 Tag + 表达式） |
| 计算表达式 | calcExpr | 等宽字体（如 `ΣGMV×分摊比例 / 在职人数`） |
| 状态 | status | ENABLED 绿 / DISABLED 灰 |
| 操作 | — | 编辑 |

**Tab2 盘点报告**：

| 列 | 字段 | 渲染 |
|----|------|------|
| 维度 | dimensionLabel | 前缀 Tag（人员/团队/IP 组/部门） |
| 指标 | metricName | 文本（metricCode 小字） |
| 指标值 | metricValue | 金额类 ¥ 千分位两位小数右对齐；R9 成本/利润类 "—" |
| 维度内排名 | rankNo | `第 {n} 名`（前三徽标） |
| 环比 | momChangeRate | `+12.3%` 绿 ↑ / `-5.1%` 红 ↓ / "—" |
| 发布状态 | publishStatus | CALCULATING 蓝 / PENDING_APPROVE 橙 / PUBLISHED 绿；人工兜底项附灰 Tag |
| 快照 | calcSnapshot | [查看] → Tooltip/子弹窗展示归属分摊与取数快照 JSON 摘要（EFF-M-R1） |

## 7. 抽屉/弹窗规格

### 7.1 指标编辑抽屉（Drawer，右滑 640px）

- **表单**：指标编码（创建可填/编辑只读）、指标名称、取数映射（模块 Select：LIVE/CONTENT/FINANCE + 表达式 Input，白名单提示 "仅支持 10/15/11 台账字段"）、计算表达式 TextArea（等宽字体，白名单字段按钮插入 + 四则运算；1001 表达式非法红字定位）、状态 Switch。
- 保存 toast："变更将于下一盘点周期生效，历史盘点快照不受影响"。

### 7.2 裁决发布抽屉（Drawer，右滑 640px，仅 R4）

- **结构**：
  1. **覆盖率前置卡**（阻断展示）：实时 coverageRate；=100% 绿 ✓ "覆盖率达标（BR-207）"；<100% 红 ✗ "阻断发布" + [查看未覆盖清单]（跳 P1 督办）。
  2. **盘点摘要**：周期 / 待裁决 {m} 项 / 维度分布 / 异常（人工兜底 {n} 项）。
  3. 审批意见 remark TextArea（驳回必填）。
  4. 底部：[驳回（退回修正）] [裁决发布]（覆盖率未达标时禁用）。
- 发布 → `PUT /eff/metrics/{period}/approve` → `{publishedCount, publishedAt}` → 成功 toast + 跳 P3 看板引导。

## 8. 错误处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| 1001 | 指标编码已存在 / 表达式非法（白名单外字段/运算） | 编码红字 / 编辑器红字 |
| 1198 | 覆盖率不足阻断发布 / 主归属冲突（msg 区分） | 阻断提示条 + 督办跳转 / 抽屉红字 |
| 1199 | 前置依赖：绩效未发布 / 兼职分摊合计 >100% | Dialog 解释 EFF-M-R2 前置链 / 红字定位 |
| 轮询失败 | CALCULATING | 静默重试 3 次后提示手动刷新 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-207（覆盖 100% 方可发布） | 裁决抽屉覆盖率前置卡 + 发布禁用 + 督办跳转 |
| EFF-M-R1（台账×分摊周期分段加权） | calcSnapshot 快照列 |
| EFF-M-R2（每月 2 日绩效后执行） | 手动触发前置依赖 Dialog + 定位说明 |
| EFF-M-R3（发布前仅 R1/R2/R4） | Tab2 权限过滤 |
| EFF-M-R4（未覆盖阻断发布） | 裁决抽屉阻断卡 |
| 9.1 性能（单次 <30 分钟） | 自动触发说明文案 |
| 9.3 可用性（失败转人工不阻塞） | 人工兜底 Tag + 可继续发布 |
| V2-A1（集群化调度） | 自动任务说明 |

---

# P3 人效看板（EFF-002 组织对比）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/eff/board`（菜单：组织人效 → 人效看板） |
| 页面级别 | 二级（聚合看板） |
| 前置依赖 | 当期盘点已发布（P2 裁决发布后更新） |
| 权限 | 查看：R1/R2/R3（成本/利润维度）/R4/R9（脱敏）/R5/R6（发布后团队维度） |
| 用户 | 管理层（组织对比决策） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 人效看板  [周期: 2025-05 ▾][维度 Select: IP组/团队/部门][指标多选        │
│ Checkbox: 人均GMV·人均净利润·人均场次·人均内容产出·人均涨粉]             │
│ 数据截至 {dataAsOf}（发布时点）                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ ◆ 组织对比矩阵（GET /eff/metrics/board）                                  │
│ ┌──────────┬──────────┬──────────┬──────────┬──────────┐                │
│ │ 维度      │人均GMV    │人均净利润 │人均场次   │排名徽章    │               │
│ ├──────────┼──────────┼──────────┼──────────┼──────────┤                │
│ │华东一组   │¥286,000  │¥52,300   │ 18.2     │ 🥇1      │                │
│ │          │(+12.3%↑) │(+8.1%↑)  │(+2.1%↑)  │          │                │
│ │华南二组   │¥198,000  │—(R9脱敏) │ 15.4     │ 🥈2      │                │
│ └──────────┴──────────┴──────────┴──────────┴──────────┘                │
│ 矩阵单元格: 值 + 环比(momChangeRate 涨绿跌红)；点击列头按该指标排序       │
│ 排名徽章: 取所选首要指标 rank                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. TypeScript 类型定义

```typescript
interface EffBoardReq {
  periodMonth: string;
  dimensionType: 'IP_GROUP' | 'TEAM' | 'DEPT';
  metricCodes?: string[];
}

interface EffBoardResp {
  periodMonth: string;
  dimensionType: string;
  comparisons: Array<{
    dimensionLabel: string;
    metrics: Array<{
      metricCode: string;
      metricName: string;
      value: number | null;              // R9 成本/利润类脱敏 null → "—"
      rank: number;
      momChangeRate?: number | null;
    }>;
  }>;
  dataAsOf: string;
}
```

## 4. 交互流程

**页面加载**：`GET /eff/metrics/board`（默认最近已发布周期 + IP 组维度 + 全部指标）。

**核心交互**：
- 周期/维度/指标切换 → 重新拉取（周期下拉仅列出已发布周期）。
- **矩阵渲染**：行 = 组织维度，列 = 所选指标；单元格 = 值（金额 ¥ 千分位）+ 环比（涨绿 ↓红）；列头点击排序；R9 视角成本/利润类 null → "—"。
- **未发布周期**：空态 "本期盘点尚未发布（R4 裁决发布后看板更新）"。
- R5/R6 登录：维度服务端过滤为本人所属团队维度（发布后可见）。

## 5. 查询条件表

| 字段 | 组件 | 说明 |
|------|------|------|
| periodMonth | MonthPicker | 仅已发布周期可选 |
| dimensionType | Select | IP 组/团队/部门 |
| metricCodes | Checkbox 组 | 指标多选（默认全选） |

## 6. 表格列定义

动态矩阵：首列维度名；其后每个指标一列（值 ¥/数字 + 环比双色 + rank 小徽章）；R9 脱敏列 "—"。

## 7. 抽屉/弹窗规格

无抽屉（纯看板）；可扩展跳转 P2 报告（点击维度行 → 报告 Tab 预置该维度筛选）。

## 8. 错误处理

| 场景 | 处理 |
|------|------|
| 周期未发布 | 空态引导 |
| 无权限维度 | 服务端过滤，前端不渲染 |
| 接口失败 | 常规 toast + 保留筛选条件重试 |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| BR-207（发布联动） | 未发布周期空态 |
| EFF-M-R3（发布后可见性） | 周期可选范围 + 角色过滤 |
| 9.2 安全（R9 脱敏） | 成本/利润类 null → "—" |

---

# P4 我的人效（工作台卡片 + H5）

## 1. 页面概述

| 项 | 内容 |
|----|------|
| 路由 | `/h5/eff/mine`（工作台"我的人效"卡片进入） |
| 页面级别 | H5 页面 + 工作台卡片摘要 |
| 前置依赖 | 当期盘点已发布（发布前不可见，EFF-M-R3） |
| 权限 | R5/R6/R7（本人与所属团队维度，发布后） |
| 用户 | 全员员工（本人人效视角） |

## 2. 页面布局（ASCII）

```
┌──────────────────────────────┐ H5
│ ┌──────────────────────────┐ │
│ │ 2025-05 我的人效          │ │  周期切换（仅已发布周期）
│ │  人均GMV   ¥286,000      │ │  myMetrics 卡片组
│ │           团队内 第 2 名  │ │  value + rankInTeam
│ │  人均场次    18.2         │ │
│ │           团队内 第 4 名  │ │
│ │  ...                     │ │
│ ├──────────────────────────┤ │
│ │ 我的团队 · 剪辑A组        │ │  teamMetrics
│ │  人均GMV   ¥212,000      │ │  团队维度对比（无他人明细，
│ │  人均场次   15.4         │ │  仅团队聚合值）
│ └──────────────────────────┘ │
└──────────────────────────────┘
工作台卡片（Web 同构摘要）：首要指标 + 排名 + [查看明细]
```

## 3. TypeScript 类型定义

```typescript
interface EffMineResp {
  myMetrics: Array<{ metricCode: string; metricName: string; value: number; rankInTeam: number }>;
  teamMetrics: Array<{
    teamName: string;
    metrics: Array<{ metricCode: string; value: number }>;
  }>;
}
```

## 4. 交互流程

**页面加载**：`GET /eff/metrics/mine`（默认最近已发布周期；R7 限本人）。
- 未发布周期空态："本期人效盘点尚未发布，发布后可见（EFF-M-R3）"。
- 周期切换仅已发布周期。
- 团队维度仅显示聚合值（无他人明细，隐私同 V2 绩效排名口径）。

## 5~7. 查询条件表 / 表格列定义 / 抽屉

查询条件：periodMonth（已发布周期）。无表格/抽屉（卡片列表视图：指标名 | 值（¥ 千分位）| 团队内排名徽章）。

## 8. 错误处理

| 场景 | 处理 |
|------|------|
| 未发布周期 | 空态说明（EFF-M-R3） |
| 无归属人员（未覆盖） | 空态 "您尚未纳入人效统计（归属关系未建立），请联系 HR" |

## 9. BR 业务规则覆盖

| 规则 | 落点 |
|------|------|
| EFF-M-R3（发布后本人可见） | 未发布空态 + 周期过滤 |
| BR-213（按归属计算） | 未归属人员空态提示 |

---

# 附录 A：模块级约定

1. **唯一主归属（BR-213/EFF-R1）**：PRIMARY shareRatio 固定 100（前端锁定 + 1001 兜底）；同人唯一 ACTIVE 主归属（1198 冲突展示既有归属）；兼职合计 ≤ 100（建立/转兼职实时合计预校验 + 1199 兜底）。
2. **时间段留痕（EFF-R2）**：正常变更一律走变更接口（旧关系封口 + 新记录生成），变更抽屉提供时间段预览；物理删除仅 R1 误操作场景（红色警示区分）；离职自动失效（EFF-R4，V1 事件联动）；时间线抽屉为回溯视图。
3. **覆盖率闭环（BR-207/EFF-R3/EFF-M-R4）**：P1 覆盖率卡与未覆盖督办（每日督办清单）→ P2 裁决抽屉覆盖率前置卡（<100% 发布禁用 + 督办跳转）→ 服务端 1198 兜底（覆盖率拦截）；覆盖 = 已建归属且纳入人效人数 / 在职总人数。
4. **盘点链路（EFF-M-R2）**：每月 2 日自动触发（绩效计算后执行，前置依赖当月绩效发布，1199 拦截未就绪）；手动触发为补算定位；单次 <30 分钟（9.1）；V2-A1 集群化调度。
5. **兜底可用性（V3 9.3）**：计算失败项转人工兜底、标记展示、不阻塞整体裁决发布。
6. **发布可见性（EFF-M-R3）**：CALCULATING → PENDING_APPROVE → PUBLISHED；发布前仅 R1/R2/R4；发布后 P3 看板（R5/R6 团队维度）与 P4 本人（R7 限本人）开放——模式与 V2 绩效快照发布一致。
7. **指标口径纪律**：sourceConfig 仅支持 10/15/11 台账模块白名单字段；calcExpr 白名单表达式（1001 拦截）；指标变更下一周期生效（历史快照不受影响）。
8. **R9 脱敏**：成本/利润类人效指标（人均净利润等）服务端 null → "—"；报表/看板统一渲染约定。
9. **既有能力复用**：IP 组管理已完成——归属目标选择器（IP_GROUP 类型）直接消费既有 IP 组数据，不重复建设。

# 附录 B：BR / EFF 规则 ↔ 页面落点总表

| 规则 | 内容 | 页面落点 |
|------|------|----------|
| BR-207 | 覆盖率 100% + 未覆盖督办 + 阻断发布 | P1 覆盖率卡/督办弹窗、P2 裁决阻断卡 |
| BR-213 | 唯一主归属 + 兼职分摊 ≤100 | P1 建立抽屉 1198/1199 + 实时合计 |
| EFF-R1 | 在职唯一主归属 | 1198 冲突展示 |
| EFF-R2 | 变更时间段留痕 | 变更抽屉预览 + 时间线抽屉 |
| EFF-R3 | 覆盖率口径与督办 | 覆盖率卡口径 + 督办清单 |
| EFF-R4 | 离职自动失效 | 删除警示 + 错误处理 |
| EFF-M-R1 | 台账×分摊周期分段加权 | calcSnapshot 快照列 |
| EFF-M-R2 | 每月 2 日绩效后执行 | 前置依赖 Dialog |
| EFF-M-R3 | 发布前仅 R1/R2/R4 | Tab2 权限 + P3/P4 空态 |
| EFF-M-R4 | 覆盖 100% 方可发布 | 裁决抽屉阻断 |
| 9.1 性能 | 单次 <30 分钟 | 说明文案 |
| 9.3 可用性 | 失败转人工不阻塞 | 人工兜底 Tag |
| 9.2 安全 | 裁决审计 + R9 脱敏 | 裁决留痕 + null "—" |
| V2-A1 | 集群化调度 | 自动任务说明 |

（全文完）
