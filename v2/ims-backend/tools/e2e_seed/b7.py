"""B7 测试环境造数。只允许 test / e2e，不写明文密码。"""
from __future__ import annotations

import os

ALLOWED = {"test", "e2e"}


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def seed() -> None:
    assert_allowed()
    from tools.e2e_seed.b6 import seed as seed_b6

    seed_b6()
    from sqlalchemy import select

    from app.core.clock import today
    from app.core.context import system_context, use_context
    from app.db.repository import Repository
    from app.db.session import session_scope
    from app.domains.account.model import AccountApply, AccountTransfer, CollectCredential, Recharge, ReturnOrder
    from app.domains.master.model import Company, PersonalAccount, PlatformAccount, Realname
    from app.domains.system.model import User

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            if session.scalar(select(PlatformAccount).where(PlatformAccount.account_no.like("B7-%"))):
                return
            company = session.scalar(select(Company).where(Company.name == "B7样例公司"))
            if company is None:
                company = Company(name="B7样例公司", code="B7CO", company_no="CO-B7-001", status="ENABLED", wx_official_capacity=20, credit_code="91310000B7SAMPLE01")
                Repository(Company).create(company)
            person = session.scalar(select(Realname).where(Realname.name == "B7样例实名"))
            if person is None:
                person = Realname(name="B7样例实名", code="B7RN", realname_no="RN-B7-001", status="ENABLED")
                Repository(Realname).create(person)
            owner = session.scalar(select(User).where(User.username == "test_r5"))
            resigned = session.scalar(select(User).where(User.username == "test_resigned"))
            target = session.scalar(select(User).where(User.username == "test_r4"))
            specs = [
                ("IN_POOL", None),
                ("IN_USE", owner.id if owner else None),
                ("FROZEN", resigned.id if resigned else None),
            ]
            platforms = ["DOUYIN", "KUAISHOU", "WECHAT_CHANNELS", "XIAOHONGSHU", "WECHAT_MP"]
            pool = None
            used = None
            frozen = None
            for platform in platforms:
                for status, user_id in specs:
                    number = f"B7-{platform[:3]}-{status}"
                    row = PlatformAccount(
                        code=number,
                        name=f"{platform}-{status}",
                        account_no=number,
                        nickname=f"{platform}-{status}",
                        platform=platform,
                        company_id=company.id,
                        realname_id=person.id,
                        status=status,
                        owner_user_id=user_id,
                        collect_bind_status="UNBOUND",
                        recharge_total_fen=0,
                    )
                    Repository(PlatformAccount).create(row)
                    if platform == "DOUYIN" and status == "IN_POOL":
                        pool = row
                    if platform == "DOUYIN" and status == "IN_USE":
                        used = row
                    if platform == "DOUYIN" and status == "FROZEN":
                        frozen = row
            if pool is not None and owner is not None:
                session.add(
                    AccountApply(
                        apply_no="AP-B7-001",
                        account_id=pool.id,
                        applicant_user_id=owner.id,
                        purpose="样例领用",
                        plan_start=today(),
                        plan_end=today(),
                        apply_status="PENDING_HANDOVER",
                        current_step="待交接",
                    )
                )
            if used is not None and owner is not None and target is not None:
                session.add(
                    AccountTransfer(
                        transfer_no="TR-B7-001",
                        account_id=used.id,
                        transfer_type="TRANSFER",
                        from_user_id=owner.id,
                        to_user_id=target.id,
                        reason_type="BUSINESS_ADJUST",
                        remark="样例流转",
                        status="PENDING_CONFIRM",
                    )
                )
            if frozen is not None and resigned is not None:
                session.add(
                    ReturnOrder(
                        return_no="RT-B7-001",
                        user_id=resigned.id,
                        resign_date=today(),
                        status="IN_PROGRESS",
                        manual=1,
                    )
                )
            if used is not None and owner is not None:
                session.add(
                    Recharge(
                        account_id=used.id,
                        amount_fen=10000,
                        channel="ALIPAY",
                        recharge_date=today(),
                        verify_status="UNVERIFIED",
                        operator_user_id=owner.id,
                    )
                )
                session.add(
                    Recharge(
                        account_id=used.id,
                        amount_fen=500001,
                        channel="BANK",
                        recharge_date=today(),
                        voucher_file_key="ACCOUNT/e2e/voucher.pdf",
                        verify_status="UNVERIFIED",
                        operator_user_id=owner.id,
                    )
                )
                bound = CollectCredential(account_id=used.id, collector_account_id=f"SIM-{used.id}", last_probe_ok=1)
                Repository(CollectCredential).create(bound)
                used.collect_bind_status = "BOUND"
            for kind, nickname in (("WEWORK", "样例企微"), ("WECHAT", "样例个微")):
                number = f"PA-B7-{kind}"
                session.add(
                    PersonalAccount(
                        code=number,
                        name=nickname,
                        account_no=number,
                        account_type=kind,
                        nickname=nickname,
                        owner_user_id=owner.id if owner else None,
                        status="ENABLED",
                    )
                )
            session.flush()
