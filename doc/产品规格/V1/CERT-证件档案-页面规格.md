# CERT - 证件档案 页面规格

> 依据：《IMS第一期PRD-V1.md》5.13~5.15（CERT-001~003）、《共享技术规范-数据库与API.md》第 7/8 章、《共享技术规范-分期技术约束.md》1.4（OCR/服务端文件目录存储/水印约束 V1-D1~D3）。
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/cert`。

## 0. 模块总览

| 页面 | 路由 | 级别 | 对应功能点 |
|------|------|------|-----------|
| P1 证件档案列表 | `/ims/cert/archive` | 一级菜单页（索引 + 上传/审核抽屉 + 分级查看） | CERT-001、CERT-003 查看 |
| P2 到期预警中心 | `/ims/cert/expire` | 一级菜单页（预警列表 + 换证抽屉 + 统计看板） | CERT-002 |
| 水印分级查看 | P1 行操作打开的水印预览层 | 全屏预览层（Drawer/Modal） | CERT-003 |
| 分级与审计配置 | `/ims/cert/security`（并入 P1 或独立 Tab） | 一级菜单页 Tab（R1） | CERT-003 配置与审计 |

通用 UI 约定：查询条件一行紧凑排布；交互优先内联抽屉；证件号脱敏（前 3 后 4，如 110\*\*\*\*\*\*\*\*\*\*1234）；状态 tag 语义色；证件原图一律经水印代理端点在线查看，禁止下载（V1-D3）。

**水印分级口径（页面强制）**：
- L1（默认全员）：仅索引可见，不可查看原图；
- L2（角色/岗位配置 · ADR-IMS-008）：在线查看 + 动态盲水印（内容=查看人姓名+手机号后 4 位+时间戳，V1-D3）；
- L3（白名单：R1 + 行政管理员明文授权）：明文在线查看，仍禁下载；
- 每次查看全量审计落库（CERT-003，服务端），前端无感知。

---

## P1. 证件档案列表页（CERT-001 + CERT-003 查看入口）

### 1. 页面概述
- 路由路径：`/ims/cert/archive`
- 页面级别：一级菜单页
- 依赖模块：服务端加密文件目录（鉴权下载链 · 本期不上对象存储）、**AUTH 角色（L2 级别来源 · ADR-IMS-008）**、CERT-002 预警状态联动、LIVE-001（锁定拦截联动）
- 权限矩阵引用：CERT-001：R1 R/W/D（全量）、R2 R/W（全量主责）、R4 R（索引，不见原图）、R7 R（本人证件）、R9 R（索引脱敏）；CERT-003 查看分级：L1/L2/L3 见上；级别配置仅 R1

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 数字化率横幅: 数字化率 96.2%（目标>95%,BR-005） [查看统计]           |
+------------------------------------------------------------------+
| 查询行: 持有人 | 证件类型 | 证件号(加密索引精确查) | 状态 |          |
|         有效期范围 | [查询] [重置]      [上传证件档案(R1/R2)]        |
+------------------------------------------------------------------+
| 表格: 持有人 | 证件类型 | 证件号(脱敏) | 签发日期 | 有效期至 |       |
|       剩余天数 | 档案状态 | 入库时间 | 操作[查看(分级)][审核][换证][详情] |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
上传抽屉(560px): 持有人*(内部人员选择/外协姓名输入) | 证件类型* |
  证件号* | 签发日期* | 有效期至* | 扫描件上传*(图片/PDF) | [提交审核]
水印查看层(全屏): 图片区(叠加动态盲水印) + 计时提示 + [关闭]（无下载按钮）
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface CertArchivePageReq {
  pageNo: number; pageSize: number;
  holderUserId?: number;          // 内部持有人
  holderName?: string;            // 外协姓名模糊
  certType?: CertType;
  certNo?: string;                // 精确查询（服务端 hash 索引，非明文）
  status?: CertArchiveStatus;
  expireRange?: [string, string]; // 有效期范围
}
interface CertUploadReq {
  holderUserId?: number;          // 内部人员（与 holderName 二选一）
  holderName?: string;            // 外协姓名
  certType: CertType;             // 必填
  certNo: string;                 // 必填，格式校验（身份证 18 位规则）
  issueDate: string;              // 必填
  expireDate: string;             // 必填，晚于 issueDate
  fileKey: string;                // 必填，已上传文件的 fileKey（服务端相对路径）
  clientToken: string;
}
interface CertReviewReq {
  certId: number;
  approved: boolean;
  remark?: string;                // 驳回必填
}
interface CertViewReq { certId: number; }   // 分级查看

// 响应类型
interface CertArchiveItem {
  certId: number;
  holderUserId: number | null;
  holderName: string;
  holderDept: string | null;
  certType: CertType;
  certNoMasked: string;           // 服务端脱敏：前3后4
  issueDate: string;
  expireDate: string;
  remainDays: number;             // 剩余天数（负=已过期）
  status: CertArchiveStatus;
  viewLevel: 'L1' | 'L2' | 'L3';  // 当前用户对该档案的查看级别
  uploadedAt: string;
}
interface CertViewResp {
  viewLevel: 'L1' | 'L2' | 'L3';
  previewUrl: string | null;      // L1 时 null；L2/L3 为 60s 签名水印代理 URL
  watermarkText: string | null;   // L2 水印内容回显
  viewDurationLimit: number;      // 建议查看时限（秒，超时自动关闭）
}
interface CertDigitalMetricsResp {
  digitizedRate: number;          // BR-005，0~1
  totalCount: number; digitizedCount: number;
  byType: { certType: CertType; total: number; digitized: number }[];
}

// 枚举类型
type CertType = 'IDCARD' | 'PASSPORT' | 'OTHER';
type CertArchiveStatus = 'PENDING_REVIEW' | 'EFFECTIVE' | 'EXPIRING' | 'EXPIRED' | 'RECYCLED';
// 待审 / 生效 / 即将到期 / 已过期 / 已回收（=全局规范 CertStatus；页面规格起见别名 CertArchiveStatus 与契约字段对齐，值域一致）
```

