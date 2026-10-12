# OPS E2E 测试工作方法（Agent 可执行规范）

> **版本**：v1.0 | 2026-07-27  
> **性质**：E2E 测试 Agent 的执行 SSOT（与阶段 Gate、Slice 闸门互补）  
> **关联**：[`PHASE-DEV-METHOD.md`](./PHASE-DEV-METHOD.md) · [`AI-IMPL-GUIDE.md`](./AI-IMPL-GUIDE.md) · [`.cursor/rules/walkthrough-methodology.mdc`](../../.cursor/rules/walkthrough-methodology.mdc) · [`OPS-STARTUP-MATRIX.md`](../delivery/OPS-STARTUP-MATRIX.md) · [`OPS-DEV-DEPLOY-GUIDE.md`](../delivery/OPS-DEV-DEPLOY-GUIDE.md)

---

## 1. 核心结论（一句话）

> **Checklist / TESTCASES 为 SSOT** → 浏览器自动化复现操作 → **页面 + 截图 + 日志** 三类证据 → 缺陷闭环 → 回归 → 归档完整测试报告。  
> E2E Agent **只测不修**；开发 Agent **只修缺陷单范围内**；Gate 未通过 = 禁止宣称阶段完成。

---

## 2. 适用范围

| 适用 | 不适用 |
|------|--------|
| 页面级联调、Gate 验收、Slice DoD | 纯单元测试、纯 API 契约测试（可辅助，不替代 E2E） |
| Football 壳 `:5777` + Gateway `:48080` + oa-server `:48094` | 未在 Spec / Checklist 中声明的能力（禁止推断补测） |
| 与 [`walkthrough-methodology.mdc`](../../.cursor/rules/walkthrough-methodology.mdc) 互补的单页深度走查 | 整模块无边界「扫全站」 |

**铁律（与 [`spec-driven-impl.mdc`](../../.cursor/rules/spec-driven-impl.mdc) 一致）**

- Checklist / TESTCASES **未写明**的步骤或预期 → **停止**，输出阻塞清单，不得用行业惯例补全。
- 一条用例 = 一次可判定 **Pass / Fail / Blocked** 的原子场景。
- 失败必须 **登记缺陷 + 留证**，修复后必须 **同用例回归**，不得带伤标记通过。
- 环境未就绪（oa-server DOWN、Nacos 不可达等）→ 记 **Blocked**，不得记入业务缺陷库。

---

## 3. 输入物（测试前必须齐套）

