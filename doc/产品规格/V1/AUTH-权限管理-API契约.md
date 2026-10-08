# AUTH - 权限管理 API 契约

> **模块范围**：01 权限管理（V1，第 2~5 周）——AUTH-001 SSO 单点登录、AUTH-002 组织架构同步（事件驱动）、AUTH-003 岗位-角色供给规则（**ADR-IMS-008** · 原「岗位模板」）、AUTH-004 个人工作台。
> **权威依据**：《IMS第一期PRD-V1.md》5.1~5.4 各功能点 API 设计表；《共享技术规范-数据库与API.md》8.1/8.3/8.4。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举引用《全局开发规范.md》第 4 章；错误码引用其第 3 章。字段一律 camelCase。

---

## 1. API 总览表（共 20 个接口 + 钉钉集成 5 个端点）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | GET | `/admin-api/ims/auth/sso/redirect` | 获取钉钉授权跳转地址 | 公开（未登录） |
| 2 | POST | `/admin-api/ims/auth/sso/callback` | 授权码换 JWT 会话 | 公开（未登录） |
| 3 | POST | `/admin-api/ims/auth/sso/refresh` | 刷新 Token | 已登录 |
| 4 | POST | `/admin-api/ims/auth/sso/logout` | 注销会话 | 已登录 |
| 5 | POST | `/admin-api/ims/auth/org/event` | 接收钉钉通讯录事件回调（服务端回调） | 钉钉服务端（签名验签） |
| 6 | GET | `/admin-api/ims/auth/org/users` | 组织人员列表（含同步状态，分页） | R1/R2（本部门）/R4 |
| 7 | POST | `/admin-api/ims/auth/org/reconcile` | 手动触发全量对账 | R1 |
| 8 | GET | `/admin-api/ims/auth/org/events` | 同步事件查询（分页） | R1/R2（本部门）/R4 |
| 9 | GET | `/admin-api/ims/auth/org/sync-metrics` | 同步延迟统计（BR-001） | R1/R4 |
| 10 | GET | `/admin-api/ims/auth/position/rules` | 岗位-角色供给规则列表（分页） | R1/R2（只读）/R4（只读） |
| 11 | POST | `/admin-api/ims/auth/position/rule` | 新建供给规则 | R1 |
| 12 | PUT | `/admin-api/ims/auth/position/rule/{id}` | 编辑（生成新版本） | R1 |
| 13 | DELETE | `/admin-api/ims/auth/position/rule/{id}` | 删除规则（逻辑删除） | R1 |
| 14 | POST | `/admin-api/ims/auth/position/role-auto-create` | 钉钉岗位自动建角色（fail-closed · 幂等） | 内部 Worker / R1 |
| 15 | GET | `/admin-api/ims/auth/workbench/dashboard` | 工作台聚合数据 | 全部角色（按本人/数据范围） |
| 16 | GET | `/admin-api/ims/auth/workbench/todos` | 待办列表（分页） | 全部角色 |
| 17 | PUT | `/admin-api/ims/auth/workbench/todos/{id}` | 处理/关闭待办 | 全部角色（本人） |
| 18 | GET | `/admin-api/ims/auth/workbench/messages` | 消息列表（分页） | 全部角色（本人） |
| 19 | PUT | `/admin-api/ims/auth/workbench/messages/{id}/read` | 单条标记已读 | 全部角色（本人） |
| 20 | PUT | `/admin-api/ims/auth/workbench/messages/read-all` | 全部标记已读 | 全部角色（本人） |

### 钉钉集成端点（共享技术规范 8.4，服务端回调，不走管理端 JWT）

| # | 方法 | 路径 | 说明 | 调用方 |
|---|------|------|------|--------|
| D1 | GET | `/sso/dingtalk/callback?authCode=xxx&state=xxx` | IMS 自建钉钉 SSO 回调（state 防 CSRF，5 分钟有效）；须绑 mobile 后对 `system_users.id` | 钉钉 |
| D2 | POST | `/callback/dingtalk/event` | 钉钉事件订阅回调（先返回加密 echo 校验；事件入重试队列） | 钉钉 |
| D3 | POST | `/callback/dingtalk/reconcile` | 触发全量对账补偿（手动/每日 02:00 定时） | 内部/定时 |
| D4 | GET | `/callback/dingtalk/reconcile/report` | 查询最近一次对账结果 | R1 |
| D5 | POST | `/callback/dingtalk/retry-queue/replay` | 重放失败事件队列（按时间区间） | R1 |

