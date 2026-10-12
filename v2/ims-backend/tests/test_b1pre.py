"""B1 预留：一主多副角色、24 小时缓冲、工号差异、锁定码 1215。"""
from datetime import timedelta

from app.core.clock import freeze, now_naive
from app.core.error_codes import get_registry
from app.services.position import revoke_expired
from tests.conftest import auth, login
from tests.stddata import U_DEPT


def test_ut_b1pre_01(client):
    headers = auth(client, "u_admin")
    created = []
    for index in range(3):
        body = client.post(
            "/admin-api/ims/system/role/create",
            headers=headers,
            json={"name": f"供给{index}", "roleKey": f"pos_r{index}", "dataScope": "ALL"},
        ).json()
        assert body["code"] == 0, body
        created.append(int(body["data"]["id"]))
    main, extra1, extra2 = created
    client.post("/admin-api/ims/system/role/grant", headers=headers, json={"roleId": main, "permCodes": ["ims:demo:order:query"]})
    client.post("/admin-api/ims/system/role/grant", headers=headers, json={"roleId": extra2, "permCodes": ["ims:demo:order:delete"]})
    saved = client.post(
        "/admin-api/ims/system/position/rule",
        headers=headers,
        json={"positionCode": "ANCHOR_PLUS", "roleId": main, "extraRoleIds": [extra1, extra2]},
    ).json()
    assert saved["code"] == 0, saved
    applied = client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "ANCHOR_PLUS", "eventId": "ev-b1-1"},
    ).json()
    assert applied["code"] == 0, applied
    dept = auth(client, "u_dept")
    page = client.get("/admin-api/ims/demo/order/page", headers=dept)
    assert page.json()["code"] == 0
    removed = client.delete("/admin-api/ims/demo/order/delete?id=1", headers=dept)
    assert removed.json()["code"] != 1008


def test_ut_b1pre_02(client):
    headers = auth(client, "u_admin")
    ids = []
    for index in range(7):
        body = client.post(
            "/admin-api/ims/system/role/create",
            headers=headers,
            json={"name": f"超额{index}", "roleKey": f"ex_r{index}"},
        ).json()
        ids.append(int(body["data"]["id"]))
    response = client.post(
        "/admin-api/ims/system/position/rule",
        headers=headers,
        json={"positionCode": "TOO_MANY", "roleId": ids[0], "extraRoleIds": ids[1:]},
    )
    assert response.json()["code"] == 1001


def test_ut_b1pre_03(client):
    """主角色、零个附加角色时，有效权限就是主角色。"""
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/system/role/create",
        headers=headers,
        json={"name": "仅主角色", "roleKey": "only_main", "dataScope": "ALL"},
    ).json()
    role_id = int(created["data"]["id"])
    client.post("/admin-api/ims/system/role/grant", headers=headers, json={"roleId": role_id, "permCodes": ["ims:demo:order:update"]})
    saved = client.post(
        "/admin-api/ims/system/position/rule",
        headers=headers,
        json={"positionCode": "ONLY_MAIN", "roleId": role_id, "extraRoleIds": []},
    ).json()
    assert saved["code"] == 0, saved
    assert saved["data"].get("extraRoleIds") in ([], None) or saved["data"].get("extraCount") in (0, None)
    applied = client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "ONLY_MAIN", "eventId": "ev-b1-03"},
    ).json()
    assert applied["code"] == 0, applied
    updated = client.put(
        "/admin-api/ims/demo/order/update",
        headers=auth(client, "u_dept"),
        json={"id": "1", "name": "零附加"},
    )
    assert updated.json()["code"] == 0, updated.text


def test_ut_b1pre_04(client):
    """调岗后新岗位角色立即生效。"""
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": "新岗", "roleKey": "role_now", "dataScope": "ALL"}).json()
    role_id = int(body["data"]["id"])
    client.post("/admin-api/ims/system/role/grant", headers=headers, json={"roleId": role_id, "permCodes": ["ims:system:dept:delete"]})
    client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS_NOW", "roleId": role_id, "extraRoleIds": []})
    applied = client.post(
        "/admin-api/ims/system/position/event",
        headers=headers,
        json={"userId": U_DEPT, "positionCode": "POS_NOW", "eventId": "ev-b1-04"},
    ).json()
    assert applied["code"] == 0
    denied_before = "ims:system:dept:delete"
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_dept")).json()
    assert denied_before in me["data"]["permCodes"]


