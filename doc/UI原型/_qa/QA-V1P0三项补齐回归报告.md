# QA 回归报告 · V1 P0 三项补齐（LIVE-002 / ACCT-004 / ASSET-002）

- 测试日期：2026-09-18
- 测试对象：`IMS-一体化管理系统-UI原型.html`（本轮修改后）
- 测试脚本：`_qa/v1p0_test.js`（node 直接运行）
- 结果：**19 / 19 全部通过**

## 断言明细

| 组 | 断言 | 结果 |
|----|------|------|
| A1 | 台账含未录入场次（达人连麦） | ✓ |
| A2 | 已录入场次带数据（大促预热 GMV 412800） | ✓ |
| A3 | liveEndEntry / liveEndEntrySubmit 函数存在 | ✓ |
| A4 | liveEntryCalc（客单价/GPM/峰值比实时测算）存在 | ✓ |
| A5 | 下播录入提交后 entered=true | ✓ |
| A6 | 提交后 gmv 写入 88800 | ✓ |
| A7 | 提交后 views 写入 20000 | ✓ |
| A8 | toast 下播数据已录入（含 BR-006 留痕提示） | ✓ |
| B1 | acctCharge / acctChargeSubmit 函数存在 | ✓ |
| B2 | acctChargeCalc（BR-017 账实核对）存在 | ✓ |
| B3 | 金额一致时入账 recharge +5000 | ✓ |
| B4 | charges 时间线留痕（凭证号写入） | ✓ |
| B5 | toast 冲话费已入账 | ✓ |
| B6 | 金额不一致时拦截（recharge 不变） | ✓ |
| B7 | 差异时 BR-017 错误 toast 拦截 | ✓ |
| C1 | assetToAcct / acctToAsset 双向穿透函数存在 | ✓ |
| C2 | 资产→账号穿透触发抽屉 | ✓ |
| C3 | 账号→资产穿透触发抽屉 | ✓ |
| C4 | 不存在账号时错误提示 | ✓ |

## 本轮新增功能说明

### LIVE-002 下播数据录入
- 台账中「已结束」且未录入的场次显示橙色「下播录入」按钮
- 表单含 GMV / 订单数 / 观看人数 / 峰值在线 / 实际时长 / 新增粉丝 / 打赏收益 / 数据来源 pills / 凭证备注
- 实时测算区：场均客单价、GPM（千次观看成交）、峰值/累计比
- 提交后写入 LIVES 数据（entered=true），场次详情抽屉新增「下播数据（BR-006 留痕）」区块
- 台账页新增四张统计卡：下播录入完整率（BR-007 三色阈值）/ 本月场次 GMV / 待录入场次 / 最高单场 GMV

### ACCT-004 冲话费管理
- 账号台账每行新增橙色「冲话费」按钮（已注销账号除外）
- 表单含金额 / 充值渠道 pills / 平台实际到账 / 凭证编号 / 凭证截图 / 备注
- **BR-017 账实核对实时校验**：申请金额 ≠ 平台到账 → 红字差异提示 + 提交拦截（error toast）
- 一致时入账：recharge 累计 + charges[] 时间线留痕（凭证号 / 日期 / 渠道）
- 账号详情抽屉：footer 增加「冲话费」按钮，时间线融合动态充值记录
- 统计卡升级：「本月充值/冲话费」+ 账实核对一致率 98.4%

### ASSET-002 反向穿透查询
- 资产详情「绑定账号」区块：账号行可点击 → 穿透跳转账号详情（正向：资产→账号）
- 账号详情「关联资产」区块：资产行可点击 → 穿透跳转资产详情（反向：账号→资产）
- 新增 assetToAcct / acctToAsset 两个穿透函数，含不存在 ID 的错误提示
- 穿透路径提示与 DC 数据中心六节点穿透链路呼应

## 测试方法论记录（复用经验）

1. 桩区 `document` 需补 `createElement` / `body.appendChild`（源码真实 toast/confirmDlg 会用）
2. `_mk` 元素需补 `appendChild` / `remove` / `setAttribute` / `insertBefore` / `parentNode`
3. **源码中真实版 toast/confirmDlg/openDrawer 的 function 声明会提升并覆盖桩**——必须在断言区开头重新赋值覆盖为桩（赋值不受提升影响）
4. 源码真实 formValidate 会校验表单字段——测试需为每个 req 字段预置值（本轮漏 F_lreal 导致 A5~A8 误报）
5. setTimeout 桩为同步执行（既有经验）

## 复跑方式

```bash
node _qa/v1p0_test.js
```
