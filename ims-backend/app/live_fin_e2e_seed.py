"""S3 FIN closure E2E 种子：抖音账号 AC-E2E-FIN + 实名人 + 手机 E2E-FIN-PHONE（幂等）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import encrypt_text
from app.models import User
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

E2E_FIN_ACCOUNT_NO = "AC-E2E-FIN"
E2E_FIN_ACCOUNT_NICK = "E2E财务场次号"
E2E_FIN_PHONE_CODE = "E2E-FIN-PHONE"


def ensure_live_fin_e2e_deps(db: Session, admin: User) -> None:
    """确保 FIN pure UI closure 可用的账号/实名人/手机（绿级风控）。"""
    del db  # ims 侧无写入；保留签名与 acct_seed 一致
    ops = ops_session()
    try:
        account = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_FIN_ACCOUNT_NO,
                PlatformAccount.deleted == 0,
            )
        )
        phone = ops.scalar(
            select(Phone).where(Phone.phone_code == E2E_FIN_PHONE_CODE, Phone.deleted == 0)
        )
        if account is not None and phone is not None and account.realname_id:
            return

        company = ops.scalar(select(Company).where(Company.deleted == 0).limit(1))
        group = ops.scalar(select(IpGroup).where(IpGroup.deleted == 0).limit(1))
        if company is None or group is None:
            company = Company(company_name="E2E财务公司", status="ENABLED", tenant_id=0)
            group = IpGroup(group_name="E2E财务组", status="ENABLED", tenant_id=0)
            ops.add_all([company, group])
            ops.flush()

        person = ops.scalar(
            select(Realname).where(Realname.real_name == "E2E财务实名人", Realname.deleted == 0)
        )
        if person is None:
            person = Realname(
                real_name="E2E财务实名人",
                id_type="ID_CARD",
                id_card_enc=encrypt_text("330101199002021234"),
                phone_enc=encrypt_text("13800009991"),
                status="ENABLED",
                tenant_id=0,
            )
            ops.add(person)
            ops.flush()

        if phone is None:
            phone = Phone(
                phone_enc=encrypt_text("13600009991"),
                phone_sha256=f"fin-e2e-{E2E_FIN_PHONE_CODE}",
                phone_code=E2E_FIN_PHONE_CODE,
                phone_model="E2E-iPhone",
                status="IN_USE",
                keeper_id=admin.id,
                device_number=E2E_FIN_PHONE_CODE,
                tenant_id=0,
            )
            ops.add(phone)
            ops.flush()

        if account is None:
            ops.add(
                PlatformAccount(
                    account_no=E2E_FIN_ACCOUNT_NO,
                    account_name=E2E_FIN_ACCOUNT_NICK,
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    company_id=company.id,
                    realname_id=person.id,
                    holder_user_id=admin.id,
                    status="IN_USE",
                    tenant_id=0,
                )
            )
        else:
            account.realname_id = person.id
            account.status = "IN_USE"
            account.holder_user_id = admin.id
        ops.commit()
    finally:
        ops.close()


def refresh_live_fin_e2e_deps(db: Session, admin: User) -> None:
    if admin.username != "admin":
        return
    ensure_live_fin_e2e_deps(db, admin)
