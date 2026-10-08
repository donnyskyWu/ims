# ACCT - 账号管理 页面规格

> 依据：《IMS第一期PRD-V1.md》5.8~5.12（ACCT-001~005）、《共享技术规范-数据库与API.md》第 7/8 章。
> **完整版叠加**：账号登记六实体与强关联选择器见《MASTER-主数据-页面规格.md》；账号 ROI 见《COST-账号财务-页面规格.md》。台账主键保持迁入前 id（IR-06）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/account`。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 账号台账列表 | `/ims/account/ledger` | 一级菜单页（含账号详情抽屉 + 时间线 Tab） | ACCT-005 及全模块入口 |
| P2 账号领用管理 | `/ims/account/apply` | 一级菜单页（申请列表 + 发起/审批抽屉） | ACCT-001 |
| P3 流转/收回管理 | `/ims/account/transfer` | 一级菜单页（流转单列表 + 发起/确认抽屉） | ACCT-002 |
| P4 离职归还管理 | `/ims/account/return` | 一级菜单页（归还单列表 + 处理抽屉） | ACCT-003 |
| P5 冲话费管理 | `/ims/account/recharge` | 一级菜单页（充值记录 + 登记抽屉 + 月度核对） | ACCT-004 |
| 时间线视图 | 并入 P1 账号详情抽屉 Tab | 抽屉内 Tab | ACCT-005 |

通用 UI 约定：查询条件一行紧凑排布；交互优先内联抽屉（Drawer）不跳转；敏感字段脱敏（手机号 138\*\*\*\*5678、账号密码任何视图不可见——APP-R4 只存"已重置"事实）；金额 DECIMAL(12,2) 前缀 ¥；状态 tag 语义色。

---

## P1. 账号台账列表

### 1. 页面概述
- 路由路径：`/ims/account/ledger`
- 页面级别：一级菜单页
- 依赖模块：已有账号登记数据（增量消费）；ACCT-001~004（台账字段由流程驱动）；ASSET 反向穿透（账号维度入口）
- 权限矩阵引用：ACCT-001~005 的查看行权限（R1/R4 全量；R2 R；R9 R 密码/敏感脱敏；R5/R6/R7 本人相关）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 账号编号/昵称 | 平台 | 当前责任人 | 状态 | [查询] [重置] [导出] |
+------------------------------------------------------------------+
| 表格: 账号编号 | 平台 | 账号昵称 | 当前责任人 | 状态 | 冻结标记 |      |
|       最近领用时间 | 累计充值 | 操作[详情][时间线][反向穿透]            |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
账号详情抽屉（720px）:
  +--------------------------------------------------------------+
  | Tab: [基本信息] [领用记录时间线] [关联资产]                      |
  | 基本信息: 账号编号/平台/昵称/实名人(脱敏)/责任人/状态/累计充值      |
  | 时间线Tab: 垂直事件流(倒序) + 类型筛选 + [导出交接凭证PDF]         |
  | 关联资产Tab: 该账号绑定资产列表(链接 ASSET 反向穿透)               |
  +--------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AccountLedgerPageReq {
  pageNo: number; pageSize: number;
  keyword?: string;          // 账号编号/昵称模糊
  platform?: string;
  ownerPersonId?: number;
  status?: AccountStatus;
}
interface AccountTimelineReq {
  accountId: number;
  eventTypes?: AccountEventType[];
  timeRange?: [string, string];
  pageNo: number; pageSize: number;
}

// 响应类型
interface AccountLedgerItem {
  accountId: number;
  accountNo: string;
  platform: string;
  nickname: string;
  ownerPersonId: number;
  ownerPersonName: string;
  verifiedPersonName: string;   // 实名人（脱敏由服务端按角色处理）
  status: AccountStatus;
  frozen: boolean;              // 冻结（离职未闭环/收回池）
  lastFlowTime: string;         // 最近领用/流转时间
  totalRecharge: number;        // 累计充值 DECIMAL(12,2)
}
interface TimelineEventItem {
  id: number;
  accountId: number;
  eventType: AccountEventType;
  refNo: string;                // 关联单据号（AP/TR/RT/…）
  refId: number;
  operatorName: string;
  eventTime: string;
  snapshotSummary: string;      // 快照摘要（责任人等）
  remark?: string;
}

// 枚举类型
type AccountStatus = 'IN_POOL' | 'IN_USE' | 'FROZEN' | 'RETURNED' | 'CANCELLED';
// 账号池可领用 / 在用 / 冻结（收回/离职未闭环） / 已归还 / 已注销（全局规范第 4 章权威枚举）
type AccountEventType =
  | 'REGISTER' | 'APPLY' | 'TRANSFER' | 'RETURN'
  | 'RECHARGE' | 'FREEZE' | 'UNFREEZE' | 'CANCEL';
// 与 ACCT API 契约 TimelineEventType 一致（大写字符串枚举）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /account/ledger/page`；R5/R6/R7 服务端自动过滤本人相关；失败重试占位。

