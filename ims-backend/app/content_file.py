"""内容域通用上传。契约 POST /admin-api/ims/content/file/upload。

落盘根目录 IMS_FILE_ROOT（缺省 ims-backend/data/ims-files），按
{scene}/{tenantId}/{yyyyMM}/{uuid}.{ext} 归档。DB 只存相对 fileKey。
读链 GET /admin-api/ims/file/{fileKey}。本期不上对象存储。
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.models import ImsFile, User

router = APIRouter(prefix="/content", tags=["content-file"])
file_read_router = APIRouter(prefix="/file", tags=["ims-file"])

SCENES = frozenset({"task_execute_attachment", "content_image", "deliverable"})
DEFAULT_SCENE = "task_execute_attachment"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024

IMAGE_EXT = {
    "image/png": frozenset({".png"}),
    "image/jpeg": frozenset({".jpg", ".jpeg"}),
    "image/gif": frozenset({".gif"}),
    "image/webp": frozenset({".webp"}),
}
GENERAL_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".zip": "application/zip",
    ".mp4": "video/mp4",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class LocalStorageProvider:
    def root(self) -> Path:
        configured = (os.environ.get("IMS_FILE_ROOT") or "").strip()
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parents[1] / "data" / "ims-files"

    def path_for(self, file_key: str) -> Path:
        if not file_key or file_key.startswith(("/", "\\")) or ".." in file_key.split("/"):
            raise ValueError("escape")
        root = self.root().resolve()
        candidate = (root / file_key).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("escape")
        return candidate

    def save(self, scene: str, tenant_id: int, ext: str, data: bytes) -> str:
        month = datetime.now(timezone.utc).strftime("%Y%m")
        file_key = f"{scene}/{tenant_id}/{month}/{uuid.uuid4().hex}{ext}"
        path = self.path_for(file_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return file_key


storage = LocalStorageProvider()


def sniff_image(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def safe_filename(raw: str | None) -> str:
    name = Path(raw or "").name.replace("\x00", "").strip()
    if not name or name in {".", ".."}:
        return ""
    return name[:200]


def disposition(name: str) -> str:
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 and ch not in {'"', "\\"} else "_" for ch in name) or "file"
    return f'inline; filename="{ascii_name}"'


def file_url(file_key: str) -> str:
    return "/admin-api/ims/file/" + quote(file_key, safe="/")


@router.post("/file/upload")
def content_file_upload(
    file: UploadFile | None = File(default=None),
    scene: str = Form(default=DEFAULT_SCENE),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    scene_name = (scene or "").strip() or DEFAULT_SCENE
    if scene_name not in SCENES:
        return fail(1500, "scene 无效")
    if file is None:
        return fail(1500, "请上传文件")
    filename = safe_filename(file.filename)
    ext = Path(filename).suffix.lower() if filename else ""
    if not filename or ext not in GENERAL_EXT:
        return fail(1500, "文件类型不支持")
    limit = MAX_IMAGE_BYTES if scene_name == "content_image" else MAX_FILE_BYTES
    raw = file.file.read(limit + 1)
    if not raw:
        return fail(1500, "文件为空")
    if len(raw) > limit:
        return fail(1500, "文件过大")
    if scene_name == "content_image":
        mime = sniff_image(raw)
        if mime is None or ext not in IMAGE_EXT.get(mime, frozenset()):
            return fail(1500, "content_image 仅支持图片")
        content_type = mime
    else:
        content_type = GENERAL_EXT[ext]
    tenant_id = actor.tenant_id or 0
    try:
        file_key = storage.save(scene_name, tenant_id, ext, raw)
    except OSError:
        return fail(5005, "文件上传失败")
    row = ImsFile(
        file_name=filename,
        file_key=file_key,
        file_size=len(raw),
        content_type=content_type,
        scene=scene_name,
        sha256=hashlib.sha256(raw).hexdigest(),
        creator=actor.id,
        deleted=0,
        tenant_id=tenant_id,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return ok(
        {
            "fileKey": file_key,
            "fileUrl": file_url(file_key),
            "fileName": filename,
            "sizeBytes": len(raw),
        }
    )


@file_read_router.get("/{file_key:path}")
def content_file_read(
    file_key: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    key = (file_key or "").strip()
    if not key or ".." in key.split("/") or "\\" in key or key.startswith("/"):
        return fail(1504, "资源不可用")
    row = db.scalar(
        select(ImsFile).where(
            ImsFile.file_key == key,
            ImsFile.deleted == 0,
            ImsFile.tenant_id == (actor.tenant_id or 0),
        )
    )
    if row is None:
        return fail(1504, "资源不可用")
    try:
        path = storage.path_for(key)
    except ValueError:
        return fail(1504, "资源不可用")
    if not path.is_file():
        return fail(1504, "资源不可用")
    try:
        data = path.read_bytes()
    except OSError:
        return fail(5005, "文件读取失败")
    return Response(content=data, media_type=row.content_type or "application/octet-stream", headers={"Content-Disposition": disposition(row.file_name)})
