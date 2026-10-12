"""B5 测试环境造数。只允许 test / e2e。"""
from __future__ import annotations

import argparse
import os
from datetime import timedelta

ALLOWED = {"test", "e2e"}


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def seed() -> None:
    """公司 3、实名人 6、手机卡 5、证件 8，以及分级配置。"""
    assert_allowed()
    from app.core.clock import today
    from app.core.context import system_context, use_context
    from app.db.repository import Repository
    from app.db.session import session_scope
    from app.domains.cert.model import CertLevelConfig
    from app.domains.master.model import Cert, Company, Realname, SimCard
    from app.domains.resource.common import digest, next_no
    from app.main import create_app
    from tools.seed.apply import apply

    create_app()
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            apply("e2e")
            if session.query(Company).filter(Company.company_no.like("CO%")).first():
                return
            companies = []
            for index, (name, status, capacity) in enumerate(
                [("星河文化", "ENABLED", 0), ("停用主体", "DISABLED", 0), ("容量为零", "ENABLED", 0)],
                start=1,
            ):
                number = next_no("CO", "COMPANY")
                row = Company(
                    code=number,
                    company_no=number,
                    name=name,
                    credit_code=f"91310000MA1FL{index:02d}W30"[:18],
                    legal_person="法人",
                    status=status,
                    wx_official_capacity=capacity,
                )
                Repository(Company).create(row)
                companies.append(row)
            people = []
            samples = ["110101199003078515", "110101199003074833", "110101199003076478", "11010119900307213X", "11010119900307915X", "110101199003071234"]
            for index, number in enumerate(samples):
                code = next_no("RN", "REALNAME")
                row = Realname(
                    code=code,
                    realname_no=code,
                    name=f"实名人{index + 1}",
                    id_type="ID_CARD",
                    id_no_enc=number,
                    id_no_hash=digest(number),
                    status="DISABLED" if index == 5 else "ENABLED",
                    company_id=companies[0].id,
                    user_id=1 if index == 0 else None,
                )
                Repository(Realname).create(row)
                people.append(row)
            for index in range(5):
                phone = f"1380000000{index}"
                code = next_no("SIM", "SIM")
                Repository(SimCard).create(
                    SimCard(
                        code=code,
                        sim_no=code,
                        name=phone,
                        phone_number_enc=phone,
                        phone_number_hash=digest(phone),
                        operator=["CMCC", "CUCC", "CTCC", "CBN", "CMCC"][index],
                        realname_id=people[index].id if index < 4 else None,
                        status="ENABLED",
                        monthly_rent=5900,
                        payment_cycle="MONTH",
                    )
                )
            day = today()
            plans = [
                (people[0], "PENDING_REVIEW", day + timedelta(days=400)),
                (people[1], "EFFECTIVE", day + timedelta(days=400)),
                (people[2], "EXPIRING", day + timedelta(days=20)),
                (people[3], "EXPIRING", day + timedelta(days=5)),
                (people[4], "EXPIRED", day - timedelta(days=1)),
                (people[0], "EFFECTIVE", day.replace(year=9999, month=12, day=31) if False else __import__("datetime").date(9999, 12, 31)),
                (people[1], "RECYCLED", day + timedelta(days=10)),
                (people[2], "EFFECTIVE", day + timedelta(days=800)),
            ]
            types = ["ID_CARD", "ID_CARD", "ID_CARD", "PASSPORT", "ID_CARD", "HEALTH", "ID_CARD", "ANCHOR_QUAL"]
            for index, ((person, status, expire), cert_type) in enumerate(zip(plans, types)):
                code = next_no("CERT", "CERT")
                Repository(Cert).create(
                    Cert(
                        code=code,
                        cert_no=code,
                        name=person.name,
                        cert_type=cert_type,
                        cert_no_enc=f"C{index:04d}8899",
                        cert_no_hash=digest(f"C{index:04d}8899"),
                        issue_date=day - timedelta(days=30),
                        expire_date=expire,
                        status=status,
                        realname_id=person.id,
                        file_key=f"CERT/seed/{index}.png",
                        uploaded_by=1,
                    )
                )
            session.add(CertLevelConfig(l2_role_ids=[102], l3_user_ids=[], opacity="0.12", position="BOTTOM_RIGHT", version=1))
            session.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("IMS_ENV") or "test")
    args = parser.parse_args()
    assert_allowed(args.env)
    seed()
