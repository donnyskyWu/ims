"""B2 系统管理：用户、角色、菜单、字典、参数、日志、通知、租户、个人中心。"""
from sqlalchemy import select

from app.core.context import RequestContext, use_context
from app.db.session import session_scope
from app.domains.message.model import NotifyRecord
from app.domains.system.model import Menu, RoleMenu, User
from tests.conftest import auth
from tests.stddata import PASSWORD

API = "/admin-api/ims/system"
AUTH = "/admin-api/ims/auth"

PATHS = [
    "/admin-api/ims/system/user",
    "/admin-api/ims/system/user/{ident}",
    "/admin-api/ims/system/user/{ident}/roles",
    "/admin-api/ims/system/user/{ident}/freeze",
    "/admin-api/ims/system/user/{ident}/unfreeze",
    "/admin-api/ims/system/user/{ident}/resign",
    "/admin-api/ims/system/user/{ident}/unlock",
    "/admin-api/ims/system/user/{ident}/kick",
    "/admin-api/ims/system/user/{ident}/reset-password",
    "/admin-api/ims/system/user/export",
    "/admin-api/ims/system/role/page",
    "/admin-api/ims/system/role",
    "/admin-api/ims/system/role/{ident}/menus",
    "/admin-api/ims/system/role/{ident}/perm-detail",
    "/admin-api/ims/system/role/{ident}/data-scope",
    "/admin-api/ims/system/role/{ident}/members",
    "/admin-api/ims/system/role/{ident}/members/{user_id}",
    "/admin-api/ims/system/role/{ident}/status",
    "/admin-api/ims/system/role/{ident}",
    "/admin-api/ims/system/role/{ident}/preview",
    "/admin-api/ims/system/role/from-position",
    "/admin-api/ims/system/menu/tree",
    "/admin-api/ims/system/menu",
    "/admin-api/ims/system/menu/{ident}",
    "/admin-api/ims/system/menu/{ident}/visible",
    "/admin-api/ims/system/dict-type/list",
    "/admin-api/ims/system/dict-type",
    "/admin-api/ims/system/dict-type/{ident}",
    "/admin-api/ims/system/dict-data/list",
    "/admin-api/ims/system/dict-data",
    "/admin-api/ims/system/dict-data/{ident}",
    "/admin-api/ims/system/param/history",
    "/admin-api/ims/system/param",
    "/admin-api/ims/system/operate-log/page",
    "/admin-api/ims/system/operate-log/{ident}",
    "/admin-api/ims/system/login-log/page",
    "/admin-api/ims/system/operate-log/export",
    "/admin-api/ims/system/login-log/export",
    "/admin-api/ims/system/notify/page",
    "/admin-api/ims/system/notify/{ident}/resend",
    "/admin-api/ims/system/tenant/page",
    "/admin-api/ims/system/tenant",
    "/admin-api/ims/system/tenant/{ident}",
    "/admin-api/ims/system/tenant/{ident}/package",
    "/admin-api/ims/system/tenant-package/page",
    "/admin-api/ims/system/tenant-package",
    "/admin-api/ims/system/tenant-package/{ident}",
    "/admin-api/ims/system/tenant-package/{ident}/menus",
]


def test_b2_routes_registered(client):
    found = set(client.app.openapi()["paths"])
    missing = [path for path in PATHS if path not in found]
    assert missing == []
    assert "/admin-api/ims/auth/password/change" in found
    assert "/admin-api/ims/auth/password/set" in found
    assert "/admin-api/ims/auth/sessions/my" in found


def _user(headers, username="b2user01", mobile="13800001001", **extra):
    body = {
        "username": username,
        "nickname": "批次用户",
        "mobile": mobile,
        "password": "Abc12345",
        "deptIds": [11],
        "mainDeptId": 11,
    }
    body.update(extra)
    return body


