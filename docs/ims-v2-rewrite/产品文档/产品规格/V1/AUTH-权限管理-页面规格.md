# AUTH - 权限管理 页面规格

> 依据：《IMS第一期PRD-V1.md》5.1~5.4（AUTH-001~004）、《共享技术规范-数据库与API.md》第 7/8 章。
> **完整版叠加**：用户/角色/菜单/字典/参数/日志/通知见《SYS-系统管理-页面规格.md》；工作台待办源见《HOME-首页-页面规格.md》。SSO 仍在 IMS 内完成，不经 OPS。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/auth`。

> **统一权限中间件（B9 · 2026-10-05 决策）**：本模块是**角色权限载体**（角色/数据范围*配置*· 菜单与功能点权限定义）；数据范围（`ALL` / `DEPT` / `IP_GROUP` / `SELF`）与 `tenant_id` 行级隔离的**执行**统一在 **SYS-002「P2A 统一权限中间件」**（见《SYS-系统管理-页面规格》），本模块与各业务模块**禁止自行实现**数据范围过滤。口径详见该节。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 SSO 登录页 | `/login` | 独立全屏页（**非侧栏**） | AUTH-001 |
| P2 组织架构同步 | `/ims/auth/org` | **系统与权限 → 权限管理 → L3** | AUTH-002 |
| P3 岗位-角色供给规则 | `/ims/auth/position` | **系统与权限 → 权限管理 → L3** | AUTH-003 |
| P4 个人工作台 | `/ims/workbench` | **工作台** 组（登录后默认首页） | AUTH-004 |
| P4a 待办中心（全量） | `/ims/workbench/todos` | 工作台二级列表 | AUTH-004 |
| P4b 消息中心（全量） | `/ims/workbench/messages` | 工作台二级列表 | AUTH-004 |

> **用户/角色/菜单/字典/参数/日志/通知** 见《SYS-系统管理-页面规格.md》（**系统管理** L2，非本模块 Tab）。

### 0.1 侧栏信息架构（走查 #15）

默认进入 **权限管理 → 组织架构同步**（`authOrg`）。废止完整原型单页「权限管理」三 Tab 混排（原「用户权限」迁入 SYS-001 **用户** L3）。

```
系统与权限（L1 侧栏组）
└── 权限管理（L2 nav-sub-g）
    ├── 组织架构同步    /ims/auth/org          AUTH-002
    └── 岗位-角色规则    /ims/auth/position     AUTH-003
```

**不出 L3（无 IMS 页面 SSOT）**：独立「数据权限」菜单 —— **ADR-IMS-008（2026-10-04）**：数据范围 `dataScope` **并入 SYS-002 角色**（角色 = 权限唯一载体），不再由岗位模板承担；租户套餐 → SYS-008（《SYS-系统管理-页面规格》· ADR-IMS-007）。

通用 UI 约定（适用于本模块全部页面）：
- 查询条件一行紧凑排布；交互操作优先内联抽屉（Drawer），不跳转新页面；
- 敏感字段脱敏显示（手机号 138\*\*\*\*5678）；
- 状态列用语义色 tag（成功绿 / 进行中蓝 / 警告黄 / 失败红）；
- 金额 DECIMAL(12,2) 两位小数，前缀 ¥（本模块基本不涉及）。

---

## P1. SSO 登录页（AUTH-001）

### 1. 页面概述
- 路由路径：`/login`（未登录访问任意路由重定向至此）
- 页面级别：独立全屏页（无侧边栏/顶栏）
- 依赖模块：钉钉 OAuth2；`ims_auth_user_mapping`（首次登录即时同步，V1-A5）
- 权限矩阵引用（PRD 4.2）：全部 10 类角色 R/W（R10 外协受限登录，仅工作台）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
|                    （顶部 30% 留白 + IMS LOGO）                    |
+------------------------------------------------------------------+
|   +----------------------------------------------------------+   |
|   |              钉钉扫码登录（二维码 220x220）                 |   |
|   |              [二维码区]  刷新按钮（失效后出现）              |   |
|   +----------------------------------------------------------+   |
|   |   Tab: [ 扫码登录 ]  [ 钉钉内免登（H5 环境自动切换）]        |   |
|   |   使用钉钉账号安全登录 IMS 一体化管理系统                    |   |
|   +----------------------------------------------------------+   |
|   状态提示区（轮询中… / 已扫码，请在手机确认 / 登录失败原因）       |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface SsoCallbackReq {
  authCode: string;      // 钉钉授权码
  state: string;         // CSRF 防护，5 分钟有效
}
interface SsoRefreshReq {
  refreshToken: string;
}

// 响应类型
interface SsoSessionResp {
  accessToken: string;   // JWT
  refreshToken: string;
  expiresAt: string;     // ISO 8601
  userId: number;
  nickname: string;
  roles: string[];       // 角色编码数组
  deptName: string;
}

// 枚举类型
type SsoLoginState = 'POLLING' | 'SCANNED' | 'SUCCESS' | 'EXPIRED' | 'LOCKED' | 'FAILED';
```

