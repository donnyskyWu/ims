# QA 回归验证报告 — IMS UI 原型「交互完整性增强」迭代

- **QA**：严过关（Yan，独立回归验证，不信实现者自检）
- **被测对象**：`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`（2205 行 / 175.4 KB，纯 HTML/CSS/JS 单文件）
- **验证方式**：Node 22 + vm.runInNewContext 沙箱 + 自建最小 DOM 桩（`_qa/dyn_regression.js` v5，HTML id 解析注册 / qbar 控件模拟 / 定时器收集）；隔离纯函数验证（`_qa/qfilter_pure_test.js`、`_qa/qfilter_root_cause.js`）；静态扫描（`_qa/scan_toast.py`、`_qa/scan_placeholder.py`）；语法检查（`_qa/scripts/s1~s4.js` node --check）
- **约束遵守**：未修改被测文件；测试脚本与报告均落盘 `_qa/` 目录

---

## 总结论

**IS_PASS: NO — 不可直接交付（需修复 1 个 P0 + 1 个 P0/P1 后复测）**

动态回归 142 PASS / 4 FAIL（4 个 FAIL 均已定位为源码缺陷并复现根因）；除「查询过滤」链路外的所有新交互（表单系统、确认弹窗、导出流程、行操作状态机）与既有 18 页面功能全部通过。

---

## 逐项验收结果

### 1. 语法与结构 — PASS
- 4 个 script 块（22855 / 52026 / 40317 / 20674 字节）node --check 全部零错误（S1_OK~S4_OK）
- 静态 tag 平衡：div 460/460、button 95/95、select 7/7、table 4/4；span 146/147、option 17/18 差异均在 JS 字符串模板拼接场景，非结构缺陷
- 新公共组件函数全部存在：confirmDlg(L600)/doConfirm(L616)/frow(L620)/formValidate(L639)/formOk(L656)/exportX(L551)/dlbar(L535)/qGrab(L567)/qFilter(L575)/hlFirst(L668)；40+ 新表单/行操作函数全部已定义

### 2. 新交互冒烟 — 表单/确认/导出 PASS；过滤 FAIL（详见缺陷 D1/D2）

| 链路 | 结果 | 证据（dyn_regression.js v5） |
|---|---|---|
| assetReg 校验/拦截 | PASS | A1~A7：空提交拦截 toast「请先完成必填项」、E_name 错误文案、红框 err、数据不写入 |
| assetReg 提交/unshift/高亮 | PASS | A8~A12：formOk 成功态 AS20260912011、ASSETS unshift 11 条、表格含新行 |
| finCalc 实时计算 | PASS | B1~B7：¥60,000/¥18,000/¥42,000、负毛利 neg 样式、提交待结算 |
| certNoPreview 脱敏预览 | PASS | C1~C5：前3+星+后4、不含明文、CERTS unshift 审核中 |
| reportWrite 完成度 | PASS | E1~E4：1字段33% → 3字段100% |
| 15 个表单抽屉冒烟 | PASS | F1×9 + F2/F4（解冻/流转表单） |
| alertHandle/Recover 状态机 | PASS | H1~H5：未处理→处理中→已恢复，danger 确认窗 btn-red |
| acctReturn 归还 | PASS | I1~I3：→已归还、责任人清空、释放至池 toast |
| trainEnroll 满员禁用 | PASS | J1~J5：signed+1、满员 disabled 拦截 |
| exportX→dlbar 导出 | PASS | K1~K7：转圈态、900ms 恢复、文件名+条数、3s fadeout、400ms 移除 |
| qFilter 文本过滤 | PASS | L1~L4/L6：「罗技」命中 2 行+toast 计数、不存在关键词→空态、resetQ 恢复全量 |
| **qFilter 下拉状态过滤** | **FAIL** | **L5/L7/L8/L9：状态/平台/类型/级别下拉选值 → 0 行（缺陷 D2）** |
| 行操作 12 链路 | PASS | M1~M17 + N1：liveToReview/urge/flowUrgeBatch/compCompare/dcDrill/dcSync/biSubscribe/liveSessionDetail 全通过 |

