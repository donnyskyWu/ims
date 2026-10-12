# 质量门控与代码审查清单

> **版本**：v1.0 | 2026-06-07
> **关联**：[`DEV-PLAN.md`](./DEV-PLAN.md) | [`AI-IMPL-GUIDE.md`](./AI-IMPL-GUIDE.md)
> **目的**：确保每个 Slice / 迭代 / 阶段的交付质量

---

## 1. 三级质量门控

### 1.1 Slice DoD（Definition of Done）

每个 Slice **必须**满足：

#### 1.1.1 文档完整性

- [ ] 阻塞问题清单已澄清（无 PENDING）
- [ ] 5 文档已完整阅读（PRD/UX/API/STATE/SLICES/TESTCASES）
- [ ] 与 Slice 相关的 ADR 已创建（如有）

#### 1.1.2 代码完整性

- [ ] 后端代码（DO/DTO/Service/Controller/Mapper）
- [ ] 前端代码（Page/Form/Table/Components）
- [ ] 数据库 DDL（含索引、审计字段、tenant_id）
- [ ] 状态机配置（如涉及）
- [ ] MyBatis XML（如需）

#### 1.1.3 5 大铁律

- [ ] 强关联字段用选择器（前端）+ 校验（后端）
- [ ] 字典字段用 @InDict
- [ ] 多租户隔离（tenant_id + WHERE）
- [ ] AES-256 加密（敏感字段）
- [ ] 错误码 1500-1504

#### 1.1.4 9 项检查

- [ ] 中文注释解释"为什么"
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 状态机转移完整
- [ ] 审计日志记录 CUD
- [ ] 权限标识符合 `oa:{resource}:{action}`
- [ ] 未修改 pom.xml（除非明确）
- [ ] 未修改 application.yml（除非明确）
- [ ] 未修改公共组件（除非 ADR 授权）
- [ ] Commit message 格式正确

#### 1.1.5 测试覆盖

- [ ] F 用例 ≥ 3 条
- [ ] P 用例 ≥ 3 条
- [ ] E 用例 ≥ 3 条
- [ ] P0 用例 100% 通过
- [ ] 覆盖率 ≥ 80%（JaCoCo）

#### 1.1.6 审查通过

- [ ] 1 个审查者通过
- [ ] 阻塞问题已解决
- [ ] PR 合并到 main

### 1.2 迭代 DoR（Definition of Release）

每个迭代结束**必须**满足：

| 项 | 标准 | 验证 |
|----|------|------|
| 所有 Slice DoD | 100% | PR 列表 |
| Pilot 抽检 | 1 个通过 | Pilot 报告 |
| 集成测试 | 跨模块接口 100% | 测试报告 |
| 性能基线 | 列表 ≤ 1.5s | JMeter |
| 文档同步 | 与代码同步 | diff 审查 |
| ADR 记录 | 决策已记录 | ADR 列表 |
| 周报 | 已提交 | 周报文档 |
| Demo | 给产品演示 | 反馈 |

### 1.3 阶段 DoR

| 阶段 | 退出标准 | 验证 |
|------|---------|------|
| 阶段 0 | HelloWorld 全流程跑通 | 演示 |
| 阶段 1 | P0 模块上线 | 集成测试 |
| 阶段 2 | 业务主流程跑通 | E2E 测试 |
| 阶段 3 | P2 模块上线 | Pilot 抽检 |
| 阶段 4 | UAT + 性能 + 安全 + 上线 | UAT 报告 |

---

## 2. 代码审查清单（详细版）

### 2.1 审查流程

```
开发者提交 PR
    ↓
CI 自动检查（5 分钟内）
    ↓
自动扫描（铁律 / 字典 / 多租户 / 加密 / 错误码）
    ↓
人工审查（指定审查者）
    ↓
通过 → 合并
不通过 → 退回 + 阻塞清单
```

### 2.2 5 大铁律审查（🔴 必查）

#### 铁律 1：强关联选择器

**审查项**：
- [ ] 5 类字段（realnameId/phoneId/simCardId/companyId/accountId）前端用 `<XxxSelect />`
- [ ] 禁用手动输入（input 框只读或不可输入）
- [ ] 后端校验 4 条：存在 / 启用 / 跨租户 / 已绑定
- [ ] 错误码：1501 / 1502 / 1504 正确

