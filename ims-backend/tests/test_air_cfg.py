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


def test_air_cfg_model_prompt_crud():
    auth = headers()
    models = client.get("/admin-api/ims/air/cfg/model/page", headers=auth)
    assert models.json()["code"] == 0
    assert models.json()["data"]["list"]

    created = client.post(
        "/admin-api/ims/air/cfg/model",
        headers=auth,
        json={"vendor": "GPT", "modelName": "gpt-4o-mini", "endpointUrl": "https://api.openai.com/v1", "status": "CONNECTED"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    updated = client.put(
        f"/admin-api/ims/air/cfg/model/{mid}",
        headers=auth,
        json={"vendor": "GPT", "modelName": "gpt-4o", "endpointUrl": "https://api.openai.com/v1", "status": "CONNECTED"},
    )
    assert updated.json()["code"] == 0

    prompts = client.get("/admin-api/ims/air/cfg/prompt/page", headers=auth)
    assert prompts.json()["code"] == 0
    assert prompts.json()["data"]["list"]

    pr = client.post(
        "/admin-api/ims/air/cfg/prompt",
        headers=auth,
        json={"scene": "测试场景", "docType": "NOTE", "content": "hello prompt"},
    )
    assert pr.json()["code"] == 0


def test_air_cfg_key_and_audit_page():
    auth = headers()
    keys = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert keys.json()["code"] == 0
    assert keys.json()["data"]["total"] >= 1

    audit = client.get("/admin-api/ims/air/cfg/audit/page", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert audit.json()["code"] == 0
    assert audit.json()["data"]["total"] >= 1
