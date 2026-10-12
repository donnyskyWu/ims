"""账号登录、锁定、改密、钉钉 SSO。"""
from __future__ import annotations

import json
import math
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import now, now_naive
from app.core.crypto import hmac_hash
from app.core.errors import BizError
from app.core.redis_client import get_redis
from app.core.security import hash_password, validate_password_policy, verify_password
from app.db.session import get_session
from app.domains.auth.model import UserMapping
from app.domains.system.model import LoginLog, User
from app.services.sessions import assert_tenant_open, issue_session, revoke_sid, revoke_user, rotate_refresh

LOCK_SECONDS = 15 * 60


def _state_key(username: str) -> str:
    return f"ims:login:fail:{username}"


def _read_state(username: str) -> dict | None:
    raw = get_redis().get(_state_key(username))
    return json.loads(raw) if raw else None


def _write_state(username: str, state: dict) -> None:
    get_redis().set(_state_key(username), json.dumps(state), ex=LOCK_SECONDS + 60)


def _clear_state(username: str) -> None:
    get_redis().delete(_state_key(username))


def _remain(first_iso: str) -> int:
    from datetime import datetime

    first = datetime.fromisoformat(first_iso)
    until = first + timedelta(seconds=LOCK_SECONDS)
    seconds = (until - now_naive()).total_seconds()
    if seconds <= 0:
        return 0
    return int(math.ceil(seconds / 60))


def _raise_if_locked(username: str) -> None:
    state = _read_state(username)
    if not state or int(state.get("count") or 0) < 5:
        return
    remain = _remain(state["first"])
    if remain <= 0:
        _clear_state(username)
        return
    _log(username, None, "LOCKED", fail_code=1215)
    raise BizError(1215, n=remain, data={"remainMinutes": remain})


def _record_failure(username: str) -> None:
    state = _read_state(username) or {"count": 0, "first": now_naive().isoformat(timespec="seconds")}
    first = state["first"]
    from datetime import datetime

    if (now_naive() - datetime.fromisoformat(first)).total_seconds() > LOCK_SECONDS:
        state = {"count": 0, "first": now_naive().isoformat(timespec="seconds")}
    state["count"] = int(state["count"]) + 1
    if state["count"] == 1:
        state["first"] = now_naive().isoformat(timespec="seconds")
    _write_state(username, state)
    if state["count"] >= 5:
        remain = _remain(state["first"])
        raise BizError(1215, n=remain, data={"remainMinutes": remain})
    raise BizError(1214)


def _log(username: str, user_id: int | None, result: str, login_type: str = "PASSWORD", channel: str | None = None, fail_code: int | None = None) -> None:
    """登录结果单独提交。失败请求会回滚业务事务，审计不能跟着丢掉。"""
    from app.core.context import get_ctx
    from app.db.session import session_scope

    ctx = get_ctx()
    row = LoginLog(
        username=username,
        user_id=user_id,
        login_type=login_type,
        result=result,
        ip=ctx.client_ip if ctx else "",
        tenant_id=ctx.tenant_id if ctx and ctx.tenant_id else 1,
        channel=channel or ("DINGTALK_QR" if login_type == "DINGTALK" else "PASSWORD"),
        fail_code=fail_code,
    )
    with session_scope(commit=True) as session:
        session.add(row)


def login(username: str, password: str) -> dict:
    _raise_if_locked(username)
    session = get_session()
    user = session.scalar(select(User).where(User.username == username).execution_options(skip_tenant=True))
    if user is None or not verify_password(password, user.password_hash):
        _log(username, user.id if user else None, "BAD_CREDENTIAL", fail_code=1214)
        _record_failure(username)
    if user.status in {"FROZEN", "RESIGNED"}:
        _log(username, user.id, "DISABLED", fail_code=1216)
        raise BizError(1216)  # 不签发任何会话，包括工作台
    try:
        assert_tenant_open(user.tenant_id)
    except BizError as exc:
        _log(username, user.id, "DISABLED", fail_code=exc.code)
        raise
    _clear_state(username)
    user.last_login_time = now_naive()
    from app.core.context import get_ctx

    ctx = get_ctx()
    user.last_login_ip = ctx.client_ip if ctx else ""
    _log(username, user.id, "SUCCESS", channel="PASSWORD")
    return issue_session(user)


