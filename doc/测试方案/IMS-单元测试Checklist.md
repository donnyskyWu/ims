# IMS 单元测试 Checklist

> 版本 V1.0 ｜ 编制日期 2026-09-19 ｜ 依据：三期 PRD v1.2.0 + AIR PRD V1.2 + 19 份 API 契约 + 全局开发规范（47 枚举、错误码 18 段）
> 覆盖率要求：新增代码行覆盖 ≥ 80%；P0 Service 分支覆盖 ≥ 90%。
> 编号体系：UT-{域}-{功能点}-{三位序号}；☐ 为待勾选执行项。
> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。AIR 检索相关单测条目已作废或改写。

## 0. 通用测试点族（全部功能点适用，逐点勾选）

| 族 | 检查项 |
|----|--------|
| G1 数据结构 | 请求/响应 DTO 字段完整性（camelCase）、必填校验触发 1001、null/空串/超长输入边界 |
| G2 枚举 | 入参枚举非法值拒绝；出参值域严格落在 47 权威枚举内（契约校验脚本自动比对） |
| G3 错误码 | 成功返回 0；各错误路径返回错误码与全局规范 3.2 明细一致（段位不漂移） |
| G4 状态机 | 非法流转拒绝（返回对应状态非法码）；合法流转落库正确 |
| G5 审计 | 六审计字段（创建/更新人/时间等）自动填充 |
| G6 幂等 | 重复提交同请求不产生重复数据（幂等键/唯一约束） |
| G7 事务 | 方法内多表写失败时整体回滚 |

---

## 1. V1 单元测试（第 1~14 周，BR-001~018）

### 1.1 AUTH 权限（BR-001/002，AUTH-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-AUTH-001-01 | 钉钉 SSO 回调：authCode 换 userid 成功→查 ims_auth_user_mapping→首次登录触发即时同步 | AUTH-001 |
| UT-AUTH-001-02 | state 防 CSRF：无效/过期（>5 分钟）state 拒绝 | 共享规范 |
| UT-AUTH-001-03 | Token 有效期 2h、刷新 7 天边界；过期返回 1002 | 4.2 基线 |
| UT-AUTH-001-04 | 并发会话 > 3 返回 1003 | AUTH-R3 |
| UT-AUTH-002-01 | 入职事件：创建用户+岗位权限模板自动开权限 | BR-002 |
| UT-AUTH-002-02 | 调岗事件：旧岗位权限回收+新岗位授权（增量 diff 计算） | BR-002 |
| UT-AUTH-002-03 | 离职事件：权限失效（联动闭环由 E2E 验证端到端） | BR-015 |
| UT-AUTH-002-04 | 事件重复投递幂等（同 userid+事件号不重复处理） | G6 |
| UT-AUTH-002-05 | 钉钉接口超时/限流返回 5003；降级为组织数据只读 | 5003 |
| UT-AUTH-003-01 | 岗位模板：角色集合绑定/解绑；模板变更不追溯已授权用户 | AUTH-003 |
| UT-AUTH-004-01 | 工作台待办聚合：跨模块计数正确性（各源模块桩注入） | AUTH-004 |

### 1.2 ASSET 资产（BR-003~005，ASSET-001~003）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-ASSET-001-01 | 台账 CRUD：状态枚举 AssetStatus 四值流转（IN_USE/RETURNED/SCRAPPED/PENDING_REVIEW） | G4 |
| UT-ASSET-001-02 | 反向穿透查询按三态区分返回 | ASSET-B-R1 |
| UT-ASSET-002-01 | 正向穿透：实名人→资产链路层级 ≤ 5，超限返回 1013 | ASSET-F-R1 |
| UT-ASSET-002-02 | 穿透查询数据可见域过滤（全部/本部门/IP 组/仅本人四值） | 4.2 |
| UT-ASSET-003-01 | 批量导入校验：工单非法状态返回 1014 | ASSET-003 |
| UT-ASSET-003-02 | 导入行级错误定位（行号+字段）；部分成功不回滚已入库行 | G7 例外验证 |

