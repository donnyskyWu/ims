"""ALERT-003 三级升级（#130）。

配置 PUT /alert/escalate/config，待升级 GET /alert/escalate/pending，
时间轴 GET /alert/escalate/timeline/{alertNo}。
响应停止后续升级；非目标人 1166。钉钉不外发，到点只写站内通知。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.audit import publish_notify
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.live import role_tags
from app.models import AlertEscalateConfig, AlertRecord, AlertRule, User
from app.scope import enabled_roles

router = APIRouter()

BJ = timezone(timedelta(hours=8))
ROLE_CODES = ("R1", "R2", "R3", "R4", "R9")
LEVEL_NAME = {1: "一级", 2: "二级", 3: "三级"}


class Level1Receivers(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dynamicTarget: str = ""


class Level2Receivers(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dynamicTarget: str = ""
    extraUserIds: list[int] = []


class Level3Receivers(BaseModel):
    model_config = ConfigDict(extra="ignore")
    roleCodes: list[str] = []


class EscalateConfigBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    level1TimeoutMinutes: int
    level2TimeoutMinutes: int
    severeStartLevel: int
    level1Receivers: Level1Receivers
    level2Receivers: Level2Receivers
    level3Receivers: Level3Receivers


@dataclass
class Cfg:
    level1_minutes: int = 30
    level2_minutes: int = 60
    severe_start_level: int = 2
    extra_user_ids: tuple[int, ...] = ()
    role_codes: tuple[str, ...] = ("R4", "R1")


@dataclass
class Step:
    level: int
    enter_at: datetime
    leave_at: datetime | None


def iso(dt: datetime | None) -> str:
    """库内 naive UTC 转成带 +08:00 的东八区时刻，供前端倒计时解析。"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def level_code(value: int) -> str:
    return {1: "L1", 2: "L2", 3: "L3"}.get(value, "L2")


def is_r1(tags: set[str]) -> bool:
    return bool(tags & {"r1", "sys:admin"})


def is_r4(tags: set[str]) -> bool:
    return "r4" in tags


def parse_ids(raw: str) -> tuple[int, ...]:
    out: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return tuple(out)


def parse_codes(raw: str) -> tuple[str, ...]:
    codes = [part.strip().upper() for part in (raw or "").split(",") if part.strip()]
    return tuple(codes) or ("R4", "R1")


def load_cfg(db: Session, tenant_id: int) -> Cfg:
    row = db.scalar(
        select(AlertEscalateConfig).where(
            AlertEscalateConfig.deleted == 0,
            AlertEscalateConfig.tenant_id == tenant_id,
        )
    )
    if row is None:
        return Cfg()
    return Cfg(
        level1_minutes=row.level1_minutes,
        level2_minutes=row.level2_minutes,
        severe_start_level=row.severe_start_level if row.severe_start_level in (2, 3) else 2,
        extra_user_ids=parse_ids(row.level2_extra_ids),
        role_codes=parse_codes(row.level3_role_codes),
    )


def start_level(alert_level: int, cfg: Cfg) -> int:
    if alert_level >= 3:
        return cfg.severe_start_level
    return 1


def build_steps(occurred: datetime, alert_level: int, cfg: Cfg) -> list[Step]:
    begin = start_level(alert_level, cfg)
    cursor = occurred
    steps: list[Step] = []
    if begin <= 1:
        leave = cursor + timedelta(minutes=cfg.level1_minutes)
        steps.append(Step(1, cursor, leave))
        cursor = leave
    if begin <= 2:
        leave = cursor + timedelta(minutes=cfg.level2_minutes)
        steps.append(Step(2, cursor, leave))
        cursor = leave
    steps.append(Step(3, cursor, None))
    return steps


def current_step(steps: list[Step], now: datetime) -> Step:
    # MySQL DATETIME 按秒四舍五入，occurred_at 读回后可能比写入时的 now 晚不到 1 秒。
    # 0 分钟超时要立刻进入下一级，不能被这一秒挡住。
    instant = now + timedelta(seconds=1)
    for step in steps:
        if step.leave_at is None or instant < step.leave_at:
            return step
    return steps[-1]


def code_matches(tags: set[str], code: str) -> bool:
    if code == "R1":
        return is_r1(tags)
    if code == "R4":
        return is_r4(tags)
    if code == "R2":
        return "r2" in tags
    if code == "R3":
        return "r3" in tags
    if code == "R9":
        return "r9" in tags
    return False


def role_label(tags: set[str], level: int) -> str:
    if level == 1:
        return "责任人"
    if level == 2:
        return "部门负责人"
    if is_r4(tags):
        return "运营总监"
    if is_r1(tags):
        return "系统管理员"
    return "三级接收人"


