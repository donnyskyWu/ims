"""D 组：登录、会话、密码、SSO、岗位与组织同步补齐。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import func, select

from app.core.clock import advance, freeze
from app.core.context import system_context, use_context
from app.core.crypto import hmac_hash
from app.core.redis_client import get_redis
from app.db.session import session_scope
from app.domains.auth.model import UserMapping
from app.domains.system.model import DictData, LoginLog, Role, User, UserRole
from app.domains.todo.model import Todo
from app.integrations.dingtalk.client import ding_state
from tests.conftest import auth, login
from tests.stddata import PASSWORD, U_ADMIN, U_DEPT, U_SELF

import pytest


def _json(response):
    return response.status_code, response.json()


def _labels():
    with session_scope() as session:
        rows = session.scalars(select(DictData).where(DictData.dict_type == "dict_login_result"))
        return {row.dict_value: row.dict_label for row in rows}


def _results(username: str) -> list[str]:
    with session_scope() as session:
        rows = session.scalars(select(LoginLog).where(LoginLog.username == username))
        return [row.result for row in rows]


def test_ut_d01_02(client):
    """UT-D01-02 错误密码与不存在用户名提示相同。"""
    wrong = login(client, "u_admin", "badpass1")
    missing = login(client, "nobody-d01", "badpass1")
    assert wrong.status_code == 200 and missing.status_code == 200
    wrong_body, missing_body = wrong.json(), missing.json()
    assert wrong_body["code"] == missing_body["code"] == 1214
    assert wrong_body["msg"] == missing_body["msg"] == "用户名或密码错误"


def test_ut_d01_03(client):
    """UT-D01-03 连续错误 5 次锁定 15 分钟。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    for _ in range(4):
        body = login(client, "u_dept", "badpass1").json()
        assert body["code"] == 1214
        assert "remainMinutes" not in (body.get("data") or {})
    fifth = login(client, "u_dept", "badpass1").json()
    assert fifth["code"] == 1215
    assert fifth["data"]["remainMinutes"] == 15


def test_ut_d01_04(client):
    """UT-D01-04 锁定后的第 6 分钟（已过 5 分钟）仍拒绝，剩余 10 分钟。"""
    start = datetime(2026, 10, 12, 9, 0, 0)
    freeze(start)
    for _ in range(5):
        login(client, "u_dept", "badpass1")
    freeze(start + timedelta(minutes=5))
    body = login(client, "u_dept", PASSWORD).json()
    assert body["code"] == 1215
    assert body["data"]["remainMinutes"] == 10
    assert not (body.get("data") or {}).get("accessToken")


def test_ut_d01_05(client):
    """UT-D01-05 锁定满 15 分 01 秒后正确密码可登录。"""
    start = datetime(2026, 10, 12, 9, 0, 0)
    freeze(start)
    for _ in range(5):
        login(client, "u_dept", "badpass1")
    freeze(start + timedelta(minutes=15, seconds=1))
    body = login(client, "u_dept", PASSWORD).json()
    assert body["code"] == 0
    assert body["data"]["accessToken"]
    assert get_redis().get("ims:login:fail:u_dept") is None


def test_ut_d01_06(client):
    """UT-D01-06 冻结账号：错误密码 1214，正确密码 1216。"""
    wrong = login(client, "u_frozen", "badpass1").json()
    right = login(client, "u_frozen", PASSWORD).json()
    assert wrong["code"] == 1214
    assert right["code"] == 1216
    assert wrong["msg"] == "用户名或密码错误"
    assert not (right.get("data") or {}).get("accessToken")


