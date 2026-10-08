"""CERT-S-R3 证件查看频次锁。

同一查看人、同一证件，滚动 1 小时内成功查看满 10 次后，下一次返回 1035。
被拦截的请求不写入成功审计，窗口内会继续拦截。其他证件不占用本证件额度。
"""

from datetime import timedelta

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import fail
from app.core import utcnow
from app.models import CertArchive, CertViewLog, User

VIEW_LIMIT = 10
WINDOW = timedelta(hours=1)
BLOCK_MSG = "1035 高频访问告警拦截（1 小时内同一证件查看超过 10 次）"


def recent_view_count(db: Session, actor: User, cert_id: int) -> int:
    since = utcnow() - WINDOW
    tenant = actor.tenant_id or 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(CertViewLog)
            .where(
                CertViewLog.deleted == 0,
                CertViewLog.tenant_id == tenant,
                CertViewLog.viewer_user_id == actor.id,
                CertViewLog.cert_id == cert_id,
                CertViewLog.created_at >= since,
            )
        )
        or 0
    )


def enforce_view_frequency(db: Session, actor: User, cert: CertArchive):
    if recent_view_count(db, actor, cert.id) >= VIEW_LIMIT:
        return fail(1035, BLOCK_MSG)
    return None


def record_cert_view(db: Session, actor: User, cert: CertArchive, watermark: str, request: Request) -> None:
    client = request.client
    ip = (client.host if client is not None else "") or ""
    device = (request.headers.get("user-agent") or "")[:256]
    now = utcnow()
    db.add(
        CertViewLog(
            cert_id=cert.id,
            viewer_user_id=actor.id,
            viewer_name=(actor.nickname or actor.username or "")[:64],
            view_level=2,
            watermark_text=watermark[:512],
            view_duration=0,
            ip=ip[:64],
            device=device,
            creator=actor.id,
            updater=actor.id,
            deleted=0,
            tenant_id=actor.tenant_id or 0,
            created_at=now,
            updated_at=now,
        )
    )
