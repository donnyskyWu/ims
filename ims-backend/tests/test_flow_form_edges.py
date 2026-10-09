"""#234 local tails: start-form length, businessKey replay, approval comment limit."""

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


def published_leave(auth: dict) -> dict:
    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    assert published["code"] == 0
    return next(row for row in published["data"]["list"] if row["templateCode"] == "FL-LEAVE")


def test_flow_start_title_and_business_key_edges():
    auth = headers()
    leave = published_leave(auth)

    missing = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={"templateId": leave["id"], "formData": {"title": "   "}},
    ).json()
    assert missing["code"] == 1001
    assert "必填" in missing["msg"]

    over_title = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={"templateId": leave["id"], "formData": {"title": "假" * 257}, "businessKey": "pytest-flow-title-257"},
    ).json()
    assert over_title["code"] == 1001
    assert "256" in over_title["msg"]

    over_key = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 超长键"},
            "businessKey": "k" * 65,
        },
    ).json()
    assert over_key["code"] == 1001
    assert "64" in over_key["msg"]

    key = "pytest-flow-form-edge-001"
    title = "假" * 256
    first = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={"templateId": leave["id"], "formData": {"title": title}, "businessKey": key},
    ).json()
    assert first["code"] == 0
    assert first["data"]["instanceNo"]
    assert first["data"].get("idempotent") is not True

    again = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={"templateId": leave["id"], "formData": {"title": "另一标题"}, "businessKey": key},
    ).json()
    assert again["code"] == 0
    assert again["data"]["idempotent"] is True
    assert again["data"]["instanceNo"] == first["data"]["instanceNo"]
    assert again["data"]["title"] == title


def test_flow_approve_comment_length():
    auth = headers()
    leave = published_leave(auth)
    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 意见长度"},
            "businessKey": "pytest-flow-comment-512",
        },
    ).json()
    assert started["code"] == 0
    instance_no = started["data"]["instanceNo"]

    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 50}).json()
    task = next(row for row in todo["data"]["list"] if row["instanceNo"] == instance_no)

    too_long = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "意" * 513},
    ).json()
    assert too_long["code"] == 1001
    assert "512" in too_long["msg"]

    still = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 50}).json()
    assert any(row["instanceNo"] == instance_no and row["taskStatus"] == "PENDING" for row in still["data"]["list"])

    ok = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "意" * 512},
    ).json()
    assert ok["code"] == 0
    assert ok["data"]["newStatus"] == "APPROVED"
