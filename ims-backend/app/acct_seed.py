"""CORP 账号领用 E2E 种子：池内抖音号 AC-E2E-POOL（幂等 / 可 refresh）。"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import engine
from app.models import AccountApply, AccountTimelineEvent, User
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount


def ensure_acct_schema() -> None:
    AccountApply.__table__.create(engine, checkfirst=True)
    AccountTimelineEvent.__table__.create(engine, checkfirst=True)

E2E_POOL_ACCOUNT_NO = "AC-E2E-POOL"
E2E_POOL_NICK = "E2E池内抖音"


def _pool_row(ops) -> PlatformAccount | None:
    return ops.scalar(
        select(PlatformAccount).where(
            PlatformAccount.account_no == E2E_POOL_ACCOUNT_NO,
            PlatformAccount.deleted == 0,
        )
    )


def ensure_acct_e2e_pool_account(db: Session, admin: User) -> None:
    ops = ops_session()
    try:
        row = _pool_row(ops)
        if row is not None:
            return
        company = ops.scalar(select(Company).where(Company.deleted == 0).limit(1))
        group = ops.scalar(select(IpGroup).where(IpGroup.deleted == 0).limit(1))
        if company is None or group is None:
            company = Company(company_name="E2E领用公司", status="ENABLED", tenant_id=0)
            group = IpGroup(group_name="E2E领用组", status="ENABLED", tenant_id=0)
            ops.add_all([company, group])
            ops.flush()
        ops.add(
            PlatformAccount(
                account_no=E2E_POOL_ACCOUNT_NO,
                account_name=E2E_POOL_NICK,
                platform_type="DOUYIN",
                ip_group_id=group.id,
                company_id=company.id,
                holder_user_id=admin.id,
                status="IN_POOL",
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()


def refresh_acct_e2e_pool(db: Session, admin: User) -> None:
    """E2E 跑前恢复池内账号与清空该账号流程单据。"""
    if admin.username != "admin":
        return
    ensure_acct_schema()
    ensure_acct_e2e_pool_account(db, admin)
    ops = ops_session()
    try:
        row = _pool_row(ops)
        if row is None:
            return
        row.status = "IN_POOL"
        row.holder_user_id = admin.id
        account_id = row.id
        ops.commit()
    finally:
        ops.close()
    db.execute(delete(AccountTimelineEvent).where(AccountTimelineEvent.account_id == account_id))
    db.execute(delete(AccountApply).where(AccountApply.account_id == account_id))
