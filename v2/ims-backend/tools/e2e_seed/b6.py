"""B6 测试环境造数。只允许 test / e2e，不写新密码。"""
from __future__ import annotations

import os
from pathlib import Path

ALLOWED = {"test", "e2e"}
ROOT = Path(__file__).resolve().parent


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def seed() -> None:
    assert_allowed()
    from sqlalchemy import select

    from app.core.context import system_context, use_context
    from app.db.repository import Repository
    from app.db.session import session_scope
    from app.domains.device.model import AssetEvent, AssetLedger
    from app.domains.master.model import Phone, Realname, SimCard
    from app.domains.resource.common import digest
    from app.domains.system.model import Dept, Role, User, UserDept, UserRole
    from app.main import create_app
    from tools.seed.apply import apply

    create_app()
    _samples()
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            apply("e2e")
            secret = _copy_secret(session)
            roles = {key: session.scalar(select(Role).where(Role.role_key == key)) for key in ("R3", "R4", "R5", "R6", "R9")}
            root = session.get(Dept, 10) or session.scalar(select(Dept).where(Dept.parent_id == 0))
            live = _dept(session, root, "直播一部")
            accounts = {
                "test_r3": ("测试财务", "ACTIVE", roles["R3"]),
                "test_r4": ("测试运营管理", "ACTIVE", roles["R4"]),
                "test_r5": ("测试运营组长", "ACTIVE", roles["R5"]),
                "test_r5b": ("测试运营组长乙", "ACTIVE", roles["R5"]),
                "test_r6": ("测试审核", "ACTIVE", roles["R6"]),
                "test_r9": ("测试分析", "ACTIVE", roles["R9"]),
            }
            users = {}
            for username, (nickname, status, role) in accounts.items():
                users[username] = _user(session, username, nickname, status, role, live, secret)
            for username in ("test_admin", "test_xz", "test_resigned"):
                found = session.scalar(select(User).where(User.username == username))
                if found is not None:
                    users[username] = found
            if users.get("test_r4") is not None and live.leader_user_id != users["test_r4"].id:
                live.leader_user_id = users["test_r4"].id
            person = _realname(session, "测试实名甲", "110101199003078515", "ENABLED")
            stopped = _realname(session, "测试实名停用", "110101199003074833", "DISABLED")
            phone_a = _phone(session, "PH-2026-001", "iPhone", "IOS", users.get("test_r5"), "IN_USE")
            _phone(session, "PH-2026-002", "Android", "ANDROID", users.get("test_xz"), "IN_USE")
            _phone(session, "PH-2026-003", "旧手机", "ANDROID", users.get("test_xz"), "SCRAPPED")
            _sim(session, "卡A", "13900001001", person, phone_a, "ENABLED")
            _sim(session, "卡B", "13900001002", person, None, "ENABLED")
            _sim(session, "卡C", "13900001003", person, None, "ENABLED")
            _sim(session, "卡停", "13900001004", stopped, None, "DISABLED")
            xz = users.get("test_xz")
            r5 = users.get("test_r5")
            resigned = users.get("test_resigned")
            _asset(session, "AS-OF-1", "待审办公设备", "OFFICE", "PENDING_REVIEW", xz, person)
            _asset(session, "AS-OF-2", "在用办公设备", "OFFICE", "IN_USE", r5, person)
            _asset(session, "AS-OF-3", "报废办公设备", "OFFICE", "SCRAPPED", xz, person)
            _asset(session, "AS-LV-1", "无实名直播设备", "LIVE", "IN_USE", r5, None)
            _asset(session, "AS-LV-2", "已归还直播设备", "LIVE", "RETURNED", xz, person)
            _asset(session, "AS-LV-3", "维修直播设备", "LIVE", "REPAIRING", xz, person)
            _asset(session, "AS-SH-1", "闲置拍摄设备", "SHOOT", "IDLE", xz, person)
            _asset(session, "AS-LV-9", "离职责任人设备", "LIVE", "IN_USE", resigned, person)


def _copy_secret(session):
    from sqlalchemy import select

    from app.domains.system.model import User

    for name in ("test_admin", "admin"):
        found = session.scalar(select(User).where(User.username == name))
        if found is not None and found.password_hash:
            return found.password_hash
    admin = session.get(User, 1)
    if admin is None or not admin.password_hash:
        raise RuntimeError("缺少可复制的登录口令")
    return admin.password_hash


def _dept(session, parent, name: str):
    from sqlalchemy import select

    from app.domains.system.model import Dept

    found = session.scalar(select(Dept).where(Dept.name == name, Dept.tenant_id == 1))
    if found is not None:
        return found
    row = Dept(parent_id=parent.id, name=name, path=parent.path, source="LOCAL", status="ENABLED", tenant_id=1)
    session.add(row)
    session.flush()
    row.path = f"{parent.path}{row.id}/"
    return row


