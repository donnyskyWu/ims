import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import SessionLocal, mask_mobile, utcnow
from app.models import AuthSession, SsoState, User
from app.security import decode, hash_password, issue_tokens, locked, mark_fail, mark_ok, verify_password

router = APIRouter()


def ok(data=None):
    return {"code": 0, "msg": "ok", "data": data}


def fail(code: int, msg: str, data=None):
    http = 200
    if code in (401, 1002):
        http = 401
    elif code in (403, 1008, 1504):
        http = 403
    return JSONResponse(status_code=http, content={"code": code, "msg": msg, "data": data})


def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError(401, "未登录")
    try:
        payload = decode(authorization[7:])
    except Exception as exc:
        raise AuthError(1002, "会话无效") from exc
    if payload.get("kind") != "access":
        raise AuthError(1002, "会话无效")
    session = db.get(AuthSession, payload["sid"])
    if session is None or session.revoked:
        raise AuthError(1002, "会话无效")
    user = db.get(User, payload["uid"])
    if user is None or user.deleted or user.status != "ENABLED":
        raise AuthError(1006, "用户不可登录")
    request.state.operator_id = user.id
    request.state.operator_name = user.nickname or user.username
    request.state.tenant_id = user.tenant_id or 0
    from app.scope import gate

    gate(db, request, user)
    return user


class AuthError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg


class LoginBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: str


class CallbackBody(BaseModel):
    authCode: str
    state: str


class RefreshBody(BaseModel):
    refreshToken: str


class UserBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str | None = None
    nickname: str | None = None
    mobile: str | None = None
    password: str | None = None
    status: str | None = None
    dingtalkUserId: str | None = None
    userId: int | None = None


def user_vo(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "nickname": user.nickname,
        "mobile": mask_mobile(user.mobile),
        "status": user.status,
        "dingtalkUserId": user.dingtalk_user_id,
    }


@router.get("/health")
def health():
    return ok({"status": "up"})


@router.post("/auth/login")
def login(body: LoginBody, db: Session = Depends(db_session)):
    from app.audit import write_login_log

    def record(success: bool, code: int, message: str, user: User | None = None) -> None:
        write_login_log(
            db,
            username=body.username,
            user_id=user.id if user else None,
            success=success,
            result_code=code,
            message=message,
            login_type="PASSWORD",
            path="POST /auth/login",
            tenant_id=(user.tenant_id if user else 0) or 0,
        )

    if locked(db, body.username):
        record(False, 1001, "登录已锁定")
        return fail(1001, "登录已锁定，请 15 分钟后再试")
    user = db.scalar(select(User).where(User.username == body.username, User.deleted == 0))
    if user is None or user.status != "ENABLED" or not verify_password(body.password, user.password_hash):
        mark_fail(db, body.username)
        record(False, 1006, "用户名或密码错误", user if user and user.status == "ENABLED" else None)
        return fail(1006, "用户名或密码错误")
    if not user.mobile:
        record(False, 1006, "未绑定手机", user)
        return fail(1006, "未绑定手机")
    mark_ok(db, body.username)
    record(True, 0, "登录成功", user)
    return ok(issue_tokens(db, user))


@router.get("/auth/sso/redirect")
def sso_redirect(db: Session = Depends(db_session)):
    state = secrets.token_urlsafe(18)
    db.add(SsoState(state=state, expire_at=utcnow() + timedelta(minutes=5)))
    return ok({"authorizeUrl": "/login", "state": state})