### 4. 交互流程

#### 4.1 页面加载
1. 检测环境：Web → 展示二维码（`GET /admin-api/ims/auth/sso/redirect` 获取跳转/二维码地址）；H5（钉钉内）→ 自动走免登，静默换取 authCode 直接回调。
2. 二维码 2 分钟未扫码 → 置灰 + "点击刷新"；登录页自身展示骨架（LOGO + 二维码占位）。

#### 4.2 核心操作流程
1. 用户钉钉扫码 → 前端轮询状态（2s 间隔）变 `SCANNED` → 手机确认；
2. 钉钉回跳 `authCode` → 前端 `POST /admin-api/ims/auth/sso/callback` 换 JWT；
3. 成功：存储 Token → 跳转 `/ims/workbench`；
4. 分支：
   - a. 映射缺失（新员工首登）→ 后端即时同步（V1-A5）成功后正常签发；
   - b. 用户被锁定（连续失败 5 次锁 15 分钟，AUTH-R4）→ 提示"账号已锁定，请 15 分钟后重试"；
   - c. 离职冻结用户（ORG-R4）→ 提示"账号已冻结，请联系管理员"，不签发 Token；
   - d. 并发会话 > 3（AUTH-R3）→ 踢出最早会话，当前登录正常；
   - e. 钉钉接口超时（V1-A6）→ 提示"钉钉服务暂不可用，请稍后重试"。
5. Token 过期（2h）→ 前端拦截器静默 `POST /auth/sso/refresh`；刷新失败 → 回登录页。

### 5. 查询条件表
无（登录页无查询）。

### 6. 表格列定义
无（登录页无表格）。

### 7. 抽屉/弹窗规格
无抽屉。仅一个"登录失败原因"内联提示条（非弹窗，避免打断）。

### 8. 错误处理
- 网络超时：轮询静默重试 3 次，仍失败提示"网络异常，请检查网络后刷新二维码"；
- 钉钉服务异常（5003）：显示降级文案"钉钉服务暂不可用，组织数据可能延迟"；
- 二维码过期：置灰 + 刷新引导；
- 失败 5 次：按 AUTH-R4 锁定提示（展示剩余解锁时间倒计时）。

### 9. BR 业务规则覆盖
- **BR-002（SSO 成功率 > 99.5%）**：登录全链路埋点上报（成功/失败/失败原因），供运营数据平台指标统计；失败态均有明确文案与恢复路径（刷新/等待解锁/联系管理员）。

---

## P2. 组织架构同步页（AUTH-002）

