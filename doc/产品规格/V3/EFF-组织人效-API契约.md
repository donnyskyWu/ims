# EFF - 组织人效 API 契约

> **模块范围**：19 组织人效（V3 增量，第 32~38 周，P2）——EFF-001 人员归属关系、EFF-002 人效指标盘点。**补齐类**：IP 组管理已完成（不重复建设），本次仅补齐人员归属与人效盘点。
> **权威依据**：《IMS第三期PRD-V3.md》5.10~5.11；BR-207、BR-213；V3 里程碑 M4（第 32~38 周）。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》第 3/4 章（EFF 域 1198~1199，与 BI 共段 1191~1199：BI 占 1191~1197、EFF 占 1198/1199）；字段 camelCase（`relation_type → relationType`、`share_ratio → shareRatio`）；周次波浪号格式。**关键口径**：在职唯一主归属（BR-213），兼职分摊比例合计 ≤ 100%；归属变更时间段留痕（人效按时间段归属计算）；覆盖率 = 100% 方可通过盘点发布（BR-207，未覆盖阻断发布）；人效计算失败转人工兜底不阻塞发布流程（V3 9.3）。

---

## 1. API 总览表（共 15 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/eff/relation/list` | 归属关系列表（分页） | R1/R2/R4/R9/R5/R6/R7（本人归属） |
| 2 | POST | `/admin-api/ims/eff/relation` | 建立归属（主归属/兼职） | R2（主责）/R1 |
| 3 | PUT | `/admin-api/ims/eff/relation/{id}` | 变更归属（时间段留痕） | R2/R1 |
| 4 | DELETE | `/admin-api/ims/eff/relation/{id}` | 删除（误操作） | R1 |
| 5 | GET | `/admin-api/ims/eff/relation/timeline/{userId}` | 人员归属时间线 | 同 1 |
| 6 | GET | `/admin-api/ims/eff/relation/coverage` | 覆盖率统计（BR-207） | R1/R2/R4/R9 |
| 7 | GET | `/admin-api/ims/eff/relation/uncovered` | 未覆盖人员清单（督办） | R1/R2 |
| 8 | GET | `/admin-api/ims/eff/metrics/list` | 人效指标配置列表（分页） | R1/R2/R3/R4/R9 |
| 9 | POST | `/admin-api/ims/eff/metrics/metric` | 创建指标 | R4/R1/R2 |
| 10 | PUT | `/admin-api/ims/eff/metrics/metric/{id}` | 编辑指标 | R4/R1/R2 |
| 11 | POST | `/admin-api/ims/eff/metrics/run` | 手动触发盘点（月度） | R4/R1/R2 |
| 12 | GET | `/admin-api/ims/eff/metrics/{period}/report` | 周期盘点报告（含排名环比） | R1/R2/R4（发布前）；发布后本人/团队 |
| 13 | PUT | `/admin-api/ims/eff/metrics/{period}/approve` | 裁决发布 | R4 |
| 14 | GET | `/admin-api/ims/eff/metrics/board` | 人效看板（组织对比） | R1/R2/R3/R4/R9（脱敏）/R5/R6（发布后团队） |
| 15 | GET | `/admin-api/ims/eff/metrics/mine` | 本人/所属团队人效 | R5/R6/R7（发布后本人） |

---

## 2. 接口明细

### 2.1 人员归属关系（EFF-001）

#### 2.1.1 GET /admin-api/ims/eff/relation/list — 归属关系列表（分页）

**请求**（Query）：`PageParam` + `{ userId?: number; relationType?: 'PRIMARY' | 'PART_TIME'; targetType?: 'IP_GROUP' | 'TEAM' | 'ACCOUNT'; targetId?: number; status?: 'ACTIVE' | 'HISTORICAL' }`

**响应** `data`：`PageResult<EffRelationVO>`

```typescript
interface EffRelationVO {
  id: number;
  userId: number;
  userName: string;
  deptName: string;
  /** 1 主归属 / 2 兼职归属 */
  relationType: 'PRIMARY' | 'PART_TIME';
  /** 归属目标：1 IP 组 / 2 团队 / 3 账号 */
  targetType: 'IP_GROUP' | 'TEAM' | 'ACCOUNT';
  targetId: number;
  targetName: string;
  /** 分摊比例 DECIMAL(5,2)：主归属 = 100；兼职合计 ≤ 100（BR-213） */
  shareRatio: number;
  effectiveFrom: string;         // yyyy-MM-dd（归属起止，时间段留痕）
  effectiveTo?: string;
  status: 'ACTIVE' | 'HISTORICAL';
  changedBy: number;
  changedByName: string;
  changedAt: string;
}
```

