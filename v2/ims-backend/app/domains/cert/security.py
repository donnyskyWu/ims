"""证件分级、水印查看与审计。高频查看只告警，不拦截。"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.clock import format_datetime, now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.redis_client import get_redis
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.cert.model import CertLevelConfig, CertViewLog
from app.domains.cert.support import holder, ident_of, load_cert, masked_no, parse_day, view_level, watermark_text
from app.domains.master.model import Cert
from app.domains.resource.common import audit_sensitive, has_perm, one, text_of, user_ids_with_perm
from app.services.exchange import remember_export

_POSITIONS = {
    "TOP_LEFT",
    "TOP_CENTER",
    "TOP_RIGHT",
    "MIDDLE_LEFT",
    "CENTER",
    "MIDDLE_RIGHT",
    "BOTTOM_LEFT",
    "BOTTOM_CENTER",
    "BOTTOM_RIGHT",
}
_TOKEN_TTL = 60


def _config() -> CertLevelConfig:
    session = get_session()
    row = session.scalar(select(CertLevelConfig).order_by(CertLevelConfig.id.asc()))
    if row is None:
        row = CertLevelConfig(l2_role_ids=[], l3_user_ids=[], opacity=Decimal("0.12"), position="BOTTOM_RIGHT", version=1)
        session.add(row)
        session.flush()
    return row


def _config_view(row: CertLevelConfig) -> dict:
    return {
        "id": row.id,
        "l2RoleIds": [int(item) for item in (row.l2_role_ids or [])],
        "l3UserIds": [int(item) for item in (row.l3_user_ids or [])],
        "opacity": f"{Decimal(row.opacity):.2f}",
        "position": row.position,
        "version": row.version,
        "hint": "下次查看即按新级别",
    }


def get_config() -> dict:
    return _config_view(_config())


def save_config(body: dict) -> dict:
    row = _config()
    expected = body.get("version")
    if expected in (None, ""):
        one("version", "请刷新后重试")
    if int(expected) != int(row.version):
        raise BizError(1001, "配置已被他人修改，请刷新后重试")
    roles = body.get("l2RoleIds") or []
    if not isinstance(roles, list) or len(roles) < 1:
        one("l2RoleIds", "请至少选择一个可查看原件的角色")
    role_ids = [ident_of(item) for item in roles]
    _roles_exist(role_ids)
    users = body.get("l3UserIds") or []
    if users is None:
        users = []
    if not isinstance(users, list):
        one("l3UserIds", "白名单格式不正确")
    user_ids = [ident_of(item) for item in users]
    _users_active(user_ids)
    try:
        opacity = Decimal(str(body.get("opacity") if body.get("opacity") not in (None, "") else "0.12"))
    except Exception:
        one("opacity", "透明度格式不正确")
    if opacity < Decimal("0.05") or opacity > Decimal("0.30"):
        one("opacity", "透明度范围为 0.05～0.3")
    position = text_of(body, "position") or "BOTTOM_RIGHT"
    if position not in _POSITIONS:
        one("position", "请选择水印位置")
    row.l2_role_ids = role_ids
    row.l3_user_ids = user_ids
    row.opacity = opacity
    row.position = position
    row.version = int(row.version) + 1
    get_session().flush()
    data = _config_view(row)
    data["hint"] = "下次查看即按新级别"
    return data


def _roles_exist(ids: list[int]) -> None:
    from app.domains.system.model import Role

    session = get_session()
    for ident in ids:
        role = session.get(Role, ident)
        if role is None or role.deleted or role.status != "ENABLED":
            raise BizError(1500, "关联的角色不存在")


def _users_active(ids: list[int]) -> None:
    from app.domains.system.model import User

    session = get_session()
    for ident in ids:
        user = session.get(User, ident)
        if user is None or user.deleted:
            raise BizError(1500, "关联的用户不存在")
        if user.status != "ACTIVE":
            raise BizError(1501, "关联的用户已停用，不可选择")


def open_view(cert_id: int, params: dict) -> dict:
    if text_of(params, "logId") and text_of(params, "durationSec"):
        return _duration(ident_of(params.get("logId")), int(params.get("durationSec") or 0))
    cert = load_cert(cert_id)
    scene = text_of(params, "scene")
    level = view_level(cert)
    if cert.status == "PENDING_REVIEW" and scene != "review":
        raise BizError(1033)
    if scene == "review":
        if not has_perm("ims:cert:archive:review"):
            raise BizError(1008)
        if level == "L1":
            level = "L2"
    if level == "L1":
        raise BizError(1034)
    text = "" if level == "L3" else watermark_text()
    log = _write_log(cert, level, text)
    _risk(log)
    token = _issue(cert.id, level)
    return {
        "certId": cert.id,
        "viewLevel": level,
        "watermarkText": text,
        "logId": log.id,
        "token": token,
        "expiresIn": _TOKEN_TTL,
        "fileUrl": f"/admin-api/ims/cert/archive/{cert.id}/file-url?token={token}",
        "autoCloseSec": 300,
    }


def _duration(log_id: int, seconds: int) -> dict:
    ctx = get_ctx()
    row = get_session().get(CertViewLog, int(log_id))
    if row is None or (ctx and row.viewer_id != ctx.user_id):
        raise BizError(1001, "查看记录不存在")
    if seconds < 0 or seconds > 86400:
        one("durationSec", "时长不正确")
    row.duration_sec = int(seconds)
    get_session().flush()
    return {"updated": True, "logId": row.id, "durationSec": row.duration_sec}


def _write_log(cert: Cert, level: str, text: str) -> CertViewLog:
    ctx = get_ctx()
    person = holder(cert.realname_id)
    label = f"{person['holderName']}·{cert.cert_type or ''}·{masked_no(cert)}"
    row = CertViewLog(
        cert_id=cert.id,
        viewer_id=ctx.user_id if ctx else None,
        viewer_name=(ctx.nickname or ctx.username) if ctx else "",
        view_level=level,
        watermark_text=text,
        duration_sec=0,
        ip=ctx.client_ip if ctx else "",
        device=_device(),
        risk_flag=0,
        holder_label=label,
    )
    get_session().add(row)
    get_session().flush()
    audit_sensitive("CERT", cert.id, "file")
    return row


def _device() -> str:
    from app.api.runtime import current_request

    request = current_request()
    if request is None:
        return ""
    return (request.headers.get("user-agent") or "")[:255]


def _risk(row: CertViewLog) -> None:
    if not row.viewer_id:
        return
    since = now_naive() - timedelta(hours=1)
    count = len(
        list(
            get_session().scalars(
                select(CertViewLog.id).where(CertViewLog.viewer_id == row.viewer_id, CertViewLog.create_time >= since)
            )
        )
    )
    if count <= 10:
        return
    row.risk_flag = 1
    get_session().flush()
    hour = now_naive().strftime("%Y%m%d%H")
    biz_key = f"cert-risk:{row.viewer_id}:{hour}"
    from app.domains.message.model import NotifyRecord

    if get_session().scalar(select(NotifyRecord.id).where(NotifyRecord.biz_key == biz_key)):
        return
    from app.domains.cert.notify import deliver

    deliver(
        user_ids_with_perm("ims:cert:security:log"),
        "notify.cert.remind",
        "cert_risk",
        biz_key,
        "/ims/corp/resource/certificate?tab=security",
        {"SITE"},
        title="证件查看异常",
        content=f"{row.viewer_name or '用户'} 1 小时内查看证件超过 10 次，请关注。",
    )


def _issue(cert_id: int, level: str) -> str:
    import uuid

    token = uuid.uuid4().hex
    ctx = get_ctx()
    uid = ctx.user_id if ctx else 0
    get_redis().set(f"ims:cert:file:{token}", f"{cert_id}:{level}:{uid}", ex=_TOKEN_TTL)
    return token


def file_url(cert_id: int, params: dict):
    token = text_of(params, "token")
    if token:
        return _stream(cert_id, token)
    cert = load_cert(cert_id)
    scene = text_of(params, "scene")
    level = view_level(cert)
    if cert.status == "PENDING_REVIEW" and scene != "review":
        raise BizError(1033)
    if scene == "review" and has_perm("ims:cert:archive:review") and level == "L1":
        level = "L2"
    if level == "L1":
        raise BizError(1034)
    issued = _issue(cert.id, level)
    return {
        "token": issued,
        "expiresIn": _TOKEN_TTL,
        "url": f"/admin-api/ims/cert/archive/{cert.id}/file-url?token={issued}",
    }


def _stream(cert_id: int, token: str):
    from fastapi.responses import Response

    from app.domains.file.service import _safe_path, _watermark

    raw = get_redis().get(f"ims:cert:file:{token}")
    if isinstance(raw, bytes):
        raw = raw.decode()
    if not raw:
        raise BizError(1001, "链接已过期，请重新打开")
    cert_text, level, _uid = str(raw).split(":")
    if int(cert_text) != int(cert_id):
        raise BizError(1001, "链接已过期，请重新打开")
    cert = load_cert(cert_id)
    if not cert.file_key:
        raise BizError(1504)
    from app.domains.file.model import StoredFile

    stored = get_session().scalar(select(StoredFile).where(StoredFile.file_key == cert.file_key))
    if stored is None:
        raise BizError(1504)
    payload = _safe_path(cert.file_key).read_bytes()
    ext = stored.ext or ""
    if level != "L3" and ext.lower() in {"png", "jpg", "jpeg"}:
        payload = _watermark(payload, ext)
    media = stored.content_type or "application/octet-stream"
    return Response(content=payload, media_type=media, headers={"Cache-Control": "no-store"})


def view_logs(page_query: Page, params: dict) -> dict:
    where = []
    if text_of(params, "viewer"):
        where.append(CertViewLog.viewer_name.contains(text_of(params, "viewer")))
    if text_of(params, "holder"):
        where.append(CertViewLog.holder_label.contains(text_of(params, "holder")))
    if text_of(params, "level"):
        where.append(CertViewLog.view_level == text_of(params, "level"))
    start = text_of(params, "from")
    end = text_of(params, "to")
    if not start and not end and not text_of(params, "all"):
        start_day = now_naive().date() - timedelta(days=7)
        where.append(CertViewLog.create_time >= datetime_of(start_day))
    if start:
        where.append(CertViewLog.create_time >= datetime_of(parse_day(start, "from", "开始日期")))
    if end:
        where.append(CertViewLog.create_time < datetime_of(parse_day(end, "to", "结束日期") + timedelta(days=1)))
    rows, total = Repository(CertViewLog).page(page_query, *where, order=[CertViewLog.id.desc()])
    return page_result([_log_view(row) for row in rows], total, page_query)


def datetime_of(value):
    from datetime import datetime

    if isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day)


def _log_view(row: CertViewLog) -> dict:
    return {
        "id": row.id,
        "viewerName": row.viewer_name or "",
        "certLabel": row.holder_label or "",
        "viewLevel": row.view_level,
        "watermarkText": row.watermark_text or "",
        "durationSec": row.duration_sec,
        "ip": row.ip or "",
        "device": row.device or "",
        "riskFlag": bool(row.risk_flag),
        "time": format_datetime(row.create_time),
    }


def risk_report(params: dict) -> dict:
    if text_of(params, "export") in {"1", "true"}:
        data = _risk_rows()
        header = ["查看人", "证件", "级别", "时间", "IP"]
        body = [[item["viewerName"], item["certLabel"], item["viewLevel"], item["time"], item["ip"]] for item in data]
        _export_log()
        return remember_export("证件异常访问.xlsx", header, body, "cert-risk")
    return {"list": _risk_rows()}


def _export_log() -> None:
    from app.core.context import get_ctx
    from app.domains.system.model import OperateLog

    ctx = get_ctx()
    get_session().add(
        OperateLog(
            operator_id=ctx.user_id if ctx else None,
            operator_name=(ctx.nickname or ctx.username) if ctx else "",
            module="证件",
            action="异常报告",
            object_type="证件",
            success=1,
            path="/admin-api/ims/cert/security/risk-report",
            method="GET",
            creator=ctx.user_id if ctx and ctx.user_id else 0,
        )
    )
    get_session().flush()


def _risk_rows() -> list[dict]:
    rows = list(get_session().scalars(select(CertViewLog).where(CertViewLog.risk_flag == 1).order_by(CertViewLog.id.desc()).limit(200)))
    return [_log_view(row) for row in rows]
