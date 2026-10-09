import base64
import os
import tempfile

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_FILE_ROOT"] = tempfile.mkdtemp(prefix="ims-files-")

from pathlib import Path

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import ImsFile

client = TestClient(app)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
UPLOAD = "/admin-api/ims/content/file/upload"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


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
