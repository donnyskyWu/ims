"""我的待办。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.errors import BizError
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.todo import service

router = APIRouter()


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(login_only=True, summary="我的待办")
def todo_my_page():
    request = current_request()
    params = dict(request.query_params)
    page = parse_page(params)
    return service.my_page(page, params.get("status"), todo_type=params.get("type"), keyword=params.get("keyword"), overdue=params.get("overdue"))


@mark(login_only=True, summary="待办数量")
def todo_my_count():
    return service.my_count()


@mark(login_only=True, operate=("待办", "关闭待办"), summary="关闭待办")
def todo_my_complete():
    body = _body()
    if body.get("id") in (None, ""):
        raise BizError(1001, data={"fieldErrors": [{"field": "id", "message": "请选择待办"}]})
    return service.complete_mine(parse_api_id(body["id"]), body.get("remark"))


@mark(login_only=True, summary="待办详情")
def todo_my_get(ident: str):
    intent = (current_request().query_params.get("intent") or "").strip().lower()
    todo_id = parse_api_id(ident)
    if intent == "open":
        return service.open_mine(todo_id)
    return service.detail(todo_id)


router.get("/my/page", summary="我的待办")(todo_my_page)
router.get("/my/count", summary="待办数量")(todo_my_count)
router.post("/my/complete", summary="关闭待办")(todo_my_complete)
router.get("/my/{ident}", summary="待办详情")(todo_my_get)