| 优先级 | 文档 | 用途 |
|--------|------|------|
| P0 | `CHECKLIST-M*` / `GATE-S*` | 通过条件、阶段范围 |
| P0 | `TESTCASES-M*`（P0 100% 必跑） | 步骤、输入、预期 |
| P1 | PRD / UX / API / ADR | 预期歧义时 SSOT |
| P1 | [`OPS-TEST-DB.md`](../delivery/OPS-TEST-DB.md)、本地 / `-Beta` 环境说明 | DB、Nacos、账号 |
| P1 | [`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md) | 菜单 ID → Football `:5777` 嵌套路由 / Standalone 对照 |
| P2 | 已有 Playwright 脚本（如 `football-content-smoke.spec.ts`） | 可复用，不得替代 Checklist 覆盖 |

**环境就绪检查（每次 E2E 会话开头）**

```
□ :5777 前端 UP（Gate 路径，见 OPS-STARTUP-MATRIX §3）
□ :48080 Gateway UP
□ :48094 oa-server UP（Beta 时本机 :8848 可为 DOWN，见 OPS-TEST-DB）
□ 登录账号 / 租户与用例一致（默认 admin / admin123，租户 1）
□ Collector :8000（仅 M10 采集类用例）
□ 启动方式已确认：本地 .\scripts\start-ops-dev.ps1 或 -Beta
```

---

## 4. 角色与职责

| 角色 | 职责 |
|------|------|
| **E2E Agent（测试）** | 读用例 → 自动化执行 → 断言 / 截图 / 采日志 → 比对 → 登记缺陷 → 出报告 |
| **开发 Agent** | 按缺陷单修复 → 自测 → 通知回归 |
| **协调者（可选）** | 环境、Gate、Slice 边界、Football 子仓库 `ops` 分支改动范围 |

**交接规则**

- E2E Agent **只测不修**（除测试脚本 / 断言本身）。
- 开发 Agent **只修缺陷单范围内**文件，修复须带 **FR/AC 或 TC 编号**（见 [`AI-IMPL-GUIDE.md`](./AI-IMPL-GUIDE.md) §Bug 修复）。
- 回归由 **E2E Agent** 重跑 **失败用例 + 同模块 P0 冒烟**。
- Football 嵌入代码改动须遵守 [`FOOTBALL-OPS-BRANCH.md`](../delivery/FOOTBALL-OPS-BRANCH.md)（`ops` 分支，非 master）。

---

## 5. 单条用例执行流程（标准 SOP）

```
读取用例 → 准备数据/环境 → 浏览器自动化操作 → 采集三类证据 → 与预期比对 → Pass/Fail/Blocked
```

### 5.1 读取用例（结构化）

每条用例至少解析：

| 字段 | 示例 |
|------|------|
| **TC-ID** | `M2-CONTENT-012` |
| **前置条件** | 已登录、存在标题含「马维超」的内容 |
| **操作步骤** | 1. 打开内容管理 2. 点「查看」… |
| **输入数据** | 标题=马维超，租户=1 |
| **预期结果** | 见「免费内容」「付费内容」；表格有边框；无系统异常 |
| **优先级** | P0 / P1 |

### 5.2 浏览器自动化（Playwright 为主）

**原则**

- 操作路径与 Checklist **逐步一致**（菜单、按钮文案、表单字段）。
- 优先 **用户可见行为**（角色、标签、表格行），少依赖实现细节。
- Football 集成入口统一 `:5777`，API 经 `:48080`（非 Standalone `:3000/:8080`，见 [`OPS-STARTUP-MATRIX.md`](../delivery/OPS-STARTUP-MATRIX.md)）。

**推荐目录**

```
football-front/apps/web-ele/tests/           # Gate :5777 用例（含静态扫描）— SSOT
football-front/apps/web-ele/playwright.config.ts  # baseURL :5777，无 webServer
football-front/apps/web-ele/test-results/    # 截图、trace（gitignore）
football-front/apps/web-ele/playwright-report/  # HTML 报告（gitignore）
scripts/logs/                                # ops-server、gateway 等日志
docs/delivery/e2e-artifacts/{date}/          # 归档用截图索引（建议，见 §11）
```

> **A-WP1 cutover**：`ops-platform-ui-vue` 已删除；Gate Playwright 仅维护 `football-front/apps/web-ele/tests/`。Standalone `:3000` 路径已退役。

**常用命令**

```powershell
# 环境（Gate 路径）
.\scripts\start-ops-dev.ps1

# Gate Playwright（推荐一键）
.\scripts\run-gate-football-e2e.ps1

# Football 集成内容冒烟（示例）
cd football-front/apps/web-ele
npx playwright test tests/football-content-smoke.spec.ts --config=playwright.config.ts

# 58 路由 UAT 基线
.\scripts\run-uat-football-e2e.ps1

# API + Vite 路由探针（非完整 AC，辅助）
python scripts/verify-ops-pages-per-menu.py --api --base http://localhost:48080 --vite http://localhost:5777
```

### 5.3 三类证据（Fail 时必须齐全）

| 类型 | 内容 | 用途 |
|------|------|------|
| **A. 页面** | 元素可见性、文案、DOM（如 `table`、`th` 背景色）、Network 状态码 | 主断言 |
| **B. 截图** | 关键步骤全页 / 组件截图（**Pass 也保存**，不只失败时） | 人工复核、报告附件 |
| **C. 日志** | 浏览器 console、Network 失败请求、oa-server / gateway 同期 ERROR | 区分前端 / 后端 / 环境问题 |

**截图命名规范**

```
test-results/{TC-ID}_{步骤}_{pass|fail}_{timestamp}.png
例：test-results/M2-CONTENT-012_view_pass_1730000000.png
```

**日志采集窗口**

- 失败时刻 **前后 ±2 分钟** 的 `scripts/logs/oa-server*.log`、相关 Network 请求 URL + response body（脱敏）。

### 5.4 预期比对规则

| 比对结果 | 判定 |
|----------|------|
| 页面 + 日志均符合预期 | **Pass** |
| 页面不符合，日志正常 | **Fail（前端 / 展示）** |
| 页面空白 / 系统异常，API 5xx | **Fail（后端 / 环境）** |
| 预期不明确 | **Blocked**，不记 Pass |
| 环境未就绪 | **Blocked**，不记入业务缺陷库 |

**禁止**

- 仅「脚本 green」但无截图、未核对 Checklist 预期 → 不得 Pass。
- API 200 但业务数据为空且 spec 要求非空 → 不得 Pass（见 walkthrough §报告自查）。

---

## 6. 缺陷管理

### 6.1 缺陷单模板

```markdown
## DEF-{YYYYMMDD}-{序号}

- **关联用例**: TC-ID / CHECKLIST 条目
- **优先级**: P0 / P1
- **现象**: （用户可见描述）
- **预期**: （摘自 TESTCASES）
- **复现步骤**: 1…2…3…
- **环境**: 本地 / Beta；:5777 / :48080 / :48094
- **证据**:
  - 截图: test-results/xxx.png（或 e2e-artifacts 归档路径）
  - API: GET /admin-api/oa/... → code/msg
  - 日志: oa-server …（摘录）
- **限定修复范围**: （文件/模块；Football 原代码约束时注明）
- **状态**: Open → Fixed → Verified
```

**缺陷库位置（SSOT）**

```
docs/delivery/defects/DEF-{YYYYMMDD}-{序号}.md   # 见 defects/README.md
docs/delivery/e2e-artifacts/{批次}-{date}/       # 见 e2e-artifacts/README.md
MASTER-EXECUTION-TRACKER.md §13                  # Gate 阻塞表（环境 / 阶段级）
GATE-S{n}-报告-{date}.md §缺陷                   # Gate 归档内嵌
```

### 6.2 交给开发 Agent 的 Prompt 要点

```markdown
缺陷单 DEF-xxx + TC-ID + 证据路径 + 限定文件范围
修复后须：相关 mvn test / IT（若适用）+ 说明验证步骤
禁止扩大范围；Football 嵌入目录改动走 ops 分支
引用 AI-IMPL-GUIDE 五段式中的 Constraints + Self-Check
```

---

## 7. 回归与闭环

```
Fail → 登记 DEF → 开发修复 → E2E 重跑该 TC（+ 同页 P0 冒烟）→ Pass 则关闭 DEF
```

| 轮次 | 范围 |
|------|------|
| **缺陷回归** | 失败 TC + 直接关联 TC |
| **模块冒烟** | 同模块 P0（如内容管理 CONTENT-GATE-001~004） |
| **Gate 回归** | 上一 Gate P0 仍绿（S1 起，见 [`PHASE-DEV-METHOD.md`](./PHASE-DEV-METHOD.md) R-G06） |

**E2E 完成条件（与 Phase Gate 对齐）**

1. 本轮 Checklist / TESTCASES **P0 100% Pass**
2. 所有 DEF 状态 **Verified**
3. 截图索引 + Playwright 报告路径 + 缺陷闭环表归档
4. 更新 `GATE-S{n}-报告-{date}.md` / `MASTER-EXECUTION-TRACKER.md`（若属 Gate）

---

## 8. 完整测试报告模板

```markdown
# E2E 测试报告 — {模块 / Gate} — {YYYY-MM-DD}

## 1. 概要
- 范围: CHECKLIST-Mx / TESTCASES-Mx P0
- 环境: 本地 / Beta（110.42.49.224）
- 结论: ✅ 通过 / ❌ 未通过（P0 x/y）

## 2. 环境
| 服务 | 地址 | 状态 |
| Gateway | :48080 | UP/DOWN |
| oa-server | :48094 | UP/DOWN |
| 前端 | :5777 | UP/DOWN |

## 3. 用例结果
| TC-ID | 描述 | 结果 | 截图 |
|-------|------|------|------|
| M2-xxx | … | Pass | test-results/… 或 e2e-artifacts/… |

## 4. 缺陷
| DEF-ID | TC | 状态 | 说明 |
|--------|-----|------|------|

## 5. 证据索引
- Playwright HTML: playwright-report/index.html（本地路径，不入库）
- 截图目录: test-results/ 或 docs/delivery/e2e-artifacts/{date}/
- 日志: scripts/logs/（摘录附录）

## 6. 回归记录（若有）
| 轮次 | 重跑 TC | 结果 |

## 7. 阻塞 / 风险
- …

## 8. 签字
- E2E Agent: 完成日期
- 开发 Agent: 修复确认（如有）
```

Gate 级报告可复用 [`gates/GATE-报告模板.md`](../delivery/gates/GATE-报告模板.md)，本模板侧重 **用例级 + 证据级** 明细。

---

## 9. Agent 执行清单（可直接当 Prompt 用）

**会话开场**

1. `@` 引用 CHECKLIST + TESTCASES（不粘贴全文）
2. 确认环境与 `-Beta` / 本地（[`OPS-TEST-DB.md`](../delivery/OPS-TEST-DB.md)）
3. 执行 §3 环境就绪检查
4. 列出本轮 **P0 用例 ID 列表**

**每条用例**

5. Playwright：按步骤操作 + 输入  
6. 断言页面元素 + 必要时 API  
7. **截图**（Pass / Fail 均保存）  
8. Fail → 采日志 → 写 DEF → **不修改业务代码**  
9. 更新用例结果表  

**会话结束**

10. 若有 Open DEF → 移交开发 Agent（§6.2 Prompt）  
11. 修复后 **新开回归会话**，重跑失败 TC  
12. P0 全绿 → 输出 §8 完整报告  

**与走查方法论的分工**

| 场景 | 用本文 | 用 walkthrough |
|------|--------|----------------|
| Gate / TESTCASES P0 验收 | ✅ 主路径 | 辅助深度断言 |
| 单页 enum / dict 不对齐排查 | 登记 DEF 后交开发 | ✅ 7 步法 + DB dict 真值 |
| S-R* 走查报告 | 引用 walkthrough 报告 §四.4 | ✅ SSOT |

---

## 10. 与现有仓库的映射

| 方法环节 | 仓库落点 |
|----------|----------|
| Checklist | `docs/delivery/CHECKLIST-M*`、`gates/GATE-S*` |
| 测试用例 | `docs/delivery/TESTCASES-M*` |
| 阶段 Gate SSOT | [`MASTER-EXECUTION-TRACKER.md`](../delivery/MASTER-EXECUTION-TRACKER.md) |
| 浏览器自动化（:5777） | `football-front/apps/web-ele/tests/*.spec.ts`、`playwright.config.ts` |
| 58 路由 UAT | `scripts/run-uat-football-e2e.ps1`、`football-front/apps/web-ele/tests/uat-football-ops-login.spec.ts` |
| API 路由探针 | `scripts/verify-ops-pages-per-menu.py` |
| 截图（运行时） | `ops-platform-ui-vue/test-results/`（`.gitignore`） |
| 后端日志 | `scripts/logs/oa-server-nacos-run.log` 等 |
| 缺陷 / 阻塞 | [`docs/delivery/defects/`](../delivery/defects/README.md) · [`e2e-artifacts/`](../delivery/e2e-artifacts/README.md) · `MASTER-EXECUTION-TRACKER.md` §13 |
| Gate 归档 | `docs/delivery/gates/GATE-S{n}-报告-{date}.md` |
| 环境启动 | `scripts/start-ops-dev.ps1` · [`OPS-DEV-DEPLOY-GUIDE.md`](../delivery/OPS-DEV-DEPLOY-GUIDE.md) |

**一句话定义**

**E2E 完成** = 在指定环境下，按 Checklist / TESTCASES 用浏览器自动化完整执行 P0 用例，以 **页面 + 截图 + 日志** 证明符合预期，缺陷全部 **登记 → 修复 → 回归通过**，并输出 **可追溯的完整测试报告**。

---

## 11. 可行性评估

> **评估日期**：2026-07-27  
> **结论**：**部分可行** — 方法论与现有 Gate / Playwright / :5777 栈高度对齐，可作为 E2E Agent 执行 SSOT；需补强缺陷库、证据归档、环境与脚本统一后，方可稳定规模化运行。

### 11.1 与当前栈的契合度

| 维度 | 现状 | 与方法的关系 |
|------|------|--------------|
| **Playwright** | `football-front/apps/web-ele/tests` 20+ spec；`playwright.config.ts` 指向 `:5777` 且 `screenshot: 'on'` | ✅ 可直接承载 §5.2 |
| **Gate 环境** | `start-ops-dev.ps1` → :5777 / :48080 / :48094；文档完备 | ✅ §3 环境检查可执行 |
| **Checklist / TESTCASES** | 各模块 `CHECKLIST-M*`、`TESTCASES-M*` 已存在 | ✅ SSOT 已有 |
| **缺陷闭环** | Gate 报告模板、§13 阻塞表、walkthrough DEF 实践（S-R*）、[`defects/`](../delivery/defects/README.md) | ✅ 已建（2026-07-27） |
| **开发 Agent 交接** | `AI-IMPL-GUIDE` 五段式 + Bug 修复规则 | ✅ §6.2 可落地 |
| **58 路由基线** | `run-uat-football-e2e.ps1` + Python 探针 58/58 | ⚠️ 路由 smoke ≠ TESTCASES AC 全覆盖 |
| **单页深度走查** | `walkthrough-methodology.mdc` 7 步法 | ✅ 互补，非重复 |

### 11.2 已有能力 vs 缺口

| 已有 | 缺口 |
|------|------|
| Playwright + Football config + `football-content-smoke.spec.ts` | TESTCASES P0 与 spec **未系统化映射**（无 TC-ID tag） |
| `verify-ops-pages-per-menu.py` 58/58 API + Vite 探针 | 多数页面 **无逐步 AC 自动化** |
| Gate 报告模板、`MASTER-EXECUTION-TRACKER`、[`defects/`](../delivery/defects/README.md) | ✅ 已建（2026-07-27） |
| walkthrough 截图 / 报告自查规则、[`e2e-artifacts/`](../delivery/e2e-artifacts/README.md) | Pass 截图运行时仍在 gitignore；Gate 归档复制到 e2e-artifacts |
| `run-uat-football-e2e.ps1` / `run-gate-football-e2e.ps1` | 均指向 `football-front/apps/web-ele/tests`（ui-vue 双轨已结束） |
| S-R* 走查报告（19+ 页经验） | E2E Agent Prompt **未写入 `.cursor/rules/`**（本文首次落盘） |

### 11.3 主要风险

| # | 风险 | 影响 | 严重度 |
|---|------|------|--------|
| **R1** | **环境 flaky**（Beta 远程 DB / Flyway 漂移、oa-server 未注册 Nacos、Redis 密码） | Blocked / Fail 混淆，假阳性业务缺陷 | 高 |
| **R2** | **截图在 `.gitignore`**（`test-results/`、`playwright-report/`） | 无归档则 **假 Pass**（脚本绿但无人工可复核证据） | 高 |
| **R3** | **Agent  scope creep**（E2E Agent 顺手改业务代码；或开发 Agent 扩大修复范围） | 破坏「一片一会话」与 Gate 可追溯性 | 中 |
| **R4** | **与 Gate 协议重复 / 冲突** | 若 E2E 报告与 GATE 报告标准不一致，出现双 SSOT | 中 |
| **R5** | **Football 嵌入代码约束** | 缺陷修复需改 `football-front` / `football-backend-saas` 时，分支与合入流程复杂 | 中 |
| **R6** | **缺陷库不存在** | DEF 散落聊天 / 临时 md，回归易遗漏 | 中 → **已缓解**（[`defects/`](../delivery/defects/README.md)） |
| **R7** | **58 路由 smoke 替代 AC** | 页面「能打开」≠ 业务正确，Gate 误签收 | 中 |

### 11.4 建议措施（可执行）

| # | 措施 | 落点 |
|---|------|------|
| **M1** | ✅ [`docs/delivery/defects/`](../delivery/defects/README.md) + [`DEF-TEMPLATE.md`](../delivery/defects/DEF-TEMPLATE.md)；Open DEF 必须入 §13 或 defects 文件 | 已落地 2026-07-27 |
| **M2** | ✅ **证据归档**：[`docs/delivery/e2e-artifacts/`](../delivery/e2e-artifacts/README.md)（如 `CONTENT-GATE-20260727/`）；Gate 通过时复制关键 Pass 截图 | §8 报告 §5 |
| **M3** | Playwright 用 **`test.describe('TC-M2-CONTENT-012')`** 或 tag `@p0` 对齐 TESTCASES ID；`playwright.config.ts` 保持 `screenshot: 'on'` | `football-front/apps/web-ele/tests/` |
| **M4** | E2E 会话 **强制** 先跑 `start-ops-dev.ps1` 健康检查脚本（或 §3 checklist）；Beta 单独标记 `-Beta`，缺陷单注明环境 | 会话开场 SOP |
| **M5** | 明确 **L3 Gate（PHASE-DEV-METHOD）为主闸门**，本文 **L2.5 E2E 证据层**；Gate 报告 §自动化 引用 E2E 报告路径，不重复定义通过标准 | 文档关系 |
| **M6** | E2E Agent 规则写入 **`.cursor/rules/e2e-agent-method.mdc`**（`alwaysApply: false`，E2E 任务触发） | 后续迭代 |
| **M7** | 深度 UI / dict 问题走 **walkthrough 7 步法**，E2E 只登记 DEF 不替代 DB dict 排查 | §9 分工表 |

### 11.5  verdict 说明

| 判定 | 含义 |
|------|------|
| ~~可行~~ | 未选 — M3–M6 等仍待迭代 |
| **部分可行** ✅ | **当前推荐**：M1/M2 已落地；方法正确，栈具备 70%+ 能力，按 §11.4 继续补强后可规模化 |
| ~~需补强~~ | 若不做 M1–M4，仅适合 **人工监督下的试点**（如单模块 CONTENT-GATE） |

**推荐试点路径**

1. 选 **TESTCASES-M2 P0** 中 4–8 条用例，补 Playwright + TC-ID tag。  
2. 跑一轮完整 **DEF → 开发修复 → 回归**，验证 §6–§7 闭环。  
3. 归档首份 `docs/delivery/e2e-artifacts/` + `defects/DEF-*.md`。  
4. 通过后写入 `.cursor/rules/e2e-agent-method.mdc`，再推广至其他模块。

---

## 12. 文档索引

| 类型 | 路径 |
|------|------|
| 本文（E2E Agent SSOT） | `docs/engineering/E2E-AGENT-METHOD.md` |
| 阶段开发方法 | `docs/engineering/PHASE-DEV-METHOD.md` |
| AI 五段式 / Bug 修复 | `docs/engineering/AI-IMPL-GUIDE.md` |
| 浏览器走查 7 步法 | `.cursor/rules/walkthrough-methodology.mdc` |
| 启动矩阵 | `docs/delivery/OPS-STARTUP-MATRIX.md` |
| 开发部署 | `docs/delivery/OPS-DEV-DEPLOY-GUIDE.md` |
| Beta 测试库 | `docs/delivery/OPS-TEST-DB.md` |
| Gate 进度 | `docs/delivery/MASTER-EXECUTION-TRACKER.md` |
| 缺陷库 | [`docs/delivery/defects/`](../delivery/defects/README.md) |
| E2E 证据归档 | [`docs/delivery/e2e-artifacts/`](../delivery/e2e-artifacts/README.md) |

---

*维护：E2E 流程或 Playwright 目录变更时，同步更新 §10 映射与 §11 缺口表。*
