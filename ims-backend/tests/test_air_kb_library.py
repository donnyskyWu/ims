import os
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import Role, RolePerm, User, UserRole

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_kb_create_tree_category_and_confidential_audit():
    auth = headers()
    users = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": "admin"},
    )
    assert users.json()["code"] == 0
    owner_id = int(users.json()["data"]["list"][0]["id"])

    empty = client.post("/admin-api/ims/air/kb", headers=auth, json={})
    assert empty.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC知识库单测", "secretLevel": "INTERNAL", "ownerUserId": owner_id},
    )
    assert created.json()["code"] == 0
    kb = created.json()["data"]
    assert kb["status"] == "PUBLISHED"
    assert kb["provider"] == "LOCAL"
    assert kb["kbNo"].startswith("KB-")

    secret = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC机密库单测", "secretLevel": "CONFIDENTIAL", "ownerUserId": owner_id},
    )
    assert secret.json()["code"] == 0
    secret_id = secret.json()["data"]["id"]
    assert secret.json()["data"]["status"] == "PENDING"
    assert secret.json()["data"]["grantsLimit"] == "仅 R1/R3/R4 可授权"

    denied = client.post(
        "/admin-api/ims/air/kb/audit",
        headers=auth,
        json={"kbId": secret_id, "approve": False},
    )
    assert denied.json()["code"] == 1001

    approved = client.post(
        "/admin-api/ims/air/kb/audit",
        headers=auth,
        json={"kbId": secret_id, "approve": True, "auditNote": "同意入库"},
    )
    assert approved.json()["code"] == 0
    assert approved.json()["data"]["status"] == "PUBLISHED"

    cat = client.post(
        "/admin-api/ims/air/kb/category",
        headers=auth,
        json={"kbId": kb["id"], "categoryName": "TC分类单测"},
    )
    assert cat.json()["code"] == 0
    cate_id = cat.json()["data"]["categoryId"]

    renamed = client.put(
        f"/admin-api/ims/air/kb/category/{cate_id}",
        headers=auth,
        json={"kbId": kb["id"], "categoryName": "TC分类改名"},
    )
    assert renamed.json()["code"] == 0

    tree = client.get("/admin-api/ims/air/kb/tree", headers=auth)
    assert tree.json()["code"] == 0
    node = next(item for item in tree.json()["data"] if item["id"] == kb["id"])
    assert node["secretLevel"] == "INTERNAL"
    names = [child["categoryName"] for child in node["children"]]
    assert "TC分类改名" in names

    removed = client.delete(
        f"/admin-api/ims/air/kb/category/{cate_id}",
        headers=auth,
        params={"kbId": kb["id"]},
    )
    assert removed.json()["code"] == 0


def test_kb_confidential_grant_blocks_plain_user():
    auth = headers()
    users = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": "admin"},
    )
    owner_id = int(users.json()["data"]["list"][0]["id"])
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": "kb_plain_c065", "nickname": "普通授权对象", "mobile": "13900006501", "password": "Pass@123"},
    )
    if created.json()["code"] != 0:
        listed = client.get(
            "/admin-api/ims/system/user/page",
            headers=auth,
            params={"pageNo": 1, "pageSize": 5, "username": "kb_plain_c065"},
        )
        plain_id = int(listed.json()["data"]["list"][0]["id"])
    else:
        plain_id = int(created.json()["data"]["id"])

    secret = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC机密授权单测", "secretLevel": "CONFIDENTIAL", "ownerUserId": owner_id},
    )
    kb_id = secret.json()["data"]["id"]
    client.post("/admin-api/ims/air/kb/audit", headers=auth, json={"kbId": kb_id, "approve": True})
    blocked = client.post(
        "/admin-api/ims/air/kb/grant",
        headers=auth,
        json={"kbId": kb_id, "grantType": "PERSON", "grantId": plain_id},
    )
    assert blocked.json()["code"] == 1001
    assert "仅 R1/R3/R4" in blocked.json()["msg"]

    allowed = client.post(
        "/admin-api/ims/air/kb/grant",
        headers=auth,
        json={"kbId": kb_id, "grantType": "PERSON", "grantId": owner_id, "expireAt": "2027-03-31"},
    )
    assert allowed.json()["code"] == 0


def _login(username: str, password: str) -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def _ensure_user(auth: dict, username: str, mobile: str, nickname: str) -> int:
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": username, "nickname": nickname, "mobile": mobile, "password": "Pass@123"},
    )
    if created.json()["code"] == 0:
        return int(created.json()["data"]["id"])
    listed = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": username},
    )
    return int(listed.json()["data"]["list"][0]["id"])


def _bind_kb_reader(user_id: int, role_key: str) -> None:
    db = SessionLocal()
    try:
        role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
        if role is None:
            role = Role(role_name=role_key, role_key=role_key, data_scope="SELF", status="ENABLED", source="MANUAL")
            db.add(role)
            db.flush()
            db.add(RolePerm(role_id=role.id, module_code="air", perm_code="air:kb:query", perm_level="R", tenant_id=0))
        linked = db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id))
        if linked is None:
            db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        db.commit()
    finally:
        db.close()


