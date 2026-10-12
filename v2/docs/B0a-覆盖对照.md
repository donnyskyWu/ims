# B0a 覆盖对照

每个功能点对应实现位置、单测编号，以及本机 MySQL 库 `imsV2.0` 与 Redis 上最近一次全量 pytest 的结果。

全量 pytest：421 passed，0 failed，耗时 872.95s。数据库 `imsV2.0`，Redis db 15。

| 功能点 | 名称 | 实现位置 | 单测 | 结果 |
| --- | --- | --- | --- | --- |
| FP-A01-01 | 应用工厂与分环境配置 | v2/ims-backend/app/main.py；v2/ims-backend/app/core/config.py；v2/ims-backend/config/ | UT-A01-01 通过；UT-A01-02 通过；UT-A01-03 通过；UT-A01-04 通过 | 通过 |
| FP-A01-02 | 路由自动注册与前缀校验 | v2/ims-backend/app/main.py（路由注册与前缀校验） | UT-A01-05 通过；UT-A01-06 通过 | 通过 |
| FP-A01-03 | 健康检查 | v2/ims-backend/app/main.py `health` | UT-A01-07 通过；UT-A01-08 通过；UT-A01-09 通过 | 通过 |
| FP-A01-04 | 请求上下文 | v2/ims-backend/app/core/context.py；v2/ims-backend/app/api/runtime.py | UT-A01-10 通过；UT-A01-11 通过 | 通过 |
| FP-A01-05 | Worker 进程入口 | v2/ims-backend/app/worker/__main__.py | UT-A01-12 通过 | 通过 |
| FP-A02-01 | 统一响应 `CommonResult` | v2/ims-backend/app/api/runtime.py | UT-A02-01 通过；UT-A02-02 通过 | 通过 |
| FP-A02-02 | 错误码注册表 | v2/ims-backend/app/core/error_codes.py | UT-A02-03 通过；UT-A02-04 通过；UT-A02-05 通过 | 通过 |
| FP-A02-03 | 全局异常处理 | v2/ims-backend/app/api/runtime.py；v2/ims-backend/app/core/errors.py | UT-A02-06 通过；UT-A02-07 通过；UT-A02-08 通过；UT-A02-09 通过；UT-A02-10 通过 | 通过 |
| FP-A03-01 | 分页参数与结果 | v2/ims-backend/app/core/pagination.py | UT-A03-01 通过；UT-A03-02 通过；UT-A03-03 通过 | 通过 |
| FP-A03-02 | 排序白名单 | v2/ims-backend/app/core/pagination.py | UT-A03-04 通过；UT-A03-05 通过；UT-A03-06 通过 | 通过 |
| FP-A04-01 | 命名转换 | v2/ims-backend/app/core/serialize.py；v2/ims-backend/app/api/dump.py | UT-A04-01 通过 | 通过 |
| FP-A04-02 | 时间与日期 | v2/ims-backend/app/core/clock.py；v2/ims-backend/app/core/serialize.py | UT-A04-02 通过；UT-A04-03 通过；UT-A04-04 通过 | 通过 |
| FP-A04-03 | 金额与百分比 | v2/ims-backend/app/core/serialize.py | UT-A04-05 通过；UT-A04-06 通过；UT-A04-07 通过 | 通过 |
| FP-A04-04 | 枚举与主键输出 | v2/ims-backend/app/core/serialize.py；v2/ims-backend/app/core/enums.py | UT-A04-08 通过；UT-A04-09 通过；UT-A04-10 通过 | 通过 |
| FP-A05-01 | OpenAPI 导出与前端客户端生成 | v2/ims-backend/tools/api_gen.py；v2/ims-web/src/api/generated/client.ts | UT-A05-01 通过；UT-A05-02 通过；UT-A05-03 通过；UT-A05-04 通过 | 通过 |
| FP-A06-01 | 脚手架输入定义 | v2/ims-backend/tools/scaffold/generate.py | UT-A06-01 通过；UT-A06-02 通过 | 通过 |
| FP-A06-02 | 后端生成 | v2/ims-backend/tools/scaffold/generate.py | UT-A06-03 通过；UT-A06-04 通过 | 通过 |
| FP-A06-03 | 前端生成 | v2/ims-backend/tools/scaffold/generate.py | UT-A06-05 通过 | 通过 |
| FP-A06-04 | 重复生成保护 | v2/ims-backend/tools/scaffold/generate.py | UT-A06-06 通过；UT-A06-07 通过 | 通过 |
| FP-B01-01 | 审计基类 | v2/ims-backend/app/db/base.py | UT-B01-01 通过；UT-B01-02 通过；UT-B01-03 通过；UT-B01-04 通过；UT-B01-05 通过；UT-B01-06 通过 | 通过 |
| FP-B02-01 | Alembic 基线与双向验证 | v2/ims-backend/migrations/versions/a8ea91bf512c_b0a_baseline.py | UT-B02-01 通过；UT-B02-02 通过 | 通过 |
| FP-B02-02 | 结构变更静态检查 | v2/ims-backend/tools/static_checks.py | UT-B02-03 通过；UT-B02-04 通过；UT-B02-05 通过 | 通过 |
| FP-B03-01 | 用户主表 `ims_sys_user` | v2/ims-backend/app/domains/system/model.py `User`；v2/ims-backend/app/services/auth_svc.py | UT-B03-01 通过；UT-B03-02 通过；UT-B03-03 通过；UT-B03-04 通过；UT-B03-05 通过；UT-B03-06 通过；UT-B03-07 通过 | 通过 |
| FP-B03-02 | 用户-部门 `ims_sys_user_dept` | v2/ims-backend/app/domains/system/model.py `UserDept` | UT-B03-08 通过；UT-B03-09 通过；UT-B03-10 通过；UT-B03-11 通过；UT-B03-12 通过 | 通过 |
| FP-B03-03 | 钉钉映射 `ims_auth_user_mapping` | v2/ims-backend/app/domains/system/model.py；v2/ims-backend/app/services/mapping.py | UT-B03-13 通过；UT-B03-14 通过 | 通过 |
| FP-B03-04 | 岗位字典 | v2/ims-backend/app/domains/system/model.py；v2/ims-backend/app/services/position.py | UT-B03-15 通过 | 通过 |
| FP-B04-01 | 角色 `ims_sys_role` | v2/ims-backend/app/domains/system/model.py `Role`；v2/ims-backend/app/domains/system/service.py | UT-B04-01 通过；UT-B04-02 通过；UT-B04-03 通过；UT-B04-04 通过；UT-B04-05 通过；UT-B04-06 通过；UT-B04-07 通过 | 通过 |
| FP-B04-02 | 菜单与权限码 `ims_sys_menu` | v2/ims-backend/app/domains/system/model.py `Menu`；v2/ims-backend/app/catalog.py | UT-B04-08 通过；UT-B04-09 通过 | 通过 |
| FP-B04-03 | 角色授权与功能点明细 | v2/ims-backend/app/domains/system/router.py；v2/ims-backend/app/domains/system/service.py | UT-B04-10 通过；UT-B04-11 通过 | 通过 |
| FP-B04-04 | 租户与套餐 | v2/ims-backend/app/domains/system/model.py `Tenant`；v2/ims-backend/app/services/principal.py | UT-B04-12 通过；UT-B04-13 通过；UT-B04-14 通过 | 通过 |
| FP-B05-01 | 共享实体骨架与表名登记册 | v2/ims-backend/app/catalog.py；v2/ims-backend/app/domains/master/model.py；v2/ims-backend/tools/docs_gen.py | UT-B05-01 通过；UT-B05-02 通过；UT-B05-03 通过 | 通过 |
| FP-B06-01 | 引用登记 | v2/ims-backend/app/db/refs.py | UT-B06-01 通过；UT-B06-02 通过 | 通过 |
| FP-B06-02 | 写入前校验 | v2/ims-backend/app/db/repository.py `validate_refs_on_write` | UT-B06-03 通过；UT-B06-04 通过；UT-B06-05 通过；UT-B06-06 通过；UT-B06-07 通过；UT-B06-14 通过 | 通过 |
| FP-B06-03 | 删除 / 停用前被引用检查 | v2/ims-backend/app/db/repository.py `protect_counts` | UT-B06-08 通过；UT-B06-09 通过；UT-B06-10 通过 | 通过 |
| FP-B06-04 | 级联策略 | v2/ims-backend/app/db/repository.py `cascade_soft` / `set_null_refs` | UT-B06-11 通过；UT-B06-12 通过；UT-B06-13 通过 | 通过 |
| FP-B06-05 | 批量模式 | v2/ims-backend/app/db/repository.py `bulk_check` | UT-B06-15 通过 | 通过 |
| FP-B06-06 | 外键字典文档生成 | v2/ims-backend/tools/docs_gen.py | UT-B06-16 通过 | 通过 |
| FP-B07-01 | 字典类型与字典值 | v2/ims-backend/app/domains/system/model.py；v2/ims-backend/app/domains/system/service.py | UT-B07-01 通过；UT-B07-02 通过；UT-B07-03 通过；UT-B07-04 通过；UT-B07-05 通过 | 通过 |
| FP-B07-02 | 首批字典与参数 | v2/ims-backend/app/catalog.py；v2/ims-backend/tools/seed/apply.py | UT-B07-06 通过；UT-B07-07 通过；UT-B07-08 通过；UT-B07-09 通过；UT-B07-10 通过 | 通过 |
| FP-B07-03 | 字典与参数缓存 | v2/ims-backend/app/domains/system/service.py 字典缓存 | UT-B07-11 通过 | 通过 |
| FP-B07-04 | 后端枚举与字典一致性校验 | v2/ims-backend/app/core/enums.py；v2/ims-backend/tools/static_checks.py | UT-B07-12 通过；UT-B07-13 通过 | 通过 |
| FP-B08-01 | 部门表 `ims_sys_dept` | v2/ims-backend/app/domains/system/model.py `Dept` | UT-B08-01 通过；UT-B08-02 通过；UT-B08-03 通过 | 通过 |
| FP-B08-02 | 部门树查询 | v2/ims-backend/app/domains/system/service.py `dept_tree` | UT-B08-04 通过；UT-B08-05 通过；UT-B08-06 通过；UT-B08-07 通过；UT-B08-08 通过；UT-B08-09 通过 | 通过 |
| FP-B08-03 | 按部门查人员 | v2/ims-backend/app/domains/system/service.py `user_page` | UT-B08-10 通过；UT-B08-11 通过 | 通过 |
| FP-B08-04 | 本地新建部门 | v2/ims-backend/app/domains/system/service.py `dept_create` | UT-B08-12 通过；UT-B08-13 通过；UT-B08-14 通过；UT-B08-15 通过 | 通过 |
| FP-B08-05 | 改名 / 修改负责人 / 排序 | v2/ims-backend/app/domains/system/router.py 部门修改 | UT-B08-16 通过；UT-B08-17 通过 | 通过 |
| FP-B08-06 | 移动部门 | v2/ims-backend/app/domains/system/service.py 移动部门 | UT-B08-18 通过；UT-B08-19 通过；UT-B08-20 通过；UT-B08-21 通过 | 通过 |
| FP-B08-07 | 停用 / 删除部门 | v2/ims-backend/app/domains/system/service.py 停用 / 删除部门 | UT-B08-22 通过；UT-B08-23 通过；UT-B08-24 通过；UT-B08-25 通过；UT-B08-26 通过 | 通过 |
| FP-B08-08 | 部门与人员基础接口（供 B0b 部门树 / 左树右表示例页与 M02 复用） | v2/ims-backend/app/domains/system/router.py 部门与用户接口 | UT-B08-27 通过；UT-B08-28 通过；UT-B08-29 通过；UT-B08-30 通过 | 通过 |
| FP-B09-01 | 引用完整性巡检 | v2/ims-backend/app/services/integrity.py | UT-B09-01 通过；UT-B09-02 通过；UT-B09-03 通过；UT-B09-04 通过；UT-B09-05 通过；UT-B09-06 通过 | 通过 |
| FP-C01-01 | 会话与事务 | v2/ims-backend/app/db/session.py | UT-C01-01 通过；UT-C01-02 通过；UT-C01-03 通过 | 通过 |
| FP-C01-02 | 通用仓储 | v2/ims-backend/app/db/repository.py | UT-C01-04 通过；UT-C01-05 通过 | 通过 |
| FP-C02-01 | 租户过滤 | v2/ims-backend/app/db/session.py 租户过滤 | UT-C02-01 通过；UT-C02-02 通过；UT-C02-03 通过；UT-C02-04 通过 | 通过 |
| FP-C02-02 | 数据范围谓词 | v2/ims-backend/app/db/scope.py | UT-C02-05 通过；UT-C02-06 通过；UT-C02-07 通过；UT-C02-08 通过；UT-C02-09 通过；UT-C02-10 通过；UT-C02-11 通过 | 通过 |
| FP-C02-03 | 防漏配 | v2/ims-backend/app/main.py 启动校验；v2/ims-backend/tools/static_checks.py | UT-C02-12 通过；UT-C02-13 通过；UT-C02-14 通过 | 通过 |
| FP-C02-04 | 发布 / 分享数据双重过滤 | v2/ims-backend/app/db/scope.py 分享过滤 | UT-C02-15 通过；UT-C02-16 通过 | 通过 |
| FP-C02-05 | fail-closed | v2/ims-backend/app/db/scope.py fail-closed | UT-C02-17 通过；UT-C02-18 通过 | 通过 |
| FP-C03-01 | 字段加密 | v2/ims-backend/app/core/crypto.py；v2/ims-backend/app/db/types.py | UT-C03-01 通过；UT-C03-02 通过 | 通过 |
| FP-C03-02 | 脱敏输出 | v2/ims-backend/app/core/crypto.py；v2/ims-backend/app/api/dump.py | UT-C03-03 通过；UT-C03-04 通过；UT-C03-05 通过；UT-C03-06 通过 | 通过 |
| FP-C04-01 | 通用编号生成器 | v2/ims-backend/app/core/sequence.py | UT-C04-01 通过；UT-C04-02 通过；UT-C04-03 通过 | 通过 |
| FP-C04-02 | 场次编号 | v2/ims-backend/app/core/sequence.py 场次编号 | UT-C04-04 通过；UT-C04-05 通过；UT-C04-06 通过 | 通过 |
| FP-C04-03 | 幂等 | v2/ims-backend/app/api/runtime.py `X-Client-Token` | UT-C04-07 通过；UT-C04-08 通过；UT-C04-09 通过；UT-C04-10 通过 | 通过 |
| FP-D01-01 | 账号密码登录 | v2/ims-backend/app/services/auth_svc.py | UT-D01-01 通过；UT-D01-02 通过；UT-D01-03 通过；UT-D01-04 通过；UT-D01-05 通过；UT-D01-06 通过；UT-D01-07 通过 | 通过 |
| FP-D01-02 | 密码策略 | v2/ims-backend/app/services/auth_svc.py 密码策略 | UT-D01-08 通过；UT-D01-09 通过；UT-D01-10 通过；UT-D01-11 通过 | 通过 |
| FP-D01-03 | 令牌与会话 | v2/ims-backend/app/services/sessions.py；v2/ims-backend/app/core/security.py | UT-D01-12 通过；UT-D01-13 通过；UT-D01-14 通过；UT-D01-15 通过；UT-D01-16 通过 | 通过 |
| FP-D01-04 | 登出与强制下线 | v2/ims-backend/app/services/sessions.py 登出 / 强制下线 | UT-D01-17 通过；UT-D01-18 通过 | 通过 |
| FP-D01-05 | 管理员解锁 | v2/ims-backend/app/domains/system/router.py 解锁 | UT-D01-19 通过 | 通过 |
| FP-D02-01 | 钉钉 SSO 跳转与 state | v2/ims-backend/app/domains/auth/router.py SSO 跳转 | UT-D02-01 通过；UT-D02-02 通过 | 通过 |
| FP-D02-02 | 钉钉 SSO 回调 | v2/ims-backend/app/domains/auth/router.py；v2/ims-backend/app/integrations/dingtalk/client.py | UT-D02-03 通过；UT-D02-04 通过；UT-D02-05 通过；UT-D02-06 通过；UT-D02-07 通过；UT-D02-08 通过；UT-D02-09 通过 | 通过 |
| FP-D03-01 | 接口权限声明 | v2/ims-backend/app/api/meta.py；v2/ims-backend/app/main.py | UT-D03-01 通过；UT-D03-02 通过 | 通过 |
| FP-D03-02 | 权限判定 | v2/ims-backend/app/api/runtime.py；v2/ims-backend/app/services/principal.py | UT-D03-03 通过；UT-D03-04 通过；UT-D03-05 通过；UT-D03-06 通过；UT-D03-07 通过 | 通过 |
| FP-D03-03 | 禁止按角色名判断（静态检查） | v2/ims-backend/tools/static_checks.py | UT-D03-08 通过 | 通过 |
| FP-D03-04 | 权限缓存与生效时间 | v2/ims-backend/app/services/principal.py | UT-D03-09 通过；UT-D03-10 通过 | 通过 |
| FP-D04-01 | 数据范围配置 | v2/ims-backend/app/db/scope.py；v2/ims-backend/app/domains/system/router.py 数据范围 | UT-D04-01 通过 | 通过 |
| FP-D05-01 | 岗位 → 角色供给 | v2/ims-backend/app/services/position.py | UT-D05-01 通过；UT-D05-02 通过；UT-D05-03 通过；UT-D05-04 通过；UT-D05-05 通过 | 通过 |
| FP-D06-01 | 我的菜单与权限 | v2/ims-backend/app/domains/auth/router.py `me` | UT-D06-01 通过；UT-D06-02 通过；UT-D06-03 通过；UT-D06-04 通过 | 通过 |
| FP-D07-01 | 钉钉事件接收 | v2/ims-backend/app/domains/callback/router.py；v2/ims-backend/app/services/org_sync.py | UT-D07-01 通过；UT-D07-02 通过 | 通过 |
| FP-D07-02 | 部门同步（钉钉为准） | v2/ims-backend/app/services/org_sync.py 部门同步 | UT-D07-03 通过；UT-D07-04 通过；UT-D07-05 通过；UT-D07-06 通过；UT-D07-07 通过；UT-D07-08 通过；UT-D07-09 通过；UT-D07-10 通过；UT-D07-11 通过；UT-D07-12 通过；UT-D07-24 通过 | 通过 |
| FP-D07-03 | 人员同步 | v2/ims-backend/app/services/org_sync.py 人员同步 | UT-D07-13 通过；UT-D07-14 通过；UT-D07-15 通过；UT-D07-16 通过；UT-D07-17 通过 | 通过 |
| FP-D07-04 | 全量对账 | v2/ims-backend/app/services/org_sync.py；v2/ims-backend/app/domains/system/org_router.py | UT-D07-18 通过；UT-D07-19 通过；UT-D07-20 通过 | 通过 |
| FP-D07-05 | 重试、死信与重放 | v2/ims-backend/app/services/org_sync.py 重试 / 死信 / 重放 | UT-D07-21 通过；UT-D07-22 通过；UT-D07-23 通过 | 通过 |
| FP-E01-01 | 上传 | v2/ims-backend/app/domains/file/service.py `upload` | UT-E01-01 通过；UT-E01-02 通过 | 通过 |
| FP-E01-02 | 下载 | v2/ims-backend/app/domains/file/service.py 下载 | UT-E01-03 通过；UT-E01-04 通过；UT-E01-05 通过；UT-E01-06 通过 | 通过 |
| FP-E01-03 | 删除策略 | v2/ims-backend/app/domains/file/service.py 解绑与清理 | UT-E01-07 通过；UT-E01-08 通过 | 通过 |
| FP-E02-01 | 场景注册与校验 | v2/ims-backend/app/domains/file/service.py 场景注册 | UT-E02-01 通过；UT-E02-02 通过；UT-E02-03 通过；UT-E02-04 通过；UT-E02-05 通过；UT-E02-06 通过 | 通过 |
| FP-E02-02 | 水印钩子 | v2/ims-backend/app/domains/file/service.py 水印 | UT-E02-07 通过 | 通过 |
| FP-F01-01 | 操作日志 | v2/ims-backend/app/api/runtime.py 操作日志 | UT-F01-01 通过；UT-F01-02 通过；UT-F01-03 通过；UT-F01-04 通过；UT-F01-05 通过；UT-F01-06 通过；UT-F01-07 通过 | 通过 |
| FP-F01-02 | 登录日志 | v2/ims-backend/app/services/auth_svc.py 登录日志 | UT-F01-08 通过 | 通过 |
| FP-F02-01 | 字段级变更历史 | v2/ims-backend/app/db/changes.py | UT-F02-01 通过；UT-F02-02 通过 | 通过 |
| FP-F02-02 | 敏感数据查看日志 | v2/ims-backend/app/api/runtime.py `sensitive_view` | UT-F02-03 通过；UT-F02-04 通过 | 通过 |
| FP-F02-03 | 时间线 | v2/ims-backend/app/services/timeline.py | UT-F02-05 通过 | 通过 |
| FP-G01-01 | 发送通知 | v2/ims-backend/app/domains/message/service.py | UT-G01-01 通过；UT-G01-02 通过；UT-G01-03 通过；UT-G01-04 通过；UT-G01-05 通过 | 通过 |
| FP-G01-02 | 我的消息 | v2/ims-backend/app/domains/message/router.py | UT-G01-06 通过；UT-G01-07 通过；UT-G01-08 通过 | 通过 |
| FP-G02-01 | 待办生成与关闭 | v2/ims-backend/app/domains/todo/service.py | UT-G02-01 通过；UT-G02-02 通过；UT-G02-03 通过；UT-G02-04 通过；UT-G02-05 通过 | 通过 |
| FP-G02-02 | 我的待办 | v2/ims-backend/app/domains/todo/router.py | UT-G02-06 通过；UT-G02-07 通过 | 通过 |
| FP-G03-01 | 流程模板与版本 | v2/ims-backend/app/domains/flow/service.py 模板 | UT-G03-06 通过；UT-G03-07 通过；UT-G03-08 通过 | 通过 |
| FP-G03-02 | 实例、任务与动作 | v2/ims-backend/app/domains/flow/service.py 实例 | UT-G03-01 通过；UT-G03-02 通过；UT-G03-03 通过；UT-G03-04 通过；UT-G03-05 通过；UT-G03-09 通过；UT-G03-10 通过 | 通过 |
| FP-G03-03 | 超时与督办 | v2/ims-backend/app/domains/flow/service.py 超时督办 | UT-G03-11 通过 | 通过 |
| FP-H01-01 | 定时任务注册 | v2/ims-backend/app/services/jobs.py；v2/ims-backend/app/worker/__main__.py | UT-H01-02 通过；UT-H01-03 通过 | 通过 |
| FP-H01-02 | 分布式锁 | v2/ims-backend/app/services/jobs.py 分布式锁 | UT-H01-01 通过；UT-H01-04 通过 | 通过 |
| FP-H02-01 | 导入 | v2/ims-backend/app/services/exchange.py 导入 | UT-H02-01 通过；UT-H02-02 通过；UT-H02-03 通过；UT-H02-04 通过 | 通过 |
| FP-H02-02 | 异步导出 | v2/ims-backend/app/services/exchange.py；v2/ims-backend/app/domains/export_task/router.py | UT-H02-05 通过；UT-H02-06 通过；UT-H02-07 通过 | 通过 |
| FP-H03-01 | 错误码策略导出 | v2/ims-backend/tools/export_error_codes.py | UT-H03-01 通过；UT-H03-02 通过；UT-H03-03 通过 | 通过 |
| FP-H04-01 | 适配器基类 | v2/ims-backend/app/integrations/base.py；v2/ims-backend/app/integrations/runtime.py | UT-H04-01 通过；UT-H04-02 通过；UT-H04-03 通过；UT-H04-04 通过；UT-H04-05 通过 | 通过 |
| FP-H04-02 | 禁止 OPS HTTP（CI 扫描） | v2/ims-backend/tools/static_checks.py `check_ops_http` | UT-H04-06 通过 | 通过 |
| FP-H05-01 | 种子脚本 | v2/ims-backend/tools/seed/apply.py | UT-H05-01 通过；UT-H05-02 通过；UT-H05-03 通过；UT-H05-04 通过 | 通过 |
| FP-H05-02 | 迁移框架 | v2/ims-backend/tools/migrate/run.py | UT-H05-05 通过；UT-H05-06 通过 | 通过 |
| FP-H06-01 | Football 只读连接与读仓储 | v2/ims-backend/app/integrations/football_live/reader.py | UT-H06-01 通过；UT-H06-02 通过；UT-H06-03 通过；UT-H06-04 通过；UT-H06-05 通过 | 通过 |
| FP-H06-02 | 结构一致性校验 | v2/ims-backend/app/integrations/football_live/schema_check.py | UT-H06-06 通过 | 通过 |
| FP-H06-03 | 替身表与造数 | v2/ims-backend/tools/football_stub/create.sql；v2/ims-backend/tools/football_stub/seed.py | UT-H06-07 通过；UT-H06-08 通过 | 通过 |
| FP-H06-04 | metrics 合并与同步补偿（框架部分） | v2/ims-backend/app/integrations/football_live/reader.py；v2/ims-backend/app/services/jobs.py | UT-H06-09 通过；UT-H06-10 通过 | 通过 |
| FP-H07-01 | 钉钉考勤配置与适配器 | v2/ims-backend/app/integrations/dingtalk_attendance/client.py；v2/ims-backend/app/services/attendance.py | UT-H07-05 通过；UT-H07-06 通过；UT-H07-07 通过；UT-H07-08 通过 | 通过 |
| FP-H07-02 | 工作日历 | v2/ims-backend/app/services/attendance.py 工作日历 | UT-H07-10 通过 | 通过 |
| FP-H07-03 | 应提交天数计算 | v2/ims-backend/app/services/attendance.py 应提交天数 | UT-H07-01 通过；UT-H07-02 通过；UT-H07-03 通过；UT-H07-04 通过 | 通过 |
| FP-H07-04 | 每日拉取 | v2/ims-backend/app/services/attendance.py 每日拉取 | UT-H07-09 通过 | 通过 |
| FP-H08-01 | 培训 AI 配置 | v2/ims-backend/app/integrations/train_ai/client.py；v2/ims-backend/tools/seed/train_ai_default.py | UT-H08-08 通过；UT-H08-09 通过；UT-H08-10 通过；UT-H08-11 通过；UT-H08-12 通过；UT-H08-13 通过；UT-H08-14 通过 | 通过 |
| FP-H08-02 | 生成试卷草稿 | v2/ims-backend/app/integrations/train_ai/client.py `generate_quiz` | UT-H08-01 通过；UT-H08-02 通过；UT-H08-03 通过；UT-H08-04 通过；UT-H08-05 通过；UT-H08-06 通过；UT-H08-07 通过 | 通过 |

## 增补用例（不属于 117 个 B0a 功能点）

- UT-B1PRE-01：预留，通过。不计入未完成功能点。
- UT-B1PRE-02：预留，通过。不计入未完成功能点。
- UT-B1PRE-03：预留，通过。不计入未完成功能点。
- UT-B1PRE-04：预留，通过。不计入未完成功能点。
- UT-B1PRE-05：预留，通过。不计入未完成功能点。
- UT-B1PRE-06：预留，通过。不计入未完成功能点。
- UT-B1PRE-07：预留，通过。不计入未完成功能点。
- UT-B1PRE-08：预留，通过。不计入未完成功能点。
- UT-B1PRE-09：预留，通过。不计入未完成功能点。
- UT-B1PRE-10：预留，通过。不计入未完成功能点。

## 未通过功能点

无。117 个功能点的对应用例均为通过。
