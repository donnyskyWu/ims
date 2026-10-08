# QA 回归报告 · 第二批 V2 六项补齐（MEET-002 / REPORT-001/002/003 / FLOW-001/003 / PERF-004 / ALERT-003）

- 测试日期：2026-09-18
- 测试对象：`IMS-一体化管理系统-UI原型.html`（本轮修改后）
- 测试脚本：`_qa/v2_test.js`（33 断言）+ `_qa/v1p0_test.js` 回归（19 断言）
- 结果：**33 / 33 全部通过**，v1p0 回归 **19 / 19 通过**（无破坏）

## 断言明细（33 项）

| 组 | 断言 | 结果 |
|----|------|------|
| D1~D6 | MEET-002 日报逐级审阅：审阅函数 / 待审数据 / 通过流转 / toast / 批量通过 / 批量提示 | ✓×6 |
| E1~E8 | REPORT 三项：模板数据 / 上报函数 / 待审核单 / 提交入列 / toast / 审核通过 / 退回流转 / 24h 重报提示 | ✓×8 |
| F1~F8 | FLOW 两项：模板数据 / 设计器函数 / 版本递增 v3→v4 / 新版本 toast / 回滚 v2 / 回滚 toast / 新建模板 / 节点解析 | ✓×8 |
| G1~G6 | PERF-004：PIP 函数 / D 级数据 / PIP 发起 / 排序正确 / 最高分何舟 96 / 最低分王野 51 | ✓×6 |
| H1~H5 | ALERT-003：升级版处理函数 / 升级链抽屉 / 处理中流转 / 升级链停止 toast / 规则表单 | ✓×5 |

## 本轮新增功能说明

### MEET-002 日报逐级审阅
- REPORTS 数据新增 rvw 审阅状态字段（待审阅/已审阅/已退回）
- report 页新增「待我审阅」Tab（红色角标显示待审数）+ 审阅状态列
- reportApprove（逐级汇总）/ reportReject（退回原因表单 + 修改提醒）/ reportRvwBatch（批量通过）
- reportDetail 详情抽屉：三级审阅流时间线（提交 → 直属主管 → 部门汇总）
- 统计 Tab 新增审阅完成率卡片

### REPORT-001/002/003 数据上报体系
- report 页新增「数据上报」Tab（三胶囊：上报模板 / 上报记录 / 完成率）
- **REPORT-001**：RTPLS 5 套模板（字段数/频率/责任部门/启停）+ reportTplEdit 编辑抽屉（字段列表+校验规则示意）+ reportTplAdd 新建
- **REPORT-002**：reportSubmitData 提交表单（模板选择/日期/附件/行数）→ UPLOADS 待审核入列
- **REPORT-003**：reportUplAudit 双向审核（通过入仓数据中心 / 退回填原因 24h 内重报）+ reportUplDetail 字段抽检抽屉
- 完成率 Tab：BR-106 完成率 + 通过率 + 字段校验命中率 + 审核时长统计

### FLOW-001/003 模板设计器与版本管理
- flow 页新增「模板管理」Tab（FTPLS 6 套模板 + 节点链可视化 + 升级链 + 版本号）
- **FLOW-001**：flowTplDesign 设计器抽屉（节点编排 + 超时配置 + 新增节点/调序 + 节点配置入口）
- **FLOW-003**：flowTplVer 版本历史抽屉（时间线 + 回滚 + 差异对比）+ flowTplRollback（回滚新流程生效、进行中按旧版）
- flowTplSave 保存自动版本递增（v3→v4）+ flowTplNew 新建（节点链顿号解析）

### PERF-004 排名与预警
- 考核结果 Tab：按综合得分动态排名列（TOP3 🏆 绿色 + 末位红色）
- 新增红榜 TOP3 / 末位预警（连续 2 期 D 级）/ 部门均分三卡片
- perfPIP 末位改进预警（BR-117 规则 + PIP 30 天周期 + 通知主管与 HR）

### ALERT-003 三级升级机制
- alertRuleAdd 规则表单新增「三级升级链」配置区块（L1 2h 主管 / L2 8h 部门 / L3 24h 总监+短信；红色减半）
- 规则表格新增「升级链」列（红色 1h/4h/12h · 其他 2h/8h/24h）
- alertHandle 升级为处理抽屉（升级链时间线 + 当前升级层级 L1/L2/L3）→ alertHandleGo 确认处理（升级链停止）

## 测试方法论补充

6. `reportUplAudit(i, 0)` 等退回流程走 `CF_CB` + `doConfirm()` 真实确认弹窗机制——测试需在调用后手动 `doConfirm()` 触发回调（桩中 CF_CB/doConfirm 需重覆盖）

## 复跑方式

```bash
node _qa/v2_test.js      # 第二批 V2 六项（33 断言）
node _qa/v1p0_test.js    # 第一批 V1 P0 回归（19 断言）
```
