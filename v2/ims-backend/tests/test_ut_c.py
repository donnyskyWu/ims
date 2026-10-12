"""C 组：数据层。函数名与 02-单测用例.md UT-C01-01～UT-C04-10 一一对应。"""
from __future__ import annotations

import inspect
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from starlette.requests import Request

from app.api.meta import mark
from app.api.runtime import reset_current_request, set_current_request
from app.core.clock import freeze, unfreeze
from app.core.config import get_settings, set_settings
from app.core.context import system_context, use_context
from app.core.errors import BizError, StartupError
from app.core.events import events
from app.core.fault import faults
from app.core.pagination import Page
from app.core.redis_client import configure_redis
from app.core.security import hash_password
from app.core.sequence import format_code, session_code
from app.db.repository import Repository
from app.db.session import init_engine, session_scope
from app.domains.demo.model import DemoDeptOnly, DemoDoc, DemoNote, DemoOrder, DemoShare
from app.domains.demo.router import order_page
from app.domains.master.model import Realname
from app.domains.system.model import Menu, RoleMenu, Sequence, User, UserDept, UserRole
from app.main import create_app
from app.services.principal import build_principal
from app.services.tx_demo import outer_swallows, write_two
from tests.conftest import auth
from tests.stddata import D1, D12, D2, PASSWORD, T2_ADMIN, U_DEPT, U_IPG

API = "/admin-api/ims"
T1_CODES = {"OD1", "OD2", "OD11", "OD12", "OG1", "OSELF"}
WHEN = datetime(2026, 10, 12, 8, 0, 0)


def _json(response):
    assert response.status_code == 200, response.text
    return response.json()


def _codes(client, username) -> set[str]:
    body = _json(client.get(f"{API}/demo/order/page?pageSize=100", headers=auth(client, username)))
    assert body["code"] == 0, body
    return {item["code"] for item in body["data"]["list"]}


def _share_names(client, username) -> set[str]:
    body = _json(client.get(f"{API}/demo/share/page", headers=auth(client, username)))
    assert body["code"] == 0, body
    return {item["name"] for item in body["data"]}


def _add_user(session, ident: int, username: str, role_ids: list[int], dept_ids: list[int], main: int) -> None:
    session.add(
        User(
            id=ident,
            username=username,
            nickname=username,
            password_hash=hash_password(PASSWORD),
            status="ACTIVE",
            tenant_id=1,
            main_dept_id=main,
            source="LOCAL",
        )
    )
    session.flush()
    for role_id in role_ids:
        session.add(UserRole(user_id=ident, role_id=role_id, source="MANUAL", tenant_id=1))
    for dept_id in dept_ids:
        session.add(UserDept(user_id=ident, dept_id=dept_id, is_main=1 if dept_id == main else 0, source="LOCAL", tenant_id=1))
    session.flush()


def _restore(app):
    settings = app.state.settings
    set_settings(settings)
    configure_redis(settings)
    init_engine(settings)


def _count_code(code: str) -> int:
    with session_scope() as session:
        return int(session.execute(text("SELECT COUNT(*) FROM ims_demo_order WHERE code=:code"), {"code": code}).scalar() or 0)


def test_ut_c01_01():
    """先写订单再写备注，备注前注入异常，两表都回滚。"""
    faults.arm("tx.second", RuntimeError("b-fail"))
    with pytest.raises(RuntimeError):
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                write_two("ab")
    with session_scope() as session:
        with use_context(system_context(1)):
            assert session.scalar(select(DemoOrder).where(DemoOrder.code == "TX-ab")) is None
            assert session.scalar(select(DemoNote).where(DemoNote.content == "ab")) is None


def test_ut_c01_02():
    """内层异常被外层吞掉后，外层继续写入，最终仍整体回滚。"""
    faults.arm("tx.inner", RuntimeError("inner-fail"))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            outer_swallows("nest")
    with session_scope() as session:
        with use_context(system_context(1)):
            assert session.scalar(select(DemoOrder).where(DemoOrder.code == "OUT-nest")) is None
            assert session.scalar(select(DemoNote).where(DemoNote.content == "inner")) is None
            assert session.scalar(select(DemoNote).where(DemoNote.content == "after-catch")) is None