def test_ut_d01_07(client):
    """UT-D01-07 不存在的用户名连续 5 次也锁定。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    for _ in range(4):
        assert login(client, "ghost-d01", "badpass1").json()["code"] == 1214
    fifth = login(client, "ghost-d01", "badpass1").json()
    assert fifth["code"] == 1215
    assert fifth["data"]["remainMinutes"] == 15


def test_ut_d01_08(client):
    """UT-D01-08 纯字母、纯数字、过短密码均拒绝。"""
    headers = auth(client, "u_admin")
    for new_password in ("abcdefgh", "12345678", "Ab1"):
        body = client.post(
            "/admin-api/ims/auth/change-password",
            headers=headers,
            json={"oldPassword": PASSWORD, "newPassword": new_password},
        ).json()
        assert body["code"] == 1001, body
        assert body["data"]["fieldErrors"][0]["field"] == "newPassword"


def test_ut_d01_09(client):
    """UT-D01-09 管理员重置后须先改密，业务接口才放行。"""
    admin = auth(client, "u_admin")
    reset = client.post("/admin-api/ims/system/user/reset-password", headers=admin, json={"id": U_DEPT}).json()
    assert reset["code"] == 0, reset
    fresh = reset["data"]["password"]
    logged = login(client, "u_dept", fresh).json()
    assert logged["code"] == 0, logged
    assert logged["data"]["pwdResetRequired"] is True
    token = logged["data"]["accessToken"]
    blocked = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {token}"})
    assert blocked.json()["code"] == 1008
    changed = client.post(
        "/admin-api/ims/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"oldPassword": fresh, "newPassword": "Abc123456"},
    ).json()
    assert changed["code"] == 0, changed
    opened = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {token}"})
    assert opened.json()["code"] == 0


def test_ut_d01_10(client):
    """UT-D01-10 一个会话改密后，另一个会话失效。"""
    first = login(client, "u_dept").json()["data"]
    second = login(client, "u_dept").json()["data"]
    changed = client.post(
        "/admin-api/ims/auth/change-password",
        headers={"Authorization": f"Bearer {first['accessToken']}"},
        json={"oldPassword": PASSWORD, "newPassword": "Abc123456"},
    )
    assert changed.json()["code"] == 0, changed.json()
    stale = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {second['accessToken']}"})
    assert stale.status_code == 401
    assert stale.json()["code"] == 1002
    alive = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {first['accessToken']}"})
    assert alive.status_code == 200
    assert alive.json()["code"] == 0


def test_ut_d01_11(client):
    """UT-D01-11 原密码错误返回 1214；新旧相同返回 1001。"""
    headers = auth(client, "u_dept")
    wrong = client.post(
        "/admin-api/ims/auth/change-password",
        headers=headers,
        json={"oldPassword": "badpass1", "newPassword": "Abc123456"},
    ).json()
    assert wrong["code"] == 1214
    same = client.post(
        "/admin-api/ims/auth/change-password",
        headers=headers,
        json={"oldPassword": PASSWORD, "newPassword": PASSWORD},
    ).json()
    assert same["code"] == 1001


def test_ut_d01_12(client):
    """UT-D01-12 访问令牌超过 2 小时失效。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    token = login(client, "u_admin").json()["data"]["accessToken"]
    advance(timedelta(hours=2, seconds=1))
    response = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == 1002


def test_ut_d01_13(client):
    """UT-D01-13 refresh 换发新的 access 与 refresh。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    issued = login(client, "u_admin").json()["data"]
    advance(timedelta(hours=2, seconds=1))
    refreshed = client.post("/admin-api/ims/auth/refresh-token", json={"refreshToken": issued["refreshToken"]})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["code"] == 0
    assert body["data"]["accessToken"] and body["data"]["accessToken"] != issued["accessToken"]
    assert body["data"]["refreshToken"] and body["data"]["refreshToken"] != issued["refreshToken"]
    page = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {body['data']['accessToken']}"})
    assert page.json()["code"] == 0


def test_ut_d01_14(client):
    """UT-D01-14 旧 refresh 不能再用。"""
    issued = login(client, "u_admin").json()["data"]
    first = client.post("/admin-api/ims/auth/refresh-token", json={"refreshToken": issued["refreshToken"]})
    assert first.json()["code"] == 0
    again = client.post("/admin-api/ims/auth/refresh-token", json={"refreshToken": issued["refreshToken"]})
    assert again.status_code == 401
    assert again.json()["code"] == 1002


def test_ut_d01_15(client):
    """UT-D01-15 refresh 超过 7 天失效。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    issued = login(client, "u_admin").json()["data"]
    advance(timedelta(days=7, seconds=1))
    response = client.post("/admin-api/ims/auth/refresh-token", json={"refreshToken": issued["refreshToken"]})
    assert response.status_code == 401
    assert response.json()["code"] == 1002


