import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_master_overview_blocks():
    auth = headers()
    res = client.get("/admin-api/ims/master/overview", headers=auth)
    assert res.json()["code"] == 0
    data = res.json()["data"]
    blocks = data["blocks"]
    assert len(blocks) >= 6
    assert data["updatedAt"]
    keys = {b["key"] for b in blocks}
    assert {"company", "realname", "sim", "certificate", "phone", "platformAccount"} <= keys
    for block in blocks:
        assert isinstance(block["count"], int)
        assert str(block["href"]).startswith("/ims/")


def test_master_resource_filter_edges():
    auth = headers()
    company = client.get(
        "/admin-api/ims/corp/resource/company/page",
        headers=auth,
        params={"creditCode": "___no_such_credit___"},
    )
    assert company.json()["code"] == 0
    assert company.json()["data"]["total"] == 0

    person = client.get(
        "/admin-api/ims/corp/resource/realname/page",
        headers=auth,
        params={"idType": "___no_such_id_type___"},
    )
    assert person.json()["code"] == 0
    assert person.json()["data"]["total"] == 0

    sim = client.get(
        "/admin-api/ims/corp/resource/sim-card/page",
        headers=auth,
        params={"phoneNumber": "12345"},
    )
    assert sim.json()["code"] == 0
    assert sim.json()["data"]["total"] == 0

    phone = client.get(
        "/admin-api/ims/corp/device/phone/page",
        headers=auth,
        params={"deviceNumber": "___no_such_device___", "phoneModel": "___no_such_model___"},
    )
    assert phone.json()["code"] == 0
    assert phone.json()["data"]["total"] == 0