def test_ut_c01_03(tmp_path):
    from tools.static_checks import check_router_commit

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "router.py").write_text("def ping():\n    return data\n", encoding="utf-8")
    assert check_router_commit(clean) == []
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "router.py").write_text("def save():\n    session.commit()\n", encoding="utf-8")
    problems = check_router_commit(bad)
    assert problems
    assert any("提交事务" in item for item in problems)


def test_ut_c01_04():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = DemoOrder(name="已删", code="CDEL", status="ACTIVE")
            Repository(DemoOrder).create(row)
            ident = row.id
            Repository(DemoOrder).soft_delete(ident)
    with session_scope() as session:
        with use_context(system_context(1)):
            rows, total = Repository(DemoOrder).page(Page(1, 100), DemoOrder.code == "CDEL")
            assert rows == []
            assert total == 0
            listed, _ = Repository(DemoOrder).page(Page(1, 100))
            assert ident not in {item.id for item in listed}
            with pytest.raises(BizError) as exc:
                Repository(DemoOrder).get(ident)
            assert exc.value.code == 1504
            hidden = Repository(DemoOrder).list(DemoOrder.code == "CDEL")
            assert hidden == []
            found = Repository(DemoOrder).list(DemoOrder.code == "CDEL", include_deleted=True)
            assert len(found) == 1
            assert int(found[0].deleted) == ident


def test_ut_c01_05():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = DemoDoc(title="版本", version=3)
            Repository(DemoDoc).create(row)
            ident = row.id
            with pytest.raises(BizError) as exc:
                Repository(DemoDoc).update(row, before={"version": 2})
            assert exc.value.code == 1001
            assert "数据已被他人修改" in exc.value.msg
    with session_scope() as session:
        with use_context(system_context(1)):
            fresh = session.get(DemoDoc, ident)
            assert fresh.version == 3


def test_ut_c02_01(client):
    codes = _codes(client, "u_admin")
    assert "T2A" not in codes
    assert "T2B" not in codes
    assert codes == T1_CODES


def test_ut_c02_02(client):
    with session_scope() as session:
        with use_context(system_context(2)):
            ident = session.scalar(select(DemoOrder.id).where(DemoOrder.code == "T2A"))
    body = _json(client.get(f"{API}/demo/order/get?id={ident}", headers=auth(client, "u_admin")))
    assert body["code"] == 1504
    assert not body.get("data")


def test_ut_c02_03(client):
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=auth(client, "u_admin"),
            json={"name": "忽略租户", "code": "CTEN", "tenantId": 2},
        )
    )
    assert created["code"] == 0, created
    with session_scope() as session:
        tenant_id = session.execute(text("SELECT tenant_id FROM ims_demo_order WHERE code='CTEN'")).scalar()
    assert int(tenant_id) == 1