def test_ut_d01_16(client):
    """UT-D01-16 第 4 个会话踢掉最早的会话。"""
    tokens = [login(client, "u_admin").json()["data"]["accessToken"] for _ in range(4)]
    kicked = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {tokens[0]}"})
    assert kicked.status_code == 401
    assert kicked.json()["code"] == 1003
    for token in tokens[1:]:
        alive = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {token}"})
        assert alive.status_code == 200
        assert alive.json()["code"] == 0


def test_ut_d01_17(client):
    """UT-D01-17 登出后原 access 失效。"""
    token = login(client, "u_admin").json()["data"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    out = client.post("/admin-api/ims/auth/logout", headers=headers)
    assert out.json()["code"] == 0
    again = client.get("/admin-api/ims/demo/order/page", headers=headers)
    assert again.status_code == 401
    assert again.json()["code"] == 1002


def test_ut_d01_18(client):
    """UT-D01-18 管理员强制下线后全部会话失效，并记操作日志。"""
    from app.domains.system.model import OperateLog

    first = login(client, "u_dept").json()["data"]["accessToken"]
    second = login(client, "u_dept").json()["data"]["accessToken"]
    kicked = client.post("/admin-api/ims/system/user/kick", headers=auth(client, "u_admin"), json={"id": U_DEPT})
    assert kicked.json()["code"] == 0, kicked.json()
    for token in (first, second):
        response = client.get("/admin-api/ims/demo/order/page", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["code"] == 1002
    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(OperateLog).where(OperateLog.action == "强制下线"))
    assert count == 1


def test_ut_d01_19(client):
    """UT-D01-19 管理员解锁后可以重新登录。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    for _ in range(5):
        login(client, "u_dept", "badpass1")
    assert login(client, "u_dept", PASSWORD).json()["code"] == 1215
    unlocked = client.post("/admin-api/ims/system/user/unlock", headers=auth(client, "u_admin"), json={"username": "u_dept"})
    assert unlocked.json()["code"] == 0, unlocked.json()
    body = login(client, "u_dept", PASSWORD).json()
    assert body["code"] == 0
    assert body["data"]["accessToken"]


def _sso_redirect(client, redirect="/sys/user"):
    response = client.get(
        "/admin-api/ims/auth/sso/dingtalk/redirect",
        params={"redirect": redirect},
        follow_redirects=False,
    )
    assert response.status_code == 302, response.text
    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    return response, state


def _bind(user_id: int, ding_id: str) -> None:
    from app.services.mapping import bind_dingtalk

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            bind_dingtalk(user_id, ding_id)
            session.flush()


def test_ut_d02_01(client):
    """UT-D02-01 钉钉跳转写入 state，TTL 约 300 秒。"""
    response, state = _sso_redirect(client, "/sys/user")
    assert "login.dingtalk.com" in response.headers["location"]
    raw = get_redis().get(f"ims:sso:{state}")
    assert raw
    assert json.loads(raw)["redirect"] == "/sys/user"
    ttl = int(get_redis().ttl(f"ims:sso:{state}"))
    assert 290 <= ttl <= 300


def test_ut_d02_02(client):
    """UT-D02-02 外链 redirect 被改写成站内根路径。"""
    _response, state = _sso_redirect(client, "https://evil.com")
    saved = json.loads(get_redis().get(f"ims:sso:{state}"))
    assert saved["redirect"] == "/"


def test_ut_d02_03(client):
    """UT-D02-03 已映射钉钉账号回调签发令牌，登录日志为钉钉。"""
    _bind(U_ADMIN, "dt_a")
    ding_state.profile = {"userid": "dt_a", "mobile": "", "name": "管理员"}
    _response, state = _sso_redirect(client, "/sys/user")
    callback = client.get(
        "/admin-api/ims/auth/sso/dingtalk/callback",
        params={"state": state, "authCode": "ok"},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    location = callback.headers["location"]
    assert location.startswith("/sso-callback#accessToken=")
    with session_scope() as session:
        row = session.scalar(select(LoginLog).where(LoginLog.username == "u_admin", LoginLog.login_type == "DINGTALK"))
    assert row is not None and row.result == "SUCCESS"


def test_ut_d02_04(client):
    """UT-D02-04 同一个 state 只能回调一次。"""
    _bind(U_ADMIN, "dt_a")
    ding_state.profile = {"userid": "dt_a", "mobile": "", "name": "管理员"}
    _response, state = _sso_redirect(client)
    first = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert first.status_code == 302
    second = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert second.status_code == 401
    assert second.json()["code"] == 1002


def test_ut_d02_05(client):
    """UT-D02-05 state 超过 5 分钟失效。"""
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    _response, state = _sso_redirect(client)
    advance(timedelta(minutes=5, seconds=1))
    response = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert response.status_code == 401
    assert response.json()["code"] == 1002


def test_ut_d02_06(client):
    """UT-D02-06 未映射但手机号命中本地用户时登录并补映射。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.get(User, U_DEPT)
            user.mobile_hash = hmac_hash("13800002222")
    ding_state.profile = {"userid": "dt_x", "mobile": "13800002222", "name": "部门用户"}
    _response, state = _sso_redirect(client)
    callback = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert callback.status_code == 302
    assert "accessToken=" in callback.headers["location"]
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_x"))
    assert mapping is not None and int(mapping.user_id) == U_DEPT


def test_ut_d02_07(client):
    """UT-D02-07 未映射且手机号无匹配时返回 1217，不签发会话。"""
    ding_state.profile = {"userid": "dt_missing", "mobile": "13900000000", "name": "陌生人"}
    before = set(get_redis().keys("ims:sess:*"))
    _response, state = _sso_redirect(client)
    response = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert response.status_code != 500
    assert response.json()["code"] == 1217
    assert set(get_redis().keys("ims:sess:*")) == before


def test_ut_d02_08(client):
    """UT-D02-08 钉钉超时 5003，钉钉错误 1006。"""
    ding_state.error = "timeout"
    _response, state = _sso_redirect(client)
    timeout = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert timeout.status_code == 200
    assert timeout.json()["code"] == 5003
    ding_state.error = "error"
    _response, state = _sso_redirect(client)
    failed = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert failed.status_code == 200
    assert failed.json()["code"] == 1006


def test_ut_d02_09(client):
    """UT-D02-09 映射到冻结用户时拒绝登录。"""
    with session_scope() as session:
        frozen = session.scalar(select(User).where(User.username == "u_frozen"))
        frozen_id = int(frozen.id)
    _bind(frozen_id, "dt_frozen")
    ding_state.profile = {"userid": "dt_frozen", "mobile": "", "name": "冻结"}
    _response, state = _sso_redirect(client)
    response = client.get("/admin-api/ims/auth/sso/dingtalk/callback", params={"state": state, "authCode": "ok"}, follow_redirects=False)
    assert response.status_code == 200
    assert response.json()["code"] == 1216


def test_ut_d03_01(app):
    """UT-D03-01 业务路由不声明权限码则启动失败。"""
    from fastapi import APIRouter

    from app.api.meta import mark
    from app.core.errors import StartupError
    from app.main import create_app

    router = APIRouter()

    @mark(summary="未声明权限")
    def open_biz():
        return {}

    router.get("/open-biz", summary="未声明权限")(open_biz)
    router.prefix_override = "/admin-api/ims/demo"
    with pytest.raises(StartupError) as exc:
        create_app(app.state.settings, extra_routers=[router])
    assert "权限" in str(exc.value)


def test_ut_d03_02(app):
    """UT-D03-02 权限码不在菜单种子中则启动失败。"""
    from fastapi import APIRouter

    from app.api.meta import mark
    from app.core.errors import StartupError
    from app.main import create_app

    router = APIRouter()

    @mark(perm="ims:demo:nope:query", summary="未登记权限")
    def nope():
        return {}

    router.get("/nope", summary="未登记权限")(nope)
    router.prefix_override = "/admin-api/ims/demo"
    with pytest.raises(StartupError) as exc:
        create_app(app.state.settings, extra_routers=[router])
    assert "ims:demo:nope:query" in str(exc.value)


def test_ut_d03_03(client):
    """UT-D03-03 只有读权限时列表成功，新建和删除为 1008。"""
    headers = auth(client, "u_ro")
    listed = client.get("/admin-api/ims/demo/order/page", headers=headers)
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["list"]
    created = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "不可建"})
    deleted = client.delete("/admin-api/ims/demo/order/delete?id=1", headers=headers)
    assert created.json()["code"] == 1008
    assert deleted.json()["code"] == 1008


