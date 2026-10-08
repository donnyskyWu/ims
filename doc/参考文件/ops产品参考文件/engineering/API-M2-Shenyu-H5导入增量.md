# API-M2-内容生产 — Shenyu H5 导入 Profile 增量

> **版本**：v1.1 | 2026-09-09 | 2026-10-02  
> **状态**：**Accepted**（ADR-029 · OQ-M2-013 于 2026-09-09 闭合）  
> **Base Path**：`/admin-api/ops`（Gateway 前缀以环境为准）  
> **关联 ADR**：[ADR-029](../adr/ADR-029-M2-Shenyu-H5导入Profile.md)  
> **Base Spec**：[API-M2-内容生产](./API-M2-内容生产.md) §6.7~§6.10

---


## 0. 路径与实现 SSOT（2026-10-02）

| 项 | 规范 |
|----|------|
| **规范 HTTP 前缀** | `/admin-api/ops/**`（Gateway → `ops-server` · [ADR-058](../adr/ADR-058-OPS后端单仓与football-module-ops命名.md)） |
| **过渡** | 部分环境仍代理 `/admin-api/oa/**`；新 Spec 与 `football-front` `src/api/ops/*.ts` 以 **`/ops/...`** 为准 |
| **Controller 对照** | 本仓库未检出 `football-module-ops` 时，以 [`GAP-INVENTORY.md`](../delivery/e2e-artifacts/P5-MIGRATE-8-cutover/GAP-INVENTORY.md) + 2026-06 [`SPEC-VS-IMPL-报告-20260609.md`](../delivery/SPEC-VS-IMPL-报告-20260609.md) 为机械对照；**未复测**端点标 ⚠️ |
| **Stub / Phase 2** | `/internal/**` 个人账号·三方关联 → [ADR-060](../adr/ADR-060-Phase2-stub-OOS-Accept.md) **Closed-Accept**（DeferredCutoverStub） |

## 1. 概述

在公推模板 **导入 Job** 上增加 **`importProfile`**，并 **文档化 MHTML 导入端点**（产品手册 P-M2-014 已描述，Base API 未单独列出）。

| 变更 | 说明 |
|------|------|
| 新字段 `importProfile` | `@InDict(dict_layout_import_profile)` |
| 新端点 `import-mhtml` | multipart MHTML 文件 → 异步 Job |
| 可选 `re-extract` | 对已有模板 id 重跑提取（迁移 template 12/17） |
| Job 响应扩展 | `extractionReport` 含 profile、warnings |

**不影响**：微信 `import-url`、`import-docx`、`import-paste` 既有契约（仅增可选 `importProfile`）。

---

## 2. 字典

### 2.1 新增 `dict_layout_import_profile`

| value | label | 说明 |
|-------|-------|------|
| `GENERIC_HTML` | 通用 HTML | 默认；现有 generic 提取 |
| `WECHAT_MP_ARTICLE` | 微信公众号文章 | mp.weixin.qq.com |
| `SHENYU_H5_NEWS` | Shenyu H5 资讯详情 | h5.shenyu.com uni-app 资讯页 |

### 2.2 扩展 `dict_layout_template_source`

| value | label |
|-------|-------|
| `MHTML` | MHTML 离线导入 |

Job / 模板 `source_type` 在 MHTML 成功创建时写 **`MHTML`**。

---

## 3. 端点

### 3.1 POST `/admin-api/ops/layout-template/import-mhtml`（新增）

**权限**：`@PreAuthorize("@ss.hasPermission('oa:layout-template:import')")`

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | `.mhtml` / `.mht` |
| `templateName` | String | ❌ | 默认从 `<title>` 或文件名推断 |
| `documentType` | String | ❌ | `@InDict(dict_document_type)` |
| `importProfile` | String | ❌ | 空则服务端推断（ADR-029 §2.2） |
| `overwriteTemplateId` | String | ❌ | 若填，Job 成功后 **更新** 该模板（snowflake 字符串） |

**响应**（同 import-url）：

```json
{
  "jobId": "9002",
  "status": "PENDING"
}
```

**失败**：

| 场景 | 错误码 |
|------|--------|
| 非 MHTML / multipart 解析失败 | **2044** |
| 显式 `importProfile` 非法 | **1503** |
| 文件 > 20MB（待确认） | **1500** |

---

### 3.2 POST `/admin-api/ops/layout-template/import-url`（扩展）

**请求体增量**：