@router.post("/auth/sso/callback")
def sso_callback(body: CallbackBody, db: Session = Depends(db_session)):
    from app.audit import write_login_log

    def record(success: bool, code: int, message: str, user: User | None = None) -> None:
        write_login_log(
            db,
            username=user.username if user else "",
            user_id=user.id if user else None,
            success=success,
            result_code=code,
            message=message,
            login_type="SSO",
            path="POST /auth/sso/callback",
            tenant_id=(user.tenant_id if user else 0) or 0,
        )

    state = db.get(SsoState, body.state)
    if state is None or state.expire_at < utcnow():
        record(False, 1002, "state 无效")
        return fail(1002, "state 无效")
    db.delete(state)
    if body.authCode in ("nophone", "frozen", "bad"):
        record(False, 1006, "钉钉用户未绑定可用手机或未导入")
        return fail(1006, "钉钉用户未绑定可用手机或未导入")
    user = db.scalar(select(User).where(User.mobile == body.authCode, User.deleted == 0, User.status == "ENABLED"))
    if user is None or not user.mobile:
        record(False, 1006, "手机号未命中本地用户")
        return fail(1006, "手机号未命中本地用户")
    record(True, 0, "登录成功", user)
    return ok(issue_tokens(db, user))


@router.post("/auth/sso/refresh")
def refresh(body: RefreshBody, db: Session = Depends(db_session)):
    try:
        payload = decode(body.refreshToken)
    except Exception:
        return fail(1002, "会话无效")
    session = db.get(AuthSession, payload.get("sid"))
    if session is None or session.revoked or session.refresh_token != body.refreshToken:
        return fail(1002, "会话无效")
    user = db.get(User, session.user_id)
    if user is None or user.status != "ENABLED":
        return fail(1006, "用户不可登录")
    return ok(issue_tokens(db, user))


@router.post("/auth/sso/logout")
def logout(body: RefreshBody, db: Session = Depends(db_session)):
    try:
        payload = decode(body.refreshToken)
        session = db.get(AuthSession, payload.get("sid"))
        if session:
            session.revoked = 1
    except Exception:
        pass
    return ok({})


@router.get("/system/user/page")
def user_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    username: str = "",
    mobile: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.scope import restrict_users

    page_no = pageNo if pageNo > 0 else 1
    size = pageSize if 0 < pageSize <= 100 else 10
    stmt = restrict_users(select(User).where(User.deleted == 0), actor, request.state.scope)
    if username:
        stmt = stmt.where(User.username.like(f"%{username}%"))
    if mobile:
        stmt = stmt.where(User.mobile.like(f"%{mobile}%"))
    if status:
        stmt = stmt.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.id).offset((page_no - 1) * size).limit(size)).all()
    return ok({"list": [user_vo(row) for row in rows], "total": total, "pageNo": page_no, "pageSize": size})


