"""站内信与钉钉通知。同一事件 24 小时内只投递一次。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.message.model import Message, NotifyRecord
from app.domains.system.model import Param
from app.integrations.dingtalk.client import send_work_notice


def send(receiver_id: int, title: str, content: str, event_type: str, biz_key: str) -> dict:
    return send_notify(receiver_id, title, content, event_type, biz_key)


def send_notify(receiver_id: int, title: str, content: str, event_type: str, biz_key: str) -> dict:
    receiver = int(receiver_id)
    session = get_session()
    if _recent_duplicate(receiver, event_type, biz_key):
        skipped = _record(event_type, biz_key, receiver, "SITE", "SKIPPED_DUP", title, content, 0)
        session.add(skipped)
        session.flush()
        return {"skipped": True, "status": "SKIPPED_DUP", "recordId": skipped.id, "messageId": None}
    message = Message(receiver_id=receiver, msg_type="SYSTEM", title=title or "", content=content or "", read_status="UNREAD")
    assert_dict_values(message)
    validate_refs_on_write(message)
    session.add(message)
    site = _record(event_type, biz_key, receiver, "SITE", "SENT", title, content, 0)
    session.add(site)
    session.flush()
    ding_status = _deliver_ding(event_type, biz_key, receiver, title, content)
    return {"skipped": False, "messageId": message.id, "dingStatus": ding_status, "siteStatus": "SENT"}


def retry_pending() -> int:
    """钉钉失败记录继续投递，累计 3 次后标记失败。"""
    session = get_session()
    now = now_naive()
    rows = list(
        session.scalars(
            select(NotifyRecord).where(
                NotifyRecord.channel == "DINGTALK",
                NotifyRecord.status == "RETRYING",
                NotifyRecord.retry_count < 3,
            )
        )
    )
    handled = 0
    for row in rows:
        if row.next_retry_at is not None and row.next_retry_at > now:
            continue
        handled += 1
        try:
            send_work_notice(str(row.receiver_id), row.title or "", row.content or "")
        except Exception:
            row.retry_count = int(row.retry_count or 0) + 1
            if row.retry_count >= 3:
                row.status = "FAILED"
                row.next_retry_at = None
            else:
                row.status = "RETRYING"
                row.next_retry_at = None
        else:
            row.status = "SENT"
            row.next_retry_at = None
    if handled:
        session.flush()
    return handled


def resend(record_id: int) -> dict:
    session = get_session()
    row = session.get(NotifyRecord, int(record_id))
    if row is None or row.deleted:
        raise BizError(1504)
    if row.status == "SENT":
        raise BizError(1001, "通知已发送，无需补发")
    try:
        if row.channel == "DINGTALK":
            send_work_notice(str(row.receiver_id), row.title or "", row.content or "")
    except Exception as exc:
        row.retry_count = int(row.retry_count or 0) + 1
        row.status = "FAILED"
        session.flush()
        raise BizError(5005, "通知补发失败") from exc
    row.status = "SENT"
    row.next_retry_at = None
    session.flush()
    return {"id": row.id, "status": row.status}


def my_page(page: Page, read_status: str = "ALL") -> dict:
    status = (read_status or "ALL").upper()
    if status not in {"UNREAD", "READ", "ALL"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "readStatus", "message": "阅读状态不正确"}]})
    uid = _uid()
    session = get_session()
    stmt = select(Message).where(Message.receiver_id == uid)
    if status != "ALL":
        stmt = stmt.where(Message.read_status == status)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(session.scalars(stmt.order_by(Message.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    return page_result([_message_view(row) for row in rows], int(total or 0), page)


def mark_read(message_id: int) -> dict:
    row = _own_message(int(message_id))
    if row.read_status != "READ":
        row.read_status = "READ"
        row.read_time = now_naive()
        get_session().flush()
    return _message_view(row)


def read_all() -> dict:
    uid = _uid()
    session = get_session()
    rows = list(session.scalars(select(Message).where(Message.receiver_id == uid, Message.read_status == "UNREAD")))
    current = now_naive()
    for row in rows:
        row.read_status = "READ"
        row.read_time = current
    if rows:
        session.flush()
    return {"count": len(rows)}


def unread_count() -> dict:
    uid = _uid()
    total = get_session().scalar(select(func.count()).select_from(Message).where(Message.receiver_id == uid, Message.read_status == "UNREAD"))
    return {"count": int(total or 0)}


def _deliver_ding(event_type: str, biz_key: str, receiver: int, title: str, content: str) -> str:
    session = get_session()
    if not _ding_enabled():
        row = _record(event_type, biz_key, receiver, "DINGTALK", "DISABLED", title, content, 0)
        session.add(row)
        session.flush()
        return "DISABLED"
    try:
        send_work_notice(str(receiver), title or "", content or "")
    except Exception:
        row = _record(event_type, biz_key, receiver, "DINGTALK", "RETRYING", title, content, 1)
        row.next_retry_at = None
        session.add(row)
        session.flush()
        return "RETRYING"
    row = _record(event_type, biz_key, receiver, "DINGTALK", "SENT", title, content, 0)
    session.add(row)
    session.flush()
    return "SENT"


def _recent_duplicate(receiver: int, event_type: str, biz_key: str) -> bool:
    since = now_naive() - timedelta(hours=24)
    row = get_session().scalar(
        select(NotifyRecord).where(
            NotifyRecord.event_type == event_type,
            NotifyRecord.biz_key == biz_key,
            NotifyRecord.receiver_id == receiver,
            NotifyRecord.status != "SKIPPED_DUP",
            NotifyRecord.create_time >= since,
        )
    )
    return row is not None


def _ding_enabled() -> bool:
    row = get_session().scalar(select(Param).where(Param.param_key == "dingtalk.notify.enabled"))
    if row is None or row.value is None or str(row.value).strip() == "":
        return True
    return str(row.value).strip().lower() in {"1", "true", "yes", "on"}


def _record(event_type, biz_key, receiver, channel, status, title, content, retry_count) -> NotifyRecord:
    return NotifyRecord(
        event_type=event_type or "",
        biz_key=biz_key or "",
        receiver_id=receiver,
        channel=channel,
        status=status,
        title=title or "",
        content=content or "",
        retry_count=retry_count,
    )


def _own_message(message_id: int) -> Message:
    uid = _uid()
    row = get_session().get(Message, message_id)
    if row is None or row.deleted or int(row.receiver_id) != uid:
        raise BizError(1504)
    return row


def _uid() -> int:
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    return int(ctx.user_id)


def _message_view(row: Message) -> dict:
    return {
        "id": row.id,
        "receiverId": row.receiver_id,
        "title": row.title,
        "content": row.content,
        "readStatus": row.read_status,
        "readTime": row.read_time.isoformat() if row.read_time else None,
        "msgType": row.msg_type,
    }
