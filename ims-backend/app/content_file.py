"""内容域文件。POST /content/file/upload，GET /file/{fileKey}。

落盘根目录 `IMS_FILE_ROOT`（缺省 `ims-backend/data/ims-files`）。
`fileKey` 为相对路径 `{scene}/{tenantId}/{yyyyMM}/{uuid}.{ext}`。DB 只存相对 fileKey。
任务附件与 content_image / deliverable 共用这一条上传链路。
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import tenant
from app.core import utcnow
from app.models import ImsFile, User

upload_router = APIRouter(prefix="/content/file", tags=["content-file"])
download_router = APIRouter(prefix="/file", tags=["content-file"])

BJ = timezone(timedelta(hours=8))
MAX_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_NAME = 200

SCENES: dict[str, frozenset[str]] = {
    "task_execute_attachment": frozenset(
        {"pdf", "png", "jpg", "jpeg", "gif", "webp", "txt", "doc", "docx", "xls", "xlsx", "csv"}
    ),
    "content_image": frozenset({"png", "jpg", "jpeg", "gif", "webp"}),
    "deliverable": frozenset(
        {"pdf", "png", "jpg", "jpeg", "gif", "webp", "txt", "doc", "docx", "xls", "xlsx", "mp4"}
    ),
}

MEDIA = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "txt": "text/plain; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "mp4": "video/mp4",
}

IMAGE_EXT = {
    "image/png": frozenset({".png"}),
    "image/jpeg": frozenset({".jpg", ".jpeg"}),
    "image/gif": frozenset({".gif"}),
    "image/webp": frozenset({".webp"}),
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
        suffix = ext if ext.startswith(".") else f".{ext}"
        month = datetime.now(BJ).strftime("%Y%m")
        file_key = f"{scene}/{tenant_id}/{month}/{uuid.uuid4().hex}{suffix}"
        path = self.path_for(file_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return file_key


storage = LocalStorageProvider()


def storage_root() -> Path:
    return storage.root()


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


def display_name(filename: str | None) -> str:
    name = Path(filename or "").name.replace("\x00", "").strip()
    if not name or name in {".", ".."}:
        return ""
    return name[:MAX_NAME]


def extension_of(filename: str) -> str:
    base = Path(filename).name
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def file_url(file_key: str) -> str:
    return f"/admin-api/ims/file/{file_key}"


def resolve_stored(file_key: str, tenant_id: int) -> Path | None:
    if not file_key or "\\" in file_key or file_key.startswith("/") or ".." in file_key.split("/"):
        return None
    parts = file_key.split("/")
    if len(parts) != 4:
        return None
    scene, tid, yyyymm, name = parts
    allowed = SCENES.get(scene)
    if allowed is None or tid != str(tenant_id) or len(yyyymm) != 6 or not yyyymm.isdigit():
        return None
    ext = extension_of(name)
    if ext not in allowed or not name.endswith(f".{ext}"):
        return None
    stem = name[: -(len(ext) + 1)]
    if len(stem) != 32 or any(ch not in "0123456789abcdef" for ch in stem):
        return None
    try:
        path = storage.path_for(file_key)
    except ValueError:
        return None
    return path


def public_attachment(item: dict) -> dict:
    key = str(item.get("fileKey") or "")
    name = str(item.get("fileName") or "")
    return {"fileKey": key, "fileName": name, "fileUrl": file_url(key) if key else ""}


def normalize_user_attachments(items: list, tenant_id: int) -> tuple[list[dict] | None, str | None]:
    if not isinstance(items, list):
        return None, "附件无效"
    normalized: list[dict] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            return None, "附件无效"
        key = str(item.get("fileKey") or "").strip()
        name = display_name(str(item.get("fileName") or ""))
        if not key or not name:
            return None, "附件无效"
        path = resolve_stored(key, tenant_id)
        if path is None or not path.is_file():
            return None, "附件文件不存在"
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"fileKey": key, "fileName": name})
    return normalized, None


@upload_router.post("/upload")
def upload_content_file(
    file: UploadFile | None = File(default=None),
    scene: str = Form(default="task_execute_attachment"),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    chosen = (scene or "").strip() or "task_execute_attachment"
    if chosen not in SCENES:
        return fail(1500, "scene 无效")
    if file is None:
        return fail(1500, "请选择文件")
    name = display_name(file.filename)
    ext = extension_of(name)
    if not name or ext not in SCENES[chosen]:
        return fail(1500, "不支持的文件类型")
    limit = MAX_IMAGE_BYTES if chosen == "content_image" else MAX_BYTES
    raw = file.file.read(limit + 1)
    if not raw:
        return fail(1500, "文件为空")
    if len(raw) > limit:
        return fail(1500, "文件过大" if chosen == "content_image" else "文件超过大小限制")
    if chosen == "content_image":
        mime = sniff_image(raw)
        if mime is None or f".{ext}" not in IMAGE_EXT.get(mime, frozenset()):
            return fail(1500, "content_image 仅支持图片")
        content_type = mime
    else:
        content_type = MEDIA.get(ext, "application/octet-stream")
    tenant_id = tenant(actor)
    try:
        file_key = storage.save(chosen, tenant_id, ext, raw)
    except OSError:
        return fail(5005, "文件上传失败，请重试")
    db.add(
        ImsFile(
            file_name=name,
            file_key=file_key,
            file_size=len(raw),
            content_type=content_type,
            scene=chosen,
            sha256=hashlib.sha256(raw).hexdigest(),
            creator=actor.id,
            deleted=0,
            tenant_id=tenant_id,
            created_at=utcnow(),
        )
    )
    db.flush()
    return ok(
        {
            "fileKey": file_key,
            "fileUrl": file_url(file_key),
            "fileName": name,
            "sizeBytes": len(raw),
        }
    )


@download_router.get("/{file_key:path}")
def download_content_file(
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
            ImsFile.tenant_id == tenant(actor),
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
    return Response(content=data, media_type=row.content_type or "application/octet-stream")
