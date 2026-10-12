"""登录与钉钉 SSO。"""
from __future__ import annotations

import json
import secrets

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.clock import now
from app.core.config import get_settings
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.redis_client import get_redis
from app.db.session import get_session
from app.domains.auth.model import UserMapping
from app.domains.system.model import User
from app.integrations.dingtalk.client import get_user_by_code
from app.services import auth_svc
from app.services.sessions import issue_session
from sqlalchemy import select

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


@mark(anonymous=True, summary="账号密码登录")
def login():
    body = _body()
    return auth_svc.login(str(body.get("username") or ""), str(body.get("password") or ""))


@mark(anonymous=True, summary="刷新令牌")
def refresh_token():
    body = _body()
    return auth_svc.refresh(str(body.get("refreshToken") or ""))


@mark(login_only=True, summary="退出登录")
def logout():
    ctx = get_ctx()
    return auth_svc.logout(ctx.user_id, ctx.session_id, ctx.username)


@mark(login_only=True, summary="修改密码")
def change_password():
    ctx = get_ctx()
    body = _body()
    return auth_svc.change_password(ctx.user_id, ctx.session_id, str(body.get("oldPassword") or ""), str(body.get("newPassword") or ""))


def _scope_text(ctx) -> str:
    from app.domains.system.model import Dept

    parts = []
    scopes = ctx.data_scopes or set()
    if "ALL" in scopes:
        parts.append("全部数据")
    if "DEPT" in scopes:
        names = []
        for ident in ctx.dept_ids:
            dept = get_session().get(Dept, ident)
            if dept:
                names.append(dept.name)
        label = "、".join(names)
        parts.append(f"本部门（{label}）" if label else "本部门")
    if "IP_GROUP" in scopes:
        parts.append("本组")
    if "SELF" in scopes:
        parts.append("仅本人")
    return "、".join(parts)


def _menu_tree(ctx) -> list[dict]:
    from app.domains.system.model import Menu, RoleMenu, UserRole

    session = get_session()
    role_ids = [row.role_id for row in session.scalars(select(UserRole).where(UserRole.user_id == ctx.user_id, UserRole.manual_removed == 0))]
    if not role_ids:
        return []
    menu_ids = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids))))
    menus = list(session.scalars(select(Menu).where(Menu.status == "ENABLED")))
    allowed_perm = ctx.perm_codes
    visible = []
    by_id = {menu.id: menu for menu in menus}
    for menu in menus:
        if menu.perm_code and menu.perm_code not in allowed_perm:
            continue
        if menu.perm_code is None and menu.id not in menu_ids and menu.type == "DIR":
            continue
        if menu.perm_code is None or menu.id in menu_ids or menu.perm_code in allowed_perm:
            visible.append(menu)
    # 补祖先
    keep = {menu.id for menu in visible}
    for menu in list(visible):
        parent = int(menu.parent_id or 0)
        while parent and parent in by_id and parent not in keep:
            keep.add(parent)
            parent = int(by_id[parent].parent_id or 0)
    rows = [by_id[ident] for ident in keep if ident in by_id]
    by_parent: dict[int, list] = {}
    for menu in rows:
        by_parent.setdefault(int(menu.parent_id or 0), []).append(menu)

    def node(menu):
        return {
            "id": menu.id,
            "name": menu.name,
            "permCode": menu.perm_code,
            "type": menu.type,
            "children": [node(child) for child in sorted(by_parent.get(menu.id, []), key=lambda item: item.sort)],
        }

    roots = [menu for menu in rows if int(menu.parent_id or 0) not in {item.id for item in rows}]
    return [node(menu) for menu in sorted(roots, key=lambda item: item.sort)]


@mark(login_only=True, summary="当前用户")
def me():
    ctx = get_ctx()
    menus = _menu_tree(ctx)
    hint = None
    if not ctx.perm_codes:
        hint = "您的账号尚未分配权限，请联系管理员"
    return {
        "id": ctx.user_id,
        "username": ctx.username,
        "nickname": ctx.nickname,
        "permCodes": sorted(ctx.perm_codes),
        "dataScopeText": _scope_text(ctx),
        "menus": menus,
        "hint": hint,
    }


@mark(anonymous=True, summary="钉钉登录跳转")
def sso_redirect():
    request = current_request()
    target = request.query_params.get("redirect") or "/"
    if not target.startswith("/") or target.startswith("//"):
        target = "/"
    state = secrets.token_hex(16)
    payload = {"redirect": target, "exp": int(now().timestamp()) + 300}
    get_redis().set(f"ims:sso:{state}", json.dumps(payload), ex=300)
    settings = get_settings()
    app_key = (settings.dingtalk or {}).get("app_key") or "test"
    url = f"https://login.dingtalk.com/oauth2/auth?client_id={app_key}&state={state}&redirect_uri=/admin-api/ims/auth/sso/dingtalk/callback"
    return RedirectResponse(url, status_code=302)


@mark(anonymous=True, summary="钉钉登录回调")
def sso_callback():
    request = current_request()
    state = request.query_params.get("state") or ""
    raw = get_redis().getdel(f"ims:sso:{state}")
    if not raw:
        raise BizError(1002)
    saved = json.loads(raw)
    if int(now().timestamp()) > int(saved["exp"]):
        raise BizError(1002)
    profile = get_user_by_code(request.query_params.get("authCode") or request.query_params.get("code") or "")
    userid = profile.get("userid")
    session = get_session()
    mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == userid).execution_options(skip_tenant=True))
    user = session.get(User, mapping.user_id) if mapping else None
    if user is None and profile.get("mobile"):
        user = auth_svc.find_by_mobile_hash(profile["mobile"], 1)
        if user is not None:
            session.add(UserMapping(user_id=user.id, dingtalk_user_id=userid, tenant_id=user.tenant_id))
            session.flush()
    if user is None:
        auth_svc._log(userid or "", None, "UNMAPPED", "DINGTALK")
        raise BizError(1217)
    if user.status in {"FROZEN", "RESIGNED"}:
        auth_svc._log(user.username, user.id, "DISABLED", "DINGTALK")
        raise BizError(1216)  # 钉钉登录同样不能只进工作台
    auth_svc._log(user.username, user.id, "SUCCESS", "DINGTALK")
    tokens = issue_session(user)
    redirect = saved.get("redirect") or "/"
    fragment = f"/sso-callback#accessToken={tokens['accessToken']}&refreshToken={tokens['refreshToken']}&redirect={redirect}"
    return RedirectResponse(fragment, status_code=302)


router.post("/login", summary="账号密码登录")(login)
router.post("/refresh-token", summary="刷新令牌")(refresh_token)
router.post("/logout", summary="退出登录")(logout)
router.post("/change-password", summary="修改密码")(change_password)
router.get("/me", summary="当前用户")(me)
router.get("/sso/dingtalk/redirect", summary="钉钉登录跳转")(sso_redirect)
router.get("/sso/dingtalk/callback", summary="钉钉登录回调")(sso_callback)