#### 4.2 核心操作流程
**A. 查看账号详情（抽屉三 Tab）**
1. 行 [详情] → 打开抽屉，基本信息 Tab 默认；
2. [领用记录时间线] Tab：
   - 加载 `GET /account/timeline/{accountId}`（事件倒序，TL-R3）；
   - 事件卡片垂直时间流：左侧类型图标+时间，右侧单据摘要+操作人；类型筛选（多选）+ 时间区间过滤；
   - 点击事件卡片 → 抽屉内嵌二级详情或路由跳转原单据（领用单/流转单/归还单/充值单）；
   - [导出交接凭证 PDF]（TL 导出，R1/R2/R4 可用）；
   - 时间线只读不可编辑（TL-R1 只增不改）。
3. [关联资产] Tab → 该账号绑定资产列表，行操作 [反向穿透] 跳 ASSET-P3（account 维度）。

**B. 反向穿透入口**
- 行操作 [反向穿透] → 跳 `/ims/asset/reverse`（携带 accountId 预填自动查询）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| keyword | Input | 否 | 空 | 账号编号/昵称模糊 |
| platform | Select | 否 | 空 | 平台字典 |
| ownerPersonId | PersonSelect | 否 | 空 | 当前责任人 |
| status | Select | 否 | 空 | 在用/池可领用/冻结/已归还/已注销 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| accountNo | 账号编号 | 150 | — | 等宽字体 |
| platform | 平台 | 90 | — | 字典翻译 |
| nickname | 账号昵称 | 140 | — | — |
| ownerPersonName | 当前责任人 | 110 | — | 冻结人员黄名 |
| status | 状态 | 100 | — | tag：在用(绿)/池可领用(蓝)/冻结(黄)/已归还(青)/已注销(灰) |
| frozen | 冻结 | 70 | — | 图标 tooltip"离职归还未闭环"（BR-015） |
| lastFlowTime | 最近领用时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| totalRecharge | 累计充值 | 110 | ✓ | ¥ 前缀两位小数（R9 角色脱敏 ¥\*\*\*\*） |
| actions | 操作 | 220 | — | [详情][时间线][反向穿透] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与逻辑 |
|-----------|------|-----------|
| 账号详情抽屉 | Drawer 720px | 三 Tab 只读聚合；时间线 Tab 支持事件筛选/分页/导出 PDF；所有密码类信息一律不出现（APP-R4） |
| 事件单据跳转 | 路由跳转（非抽屉） | 按单据号跳 P2/P3/P4/P5 对应页面并定位单据 |

### 8. 错误处理
- 网络超时：列表与抽屉各 Tab 独立重试；
- 无数据：空态"暂无账号，可从已有账号登记数据同步"；
- 导出凭证失败（5005）：提示重试；
- 权限不足（1008）：提示并关闭抽屉。

### 9. BR 业务规则覆盖
- **BR-004（账号线上化率 100%）**：台账"最近领用时间"与时间线完整性即线上化落点（所有领用/流转/归还事件必须存在于时间线，TL-R2 事务内写入）；
- **BR-015（离职归还强制闭环）**：冻结列与责任人黄名标识；冻结账号不可发起新领用（在 P2 提交时服务端校验）。

---

## P2. 账号领用管理页（ACCT-001）

### 1. 页面概述
- 路由路径：`/ims/account/apply`
- 页面级别：一级菜单页
- 依赖模块：账号池（P1）、审批流（直属上级→运营总监）、工作台待办、ACCT-005 时间线
- 权限矩阵引用：R1 R/W/D（全量）、R4 R/W/D（全量审批）、R2 R、R9 R（密码脱敏→实际无密码展示）、R5/R6/R7 W（本人发起）+ 本人申请可见

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 申请单号 | 账号 | 申请人 | 状态(待审批/已领用/拒绝/已归还)     |
|         [查询] [重置]                        [发起新申请] [导出]     |
+------------------------------------------------------------------+
| 表格: 申请单号 | 账号(编号/昵称) | 申请人 | 用途 | 计划使用起止 |      |
|       审批状态 | 当前审批节点 | 申请时间 | 操作[审批][详情][交接确认]   |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
发起申请抽屉(560px):
  选择账号(账号池-可用,搜索) | 用途说明* | 计划开始* | 计划结束*  | 提交