#### 2.1.2 POST /admin-api/ims/eff/relation — 建立归属

**请求**：

```typescript
interface EffRelationCreateReq {
  userId: number;
  relationType: 'PRIMARY' | 'PART_TIME';
  targetType: 'IP_GROUP' | 'TEAM' | 'ACCOUNT';
  targetId: number;
  shareRatio: number;            // PRIMARY 固定 100
  effectiveFrom: string;         // yyyy-MM-dd
}
```

**响应** `data`：`EffRelationVO`。

**错误码**：1198（主归属冲突——在职人员唯一主归属，BR-213/EFF-R1）、1199（兼职分摊比例合计超 100%）、1001（参数校验：PRIMARY 必须 shareRatio=100）。

#### 2.1.3 PUT /admin-api/ims/eff/relation/{id} — 变更归属（时间段留痕）

**请求**：

```typescript
interface EffRelationChangeReq {
  /** 变更动作：调岗（换目标）/转兼职/失效 */
  action: 'TRANSFER' | 'TO_PART_TIME' | 'TERMINATE';
  newTargetId?: number;          // TRANSFER 时必填
  newShareRatio?: number;        // TO_PART_TIME 时必填
  /** 旧关系在 effectiveTo 生效（历史保留，人效按时间段计算，EFF-R2） */
  effectiveDate: string;
  changeReason?: string;
}
```

**响应** `data`：`{ oldRelationId: number; oldEffectiveTo: string; newRelationId?: number }`（变更生成新时间段记录，历史保留供回溯）。

#### 2.1.4 DELETE /admin-api/ims/eff/relation/{id} — 删除（误操作）

**响应**：`data: null`（仅误操作场景物理删除；正常变更一律走 2.1.3 时间段留痕）。

#### 2.1.5 GET /admin-api/ims/eff/relation/timeline/{userId} — 归属时间线

**响应** `data`：

```typescript
interface EffRelationTimelineResp {
  userId: number;
  userName: string;
  timeline: Array<{
    relationId: number;
    relationType: 'PRIMARY' | 'PART_TIME';
    targetName: string;
    targetType: string;
    shareRatio: number;
    effectiveFrom: string;
    effectiveTo?: string;
    status: 'ACTIVE' | 'HISTORICAL';
    changedByName: string;
    changedAt: string;
  }>;
  /** 当前生效归属概览（主+兼职） */
  currentRelations: EffRelationVO[];
  totalShareRatio: number;       // 合计 ≤ 100 校验展示
}
```

#### 2.1.6 GET /admin-api/ims/eff/relation/coverage — 覆盖率（BR-207）

**响应** `data`：`{ activeEmployeeCount: number; coveredCount: number; coverageRate: number; target: 100; isBlocking: boolean }`（覆盖率 = 已建归属且纳入人效人数/在职总人数，目标 = 100%，BR-207/EFF-R3；不足 100% 时阻断盘点发布）。

#### 2.1.7 GET /admin-api/ims/eff/relation/uncovered — 未覆盖人员清单（分页）

**响应** `data`：`PageResult<{ userId: number; userName: string; deptName: string; positionName: string; onboardingDate: string; uncoveredDays: number }>`（未覆盖人员每日督办，EFF-R3）。

### 2.2 人效指标盘点（EFF-002）

#### 2.2.1 GET /admin-api/ims/eff/metrics/list — 指标配置列表（分页）

**请求**（Query）：`PageParam` + `{ metricName?: string; status?: 'ENABLED' | 'DISABLED' }`

**响应** `data`：`PageResult<EffMetricConfigVO>`

```typescript
interface EffMetricConfigVO {
  id: number;
  metricCode: string;            // 如 EFF_GMV_PER_CAPITA
  metricName: string;
  /** 取数映射（10/15/11 台账字段+口径） */
  sourceConfig: {
    module: 'LIVE' | 'CONTENT' | 'FINANCE';
    metricExpression: string;    // 如 'SUM(gmv)'
  };
  /** 计算表达式（如 人均GMV = ΣGMV×分摊比例 / 在职人数） */
  calcExpr: string;
  status: 'ENABLED' | 'DISABLED';
}
```