### 3. 既有功能回归 — PASS（全项）
- 18 页面 R1 渲染完整无 undefined/NaN（P1 × 18，len>500 + 模块标记命中）
- R1 侧边栏 18 项；10 角色侧边栏数量与上版一致（R1:18/R2:7/.../R10:1）
- R9 脱敏：cert/acct/dc 三模块 `class="masked"` 且无明文人名；R1 切回明文恢复
- 既有抽屉/详情：assetDetail 720px、certDetail L1/L2/L3 水印分级（R9 L3 拒绝）、liveReg、liveRiskResult 82 分、sopEdit 90%
- ESC 优先级：先关确认窗、再关抽屉（P19/P20）
- 工作台快捷入口 3 处联动表单：assetReg/acctApply/finReimburse 均可开表单（P21~P23）
- 事件绑定函数全定义：onXXX 属性扫描出的全部函数名 typeof=function 零缺失（Q1）

### 4. 死按钮（toast 占位）扫描与分类 — 27 处

**FAIL（关键操作漏改，P0 关联）**
- L523（qbar 查询按钮，全局 14 处实例共用）：查询按钮仍是 `toast('查询完成 · 原型示意')` —— 见缺陷 D1
- L1179 live 场次台账「导出」、L2144 eff「导出月报」：本轮已建立 exportX 组件但这两处导出按钮未接入 → P2 漏改
- L1207 liveRow 场次 ID 点击 toast 占位，但 liveSessionDetail/liveSessionOp 已实现且操作列已接 → P2 漏改（不一致）

**OK（查看/详情/帮助类，原型阶段合理保留 24 处）**
- L423 全局搜索、L425 帮助中心、L544 dlbar 查看、L627 附件上传、L672 继续新增提示、L758 todoGo 无权限兜底、L806 权限明细、L824 模板编辑、L1021×2 Tab、L1292 导入SOP、L1328 新增节点、L1368 培训详情、L1437 会议详情、L1505 日报详情、L1684 核算单详情、L1756 方案编辑、L1774 考核明细、L1836 规则编辑、L1854 处理记录、L1984 数据字典、L2164 人效详情

### 5. 设计规范抽查 — PASS
- 新增 CSS 块（L214-262：cfwrap/cfcard/btn-red/spin/dlbar/ferr/unit/fup/pills/okwrap/rowflash）复用 9 个既有 token：`var(--bg/--blue/--blue-bg/--line/--line2/--red/--spring/--text/--text2)`
- 硬编码色仅 4 处且合规：#fff（卡片底）、#d70015（cf-warn 文案色，与 TAGMAP.red 文字色一致）、#ff453a（btn-red hover，Apple 红系的深色变体，同页 var(--red)=#ff3b30 家族）
- 危险操作红按钮：`.btn-red{background:var(--red)}`（L226），danger 确认窗图标 rgba(255,59,48,.12)+var(--red) —— 均走 #ff3b30 体系 ✅
- 圆角体系一致：cfcard 12px（=--r）、cf-warn/dl-x 8px/4px（--r-s/--r-xs 邻域）、pill 980px 胶囊（iOS 语义）
- @keyframes cfIn/spin/rowfl/tin 全部有定义，无悬空动画引用

### 6. 零运行时异常 — PASS
- 沙箱合并执行 4 块脚本 + 142 断言驱动：无 RUNTIME_ERROR、无 TIMER_ERR
- 注：本轮 2 个此前疑似 FAIL（F3 解冻 danger 确认窗 / L11 resetQ 行数）经隔离复测（`_qa/debug_f3.js`）确认是**测试桩缺陷**（DOM 桩 id 复用导致 F_reason 串元素 + 期望值写死 11），修复桩后转 PASS —— 非源码问题

---

## 缺陷清单（源码）