def test_kb_owner_candidates_without_user_directory():
    auth = headers()
    reader_id = _ensure_user(auth, "kb_r11_c065", "13900006511", "知识库责任候选")
    off_id = _ensure_user(auth, "kb_off_c065", "13900006512", "停用候选")
    _bind_kb_reader(reader_id, "air-kb-c065")
    db = SessionLocal()
    try:
        off = db.get(User, off_id)
        off.status = "DISABLED"
        db.commit()
    finally:
        db.close()

    reader = _login("kb_r11_c065", "Pass@123")
    directory = client.get("/admin-api/ims/system/user/page", headers=reader, params={"pageNo": 1, "pageSize": 50})
    assert directory.json()["code"] == 0
    assert [int(item["id"]) for item in directory.json()["data"]["list"]] == [reader_id]

    picked = client.get("/admin-api/ims/air/kb/owner-candidates", headers=reader)
    assert picked.json()["code"] == 0
    rows = picked.json()["data"]
    assert rows
    assert all(set(item.keys()) == {"userId", "name"} for item in rows)
    ids = {int(item["userId"]) for item in rows}
    assert reader_id in ids
    assert off_id not in ids
    assert len(ids) > 1
    names = {item["name"] for item in rows}
    assert "知识库责任候选" in names
    assert "停用候选" not in names


def test_kb_download_respects_publish_and_secret():
    auth = headers()
    reader_id = _ensure_user(auth, "kb_reader_c065", "13900006513", "知识库下载员")
    peer_id = _ensure_user(auth, "kb_peer_c065", "13900006514", "知识库旁观者")
    _bind_kb_reader(reader_id, "air-kb-reader-c065")
    _bind_kb_reader(peer_id, "air-kb-peer-c065")
    reader = _login("kb_reader_c065", "Pass@123")
    peer = _login("kb_peer_c065", "Pass@123")
    owner_id = int(
        client.get(
            "/admin-api/ims/system/user/page",
            headers=auth,
            params={"pageNo": 1, "pageSize": 5, "username": "admin"},
        ).json()["data"]["list"][0]["id"]
    )
    created = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC下载密级单测", "secretLevel": "INTERNAL", "ownerUserId": owner_id},
    )
    assert created.json()["code"] == 0
    kb_id = created.json()["data"]["id"]
    granted = client.post(
        "/admin-api/ims/air/kb/grant",
        headers=auth,
        json={"kbId": kb_id, "grantType": "PERSON", "grantId": reader_id},
    )
    assert granted.json()["code"] == 0

    internal = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        data={"kbId": str(kb_id), "secretLevel": "INTERNAL", "title": "TC内部可下"},
        files={"file": ("internal.txt", b"internal-bytes", "text/plain")},
    )
    internal_id = internal.json()["data"]["docIds"][0]
    client.post("/admin-api/ims/air/kb/doc/audit", headers=auth, json={"docId": internal_id, "approve": True})
    opened = client.get(f"/admin-api/ims/air/kb/doc/{internal_id}/download", headers=reader)
    assert opened.status_code == 200
    assert "attachment" in opened.headers["content-disposition"]

    secret = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        data={"kbId": str(kb_id), "secretLevel": "CONFIDENTIAL", "title": "TC机密下载"},
        files={"file": ("secret.txt", b"secret-bytes", "text/plain")},
    )
    doc_id = secret.json()["data"]["docIds"][0]
    pending = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=reader)
    assert pending.json()["code"] == 1001
    assert pending.json()["msg"] == "未发布文档不可下载"

    audited = client.post("/admin-api/ims/air/kb/doc/audit", headers=auth, json={"docId": doc_id, "approve": True})
    assert audited.json()["code"] == 0
    allowed = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=reader)
    assert allowed.status_code == 200
    assert "attachment" in allowed.headers["content-disposition"]
    blocked = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=peer)
    assert blocked.json()["code"] == 1001
    assert blocked.json()["msg"] == "当前密级无权下载"
    assert "attachment" not in blocked.headers.get("content-disposition", "")
    admin_dl = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=auth)
    assert admin_dl.status_code == 200
    assert "attachment" in admin_dl.headers["content-disposition"]


def test_kb_doc_download_content_disposition():
    auth = headers()
    up = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={
            "title": "TC下载正文",
            "fileKey": "kb/c065/body.txt",
            "content": "hello-c065-body",
            "contentType": "text/plain",
        },
    )
    assert up.json()["code"] == 0
    doc_id = up.json()["data"]["docIds"][0]
    pending = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=auth)
    assert pending.json()["code"] == 1001
    assert pending.json()["msg"] == "未发布文档不可下载"
    missing = client.get("/admin-api/ims/air/kb/doc/99999999/download", headers=auth)
    assert missing.json()["code"] == 1004
    audited = client.post("/admin-api/ims/air/kb/doc/audit", headers=auth, json={"docId": doc_id, "approve": True})
    assert audited.json()["code"] == 0
    downloaded = client.get(f"/admin-api/ims/air/kb/doc/{doc_id}/download", headers=auth)
    assert downloaded.status_code == 200
    disposition = downloaded.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "body.txt" in disposition
    assert downloaded.content == "hello-c065-body".encode()


def test_kb_timestamps_use_shanghai():
    auth = headers()
    owner_id = int(
        client.get(
            "/admin-api/ims/system/user/page",
            headers=auth,
            params={"pageNo": 1, "pageSize": 5, "username": "admin"},
        ).json()["data"]["list"][0]["id"]
    )
    created = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC时区单测", "secretLevel": "INTERNAL", "ownerUserId": owner_id},
    )
    assert created.json()["code"] == 0
    bj = timezone(timedelta(hours=8))
    shown = datetime.strptime(created.json()["data"]["updatedAt"], "%Y-%m-%d %H:%M").replace(tzinfo=bj)
    assert abs((datetime.now(bj) - shown).total_seconds()) < 120

    uploaded = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"title": "TC时区资料", "fileKey": "kb/c084/clock.txt", "content": "clock", "kbId": created.json()["data"]["id"]},
    )
    assert uploaded.json()["code"] == 0
    stamp = uploaded.json()["data"]["doc"]["createdAt"]
    assert stamp.endswith("+08:00")
    parsed = datetime.fromisoformat(stamp)
    assert abs((datetime.now(bj) - parsed).total_seconds()) < 120
