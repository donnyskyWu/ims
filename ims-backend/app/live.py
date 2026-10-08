from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import (
    CertArchive,
    LiveAlarmRecord,
    LiveDataSnapshot,
    LiveReport,
    LiveRiskCheck,
    LiveSession,
    LiveSessionSeq,
    LiveSessionToken,
    User,
)
from app.ops_models import LiveRoom, Phone, PlatformAccount, Realname

router = APIRouter(prefix="/live", tags=["live"])

SESSION_CODE_RE = re.compile(r"^IMS\d{8}[A-Z]{3}\d{4}$")
PLATFORM_CODES = {
    "DOUYIN": "DYS",
    "KUAISHOU": "KS",
    "WECHAT_CHANNELS": "WX",
    "WECHAT_VIDEO": "WX",
    "TAOBAO": "TM",
    "JD": "JD",
    "OTHER": "OTA",
    "OTA": "OTA",
}
RISK_ITEMS = ("CERT_VALID", "ACCOUNT_STATUS", "BALANCE", "BLACKLIST", "DEVICE_OWNER")
WEIGHTS = {
    "CERT_VALID": 30,
    "ACCOUNT_STATUS": 20,
    "BALANCE": 10,
    "BLACKLIST": 25,
    "DEVICE_OWNER": 15,
}
BJ = timezone(timedelta(hours=8))


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def platform_code(platform: str) -> str:
    return PLATFORM_CODES.get(platform.upper(), "OTA")


def next_session_code(db: Session, tenant_id: int, platform: str) -> str:
    now = datetime.now(BJ)
    biz_date = now.strftime("%Y%m%d")
    code = platform_code(platform)
    row = db.scalar(
        select(LiveSessionSeq).where(
            LiveSessionSeq.tenant_id == tenant_id,
            LiveSessionSeq.biz_date == biz_date,
            LiveSessionSeq.platform_code == code,
        )
    )
    if row is None:
        row = LiveSessionSeq(biz_date=biz_date, platform_code=code, tenant_id=tenant_id, seq_val=0)
        db.add(row)
        db.flush()
    row.seq_val += 1
    seq = row.seq_val
    if seq > 9999:
        seq_str = f"{seq:05d}"[-5:]
    else:
        seq_str = f"{seq:04d}"
    return f"IMS{biz_date}{code}{seq_str}"


def restrict_sessions(stmt, actor: User, scope):
    stmt = stmt.where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_of(actor))
    if scope is None or scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(LiveSession.responsible_user_id == actor.id)
    if scope.kind == "DEPT":
        return stmt.where(LiveSession.responsible_user_id == actor.id)
    if scope.kind == "IP_GROUP":
        return stmt.where(LiveSession.responsible_user_id == actor.id)
    return stmt.where(LiveSession.id < 0)


def get_session(db: Session, actor: User, scope, session_code: str) -> LiveSession | None:
    row = db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == session_code,
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_of(actor),
        )
    )
    if row is None:
        return None
    if scope is not None and scope.kind != "ALL" and row.responsible_user_id != actor.id:
        return None
    return row


def load_account(ops: Session, actor: User, account_id: int) -> PlatformAccount | None:
    row = ops.get(PlatformAccount, account_id)
    if not visible(row, actor):
        return None
    return row


def load_realname(ops: Session, actor: User, person_id: int) -> Realname | None:
    row = ops.get(Realname, person_id)
    if not visible(row, actor):
        return None
    return row


def validate_devices(ops: Session, actor: User, device_ids: list[int]) -> bool:
    if not device_ids:
        return False
    for device_id in device_ids:
        phone = ops.get(Phone, device_id)
        if not visible(phone, actor):
            return False
    return True


USABLE_CERT_STATUS = frozenset({"EFFECTIVE", "EXPIRING"})


def cert_blocks_live(db: Session, actor: User, person: Realname) -> str | None:
    """LIVE-R2 / CERT-E-R3：实名人名下过期、锁定或未生效证件拦截开播（1045）。

    没有证件不拦截，避免无档实名人的既有场次被误伤。
    仍有 EXPIRED 档时，旁边即使已有新的 EFFECTIVE 档也不放行，须走换证把旧档改为 RECYCLED。
    """
    name = (person.real_name or "").strip()[:64]
    if not name:
        return None
    rows = db.scalars(
        select(CertArchive).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == tenant_of(actor),
            CertArchive.holder_name == name,
        )
    ).all()
    if not rows:
        return None
    if any(row.status == "EXPIRED" for row in rows):
        return "实名人证件过期或锁定，禁止开播"
    if any(row.status in USABLE_CERT_STATUS for row in rows):
        return None
    if any(row.status != "RECYCLED" for row in rows):
        return "实名人证件未生效，禁止开播"
    return None


