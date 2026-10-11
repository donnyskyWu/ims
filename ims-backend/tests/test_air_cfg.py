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
    assert created.json()["data"]["status"] == "DISCONNECTED"
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


def test_air_cfg_model_test_is_stub():
    auth = headers()
    empty = client.post("/admin-api/ims/air/cfg/model", headers=auth, json={})
    assert empty.status_code == 200
    assert empty.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/air/cfg/model",
        headers=auth,
        json={"displayName": "备用直连", "vendor": "自建网关", "modelName": "gpt-4o-mini", "useCase": "降级直连"},
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["status"] == "DISCONNECTED"
    mid = created.json()["data"]["id"]
    blocked = client.post(f"/admin-api/ims/air/cfg/model/{mid}/test", headers=auth)
    assert blocked.json()["code"] == 5004

    saved = client.put(
        f"/admin-api/ims/air/cfg/model/{mid}",
        headers=auth,
        json={"vendor": "自建网关", "modelName": "gpt-4o-mini", "apiKey": "sk-test-1234"},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["apiKeyMask"] == "****1234"
    assert "sk-test" not in saved.text

    tested = client.post(f"/admin-api/ims/air/cfg/model/{mid}/test", headers=auth)
    assert tested.json()["code"] == 0
    assert tested.json()["data"]["status"] == "CONNECTED"
    assert tested.json()["data"]["stub"] is True

    jingcai = client.post(
        "/admin-api/ims/air/cfg/model",
        headers=auth,
        json={"displayName": "jingcai.article", "vendor": "Football jingcai", "modelName": "FOOTBALL_AI_MODEL"},
    )
    jingcai_id = jingcai.json()["data"]["id"]
    jingcai_test = client.post(f"/admin-api/ims/air/cfg/model/{jingcai_id}/test", headers=auth)
    assert jingcai_test.json()["code"] == 0
    assert jingcai_test.json()["data"]["status"] == "CONNECTED"


def test_air_cfg_key_and_audit_page():
    auth = headers()
    keys = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert keys.json()["code"] == 0
    assert keys.json()["data"]["total"] >= 1

    audit = client.get("/admin-api/ims/air/cfg/audit/page", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert audit.json()["code"] == 0
    assert audit.json()["data"]["total"] >= 1
