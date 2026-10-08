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


def test_air_kb_upload_page_download_stub():
    auth = headers()
    tree = client.get("/admin-api/ims/air/kb/tree", headers=auth)
    assert tree.json()["code"] == 0
    assert tree.json()["data"][0]["children"]

    cate_tree = client.get(
        "/admin-api/ims/air/kb/category/tree",
        headers=auth,
        params={"kbId": tree.json()["data"][0]["id"]},
    )
    assert cate_tree.json()["code"] == 0

    up = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"title": "制度汇编", "fileKey": "kb/2026/policy.pdf", "fileSize": 1024},
    )
    assert up.json()["code"] == 0
    assert up.json()["data"]["auditStatus"] == ["PENDING"]
    doc_id = up.json()["data"]["docIds"][0]

    blocked = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=auth)
    assert blocked.json()["code"] == 1001

    audit = client.post(
        "/admin-api/ims/air/kb/doc/audit",
        headers=auth,
        json={"docId": doc_id, "approve": True},
    )
    assert audit.json()["code"] == 0
    assert audit.json()["data"]["auditStatus"] == "PUBLISHED"

    page = client.get("/admin-api/ims/air/kb/page", headers=auth, params={"pageNo": 1, "pageSize": 5})
    assert page.json()["code"] == 0
    assert any(r["id"] == doc_id for r in page.json()["data"]["list"])

    dl = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=auth)
    assert dl.json()["code"] == 0
    assert dl.json()["data"]["stub"] is True
    assert "policy.pdf" in dl.json()["data"]["fileKey"]


def test_air_kb_audit_reject_requires_note():
    auth = headers()
    up = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"title": "驳回测", "fileKey": "kb/reject.pdf"},
    )
    doc_id = up.json()["data"]["docIds"][0]
    bad = client.post(
        "/admin-api/ims/air/kb/doc/audit",
        headers=auth,
        json={"docId": doc_id, "approve": False},
    )
    assert bad.json()["code"] == 1001