def is_dept_leader(db: Session, user: User) -> bool:
    for role in enabled_roles(db, user):
        name = role.role_name or ""
        key = (role.role_key or "").lower()
        if "部门负责人" in name or key in {"dept:leader", "dept_leader"}:
            return True
    return False


def tenant_users(db: Session, tenant_id: int) -> list[User]:
    return list(
        db.scalars(
            select(User).where(
                User.deleted == 0,
                User.status == "ENABLED",
                User.tenant_id == tenant_id,
            )
        ).all()
    )


@dataclass
class Directory:
    users: list[User]
    tags: dict[int, set[str]]
    leaders: list[User]
    extras: list[User]


def directory(db: Session, tenant_id: int, cfg: Cfg) -> Directory:
    users = tenant_users(db, tenant_id)
    tags = {user.id: role_tags(db, user) for user in users}
    leaders = [user for user in users if is_dept_leader(db, user)]
    extras: list[User] = []
    if cfg.extra_user_ids:
        found = {
            user.id: user
            for user in db.scalars(
                select(User).where(User.deleted == 0, User.id.in_(list(cfg.extra_user_ids)))
            ).all()
        }
        extras = [found[item] for item in cfg.extra_user_ids if item in found]
        for user in extras:
            tags.setdefault(user.id, role_tags(db, user))
    return Directory(users=users, tags=tags, leaders=leaders, extras=extras)


def receivers_at(level: int, rule: AlertRule | None, cfg: Cfg, book: Directory) -> list[User]:
    if level == 1:
        owner_id = rule.created_by if rule is not None else 0
        return [user for user in book.users if user.id == owner_id]
    if level == 2:
        seen: dict[int, User] = {}
        for user in [*book.leaders, *book.extras]:
            seen[user.id] = user
        return list(seen.values())
    picked: list[User] = []
    for user in book.users:
        tags = book.tags.get(user.id, set())
        if any(code_matches(tags, code) for code in cfg.role_codes):
            picked.append(user)
    return picked


def person_vo(user: User, tags: set[str], level: int) -> dict:
    return {
        "userId": user.id,
        "userName": (user.nickname or user.username or "").strip() or str(user.id),
        "roleLabel": role_label(tags, level),
    }


def receiver_ids(rule: AlertRule | None, cfg: Cfg, book: Directory) -> set[int]:
    ids: set[int] = set()
    for level in (1, 2, 3):
        for user in receivers_at(level, rule, cfg, book):
            ids.add(user.id)
    return ids


def actor_may_respond(db: Session, actor: User, rule: AlertRule | None) -> bool:
    tags = role_tags(db, actor)
    if is_r1(tags) or is_r4(tags):
        return True
    if rule is not None and rule.created_by and actor.id == rule.created_by:
        return True
    tenant_id = tenant_of(actor)
    cfg = load_cfg(db, tenant_id)
    book = directory(db, tenant_id, cfg)
    return actor.id in receiver_ids(rule, cfg, book)


def was_escalated(row: AlertRecord, alert_level: int, cfg: Cfg, now: datetime) -> bool:
    if row.occurred_at is None:
        return False
    steps = build_steps(row.occurred_at, alert_level, cfg)
    if len(steps) < 2:
        return False
    instant = row.updated_at if row.response_status != 0 and row.updated_at is not None else now
    return steps[1].enter_at <= instant


def count_escalated(db: Session, tenant_id: int, rows: list[AlertRecord]) -> int:
    if not rows:
        return 0
    cfg = load_cfg(db, tenant_id)
    rule_ids = {row.rule_id for row in rows if row.rule_id}
    rules: dict[int, AlertRule] = {}
    if rule_ids:
        for rule in db.scalars(select(AlertRule).where(AlertRule.id.in_(rule_ids))).all():
            rules[rule.id] = rule
    now = utcnow()
    total = 0
    for row in rows:
        rule = rules.get(row.rule_id)
        level = rule.level if rule is not None else row.level
        if was_escalated(row, level, cfg, now):
            total += 1
    return total


def note_reached(
    db: Session,
    tenant_id: int,
    row: AlertRecord,
    steps: list[Step],
    book: Directory,
    rule: AlertRule | None,
    cfg: Cfg,
    now: datetime,
    actor: User,
) -> None:
    for step in steps:
        if step.enter_at > now:
            continue
        people = receivers_at(step.level, rule, cfg, book)
        names = "、".join(person_vo(user, book.tags.get(user.id, set()), step.level)["userName"] for user in people)
        publish_notify(
            db,
            event_type="ALERT_ESCALATE",
            biz_key=f"{row.alert_no}:L{step.level}",
            receiver=(names or LEVEL_NAME.get(step.level, "升级"))[:64],
            channel="IN_APP",
            receiver_user_id=people[0].id if people else 0,
            tenant_id=tenant_id,
            creator=actor.id,
        )