---

## 2. 接口明细

### 2.1 SSO 单点登录（AUTH-001）

#### 2.1.1 GET /admin-api/ims/auth/sso/redirect — 获取钉钉授权跳转地址

**请求**（Query）：

```typescript
interface SsoRedirectReq {
  /** 跳转回跳地址（登录完成后前端落地页），可选 */
  redirectUri?: string;
}
```

**响应** `data`：

```typescript
interface SsoRedirectResp {
  /** 钉钉扫码/免登授权页完整 URL（含 state） */
  authorizeUrl: string;
  /** CSRF state（前端无需持久化，后端会话持有） */
  state: string;
}
```

#### 2.1.2 POST /admin-api/ims/auth/sso/callback — 授权码换 JWT 会话

**请求**（Body）：

```typescript
interface SsoCallbackReq {
  /** 钉钉返回的授权码 */
  authCode: string;
  /** 防 CSRF state */
  state: string;
  /** 登录来源（Web 管理后台 / H5 免登） */
  loginChannel: 'WEB' | 'H5';
  /** 登录 IP（后端兜底取 Header） */
  loginIp?: string;
  /** 设备标识 */
  loginDevice?: string;
}
```

**响应** `data`：

```typescript
interface SsoCallbackResp {
  /** JWT 访问令牌（有效期 2 小时，AUTH-R2） */
  accessToken: string;
  /** 刷新令牌（7 天） */
  refreshToken: string;
  /** 会话过期时间 ISO 8601 */
  expiresAt: string;
  /** 用户基础信息（含角色并集 + 岗位供给规则套用结果 · ADR-IMS-008） */
  userProfile: UserProfileVO;
}

interface UserProfileVO {
  userId: number;
  nickname: string;
  deptIds: number[];
  deptNames: string[];
  /** 套用的角色编号（R1~R10） */
  roleCodes: string[];
  /** 证件访问级别（CERT-003 联动） */
  certViewLevel: 1 | 2 | 3;
  /** 账号状态（离职冻结时为 FROZEN，仅可登录工作台） */
  status: AccountStatus;
}
```

**错误码**：1002（会话无效/state 过期）、1003（并发会话超限被踢出提示）、1006（钉钉接口同步失败）、5003（钉钉超时）。首次登录映射缺失触发单用户即时同步（V1-A5）。

#### 2.1.3 POST /admin-api/ims/auth/sso/refresh — 刷新 Token

**请求**：`{ refreshToken: string }` → **响应**：`SsoCallbackResp`（新令牌对）。

#### 2.1.4 POST /admin-api/ims/auth/sso/logout — 注销会话

**请求**：`{}`（Bearer Token 识别会话）→ **响应**：`data: null`。注销后同账号最早会话保留策略按 AUTH-R3。

### 2.2 组织架构同步（AUTH-002）

#### 2.2.1 POST /admin-api/ims/auth/org/event — 钉钉通讯录事件回调（服务端）

**请求**：

```typescript
interface OrgEventCallbackReq {
  /** 钉钉推送加密原文（后端验签解密，V1-A1：只做验签/解密/解析，业务异步投递重试队列，P95 < 500ms 返回） */
  encrypt: string;
  /** 钉钉签名头：timestamp/nonce/sign 由 Header 传递 */
}
```

**响应**：`data: null`（立即 ACK；幂等键 `dingtalkEventId + eventType`，已处理事件直接成功返回，V1-A3）。

**解析后的事件结构**（内部异步消费，接口层不透出）：

```typescript
interface OrgSyncEvent {
  eventType: 'hire' | 'transfer' | 'resign' | 'dept_change';
  dingtalkEventId: string;
  unionId: string;
  userId?: number;
  beforeDept?: string;
  afterDept?: string;
  /** 事件原文 JSON（payload） */
  payloadJson: Record<string, unknown>;
}
```

#### 2.2.2 GET /admin-api/ims/auth/org/users — 组织人员列表（分页）

**请求**（Query）：`PageParam` + `{ deptId?: number; keyword?: string; syncStatus?: 'PENDING' | 'SUCCESS' | 'FAILED' }`

**响应** `data`：`PageResult<OrgUserVO>`

