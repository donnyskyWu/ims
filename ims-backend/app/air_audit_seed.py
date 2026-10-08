"""审计报表页的本地样例。只写 ims_mcp_log，不调用外部模型。"""

from sqlalchemy import select

from app.core import utcnow
from app.models import AirMcpLog, User

ASSEMBLE_MARKER = "e2e-s8-11"
LIST_MARKER = "e2e-s8-11-list"


def ensure_air_mcp_audit_fixture(db) -> None:
    exists = db.scalar(select(AirMcpLog.id).where(AirMcpLog.param_digest == ASSEMBLE_MARKER))
    if exists is not None:
        return
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    if admin is None:
        return
    now = utcnow()
    tenant_id = admin.tenant_id or 0
    db.add(
        AirMcpLog(
            key_id=0,
            user_id=admin.id,
            tool="experts.assemble",
            param_digest=ASSEMBLE_MARKER,
            result_code="0",
            cost_ms=128,
            token_cnt=0,
            filter_hit=1,
            tenant_id=tenant_id,
            created_at=now,
        )
    )
    db.add(
        AirMcpLog(
            key_id=0,
            user_id=admin.id,
            tool="skills.list",
            param_digest=LIST_MARKER,
            result_code="0",
            cost_ms=16,
            token_cnt=0,
            filter_hit=0,
            tenant_id=tenant_id,
            created_at=now,
        )
    )
    db.flush()