**反模式**：
```vue
<!-- ❌ 错误：手动输入 -->
<el-input v-model="form.realnameId" />

<!-- ❌ 错误：单选 input -->
<el-radio-group v-model="form.realnameId">
  <el-radio :label="1">张三</el-radio>
</el-radio-group>

<!-- ✅ 正确：使用选择器 -->
<RealNameSelect v-model="form.realnameId"
  :show-bound="true"
  :allow-force-replace="true" />
```

**后端校验**：
```java
// ❌ 错误：无校验
realnameMapper.selectById(req.getRealnameId());

// ✅ 正确：完整校验
private void validateRealname(Long realnameId) {
    RealnameDO rn = realnameMapper.selectById(realnameId);
    if (rn == null) throw new BusinessException(REALNAME_NOT_EXISTS);  // 1501
    if (!rn.getTenantId().equals(getCurrentTenantId())) {
        throw new BusinessException(REALNAME_CROSS_TENANT);  // 1504
    }
    if (!"ENABLED".equals(rn.getStatus())) {
        throw new BusinessException(REALNAME_DISABLED);  // 1501
    }
    if (realnameMapper.isBound(realnameId) && !forceReplace) {
        throw new BusinessException(REALNAME_ALREADY_BOUND);  // 1502
    }
}
```

#### 铁律 2：数据字典

**审查项**：
- [ ] 所有枚举字段（方式/状态/类型/平台/阶段）有 `@InDict`
- [ ] dict-type 字符串与 GLOBAL-CONVENTIONS 一致
- [ ] 错误码 1503

**反模式**：
```java
// ❌ 错误：无注解
private String status;

// ✅ 正确
@InDict("dict_realname_status")
private String status;
```

#### 铁律 3：多租户隔离

**审查项**：
- [ ] 所有业务表 DDL 含 `tenant_id` 字段
- [ ] 字段含 `idx_tenant_id` 索引
- [ ] 所有 SELECT/WHERE/DELETE 自动注入 `tenant_id`
- [ ] 错误码 1504

**反模式**：
```sql
-- ❌ 错误：缺 tenant_id
SELECT * FROM oa_realname WHERE id = ?

-- ✅ 正确
SELECT * FROM oa_realname WHERE id = ? AND tenant_id = ?
```

#### 铁律 4：AES-256 加密

**审查项**：
- [ ] 敏感字段（idCard/phone/cookie/apiKey/password）落库前加密
- [ ] 字段名以 `Encrypted` 结尾
- [ ] 入参 DTO 是明文，落库前调用 `aesUtil.encrypt()`
- [ ] 出参解密（响应给前端）
- [ ] 日志脱敏（不打印明文）

**反模式**：
```java
// ❌ 错误：明文落库
private String idCard;

// ✅ 正确
private String idCardEncrypted;  // 落库前 aesUtil.encrypt(req.getIdCard())

// DTO 入参明文
@NotBlank
private String idCard;  // 入参明文
```

#### 铁律 5：错误码 1500-1504

**审查项**：
- [ ] 业务异常用 `BusinessException(CODE, MSG)`
- [ ] CODE 必须在 1500-1504 范围
- [ ] 不用 `RuntimeException`
- [ ] 不用 HTTP 5xx 模拟业务错误

**反模式**：
```java
// ❌ 错误
throw new RuntimeException("参数错误");

// ✅ 正确
throw new BusinessException(ErrorCodeConstants.PARAM_INVALID, "参数错误");
```

### 2.3 9 项检查（🟡 推荐）

#### 检查 1：字段名一致性

**工具**：字段对比脚本

```python
# scripts/check_field_consistency.py
api_fields = extract_fields_from_api_doc(API_DOC_PATH)
do_fields = extract_fields_from_java(JAVA_PATH)
diff = api_fields - do_fields
if diff:
    raise Exception(f"字段不一致: {diff}")
```

#### 检查 2：中文注释"为什么"

```java
// ❌ 反例：解释"做了什么"
// 设置状态为启用
rn.setStatus("ENABLED");

// ✅ 正例：解释"为什么"
// 启用前必须检查多租户，防止跨租户操作
validateTenant(rn);
rn.setStatus("ENABLED");
```

#### 检查 3：测试覆盖率 ≥ 80%

**工具**：JaCoCo

```bash
mvn clean test
# 报告：target/site/jacoco/index.html
# 检查 Line Coverage ≥ 80%
```

