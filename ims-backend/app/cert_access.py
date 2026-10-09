"""CERT-001 数字化率与原图签名链接，CERT-003 查看级别。

GET /cert/archive/digital-metrics：未回收档案里，已审核且有扫描件的占比（BR-005，目标 > 95%）。
GET /cert/archive/{id}/file-url：60 秒水印代理。待审 1033，级别不足 1034。成功计入查看频次。
GET /cert/archive/file：凭 token 取预览。过期 1002，他人 1008。不提供下载。
PUT /cert/security/level-config：R1 配置角色 L1/L2 与 L3 白名单。
GET /cert/security/level-config：同一配置的读取，供证件页回显。
"""

import json
import secrets
import threading
import time

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.cert_view import can_cert_r1, enforce_view_frequency, record_cert_view
from app.core import utcnow
from app.corp import tenant_of, visible
from app.models import CertArchive, CertWatermarkConfig, User
from app.scope import enabled_roles

router = APIRouter()

TTL_SEC = 60
EXPECTED_STATUS = ("PENDING_REVIEW", "EFFECTIVE", "EXPIRING", "EXPIRED")
DIGITAL_STATUS = ("EFFECTIVE", "EXPIRING", "EXPIRED")
TARGETS = frozenset({"ROLE", "POSITION_TEMPLATE"})
POSITIONS = frozenset(
    {"center", "top-left", "top-right", "bottom-left", "bottom-right", "top", "bottom", "left", "right"}
)
TICKETS: dict[str, dict] = {}
_LOCK = threading.Lock()


class LevelRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    target: str
    targetCode: str
    viewLevel: int


class LevelConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    rules: list[LevelRule]
    l3Whitelist: list[int]
    opacity: float | None = None
    position: str | None = None


def parse_json(raw: str, fallback):
    try:
        return json.loads(raw or "")
    except (TypeError, ValueError):
        return fallback


def load_config(db: Session, tenant: int) -> CertWatermarkConfig | None:
    return db.scalar(
        select(CertWatermarkConfig).where(
            CertWatermarkConfig.deleted == 0,
            CertWatermarkConfig.tenant_id == tenant,
        )
    )


def config_rules(row: CertWatermarkConfig | None) -> list[dict]:
    if row is None:
        return []
    parsed = parse_json(row.rules_json, [])
    return parsed if isinstance(parsed, list) else []


def config_whitelist(row: CertWatermarkConfig | None) -> list[int]:
    if row is None:
        return []
    parsed = parse_json(row.whitelist_json, [])
    if not isinstance(parsed, list):
        return []
    ids: list[int] = []
    for item in parsed:
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            ids.append(int(item))
    return ids


def config_vo(row: CertWatermarkConfig | None) -> dict:
    return {
        "rules": config_rules(row),
        "l3Whitelist": config_whitelist(row),
        "permLevel": 1 if row is None else int(row.perm_level or 1),
        "opacity": 0.12 if row is None else float(row.opacity or 0.12),
        "position": "bottom-right" if row is None else (row.position or "bottom-right"),
        "watermarkText": "" if row is None else (row.watermark_text or ""),
    }


def actor_codes(db: Session, actor: User) -> set[str]:
    codes: set[str] = set()
    for role in enabled_roles(db, actor):
        if role.role_key:
            codes.add(role.role_key)
        if role.role_name:
            codes.add(role.role_name)
        if role.dingtalk_position:
            codes.add(role.dingtalk_position)
    return codes


def view_level_of(db: Session, actor: User) -> int:
    row = load_config(db, tenant_of(actor))
    level = 1
    codes = actor_codes(db, actor)
    for rule in config_rules(row):
        code = str(rule.get("targetCode") or "")
        try:
            granted = int(rule.get("viewLevel") or 1)
        except (TypeError, ValueError):
            granted = 1
        if code and code in codes:
            level = max(level, granted)
    if actor.id in config_whitelist(row):
        level = 3
    return level


