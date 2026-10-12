"""我的待办。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.domains.todo import service

router = APIRouter()


@mark(login_only=True, summary="我的待办")
def todo_my_page():
    request = current_request()
    page = parse_page(dict(request.query_params))
    return service.my_page(page, request.query_params.get("status"))


@mark(login_only=True, summary="待办数量")
def todo_my_count():
    return service.my_count()


router.get("/my/page", summary="我的待办")(todo_my_page)
router.get("/my/count", summary="待办数量")(todo_my_count)
