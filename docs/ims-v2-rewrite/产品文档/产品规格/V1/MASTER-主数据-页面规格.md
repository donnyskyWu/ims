# MASTER - 主数据 页面规格（OPS M4 并入）

> 完整 PRD MASTER-001～006。证件影像扩展见 CERT 原规格。账号领用见 ACCT 原规格。  
> 前缀：`/admin-api/ims/master`

## 页面

| 页面 | 路由 | 功能点 |
|------|------|--------|
| P1 公司 | `/ims/master/company` | MASTER-002 |
| P2 实名人 | `/ims/master/person` | MASTER-001 |
| P3 手机 | `/ims/master/phone` | MASTER-003 |
| P4 手机卡 | `/ims/master/sim` | MASTER-004 |
| P5 平台账号台账 | `/ims/master/platform-account` | MASTER-005（与 ACCT 台账可 Tab 合一，禁止两套登记） |
| P6 个人账号 | `/ims/master/personal-account` | MASTER-006 |

## 规则（铁律）

- 平台账号创建：**选择器**绑定公司、实名人、手机/卡、IP 组，禁止手输 ID（1500/1501/1502）。
- 证件号/手机号/ICCID/Cookie 脱敏展示，AES 存储。
- 表结构同构 OPS，主键不变；领用状态为扩展列或从表，不改账号 PK。
- 公众号容量在公司页展示。

## P5 列表列

账号名、平台、IP 组、实名人（脱敏）、状态、采集绑定、操作[编辑][领用][反向穿透]。
