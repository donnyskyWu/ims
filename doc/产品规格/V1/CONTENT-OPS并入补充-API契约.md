# CONTENT - OPS 并入补充 API 契约

> **双边契约边界（方案甲 · 2026-10-05 拍板）**：本契约**只行使「范围权」**，**不定义字段**。
> | 契约 | 权限 | 裁定什么 |
> |------|------|----------|
> | 《CONTENT-OPS并入补充-API契约》（本文） | **范围权** | **端点范围与 OPS 主路径清单**——OPS 主路径端点、IMS-only 端点、OPS 现网对照、附件上传范围 |
> | 《CONTENT-内容生产-API契约》 | **字段权** | **所有端点的字段级 SSOT**——请求/响应 DTO、校验、状态机、错误码 |
>
> **裁决规则**：**「端点是否在范围内 / 是否属 OPS 主路径」→ 查本文；「端点字段长什么样」→ 查主契约**。本文出现的任何字段/参数描述**仅为索引**，字段冲突**一律以主契约为准**。

> **2026-10-01 SSOT 裁决**：**运行时前缀**统一为 **`/admin-api/ims/content/**`**（IMS 重写表与 BFF，**非** 网关 1:1 暴露 OPS 进程）。
> **参考（非 runtime）**：现网 OPS `/admin-api/oa/*`、`/admin-api/ops/content/*` 及 `docs/product/PRD-M2-*` — **仅 UX/行为/迁移对照**，禁止新代码直连 OPS HTTP。
> 共享库读：ADR-001 允许处仍可读 `oa_*`；**写** 走 IMS 表 + IMS API。

## 与主契约关系

| 来源 | 用途 |
|------|------|
| 《CONTENT-内容生产-API契约.md》§1/§2 | **字段级 SSOT**（请求/响应 DTO）——**唯一字段权威** |
| 本文 | **OPS 主路径端点清单（范围权）**；本文不定义字段，冲突 **以主契约为准** |

**仍 TBD（不发明字段）**：工作任务矩阵 bulk 确认分页上限、审核多级会签回调细节 — 切片 Checklist 登记。

### OPS 主路径端点清单（与 IMS 映射一致）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET/POST/PUT | `/admin-api/ims/content/sop` | SOP 模板 |
| 2 | GET/POST | `/admin-api/ims/content/plan` | 计划 |
| 3 | GET | `/admin-api/ims/content/task/page` | 任务分页（我的/全部） |
| 4 | GET | `/admin-api/ims/content/task/{id}/execute` | 任务执行页 VO（P-M2-012） |
| 5 | POST | `/admin-api/ims/content/task/{id}/execute/save` | 保存执行页（deliverables、userAttachments） |
| 6 | POST | `/admin-api/ims/content/task/{id}/execute/complete` | 执行页完成（门禁同 #7） |
| 7 | PUT | `/admin-api/ims/content/task/{id}/complete` | 列表侧完成（门禁 ADR-079） |
| 8 | GET/POST | `/admin-api/ims/content/work-task/sheet` | 工作任务表 |
| 9 | POST | `/admin-api/ims/content/work-task/{id}/confirm` | 确认登记 |
| 10 | POST | `/admin-api/ims/content/work-task/{id}/withdraw` | 撤回 |
| 11 | GET/POST/PUT | `/admin-api/ims/content` | 内容 CRUD（含 matchScheme 字段 · amphipoda 增量） |
| 12 | POST | `/admin-api/ims/content/{id}/submit-review` | 提审 |
| 13 | POST | `/admin-api/ims/content/{id}/retry-ai-generate` | 重试 jingcai |
| 14 | POST | `/admin-api/ims/content/{id}/typeset/preview` | AI 排版预览 |
| 15 | POST | `/admin-api/ims/content/{id}/typeset/apply` | 套用 |
| 16 | DELETE | `/admin-api/ims/content/{id}` | 逻辑删 + WebAPI 同步 |
| 17 | GET | `/admin-api/ims/content/{id}/fb-sync` | 同步状态 |
| 18 | POST | `/admin-api/ims/content/file/upload` | 通用上传（见 §附件上传） |
| 19 | GET/PUT | `/admin-api/ims/content/review/*` | 审核队列/结论（与主契约 §2.5 合并） |
| 20 | GET/POST/PUT | `/admin-api/ims/content/layout-template/*` | 公推模板库 |