### 1. 页面概述
- 路由路径：`/ims/auth/org`
- 页面级别：一级菜单页，含"人员列表 / 同步事件 / 对账报告"三个 Tab
- 依赖模块：钉钉集成（事件订阅 + 全量对账）、AUTH-003（入职套模板联动展示）
- 权限矩阵引用（PRD 4.2）：R1 R/W/D（全量，可手动对账/重放）；R2 R（本部门）；R4 R（全量只读）；其余角色不可见菜单

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [人员列表] [同步事件] [对账报告]        [手动对账] [重放失败事件] |
+------------------------------------------------------------------+
| 查询行: 姓名/工号 | 部门(树选) | 同步状态(下拉) | [查询] [重置]     |
+------------------------------------------------------------------+
| 表格: 姓名 | 工号 | 部门 | 岗位 | 钉钉绑定 | 同步状态 | 最近同步时间 | 状态 | 操作 |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
| 同步概览条（页面顶部固定）：人员总数 / 昨日事件 / 待处理事件 / 平均同步延迟 |
+------------------------------------------------------------------+
同步事件 Tab: 事件类型 | 事件ID | 人员 | 变更前部门→变更后部门 | 同步状态 | 同步时间 | 操作(重试/详情)
对账报告 Tab: 对账时间 | 差异数 | 修正数 | 失败明细 | 报告下载
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface OrgUserPageReq {
  pageNo: number;
  pageSize: number;
  keyword?: string;       // 姓名/工号模糊
  deptId?: number;
  syncStatus?: OrgSyncStatus;
}
interface OrgEventPageReq {
  pageNo: number;
  pageSize: number;
  eventType?: OrgEventType;
  syncStatus?: OrgSyncStatus;
  timeRange?: [string, string];
}
interface OrgReconcileReq { clientToken: string; }
interface OrgReplayReq { startTime: string; endTime: string; }

// 响应类型
interface OrgUserItem {
  userId: number;
  name: string;
  empNo: string;
  deptName: string;
  positionName: string;
  dingtalkBound: boolean;
  syncStatus: OrgSyncStatus;
  lastSyncTime: string;      // ISO 8601
  userStatus: 'ACTIVE' | 'FROZEN' | 'RESIGNED';
}
interface OrgEventItem {
  id: number;
  eventType: OrgEventType;
  dingtalkEventId: string;
  userName: string;
  beforeDept: string | null;
  afterDept: string | null;
  syncStatus: OrgSyncStatus;
  syncedAt: string | null;
}
interface SyncMetricsResp {
  totalUsers: number;
  yesterdayEvents: number;
  pendingEvents: number;
  avgSyncDelayMinutes: number;   // BR-001 目标 < 5
}
interface PageResp<T> { list: T[]; total: number; }