def locked_cert_fail(db: Session, actor: User, person: Realname):
    reason = cert_blocks_live(db, actor, person)
    if reason is None:
        return None
    return fail(1045, reason)


def risk_level_of(score: int) -> str:
    if score >= 70:
        return "RED"
    if score >= 40:
        return "YELLOW"
    return "GREEN"


def run_risk_checks(
    db: Session,
    ops: Session,
    actor: User,
    session: LiveSession,
    account: PlatformAccount,
    person: Realname,
    device_ids: list[int],
) -> tuple[int, str, list[LiveRiskCheck]]:
    now = iso(utcnow()) or ""
    results: list[LiveRiskCheck] = []
    score = 0
    for item in RISK_ITEMS:
        result = "PASS"
        weight = WEIGHTS[item]
        if item == "CERT_VALID":
            if person.status != "ENABLED":
                result = "FAIL"
                score += weight
            elif person.status == "ENABLED":
                result = "PASS"
        elif item == "ACCOUNT_STATUS":
            if account.status != "IN_USE":
                result = "FAIL"
                score += weight
        elif item == "DEVICE_OWNER":
            if not validate_devices(ops, actor, device_ids):
                result = "WARN"
                score += weight // 2
        else:
            result = "PASS"
        row = LiveRiskCheck(
            session_id=session.id,
            check_item=item,
            check_result=result,
            score_weight=weight if result != "PASS" else 0,
            checked_at=now,
            tenant_id=session.tenant_id,
        )
        results.append(row)
    level = risk_level_of(score)
    return score, level, results


def apply_risk(db: Session, session: LiveSession, score: int, level: str, checks: list[LiveRiskCheck]) -> None:
    db.execute(
        LiveRiskCheck.__table__.delete().where(
            LiveRiskCheck.session_id == session.id, LiveRiskCheck.deleted == 0
        )
    )
    for row in checks:
        db.add(row)
    session.risk_score = score
    session.risk_level = level
    if level == "GREEN":
        session.session_status = "APPROVED"
    elif level == "YELLOW":
        session.session_status = "PENDING_RISK_CHECK"
    else:
        session.session_status = "PENDING_RISK_CHECK"


def report_vo(report: LiveReport | None) -> dict | None:
    if report is None or report.deleted:
        return None
    total_cost = float(report.ad_cost or 0)
    avg_order = round(report.gmv / report.order_count, 2) if report.order_count else 0.0
    roas = round(report.gmv / total_cost, 2) if total_cost else 0.0
    return {
        "id": report.id,
        "sessionCode": report.session_code,
        "actualStart": report.actual_start,
        "actualEnd": report.actual_end,
        "durationMinutes": report.duration_minutes,
        "gmv": round(report.gmv, 2),
        "refundAmount": round(report.refund_amount, 2),
        "orderCount": report.order_count,
        "viewerCount": report.viewer_count,
        "peakOnline": report.peak_online,
        "newFans": report.new_fans,
        "adCost": round(report.ad_cost, 2),
        "avgOrderValue": avg_order,
        "roas": roas,
        "entryUserId": report.entry_user_id,
        "entryStatus": report.entry_status,
        "submittedAt": report.submitted_at,
    }


def report_summary(report: LiveReport | None) -> dict | None:
    vo = report_vo(report)
    if vo is None:
        return None
    return {
        "gmv": vo["gmv"],
        "orderCount": vo["orderCount"],
        "durationMinutes": vo["durationMinutes"],
        "roas": vo["roas"],
        "entryStatus": vo["entryStatus"],
    }


