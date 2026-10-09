"""CERT-003 查看审计与异常访问报告。

GET /cert/security/view-logs：按证件、查看人、级别、时间查询成功查看记录。
GET /cert/security/risk-report：近 1 小时查看次数超过 10 的用户。
下载不提供（CERT-S-R2）。换证不写入查看审计。
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.cert_view import VIEW_LIMIT, can_cert_r1
from app.core import mask_cert_no, utcnow
from app.corp import count_of, page_args, paged, tenant_of
from app.crypto import decrypt_text
from app.models import CertArchive, CertViewLog, User

router = APIRouter()

TYPE_LABEL = {"IDCARD": "身份证", "PASSPORT": "护照", "OTHER": "其他"}


def iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


def parse_dt(value: str) -> datetime | None:
    text = (value or "").strip().replace("T", " ")
    if not text:
        return None
    try:
        if len(text) <= 10:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def view_log_vo(row: CertViewLog, cert: CertArchive | None) -> dict:
    plain = decrypt_text(cert.cert_no_enc) if cert and cert.cert_no_enc else ""
    masked = mask_cert_no(plain)
    holder = cert.holder_name if cert else ""
    cert_type = TYPE_LABEL.get(cert.cert_type, cert.cert_type) if cert else ""
    label = f"{holder}·{cert_type}（{masked}）" if holder or cert_type else masked
    return {
        "id": row.id,
        "certId": row.cert_id,
        "certNoMasked": masked,
        "holderName": holder,
        "certLabel": label,
        "viewerUserId": row.viewer_user_id,
        "viewerName": row.viewer_name,
        "viewLevel": row.view_level,
        "watermarkText": row.watermark_text,
        "viewDuration": row.view_duration,
        "ip": row.ip,
        "device": row.device,
        "createdAt": iso(row.created_at),
    }


@router.get("/cert/security/view-logs")
def view_logs(
    pageNo: int = 1,
    pageSize: int = 10,
    certId: int = 0,
    viewerUserId: int = 0,
    viewLevel: int = 0,
    timeRange: list[str] = Query(default=[]),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_cert_r1(db, actor):
        return fail(1008, "权限不足")
    if viewLevel not in (0, 1, 2, 3):
        return fail(1001, "查看级别不合法")
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(CertViewLog).where(CertViewLog.deleted == 0, CertViewLog.tenant_id == tenant_of(actor))
    if certId:
        stmt = stmt.where(CertViewLog.cert_id == certId)
    if viewerUserId:
        stmt = stmt.where(CertViewLog.viewer_user_id == viewerUserId)
    if viewLevel:
        stmt = stmt.where(CertViewLog.view_level == viewLevel)
    if len(timeRange) >= 2 and timeRange[0] and timeRange[1]:
        start = parse_dt(timeRange[0])
        end = parse_dt(timeRange[1])
        if start is None or end is None:
            return fail(1001, "时间范围不合法")
        if start > end:
            return fail(1001, "开始时间不能晚于结束时间")
        stmt = stmt.where(CertViewLog.created_at >= start, CertViewLog.created_at <= end)
    total = count_of(db, stmt)
    rows = db.scalars(stmt.order_by(CertViewLog.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    certs: dict[int, CertArchive] = {}
    if rows:
        ids = [row.cert_id for row in rows]
        for cert in db.scalars(select(CertArchive).where(CertArchive.id.in_(ids))).all():
            certs[cert.id] = cert
    return paged([view_log_vo(row, certs.get(row.cert_id)) for row in rows], total, page_no, size)


@router.get("/cert/security/risk-report")
def risk_report(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    """近 1 小时成功查看超过 10 次的用户。单证第 11 次被 1035 拦住且不写审计。"""
    if not can_cert_r1(db, actor):
        return fail(1008, "权限不足")
    since = utcnow() - timedelta(hours=1)
    rows = db.execute(
        select(
            CertViewLog.viewer_user_id,
            func.max(CertViewLog.viewer_name),
            func.count(),
        )
        .where(
            CertViewLog.deleted == 0,
            CertViewLog.tenant_id == tenant_of(actor),
            CertViewLog.created_at >= since,
        )
        .group_by(CertViewLog.viewer_user_id)
    ).all()
    users = []
    abnormal = 0
    for user_id, name, count in rows:
        views = int(count)
        if views <= VIEW_LIMIT:
            continue
        users.append({"userId": int(user_id), "name": name or "", "viewsInLastHour": views})
        abnormal += views
    users.sort(key=lambda item: (-item["viewsInLastHour"], item["userId"]))
    return ok({"highFrequencyUsers": users, "abnormalTotal": abnormal})