def test_ut_c02_04():
    """UT-C02-04 租户二持有菜单写权限，仍不能改平台菜单。"""
    from app.domains.system.model import Role

    with session_scope(commit=True) as session:
        with use_context(system_context(2)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:system:menu:create"))
            role = Role(
                name="租户二菜单",
                role_key="t2_menu_w",
                source="MANUAL",
                status="ENABLED",
                data_scope="ALL",
                is_standard=0,
                tenant_id=2,
            )
            session.add(role)
            session.flush()
            session.add(RoleMenu(role_id=role.id, menu_id=menu.id, tenant_id=2))
            session.add(UserRole(user_id=T2_ADMIN, role_id=role.id, source="MANUAL", tenant_id=2))
    with session_scope() as session:
        with use_context(system_context(1)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:system:dept:query"))
            ident = menu.id
            original = menu.name
        with use_context(system_context(2)):
            principal = build_principal(T2_ADMIN, 2)
        assert "ims:system:menu:create" in principal.perm_codes
        with use_context(principal):
            row = session.get(Menu, ident)
            row.name = original + "改"
            with pytest.raises(BizError) as exc:
                Repository(Menu).update(row)
            assert exc.value.code == 1008
    with session_scope() as session:
        with use_context(system_context(1)):
            assert session.get(Menu, ident).name == original


def test_ut_c02_05(client):
    assert _codes(client, "u_admin") == T1_CODES
    assert _codes(client, "u_dept") == {"OD1", "OD2"}
    assert _codes(client, "u_ipg") == {"OG1"}
    assert _codes(client, "u_self") == {"OSELF"}


def test_ut_c02_06(client):
    codes = _codes(client, "u_dept")
    assert "OD1" in codes
    assert "OD11" not in codes
    assert "OD12" not in codes


def test_ut_c02_07(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            _add_user(session, 3011, "u_both", [202, 204], [D2], D2)
            session.add(DemoOrder(name="OWN7", code="OWN7", dept_id=D1, owner_user_id=3011, status="ACTIVE"))
            session.flush()
    assert _codes(client, "u_both") == {"OD2", "OWN7"}


def test_ut_c02_08(client):
    admin = auth(client, "u_admin")
    scoped = _json(client.put(f"{API}/system/role/data-scope", headers=admin, json={"id": 202, "dataScope": ""}))
    assert scoped["code"] == 0, scoped
    page = _json(client.get(f"{API}/demo/order/page?pageSize=100", headers=admin))
    ident = page["data"]["list"][0]["id"]
    dept = auth(client, "u_dept")
    listed = _json(client.get(f"{API}/demo/order/page?pageSize=100", headers=dept))
    assert listed["code"] == 0, listed
    assert listed["data"]["list"] == []
    assert listed["data"]["total"] == 0
    got = _json(client.get(f"{API}/demo/order/get?id={ident}", headers=dept))
    assert got["code"] == 1504
    created = _json(client.post(f"{API}/demo/order/create", headers=dept, json={"name": "空范围", "code": "CEMPTY"}))
    assert created["code"] == 1008


def test_ut_c02_09():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(DemoDeptOnly(name="仅部门", dept_id=D1))
            session.flush()
    with session_scope() as session:
        with use_context(system_context(1)):
            visible = Repository(DemoDeptOnly).list()
            principal = build_principal(U_IPG, 1)
        assert visible
        assert principal.data_scopes == {"IP_GROUP"}
        with use_context(principal):
            assert Repository(DemoDeptOnly).list() == []


def test_ut_c02_10(client):
    headers = auth(client, "u_admin")
    updated = _json(client.put(f"{API}/system/role/update-status", headers=headers, json={"id": 101, "status": "DISABLED"}))
    assert updated["code"] == 0, updated
    listed = _json(client.get(f"{API}/demo/order/page", headers=headers))
    assert listed["code"] == 1008
    assert not listed.get("data")


def test_ut_c02_11(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(UserDept(user_id=U_DEPT, dept_id=D12, is_main=0, source="LOCAL", tenant_id=1))
    codes = _codes(client, "u_dept")
    assert "OD12" in codes
    assert "OD1" in codes
    assert "OD2" in codes


def test_ut_c02_12(app):
    class DemoNoScope:
        pass

    router = APIRouter()

    @mark(perm="ims:demo:order:query", scope_model=DemoNoScope, summary="未声明范围")
    def bare():
        return {}

    router.get("/admin-api/ims/demo/bare-scope", summary="未声明范围")(bare)
    router.prefix_override = ""
    try:
        with pytest.raises(StartupError) as exc:
            create_app(app.state.settings, extra_routers=[router])
        assert "数据范围模型未声明范围字段" in str(exc.value)
        assert "DemoNoScope" in str(exc.value)
    finally:
        _restore(app)


def test_ut_c02_13(tmp_path):
    from tools.static_checks import check_manual_tenant

    clean = tmp_path / "clean"
    (clean / "app" / "services").mkdir(parents=True)
    (clean / "app" / "services" / "ok.py").write_text("rows = session.scalars(select(Order))\n", encoding="utf-8")
    assert check_manual_tenant(clean) == []
    bad = tmp_path / "bad"
    (bad / "app" / "services").mkdir(parents=True)
    (bad / "app" / "services" / "order.py").write_text(
        "def load(stmt):\n    return stmt.where(Order.tenant_id == 1)\n",
        encoding="utf-8",
    )
    problems = check_manual_tenant(bad)
    assert problems
    assert any("租户" in item for item in problems)


def test_ut_c02_14(app):
    from app.domains.demo.error_router import router as error_router
    from app.main import MOUNTS, _iter_routes

    exported = set()
    for path, route in _iter_routes(app):
        meta = getattr(getattr(route, "endpoint", None), "__ims_meta__", None) or {}
        if not meta.get("login_only"):
            continue
        for method in getattr(route, "methods", None) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            exported.add((method, path))

    prefixes: dict[str, str] = {}
    for prefix, router in [*MOUNTS, ("/admin-api/ims/demo", error_router)]:
        for route in router.routes:
            module = inspect.getmodule(route.endpoint)
            file = str(Path(inspect.getfile(module)).resolve())
            prefixes.setdefault(file, prefix)
    declared = set()
    mark_re = re.compile(r"@mark\((.*?)\)\s*def\s+(\w+)\(", re.S)
    route_re = re.compile(r"""router\.(get|post|put|delete|patch)\(\s*["']([^"']+)["'][^\n]*\)\((\w+)\)""")
    for file, prefix in prefixes.items():
        source = Path(file).read_text(encoding="utf-8")
        names = {name for args, name in mark_re.findall(source) if re.search(r"login_only\s*=\s*True", args)}
        for method, path, name in route_re.findall(source):
            if name in names:
                declared.add((method.upper(), prefix + path))
    root = Path(__file__).resolve().parents[1] / "app"
    for file in root.rglob("*.py"):
        if "login_only=True" in file.read_text(encoding="utf-8"):
            assert str(file.resolve()) in prefixes
    assert exported
    assert ("GET", "/admin-api/ims/auth/me") in exported
    assert ("GET", "/admin-api/ims/demo/order/page") not in exported
    assert exported == declared


def test_ut_c02_15(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            _add_user(session, 3012, "u_pub", [202], [D1], D1)
            _add_user(session, 3013, "u_view_a", [202], [D1], D1)
    created = _json(client.post(f"{API}/demo/share/create", headers=auth(client, "u_pub"), json={"name": "发布快照", "deptId": D1}))
    assert created["code"] == 0, created
    assert "发布快照" in _share_names(client, "u_view_a")
    assert "发布快照" not in _share_names(client, "u_ro")


def test_ut_c02_16(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            _add_user(session, 3012, "u_pub", [202], [D1], D1)
            _add_user(session, 3013, "u_view_a", [202], [D1], D1)
    created = _json(client.post(f"{API}/demo/share/create", headers=auth(client, "u_pub"), json={"name": "发布快照", "deptId": D1}))
    assert created["code"] == 0, created
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.get(User, 3012)
            for link in list(session.scalars(select(UserDept).where(UserDept.user_id == 3012))):
                session.delete(link)
            session.flush()
            session.add(UserDept(user_id=3012, dept_id=D2, is_main=1, source="LOCAL", tenant_id=1))
            user.main_dept_id = D2
            share = session.scalar(select(DemoShare).where(DemoShare.name == "发布快照"))
            assert D1 in (share.publish_scope or {}).get("deptIds", [])
            assert D2 not in (share.publish_scope or {}).get("deptIds", [])
    with session_scope() as session:
        with use_context(system_context(1)):
            moved = build_principal(3012, 1)
    assert set(moved.dept_ids) == {D2}
    assert "发布快照" in _share_names(client, "u_view_a")


def test_ut_c02_17():
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/admin-api/ims/demo/order/page",
        "raw_path": b"/admin-api/ims/demo/order/page",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 9),
        "server": ("testserver", 80),
    }
    request = Request(scope)
    request.state.trace_id = "ut-c02-17"
    request.state.client_ip = "127.0.0.1"
    token = set_current_request(request)
    try:
        response = order_page()
    finally:
        reset_current_request(token)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["code"] == 1008
    assert payload["data"] is None


def test_ut_c02_18(client, caplog):
    faults.arm("scope.calc", RuntimeError("范围计算失败"))
    with caplog.at_level(logging.ERROR, logger="ims.scope"):
        body = _json(client.get(f"{API}/demo/order/page", headers=auth(client, "u_admin")))
    assert body["code"] == 1008
    assert not body.get("data")
    scoped = [record for record in caplog.records if record.name == "ims.scope"]
    assert len(scoped) == 1


def test_ut_c03_01(client):
    plain = "110101199001011234"
    headers = auth(client, "u_admin")
    first = _json(client.post(f"{API}/demo/order/create", headers=headers, json={"name": "证件一", "code": "IDC1", "idCard": plain}))
    second = _json(client.post(f"{API}/demo/order/create", headers=headers, json={"name": "证件二", "code": "IDC2", "idCard": plain}))
    assert first["code"] == 0, first
    assert second["code"] == 0, second
    with session_scope() as session:
        rows = session.execute(text("SELECT id_card, id_card_hash FROM ims_demo_order WHERE code IN ('IDC1','IDC2') ORDER BY code")).all()
    assert len(rows) == 2
    ciphers = [row[0] for row in rows]
    hashes = [row[1] for row in rows]
    assert all(item != plain and plain not in str(item) for item in ciphers)
    assert ciphers[0] != ciphers[1]
    assert hashes[0] == hashes[1]
    assert hashes[0]


def test_ut_c03_02(client):
    plain = "110101199001011234"
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=auth(client, "u_admin"),
            json={"name": "旧密钥", "code": "IDOLD", "idCard": plain},
        )
    )
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    with session_scope() as session:
        stored = session.execute(text("SELECT id_card FROM ims_demo_order WHERE id=:id"), {"id": ident}).scalar()
    assert str(stored).startswith("v1:")
    settings = get_settings()
    original = settings.field_key
    settings.field_key = settings.field_keys["v2"]
    try:
        with session_scope() as session:
            with use_context(system_context(1)):
                row = session.get(DemoOrder, ident)
                assert row.id_card == plain
    finally:
        settings.field_key = original


def test_ut_c03_03(client):
    headers = auth(client, "u_admin")
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=headers,
            json={"name": "脱敏", "code": "IDMASK", "idCard": "110101199001011234", "mobile": "13812345678"},
        )
    )
    assert created["code"] == 0, created
    ident = created["data"]["id"]
    body = _json(client.get(f"{API}/demo/order/get?id={ident}", headers=auth(client, "u_ro")))
    assert body["code"] == 0, body
    assert body["data"]["idCard"] == "110***********1234"
    assert body["data"]["mobile"] == "138****5678"


