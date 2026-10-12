"""公司、实名人、手机卡。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.resource import company, realname, sim

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


def _id(ident: str) -> int:
    return int(parse_api_id(ident))


@mark(perm="ims:corp:company:query", summary="公司列表")
def company_page():
    return company.page(_page(), _params())


@mark(perm="ims:corp:company:export", summary="导出公司", operate=("公司", "导出"))
def company_export():
    return company.export(_params())


@mark(perm="ims:corp:company:create", summary="新建公司", operate=("公司", "新建"))
def company_create():
    return company.create(_body())


@mark(perm="ims:corp:company:query", summary="公司详情")
def company_detail(ident: str):
    return company.detail(_id(ident))


@mark(perm="ims:corp:company:update", summary="编辑公司", operate=("公司", "编辑"))
def company_update(ident: str):
    return company.update(_id(ident), _body())


@mark(perm="ims:corp:company:update", summary="停用或启用公司", operate=("公司", "启停"))
def company_status(ident: str):
    return company.set_status(_id(ident), _body())


@mark(perm="ims:corp:company:delete", summary="删除公司", operate=("公司", "删除"))
def company_delete(ident: str):
    return company.remove(_id(ident))


@mark(perm="ims:corp:company:capacity", summary="调整公众号容量", operate=("公司", "容量"))
def company_capacity(ident: str):
    return company.adjust_capacity(_id(ident), _body())


@mark(perm="ims:corp:realname:query", summary="实名人列表")
def realname_page():
    return realname.page(_page(), _params())


@mark(perm="ims:corp:realname:export", summary="导出实名人", operate=("实名人", "导出"))
def realname_export():
    return realname.export(_params())


@mark(perm="ims:corp:realname:create", summary="新增实名人", operate=("实名人", "新增"))
def realname_create():
    return realname.create(_body())


@mark(perm="ims:corp:realname:query", summary="实名人详情")
def realname_detail(ident: str):
    return realname.detail(_id(ident))


@mark(perm="ims:corp:realname:plain", summary="实名人明文", operate=("实名人", "明文"))
def realname_plain(ident: str):
    return realname.plain(_id(ident))


@mark(perm="ims:corp:realname:update", summary="编辑实名人", operate=("实名人", "编辑"))
def realname_update(ident: str):
    return realname.update(_id(ident), _body())


@mark(perm="ims:corp:realname:update", summary="停用或启用实名人", operate=("实名人", "启停"))
def realname_status(ident: str):
    return realname.set_status(_id(ident), _body())


@mark(perm="ims:corp:realname:delete", summary="删除实名人", operate=("实名人", "删除"))
def realname_delete(ident: str):
    return realname.remove(_id(ident))


@mark(perm="ims:corp:sim:query", summary="手机卡列表")
def sim_page():
    return sim.page(_page(), _params())


@mark(perm="ims:corp:sim:export", summary="导出手机卡", operate=("手机卡", "导出"))
def sim_export():
    return sim.export(_params())


@mark(perm="ims:corp:sim:create", summary="新增手机卡", operate=("手机卡", "新增"))
def sim_create():
    return sim.create(_body())


@mark(perm="ims:corp:sim:query", summary="手机卡详情")
def sim_detail(ident: str):
    return sim.detail(_id(ident))


@mark(perm="ims:corp:sim:plain", summary="手机卡明文", operate=("手机卡", "明文"))
def sim_plain(ident: str):
    return sim.plain(_id(ident))


@mark(perm="ims:corp:sim:update", summary="编辑手机卡", operate=("手机卡", "编辑"))
def sim_update(ident: str):
    return sim.update(_id(ident), _body())


@mark(perm="ims:corp:sim:update", summary="停用或启用手机卡", operate=("手机卡", "启停"))
def sim_status(ident: str):
    return sim.set_status(_id(ident), _body())


@mark(perm="ims:corp:sim:delete", summary="删除手机卡", operate=("手机卡", "删除"))
def sim_delete(ident: str):
    return sim.remove(_id(ident))


router.get("/company/page", summary="公司列表")(company_page)
router.get("/company/export", summary="导出公司")(company_export)
router.post("/company", summary="新建公司")(company_create)
router.get("/company/{ident}", summary="公司详情")(company_detail)
router.put("/company/{ident}", summary="编辑公司")(company_update)
router.put("/company/{ident}/status", summary="停用或启用公司")(company_status)
router.delete("/company/{ident}", summary="删除公司")(company_delete)
router.put("/company/{ident}/capacity", summary="调整公众号容量")(company_capacity)
router.get("/realname/page", summary="实名人列表")(realname_page)
router.get("/realname/export", summary="导出实名人")(realname_export)
router.post("/realname", summary="新增实名人")(realname_create)
router.get("/realname/{ident}", summary="实名人详情")(realname_detail)
router.get("/realname/{ident}/plain", summary="实名人明文")(realname_plain)
router.put("/realname/{ident}", summary="编辑实名人")(realname_update)
router.put("/realname/{ident}/status", summary="停用或启用实名人")(realname_status)
router.delete("/realname/{ident}", summary="删除实名人")(realname_delete)
router.get("/sim-card/page", summary="手机卡列表")(sim_page)
router.get("/sim-card/export", summary="导出手机卡")(sim_export)
router.post("/sim-card", summary="新增手机卡")(sim_create)
router.get("/sim-card/{ident}", summary="手机卡详情")(sim_detail)
router.get("/sim-card/{ident}/plain", summary="手机卡明文")(sim_plain)
router.put("/sim-card/{ident}", summary="编辑手机卡")(sim_update)
router.put("/sim-card/{ident}/status", summary="停用或启用手机卡")(sim_status)
router.delete("/sim-card/{ident}", summary="删除手机卡")(sim_delete)