def event_vo(
    row: AlertRecord,
    rule: AlertRule | None,
    step: Step,
    people: list[User],
) -> dict:
    ids = [user.id for user in people]
    return {
        "id": row.id,
        "alertNo": row.alert_no,
        "ruleId": row.rule_id,
        "ruleCode": rule.rule_code if rule else "",
        "ruleName": rule.rule_name if rule else "",
        "sourceRefType": row.source_ref_type or "",
        "sourceRefId": str(row.source_ref_id or ""),
        "level": level_code(row.level),
        "content": row.content,
        "dedupKey": f"{rule.rule_code if rule else row.rule_id}:{row.source_ref_type}:{row.source_ref_id}",
        "mergedCount": 1,
        "notifyTargetUserIds": ids,
        "pushStatus": "DELIVERED" if row.push_status == 1 else "PENDING",
        "pushChannels": [
            {
                "channel": "WORKBENCH",
                "success": True,
                "receiptAt": iso(row.occurred_at),
            }
        ],
        "responseStatus": "OPEN",
        "occurredAt": iso(row.occurred_at),
        "currentLevel": step.level,
        "nextEscalateAt": iso(step.leave_at) if step.leave_at is not None else "",
    }


def timeline_vo(
    row: AlertRecord,
    rule: AlertRule | None,
    steps: list[Step],
    book: Directory,
    cfg: Cfg,
    now: datetime,
    response_status: str,
) -> dict:
    nodes = []
    current = current_step(steps, now)
    alert_level = rule.level if rule is not None else row.level
    if start_level(alert_level, cfg) > 1:
        nodes.append(
            {
                "escalationLevel": 1,
                "escalatedTo": [],
                "escalatedAt": "",
                "elapsedMinutes": 0,
                "skipped": True,
                "note": "跳过（严重级直接二级起跳，ALR-E-R2）",
            }
        )
    for step in steps:
        if step.enter_at > now:
            continue
        people = receivers_at(step.level, rule, cfg, book)
        elapsed = 0
        if row.occurred_at is not None:
            elapsed = int(round((step.enter_at - row.occurred_at).total_seconds() / 60.0))
        nodes.append(
            {
                "escalationLevel": step.level,
                "escalatedTo": [person_vo(user, book.tags.get(user.id, set()), step.level) for user in people],
                "escalatedAt": iso(step.enter_at),
                "elapsedMinutes": max(elapsed, 0),
                "skipped": False,
                "note": "",
            }
        )
    shown_level = current.level if response_status == "OPEN" else None
    open_next = iso(current.leave_at) if response_status == "OPEN" and current.leave_at is not None else ""
    return {
        "alertNo": row.alert_no,
        "alertLevel": level_code(alert_level),
        "occurredAt": iso(row.occurred_at),
        "timeline": nodes,
        "currentLevel": shown_level,
        "nextEscalateAt": open_next,
        "responseStatus": response_status,
        "channelStub": "钉钉/短信外发保持本地桩，未实际发送",
    }


def validate_body(db: Session, body: EscalateConfigBody, tenant_id: int):
    if body.level1TimeoutMinutes < 0 or body.level1TimeoutMinutes > 10080:
        return fail(1001, "一级升级时限须在 0～10080 分钟")
    if body.level2TimeoutMinutes < 0 or body.level2TimeoutMinutes > 10080:
        return fail(1001, "二级升级时限须在 0～10080 分钟")
    if body.severeStartLevel not in (2, 3):
        return fail(1001, "严重级起跳仅支持二级或三级")
    if body.level1Receivers.dynamicTarget != "RESPONSIBLE_PERSON":
        return fail(1001, "一级接收人须为责任人")
    if body.level2Receivers.dynamicTarget != "DEPT_LEADER":
        return fail(1001, "二级接收人须为部门负责人")
    codes = [code.strip().upper() for code in body.level3Receivers.roleCodes if code and code.strip()]
    if not codes:
        codes = ["R4", "R1"]
    if any(code not in ROLE_CODES for code in codes):
        return fail(1001, "三级角色仅支持 R1/R2/R3/R4/R9")
    extra = []
    for user_id in body.level2Receivers.extraUserIds:
        user = db.get(User, user_id)
        if user is None or user.deleted or (user.tenant_id or 0) != tenant_id:
            return fail(1001, "二级额外接收人不存在")
        extra.append(user_id)
    return codes, extra


