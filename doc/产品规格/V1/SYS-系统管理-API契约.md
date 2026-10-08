# SYS - 系统管理 API 契约（OPS 并入）

> `/admin-api/ims/system` ｜ SYS-001～008  
> **用户（ADR-IMS-009）**：`POST/PUT /system/user` 读写 `ims_sys_user`。创建分配新 ID 或导入时保留来源 ID。更新不得改 `id`（1211）。列表手机号脱敏。不调用 Football 用户接口。SYS-008 租户套餐仍不在当前交付波次。

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/system/user/page` | 用户分页 |
| 2 | POST/PUT | `/system/user` | 创建/更新（不可改 id） |
| 3 | GET | `/system/role/list` | 角色 |
| 4 | PUT | `/system/role/{id}/menus` | 角色菜单（权限码） |
| 4a | PUT | `/system/role/{id}/perm-detail` | **角色功能点 R/W/D 明细**（ADR-IMS-008 吸收自 AUTH-003） |
| 4b | PUT | `/system/role/{id}/data-scope` | **角色数据范围**（ALL / DEPT / IP_GROUP / SELF；ADR-IMS-008 · BR-305 权威口径） |
| 4c | PUT | `/system/role/{id}/dingtalk-position` | **角色绑定钉钉岗位**（唯一，ADR-IMS-008） |
| 4d | POST | `/system/role/{id}/preview` | **角色权限 Diff 预览**（模拟用户，迁自 AUTH-003 preview） |
| 4e | POST | `/system/role/from-position` | **从岗位自动建角色**（PENDING_CONFIG 空权限；ADR-IMS-008 G1~G8） |
| 5 | GET | `/system/menu/tree` | 菜单树 |
| 6 | GET | `/system/dict-type/list` | 字典类型 |
| 7 | GET | `/system/dict-data/list` | 字典数据 `dictType` |
| 8 | GET/PUT | `/system/param` | 参数列表/更新 by key |
| 9 | GET | `/system/operate-log/page` | 操作日志 |
| 10 | GET | `/system/login-log/page` | 登录日志 |
| 11 | GET | `/system/notify/page` | 通知 |
| 12 | GET | `/system/tenant/page` | 租户分页（SYS-008） |
| 13 | GET | `/system/tenant-package/simple-list` | 套餐下拉 |
| 14 | PUT | `/system/tenant/{id}` | 更新租户（含 `packageId`、状态） |

**角色 = 权限唯一载体（ADR-IMS-008）**：角色对象扩展 `permDetail`（功能点 → R/W/D）、`dataScope`、`dingtalkPosition`、`source`（`MANUAL`/`DINGTALK_AUTO`）、`status`（`ENABLED`/`PENDING_CONFIG`）。原 AUTH-003 岗位模板的权限明细字段迁入此处。

```typescript
interface RoleVO {
  id: number; roleName: string; roleKey: string;
  menuIds: number[];                             // 菜单权限码（兼容 ops:*）
  permDetail: Record<string, 'R' | 'W' | 'D' | 'RW' | 'RWD'>;  // 功能点 R/W/D（吸收自 AUTH-003）
  dataScope: 'ALL' | 'DEPT' | 'IP_GROUP' | 'SELF';  // 数据范围（吸收自 AUTH-003；BR-305 权威口径，「本部门」不含下级）
  dingtalkPosition?: string;                     // 钉钉岗位绑定（可空唯一）
  source: 'MANUAL' | 'DINGTALK_AUTO';            // 来源（G2）
  status: 'ENABLED' | 'PENDING_CONFIG';          // 待配置（G3）
}
```

**租户隔离**：除 platform 运维接口外，上述业务接口 **服务端注入** `tenant_id` 过滤；跨租户访问 → **1504**。

错误码：1211 禁止修改用户主键；1212 权限码不存在；1213 参数 key 未知。业务校验 1503 枚举仍可用于字典。