### 4. 交互流程

#### 4.1 页面加载
1. 骨架屏 → 并行 `GET /cert/archive/list` + 数字化率横幅（`GET /cert/archive/digital-metrics`）；
2. R7 主播进入自动过滤本人证件（服务端）；R4/R9 仅索引字段（无查看按钮或按钮置灰）；
3. 失败分区重试。

#### 4.2 核心操作流程
**A. 上传证件档案（R2 主责 / R1）**
1. [上传证件档案] → 抽屉：选择持有人（内部人员搜索 / 切换"外协人员"输入姓名）；证件号即时前端格式校验（身份证 18 位含校验位）；
2. 上传扫描件（图片/PDF，≤20MB）→ POST IMS 上传端点落服务端加密目录，返回 fileKey；
3. 提交后状态"待审"（CERT-A-R4）；
4. 重复校验：同人同类型已有生效档案 → 服务端提示"已存在有效档案，如为新证请走换证流程"（CERT-A-R3）；
5. OCR 增量（V1-D1）：仅新上传触发，识别结果回填表单供人工确认（证件号/有效期预填可改）。

**B. 档案审核（R2/R1）**
1. 待审行 [审核] → 抽屉预览（行政管理员默认 L2/L3 可见原图）+ 元信息比对；
2. [通过]（状态生效）或 [驳回]（填写原因，退回上传人重新提交）。

**C. 分级查看（水印层）**
1. 行 [查看] → 前端先按行内 viewLevel 预判：
   - L1：按钮置灰 tooltip"无原图查看权限，仅索引可见"；
   - L2/L3：`GET /cert/security/view/{certId}` 获取 60s 签名水印代理 URL；
2. 打开全屏水印查看层：图片居中 + 动态盲水印平铺（V1-D3）+ 右上角查看计时；L3 无水印明文；
3. 查看层**无下载/右键保存**（前端禁用 contextmenu/拖拽 + 服务端 URL 60s 过期兜底）；
4. 超时（viewDurationLimit，默认 300s）自动关闭并提示；
5. 1 小时内查看 > 10 次 → 服务端告警（CERT-S-R3），前端无感知。

