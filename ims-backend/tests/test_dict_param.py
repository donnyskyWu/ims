import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db



client = TestClient(app)


def login() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_platform_dict_seed_and_disabled_cannot_delete():
    headers = login()
    types = client.get("/admin-api/ims/system/dict-type/list", headers=headers).json()["data"]
    assert any(row["dictType"] == "dict_sop_node_type" for row in types)
    rows = client.get(
        "/admin-api/ims/system/dict-data/list",
        headers=headers,
        params={"dictType": "dict_platform_type"},
    ).json()["data"]
    assert rows
    assert any(row["dictValue"] == "DOUYIN" for row in rows)
    disabled = next(row for row in rows if row["status"] == "DISABLED")
    blocked = client.delete(f"/admin-api/ims/system/dict-data/{disabled['id']}", headers=headers)
    assert blocked.json()["code"] == 1503
    enabled = next(row for row in rows if row["dictValue"] == "XIAOHONGSHU")
    removed = client.delete(f"/admin-api/ims/system/dict-data/{enabled['id']}", headers=headers)
    assert removed.json()["code"] == 0
    again = client.get(
        "/admin-api/ims/system/dict-data/list",
        headers=headers,
        params={"dictType": "dict_platform_type"},
    ).json()["data"]
    assert all(row["dictValue"] != "XHS" for row in again)


def test_unknown_param_key_and_bool_persists():
    headers = login()
    listed = client.get("/admin-api/ims/system/param", headers=headers).json()["data"]
    keys = {row["paramKey"] for row in listed}
    assert "work.task.confirm.auto-ai-generate" in keys
    assert "content.review.level1.role" in keys
    assert "dingtalk.sso.enabled" in keys
    assert "dingtalk.corpId" in keys
    assert "football.webapiBaseUrl" in keys
    assert "air.key.ip_whitelist.enabled" in keys
    unknown = client.put("/admin-api/ims/system/param", headers=headers, json={"paramKey": "not.a.key", "paramValue": "1"})
    assert unknown.json()["code"] == 1213
    saved = client.put(
        "/admin-api/ims/system/param",
        headers=headers,
        json={"paramKey": "work.task.confirm.auto-ai-generate", "paramValue": True},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["paramValue"] == "true"
    again = client.get("/admin-api/ims/system/param", headers=headers).json()["data"]
    row = next(item for item in again if item["paramKey"] == "work.task.confirm.auto-ai-generate")
    assert row["paramValue"] == "true"


def test_secret_param_masks_and_skips_empty_update():
    headers = login()
    saved = client.put(
        "/admin-api/ims/system/param",
        headers=headers,
        json={"paramKey": "dingtalk.clientSecret", "paramValue": "super-secret-value"},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["paramValue"] == "********"
    assert saved.json()["data"]["secret"] is True
    noop = client.put(
        "/admin-api/ims/system/param",
        headers=headers,
        json={"paramKey": "dingtalk.clientSecret", "paramValue": ""},
    )
    assert noop.json()["code"] == 0
    assert noop.json()["data"]["paramValue"] == "********"