错误码：内容域 **1500～1504**（全局关联/校验/租户）；模块 **1051～1060**；Football **1271/1272** 记 outbox；删除 **1058** 已上架有订单则改为下架。

---

## OPS → IMS 契约对照（runtime SSOT = IMS）

> **权限**：IMS 菜单 seed 使用 `ims:content:*`；切流期可与 OPS `oa:content:*` 等效绑定（`docs/engineering/OPS-RBAC-DATA-SCOPE.md` · SYS-003 对账）。下表「IMS 权限」为 canonical。

| OPS 参考路径（非 runtime） | IMS canonical 路径 | IMS 权限（示例） | 备注 |
|---------------------------|---------------------|------------------|------|
| `GET /admin-api/oa/sop/template/list` 等 | `/admin-api/ims/content/sop/*` | `ims:content:sop:list` / `:create` | 与主契约 SOP #1～6 **路径不同**，DTO 以主契约为准 |
| `GET /admin-api/oa/plan/*` | `/admin-api/ims/content/plan/*` | `ims:content:plan:list` | |
| `GET /admin-api/oa/task/list` · `my-tasks` | `GET /admin-api/ims/content/task/page` | `ims:content:task:list` | 查询参数 camelCase |
| `GET /admin-api/oa/task/{id}/execute` | `GET /admin-api/ims/content/task/{id}/execute` | `ims:content:task:execute` | TaskExecuteVO · API-M2 §2.6 |
| `POST …/execute/save` · `execute/complete` | 同左 IMS 前缀 | `ims:content:task:execute` | |
| `POST /admin-api/oa/task/{id}/execute/upload`（迁移分析） | `POST /admin-api/ims/content/file/upload` + save 绑定 | `ims:content:task:execute` | BLK-M2-007 关闭 · 见下节 |
| `PUT /admin-api/oa/task/{id}/complete` | `PUT /admin-api/ims/content/task/{id}/complete` | `ims:content:task:complete` | ADR-079 |
| `GET/POST /admin-api/oa/work-task/*` | `/admin-api/ims/content/work-task/*` | `ims:content:work-task:list` | |
| `GET/POST/PUT /admin-api/ops/content/*` | `/admin-api/ims/content` | `ims:content:list` / `:create` / `:update` | matchScheme 字段见 amphipoda API 增量 |
| `POST /ops/content/{id}/submit-review` | `POST /admin-api/ims/content/{id}/submit-review` | `ims:content:submit-review` | |
| `POST …/typeset/preview` · `apply` | 同左 IMS 前缀 | `ims:content:typeset` | 兼容 `oa:content:typeset` |
| `GET /admin-api/oa/content/review/*` | `/admin-api/ims/content/review/*` | `ims:content:review:list` | 与主契约 #27～29 **合并实现** |
| `GET/POST /admin-api/oa/layout-template/*` | `/admin-api/ims/content/layout-template/*` | `ims:content:layout-template:list` | |
| `POST /admin-api/oa/file/upload` | 内容图：**同上 #18** 或 infra 直传 | `ims:content:file:upload` | 终态不走 OPS 本地盘 |
| — | **见《CONTENT-内容生产-API契约》§1 共 36 端点** | 见各接口 | **IMS-only**，无 OPS 1:1 |

**IMS-only（主契约保留，不删）**：选题 `/content/topic/*`、脚本 `/content/script/*`、ComfyUI `/content/ai-production/*` · `/content/ai-job/*`、发布归档 `/content/publish/*` — OPS M2 主路径 **不出菜单**，切片独立 Gate。

---

## §附件上传（关闭 BLK-M2-007 · 产品规格）

