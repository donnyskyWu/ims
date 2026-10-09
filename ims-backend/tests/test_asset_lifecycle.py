"""#63 · E2E-S5-02 资产状态全流转：领用 → 使用 → 归还 → 报废。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app

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
