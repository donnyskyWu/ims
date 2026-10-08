# CHECKLIST-IMS-CORP — 公司资产

> **关联**：[SLICES-IMS-CORP](./SLICES-IMS-CORP.md)

---

## 1. 导航

- [ ] L1 公司资产 → L2 三组 → L3 路由与 PRD #8 一致
- [ ] 默认进入抖音平台叶

## 2. 平台账号（P-A1～A5）

- [ ] 每 L3 `platformType` 固定筛选
- [ ] 列表含采集绑定摘要列
- [ ] 详情 Tab：基本信息 | **采集** | 领用时间线 | 关联资产
- [ ] 采集 Tab 对齐《ACCT-平台账号采集Tab-OPS对齐》（Cookie/bind **不在** COLLECT P2a）
- [ ] 强关联字段用选择器；1500/1501/1502 后端校验
- [ ] `GET /corp/account/page` BFF 透传 OPS + platformType

## 3. 资源管理（P-R1～R4）

- [x] 四 L3 可列表/抽屉（字段以 UX-M4 为准）
- [x] 实名人/公司选择器不回写错误 FK

## 4. 设备（BLOCKED 部分）

- [x] 三 L3 路由存在
- [x] API BLOCKED 时：空态 + 规格 hint（**禁止** toast-only 冒充 CRUD）

## 5. 全局

- [ ] tenant_id 1504
- [ ] TESTCASES-IMS-CORP P0 100%
