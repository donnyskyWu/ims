# CERT - 证件档案 API 契约

> **模块范围**：06 证件档案（V1，第 8~10 周，补齐类）——CERT-001 档案存储与索引、CERT-002 到期预警、CERT-003 权限分级与水印。
> **权威依据**：《IMS第一期PRD-V1.md》5.13~5.15；《共享技术规范-数据库与API.md》7.2/8.3 及 V1-D1~D3 技术约束。
> **全局约定**：响应包裹 `{code, msg, data}`；分页 `{pageNo, pageSize}` / `{list, total, pageNo, pageSize}`；枚举/错误码引用《全局开发规范.md》；字段 camelCase。**敏感字段强制**：证件号 AES-256 加密存储、接口返回脱敏值；检索走 SHA-256 哈希索引，禁止明文。

---

## 1. API 总览表（共 15 个接口）

| # | 方法 | 路径 | 说明 | 权限（角色） |
|---|------|------|------|--------------|
| 1 | POST | `/admin-api/ims/cert/archive/upload` | 上传证件档案（OCR 增量识别，V1-D1） | R2（主责）/R1 |
| 2 | GET | `/admin-api/ims/cert/archive/list` | 档案索引列表（分页） | R1/R2（全量）/R4（索引无原图）/R7（本人）/R9（索引脱敏） |
| 3 | GET | `/admin-api/ims/cert/archive/{id}` | 档案详情（按权限分级返回） | 同上 |
| 4 | PUT | `/admin-api/ims/cert/archive/{id}/review` | 档案审核生效 | R2/R1 |
| 5 | GET | `/admin-api/ims/cert/archive/{id}/file-url` | 获取原图签名访问 URL（60 秒有效，经水印代理） | 按 L1/L2/L3 分级 |
| 6 | GET | `/admin-api/ims/cert/archive/digital-metrics` | 数字化率统计（BR-005） | R1/R2/R4 |
| 7 | GET | `/admin-api/ims/cert/expire/list` | 到期预警列表（分级，分页） | R1/R2/R4/R7（本人）/R9 |
| 8 | POST | `/admin-api/ims/cert/expire/scan` | 手动触发到期扫描 | R1/R2 |
| 9 | PUT | `/admin-api/ims/cert/expire/{id}/renew` | 换证登记（新证替换旧证） | R2（主责）/R1 |
| 10 | GET | `/admin-api/ims/cert/expire/stats` | 预警统计看板 | R1/R2/R4/R9 |
| 11 | GET | `/admin-api/ims/cert/security/view/{certId}` | 分级查看（返回在线预览或拒绝） | 全部（按分级） |
| 12 | PUT | `/admin-api/ims/cert/security/level-config` | 配置访问级别规则 | R1 |
| 13 | GET | `/admin-api/ims/cert/security/view-logs` | 查看审计日志（分页） | R1 |
| 14 | GET | `/admin-api/ims/cert/security/risk-report` | 异常访问报告 | R1 |
| 15 | PUT | `/admin-api/ims/cert/expire/{id}/remind` | 人工催办提醒（工作台/钉钉） | R2/R1 |

---

## 2. 接口明细

### 2.1 档案存储与索引（CERT-001）

#### 2.1.1 POST /admin-api/ims/cert/archive/upload — 上传证件档案

**请求**：

```typescript
interface CertArchiveUploadReq {
  holderUserId?: number;         // 持有人（内部人员，二选一）
  holderName?: string;           // 持有人姓名（外协人员无内部账号时）
  certType: 'IDCARD' | 'PASSPORT' | 'OTHER';
  /** 证件号明文（HTTPS 传输，后端 AES-256 加密落库 certNoEncrypted + SHA-256 哈希索引 certNoHash） */
  certNoPlain: string;
  /** fileKey（FileUpload 服务端上传回执 · 本期不上对象存储，落服务端加密目录，见《全局开发规范》§6.3） */
  fileKey: string;
  issueDate: string;             // yyyy-MM-dd
  expireDate: string;            // yyyy-MM-dd
}
```

**响应** `data`：

