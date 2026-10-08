# COLLECT - 数据采集 API 契约（OPS 并入）

前缀：`/admin-api/ims/collect`（与 OPS `/admin-api/oa/**` 字段语义一致，路径挂 IMS 网关）。

## 1. 任务与日志（M10 · UX-M10）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/task/page` | 任务分页；筛选项同 UX-M10 P-M10-001 |
| 2 | GET/POST/PUT/DELETE | `/task/{id}` | 任务 CRUD |
| 3 | POST | `/task/{id}/run` | 立即执行 |
| 4 | POST | `/task/ensure-unified` | 统一任务成员（ADR-061） |
| 5 | GET | `/log/page` | 采集日志分页 |
| 6 | GET | `/log/{id}` | 日志详情含 `typeResults[]`（ADR-049） |

## 2. 外部采集（M8 · 拆分账号/关键词）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 7 | GET/POST/PUT/DELETE | `/external/account/**` | 外部账号（原 `/external-collect` 账号段） |
| 8 | POST | `/external/account/import` | CSV 批量导入 |
| 9 | GET/POST/PUT/DELETE | `/external/keyword/**` | 关键词（原 `/external-collect/keyword`） |
| 10 | GET/PUT | `/external/source/**` | 外部 HTTP 数据源（FR-M8-003；无侧栏，P2a 入口） |
| 11 | GET/POST/PUT | `/external/credential/**` | 租户采集凭账号（ADR-052；P2t） |

Channel-D 任务体：`collect_config_id` + 可选 `credential_profile`；`account_id` 必须为 null。

## 3. 元数据（M8 · 导航在 COLLECT）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 12 | GET | `/metadata/list` | 实体分页 |
| 13 | GET | `/metadata/unmapped-tables` | 未映射物理表 |
| 14 | GET | `/metadata/table-columns` | 表列信息 |
| 15 | POST | `/metadata/create` | 新建实体 |
| 16 | GET/PUT | `/metadata/{id}` | 详情/更新 |
| 17 | PUT | `/metadata/{entityId}/fields` | 批量保存字段 |
| 18 | GET | `/metadata/entity/{code}/fields` | BI0/指标只读读口（与 OPS 同形） |

## 4. 阈值（M8 · COLLECT + ALERT + MON）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 19 | GET | `/threshold/list` | `thresholdCategory` 必填 |
| 20 | POST/PUT/DELETE | `/threshold/**` | CRUD；字段见 UX-M8 §5 |

## 5. 内部例外 / 订单 / 质量（无主导航）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 21 | GET/PUT | `/internal/{platform}` | 企微应用 / 个微奥创（P1） |
| 22 | GET/PUT | `/order-config` | 订单 WebAPI 拉取；**禁止** JDBC 连接串 |
| 23 | GET | `/quality/summary` | 数据质量汇总（P6） |
| 24 | POST | `/manual-fill` | 手工补录 |

## 5.1 OPS runtime 对照（非 IMS canonical · 2026-10-02）

| IMS 契约路径 | 现网 OPS（football-front 调用） | Controller |
|--------------|--------------------------------|------------|
| `GET /task/page` | `GET /admin-api/ops/collect/task/page` | `CollectTaskController` |
| `POST /task/{id}/run` | 同左 | 同左 |
| `POST /task/ensure-unified` | `POST …/ensure-unified` · `…/ensure-external-unified` | 同左 |
| `POST …/{id}/start` · `…/stop` | Vue `startCollectTask` / `stopCollectTask` | 同左 |
| `GET /log/page` | `GET /admin-api/ops/collect/log/page` | 同左 |
| 外部账号/关键词 | `/admin-api/ops/config/external-collect/**` | ExternalCollect 配置 Controller |
| 阈值 | `/admin-api/ops/config/threshold/**` | `ThresholdConfigController` |
| 元数据 | `/admin-api/ops/metadata/**` | `MetadataController` |

前端 SSOT：`football-front/apps/web-ele/src/api/ops/collect.ts` · `config.ts` · `metadata.ts`。

---

## 6. 错误码

| 码 | 含义 |
|----|------|
| 1241 | 凭据无效 |
| 1242 | 平台不支持 |
| 1243 | 禁止 JDBC / 直连 Football 订单库 |
| 1261 | 自定义查询实体未映射（引导 `/collect/metadata`） |
