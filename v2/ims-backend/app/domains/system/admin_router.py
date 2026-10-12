"""B2 管理页接口。路径前缀 /admin-api/ims/system 与 /admin-api/ims/auth。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.domains.system import admin_service as svc
from app.domains.system import service as core

router = APIRouter()


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


def _q(name, default=None):
    return current_request().query_params.get(name, default)


def _params() -> dict:
    return dict(current_request().query_params)


@mark(perm="ims:system:user:query", summary="用户详情")
def user_get(ident: str):
    return svc.user_detail(svc._ident(ident))


@mark(perm="ims:system:user:create", operate=("用户", "新建用户"), summary="完整新建用户")
def user_create():
    return svc.user_create_full(_body())


@mark(perm="ims:system:user:update", operate=("用户", "修改用户"), summary="完整修改用户")
def user_update():
    return svc.user_update_full(_body())


@mark(perm="ims:system:user:update", operate=("用户", "调整角色"), summary="设置用户角色")
def user_roles(ident: str):
    body = _body()
    svc._set_roles(svc._ident(ident), svc._ids(body.get("roleIds"), "roleIds"))
    return svc.user_detail(svc._ident(ident))


@mark(perm="ims:system:user:update", operate=("用户", "冻结用户"), summary="冻结用户")
def user_freeze(ident: str):
    return svc.freeze_user(svc._ident(ident))


@mark(perm="ims:system:user:update", operate=("用户", "解冻用户"), summary="解冻用户")
def user_unfreeze(ident: str):
    return svc.unfreeze_user(svc._ident(ident))


@mark(perm="ims:system:user:update", operate=("用户", "办理离职"), summary="办理离职")
def user_resign(ident: str):
    return svc.resign_user(svc._ident(ident))


@mark(perm="ims:system:user:unlock", operate=("用户", "解锁账号"), summary="按用户解锁")
def user_unlock(ident: str):
    return svc.unlock_user(svc._ident(ident))


@mark(perm="ims:system:user:kick", operate=("用户", "强制下线"), summary="按用户强制下线")
def user_kick(ident: str):
    return svc.kick_user(svc._ident(ident))


@mark(perm="ims:system:user:reset-pwd", operate=("用户", "重置密码"), summary="重置用户密码")
def user_reset(ident: str):
    return svc.reset_user_password(svc._ident(ident))


@mark(perm="ims:system:user:export", operate=("用户", "导出用户"), summary="导出用户")
def user_export():
    return svc.export_users({**_params(), **_body()})


@mark(perm="ims:system:role:query", summary="角色分页")
def role_page():
    return svc.role_page(parse_page(_params()), _q("keyword"), _q("status"))


@mark(perm="ims:system:role:create", operate=("角色", "新建角色"), summary="新建角色")
def role_create():
    return svc.role_create(_body())


@mark(perm="ims:system:role:update", operate=("角色", "修改角色"), summary="修改角色")
def role_update():
    return svc.role_update(_body())


@mark(perm="ims:system:role:update", operate=("角色", "配置菜单"), summary="保存角色菜单")
def role_menus(ident: str):
    return svc.role_menus(svc._ident(ident), svc._ids(_body().get("menuIds"), "menuIds"))


@mark(perm="ims:system:role:grant", operate=("角色", "配置功能点"), summary="保存角色功能点")
def role_perms(ident: str):
    return svc.role_perm_detail(svc._ident(ident), _body().get("details") or [])


@mark(perm="ims:system:role:update", operate=("角色", "配置数据范围"), summary="保存数据范围")
def role_scope(ident: str):
    return svc.role_data_scope(svc._ident(ident), str(_body().get("dataScope") or ""))


@mark(perm="ims:system:role:query", summary="角色成员")
def role_members(ident: str):
    return svc.role_members(svc._ident(ident))


@mark(perm="ims:system:role:update", operate=("角色", "添加成员"), summary="添加角色成员")
def role_member_add(ident: str):
    return svc.role_add_member(svc._ident(ident), svc._ident(_body().get("userId"), "userId"))


@mark(perm="ims:system:role:update", operate=("角色", "移除成员"), summary="移除角色成员")
def role_member_remove(ident: str, user_id: str):
    return svc.role_remove_member(svc._ident(ident), svc._ident(user_id))


@mark(perm="ims:system:role:update", operate=("角色", "修改状态"), summary="启用或停用角色")
def role_status(ident: str):
    return svc.role_set_status(svc._ident(ident), str(_body().get("status") or ""))


@mark(perm="ims:system:role:delete", operate=("角色", "删除角色"), summary="确认后删除角色")
def role_delete(ident: str):
    return svc.role_delete_named(svc._ident(ident), str(_body().get("confirmName") or _q("confirmName") or ""))


@mark(perm="ims:system:role:query", summary="权限预览")
def role_preview(ident: str):
    return svc.role_preview(svc._ident(ident), svc._ident(_body().get("userId"), "userId"))


@mark(perm="ims:system:role:create", operate=("角色", "从岗位生成"), summary="从岗位生成待配置角色")
def role_from_position():
    return svc.role_from_position(str(_body().get("positionCode") or ""))


@mark(perm="ims:system:menu:query", summary="菜单树")
def menu_tree():
    return svc.menu_tree()


@mark(perm="ims:system:menu:create", operate=("菜单", "新建菜单"), summary="新建菜单")
def menu_create():
    return svc.menu_save(_body())


@mark(perm="ims:system:menu:update", operate=("菜单", "修改菜单"), summary="修改菜单")
def menu_update():
    body = _body()
    return svc.menu_save(body, svc._ident(body.get("id")))


@mark(perm="ims:system:menu:delete", operate=("菜单", "删除菜单"), summary="删除菜单")
def menu_delete(ident: str):
    return svc.menu_delete(svc._ident(ident))


@mark(perm="ims:system:menu:update", operate=("菜单", "显隐菜单"), summary="显示或隐藏菜单")
def menu_visible(ident: str):
    return svc.menu_visible(svc._ident(ident), _body().get("visible") in (True, 1, "1", "true"))


@mark(perm="ims:system:dict:query", summary="字典类型列表")
def dict_type_list():
    return svc.dict_types()


@mark(perm="ims:system:dict:update", operate=("字典", "修改字典类型"), summary="修改字典类型")
def dict_type_update():
    return svc.dict_type_update(_body())


@mark(perm="ims:system:dict:delete", operate=("字典", "删除字典类型"), summary="删除字典类型")
def dict_type_delete(ident: str):
    return svc.dict_type_delete(svc._ident(ident))


@mark(perm="ims:system:dict:query", summary="字典值列表")
def dict_data_list():
    return svc.dict_values(str(_q("dictType") or ""))


@mark(perm="ims:system:dict:create", operate=("字典", "新建字典值"), summary="新建字典值")
def dict_data_create():
    return svc.dict_data_save(_body())


@mark(perm="ims:system:dict:update", operate=("字典", "修改字典值"), summary="修改字典值")
def dict_data_update():
    body = _body()
    return svc.dict_data_save(body, svc._ident(body.get("id")))


@mark(perm="ims:system:dict:delete", operate=("字典", "删除字典值"), summary="删除字典值")
def dict_data_delete(ident: str):
    return service_delete_dict(ident)


def service_delete_dict(ident: str):
    return core.dict_data_delete(svc._ident(ident))


@mark(perm="ims:system:param:query", summary="参数变更历史")
def param_history():
    return svc.param_history(str(_q("paramKey") or ""))


@mark(perm="ims:system:param:update", operate=("参数", "修改参数"), summary="按键修改参数")
def param_put():
    body = _body()
    return core.param_update(body.get("paramKey") or body.get("key") or "", body.get("value"))


@mark(perm="ims:system:log:query", summary="操作日志")
def operate_page():
    return svc.operate_log_page(parse_page(_params(), ["createTime"]), _params())


@mark(perm="ims:system:log:query", summary="操作日志详情")
def operate_detail(ident: str):
    return svc.operate_log_detail(svc._ident(ident))


@mark(perm="ims:system:log:query", summary="登录日志")
def login_page():
    return svc.login_log_page(parse_page(_params(), ["createTime"]), _params())


@mark(perm="ims:system:log:export", operate=("日志", "导出操作日志"), summary="导出操作日志")
def operate_export():
    return svc.export_operate_logs({**_params(), **_body()})


@mark(perm="ims:system:log:export", operate=("日志", "导出登录日志"), summary="导出登录日志")
def login_export():
    return svc.export_login_logs({**_params(), **_body()})


@mark(perm="ims:system:notify:query", summary="通知发送记录")
def notify_page():
    return svc.notify_page(parse_page(_params()), _params())


@mark(perm="ims:system:notify:resend", operate=("通知", "补发通知"), summary="补发失败通知")
def notify_resend(ident: str):
    return svc.notify_resend(svc._ident(ident))


@mark(perm="ims:tenant:query", summary="租户分页")
def tenant_page():
    return svc.tenant_page(parse_page(_params()))


@mark(perm="ims:tenant:update", operate=("租户", "新建租户"), summary="新建租户")
def tenant_create():
    return svc.tenant_create(_body())


@mark(perm="ims:tenant:update", operate=("租户", "修改租户"), summary="修改租户")
def tenant_update(ident: str):
    return svc.tenant_update(svc._ident(ident), _body())


@mark(perm="ims:tenant:update", operate=("租户", "分配套餐"), summary="分配租户套餐")
def tenant_package(ident: str):
    return svc.tenant_assign_package(svc._ident(ident), svc._ident(_body().get("packageId"), "packageId"))


@mark(perm="ims:tenant:query", summary="套餐分页")
def package_page():
    return svc.package_page(parse_page(_params()))


@mark(perm="ims:tenant:package:update", operate=("套餐", "新建套餐"), summary="新建套餐")
def package_create():
    return svc.package_save(_body())


@mark(perm="ims:tenant:package:update", operate=("套餐", "修改套餐"), summary="修改套餐")
def package_update(ident: str):
    return svc.package_save(_body(), svc._ident(ident))


@mark(perm="ims:tenant:package:update", operate=("套餐", "配置菜单"), summary="保存套餐菜单")
def package_menus(ident: str):
    return svc.package_menus(svc._ident(ident), svc._ids(_body().get("menuIds"), "menuIds"))


@mark(perm="ims:tenant:package:update", operate=("套餐", "删除套餐"), summary="删除套餐")
def package_delete(ident: str):
    return svc.package_delete(svc._ident(ident), str(_body().get("confirmName") or ""))


router.get("/user/{ident}", summary="用户详情")(user_get)
router.post("/user", summary="完整新建用户")(user_create)
router.put("/user", summary="完整修改用户")(user_update)
router.put("/user/{ident}/roles", summary="设置用户角色")(user_roles)
router.put("/user/{ident}/freeze", summary="冻结用户")(user_freeze)
router.put("/user/{ident}/unfreeze", summary="解冻用户")(user_unfreeze)
router.put("/user/{ident}/resign", summary="办理离职")(user_resign)
router.put("/user/{ident}/unlock", summary="按用户解锁")(user_unlock)
router.put("/user/{ident}/kick", summary="按用户强制下线")(user_kick)
router.post("/user/{ident}/reset-password", summary="重置用户密码")(user_reset)
router.post("/user/export", summary="导出用户")(user_export)
router.get("/role/page", summary="角色分页")(role_page)
router.post("/role", summary="新建角色")(role_create)
router.put("/role", summary="修改角色")(role_update)
router.put("/role/{ident}/menus", summary="保存角色菜单")(role_menus)
router.put("/role/{ident}/perm-detail", summary="保存角色功能点")(role_perms)
router.put("/role/{ident}/data-scope", summary="保存数据范围")(role_scope)
router.get("/role/{ident}/members", summary="角色成员")(role_members)
router.post("/role/{ident}/members", summary="添加角色成员")(role_member_add)
router.delete("/role/{ident}/members/{user_id}", summary="移除角色成员")(role_member_remove)
router.put("/role/{ident}/status", summary="启用或停用角色")(role_status)
router.delete("/role/{ident}", summary="确认后删除角色")(role_delete)
router.post("/role/{ident}/preview", summary="权限预览")(role_preview)
router.post("/role/from-position", summary="从岗位生成待配置角色")(role_from_position)
router.get("/menu/tree", summary="菜单树")(menu_tree)
router.post("/menu", summary="新建菜单")(menu_create)
router.put("/menu", summary="修改菜单")(menu_update)
router.delete("/menu/{ident}", summary="删除菜单")(menu_delete)
router.put("/menu/{ident}/visible", summary="显示或隐藏菜单")(menu_visible)
router.get("/dict-type/list", summary="字典类型列表")(dict_type_list)
router.put("/dict-type", summary="修改字典类型")(dict_type_update)
router.delete("/dict-type/{ident}", summary="删除字典类型")(dict_type_delete)
router.get("/dict-data/list", summary="字典值列表")(dict_data_list)
router.post("/dict-data", summary="新建字典值")(dict_data_create)
router.put("/dict-data", summary="修改字典值")(dict_data_update)
router.delete("/dict-data/{ident}", summary="删除字典值")(dict_data_delete)
router.get("/param/history", summary="参数变更历史")(param_history)
router.put("/param", summary="按键修改参数")(param_put)
router.get("/operate-log/page", summary="操作日志")(operate_page)
router.get("/operate-log/{ident}", summary="操作日志详情")(operate_detail)
router.get("/login-log/page", summary="登录日志")(login_page)
router.post("/operate-log/export", summary="导出操作日志")(operate_export)
router.post("/login-log/export", summary="导出登录日志")(login_export)
router.get("/notify/page", summary="通知发送记录")(notify_page)
router.post("/notify/{ident}/resend", summary="补发失败通知")(notify_resend)
router.get("/tenant/page", summary="租户分页")(tenant_page)
router.post("/tenant", summary="新建租户")(tenant_create)
router.put("/tenant/{ident}", summary="修改租户")(tenant_update)
router.put("/tenant/{ident}/package", summary="分配租户套餐")(tenant_package)
router.get("/tenant-package/page", summary="套餐分页")(package_page)
router.post("/tenant-package", summary="新建套餐")(package_create)
router.put("/tenant-package/{ident}", summary="修改套餐")(package_update)
router.put("/tenant-package/{ident}/menus", summary="保存套餐菜单")(package_menus)
router.delete("/tenant-package/{ident}", summary="删除套餐")(package_delete)
