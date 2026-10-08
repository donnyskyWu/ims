import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ACCESS_MINUTES, JWT_SECRET, REFRESH_DAYS, utcnow
from app.models import AuthSession, LoginGuard, User


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(check, digest)


def encode(user_id: int, session_id: int, kind: str, minutes: int) -> str:
    payload = {
        "uid": user_id,
        "sid": session_id,
        "kind": kind,
        "exp": utcnow() + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


def issue_tokens(db: Session, user: User) -> dict:
    active = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked == 0).order_by(AuthSession.id)
    ).all()
    if len(active) >= 3:
        active[0].revoked = 1
    row = AuthSession(user_id=user.id, refresh_token="")
    db.add(row)
    db.flush()
    access = encode(user.id, row.id, "access", ACCESS_MINUTES)
    refresh = encode(user.id, row.id, "refresh", REFRESH_DAYS * 24 * 60)
    row.refresh_token = refresh
    return {
        "accessToken": access,
        "refreshToken": refresh,
        "profile": {"userId": str(user.id), "nickname": user.nickname, "username": user.username},
    }


def locked(db: Session, username: str) -> bool:
    row = db.get(LoginGuard, username)
    if row is None or row.locked_until is None:
        return False
    if row.locked_until > utcnow():
        return True
    row.fail_count = 0
    row.locked_until = None
    return False


def mark_fail(db: Session, username: str) -> None:
    row = db.get(LoginGuard, username)
    if row is None:
        row = LoginGuard(username=username, fail_count=0)
        db.add(row)
    row.fail_count += 1
    if row.fail_count >= 5:
        row.locked_until = utcnow() + timedelta(minutes=15)


def mark_ok(db: Session, username: str) -> None:
    row = db.get(LoginGuard, username)
    if row:
        row.fail_count = 0
        row.locked_until = None
