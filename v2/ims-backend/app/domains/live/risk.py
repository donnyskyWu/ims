"""五项风控。证件或账号直接 100 分即红；阈值 40 / 70。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.clock import today
from app.db.session import get_session
from app.domains.cert.expire import is_locked
from app.domains.cert.support import LONG_TERM
from app.domains.master.model import Cert

ITEMS = ("CERT_VALID", "ACCOUNT_STATUS", "BALANCE", "BLACKLIST", "DEVICE_OWNER")
LABELS = {
    "CERT_VALID": "证件有效性",
    "ACCOUNT_STATUS": "账号状态",
    "BALANCE": "话费余额",
    "BLACKLIST": "黑名单词",
    "DEVICE_OWNER": "设备归属",
}


def level_of(score: int) -> str:
    if score >= 70:
        return "RED"
    if score >= 40:
        return "YELLOW"
    return "GREEN"


def level_label(level: str | None) -> str:
    return {"GREEN": "绿", "YELLOW": "黄", "RED": "红"}.get(level or "", "补录" if level in (None, "") else level or "")


def result_of(score: int) -> str:
    if score >= 40:
        return "FAIL" if score >= 40 and score != 20 and score != 10 else "WARN"
    if score > 0:
        return "WARN"
    return "PASS"


def judge(score: int) -> str:
    """单项：40 及以上为未通过，大于 0 为警告，否则通过。直接 100 分也是未通过。"""
    if score >= 40:
        return "FAIL"
    if score > 0:
        return "WARN"
    return "PASS"


def latest_cert(realname_id: int) -> Cert | None:
    rows = list(
        get_session().scalars(
            select(Cert).where(Cert.realname_id == int(realname_id)).order_by(Cert.id.desc())
        )
    )
    return rows[0] if rows else None


def cert_fact(realname_id: int) -> dict:
    """证件预检。过期、锁定、未建档都可提交，只给出红字。"""
    cert = latest_cert(realname_id)
    if cert is None:
        return {"tone": "danger", "message": "该实名人未建证件档案", "score": 100, "code": 1045, "expireDate": ""}
    expire = cert.expire_date
    locked = is_locked(realname_id) or cert.status == "EXPIRED"
    if locked or (expire and expire != LONG_TERM and expire < today()):
        shown = expire.isoformat() if isinstance(expire, date) else ""
        return {
            "tone": "danger",
            "message": f"证件已过期（{shown}），可提交但风控将判红，请先到证件管理换证",
            "score": 100,
            "code": 1045,
            "expireDate": shown,
        }
    if expire and expire != LONG_TERM:
        days = (expire - today()).days
        if days <= 7:
            return {"tone": "danger", "message": f"证件 {days} 天后到期", "score": 20, "code": None, "expireDate": expire.isoformat()}
        if days <= 30:
            return {"tone": "warning", "message": f"证件 {days} 天后到期", "score": 10, "code": None, "expireDate": expire.isoformat()}
    return {"tone": "", "message": "", "score": 0, "code": None, "expireDate": expire.isoformat() if expire else ""}
