# IMS 用户外键写入规范（ADR-056 摘要）

> **SSOT（实现仓）**：`docs/adr/ADR-056-Football用户身份SSOT.md`  
> **IMS 范围**：凡写入 `*_user_id`、`assignee_id`、`keeper_id`、`target_user_id`、`leader_user_id`、`evaluator_id` 等人员 FK 的 IMS/OPS 并入模块（IPG 成员、采集任务、领用、REPORT 作者、PERF 考核对象等）。  
> **本文**：IMS 文档侧 checklist；**不**要求在本任务中修改 OPS 代码。

---

## 1. 身份铁律

| 项 | 规则 |
|----|------|
| LoginUser.userId | **shenyu-system** `system_users.id` |
| UserSelect / simple-list | Football 用户 HTTP（如 `GET /admin-api/system/user/simple-list`） |
| JSON 传 id | **字符串**（snowflake 精度） |

---

## 2. 写入前 / 回显

- **写入前**：`FootballSystemUserValidator.resolveStorableUserId(submittedId, tenantId)`  
- **回显选择器**：`resolvePresentableUserId(storedId)`（兼容历史 wd/legacy 存量）  
- **校验**：`assertInTenant` / `assertEnabledInTenant` / `hasRoleCode` — 禁止仅用 wd master 或 legacy `sys_user` 作为唯一写入校验  
- **禁止**：Football 集成场景下将 UserSelect id normalize 为 wd master id 再存储  

---

## 3. IMS 模块落点（文档验收）

| 模块 | 字段示例 | 规格引用 |
|------|----------|----------|
| IPG | 成员 userId | IPG 页面规格 |
| COLLECT | 任务责任人（若有） | COLLECT P5 |
| CORP/ACCT | keeper、领用 | ACCT / MASTER |
| REPORT | authorId（作者实体，非 system user 时见 ADR-051） | REPORT §0.2 |
| PERF | targetUserId | PERF-绩效考核 |
| SYS | 用户列表主键列 | SYS P1 |

---

## 4. 与 PRD 关系

完整 PRD IR-06 / §5.1 与 ADR-056 方向一致；Slice Gate 检查本摘要 + ADR-056 §4.2 Checklist。