**D. 详情**
- 行 [详情] → 抽屉：元信息 + 状态 + 预警记录（CERT-002 联动）+ 查看审计摘要（仅 R1 可见：最近 5 条查看记录）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| holderUserId / holderName | PersonSelect / Input | 否 | 空 | 内部/外协持有人（Segmented 切换） |
| certType | Select | 否 | 空 | 身份证/护照/其他 |
| certNo | Input | 否 | 空 | 精确查询（服务端 SHA-256 hash 索引，输入明文前端即散列/或后端处理，不明文落日志） |
| status | Select | 否 | 空 | 待审/生效/即将到期/已过期/已回收 |
| expireRange | DateRangePicker | 否 | 空 | 有效期范围 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| holderName | 持有人 | 120 | — | 外协人员后加"（外协）"灰标 |
| certType | 证件类型 | 100 | — | 字典翻译 |
| certNoMasked | 证件号 | 170 | — | 前 3 后 4 脱敏（110\*\*\*\*…\*\*\*\*1234） |
| issueDate | 签发日期 | 110 | — | yyyy-MM-dd |
| expireDate | 有效期至 | 110 | ✓ | yyyy-MM-dd |
| remainDays | 剩余天数 | 100 | ✓ | ≤0 红"已过期"；≤7 红；≤30 黄；其余绿 |
| status | 档案状态 | 100 | — | tag：待审(蓝)/生效(绿)/即将到期(黄)/已过期(红)/已回收(灰) |
| uploadedAt | 入库时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 220 | — | [查看(分级)][审核][换证][详情]，按状态与角色动态显示 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 上传证件抽屉 | Drawer 560px | 持有人二选一必填；certType 必选；certNo 必填（前端身份证格式校验）；issueDate/expireDate 必填且 expireDate > issueDate；fileKey 必填（服务端上传返回）；OCR 回填字段可人工修改；防重 clientToken |
| 审核抽屉 | Drawer 640px | 只读元信息 + 原图预览（审核人 L2/L3）；[通过][驳回（remark 必填）] |
| 证件详情抽屉 | Drawer 560px | 只读聚合；R1 附加查看审计摘要（最近 5 条：查看人/级别/时长） |
| 水印查看层 | 全屏 Modal/Drawer 100% | 只读图片 + 盲水印；无下载控件；计时自动关闭；关闭时上报查看时长（服务端记录 view_duration） |
| 数字化率统计弹窗 | Modal 560px | 总数/已数字化/分类型统计 + 目标线 95% |

### 8. 错误处理
- 网络超时：列表/横幅独立重试；
- 上传失败（5005 文件落盘）：抽屉内文件区红字提示重传，其他字段保留；
- 查看权限不足（L1 或 1008）：查看按钮置灰 + tooltip，点击无效；
- 签名 URL 过期（60s）：查看层提示"链接已过期，请重新打开查看"；
- 重复档案（CERT-A-R3）：提交时服务端校验返回，弹窗引导走换证（跳 P2 换证抽屉）；
- OCR 识别失败：不阻断上传，表单留空人工填写。

### 9. BR 业务规则覆盖
- **BR-005（证件数字化率 > 95%）**：页面顶部数字化率横幅常显 + 未达标红色，统计弹窗分类型展示缺口；
- **BR-013（到期预警）**：档案列表"剩余天数"三色渲染（黄/红/过期锁定）与状态联动 P2；已锁定档案在 LIVE-001 登记时服务端强校验拦截（LIVE-R2），本页状态列展示"已过期-锁定"红色 tag 提示影响；
- **BR-016（多主体预留）**：上传透传默认主体，前端无感知。

---

## P2. 到期预警中心页（CERT-002）