def whitelist_user(db: Session, actor: User, user_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None or user.deleted or (user.tenant_id or 0) != tenant_of(actor):
        return None
    if can_cert_r1(db, user):
        return user
    if any("行政" in (role.role_name or "") for role in enabled_roles(db, user)):
        return user
    return None


def watermark_of(actor: User, opacity: float, position: str) -> dict:
    tail = (actor.mobile or "")[-4:]
    name = (actor.nickname or actor.username or "").strip()
    stamp = utcnow().isoformat(sep=" ", timespec="seconds")
    text = " ".join(part for part in (name, tail, stamp) if part)
    return {"text": text, "opacity": opacity, "position": position}


def purge_tickets(now: float) -> None:
    dead = [key for key, item in TICKETS.items() if float(item["exp"]) < now]
    for key in dead:
        TICKETS.pop(key, None)


def issue_ticket(actor: User, level: int, watermark: dict | None, file_key: str) -> str:
    now = time.time()
    with _LOCK:
        purge_tickets(now)
        token = secrets.token_urlsafe(24)
        TICKETS[token] = {
            "exp": now + TTL_SEC,
            "user_id": actor.id,
            "view_level": level,
            "watermark": watermark,
            "file_key": file_key if level >= 3 else "",
            "preview": "明文预览，禁止下载" if level >= 3 else "水印预览，禁止下载",
        }
    return token


@router.get("/cert/archive/digital-metrics")
def digital_metrics(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant = tenant_of(actor)
    base = (CertArchive.deleted == 0, CertArchive.tenant_id == tenant, CertArchive.status.in_(EXPECTED_STATUS))
    total = int(
        db.scalar(select(func.count()).select_from(CertArchive).where(*base))
        or 0
    )
    digital = int(
        db.scalar(
            select(func.count())
            .select_from(CertArchive)
            .where(*base, CertArchive.status.in_(DIGITAL_STATUS), CertArchive.file_key != "")
        )
        or 0
    )
    rate = 1.0 if total == 0 else round(digital / total, 4)
    return ok({"totalExpected": total, "digitalizedCount": digital, "digitalizedRate": rate})


@router.get("/cert/archive/{cert_id}/file-url")
def archive_file_url(
    cert_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(CertArchive, cert_id)
    if not visible(row, actor):
        return fail(1031, "证件档案不存在")
    if row.status == "PENDING_REVIEW":
        return fail(1033, "1033 待审状态不可查看原图")
    blocked = enforce_view_frequency(db, actor, row)
    if blocked is not None:
        return blocked
    level = view_level_of(db, actor)
    if level < 2:
        return fail(1034, "1034 访问级别不足")
    cfg = load_config(db, tenant_of(actor))
    style = config_vo(cfg)
    watermark = None
    watermark_text = ""
    if level == 2:
        watermark = watermark_of(actor, float(style["opacity"]), str(style["position"]))
        watermark_text = str(watermark["text"])
    token = issue_ticket(actor, level, watermark, row.file_key or "")
    record_cert_view(db, actor, row, watermark_text, request, view_level=level)
    data: dict = {
        "signedUrl": f"/admin-api/ims/cert/archive/file?token={token}",
        "expiresInSeconds": TTL_SEC,
    }
    if watermark is not None:
        data["watermark"] = watermark
    return ok(data)


@router.get("/cert/archive/file")
def archive_file(token: str = "", db: Session = Depends(db_session), actor: User = Depends(current_user)):
    now = time.time()
    with _LOCK:
        purge_tickets(now)
        item = TICKETS.get((token or "").strip())
    if item is None or float(item["exp"]) < now:
        return fail(1002, "签名链接已过期")
    if int(item["user_id"]) != actor.id:
        return fail(1008, "无数据权限")
    payload = {
        "viewLevel": int(item["view_level"]),
        "preview": item["preview"],
        "download": False,
        "expiresInSeconds": max(0, int(float(item["exp"]) - now)),
    }
    if item.get("watermark"):
        payload["watermark"] = item["watermark"]
    if int(item["view_level"]) >= 3 and item.get("file_key"):
        payload["fileKey"] = item["file_key"]
    return ok(payload)


@router.get("/cert/security/level-config")
def level_config_get(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    if not can_cert_r1(db, actor):
        return fail(1008, "权限不足")
    return ok(config_vo(load_config(db, tenant_of(actor))))


@router.put("/cert/security/level-config")
def level_config_put(
    body: LevelConfigBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_cert_r1(db, actor):
        return fail(1008, "权限不足")
    seen: set[tuple[str, str]] = set()
    rules: list[dict] = []
    for rule in body.rules:
        target = (rule.target or "").strip()
        code = (rule.targetCode or "").strip()
        if target not in TARGETS:
            return fail(1001, "级别适用范围不合法")
        if not code:
            return fail(1001, "角色或岗位编码必填")
        if rule.viewLevel not in (1, 2):
            return fail(1001, "L3 只能通过白名单配置")
        key = (target, code)
        if key in seen:
            return fail(1001, "级别规则重复")
        seen.add(key)
        rules.append({"target": target, "targetCode": code, "viewLevel": rule.viewLevel})
    whitelist: list[int] = []
    for user_id in body.l3Whitelist:
        if whitelist_user(db, actor, int(user_id)) is None:
            found = db.get(User, int(user_id))
            if found is None or found.deleted or (found.tenant_id or 0) != tenant_of(actor):
                return fail(1500, "白名单用户不存在")
            return fail(1001, "白名单仅限管理员或行政角色")
        if int(user_id) not in whitelist:
            whitelist.append(int(user_id))
    row = load_config(db, tenant_of(actor))
    opacity = float(row.opacity) if row is not None else 0.12
    position = row.position if row is not None else "bottom-right"
    if body.opacity is not None:
        if body.opacity < 0.05 or body.opacity > 0.3:
            return fail(1001, "水印透明度须在 0.05 到 0.3")
        opacity = float(body.opacity)
    if body.position is not None:
        place = body.position.strip()
        if place not in POSITIONS:
            return fail(1001, "水印位置不合法")
        position = place
    now = utcnow()
    if row is None:
        row = CertWatermarkConfig(
            rules_json="[]",
            whitelist_json="[]",
            perm_level=1,
            watermark_text="",
            opacity=opacity,
            position=position,
            creator=actor.id,
            updater=actor.id,
            deleted=0,
            tenant_id=tenant_of(actor),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    row.rules_json = json.dumps(rules, ensure_ascii=False)
    row.whitelist_json = json.dumps(whitelist)
    row.perm_level = 1
    row.opacity = opacity
    row.position = position
    row.updater = actor.id
    row.updated_at = now
    db.flush()
    return ok(None)
