"""站内信与通知补发。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.domains.message import service

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


@mark(login_only=True, summary="发送消息")
def message_send():
    body = _body()
    return service.send(
        int(body["receiverId"]),
        body.get("title") or "",
        body.get("content") or "",
        body.get("eventType") or "",
        body.get("bizKey") or "",
    )


@mark(login_only=True, summary="我的消息")
def message_my_page():
    request = current_request()
    page = parse_page(dict(request.query_params))
    return service.my_page(page, request.query_params.get("readStatus") or "ALL")


@mark(login_only=True, summary="标记已读")
def message_read():
    return service.mark_read(int(_body()["id"]))


@mark(login_only=True, summary="全部已读")
def message_read_all():
    return service.read_all()


@mark(login_only=True, summary="未读数量")
def message_unread_count():
    return service.unread_count()


@mark(perm="ims:system:notify:resend", summary="补发通知")
def notify_resend():
    return service.resend(int(_body()["id"]))


router.post("/send", summary="发送消息")(message_send)
router.get("/my/page", summary="我的消息")(message_my_page)
router.post("/read", summary="标记已读")(message_read)
router.post("/read-all", summary="全部已读")(message_read_all)
router.get("/unread-count", summary="未读数量")(message_unread_count)
router.post("/notify/resend", summary="补发通知")(notify_resend)