审批抽屉(560px): 申请详情(只读) + 审批意见* + [通过][拒绝]
交接确认抽屉(560px): 申请详情 + 交接清单(密码已重置✓/绑定手机已换✓勾选) + 确认生效
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AccountApplyPageReq {
  pageNo: number; pageSize: number;
  applyNo?: string; accountId?: number;
  applicantUserId?: number;
  applyStatus?: ApplyStatus;
}
interface AccountApplyCreateReq {
  accountId: number;            // 必填，仅账号池-可用
  purpose: string;              // 必填 ≤256 字
  planStart: string;            // ISO 8601 必填
  planEnd: string;              // 必填，须晚于 planStart
  clientToken: string;
}
interface AccountApplyApproveReq {
  applyId: number;
  approved: boolean;
  opinion: string;              // 必填 ≤512 字（拒绝时必填，通过时可选）
}
interface AccountApplyConfirmReq {
  applyId: number;
  handoverItems: { itemKey: string; done: boolean }[];   // 交接清单勾选
  clientToken: string;
}

// 响应类型
interface AccountApplyItem {
  id: number; applyNo: string;            // AP+日期+流水
  accountId: number; accountNo: string; accountNickname: string;
  applicantUserId: number; applicantName: string;
  purpose: string;
  planStart: string; planEnd: string;
  applyStatus: ApplyStatus;
  currentStep: 'FIRST_APPROVER' | 'DIRECTOR_APPROVER' | 'HANDOVER' | 'DONE';   // 审批当前节点（交接中等中间态）
  currentApproverName: string;
  createdAt: string;
}
interface HandoverItemDef { itemKey: string; label: string; required: boolean; }

// 枚举类型
type ApplyStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'RETURNED';
// 待审批 / 已领用 / 拒绝 / 已归还（与 ACCT API 契约 ApplyStatus 一致；交接中等中间态由 currentStep 表达，不进状态机）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /account/apply/list`；数据范围按角色（R5/R6/R7 仅本人申请）服务端过滤；失败重试。

#### 4.2 核心操作流程
**A. 发起领用申请（R5/R6/R7 本人）**
1. [发起新申请] → 抽屉：账号选择器（仅列出"账号池-可用"账号，搜索平台/昵称/编号）；
2. 填写用途（必填）、计划起止（结束须晚于开始）；
3. 校验通过 → `POST /account/apply`（clientToken 防重复提交，按钮 loading）；
4. 成功 → 消息"已提交，等待直属上级审批" + 待办推送审批人（工作台联动）；
5. 账号当前非"池-可用"（如已被他人领用/冻结）→ 服务端 1003 → 表单账号字段下方内联错误"该账号当前不可领用"（APP-R1：同时仅一个责任人）。

**B. 审批（直属上级 → 运营总监）**
1. 审批人收到待办 → 点击进入本页（或工作台 [去处理] 直达）→ 行 [审批] 打开审批抽屉；
2. 查看申请详情（只读）→ 填写审批意见 → [通过]（进入下一节点）或 [拒绝]（必填意见，单据归档）；
3. 审批超 24h 未处理（APP-R2）→ 工作台升级提醒（服务端）；
4. 两级审批均通过 → 交接待办推送给申请人（currentStep=HANDOVER，applyStatus 保持 PENDING_APPROVAL 终态前置，交接确认后转 APPROVED）。

**C. 交接确认（申请人 + 管理员执行）**
1. [交接确认] 打开抽屉：交接清单勾选（密码已重置、绑定手机已更换、绑定设备已交接等，关键项必勾）；
2. 全部必勾完成 → [确认领用生效] → `PUT /account/apply/{id}/confirm`；
3. 生效：账号责任人变更（APP-R1）、时间线写入 apply 事件（TL-R2）、台账刷新、applyStatus=APPROVED、账号状态转 IN_USE；
4. 领用后 15 天无使用（APP-R3 / BR-012）→ 服务端生成提醒待办（不在本页处理）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| applyNo | Input | 否 | 空 | 申请单号 |
| accountId | AccountSelect | 否 | 空 | 账号选择 |
| applicantUserId | PersonSelect | 否 | 空 | 申请人 |
| applyStatus | Select | 否 | 空 | 待审批/已领用/拒绝/已归还（交接中经 currentStep 筛选） |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| applyNo | 申请单号 | 150 | — | 等宽字体 |
| accountInfo | 账号 | 180 | — | "编号 昵称"两行 |
| applicantName | 申请人 | 100 | — | — |
| purpose | 用途 | 自适应 | — | 省略 + tooltip |
| planRange | 计划使用起止 | 200 | — | yyyy-MM-dd ~ yyyy-MM-dd |
| applyStatus | 审批状态 | 110 | — | tag：待审批(蓝)/已领用(绿)/拒绝(红)/已归还(灰)；currentStep=HANDOVER 时叠加"交接中"青色角标 |
| currentStep | 当前节点 | 120 | — | 直属上级/运营总监/交接/完成 |
| createdAt | 申请时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 180 | — | 按状态+角色动态：[审批][交接确认][详情] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 发起申请抽屉 | Drawer 560px | accountId（必填，搜索选择仅池-可用）；purpose（必填 ≤256 字）；planStart/planEnd（必填，planEnd > planStart）；提交防重（clientToken + 按钮 loading） |
| 审批抽屉 | Drawer 560px | 上半部只读申请详情；opinion（拒绝必填 ≤512 字，通过可选）；[通过][拒绝] 二按钮 |
| 交接确认抽屉 | Drawer 560px | 只读申请详情 + 交接清单（checkbox，必勾项未勾不可提交）；底部提示"密码不在系统存储，仅记录交接事实"（APP-R4）；[确认领用生效] |
| 拒绝确认弹窗 | Modal 360px | 意见为空时阻断提交 |