def test_user_rules(client):
    headers = auth(client, "u_admin")
    missing = client.post(f"{API}/user", headers=headers, json=_user(headers, mainDeptId=None))
    assert missing.json()["code"] == 1287
    created = client.post(f"{API}/user", headers=headers, json=_user(headers)).json()
    assert created["code"] == 0, created
    assert isinstance(created["data"]["id"], str)
    user_id = created["data"]["id"]
    renamed = client.put(f"{API}/user", headers=headers, json={"id": user_id, "username": "b2renamed"}).json()
    assert renamed["code"] == 1001
    dup = client.post(f"{API}/user", headers=headers, json=_user(headers, username="b2user02", mobile="13800001001")).json()
    assert dup["code"] == 1292
    fresh = client.post(f"{API}/user", headers=headers, json=_user(headers, username="b2fresh", mobile="13800001002")).json()
    assert client.delete(f"{API}/user/delete", headers=headers, params={"id": fresh["data"]["id"]}).json()["code"] == 0
    assert client.post(f"{AUTH}/login", json={"username": "b2user01", "password": "Abc12345"}).json()["code"] == 0
    blocked = client.delete(f"{API}/user/delete", headers=headers, params={"id": user_id}).json()
    assert blocked["code"] == 1502
    assert client.put(f"{API}/user/{user_id}/freeze", headers=headers).json()["code"] == 0
    assert client.put(f"{API}/user/{user_id}/unfreeze", headers=headers).json()["code"] == 0
    assert client.put(f"{API}/user/{user_id}/unlock", headers=headers).json()["code"] == 0
    assert client.put(f"{API}/user/{user_id}/kick", headers=headers).json()["code"] == 0
    reset = client.post(f"{API}/user/{user_id}/reset-password", headers=headers).json()
    assert reset["code"] == 0 and reset["data"]["password"]
    assert client.put(f"{API}/user/{user_id}/resign", headers=headers).json()["code"] == 0
    assert client.put(f"{API}/user/{user_id}/unfreeze", headers=headers).json()["code"] == 1001
    exported = client.post(f"{API}/user/export", headers=headers, json={"deptId": 11}).json()
    assert exported["code"] == 0, exported


def test_role_scope_position_and_delete(client):
    headers = auth(client, "u_admin")
    created = client.post(f"{API}/role", headers=headers, json={"name": "批次角色", "roleKey": "b2_role", "dataScope": "DEPT", "remark": "b2"}).json()
    assert created["code"] == 0, created
    role_id = created["data"]["id"]
    assert created["data"]["positionCode"] in (None, "")
    updated = client.put(f"{API}/role", headers=headers, json={"id": role_id, "name": "批次角色", "positionCode": "B2POS"}).json()
    assert updated["code"] == 0
    assert updated["data"]["positionCode"] in (None, "")
    assert "岗位" in updated["data"]["positionHint"]
    menu = client.get(f"{API}/menu/tree", headers=headers).json()["data"]
    menu_id = _find_perm(menu, "ims:system:role:update")
    assert client.put(f"{API}/role/{role_id}/menus", headers=headers, json={"menuIds": [menu_id]}).json()["code"] == 0
    assert client.put(f"{API}/role/{role_id}/perm-detail", headers=headers, json={"details": [{"permCode": "ims:system:role:update", "r": 0, "w": 1, "d": 0}]}).json()["code"] == 0
    scoped = client.post(f"{API}/user", headers=headers, json=_user(headers, username="b2scope", mobile="13800001009", roleIds=[role_id])).json()
    assert scoped["code"] == 0, scoped
    _clear_reset("b2scope")
    limited = auth(client, "b2scope")
    denied = client.put(f"{API}/role/{role_id}/data-scope", headers=limited, json={"dataScope": "ALL"}).json()
    assert denied["code"] == 1001
    allowed = client.put(f"{API}/role/{role_id}/data-scope", headers=headers, json={"dataScope": "SELF"}).json()
    assert allowed["code"] == 0
    member = client.post(f"{API}/role/{role_id}/members", headers=headers, json={"userId": "1001"}).json()
    assert member["code"] == 0
    preview = client.post(f"{API}/role/{role_id}/preview", headers=headers, json={"userId": "1001"}).json()
    assert preview["code"] == 0 and "added" in preview["data"]
    blocked = client.request("DELETE", f"{API}/role/{role_id}", headers=headers, json={"confirmName": "批次角色"}).json()
    assert blocked["code"] == 1502
    empty = client.post(f"{API}/role", headers=headers, json={"name": "空角色", "roleKey": "b2_empty", "dataScope": "SELF"}).json()
    assert empty["code"] == 0, empty
    bad = client.request("DELETE", f"{API}/role/{empty['data']['id']}", headers=headers, json={"confirmName": "不对"}).json()
    assert bad["code"] == 1293
    gone = client.request("DELETE", f"{API}/role/{empty['data']['id']}", headers=headers, json={"confirmName": "空角色"}).json()
    assert gone["code"] == 0, gone
    generated = client.post(f"{API}/role/from-position", headers=headers, json={"positionCode": "SALES"}).json()
    assert generated["code"] == 0 and generated["data"]["status"] == "PENDING_CONFIG", generated
    again = client.post(f"{API}/role/from-position", headers=headers, json={"positionCode": "SALES"}).json()
    assert again["data"]["existed"] is True