#### 检查 4：状态机完整

```java
// 状态机转移定义
StateMachineTransition<RealnameState, RealnameEvent> transitions = ...;
transitions
    .withSource().state(ENABLED).and()
    .withSource().state(DISABLED).and();
```

#### 检查 5：审计日志

```java
// 所有 CUD 都应记录
@Around("execution(* cn.iocoder.yudao.module.oa.service..*.create*(..))")
public Object audit(ProceedingJoinPoint pjp) {
    Object before = ...;
    Object result = pjp.proceed();
    auditLogService.log("CREATE", before, result);
    return result;
}
```

#### 检查 6：权限标识

```java
// ✅ 规范：oa:{resource}:{action}
@PreAuthorize("hasAuthority('oa:realname:create')")
@PreAuthorize("hasAuthority('oa:account:disable')")
```

#### 检查 7-9：未修改公共文件

```bash
git diff main --name-only | grep -E "(pom.xml|application.yml|common/)" 
# 应为空（除非 ADR 授权）
```

---

## 3. 自动化检查脚本

### 3.1 字段一致性检查

```python
# scripts/audit/check_field_consistency.py
"""对比 API 文档字段定义与 Java DO 字段名"""
import re
import sys

def extract_api_fields(api_doc_path):
    with open(api_doc_path) as f:
        c = f.read()
    return set(re.findall(r'`([a-z][a-zA-Z]+)`', c))

def extract_do_fields(do_path):
    with open(do_path) as f:
        c = f.read()
    return set(re.findall(r'private\s+\w+\s+(\w+);', c))

if __name__ == '__main__':
    api_fields = extract_api_fields(sys.argv[1])
    do_fields = extract_do_fields(sys.argv[2])
    missing = api_fields - do_fields
    extra = do_fields - api_fields
    if missing or extra:
        print(f"❌ 字段不一致")
        print(f"  API 有 DO 无: {missing}")
        print(f"  DO 有 API 无: {extra}")
        sys.exit(1)
    print("✅ 字段一致")
```

### 3.2 5 铁律静态扫描

```python
# scripts/audit/check_5_rules.py
"""5 大铁律静态扫描"""
import re
import os

def check_strong_selectors(java_path):
    """检查强关联字段是否校验"""
    with open(java_path) as f:
        c = f.read()
    for field in ['realnameId', 'phoneId', 'simCardId', 'companyId', 'accountId']:
        if field in c:
            # 检查附近 500 字符内是否有 1501/1504 错误码
            for m in re.finditer(field, c):
                ctx = c[max(0, m.start()-500):m.end()+500]
                if '1501' not in ctx and '1504' not in ctx:
                    print(f"⚠️ {java_path}: {field} 缺少 1501/1504 校验")

def check_dicts(java_path):
    """检查字典字段是否 @InDict"""
    with open(java_path) as f:
        c = f.read()
    # 找到所有 String 字段
    fields = re.findall(r'private\s+String\s+(\w+);', c)
    for f in fields:
        if f.startswith('dict') or 'Status' in f or 'Type' in f:
            # 检查类级别是否有 @InDict
            if '@InDict' not in c:
                print(f"⚠️ {java_path}: {f} 缺少 @InDict")

def check_tenant_id(sql_path):
    """检查 DDL 是否含 tenant_id"""
    with open(sql_path) as f:
        c = f.read()
    if 'CREATE TABLE' in c and 'oa_' in c:
        if 'tenant_id' not in c:
            print(f"❌ {sql_path}: 缺 tenant_id 字段")

def check_aes(java_path):
    """检查敏感字段是否加密"""
    with open(java_path) as f:
        c = f.read()
    sensitive = ['idCard', 'phone', 'cookie', 'apiKey', 'password']
    for s in sensitive:
        if s in c and 'Encrypted' not in c:
            print(f"⚠️ {java_path}: 敏感字段 {s} 可能未加密")

def check_error_code(java_path):
    """检查错误码是否 1500-1504"""
    with open(java_path) as f:
        c = f.read()
    if 'throw new RuntimeException' in c:
        print(f"❌ {java_path}: 不允许 RuntimeException")
    if 'throw new Exception' in c and 'BusinessException' not in c:
        print(f"⚠️ {java_path}: 建议用 BusinessException")
```