### 1.3 ACCT 账号（BR-015/017，ACCT-001~005）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-ACCT-001-01 | 账号池领用：责任人非空且 IN_USE 返回 1021 | APP-R1 |
| UT-ACCT-001-02 | AccountStatus 五值状态机：IN_POOL→IN_USE→RETURNED 合法；FROZEN 态禁止领用/流转返回 1022 | G4/TRF-R2 |
| UT-ACCT-002-01 | 流转单状态：非法审批/确认/撤销返回 1023；FlowType 三类正确落 ims_account_flow | APP-R2 |
| UT-ACCT-002-02 | 流转收回：原责任人冻结逻辑 | TRF |
| UT-ACCT-003-01 | 归还闭环：未闭环禁关权限返回 1024 | RET-R3/BR-015 |
| UT-ACCT-004-01 | 冲话费：金额 > 5000 凭证必填返回 1025；凭证仅财务角色可见 | RC-R3/4.2 |
| UT-ACCT-004-02 | 账实核对差异率 ≥ 2% 返回 1026 | RC-R2/BR-017 |
| UT-ACCT-004-03 | 差异率计算精度（1.99% 通过 / 2.00% 拦截边界） | BR-017 |
| UT-ACCT-004-04 | 成本汇总：按账号/部门/平台聚合，月份过滤，合计等于冲话费记录 | ACCT-004 / 2.4.5 |
| UT-ACCT-005-01 | 时间线：按 flow_type 汇聚全生命周期事件，乱序时间排序正确 | ACCT-005 |

### 1.4 CERT 证件（BR-013，CERT-001~003）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-CERT-001-01 | 档案 CRUD；已删除档案操作返回 1031 | CERT-001 |
| UT-CERT-001-02 | 重复档案拦截：一人一类型一份有效返回 1032 | CERT-A-R3 |
| UT-CERT-001-03 | 审核状态非法流转返回 1033；CertStatus 五值映射 TINYINT 0~4 | G4 |
| UT-CERT-002-01 | 到期预警：T−30 黄 / T−7 红 / T−0 锁定，CertWarnLevel 三态正确 | BR-013 |
| UT-CERT-002-02 | 边界日：T=30/T=7/T=0 当天触发对应级别 | BR-013 |
| UT-CERT-002-03 | 证件过期/锁定在 LIVE 风控中直接判红（1045 联动） | LIVE-R2 |
| UT-CERT-003-01 | 访问级别：L1 请求原图返回 1034 | CERT-S-R1 |
| UT-CERT-003-02 | 高频访问：1 小时 > 10 次拦截返回 1035（10 次通过/11 次拦截边界） | CERT-S-R3 |
| UT-CERT-003-03 | 水印：人名+手机尾号+时间戳合成正确；原图不下放 | 4.2 |

### 1.5 LIVE 直播（BR-011/014，LIVE-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-LIVE-001-01 | 场次 ID 生成：19 位 = IMS+yyyyMMdd+3 位平台码（DYS/KS/WX/TM/JD/OTA）+4 位序列 | BR-011 |
| UT-LIVE-001-02 | 序列日切重置（跨日 0001）；并发 100 TPS 唯一性（压单测 100 线程） | V1-E1~E3 |
| UT-LIVE-001-03 | Redis 不可用降级 DB 行锁；恢复后对账回补（V1-E4） | V1-E4 |
| UT-LIVE-001-04 | ID 冲突兜底返回 1005 | 1005 |
| UT-LIVE-001-05 | 场次编码非法/不存在返回 1041 | LIVE-001 |
| UT-LIVE-002-01 | 风控评分：≥70 红（1043）/40~69 黄（1044）/＜40 绿；边界 69/70/39/40 | BR-014 |
| UT-LIVE-002-02 | 红色禁止开播；黄色需审批放行；LiveSessionStatus 状态机（PENDING_RISK_CHECK→APPROVED→LIVE→ENDED/CANCELLED）非法流转返回 1042 | G4 |
| UT-LIVE-003-01 | 下播数据必填缺失返回 1046 | BR-007 |
| UT-LIVE-003-02 | 已提交只读，修改走更正单返回 1047 | LIVE-D-R3 |
| UT-LIVE-003-03 | 24 小时录入超时督办标记 | LIVE-D-R1/1048 |
| UT-LIVE-003-04 | 补录缺说明/未审批返回 1049 | LED-R1 |
| UT-LIVE-004-01 | 下播数据字段校验（GMV/时长非负、金额两位小数） | G1 |