### 8. 错误处理
- 网络超时：抽屉提交恢复 + 重试提示，表单内容保留；
- 账号被占用（1003）：内联错误在账号字段；
- 并发审批冲突（他人已处理）：刷新单据状态提示"该单据已被处理"；
- 权限不足：操作按钮按矩阵隐藏。

### 9. BR 业务规则覆盖
- **BR-004（账号领用线上化率 100%）**：领用唯一入口为本页线上流程，单据留痕 + 时间线联动即落点；
- **BR-012（领用超期自动提醒）**：领用生效后 15 天无使用，服务端提醒进入工作台（页面无操作，但状态列加"超期未使用"黄色角标提示）；
- **BR-016（多主体字段预留）**：发起请求透传 tenant_id=0 默认值（前端无感知，类型不暴露）。

---

## P3. 流转/收回管理页（ACCT-002）

### 1. 页面概述
- 路由路径：`/ims/account/transfer`
- 页面级别：一级菜单页
- 依赖模块：P1 台账、工作台（新责任人确认待办）、ASSET（资产同步转移提示）
- 权限矩阵引用：R1 R/W/D（全量）、R4 R/W/D（全量）、R5 W（本人经手发起）、R9 R（脱敏）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 流转单号 | 账号 | 类型(流转/收回) | 状态 | [查询] [重置]      |
|                                        [发起流转/收回] [导出]      |
+------------------------------------------------------------------+
| 表格: 流转单号 | 类型 | 账号 | 原责任人 | 新责任人 | 原因分类 |       |
|       交接说明 | 状态 | 生效时间 | 操作[确认][撤销][详情]            |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
发起抽屉(600px):
  流转类型(Segmented: 流转/收回) | 账号*(使用中) | 原责任人(自动带出)    |
  新责任人*(流转时必填,收回时空) | 原因分类* | 交接说明* | [提交]
确认抽屉: 单据详情 + [确认接收]（新责任人本人）
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AccountTransferPageReq {
  pageNo: number; pageSize: number;
  transferNo?: string; accountId?: number;
  transferType?: 'TRANSFER' | 'RECALL';
  status?: TransferStatus;
}
interface AccountTransferCreateReq {
  transferType: 'TRANSFER' | 'RECALL';
  accountId: number;                 // 必填，当前使用中
  toUserId?: number;                 // 流转必填；收回不传
  reasonType: TransferReasonType;    // 必填
  remark: string;                    // 交接说明必填 ≤512 字
  clientToken: string;
}
interface AccountTransferConfirmReq { transferId: number; }
interface AccountTransferRevokeReq { transferId: number; reason: string; }

// 响应类型
interface AccountTransferItem {
  id: number; transferNo: string;             // TR+日期+流水
  transferType: 'TRANSFER' | 'RECALL';
  accountId: number; accountNo: string; accountNickname: string;
  fromUserName: string;
  toUserName: string | null;                  // 收回单为空
  reasonType: TransferReasonType;
  remark: string;
  status: TransferStatus;
  createdAt: string; effectiveAt: string | null;
}

