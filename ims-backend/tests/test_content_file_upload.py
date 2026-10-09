"""#108 · POST /content/file/upload 并在执行页保存时绑定 userAttachments。"""

import base64
import os
from pathlib import Path

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

import pytest
from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import ContentSopNode, ContentTask, ImsFile
from app.ops_db import ops_session
from app.ops_models import IpGroup

client = TestClient(app)


@pytest.fixture(autouse=True)
def _file_root(tmp_path, monkeypatch):
    monkeypatch.setenv("IMS_FILE_ROOT", str(tmp_path))
    return tmp_path


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def start_normal_task(auth: dict, name: str = "附件任务") -> int:
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": f"{name} SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "校对",
                    "nodeType": "NORMAL",
                    "ownerRole": "R6",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert sop.json()["code"] == 0
    sop_id = sop.json()["data"]["id"]
    ops = ops_session()
    try:
        group = IpGroup(group_name=f"{name}组", status="ENABLED", leader_user_id=1, tenant_id=0)
        ops.add(group)
        ops.commit()
        ip_group_id = group.id
    finally:
        ops.close()
    plan = client.post(
        "/admin-api/ims/content/plan",
        headers=auth,
        json={
            "planName": name,
            "sopId": sop_id,
            "ipGroupIds": [ip_group_id],
            "startDate": "2026-10-01",
            "endDate": "2026-10-31",
        },
    )
    assert plan.json()["code"] == 0
    started = client.post(f"/admin-api/ims/content/plan/{plan.json()['data']['id']}/start", headers=auth)
    assert started.json()["code"] == 0
    mine = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"onlyMine": True, "pageSize": 20, "planName": name},
    )
    assert mine.json()["code"] == 0
    assert mine.json()["data"]["total"] >= 1
    return mine.json()["data"]["list"][0]["id"]


def upload(auth: dict, filename: str, body: bytes, scene: str | None = None):
    data = {} if scene is None else {"scene": scene}
    return client.post(
        "/admin-api/ims/content/file/upload",
        headers=auth,
        files={"file": (filename, body, "application/octet-stream")},
        data=data,
    )


def test_upload_save_reopen_splits_reference_and_user_attachments():
    auth = headers()
    task_id = start_normal_task(auth)
    db = SessionLocal()
    try:
        task = db.get(ContentTask, task_id)
        node = db.get(ContentSopNode, task.sop_node_id)
        node.attachment_urls = ["参考说明.pdf"]
        db.commit()
    finally:
        db.close()

    stored = upload(auth, "现场记录.txt", b"hello-attachment")
    assert stored.status_code == 200
    payload = stored.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["fileName"] == "现场记录.txt"
    assert data["sizeBytes"] == len(b"hello-attachment")
    assert data["fileKey"].startswith("task_execute_attachment/0/")
    assert data["fileKey"].endswith(".txt")
    assert data["fileUrl"] == f"/admin-api/ims/file/{data['fileKey']}"

    saved = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/save",
        headers=auth,
        json={"deliverables": "已附现场记录", "userAttachments": [{"fileKey": data["fileKey"], "fileName": data["fileName"]}]},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["userAttachments"][0]["fileName"] == "现场记录.txt"

    note_only = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/save",
        headers=auth,
        json={"deliverables": "只改工作说明"},
    )
    assert note_only.json()["code"] == 0
    assert note_only.json()["data"]["userAttachments"][0]["fileKey"] == data["fileKey"]

    execute = client.get(f"/admin-api/ims/content/task/{task_id}/execute", headers=auth)
    body = execute.json()["data"]
    assert body["attachments"] == ["参考说明.pdf"]
    assert body["userAttachments"] == [
        {
            "fileKey": data["fileKey"],
            "fileName": "现场记录.txt",
            "fileUrl": data["fileUrl"],
        }
    ]
    assert body["deliverables"] == "只改工作说明"

    downloaded = client.get(data["fileUrl"], headers=auth)
    assert downloaded.status_code == 200
    assert downloaded.content == b"hello-attachment"