### 1. 页面概述
- 路由路径：`/ims/cert/expire`
- 页面级别：一级菜单页（预警列表 + 换证抽屉 + 统计看板）
- 依赖模块：CERT-001（换证上传复用）、工作台/钉钉推送（预警通知）、LIVE-001（锁定拦截联动）
- 权限矩阵引用：R1 R/W（全量）、R2 R/W/D（全量主责）、R4 R（全量）、R5 R（涉及本人）、R7 R（本人）、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 统计看板: [黄色预警 N] [红色预警 N] [已锁定 N] [本月换证 N]  [手动扫描] |
+------------------------------------------------------------------+
| 查询行: 持有人 | 预警级别(黄/红/锁定) | 预警状态(预警中/已换证/已锁定) |
|         [查询] [重置]                                             |
+------------------------------------------------------------------+
| 表格: 持有人 | 证件类型 | 证件号(脱敏) | 有效期至 | 剩余天数 |       |
|       预警级别 | 通知状态 | 换证状态 | 操作[换证登记][提醒][详情]      |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
换证抽屉(600px): 旧证信息(只读) | 新证上传区(复用P1上传组件) | [提交换证]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface CertExpirePageReq {
  pageNo: number; pageSize: number;
  holderUserId?: number;
  warnLevel?: CertWarnLevel;
  status?: CertExpireStatus;
}
interface CertScanReq { clientToken: string; }       // 手动触发扫描
interface CertRenewReq {
  certId: number;                   // 旧证
  newCert: CertUploadReq;           // 新证信息+文件（复用上传结构）
  clientToken: string;
}
interface CertRemindReq { certId: number; remindChannel?: 'APP' | 'DINGTALK'; }   // 渠道缺省默认双渠道，与契约 2.2.5 一致

// 响应类型
interface CertExpireItem {
  certId: number;
  holderUserId: number | null;
  holderName: string;
  certType: CertType;
  certNoMasked: string;
  expireDate: string;
  remainDays: number;
  warnLevel: CertWarnLevel;
  notifiedUsers: string;            // 已通知人摘要
  status: CertExpireStatus;
  lastNotifiedAt: string | null;
}
interface CertExpireStatsResp {
  yellowCount: number; redCount: number; lockedCount: number;
  renewedThisMonth: number;
}