// 枚举类型
type TransferStatus = 'PENDING_CONFIRM' | 'EFFECTIVE' | 'REVOKED';
type TransferReasonType = 'TRANSFER_POSITION' | 'PRE_RESIGN' | 'VIOLATION' | 'BUSINESS_ADJUST';
// 调岗 / 离职前置 / 违规 / 业务调整
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /account/transfer/list`；R5 仅本人经手（from 或 to 为本人）；失败重试。

#### 4.2 核心操作流程
**A. 发起流转/收回**
1. [发起流转/收回] → 抽屉：类型切换（Segmented），收回时"新责任人"隐藏且账号进入冻结提示；
2. 账号选择器仅列"使用中"账号；选择后自动带出原责任人；
3. 原因分类（必选）+ 交接说明（必填）→ 提交（clientToken）；
4. 流转单：状态待确认 → 新责任人收到工作台待办（TRF-R1 防错领确认）；
5. 收回单：管理发起后直接生效 → 账号进入"池-冻结"（TRF-R2，需管理员解冻后方可再领用）；
6. 若该账号名下绑定资产 → 提交成功后弹窗提示"该账号绑定了 N 项资产，是否同步发起资产转移？"→ [跳转资产处理][仅转账号]（可选，不阻断）。

**B. 新责任人确认**
1. 新责任人 [去处理] → 本页行 [确认] → 抽屉展示单据详情 → [确认接收]；
2. 生效：责任人变更 + 时间线写入 transfer 事件（TRF-R3）+ 台账刷新。

**C. 撤销**
1. 待确认状态且发起人/管理员可 [撤销] → 填写撤销原因（必填）→ 单据作废留痕。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| transferNo | Input | 否 | 空 | 流转单号 |
| accountId | AccountSelect | 否 | 空 | 账号 |
| transferType | Select | 否 | 空 | 流转/收回 |
| status | Select | 否 | 空 | 待确认/已生效/已撤销 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| transferNo | 流转单号 | 150 | — | 等宽字体 |
| transferType | 类型 | 80 | — | tag：流转(蓝)/收回(橙) |
| accountInfo | 账号 | 180 | — | 编号+昵称 |
| fromUserName | 原责任人 | 100 | — | — |
| toUserName | 新责任人 | 100 | — | 收回单显示"—（收回至账号池）" |
| reasonType | 原因分类 | 100 | — | 字典翻译 |
| remark | 交接说明 | 自适应 | — | 省略 + tooltip |
| status | 状态 | 100 | — | tag：待确认(蓝)/已生效(绿)/已撤销(灰) |
| effectiveAt | 生效时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 160 | — | [确认]（新责任人+待确认）[撤销][详情] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 发起流转/收回抽屉 | Drawer 600px | transferType（Segmented 必选）；accountId（必填，仅使用中账号）；toUserId（流转必填人员搜索；收回隐藏）；reasonType（必选 4 类）；remark（必填 ≤512 字）；提交防重 |
| 确认接收抽屉 | Drawer 560px | 只读单据详情；[确认接收]（仅新责任人本人可见）；底部灰字"确认后账号责任人即刻变更" |
| 撤销弹窗 | Modal 420px | reason（必填 ≤256 字） |
| 资产同步转移提示弹窗 | Modal 480px | 资产列表只读 + [跳转资产处理][仅转账号] |

### 8. 错误处理
- 网络超时：提交重试、表单保留；
- 账号状态变化（已被流转/冻结）：1003 类内联错误"账号状态已变化，请刷新"；
- 确认人身份不符：服务端 1008，提示"仅新责任人可确认"；
- 权限不足：按钮隐藏。

### 9. BR 业务规则覆盖
- **BR-004（线上化率 100%）**：流转/收回全流程线上单据 + 时间线（TRF-R3）；
- **BR-015（离职归还强制闭环）**：收回后账号"池-冻结"态在台账可视；离职前置流转作为归还闭环的补充手段（归还项处理时跳转本页发起）。

---

## P4. 离职归还管理页（ACCT-003）

### 1. 页面概述
- 路由路径：`/ims/account/return`
- 页面级别：一级菜单页
- 依赖模块：AUTH-002（离职事件触发）、ACCT-001/002（账号处理）、ASSET（资产归还）、CERT（证件回收）、权限关闭联动
- 权限矩阵引用：R1 R/W/D（全量）、R2 R/W/D（全量主责）、R3 R（只读）、R4 R、R5 R（涉及账号只读）、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 归还单号 | 离职人 | 状态(进行中/已闭环/异常挂起) |          |
|         离职日期范围 | [查询] [重置]    [手动补建归还单(R1/R2)]      |
+------------------------------------------------------------------+
| 表格: 归还单号 | 离职人 | 部门 | 离职生效日 | 归还项进度 | 状态 |    |
|       逾期标记 | 闭环时间 | 操作[处理][详情]                          |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
归还单处理抽屉(720px):
  头部: 离职人信息 + 冻结提示(未闭环账号/资产冻结)
  归还项列表(Tab: 全部/账号/资产/证件):
    项 | 类型tag | 名称/编号 | 当前持有人 | 状态(待归还/已归还/转交/争议) | 操作[确认归还][转交][标记争议]
  底部: [全部闭环确认]（全部项∈{已归还,转交}时可用）
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ReturnOrderPageReq {
  pageNo: number; pageSize: number;
  returnNo?: string; userId?: number;
  status?: ReturnOrderStatus;
  resignDateRange?: [string, string];
}
interface ReturnGenerateReq {
  userId: number;                  // 手动补建：离职人
  resignDate: string;
  clientToken: string;
}
interface ReturnItemHandleReq {
  itemId: number;
  itemStatus: 'RETURNED' | 'TRANSFERRED' | 'DISPUTED';
  toUserId?: number;               // 转交时必填
  remark?: string;                 // 争议时必填 ≤512 字
}
interface ReturnCloseReq { returnOrderId: number; }

// 响应类型
interface ReturnOrderItem {
  id: number; returnNo: string;            // RT+日期+流水
  userId: number; userName: string;
  deptName: string;
  resignDate: string;
  status: ReturnOrderStatus;
  progress: { total: number; done: number; disputed: number };
  overdue: boolean;                        // D+7 未闭环（RET-R2）
  closedAt: string | null;
}
interface ReturnItemDetail {
  id: number;
  itemType: 'ACCOUNT' | 'ASSET' | 'CERT';
  itemLabel: string;                       // 账号昵称/资产名称/证件类型+姓名
  itemId: number;
  currentHolder: string;
  itemStatus: 'PENDING' | 'RETURNED' | 'TRANSFERRED' | 'DISPUTED';
  handlerName: string | null;
  remark?: string;
}

// 枚举类型
type ReturnOrderStatus = 'IN_PROGRESS' | 'CLOSED' | 'EXCEPTION_SUSPENDED';
// 进行中 / 已闭环 / 异常挂起（与 ACCT API 契约 ReturnOrderVO.status 一致）
type ReturnItemStatus = 'PENDING' | 'RETURNED' | 'TRANSFERRED' | 'DISPUTED';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /account/return/list`；失败重试；空态引导见 8。