def session_vo(
    db: Session,
    row: LiveSession,
    report: LiveReport | None = None,
    risk_checks: list[LiveRiskCheck] | None = None,
) -> dict:
    names = user_names(db, [row.responsible_user_id, row.approver_user_id or 0])
    base = {
        "id": row.id,
        "sessionCode": row.session_code,
        "accountId": row.account_id,
        "accountNo": row.account_no,
        "realnamePersonId": row.realname_person_id,
        "realnameName": row.realname_name,
        "responsibleUserId": row.responsible_user_id,
        "responsibleUserName": names.get(row.responsible_user_id, ""),
        "deviceAssetIds": json.loads(row.device_asset_ids or "[]"),
        "platform": row.platform,
        "topic": row.topic,
        "planStartTime": row.plan_start_time,
        "planEndTime": row.plan_end_time,
        "sessionStatus": row.session_status,
        "riskScore": row.risk_score,
        "riskLevel": row.risk_level,
        "approverUserId": row.approver_user_id,
        "approverName": names.get(row.approver_user_id or 0),
        "footballRoomId": row.football_room_id,
        "footballSyncStatus": row.football_sync_status,
        "lastFootballSyncAt": row.last_football_sync_at,
        "isSupplement": bool(row.is_supplement),
        "actualStart": row.actual_start,
        "actualEnd": row.actual_end,
        "createdAt": iso(row.created_at),
    }
    if report is not None:
        base["reportSummary"] = report_summary(report)
        base["reportEntryStatus"] = report.entry_status if report and not report.deleted else None
    else:
        base["reportEntryStatus"] = None
    if risk_checks is not None:
        base["riskCheckResults"] = [
            {
                "id": item.id,
                "sessionId": item.session_id,
                "checkItem": item.check_item,
                "checkResult": item.check_result,
                "scoreWeight": item.score_weight,
                "checkedAt": item.checked_at,
            }
            for item in risk_checks
        ]
    return base


def ledger_vo(db: Session, row: LiveSession, report: LiveReport | None) -> dict:
    item = session_vo(db, row, report)
    item["reportSummary"] = report_summary(report)
    return item


def read_live_room(ops: Session, actor: User, room_id: str) -> LiveRoom | None:
    try:
        rid = int(room_id)
    except ValueError:
        return None
    row = ops.get(LiveRoom, rid)
    if row is None or row.deleted:
        return None
    if (row.tenant_id or 0) != tenant_of(actor):
        return None
    return row