@router.post("/system/user")
def user_create(body: UserBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    if not body.username or not body.password:
        return fail(1001, "用户名和密码必填")
    exists = db.scalar(select(User).where(or_(User.username == body.username, User.mobile == (body.mobile or ""))))
    if body.mobile and exists:
        return fail(1001, "用户名或手机号已存在")
    if db.scalar(select(User).where(User.username == body.username)):
        return fail(1001, "用户名或手机号已存在")
    user = User(
        username=body.username,
        nickname=body.nickname or body.username,
        mobile=body.mobile or "",
        password_hash=hash_password(body.password),
        status=body.status or "ENABLED",
        dingtalk_user_id=body.dingtalkUserId or "",
        tenant_id=actor.tenant_id or 0,
    )
    db.add(user)
    db.flush()
    return ok(user_vo(user))


@router.put("/system/user/{user_id}")
def user_update(request: Request, user_id: int, body: UserBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    from app.scope import user_visible

    if body.userId is not None and body.userId != user_id:
        return fail(1211, "禁止修改用户主键")
    user = db.get(User, user_id)
    if user is None or user.deleted or not user_visible(db, actor, request.state.scope, user):
        return fail(1504, "资源不可用")
    if body.nickname is not None:
        user.nickname = body.nickname
    if body.mobile is not None:
        user.mobile = body.mobile
    if body.status is not None:
        user.status = body.status
    if body.dingtalkUserId is not None:
        user.dingtalk_user_id = body.dingtalkUserId
    if body.password:
        user.password_hash = hash_password(body.password)
    return ok(user_vo(user))


from app.account import router as account_router
from app.ip_group import router as ip_group_router
from app.audit import router as audit_router
from app.corp import router as corp_router
from app.device import router as device_router
from app.asset_ledger import router as asset_ledger_router
from app.asset_purchase import router as asset_purchase_router
from app.asset_penetrate import router as asset_penetrate_router
from app.asset_export import router as asset_export_router
from app.asset_verify import router as asset_verify_router
from app.content import router as content_router
from app.content_fb import router as content_fb_router
from app.content_production import router as content_production_router
from app.content_task import router as content_task_router
from app.work_task import router as work_task_router
from app.collect import router as collect_router
from app.home import router as home_router
from app.bi_query import router as bi_query_router
from app.int_analysis import router as int_analysis_router
from app.comp_analysis import router as comp_analysis_router
from app.comp_asset import router as comp_asset_router
from app.monitor import router as monitor_router
from app.meet import router as meet_router
from app.report import router as report_router
from app.train import router as train_router
from app.air import router as air_router
from app.fin import router as fin_router
from app.fin_dashboard import router as fin_dashboard_router
from app.fin_share_rule import router as fin_share_rule_router
from app.dc_profit_trace import router as dc_profit_trace_router
from app.dc_trace import router as dc_trace_router
from app.perf import router as perf_router
from app.perf_calc import router as perf_calc_router
from app.alert import router as alert_router
from app.content_layout import router as content_layout_router
from app.eff import router as eff_router
from app.bi_report import router as bi_report_router
from app.bi_metric import router as bi_metric_router
from app.air_skill import router as air_skill_router
from app.air_expert import router as air_expert_router
from app.air_cfg import router as air_cfg_router
from app.air_key import router as air_key_router
from app.air_mcp_log import router as air_mcp_log_router
from app.query_tool import router as query_tool_router
from app.bi_subscribe import router as bi_subscribe_router
from app.flow import router as flow_router
from app.bi_screen import router as bi_screen_router
from app.master_data import router as master_data_router
from app.cost import router as cost_router
from app.live import router as live_router
from app.org_sync import router as org_router
from app.position_rule import router as position_router
from app.system_dict import router as dict_router
from app.system_role import router as role_router
from app.workbench import router as workbench_router
from app.acct_flow import router as acct_flow_router
from app.cert_expire import router as cert_expire_router
from app.cert_security import router as cert_security_router

router.include_router(role_router)
router.include_router(dict_router)
router.include_router(org_router)
router.include_router(position_router)
router.include_router(workbench_router)
router.include_router(audit_router)
router.include_router(corp_router)
router.include_router(account_router)
router.include_router(acct_flow_router)
router.include_router(ip_group_router)
router.include_router(device_router)
router.include_router(asset_ledger_router)
router.include_router(asset_purchase_router)
router.include_router(asset_penetrate_router)
router.include_router(asset_export_router)
router.include_router(asset_verify_router)
router.include_router(live_router)
router.include_router(content_router)
router.include_router(content_fb_router)
router.include_router(content_production_router)
router.include_router(content_task_router)
router.include_router(work_task_router)
router.include_router(cost_router, prefix="/cost")
router.include_router(collect_router)
router.include_router(home_router)
router.include_router(bi_query_router)
router.include_router(int_analysis_router)
router.include_router(comp_analysis_router)
router.include_router(comp_asset_router)
router.include_router(monitor_router)
router.include_router(meet_router)
router.include_router(report_router)
router.include_router(train_router)
router.include_router(air_router)
router.include_router(fin_router)
router.include_router(fin_dashboard_router)
router.include_router(fin_share_rule_router)
router.include_router(dc_profit_trace_router)
router.include_router(dc_trace_router)
router.include_router(perf_router)
router.include_router(perf_calc_router)
router.include_router(alert_router)
router.include_router(content_layout_router)
router.include_router(eff_router)
router.include_router(bi_report_router)
router.include_router(bi_metric_router)
router.include_router(air_skill_router)
router.include_router(air_expert_router)
router.include_router(air_cfg_router)
router.include_router(air_key_router)
router.include_router(air_mcp_log_router)
router.include_router(query_tool_router)
router.include_router(bi_subscribe_router)
router.include_router(flow_router)
router.include_router(bi_screen_router)
router.include_router(master_data_router)
router.include_router(cert_expire_router)
router.include_router(cert_security_router)