#### 4.2 核心操作流程
**A. 归还单生成（自动为主）**
1. 钉钉离职事件 → 服务端 D+0 自动生成归还单（RET-R1），汇总名下账号/资产/证件，无需页面操作；
2. 手动补建（R1/R2，漏单场景）：[手动补建] → 抽屉选择离职人+离职日期 → `POST /account/return/generate`（clientToken）→ 生成后进入列表。

**B. 逐项处理（R2 主责）**
1. 行 [处理] → 打开处理抽屉，Tab 切换查看账号/资产/证件归还项；
2. 每项操作：
   - [确认归还]：账号 → 收回至"池-冻结"；资产 → 归还入库（状态 RETURNED）；证件 → 回收（CERT 档案状态置"已回收"）；
   - [转交]：选择接收人（人员选择，必填）→ 单独走 P3 流转单（账号）或资产转移；
   - [标记争议]：填写争议说明（必填）→ 项状态"争议"，进入行政裁决流程（RET-R4）；
3. 每次处理即时保存（`PUT /return/item/{itemId}`），进度条刷新。

**C. 闭环确认**
1. 全部项 ∈ {已归还, 转交}（RET-R3 / BR-015）→ [全部闭环确认] 按钮激活；
2. 点击 → `PUT /return/{id}/close`（服务端校验闭环条件 + 钉钉离职生效）；
3. 成功：权限关闭（AUTH-002 联动）、账号/资产解冻、归还单归档；
4. 存在争议项 → 按钮禁用 + tooltip"N 项争议待裁决"；
5. D+7 未闭环（RET-R2）→ 逾期红标 + 服务端升级行政负责人（工作台待办）。

**D. 异常挂起**
- 争议长期未决 → R2 可 [挂起]（填原因），状态"异常挂起"，闭环链路等待裁决后恢复。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| returnNo | Input | 否 | 空 | 归还单号 |
| userId | PersonSelect | 否 | 空 | 离职人 |
| status | Select | 否 | 空 | 进行中/已闭环/异常挂起 |
| resignDateRange | DateRangePicker | 否 | 空 | 离职生效日 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| returnNo | 归还单号 | 150 | — | 等宽字体 |
| userName | 离职人 | 100 | — | 冻结态黄色 |
| deptName | 部门 | 140 | — | — |
| resignDate | 离职生效日 | 110 | ✓ | yyyy-MM-dd |
| progress | 归还项进度 | 140 | — | "5/8 已处理 · 1 争议" 进度条 |
| status | 状态 | 100 | — | tag：进行中(蓝)/已闭环(绿)/异常挂起(红) |
| overdue | 逾期 | 80 | — | 逾期红标"逾期 N 天"（D+7） |
| closedAt | 闭环时间 | 150 | ✓ | yyyy-MM-dd HH:mm；未闭环"—" |
| actions | 操作 | 140 | — | [处理][详情] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 归还单处理抽屉 | Drawer 720px | 头部只读：离职人/部门/生效日/冻结提示横幅"未闭环期间离职人 IMS 登录受限，名下账号/资产冻结"；归还项列表 Tab（全部/账号/资产/证件）+ 行内操作；底部 [全部闭环确认]（条件激活） |
| 转交弹窗（项内） | Modal 420px | toUserId（必填人员搜索）；提示"将发起流转单，需接收人确认" |
| 争议标记弹窗（项内） | Modal 420px | remark（必填 ≤512 字） |
| 手动补建抽屉 | Drawer 480px | userId（必填，仅离职/冻结人员可选）；resignDate（必填）；防重 clientToken |
| 挂起弹窗 | Modal 420px | 原因必填 |