// 枚举类型
type OrgSyncStatus = 'PENDING' | 'SUCCESS' | 'FAILED_RETRY' | 'DEAD_LETTER';
// 口径说明：/auth/org/users 接口传输时 FAILED_RETRY/DEAD_LETTER 归并为 FAILED，另以 retryFlag/deadLetter 布尔标记区分（见 AUTH-API 契约 2.2.2）；前端渲染时由 FAILED + 标记位还原本四态枚举
type OrgEventType = 'hire' | 'transfer' | 'resign' | 'dept_change';
```

### 4. 交互流程

#### 4.1 页面加载
1. 骨架屏（同步概览条 + 表格占位）→ 并行请求 `GET /auth/org/users` + `GET /auth/org/sync-metrics`；
2. 任一失败 → 区域内"加载失败，点击重试"。

#### 4.2 核心操作流程
**A. 手动触发全量对账（仅 R1）**
1. 点击 [手动对账] → 二次确认弹窗"将拉取钉钉全量部门+人员比对修正，预计 1~3 分钟，确认执行？"；
2. `POST /callback/dingtalk/reconcile`（携带 clientToken 幂等）→ 按钮转 loading"对账中…"；
3. 成功 → 自动切到 [对账报告] Tab 展示最新报告 + 成功消息；
4. 失败 → 错误消息（5006 调度失败则提示稍后重试）。

**B. 重放失败事件（仅 R1）**
1. [重放失败事件] → 抽屉选择时间区间（默认近 24h）→ `POST /callback/dingtalk/retry-queue/replay`；
2. 提交后事件 Tab 中"失败重试"状态项逐条刷新。

**C. 查看事件详情（内联抽屉 Drawer，宽 480px）**
- 展示事件原文 payload（JSON 折叠树）+ 处理轨迹（入队→重试→成功/死信）；
- 失败/死信项提供 [重试本条] 按钮。

**D. 人员行下钻**
- 点击人员姓名 → 抽屉展示人员详情：基本信息、当前生效**角色（含来源角标）**与**岗位-角色供给规则**（AUTH-003 联动 · ADR-IMS-008）、权限概要（角色 + 关联功能域个数）、名下资产/账号数量汇总（链接到 ASSET/ACCT 反向穿透）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| keyword | Input | 否 | 空 | 姓名/工号模糊匹配 |
| deptId | TreeSelect | 否 | 空 | 部门树选择（**可选范围**：R1 全量 / R2 **本部门**（`DEPT`）；「本部门」**不含下级**——此为**筛选范围**，非数据范围配置项；行级过滤由统一权限中间件按 **BR-305** 执行） |
| syncStatus | Select | 否 | 空 | 待处理/成功/失败重试/死信 |
| eventType（事件Tab） | Select | 否 | 空 | 入职/调岗/离职/部门变更 |
| timeRange（事件Tab） | DateRangePicker | 否 | 近 7 天 | 同步时间区间 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| name | 姓名 | 100 | — | 可点击打开人员详情抽屉 |
| empNo | 工号 | 90 | — | — |
| deptName | 部门 | 160 | — | — |
| positionName | 岗位 | 120 | — | — |
| dingtalkBound | 钉钉绑定 | 90 | — | tag：已绑定(绿)/未绑定(灰) |
| syncStatus | 同步状态 | 110 | — | tag：成功(绿)/待处理(蓝)/失败重试(黄)/死信(红) |
| lastSyncTime | 最近同步时间 | 160 | ✓ | yyyy-MM-dd HH:mm |
| userStatus | 状态 | 90 | — | tag：在职(绿)/冻结(黄)/离职(灰) |
| actions | 操作 | 120 | — | [详情][同步事件] |

事件 Tab / 对账报告 Tab 列见布局图注释，同步状态列同上脱敏规范不涉及。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与逻辑 |
|-----------|------|-----------|
| 事件详情抽屉 | Drawer 480px | 只读：事件类型、事件 ID、人员、前后部门、payload JSON 树、处理轨迹时间线；底部 [重试本条]（仅失败/死信 + R1） |
| 重放失败事件抽屉 | Drawer 420px | startTime / endTime（DateRangePicker，必填，跨度 ≤ 7 天）；提交 `POST /callback/dingtalk/retry-queue/replay`，校验区间必填 |
| 人员详情抽屉 | Drawer 560px | 只读聚合：基本信息 + 生效模板（版本号）+ 权限概要 + 名下资产/账号数（数字链接）；离职人员头部黄条提示"该人员处于冻结态，归还单未闭环" |
| 手动对账确认弹窗 | Modal 420px | 文案确认 + [取消][确认执行] |

### 8. 错误处理
- 网络超时：表格区"加载失败"占位 + 重试按钮；
- 权限不足（403 / 1008）：操作按钮置灰 + tooltip"无操作权限"，菜单对无权角色整体隐藏；
- 钉钉接口超时（5003）：同步概览条显示橙色横幅"钉钉服务暂不可用，数据可能延迟"（V1-A6）；
- 对账失败（5006）：消息提示 + 建议查看对账报告失败明细。

### 9. BR 业务规则覆盖
- **BR-001（同步延迟 < 5 分钟）**：同步概览条常显 avgSyncDelayMinutes，超 5 分钟指标红色高亮，供 R1 追查慢事件；
- **BR-015（离职归还强制闭环）**：人员详情抽屉对离职冻结人员展示闭环状态与归还单链接（联动 ACCT-003）。

---

## P3. 岗位-角色供给规则页（AUTH-003 · ADR-IMS-008）

> **2026-10-04 重定义**：本页由「岗位模板（岗位-权限矩阵）」**降级为「岗位 → 角色 自动供给规则」**。**权限明细（功能点 R/W/D + 数据范围 + 菜单权限码）已迁入 SYS-002 角色**（角色 = 权限唯一载体）。本页只声明「某钉钉岗位 → 授予哪些角色」。

### 1. 页面概述
- 路由路径：`/ims/auth/position`
- 页面级别：一级菜单页（供给规则列表 + 新建/编辑抽屉 + 角色授权校验）
- 依赖模块：**SYS-002 角色**（授权对象）、AUTH-002（钉钉岗位映射）、AUTH-004（自动建角色待办）
- 权限矩阵引用：R1 R/W/D（全量）；R2、R4 只读

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 规则名称 | 钉钉岗位 | 授权角色 | 状态 | [查询][重置] [新建规则] |
+------------------------------------------------------------------+
| 表格: 规则名称 | 钉钉岗位 | 授予角色 | 版本 | 状态 | 套用人数 | 更新时间 | 操作 |
|       操作 = [查看][编辑(新版本)][停用/启用][删除]                        |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=10  total=xxx                            |
+------------------------------------------------------------------+
编辑抽屉（右侧 560px）:
  +--------------------------------------------------------------+
  | 规则名称* | 钉钉岗位*(下拉) | 说明                              |
  | 授予角色*: [角色多选 Select]（含来源角标：手工/钉钉自动/待配置）  |
  |   ⓘ 权限由角色决定；本规则不配置权限明细                          |
  | [保存为新版本]  [取消]                                         |
  +--------------------------------------------------------------+
自动建角色（钉钉同步）: 无对应角色 → 建 PENDING_CONFIG 空权限角色 + 推 R1 待办
```
> 权限明细（功能点 R/W/D / 数据范围 / 菜单权限码）**在 SYS-002 角色页维护**，本页不出现权限勾选矩阵。

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface PositionRulePageReq {
  pageNo: number; pageSize: number;
  ruleName?: string; dingtalkPosition?: string; grantRoleId?: number; status?: 'ENABLED' | 'DISABLED';
}
interface PositionRuleSaveReq {
  ruleName: string;              // ≤64 字
  dingtalkPosition: string;      // 必填，唯一绑定启用版本（沿用 POS-R1）
  description?: string;
  grantRoleIds: number[];        // 授予角色（1..n）；权限明细在角色侧
  clientToken: string;
}

