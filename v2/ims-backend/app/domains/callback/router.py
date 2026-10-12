"""钉钉事件回调。验签失败不入库。"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter
from sqlalchemy import select

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.config import get_settings
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.auth.model import OrgSyncEvent

router = APIRouter()


@mark(anonymous=True, summary="钉钉事件回调")
def dingtalk_event():
    request = current_request()
    raw = getattr(request.state, "raw_body", b"") or b""
    secret = str((get_settings().dingtalk or {}).get("app_secret") or "")
    expect = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    given = request.headers.get("x-dingtalk-signature") or ""
    if not hmac.compare_digest(expect, given):
        raise BizError(1008)
    body = getattr(request.state, "json_body", None) or {}
    event_id = str(body.get("eventId") or "")
    exists = get_session().scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id).execution_options(skip_tenant=True, include_deleted=True))
    if exists is None:
        from app.core.clock import parse_input_datetime

        event_time = None
        if body.get("eventTime"):
            event_time = parse_input_datetime(str(body["eventTime"]))
        get_session().add(
            OrgSyncEvent(
                event_id=event_id,
                event_type=str(body.get("eventType") or ""),
                event_time=event_time,
                payload=body,
                status="PENDING",
                tenant_id=1,
            )
        )
    return {"accepted": True}


router.post("/dingtalk/event", summary="钉钉事件回调")(dingtalk_event)