#### 2.2.2 POST /admin-api/ims/eff/metrics/metric — 创建指标

**请求**：`Omit<EffMetricConfigVO, 'id'>` → **响应** `data`：`EffMetricConfigVO`。

**错误码**：1001（指标编码已存在——编码重复归参数校验族；表达式非法：仅支持白名单台账字段与四则运算）。

#### 2.2.3 PUT /admin-api/ims/eff/metrics/metric/{id} — 编辑指标

**请求**：同创建 → **响应** `data`：`EffMetricConfigVO`。生效于下一盘点周期（历史盘点快照不受影响）。

#### 2.2.4 POST /admin-api/ims/eff/metrics/run — 手动触发盘点

**请求**：`{ periodMonth: string; scope?: { dimensionTypes?: Array<'PERSON' | 'TEAM' | 'IP_GROUP' | 'DEPT'> } }` → **响应** `data`：`{ batchId: string; targetDimensionCount: number; message: string }`（每月 2 日自动触发——绩效计算后执行，数据依赖绩效前置完成，EFF-M-R2；V2-A1 集群化调度；单次计算 < 30 分钟）。

**错误码**：1199（前置依赖拦截——当月绩效结果未发布，盘点不可执行，EFF-M-R2 前置校验）。

#### 2.2.5 GET /admin-api/ims/eff/metrics/{period}/report — 周期盘点报告（分页）

**请求**（Query）：`PageParam` + `{ dimensionType?: 'PERSON' | 'TEAM' | 'IP_GROUP' | 'DEPT' }`

**响应** `data`：`PageResult<EffResultVO>`

```typescript
interface EffResultVO {
  id: number;
  periodMonth: string;
  dimensionType: 'PERSON' | 'TEAM' | 'IP_GROUP' | 'DEPT';
  dimensionId: number;
  dimensionLabel: string;
  metricId: number;
  metricCode: string;
  metricName: string;
  metricValue: number;
  rankNo: number;                // 维度内排名
  /** 环比上期 */
  momChangeRate?: number;
  publishStatus: 'CALCULATING' | 'PENDING_APPROVE' | 'PUBLISHED';
  calcSnapshot: Record<string, unknown>;   // 归属分摊与取数快照
}
```

**可见性**：发布前仅 R1/R2/R4 可见（EFF-M-R3）；发布后 R5/R6/R7 可见本人与所属团队维度。

#### 2.2.6 PUT /admin-api/ims/eff/metrics/{period}/approve — 裁决发布

**请求**：`{ approve: boolean; remark?: string }` → **响应** `data`：`{ publishedCount: number; publishedAt: string }`（R4 裁决后发布，人效看板更新；**覆盖率 ≠ 100% 时阻断发布并督办**，EFF-M-R4/BR-207）。

**错误码**：1198（覆盖率拦截——覆盖率不足 100% 阻断发布并返回未覆盖清单引用，EFF-M-R4/BR-207；与主归属冲突共用 1198 拦截族时以 msg 区分语义）。

#### 2.2.7 GET /admin-api/ims/eff/metrics/board — 人效看板（组织对比）

**请求**（Query）：`{ periodMonth: string; dimensionType: 'IP_GROUP' | 'TEAM' | 'DEPT'; metricCodes?: string[] }` → **响应** `data`：`{ periodMonth: string; dimensionType: string; comparisons: Array<{ dimensionLabel: string; metrics: Array<{ metricCode: string; metricName: string; value: number | null; rank: number; momChangeRate?: number | null }> }>; dataAsOf: string }`（组织维度人效对比；R9 成本/利润类指标脱敏 null）。

#### 2.2.8 GET /admin-api/ims/eff/metrics/mine — 本人/所属团队人效

**请求**（Query）：`{ periodMonth?: string }` → **响应** `data`：`{ myMetrics: Array<{ metricCode: string; metricName: string; value: number; rankInTeam: number }>; teamMetrics: Array<{ teamName: string; metrics: Array<{ metricCode: string; value: number }> }> }`（发布后可见；R7 限本人）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**归属关系（EffRelationVO.status）**：