> **依据**：UX-M2 §4.3 附件区 · PRD-M2 §4.2.5.1 · 现网 `POST /admin-api/infra/file/upload`（`docs/delivery/OPS-FOOTBALL-FULL-MERGE-RPC-ANALYSIS.md`，**仅行为对照，非 runtime**）· IMS `FileUpload`（《全局开发规范》§6.1/§6.3）· CERT 上传形态（服务端上传 `fileKey` 回执）。

**大小限制**：OPS 任务附件 **无单独 SSOT** → **沿用平台统一上传，规格不新造上限**（由 `FileUpload.maxSize` 与 `scene` 默认值约束，不在 CONTENT 契约写 MB）。

### POST `/admin-api/ims/content/file/upload`

| 项 | 说明 |
|----|------|
| Content-Type | `multipart/form-data` |
| 字段 `file` | 必填，二进制 |
| 字段 `scene` | `task_execute_attachment` \| `content_image` \| `deliverable`（默认 `task_execute_attachment`） |
| 权限 | `@PreAuthorize('ims:content:file:upload')`（切流期可兼 `oa:content:list`） |
| 实现 | **IMS Go 服务端**直接落 `ims.file.storage.root`（《全局开发规范》§6.3）；回执 `fileKey`（服务端相对路径）+ `fileUrl`（IMS 鉴权下载链）。**本期不上对象存储**——**禁止**调用 OPS/infra 上传、**禁止** OSS 直传凭证模式、**禁止**写 OPS 本地盘 |
| 响应 `data` | `{ fileKey: string; fileUrl: string; fileName: string; sizeBytes: number }` |

### 绑定任务执行节点

| 步骤 | API |
|------|-----|
| 1 上传 | `POST …/file/upload` → 得 `fileKey` |
| 2 绑定 | `POST /admin-api/ims/content/task/{taskId}/execute/save` body 增量：`userAttachments: [{ fileKey, fileName }]` |
| 只读 | `GET …/task/{id}/execute` → `userAttachments[]` 与 SOP `attachments[]`（预置参考）**分开展示** |

内容编辑内嵌图片：同 #18 `scene=content_image`，保存内容时写 `layout_html` / 媒体字段（不重复发明 `/oa/file/upload` 路径）。

**Slice 待办（非产品阻塞）**：`oa_task` 或附属表持久化 `userAttachments` 的 Flyway 表名 — 实现 Slice 与 DATA 文档对齐，**不在本契约发明列名**。

---

## OPS 前后端对照索引（2026-10-02）

> 字段级 SSOT 仍为上表 IMS canonical；下列为 **现网 OPS HTTP**（`#/api/ops/*` → `/admin-api/ops/*`），供迁移验收与 ADR-IMS-003 走查。

| 域 | Java Controller（`…/controller/`） | 前端 API 模块 | 代表端点 |
|----|-----------------------------------|---------------|----------|
| SOP | `sop/SopTemplateController` · `SopNodeController` | `sop.ts` | `/ops/sop/template/*` · `/ops/sop/node/*` |
| 计划 | `plan/ContentPlanController` | `plan.ts` | `/ops/plan/list` · `create` · `update` |
| 任务 | `task/TaskController` | `task.ts` | `/ops/task/list` · `my-tasks` · `/{id}/execute` · `execute/save` · `execute/complete` |
| 工作任务 | `worktask/WorkTaskController` | `workTask.ts` | `/ops/work-task/sheet/*` · `/matrix` |
| 内容 | `content/ProductionContentController` | `content.ts` | `/ops/content/list` · `create` · `update` · `/{id}/submit-review` · `shelf-on/off` · `publish-draft` · `formal-publish` |
| AI 内容 | `aicontent/AiContentController` | `aiContent.ts` · `content.ts` | `/ops/content/ai-generate` · `/ops/ai-content/generate` |
| 模板 | `layout/LayoutTemplateController` | `layoutTemplate.ts` | `/ops/layout-template/*` |

Vue 页面映射见《CONTENT-OPS并入补充-页面规格.md》§OPS 前后端对照。