def test_ut_c03_04(client):
    headers = auth(client, "u_admin")
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=headers,
            json={"name": "明文", "code": "IDPLAIN", "idCard": "110101199001011234", "mobile": "13812345678"},
        )
    )
    assert created["code"] == 0, created
    ident = created["data"]["id"]
    body = _json(client.get(f"{API}/demo/order/get?id={ident}", headers=headers))
    assert body["code"] == 0, body
    assert body["data"]["idCard"] == "110101199001011234"
    assert body["data"]["mobile"] == "13812345678"


def test_ut_c03_05(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            _add_user(session, 3014, "u_r9", [109], [D1], D1)
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=auth(client, "u_admin"),
            json={"name": "成本", "code": "COST1", "cost": "12.30"},
        )
    )
    assert created["code"] == 0, created
    reader = auth(client, "u_r9")
    me = _json(client.get(f"{API}/auth/me", headers=reader))
    assert "ims:demo:order:cost-plain" not in me["data"]["permCodes"]
    body = _json(client.get(f"{API}/demo/order/get?id={created['data']['id']}", headers=reader))
    assert body["code"] == 0, body
    assert body["data"]["cost"] == "***"


def test_ut_c03_06(client):
    created = _json(
        client.post(
            f"{API}/demo/order/create",
            headers=auth(client, "u_admin"),
            json={"name": "导出脱敏", "code": "IDEXP", "idCard": "110101199001011234", "mobile": "13812345678"},
        )
    )
    assert created["code"] == 0, created
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:demo:order:export"))
            session.add(RoleMenu(role_id=205, menu_id=menu.id, tenant_id=1))
    reader = auth(client, "u_ro")
    exported = _json(client.post(f"{API}/demo/order/export", headers=reader, json={}))
    assert exported["code"] == 0, exported
    downloaded = _json(client.get(f"{API}/export-task/download?id={exported['data']['id']}", headers=reader))
    assert downloaded["code"] == 0, downloaded
    content = downloaded["data"]["content"]
    assert "110***********1234" in content
    assert "138****5678" in content
    assert "110101199001011234" not in content
    assert "13812345678" not in content