def test_upload_rejects_type_scene_empty_and_oversize(monkeypatch):
    auth = headers()
    denied = upload(auth, "virus.exe", b"nope")
    assert denied.json()["code"] == 1500
    assert denied.json()["msg"] == "不支持的文件类型"

    image_scene = upload(auth, "note.txt", b"abc", scene="content_image")
    assert image_scene.json()["code"] == 1500
    assert image_scene.json()["msg"] == "不支持的文件类型"

    bad_scene = upload(auth, "note.txt", b"abc", scene="oss")
    assert bad_scene.json()["code"] == 1500
    assert bad_scene.json()["msg"] == "scene 无效"

    empty = upload(auth, "note.txt", b"")
    assert empty.json()["code"] == 1500
    assert empty.json()["msg"] == "文件为空"

    monkeypatch.setattr("app.content_file.MAX_BYTES", 4)
    huge = upload(auth, "note.txt", b"12345")
    assert huge.json()["code"] == 1500
    assert huge.json()["msg"] == "文件超过大小限制"

    missing = client.post("/admin-api/ims/content/file/upload", headers=auth, data={"scene": "deliverable"})
    assert missing.json()["code"] == 1500
    assert missing.json()["msg"] == "请选择文件"

    anon = client.post(
        "/admin-api/ims/content/file/upload",
        files={"file": ("note.txt", b"abc", "text/plain")},
    )
    assert anon.status_code == 401


def test_save_rejects_unbound_key_and_download_stays_in_tenant(tmp_path):
    auth = headers()
    task_id = start_normal_task(auth, "附件校验")
    missing = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/save",
        headers=auth,
        json={"userAttachments": [{"fileKey": "task_execute_attachment/0/202610/" + ("ab" * 16) + ".txt", "fileName": "a.txt"}]},
    )
    assert missing.json()["code"] == 1500
    assert missing.json()["msg"] == "附件文件不存在"

    escaped = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/save",
        headers=auth,
        json={"userAttachments": [{"fileKey": "../etc/passwd", "fileName": "passwd"}]},
    )
    assert escaped.json()["code"] == 1500

    other = tmp_path / "task_execute_attachment" / "9" / "202610"
    other.mkdir(parents=True)
    name = "c" * 32 + ".txt"
    (other / name).write_bytes(b"secret")
    foreign = client.get(f"/admin-api/ims/file/task_execute_attachment/9/202610/{name}", headers=auth)
    assert foreign.status_code == 403
    assert foreign.json()["code"] == 1504

    naked = client.get(f"/admin-api/ims/file/task_execute_attachment/0/202610/{name}")
    assert naked.status_code == 401


def test_upload_disk_failure_returns_5005(monkeypatch, tmp_path):
    auth = headers()
    blocker = tmp_path / "not-dir"
    blocker.write_text("x")
    monkeypatch.setenv("IMS_FILE_ROOT", str(blocker))
    failed = upload(auth, "note.txt", b"abc")
    assert failed.json()["code"] == 5005
    assert failed.json()["msg"] == "文件上传失败，请重试"

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
UPLOAD = "/admin-api/ims/content/file/upload"