### 1.6 CONTENT 内容（BR-016，CONTENT-001~006）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-CONTENT-001-01 | SOP 不存在/未启用返回 1051；SopLevel 两值 | SOP-R1 |
| UT-CONTENT-002-01 | 选题立项缺 SOP 或计划发布日返回 1052 | TOP-R1 |
| UT-CONTENT-003-01 | 脚本未定稿传下游返回 1053 | SCR-R1 |
| UT-CONTENT-004-01 | DAG 节点不存在/打回节点非法返回 1055 | AIP-R3 |
| UT-CONTENT-004-02 | 全链路超时（60 分钟）返回 1056（59 分钟过/61 分钟超） | AIP-R4 |
| UT-CONTENT-004-03 | AiJobStatus 六值状态机（WAITING→GENERATING→PENDING_FINAL_REVIEW→REVIEW_PASSED/REVIEW_REJECTED/FAILED） | G4 |
| UT-CONTENT-005-01 | 审核回避：审核人=提交人返回 1057 | REV-R1 |
| UT-CONTENT-005-02 | 打回缺结构化未通过项返回 1058 | REV-R2 |
| UT-CONTENT-006-01 | 终审未通过禁止发布返回 1054 | AIP-R5/PUB-R1 |
| UT-CONTENT-006-02 | ContentStatus 七值状态机（DRAFT→IN_PROGRESS→PENDING_REVIEW→APPROVED/REJECTED→PUBLISHED→ARCHIVED） | G4 |
| UT-CONTENT-004-04 | ComfyUI 队列满返回 5004；P2 及以下任务暂停派发（队列 > 100） | V1-C6 |

### 1.7 V1 通用约束单测

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-COM-001 | 47 枚举常量与全局规范第 4 章一致性（脚本比对 src/enums/index.ts） | 全局规范 4 |
| UT-COM-002 | 错误码常量与 3.2 明细一致；各段位不越界 | 全局规范 3 |
| UT-COM-003 | 表名 47 张与共享规范 7.5.2 字典一致（实体注解扫描） | 共享规范 7.5.2 |
| UT-COM-004 | 多主体/租户预留字段默认值写入 | 关键约束 3 |
| UT-COM-005 | API 前缀路由断言（/auth /asset /acct /cert /live /content） | 共享规范 8.3 |

---

## 2. V2 单元测试（第 15~27 周，BR-101~117）

### 2.1 TRAIN 培训（TRAIN-001~003）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-TRAIN-001-01 | 资料 CRUD：MaterialType 三值（DOC/VIDEO/LINK）；ims_train_material | G1 |
| UT-TRAIN-002-01 | 任务下发：TrainTaskStatus 两值；按部门/岗位圈定人群正确 | TRAIN-002 |
| UT-TRAIN-002-02 | 学习记录 TrainStatus 四值状态机（NOT_STARTED→IN_PROGRESS→COMPLETED/MISSED） | G4 |
| UT-TRAIN-003-01 | 完成率统计口径（分母含 MISSED）；按部门聚合正确 | TRAIN-003 |

### 2.2 MEET 会议日报（MEET-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-MEET-001-01 | 会议 CRUD + ims_meeting_minutes 关联 | MEET-001 |
| UT-MEET-002-01 | 纪要审阅：ReviewAction 三值（READ/COMMENT/MARK_FOLLOW_UP）；待审阅人清单计算 | MEET-002 |
| UT-MEET-003-01 | 日报：ReportStatus 三值（DRAFT→SUBMITTED→READ）；补交标记 | MEET-003 |
| UT-MEET-004-01 | 日报模板 ims_report_template 变量替换正确性 | MEET-004 |