```typescript
interface OrgUserVO {
  userId: number;
  nickname: string;
  mobileMasked: string;          // 138****5678
  deptIds: number[];
  deptNames: string[];
  dingtalkUserId: string;
  syncStatus: 'PENDING' | 'SUCCESS' | 'FAILED';
  /** syncStatus 映射标记：页面规格 OrgSyncStatus 的 FAILED_RETRY/DEAD_LETTER 归并为 FAILED */
  retryFlag: boolean;            // true=FAILED_RETRY（重试中，1min/5min/15min/1h 指数退避）
  deadLetter: boolean;           // true=DEAD_LETTER（重试耗尽入死信队列，已告警）
  lastSyncTime: string;          // ISO 8601
  /** 账号状态（离职冻结标记） */
  status: AccountStatus;
  /** 由岗位-角色供给规则授予的角色（AUTH-003 联动 · ADR-IMS-008） */
  grantedRoleNames?: string[];
}
```

> **syncStatus 映射口径**：页面规格 `OrgSyncStatus`（PENDING|SUCCESS|FAILED_RETRY|DEAD_LETTER）与本接口传输值的映射关系为——`FAILED_RETRY` / `DEAD_LETTER` 归并为 `FAILED` 传输，另以 `retryFlag` / `deadLetter` 两个布尔标记区分（均为 false 时即普通失败）。

#### 2.2.3 POST /admin-api/ims/auth/org/reconcile — 手动触发全量对账

**请求**：`{}` → **响应**：`{ reconcileTaskId: string; triggeredAt: string }`。对账结果见 D4 端点。连续 2 次对账失败触发 P1 告警（V1-A4）。

#### 2.2.4 GET /admin-api/ims/auth/org/events — 同步事件查询（分页）

**请求**（Query）：`PageParam` + `{ eventType?: string; syncStatus?: 'PENDING' | 'SUCCESS' | 'FAILED_RETRY'; timeRange?: [string, string] }`

**响应** `data`：`PageResult<OrgSyncEventVO>`（`OrgSyncEvent` 透出 camelCase 字段 + `syncedAt: string; retryCount: number`）。

#### 2.2.5 GET /admin-api/ims/auth/org/sync-metrics — 同步延迟统计

**响应** `data`：

```typescript
interface SyncMetricsResp {
  /** 目标 < 5 分钟（BR-001） */
  avgSyncDelayMinutes: number;
  p95SyncDelayMinutes: number;
  successRate: number;           // BR-002 关联
  /** 近 30 天延迟趋势 [{date, delayMinutes}] */
  trend: Array<{ date: string; delayMinutes: number }>;
}
```

### 2.3 岗位-角色供给规则（AUTH-003 · ADR-IMS-008）

> **2026-10-04 重定义**：由「岗位模板（岗位-权限矩阵）」降级为「岗位 → 角色 自动供给规则」。**功能点权限明细（`permDetail`）与数据范围（`dataScope`）迁入 SYS-002 角色**（见《SYS-系统管理-API契约》§角色）。本组只声明「钉钉岗位 → 授予角色」。端点由 `/template(s)` 改为 `/rule(s)`（**旧 `/template(s)` 保留兼容别名 1 个版本**，转发同逻辑）。

#### 2.3.1 GET /admin-api/ims/auth/position/rules — 供给规则列表（分页）

**请求**（Query）：`PageParam` + `{ keyword?: string; dingtalkPosition?: string; grantRoleId?: number; status?: EnableStatus }`

**响应** `data`：`PageResult<PositionRuleVO>`

```typescript
interface PositionRuleVO {
  id: number;
  ruleName: string;              // 如"直播运营岗供给"
  dingtalkPosition: string;      // 对应钉钉岗位（唯一绑定启用版本）
  version: number;
  status: EnableStatus;
  /** 授予角色（1..n）；权限明细在角色侧，此处只挂角色 */
  grantRoles: Array<{
    roleId: number;
    roleName: string;
    source: 'MANUAL' | 'DINGTALK_AUTO';   // 来源（ADR-IMS-008 G2）
    status: 'ENABLED' | 'PENDING_CONFIG'; // 待配置（G3）
  }>;
  appliedUserCount: number;
  createdBy: number;
  createdAt: string;
}
```

#### 2.3.2 POST /admin-api/ims/auth/position/rule — 新建供给规则