def test_ut_d03_04(client):
    """UT-D03-04 唯一角色待配置时业务接口 1008。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            role = session.get(Role, 202)
            role.status = "PENDING_CONFIG"
    body = client.get("/admin-api/ims/demo/order/page", headers=auth(client, "u_dept")).json()
    assert body["code"] == 1008


def test_ut_d03_05(client):
    """UT-D03-05 无权限用户业务接口 1008，当前用户接口仍可访问。"""
    headers = auth(client, "u_none")
    denied = client.get("/admin-api/ims/demo/order/page", headers=headers).json()
    me = client.get("/admin-api/ims/auth/me", headers=headers).json()
    assert denied["code"] == 1008
    assert me["code"] == 0


def test_ut_d03_06(client):
    """UT-D03-06 两个角色的权限取并集。"""
    from app.domains.system.model import Menu, RoleMenu, UserRole

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.scalar(select(User).where(User.username == "u_ro"))
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:demo:order:create"))
            role = Role(name="示例写", role_key="demo_w", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1)
            session.add(role)
            session.flush()
            session.add(RoleMenu(role_id=role.id, menu_id=menu.id, tenant_id=1))
            session.add(UserRole(user_id=user.id, role_id=role.id, source="MANUAL", tenant_id=1))
    created = client.post("/admin-api/ims/demo/order/create", headers=auth(client, "u_ro"), json={"name": "并集可建", "code": "UNION1"})
    assert created.json()["code"] == 0, created.json()


def test_ut_d03_07(client):
    """UT-D03-07 套餐未包含的菜单，角色里有也不放行。"""
    body = client.get("/admin-api/ims/demo/order/page", headers=auth(client, "t2_admin")).json()
    assert body["code"] == 1008


def test_ut_d03_08(tmp_path):
    """UT-D03-08 按角色名或角色键分支会被静态检查拦住。"""
    from tools.static_checks import check_role_branch

    first = tmp_path / "by_key.py"
    second = tmp_path / "by_name.py"
    first.write_text('def allow(user):\n    if user.role_key == "R1":\n        return True\n', encoding="utf-8")
    second.write_text('def allow(roles):\n    if "admin" in roles:\n        return True\n', encoding="utf-8")
    problems = check_role_branch(tmp_path)
    assert any("R1" in item for item in problems)
    assert any("admin" in item for item in problems)


def test_ut_d03_09(client):
    """UT-D03-09 授权后立即生效。"""
    from app.domains.system.model import UserRole

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.scalar(select(User).where(User.username == "u_none"))
            role = Role(name="稍后授权", role_key="later_r", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1)
            session.add(role)
            session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id, source="MANUAL", tenant_id=1))
            role_id = int(role.id)
    headers = auth(client, "u_none")
    assert client.get("/admin-api/ims/demo/order/page", headers=headers).json()["code"] == 1008
    granted = client.post(
        "/admin-api/ims/system/role/grant",
        headers=auth(client, "u_admin"),
        json={"roleId": role_id, "permCodes": ["ims:demo:order:query"]},
    )
    assert granted.json()["code"] == 0, granted.json()
    assert client.get("/admin-api/ims/demo/order/page", headers=headers).json()["code"] == 0


def test_ut_d03_10(client):
    """UT-D03-10 撤销授权后立即变为 1008。"""
    from app.domains.system.model import UserRole

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.scalar(select(User).where(User.username == "u_ro"))
            role_id = int(session.scalar(select(UserRole.role_id).where(UserRole.user_id == user.id)))
    headers = auth(client, "u_ro")
    assert client.get("/admin-api/ims/demo/order/page", headers=headers).json()["code"] == 0
    revoked = client.post(
        "/admin-api/ims/system/role/grant",
        headers=auth(client, "u_admin"),
        json={"roleId": role_id, "permCodes": []},
    )
    assert revoked.json()["code"] == 0, revoked.json()
    assert client.get("/admin-api/ims/demo/order/page", headers=headers).json()["code"] == 1008


def test_ut_d04_01(client):
    """UT-D04-01 保存部门数据范围后，当前用户看到本部门中文说明。"""
    saved = client.put(
        "/admin-api/ims/system/role/data-scope",
        headers=auth(client, "u_admin"),
        json={"id": 202, "dataScope": "DEPT"},
    ).json()
    assert saved["code"] == 0, saved
    assert saved["data"]["dataScope"] == "DEPT"
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_dept")).json()
    assert me["data"]["dataScopeText"] == "本部门（市场部、技术部）"


def test_ut_d05_01(client):
    """UT-D05-01 新岗位自动建待配置角色、规则和待办，用户业务接口仍是 1008。"""
    from app.domains.todo.model import TodoAssignee

    user_id = None
    with session_scope() as session:
        user_id = int(session.scalar(select(User.id).where(User.username == "u_none")))
    body = client.post(
        "/admin-api/ims/system/position/event",
        headers=auth(client, "u_admin"),
        json={"userId": user_id, "positionCode": "NEW_POS", "eventId": "ev-new-pos"},
    ).json()
    assert body["code"] == 0, body
    with session_scope() as session:
        role = session.scalar(select(Role).where(Role.position_code == "NEW_POS"))
        assert role.source == "DINGTALK_AUTO"
        assert role.status == "PENDING_CONFIG"
        link = session.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id))
        assert link is not None
        todo = session.scalar(select(Todo).where(Todo.source_type == "POSITION_CONFIG", Todo.source_id == role.id))
        assert todo is not None
        holders = {row.user_id for row in session.scalars(select(TodoAssignee).where(TodoAssignee.todo_id == todo.id))}
        assert U_ADMIN in holders
    denied = client.get("/admin-api/ims/demo/order/page", headers=auth(client, "u_none")).json()
    assert denied["code"] == 1008


def test_ut_d05_02(client):
    """UT-D05-02 同一岗位事件重复投递不新增角色、规则、关系和待办。"""
    from app.domains.auth.model import PositionRoleRule

    with session_scope() as session:
        user_id = int(session.scalar(select(User.id).where(User.username == "u_none")))
    payload = {"userId": user_id, "positionCode": "NEW_POS", "eventId": "ev-new-pos"}
    headers = auth(client, "u_admin")
    assert client.post("/admin-api/ims/system/position/event", headers=headers, json=payload).json()["code"] == 0
    with session_scope() as session:
        before = (
            session.scalar(select(func.count()).select_from(Role).where(Role.position_code == "NEW_POS")),
            session.scalar(select(func.count()).select_from(PositionRoleRule).where(PositionRoleRule.position_code == "NEW_POS")),
            session.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user_id)),
            session.scalar(select(func.count()).select_from(Todo).where(Todo.source_type == "POSITION_CONFIG")),
        )
    again = client.post("/admin-api/ims/system/position/event", headers=headers, json=payload).json()
    assert again["data"]["duplicated"] is True
    with session_scope() as session:
        after = (
            session.scalar(select(func.count()).select_from(Role).where(Role.position_code == "NEW_POS")),
            session.scalar(select(func.count()).select_from(PositionRoleRule).where(PositionRoleRule.position_code == "NEW_POS")),
            session.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user_id)),
            session.scalar(select(func.count()).select_from(Todo).where(Todo.source_type == "POSITION_CONFIG")),
        )
    assert after == before


def test_ut_d05_03(client):
    """UT-D05-03 调岗后旧自动角色进入回收，手工角色保留。"""
    from app.core.clock import now_naive
    from app.services.position import revoke_expired

    headers = auth(client, "u_admin")
    ids = []
    for key in ("role_m", "role_p1", "role_p2"):
        body = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": key, "roleKey": key, "dataScope": "SELF"}).json()
        assert body["code"] == 0, body
        ids.append(int(body["data"]["id"]))
    manual, p1, p2 = ids
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(UserRole(user_id=U_DEPT, role_id=manual, source="MANUAL", tenant_id=1))
    assert client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS1", "roleId": p1, "extraRoleIds": []}).json()["code"] == 0
    assert client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS1", "eventId": "ev-pos1"}).json()["code"] == 0
    assert client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS2", "roleId": p2, "extraRoleIds": []}).json()["code"] == 0
    assert client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS2", "eventId": "ev-pos2"}).json()["code"] == 0
    freeze(now_naive() + timedelta(hours=24, seconds=1))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            revoke_expired()
    with session_scope() as session:
        left = {row.role_id for row in session.scalars(select(UserRole).where(UserRole.user_id == U_DEPT))}
    assert manual in left and p2 in left and p1 not in left


def test_ut_d05_04(client):
    """UT-D05-04 管理员手工移除的自动角色，再次投递也不会加回。"""
    headers = auth(client, "u_admin")
    created = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": "岗位二", "roleKey": "role_p2b", "dataScope": "SELF"}).json()
    p2 = int(created["data"]["id"])
    assert client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS2", "roleId": p2, "extraRoleIds": []}).json()["code"] == 0
    assert client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_SELF, "positionCode": "POS2", "eventId": "ev-pos2-a"}).json()["code"] == 0
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            link = session.scalar(select(UserRole).where(UserRole.user_id == U_SELF, UserRole.role_id == p2))
            link.manual_removed = 1
    again = client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_SELF, "positionCode": "POS2", "eventId": "ev-pos2-b"}).json()
    assert again["code"] == 0, again
    with session_scope() as session:
        link = session.scalar(select(UserRole).where(UserRole.user_id == U_SELF, UserRole.role_id == p2))
    assert link.manual_removed == 1


def test_ut_d05_05(client):
    """UT-D05-05 修改岗位规则后旧版本归档，新版本生效。"""
    from app.domains.auth.model import PositionRoleRule

    headers = auth(client, "u_admin")
    ids = []
    for key in ("hist_p1", "hist_p3"):
        body = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": key, "roleKey": key, "dataScope": "SELF"}).json()
        ids.append(int(body["data"]["id"]))
    p1, p3 = ids
    assert client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS1", "roleId": p1, "extraRoleIds": []}).json()["code"] == 0
    changed = client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS1", "roleId": p3, "extraRoleIds": []}).json()
    assert changed["code"] == 0, changed
    assert changed["data"]["version"] == 2
    with session_scope() as session:
        rows = list(session.scalars(select(PositionRoleRule).where(PositionRoleRule.position_code == "POS1")))
    archived = [row for row in rows if row.archived == 1]
    active = [row for row in rows if row.archived == 0 and row.status == "ENABLED"]
    assert len(archived) == 1 and int(archived[0].role_id) == p1
    assert len(active) == 1 and int(active[0].role_id) == p3


def _names(nodes):
    found = []
    for node in nodes:
        found.append(node["name"])
        found.extend(_names(node.get("children") or []))
    return found


def test_ut_d06_01(client):
    """UT-D06-01 角色没有示例域菜单时，菜单和权限码都不返回示例域。"""
    from app.domains.system.model import Menu, RoleMenu

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.scalar(select(User).where(User.username == "u_none"))
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:system:dept:query"))
            role = Role(name="仅部门查询", role_key="dept_q", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1)
            session.add(role)
            session.flush()
            session.add(RoleMenu(role_id=role.id, menu_id=menu.id, tenant_id=1))
            session.add(UserRole(user_id=user.id, role_id=role.id, source="MANUAL", tenant_id=1))
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_none")).json()
    assert "示例域" not in _names(me["data"]["menus"])
    assert all(not code.startswith("ims:demo:") for code in me["data"]["permCodes"])


def test_ut_d06_02(client):
    """UT-D06-02 套餐未包含示例域时，菜单树不返回示例域。"""
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "t2_admin")).json()
    assert me["code"] == 0, me
    assert "示例域" not in _names(me["data"]["menus"])


def test_ut_d06_03(client):
    """UT-D06-03 多个数据范围用中文说明，不出现编码。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            role = Role(name="仅本人补充", role_key="self_extra", source="MANUAL", status="ENABLED", data_scope="SELF", is_standard=0, tenant_id=1)
            session.add(role)
            session.flush()
            session.add(UserRole(user_id=U_DEPT, role_id=role.id, source="MANUAL", tenant_id=1))
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_dept")).json()
    text = me["data"]["dataScopeText"]
    assert "本部门" in text and "仅本人" in text
    assert "DEPT" not in text and "SELF" not in text


def test_ut_d06_04(client):
    """UT-D06-04 未分配权限时菜单为空并给出提示。"""
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_none")).json()
    assert me["data"]["menus"] == []
    assert me["data"]["hint"] == "您的账号尚未分配权限，请联系管理员"