def _user(session, username, nickname, status, role, dept, secret):
    from sqlalchemy import select

    from app.domains.system.model import User, UserDept, UserRole

    found = session.scalar(select(User).where(User.username == username))
    if found is not None:
        return found
    row = User(username=username, nickname=nickname, password_hash=secret, status=status, main_dept_id=dept.id, source="LOCAL", tenant_id=1)
    session.add(row)
    session.flush()
    if role is not None:
        session.add(UserRole(user_id=row.id, role_id=role.id, source="MANUAL", tenant_id=1))
    session.add(UserDept(user_id=row.id, dept_id=dept.id, is_main=1, source="LOCAL", tenant_id=1))
    return row


def _realname(session, name, number, status):
    from sqlalchemy import select

    from app.db.repository import Repository
    from app.domains.master.model import Realname
    from app.domains.resource.common import digest, next_no

    found = session.scalar(select(Realname).where(Realname.name == name))
    if found is not None:
        return found
    code = next_no("RN", "REALNAME")
    row = Realname(code=code, realname_no=code, name=name, id_type="ID_CARD", id_no_enc=number, id_no_hash=digest(number), status=status)
    Repository(Realname).create(row)
    return row


def _phone(session, number, model, os_type, keeper, status):
    from sqlalchemy import select

    from app.db.repository import Repository
    from app.domains.master.model import Phone

    found = session.scalar(select(Phone).where(Phone.device_no == number))
    if found is not None:
        return found
    row = Phone(
        code=number,
        name=model,
        device_no=number,
        model=model,
        os_type=os_type,
        custodian_user_id=keeper.id if keeper is not None else None,
        status=status,
        purchase_amount=0,
    )
    Repository(Phone).create(row)
    return row


def _sim(session, name, phone, person, device, status):
    from sqlalchemy import select

    from app.db.repository import Repository
    from app.domains.master.model import SimCard
    from app.domains.resource.common import digest, next_no

    found = session.scalar(select(SimCard).where(SimCard.name == name))
    if found is not None:
        return found
    code = next_no("SIM", "SIM")
    row = SimCard(
        code=code,
        sim_no=code,
        name=name,
        phone_number_enc=phone,
        phone_number_hash=digest(phone),
        operator="CMCC",
        realname_id=person.id if person is not None else None,
        phone_id=device.id if device is not None else None,
        status=status,
        monthly_rent=0,
    )
    Repository(SimCard).create(row)
    return row


def _asset(session, code, name, asset_type, status, owner, person):
    from sqlalchemy import select

    from app.db.repository import Repository
    from app.domains.device.model import AssetEvent, AssetLedger

    found = session.scalar(select(AssetLedger).where(AssetLedger.asset_code == code))
    if found is not None:
        return found
    row = AssetLedger(
        asset_code=code,
        asset_name=name,
        asset_type=asset_type,
        status=status,
        owner_user_id=owner.id if owner is not None else None,
        realname_id=person.id if person is not None else None,
        purchase_amount=0,
        version=1,
    )
    Repository(AssetLedger).create(row)
    session.add(AssetEvent(asset_id=row.id, event_type="REGISTER", title="资产登记", to_status=status, to_owner_id=row.owner_user_id))
    return row


def _samples() -> None:
    folder = ROOT / "samples"
    folder.mkdir(exist_ok=True)
    mixed = folder / "purchase_mixed.csv"
    if not mixed.exists():
        mixed.write_text(
            "资产编号,资产名称,资产类型,规格,采购日期,责任人工号\n"
            "AS-M-1,麦克风,办公设备,手持,2026-01-01,test_xz\n"
            "AS-M-2,灯光,,支架,2026-01-02,\n"
            ",名称为空,办公设备,,2026-01-03,\n"
            "AS-M-4,日期坏,办公设备,,2026-13-40,\n"
            "AS-M-1,重复,办公设备,,2026-01-04,\n",
            encoding="utf-8",
        )
    live = folder / "purchase_live_empty_type.csv"
    if not live.exists():
        live.write_text("资产编号,资产名称,资产类型,规格,采购日期,责任人工号\n,缺类型,,,2026-01-01,\n", encoding="utf-8")
    image = folder / "device.jpg"
    if not image.exists():
        image.write_bytes(
            bytes.fromhex(
                "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffda00080001000100003f00fbffd9"
            )
        )
    exe = folder / "sample.exe"
    if not exe.exists():
        exe.write_bytes(b"MZ")


if __name__ == "__main__":
    seed()
