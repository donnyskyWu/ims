# 平台账号 · 采集 Tab（OPS M4 并入 · ADR-047）

> 挂载于 **主数据/平台账号详情**（`MASTER` P4 平台账号详情 或 IMS 账号台账详情，以 OPS `oa_internal_account` 为准）。  
> **不是**「数据采集 · 内部配置」页面。  
> SSOT：`docs/product/UX-M4-账号管理.md` §7.2 采集 Tab、`docs/adr/ADR-047-*`、`docs/engineering/API-M10-数据采集.md` §3（bind/扫码/探活）

## 1. 入口

- 平台账号列表列：**采集绑定**（已绑定 / 未绑定 / 连接失败）。
- 详情抽屉 Tab 顺序建议：`基本信息` | **`采集`** | `粉丝列表`（公众号）| `领用时间线`（IMS ACCT 增量）| `关联资产`

## 2. 采集 Tab 布局

```
[Alert] 凭证保存后须「导入 Collector」完成 bind，否则任务报错：未绑定 Collector
┌─ 绑定状态 ─────────────────────────────────────┐
│ Collector account_id: acc_douyin_xxx  [复制]      │
│ 最近探活: 2026-09-29 08:00  成功                  │
└──────────────────────────────────────────────────┘
┌─ 凭证（AES，列表/详情脱敏）──────────────────────┐
│ Cookie / authorization_token  [更新] [清空]       │
│ 快手: auth_token + field_mapping JSON（若有）     │
└──────────────────────────────────────────────────┘
[扫码登录] [测试连接] [导入 Collector / 重新 bind]
```

## 3. 交互

| 操作 | 行为 |
|------|------|
| 更新 Cookie | 加密写入 `oa_account`；**不**自动 bind，提示执行「导入 Collector」 |
| 扫码登录 | 代理 QR（ADR-050）；成功后刷新凭证与 bind 状态 |
| 测试连接 | 调 Collector 探活；失败展示错误码与建议 |
| 导入 Collector | `POST /api/v1/accounts/import` → 写 `oa_collector_account_bind` |
| 批量（列表页） | 未绑定账号批量 bind（UX-M4 列表操作，P1） |

## 4. 与采集任务联动

- 任务编辑选 `<AccountSelect />` 时，未 bind 账号 **警告**（可保存任务，执行必失败）。
- 日志详情「未绑定 / Cookie 失效」→ 深链本 Tab（带 `accountId`）。

## 4.1 与 COLLECT 分工（ADR-047）

| 能力 | 页面 |
|------|------|
| Cookie / bind / 探活 | **本 Tab**（平台账号详情） |
| cron / 跑任务 / 日志 | COLLECT P5 / P5b |
| 外部竞品主体配置 | COLLECT **P2a 竞品账号配置**（**无** Cookie 字段） |

规格交叉：《COLLECT-数据采集-页面规格.md》§P2a、§「与账号模块分工」。

## 5. 权限与敏感

Cookie/Token 不明文；R9 等角色按 OPS 数据权限。AES-256（BR-306）。
