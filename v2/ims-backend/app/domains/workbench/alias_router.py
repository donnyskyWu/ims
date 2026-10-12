"""AUTH 契约路径的只读/关闭别名，逻辑仍走 todo/my 与 message/my。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.message import service as message_service
from app.domains.todo import service as todo_service

router = APIRouter()


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(login_only=True, summary="工作台待办别名")
def alias_todos():
    request = current_request()
    params = dict(request.query_params)
    page = parse_page(params)
    return todo_service.my_page(
        page,
        params.get("status"),
        todo_type=params.get("type"),
        keyword=params.get("keyword"),
        overdue=params.get("overdue"),
    )


@mark(login_only=True, summary="工作台消息别名")
def alias_messages():
    request = current_request()
    params = dict(request.query_params)
    page = parse_page(params)
    return message_service.my_page(page, params.get("readStatus") or "ALL", params.get("keyword"))


@mark(login_only=True, summary="工作台消息全部已读别名")
def alias_read_all():
    return message_service.read_all()


@mark(login_only=True, summary="工作台消息已读别名")
def alias_message_read(ident: str):
    return message_service.mark_read(parse_api_id(ident))


@mark(login_only=True, summary="工作台待办详情别名")
def alias_todo_get(ident: str):
    return todo_service.detail(parse_api_id(ident))


@mark(login_only=True, operate=("待办", "关闭待办"), summary="工作台关闭待办别名")
def alias_todo_complete(ident: str):
    return todo_service.complete_mine(parse_api_id(ident), _body().get("remark"))


router.get("/workbench/todos", summary="工作台待办别名")(alias_todos)
router.get("/workbench/messages", summary="工作台消息别名")(alias_messages)
router.post("/workbench/messages/read-all", summary="工作台消息全部已读别名")(alias_read_all)
router.post("/workbench/messages/{ident}/read", summary="工作台消息已读别名")(alias_message_read)
router.get("/workbench/todos/{ident}", summary="工作台待办详情别名")(alias_todo_get)
router.post("/workbench/todos/{ident}", summary="工作台关闭待办别名")(alias_todo_complete)