def test_menu_dict_param(client):
    headers = auth(client, "u_admin")
    tree = client.get(f"{API}/menu/tree", headers=headers).json()["data"]
    locked = _find_node(tree, lambda node: node.get("seedLocked") and node.get("path"))
    blocked = client.put(f"{API}/menu", headers=headers, json={"id": locked["id"], "path": "/ims/hack"}).json()
    assert blocked["code"] == 1001
    renamed = client.put(f"{API}/menu", headers=headers, json={"id": locked["id"], "name": locked["name"], "sort": locked.get("sort") or 0}).json()
    assert renamed["code"] == 0
    hidden = client.put(f"{API}/menu/{locked['id']}/visible", headers=headers, json={"visible": False}).json()
    assert hidden["code"] == 0
    shown = client.put(f"{API}/menu/{locked['id']}/visible", headers=headers, json={"visible": True}).json()
    assert shown["code"] == 0
    values = client.get(f"{API}/dict-data/list", headers=headers, params={"dictType": "dict_user_status"}).json()
    assert values["code"] == 0 and values["data"]
    removed = client.delete(f"{API}/dict-data/{values['data'][0]['id']}", headers=headers).json()
    assert removed["code"] == 1502
    params = client.get(f"{API}/param/list", headers=headers).json()["data"]
    groups = {item["groupName"] for item in params}
    assert {"内容审核", "钉钉", "钉钉考勤", "AI", "通用"} <= groups
    assert all(not str(item["paramKey"]).startswith("train_ai") for item in params)
    secret = next(item for item in params if item["paramKey"] == "dingtalk_attendance.app_secret")
    assert secret["value"] == "******"
    kept = client.put(f"{API}/param", headers=headers, json={"paramKey": secret["paramKey"], "value": ""}).json()
    assert kept["code"] == 0 and kept["data"]["value"] == "******"
    unknown = client.put(f"{API}/param", headers=headers, json={"paramKey": "missing.key", "value": "1"}).json()
    assert unknown["code"] == 1213


def test_logs_notify_tenant_profile(client):
    headers = auth(client, "u_admin")
    assert client.post(f"{API}/user", headers=headers, json=_user(headers, username="b2log", mobile="13800001003")).json()["code"] == 0
    logs = client.get(f"{API}/operate-log/page", headers=headers).json()
    assert logs["code"] == 0 and logs["data"]["list"]
    assert all("path" not in item for item in logs["data"]["list"])
    detail = client.get(f"{API}/operate-log/{logs['data']['list'][0]['id']}", headers=headers).json()
    assert detail["code"] == 0 and "path" in detail["data"] and "paramsDigest" in detail["data"]
    login_logs = client.get(f"{API}/login-log/page", headers=headers).json()
    assert login_logs["code"] == 0
    assert any(item["resultText"] for item in login_logs["data"]["list"])
    assert client.post(f"{API}/operate-log/export", headers=headers, json={}).json()["code"] == 0
    _notify()
    page = client.get(f"{API}/notify/page", headers=headers).json()
    assert page["code"] == 0
    failed = next(item for item in page["data"]["list"] if item["status"] == "FAILED")
    sent = next(item for item in page["data"]["list"] if item["status"] == "SENT")
    resent = client.post(f"{API}/notify/{failed['id']}/resend", headers=headers).json()
    assert resent["code"] == 0 and resent["data"]["status"] == "SENT"
    again = client.post(f"{API}/notify/{sent['id']}/resend", headers=headers).json()
    assert again["code"] == 1001
    assert client.put(f"{API}/tenant/1", headers=headers, json={"status": "DISABLED"}).json()["code"] == 1290
    packages = client.get(f"{API}/tenant-package/page", headers=headers, params={"pageNo": 1, "pageSize": 20}).json()
    used_row = next(item for item in packages["data"]["list"] if str(item["id"]) == "2")
    mismatch = client.request("DELETE", f"{API}/tenant-package/2", headers=headers, json={"confirmName": "不对"}).json()
    assert mismatch["code"] == 1293
    used = client.request("DELETE", f"{API}/tenant-package/2", headers=headers, json={"confirmName": used_row["packageName"]}).json()
    assert used["code"] == 1289
    _grant_tenant_query()
    foreign = auth(client, "t2_admin")
    denied = client.get(f"{API}/tenant/page", headers=foreign).json()
    assert denied["code"] == 1291
    changed = client.post(f"{AUTH}/password/change", headers=headers, json={"oldPassword": PASSWORD, "newPassword": "Abc123456"}).json()
    assert changed["code"] == 0, changed
    assert client.post(f"{AUTH}/login", json={"username": "u_admin", "password": "Abc123456"}).json()["code"] == 0
    sessions = client.get(f"{AUTH}/sessions/my", headers=headers).json()
    assert sessions["code"] == 0 and any(item["current"] for item in sessions["data"])
    current = next(item for item in sessions["data"] if item["current"])
    dropped = client.delete(f"{AUTH}/sessions/{current['sid']}", headers=headers).json()
    assert dropped["code"] == 0 and dropped["data"]["logout"] is True


