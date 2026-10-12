# CHECKLIST-IMS-AIR — AI资源

> v2.6.32：主导航 **4 叶**（技能库/专家库/**知识库**/模型与提示词）；知识库 In Scope，**本期仅文件管理**（KNOW-003 检索 / KB-001 RAGFlow 底座已移除）。
> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。

- [x] 路由与 PRD §17 一致（W9-7：`airExpert` → `/ims/air/expert`；`skill|kb` 已接）
- [ ] API 契约对齐（管理端 42 路由 + MCP 网关 5 行 · 总 47）
- [ ] tenant_id + ADR-056
- [ ] P0: `GET /air/skill/page`
- [x] W9-7：`airExpert` → `GET /air/expert/page|summary`、`POST /air/expert`、`PUT …/publish`、`GET …/{id}` 组装预览、`POST /air/expert/grant`
- [x] W9-8：`airCfg` → `/ims/air/cfg` · `GET/POST/PUT /air/cfg/model/*` · `GET/POST/PUT /air/cfg/prompt/*`（B9 creator 轴）
- [ ] P0: `GET /air/kb/tree`（库内两级树）+ `GET /air/kb/page`
- [ ] P0: `POST /air/kb` 新建知识库（密级四选 + Provider 固定 LOCAL，IMS 服务端文件目录）
- [ ] P0: `POST /air/kb/doc/upload`（文件，服务端上传回执落 `file_key/file_size/content_type`）/ `doc/import-url`（URL）/ `doc/import-text`（文本）
- [ ] P0: `POST /air/kb/category`、`PUT /air/kb/category/{id}`、`PUT /air/kb/category/sort`、`DELETE /air/kb/category/{id}`（KNOW-005）
- [ ] P0: `GET /air/kb/transfer-source` + `POST /air/kb/doc/import-from`（TRAIN/PERF/CONTENT 按条目转入，source_type/source_ref 溯源）
- [ ] P0: `POST /air/kb/doc/audit`（PENDING→PUBLISHED，审批通过即发布；**无 PARSING 态**）
- [ ] P0: 机密/绝密 BR-027 口径（本期正文不出库，库内链接提示）；检索拦截已移除
- [ ] ~~KNOW-003 知识检索 + KB-001 RAGFlow 底座 + MCP `knowledge.search`/`knowledge.get`~~ **已移除（不做）**
- [ ] Deferred: Key 管理 / 审计监控（`go()` 重定向技能库，不 404）
