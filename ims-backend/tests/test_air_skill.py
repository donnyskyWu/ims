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


def test_air_skill_create_list_audit():
    auth = headers()
    created = client.post(
        "/admin-api/ims/air/skill",
        headers=auth,
        json={"skillName": "测试技能 W9", "category": "数据分析"},
    )
    assert created.json()["code"] == 0
    skill_id = created.json()["data"]["id"]

    listed = client.get("/admin-api/ims/air/skill/list", headers=auth, params={"skillName": "W9", "pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert any(r["id"] == skill_id for r in listed.json()["data"]["list"])

    submit = client.put(f"/admin-api/ims/air/skill/{skill_id}/submit-audit", headers=auth)
    assert submit.json()["code"] == 0
    assert submit.json()["data"]["auditStatus"] == "PENDING"

    approved = client.put(f"/admin-api/ims/air/skill/{skill_id}/audit", headers=auth, json={"approve": True})
    assert approved.json()["code"] == 0
    assert approved.json()["data"]["status"] == "PUBLISHED"
