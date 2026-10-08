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


def test_air_expert_create_page_grant():
    auth = headers()
    skill = client.post(
        "/admin-api/ims/air/skill",
        headers=auth,
        json={"skillName": "专家挂载技能 W9-7", "category": "直播"},
    )
    assert skill.json()["code"] == 0
    skill_id = skill.json()["data"]["id"]
    client.put(f"/admin-api/ims/air/skill/{skill_id}/submit-audit", headers=auth)
    pub_skill = client.put(f"/admin-api/ims/air/skill/{skill_id}/audit", headers=auth, json={"approve": True})
    assert pub_skill.json()["data"]["status"] == "PUBLISHED"

    created = client.post(
        "/admin-api/ims/air/expert",
        headers=auth,
        json={
            "expertName": "直播运营专家 W9-7",
            "scene": "直播复盘",
            "systemPrompt": "你是直播运营专家。",
            "skillIds": [skill_id],
            "toolWhitelist": ["experts.assemble"],
        },
    )
    assert created.json()["code"] == 0
    expert_id = created.json()["data"]["id"]

    listed = client.get(
        "/admin-api/ims/air/expert/page",
        headers=auth,
        params={"expertName": "W9-7", "pageNo": 1, "pageSize": 5},
    )
    assert listed.json()["code"] == 0
    assert any(r["id"] == expert_id for r in listed.json()["data"]["list"])

    published = client.put(f"/admin-api/ims/air/expert/{expert_id}/publish", headers=auth)
    assert published.json()["data"]["status"] == "PUBLISHED"

    detail = client.get(f"/admin-api/ims/air/expert/{expert_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["assemblePreview"]["systemPrompt"]

    grant = client.post(
        "/admin-api/ims/air/expert/grant",
        headers=auth,
        json={"expertId": expert_id, "grantType": "USER", "grantId": 1},
    )
    assert grant.json()["code"] == 0
    assert grant.json()["data"]["status"] == "ACTIVE"
