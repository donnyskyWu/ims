"""A 组：工程、响应、分页、序列化、OpenAPI、脚手架。"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.meta import mark
from app.core.config import load_settings, set_settings
from app.core.errors import StartupError
from app.core.fault import faults
from app.core.redis_client import RedisDown, configure_redis
from app.db.session import init_engine, session_scope
from app.main import create_app
from tests.conftest import auth


def _restore(app):
    settings = app.state.settings
    set_settings(settings)
    configure_redis(settings)
    init_engine(settings)


def test_ut_a01_01(tmp_path):
    raw = yaml.safe_load(Path("config/test.yaml").read_text(encoding="utf-8"))
    raw["jwt"].pop("secret", None)
    path = tmp_path / "no-secret.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(StartupError) as exc:
        load_settings(config_path=str(path))
    message = str(exc.value)
    assert "jwt.secret" in message
    assert "test-only" not in message


def test_ut_a01_02(app):
    settings = load_settings("prod")
    try:
        prod = create_app(settings)
        assert TestClient(prod).get("/docs").status_code == 404
    finally:
        _restore(app)


def test_ut_a01_03(app):
    settings = load_settings("dev")
    settings.redis_port = 1
    try:
        dev = create_app(settings)
        client = TestClient(dev)
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["data"]["redis"] == "MEMORY"
        logged = client.post("/admin-api/ims/auth/login", json={"username": "u_admin", "password": "Abc12345"})
        assert logged.json()["code"] == 0
    finally:
        _restore(app)


def test_ut_a01_04(app):
    settings = load_settings("test")
    settings.redis_port = 1
    try:
        with pytest.raises(StartupError) as exc:
            create_app(settings)
        assert "Redis" in str(exc.value)
    finally:
        _restore(app)


def test_ut_a01_05(app):
    router = APIRouter()

    @mark(perm="ims:demo:order:query", summary="坏前缀")
    def broken():
        return {}

    router.get("/demo/x", summary="坏前缀")(broken)
    router.prefix_override = ""
    try:
        with pytest.raises(StartupError) as exc:
            create_app(app.state.settings, extra_routers=[router])
        assert "路由前缀不符" in str(exc.value)
    finally:
        _restore(app)


def test_ut_a01_06(app):
    router = APIRouter()

    @mark(anonymous=True, summary="未登记匿名")
    def opened():
        return {}

    router.get("/admin-api/ims/demo/open", summary="未登记匿名")(opened)
    router.prefix_override = ""
    try:
        with pytest.raises(StartupError) as exc:
            create_app(app.state.settings, extra_routers=[router])
        assert "匿名路由不在白名单" in str(exc.value)
    finally:
        _restore(app)


def test_ut_a01_08(client, app):
    original = app.state.settings.football_live.port
    app.state.settings.football_live.port = 1
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "DEGRADED"
        assert response.json()["data"]["footballLive"] == "DOWN"
    finally:
        app.state.settings.football_live.port = original


def test_ut_a01_09(client, monkeypatch):
    def down():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.main.get_engine", down)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["data"]["db"] == "DOWN"


def test_ut_a01_12():
    from app.domains.system.model import User
    from app.services.jobs import JOBS
    from app.worker import ROUTES, model_classes, registered_jobs

    assert ROUTES == []
    names = {item.name for item in registered_jobs()}
    assert names == {item.name for item in JOBS}
    assert User in model_classes()
    assert User.__module__ == "app.domains.system.model"


def test_ut_a02_02(tmp_path):
    from tools.static_checks import check_handwritten_response

    root = tmp_path
    (root / "router.py").write_text('def ping():\n    return {"code": 0}\n', encoding="utf-8")
    problems = check_handwritten_response(root)
    assert problems
    assert "router.py" in problems[0]


def test_ut_a02_03(app):
    from app.core.error_codes import ErrorEntry

    try:
        with pytest.raises(StartupError) as exc:
            create_app(app.state.settings, extra_errors=[ErrorEntry(1211, "TRAIN", "号段不对", "toast")])
        assert "1211" in str(exc.value)
    finally:
        _restore(app)


def test_ut_a02_04(app):
    from app.core.error_codes import ErrorEntry

    try:
        with pytest.raises(StartupError) as exc:
            create_app(app.state.settings, extra_errors=[ErrorEntry(1214, "SYS", "重复", "toast")])
        assert "重复" in str(exc.value)
    finally:
        _restore(app)


def test_ut_a02_05():
    from app.core.error_codes import ErrorEntry, check_messages

    bad = check_messages([ErrorEntry(1001, "COMMON", "状态 PENDING_CONFIG 不可用", "toast")])
    assert bad


def test_ut_a02_06(client):
    headers = auth(client, "u_admin")
    response = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"amount": "abc"})
    body = response.json()
    assert body["code"] == 1001
    fields = {item["field"] for item in body["data"]["fieldErrors"]}
    assert {"amount", "name"} <= fields
    assert all(item["field"][0].islower() or item["field"][0].isupper() for item in body["data"]["fieldErrors"])


def test_ut_a02_07(client, caplog):
    headers = auth(client, "u_admin")
    faults.arm("demo.boom", RuntimeError("boom"))
    with caplog.at_level(logging.ERROR):
        response = client.get("/admin-api/ims/demo/order/get?id=1", headers=headers)
    body = response.json()
    assert body["code"] == 5007
    assert body["msg"] == "系统繁忙，请稍后再试"
    assert "boom" not in response.text
    assert "Traceback" not in response.text
    assert any("trace=" in rec.message or "trace" in rec.message.lower() for rec in caplog.records)


def test_ut_a02_08(client):
    headers = auth(client, "u_admin")
    faults.arm("demo.db", OperationalError("SELECT secret_sql", {}, Exception("secret_sql")))
    response = client.get("/admin-api/ims/demo/order/get?id=1", headers=headers)
    assert response.json()["code"] == 5001
    assert "secret_sql" not in response.text


def test_ut_a02_09(client):
    headers = auth(client, "u_admin")
    faults.arm("redis.down", RedisDown("down"))
    response = client.post("/admin-api/ims/auth/logout", headers=headers)
    assert response.json()["code"] == 5002


def test_ut_a02_10(client):
    headers = auth(client, "u_admin")
    response = client.get("/admin-api/ims/demo/order/get?id=999999", headers=headers)
    body = response.json()
    assert body["code"] == 1504
    assert body["msg"] == "资源不可用"
    assert not body["data"]


def _fill_orders(client, count):
    headers = auth(client, "u_admin")
    for index in range(count):
        created = client.post(
            "/admin-api/ims/demo/order/create",
            headers=headers,
            json={"name": f"批量{index}", "amount": f"{index}.00", "code": f"PG{index:03d}"},
        )
        assert created.json()["code"] == 0, created.text


def _ensure_total(client, total):
    headers = auth(client, "u_admin")
    current = client.get("/admin-api/ims/demo/order/page", headers=headers).json()["data"]["total"]
    if current < total:
        _fill_orders(client, total - current)


def test_ut_a03_01(client):
    _ensure_total(client, 25)
    headers = auth(client, "u_admin")
    body = client.get("/admin-api/ims/demo/order/page", headers=headers).json()
    assert body["data"]["pageNo"] == 1
    assert body["data"]["pageSize"] == 10
    assert len(body["data"]["list"]) == 10
    assert body["data"]["total"] == 25


def test_ut_a03_02(client):
    headers = auth(client, "u_admin")
    for query in ("pageSize=101", "pageSize=0", "pageNo=0", "pageNo=a"):
        body = client.get(f"/admin-api/ims/demo/order/page?{query}", headers=headers).json()
        assert body["code"] == 1001


def test_ut_a03_03(client):
    _ensure_total(client, 25)
    headers = auth(client, "u_admin")
    body = client.get("/admin-api/ims/demo/order/page?pageNo=3&pageSize=10", headers=headers).json()
    assert len(body["data"]["list"]) == 5


def test_ut_a03_04(client):
    headers = auth(client, "u_admin")
    for amount in ("1.00", "3.00", "2.00"):
        assert client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": amount, "amount": amount, "code": "A" + amount}).json()["code"] == 0
    body = client.get("/admin-api/ims/demo/order/page?sortField=amount&sortOrder=asc&pageSize=100", headers=headers).json()
    amounts = [item["amount"] for item in body["data"]["list"] if item["amount"] is not None]
    assert amounts == sorted(amounts)


def test_ut_a03_05(client):
    headers = auth(client, "u_admin")
    body = client.get("/admin-api/ims/demo/order/page?sortField=password", headers=headers).json()
    assert body["code"] == 1001
    assert body["data"]["fieldErrors"][0]["field"] == "sortField"


def test_ut_a03_06(client):
    headers = auth(client, "u_admin")
    body = client.get("/admin-api/ims/demo/order/page?sortField=amount;drop%20table%20x", headers=headers).json()
    assert body["code"] == 1001
    with session_scope() as session:
        session.execute(text("SELECT 1 FROM ims_demo_order"))


def test_ut_a04_01(client):
    headers = auth(client, "u_admin")
    ok = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "驼峰", "ownerUserId": "1001", "code": "CAMEL"})
    assert ok.json()["code"] == 0
    assert ok.json()["data"]["ownerUserId"] == "1001"
    ignored = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "蛇形", "owner_user_id": "1001", "code": "SNAKE"})
    assert ignored.json()["code"] == 0
    assert ignored.json()["data"]["ownerUserId"] in (None, "")
    assert "owner_user_id" not in ignored.json()["data"]


def test_ut_a04_02(client):
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "时区", "bizTime": "2026-10-12T02:00:00Z", "code": "TZ1"},
    )
    assert created.json()["code"] == 0, created.text
    assert created.json()["data"]["bizTime"] == "2026-10-12T10:00:00+08:00"
    with session_scope() as session:
        stored = session.execute(text("SELECT biz_time FROM ims_demo_order WHERE code='TZ1'")).scalar()
    assert str(stored).startswith("2026-10-12 10:00:00")


def test_ut_a04_03(client):
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "本地时间", "bizTime": "2026-10-12 10:00:00", "code": "TZ2"},
    )
    assert created.json()["data"]["bizTime"] == "2026-10-12T10:00:00+08:00"


def test_ut_a04_04(client):
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "日期", "bizDate": "2026/10/12"}).json()
    assert body["code"] == 1001


def test_ut_a04_05(client):
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "金额", "amount": "12.345"}).json()
    assert body["code"] == 1001


def test_ut_a04_06(client):
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "三分", "amount": 0.3, "code": "MONEY"}).json()
    assert body["data"]["amount"] == "0.30"


def test_ut_a04_07(client):
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "比例", "rate": 5, "code": "RATE"}).json()
    assert body["code"] == 0, body
    assert body["data"]["rate"] == 5
    with session_scope() as session:
        stored = session.execute(text("SELECT rate FROM ims_demo_order WHERE code='RATE'")).scalar()
    assert str(stored).startswith("0.0500")


def test_ut_a04_08(client):
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "枚举", "status": "Active"}).json()
    assert body["code"] == 1503, body


def test_ut_a05_01(app):
    from tools.api_gen import dump_openapi

    first = dump_openapi(app=app)
    second = dump_openapi(app=app)
    assert first == second


def test_ut_a05_02(tmp_path, app):
    from tools.api_gen import dump_openapi

    path = tmp_path / "openapi.json"
    dump_openapi(openapi_path=path, app=app)
    saved = path.read_text(encoding="utf-8")
    path.write_text(saved.replace("健康检查", "健康检查已改"), encoding="utf-8")
    fresh = dump_openapi(openapi_path=tmp_path / "next.json", app=app)
    assert path.read_text(encoding="utf-8") != (tmp_path / "next.json").read_text(encoding="utf-8")
    assert "健康检查" in str(fresh)


def test_ut_a05_03(app):
    from fastapi.routing import APIRoute

    route = APIRoute("/admin-api/ims/demo/nosummary", lambda: None, methods=["GET"])
    app.router.routes.append(route)
    try:
        from app.main import _validate_routes

        with pytest.raises(StartupError) as exc:
            _validate_routes(app)
        assert "摘要" in str(exc.value)
    finally:
        app.router.routes.remove(route)


def test_ut_a05_04(tmp_path):
    from tools.static_checks import check_frontend_paths

    target = tmp_path / "src" / "views"
    target.mkdir(parents=True)
    (target / "demo.ts").write_text('const url = "/admin-api/ims/demo"\n', encoding="utf-8")
    problems = check_frontend_paths(tmp_path)
    assert problems


def test_ut_a06_01(tmp_path):
    from tools.scaffold.generate import ScaffoldError, generate

    path = tmp_path / "bad.yaml"
    path.write_text(
        "table: ghost\nperm: ops:demo\nregistry: []\nfields:\n  - {name: status, type: dict, dict: missing_dict}\n",
        encoding="utf-8",
    )
    with pytest.raises(ScaffoldError) as exc:
        generate(path, tmp_path / "out")
    text = str(exc.value)
    assert "表未登记" in text
    assert "权限码前缀" in text
    assert "字典类型不存在" in text


def test_ut_a06_02(tmp_path):
    from tools.scaffold.generate import ScaffoldError, generate

    path = tmp_path / "noref.yaml"
    path.write_text(
        "table: ims_demo_item\nperm: ims:demo:item\nregistry: [ims_demo_item]\nfields:\n  - {name: owner_id, type: ref, target: ims_sys_user}\n",
        encoding="utf-8",
    )
    with pytest.raises(ScaffoldError) as exc:
        generate(path, tmp_path / "out")
    assert "删除策略" in str(exc.value)


def _item_yaml(path: Path):
    path.write_text(
        """