def test_ut_c04_01():
    def one(_index: int) -> str:
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                return format_code("CA", WHEN)

    with ThreadPoolExecutor(max_workers=100) as pool:
        codes = list(pool.map(one, range(100)))
    assert len(codes) == 100
    assert len(set(codes)) == 100
    assert all(code.startswith("CA20261012") for code in codes)
    assert sorted(int(code[10:]) for code in codes) == list(range(1, 101))


def test_ut_c04_02():
    try:
        freeze(datetime(2026, 10, 12, 23, 59, 59))
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                first = format_code("CA")
        freeze(datetime(2026, 10, 13, 0, 0, 1))
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                second = format_code("CA")
    finally:
        unfreeze()
    assert first == "CA202610120001"
    assert second == "CA202610130001"


def test_ut_c04_03():
    import app.core.sequence as sequence

    real = sequence.get_redis

    def down():
        raise ConnectionError("redis down")

    sequence.get_redis = down
    try:
        codes = []
        for _ in range(3):
            with session_scope(commit=True) as session:
                with use_context(system_context(1)):
                    codes.append(format_code("CA", WHEN))
    finally:
        sequence.get_redis = real
    assert len(set(codes)) == 3
    with session_scope() as session:
        with use_context(system_context(1)):
            row = session.scalar(select(Sequence).where(Sequence.rule_name == "CA", Sequence.seq_date == "20261012", Sequence.group_key == ""))
    assert row is not None
    assert int(row.current_value) == 3
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            nxt = format_code("CA", WHEN)
    assert nxt not in codes
    assert int(nxt[10:]) == 4


