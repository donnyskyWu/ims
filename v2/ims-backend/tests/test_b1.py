"""B1 登录、组织同步页与岗位供给规则。"""
import pytest

from sqlalchemy import select

from app.core.context import system_context, use_context
from app.db.session import session_scope
from app.domains.auth.model import OrgSyncEvent, PositionRoleRule
from app.domains.system.model import Role, User, UserRole
from app.integrations.dingtalk.client import ding_state
from tests.conftest import auth, login
from tests.stddata import U_DEPT, U_RESIGNED


def _role(client, headers, key):
    body = client.post(
        "/admin-api/ims/system/role/create",
        headers=headers,
        json={"name": key, "roleKey": key, "dataScope": "ALL"},
    ).json()
    assert body["code"] == 0, body
    return int(body["data"]["id"])


def _rule(client, headers, name, position, role_id, **extra):
    payload = {"ruleName": name, "positionCode": position, "mainRoleId": role_id, "extraRoleIds": [], "description": "说明"}
    payload.update(extra)
    token = f"tok-{position}-{role_id}-{int(bool(extra.get('replaceExisting')))}"
    return client.post(
        "/admin-api/ims/auth/position/rules",
        headers={**headers, "X-Client-Token": token},
        json=payload,
    ).json()


def test_b1_login_options_and_authorize(client):
    options = client.get("/admin-api/ims/auth/login-options").json()
    assert options["code"] == 0, options
    assert options["data"]["dingtalkEnabled"] is True
    params = client.get("/admin-api/ims/auth/sso/dingtalk/authorize-params", params={"redirect": "/ims/auth/org"}).json()
    assert params["code"] == 0, params
    assert params["data"]["state"]
    assert params["data"]["redirectUri"].endswith("/auth/sso/dingtalk/callback")
    ding_state.force_off = True
    try:
        closed = client.get("/admin-api/ims/auth/login-options").json()
        assert closed["data"]["dingtalkEnabled"] is False
        refused = client.get("/admin-api/ims/auth/sso/dingtalk/authorize-params").json()
        assert refused["code"] == 1008
    finally:
        ding_state.force_off = False


def test_b1_h5_and_first_sync(client):
    missing = client.post("/admin-api/ims/auth/sso/dingtalk/h5-login", json={}).json()
    assert missing["code"] == 1001
    ding_state.profile = {"userid": "dt_new_hire", "mobile": "", "name": "新员工"}
    ding_state.login_sync = {"userid": "dt_new_hire", "name": "新员工", "deptIds": [200], "job_number": "NE1", "title": "ANCHOR"}
    body = client.post("/admin-api/ims/auth/sso/dingtalk/h5-login", json={"authCode": "ok"}).json()
    assert body["code"] == 0, body
    assert body["data"]["accessToken"]
    with session_scope() as session:
        user = session.scalar(select(User).where(User.emp_no == "NE1"))
        assert user is not None
        assert user.nickname == "新员工"


def test_b1_resigned_still_blocked(client):
    body = login(client, "u_resigned").json()
    assert body["code"] == 1216


def test_b1_position_rules_and_errors(client):
    headers = auth(client, "u_admin")
    main = _role(client, headers, "b1_main")
    other = _role(client, headers, "b1_other")
    created = _rule(client, headers, "主播规则", "ANCHOR", main)
    assert created["code"] == 0, created
    rule_id = int(created["data"]["id"])
    clash = _rule(client, headers, "另一条", "ANCHOR", other)
    assert clash["code"] == 1281
    assert clash["data"]["existingRuleId"]
    replaced = _rule(client, headers, "另一条", "ANCHOR", other, replaceExisting=True)
    assert replaced["code"] == 0, replaced
    dup = _rule(client, headers, "另一条", "SALES", main)
    assert dup["code"] == 1284
    stale = client.put(
        f"/admin-api/ims/auth/position/rules/{replaced['data']['id']}",
        headers=headers,
        json={"ruleName": "另一条改", "mainRoleId": other, "extraRoleIds": [], "description": "改", "baseVersion": 9},
    ).json()
    assert stale["code"] == 1285
    current = client.get(f"/admin-api/ims/auth/position/rules/{replaced['data']['id']}", headers=headers).json()
    saved = client.put(
        f"/admin-api/ims/auth/position/rules/{replaced['data']['id']}",
        headers=headers,
        json={
            "ruleName": "另一条改",
            "mainRoleId": other,
            "extraRoleIds": [],
            "description": "改过",
            "baseVersion": current["data"]["version"],
        },
    ).json()
    assert saved["code"] == 0, saved
    assert saved["data"]["version"] == int(current["data"]["version"]) + 1
    overview = client.get("/admin-api/ims/auth/position/overview", headers=headers).json()
    assert overview["code"] == 0
    assert overview["data"]["enabledRuleCount"] >= 1
    page = client.get("/admin-api/ims/auth/position/rules", headers=headers).json()
    assert any(item["ruleName"] == "另一条改" for item in page["data"]["list"])
    blocked = client.delete(f"/admin-api/ims/auth/position/rules/{replaced['data']['id']}?confirmText=不对", headers=headers).json()
    assert blocked["code"] == 1283
    removed = client.delete(
        f"/admin-api/ims/auth/position/rules/{replaced['data']['id']}?confirmText=另一条改",
        headers=headers,
    ).json()
    assert removed["code"] == 0, removed
    assert rule_id