### 2.3 REPORT 数据上报（REPORT-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-REPORT-001-01 | 模板字段类型校验（数值/文本/枚举/日期） | REPORT-001 |
| UT-REPORT-002-01 | 填报单 SubmissionStatus 四值状态机（DRAFT→SUBMITTED→APPROVED/REJECTED）；驳回重报 | G4 |
| UT-REPORT-002-02 | 数值字段区间校验、必填触发 1001 | G1 |
| UT-REPORT-003-01 | 审批驳回原因必填 | REPORT-003 |
| UT-REPORT-004-01 | 汇总口径：PeriodType 三值；跨期归属（周报跨月） | REPORT-004 |

### 2.4 FLOW 工作流（FLOW-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-FLOW-001-01 | 模板 CRUD：ims_flow_template/ims_flow_node 节点编排校验（无孤立节点） | FLOW-001 |
| UT-FLOW-002-01 | 实例 FlowInstanceStatus 五值状态机（RUNNING→APPROVED/REJECTED/CANCELLED/TIMEOUT） | G4 |
| UT-FLOW-002-02 | 节点 FlowNodeStatus 四值（PENDING→APPROVED/REJECTED/TRANSFERRED）；转办后办理人变更 | FLOW-002 |
| UT-FLOW-002-03 | 会签/或签规则计算正确 | FLOW-002 |
| UT-FLOW-003-01 | 超时自动流转（TIMEOUT）触发 | FLOW-002 |
| UT-FLOW-004-01 | 节点权限校验（V2 授权基线：工作流节点权限） | 4.2 |

### 2.5 PERF 绩效（BR-109/110/BR-101~106 相关，PERF-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-PERF-001-01 | 指标编码唯一：重复返回 1151 | PERF-M |
| UT-PERF-001-02 | 得分规则：分段区间重叠返回 1152；分数越界 [0,100] 返回 1152 | PERF-M |
| UT-PERF-001-03 | COMPETE_SUBMIT_RATE 启用返回 1153（V2 期间禁用） | BR-110 |
| UT-PERF-001-04 | 同岗位指标集权重合计 ≠ 100 返回 1154（99.99/100/100.01 边界） | PERF-M |
| UT-PERF-002-01 | 计算引擎：指标取数源（TRAIN/MEET/REPORT 桩数据）聚合正确 | PERF-002 |
| UT-PERF-002-02 | 周期锁定后更正须审批：FinanceStatus.LOCKED 语义返回 1155 | BR-108 |
| UT-PERF-002-03 | 观察期不足（第 23 周前无基线）返回 1156 | BR-109 |
| UT-PERF-002-04 | 人工补充指标值缺 supplementReason 返回 1158 | PERF-C |
| UT-PERF-002-05 | PerfResultStatus 四值状态机（CALCULATING→PENDING_APPROVE→PUBLISHED/PENDING_MANUAL） | G4 |
| UT-PERF-003-01 | 结果未发布员工不可见返回 1157 | PERF-C |
| UT-PERF-003-02 | PerfGrade S~D 分档边界（85/60 分数分档 PerfGradeLevel EXCELLENT/QUALIFIED/IMPROVE） | PERF |
| UT-PERF-004-01 | 考试试卷：Σ题目分 ≠ totalScore 返回 1159 | PERF-E |
| UT-PERF-004-02 | 随机策略抽题数 > 题库存量返回 1160 | PERF-E |
| UT-PERF-004-03 | 考试窗口外开始返回 1161；重复开始返回 1162；答卷非本人返回 1163；已交卷重复提交返回 1164 | PERF-E |
| UT-PERF-004-04 | ExamStatus 五值状态机（NOT_STARTED→IN_PROGRESS→SUBMITTED→GRADED→MAKEUP_EXAM） | G4 |
| UT-PERF-004-05 | 补考成绩覆盖规则 | PERF-E |