### 8. 错误处理
- 网络超时：项处理即时保存失败 → 项行内错误 + 重试，不影响其他项；
- 闭环校验失败（存在待归还/争议项）：服务端 1001 → 提示具体未完成项数；
- 手动补建重复（同人已有进行中归还单）：提示"该离职人已有归还单 RTxxx"；
- 空态：引导"离职归还单由钉钉离职事件自动生成，异常缺单时使用手动补建"。

### 9. BR 业务规则覆盖
- **BR-015（离职归还强制闭环）**：本页即 BR-015 全量落点——冻结提示、逐项闭环条件（RET-R3）、闭环确认校验、D+7 逾期升级（RET-R2）、闭环后权限关闭联动。

---

## P5. 冲话费管理页（ACCT-004）

### 1. 页面概述
- 路由路径：`/ims/account/recharge`
- 页面级别：一级菜单页（记录列表 + 登记抽屉 + 月度核对视图）
- 依赖模块：P1 账号台账、财务核对（BR-017）、工作台督办
- 权限矩阵引用：R3 R/W/D（全量主责）、R1 R（全量）、R4 R（全量）、R9 R（全量）；其余角色不可见

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 核对概览条: 本月待核对 N 条 | 上月差异率 1.2%(目标<2%) | 上月差异金额 ¥xx |
|                                        [触发月度核对] [成本汇总报表] |
+------------------------------------------------------------------+
| 查询行: 账号 | 核对状态(未核对/一致/差异) | 充值日期范围 | [查询][重置] |
|                                        [登记充值记录] [导出]          |
+------------------------------------------------------------------+
| 表格: 账号 | 充值金额 | 充值渠道 | 充值日期 | 凭证 | 核对状态 | 差异金额 |
|       | 操作人 | 登记时间 | 操作[编辑][查看凭证][核对详情]              |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
登记抽屉(560px): 账号* | 金额* | 渠道* | 充值日期* | 凭证上传(>5000必填) | 备注
月度核对抽屉: 选择月份 | 拉取平台消费 → 差异清单 | [生成核查工单]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface RechargePageReq {
  pageNo: number; pageSize: number;
  accountId?: number;
  verifyStatus?: RechargeVerifyStatus;
  rechargeDateRange?: [string, string];
}
interface RechargeCreateReq {
  accountId: number;              // 必填
  amount: number;                 // 必填 > 0，两位小数
  channel: string;                // 必填
  rechargeDate: string;           // 必填
  voucherFileId?: string;         // >5000 必填
  remark?: string;
  clientToken: string;
}
interface RechargeUpdateReq extends Partial<RechargeCreateReq> { id: number; }
interface RechargeVerifyReq { month: string; clientToken: string; }   // 'yyyy-MM'

// 响应类型
interface RechargeItem {
  id: number;
  accountId: number; accountNo: string; accountNickname: string;
  amount: number;                 // DECIMAL(12,2)
  channel: string;
  rechargeDate: string;
  voucherUrl: string | null;      // 仅 R3 可见签名 URL
  verifyStatus: RechargeVerifyStatus;
  verifyDiff: number | null;      // 差异金额
  operatorName: string;
  createdAt: string;
}
interface RechargeVerifyResult {
  month: string;
  totalRecharge: number;
  platformConsumed: number;
  diffAmount: number;
  diffRate: number;               // 0~1
  diffItems: { accountId: number; accountNickname: string; rechargeAmount: number; platformAmount: number; diff: number }[];
}
interface RechargeSummaryResp {
  byAccount: { accountId: number; accountNickname: string; totalAmount: number }[];
  byDept: { deptName: string; totalAmount: number }[];
  byMonth: { month: string; totalAmount: number }[];
}