```typescript
interface CertArchiveVO {
  id: number;
  holderUserId?: number;
  holderName?: string;
  certType: 'IDCARD' | 'PASSPORT' | 'OTHER';
  /** 脱敏证件号：110***********5678（CERT-A-R1：明文不出接口） */
  certNoMasked: string;
  /** SHA-256 哈希前 16 位（等值检索索引回显，非明文） */
  certNoHashPrefix: string;
  issueDate: string;
  expireDate: string;
  status: CertStatus;            // PENDING_REVIEW / EFFECTIVE / EXPIRING / EXPIRED / RECYCLED
  uploadedBy: number;
  createdAt: string;
  /** OCR 识别结果（V1-D1：仅新上传/变更触发，人工确认后落库） */
  ocrResult?: {
    recognizeStatus: 'PENDING_CONFIRM' | 'CONFIRMED' | 'FAILED';
    recognizedFields: Record<string, string>;   // 姓名/证号/有效期等
  };
}
```

**错误码**：1032（一人一类型一份有效档案，重复上传走"换证"5.2.3，CERT-A-R3）、1001（参数校验）。文件按 `certId/版本号` 存储，重传生成新版本不覆盖（V1-D2）。

#### 2.1.2 GET /admin-api/ims/cert/archive/list — 档案索引列表（分页）

**请求**（Query）：`PageParam` + `{ holderUserId?: number; holderName?: string; certType?: string; status?: CertStatus; expireDateRange?: [string, string] }`

**响应** `data`：`PageResult<CertArchiveVO>`（列表仅含索引字段，原图访问一律走 2.1.5 / 2.3.1 分级端点）。

#### 2.1.3 GET /admin-api/ims/cert/archive/{id} — 档案详情

**响应** `data`：`CertArchiveVO` + `{ viewPermission: 1 | 2 | 3 }`（按当前用户分级，R4 仅索引无原图、R9 索引脱敏）。

#### 2.1.4 PUT /admin-api/ims/cert/archive/{id}/review — 档案审核

**请求**：`{ action: 'APPROVE' | 'REJECT'; remark?: string }` → **响应**：`data: null`。上传后需行政管理员审核生效（CERT-A-R4，状态 PENDING_REVIEW → EFFECTIVE）。

#### 2.1.5 GET /admin-api/ims/cert/archive/{id}/file-url — 签名访问 URL

**响应** `data`：

```typescript
interface CertFileUrlResp {
  /** 60 秒有效签名 URL（原图禁止直接下放，一律经水印代理端点，V1-D3） */
  signedUrl: string;
  /** 水印参数（L2 查看时） */
  watermark?: { text: string; opacity: number; position: string };
  expiresInSeconds: 60;
}
```

**错误码**：1034（访问级别不足）、1033（待审状态不可查看原图）。

#### 2.1.6 GET /admin-api/ims/cert/archive/digital-metrics — 数字化率统计

**响应** `data`：`{ totalExpected: number; digitalizedCount: number; digitalizedRate: number }`（BR-005 目标 > 95%）。

### 2.2 到期预警（CERT-002）

#### 2.2.1 GET /admin-api/ims/cert/expire/list — 预警列表（分页）

**请求**（Query）：`PageParam` + `{ level?: CertWarnLevel; status?: 'WARNING' | 'RENEW_RESOLVED' | 'EXPIRED_LOCKED' }`

**响应** `data`：`PageResult<CertExpireTaskVO>`

```typescript
interface CertExpireTaskVO {
  id: number;
  certId: number;
  certNoMasked: string;
  holderName: string;
  holderUserId?: number;
  certType: string;
  expireDate: string;
  level: CertWarnLevel;          // YELLOW(T−30) / RED(T−7) / LOCKED(T−0)
  /** 已通知人列表（CERT-E-R2：同级别不重复推送） */
  notifiedUserIds: number[];
  status: 'WARNING' | 'RENEW_RESOLVED' | 'EXPIRED_LOCKED';
  createdAt: string;
}
```

#### 2.2.2 POST /admin-api/ims/cert/expire/scan — 手动触发扫描

**响应**：`{ scanTaskId: string; message: string }`。每日 08:00 定时扫描（CERT-E-R1），当日命中即推送持有人 + 行政（工作台 + 钉钉）。