def test_set_password_and_review_members(client):
    headers = auth(client, "u_admin")
    created = client.post(f"{API}/user", headers=headers, json=_user(headers, username="b2nopass", mobile="13800001008")).json()
    assert created["code"] == 0
    login = client.post(f"{AUTH}/login", json={"username": "b2nopass", "password": "Abc12345"}).json()
    token = {"Authorization": f"Bearer {login['data']['accessToken']}"}
    _clear_password("b2nopass")
    saved = client.post(f"{AUTH}/password/set", headers=token, json={"newPassword": "Abc123456"}).json()
    assert saved["code"] == 0, saved
    assert client.post(f"{AUTH}/login", json={"username": "b2nopass", "password": "Abc123456"}).json()["code"] == 0
    assert client.put(f"{API}/param", headers=headers, json={"paramKey": "content.review.level1.role", "value": "101"}).json()["code"] == 0
    from app.domains.system.admin_service import review_members

    with session_scope() as _session:
        with use_context(RequestContext(user_id=1002, tenant_id=1, data_scopes={"DEPT"}, dept_ids=[11])):
            dept_rows = review_members("content.review.level1.role")
        with use_context(RequestContext(user_id=1004, tenant_id=1, data_scopes={"SELF"}, dept_ids=[14])):
            self_rows = review_members("content.review.level1.role")
    assert any(int(row["id"]) == 1001 for row in dept_rows)
    assert self_rows == []


def _clear_reset(username: str) -> None:
    with session_scope(commit=True) as session:
        user = session.scalar(select(User).where(User.username == username))
        user.pwd_reset_required = 0


def _clear_password(username: str) -> None:
    with session_scope(commit=True) as session:
        user = session.scalar(select(User).where(User.username == username))
        user.password_hash = None


def _grant_tenant_query() -> None:
    with session_scope(commit=True) as session:
        menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:tenant:query"))
        with use_context(RequestContext(tenant_id=2, system=True, skip_tenant=True)):
            session.add(RoleMenu(role_id=206, menu_id=menu.id, tenant_id=2))


def _notify() -> None:
    with session_scope(commit=True) as session:
        session.add(NotifyRecord(event_type="EVT", biz_key="b2-fail", receiver_id=1001, channel="SITE", status="FAILED", title="失败", tenant_id=1))
        session.add(NotifyRecord(event_type="EVT", biz_key="b2-sent", receiver_id=1001, channel="SITE", status="SENT", title="成功", tenant_id=1))


def _find_perm(nodes, code):
    found = _find_node(nodes, lambda node: node.get("permCode") == code)
    return found["id"]


def _find_node(nodes, predicate):
    for node in nodes:
        if predicate(node):
            return node
        child = _find_node(node.get("children") or [], predicate)
        if child:
            return child
    return None