def test_ut_b1pre_05(client):
    """旧自动角色在 revoke_at 之前仍然有效，未到点不会被删掉。"""
    headers = auth(client, "u_admin")
    ids = []
    for key, perm in (("old_auto", "ims:demo:order:query"), ("new_auto", "ims:demo:order:create")):
        body = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": key, "roleKey": key, "dataScope": "ALL"}).json()
        ids.append(int(body["data"]["id"]))
        client.post("/admin-api/ims/system/role/grant", headers=headers, json={"roleId": ids[-1], "permCodes": [perm]})
    old_id, new_id = ids
    client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS_OLD", "roleId": old_id, "extraRoleIds": []})
    client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS_OLD", "eventId": "ev-b1-05a"})
    client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS_NEW", "roleId": new_id, "extraRoleIds": []})
    client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS_NEW", "eventId": "ev-b1-05b"})
    from app.db.session import session_scope
    from app.domains.system.model import UserRole

    with session_scope(commit=False) as session:
        old = session.query(UserRole).filter(UserRole.user_id == U_DEPT, UserRole.role_id == old_id).one()
        assert old.revoke_at is not None
        assert old.revoke_at > now_naive()
    me = client.get("/admin-api/ims/auth/me", headers=auth(client, "u_dept")).json()
    assert "ims:demo:order:query" in me["data"]["permCodes"]
    assert "ims:demo:order:create" in me["data"]["permCodes"]


def test_ut_b1pre_09(client):
    for _ in range(4):
        body = login(client, "nobody-lock", "badpass1").json()
        assert body["code"] == 1214
    body = login(client, "nobody-lock", "badpass1").json()
    assert body["code"] == 1215
    assert body["code"] != 1001
    assert body["data"]["remainMinutes"] == 15


def test_ut_b1pre_10():
    registry = get_registry()
    assert "确认替换" in registry[1281].msg
    assert "{n}" in registry[1282].msg
    assert registry[1283].msg == "输入的规则名称不一致，未删除"
    assert registry[1284].msg == "规则名称已存在"
    assert "v{n}" in registry[1285].msg
    assert registry[1286].msg == "事件状态已变化，请刷新后重试"


def test_ut_d05_03_buffer(client):
    """调岗后旧自动角色保留 24 小时，到期任务再回收。手工角色一直保留。"""
    headers = auth(client, "u_admin")
    ids = []
    for key in ("role_m", "role_p1", "role_p2"):
        body = client.post("/admin-api/ims/system/role/create", headers=headers, json={"name": key, "roleKey": key}).json()
        ids.append(int(body["data"]["id"]))
    manual, p1, p2 = ids
    from app.core.context import system_context, use_context
    from app.db.session import session_scope
    from app.domains.system.model import UserRole

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(UserRole(user_id=U_DEPT, role_id=manual, source="MANUAL", tenant_id=1))
    client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS1", "roleId": p1, "extraRoleIds": []})
    client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS1", "eventId": "ev-pos1"})
    client.post("/admin-api/ims/system/position/rule", headers=headers, json={"positionCode": "POS2", "roleId": p2, "extraRoleIds": []})
    client.post("/admin-api/ims/system/position/event", headers=headers, json={"userId": U_DEPT, "positionCode": "POS2", "eventId": "ev-pos2"})
    with session_scope(commit=False) as session:
        links = list(session.query(UserRole).filter(UserRole.user_id == U_DEPT).all())
    role_ids = {row.role_id for row in links}
    assert manual in role_ids and p1 in role_ids and p2 in role_ids
    old = next(row for row in links if row.role_id == p1)
    assert old.revoke_at is not None
    freeze(now_naive() + timedelta(hours=24, seconds=1))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            revoke_expired()
    with session_scope(commit=False) as session:
        left = {row.role_id for row in session.query(UserRole).filter(UserRole.user_id == U_DEPT).all()}
    assert p1 not in left
    assert manual in left and p2 in left
