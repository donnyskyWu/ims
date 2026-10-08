# API-M2 · 知识库

> **状态**：草案（S-R1 2026-06-09 产出，Phase 2 完善）
> **依据**：[ADR-007](../adr/ADR-007-M2知识库最小可用实现与遗留.md)
> **对应前端**：`ops-platform-ui-vue/src/views/production/knowledge/`

## 模块边界

M2 知识库存储团队 SOP、案例库、模板库、行业资料、运营经验，**只读给全员**、**CRUD 限定角色**（GATE-S2 鉴权矩阵）。

## 数据对象 `oa_knowledge_base`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Long | ✅ | 主键 |
| `tenant_id` | Long | ✅ | 租户隔离 |
| `title` | String(100) | ✅ | 标题 |
| `content` | Text | - | 富文本内容（HTML） |
| `category` | String(32) | - | 字典 `dict_knowledge_category`（case/template/industry/experience） |
| `tags` | String(500) | - | 标签，**逗号分隔**（S-R2 改 JSON 或关联表） |
| `is_public` | TINYINT | - | 0/1，默认 1 |
| `status` | TINYINT | - | 0/1，默认 1 |
| `creator` | String(64) | ✅ | 创建人 username |
| `create_time` / `update_time` | LocalDateTime | ✅ | 审计 |

**S-R1 妥协**（无 DB 字段，VO 固定返 0 / 前端本地维护）：
- `viewCount`：固定 0（S-R2 加 `oa_knowledge_view`）
- `likeCount`：固定 0（S-R2 加 `oa_knowledge_like`）
- `isLiked`：固定 false（S-R2 按当前 userId 判断）

## 端点

### 1. GET `/admin-api/ops/knowledge/list`

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `title` | String | - | - | 标题模糊搜索 |
| `category` | String | - | - | 字典值 |
| `pageNum` | Integer | - | 1 | 页码 |
| `pageSize` | Integer | - | 20 | 每页条数 |

**响应**：`PageResult<KnowledgeVO>`（VO 见上）

### 2. GET `/admin-api/ops/knowledge/{id}`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 路径 `id` | Long | ✅ | 知识 ID |

**响应**：`KnowledgeVO`（含 `content` 字段）

**错误**：1500 实体不存在

### 3. POST `/admin-api/ops/knowledge/create`

**请求体** `KnowledgeCreateReq`：

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| `title` | String | ✅ | `@NotBlank @Size(max=100)` |
| `category` | String | - | `@InDict("dict_knowledge_category")` |
| `content` | String | - | - |
| `tags` | String | - | - |
| `isPublic` | Integer | - | 0/1，默认 1 |

**响应**：`Long`（新 ID）

### 4. PUT `/admin-api/ops/knowledge/update`

**请求体** `KnowledgeUpdateReq`：同 create + `id` 必填

**响应**：`Boolean`

### 5. DELETE `/admin-api/ops/knowledge/delete?id={id}`

**响应**：`Boolean`

### 6. POST `/admin-api/ops/knowledge/like`

**请求体** `KnowledgeLikeReq`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Long | ✅ | 知识 ID |
| `action` | String | ✅ | `like` / `unlike` |

**S-R1 行为**：仅触发 `update_time` 更新（占位），S-R2 加 `oa_knowledge_like` 持久化

**响应**：`Boolean`

## 鉴权

- 列表 / 详情：所有登录用户可读
- 新增 / 编辑 / 删除：需 `oa:knowledge:write` 权限（**Phase 2 完善，当前 dev 模式 admin 全通过**）
- 收藏：所有登录用户

## 错误码

- 1500 ENTITY_NOT_EXISTS — 知识 ID 不存在
- 1503 DICT_VALUE_INVALID — category 字典值非法
- 1500 BAD_REQUEST — like action 非法值

## Phase 2 待办

- [ ] `oa_knowledge_tag` 关联表（替代 `tags String`）
- [ ] `oa_knowledge_view` 统计表
- [ ] `oa_knowledge_like` 收藏表（user_id + knowledge_id unique）
- [ ] `oa:knowledge:write` 权限矩阵细化
- [ ] 内容审核流程（参考 ProductionContent 三审机制）