@router.put("/escalate/config")
def save_config(
    body: EscalateConfigBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not is_r1(role_tags(db, actor)):
        return fail(1008, "仅系统管理员可配置升级链路")
    tenant_id = tenant_of(actor)
    checked = validate_body(db, body, tenant_id)
    if not isinstance(checked, tuple):
        return checked
    codes, extra = checked
    row = db.scalar(
        select(AlertEscalateConfig).where(
            AlertEscalateConfig.deleted == 0,
            AlertEscalateConfig.tenant_id == tenant_id,
        )
    )
    now = utcnow()
    if row is None:
        row = AlertEscalateConfig(tenant_id=tenant_id, created_at=now)
        db.add(row)
    row.level1_minutes = body.level1TimeoutMinutes
    row.level2_minutes = body.level2TimeoutMinutes
    row.severe_start_level = body.severeStartLevel
    row.level2_extra_ids = ",".join(str(item) for item in extra)
    row.level3_role_codes = ",".join(codes)
    row.updated_at = now
    db.flush()
    return ok(None)


def open_rows(db: Session, tenant_id: int) -> list[AlertRecord]:
    return list(
        db.scalars(
            select(AlertRecord).where(
                AlertRecord.deleted == 0,
                AlertRecord.tenant_id == tenant_id,
                AlertRecord.response_status == 0,
            )
        ).all()
    )


def load_rules(db: Session, rows: list[AlertRecord]) -> dict[int, AlertRule]:
    rule_ids = {row.rule_id for row in rows if row.rule_id}
    if not rule_ids:
        return {}
    return {rule.id: rule for rule in db.scalars(select(AlertRule).where(AlertRule.id.in_(rule_ids))).all()}


@router.get("/escalate/pending")
def pending(
    currentLevel: int | None = None,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tags = role_tags(db, actor)
    if not (is_r1(tags) or is_r4(tags)):
        return fail(1008, "仅管理员与运营总监可查看待升级预警")
    if currentLevel is not None and currentLevel not in (1, 2, 3):
        return fail(1001, "currentLevel 无效")
    tenant_id = tenant_of(actor)
    cfg = load_cfg(db, tenant_id)
    book = directory(db, tenant_id, cfg)
    now = utcnow()
    rows = open_rows(db, tenant_id)
    rules = load_rules(db, rows)
    matched: list[dict] = []
    for row in rows:
        if row.occurred_at is None:
            continue
        rule = rules.get(row.rule_id)
        level = rule.level if rule is not None else row.level
        steps = build_steps(row.occurred_at, level, cfg)
        step = current_step(steps, now)
        if currentLevel is not None and step.level != currentLevel:
            continue
        note_reached(db, tenant_id, row, steps, book, rule, cfg, now, actor)
        people = receivers_at(step.level, rule, cfg, book)
        matched.append((row.occurred_at, row.id, event_vo(row, rule, step, people)))
    matched.sort(key=lambda item: (item[0], item[1]), reverse=True)
    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    page = [item[2] for item in matched[start : start + size]]
    return paged(page, len(matched), page_no, size)


def status_label(code: int) -> str:
    return {0: "OPEN", 1: "CONFIRMED", 2: "RESOLVED", 3: "FALSE_ALARM"}.get(code, "OPEN")


@router.get("/escalate/timeline/{alert_no}")
def timeline(
    alert_no: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(AlertRecord).where(
            AlertRecord.deleted == 0,
            AlertRecord.tenant_id == tenant_id,
            AlertRecord.alert_no == alert_no,
        )
    )
    if row is None or row.occurred_at is None:
        return fail(1500, "预警不存在")
    rule = db.get(AlertRule, row.rule_id) if row.rule_id else None
    cfg = load_cfg(db, tenant_id)
    book = directory(db, tenant_id, cfg)
    tags = role_tags(db, actor)
    allowed = is_r1(tags) or is_r4(tags) or actor.id in receiver_ids(rule, cfg, book)
    if not allowed:
        return fail(1008, "仅升级链路接收人与管理员可查看")
    level = rule.level if rule is not None else row.level
    steps = build_steps(row.occurred_at, level, cfg)
    now = utcnow()
    if row.response_status == 0:
        note_reached(db, tenant_id, row, steps, book, rule, cfg, now, actor)
    return ok(timeline_vo(row, rule, steps, book, cfg, now, status_label(row.response_status)))
