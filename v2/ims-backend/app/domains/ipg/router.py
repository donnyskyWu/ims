"""IP 组与作者。静态路径写在编号路径前面。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.domains.ipg import service

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


def _params() -> dict:
    return dict(current_request().query_params)


def _page():
    params = _params()
    if not params.get("pageSize"):
        params["pageSize"] = 20
    return parse_page(params)


@mark(perm="ims:ip-group:query", summary="IP 组全量树")
def group_tree():
    return service.tree()


@mark(perm="ims:ip-group:query", summary="IP 组可访问树")
def group_accessible():
    return service.accessible_tree()


@mark(perm="ims:ip-group:query", summary="IP 组列表")
def group_list():
    return service.list_groups(_page(), _params())


@mark(perm="ims:ip-group:create", idempotent=True, summary="创建 IP 组", operate=("IP组", "创建"))
def group_create():
    return service.create_group(_body())


@mark(perm="ims:ip-group:update", summary="更新 IP 组", operate=("IP组", "更新"))
def group_update():
    return service.update_group(_body())


@mark(perm="ims:ip-group:delete", summary="删除 IP 组", operate=("IP组", "删除"))
def group_delete():
    return service.remove_group(_params().get("id"))


@mark(perm="ims:ip-group:author:query", summary="作者分页")
def author_page():
    return service.author_page(_page(), _params())


@mark(perm="ims:ip-group:author:export", summary="导出作者", operate=("作者", "导出"))
def author_export():
    return service.author_export(_params())


@mark(perm="ims:ip-group:author:create", idempotent=True, summary="新建作者", operate=("作者", "新建"))
def author_create():
    return service.create_author(_body())


@mark(perm="ims:ip-group:author:query", summary="作者详情")
def author_detail(ident: str):
    return service.author_detail(ident)


@mark(perm="ims:ip-group:author:update", summary="编辑作者", operate=("作者", "编辑"))
def author_update(ident: str):
    return service.update_author(ident, _body())


@mark(perm="ims:ip-group:author:update", summary="启停作者", operate=("作者", "启停"))
def author_status(ident: str):
    return service.author_status(ident, _body())


@mark(perm="ims:ip-group:author:delete", summary="删除作者", operate=("作者", "删除"))
def author_delete(ident: str):
    return service.remove_author(ident)


@mark(perm="ims:ip-group:query", summary="IP 组成员")
def member_list(ident: str):
    return service.members(ident)


@mark(perm="ims:ip-group:member", idempotent=True, summary="添加成员", operate=("IP组成员", "添加"))
def member_add(ident: str):
    return service.add_member(ident, _body())


@mark(perm="ims:ip-group:member", summary="修改成员", operate=("IP组成员", "修改"))
def member_update(ident: str, member_id: str):
    return service.update_member(ident, member_id, _body())


@mark(perm="ims:ip-group:member", summary="移除成员", operate=("IP组成员", "移除"))
def member_delete(ident: str, member_id: str):
    return service.remove_member(ident, member_id)


@mark(perm="ims:ip-group:query", summary="IP 组账号")
def account_list(ident: str):
    return service.accounts(ident)


@mark(perm="ims:ip-group:account", idempotent=True, summary="绑定账号", operate=("IP组账号", "绑定"))
def account_bind(ident: str):
    return service.bind_accounts(ident, _body())


@mark(perm="ims:ip-group:account", summary="解绑账号", operate=("IP组账号", "解绑"))
def account_unbind(ident: str, account_id: str):
    return service.unbind_account(ident, account_id)


@mark(perm="ims:ip-group:query", summary="IP 组关联作者")
def anchor_list(ident: str):
    return service.anchors(ident)


@mark(perm="ims:ip-group:anchor", idempotent=True, summary="关联作者", operate=("IP组作者", "关联"))
def anchor_add(ident: str):
    return service.add_anchors(ident, _body())


@mark(perm="ims:ip-group:anchor", summary="设置主作者", operate=("IP组作者", "设主作者"))
def anchor_primary(ident: str, rel_id: str):
    return service.set_primary(ident, rel_id)


@mark(perm="ims:ip-group:anchor", summary="移除关联作者", operate=("IP组作者", "移除"))
def anchor_delete(ident: str, rel_id: str):
    return service.remove_anchor(ident, rel_id)


@mark(perm="ims:ip-group:query", summary="IP 组统计")
def group_stats(ident: str):
    return service.stats(ident)


router.get("/ip-group/tree", summary="IP 组全量树")(group_tree)
router.get("/ip-group/accessible-tree", summary="IP 组可访问树")(group_accessible)
router.get("/ip-group/list", summary="IP 组列表")(group_list)
router.post("/ip-group/create", summary="创建 IP 组")(group_create)
router.put("/ip-group/update", summary="更新 IP 组")(group_update)
router.delete("/ip-group/delete", summary="删除 IP 组")(group_delete)
router.get("/ip-group/author/page", summary="作者分页")(author_page)
router.get("/ip-group/author/export", summary="导出作者")(author_export)
router.post("/ip-group/author", summary="新建作者")(author_create)
router.get("/ip-group/author/{ident}", summary="作者详情")(author_detail)
router.put("/ip-group/author/{ident}", summary="编辑作者")(author_update)
router.put("/ip-group/author/{ident}/status", summary="启停作者")(author_status)
router.delete("/ip-group/author/{ident}", summary="删除作者")(author_delete)
router.get("/ip-group/{ident}/members", summary="IP 组成员")(member_list)
router.post("/ip-group/{ident}/members", summary="添加成员")(member_add)
router.put("/ip-group/{ident}/members/{member_id}", summary="修改成员")(member_update)
router.delete("/ip-group/{ident}/members/{member_id}", summary="移除成员")(member_delete)
router.get("/ip-group/{ident}/accounts", summary="IP 组账号")(account_list)
router.post("/ip-group/{ident}/accounts", summary="绑定账号")(account_bind)
router.delete("/ip-group/{ident}/accounts/{account_id}", summary="解绑账号")(account_unbind)
router.get("/ip-group/{ident}/anchors", summary="IP 组关联作者")(anchor_list)
router.post("/ip-group/{ident}/anchors", summary="关联作者")(anchor_add)
router.put("/ip-group/{ident}/anchors/{rel_id}/primary", summary="设置主作者")(anchor_primary)
router.delete("/ip-group/{ident}/anchors/{rel_id}", summary="移除关联作者")(anchor_delete)
router.get("/ip-group/{ident}/stats", summary="IP 组统计")(group_stats)
