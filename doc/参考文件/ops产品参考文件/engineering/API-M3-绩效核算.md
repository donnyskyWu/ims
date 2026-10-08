# API-M3-绩效核算

> **版本**：v1.1 | 2026-06-07 | 2026-10-02
> **关联 PRD**：[`PRD-M3-绩效核算.md`](../product/PRD-M3-绩效核算.md)
> **关联 UX**：[`UX-M3-绩效核算.md`](../product/UX-M3-绩效核算.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 考核模板 API

### 1.1 GET `/admin-api/ops/perf/template/list`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| position | String | ❌ | `dict_position` |
| isActive | Integer | ❌ | `dict_yes_no` |
| pageNum | Integer | ❌ | - |

**响应**：

```json
{
  "id": 1,
  "position": "OPS_LEADER",
  "positionLabel": "运营组长",
  "templateName": "运营组长考核-2026",
  "isActive": 1,
  "itemCount": 5
}
```

### 1.2 POST `/admin-api/ops/perf/template/create`

**请求体**：

```json
{
  "position": "OPS_LEADER",
  "templateName": "运营组长考核-2026",
  "isActive": 1,
  "items": [
    {
      "metricId": 101,
      "weight": 40.00,
      "calcRule": "AUTO",
      "scoreStandard": {
        "ranges": [
          {"min": 0, "max": 60, "score": 0, "grade": "D"},
          {"min": 60, "max": 75, "score": 60, "grade": "C"},
          {"min": 75, "max": 85, "score": 75, "grade": "B"},
          {"min": 85, "max": 95, "score": 85, "grade": "A"},
          {"min": 95, "max": 9999, "score": 100, "grade": "S"}
        ]
      }
    }
  ]
}
```

**校验**：
- `position` `@InDict(type="dict_position")`
- 权重合计 = 100%
- 区间无重叠 + 无 gap
- 同岗位 isActive 互斥（启用新模板自动停用旧）

### 1.3 PUT `/admin-api/ops/perf/template/update`

同 create + `id`。

### 1.4 POST `/admin-api/ops/perf/template/activate`

**请求体**：

```json
{"id": 1}
```

**业务**：
- 同岗位其他模板 `is_active=0`
- 本模板 `is_active=1`

### 1.5 GET `/admin-api/ops/perf/template/{id}/items`

**响应**：

```json
{
  "items": [
    {
      "id": 1,
      "metricId": 101,
      "metricName": "推文发布数",
      "weight": 40.00,
      "calcRule": "AUTO",
      "scoreStandard": {...}
    }
  ]
}
```

---

## 2. 考核执行 API

### 2.1 GET `/admin-api/ops/perf/record/list`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| ipGroupId | Long | ❌ | - |
| targetUserId | Long | ❌ | - |
| periodType | String | ❌ | `dict_perf_period` |
| status | String | ❌ | `dict_perf_status` |

### 2.2 POST `/admin-api/ops/perf/record/create`

**请求体**：

```json
{
  "targetUserId": 123,
  "periodType": "MONTH",
  "periodStart": "2026-06-01",
  "periodEnd": "2026-06-30"
}
```

**校验**：
- `targetUserId` 必须存在 + 启用
- 同周期内已有记录 → 拒绝（错误码 2008）
- 自动按 `targetUser.position` 匹配模板

### 2.3 POST `/admin-api/ops/perf/record/calculate`

**请求体**：

```json
{"recordId": 1}
```

**业务**：
- 拉取指标数据
- 按 `score_standard` 算分
- 写入 `oa_perf_item_record`

### 2.4 PUT `/admin-api/ops/perf/record/adjust`

**请求体**：

```json
{
  "itemRecordId": 100,
  "manualAdjustment": 5.0,
  "remark": "工作努力"
}
```

**校验**：
- `|manual_adjustment| / |score| <= 20%`（错误码 2009）
- 状态必须 = DRAFT

### 2.5 GET `/admin-api/ops/perf/record/detail?id=xxx`

**响应**：

```json
{
  "id": 1,
  "targetUserId": 1003,
  "templateId": 9512,
  "targetUserName": "张三",
  "templateName": "SEED-运营专员考核-2026",
  "position": "OPERATOR",
  "periodType": "MONTH",
  "periodStart": "2026-06-01",
  "periodEnd": "2026-06-30",
  "totalScore": 85.5,
  "baseScore": 60,
  "maxScore": 100,
  "grade": "A",
  "status": "CONFIRMED",
  "workflowStatus": 3,
  "submittedAt": "2026-06-01 10:00:00",
  "publishedAt": "2026-06-02 15:30:00",
  "reviewer1": "oa-leader / 2026-06-02 15:30:00",
  "reviewer2": "HR复核 / 2026-06-02 15:30:00",
  "items": [
    {
      "metricName": "推文发布数",
      "metricCode": "POST_COUNT",
      "weight": 40,
      "metricValue": 50,
      "actualValue": 50,
      "target": 9999,
      "score": 80,
      "manualAdjustment": 5,
      "finalScore": 85
    }
  ]
}
```

> **S-R27a**：`workflowStatus` / 审批流时间由 `status` + `create_time` / `update_time` 推导（无独立审批表）。

### 2.6 POST `/admin-api/ops/perf/record/confirm`

**业务**：
- 状态：DRAFT → CONFIRMED
- 锁定记录，不可调整

---

## 3. 绩效结果 API

### 3.1 GET `/admin-api/ops/perf/result/list`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| userId | Long | ❌ | - |
| periodType | String | ❌ | `dict_perf_period` |
| grade | String | ❌ | `dict_perf_grade`（V34：S/A/B/C/D） |
| startDate | Date | ❌ | - |

**权限**：
- 员工：自动注入 `userId = 当前用户`
- 部门负责人：自动注入 `dept_id = 本部门`
- 管理员/财务：全部

### 3.2 GET `/admin-api/ops/perf/result/{userId}/trend`

**请求参数**：

| 参数 | 类型 | 必填 |
|------|------|------|
| month | Integer | ❌ | 默认 6 |

**响应**：

```json
{
  "userId": 1003,
  "userName": "运营专员",
  "position": "OPERATOR",
  "dept": "SEED-八卦一组",
  "joinAt": "2026-01-01",
  "userInfo": {
    "id": 1003,
    "name": "运营专员",
    "position": "OPERATOR",
    "dept": "SEED-八卦一组",
    "joinAt": "2026-01-01"
  },
  "trends": [
    {
      "period": "2026-05",
      "totalScore": 75,
      "score": 75,
      "grade": "B",
      "templateName": "SEED-运营专员考核-2026",
      "baseScore": 60,
      "metricScore": 75,
      "bonusScore": -5,
      "status": "已发布"
    }
  ],
  "points": []
}
```

> `points` 与 `trends` 内容相同，兼容前端 `res.points || res.historyList`。

### 3.3 POST `/admin-api/ops/perf/result/export`

**请求体**：

```json
{
  "ids": [1, 2, 3]
}
```

**响应**：Excel 文件流

---

## 4. 订单归因 API

### 4.1 GET `/admin-api/ops/order-attribution/list`

**请求参数**：

| 参数 | 类型 | 必填 | 字典 |
|------|------|------|------|
| ipGroupId | Long | ❌ | - |
| accountId | Long | ❌ | - |
| startDate | Date | ✅ | - |
| endDate | Date | ✅ | - |

### 4.2 GET `/admin-api/ops/order-attribution/roi`

**请求参数**：同上

**响应**：

```json
{
  "totalPayAmount": 1000000.00,
  "totalInCost": 238000.00,
  "roi": 4.20,
  "byIpGroup": [
    {"ipGroupId": 1, "ipGroupName": "八卦一组", "payAmount": 500000, "inCost": 100000, "roi": 5.00}
  ]
}
```

### 4.3 POST `/admin-api/ops/order-attribution/export`

---

## 5. 错误码

| 错误码 | 含义 |
|--------|------|
| 1500~1504 | 全局关联错误（见 GLOBAL-CONVENTIONS） |
| 2008 | 周期内已有考核 |
| 2009 | 人工调整幅度超过 ±20% |
| 2010 | 权重合计不等于 100% |
| 2011 | 区间存在 gap |
| 2012 | 区间重叠 |
| 2013 | 岗位无可用模板 |

---

*下一步：STATE / SLICES / CHECKLIST / TESTCASES。*
