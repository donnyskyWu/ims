# API-M11-字典管理

> **版本**：v1.1 | 2026-06-09 | 2026-10-02
> **关联 ADR**：[`ADR-006-字典查询端点与作者类型扩展.md`](../adr/ADR-006-字典查询端点与作者类型扩展.md)
> **关联全局规范**：[`GLOBAL-CONVENTIONS.md`](./GLOBAL-CONVENTIONS.md)

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 概述

字典查询为横切能力，M0–M9 任意页面中 `<DictSelect dict-type="xxx" />` 渲染均依赖此端点。

| 项 | 值 |
|----|----|
| 控制器 | `DictController` |
| 基础路径 | `/admin-api/ops/dict` |
| 鉴权 | DevAuthFilter（ADR-003） |
| 权限 | 已认证用户即可（不下放到匿名） |
| 租户 | 不区分租户（字典为公共主数据） |
| 缓存 | 本地 Caffeine 5 分钟（key=`dict:type`） |

---

## 2. 接口

### 2.1 GET `/admin-api/ops/dict/data`

**用途**：根据 `type` 查询字典项列表。

**入参**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | String | ✅ | 字典 type（对应 `sys_dict_type.type`） |

**出参**（HTTP 200）：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "list": [
      { "dictType": "dict_author_type", "label": "直播", "value": "LIVE", "sort": 0, "status": "ENABLED" },
      { "dictType": "dict_author_type", "label": "短视频", "value": "SHORT_VIDEO", "sort": 1, "status": "ENABLED" },
      { "dictType": "dict_author_type", "label": "图文", "value": "ARTICLE", "sort": 2, "status": "ENABLED" },
      { "dictType": "dict_author_type", "label": "直播+短视频", "value": "BOTH", "sort": 3, "status": "ENABLED" }
    ],
    "total": 4
  }
}
```

**错误码**：

| code | 含义 | 场景 |
|------|------|------|
| 401 | 未登录 | DevAuthFilter 拦截 |
| 1500 | 业务校验失败 | `type` 缺失 / 长度超 64 |
| 1501 | 实体不存在 | `type` 在 `sys_dict_type` 中不存在 |
| 2006 | 系统错误 | DB 异常 |

**排序**：`sort ASC, value ASC`。

**状态过滤**：仅返回 `status='ENABLED'`。

---

### 2.2 GET `/admin-api/ops/dict/types`（辅助）

**用途**：列出所有可用字典 type（用于前端"字典管理"页面或调试）。

**出参**：

```json
{
  "code": 0,
  "data": {
    "list": [
      { "type": "dict_author_type", "name": "作者类型", "status": "ENABLED" },
      { "type": "dict_ip_group_type", "name": "IP组类型", "status": "ENABLED" },
      { "type": "dict_ip_group_level", "name": "IP组等级", "status": "ENABLED" }
    ],
    "total": 27
  }
}
```

---

## 3. 数据模型

### 3.1 `sys_dict_type`（已存在，V1 baseline）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT PK | - |
| `type` | VARCHAR(64) UK | 字典 type 编码 |
| `name` | VARCHAR(128) | 字典中文名 |
| `status` | VARCHAR(16) | ENABLED / DISABLED |
| `tenant_id` | BIGINT | 占位（字典本身公共，但表结构带） |

### 3.2 `sys_dict_data`（已存在，V1 baseline）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT PK | - |
| `dict_type` | VARCHAR(64) | 关联 `sys_dict_type.type` |
| `label` | VARCHAR(128) | 中文标签（前端展示） |
| `dict_value` | VARCHAR(128) | 字典值（业务代码使用） |
| `sort` | INT | 排序 |
| `status` | VARCHAR(16) | ENABLED / DISABLED |

### 3.3 `DictDataRespVO`（新增）

```java
@Data
public class DictDataRespVO {
    private String dictType;
    private String label;
    private String value;       // 对应 dict_value
    private Integer sort;
    private String status;
}
```

---

## 4. 业务规则

- **铁律二**：`@InDict("dict_xxx")` 注解是**写入校验**（POST/PUT），本接口是**读取**，互不替代。
- 字典值变更（增/删/改）通过 **Flyway 迁移** 落地，**不开放管理端 API**（本期 Phase 2 再做）。
- 缓存键：`dict:data:{type}`，TTL=5 分钟；命中即返回。
- 不区分租户，但**强制登录**（铁律三）。

---

## 5. IT 用例（P0 必过）

| # | 用例 | 期望 |
|---|------|------|
| 1 | `GET /dict/data?type=dict_author_type` 含 4 项：`LIVE / SHORT_VIDEO / ARTICLE / BOTH` | 200 + list.length=4 |
| 2 | `GET /dict/data` 缺 `type` | 1500 |
| 3 | `GET /dict/data?type=dict_not_exist` | 1501 |
| 4 | `GET /dict/data?type=dict_author_type` 无 token | 401 |
| 5 | `GET /dict/types` 含 `dict_author_type / dict_ip_group_type / dict_ip_group_level / dict_content_length_type / ...` | 200 + 29 项 |
| 6 | 重复调用 `dict:data:dict_author_type` 第二次应命中缓存 | DB query count 不增加 |

---

## 6. 前端组件

```ts
// ops-platform-ui-vue/src/components/DictSelect.vue
<template>
  <el-select v-model="model" :placeholder="`请选择${label}`">
    <el-option v-for="o in options" :key="o.value" :label="o.label" :value="o.value" />
  </el-select>
</template>
```

```ts
// ops-platform-ui-vue/src/api/dict.ts
export function fetchDictData(type: string) {
  return request.get<{ list: DictItemVO[]; total: number }>({
    url: '/oa/dict/data',
    params: { type }
  })
}

export function fetchDictTypes() {
  return request.get({ url: '/oa/dict/types' })
}
```

---

## 7. 关联模块

- M1 / M2 / M3 / M4 / M5 / M6 / M8 / M9 全部使用
- 已存在字典 type 29 项（含 V128 `dict_ip_group_level`、V134 `dict_content_length_type`）