**请求**：

```typescript
interface PositionRuleCreateReq {
  ruleName: string;              // ≤64 字
  dingtalkPosition: string;      // 必填，唯一绑定启用版本
  description?: string;          // ≤200 字
  grantRoleIds: number[];        // 必填 ≥1；权限明细在角色侧
}
```

**响应**：`PositionRuleVO`（version=1）。一个钉钉岗位只能绑定一个启用版本规则（POS-R1，冲突返回 1001）。

#### 2.3.3 PUT /admin-api/ims/auth/position/rule/{id} — 编辑（生成新版本）

**请求**：`PositionRuleCreateReq`（同名即新版本，version+1；已套用用户不自动变更，POS-R2）→ **响应**：新 `PositionRuleVO`。

#### 2.3.4 DELETE /admin-api/ims/auth/position/rule/{id}

**请求**（Query）：`{ confirmText: 'DELETE' }` → **响应**：`data: null`。在用用户非零时拒绝删除（POS-R3，返回 1001）。前端需 ConfirmDialog 结构化提示。

#### 2.3.5 POST /admin-api/ims/auth/position/role-auto-create — 钉钉岗位自动建角色（内部/联动）

**说明**：由钉钉同步 Worker 调用（G1~G8 护栏）；也可供 R1 手动触发。

**请求**：`{ dingtalkPosition: string }`

**响应** `data`：

```typescript
interface RoleAutoCreateResp {
  roleId: number;                // 新建或已存在的角色
  roleName: string;
  source: 'DINGTALK_AUTO';
  status: 'PENDING_CONFIG';      // 空权限（fail-closed）
  created: boolean;              // 幂等：false 表示已存在（G6）
  todoId?: number;               // 推 R1 待办（G4）
}
```

> **幂等**：以 `dingtalkPosition` 唯一键 upsert；重复调用不重建、不覆盖已配置权限。
> **fail-closed**：新建角色 `permDetail` 为空集，**绝不**因"无角色"放行。

#### 2.3.6 权限 Diff 预览（已迁往角色）

原 `POST /auth/position/preview`（按模板预演权限）**迁往 SYS-002 角色**：`POST /admin-api/ims/system/role/{id}/preview`（模拟用户按角色的权限 Diff），见《SYS-系统管理-API契约》角色节。

### 2.4 个人工作台（AUTH-004）

#### 2.4.1 GET /admin-api/ims/auth/workbench/dashboard — 工作台聚合数据

**响应** `data`：

```typescript
interface WorkbenchDashboardResp {
  todoCount: number;
  unreadMessageCount: number;
  /** 我的数据卡片：我名下账号/资产/证件/场次一览（BR 视角按角色裁剪） */
  myAccountCount: number;
  myAssetCount: number;
  myCertCount: number;
  myLiveSessionCount: number;
}
```

> **说明**：个人工作台（AUTH-004）不含快捷入口；角色常用入口由 HOME-001 `GET /home/shortcuts` 提供。工作台首页待办/消息各预览 **10 条**，全量走 todos/messages 分页接口。

#### 2.4.2 GET /admin-api/ims/auth/workbench/todos — 待办列表（分页）

**请求**（Query）：`PageParam` + `{ taskType?: TodoTaskType; status?: HandleStatus }`

```typescript
type TodoTaskType = 'approval' | 'return' | 'review' | 'cert_expire' | 'live_alarm';
```

**响应** `data`：`PageResult<TodoTaskVO>`

```typescript
interface TodoTaskVO {
  id: number;
  taskType: TodoTaskType;
  refType: string;
  refId: number;
  title: string;
  content: string;
  status: HandleStatus;          // PENDING / DONE / EXPIRED
  deadline: string;              // WB-R1：逾期红色高亮并升级推送
  createdAt: string;
}
```

#### 2.4.3 PUT /admin-api/ims/auth/workbench/todos/{id} — 处理/关闭待办

**请求**：`{ action: 'DONE' | 'CLOSE'; remark?: string }` → **响应**：`data: null`。钉钉推送去重：同一待办最多推送 3 次（创建/临期/逾期，WB-R2）；外协仅显示被指派任务（WB-R3）。

#### 2.4.4 GET /admin-api/ims/auth/workbench/messages — 消息列表（分页）

**请求**（Query）：`PageParam` + `{ read?: boolean }`