```
ACTIVE（生效中）──变更（TRANSFER/TO_PART_TIME）──▶ HISTORICAL（effectiveTo 封口）+ 新 ACTIVE 记录
        │
        └──离职联动（V1 离职事件）──▶ HISTORICAL（自动失效，历史保留供回溯，EFF-R4）
```

**盘点结果（EffResultVO.publishStatus）**：

```
CALCULATING（每月 2 日自动触发）──计算完成──▶ PENDING_APPROVE ──R4 裁决通过──▶ PUBLISHED
                                                    │                    │
                                                    └──驳回（退回修正）    └──覆盖率 ≠ 100% 阻断（EFF-M-R4）
计算失败 ──▶ 转人工兜底（不阻塞发布流程，V3 9.3）
```

**指标配置（status）**：`ENABLED ↔ DISABLED`（变更生效于下一盘点周期）。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-207 | 覆盖率 = 100%（未覆盖人员每日督办；阻断盘点发布） | 2.1.6 / 2.2.6 阻断 |
| BR-213 | 唯一主归属（100% 计入）+ 兼职按比例分摊（合计 ≤ 100%） | 2.1.2 错误码 1198/1199 |
| EFF-R1 | 在职唯一主归属 | 同上 |
| EFF-R2 | 变更生成新时间段（人效按时间段归属计算） | 2.1.3 / 2.1.5 |
| EFF-R3 | 覆盖率口径与督办 | 2.1.6 / 2.1.7 |
| EFF-R4 | 离职归属自动失效（联动 V1 离职事件） | 2.1.3 状态机 |
| EFF-M-R1 | 指标计算 = 台账数据 × 归属分摊（周期分段加权） | 2.2.5 calcSnapshot |
| EFF-M-R2 | 每月 2 日自动盘点（绩效计算后执行，数据前置依赖） | 2.2.4 |
| EFF-M-R3 | 发布前仅 R1/R2/R4 可见 | 2.2.5 可见性 |
| EFF-M-R4 | 覆盖 100% 方可发布（未覆盖阻断） | 2.2.6 错误码 |
| 9.1 性能 | 人效月度盘点计算单次 < 30 分钟 | 2.2.4 |
| 9.3 可用性 | 人效计算失败转人工兜底（不阻塞发布流程） | 2.2.4 兜底 |
| 9.2 安全 | 人效裁决全量审计；R9 脱敏 | 2.2.6 审计 / 2.2.7 脱敏 |
| V2-A1 | 盘点任务纳入集群化调度（Redisson 锁） | 2.2.4 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 归属关系管理页（QueryBar + 表格） | 归属关系列表查询（类型/目标/状态筛选） | GET /eff/relation/list |
| 归属建立抽屉（表单 + 目标选择器 + 比例校验） | 建立归属（主归属/兼职，比例实时合计校验） | POST /eff/relation |
| 归属变更操作 | 变更归属（调岗/转兼职/终止，时间段预览） | PUT /eff/relation/{id} |
| 误操作处理 | 删除（ConfirmDialog，正常变更走时间段） | DELETE /eff/relation/{id} |
| 人员归属时间线页（时间轴视图） | 归属时间线查看（历史分段+当前生效） | GET /eff/relation/timeline/{userId} |
| 覆盖率指标卡 | 覆盖率统计（BR-207，未达标阻断提示） | GET /eff/relation/coverage |
| 未覆盖督办页 | 未覆盖人员清单导出 | GET /eff/relation/uncovered |
| 人效指标配置页（QueryBar + 表格） | 指标列表查询 | GET /eff/metrics/list |
| 指标编辑抽屉 | 创建/编辑指标（取数映射+计算表达式） | POST /eff/metrics/metric、PUT /eff/metrics/metric/{id} |
| 盘点触发操作（R4/R1/R2） | 手动触发盘点（月度补算，ConfirmDialog） | POST /eff/metrics/run |
| 盘点报告页（发布前 R4 视角） | 周期盘点报告（维度切换 + 排名环比） | GET /eff/metrics/{period}/report |
| 盘点裁决页 | 裁决发布（覆盖率不足阻断提示） | PUT /eff/metrics/{period}/approve |
| 人效看板页（组织对比矩阵） | 人效看板（IP 组/团队/部门对比） | GET /eff/metrics/board |
| 个人工作台-我的人效 | 本人/所属团队人效（发布后） | GET /eff/metrics/mine |

（全文完）