// 响应类型
interface PositionRuleItem {
  id: number;
  ruleName: string;
  dingtalkPosition: string;
  grantRoles: { roleId: number; roleName: string; source: 'MANUAL' | 'DINGTALK_AUTO'; status: 'ENABLED' | 'PENDING_CONFIG' }[];
  version: number;
  status: 'ENABLED' | 'DISABLED';
  appliedUserCount: number;
  updateTime: string;
}

// 枚举类型
type RuleStatus = 'ENABLED' | 'DISABLED';
type RoleSource = 'MANUAL' | 'DINGTALK_AUTO';
type RoleStatus = 'ENABLED' | 'PENDING_CONFIG';
```

> **已移除类型**（迁往 SYS-002 角色）：`PermDetailItem`、`PermLevel`、`dataScope`、`PermDiffPreviewReq`/`PermDiffResp`（权限 Diff 预览改为**按角色**在角色页/调岗预演中进行）。

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /auth/position/rules` → 渲染；失败 → 重试占位。

#### 4.2 核心操作流程
**A. 新建/编辑供给规则（抽屉）**
1. [新建规则] / 行内 [编辑] → 打开抽屉；编辑模式头部显示"当前版本 v3，保存后生成 v4"；
2. 选择钉钉岗位（必填，唯一）；选择**授予角色**（多选，下拉展示角色 `source`/`status` 角标）；
3. 保存前校验：规则名 ≤64 字且非空；钉钉岗位必选；若该岗位已绑定其他**启用**规则 → 二次确认"该岗位已有启用规则，保存后将替换绑定，是否继续？"（POS-R1）；若所选角色含 `PENDING_CONFIG` → 提示"角色 X 尚未配置权限，用户将无任何权限，是否继续？"（fail-closed 提醒）；
4. `POST /auth/position/rule` 或 `PUT /auth/position/rule/{id}`（携带 clientToken）→ 成功消息 + 列表刷新 + 版本号 +1（POS-R2：已套用用户不自动变更）。