**响应** `data`：`PageResult<WorkbenchMessageVO>`

```typescript
interface WorkbenchMessageVO {
  id: number;
  title: string;
  content: string;
  channel: 'IN_APP' | 'DINGTALK';
  read: boolean;
  sourceModule?: string;
  refType?: string;
  refId?: number;
  createdAt: string;
}
```

#### 2.4.5 PUT /admin-api/ims/auth/workbench/messages/{id}/read — 单条标记已读

**请求**：无 Body → **响应**：`data: null`（幂等：已读重复调用仍 200）。

#### 2.4.6 PUT /admin-api/ims/auth/workbench/messages/read-all — 全部标记已读

**请求**：无 Body → **响应**：`data: { updated: number }`（本次新置已读条数）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**人员账号状态（OrgUserVO.status / UserProfileVO.status）**：

```
IN_POOL（可选）──hire事件──▶ IN_USE ──resign事件──▶ FROZEN（BR-015 未闭环：不可登录业务模块）
                                │                        │
                            transfer事件               归还闭环（RET-R3）
                                ▼                        ▼
                          IN_USE（新部门，24h 权限缓冲 ORG-R3）   CANCELLED（彻底关闭）
```

**同步事件状态**：`PENDING →（处理）SUCCESS / FAILED_RETRY（1min/5min/15min/1h 指数退避，≤16 次）→ 死信队列告警`。

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-001 | 同步延迟 < 5 分钟 | 2.2.5 sync-metrics 统计口径 |
| BR-002 | SSO 成功率 > 99.5% | 2.1.2 成功/失败审计落库 |
| BR-015 | 离职归还闭环前账号/资产冻结 | 2.2.1 resign 事件 → 冻结；联动 ACCT-003 close |
| AUTH-R2 | JWT 2h / Refresh 7d | 2.1.2/2.1.3 |
| AUTH-R3 | 并发会话 ≤ 3，踢出最早 | 2.1.2（错误码 1003） |
| AUTH-R4 | 连续失败 5 次锁 15 分钟 | 2.1.2（错误码 1001 附 msg） |
| ORG-R1~R4 | 幂等/重试 3 次/调岗 24h 缓冲/离职先冻结 | 2.2.1（+V1-A1~A6 技术约束） |
| POS-R1~R3 | 一岗一启用版本/变更不自动套用/删除校验 | 2.3.x |
| WB-R1~R3 | 逾期高亮/推送去重 3 次/外协仅指派任务 | 2.4.x |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 登录页（无独立页面，入口重定向） | 访问系统触发钉钉授权 | GET /auth/sso/redirect → 钉钉授权页 |
| 登录回跳处理 | 换取会话并进入工作台 | POST /auth/sso/callback |
| 全局（顶部栏） | 会话过期静默续期 | POST /auth/sso/refresh |
| 全局（顶部栏） | 退出登录 | POST /auth/sso/logout |
| 组织架构页（人员 Tab，QueryBar+表格） | 人员列表查询/筛选 | GET /auth/org/users |
| 组织架构页（事件 Tab） | 同步事件查询 | GET /auth/org/events |
| 组织架构页（指标卡） | 同步延迟看板 | GET /auth/org/sync-metrics |
| 组织架构页（操作按钮） | 手动触发全量对账（ConfirmDialog） | POST /auth/org/reconcile |
| 岗位-角色供给规则页（QueryBar+表格+Drawer 编辑） | 规则列表/新建/编辑（授予角色）/删除/自动建角色 | GET/POST/PUT/DELETE /auth/position/rule*、POST /auth/position/role-auto-create |
| 个人工作台（首页） | 聚合卡片 + 待办/消息各 10 条预览 | GET /auth/workbench/dashboard、GET todos/messages（pageSize=10） |
| 工作台-待办中心（P4a） | 全量待办列表/去处理/关闭 | GET /auth/workbench/todos、PUT /auth/workbench/todos/{id} |
| 工作台-消息中心（P4/P4b/顶栏） | 列表/详情/已读 | GET /auth/workbench/messages、PUT …/messages/{id}/read、PUT …/messages/read-all |
| 系统集成页（R1） | 对账报告查询/失败事件重放 | GET /callback/dingtalk/reconcile/report、POST /callback/dingtalk/retry-queue/replay |

（全文完）
