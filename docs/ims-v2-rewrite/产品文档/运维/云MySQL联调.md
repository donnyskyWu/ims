# 云 MySQL 联调（开发 / E2E）

## 概览

- **业务库**：云主机 `47.110.62.216:3306`，库名 **`ims`**（utf8mb4）。
- **密钥**：仅写在 **`ims-backend/.env`**（已 gitignore），**勿**提交密码或完整连接串。
- **pytest**：默认仍用本机 **`ims_test` / `ims_ops_test`**；全量用例请勿指向云库。
- **`opsbiz`**：当前同步脚本只推 **`ims`**；直播/成本等依赖 ops 的功能在云模式下仍可能需要本机 `opsbiz` 或后续单独同步。

## PO：切到云库（API / 手工联调）

1. 复制模板：`Copy-Item ims-backend\.env.local.example ims-backend\.env`
2. 在 `.env` 中任选一种方式（二选一）：

**方式 A — 分项变量 + 云 profile**

```env
IMS_USE_CLOUD_DB=1
IMS_MYSQL_HOST=47.110.62.216
IMS_MYSQL_USER=shenyu
IMS_MYSQL_PASSWORD=<向运维索取，勿入 git>
IMS_MYSQL_PORT=3306
IMS_DB=ims
```

**方式 B — 整串 URL**（密码含 `+` 等须 URL 编码，`core.py` 对分项变量会自动 `quote_plus`）

```env
IMS_DATABASE_URL=mysql+pymysql://shenyu:<URL-encoded-password>@47.110.62.216:3306/ims?charset=utf8mb4
```

3. 启动 API：`ims-backend/scripts/start_api.ps1 -KillPort`（脚本会加载 `.env`）。
4. 前端不变：Vite 仍代理 `IMS_API=http://127.0.0.1:18080`（见 `ims-web/vite.config.ts`）。

## PO：切回本机 MySQL

- 删除或注释 `.env` 中的 `IMS_USE_CLOUD_DB` / `IMS_DATABASE_URL`。
- 恢复本地默认：

```env
IMS_MYSQL_HOST=127.0.0.1
IMS_MYSQL_USER=root
IMS_MYSQL_PASSWORD=root
IMS_DB=ims
```

- 本机库初始化：`ims-backend/scripts/init_ims_db.ps1`

## 本地 ims → 云 ims 同步

```powershell
# 在 ims-backend/.env 中设置 IMS_CLOUD_MYSQL_PASSWORD=...（或当前 shell 导出）
cd ims-backend\scripts
.\sync_ims_to_cloud.ps1
```

摘要可写入 `ims-backend/cloud_db_sync_result.txt`（勿含密码；该文件已在根 `.gitignore`）。

## E2E

- `ims-web/scripts/run_e2e.ps1` 会加载 `ims-backend/.env` 后再启动 API；**云库与多人共享**，跑 E2E 前确认是否接受 seed 脚本对数据的写入。
- 仅测前端时仍用本机 API + 本机库即可；与云库切换无关的是 Playwright `E2E_BASE_URL`（默认 6173）。

## 安全

- 聊天/邮件中出现的 DB 密码应视为泄露；若仓库或频道对外公开，请在云 MySQL **轮换密码** 并只更新本机 `.env`。
