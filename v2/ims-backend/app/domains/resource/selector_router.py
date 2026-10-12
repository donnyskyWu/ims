"""主数据选择器。空列表返回提示码，由前端静默处理。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.domains.resource import selector

router = APIRouter()


def _params() -> dict:
    return dict(current_request().query_params)


def _page():
    params = _params()
    if not params.get("pageSize"):
        params["pageSize"] = 20
    return parse_page(params)


@mark(login_only=True, summary="公司选择器")
def selector_company():
    return selector.companies(_page(), _params())


@mark(login_only=True, summary="实名人选择器")
def selector_person():
    return selector.persons(_page(), _params())


@mark(login_only=True, summary="手机卡选择器")
def selector_sim():
    return selector.sim_cards(_page(), _params())


@mark(login_only=True, summary="手机选择器")
def selector_phone():
    from app.domains.device.phone import selector as phone_selector

    return phone_selector(_page(), _params())


@mark(login_only=True, summary="资产选择器")
def selector_asset():
    from app.domains.device.ledger import selector as asset_selector

    return asset_selector(_page(), _params())


router.get("/selector/company", summary="公司选择器")(selector_company)
router.get("/selector/person", summary="实名人选择器")(selector_person)
router.get("/selector/sim-card", summary="手机卡选择器")(selector_sim)
router.get("/selector/phone", summary="手机选择器")(selector_phone)
router.get("/selector/asset", summary="资产选择器")(selector_asset)