### 3.3 CI 集成

```yaml
# .github/workflows/ci.yml
name: CI

on: [pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # 1. 自动构建
      - name: Build
        run: mvn clean compile

      # 2. 单元测试 + 覆盖率
      - name: Test
        run: mvn test
      - name: Coverage
        run: mvn jacoco:report
      - name: Check Coverage >= 80%
        run: |
          if [ $(jq '.totalLineCoverage' target/site/jacoco/jacoco.json) -lt 80 ]; then
            echo "Coverage < 80%"
            exit 1
          fi

      # 3. 5 大铁律扫描
      - name: 5 Rules Scan
        run: python scripts/audit/check_5_rules.py

      # 4. 字段一致性
      - name: Field Consistency
        run: python scripts/audit/check_field_consistency.py

      # 5. 字典使用
      - name: Dict Check
        run: python scripts/audit/check_dicts.py
```

---

## 4. Pilot 抽检机制

### 4.1 目的

每迭代抽检 1 个 Slice，用**手工方式**完整走查 5 文档 → 代码的一致性，发现自动化扫描遗漏的问题。

### 4.2 抽检流程

```
1. 选 1 个 Slice（建议覆盖不同模块）
2. 完整阅读 5 文档（PRD/UX/API/STATE/SLICES）
3. 对比代码与文档字段、逻辑、错误码
4. 执行 F+P+E 用例
5. 写 Pilot 报告（参考已有 7 个 Pilot 模板）
6. 问题反馈给开发者
```

### 4.3 抽检清单

| 检查项 | 评分 |
|--------|------|
| 字段名与 API 一致 | 100% |
| 字典使用与文档一致 | 100% |
| 错误码使用正确 | 100% |
| 选择器使用正确 | 100% |
| 多租户隔离 | 100% |
| 加密字段处理 | 100% |
| 状态机完整 | 100% |
| F+P+E 用例通过 | 100% |

---

## 5. 故障处理

### 5.1 阻塞 PR

如审查发现严重问题：

```markdown
# ❌ 阻塞原因

## 1. 字段不一致
- API 定义 `realName`（小驼峰）
- DO 字段为 `RealName`（大驼峰）
- 文件：cn.iocoder.yudao.module.oa.dal.dataobject.RealnameDO:23

## 2. 缺 @InDict
- `status` 字段无 @InDict
- 文件：cn.iocoder.yudao.module.oa.api.dto.RealnameCreateReq:18

## 3. 选择器误用
- 前端 RealnameSelect 用了 input 组件
- 文件：src/views/oa/internal/realname/Form.vue:42

## 4. 错误码错误
- 用了 503，应为 1501
- 文件：cn.iocoder.yudao.module.oa.service.RealnameServiceImpl:67

## 修改后重新提交
```

### 5.2 紧急修复

如生产环境紧急问题：

```bash
# 1. 创建 hotfix 分支
git checkout -b hotfix/realname-null-pointer main

# 2. 修复
# （修复代码）

# 3. 加测试
# （加回归测试）

# 4. 提交
git commit -m "fix(realname): NPE when realname not found"

# 5. 合并 + 部署
```

---

## 6. 总结

| 维度 | 数据 |
|------|------|
| 质量门控 | 3 级（Slice/迭代/阶段）|
| 5 大铁律 | 100% 自动化扫描 |
| 9 项检查 | 80% 自动化 + 20% 人工 |
| Pilot 抽检 | 1 个/迭代 |
| CI 集成 | 5 分钟内反馈 |
| 阻塞处理 | 24 小时内澄清 |

**核心原则**：
1. ✅ **5 大铁律不可妥协** —— 违反即退
2. ✅ **自动化扫描 + 人工审查** —— 双保险
3. ✅ **阻塞即停** —— 不修不让过
4. ✅ **Pilot 抽检** —— 防止漏网

---

## 附录

- [DEV-PLAN.md](./DEV-PLAN.md) - 开发计划
- [AI-IMPL-GUIDE.md](./AI-IMPL-GUIDE.md) - AI 实现规范
- [GLOBAL-CONVENTIONS.md](./GLOBAL-CONVENTIONS.md) - 5 大铁律
- [TECH-CONSTRAINTS.md](./TECH-CONSTRAINTS.md) - 技术栈
- [../../pilot/](../../pilot/) - 7 个 Pilot 报告