table: ims_demo_item
name: 示例项
perm: ims:demo:item
registry: [ims_demo_item]
fields:
  - {name: name, type: string, length: 40}
  - {name: owner_id, type: ref, target: ims_sys_user, on_delete: RESTRICT}
""".strip(),
        encoding="utf-8",
    )


def test_ut_a06_03(tmp_path):
    from tools.scaffold.generate import generate

    definition = tmp_path / "demo_item.yaml"
    _item_yaml(definition)
    out = tmp_path / "gen"
    generate(definition, out)
    names = {item.name for item in out.rglob("*") if item.is_file()}
    assert "model.py" in names
    assert "router.py" in names
    test = next(out.rglob("test_*.py"))
    text = test.read_text(encoding="utf-8")
    for token in ("1001", "1008", "1504", "1502"):
        assert token in text
    router = (out / "router.py").read_text(encoding="utf-8")
    for token in ("/page", "/create", "/update", "/delete"):
        assert token in router
    completed = __import__("subprocess").run([__import__("sys").executable, "-m", "pytest", str(test), "-q"], cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_ut_a06_04(tmp_path):
    from tools.scaffold.generate import generate

    definition = tmp_path / "demo_item.yaml"
    _item_yaml(definition)
    out = tmp_path / "gen"
    generate(definition, out)
    header = (out / "model.py").read_text(encoding="utf-8")
    assert "generator-version" in header
    assert "def-hash" in header
    assert "generated-at" in header


def test_ut_a06_05(tmp_path):
    from tools.scaffold.generate import generate

    definition = tmp_path / "demo_item.yaml"
    _item_yaml(definition)
    out = tmp_path / "gen"
    generate(definition, out)
    vue = next(out.rglob("*.vue")).read_text(encoding="utf-8")
    for token in ("PageHeader", "QueryBar", "DataTable", "Pagination", "v-perm"):
        assert token in vue
    assert "color:" not in vue
    assert "有效" not in vue


def test_ut_a06_06(tmp_path):
    from tools.scaffold.generate import generate

    definition = tmp_path / "demo_item.yaml"
    _item_yaml(definition)
    out = tmp_path / "gen"
    generate(definition, out)
    service = out / "service.py"
    service.write_text(service.read_text(encoding="utf-8") + "\n# hand edited\n", encoding="utf-8")
    before = service.read_text(encoding="utf-8")
    summary = generate(definition, out, force=False)
    assert service.read_text(encoding="utf-8") == before
    assert (out / "service.py.generated").exists() or "service.py" in str(summary)


def test_ut_a06_07(tmp_path):
    from tools.scaffold.generate import generate

    definition = tmp_path / "demo_item.yaml"
    _item_yaml(definition)
    out = tmp_path / "gen"
    generate(definition, out)
    service = out / "service.py"
    service.write_text(service.read_text(encoding="utf-8") + "\n# hand edited\n", encoding="utf-8")
    generate(definition, out, force=True)
    assert "hand edited" not in service.read_text(encoding="utf-8")
