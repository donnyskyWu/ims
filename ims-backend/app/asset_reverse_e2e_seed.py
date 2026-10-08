"""#72 账号/场次反查 E2E 种子：稳定场次 IMS20261008DYE0072，挂在 AC-E2E-FIN 上。

只读既有直播场次表，不改 live 登记接口。场次不存在时补一行，已存在则保持。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.live_fin_e2e_seed import E2E_FIN_ACCOUNT_NO, ensure_live_fin_e2e_deps
from app.models import LiveSession, User
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

E2E_ASSET_SESSION_CODE = "IMS20261008DYE0072"


def ensure_asset_reverse_e2e_session(db: Session, admin: User) -> None:
    ensure_live_fin_e2e_deps(db, admin)
    ops = ops_session()
    try:
        account = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_FIN_ACCOUNT_NO,
                PlatformAccount.deleted == 0,
            )
        )
    finally:
        ops.close()
    if account is None:
        return
    existing = db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == E2E_ASSET_SESSION_CODE,
            LiveSession.deleted == 0,
        )
    )
    if existing is not None:
        return
    db.add(
        LiveSession(
            session_code=E2E_ASSET_SESSION_CODE,
            account_id=account.id,
            account_no=account.account_no,
            realname_person_id=account.realname_id or 0,
            realname_name="E2E财务实名人",
            responsible_user_id=admin.id,
            device_asset_ids="[]",
            platform="DOUYIN",
            topic="资产反查种子场次",
            plan_start_time="2026-10-08 10:00:00",
            plan_end_time="2026-10-08 12:00:00",
            session_status="ENDED",
            creator=admin.id,
            deleted=0,
            tenant_id=admin.tenant_id or 0,
        )
    )


def refresh_asset_reverse_e2e_session(db: Session, admin: User) -> None:
    if admin.username != "admin":
        return
    ensure_asset_reverse_e2e_session(db, admin)