**B. 从岗位自动建角色（钉钉同步联动 · §4.2.1 护栏）**
1. 钉钉同步到**无对应角色**的岗位 → 系统自动建角色：`source=DINGTALK_AUTO`、`status=PENDING_CONFIG`、**权限空集**（fail-closed）；
2. 推待办「新岗位 X 已自动建角色，请配置权限」到 R1（AUTH-004）；
3. 本页该岗位规则行显示"待配置角色"角标，点击跳 SYS-002 角色页配置。

**C. 停用/启用**
1. [停用] → 确认弹窗"停用后新入职/调岗不再套用此规则"；appliedUserCount > 0 时提示"当前有 N 人在用，停用不影响既有用户"。

**D. 删除**
1. [删除] → 前端预检：appliedUserCount > 0 → 直接阻断提示"请先处理在用用户（调岗或刷新规则）后删除"（POS-R3）；
2. 无在用用户 → 危险确认弹窗（输入规则名二次确认）→ `DELETE /auth/position/rule/{id}`（逻辑删除）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| ruleName | Input | 否 | 空 | 模糊匹配 |
| dingtalkPosition | Select | 否 | 空 | 钉钉岗位字典 |
| grantRoleId | Select | 否 | 空 | 按授予角色筛选 |
| status | Select | 否 | 空 | 启用/停用 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| ruleName | 规则名称 | 180 | — | 点击查看只读详情抽屉 |
| dingtalkPosition | 钉钉岗位 | 140 | — | — |
| grantRoles | 授予角色 | 200 | — | 角色名 tag（含来源角标·待配置警示） |
| version | 版本 | 70 | ✓ | v{version} |
| status | 状态 | 80 | — | tag：启用(绿)/停用(灰) |
| appliedUserCount | 套用人数 | 90 | ✓ | 数字；>0 时删除按钮禁用 |
| updateTime | 更新时间 | 160 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 200 | — | 按角色权限动态显示 |

> **已移除列**：`permSummary`（权限概要）—— 权限属角色，本页不再展示功能点计数。

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 规则新建/编辑抽屉 | Drawer 560px | ruleName（必填 ≤64 字）；dingtalkPosition（必填，Select）；description（≤200 字）；grantRoleIds（必填≥1，角色多选，展示 source/status 角标）；提交逻辑见 4.2-A |
| 待配置角色跳转 | — | 行内角标 → 跳 SYS-002 角色页配置权限 |
| 停用确认弹窗 | Modal 420px | 文案 + 确认 |
| 删除危险确认弹窗 | Modal 420px | 输入规则名匹配方可提交 |

### 8. 错误处理
- 网络超时：抽屉提交按钮恢复可点 + "网络异常请重试"；
- 权限不足：R2/R4 进入页面只读（操作列不渲染）；
- 唯一绑定冲突（业务错误 1001）：内联表单错误提示在钉钉岗位字段下方；
- 保存失败（5001）：保留表单草稿不丢失，提示重试；
- **授予角色含待配置项（业务错误 1002）**：提示"所选角色未配置权限，用户将无权限"（fail-closed）。

### 9. BR 业务规则覆盖
- 本页不直接落 BR 指标，但为 **BR-015**（离职模板权限关闭）、AUTH-002 入职自动开权限提供**供给规则基座**；**权限明细由 SYS-002 角色承担**（ADR-IMS-008），本页只声明「岗位 → 角色」映射。

---

## P4. 个人工作台（AUTH-004）

