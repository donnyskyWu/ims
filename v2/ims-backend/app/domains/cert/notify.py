"""证件预警、催办与驳回通知。站内消息进工作台，钉钉走工作通知。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.message.model import Message, NotifyRecord
from app.domains.system.model import Param
from app.integrations.dingtalk.client import send_work_notice

_DEFAULTS = {
    "notify.cert.yellow": ("证件即将到期", "证件将在 30 天内到期，请尽快换证。"),
    "notify.cert.red": ("证件即将到期", "证件将在 7 天内到期，请立即换证。"),
    "notify.cert.locked": ("证件已锁定", "证件已过期并锁定，请完成换证。"),
    "notify.cert.remind": ("证件换证催办", "请尽快办理证件换证。"),
    "notify.cert.reject": ("证件审核未通过", "证件审核未通过，请重新上传。"),
}


def template(key: str) -> tuple[str, str]:
    row = get_session().scalar(select(Param).where(Param.param_key == key))
    title, content = _DEFAULTS.get(key, ("证件通知", "请处理证件事项。"))
    if row is not None and (row.value or "").strip():
        content = row.value.strip()
    return title, content


def deep_link(cert_id: int, tab: str = "expire") -> str:
    return f"/ims/corp/resource/certificate?tab={tab}&certId={cert_id}"


def deliver(user_ids: list[int], key: str, event_type: str, biz_key: str, route: str, channels: set[str], extra: str = "", title: str | None = None, content: str | None = None) -> list[int]:
    default_title, default_content = template(key)
    title = title or default_title
    content = content or default_content
    if extra:
        content = f"{content}{extra}"
    sent = []
    session = get_session()
    for raw in user_ids:
        uid = int(raw)
        if uid <= 0 or uid in sent:
            continue
        sent.append(uid)
        if "SITE" in channels:
            message = Message(
                receiver_id=uid,
                msg_type="SYSTEM",
                title=title,
                content=content,
                route=route,
                source_module="cert",
                read_status="UNREAD",
            )
            assert_dict_values(message)
            validate_refs_on_write(message)
            session.add(message)
            session.add(_record(event_type, biz_key, uid, "SITE", "SENT", title, content))
        if "DINGTALK" in channels:
            status = "SENT"
            try:
                send_work_notice(str(uid), title, content)
            except Exception:
                status = "RETRYING"
            session.add(_record(event_type, biz_key, uid, "DINGTALK", status, title, content))
    if sent:
        session.flush()
    return sent


def _record(event_type: str, biz_key: str, receiver: int, channel: str, status: str, title: str, content: str) -> NotifyRecord:
    return NotifyRecord(
        event_type=event_type,
        biz_key=biz_key,
        receiver_id=receiver,
        channel=channel,
        status=status,
        title=title,
        content=content,
        retry_count=1 if status == "RETRYING" else 0,
        next_retry_at=None,
    )


def stamp() -> str:
    return now_naive().strftime("%Y-%m-%d %H:%M:%S")