#### 2.2.3 PUT /admin-api/ims/cert/expire/{id}/renew — 换证登记

**请求**：

```typescript
interface CertRenewReq {
  /** 新证件档案 ID（先走 2.1.1 上传） */
  newCertId: number;
  remark?: string;
}
```

**响应**：`data: null`。新证审核生效后旧证归档（RECYCLED）、预警解除（RENEW_RESOLVED）。

#### 2.2.4 GET /admin-api/ims/cert/expire/stats — 预警统计看板

**响应** `data`：`{ byLevel: Record<CertWarnLevel, number>; trend: Array<{ date: string; yellow: number; red: number; locked: number }> }`

**联动约束**：锁定态证件在 LIVE-001 开播登记时由 LIVE 域拦截（1045 归 LIVE 段 1041~1050，CERT-E-R3 联动；CERT 本域不占用 1045）。

#### 2.2.5 PUT /admin-api/ims/cert/expire/{id}/remind — 人工催办提醒

**说明**：持有人未响应预警时，行政管理员（R2 主责/R1）手动触发催办提醒（不占用 CERT-E-R2 系统推送的同级别不重复限制，服务端记录催办事实）。

**请求**：

```typescript
interface CertRemindReq {
  /** 提醒渠道（不传默认双渠道） */
  remindChannel?: 'APP' | 'DINGTALK';
}
```

**响应** `data`：

```typescript
interface CertRemindResp {
  /** 本次催办时间 */
  remindedAt: string;
}
```

**错误码**：1039（催办对象或预警任务不存在）、1008（权限不足）。

### 2.3 权限分级与水印（CERT-003）

#### 2.3.1 GET /admin-api/ims/cert/security/view/{certId} — 分级查看

**响应** `data`：

```typescript
interface CertSecurityViewResp {
  viewLevel: 1 | 2 | 3;
  /** L1：仅索引信息，无原图 */
  indexInfo?: CertArchiveVO;
  /** L2：在线预览（叠水印，下载禁止）；L3：明文可见 */
  preview?: {
    signedUrl: string;           // 60 秒签名 URL（经水印代理端点）
    watermark: { text: string; opacity: number; position: string };
  };
  /** 水印内容：工号+姓名+时间戳（CERT-S-R2） */
  watermarkText?: string;
  rejected?: { code: number; reason: string };   // 如 1034 级别不足
}
```

分级规则（CERT-S-R1）：默认所有人 L1；L2 需**角色**配置（ADR-IMS-008）；L3 仅 R1 + 行政管理员白名单。

#### 2.3.2 PUT /admin-api/ims/cert/security/level-config — 配置访问级别规则

**请求**：

```typescript
interface CertLevelConfigReq {
  /** 角色 → 级别映射（ADR-IMS-008） */
  rules: Array<{
    target: 'ROLE' | 'POSITION_TEMPLATE';
    targetCode: string;          // 如 'R9' / 'POSITION_TPL_12'
    viewLevel: 1 | 2 | 3;
  }>;
  /** L3 白名单（仅 R1 可配置） */
  l3Whitelist: number[];         // userId 列表
}
```

**响应**：`data: null`。映射 `ims_cert_watermark_config`（permLevel / watermarkText / opacity / position）。

#### 2.3.3 GET /admin-api/ims/cert/security/view-logs — 查看审计日志（分页）

**请求**（Query）：`PageParam` + `{ certId?: number; viewerUserId?: number; viewLevel?: 1 | 2 | 3; timeRange?: [string, string] }`

**响应** `data`：`PageResult<CertViewLogVO>`

```typescript
interface CertViewLogVO {
  id: number;
  certId: number;
  certNoMasked: string;
  viewerUserId: number;
  viewerName: string;
  viewLevel: 1 | 2 | 3;
  watermarkText: string;         // 工号+姓名+时间戳
  viewDuration: number;          // 秒
  ip: string;
  device: string;
  createdAt: string;
}
```

#### 2.3.4 GET /admin-api/ims/cert/security/risk-report — 异常访问报告

**响应** `data`：`{ highFrequencyUsers: Array<{ userId: number; name: string; viewsInLastHour: number }>; abnormalTotal: number }`（1 小时 > 10 次告警，CERT-S-R3，前端返回 1035 拦截）。

