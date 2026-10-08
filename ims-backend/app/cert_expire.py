"""CERT-002 证件到期预警（BR-013）。

T−30 黄色、T−7 红色、T−0 锁定。扫描后推送工作台待办和消息。
同级别不重复推送（CERT-E-R2）；级别升高才再推。钉钉不外发。
"""

import json
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_cert_no, utcnow
from app.corp import cert_vo, count_of, page_args, paged, tenant_of, visible
from app.crypto import decrypt_text, encrypt_text, sha256_hex
from app.models import CertArchive, CertExpireLog, Todo, User, WorkMessage

router = APIRouter()

DATE_RE_OK = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")
CERT_TYPES = ("IDCARD", "PASSPORT", "OTHER")
BLOCKING_STATUS = ("PENDING_REVIEW", "EFFECTIVE", "EXPIRING", "EXPIRED")
SCAN_STATUS = ("EFFECTIVE", "EXPIRING", "EXPIRED")
OPEN_LOG = ("WARNING", "EXPIRED_LOCKED")
RANK = {"YELLOW": 1, "RED": 2, "LOCKED": 3}
LABEL = {"YELLOW": "黄色", "RED": "红色", "LOCKED": "锁定"}


def warn_level(days: int) -> str | None:
    """剩余天数 → 预警级别。30 黄、7 红、0 及已过期锁定。"""
    if days <= 0:
        return "LOCKED"
    if days <= 7:
        return "RED"
    if days <= 30:
        return "YELLOW"
    return None


def parse_date(value: str) -> date | None:
    text = (value or "").strip()
    if not DATE_RE_OK.match(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def remain_days(expire_date: str, today: date) -> int | None:
    parsed = parse_date(expire_date)
    if parsed is None:
        return None
    return (parsed - today).days


def iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


class UploadBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    holderUserId: int | None = None
    holderName: str | None = None
    certType: str
    certNoPlain: str
    fileKey: str
    issueDate: str
    expireDate: str


class ReviewBody(BaseModel):
    action: str
    remark: str | None = None


def blocking_archive(db: Session, actor: User, holder_name: str, cert_type: str) -> CertArchive | None:
    return db.scalar(
        select(CertArchive).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == tenant_of(actor),
            CertArchive.holder_name == holder_name,
            CertArchive.cert_type == cert_type,
            CertArchive.status.in_(BLOCKING_STATUS),
        )
    )


