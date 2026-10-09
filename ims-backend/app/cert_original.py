"""证件原件上传桩。

POST /cert/archive/original：原件落服务端目录，回执 fileKey，并给出 OCR 桩结果。
识别成功为 PENDING_CONFIRM，供人工确认；识别不了为 FAILED，不阻断后续录入。
绑定档案时按 certId 递增版本，旧文件保留（V1-D2）。
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import tenant_of, visible
from app.models import CertArchive, CertOriginalFile, User

router = APIRouter()

MAX_BYTES = 20 * 1024 * 1024
OCR_KEYS = ("holderName", "certNo", "expireDate", "issueDate")
ALLOWED_EXT = {".txt", ".pdf", ".png", ".jpg", ".jpeg"}


class ConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fileKey: str
    action: str
    recognizedFields: dict | None = None


class BindBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fileKey: str
    certId: int


class VersionsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    certId: int


def file_root() -> Path:
    configured = (os.environ.get("IMS_FILE_ROOT") or "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "ims-files"


def stored_path(file_key: str) -> Path | None:
    key = (file_key or "").strip().replace("\\", "/")
    if not key or key.startswith("/") or ".." in key.split("/"):
        return None
    root = file_root().resolve()
    path = (root / key).resolve()
    if path != root and root not in path.parents:
        return None
    return path


def parse_stub(data: bytes) -> tuple[str, dict]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "FAILED", {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        name = key.strip()
        cleaned = value.strip()[:64]
        if name in OCR_KEYS and cleaned:
            fields[name] = cleaned
    if fields.get("holderName") or fields.get("certNo"):
        return "PENDING_CONFIRM", fields
    return "FAILED", {}


def load_fields(raw: str) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def clean_fields(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {}
    fields: dict[str, str] = {}
    for key in OCR_KEYS:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()[:64]
        if text:
            fields[key] = text
    return fields


def original_vo(row: CertOriginalFile) -> dict:
    fields = load_fields(row.ocr_fields)
    return {
        "id": row.id,
        "certId": row.cert_id or None,
        "version": row.version,
        "fileKey": row.file_key,
        "fileName": row.file_name,
        "fileSize": row.file_size,
        "sha256": row.sha256,
        "contentType": row.content_type,
        "ocrResult": {
            "recognizeStatus": row.ocr_status,
            "recognizedFields": fields,
        },
        "createdAt": row.created_at.strftime("%Y-%m-%dT%H:%M:%S") if row.created_at else "",
    }


def find_original(db: Session, actor: User, file_key: str) -> CertOriginalFile | None:
    key = (file_key or "").strip()
    if not key:
        return None
    return db.scalar(
        select(CertOriginalFile).where(
            CertOriginalFile.deleted == 0,
            CertOriginalFile.tenant_id == tenant_of(actor),
            CertOriginalFile.file_key == key,
        )
    )


def suffix_of(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_EXT:
        return ext
    return ".bin"


@router.post("/cert/archive/original")
def upload_original(
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """原件落盘并返回 OCR 桩。空文件 1001，落盘失败 5005。"""
    try:
        data = file.file.read()
    except OSError:
        return fail(5005, "原件落盘失败")
    if not data:
        return fail(1001, "原件不能为空")
    if len(data) > MAX_BYTES:
        return fail(1001, "原件不能超过 20MB")
    status, fields = parse_stub(data)
    tenant = tenant_of(actor)
    stamp = datetime.now().strftime("%Y%m")
    file_key = f"cert/{tenant}/{stamp}/{uuid.uuid4().hex}{suffix_of(file.filename or '')}"
    path = stored_path(file_key)
    if path is None:
        return fail(5005, "原件落盘失败")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError:
        return fail(5005, "原件落盘失败")
    row = CertOriginalFile(
        cert_id=0,
        version=0,
        file_key=file_key,
        file_name=(file.filename or "original")[:256],
        file_size=len(data),
        content_type=(file.content_type or "")[:128],
        sha256=hashlib.sha256(data).hexdigest(),
        ocr_status=status,
        ocr_fields=json.dumps(fields, ensure_ascii=False),
        creator=actor.id,
        updater=actor.id,
        tenant_id=tenant,
    )
    db.add(row)
    db.flush()
    return ok(original_vo(row))


@router.post("/cert/archive/original/confirm")
def confirm_original(
    body: ConfirmBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """人工确认 OCR 桩结果。识别失败也可以改字段后确认。"""
    action = (body.action or "").strip().upper()
    if action != "CONFIRM":
        return fail(1001, "动作不合法")
    row = find_original(db, actor, body.fileKey)
    if row is None:
        return fail(1504, "原件不存在")
    edited = clean_fields(body.recognizedFields)
    if edited:
        row.ocr_fields = json.dumps(edited, ensure_ascii=False)
    elif row.ocr_status == "FAILED" and not load_fields(row.ocr_fields):
        return fail(1001, "未识别到字段，请填写后确认")
    row.ocr_status = "CONFIRMED"
    row.updater = actor.id
    row.updated_at = utcnow()
    return ok(original_vo(row))


@router.post("/cert/archive/original/bind")
def bind_original(
    body: BindBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """把原件挂到档案并分配下一个版本。已有版本的文件留在磁盘上。"""
    row = find_original(db, actor, body.fileKey)
    if row is None:
        return fail(1504, "原件不存在")
    cert = db.get(CertArchive, body.certId)
    if not visible(cert, actor):
        return fail(1504, "资源不可用")
    if row.cert_id and row.cert_id != cert.id:
        return fail(1001, "原件已绑定其他档案")
    if row.cert_id == cert.id and row.version:
        return ok(original_vo(row))
    current = db.scalar(
        select(func.max(CertOriginalFile.version)).where(
            CertOriginalFile.deleted == 0,
            CertOriginalFile.tenant_id == tenant_of(actor),
            CertOriginalFile.cert_id == cert.id,
        )
    )
    row.cert_id = cert.id
    row.version = int(current or 0) + 1
    row.updater = actor.id
    row.updated_at = utcnow()
    return ok(original_vo(row))


@router.post("/cert/archive/original/versions")
def original_versions(
    body: VersionsBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    cert = db.get(CertArchive, body.certId)
    if not visible(cert, actor):
        return fail(1504, "资源不可用")
    rows = db.scalars(
        select(CertOriginalFile)
        .where(
            CertOriginalFile.deleted == 0,
            CertOriginalFile.tenant_id == tenant_of(actor),
            CertOriginalFile.cert_id == cert.id,
        )
        .order_by(CertOriginalFile.version.asc(), CertOriginalFile.id.asc())
    ).all()
    return ok({"certId": cert.id, "versions": [original_vo(row) for row in rows]})
