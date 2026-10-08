"""#75 · ASSET-003 登记关联校验，以及穿透详情的场次层 / 成本层。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core import SessionLocal
from app.main import app
from app.models import AssetBind, AssetHierarchy, AssetLedger, AssetLifecycleEvent, LiveReport, LiveSession, Role, RolePerm, User, UserRole
from app.ops_db import ops_session
from app.ops_models import PlatformAccount, Realname
from app.security import hash_password

client = TestClient(app)

ACCOUNT = "AC-VY-75A"
OTHER = "AC-VY-75B"
STOPPED = "AC-VY-75X"
GOOD_SESSION = "IMS20261008VYA0001"
CANCEL_SESSION = "IMS20261008VYA0002"
OTHER_SESSION = "IMS20261008VYB0001"
PERSON_ON = "VY-75-ON"
PERSON_OFF = "VY-75-OFF"


def headers(username: str = "admin", password: str = "Admin@123") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    return int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])


def _person(name: str, status: str) -> int:
    ops = ops_session()
    try:
        row = ops.scalar(select(Realname).where(Realname.real_name == name, Realname.deleted == 0))
        if row is None:
            row = Realname(real_name=name, status=status, tenant_id=0)
            ops.add(row)
        else:
            row.status = status
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _account(account_no: str, holder_id: int, status: str, realname_id: int) -> int:
    ops = ops_session()
    try:
        row = ops.scalar(select(PlatformAccount).where(PlatformAccount.account_no == account_no, PlatformAccount.deleted == 0))
        if row is None:
            row = PlatformAccount(
                account_no=account_no,
                account_name=account_no,
                platform_type="DOUYIN",
                holder_user_id=holder_id,
                realname_id=realname_id,
                status=status,
                tenant_id=0,
            )
            ops.add(row)
        else:
            row.status = status
            row.realname_id = realname_id
            row.holder_user_id = holder_id
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _session(account_id: int, account_no: str, code: str, owner_id: int, status: str, realname_id: int) -> int:
    db = SessionLocal()
    try:
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == code, LiveSession.deleted == 0))
        if row is None:
            row = LiveSession(
                session_code=code,
                account_id=account_id,
                account_no=account_no,
                realname_person_id=realname_id,
                responsible_user_id=owner_id,
                device_asset_ids="[]",
                platform="DOUYIN",
                topic="关联校验场次",
                session_status=status,
                tenant_id=0,
                creator=owner_id,
                deleted=0,
            )
            db.add(row)
        else:
            row.account_id = account_id
            row.account_no = account_no
            row.realname_person_id = realname_id
            row.session_status = status
        db.commit()
        return int(row.id)
    finally:
        db.close()


def _report(code: str, owner_id: int) -> None:
    db = SessionLocal()
    try:
        row = db.scalar(select(LiveReport).where(LiveReport.session_code == code, LiveReport.deleted == 0))
        if row is None:
            db.add(
                LiveReport(
                    session_code=code,
                    gmv=12800,
                    ad_cost=1860,
                    entry_status="SUBMITTED",
                    entry_user_id=owner_id,
                    tenant_id=0,
                    deleted=0,
                )
            )
        else:
            row.gmv = 12800
            row.ad_cost = 1860
        db.commit()
    finally:
        db.close()


def _wipe(codes: list[str]) -> None:
    db = SessionLocal()
    try:
        ids = list(db.scalars(select(AssetLedger.id).where(AssetLedger.asset_code.in_(codes))).all())
        if ids:
            db.execute(delete(AssetBind).where(AssetBind.asset_id.in_(ids)))
            db.execute(delete(AssetHierarchy).where(AssetHierarchy.asset_id.in_(ids)))
            db.execute(delete(AssetLifecycleEvent).where(AssetLifecycleEvent.asset_id.in_(ids)))
            db.execute(delete(AssetLedger).where(AssetLedger.id.in_(ids)))
            db.commit()
    finally:
        db.close()


def _create(auth: dict, code: str, **extra) -> dict:
    body = {"assetCode": code, "assetName": code, "assetType": "OFFICE", **extra}
    return client.post("/admin-api/ims/asset/ledger", headers=auth, json=body).json()


def _ensure_user(username: str, status: str, role_key: str = "") -> int:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if user is None:
            user = User(
                username=username,
                nickname=username,
                mobile="13900000075" if username == "asset_r9" else "13900000076",
                password_hash=hash_password("Admin@123"),
                status=status,
                tenant_id=0,
                deleted=0,
            )
            db.add(user)
            db.flush()
        else:
            user.status = status
        if role_key:
            role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
            if role is None:
                role = Role(role_name=role_key, role_key=role_key, data_scope="ALL", status="ENABLED", tenant_id=0, deleted=0)
                db.add(role)
                db.flush()
            linked = db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id))
            if linked is None:
                db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
            if db.scalar(select(RolePerm).where(RolePerm.role_id == role.id)) is None:
                db.add(
                    RolePerm(
                        role_id=role.id,
                        module_code="asset",
                        perm_code="asset:verify:query",
                        perm_level="R",
                        tenant_id=0,
                    )
                )
        db.commit()
        return int(user.id)
    finally:
        db.close()


def test_register_rejects_missing_disabled_and_mismatched_links_and_shows_layers():
    auth = headers()
    admin_id = _admin_id(auth)
    on_id = _person(PERSON_ON, "ENABLED")
    off_id = _person(PERSON_OFF, "DISABLED")
    account_id = _account(ACCOUNT, admin_id, "IN_USE", on_id)
    other_id = _account(OTHER, admin_id, "IN_USE", on_id)
    _account(STOPPED, admin_id, "CANCELLED", on_id)
    _session(account_id, ACCOUNT, GOOD_SESSION, admin_id, "ENDED", on_id)
    _session(account_id, ACCOUNT, CANCEL_SESSION, admin_id, "CANCELLED", on_id)
    _session(other_id, OTHER, OTHER_SESSION, admin_id, "ENDED", on_id)
    _report(GOOD_SESSION, admin_id)
    _wipe(["AS-VY-BARE", "AS-VY-GOOD", "AS-VY-CLEAN"])

    missing = _create(auth, "AS-VY-BARE", accountNo="AC-NO-SUCH-75")
    assert missing["code"] == 1500, missing
    assert "账号不存在" in missing["msg"]

    stopped = _create(auth, "AS-VY-BARE", accountNo=STOPPED)
    assert stopped["code"] == 1501, stopped
    assert "账号已停用" in stopped["msg"]

    gone = _create(auth, "AS-VY-BARE", sessionCode="IMS20261008AAA0009")
    assert gone["code"] == 1500, gone
    assert "场次不存在" in gone["msg"]

    cancelled = _create(auth, "AS-VY-BARE", sessionCode=CANCEL_SESSION)
    assert cancelled["code"] == 1501, cancelled
    assert "场次已取消" in cancelled["msg"]

    mismatch = _create(auth, "AS-VY-BARE", accountNo=ACCOUNT, sessionCode=OTHER_SESSION)
    assert mismatch["code"] == 1001, mismatch
    assert "场次不属于该账号" in mismatch["msg"]

    foreign = _create(auth, "AS-VY-BARE", realnameId=off_id, accountNo=ACCOUNT)
    assert foreign["code"] == 1001, foreign
    assert "账号不属于该实名人" in foreign["msg"]

    disabled = _create(auth, "AS-VY-BARE", realnameId=off_id)
    assert disabled["code"] == 1501, disabled
    assert "实名人已停用" in disabled["msg"]

    good = _create(auth, "AS-VY-GOOD", realnameId=on_id, accountNo=ACCOUNT, sessionCode=GOOD_SESSION)
    assert good["code"] == 0, good
    assert "绑定账号 AC-VY-75A" in good["data"]["timeline"][0]["remark"]
    assert "绑定场次 IMS20261008VYA0001" in good["data"]["timeline"][0]["remark"]

    detail = client.get(f"/admin-api/ims/asset/forward/detail/{good['data']['id']}", headers=auth).json()
    assert detail["code"] == 0, detail
    assert detail["data"]["liveSessions"][0]["sessionCode"] == GOOD_SESSION
    assert detail["data"]["liveSessions"][0]["status"] == "ENDED"
    assert detail["data"]["financeSummary"]["totalCost"] == 1860
    assert detail["data"]["financeSummary"]["totalRevenue"] == 12800
    assert detail["data"]["financeSummary"]["costMasked"] is False

    hidden = client.get(
        f"/admin-api/ims/asset/forward/detail/{good['data']['id']}",
        headers=auth,
        params={"withSessionLayer": False, "withFinanceLayer": False},
    ).json()
    assert hidden["data"]["liveSessions"] == []
    assert hidden["data"]["financeSummary"]["totalCost"] == 0
    assert hidden["data"]["financeSummary"]["costMasked"] is False

    _ensure_user("asset_r9", "ENABLED", "R9")
    masked = client.get(
        f"/admin-api/ims/asset/forward/detail/{good['data']['id']}",
        headers=headers("asset_r9"),
    ).json()
    assert masked["code"] == 0, masked
    assert masked["data"]["financeSummary"]["costMasked"] is True
    assert masked["data"]["financeSummary"]["totalCost"] == -1
    assert masked["data"]["financeSummary"]["totalRevenue"] == 12800
    assert masked["data"]["liveSessions"][0]["sessionCode"] == GOOD_SESSION


def test_verify_run_lists_gaps_and_illegal_task_is_1014():
    auth = headers()
    admin_id = _admin_id(auth)
    on_id = _person(PERSON_ON, "ENABLED")
    account_id = _account(ACCOUNT, admin_id, "IN_USE", on_id)
    _session(account_id, ACCOUNT, GOOD_SESSION, admin_id, "ENDED", on_id)
    owner_id = _ensure_user("asset_owner_off", "ENABLED")
    _wipe(["AS-VY-BARE", "AS-VY-GOOD", "AS-VY-CLEAN"])
    bare = _create(auth, "AS-VY-BARE")
    assert bare["code"] == 0, bare
    clean = _create(auth, "AS-VY-CLEAN", realnameId=on_id, accountNo=ACCOUNT, sessionCode=GOOD_SESSION)
    assert clean["code"] == 0, clean
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{clean['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": owner_id, "purpose": "校验使用人"},
    ).json()
    assert checked["code"] == 0, checked
    db = SessionLocal()
    try:
        owner = db.scalar(select(User).where(User.username == "asset_owner_off"))
        owner.status = "DISABLED"
        db.commit()
    finally:
        db.close()

    empty = client.post("/admin-api/ims/asset/verify/run", headers=auth, json={"verifyTypes": [], "scope": "FULL"}).json()
    assert empty["code"] == 1001

    ran = client.post(
        "/admin-api/ims/asset/verify/run",
        headers=auth,
        json={"verifyTypes": ["asset_person", "asset_account", "asset_session"], "scope": "FULL"},
    ).json()
    assert ran["code"] == 0, ran
    assert ran["data"]["batchNo"].startswith("AV")
    assert 0 <= float(ran["data"]["relationCompleteRate"]) <= 1
    assert 0 <= float(ran["data"]["consistencyRate"]) <= 1

    described = set()
    for code in ("AS-VY-BARE", "AS-VY-CLEAN"):
        errors = client.get(
            "/admin-api/ims/asset/verify/errors",
            headers=auth,
            params={"batchNo": ran["data"]["batchNo"], "assetCode": code, "pageSize": 50},
        ).json()
        assert errors["code"] == 0, errors
        described.update((item["assetCode"], item["description"]) for item in errors["data"]["list"])
    assert ("AS-VY-BARE", "未关联实名人") in described
    assert ("AS-VY-BARE", "未关联账号") in described
    assert ("AS-VY-CLEAN", "使用人已停用") in described
    assert not any(code == "AS-VY-CLEAN" and text == "未关联账号" for code, text in described)
    assert not any(code == "AS-VY-CLEAN" and "场次" in text for code, text in described)

    batches = client.get(
        "/admin-api/ims/asset/verify/batches",
        headers=auth,
        params={"batchNo": ran["data"]["batchNo"], "verifyType": "asset_person"},
    ).json()
    assert batches["code"] == 0, batches
    person_batch = batches["data"]["list"][0]
    assert person_batch["taskStatus"] == "PENDING_DISPATCH"
    assert person_batch["errorCount"] >= 1

    skip = client.put(
        f"/admin-api/ims/asset/verify/task/{person_batch['id']}",
        headers=auth,
        json={"taskStatus": "CLOSED"},
    ).json()
    assert skip["code"] == 1014, skip
    assert "工单状态非法" in skip["msg"]

    missing = client.put("/admin-api/ims/asset/verify/task/99999999", headers=auth, json={"taskStatus": "REPAIRING", "ownerUserId": admin_id}).json()
    assert missing["code"] == 1014
    assert "校验批次不存在" in missing["msg"]

    dispatched = client.put(
        f"/admin-api/ims/asset/verify/task/{person_batch['id']}",
        headers=auth,
        json={"taskStatus": "REPAIRING", "ownerUserId": admin_id, "remark": "派给管理员"},
    ).json()
    assert dispatched["code"] == 0, dispatched
    assert dispatched["data"]["taskStatus"] == "REPAIRING"
    assert dispatched["data"]["ownerUserId"] == admin_id

    closed = client.put(
        f"/admin-api/ims/asset/verify/task/{person_batch['id']}",
        headers=auth,
        json={"taskStatus": "CLOSED", "remark": "已复核"},
    ).json()
    assert closed["code"] == 0, closed
    assert closed["data"]["taskStatus"] == "CLOSED"

    again = client.put(
        f"/admin-api/ims/asset/verify/task/{person_batch['id']}",
        headers=auth,
        json={"taskStatus": "REPAIRING", "ownerUserId": admin_id},
    ).json()
    assert again["code"] == 1014

    metrics = client.get("/admin-api/ims/asset/verify/metrics", headers=auth).json()
    assert metrics["code"] == 0, metrics
    assert 0 <= metrics["data"]["relationCompleteRate"] <= 1
    assert 0 <= metrics["data"]["consistencyRate"] <= 1
    assert metrics["data"]["trend"]