### 2.6 ALERT 预警（ALERT-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-ALERT-001-01 | 规则编码唯一返回 1165；DSL 语法非法返回 1009 | ALERT-001 |
| UT-ALERT-001-02 | 规则评估引擎：指标阈值条件真假分支（L1/L2/L3 三级 AlertLevel） | ALERT-001 |
| UT-ALERT-001-03 | V2.3 子集剔除「成本未录入」规则（11 移 V3，源不可用） | 分期修订① |
| UT-ALERT-002-01 | 非预警目标人响应返回 1166 | ALERT-002 |
| UT-ALERT-002-02 | 已终态重复响应返回 1167；AlertEventStatus 四值状态机（OPEN→CONFIRMED→RESOLVED/FALSE_ALARM） | G4 |
| UT-ALERT-003-01 | 推送：AlertPushStatus 四值（PENDING→DELIVERED/PARTIAL_FAILED/FAILED）；部分失败重试 | ALERT-003 |
| UT-ALERT-004-01 | 统计口径：响应时长/解决率按事件维度计算 | ALERT-004 |
| ~~UT-ALERT-003-02~~ **已作废** | ~~5008（RAGFlow 组件不健康）事件接入预警中心~~（5007/5008 已移除、号位作废） | — |

---

## 3. AIR 单元测试（V2.2 批次，BR-019~035）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-AIR-SKILL-01 | SkillStatus 四值状态机（PENDING_AUDIT→PUBLISHED/DISABLED/REJECTED） | SKILL-001 |
| UT-AIR-SKILL-02 | 版本管理：ims_skill_ver 审核记录不可变；AirAuditStatus 三值 | SKILL-002 |
| UT-AIR-SKILL-03 | 技能上架禁用即时生效（网关查询结果变化） | SKILL-003 |
| UT-AIR-EXPERT-01 | 专家包组装：技能+知识+提示词组合校验（引用资源均已发布） | EXPERT-001/002 |
| UT-AIR-EXPERT-02 | 组装产物下发格式（服务端纯组装不执行 LLM） | 边界定义 |
| UT-AIR-KNOW-01 | 知识密级 KnowledgeSecretLevel 四值（PUBLIC/INTERNAL/CONFIDENTIAL/TOP_SECRET） | KNOW-002 |
| UT-AIR-KNOW-02 | 密级脱敏规则：机密外发拦截率 100%（样本含边界组合） | BR-027 |
| ~~UT-AIR-KNOW-03~~ **已作废** | ~~向量化任务入独立队列+优先级（GPU 池共用约束）~~（语义检索已移除，不做向量化） | — |
| UT-AIR-KEY-01 | Key 生成：air- 前缀；哈希存储明文不可反查 | KEY-001 |
| UT-AIR-KEY-02 | 动态鉴权：每次调用实时校验在职+授权，缓存 60s；离职即 403 | BR-021 |
| UT-AIR-KEY-03 | ApiKeyStatus 三值（ACTIVE/FROZEN/REVOKED）；吊销即时生效（缓存击穿验证 60s 窗口内） | BR-023 |
| UT-AIR-KEY-04 | QPM 默认 60 次/分钟/人；超限返回 429 并告警；按人调整生效 | BR-029 |
| UT-AIR-KEY-05 | 每日 Token 限额校验与累计 | KEY-003 |
| UT-AIR-MCP-01 | 网关验签：Bearer 优先/URL 兼容；白名单开启时 IP/指纹校验 | BR 链路 |
| UT-AIR-MCP-02 | McpToolName 四工具白名单（skills.list/get、experts.list/assemble）；knowledge.search/get 已移除 | McpToolName |
| UT-AIR-MCP-03 | 网关豁免 {code:0} 包装，按 MCP 协议错误格式返回 | V2-F3 |
| ~~UT-AIR-MCP-04~~ **已作废** | ~~输出密级过滤（检索结果按调用者授权+密级双重过滤）~~（语义检索已移除） | — |
| UT-AIR-KB-01 | 知识库 KbProvider=LOCAL 单值；文档审核 AirAuditStatus 三值 | KB-002/003 |
| ~~UT-AIR-KB-02~~ **已作废** | ~~5007 检索超时/5008 组件不健康错误路径~~（错误码已移除、号位作废） | — |
| UT-AIR-GRANT-01 | 三类授权 AirGrantType（DEPT/ROLE/PERSON）grant 表写入；AirGrantStatus（ACTIVE/REVOKED） | 授权模型 |
| UT-AIR-AUDIT-01 | 全量调用审计日志（工具名/耗时/Token 数/过滤命中） | KEY-003 |

