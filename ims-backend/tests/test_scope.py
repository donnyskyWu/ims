import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import AuthError
from app.core import Base, SessionLocal, engine
from app.main import app, init_db
from app.models import Role, RolePerm, User, UserDept, UserRole, UserScope
from app.scope import DataScope, SPECS, gate, intersection_sql, refresh_user_scope, scope_values


client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0, res.json()
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_user(headers: dict, username: str, mobile: str) -> int:
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": username, "nickname": username, "mobile": mobile, "password": "Pass@123"},
    )
    assert created.json()["code"] == 0, created.json()
    return int(created.json()["data"]["id"])


def bind(user_id: int, *, key: str, scope: str, status: str = "ENABLED", perm: bool = True, depts: list[int] | None = None) -> None:
    db = SessionLocal()
    try:
        role = Role(role_name=key, role_key=key, data_scope=scope, status=status, source="MANUAL")
        db.add(role)
        db.flush()
        if perm:
            db.add(RolePerm(role_id=role.id, module_code="system", perm_code="system:user:query", perm_level="R"))
        db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        for dept_id in depts or []:
            db.add(UserDept(user_id=user_id, dept_id=dept_id, tenant_id=0))
        db.commit()
        refresh_user_scope(db, user_id)
        db.commit()
    finally:
        db.close()


def test_empty_pending_illegal_and_unregistered_are_1008():
    token = login()
    headers = auth(token)
    bare_id = create_user(headers, "bare", "13611110001")
    pending_id = create_user(headers, "pending", "13611110002")
    empty_id = create_user(headers, "emptyperm", "13611110003")
    bad_id = create_user(headers, "badscope", "13611110004")
    ip_id = create_user(headers, "iponly", "13611110005")
    bind(pending_id, key="b9-pending", scope="ALL", status="PENDING_CONFIG")
    bind(empty_id, key="b9-empty", scope="ALL", perm=False)
    bind(bad_id, key="b9-bad", scope="DEPT_AND_CHILD")
    bind(ip_id, key="b9-ip", scope="IP_GROUP")

    for username in ("bare", "pending", "emptyperm", "badscope", "iponly"):
        token = login(username, "Pass@123")
        denied = client.get("/admin-api/ims/system/user/page", headers=auth(token))
        assert denied.status_code == 403
        assert denied.json()["code"] == 1008
        assert denied.json()["msg"] == "无数据权限"
        assert denied.json()["data"] is None

    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=auth(login("bare", "Pass@123")))
    assert board.status_code == 200
    assert board.json()["code"] == 0

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").one()

        class Request:
            method = "GET"
            url = type("Url", (), {"path": "/admin-api/ims/not-registered"})()
            state = type("State", (), {})()

        try:
            gate(db, Request(), admin)
            raised = False
        except AuthError as exc:
            raised = exc.code == 1008 and exc.msg == "无数据权限"
        assert raised
    finally:
        db.close()
    assert bare_id and bad_id and ip_id


def test_missing_and_cross_tenant_both_say_unavailable():
    token = login()
    headers = auth(token)
    user_id = create_user(headers, "other-tenant", "13611110006")
    db = SessionLocal()
    try:
        row = db.get(User, user_id)
        row.tenant_id = 9
        db.commit()
    finally:
        db.close()
    missing = client.put(f"/admin-api/ims/system/user/999999", headers=headers, json={"nickname": "无"})
    cross = client.put(f"/admin-api/ims/system/user/{user_id}", headers=headers, json={"nickname": "跨租户"})
    assert missing.json() == cross.json()
    assert missing.json()["code"] == 1504
    assert missing.json()["msg"] == "资源不可用"
    assert missing.json()["data"] is None
    page = client.get("/admin-api/ims/system/user/page", headers=headers).json()["data"]["list"]
    assert all(row["username"] != "other-tenant" for row in page)


def test_dept_excludes_child_and_materializes_exact_scope():
    token = login()
    headers = auth(token)
    viewer_id = create_user(headers, "dept-viewer", "13611110007")
    peer_id = create_user(headers, "dept-peer", "13611110008")
    child_id = create_user(headers, "dept-child", "13611110009")
    bind(viewer_id, key="b9-dept", scope="DEPT", depts=[11])
    db = SessionLocal()
    try:
        db.add(UserDept(user_id=peer_id, dept_id=11, tenant_id=0))
        db.add(UserDept(user_id=child_id, dept_id=12, tenant_id=0))
        db.commit()
        assert scope_values(db, viewer_id) == {("DEPT", "11")}
        assert ("DEPT", "12") not in scope_values(db, viewer_id)
    finally:
        db.close()
    page = client.get("/admin-api/ims/system/user/page", headers=auth(login("dept-viewer", "Pass@123"))).json()["data"]
    names = {row["username"] for row in page["list"]}
    assert "dept-viewer" in names
    assert "dept-peer" in names
    assert "dept-child" not in names
    assert "admin" not in names
    logs = client.get("/admin-api/ims/system/operate-log/page", headers=auth(login("dept-viewer", "Pass@123")))
    assert logs.json()["code"] == 1008


def test_br212_intersects_creator_and_viewer_scopes():
    db = SessionLocal()
    try:
        db.execute(text("DROP TABLE IF EXISTS scope_probe"))
        db.execute(
            text(
                "CREATE TABLE scope_probe ("
                "id BIGINT PRIMARY KEY, tenant_id BIGINT, dept_id BIGINT, creator_id BIGINT, "
                "publish_state VARCHAR(16), share_owner_id BIGINT)"
            )
        )
        db.execute(
            text(
                "INSERT INTO scope_probe (id, tenant_id, dept_id, creator_id, publish_state, share_owner_id) VALUES "
                "(100, 0, 11, 101, 'PUBLISHED', 101),"
                "(101, 0, 12, 101, 'PUBLISHED', 101),"
                "(200, 0, 11, 105, 'PUBLISHED', 105)"
            )
        )
        db.add(UserScope(user_id=101, scope_type="DEPT", scope_value="11", tenant_id=0))
        db.add(UserScope(user_id=105, scope_type="SELF", scope_value="105", tenant_id=0))
        db.commit()

        def ids_for(scope: DataScope) -> set[int]:
            sql, params = intersection_sql(scope, 0, SPECS["scope_probe"])
            assert "parent" not in sql.lower()
            assert "recursive" not in sql.lower()
            rows = db.execute(text("SELECT id FROM scope_probe t WHERE 1=1" + sql), params).all()
            return {int(row[0]) for row in rows}

        hidden = ids_for(DataScope(kind="DEPT", user_id=102, dept_ids=[22]))
        same = ids_for(DataScope(kind="DEPT", user_id=103, dept_ids=[11]))
        broad = ids_for(DataScope(kind="ALL", user_id=104, dept_ids=[11]))
        assert hidden == set()
        assert same == {100}
        assert broad == {100, 101}
        assert 200 not in broad
    finally:
        db.execute(text("DROP TABLE IF EXISTS scope_probe"))
        db.commit()
        db.close()