### 1. 页面概述
- 路由路径：`/ims/workbench`（SSO 登录后默认落地页）
- 页面级别：一级菜单页（仪表盘布局，非表格页）
- 依赖模块：全部模块待办来源（领用审批/归还单/审核任务/证件预警/直播告警）、钉钉工作通知
- 权限矩阵引用（PRD 4.2）：R1 R/W（全量可查）；R2~R9 R/W（本人；R4 本人+下属）；R10 R/W（仅被指派任务）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 问候区: 早上好，{姓名}（{部门}·{角色}）     [消息中心 icon+红点]     |
+------------------------------------------------------------------+
| 数据卡片区（一行 4 卡，按权限动态渲染）:                              |
| [我名下账号 N] [我名下资产 N] [我的证件 N(含预警角标)] [我的场次 N]    |
+------------------------------------------------------------------+
| +-----------------------------+  +------------------------------+  |
| | 待办中心（左 60%）           |  | 消息中心（右 40%）             |  |
| | Tab: [全部][审批][归还][审核] |  | 未读角标 + [全部已读]          |  |
| | [确认][预警][告警]           |  | 列表: 类型tag|标题|摘要|时间   |  |
| | 列表预览 **10 条**           |  | 列表预览 **10 条**             |  |
| | [查看更多] → P4a             |  | 点击 → 详情抽屉 + 标记已读     |  |
| | 操作[去处理][关闭]           |  | [查看更多] → P4b               |  |
| | (逾期项红色高亮+排序置顶)     |  |                                |  |
| +-----------------------------+  +------------------------------+  |
+------------------------------------------------------------------+
顶栏: 消息 icon+红点 → 420px 抽屉（快捷查看，与 P4/P4b 数据同源）
说明: **不含快捷入口**；角色常用入口见 HOME-001 运营看板快捷区
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface WorkbenchDashboardReq { /* 无参数，按当前用户聚合 */ }
interface TodoPageReq {
  pageNo: number; pageSize: number;
  taskType?: TodoTaskType;
  status?: 'PENDING' | 'DONE' | 'EXPIRED';
}
interface TodoHandleReq { todoId: number; action: 'OPEN' | 'CLOSE'; }

// 响应类型
interface DashboardResp {
  greeting: string;
  myAccountCount: number;
  myAssetCount: number;
  myCertCount: number;
  myCertWarningCount: number;     // 黄/红/锁定预警数
  mySessionCount: number;
  pendingTodoCount: number;
  unreadMessageCount: number;
}
interface TodoItem {
  id: number;
  taskType: TodoTaskType;
  title: string;
  content: string;                // 摘要
  status: 'PENDING' | 'DONE' | 'EXPIRED';
  deadline: string;               // ISO 8601
  overdue: boolean;               // 前端亦可由 deadline 计算
  refType: string; refId: number; // 跳转目标单据
  createdAt: string;
}
interface MessageItem {
  id: number; title: string; content: string;
  isRead: boolean; sourceModule: string;
  refType?: string; refId?: number;
  createdAt: string;
}