---

## 4. V3 单元测试（FIN 先行第 28~33 周 + 其余第 33~42 周）

### 4.1 FIN 财务核算（BR-107~109/118，FIN-001~004）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-FIN-001-01 | 成本录入：EntryCostStatus 三值（DRAFT→SUBMITTED→CONFIRMED）；金额两位小数、非负 | FIN-001 |
| UT-FIN-001-02 | 成本核准触发 5 分钟内自动计算 | FIN-P-R1 |
| UT-FIN-002-01 | 利润计算：收入−成本聚合口径正确（场次维度） | FIN-002 |
| UT-FIN-002-02 | ProfitCalcStatus 四值（PENDING→CALCULATED→RECALCULATED/ABNORMAL）；重算幂等 | G4/G6 |
| UT-FIN-002-03 | 计算精度：金额全程 BigDecimal（scale 2、舍入模式统一）；典型样例 3 组复算误差为零 | BR-107 |
| UT-FIN-003-01 | 分成规则：同一场次多分成对象比例求和 ≤ 1.0000 且多对象集合求和 = 1.0000（V2-E2 口径）；边界 0.9999/1.0000/1.0001；fixedRate 超出 (0,1] 或阶梯区间重叠/比例非法返回 1146，优先级冲突返回 1147 | FIN-003 |
| UT-FIN-003-02 | ShareResultStatus 四值（PENDING_AUDIT→AUDITED→PAID_OFF→REVERSED）；冲销（REVERSED）负向记账 | G4 |
| UT-FIN-003-03 | 分成金额拆分精度：比例拆分累计 = 总额（尾差处理规则验证） | BR-107 |
| UT-FIN-004-01 | 期间结账：已结账期间录入返回 **1142**（归并原 1010 · FinanceStatus.LOCKED）（**#59** `test_fin_period_close_locks_writes_then_r4_red_correction`） | BR-118 |
| UT-FIN-004-02 | 结账后更正须 R4 审批流程（返回 1155 语义） | BR-108 |
| UT-FIN-004-03 | 台账一致性：场次 ID 关联 LIVE 数据；对账差异输出 | FIN-004 |

### 4.2 COMP 竞品（BR-206，COMP-001~003）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-COMP-001-01 | 竞品档案 CRUD；CompeteStatus 三值（TRACKING/PAUSED/ARCHIVED） | COMP-001 |
| UT-COMP-002-01 | 分析提交：CompAnalysisStatus 四值（DRAFT→SUBMITTED→STORED/REJECTED） | COMP-002 |
| UT-COMP-002-02 | 提交率 ≥ 95% 解禁条件计算（94.99/95/95.01 边界） | BR-206 |
| UT-COMP-003-01 | 竞品资产库查询与引用 | COMP-003 |
| UT-COMP-002-03 | 竞品指标禁用（1153）联动：PERF 指标启用须先过 COMP 提交率门槛 | BR-110/206 |

### 4.3 DC 数据中心（DC-001~003）

| 编编号 | 测试点 | 依据 |
|------|--------|------|
| UT-DC-001-01 | ODS 同步：15 分钟增量 + binlog 双通道任务调度；失败重试 | V3-A2 |
| UT-DC-001-02 | 同步延迟 > 1h 告警事件生成 | V3-A2 |
| UT-DC-002-01 | 聚合层预 join 结果正确性（场次×成本×利润宽表） | DC-T-R1 |
| UT-DC-002-02 | 双时态字段（业务时间/同步时间）写入 | DC-002 |
| UT-DC-003-01 | 穿透查询引擎：六入口（实名人/账号/资产/场次/成本/利润）返回链路完整 | BR-205 |
| UT-DC-003-02 | ims_dc_trace 轨迹留痕记录 | DC-003 |
| UT-DC-003-03 | 账号穿透查询不依赖 FIN（可并行验证） | 分期约束 |