def test_ut_c04_04():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            code = session_code("DOUYIN", WHEN)
    assert code == "IMS20261012DYS0001"
    assert len(code) == 18


def test_ut_c04_05():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(Sequence(rule_name="SESSION", seq_date="20261012", group_key="DYS", current_value=9999))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            code = session_code("DOUYIN", WHEN)
    assert code == "IMS20261012DYS10000"
    assert len(code) == 19
    published = events.of("seq.p2")
    assert len(published) == 1
    assert published[0]["payload"]["value"] == 10000
    assert published[0]["payload"]["platform"] == "DOUYIN"


def test_ut_c04_06():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            douyin = session_code("DOUYIN", WHEN)
            kuaishou = session_code("KUAISHOU", WHEN)
    assert douyin == "IMS20261012DYS0001"
    assert kuaishou == "IMS20261012KSH0001"
    assert douyin[-4:] == "0001"
    assert kuaishou[-4:] == "0001"


def test_ut_c04_07(client):
    headers = auth(client, "u_admin")
    headers["X-Client-Token"] = "c-once"
    payload = {"name": "只一单", "code": "CONCE"}
    first = _json(client.post(f"{API}/demo/order/echo", headers=headers, json=payload))
    second = _json(client.post(f"{API}/demo/order/echo", headers=headers, json=payload))
    assert first["code"] == 0, first
    assert second == first
    assert _count_code("CONCE") == 1


def test_ut_c04_08(client):
    body = _json(client.post(f"{API}/demo/order/echo", headers=auth(client, "u_admin"), json={"name": "无令牌", "code": "CNOTOK"}))
    assert body["code"] == 1001
    assert body["data"]["fieldErrors"][0]["field"] == "xClientToken"
    assert _count_code("CNOTOK") == 0


def test_ut_c04_09(app):
    first_client = TestClient(app)
    second_client = TestClient(app)
    headers = auth(first_client, "u_admin")
    headers["X-Client-Token"] = "c-delay"
    payload = {"name": "延迟回放", "code": "CDELAY", "testDelayMs": 2000}
    state: dict = {}

    def run_first():
        state["a"] = first_client.post(f"{API}/demo/order/echo", headers=headers, json=payload)
        state["a_done"] = time.perf_counter()

    def run_second():
        time.sleep(1)
        state["b_start"] = time.perf_counter()
        state["b"] = second_client.post(f"{API}/demo/order/echo", headers=headers, json=payload)

    started = time.perf_counter()
    left = threading.Thread(target=run_first)
    right = threading.Thread(target=run_second)
    left.start()
    right.start()
    left.join()
    right.join()
    elapsed = time.perf_counter() - started
    first = _json(state["a"])
    second = _json(state["b"])
    assert first["code"] == 0, first
    assert second == first
    assert state["b_start"] < state["a_done"]
    assert elapsed < 3.5
    assert _count_code("CDELAY") == 1


def test_ut_c04_10(client):
    headers = auth(client, "u_admin")
    headers["X-Client-Token"] = "c-1500"
    payload = {"name": "缺失实名", "code": "C1500", "realnameId": 999999}
    first = _json(client.post(f"{API}/demo/order/echo", headers=headers, json=payload))
    assert first["code"] == 1500
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(Realname(id=999999, name="补录", code="RN999", status="ENABLED"))
    second = _json(client.post(f"{API}/demo/order/echo", headers=headers, json=payload))
    assert second == first
    assert second["code"] == 1500
    assert _count_code("C1500") == 0