def room_basic_vo(room: LiveRoom) -> dict:
    start = room.start_time
    end = room.end_time
    duration = None
    if start and end:
        duration = int((end - start).total_seconds() // 60)
    return {
        "roomId": str(room.id),
        "liveId": room.live_id or None,
        "liveName": room.live_name or None,
        "authorId": room.author_id or None,
        "authorNickname": room.nickname or None,
        "authorAvatar": room.avatar or None,
        "status": room.status,
        "orientation": room.orientation or None,
        "payType": room.pay_type or None,
        "startTime": iso(start),
        "endTime": iso(end),
        "durationMinutes": duration,
        "coverUrl": room.cover or None,
        "playUrl": room.play_url or None,
        "replayUrl": room.replay_url or None,
        "pushUrl": room.push_url or None,
        "viewerCount": room.viewer_count,
        "likeCount": room.like_count,
        "reservationCount": room.reservation_count,
        "sourceTable": "live_room",
    }


def metrics_payload(db: Session, ops: Session, actor: User, session: LiveSession) -> dict:
    sync = session.football_sync_status or "UNLINKED"
    if not session.football_room_id:
        sync = "UNLINKED"
    basic = None
    if session.football_room_id:
        room = read_live_room(ops, actor, session.football_room_id)
        if room:
            basic = room_basic_vo(room)
            if sync == "UNLINKED":
                sync = "PENDING"
    snap = db.scalar(
        select(LiveDataSnapshot).where(
            LiveDataSnapshot.session_code == session.session_code,
            LiveDataSnapshot.deleted == 0,
            LiveDataSnapshot.tenant_id == tenant_of(actor),
        )
    )
    snapshot = None
    if snap:
        snapshot = {
            "viewerCount": snap.viewer_count,
            "peakOnline": snap.peak_online,
            "durationMinutes": snap.duration_minutes,
            "gmvFromPlatform": snap.gmv_from_platform,
            "source": snap.source,
            "capturedAt": snap.captured_at,
        }
    return {
        "sessionCode": session.session_code,
        "footballRoomId": session.football_room_id,
        "syncStatus": sync,
        "lastSyncAt": session.last_football_sync_at,
        "footballRoomBasic": basic,
        "snapshot": snapshot,
        "metricsByManualEntry": {
            "gmv": True,
            "peakOnline": True,
            "fansGrowth": True,
            "refundAmount": True,
            "adCost": True,
        },
    }


class LiveCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    accountId: int
    realnamePersonId: int
    responsibleUserId: int
    deviceAssetIds: list[int] = Field(default_factory=list)
    platform: str
    topic: str
    planStartTime: str
    planEndTime: str = ""
    footballRoomId: str | None = None


class LiveUpdateBody(LiveCreateBody):
    footballRoomId: str | None = None


class ApproveBody(BaseModel):
    approve: bool
    comment: str | None = None


class CancelBody(BaseModel):
    cancelReason: str


class ReportBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    actualStart: str
    actualEnd: str
    durationMinutes: int | None = None
    gmv: float
    refundAmount: float
    orderCount: int
    viewerCount: int
    peakOnline: int
    newFans: int
    adCost: float


class SyncBody(BaseModel):
    force: bool | None = False


def filter_sessions(
    db: Session,
    actor: User,
    scope,
    session_code: str = "",
    account_id: int | None = None,
    responsible_user_id: int | None = None,
    session_status: str = "",
    risk_level: str = "",
    platform: str = "",
    is_supplement: bool | None = None,
):
    stmt = select(LiveSession)
    stmt = restrict_sessions(stmt, actor, scope)
    if session_code:
        stmt = stmt.where(LiveSession.session_code == session_code)
    if account_id:
        stmt = stmt.where(LiveSession.account_id == account_id)
    if responsible_user_id:
        stmt = stmt.where(LiveSession.responsible_user_id == responsible_user_id)
    if session_status:
        stmt = stmt.where(LiveSession.session_status == session_status)
    if risk_level:
        stmt = stmt.where(LiveSession.risk_level == risk_level)
    if platform:
        stmt = stmt.where(LiveSession.platform == platform)
    if is_supplement is not None:
        stmt = stmt.where(LiveSession.is_supplement == (1 if is_supplement else 0))
    return stmt.order_by(LiveSession.id.desc())


@router.get("/sessions/list")
def sessions_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    accountId: int | None = None,
    responsibleUserId: int | None = None,
    sessionStatus: str = "",
    riskLevel: str = "",
    platform: str = "",
    isSupplement: bool | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = filter_sessions(
        db,
        actor,
        request.state.scope,
        sessionCode,
        accountId,
        responsibleUserId,
        sessionStatus,
        riskLevel,
        platform,
        isSupplement,
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all()
    out = []
    for row in rows:
        report = db.scalar(
            select(LiveReport).where(LiveReport.session_code == row.session_code, LiveReport.deleted == 0)
        )
        out.append(ledger_vo(db, row, report))
    return paged(out, total, page_no, size)


@router.get("/sessions/{session_code}")
def sessions_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    report = db.scalar(select(LiveReport).where(LiveReport.session_code == session_code, LiveReport.deleted == 0))
    checks = db.scalars(
        select(LiveRiskCheck).where(LiveRiskCheck.session_id == row.id, LiveRiskCheck.deleted == 0)
    ).all()
    data = session_vo(db, row, report, list(checks))
    data["metricsSnapshot"] = metrics_payload(db, ops, actor, row)
    data["footballEnrichment"] = data["metricsSnapshot"].get("footballRoomBasic")
    if report:
        data["report"] = report_vo(report)
        data["costSummary"] = {"totalCost": round(report.ad_cost, 2), "byType": {"AD": round(report.ad_cost, 2)}}
    else:
        data["report"] = None
        data["costSummary"] = None
    return ok(data)


@router.get("/sessions/{session_code}/metrics")
def sessions_metrics(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    return ok(metrics_payload(db, ops, actor, row))


@router.post("/sessions/{session_code}/football-sync")
def football_sync(
    request: Request,
    session_code: str,
    body: SyncBody | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if not row.football_room_id:
        return fail(1041, "未绑定 Football 直播间")
    room = read_live_room(ops, actor, row.football_room_id)
    if room is None:
        return fail(1051, "Football 直播间不存在")
    now = iso(utcnow())
    row.football_sync_status = "SYNCED"
    row.last_football_sync_at = now
    snap = db.scalar(
        select(LiveDataSnapshot).where(
            LiveDataSnapshot.session_code == session_code,
            LiveDataSnapshot.deleted == 0,
        )
    )
    if snap is None:
        snap = LiveDataSnapshot(session_code=session_code, tenant_id=tenant_of(actor), source="COLLECT")
        db.add(snap)
    snap.viewer_count = room.viewer_count
    snap.duration_minutes = room_basic_vo(room).get("durationMinutes")
    snap.captured_at = now or ""
    return ok(metrics_payload(db, ops, actor, row))


@router.post("/register")
def register_create(
    body: LiveCreateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
    clientToken: str | None = Header(default=None),
):
    if not clientToken:
        return fail(1001, "clientToken 必填")
    tenant_id = tenant_of(actor)
    existing = db.scalar(
        select(LiveSessionToken).where(
            LiveSessionToken.client_token == clientToken,
            LiveSessionToken.tenant_id == tenant_id,
        )
    )
    if existing:
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == existing.session_code))
        if row:
            checks = db.scalars(select(LiveRiskCheck).where(LiveRiskCheck.session_id == row.id)).all()
            return ok(session_vo(db, row, risk_checks=list(checks)))
    account = load_account(ops, actor, body.accountId)
    if account is None:
        return fail(1041, "账号不存在")
    person = load_realname(ops, actor, body.realnamePersonId)
    if person is None:
        return fail(1041, "实名人不存在")
    blocked = locked_cert_fail(db, actor, person)
    if blocked is not None:
        return blocked
    if not validate_devices(ops, actor, body.deviceAssetIds):
        return fail(1041, "设备资产不存在")
    user = db.get(User, body.responsibleUserId)
    if user is None or user.deleted or (user.tenant_id or 0) != tenant_id:
        return fail(1041, "责任人不存在")
    session_code = next_session_code(db, tenant_id, body.platform)
    if not SESSION_CODE_RE.match(session_code):
        return fail(1005, "场次 ID 生成失败")
    row = LiveSession(
        session_code=session_code,
        account_id=body.accountId,
        account_no=account.account_no,
        realname_person_id=body.realnamePersonId,
        realname_name=person.real_name,
        responsible_user_id=body.responsibleUserId,
        device_asset_ids=json.dumps(body.deviceAssetIds),
        platform=body.platform,
        topic=body.topic,
        plan_start_time=body.planStartTime,
        plan_end_time=body.planEndTime or "",
        creator=actor.id,
        tenant_id=tenant_id,
        football_room_id=body.footballRoomId,
        football_sync_status="UNLINKED" if not body.footballRoomId else "PENDING",
    )
    db.add(row)
    db.flush()
    db.add(LiveSessionToken(client_token=clientToken, session_code=session_code, tenant_id=tenant_id))
    score, level, checks = run_risk_checks(db, ops, actor, row, account, person, body.deviceAssetIds)
    apply_risk(db, row, score, level, checks)
    db.flush()
    for item in checks:
        db.refresh(item)
    return ok(session_vo(db, row, risk_checks=checks))


@router.get("/register/list")
def register_list(
    request: Request,
    pageNum: int = 1,
    pageSize: int = 20,
    pageNo: int | None = None,
    sessionCode: str = "",
    accountId: int | None = None,
    responsibleUserId: int | None = None,
    riskLevel: str = "",
    sessionStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no = pageNo or pageNum
    page_no, size = page_args(page_no, pageSize)
    stmt = filter_sessions(
        db,
        actor,
        request.state.scope,
        sessionCode,
        accountId,
        responsibleUserId,
        sessionStatus,
        riskLevel,
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all()
    records = [session_vo(db, row) for row in rows]
    return ok({"total": total, "records": records})


@router.get("/register/{session_code}")
def register_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    checks = db.scalars(
        select(LiveRiskCheck).where(LiveRiskCheck.session_id == row.id, LiveRiskCheck.deleted == 0)
    ).all()
    return ok(session_vo(db, row, risk_checks=list(checks)))


@router.put("/register/{session_code}")
def register_update(
    request: Request,
    session_code: str,
    body: LiveUpdateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if row.session_status not in ("PENDING_RISK_CHECK", "APPROVED"):
        return fail(1042, "当前状态不可编辑")
    account = load_account(ops, actor, body.accountId)
    person = load_realname(ops, actor, body.realnamePersonId)
    if account is None or person is None:
        return fail(1041, "账号或实名人不存在")
    blocked = locked_cert_fail(db, actor, person)
    if blocked is not None:
        return blocked
    if not validate_devices(ops, actor, body.deviceAssetIds):
        return fail(1041, "设备资产不存在")
    row.account_id = body.accountId
    row.account_no = account.account_no
    row.realname_person_id = body.realnamePersonId
    row.realname_name = person.real_name
    row.responsible_user_id = body.responsibleUserId
    row.device_asset_ids = json.dumps(body.deviceAssetIds)
    row.platform = body.platform
    row.topic = body.topic
    row.plan_start_time = body.planStartTime
    row.plan_end_time = body.planEndTime or ""
    if body.footballRoomId is not None:
        row.football_room_id = body.footballRoomId or None
        row.football_sync_status = "UNLINKED" if not body.footballRoomId else "PENDING"
    score, level, checks = run_risk_checks(db, ops, actor, row, account, person, body.deviceAssetIds)
    apply_risk(db, row, score, level, checks)
    return ok(None)


@router.post("/register/{session_code}/risk-check")
def risk_check(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    account = load_account(ops, actor, row.account_id)
    person = load_realname(ops, actor, row.realname_person_id)
    if account is None or person is None:
        return fail(1041, "账号或实名人不存在")
    blocked = locked_cert_fail(db, actor, person)
    if blocked is not None:
        return blocked
    device_ids = json.loads(row.device_asset_ids or "[]")
    score, level, checks = run_risk_checks(db, ops, actor, row, account, person, device_ids)
    apply_risk(db, row, score, level, checks)
    db.flush()
    if level == "RED":
        return ok(
            {
                "riskScore": score,
                "riskLevel": level,
                "checkResults": [
                    {
                        "id": c.id,
                        "sessionId": c.session_id,
                        "checkItem": c.check_item,
                        "checkResult": c.check_result,
                        "scoreWeight": c.score_weight,
                        "checkedAt": c.checked_at,
                    }
                    for c in checks
                ],
                "code": 1043,
            }
        )
    if level == "YELLOW":
        return ok({"riskScore": score, "riskLevel": level, "checkResults": session_vo(db, row, risk_checks=checks)["riskCheckResults"]})
    return ok({"riskScore": score, "riskLevel": level, "checkResults": session_vo(db, row, risk_checks=checks)["riskCheckResults"]})


@router.put("/register/{session_code}/approve")
def register_approve(
    request: Request,
    session_code: str,
    body: ApproveBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if row.risk_level == "RED":
        return fail(1043, "红色风险禁止放行")
    if row.risk_level != "YELLOW":
        return fail(1044, "仅黄级可审批")
    if body.approve:
        row.session_status = "APPROVED"
        row.approver_user_id = actor.id
    else:
        row.session_status = "PENDING_RISK_CHECK"
    return ok(None)


@router.put("/register/{session_code}/cancel")
def register_cancel(
    request: Request,
    session_code: str,
    body: CancelBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if not body.cancelReason:
        return fail(1001, "取消原因必填")
    row.session_status = "CANCELLED"
    row.cancel_reason = body.cancelReason
    return ok(None)


@router.put("/register/{session_code}/start")
def register_start(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if row.session_status != "APPROVED":
        return fail(1042, "未放行不可开播")
    person = load_realname(ops, actor, row.realname_person_id)
    if person is None:
        return fail(1041, "实名人不存在")
    blocked = locked_cert_fail(db, actor, person)
    if blocked is not None:
        return blocked
    row.session_status = "LIVE"
    return ok(None)


def upsert_report(db: Session, session: LiveSession, body: ReportBody, actor: User, submit: bool) -> LiveReport:
    report = db.scalar(select(LiveReport).where(LiveReport.session_code == session.session_code))
    duration = body.durationMinutes
    if duration is None:
        start = parse_iso(body.actualStart)
        end = parse_iso(body.actualEnd)
        duration = int((end - start).total_seconds() // 60) if start and end and end > start else 0
    if report is None:
        report = LiveReport(session_code=session.session_code, tenant_id=tenant_of(actor))
        db.add(report)
    report.actual_start = body.actualStart
    report.actual_end = body.actualEnd
    report.duration_minutes = duration or 0
    report.gmv = body.gmv
    report.refund_amount = body.refundAmount
    report.order_count = body.orderCount
    report.viewer_count = body.viewerCount
    report.peak_online = body.peakOnline
    report.new_fans = body.newFans
    report.ad_cost = body.adCost
    report.entry_user_id = actor.id
    if submit:
        report.entry_status = "SUBMITTED"
        report.submitted_at = iso(utcnow())
        session.session_status = "ENDED"
        session.actual_start = body.actualStart
        session.actual_end = body.actualEnd
    else:
        report.entry_status = "DRAFT"
    return report


@router.post("/report/{session_code}")
def report_submit(
    request: Request,
    session_code: str,
    body: ReportBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    if row.session_status not in ("LIVE", "ENDED") and row.session_status != "APPROVED":
        return fail(1042, "场次状态不允许录入")
    required = [body.actualStart, body.actualEnd, body.gmv, body.orderCount]
    if not all(x is not None for x in required):
        return fail(1046, "必填项缺失")
    report = upsert_report(db, row, body, actor, submit=True)
    db.flush()
    return ok(report_vo(report))


@router.get("/report/{session_code}")
def report_get(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    report = db.scalar(select(LiveReport).where(LiveReport.session_code == session_code, LiveReport.deleted == 0))
    if report is None:
        return ok(None)
    return ok(report_vo(report))


@router.put("/report/{session_code}")
def report_update(
    request: Request,
    session_code: str,
    body: ReportBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    report = db.scalar(select(LiveReport).where(LiveReport.session_code == session_code, LiveReport.deleted == 0))
    if report and report.entry_status != "DRAFT":
        return fail(1047, "提交后只读")
    upsert_report(db, row, body, actor, submit=False)
    return ok(None)


@router.put("/report/{session_code}/confirm")
def report_confirm(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = get_session(db, actor, request.state.scope, session_code)
    if row is None:
        return fail(1504, "资源不可用")
    report = db.scalar(select(LiveReport).where(LiveReport.session_code == session_code, LiveReport.deleted == 0))
    if report is None or report.entry_status != "SUBMITTED":
        return fail(1042, "报告未提交")
    report.entry_status = "CONFIRMED"
    return ok(None)


@router.get("/report/pending")
def report_pending(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = restrict_sessions(select(LiveSession), actor, request.state.scope)
    stmt = stmt.where(LiveSession.session_status.in_(("LIVE", "ENDED")))
    rows = db.scalars(stmt).all()
    pending = []
    for row in rows:
        report = db.scalar(select(LiveReport).where(LiveReport.session_code == row.session_code, LiveReport.deleted == 0))
        if report and report.entry_status in ("SUBMITTED", "CONFIRMED"):
            continue
        pending.append(
            {
                "sessionCode": row.session_code,
                "topic": row.topic,
                "endedAt": row.actual_end or row.plan_end_time,
                "responsibleUserName": user_names(db, [row.responsible_user_id]).get(row.responsible_user_id, ""),
                "submitted": bool(report and report.entry_status == "SUBMITTED"),
                "overdueHours": 0,
            }
        )
    total = len(pending)
    chunk = pending[(page_no - 1) * size : page_no * size]
    return ok({"list": chunk, "total": total, "pageNo": page_no, "pageSize": size})


@router.get("/ledger/list")
def ledger_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    accountId: int | None = None,
    responsibleUserId: int | None = None,
    sessionStatus: str = "",
    riskLevel: str = "",
    platform: str = "",
    isSupplement: bool | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    return sessions_list(
        request,
        pageNo,
        pageSize,
        sessionCode,
        accountId,
        responsibleUserId,
        sessionStatus,
        riskLevel,
        platform,
        isSupplement,
        db,
        actor,
    )


@router.get("/ledger/{session_code}")
def ledger_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    return sessions_detail(request, session_code, db, ops, actor)


@router.get("/alarm/records")
def alarm_records(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(LiveAlarmRecord).where(
        LiveAlarmRecord.deleted == 0,
        LiveAlarmRecord.tenant_id == tenant_of(actor),
    )
    if sessionCode:
        stmt = stmt.where(LiveAlarmRecord.session_code == sessionCode)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(LiveAlarmRecord.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    items = [
        {
            "id": row.id,
            "ruleId": row.rule_id,
            "ruleName": row.rule_name,
            "sessionCode": row.session_code,
            "alarmLevel": row.alarm_level,
            "alarmContent": row.alarm_content,
            "occurAt": row.occur_at,
            "handleStatus": row.handle_status,
            "handlerUserId": row.handler_user_id,
            "handleRemark": row.handle_remark,
        }
        for row in rows
    ]
    return ok({"list": items, "total": total, "pageNo": page_no, "pageSize": size})
