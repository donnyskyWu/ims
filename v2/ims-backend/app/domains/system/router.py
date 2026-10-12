"""系统管理接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.context import get_ctx
from app.core.pagination import parse_page
from app.domains.system import service

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


def _q(name, default=None):
    request = current_request()
    return request.query_params.get(name, default)


@mark(any_perm=("ims:system:dept:query", "ims:system:user:query"), summary="部门树")
def dept_tree():
    return service.dept_tree(keyword=_q("keyword"), status=_q("status"))


@mark(perm="ims:system:dept:create", operate=("部门", "新建部门"), summary="新建部门")
def dept_create():
    body = _body()
    return service.dept_create(body.get("name") or "", int(body.get("parentId")), body.get("source") or "LOCAL")


@mark(perm="ims:system:dept:update", operate=("部门", "修改部门"), summary="修改部门")
def dept_update():
    body = _body()
    return service.dept_update(int(body["id"]), body.get("name"), body.get("leaderUserId"), body.get("sort"))


@mark(perm="ims:system:dept:update", operate=("部门", "移动部门"), summary="移动部门")
def dept_move():
    body = _body()
    return service.dept_move(int(body["id"]), int(body["parentId"]))


@mark(perm="ims:system:dept:update", operate=("部门", "停用部门"), summary="修改部门状态")
def dept_status():
    body = _body()
    return service.dept_status(int(body["id"]), body.get("status") or "DISABLED")


@mark(perm="ims:system:dept:delete", operate=("部门", "删除部门"), summary="删除部门")
def dept_delete():
    return service.dept_delete(int(_q("id")))


@mark(perm="ims:system:dept:update", operate=("部门", "确认本地部门"), summary="确认保留本地部门")
def confirm_orphan():
    return service.confirm_orphan(int(_body()["id"]))


@mark(perm="ims:system:user:query", summary="用户分页")
def user_page():
    request = current_request()
    page = parse_page(dict(request.query_params), ["createTime"])
    include = request.query_params.get("includeChildren", "true")
    dept = request.query_params.get("deptId")
    return service.user_page(
        page,
        int(dept) if dept else None,
        str(include).lower() != "false",
        request.query_params.get("keyword"),
        request.query_params.get("status"),
        request.query_params.get("username"),
        request.query_params.get("nickname"),
        request.query_params.get("mobile"),
    )


@mark(login_only=True, summary="用户简表")
def user_simple():
    request = current_request()
    page = parse_page(dict(request.query_params))
    return service.user_simple(page)


@mark(perm="ims:system:user:create", operate=("用户", "新建用户"), summary="新建用户")
def user_create():
    body = _body()
    return service.user_create(
        body.get("username") or "",
        body.get("nickname") or body.get("name") or "",
        [int(item) for item in body.get("deptIds") or []],
        int(body.get("mainDeptId")),
        body.get("password") or "",
        body.get("mobile"),
        body.get("empNo"),
        body.get("positionCode"),
    )


@mark(perm="ims:system:user:update", operate=("用户", "调整部门"), summary="调整用户部门")
def update_depts():
    body = _body()
    return service.update_depts(int(body["id"]), [int(item) for item in body.get("deptIds") or []], body.get("mainDeptId") and int(body["mainDeptId"]))


@mark(perm="ims:system:user:update", operate=("用户", "修改用户"), summary="修改用户")
def user_update(ident: int):
    body = _body()
    return service.user_update(ident, body.get("id"), {"nickname": body.get("nickname"), "emp_no": body.get("empNo"), "position_code": body.get("positionCode")})


@mark(perm="ims:system:user:delete", operate=("用户", "删除用户"), summary="删除用户")
def user_delete():
    ident = _q("id") or (_body().get("id") if _body() else None)
    return service.user_delete(int(ident))


@mark(perm="ims:system:user:update", operate=("用户", "修改状态"), summary="修改用户状态")
def user_status():
    body = _body()
    return service.user_status(int(body["id"]), body["status"])


@mark(perm="ims:system:user:update", operate=("用户", "重置密码"), summary="重置密码")
def reset_password():
    return auth_reset(int(_body()["id"]))


def auth_reset(ident: int):
    from app.services.auth_svc import reset_password

    return reset_password(ident)


@mark(perm="ims:system:user:kick", operate=("用户", "强制下线"), summary="强制下线")
def kick():
    from app.services.auth_svc import kick as do_kick

    do_kick(int(_body()["id"]))
    return {}


@mark(perm="ims:system:user:unlock", operate=("用户", "解锁"), summary="解锁账号")
def unlock():
    from app.services.auth_svc import unlock as do_unlock

    return do_unlock(str(_body().get("username") or ""))


@mark(perm="ims:system:role:create", operate=("角色", "新建角色"), summary="新建角色")
def role_create():
    body = _body()
    return service.role_create(body.get("name") or "", body.get("roleKey") or "", body.get("source") or "MANUAL", body.get("dataScope"), body.get("positionCode"))


@mark(perm="ims:system:role:delete", operate=("角色", "删除角色"), summary="删除角色")
def role_delete():
    return service.role_delete(int(_q("id")))


@mark(perm="ims:system:role:update", operate=("角色", "停用角色"), summary="修改角色状态")
def role_status():
    body = _body()
    return service.role_status(int(body["id"]), body["status"])


@mark(perm="ims:system:role:grant", operate=("角色", "授权"), summary="角色授权")
def role_grant():
    body = _body()
    return service.role_grant(int(body["roleId"]), body.get("permCodes") or [], body.get("details"))


@mark(perm="ims:system:role:update", summary="保存角色数据范围")
def role_scope():
    from app.db.session import get_session
    from app.domains.system.model import Role

    body = _body()
    role = get_session().get(Role, int(body["id"]))
    role.data_scope = body.get("dataScope")
    return {"id": role.id, "dataScope": role.data_scope, "dataScopeText": None}


@mark(login_only=True, summary="角色简表")
def role_simple():
    return service.role_simple()


@mark(perm="ims:system:menu:create", operate=("菜单", "新建菜单"), summary="新建菜单")
def menu_create():
    body = _body()
    return service.menu_create(body.get("name") or "", body.get("type") or "BUTTON", body.get("permCode"), int(body.get("parentId") or 0))


@mark(perm="ims:system:dict:create", summary="新建字典类型")
def dict_type_create():
    body = _body()
    return service.dict_type_create(body.get("dictType") or "", body.get("name") or "")


@mark(perm="ims:system:dict:create", summary="新建字典值")
def dict_data_create():
    body = _body()
    return service.dict_data_create(body.get("dictType") or "", body.get("dictValue") or "", body.get("dictLabel") or "", body.get("colorType") or "neutral")


@mark(perm="ims:system:dict:update", summary="修改字典值")
def dict_data_update():
    body = _body()
    return service.dict_data_update(int(body["id"]), body.get("dictValue"), body.get("dictLabel"), body.get("colorType"), body.get("status"))


@mark(perm="ims:system:dict:delete", summary="删除字典值")
def dict_data_delete():
    return service.dict_data_delete(int(_q("id")))


@mark(perm="ims:system:param:query", summary="参数列表")
def param_list():
    return service.param_list()


@mark(perm="ims:system:param:update", operate=("参数", "修改参数"), summary="修改参数")
def param_update():
    body = _body()
    return service.param_update(body.get("paramKey") or "", body.get("value"))


router.get("/dept/tree", summary="部门树")(dept_tree)
router.post("/dept/create", summary="新建部门")(dept_create)
router.put("/dept/update", summary="修改部门")(dept_update)
router.put("/dept/move", summary="移动部门")(dept_move)
router.put("/dept/update-status", summary="修改部门状态")(dept_status)
router.delete("/dept/delete", summary="删除部门")(dept_delete)
router.put("/dept/confirm-orphan", summary="确认保留本地部门")(confirm_orphan)
router.get("/user/page", summary="用户分页")(user_page)
router.get("/user/simple-page", summary="用户简表")(user_simple)
router.post("/user/create", summary="新建用户")(user_create)
router.put("/user/update-depts", summary="调整用户部门")(update_depts)
router.put("/user/update/{ident}", summary="修改用户")(user_update)
router.delete("/user/delete", summary="删除用户")(user_delete)
router.put("/user/update-status", summary="修改用户状态")(user_status)
router.post("/user/reset-password", summary="重置密码")(reset_password)
router.post("/user/kick", summary="强制下线")(kick)
router.post("/user/unlock", summary="解锁账号")(unlock)
router.post("/role/create", summary="新建角色")(role_create)
router.delete("/role/delete", summary="删除角色")(role_delete)
router.put("/role/update-status", summary="修改角色状态")(role_status)
router.post("/role/grant", summary="角色授权")(role_grant)
router.put("/role/data-scope", summary="保存角色数据范围")(role_scope)
router.get("/role/simple-list", summary="角色简表")(role_simple)
router.post("/menu/create", summary="新建菜单")(menu_create)
router.post("/dict/type/create", summary="新建字典类型")(dict_type_create)
router.post("/dict/data/create", summary="新建字典值")(dict_data_create)
router.put("/dict/data/update", summary="修改字典值")(dict_data_update)
router.delete("/dict/data/delete", summary="删除字典值")(dict_data_delete)
router.get("/param/list", summary="参数列表")(param_list)
router.put("/param/update", summary="修改参数")(param_update)