// 枚举类型
type CertWarnLevel = 'YELLOW' | 'RED' | 'LOCKED';     // T−30 / T−7 / T−0（BR-013）
type CertExpireStatus = 'WARNING' | 'RENEW_RESOLVED' | 'EXPIRED_LOCKED';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /cert/expire/list` + `GET /cert/expire/stats`；R7/R5 服务端过滤本人/涉及本人；失败分区重试。

#### 4.2 核心操作流程
**A. 手动触发扫描（R1/R2）**
1. [手动扫描] → 确认弹窗 → `POST /cert/expire/scan`（clientToken）；每日 08:00 定时扫描兜底（CERT-E-R1），手动为补偿；
2. 完成后列表与看板刷新；同级别不重复推送由服务端保证（CERT-E-R2），前端仅展示通知状态。

**B. 换证登记（R2 主责 / R1）**
1. 行 [换证登记] → 抽屉：上半部旧证只读信息；下半部新证上传（复用 P1 上传组件：类型/证件号/起止日期/扫描件）；
2. 提交（clientToken）→ 走审核流程（新证待审→行政审核生效，CERT-A-R4）；
3. 生效后：旧证归档（状态已回收）、预警解除（状态 RENEW_RESOLVED）、通知闭环；
4. 新证未审核生效前，旧证预警状态保持（不提前解除）。

**C. 手动提醒（R2）**
1. 行 [提醒] → 选择渠道（工作台/钉钉）→ `PUT /cert/expire/{id}/remind`；
2. 用于持有人未响应时人工催办（不占用 3 次系统推送限额之外的重复限制，服务端记录）。

**D. 详情**
- [详情] → 抽屉：预警产生/升级轨迹（黄→红→锁定时间线）、通知记录、换证记录。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| holderUserId | PersonSelect | 否 | 空 | 持有人 |
| warnLevel | Select | 否 | 空 | 黄色(T−30)/红色(T−7)/锁定(T−0) |
| status | Select | 否 | 空 | 预警中/已换证/已锁定 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| holderName | 持有人 | 120 | — | — |
| certType | 证件类型 | 100 | — | 字典翻译 |
| certNoMasked | 证件号 | 170 | — | 前 3 后 4 脱敏 |
| expireDate | 有效期至 | 110 | ✓ | yyyy-MM-dd |
| remainDays | 剩余天数 | 100 | ✓ | 30~8 黄；7~1 红；≤0 红"已过期" |
| warnLevel | 预警级别 | 100 | — | tag：黄色(黄)/红色(红)/锁定(深红) |
| notifiedUsers | 通知状态 | 160 | — | "已通知：本人、行政" 摘要 + tooltip 明细 |
| status | 换证状态 | 100 | — | tag：预警中(黄)/已换证(绿)/已锁定(灰) |
| actions | 操作 | 200 | — | [换证登记][提醒][详情] 按角色显示 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 换证登记抽屉 | Drawer 600px | 旧证只读区；新证表单（复用上传校验：必填、格式、有效期）；防重 clientToken；提交后提示"新证需行政审核生效后旧证自动归档" |
| 手动扫描确认弹窗 | Modal 360px | 文案 + [确认] |
| 提醒渠道弹窗 | Modal 360px | remindChannel 单选（APP/钉钉，缺省默认双渠道，与契约 2.2.5 一致） |
| 预警详情抽屉 | Drawer 560px | 只读：预警升级轨迹（黄→红→锁定时间线）、通知记录列表、换证记录 |

### 8. 错误处理
- 网络超时：分区重试；换证提交失败保留草稿；
- 扫描调度失败（5006）：提示稍后重试；
- 新证与旧证同人同类型冲突：走 CERT-A-R3 换证逻辑（服务端自动关联），冲突异常时明确报错文案；
- 空态：绿色空态"当前无到期预警 🎉"（不用 emoji 于正文，仅示意，实际用文字）。

### 9. BR 业务规则覆盖
- **BR-013（T−30 黄/T−7 红/T−0 锁定）**：预警级别列三色 tag、看板三计数、扫描频率（每日 08:00 + 手动）、升级推送（CERT-E-R2 同级不重复）均在本页落点；锁定证件联动 LIVE-001 拦截（LIVE-R2）在直播登记页强校验（见 LIVE 规格）。

---

## P3. 分级与审计管理（CERT-003 配置，R1 专属）

### 1. 页面概述
- 路由路径：`/ims/cert/archive` 页内 Tab [查看分级与审计]（或 `/ims/cert/security` 独立菜单，仅 R1 可见）
- 页面级别：一级菜单页 Tab / 二级页面
- 依赖模块：**AUTH 角色（L2 角色来源 · ADR-IMS-008）**、审计日志查询
- 权限矩阵引用：CERT-003：R1 R/W/D（全量，唯一角色）；级别配置与审计查询仅 R1

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [查看级别配置] [查看审计日志] [异常访问报告]                    |
+------------------------------------------------------------------+
| 级别配置Tab:                                                      |
|   规则表: 级别 | 适用范围(默认全员/角色/白名单) | 水印样式 |      |
|           操作[编辑]                                               |
|   L3 白名单人员管理: [添加人员][移除]                               |
| 审计日志Tab:                                                      |
|   查询行: 查看人 | 证件 | 级别 | 时间范围                           |
|   表格: 查看人 | 证件(脱敏) | 查看级别 | 水印内容 | 查看时长 |       |
|         IP/设备 | 查看时间                                          |
| 异常Tab: 高频访问列表(1小时>10次) + [导出报告]                       |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface CertLevelConfigReq {
  level: 'L2' | 'L3';
  scopeType: 'ALL' | 'TEMPLATE' | 'WHITELIST';
  templateIds?: number[];          // scopeType=TEMPLATE 时
  whitelistUserIds?: number[];     // scopeType=WHITELIST 时（L3）
  watermarkStyle?: { opacity: number; position: string };
}
interface CertViewLogPageReq {
  pageNo: number; pageSize: number;
  viewerUserId?: number; certId?: number;
  viewLevel?: 'L1' | 'L2' | 'L3';
  timeRange?: [string, string];
}

// 响应类型
interface CertLevelConfigItem {
  level: 'L1' | 'L2' | 'L3';
  scopeType: 'ALL' | 'TEMPLATE' | 'WHITELIST';
  scopeLabels: string[];           // 模板名/白名单姓名
  watermarkStyle: { opacity: number; position: string } | null;
}
interface CertViewLogItem {
  id: number;
  viewerName: string;
  certLabel: string;               // 持有人+类型
  viewLevel: 'L1' | 'L2' | 'L3';
  watermarkText: string | null;
  viewDuration: number;            // 秒
  ip: string; device: string;
  createdAt: string;
}
interface CertRiskReportItem {
  viewerName: string;
  viewCountInHour: number;
  certCount: number;
  lastViewAt: string;
}
```

