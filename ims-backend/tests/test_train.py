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


def test_train_material_cates_create_list_offline():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    assert cates.json()["code"] == 0
    roots = cates.json()["data"]
    assert len(roots) >= 1
    leaf = roots[0]["children"][0]
    cate_id = leaf["id"]

    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "开播 SOP 2026",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/demo.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["materialNo"].startswith("MT")
    assert body["data"]["status"] == "PUBLISHED"
    material_id = body["data"]["id"]

    listed = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"cateId": cate_id, "title": "开播", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1

    offline = client.delete(f"/admin-api/ims/train/material/{material_id}", headers=auth)
    assert offline.json()["code"] == 0

    again = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"cateId": cate_id, "status": "OFFLINE", "pageNo": 1, "pageSize": 10},
    )
    assert again.json()["code"] == 0
    assert any(row["id"] == material_id for row in again.json()["data"]["list"])


def test_train_task_create_and_list():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "任务关联资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/task.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]

    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "新人 onboarding",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["taskNo"].startswith("TT")
    assert body["data"]["assignedCount"] == 1

    listed = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": "onboarding", "pageNo": 1, "pageSize": 10},
    )
    list_body = listed.json()
    assert list_body["code"] == 0
    assert list_body["data"]["total"] >= 1
    row = next(r for r in list_body["data"]["list"] if r["taskName"] == "新人 onboarding")
    assert row["finishRate"] == 0.0
    assert row["materialCount"] == 1


def test_train_task_1102_deadline_past():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "过期测试资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/past.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]
    bad = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "过期任务",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2020-01-01T00:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert bad.json()["code"] == 1102


def test_train_stat_summary():
    auth = headers()
    summary = client.get("/admin-api/ims/train/stat/summary", headers=auth)
    assert summary.json()["code"] == 0
    data = summary.json()["data"]
    assert "taskCount" in data
    assert "avgFinishRate" in data
