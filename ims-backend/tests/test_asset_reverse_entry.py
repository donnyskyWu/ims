"""#72 · 按账号 / 按场次反查资产。物理盘点未定义，本片做 ASSET-002 剩余入口。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import LiveSession
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)

ACCOUNT_NO = "AC-REV-72"
OTHER_NO = "AC-REV-72B"
SESSION_CODE = "IMS20261008DYE0072"
OTHER_SESSION = "IMS20261008DYE0073"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    return int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])


def _account(account_no: str, holder_id: int) -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            holder_user_id=holder_id,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _session(account_id: int, account_no: str, code: str, owner_id: int) -> int:
    db = SessionLocal()
    try:
        row = LiveSession(
            session_code=code,
            account_id=account_id,
            account_no=account_no,
            responsible_user_id=owner_id,
            device_asset_ids="[]",
            platform="DOUYIN",
            topic="反查场次",
            session_status="ENDED",
            tenant_id=0,
            creator=owner_id,
            deleted=0,
        )
        db.add(row)
        db.commit()
        return int(row.id)
    finally:
        db.close()


def _create(auth: dict, code: str, **extra) -> dict:
    body = {"assetCode": code, "assetName": code, "assetType": "OFFICE", **extra}
    return client.post("/admin-api/ims/asset/ledger", headers=auth, json=body).json()


def test_reverse_by_account_and_session_keeps_asset_status():
    auth = headers()
    admin_id = _admin_id(auth)
    account_id = _account(ACCOUNT_NO, admin_id)
    other_id = _account(OTHER_NO, admin_id)
    session_id = _session(account_id, ACCOUNT_NO, SESSION_CODE, admin_id)
    _session(other_id, OTHER_NO, OTHER_SESSION, admin_id)

    missing = client.get("/admin-api/ims/asset/reverse/by-account/0", headers=auth, params={"accountNo": "AC-NO-SUCH"}).json()
    assert missing["code"] == 1500
    bad_code = client.get("/admin-api/ims/asset/reverse/by-session/NOT-A-SESSION", headers=auth).json()
    assert bad_code["code"] == 1001
    gone = client.get("/admin-api/ims/asset/reverse/by-session/IMS20261008AAA0001", headers=auth).json()
    assert gone["code"] == 1500

    mismatch = _create(auth, "AS-REV-BAD", accountNo=OTHER_NO, sessionCode=SESSION_CODE)
    assert mismatch["code"] == 1001, mismatch

    office = _create(auth, "AS-REV-ACC", accountNo=ACCOUNT_NO)
    assert office["code"] == 0, office
    assert "绑定账号 AC-REV-72" in office["data"]["timeline"][0]["remark"]
    assert "绑定场次" not in office["data"]["timeline"][0]["remark"]

    pending = client.get(
        "/admin-api/ims/asset/reverse/by-account/0",
        headers=auth,
        params={"accountNo": ACCOUNT_NO},
    ).json()
    assert pending["code"] == 0, pending
    assert pending["data"]["summary"]["total"] == 1
    assert pending["data"]["summary"]["inUse"] == 0
    assert pending["data"]["list"][0]["assetCode"] == "AS-REV-ACC"
    assert pending["data"]["list"][0]["status"] == "PENDING_REVIEW"
    assert pending["data"]["list"][0]["relatedAccountNo"] == ACCOUNT_NO
    assert pending["data"]["list"][0]["bindType"] == "HOLD"

    checked = client.post(
        f"/admin-api/ims/asset/ledger/{office['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    in_use = client.get(f"/admin-api/ims/asset/reverse/by-account/{account_id}", headers=auth).json()
    assert in_use["data"]["list"][0]["status"] == "IN_USE"
    assert in_use["data"]["summary"]["inUse"] == 1

    shoot = _create(auth, "AS-REV-SES", sessionCode=SESSION_CODE)
    assert shoot["code"] == 0, shoot
    assert "绑定场次 IMS20261008DYE0072" in shoot["data"]["timeline"][0]["remark"]
    by_session = client.get(f"/admin-api/ims/asset/reverse/by-session/{session_id}", headers=auth).json()
    assert by_session["code"] == 0, by_session
    assert [item["assetCode"] for item in by_session["data"]["list"]] == ["AS-REV-SES"]
    assert by_session["data"]["list"][0]["status"] == "PENDING_REVIEW"
    assert by_session["data"]["list"][0]["relatedAccountNo"] == ACCOUNT_NO

    by_code = client.get(f"/admin-api/ims/asset/reverse/by-session/{SESSION_CODE}", headers=auth).json()
    assert [item["assetCode"] for item in by_code["data"]["list"]] == ["AS-REV-SES"]

    both = client.get(f"/admin-api/ims/asset/reverse/by-account/{account_id}", headers=auth).json()
    codes = {item["assetCode"] for item in both["data"]["list"]}
    assert codes == {"AS-REV-ACC", "AS-REV-SES"}
    assert both["data"]["summary"]["total"] == 2
    assert both["data"]["summary"]["inUse"] == 1

    detail = client.get(f"/admin-api/ims/asset/forward/detail/{shoot['data']['id']}", headers=auth).json()
    assert detail["code"] == 0, detail
    assert detail["data"]["bindAccounts"][0]["accountNo"] == ACCOUNT_NO
    assert detail["data"]["liveSessions"][0]["sessionCode"] == SESSION_CODE
