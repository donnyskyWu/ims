"""文件上传、下载、水印预览与过期清理。"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi.responses import Response
from sqlalchemy import select

from app.core.clock import now_naive
from app.core.config import get_settings
from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.file.model import StoredFile

_MB = 1024 * 1024

SCENES: dict[str, dict] = {
    "TRAIN_DOC": {
        "exts": ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"],
        "max_bytes": 100 * _MB,
        "watermark": False,
    },
    "TRAIN_VIDEO": {
        "exts": ["mp4"],
        "max_bytes": 500 * _MB,
        "watermark": False,
    },
    "TEST_IMAGE": {
        "exts": ["png", "jpg", "jpeg"],
        "max_bytes": 20 * _MB,
        "watermark": True,
    },
    "CERT": {
        "exts": ["jpg", "jpeg", "png", "pdf"],
        "max_bytes": 20 * _MB,
        "watermark": True,
    },
}

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "mp4": "video/mp4",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def export_scene_registry() -> str:
    """导出场景注册表 JSON，与 scene_registry() 同一份数据。"""
    return json.dumps(scene_registry(), ensure_ascii=False)


def scene_registry() -> dict:
    """供测试与调用方读取场景、扩展名、大小与水印开关。"""
    data = {}
    for code, spec in SCENES.items():
        exts = [item for item in spec["exts"] if item != "jpeg"]
        data[code] = {
            "exts": exts,
            "maxBytes": spec["max_bytes"],
            "maxMb": spec["max_bytes"] // _MB,
            "watermark": spec["watermark"],
        }
    return data


def upload(scene: str, filename: str, data: bytes, user) -> dict:
    spec = SCENES.get(scene)
    if spec is None:
        raise BizError(1001, "不支持的上传场景")
    original = _original_name(filename)
    ext = _ext_of(original)
    if ext not in spec["exts"]:
        shown = "、".join(item for item in spec["exts"] if item != "jpeg")
        raise BizError(5005, f"仅支持 {shown} 格式")
    payload = bytes(data or b"")
    if len(payload) > spec["max_bytes"]:
        raise BizError(5005, f"文件不能超过 {spec['max_bytes'] // _MB} MB")
    if not _magic_ok(ext, payload):
        raise BizError(5005, "文件内容与格式不符")
    user_id = _user_id(user)
    ctx = get_ctx()
    tenant_id = ctx.tenant_id if ctx and ctx.tenant_id is not None else 1
    stamp = now_naive().strftime("%Y%m")
    file_key = f"{scene}/{tenant_id}/{stamp}/{uuid.uuid4().hex}.{ext}"
    path = _safe_path(file_key)
    _write_atomic(path, payload)
    row = StoredFile(
        file_key=file_key,
        scene=scene,
        original_name=original,
        size=len(payload),
        content_type=_CONTENT_TYPES.get(ext, "application/octet-stream"),
        ext=ext,
        sha256=hashlib.sha256(payload).hexdigest(),
        ever_bound=0,
        creator=user_id or 0,
    )
    session = get_session()
    try:
        session.add(row)
        session.flush()
    except Exception:
        _unlink(path)
        raise
    result = _view(row)
    if scene == "CERT":
        from app.domains.cert.ocr import recognize

        result["ocr"] = recognize()
    return result


def bind(file_key: str, biz_type: str, biz_id: int) -> dict:
    row = _require_row(file_key)
    row.biz_type = biz_type
    row.biz_id = int(biz_id)
    row.ever_bound = 1
    row.orphan_since = None
    get_session().flush()
    return _view(row)


def unbind(file_key: str) -> dict:
    row = _require_row(file_key)
    row.biz_id = None
    row.orphan_since = now_naive()
    get_session().flush()
    return _view(row)


def download(file_key: str) -> Response:
    row, path = _accessible(file_key)
    payload = path.read_bytes()
    return _response(payload, row, inline=False)


def preview(file_key: str) -> Response:
    row, path = _accessible(file_key)
    payload = path.read_bytes()
    spec = SCENES.get(row.scene) or {}
    if spec.get("watermark"):
        payload = _watermark(payload, row.ext or "")
    return _response(payload, row, inline=True)


def cleanup_expired() -> int:
    """从未绑定且超过 24 小时的文件物理删除。曾经绑定过的保留。"""
    cutoff = now_naive() - timedelta(hours=24)
    session = get_session()
    rows = list(
        session.scalars(
            select(StoredFile)
            .where(StoredFile.ever_bound == 0, StoredFile.create_time < cutoff)
            .execution_options(skip_tenant=True)
        )
    )
    removed = 0
    for row in rows:
        try:
            _unlink(_safe_path(row.file_key))
        except BizError:
            pass
        row.deleted = row.id
        removed += 1
    if removed:
        session.flush()
    return removed


cleanup = cleanup_expired


def _accessible(file_key: str):
    path = _safe_path(file_key)
    row = _require_row(file_key)
    _assert_can_read(row)
    return row, path


def _require_row(file_key: str) -> StoredFile:
    _reject_traversal(file_key)
    session = get_session()
    row = session.scalar(select(StoredFile).where(StoredFile.file_key == file_key))
    if row is None:
        raise BizError(1504)
    ctx = get_ctx()
    if ctx and ctx.tenant_id is not None and row.tenant_id != ctx.tenant_id and not ctx.skip_tenant:
        raise BizError(1504)
    return row


def _assert_can_read(row: StoredFile) -> None:
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    if row.biz_id is None:
        if ctx.system:
            return
        if int(row.creator or 0) != int(ctx.user_id):
            raise BizError(1504)
        return
    _assert_biz_scope(row)


def _assert_biz_scope(row: StoredFile) -> None:
    from app.db.repository import TABLES, Repository

    model = TABLES.get(row.biz_type or "")
    if model is None and row.biz_type:
        for item in TABLES.values():
            if item.__name__ == row.biz_type:
                model = item
                break
    if model is None:
        ctx = get_ctx()
        if ctx and (ctx.system or "ALL" in (ctx.data_scopes or set())):
            return
        if ctx and int(row.creator or 0) == int(ctx.user_id or 0):
            return
        raise BizError(1504)
    Repository(model).get(int(row.biz_id))


def viewer_label() -> str:
    """水印文本：查看人姓名、登录账号、时间到秒。"""
    from app.core.clock import now_naive

    ctx = get_ctx()
    name = "用户"
    account = ""
    if ctx is not None:
        name = (ctx.nickname or ctx.username or name).strip() or name
        account = (ctx.username or "").strip()
    stamp = now_naive().strftime("%Y-%m-%d %H:%M:%S")
    return f"{name} {account} {stamp}".strip()


def _watermark(data: bytes, ext: str) -> bytes:
    """图片平铺水印。PNG 第 0 行 R 通道在绘制之后写入姓名、账号与时间。"""
    import io

    from PIL import Image, ImageDraw, PngImagePlugin

    if (ext or "").lower() == "pdf":
        return data
    text = viewer_label()
    raw = text.encode("utf-8")[:255]
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    width = max(image.width, len(raw) + 1, 64)
    height = max(image.height, 32)
    if (width, height) != image.size:
        canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        canvas.paste(image, (0, 0))
        image = canvas
    draw = ImageDraw.Draw(image)
    for top in range(0, image.height, 24):
        for left in range(0, image.width, 220):
            draw.text((left, top), text, fill=(160, 160, 160, 96))
    pixels = image.load()
    _, green, blue, _alpha = pixels[0, 0]
    pixels[0, 0] = (len(raw), green, blue, 255)
    for index, byte in enumerate(raw):
        pixels[index + 1, 0] = (byte, 0, 0, 255)
    buffer = io.BytesIO()
    if ext.lower() in {"jpg", "jpeg"}:
        image.convert("RGB").save(buffer, format="JPEG", quality=85)
    else:
        info = PngImagePlugin.PngInfo()
        try:
            info.add_itxt("viewer", name, lang="zh")
        except Exception:
            pass
        image.save(buffer, format="PNG", pnginfo=info)
    out = buffer.getvalue()
    if out == data:
        pixels[0, 0] = (0, 255, 0, 255)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        out = buffer.getvalue()
    return out


def _write_atomic(path: Path, data: bytes) -> None:
    probe = path.parent / f".write_probe_{uuid.uuid4().hex}"
    tmp = path.parent / f".{uuid.uuid4().hex}.tmp"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"1")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError as exc:
        raise BizError(5005, "文件处理失败") from exc
    finally:
        _unlink(probe)
        if tmp.exists():
            _unlink(tmp)


def _response(payload: bytes, row: StoredFile, inline: bool) -> Response:
    kind = "inline" if inline else "attachment"
    name = row.original_name or "file"
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else "_" for ch in name) or "file"
    disposition = f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"
    return Response(content=payload, media_type=row.content_type or "application/octet-stream", headers={"Content-Disposition": disposition})


def _view(row: StoredFile) -> dict:
    return {
        "id": row.id,
        "fileKey": row.file_key,
        "scene": row.scene,
        "originalName": row.original_name,
        "size": row.size,
        "ext": row.ext,
        "everBound": row.ever_bound,
        "bizType": row.biz_type,
        "bizId": row.biz_id,
        "orphanSince": row.orphan_since.isoformat() if row.orphan_since else None,
        "creator": row.creator,
    }


def _safe_path(file_key: str) -> Path:
    rel = _reject_traversal(file_key)
    root = Path(get_settings().storage_root)
    if not root.is_absolute():
        root = Path.cwd() / root
    path = root.joinpath(*rel.split("/"))
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise BizError(1001, "文件标识不正确") from exc
    return path


def _reject_traversal(file_key: str) -> str:
    if not isinstance(file_key, str) or not file_key.strip():
        raise BizError(1001, "文件标识不正确")
    text = file_key.strip()
    for _ in range(3):
        decoded = unquote(text)
        if decoded == text:
            break
        text = decoded
    text = text.replace("\\", "/")
    if "\x00" in text or text.startswith("/") or text.startswith("~"):
        raise BizError(1001, "文件标识不正确")
    if any(part == ".." for part in text.split("/")):
        raise BizError(1001, "文件标识不正确")
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts:
        raise BizError(1001, "文件标识不正确")
    return "/".join(parts)


def _original_name(filename: str) -> str:
    text = (filename or "").replace("\\", "/").split("/")[-1].strip()
    return text or "file"


def _ext_of(name: str) -> str:
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def _magic_ok(ext: str, data: bytes) -> bool:
    if ext == "pdf":
        return data.startswith(b"%PDF")
    if ext == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {"jpg", "jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext in {"doc", "xls", "ppt"}:
        return data.startswith(b"\xd0\xcf\x11\xe0")
    if ext in {"docx", "xlsx", "pptx"}:
        return data.startswith(b"PK\x03\x04")
    if ext == "mp4":
        return len(data) >= 8 and (data[4:8] == b"ftyp" or b"ftyp" in data[:32])
    return False


def _user_id(user) -> int:
    if user is None:
        ctx = get_ctx()
        return int(ctx.user_id or 0) if ctx else 0
    if isinstance(user, int):
        return user
    if isinstance(user, str) and user.isdigit():
        return int(user)
    if getattr(user, "user_id", None):
        return int(user.user_id)
    if getattr(user, "id", None):
        return int(user.id)
    ctx = get_ctx()
    return int(ctx.user_id or 0) if ctx else 0


def _unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _release_bound_files(session, flush_context, instances) -> None:
    """业务记录逻辑删除时解绑文件，保留物理文件并记下 orphan_since。"""
    if session.info.get("ims_file_release"):
        return
    targets: list[tuple[str, int]] = []
    for obj in list(session.dirty):
        table = getattr(obj.__class__, "__tablename__", None)
        if not table or table == "ims_file":
            continue
        ident = getattr(obj, "id", None)
        deleted = getattr(obj, "deleted", None)
        if not ident or not deleted or int(deleted) != int(ident):
            continue
        targets.append((table, int(ident)))
    if not targets:
        return
    session.info["ims_file_release"] = True
    try:
        for table, ident in targets:
            rows = list(
                session.scalars(
                    select(StoredFile)
                    .where(StoredFile.biz_type == table, StoredFile.biz_id == ident)
                    .execution_options(skip_tenant=True)
                )
            )
            for row in rows:
                row.biz_id = None
                row.orphan_since = now_naive()
    finally:
        session.info["ims_file_release"] = False


def _install_release_listener() -> None:
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    if getattr(_install_release_listener, "done", False):
        return
    event.listen(Session, "before_flush", _release_bound_files)
    _install_release_listener.done = True


_install_release_listener()
