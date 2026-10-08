# CHECKLIST-IMS-BI — 数据报表

- [x] 路由与 PRD §17 一致（W9-6：`biList` → `/ims/bi/report/list` · `bi0Report` 已接）
- [x] API 契约对齐（W9-6 首片：`GET/POST /bi/report/list` · `GET /bi/report/categories`）
- [x] tenant_id + ADR-056（`ims_bi_report_def` · B9 creator 轴）
- [x] P0: `GET /bi/report/{code}` 标准预览（W9-5）；报表目录 CRUD 首片 POST+list
- [x] W9-8：`biDesign` 隐藏路由 `/ims/bi/report/designer` · `GET /bi/report/datasets` · `GET/PUT /bi/report/{id}` · `POST …/publish` · `POST /bi/report/query` 首片
- [x] W9-9：`bi0Analysis` `/ims/bi/analysis` · `POST /bi/metric/analysis/run` 首片
- [x] W9-10：`biShare` 隐藏路由 `/ims/bi/report/subscribe` · `GET/POST /bi/subscribe/*` · 分享链接/发布管理 Tab 首片
- [x] W9-10：`biPreview` `/ims/bi/report/preview` · `POST /bi/report/preview/run|drill` 首片