### D1【P0】查询按钮未接入过滤链路，「查询过滤」在真实浏览器完全不可达
- **位置**：`qbar(controls, onQuery)` L520-524
- **现象**：第 2 参数 `onQuery`（9 处调用传了 `'qSave(\'asset\')'` 等字符串）在函数体内被完全丢弃；查询按钮 onclick 硬编码 `toast('查询完成 · 原型示意','success')`（L523）。全文件 0 处 onclick 含 qSave。
- **后果**：用户在下拉/输入框选好后点「查询」只弹 toast，表格不刷新、过滤不发生。qSave/qFilter/qGrab 三个函数全部存在且逻辑自洽，但入口断链 —— 需求「查询过滤覆盖 9 模块」实际为 0 模块可达（仅测试直调 qSave 可走通文本过滤路径）。
- **修复建议**：L523 改为 `onclick="' + (onQuery || 'qresetHint()') + '"`。
- **连带 P2**：`qi(ph,w)` L532 / `qs(opts,w)` L533 签名只有 2 参，但 31 处调用传了第 3 参（qr.k0~k4 回显值）被静默丢弃 —— 即使修好入口，条件回显也不生效（qSave 存入 state.q 后 renderPage 重建 qbar 不带 value）。

### D2【P0/P1】qFilter 对复合状态串的下拉过滤恒返回 0 行（5 模块）
- **位置**：`qFilter` L575-595，状态枚举精确排除分支 L585-588
- **根因**（`_qa/qfilter_root_cause.js` 单行跟踪复现）：
  1. acct/cert/live/train/alert 五个模块的 status 函数返回复合串（如 `'抖音|冻结'`）；
  2. 用户选「冻结」时 `v('冻结') !== s('抖音|冻结')` 恒成立 → 进入 else 分支；
  3. L587 枚举正则命中「冻结」→ `ok=false` → 该行被排除 → **所有行被排除 → 0 行**。
- **影响范围**：acct(L979 平台+状态两个下拉)、cert(L1089 类型+档案状态)、live(L1196 平台+状态)、train(L1358 状态)、alert(L1847 级别+状态) —— 这 5 个模块的**全部下拉过滤均失效且返回 0 行**（比不过滤更糟，是错误行为）。
- **正常对照**：fin(L1671 单维 status=f.st) 与文本关键词过滤（norm 数组）逻辑正确 —— 证明 `v===s` 精确匹配路径本身没问题，问题只在复合串形态。
- **测试证据**：dyn_regression L5(冻结→0/期望2)、L7(护照→0/期望1)、L8(报名中→0/期望2)、L9(红→0/期望3)；qfilter_pure_test T1/T2/T5/T6/T7 同样 0 行复现，T3/T4/T8（文本/单维/初始态）通过。
- **修复建议**：复合串匹配改为 `if (s && (v === s || s.split('|').indexOf(v) >= 0)) return;`，或让各模块 status 返回数组。

### D3【P2】次要问题
- resetQ(L526-530) 只清空控件值 + toast，不触发重渲染/重过滤（与 D1 同根源：没有刷新入口）。
- auth(L800)/report(L1498)/flow(L1571)/perf(L1764)/dc(L2021)/eff(L2154) 六处 qbar 无 onQuery 且页面数据表未接 qFilter —— 属于范围外，但「覆盖 9 模块」的宣称按 qFilter 调用点实为 8 个模块（asset/acct/cert/live/train/meet/fin/alert）。

---

## 复测指引（Round 2，送软件工程师 Alex 修复后）
1. 修复 D1（L523 接 onQuery）+ qi/qs 第 3 参回显
2. 修复 D2（复合串匹配）
3. 复跑：`node _qa/dyn_regression.js`（期望 146/146）+ `node _qa/qfilter_pure_test.js`（期望 8/8）
4. 顺带 P2：L1179/L2144 导出按钮接 exportX、L1207 场次 ID 接 liveSessionDetail

## 交付判定
**IS_PASS: NO**。阻断项为 D1+D2（查询过滤链路双断点：入口不可达 + 达到后 5 模块返回 0 行）。其余全部通过：表单系统、确认弹窗、导出流程、行操作状态机、18 页面回归、脱敏、设计规范、零运行时异常。修复量小（两处各 1-2 行），修复后可快速复测转 PASS。
