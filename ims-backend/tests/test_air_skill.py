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

    self_audit = client.put(f"/admin-api/ims/air/skill/{skill_id}/audit", headers=auth, json={"approve": True})
    assert self_audit.json()["code"] == 1057

    from app.core import SessionLocal
    from app.models import AirSkill, User

    db = SessionLocal()
    try:
        other = db.query(User).filter(User.username == "e2e_author", User.deleted == 0).one()
        row = db.get(AirSkill, skill_id)
        assert row is not None
        row.owner_user_id = other.id
        db.commit()
    finally:
        db.close()

    rejected = client.put(
        f"/admin-api/ims/air/skill/{skill_id}/audit",
        headers=auth,
        json={"approve": False},
    )
    assert rejected.json()["code"] == 1001

    approved = client.put(
        f"/admin-api/ims/air/skill/{skill_id}/audit",
        headers=auth,
        json={"approve": True, "auditNote": "同意发布"},
    )
    assert approved.json()["code"] == 0
    assert approved.json()["data"]["status"] == "PUBLISHED"

    summary = client.get("/admin-api/ims/air/skill/summary", headers=auth)
    assert summary.json()["code"] == 0
    for key in ("expertCount", "kbCount", "docCount", "activeKeyCount"):
        assert key in summary.json()["data"]
    filtered = client.get(
        "/admin-api/ims/air/skill/list",
        headers=auth,
        params={"skillName": "W9", "category": "数据分析", "pageNo": 1, "pageSize": 5},
    )
    assert any(r["id"] == skill_id for r in filtered.json()["data"]["list"])