def test_content_image_upload_roundtrip_and_layout_html():
    auth = headers()
    uploaded = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("cover.png", PNG, "image/png")},
        data={"scene": "content_image"},
    )
    body = uploaded.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["fileName"] == "cover.png"
    assert data["sizeBytes"] == len(PNG)
    assert data["fileKey"].startswith("content_image/0/")
    assert not data["fileKey"].startswith("/")
    assert data["fileUrl"] == "/admin-api/ims/file/" + data["fileKey"]
    assert "oss" not in data["fileKey"]
    stored = Path(os.environ["IMS_FILE_ROOT"]) / data["fileKey"]
    assert stored.is_file()
    assert stored.read_bytes() == PNG

    downloaded = client.get(data["fileUrl"], headers=auth)
    assert downloaded.status_code == 200
    assert downloaded.content == PNG
    assert downloaded.headers["content-type"].startswith("image/png")

    html = (
        f'<img src="{data["fileUrl"]}" alt="{data["fileName"]}" data-file-key="{data["fileKey"]}" />'
    )
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "带图内容", "layoutHtml": html, "body": "正文"},
    )
    assert created.json()["code"] == 0
    content_id = created.json()["data"]["id"]
    assert data["fileKey"] in created.json()["data"]["layoutHtml"]
    detail = client.get(f"/admin-api/ims/content/{content_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["layoutHtml"] == html


def test_upload_default_scene_and_rejects():
    auth = headers()
    defaulted = client.post(UPLOAD, headers=auth, files={"file": ("note.txt", b"hello", "text/plain")})
    assert defaulted.json()["code"] == 0
    assert defaulted.json()["data"]["fileKey"].startswith("task_execute_attachment/")

    deliverable = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("brief.pdf", b"%PDF-1.4\n", "application/pdf")},
        data={"scene": "deliverable"},
    )
    assert deliverable.json()["code"] == 0
    assert deliverable.json()["data"]["fileKey"].startswith("deliverable/")

    bad_scene = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("cover.png", PNG, "image/png")},
        data={"scene": "oss"},
    )
    assert bad_scene.json()["code"] == 1500

    not_image = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("a.txt", b"hello", "text/plain")},
        data={"scene": "content_image"},
    )
    assert not_image.json()["code"] == 1500

    mismatch = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("a.jpg", PNG, "image/jpeg")},
        data={"scene": "content_image"},
    )
    assert mismatch.json()["code"] == 1500

    empty = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("a.png", b"", "image/png")},
        data={"scene": "content_image"},
    )
    assert empty.json()["code"] == 1500

    missing = client.post(UPLOAD, headers=auth, data={"scene": "content_image"})
    assert missing.json()["code"] == 1500

    anon = client.post(UPLOAD, files={"file": ("cover.png", PNG, "image/png")}, data={"scene": "content_image"})
    assert anon.status_code == 401


def test_download_missing_deleted_and_escape(monkeypatch):
    auth = headers()
    uploaded = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("cover.png", PNG, "image/png")},
        data={"scene": "content_image"},
    )
    key = uploaded.json()["data"]["fileKey"]
    missing = client.get("/admin-api/ims/file/content_image/0/202610/missing.png", headers=auth)
    assert missing.status_code == 403
    assert missing.json()["code"] == 1504

    escaped = client.get("/admin-api/ims/file/content_image/%2e%2e/etc/passwd", headers=auth)
    assert escaped.json()["code"] == 1504

    from app.content_file import LocalStorageProvider

    try:
        LocalStorageProvider().path_for("content_image/../../etc/passwd")
        raise AssertionError("path escaped")
    except ValueError:
        pass

    db = SessionLocal()
    try:
        row = db.query(ImsFile).filter(ImsFile.file_key == key).one()
        row.deleted = 1
        db.commit()
    finally:
        db.close()
    gone = client.get(f"/admin-api/ims/file/{key}", headers=auth)
    assert gone.json()["code"] == 1504

    def boom(*_args, **_kwargs):
        raise OSError("disk")

    monkeypatch.setattr("app.content_file.storage.save", boom)
    failed = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("cover.png", PNG, "image/png")},
        data={"scene": "content_image"},
    )
    assert failed.json()["code"] == 5005

    monkeypatch.setattr("app.content_file.MAX_IMAGE_BYTES", 4)
    oversized = client.post(
        UPLOAD,
        headers=auth,
        files={"file": ("cover.png", PNG, "image/png")},
        data={"scene": "content_image"},
    )
    assert oversized.json()["code"] == 1500
    assert oversized.json()["msg"] == "文件过大"
