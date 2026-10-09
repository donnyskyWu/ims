"""CONTENT #18 · POST /content/file/upload（任务执行附件落盘）。

落盘根目录 `IMS_FILE_ROOT`（缺省 `ims-backend/data/ims-files`，对应 `ims.file.storage.root`）。
`fileKey` 为相对路径 `{scene}/{tenantId}/{yyyyMM}/{uuid}.{ext}`。
大小沿用平台 `maxBodyBytes`（20MiB），不在内容契约另写上限。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.api import current_user, fail, ok
from app.content import tenant
from app.models import User

upload_router = APIRouter(prefix="/content/file", tags=["content-file"])
download_router = APIRouter(prefix="/file", tags=["content-file"])

BJ = timezone(timedelta(hours=8))
# 设计稿 §8 `maxBodyBytes`；与 FileUpload 平台上限一致。
MAX_BYTES = 20 * 1024 * 1024
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


def storage_root() -> Path:
    configured = (os.environ.get("IMS_FILE_ROOT") or "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "ims-files"


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
    root = storage_root().resolve()
    path = (root / scene / tid / yyyymm / name).resolve()
    if not path.is_relative_to(root):
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
    raw = file.file.read(MAX_BYTES + 1)
    if not raw:
        return fail(1500, "文件为空")
    if len(raw) > MAX_BYTES:
        return fail(1500, "文件超过大小限制")
    tenant_id = tenant(actor)
    yyyymm = datetime.now(BJ).strftime("%Y%m")
    folder = storage_root() / chosen / str(tenant_id) / yyyymm
    dest = folder / f"{uuid.uuid4().hex}.{ext}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    except OSError:
        return fail(5005, "文件上传失败，请重试")
    file_key = f"{chosen}/{tenant_id}/{yyyymm}/{dest.name}"
    return ok(
        {
            "fileKey": file_key,
            "fileUrl": file_url(file_key),
            "fileName": name,
            "sizeBytes": len(raw),
        }
    )


@download_router.get("/{file_key:path}")
def download_content_file(file_key: str, actor: User = Depends(current_user)):
    path = resolve_stored(file_key, tenant(actor))
    if path is None or not path.is_file():
        return fail(1504, "资源不可用")
    ext = extension_of(path.name)
    return FileResponse(path, media_type=MEDIA.get(ext, "application/octet-stream"), filename=path.name)
