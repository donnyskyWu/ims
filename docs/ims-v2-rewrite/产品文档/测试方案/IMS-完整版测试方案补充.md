# IMS 完整版测试方案补充（v2.0）

> 叠加《IMS-整体测试方案.md》。依据：《IMS完整产品需求文档》v2.0、产品规格 V1 并入模块、铁律 IR-01～06。

## 1. 范围增量

在原 20 模块测试上增加 **OPS 并入域**：HOME、SYS、MASTER、IPG、COST、COLLECT、MON、BI0、CONTENT-100～110、Football WebAPI Client。

原「398 端点」基数 **增加并入 API**（以各新契约行数为准，预估 +80～120）。P0 增加：

- 无 Feign/`@DS`（架构扫描用例 ST-IR-001）
- 无运行时调用 OPS（ST-IR-002）
- 主数据选择器不可手输（ST-MASTER-001）
- 用户/账号主键迁入后不变（ST-MIG-010）
- 内容保存成功 + Football 超时仍 200 + outbox（ST-FB-001）
- 订单 ROI 不直连 pay 库（ST-COST-001）
- 采集明细在 IMS 库可查 3 日（ST-COLLECT-001）

## 2. 集成测试增量

| 编号 | 场景 |
|------|------|
| IT-FB-WEBAPI | Mock Football HTTP：方案 upsert/status/delete、订单汇总、赛程 |
| IT-MIG | 同构灌数 → 行数/主键集合/孤儿池 |
| IT-JINGCAI | 参数 true/false 确认登记是否入队 AI |
| IT-DELETE | 删草稿 → WebAPI delete 或 off_shelf |

外部依赖桩：Football 用 WireMock，**禁止**测环境直连生产 member。

## 3. E2E 主线增量（在原 12 条上 +4）

| 编号 | 路径 |
|------|------|
| ET-13 | 登录 SSO → 建 IP 组 → 录账号 → 录成本 → 看 ROI（营收 Mock） |
| ET-14 | 工作任务确认 → 任务列表 → 内容编辑 → 提审 |
| ET-15 | 采集配置 → 手动任务 → 监测爆款列表 |
| ET-16 | 自定义查询保存并执行 ≥1 次 |

## 4. 准出（V1 并入批次）

- 原 V1 冒烟仍绿
- ST-IR-001/002 通过
- ET-13～16 通过
- 迁数报告附于 Gate