// 枚举类型
type TodoTaskType = 'approval' | 'return' | 'review' | 'cert_expire' | 'live_alarm' | 'supplement' | 'recharge_verify';
```

### 4. 交互流程

#### 4.1 页面加载
1. 骨架屏（卡片 + 待办列表占位）→ 并行 `GET /auth/workbench/dashboard` + `GET /auth/workbench/todos`；
2. 卡片按权限渲染：无权限的卡片（如 R10 无"我的场次"）不显示；
3. 失败 → 各区域独立"加载失败，重试"。

#### 4.2 核心操作流程
**A. 待办处理**
1. 待办按 deadline 升序（WB-R1）；逾期项红底置顶；
2. 点击 [去处理] → 按 refType 路由跳转（领用审批 → `/ims/account/apply` 并自动打开对应审批抽屉；归还 → `/ims/account/return`；审核 → `/ims/content/review`；证件预警 → `/ims/cert/expire`；直播告警 → `/ims/live/alarm`）；
3. 处理完成回到工作台 → 对应待办自动闭环（状态变 DONE，WB 机制）；
4. 也可直接 [关闭] 待办（`PUT /todos/{id}`，action=CLOSE）。

**B. 数据卡片下钻**
- "我名下账号" → `/ims/asset/reverse`（入口维度=person，本人）；
- "我的证件（含预警角标）" → `/ims/cert/archive`（过滤本人）；
- "我的场次" → `/ims/live/ledger`（过滤本人）。

**C. 消息中心（P4 内嵌 + P4b 全量 + 顶栏抽屉）**
1. P4 右侧预览 10 条；点击条目 → **消息详情 Drawer**（正文 + 来源模块）并 `PUT …/messages/{id}/read`；
2. [查看更多] → P4b `/ims/workbench/messages`：Tab [全部|未读|已读] + 标题/摘要搜索 + 分页（pageSize=20）；
3. [全部已读] → `PUT …/messages/read-all`；顶栏 bell 抽屉与 P4/P4b **同源列表**，仅交互容器不同；
4. 有 `refType/refId` 时详情底栏 [查看来源] 跳转对应业务页；钉钉通道推送由服务端完成（WB-R2），前端不重复推送。

**D. 待办全量列表（P4a）**
1. 从 P4 [查看更多] 进入；继承 P4 Tab 过滤；表格列见 §6；
2. QueryBar：标题关键词 + 状态（待处理/已过期）；分页 pageSize=20；
3. [返回工作台] 回到 P4；[去处理]/[关闭] 与 P4 一致。

**E. R10 外协视角**
- 仅显示被指派任务待办（WB-R3）；数据卡片区仅"我的任务"卡；消息/待办列表同样仅本人数据。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| taskType | Tab 切换 | 否 | 全部 | 待办类型过滤 |
| status | Tab/Select | 否 | PENDING | 待处理/已处理/已过期 |

### 6. 表格列定义（待办列表）

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| taskType | 类型 | 100 | — | tag：审批(蓝)/归还(橙)/审核(紫)/证件预警(黄)/直播告警(红)/补录(青)/充值核对(绿) |
| title | 标题 | 自适应 | — | 超 1 行省略 + tooltip |
| deadline | 截止时间 | 150 | ✓ | yyyy-MM-dd HH:mm；逾期红色 + "逾期 X 天" |
| status | 状态 | 90 | — | tag：待处理(蓝)/已处理(绿)/已过期(灰) |
| actions | 操作 | 140 | — | [去处理][关闭]（DONE/EXPIRED 行仅 [查看]） |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与逻辑 |
|-----------|------|-----------|
| 消息中心抽屉（顶栏） | Drawer 420px | 与 P4b 同源；pageSize=20；点击 → 消息详情 Drawer |
| 消息详情 | Drawer 520px | 标题/类型 tag/时间/正文；[关闭][查看来源]（有 ref 时） |
| 待办关闭确认弹窗 | Modal 360px | "确认关闭该待办？关闭后不再提醒"，[取消][确认] |

### 8. 错误处理
- 网络超时：卡片与待办独立重试；
- 跳转目标单据已不存在（1002 等）：提示"单据已被处理或删除" + 待办自动置 DONE；
- 权限变化导致卡片无权：直接隐藏卡片（不做报错）。

### 9. BR 业务规则覆盖
- **BR-012（领用超期提醒）**：领用后 15 天无使用的提醒以 cert_expire 类似的 todo（taskType=supplement 由服务端判定）进入待办并钉钉推送；
- **BR-013（证件到期预警）**：预警待办 taskType=cert_expire 按黄/红/锁定着色推送持有人与行政；
- **BR-007（下播录入完整率）**：下播 24h 未录入进入督办待办（LIVE-D-R1）；
- 本页是 AUTH-004 待办统一闭环入口，处理完成自动闭环是所有流程页面约定（ACCT/LIVE/CONTENT 页面在提交成功后回调待办关闭）。

---

## 模块通用备注
- 本模块 **6 个页面**（含 P4a/P4b 二级列表）、8 个抽屉/弹窗（事件详情、重放、人员详情、对账确认、模板编辑、Diff 预览、顶栏消息抽屉、**消息详情**）+ 3 个确认类弹窗。
- 页面规格中所有时间字段 ISO 8601；分页统一 `pageNo/pageSize`；响应格式遵循共享规范 8.1。