// 枚举类型
type RechargeVerifyStatus = 'UNVERIFIED' | 'MATCHED' | 'DIFF';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /account/recharge/list` + 概览统计（上月核对结果缓存）；失败分区重试。

#### 4.2 核心操作流程
**A. 登记充值记录（R3）**
1. [登记充值记录] → 抽屉：选账号（在用/池内均可）→ 金额（>0，两位小数）→ 渠道 → 日期 → 凭证上传（图片/PDF）；
2. 联动校验：金额 > 5000 → 凭证必填（RC-R3），未传时提交按钮禁用 + 提示；
3. 提交（clientToken）→ 列表刷新，状态"未核对"。

**B. 编辑记录（未核对状态可编辑；已核对一致后禁改）**
1. [编辑] → 同登记抽屉回填；差异状态记录需先 [发起核查工单] 处理后由 R1 解锁更正。

**C. 月度核对（R3）**
1. [触发月度核对] → 抽屉选月份（默认上月，每月 5 日前完成 RC-R1）→ `POST /account/recharge/verify`；
2. 结果：差异率、差异金额、差异清单（逐账号充值 vs 平台消费对比表）；
3. 差异率 ≥ 2%（RC-R2 / BR-017）→ 红色告警 + [生成财务核查工单] 按钮 → 工单进入工作台待办；
4. 差异项行操作 [核对详情] → 差异明细弹窗。

**D. 成本汇总**
- [成本汇总报表] → 抽屉/页面内切换汇总视图：按账号/部门/月份三个维度（RechargeSummaryResp），可导出。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| accountId | AccountSelect | 否 | 空 | 账号 |
| verifyStatus | Select | 否 | 空 | 未核对/一致/差异 |
| rechargeDateRange | DateRangePicker | 否 | 本月 | 充值日期范围 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| accountInfo | 账号 | 180 | — | 编号+昵称 |
| amount | 充值金额 | 120 | ✓ | ¥ 前缀两位小数 |
| channel | 充值渠道 | 100 | — | 字典 |
| rechargeDate | 充值日期 | 110 | ✓ | yyyy-MM-dd |
| voucher | 凭证 | 80 | — | 图标，仅 R3 可点（60s 签名 URL 预览）；其他角色隐藏 |
| verifyStatus | 核对状态 | 100 | — | tag：未核对(灰)/一致(绿)/差异(红) |
| verifyDiff | 差异金额 | 110 | ✓ | ¥xx.xx；无差异"—" |
| operatorName | 操作人 | 100 | — | — |
| createdAt | 登记时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 160 | — | [编辑][查看凭证][核对详情] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 登记/编辑抽屉 | Drawer 560px | accountId 必填；amount 必填 >0 两位小数；channel 必选；rechargeDate 必填（不得晚于今日）；voucherFileId 条件必填（>¥5000，RC-R3）；remark ≤256 字；防重 |
| 月度核对抽屉 | Drawer 720px | month 必选（默认上月）；触发后展示核对结果卡（差异率大数字，≥2% 红）+ 差异清单表 + [生成财务核查工单] |
| 核对详情弹窗 | Modal 480px | 单条差异：充值额 / 平台消费额 / 差异额 对比 |
| 成本汇总视图 | 页面内切换（非抽屉） | 三维度汇总表 + 导出 |

### 8. 错误处理
- 网络超时：提交防重 + 重试；
- 凭证上传失败（5005 文件落盘）：提示重传，不影响其他字段；
- 核对数据拉取失败（平台接口超时）：提示"平台消费数据拉取失败，请稍后重试"，核对结果不入库；
- 权限不足：R1/R4/R9 进入只读（无登记/编辑按钮，凭证列隐藏）。

### 9. BR 业务规则覆盖
- **BR-017（冲话费账实核对差异率 < 2%）**：核对概览条常显上月差异率（≥2% 红色告警）；月度核对流程 + 差异清单 + ≥2% 自动生成财务核查工单即 BR-017 页面闭环；
- **RC-R1（每月 5 日前）**：每月 1~5 日进入页面顶部横幅提示"请于 5 日前完成上月核对"；
- **BR-016（多主体预留）**：tenant_id 默认透传，前端无感知。

---

## 模块通用备注
- 本模块 5 个一级页面 + 时间线并入 P1 详情抽屉；抽屉/弹窗共 14 个（账号详情、发起申请、审批、交接确认、拒绝确认、发起流转、确认接收、撤销、资产同步提示、归还处理、转交、争议、补建、核对详情等）。
- 单据编号口径：AP/TR/RT 前缀 + 日期 + 流水（与 PRD 5.8~5.10 一致）；
- 时间线（ACCT-005）只读、只增不改（TL-R1），所有单据操作在事务内写入时间线（TL-R2），页面跳转遵循"事件卡片 → 原单据"路径。
