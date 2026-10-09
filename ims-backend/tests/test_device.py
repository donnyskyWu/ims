import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine



client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_office_and_live_pages_stay_empty():
    auth = headers()
    office = client.get("/admin-api/ims/corp/device/office/page", headers=auth)
    assert office.json()["code"] == 0
    assert office.json()["data"]["list"] == []
    assert office.json()["data"]["total"] == 0
    live = client.get("/admin-api/ims/corp/device/live/page", headers=auth, params={"pageNo": 2, "pageSize": 10})
    assert live.json()["data"]["pageNo"] == 2
    assert live.json()["data"]["total"] == 0
    blocked = client.post("/admin-api/ims/corp/device/office", headers=auth, json={"name": "显示器"})
    assert blocked.status_code == 404


def test_phone_follows_master_contract():
    auth = headers()
    admin_id = int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])
    missing = client.post(
        "/admin-api/ims/master/phone",
        headers=auth,
        json={"phoneNumber": "13700003333", "keeperId": 99999, "status": "IN_USE"},
    )
    assert missing.json()["code"] == 1500
    bad = client.post(
        "/admin-api/ims/master/phone",
        headers=auth,
        json={"phoneNumber": "13700003333", "keeperId": admin_id, "status": "IN_USE", "phoneType": "NO_TYPE"},
    )
    assert bad.json()["code"] == 1503
    created = client.post(
        "/admin-api/ims/master/phone",
        headers=auth,
        json={
            "phoneNumber": "13700003333",
            "phoneCode": "PH-001",
            "phoneModel": "iPhone 15",
            "keeperId": admin_id,
            "status": "IN_USE",
            "deviceNumber": "DV-9",
            "phoneType": "IPHONE",
        },
    )
    assert created.json()["code"] == 0, created.json()
    assert created.json()["data"]["phoneNumber"] == "137****3333"
    assert "13700003333" not in created.text
    assert "realnameId" not in created.json()["data"]
    listed = client.get("/admin-api/ims/corp/device/phone/page", headers=auth, params={"deviceNumber": "DV-9"})
    assert listed.json()["data"]["total"] == 1
    typed = client.get(
        "/admin-api/ims/master/phone/page",
        headers=auth,
        params={"phoneType": "IPHONE", "deviceNumber": "DV-9"},
    )
    assert typed.json()["code"] == 0
    assert typed.json()["data"]["total"] == 1
    assert typed.json()["data"]["list"][0]["phoneType"] == "IPHONE"
    other = client.get(
        "/admin-api/ims/master/phone/page",
        headers=auth,
        params={"phoneType": "ANDROID", "deviceNumber": "DV-9"},
    )
    assert other.json()["data"]["total"] == 0
    again = client.post(
        "/admin-api/ims/master/phone",
        headers=auth,
        json={"phoneNumber": "13700003333", "keeperId": admin_id, "status": "IN_USE"},
    )
    assert again.json()["code"] == 1001