---

## 3. 状态机与业务约束

### 3.1 状态机

**证件档案（CertStatus，映射 PRD 5.13.2 TINYINT 0~4）**：

```
PENDING_REVIEW ──审核通过──▶ EFFECTIVE ──T−30/T−7──▶ EXPIRING ──T−0──▶ EXPIRED（锁定，LIVE 拦截）
      │                        │                                    │
    审核拒绝                 换证（新证生效）◀──新证上传+审核          换证（新证替换）
      ▼                        ▼                                    ▼
   （删除归档）            RECYCLED（旧证归档，换证流程）
```

**到期预警任务（CertExpireTaskVO.status）**：`WARNING（YELLOW→RED 级别升级才再推）→ RENEW_RESOLVED（换证解除）/ EXPIRED_LOCKED（到期锁定）`

### 3.2 业务规则引用（PRD）

| 规则 | 约束 | API 落点 |
|------|------|----------|
| BR-005 | 证件数字化率 > 95% | 2.1.6 digital-metrics |
| BR-013 | T−30 黄 / T−7 红 / T−0 锁定 | 2.2.x（CertWarnLevel 枚举） |
| CERT-A-R1 | AES-256 加密 + hash 检索 | 2.1.1（certNoPlain 仅入参，出参脱敏） |
| CERT-A-R2 | 私有桶 + 60 秒签名 URL | 2.1.5 / 2.3.1 |
| CERT-A-R3 | 一人一类型一份有效 | 2.1.1 错误码 1032 |
| CERT-A-R4 | 上传后审核生效 | 2.1.4 |
| CERT-E-R1~R3 | 08:00 扫描/同级别不重推/锁定拦截直播 | 2.2.x |
| CERT-S-R1~R3 | 三级访问/L2 水印禁下载/高频告警 | 2.3.x（错误码 1034/1035） |
| V1-D1~D3 | OCR 增量/服务端文件目录版本存储/水印代理 | 2.1.1 ocrResult、2.1.5 代理端点 |

---

## 4. 与页面规格的对应关系（API ↔ 页面操作映射）

| 页面/区域 | 页面操作 | 调用 API |
|-----------|----------|----------|
| 证件档案管理页（QueryBar+表格） | 索引列表查询（持有人/类型/有效期筛选） | GET /cert/archive/list |
| 档案上传抽屉（DetailDrawer + FileUpload 服务端上传） | 上传证件（POST 落服务端加密目录得 fileKey，再提交元信息） | POST /cert/archive/upload |
| 档案详情抽屉 | 查看详情（按分级渲染：索引/水印预览/明文） | GET /cert/archive/{id} |
| 档案详情抽屉-原图按钮 | 获取 60 秒签名 URL（L2 叠水印在线预览） | GET /cert/archive/{id}/file-url |
| 待审列表 Tab-审核操作 | 通过/拒绝审核 | PUT /cert/archive/{id}/review |
| 数字化率指标卡 | 数字化率看板（BR-005） | GET /cert/archive/digital-metrics |
| 到期预警页（分级 Tab：黄/红/锁定） | 预警列表查询 | GET /cert/expire/list |
| 到期预警页-操作 | 手动触发扫描（ConfirmDialog） | POST /cert/expire/scan |
| 到期预警详情抽屉-换证 | 换证登记（新证上传后关联替换） | PUT /cert/expire/{id}/renew |
| 到期预警行操作-提醒 | 人工催办（渠道弹窗 APP/钉钉） | PUT /cert/expire/{id}/remind |
| 到期预警统计看板 | 分级分布与趋势图 | GET /cert/expire/stats |
| 分级查看（列表行/详情触发） | 分级判定查看（L1 拒绝提示/L2 水印预览计时/L3 明文） | GET /cert/security/view/{certId} |
| 安全配置页（R1） | 访问级别规则与 L3 白名单配置 | PUT /cert/security/level-config |
| 查看审计日志页（QueryBar+表格） | 审计日志查询（谁/何时/看了几秒） | GET /cert/security/view-logs |
| 风险报告页 | 异常高频访问报告 | GET /cert/security/risk-report |

（全文完）