def test_b1_disabled_rule_skips_auto_role(client):
    headers = auth(client, "u_admin")
    role_id = _role(client, headers, "b1_hold")
    created = _rule(client, headers, "停用供给", "SALES", role_id)
    assert created["code"] == 0, created
    stopped = client.post(f"/admin-api/ims/auth/position/rules/{created['data']['id']}/disable", headers=headers).json()
    assert stopped["code"] == 0, stopped
    changed = client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "SALES", "eventId": "b1-skip-auto"},
    ).json()
    assert changed["code"] == 0, changed
    assert changed["data"]["skipped"] == "DISABLED_RULE"


def test_b1_delete_blocked_when_applied(client):
    headers = auth(client, "u_admin")
    role_id = _role(client, headers, "b1_busy")
    created = _rule(client, headers, "在用规则", "ANCHOR", role_id)
    assert created["code"] == 0, created
    client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "ANCHOR", "eventId": "b1-apply"},
    )
    refused = client.delete(
        f"/admin-api/ims/auth/position/rules/{created['data']['id']}?confirmText=在用规则",
        headers=headers,
    ).json()
    assert refused["code"] == 1282


def test_b1_org_metrics_and_retry(client):
    headers = auth(client, "u_admin")
    metrics = client.get("/admin-api/ims/auth/org/sync-metrics", headers=headers).json()
    assert metrics["code"] == 0, metrics
    assert "userTotal" in metrics["data"]
    summary = client.get("/admin-api/ims/auth/org/diffs/summary", headers=headers).json()
    assert summary["code"] == 0
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(
                OrgSyncEvent(
                    event_id="b1-dead-1",
                    event_type="user_modify",
                    biz_type="USER_UPDATE",
                    status="SUCCESS",
                    subject_name="已成功",
                    tenant_id=1,
                )
            )
            session.flush()
            row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == "b1-dead-1"))
            ident = int(row.id)
    refused = client.post(
        f"/admin-api/ims/auth/org/events/{ident}/retry",
        headers={**headers, "X-Client-Token": "retry-once"},
    ).json()
    assert refused["code"] == 1286
    preview = client.get(
        "/admin-api/ims/auth/org/events/replay-preview",
        headers=headers,
        params={"startTime": "2020-01-01 00:00:00", "endTime": "2020-01-02 00:00:00", "statuses": "SUCCESS"},
    ).json()
    assert preview["code"] == 1001


def test_b1_seed_refuses_production():
    import tools.e2e_seed.b1 as seed

    with pytest.raises(RuntimeError):
        seed.assert_allowed("prod")
    with pytest.raises(RuntimeError):
        seed.assert_allowed("production")
    seed.assert_allowed("test")
    seed.assert_allowed("e2e")


def test_b1_refresh_preview(client):
    headers = auth(client, "u_admin")
    role_id = _role(client, headers, "b1_refresh")
    extra = _role(client, headers, "b1_extra")
    created = _rule(client, headers, "刷新规则", "ANCHOR", role_id)
    assert created["code"] == 0, created
    ident = created["data"]["id"]
    client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "ANCHOR", "eventId": "b1-refresh-grant"},
    )
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            link = session.scalar(select(UserRole).where(UserRole.user_id == U_DEPT, UserRole.role_id == role_id))
            link.rule_version = 1
            rule = session.get(PositionRoleRule, int(ident))
            rule.version = 2
            rule.role_id = extra
    preview = client.post(
        f"/admin-api/ims/auth/position/rules/{ident}/refresh-preview",
        headers=headers,
        json={"userIds": [U_DEPT]},
    ).json()
    assert preview["code"] == 0, preview
    assert preview["data"]["count"] == 1
    done = client.post(
        f"/admin-api/ims/auth/position/rules/{ident}/refresh",
        headers={**headers, "X-Client-Token": "refresh-1"},
        json={"userIds": [U_DEPT]},
    ).json()
    assert done["code"] == 0, done
    assert U_RESIGNED
    assert Role is not None
