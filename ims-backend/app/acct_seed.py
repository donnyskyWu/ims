"""CORP 账号领用 E2E 种子：池内抖音号 AC-E2E-POOL（幂等 / 可 refresh）。"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import engine
from app.models import (
    AccountApply,
    AccountRecharge,
    AccountRechargeVerify,
    AccountTimelineEvent,
    AccountTransfer,
    Role,
    RoleMenu,
    RolePerm,
    Todo,
    User,
    UserDept,
    UserRole,
    WorkMessage,
)
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount


def ensure_acct_schema() -> None:
    AccountApply.__table__.create(engine, checkfirst=True)
    AccountTimelineEvent.__table__.create(engine, checkfirst=True)
    AccountRecharge.__table__.create(engine, checkfirst=True)
    AccountRechargeVerify.__table__.create(engine, checkfirst=True)
    AccountTransfer.__table__.create(engine, checkfirst=True)

E2E_POOL_ACCOUNT_NO = "AC-E2E-POOL"
E2E_POOL_NICK = "E2E池内抖音"
E2E_XFER_ACCOUNT_NO = "AC-E2E-XFER"
E2E_XFER_NICK = "E2E流转抖音"
E2E_RECALL_ACCOUNT_NO = "AC-E2E-RECALL"
E2E_RECALL_NICK = "E2E收回抖音"
E2E_UNFREEZE_ACCOUNT_NO = "AC-E2E-UNFREEZE"
E2E_UNFREEZE_NICK = "E2E解冻抖音"
E2E_RECON_ACCOUNT_NO = "AC-E2E-RECON"
E2E_RECON_NICK = "E2E核对抖音"
E2E_SUM_ACCOUNT_NO = "AC-E2E-SUM"
E2E_SUM_NICK = "E2E汇总抖音"
E2E_SUM_DEPT_USER = "e2e_acct_sum"
E2E_SUM_DEPT_NICK = "汇总部门"
E2E_SUM_DEPT_ID = 70070
E2E_ACCT_FINANCE_USER = "e2e_acct_r3"
E2E_ACCT_PEER_USER = "e2e_acct_peer"
E2E_ACCT_PEER_NICK = "流转同事"
FINANCE_ROLE_KEY = "acct:r3"
PEER_ROLE_KEY = "acct:peer"


def _account_row(ops, account_no: str) -> PlatformAccount | None:
    return ops.scalar(
        select(PlatformAccount).where(
            PlatformAccount.account_no == account_no,
            PlatformAccount.deleted == 0,
        )
    )


def _pool_row(ops) -> PlatformAccount | None:
    return _account_row(ops, E2E_POOL_ACCOUNT_NO)


def _ensure_named_account(ops, admin: User, account_no: str, nick: str) -> None:
    if _account_row(ops, account_no) is not None:
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
            account_no=account_no,
            account_name=nick,
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            holder_user_id=admin.id,
            status="IN_POOL",
            tenant_id=0,
        )
    )


def ensure_acct_e2e_pool_account(db: Session, admin: User) -> None:
    ops = ops_session()
    try:
        _ensure_named_account(ops, admin, E2E_POOL_ACCOUNT_NO, E2E_POOL_NICK)
        _ensure_named_account(ops, admin, E2E_XFER_ACCOUNT_NO, E2E_XFER_NICK)
        _ensure_named_account(ops, admin, E2E_RECALL_ACCOUNT_NO, E2E_RECALL_NICK)
        _ensure_named_account(ops, admin, E2E_UNFREEZE_ACCOUNT_NO, E2E_UNFREEZE_NICK)
        _ensure_named_account(ops, admin, E2E_RECON_ACCOUNT_NO, E2E_RECON_NICK)
        _ensure_named_account(ops, admin, E2E_SUM_ACCOUNT_NO, E2E_SUM_NICK)
        ops.commit()
    finally:
        ops.close()


def _clone_admin_perms(db: Session, role_id: int) -> None:
    admin_role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
    if admin_role is None:
        return
    for rm in db.scalars(select(RoleMenu).where(RoleMenu.role_id == admin_role.id)).all():
        if db.scalar(select(RoleMenu).where(RoleMenu.role_id == role_id, RoleMenu.menu_id == rm.menu_id)):
            continue
        db.add(RoleMenu(role_id=role_id, menu_id=rm.menu_id, perm_code=rm.perm_code, tenant_id=rm.tenant_id))
    for rp in db.scalars(select(RolePerm).where(RolePerm.role_id == admin_role.id)).all():
        exists = db.scalar(
            select(RolePerm).where(RolePerm.role_id == role_id, RolePerm.perm_code == rp.perm_code)
        )
        if exists is None:
            db.add(
                RolePerm(
                    role_id=role_id,
                    module_code=rp.module_code,
                    perm_code=rp.perm_code,
                    perm_level=rp.perm_level,
                    tenant_id=rp.tenant_id,
                )
            )


def _ensure_cloned_user(
    db: Session,
    *,
    username: str,
    nickname: str,
    mobile: str,
    role_key: str,
    role_name: str,
) -> None:
    """本地 E2E 用户。密码与 admin 种子相同，克隆 sys:admin 菜单以便纯 UI 登录进账号页。"""
    from app.scope import refresh_user_scope
    from app.security import hash_password

    user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
    if user is None:
        user = User(
            username=username,
            nickname=nickname,
            mobile=mobile,
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
        )
        db.add(user)
        db.flush()
    elif user.nickname != nickname:
        user.nickname = nickname
    role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
    if role is None:
        role = Role(
            role_name=role_name,
            role_key=role_key,
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    perm_count = db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id == role.id)) or 0
    if perm_count == 0:
        _clone_admin_perms(db, role.id)
    if not db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)):
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
    refresh_user_scope(db, user.id)


def ensure_acct_finance_user(db: Session) -> None:
    """冲话费凭证可见角色（R3 · acct:r3）。"""
    _ensure_cloned_user(
        db,
        username=E2E_ACCT_FINANCE_USER,
        nickname="财务管理员",
        mobile="13900000058",
        role_key=FINANCE_ROLE_KEY,
        role_name="财务管理员",
    )


def ensure_acct_peer_user(db: Session) -> None:
    """他人领用 / 流转接收人（e2e_acct_peer · 流转同事）。"""
    _ensure_cloned_user(
        db,
        username=E2E_ACCT_PEER_USER,
        nickname=E2E_ACCT_PEER_NICK,
        mobile="13900000060",
        role_key=PEER_ROLE_KEY,
        role_name="账号流转同事",
    )


def ensure_acct_sum_user(db: Session) -> User:
    """成本汇总部门维度。固定部门 70070，不占用 admin 的部门。"""
    _ensure_cloned_user(
        db,
        username=E2E_SUM_DEPT_USER,
        nickname=E2E_SUM_DEPT_NICK,
        mobile="13900000070",
        role_key="acct:sum",
        role_name="账号汇总同事",
    )
    user = db.scalar(select(User).where(User.username == E2E_SUM_DEPT_USER, User.deleted == 0))
    assert user is not None
    linked = db.scalar(
        select(UserDept).where(UserDept.user_id == user.id, UserDept.dept_id == E2E_SUM_DEPT_ID)
    )
    if linked is None:
        db.add(UserDept(user_id=user.id, dept_id=E2E_SUM_DEPT_ID, tenant_id=user.tenant_id or 0))
        db.flush()
    return user


def refresh_acct_e2e_pool(db: Session, admin: User) -> None:
    """E2E 跑前恢复池内账号与清空该账号流程单据。"""
    if admin.username != "admin":
        return
    ensure_acct_schema()
    ensure_acct_e2e_pool_account(db, admin)
    ensure_acct_finance_user(db)
    ensure_acct_peer_user(db)
    sum_user = ensure_acct_sum_user(db)
    ops = ops_session()
    account_ids: list[int] = []
    try:
        for account_no in (
            E2E_POOL_ACCOUNT_NO,
            E2E_XFER_ACCOUNT_NO,
            E2E_RECALL_ACCOUNT_NO,
            E2E_UNFREEZE_ACCOUNT_NO,
            E2E_RECON_ACCOUNT_NO,
            E2E_SUM_ACCOUNT_NO,
        ):
            row = _account_row(ops, account_no)
            if row is None:
                continue
            row.status = "IN_POOL"
            row.holder_user_id = sum_user.id if account_no == E2E_SUM_ACCOUNT_NO else admin.id
            account_ids.append(row.id)
        ops.commit()
    finally:
        ops.close()
    if not account_ids:
        return
    db.execute(delete(AccountTimelineEvent).where(AccountTimelineEvent.account_id.in_(account_ids)))
    db.execute(delete(AccountApply).where(AccountApply.account_id.in_(account_ids)))
    db.execute(delete(AccountRecharge).where(AccountRecharge.account_id.in_(account_ids)))
    db.execute(delete(AccountTransfer).where(AccountTransfer.account_id.in_(account_ids)))
    verify_ids = list(
        db.scalars(
            select(AccountRechargeVerify.id).where(AccountRechargeVerify.account_id.in_(account_ids))
        ).all()
    )
    if verify_ids:
        db.execute(delete(Todo).where(Todo.ref_type == "acct_recharge_verify", Todo.ref_id.in_(verify_ids)))
        db.execute(
            delete(WorkMessage).where(
                WorkMessage.ref_type == "acct_recharge_verify",
                WorkMessage.ref_id.in_(verify_ids),
            )
        )
        db.execute(delete(AccountRechargeVerify).where(AccountRechargeVerify.id.in_(verify_ids)))