```json
{
  "sourceUrl": "https://h5.shenyu.com/pages/news/detail?id=123",
  "templateName": "神鱼体育-资讯详情",
  "documentType": null,
  "importProfile": "SHENYU_H5_NEWS",
  "overwriteTemplateId": "17"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `importProfile` | String | ❌ | 见 §2.1 |
| `overwriteTemplateId` | String | ❌ | 迁移 re-import |

**MVP 约束（OQ-M2-013-03）**：Shenyu H5 导入 **仅验收 MHTML 路径**。`import-url` 保留 `importProfile` 契约，但 **不**保证 h5 URL 直连成功；失败仍 **2014**，UX 引导上传 MHTML。

---

### 3.3 POST `/admin-api/ops/layout-template/import-paste`（扩展）

**请求体增量**：

```json
{
  "templateName": "粘贴导入",
  "html": "<div class=\"content\">...</div>",
  "importProfile": "SHENYU_H5_NEWS"
}
```

---

### 3.4 POST `/admin-api/ops/layout-template/{id}/re-extract`（新增 · 迁移用）

**权限**：`oa:layout-template:update`

**请求体** `LayoutTemplateReExtractReq`：

```json
{
  "importProfile": "SHENYU_H5_NEWS",
  "sourceType": "MHTML",
  "uploadToken": "temp-file-token-from-upload"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `importProfile` | String | ✅ | 目标 profile |
| `sourceType` | String | ✅ | `MHTML` \| `URL` \| `PASTE` |
| `uploadToken` | String | 条件 | `MHTML` 时必填（预上传临时文件 id） |
| `sourceUrl` | String | 条件 | `URL` 时必填 |
| `html` | String | 条件 | `PASTE` 时必填 |

**业务**：

1. 校验模板 `{id}` 存在、租户一致（**1504**）
2. 异步 Job；成功后 **更新** 该模板的 `layout_schema` / `style_css` / `preview_html` / `schema_version=2`
3. **不**改 `template_name` / `status` / 已引用内容的快照

**响应**：`{ "jobId": "9003", "status": "PENDING" }`

---

### 3.5 GET `/admin-api/ops/layout-template/import-job/{jobId}`（扩展）

**响应** `LayoutImportJobVO` 增量字段：

```json
{
  "id": "9002",
  "status": "SUCCESS",
  "sourceType": "MHTML",
  "importProfile": "SHENYU_H5_NEWS",
  "previewLayoutSchema": { "version": 2, "blocks": [] },
  "previewHtml": "<div class=\"content\">...</div>",
  "extractionReport": {
    "profileUsed": "SHENYU_H5_NEWS",
    "profileRequested": null,
    "profileAutoDetected": true,
    "rootSelector": "div.content",
    "imageFrameCount": 2,
    "styleCssRuleCount": 14,
    "warnings": [
      "SHELL_NODE_REMOVED: zp-paging",
      "TOXIC_STYLE_STRIPPED: display:none"
    ],
    "degraded": false,
    "previousSchemaHash": null
  },
  "suggestedTemplateName": "神鱼体育-资讯详情",
  "errorCode": null,
  "errorMessage": null
}
```

| 字段 | 说明 |
|------|------|
| `importProfile` | 实际使用的 profile |
| `previewLayoutSchema` | ADR-020 v2 schema 预览 |
| `extractionReport` | 提取诊断；`warnings` 非空时 UI 黄色提示 |
| `extractionReport.rootSelector` | 实际命中的 DOM 根（P0~P6 之一，见 ADR-029 §2.3.1） |
| `errorCode` | `FAILED` 时：**2043** / **2044** / **2045** / **2014** 等 |

**Deprecated 说明**：旧字段 `previewLayoutJson` 只读兼容；新 Job 优先写 `previewLayoutSchema`。

---

## 4. 服务端推断伪码

```text
resolveImportProfile(req):
  if req.importProfile != null:
    assertInDict(req.importProfile, dict_layout_import_profile)
    return req.importProfile
  host, path = parseSource(req)  // MHTML Snapshot-Content-Location or sourceUrl
  if host matches (h5|beta.h5).shenyu.com and looksLikeNewsDetail(path, html):
    return SHENYU_H5_NEWS
  if host == mp.weixin.qq.com:
    return WECHAT_MP_ARTICLE
  return GENERIC_HTML
```

---

## 5. 错误码增量

| 错误码 | 常量 | 含义 |
|--------|------|------|
| **2043** | `LAYOUT_IMPORT_PROFILE_ROOT_NOT_FOUND` | Profile 约定 DOM 根未找到 |
| **2044** | `LAYOUT_IMPORT_MHTML_PARSE_FAILED` | MHTML 解析失败 |
| **2045** | `LAYOUT_IMPORT_PROFILE_UNSUPPORTED` | Profile 未实现（预留） |

复用：**1503**（非法 profile）、**1504**（跨租户）、**2016**（Job 不存在）、**2014**（URL 抓取失败）。

---

## 6. 前端（导入向导）增量要点

| 项 | 行为 |
|----|------|
| MHTML 上传 | 调 `import-mhtml`；展示推断的 `importProfile` |
| Profile 覆盖 | 高级选项下拉 `dict_layout_import_profile` |
| 迁移 | 「覆盖已有模板」→ 传 `overwriteTemplateId`（12 / 17） |
| 成功预览 | 展示 `extractionReport.warnings`；image 帧数摘要 |
| 免责声明 | 延续 ADR-020 / PROPOSAL v2 §4.5 骨架声明 |

---

## 7. TESTCASES 索引（S-21b 草案）

| ID | 场景 |
|----|------|
| TC-M2-013-P0-01 | `神鱼体育.mhtml` + 自动推断 → `SHENYU_H5_NEWS` |
| TC-M2-013-P0-02 | image 帧数 = 正文去重图数（≠11） |
| TC-M2-013-P0-03 | `style_css` 非空；schema 无 `display:none` |
| TC-M2-013-P0-04 | 缺 `div.content` → 2043 |
| TC-M2-013-P0-05 | re-extract template 17 → schema 更新、id 不变 |
| TC-M2-013-P0-06 | template 17 + ADR-028 TEMPLATE_GUIDED preview 回归 |

---

*Accepted · 2026-09-09 · ADR-029 Accepted*
