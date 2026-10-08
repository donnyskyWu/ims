"""S3 FIN closure E2E 种子：抖音账号 AC-E2E-FIN + 实名人 + 手机 E2E-FIN-PHONE（幂等）。

#71 另备 AC-E2E-LIVE1045 / 实名人 E2E-Live-1045 / 手机 E2E-LIVE1045-PHONE。
证件由 closure 纯 UI 录入，refresh 时清掉该持有人的档案，避免换证后的生效档让下一轮录入撞上 1032。
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crypto import encrypt_text
from app.models import CertArchive, CertExpireLog, CertViewLog, Todo, User, WorkMessage
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

E2E_FIN_ACCOUNT_NO = "AC-E2E-FIN"
E2E_FIN_ACCOUNT_NICK = "E2E财务场次号"
E2E_FIN_PHONE_CODE = "E2E-FIN-PHONE"
E2E_LIVE1045_ACCOUNT_NO = "AC-E2E-LIVE1045"
E2E_LIVE1045_ACCOUNT_NICK = "E2E锁定证件场次"
E2E_LIVE1045_PHONE_CODE = "E2E-LIVE1045-PHONE"
E2E_LIVE1045_REALNAME = "E2E-Live-1045"
E2E_LIVE1044_ACCOUNT_NO = "AC-E2E-LIVE1044"
E2E_LIVE1044_ACCOUNT_NICK = "E2E黄级场次"
E2E_LIVE1044_PHONE_CODE = "E2E-LIVE1044-PHONE"
E2E_LIVE1044_REALNAME = "E2E-Live-1044"
E2E_LIVE1043_ACCOUNT_NO = "AC-E2E-LIVE1043"
E2E_LIVE1043_ACCOUNT_NICK = "E2E红级场次"
E2E_LIVE1043_PHONE_CODE = "E2E-LIVE1043-PHONE"
E2E_LIVE1043_REALNAME = "E2E-Live-1043"


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


def _company_and_group(ops):
    company = ops.scalar(select(Company).where(Company.deleted == 0).limit(1))
    group = ops.scalar(select(IpGroup).where(IpGroup.deleted == 0).limit(1))
    if company is None or group is None:
        company = Company(company_name="E2E财务公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="E2E财务组", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.flush()
    return company, group


def ensure_live_cert_lock_e2e_deps(db: Session, admin: User) -> None:
    """#71 开播 1045 用的独立账号/实名人/手机。不写入证件。"""
    del db
    ops = ops_session()
    try:
        company, group = _company_and_group(ops)
        person = ops.scalar(
            select(Realname).where(Realname.real_name == E2E_LIVE1045_REALNAME, Realname.deleted == 0)
        )
        if person is None:
            person = Realname(
                real_name=E2E_LIVE1045_REALNAME,
                id_type="ID_CARD",
                id_card_enc=encrypt_text("330101199003031045"),
                phone_enc=encrypt_text("13800001045"),
                status="ENABLED",
                tenant_id=0,
            )
            ops.add(person)
            ops.flush()
        else:
            person.status = "ENABLED"

        phone = ops.scalar(
            select(Phone).where(Phone.phone_code == E2E_LIVE1045_PHONE_CODE, Phone.deleted == 0)
        )
        if phone is None:
            phone = Phone(
                phone_enc=encrypt_text("13600001045"),
                phone_sha256=f"live1045-e2e-{E2E_LIVE1045_PHONE_CODE}",
                phone_code=E2E_LIVE1045_PHONE_CODE,
                phone_model="E2E-iPhone",
                status="IN_USE",
                keeper_id=admin.id,
                device_number=E2E_LIVE1045_PHONE_CODE,
                tenant_id=0,
            )
            ops.add(phone)
            ops.flush()
        else:
            phone.status = "IN_USE"

        account = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_LIVE1045_ACCOUNT_NO,
                PlatformAccount.deleted == 0,
            )
        )
        if account is None:
            ops.add(
                PlatformAccount(
                    account_no=E2E_LIVE1045_ACCOUNT_NO,
                    account_name=E2E_LIVE1045_ACCOUNT_NICK,
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
            account.platform_type = "DOUYIN"
            account.account_name = E2E_LIVE1045_ACCOUNT_NICK
        ops.commit()
    finally:
        ops.close()


def clear_live_cert_lock_archives(db: Session) -> None:
    """清掉 #71 持有人的证件与预警，下一轮 closure 从录入开始。不动水印/频次/换证种子。"""
    ids = list(
        db.scalars(select(CertArchive.id).where(CertArchive.holder_name == E2E_LIVE1045_REALNAME)).all()
    )
    if not ids:
        return
    log_ids = list(db.scalars(select(CertExpireLog.id).where(CertExpireLog.cert_id.in_(ids))).all())
    if log_ids:
        db.execute(delete(Todo).where(Todo.ref_type == "cert_expire", Todo.ref_id.in_(log_ids)))
        db.execute(delete(WorkMessage).where(WorkMessage.ref_type == "cert_expire", WorkMessage.ref_id.in_(log_ids)))
        db.execute(delete(CertExpireLog).where(CertExpireLog.id.in_(log_ids)))
    db.execute(delete(CertViewLog).where(CertViewLog.cert_id.in_(ids)))
    db.execute(delete(CertArchive).where(CertArchive.id.in_(ids)))


def _upsert_risk_account(
    ops,
    admin: User,
    company,
    group,
    *,
    account_no: str,
    account_nick: str,
    phone_code: str,
    real_name: str,
    person_status: str,
    account_status: str,
    id_card: str,
    mobile: str,
    phone_number: str,
) -> None:
    person = ops.scalar(select(Realname).where(Realname.real_name == real_name, Realname.deleted == 0))
    if person is None:
        person = Realname(
            real_name=real_name,
            id_type="ID_CARD",
            id_card_enc=encrypt_text(id_card),
            phone_enc=encrypt_text(mobile),
            status=person_status,
            tenant_id=0,
        )
        ops.add(person)
        ops.flush()
    else:
        person.status = person_status

    phone = ops.scalar(select(Phone).where(Phone.phone_code == phone_code, Phone.deleted == 0))
    if phone is None:
        phone = Phone(
            phone_enc=encrypt_text(phone_number),
            phone_sha256=f"live-risk-{phone_code}",
            phone_code=phone_code,
            phone_model="E2E-iPhone",
            status="IN_USE",
            keeper_id=admin.id,
            device_number=phone_code,
            tenant_id=0,
        )
        ops.add(phone)
        ops.flush()
    else:
        phone.status = "IN_USE"

    account = ops.scalar(
        select(PlatformAccount).where(PlatformAccount.account_no == account_no, PlatformAccount.deleted == 0)
    )
    if account is None:
        ops.add(
            PlatformAccount(
                account_no=account_no,
                account_name=account_nick,
                platform_type="DOUYIN",
                ip_group_id=group.id,
                company_id=company.id,
                realname_id=person.id,
                holder_user_id=admin.id,
                status=account_status,
                tenant_id=0,
            )
        )
    else:
        account.realname_id = person.id
        account.status = account_status
        account.holder_user_id = admin.id
        account.platform_type = "DOUYIN"
        account.account_name = account_nick
        account.ip_group_id = group.id
        account.company_id = company.id


def ensure_live_risk_e2e_deps(db: Session, admin: User) -> None:
    """#78 黄级（账号非在用）与红级（实名人停用 + 账号非在用）种子。主题里的黑名单词由 closure 填写。"""
    del db
    ops = ops_session()
    try:
        company, group = _company_and_group(ops)
        _upsert_risk_account(
            ops,
            admin,
            company,
            group,
            account_no=E2E_LIVE1044_ACCOUNT_NO,
            account_nick=E2E_LIVE1044_ACCOUNT_NICK,
            phone_code=E2E_LIVE1044_PHONE_CODE,
            real_name=E2E_LIVE1044_REALNAME,
            person_status="ENABLED",
            account_status="FROZEN",
            id_card="330101199004041044",
            mobile="13800001044",
            phone_number="13600001044",
        )
        _upsert_risk_account(
            ops,
            admin,
            company,
            group,
            account_no=E2E_LIVE1043_ACCOUNT_NO,
            account_nick=E2E_LIVE1043_ACCOUNT_NICK,
            phone_code=E2E_LIVE1043_PHONE_CODE,
            real_name=E2E_LIVE1043_REALNAME,
            person_status="DISABLED",
            account_status="FROZEN",
            id_card="330101199004041043",
            mobile="13800001043",
            phone_number="13600001043",
        )
        ops.commit()
    finally:
        ops.close()


def refresh_live_fin_e2e_deps(db: Session, admin: User) -> None:
    if admin.username != "admin":
        return
    ensure_live_fin_e2e_deps(db, admin)
    ensure_live_cert_lock_e2e_deps(db, admin)
    clear_live_cert_lock_archives(db)
    ensure_live_risk_e2e_deps(db, admin)
