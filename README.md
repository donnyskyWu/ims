# IMS（神鱼体育 · 一体化管理系统）

Python FastAPI 后端 + Vue 前端 · 本地 MySQL · Playwright E2E。

## 协同开发

团队共用进度与验收 SSOT（克隆后请先读）：

| 文档 | 说明 |
|------|------|
| [IMS-任务进度计划表](doc/开发方案/IMS-任务进度计划表.md) | 全局 **#** 看板（**#57/#58** 已完成；**#59** = FIN 结账 LOCKED + 锁后更正，开发完成/待 UAT；**#60** = S4 流转/1021，进行中） |
| [IMS-PRD功能点执行对照表](doc/开发方案/IMS-PRD功能点执行对照表.md) | 功能矩阵 · **UAT 建议 / UAT 状态** |
| [IMS-Agent交付循环](doc/开发规范/IMS-Agent交付循环.md) | 开发 → pytest → E2E → 文档 → PO UAT 门禁 |
| [云 MySQL 联调](doc/运维/云MySQL联调.md) | 可选云库 · `IMS_USE_CLOUD_DB` / `sync_ims_to_cloud.ps1` |
| [E2E 说明](ims-web/e2e/README.md) | closure / smoke · 一键 `npm run test:e2e:ci` |

### 本地联调端口

- **API**：`http://127.0.0.1:18080`（`ims-backend/scripts/start_api.ps1`）
- **Web**：`http://127.0.0.1:6173`（Vite；E2E 默认 `E2E_BASE_URL`）

### 环境

- 复制 `ims-backend/.env.example` → `ims-backend/.env`（**勿提交**；钉钉/L3/云库密钥仅本地或 CI secret）。
- 初始化库：`ims-backend/scripts/init_ims_db.ps1`

### 验收口径

- **Smoke** ≠ PO 签收；**closure** + 全量 E2E PASS + 对照表 **UAT 状态=通过** → **已验收**（见 [`.cursor/rules/ims-delivery.mdc`](.cursor/rules/ims-delivery.mdc)）。

更多产品/规格文档：[doc/README.md](doc/README.md)
