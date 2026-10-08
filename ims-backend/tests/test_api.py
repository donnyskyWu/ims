import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db



client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["code"] == 0


def test_login_and_user_mask():
    res = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"})
    body = res.json()
    assert body["code"] == 0
    token = body["data"]["accessToken"]
    page = client.get("/admin-api/ims/system/user/page", headers={"Authorization": f"Bearer {token}"})
    assert page.json()["data"]["list"][0]["mobile"] == "138****5678"


def test_create_and_reject_pk_change():
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "bob", "nickname": "鲍勃", "mobile": "13900001111", "password": "Pass@123"},
    )
    assert created.json()["code"] == 0
    user_id = int(created.json()["data"]["id"])
    changed = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=headers,
        json={"userId": user_id + 9, "nickname": "改主键"},
    )
    assert changed.status_code == 200
    assert changed.json()["code"] == 1211


def test_login_lock_on_sixth_failure():
    for _ in range(5):
        res = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "wrong"})
        assert res.json()["code"] == 1006
    locked = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "wrong"})
    assert locked.json()["code"] == 1001


def test_sso_matches_local_mobile():
    state = client.get("/admin-api/ims/auth/sso/redirect").json()["data"]["state"]
    res = client.post("/admin-api/ims/auth/sso/callback", json={"authCode": "13812345678", "state": state})
    assert res.json()["code"] == 0
    assert res.json()["data"]["profile"]["username"] == "admin"


def test_user_api_requires_login():
    res = client.get("/admin-api/ims/system/user/page")
    assert res.status_code == 401