def refresh(token: str) -> dict:
    return rotate_refresh(token)


def logout(user_id: int, sid: str, username: str) -> dict:
    revoke_sid(user_id, sid)
    _log(username, user_id, "LOGOUT")
    return {}


def change_password(user_id: int, sid: str, old_password: str, new_password: str) -> dict:
    user = get_session().get(User, user_id)
    if user is None:
        raise BizError(1504)
    if not verify_password(old_password, user.password_hash):
        raise BizError(1214)
    if old_password == new_password:
        raise BizError(1001, data={"fieldErrors": [{"field": "newPassword", "message": "新密码不能与原密码相同"}]})
    policy = validate_password_policy(new_password)
    if policy:
        raise BizError(1001, data={"fieldErrors": [{"field": "newPassword", "message": policy}]})
    user.password_hash = hash_password(new_password)
    user.pwd_reset_required = 0
    revoke_user(user_id, except_sid=sid)
    return {}


def reset_password(user_id: int) -> dict:
    from app.core.security import random_password

    user = get_session().get(User, user_id)
    if user is None:
        raise BizError(1504)
    plain = random_password()
    user.password_hash = hash_password(plain)
    user.pwd_reset_required = 1
    revoke_user(user_id)
    return {"password": plain}


def unlock(username: str) -> dict:
    _clear_state(username)
    return {}


def kick(user_id: int) -> None:
    revoke_user(user_id)


def resolve_ding_user(profile: dict, channel: str) -> User:
    """扫码和免登共用：映射、手机号、首登即时同步，再校验能否登录。"""
    userid = str(profile.get("userid") or "")
    session = get_session()
    mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == userid).execution_options(skip_tenant=True))
    user = session.get(User, mapping.user_id) if mapping else None
    if user is None and profile.get("mobile"):
        user = find_by_mobile_hash(str(profile["mobile"]), 1)
        if user is not None:
            session.add(UserMapping(user_id=user.id, dingtalk_user_id=userid, tenant_id=user.tenant_id))
            session.flush()
    if user is None:
        user = _login_sync(userid, channel)
    if user is None:
        _log(userid or "", None, "UNMAPPED", "DINGTALK", channel=channel, fail_code=1217)
        raise BizError(1217)
    if user.status in {"FROZEN", "RESIGNED"}:
        _log(user.username, user.id, "DISABLED", "DINGTALK", channel=channel, fail_code=1216)
        raise BizError(1216)
    try:
        assert_tenant_open(user.tenant_id)
    except BizError as exc:
        _log(user.username, user.id, "DISABLED", "DINGTALK", channel=channel, fail_code=exc.code)
        raise
    _log(user.username, user.id, "SUCCESS", "DINGTALK", channel=channel)
    return user


def _login_sync(userid: str, channel: str) -> User | None:
    from app.integrations.dingtalk.client import fetch_user
    from app.services.org_sync import process_event

    if not userid:
        return None
    today = now_naive().strftime("%Y%m%d")
    event_id = f"login-sync:{userid}:{today}"
    detail = fetch_user(userid)
    if detail is None:
        return None
    dept_ids = detail.get("deptIds") or detail.get("dept_ids") or []
    body = {
        "eventId": event_id,
        "eventType": "user_add",
        "eventTime": now_naive().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "dingtalkUserId": userid,
        "nickname": detail.get("name") or detail.get("nickname") or userid,
        "mobile": detail.get("mobile"),
        "deptIds": dept_ids,
        "empNo": detail.get("job_number") or detail.get("jobNumber") or detail.get("empNo"),
        "positionCode": detail.get("title") or detail.get("positionCode"),
    }
    process_event(body)
    session = get_session()
    mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == userid).execution_options(skip_tenant=True))
    if mapping is None:
        return None
    return session.get(User, mapping.user_id)


def find_by_mobile_hash(mobile: str, tenant_id: int) -> User | None:
    digest = hmac_hash(mobile)
    return get_session().scalar(
        select(User).where(User.mobile_hash == digest, User.tenant_id == tenant_id).execution_options(skip_tenant=True)
    )
