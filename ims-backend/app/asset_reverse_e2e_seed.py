"""#72 账号/场次反查 E2E 种子：稳定场次 IMS20261008DYE0072，挂在 AC-E2E-FIN 上。

#75 另备已注销账号、已取消场次，以及带下播成本的场次，供登记关联校验和成本层展示。
只写既有直播场次 / 下播报告表，不改 live 登记接口。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.live_fin_e2e_seed import E2E_FIN_ACCOUNT_NO, ensure_live_fin_e2e_deps
from app.models import LiveReport, LiveSession, User
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

E2E_ASSET_SESSION_CODE = "IMS20261008DYE0072"
E2E_ASSET_OFF_ACCOUNT = "AC-E2E-ASSET-OFF"
E2E_ASSET_CANCEL_SESSION = "IMS20261008DYE0075"
E2E_ASSET_LAYER_SESSION = "IMS20261008DYE0076"
E2E_ASSET_LAYER_REVENUE = 12800.0
E2E_ASSET_LAYER_COST = 1860.0


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


def _upsert_session(
    db: Session,
    admin: User,
    code: str,
    account_id: int,
    account_no: str,
    realname_id: int,
    status: str,
    topic: str,
) -> None:
    row = db.scalar(select(LiveSession).where(LiveSession.session_code == code, LiveSession.deleted == 0))
    if row is None:
        db.add(
            LiveSession(
                session_code=code,
                account_id=account_id,
                account_no=account_no,
                realname_person_id=realname_id,
                realname_name="E2E财务实名人",
                responsible_user_id=admin.id,
                device_asset_ids="[]",
                platform="DOUYIN",
                topic=topic,
                plan_start_time="2026-10-08 10:00:00",
                plan_end_time="2026-10-08 12:00:00",
                session_status=status,
                creator=admin.id,
                deleted=0,
                tenant_id=admin.tenant_id or 0,
            )
        )
        return
    row.account_id = account_id
    row.account_no = account_no
    row.realname_person_id = realname_id
    row.session_status = status
    row.deleted = 0
    row.tenant_id = admin.tenant_id or 0


def _upsert_report(db: Session, admin: User, code: str) -> None:
    row = db.scalar(select(LiveReport).where(LiveReport.session_code == code, LiveReport.deleted == 0))
    if row is None:
        db.add(
            LiveReport(
                session_code=code,
                gmv=E2E_ASSET_LAYER_REVENUE,
                ad_cost=E2E_ASSET_LAYER_COST,
                entry_status="SUBMITTED",
                entry_user_id=admin.id,
                tenant_id=admin.tenant_id or 0,
                deleted=0,
            )
        )
        return
    row.gmv = E2E_ASSET_LAYER_REVENUE
    row.ad_cost = E2E_ASSET_LAYER_COST
    row.deleted = 0
    row.tenant_id = admin.tenant_id or 0


def ensure_asset_verify_e2e_links(db: Session, admin: User) -> None:
    """已注销账号、已取消场次、带成本的正常场次。供办公设备登记校验和场次/成本层。"""
    ensure_live_fin_e2e_deps(db, admin)
    ops = ops_session()
    try:
        fin = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_FIN_ACCOUNT_NO,
                PlatformAccount.deleted == 0,
            )
        )
        if fin is None:
            return
        off = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_ASSET_OFF_ACCOUNT,
                PlatformAccount.deleted == 0,
            )
        )
        if off is None:
            ops.add(
                PlatformAccount(
                    account_no=E2E_ASSET_OFF_ACCOUNT,
                    account_name="E2E资产已注销账号",
                    platform_type="DOUYIN",
                    realname_id=fin.realname_id,
                    holder_user_id=admin.id,
                    status="CANCELLED",
                    tenant_id=0,
                )
            )
        else:
            off.status = "CANCELLED"
            off.realname_id = fin.realname_id
            off.deleted = 0
        ops.commit()
        account_id = int(fin.id)
        account_no = fin.account_no or E2E_FIN_ACCOUNT_NO
        realname_id = int(fin.realname_id or 0)
    finally:
        ops.close()
    _upsert_session(
        db,
        admin,
        E2E_ASSET_CANCEL_SESSION,
        account_id,
        account_no,
        realname_id,
        "CANCELLED",
        "资产校验已取消场次",
    )
    _upsert_session(
        db,
        admin,
        E2E_ASSET_LAYER_SESSION,
        account_id,
        account_no,
        realname_id,
        "ENDED",
        "资产校验场次层",
    )
    _upsert_report(db, admin, E2E_ASSET_LAYER_SESSION)


def refresh_asset_reverse_e2e_session(db: Session, admin: User) -> None:
    if admin.username != "admin":
        return
    ensure_asset_reverse_e2e_session(db, admin)
    ensure_asset_verify_e2e_links(db, admin)