@router.post("/cert/archive/upload")
def archive_upload(body: UploadBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    holder = (body.holderName or "").strip()
    if not holder:
        return fail(1001, "持有人必填")
    if body.certType not in CERT_TYPES:
        return fail(1001, "证件类型不合法")
    plain = (body.certNoPlain or "").strip()
    if len(plain) < 8:
        return fail(1001, "证件号不合法")
    if not (body.fileKey or "").strip():
        return fail(1001, "fileKey 必填")
    issue = parse_date(body.issueDate)
    expire = parse_date(body.expireDate)
    if issue is None or expire is None:
        return fail(1001, "日期须为 yyyy-MM-dd")
    if expire < issue:
        return fail(1001, "有效期须不早于签发日期")
    if blocking_archive(db, actor, holder, body.certType) is not None:
        return fail(1032, "已存在同类型档案，请走换证")
    holder_user_id = body.holderUserId if body.holderUserId else actor.id
    holder_user = db.get(User, holder_user_id)
    if holder_user is None or holder_user.deleted or (holder_user.tenant_id or 0) != tenant_of(actor):
        return fail(1500, "持有人不存在")
    row = CertArchive(
        holder_user_id=holder_user.id,
        holder_name=holder[:64],
        cert_type=body.certType,
        cert_no_enc=encrypt_text(plain),
        cert_no_hash=sha256_hex(plain),
        issue_date=issue.isoformat(),
        expire_date=expire.isoformat(),
        status="PENDING_REVIEW",
        uploaded_by=actor.id,
        creator=actor.id,
        updater=actor.id,
        tenant_id=tenant_of(actor),
    )
    db.add(row)
    db.flush()
    return ok(cert_vo(row))


@router.put("/cert/archive/{cert_id}/review")
def archive_review(
    cert_id: int,
    body: ReviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(CertArchive, cert_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if row.status != "PENDING_REVIEW":
        return fail(1033, "当前状态不可审核")
    action = (body.action or "").strip().upper()
    if action == "APPROVE":
        row.status = "EFFECTIVE"
    elif action == "REJECT":
        row.deleted = 1
    else:
        return fail(1001, "动作不合法")
    row.updater = actor.id
    row.updated_at = utcnow()
    return ok(None)


def open_log(db: Session, actor: User, cert_id: int) -> CertExpireLog | None:
    return db.scalar(
        select(CertExpireLog)
        .where(
            CertExpireLog.deleted == 0,
            CertExpireLog.tenant_id == tenant_of(actor),
            CertExpireLog.cert_id == cert_id,
            CertExpireLog.status.in_(OPEN_LOG),
        )
        .order_by(CertExpireLog.id.desc())
    )


def recipient_ids(db: Session, actor: User, cert: CertArchive) -> list[int]:
    tenant = tenant_of(actor)
    wanted = {actor.id}
    if cert.holder_user_id:
        wanted.add(int(cert.holder_user_id))
    admins = db.scalars(
        select(User.id).where(User.deleted == 0, User.tenant_id == tenant, User.username == "admin", User.status == "ENABLED")
    ).all()
    wanted.update(int(item) for item in admins)
    found: list[int] = []
    for user_id in sorted(wanted):
        user = db.get(User, user_id)
        if user is None or user.deleted or user.status != "ENABLED":
            continue
        if (user.tenant_id or 0) != tenant:
            continue
        found.append(user.id)
    return found


def push_workbench(db: Session, actor: User, cert: CertArchive, log: CertExpireLog, level: str) -> list[int]:
    users = recipient_ids(db, actor, cert)
    plain = decrypt_text(cert.cert_no_enc) if cert.cert_no_enc else ""
    masked = mask_cert_no(plain)
    label = LABEL[level]
    title = f"证件{label}预警：{cert.holder_name}"[:128]
    content = f"{label}预警（{level}）· 有效期 {cert.expire_date} · {masked}"[:512]
    deadline = None
    parsed = parse_date(cert.expire_date)
    if parsed is not None:
        deadline = datetime(parsed.year, parsed.month, parsed.day)
    for user_id in users:
        db.add(
            Todo(
                assignee_user_id=user_id,
                task_type="cert_expire",
                ref_type="cert_expire",
                ref_id=log.id,
                title=title,
                content=content,
                status="PENDING",
                deadline=deadline,
                tenant_id=tenant_of(actor),
            )
        )
        db.add(
            WorkMessage(
                user_id=user_id,
                title=title,
                content=content,
                channel="IN_APP",
                read_flag=0,
                source_module="CERT",
                ref_type="cert_expire",
                ref_id=log.id,
                tenant_id=tenant_of(actor),
            )
        )
    known = {item for item in (log.notified_levels or "").split(",") if item}
    known.add(level)
    log.notified_levels = ",".join(sorted(known, key=lambda item: RANK[item]))
    log.notify_user_ids = json.dumps(users)
    log.updater = actor.id
    log.updated_at = utcnow()
    return users


def apply_cert_status(cert: CertArchive, level: str, actor: User) -> None:
    if level == "LOCKED":
        cert.status = "EXPIRED"
    elif cert.status in ("EFFECTIVE", "EXPIRING"):
        cert.status = "EXPIRING"
    cert.updater = actor.id
    cert.updated_at = utcnow()


def log_status_for(level: str) -> str:
    return "EXPIRED_LOCKED" if level == "LOCKED" else "WARNING"


@router.post("/cert/expire/scan")
def expire_scan(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    today = date.today()
    rows = db.scalars(
        select(CertArchive).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == tenant_of(actor),
            CertArchive.status.in_(SCAN_STATUS),
        )
    ).all()
    created = 0
    upgraded = 0
    skipped = 0
    for cert in rows:
        days = remain_days(cert.expire_date, today)
        if days is None:
            continue
        level = warn_level(days)
        if level is None:
            continue
        log = open_log(db, actor, cert.id)
        if log is None:
            log = CertExpireLog(
                cert_id=cert.id,
                holder_user_id=cert.holder_user_id,
                level=level,
                status=log_status_for(level),
                creator=actor.id,
                updater=actor.id,
                tenant_id=tenant_of(actor),
            )
            db.add(log)
            db.flush()
            push_workbench(db, actor, cert, log, level)
            apply_cert_status(cert, level, actor)
            created += 1
            continue
        if log.level == level or RANK[level] < RANK.get(log.level, 0):
            skipped += 1
            continue
        log.level = level
        log.status = log_status_for(level)
        log.holder_user_id = cert.holder_user_id
        push_workbench(db, actor, cert, log, level)
        apply_cert_status(cert, level, actor)
        upgraded += 1
    scan_id = f"SCAN-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    message = f"扫描完成：新增 {created}，升级 {upgraded}，同级不重复 {skipped}。已推送工作台，钉钉未外发。"
    return ok({"scanTaskId": scan_id, "message": message, "created": created, "upgraded": upgraded, "skipped": skipped})


def notified_ids(raw: str) -> list[int]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [int(item) for item in data if str(item).isdigit() or isinstance(item, int)]


def expire_vo(log: CertExpireLog, cert: CertArchive | None, today: date) -> dict:
    plain = decrypt_text(cert.cert_no_enc) if cert and cert.cert_no_enc else ""
    expire_date = cert.expire_date if cert else ""
    days = remain_days(expire_date, today) if expire_date else None
    return {
        "id": log.id,
        "certId": log.cert_id,
        "certNoMasked": mask_cert_no(plain),
        "holderName": cert.holder_name if cert else "",
        "holderUserId": log.holder_user_id,
        "certType": cert.cert_type if cert else "",
        "expireDate": expire_date,
        "remainDays": days if days is not None else "",
        "level": log.level,
        "notifiedUserIds": notified_ids(log.notify_user_ids),
        "status": log.status,
        "createdAt": iso(log.created_at),
    }


def expire_stmt(actor: User, request: Request):
    stmt = select(CertExpireLog).where(CertExpireLog.deleted == 0, CertExpireLog.tenant_id == tenant_of(actor))
    scope = getattr(request.state, "scope", None)
    if scope is not None and scope.kind == "SELF":
        stmt = stmt.where(CertExpireLog.holder_user_id == actor.id)
    return stmt


@router.get("/cert/expire/list")
def expire_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    level: str = "",
    status: str = "",
    holderName: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = expire_stmt(actor, request)
    if level:
        stmt = stmt.where(CertExpireLog.level == level)
    if status:
        stmt = stmt.where(CertExpireLog.status == status)
    if holderName.strip():
        cert_ids = select(CertArchive.id).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == tenant_of(actor),
            CertArchive.holder_name.like(f"%{holderName.strip()}%"),
        )
        stmt = stmt.where(CertExpireLog.cert_id.in_(cert_ids))
    total = count_of(db, stmt)
    rows = db.scalars(stmt.order_by(CertExpireLog.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    today = date.today()
    certs = {}
    if rows:
        ids = [row.cert_id for row in rows]
        for cert in db.scalars(select(CertArchive).where(CertArchive.id.in_(ids))).all():
            certs[cert.id] = cert
    return paged([expire_vo(row, certs.get(row.cert_id), today) for row in rows], total, page_no, size)


@router.get("/cert/expire/stats")
def expire_stats(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant = tenant_of(actor)
    by_level = {"YELLOW": 0, "RED": 0, "LOCKED": 0}
    rows = db.execute(
        select(CertExpireLog.level, func.count())
        .where(
            CertExpireLog.deleted == 0,
            CertExpireLog.tenant_id == tenant,
            CertExpireLog.status.in_(OPEN_LOG),
        )
        .group_by(CertExpireLog.level)
    ).all()
    for level, count in rows:
        if level in by_level:
            by_level[level] = int(count)
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    renewed = db.scalar(
        select(func.count())
        .select_from(CertExpireLog)
        .where(
            CertExpireLog.deleted == 0,
            CertExpireLog.tenant_id == tenant,
            CertExpireLog.status == "RENEW_RESOLVED",
            CertExpireLog.updated_at >= datetime.fromisoformat(month_start),
        )
    ) or 0
    return ok(
        {
            "byLevel": by_level,
            "yellowCount": by_level["YELLOW"],
            "redCount": by_level["RED"],
            "lockedCount": by_level["LOCKED"],
            "renewedThisMonth": int(renewed),
            "trend": [
                {
                    "date": today.isoformat(),
                    "yellow": by_level["YELLOW"],
                    "red": by_level["RED"],
                    "locked": by_level["LOCKED"],
                }
            ],
        }
    )
