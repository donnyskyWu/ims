"""B 组单测：UT-B01-01 ～ UT-B09-06，与 02-单测用例.md 第 B 节逐条对应。"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import BigInteger, Column, MetaData, String, insert, select, text
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog import SHARED_TABLES
from app.core.clock import freeze, now_naive
from app.core.context import system_context, use_context
from app.core.crypto import encrypt
from app.core.enums import CodeEnum, all_enum_classes
from app.core.errors import BizError, StartupError
from app.core.events import events
from app.core.fault import faults
from app.db.base import AuditBase, Base, audit_gaps
from app.db.refs import REGISTRY, RefSpec, refs_to, validate_refs
from app.db.repository import TABLES, Repository, bulk_check, register_tables
from app.db.session import SQL_LOG, session_scope, set_sql_log
from app.domains import all_models
from app.domains.auth.model import PositionRoleRule
from app.domains.demo.model import DemoNote, DemoOrder, DemoOrderItem
from app.domains.master.model import Company, LiveSession, PersonalAccount, PlatformAccount, Realname
from app.domains.message.model import Message
from app.domains.system.model import (
    ChangeLog,
    Dept,
    DictData,
    IntegrityIssue,
    Menu,
    OperateLog,
    Param,
    Role,
    RolePermDetail,
    User,
    UserDept,
    UserRole,
)
from app.domains.system.service import cache, dept_tree, init_tenant, other_cache
from app.services.integrity import run_scan
from app.services.mapping import bind_dingtalk
from tests.conftest import auth, login
from tests.stddata import D1, D11, D12, D2, DX, ROOT, U_ADMIN, U_DEPT, U_D12, U_FROZEN, U_IPG, U_RO

API = "/admin-api/ims"
BACKEND = Path(__file__).resolve().parents[1]
SCAN_TABLES = ["ims_demo_order", "ims_demo_order_item"]
_REPORT_TABLES = {
    "ims_sys_integrity_scan",
    "ims_sys_integrity_issue",
    "ims_sys_message",
    "ims_sys_notify_record",
}


def db(tenant: int = 1, commit: bool = False):
    from contextlib import contextmanager

    @contextmanager
    def _scope():
        with session_scope(commit=commit) as session:
            with use_context(system_context(tenant)):
                yield session

    return _scope()


def body(response):
    return response.json()


def call(client, method, path, username="u_admin", payload=None, headers=None):
    hdrs = headers if headers is not None else auth(client, username)
    kwargs = {"headers": hdrs}
    if payload is not None:
        kwargs["json"] = payload
    return body(getattr(client, method)(path, **kwargs))


def order_page(client, username="u_admin"):
    return body(client.get(f"{API}/demo/order/page?pageSize=100", headers=auth(client, username)))


def walk(nodes):
    for node in nodes or []:
        yield node
        yield from walk(node.get("children") or [])


def dept_nodes(client, username="u_admin", **query):
    suffix = "&".join(f"{key}={value}" for key, value in query.items())
    path = f"{API}/system/dept/tree" + (f"?{suffix}" if suffix else "")
    payload = call(client, "get", path, username)
    assert payload["code"] == 0, payload
    return {str(node["id"]): node for node in walk(payload["data"])}


def menu_names(nodes):
    return {node["name"] for node in walk(nodes)}


def _restore_refs():
    validate_refs(all_models())
    register_tables(all_models())


def _drop_gap(model):
    table = getattr(model, "__table__", None)
    if table is not None and table.name in Base.metadata.tables:
        Base.metadata.remove(table)
    dispose = getattr(Base.registry, "_dispose_cls", None)
    if dispose is not None:
        dispose(model)
    _restore_refs()


def _missing_enum_labels(classes):
    missing = []
    for enum_cls in classes:
        for item in enum_cls:
            label = cache.get_label(enum_cls.__dict_type__, item.value)
            if not label or not any("\u4e00" <= char <= "\u9fff" for char in label):
                missing.append(f"{enum_cls.__name__}.{item.value}")
    return missing


def _sqlite_alembic(tmp_path):
    from alembic.config import Config

    url = "sqlite:///" + (tmp_path / "b02.sqlite").as_posix()
    ini = tmp_path / "alembic.ini"
    text_body = (BACKEND / "alembic.ini").read_text(encoding="utf-8")
    ini.write_text(text_body, encoding="utf-8")
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg, url


def _business_digest(session) -> dict:
    found = {}
    for table in Base.metadata.sorted_tables:
        if table.name in _REPORT_TABLES:
            continue
        cols = ", ".join(f"IFNULL(CAST(`{column.name}` AS CHAR), '')" for column in table.columns)
        sql = f"SELECT COUNT(*), COALESCE(BIT_XOR(CRC32(CONCAT_WS('#', {cols}))), 0) FROM `{table.name}`"
        count, digest = session.execute(text(sql)).one()
        found[table.name] = f"{count}:{digest}"
    return found


def _plant_four(session):
    """4 类问题各 1 条，另加 100 条正常订单。"""
    disabled_dept = Dept(parent_id=ROOT, name="停用被引", source="LOCAL", status="ENABLED", path="/")
    session.add(disabled_dept)
    session.flush()
    disabled_dept.path = f"/{ROOT}/{disabled_dept.id}/"
    disabled_order = DemoOrder(name="停用引用", code="B9DIS", status="ACTIVE", dept_id=disabled_dept.id, owner_user_id=U_ADMIN)
    session.add(disabled_order)
    session.flush()
    disabled_dept.status = "DISABLED"
    orphan = DemoOrder(name="孤儿", code="B9ORP", status="ACTIVE", owner_user_id=999999)
    session.add(orphan)
    session.flush()
    with use_context(system_context(2)):
        foreign = Dept(parent_id=0, name="外租户部门", source="LOCAL", status="ENABLED", path="/")
        session.add(foreign)
        session.flush()
        foreign.path = f"/{foreign.id}/"
        foreign_id = foreign.id
    cross = DemoOrder(name="跨租户", code="B9X", status="ACTIVE", dept_id=foreign_id, owner_user_id=U_ADMIN)
    session.add(cross)
    parent = DemoOrder(name="漏级联", code="B9CAS", status="ACTIVE", dept_id=D1, owner_user_id=U_ADMIN)
    session.add(parent)
    session.flush()
    item = DemoOrderItem(order_id=parent.id, name="残留")
    session.add(item)
    session.flush()
    parent.deleted = parent.id
    normal = []
    for index in range(100):
        row = DemoOrder(name=f"正常{index}", code=f"B9N{index:03d}", status="ACTIVE", dept_id=D1, owner_user_id=U_ADMIN)
        session.add(row)
        session.flush()
        normal.append(row.id)
    session.flush()
    return {"orphan": orphan.id, "cross": cross.id, "disabled": disabled_order.id, "item": item.id, "normal": normal}


def test_ut_b01_01():
    class ims_demo_x:
        __tablename__ = "ims_demo_x"

    gaps = audit_gaps([ims_demo_x, *all_models()])
    assert "ims_demo_x" in gaps


def test_ut_b01_02(client):
    created = call(client, "post", f"{API}/demo/order/create", payload={"name": "审计", "code": "AUD1", "deptId": D1})
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    updated = call(client, "put", f"{API}/demo/order/update", payload={"id": ident, "name": "审计后"})
    assert updated["code"] == 0, updated
    with db() as session:
        row = session.get(DemoOrder, ident)
        assert row.creator == U_ADMIN
        assert row.updater == U_ADMIN
        assert row.create_time is not None
        assert row.update_time is not None
        assert row.tenant_id == 1


def test_ut_b01_03(client):
    with db(commit=True) as session:
        session.execute(text("DELETE FROM ims_demo_order WHERE id=5"))
        session.add(DemoOrder(id=5, name="五号", code="ID5", status="ACTIVE", dept_id=D1, owner_user_id=U_ADMIN))
        session.flush()
    removed = call(client, "delete", f"{API}/demo/order/delete?id=5")
    assert removed["code"] == 0, removed
    page = call(client, "get", f"{API}/demo/order/page?pageSize=100")
    assert page["code"] == 0, page
    assert all(str(item["id"]) != "5" for item in page["data"]["list"])
    with db() as session:
        deleted = session.execute(text("SELECT deleted FROM ims_demo_order WHERE id=5")).scalar()
        assert int(deleted) == 5


def test_ut_b01_04(client):
    first = call(client, "post", f"{API}/demo/order/create", payload={"name": "编码", "code": "C001"})
    assert first["code"] == 0, first
    assert call(client, "delete", f"{API}/demo/order/delete?id={int(first['data']['id'])}")["code"] == 0
    second = call(client, "post", f"{API}/demo/order/create", payload={"name": "编码重建", "code": "C001"})
    assert second["code"] == 0, second
    assert int(second["data"]["id"]) != int(first["data"]["id"])


def test_ut_b01_05(client):
    assert call(client, "post", f"{API}/demo/order/create", payload={"name": "编码", "code": "C001"})["code"] == 0
    duplicated = call(client, "post", f"{API}/demo/order/create", payload={"name": "编码重复", "code": "C001"})
    assert duplicated["code"] == 1001, duplicated
    assert any(item["field"] == "code" for item in duplicated["data"]["fieldErrors"])


def test_ut_b01_06():
    with db(commit=True) as session:
        row = DemoOrder(name="工人", code="WRK1", status="ACTIVE")
        session.add(row)
        session.flush()
        assert row.creator == 0


def test_ut_b02_01(tmp_path):
    from alembic import command
    from sqlalchemy import create_engine, inspect

    with db() as session:
        before = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    cfg, url = _sqlite_alembic(tmp_path)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        assert "ims_demo_order" in inspect(engine).get_table_names()
        command.downgrade(cfg, "base")
        assert "ims_demo_order" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        assert "ims_demo_order" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    with db() as session:
        after = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert after == before


def test_ut_b02_02(tmp_path):
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    cfg, url = _sqlite_alembic(tmp_path)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        reflected = MetaData()
        reflected.reflect(bind=engine, only=["ims_demo_order"])
        reflected.tables["ims_demo_order"].append_column(Column("company_extra", String(16)))
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), reflected)
    finally:
        engine.dispose()
    rendered = repr(diff)
    assert diff
    assert "company_extra" in rendered


def test_ut_b02_03(tmp_path):
    from tools.static_checks import check_create_all

    target = tmp_path / "boot.py"
    target.write_text("Base.metadata.create_all" + "(bind)\n", encoding="utf-8")
    problems = check_create_all(tmp_path)
    assert problems
    assert "create_all" in problems[0]


def test_ut_b02_04(tmp_path):
    from tools.static_checks import check_alter_startup

    app = tmp_path / "app"
    app.mkdir()
    (app / "main.py").write_text("stmt = 'ALTER TABLE ims_sys_user ADD x int'\n", encoding="utf-8")
    problems = check_alter_startup(tmp_path)
    assert problems
    assert "ALTER TABLE" in problems[0]


def test_ut_b02_05(tmp_path):
    from tools.static_checks import check_live_room_leak

    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "extra.py").write_text("op.create_table('live_room')\n", encoding="utf-8")
    problems = check_live_room_leak(tmp_path)
    assert problems
    assert "live_room" in problems[0]


def test_ut_b03_01(client):
    changed = call(client, "put", f"{API}/system/user/update/1005", payload={"id": 2000, "nickname": "改主键"})
    assert changed["code"] == 1211, changed
    with db() as session:
        assert session.get(User, 1005) is not None
        assert session.get(User, 1005).id == 1005
        assert session.get(User, 2000) is None


def test_ut_b03_02(client):
    for username in ("u_frozen", "u_resigned"):
        response = login(client, username)
        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 1216, payload


def test_ut_b03_03(client):
    created = call(
        client,
        "post",
        f"{API}/system/user/create",
        payload={"username": "never_login", "nickname": "未登录", "deptIds": [D1], "mainDeptId": D1, "password": "Abc12345"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db() as session:
        assert session.get(User, ident).last_login_time is None
    removed = call(client, "delete", f"{API}/system/user/delete?id={ident}")
    assert removed["code"] == 0, removed
    with db() as session:
        deleted = session.execute(text("SELECT deleted FROM ims_sys_user WHERE id=:id"), {"id": ident}).scalar()
        assert int(deleted) == ident


def test_ut_b03_04(client):
    created = call(
        client,
        "post",
        f"{API}/system/user/create",
        payload={"username": "ref_user", "nickname": "被引用", "deptIds": [D1], "mainDeptId": D1, "password": "Abc12345"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    order = call(client, "post", f"{API}/demo/order/create", payload={"name": "挂用户", "code": "REFU", "ownerUserId": ident})
    assert order["code"] == 0, order
    removed = call(client, "delete", f"{API}/system/user/delete?id={ident}")
    assert removed["code"] == 1502, removed


def test_ut_b03_05(client):
    with db() as session:
        ident = session.scalar(select(User.id).where(User.username == "u_resigned"))
    removed = call(client, "delete", f"{API}/system/user/delete?id={ident}")
    assert removed["code"] == 1502, removed
    restored = call(client, "put", f"{API}/system/user/update-status", payload={"id": ident, "status": "ACTIVE"})
    assert restored["code"] == 1001, restored


def test_ut_b03_06(client):
    first = login(client, "u_dept").json()["data"]["accessToken"]
    second = login(client, "u_dept").json()["data"]["accessToken"]
    assert first != second
    frozen = call(client, "put", f"{API}/system/user/update-status", payload={"id": U_DEPT, "status": "FROZEN"})
    assert frozen["code"] == 0, frozen
    for token in (first, second):
        response = client.get(f"{API}/demo/order/page", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["code"] == 1002
    assert events.items == []


def test_ut_b03_07(client):
    first = login(client, "u_dept").json()["data"]["accessToken"]
    second = login(client, "u_dept").json()["data"]["accessToken"]
    resigned = call(client, "put", f"{API}/system/user/update-status", payload={"id": U_DEPT, "status": "RESIGNED"})
    assert resigned["code"] == 0, resigned
    assert resigned["data"]["status"] == "RESIGNED"
    assert len(events.of("user.resigned")) == 1
    for token in (first, second):
        response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["code"] == 1002
    with db() as session:
        assert session.get(User, U_DEPT).status == "RESIGNED"


def test_ut_b03_08():
    with db() as session:
        user = session.get(User, U_DEPT)
        rows = list(session.scalars(select(UserDept).where(UserDept.user_id == U_DEPT)))
        mains = [row for row in rows if int(row.is_main) == 1]
        assert len(mains) == 1
        assert mains[0].dept_id == user.main_dept_id == D1


def test_ut_b03_09(client):
    updated = call(
        client,
        "put",
        f"{API}/system/user/update-depts",
        payload={"id": U_DEPT, "deptIds": [D1, D2], "mainDeptId": D2},
    )
    assert updated["code"] == 0, updated
    with db() as session:
        user = session.get(User, U_DEPT)
        rows = {row.dept_id: row for row in session.scalars(select(UserDept).where(UserDept.user_id == U_DEPT))}
        assert int(rows[D2].is_main) == 1
        assert int(rows[D1].is_main) == 0
        assert user.main_dept_id == D2


def test_ut_b03_10(client):
    assert call(
        client,
        "put",
        f"{API}/system/user/update-depts",
        payload={"id": U_DEPT, "deptIds": [D1, D2], "mainDeptId": D2},
    )["code"] == 0
    refused = call(client, "put", f"{API}/system/user/update-depts", payload={"id": U_DEPT, "deptIds": [D1]})
    assert refused["code"] == 1001, refused
    assert "请先指定其他主部门" in refused["msg"]


def test_ut_b03_11(client):
    moved = call(client, "put", f"{API}/system/user/update-depts", payload={"id": U_RO, "deptIds": []})
    assert moved["code"] == 0, moved
    with db() as session:
        user = session.get(User, U_RO)
        rows = list(session.scalars(select(UserDept).where(UserDept.user_id == U_RO)))
        assert user.main_dept_id == DX
        assert len(rows) == 1
        assert rows[0].dept_id == DX
        assert int(rows[0].is_main) == 1


def test_ut_b03_12(client):
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "D9停用", "parentId": ROOT})
    assert created["code"] == 0, created
    dept_id = int(created["data"]["id"])
    assert call(client, "put", f"{API}/system/dept/update-status", payload={"id": dept_id, "status": "DISABLED"})["code"] == 0
    refused = call(
        client,
        "put",
        f"{API}/system/user/update-depts",
        payload={"id": U_DEPT, "deptIds": [D1, D2, dept_id], "mainDeptId": D1},
    )
    assert refused["code"] == 1501, refused


def test_ut_b03_13():
    with db(commit=True) as session:
        bind_dingtalk(U_ADMIN, "dt_a")
        with pytest.raises(BizError) as exc:
            bind_dingtalk(U_DEPT, "dt_a")
        assert exc.value.code == 1001
        assert exc.value.msg == "该钉钉账号已绑定其他用户"


def test_ut_b03_14():
    with db(commit=True) as session:
        bind_dingtalk(U_ADMIN, "dt_a")
        with pytest.raises(BizError) as exc:
            bind_dingtalk(U_ADMIN, "dt_b")
        assert exc.value.code == 1001


def test_ut_b03_15(client):
    with db() as session:
        row = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == "SALES"))
        ident = row.id
    assert call(client, "put", f"{API}/system/dict/data/update", payload={"id": ident, "status": "DISABLED"})["code"] == 0
    refused = call(client, "put", f"{API}/system/user/update/{U_ADMIN}", payload={"positionCode": "SALES"})
    assert refused["code"] == 1503, refused
    with db() as session:
        assert session.get(User, U_ADMIN).position_code != "SALES"
    cache.local.clear()
    other_cache.local.clear()


def test_ut_b04_01(client):
    first = call(
        client,
        "post",
        f"{API}/system/role/create",
        payload={"name": "岗位角色甲", "roleKey": "pos_x", "positionCode": "ANCHOR"},
    )
    assert first["code"] == 0, first
    second = call(
        client,
        "post",
        f"{API}/system/role/create",
        payload={"name": "岗位角色乙", "roleKey": "pos_y", "positionCode": "ANCHOR"},
    )
    assert second["code"] == 1001, second


def test_ut_b04_02(client):
    created = call(client, "post", f"{API}/system/role/create", payload={"name": "系统来源", "roleKey": "sys_src", "source": "SYSTEM"})
    assert created["code"] == 1503, created


def test_ut_b04_03(client):
    created = call(client, "post", f"{API}/system/role/create", payload={"name": "有成员", "roleKey": "with_members"})
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db(commit=True) as session:
        session.add(UserRole(user_id=U_DEPT, role_id=ident, source="MANUAL"))
        session.add(UserRole(user_id=U_RO, role_id=ident, source="MANUAL"))
        session.flush()
    removed = call(client, "delete", f"{API}/system/role/delete?id={ident}")
    assert removed["code"] == 1502, removed
    assert any(item["entity"] == "成员" and item["count"] == 2 for item in removed["data"]["refs"])
    with db() as session:
        links = list(session.scalars(select(UserRole).where(UserRole.role_id == ident)))
        assert len(links) == 2


def test_ut_b04_04(client):
    created = call(
        client,
        "post",
        f"{API}/system/role/create",
        payload={"name": "被规则引用", "roleKey": "ruled", "positionCode": "ANCHOR"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db(commit=True) as session:
        session.add(PositionRoleRule(position_code="ANCHOR", role_id=ident, version=1, status="ENABLED"))
        session.flush()
    removed = call(client, "delete", f"{API}/system/role/delete?id={ident}")
    assert removed["code"] == 1502, removed


def test_ut_b04_05(client):
    removed = call(client, "delete", f"{API}/system/role/delete?id=103")
    assert removed["code"] == 1502, removed
    with db() as session:
        role = session.get(Role, 103)
        assert role is not None
        assert int(role.deleted) == 0
        assert role.role_key == "R3"


def test_ut_b04_06(client):
    by_key = call(client, "post", f"{API}/system/role/create", payload={"name": "自定义键", "roleKey": "R1"})
    assert by_key["code"] == 1001, by_key
    by_name = call(client, "post", f"{API}/system/role/create", payload={"name": "系统管理员", "roleKey": "custom_admin"})
    assert by_name["code"] == 1001, by_name


def test_ut_b04_07(client):
    stopped = call(client, "put", f"{API}/system/role/update-status", payload={"id": 202, "status": "DISABLED"})
    assert stopped["code"] == 0, stopped
    page = order_page(client, "u_dept")
    assert page["code"] == 1008, page
    with db() as session:
        logs = list(session.scalars(select(OperateLog).where(OperateLog.action == "停用角色")))
        assert logs


def test_ut_b04_08(client):
    for code in ("ops:demo:x", "ims:Demo:x"):
        created = call(client, "post", f"{API}/system/menu/create", payload={"name": code, "type": "BUTTON", "permCode": code})
        assert created["code"] == 1001, created


def test_ut_b04_09(client):
    created = call(client, "post", f"{API}/system/menu/create", payload={"name": "无权限码菜单", "type": "MENU"})
    assert created["code"] == 1001, created


def test_ut_b04_10(client):
    granted = call(client, "post", f"{API}/system/role/grant", payload={"roleId": 202, "permCodes": ["ims:demo:nope:query"]})
    assert granted["code"] == 1212, granted


def test_ut_b04_11(client):
    granted = call(
        client,
        "post",
        f"{API}/system/role/grant",
        payload={"roleId": 202, "permCodes": [], "details": [{"permCode": "ims:demo:order:query", "w": 1, "r": 0}]},
    )
    assert granted["code"] == 0, granted
    assert granted["data"]["details"][0]["r"] == 1
    with db() as session:
        row = session.scalar(select(RolePermDetail).where(RolePermDetail.role_id == 202, RolePermDetail.perm_code == "ims:demo:order:query"))
        assert row is not None
        assert int(row.r) == 1


def test_ut_b04_12(client):
    me = call(client, "get", f"{API}/auth/me", "t2_admin")
    assert me["code"] == 0, me
    names = menu_names(me["data"]["menus"])
    assert "系统管理" in names
    assert "示例域" not in names
    assert [node["name"] for node in me["data"]["menus"]] == ["系统管理"]


def test_ut_b04_13(client):
    me = call(client, "get", f"{API}/auth/me")
    assert me["code"] == 0, me
    with db() as session:
        stored = set(session.scalars(select(Menu.name).where(Menu.status == "ENABLED")))
    assert menu_names(me["data"]["menus"]) == stored
    assert "示例域" in stored
    assert "系统管理" in stored


def test_ut_b04_14(client):
    issued = login(client, "t2_admin").json()
    assert issued["code"] == 0, issued
    refresh = issued["data"]["refreshToken"]
    with db(tenant=2, commit=True) as session:
        from app.domains.system.model import Tenant

        tenant = session.get(Tenant, 2)
        tenant.expire_time = now_naive() - timedelta(minutes=1)
    again = login(client, "t2_admin").json()
    assert again["code"] == 1008, again
    assert "所属组织已停用" in again["msg"]
    refreshed = client.post(f"{API}/auth/refresh-token", json={"refreshToken": refresh})
    payload = refreshed.json()
    assert payload["code"] == 1008, payload
    assert "所属组织已停用" in payload["msg"]


def test_ut_b05_01(tmp_path):
    from tools.docs_gen import write_docs

    _restore_refs()
    write_docs(tmp_path)
    er = (tmp_path / "ER.md").read_text(encoding="utf-8")
    parsed = set()
    for line in er.splitlines():
        if "||--o{" not in line:
            continue
        left, right = line.split("||--o{")
        table, column = [part.strip() for part in right.split(":")]
        parsed.add((table, column.strip(), left.strip()))
    expected = {(table, column, spec.target) for (table, column), spec in REGISTRY.items()}
    assert parsed == expected


def test_ut_b05_02():
    _restore_refs()
    spec = REGISTRY[("ims_live_session", "football_room_id")]
    assert spec.external is True
    protected = {(table, column) for table, column, _spec in refs_to("live_room")}
    assert ("ims_live_session", "football_room_id") not in protected


def test_ut_b05_03():
    _restore_refs()
    names = {table.name for table in Base.metadata.sorted_tables}
    assert len(SHARED_TABLES) == 12
    for table, prefix, _title in SHARED_TABLES:
        assert table in names
        assert table.startswith(prefix)
        assert TABLES[table].__tablename__ == table


def test_ut_b06_01():
    from app.core.config import get_settings
    from app.main import create_app

    class GapCompany(AuditBase):
        __tablename__ = "ims_gap_company"
        company_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    try:
        with pytest.raises(StartupError) as exc:
            create_app(get_settings(), extra_models=[GapCompany])
        message = str(exc.value)
        assert "GapCompany" in message
        assert "company_id" in message
    finally:
        _drop_gap(GapCompany)


def test_ut_b06_02():
    from app.core.config import get_settings
    from app.main import create_app

    class GapPolicy(AuditBase):
        __tablename__ = "ims_gap_policy"
        company_id: Mapped[int | None] = mapped_column(BigInteger, info={"ref": RefSpec("ims_org_company", on_delete="")})

    try:
        with pytest.raises((StartupError, RuntimeError)) as exc:
            create_app(get_settings(), extra_models=[GapPolicy])
        assert "删除策略" in str(exc.value)
    finally:
        _drop_gap(GapPolicy)


def test_ut_b06_03():
    with db() as session:
        with pytest.raises(BizError) as exc:
            Repository(PlatformAccount).create(PlatformAccount(name="无实名", status="ENABLED", realname_id=999999))
        assert exc.value.code == 1500
        assert exc.value.data["field"] == "realnameId"


def test_ut_b06_04():
    with db() as session:
        row = Realname(name="R1", code="R1", status="ENABLED")
        session.add(row)
        session.flush()
        row.deleted = row.id
        session.flush()
        with pytest.raises(BizError) as exc:
            Repository(PlatformAccount).create(PlatformAccount(name="引用已删", status="ENABLED", realname_id=row.id))
        assert exc.value.code == 1500


def test_ut_b06_05():
    with db() as session:
        row = Realname(name="R2", code="R2", status="DISABLED")
        session.add(row)
        session.flush()
        with pytest.raises(BizError) as exc:
            Repository(PlatformAccount).create(PlatformAccount(name="引用停用", status="ENABLED", realname_id=row.id))
        assert exc.value.code == 1501


def test_ut_b06_06():
    with db() as session:
        row = Realname(name="停用可引", code="RDIS", status="DISABLED")
        session.add(row)
        session.flush()
        created = Repository(PersonalAccount).create(PersonalAccount(name="允许停用", status="ENABLED", realname_id=row.id, code="PALOW"))
        assert created.id
        assert created.realname_id == row.id


def test_ut_b06_07():
    with db() as session:
        with use_context(system_context(2)):
            row = Realname(name="R3", code="R3", status="ENABLED")
            session.add(row)
            session.flush()
            ident = row.id
        with pytest.raises(BizError) as exc:
            Repository(PlatformAccount).create(PlatformAccount(name="跨租户引用", status="ENABLED", realname_id=ident))
        assert exc.value.code == 1504


def test_ut_b06_08():
    with db() as session:
        person = Realname(name="被三人引用", code="RMANY", status="ENABLED")
        session.add(person)
        session.flush()
        for index in range(3):
            Repository(PlatformAccount).create(PlatformAccount(name=f"账号{index}", code=f"PA{index}", status="ENABLED", realname_id=person.id))
        with pytest.raises(BizError) as exc:
            Repository(Realname).soft_delete(person.id)
        assert exc.value.code == 1502
        assert exc.value.data["refs"] == [{"entity": "平台账号", "count": 3}]


def test_ut_b06_09():
    with db() as session:
        company = Company(name="被引用公司", code="CO1", status="ENABLED")
        session.add(company)
        session.flush()
        session.add(Realname(name="挂公司", code="RCO", status="ENABLED", company_id=company.id))
        session.flush()
        with pytest.raises(BizError) as exc:
            Repository(Company).disable(company.id)
        assert exc.value.code == 1502


def test_ut_b06_10():
    with db() as session:
        account = PlatformAccount(name="跨租户引用账号", code="PAX", status="ENABLED")
        Repository(PlatformAccount).create(account)
        for index in range(2):
            session.add(LiveSession(name=f"本租户{index}", status="ENABLED", account_id=account.id))
        session.flush()
        with use_context(system_context(2)):
            session.add(LiveSession(name="他租户异常", status="ENABLED", account_id=account.id))
            session.flush()
        with pytest.raises(BizError) as exc:
            Repository(PlatformAccount).soft_delete(account.id)
        assert exc.value.code == 1502
        assert sum(item["count"] for item in exc.value.data["refs"]) == 2


def test_ut_b06_11(client):
    created = call(client, "post", f"{API}/demo/order/create", payload={"name": "级联", "code": "CASC3"})
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db(commit=True) as session:
        for name in ("甲", "乙", "丙"):
            session.add(DemoOrderItem(order_id=ident, name=name))
        session.flush()
    assert call(client, "delete", f"{API}/demo/order/delete?id={ident}")["code"] == 0
    with db() as session:
        order_deleted = session.execute(text("SELECT deleted FROM ims_demo_order WHERE id=:id"), {"id": ident}).scalar()
        assert int(order_deleted) != 0
        items = list(
            session.scalars(
                select(DemoOrderItem).where(DemoOrderItem.order_id == ident).execution_options(include_deleted=True)
            )
        )
        assert len(items) == 3
        assert all(int(item.deleted) != 0 for item in items)


def test_ut_b06_12(client):
    created = call(client, "post", f"{API}/demo/order/create", payload={"name": "级联失败", "code": "CASCX"})
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db(commit=True) as session:
        for name in ("甲", "乙", "丙"):
            session.add(DemoOrderItem(order_id=ident, name=name))
        session.flush()
    faults.arm("cascade:ims_demo_order_item:2", RuntimeError("cascade"))
    removed = call(client, "delete", f"{API}/demo/order/delete?id={ident}")
    assert removed["code"] != 0
    with db() as session:
        order = session.get(DemoOrder, ident)
        assert order is not None and int(order.deleted) == 0
        items = list(session.scalars(select(DemoOrderItem).where(DemoOrderItem.order_id == ident)))
        assert len(items) == 3
        assert all(int(item.deleted) == 0 for item in items)


def test_ut_b06_13(client):
    created = call(client, "post", f"{API}/demo/order/create", payload={"name": "置空", "code": "NULL1"})
    ident = int(created["data"]["id"])
    with db(commit=True) as session:
        session.add(DemoNote(order_id=ident, content="置空备注"))
        session.flush()
    assert call(client, "delete", f"{API}/demo/order/delete?id={ident}")["code"] == 0
    with db() as session:
        note = session.scalar(select(DemoNote).where(DemoNote.content == "置空备注"))
        assert note.order_id is None
        logs = list(session.scalars(select(ChangeLog).where(ChangeLog.biz_type == "ims_demo_note", ChangeLog.reason == "SET_NULL_CASCADE")))
        assert len(logs) == 1


def test_ut_b06_14():
    with db(commit=True) as session:
        row = Realname(name="R4", code="R4", status="ENABLED")
        session.add(row)
        session.flush()
        ident = row.id
    barrier = threading.Barrier(2)
    outcome = {}

    def delete_side():
        with session_scope(commit=True) as _session:
            with use_context(system_context(1)):
                barrier.wait(timeout=10)
                try:
                    Repository(Realname).soft_delete(ident)
                    outcome["delete"] = 0
                except BizError as exc:
                    outcome["delete"] = exc.code

    def insert_side():
        with session_scope(commit=True) as _session:
            with use_context(system_context(1)):
                barrier.wait(timeout=10)
                try:
                    Repository(PlatformAccount).create(PlatformAccount(name="并发引用", code="CONC", status="ENABLED", realname_id=ident))
                    outcome["insert"] = 0
                except BizError as exc:
                    outcome["insert"] = exc.code

    threads = [threading.Thread(target=delete_side), threading.Thread(target=insert_side)]
    for item in threads:
        item.start()
    for item in threads:
        item.join(timeout=30)
    assert outcome.get("delete") == 0 and outcome.get("insert") == 1500 or outcome.get("delete") == 1502 and outcome.get("insert") == 0


def test_ut_b06_15():
    rows = [{"owner_user_id": U_ADMIN} for _index in range(10)]
    rows[2] = {"owner_user_id": 999999}
    rows[6] = {"owner_user_id": U_FROZEN}
    with db() as session:
        errors = bulk_check(rows, DemoOrder)
    assert len(errors) == 2
    by_row = {item["row"]: item for item in errors}
    assert by_row[3]["code"] == 1500
    assert by_row[7]["code"] == 1501
    assert "不存在" in by_row[3]["message"]
    assert "停用" in by_row[7]["message"]


def test_ut_b06_16(tmp_path):
    from tools.docs_gen import write_docs

    _restore_refs()
    write_docs(tmp_path)
    text_body = (tmp_path / "外键字典.md").read_text(encoding="utf-8")
    parsed = set()
    for line in text_body.splitlines():
        if not line.startswith("| ims_"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        parsed.add((parts[0], parts[1], parts[2], parts[3]))
    expected = {(table, column, spec.target, spec.on_delete) for (table, column), spec in REGISTRY.items()}
    assert parsed == expected
    again = tmp_path / "again"
    write_docs(again)
    assert (again / "外键字典.md").read_text(encoding="utf-8") == text_body


def test_ut_b07_01(client):
    bad_type = call(client, "post", f"{API}/system/dict/type/create", payload={"dictType": "DictUser", "name": "用户"})
    assert bad_type["code"] == 1001, bad_type
    bad_value = call(
        client,
        "post",
        f"{API}/system/dict/data/create",
        payload={"dictType": "dict_demo_status", "dictValue": "active", "dictLabel": "有效"},
    )
    assert bad_value["code"] == 1001, bad_value


def test_ut_b07_02(client):
    created = call(
        client,
        "post",
        f"{API}/system/dict/data/create",
        payload={"dictType": "dict_demo_status", "dictValue": "X", "dictLabel": "临时"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    assert call(client, "put", f"{API}/system/dict/data/update", payload={"id": ident, "status": "DISABLED"})["code"] == 0
    removed = call(client, "delete", f"{API}/system/dict/data/delete?id={ident}")
    assert removed["code"] == 1502, removed


def test_ut_b07_03(client):
    with db() as session:
        row = session.scalar(select(DictData).where(DictData.dict_type == "dict_user_status", DictData.dict_value == "ACTIVE"))
        ident = row.id
        assert int(row.is_builtin) == 1
    changed = call(client, "put", f"{API}/system/dict/data/update", payload={"id": ident, "dictValue": "WORKING"})
    assert changed["code"] == 1001, changed
    renamed = call(client, "put", f"{API}/system/dict/data/update", payload={"id": ident, "dictLabel": "在职人员", "colorType": "info"})
    assert renamed["code"] == 0, renamed
    with db() as session:
        fresh = session.get(DictData, ident)
        assert fresh.dict_value == "ACTIVE"
        assert fresh.dict_label == "在职人员"
        assert fresh.color_type == "info"
    cache.local.clear()
    other_cache.local.clear()


def test_ut_b07_04(client):
    created = call(
        client,
        "post",
        f"{API}/system/dict/data/create",
        payload={"dictType": "dict_demo_status", "dictValue": "PINK", "dictLabel": "粉色", "colorType": "pink"},
    )
    assert created["code"] == 1001, created


def test_ut_b07_05(client):
    created = call(
        client,
        "post",
        f"{API}/system/dict/data/create",
        payload={"dictType": "dict_demo_status", "dictValue": "USED", "dictLabel": "已用"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    order = call(client, "post", f"{API}/demo/order/create", payload={"name": "用字典", "code": "DUSED", "status": "USED"})
    assert order["code"] == 0, order
    removed = call(client, "delete", f"{API}/system/dict/data/delete?id={ident}")
    assert removed["code"] == 1502, removed


def test_ut_b07_06(client):
    updated = call(client, "put", f"{API}/system/param/update", payload={"paramKey": "no.such.key", "value": "1"})
    assert updated["code"] == 1213, updated


def test_ut_b07_07(client):
    for value in ("abc", "120"):
        updated = call(client, "put", f"{API}/system/param/update", payload={"paramKey": "perf.grade.excellent", "value": value})
        assert updated["code"] == 1001, updated


def test_ut_b07_08(client):
    secret = encrypt("sk-hidden")
    with db(commit=True) as session:
        session.add(Param(param_key="train_ai.api_key", name="培训密钥", group_name="培训", value_type="SECRET", value=secret))
        session.flush()
    listed = call(client, "get", f"{API}/system/param/list")
    assert listed["code"] == 0, listed
    found = next(item for item in listed["data"] if item["paramKey"] == "train_ai.api_key")
    assert found["value"] == "******"
    updated = call(client, "put", f"{API}/system/param/update", payload={"paramKey": "train_ai.api_key", "value": ""})
    assert updated["code"] == 0, updated
    with db() as session:
        stored = session.scalar(select(Param.value).where(Param.param_key == "train_ai.api_key"))
        assert stored == secret


def test_ut_b07_09(client):
    updated = call(client, "put", f"{API}/system/param/update", payload={"paramKey": "content.review.level1.role", "value": "999999"})
    assert updated["code"] == 1500, updated


def test_ut_b07_10(client):
    headers = auth(client, "u_admin")
    created = client.post(f"{API}/system/param/create", headers=headers, json={"paramKey": "new.key", "value": "1"})
    removed = client.delete(f"{API}/system/param/delete?id=1", headers=headers)
    for response in (created, removed):
        if response.status_code == 404:
            continue
        assert response.json()["code"] == 1008


def test_ut_b07_11(client):
    with db() as session:
        row = session.scalar(select(DictData).where(DictData.dict_type == "dict_demo_status", DictData.dict_value == "CLOSED"))
        ident = row.id
        old = row.dict_label
    cache.local.clear()
    other_cache.local.clear()
    start = datetime(2026, 10, 12, 9, 0, 0)
    freeze(start)
    with db() as session:
        assert other_cache.get_label("dict_demo_status", "CLOSED") == old
    renamed = call(client, "put", f"{API}/system/dict/data/update", payload={"id": ident, "dictLabel": "已关闭新"})
    assert renamed["code"] == 0, renamed
    with db() as session:
        assert cache.get_label("dict_demo_status", "CLOSED") == "已关闭新"
        assert other_cache.get_label("dict_demo_status", "CLOSED") == old
    freeze(start + timedelta(seconds=61))
    with db() as session:
        assert other_cache.get_label("dict_demo_status", "CLOSED") == "已关闭新"
    cache.local.clear()
    other_cache.local.clear()


def test_ut_b07_12():
    with db() as session:
        missing = _missing_enum_labels(all_enum_classes())
    assert missing == []


def test_ut_b07_13():
    class TempStatus(CodeEnum):
        __dict_type__ = "dict_demo_status"
        FOO = "FOO"

    with db() as session:
        missing = _missing_enum_labels([TempStatus])
    assert any("FOO" in item for item in missing)


def test_ut_b08_01():
    with db(tenant=3, commit=True) as session:
        init_tenant(3)
        rows = list(session.scalars(select(Dept)))
        by_name = {row.name: row for row in rows}
        assert "根部门" in by_name
        assert by_name["待分配"].source == "SYSTEM"
        assert by_name["待分配"].parent_id == by_name["根部门"].id


def test_ut_b08_02(client):
    renamed = call(client, "put", f"{API}/system/dept/update", payload={"id": DX, "name": "不能改"})
    moved = call(client, "put", f"{API}/system/dept/move", payload={"id": DX, "parentId": D2})
    stopped = call(client, "put", f"{API}/system/dept/update-status", payload={"id": DX, "status": "DISABLED"})
    removed = call(client, "delete", f"{API}/system/dept/delete?id={DX}")
    for payload in (renamed, moved, stopped, removed):
        assert payload["code"] == 1220, payload


def test_ut_b08_03(client):
    created = call(
        client,
        "post",
        f"{API}/system/org-sync/process",
        payload={"eventId": "dup-ding-100", "eventType": "dept_add", "dingtalkDeptId": 100, "name": "另一个市场部"},
    )
    assert created["code"] == 1001, created
    assert created["data"]["fieldErrors"][0]["field"] == "dingtalkDeptId"
    with db() as session:
        rows = list(session.scalars(select(Dept).where(Dept.dingtalk_dept_id == 100)))
        assert len(rows) == 1
        assert rows[0].id == D1


def test_ut_b08_04(client):
    nodes = dept_nodes(client)
    assert nodes[str(D1)]["memberCount"] == 5
    assert nodes[str(D1)]["directMemberCount"] == 3
    assert nodes[str(D11)]["memberCount"] == 2
    assert nodes[str(D12)]["memberCount"] == 1


def test_ut_b08_05(client):
    before = dept_nodes(client)[str(D11)]["memberCount"]
    with db(commit=True) as session:
        user = User(username="res_d11", nickname="离职一组", status="RESIGNED", main_dept_id=D11, source="LOCAL")
        session.add(user)
        session.flush()
        session.add(UserDept(user_id=user.id, dept_id=D11, is_main=1, source="LOCAL"))
        session.flush()
    assert dept_nodes(client)[str(D11)]["memberCount"] == before


def test_ut_b08_06(client):
    payload = call(client, "get", f"{API}/system/dept/tree?keyword=二组")
    assert payload["code"] == 0, payload
    names = menu_names(payload["data"])
    assert "技术部" not in names
    root = payload["data"][0]
    assert root["name"] == "根部门"
    market = next(node for node in root["children"] if node["name"] == "市场部")
    assert any(node["name"] == "市场二组" for node in market["children"])


def test_ut_b08_07(client):
    assert call(client, "put", f"{API}/system/dept/update-status", payload={"id": D2, "status": "DISABLED"})["code"] == 0
    hidden = dept_nodes(client)
    assert str(D2) not in hidden
    shown = dept_nodes(client, status="ALL")
    assert shown[str(D2)]["status"] == "DISABLED"


def test_ut_b08_08(client):
    refused = call(client, "get", f"{API}/system/dept/tree", "u_none")
    assert refused["code"] == 1008, refused


@pytest.mark.slow
def test_ut_b08_09():
    stamp = datetime(2026, 10, 12, 8, 0, 0)
    with db() as session:
        departments = []
        for index in range(2000):
            ident = 30000 + index
            departments.append(
                {
                    "id": ident,
                    "parent_id": ROOT,
                    "path": f"/{ROOT}/{ident}/",
                    "name": f"压{index}",
                    "sort": 0,
                    "status": "ENABLED",
                    "source": "LOCAL",
                    "local_orphan": 0,
                    "creator": 0,
                    "updater": 0,
                    "create_time": stamp,
                    "update_time": stamp,
                    "deleted": 0,
                    "tenant_id": 1,
                }
            )
        session.execute(insert(Dept), departments)
        users = []
        links = []
        for index in range(20000):
            ident = 80000 + index
            dept_id = 30000 + (index % 2000)
            users.append(
                {
                    "id": ident,
                    "username": f"p{index}",
                    "nickname": "压",
                    "status": "ACTIVE",
                    "main_dept_id": dept_id,
                    "source": "LOCAL",
                    "login_fail_count": 0,
                    "pwd_reset_required": 0,
                    "perm_version": 1,
                    "creator": 0,
                    "updater": 0,
                    "create_time": stamp,
                    "update_time": stamp,
                    "deleted": 0,
                    "tenant_id": 1,
                }
            )
            links.append(
                {
                    "user_id": ident,
                    "dept_id": dept_id,
                    "is_main": 1,
                    "source": "LOCAL",
                    "creator": 0,
                    "create_time": stamp,
                    "tenant_id": 1,
                }
            )
        for start in range(0, len(users), 1000):
            session.execute(insert(User), users[start : start + 1000])
            session.execute(insert(UserDept), links[start : start + 1000])
        session.flush()
        set_sql_log(True)
        started = datetime.now()
        tree = dept_tree()
        elapsed = (datetime.now() - started).total_seconds()
        statements = list(SQL_LOG)
        set_sql_log(False)
    assert tree
    assert elapsed <= 0.5
    assert len(statements) <= 3


def test_ut_b08_10(client):
    wide = call(client, "get", f"{API}/system/user/page?deptId={D1}&includeChildren=true&pageSize=100")
    narrow = call(client, "get", f"{API}/system/user/page?deptId={D1}&includeChildren=false&pageSize=100")
    assert wide["code"] == 0 and narrow["code"] == 0
    assert wide["data"]["total"] == 5
    assert narrow["data"]["total"] == 3


def test_ut_b08_11(client):
    updated = call(
        client,
        "put",
        f"{API}/system/user/update-depts",
        payload={"id": U_IPG, "deptIds": [D2, D11], "mainDeptId": D2},
    )
    assert updated["code"] == 0, updated
    page = call(client, "get", f"{API}/system/user/page?deptId={D11}&includeChildren=false&pageSize=100")
    assert page["code"] == 0, page
    assert "u_ipg" in {item["username"] for item in page["data"]["list"]}


def test_ut_b08_12(client):
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "市场三组", "parentId": D1})
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    assert created["data"]["source"] == "LOCAL"
    assert created["data"]["dingtalkDeptId"] in (None, "")
    assert created["data"]["path"] == f"/{ROOT}/{D1}/{ident}/"


def test_ut_b08_13(client):
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "市场一组", "parentId": D1})
    assert created["code"] == 1219, created


def test_ut_b08_14(client):
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "待分配下", "parentId": DX})
    assert created["code"] == 1220, created


def test_ut_b08_15(client):
    assert call(client, "put", f"{API}/system/dept/update-status", payload={"id": D2, "status": "DISABLED"})["code"] == 0
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "停用下新建", "parentId": D2})
    assert created["code"] == 1501, created


def test_ut_b08_16(client):
    updated = call(client, "put", f"{API}/system/dept/update", payload={"id": D11, "name": "一组"})
    assert updated["code"] == 0, updated
    assert updated["data"]["syncOverrideHint"] is True


def test_ut_b08_17(client):
    updated = call(client, "put", f"{API}/system/dept/update", payload={"id": D12, "name": "二组改名"})
    assert updated["code"] == 0, updated
    assert updated["data"]["syncOverrideHint"] is False


def test_ut_b08_18(client):
    into_child = call(client, "put", f"{API}/system/dept/move", payload={"id": D1, "parentId": D11})
    into_self = call(client, "put", f"{API}/system/dept/move", payload={"id": D1, "parentId": D1})
    assert into_child["code"] == 1218, into_child
    assert into_self["code"] == 1218, into_self


def test_ut_b08_19(client):
    moved = call(client, "put", f"{API}/system/dept/move", payload={"id": D11, "parentId": D12})
    assert moved["code"] == 1220, moved


def test_ut_b08_20(client):
    child = call(client, "post", f"{API}/system/dept/create", payload={"name": "D121", "parentId": D12})
    assert child["code"] == 0, child
    child_id = int(child["data"]["id"])
    moved = call(client, "put", f"{API}/system/dept/move", payload={"id": D12, "parentId": D2})
    assert moved["code"] == 0, moved
    with db() as session:
        parent = session.get(Dept, D12)
        kid = session.get(Dept, child_id)
        assert parent.path == f"/{ROOT}/{D2}/{D12}/"
        assert kid.path == f"/{ROOT}/{D2}/{D12}/{child_id}/"


def test_ut_b08_21(client):
    created = call(client, "post", f"{API}/system/dept/create", payload={"name": "市场二组", "parentId": D2})
    assert created["code"] == 0, created
    moved = call(client, "put", f"{API}/system/dept/move", payload={"id": D12, "parentId": D2})
    assert moved["code"] == 1219, moved


def test_ut_b08_22(client):
    removed = call(client, "delete", f"{API}/system/dept/delete?id={D1}")
    assert removed["code"] == 1502, removed
    children = next(item for item in removed["data"]["refs"] if item["entity"] == "下级部门")
    assert children["count"] == 2


def test_ut_b08_23(client):
    assert call(client, "put", f"{API}/system/user/update-status", payload={"id": U_D12, "status": "RESIGNED"})["code"] == 0
    removed = call(client, "delete", f"{API}/system/dept/delete?id={D12}")
    assert removed["code"] == 1502, removed
    people = next(item for item in removed["data"]["refs"] if item["entity"] == "人员")
    assert people["count"] == 1


def test_ut_b08_24(client):
    moved = call(client, "put", f"{API}/system/user/update-depts", payload={"id": U_D12, "deptIds": [DX], "mainDeptId": DX})
    assert moved["code"] == 0, moved
    removed = call(client, "delete", f"{API}/system/dept/delete?id={D12}")
    assert removed["code"] == 0, removed
    with db() as session:
        deleted = session.execute(text("SELECT deleted FROM ims_sys_dept WHERE id=:id"), {"id": D12}).scalar()
        assert int(deleted) == D12


def test_ut_b08_25(client):
    stopped = call(client, "put", f"{API}/system/dept/update-status", payload={"id": D1, "status": "DISABLED"})
    assert stopped["code"] == 1502, stopped


def test_ut_b08_26(client):
    assert call(client, "put", f"{API}/system/dept/update-status", payload={"id": D12, "status": "DISABLED"})["code"] == 0
    created = call(
        client,
        "post",
        f"{API}/system/user/create",
        payload={"username": "pick_d12", "nickname": "选停用", "deptIds": [D12], "mainDeptId": D12, "password": "Abc12345"},
    )
    assert created["code"] == 1501, created
    with db() as session:
        depts = set(session.scalars(select(UserDept.dept_id).where(UserDept.user_id == U_D12)))
        assert D12 in depts


def test_ut_b08_27(client):
    page = call(client, "get", f"{API}/system/user/page?pageSize=100", "u_ro")
    assert page["code"] == 0, page
    created = call(client, "post", f"{API}/system/dept/create", "u_ro", {"name": "只读不能建", "parentId": ROOT})
    assert created["code"] == 1008, created


def test_ut_b08_28(client):
    page = call(client, "get", f"{API}/system/user/page?deptId={ROOT}&includeChildren=true&pageSize=100", "u_dept")
    assert page["code"] == 0, page
    names = {item["username"] for item in page["data"]["list"]}
    assert names == {"u_admin", "u_dept", "u_overlap", "u_ipg", "u_self", "u_ro", "u_frozen"}
    assert "u_d11" not in names


def test_ut_b08_29(client):
    before = dept_nodes(client)[str(D12)]["memberCount"]
    created = call(
        client,
        "post",
        f"{API}/system/user/create",
        payload={"username": "two_dept", "nickname": "两部门", "deptIds": [D1, D12], "mainDeptId": D12, "password": "Abc12345"},
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with db() as session:
        rows = list(session.scalars(select(UserDept).where(UserDept.user_id == ident)))
        assert len(rows) == 2
        assert session.get(User, ident).main_dept_id == D12
        assert sum(int(row.is_main) for row in rows) == 1
        assert next(row.dept_id for row in rows if int(row.is_main) == 1) == D12
    assert dept_nodes(client)[str(D12)]["memberCount"] == before + 1


def test_ut_b08_30(client):
    page = call(client, "get", f"{API}/system/user/simple-page?pageSize=100", "u_none")
    assert page["code"] == 0, page
    assert page["data"]["list"]
    allowed = {"id", "nickname", "mainDeptId", "status"}
    for item in page["data"]["list"]:
        assert set(item) == allowed


def test_ut_b09_01(client):
    with db(commit=True) as session:
        planted = _plant_four(session)
    scanned = call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 1, "tables": SCAN_TABLES})
    assert scanned["code"] == 0, scanned
    issues = scanned["data"]["issues"]
    assert scanned["data"]["issueCount"] == 4
    assert len(issues) == 4
    found = {(item["issue_type"], item["record_id"]) for item in issues}
    assert found == {
        ("ORPHAN", planted["orphan"]),
        ("CROSS_TENANT", planted["cross"]),
        ("DISABLED_REF", planted["disabled"]),
        ("CASCADE_MISSED", planted["item"]),
    }
    reported = {item["record_id"] for item in issues}
    assert not reported & set(planted["normal"])


def test_ut_b09_02(client):
    headers = auth(client, "u_admin")
    with db(commit=True) as session:
        _plant_four(session)
    with db() as session:
        before = _business_digest(session)
    scanned = call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 1, "tables": SCAN_TABLES}, headers=headers)
    assert scanned["code"] == 0, scanned
    with db() as session:
        after = _business_digest(session)
    assert after == before


def test_ut_b09_03(client):
    start = datetime(2026, 10, 12, 11, 0, 0)
    freeze(start)
    with db(commit=True) as session:
        _plant_four(session)
    assert call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 1, "tables": SCAN_TABLES})["code"] == 0
    with db() as session:
        first = list(session.scalars(select(IntegrityIssue)))
        assert len(first) == 4
        seen = [row.last_seen_time for row in first]
    freeze(start + timedelta(seconds=30))
    again = call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 1, "tables": SCAN_TABLES})
    assert again["code"] == 0, again
    assert again["data"]["issueCount"] == 4
    with db() as session:
        rows = list(session.scalars(select(IntegrityIssue)))
        assert len(rows) == 4
        assert all(row.last_seen_time > min(seen) for row in rows)


def test_ut_b09_04(client):
    with db(commit=True) as session:
        for code in ("T2A", "T2B"):
            row = session.scalar(select(DemoOrder).where(DemoOrder.code == code).execution_options(skip_tenant=True))
            row.dept_id = None
        session.add(DemoOrder(name="T1孤儿", code="T1ORP", status="ACTIVE", owner_user_id=888888))
        session.flush()
        with use_context(system_context(2)):
            foreign = DemoOrder(name="T2孤儿", code="T2ORP", status="ACTIVE", owner_user_id=777777)
            session.add(foreign)
            session.flush()
            foreign_id = foreign.id
    set_sql_log(True)
    scanned = call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 2, "tables": ["ims_demo_order"]})
    logged = " ".join(SQL_LOG).replace(" ", "")
    set_sql_log(False)
    assert scanned["code"] == 0, scanned
    assert scanned["data"]["issueCount"] == 1
    assert scanned["data"]["issues"][0]["record_id"] == foreign_id
    assert "tenant_id=2" in logged


def test_ut_b09_05(client):
    with db(commit=True) as session:
        session.add(DemoOrder(name="通知孤儿", code="B9MSG", status="ACTIVE", owner_user_id=666666))
        session.flush()
    scanned = call(client, "post", f"{API}/system/integrity-scan/run", payload={"tenantId": 1, "tables": ["ims_demo_order"]})
    assert scanned["code"] == 0, scanned
    assert scanned["data"]["issueCount"] >= 1
    with db() as session:
        rows = list(session.scalars(select(Message).where(Message.receiver_id == U_ADMIN)))
        assert len(rows) == 1
        assert "巡检" in rows[0].title


def test_ut_b09_06():
    with db(commit=True) as session:
        session.add(LiveSession(name="外部房间", status="ENABLED", football_room_id=424242))
        session.flush()
        found = run_scan(1, ["ims_live_session"])
    assert found["issueCount"] == 0
    assert all(item["field"] != "football_room_id" for item in found["issues"])
