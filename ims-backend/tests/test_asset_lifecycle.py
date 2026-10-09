"""#63 · E2E-S5-02 资产状态全流转：领用 → 使用 → 归还 → 报废。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import User
from app.security import hash_password

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    return int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])


def test_asset_status_full_flow_checkout_use_return_scrap():
    auth = headers()
    admin_id = _admin_id(auth)
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={
            "assetCode": "AS-PY-63",
            "assetName": "pytest显示器",
            "assetType": "OFFICE",
            "spec": "27寸",
            "purchaseDate": "2026-10-08",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["status"] == "PENDING_REVIEW"
    assert body["data"]["timeline"][0]["eventType"] == "REGISTER"
    asset_id = body["data"]["id"]

    duplicate = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-63", "assetName": "另一台", "assetType": "OFFICE"},
    )
    assert duplicate.json()["code"] == 1012

    bad_type = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-BAD", "assetName": "坏类型", "assetType": "NO_TYPE"},
    )
    assert bad_type.json()["code"] == 1503

    early_use = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/use", headers=auth, json={"remark": "过早"})
    assert early_use.json()["code"] == 1015

    missing_owner = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": 99999, "purpose": "无此人"},
    )
    assert missing_owner.json()["code"] == 1500

    checked = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    )
    assert checked.json()["code"] == 0, checked.json()
    assert checked.json()["data"]["status"] == "IN_USE"
    assert checked.json()["data"]["used"] is False
    assert checked.json()["data"]["ownerUserId"] == admin_id
    listed = client.get(
        "/admin-api/ims/corp/device/office/page",
        headers=auth,
        params={"keyword": "AS-PY-63"},
    ).json()
    assert listed["code"] == 0
    assert listed["data"]["list"][0]["used"] is False

    again = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "重复领用"},
    )
    assert again.json()["code"] == 1012

    early_return = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/return", headers=auth, json={})
    assert early_return.json()["code"] == 1015
    assert "使用" in early_return.json()["msg"]

    early_scrap = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
        headers=auth,
        json={"remark": "未归还"},
    )
    assert early_scrap.json()["code"] == 1015

    used = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/use",
        headers=auth,
        json={"remark": "现场使用"},
    )
    assert used.json()["code"] == 0, used.json()
    assert used.json()["data"]["status"] == "IN_USE"
    assert used.json()["data"]["used"] is True
    assert any(item["eventType"] == "USE" for item in used.json()["data"]["timeline"])

    returned = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/return",
        headers=auth,
        json={"remark": "归还入库"},
    )
    assert returned.json()["code"] == 0, returned.json()
    assert returned.json()["data"]["status"] == "RETURNED"
    assert returned.json()["data"]["ownerUserId"] is None

    no_reason = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/scrap", headers=auth, json={"remark": "  "})
    assert no_reason.json()["code"] == 1001

    scrapped = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
        headers=auth,
        json={"remark": "无法修复"},
    )
    assert scrapped.json()["code"] == 0, scrapped.json()
    assert scrapped.json()["data"]["status"] == "SCRAPPED"
    types = [item["eventType"] for item in scrapped.json()["data"]["timeline"]]
    assert types == ["REGISTER", "CHECKOUT", "USE", "RETURN", "SCRAP"]

    office = client.get(
        "/admin-api/ims/corp/device/office/page",
        headers=auth,
        params={"keyword": "AS-PY-63"},
    )
    assert office.json()["code"] == 0
    assert office.json()["data"]["total"] == 1
    assert office.json()["data"]["list"][0]["status"] == "SCRAPPED"
    assert office.json()["data"]["list"][0]["assetType"] == "OFFICE"

    live = client.get(
        "/admin-api/ims/corp/device/live/page",
        headers=auth,
        params={"keyword": "AS-PY-63"},
    )
    assert live.json()["data"]["total"] == 0

    blocked = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id},
    )
    assert blocked.json()["code"] == 1015

    missing = client.get("/admin-api/ims/asset/ledger/999999", headers=auth)
    assert missing.json()["code"] == 1011


def test_terminal_edges_block_checkout_use_return_and_blank_scrap():
    auth = headers()
    admin_id = _admin_id(auth)
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-200", "assetName": "终态显示器", "assetType": "OFFICE"},
    ).json()
    assert created["code"] == 0, created
    asset_id = created["data"]["id"]

    early_use = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/use", headers=auth, json={"remark": "过早"}).json()
    assert early_use["code"] == 1015
    assert "尚未领用" in early_use["msg"]
    early_return = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/return", headers=auth, json={}).json()
    assert early_return["code"] == 1015
    assert "尚未领用" in early_return["msg"]
    early_scrap = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
        headers=auth,
        json={"remark": "未归还"},
    ).json()
    assert early_scrap["code"] == 1015
    assert "须先归还" in early_scrap["msg"]

    blank_owner = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": 0, "purpose": "无责任人"},
    ).json()
    assert blank_owner["code"] == 1001
    assert "责任人" in blank_owner["msg"]

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "asset_edge_off", User.deleted == 0))
        if user is None:
            user = User(
                username="asset_edge_off",
                nickname="停用责任人",
                mobile="13900000200",
                password_hash=hash_password("Admin@123"),
                status="DISABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(user)
            db.flush()
        else:
            user.status = "DISABLED"
        db.commit()
        disabled_id = int(user.id)
    finally:
        db.close()

    denied = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": disabled_id, "purpose": "停用"},
    ).json()
    assert denied["code"] == 1501
    assert "停用" in denied["msg"]

    checked = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    client.post(f"/admin-api/ims/asset/ledger/{asset_id}/use", headers=auth, json={"remark": "现场使用"})
    returned = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/return",
        headers=auth,
        json={"remark": "归还入库"},
    ).json()
    assert returned["code"] == 0, returned

    again = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "再领"},
    ).json()
    assert again["code"] == 1015
    assert "已归还，不能再领用" in again["msg"]
    used = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/use", headers=auth, json={}).json()
    assert used["code"] == 1015
    assert "已归还，不能再使用" in used["msg"]
    returned_again = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/return", headers=auth, json={}).json()
    assert returned_again["code"] == 1015
    assert "不能再次归还" in returned_again["msg"]
    blank_scrap = client.post(f"/admin-api/ims/asset/ledger/{asset_id}/scrap", headers=auth, json={"remark": " "}).json()
    assert blank_scrap["code"] == 1001

    scrapped = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
        headers=auth,
        json={"remark": "无法修复"},
    ).json()
    assert scrapped["code"] == 0, scrapped
    blocked = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id},
    ).json()
    assert blocked["code"] == 1015
    assert "已报废，不能再领用" in blocked["msg"]
    assert client.post(f"/admin-api/ims/asset/ledger/{asset_id}/use", headers=auth, json={}).json()["msg"].find("已报废") >= 0
    assert "已报废" in client.post(f"/admin-api/ims/asset/ledger/{asset_id}/return", headers=auth, json={}).json()["msg"]
    assert "再次报废" in client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
        headers=auth,
        json={"remark": "再报"},
    ).json()["msg"]