### 4.4 BI 数据分析（BI-001~003）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-BI-001-01 | 自助报表：拖拽定义→DSL 解析→查询计划生成 | BI-001 |
| UT-BI-001-02 | DrillDimension 六维下钻（SESSION/PERSON/ACCOUNT/PLATFORM/DATE/SUBJECT） | BI-001 |
| UT-BI-001-03 | 超时转异步：> 10s 自动转异步任务（BiQueryMode SYNC→ASYNC）；单用户并发上限 10 | V3-B6 |
| UT-BI-002-01 | 看板订阅：PeriodType 三值推送 | BI-002 |
| UT-BI-003-01 | 分享：BiShareApproval 五值（含 EXPIRED）；行级权限过滤 BR-212 | BI-003 |
| UT-BI-002-02 | 查询结果 Redis 缓存 TTL 15 分钟；定义变更主动失效 | V3-B3 |
| UT-BI-001-04 | 查询性能统计写日志（BR-204 监控） | BI |

### 4.5 EFF 组织人效（EFF-001~002）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-EFF-001-01 | 人员归属：EffRelationType 两值；在职唯一主归属冲突返回 1198 | BR-213 |
| UT-EFF-001-02 | 兼职分摊合计 > 100% 返回 1199（边界 99.99/100/100.01） | BR-213 |
| UT-EFF-002-01 | 人效指标盘点：前置依赖（当月绩效未发布不可盘点返回 1199 拦截族） | BR-207/EFF-M-R2 |
| UT-EFF-002-02 | 覆盖率不足阻断发布（1198 拦截族） | EFF-M-R4 |
| UT-EFF-002-03 | ROI 计算口径（依赖 FIN 先行数据） | V3 依赖 |

---

## 5. 前端单元测试（Vitest，三期共用）

| 编号 | 测试点 | 依据 |
|------|--------|------|
| UT-FE-001 | 47 枚举工具（枚举→中文标签映射、非法值兜底） | 全局规范 4 |
| UT-FE-002 | StatusTag 组件：颜色映射集中配置、任意枚举值渲染 | 全局规范 5 |
| UT-FE-003 | FormRule 工厂：required/enumOf/money/dateRange 规则触发 | 全局规范 5 |
| UT-FE-004 | Axios 拦截器：错误码→提示映射（1001~1199/5001~5006；5007/5008 已移除）；401/403 跳转 | 8.2 |
| UT-FE-005 | 抽屉/表格组件分页、排序参数转换 | 契约分页规范 |

---

## 6. BR 覆盖矩阵（单元层）

| 期次 | BR 区间 | 总数 | 单元层覆盖用例数 | 覆盖说明 |
|------|---------|------|------------------|----------|
| V1 | BR-001~018 | 18 | 46 | 全部 BR 均有 ≥ 1 单测分支 |
| V2 | BR-101~106/110~117 | 14（110 禁用占位） | 33 | 计算类 BR（权重/观察期/指标禁用）重点覆盖 |
| AIR | BR-019~035 | 17 | 21 | 安全链路 BR 逐条覆盖 |
| V3 | BR-107/108/109/118 + BR-201~214 | 19（含 BR-101 备案引用） | 26 | FIN 精度类 + COMP 解禁阈值 + EFF 归属边界 |
| **合计** | — | **67（BR-101 V2 定义/V3 备案去重）** | **126** | 100% BR 单元层覆盖 |

> 执行要求：本 Checklist 全部 ☐ 项随开发迭代执行，CI 强制门禁（P0 Service 分支覆盖 < 90% 阻断合并）；每次文档版本升级（PRD/契约变更）须同步修订对应用例并跑回归。