### 4. 交互流程

#### 4.1 页面加载
仅 R1 可见入口；骨架屏 → 配置与审计默认加载；失败重试。

#### 4.2 核心操作流程
**A. 级别配置（R1）**
1. 规则表展示三级：L1（默认全员，不可编辑范围，仅说明）；L2（默认按**角色** · ADR-IMS-008）；L3（白名单）；
2. [编辑] L2 → 抽屉选择适用**角色**（多选）+ 水印样式（透明度滑杆 0.05~0.3、位置九宫格）；
3. [编辑] L3 → 白名单人员管理（添加/移除，仅限 R1 本人之外可加行政管理员等）；保存即时生效（CERT-S-R1）。

**B. 审计日志查询**
- 多条件分页查询；行 [水印内容] 列显示完整水印文本（工号+姓名+时间戳回溯）。

**C. 异常访问报告**
- 高频访问列表（1 小时 > 10 次，CERT-S-R3）+ [导出报告]。

### 5. 查询条件表（审计 Tab）

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| viewerUserId | PersonSelect | 否 | 空 | 查看人 |
| certId | Input+搜索 | 否 | 空 | 证件（持有人/编号搜索） |
| viewLevel | Select | 否 | 空 | L1/L2/L3 |
| timeRange | DateRangePicker | 否 | 近 7 天 | 查看时间 |

### 6. 表格列定义（审计 Tab）

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| viewerName | 查看人 | 110 | — | — |
| certLabel | 证件 | 180 | — | "姓名·身份证（110\*\*\*\*1234）" |
| viewLevel | 查看级别 | 90 | — | tag：L1(灰)/L2(蓝)/L3(橙) |
| watermarkText | 水印内容 | 自适应 | — | 等宽小字 |
| viewDuration | 查看时长 | 90 | ✓ | "3 分 12 秒" |
| ipDevice | IP/设备 | 200 | — | 两行 |
| createdAt | 查看时间 | 150 | ✓ | yyyy-MM-dd HH:mm |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| L2 级别编辑抽屉 | Drawer 480px | templateIds（多选，必选至少 1 个）；watermarkStyle.opacity（滑杆 0.05~0.3 默认 0.12）；position（九宫格单选默认右下） |
| L3 白名单管理抽屉 | Drawer 480px | 人员多选（当前 R1 与行政白名单）；保存即时生效并提示"下次查看即按新级别" |
| 导出报告确认弹窗 | Modal 360px | 导出范围确认（导出留审计） |

### 8. 错误处理
- 网络超时：重试；
- 配置保存冲突（并发编辑）：提示刷新后重试；
- 权限不足：非 R1 访问该 Tab → 403 页面提示"仅系统管理员可访问"。

### 9. BR 业务规则覆盖
- **BR-013 支撑**：L2/L3 分级保证行政与持有人在预警处理期间可在线核验证件，同时水印防泄露；
- 本页为 CERT-003 全量落点：三级访问（CERT-S-R1）、水印强制（CERT-S-R2 禁下载）、高频告警（CERT-S-R3）。

---

## 模块通用备注
- 本模块 2 个一级页面（P1 含分级审计 Tab 即 P3 并入）+ 1 个全屏水印查看层，共 12 个抽屉/弹窗（上传、审核、详情、水印层、统计、换证、扫描确认、提醒、级别编辑×2、导出确认等）。
- 前端强制约定：证件原图任何情况不落本地缓存、不提供下载控件、查看 URL 60s 过期重取（V1-D3）；证件号查询走 hash 索引不明文传输（CERT-A-R1）。
- OCR 仅对新上传触发（V1-D1），文件按 cert_id/版本存储不覆盖（V1-D2）。
- 枚举对齐说明：`CertArchiveStatus`（PENDING_REVIEW/EFFECTIVE/EXPIRING/EXPIRED/RECYCLED）与全局规范权威枚举 `CertStatus` 值域完全一致，前端实现统一 import `CertStatus`。
