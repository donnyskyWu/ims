"""H 组单测，编号与 B0a「02-单测用例」H 节逐条对应。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select, text

from app.core.clock import advance, freeze, unfreeze
from app.core.config import get_settings, load_settings
from app.core.context import system_context, use_context
from app.core.error_codes import ErrorEntry, get_entry
from app.core.errors import BizError, StartupError
from app.core.fault import faults
from app.db.base import Base
from app.db.session import session_scope
from app.domains.demo.model import DemoOrder
from app.domains.system.model import (
    Dept,
    DictData,
    DictType,
    ExportTask,
    IntegrityScan,
    JobLog,
    LeaveRecord,
    Menu,
    MigrationPending,
    OperateLog,
    Outbox,
    Param,
    Role,
    RoleMenu,
    SyncState,
    Tenant,
    User,
    WorkCalendar,
)
from app.domains.todo.model import Todo
from app.integrations.air_ai.client import CONFIG as AIR_CONFIG
from app.integrations.air_ai.client import complete as air_complete
from app.integrations.air_ai.client import current_config as air_current_config
from app.integrations.base import STATEMENTS, SelectOnlyError
from app.integrations.collector.client import pull as collector_pull
from app.integrations.comfyui.client import render as comfy_render
from app.integrations.dingtalk.client import get_user_by_code
from app.integrations.dingtalk_attendance.client import ADAPTER_LOGS, list_leaves
from app.integrations.football_live.reader import (
    QUERIES,
    UNAVAILABLE,
    football_engine,
    football_row_or_unavailable,
    get_room,
    live_duration,
    merge_live_metrics,
    room_exists_for_bind,
)
from app.integrations.football_web.client import RealFootballWeb, fetch_room, implementation
from app.integrations.runtime import ADAPTERS
from app.integrations.train_ai.client import TrainQuizAiClient, configure, current_config, generate_quiz, mock_questions
from app.services import jobs as jobs_mod
from app.services.attendance import (
    pull_leaves,
    read_attendance_config,
    set_attendance_app_key,
    set_dingtalk_app_key,
    should_days,
    update_attendance_secret,
    update_calendar,
)
from app.services.jobs import JOBS, run_job, watch_state
from app.domains.system.service import param_list
from tests.conftest import auth
from tests.stddata import D1, U_ADMIN
from tools.export_error_codes import export_error_codes
from tools.migrate.run import migrate_sample
from tools.seed.apply import PARAMS, ROLES, apply
from tools.static_checks import (
    VENDOR_HOST,
    VENDOR_MODEL,
    check_live_room_leak,
    check_ops_http,
    check_seed_apply_call,
    check_train_ai_isolation,
    check_vendor_hardcode,
)
from app.catalog import DICT_TYPE_NAMES

ROOT = Path(__file__).resolve().parents[1]
API = "/admin-api/ims"


def _count(model) -> int:
    with session_scope() as session:
        with use_context(system_context(1)):
            return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _grant_export(role_id: int) -> None:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:demo:order:export"))
            linked = session.scalar(select(RoleMenu.id).where(RoleMenu.role_id == role_id, RoleMenu.menu_id == menu.id))
            if linked is None:
                session.add(RoleMenu(role_id=role_id, menu_id=menu.id, tenant_id=1))


def _import_rows(prefix: str) -> list[dict]:
    rows = []
    for index in range(10):
        rows.append(
            {
                "name": f"{prefix}-{index + 1}",
                "status": "ACTIVE",
                "deptId": D1,
                "code": f"{prefix}-{index + 1}",
            }
        )
    # 表头是 Excel 第 1 行，所以第 3、8 行对应数据下标 1 和 6。
    rows[1]["status"] = "NOPE"
    rows[6]["status"] = "BAD"
    return rows


def test_ut_h01_01():
    """UT-H01-01 两个 Worker 同时触发，只执行 1 次，另一实例日志写明已在其他实例执行。"""
    spec = next(item for item in JOBS if item.name == "org_reconcile")
    original = spec.fn
    ran: list[int] = []
    results: list[dict] = []
    hold = {"go": True}
    barrier = threading.Barrier(2)

    def body():
        ran.append(1)
        while hold["go"]:
            time.sleep(0.01)

    def worker():
        barrier.wait(timeout=3)
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                results.append(run_job("org_reconcile"))

    spec.fn = body
    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    try:
        for item in threads:
            item.start()
        deadline = time.time() + 3
        while time.time() < deadline and not (len(ran) == 1 and any(item.get("skipped") for item in results)):
            time.sleep(0.01)
        hold["go"] = False
        for item in threads:
            item.join(timeout=3)
        assert len(ran) == 1
        assert len(results) == 2
        assert sum(1 for item in results if item.get("success")) == 1
        skipped = [item for item in results if item.get("skipped")]
        assert len(skipped) == 1
        assert skipped[0]["message"] == "已在其他实例执行"
        with session_scope() as session:
            logs = list(session.scalars(select(JobLog).where(JobLog.job_name == "org_reconcile")))
        assert any(row.error_digest == "已在其他实例执行" for row in logs)
        assert sum(1 for row in logs if row.success == 1) == 1
    finally:
        hold["go"] = False
        spec.fn = original


def test_ut_h01_02():
    """UT-H01-02 任务异常：执行日志失败并带错误摘要，告警站内信 1 条。"""
    spec = next(item for item in JOBS if item.name == "integrity")
    original = spec.fn

    def boom():
        raise RuntimeError("任务炸了")

    spec.fn = boom
    try:
        from app.domains.message.model import Message

        before_msg = _count(Message)
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                result = run_job("integrity")
        assert result["success"] is False
        assert "任务炸了" in result["message"]
        with session_scope() as session:
            with use_context(system_context(1)):
                log = session.scalar(select(JobLog).where(JobLog.job_name == "integrity", JobLog.success == 0))
                assert log is not None
                assert log.error_digest and "任务炸了" in log.error_digest
        assert _count(Message) == before_msg + 1
    finally:
        spec.fn = original


def test_ut_h01_03(client):
    """UT-H01-03 持有 ims:system:job:run 手动触发，执行 1 次，日志触发方式为手动。"""
    with session_scope() as session:
        before = list(session.scalars(select(JobLog).where(JobLog.job_name == "org_reconcile", JobLog.trigger_mode == "手动")))
    body = client.post(f"{API}/system/job/run", headers=auth(client, "u_admin"), json={"name": "org_reconcile"}).json()
    assert body["code"] == 0, body
    assert body["data"]["success"] is True
    with session_scope() as session:
        logs = list(session.scalars(select(JobLog).where(JobLog.job_name == "org_reconcile", JobLog.trigger_mode == "手动")))
    assert len(logs) == len(before) + 1
    assert logs[-1].success == 1
    assert logs[-1].trigger_mode == "手动"


def test_ut_h01_04():
    """UT-H01-04 执行超过锁 TTL 时看门狗续约，另一实例仍拿不到锁。"""
    spec = next(item for item in JOBS if item.name == "integrity")
    original = spec.fn
    previous_ttl = jobs_mod.LOCK_TTL
    previous_watch = jobs_mod.WATCH_INTERVAL
    calls = []
    rival = {}

    def slow():
        calls.append(1)
        time.sleep(1.5)

    def other():
        time.sleep(1.15)
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                rival["result"] = run_job("integrity")

    spec.fn = slow
    jobs_mod.LOCK_TTL = 1
    jobs_mod.WATCH_INTERVAL = 0.15
    watch_state["extends"] = 0
    thread = threading.Thread(target=other)
    try:
        thread.start()
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                watched = run_job("integrity")
        thread.join(timeout=4)
        assert watched["success"] is True
        assert calls == [1]
        assert rival["result"]["skipped"] is True
        assert rival["result"]["message"] == "已在其他实例执行"
        assert watch_state["extends"] >= 1
    finally:
        spec.fn = original
        jobs_mod.LOCK_TTL = previous_ttl
        jobs_mod.WATCH_INTERVAL = previous_watch


def test_ut_h02_01(client):
    """UT-H02-01 全有或全无：10 行里第 3、8 行错误，返回 2 条错误且 0 条入库。"""
    rows = _import_rows("H0201")
    body = client.post(
        f"{API}/demo/order/import",
        headers=auth(client, "u_admin"),
        json={"mode": "ALL_OR_NOTHING", "rows": rows},
    ).json()
    assert body["code"] == 0, body
    assert body["data"]["successCount"] == 0
    errors = body["data"]["errors"]
    assert len(errors) == 2
    reason = get_entry(1503).msg
    assert {(item["row"], item["column"], item["message"]) for item in errors} == {(3, "status", reason), (8, "status", reason)}
    for item in errors:
        assert item["row"] and item["column"] and item["message"]
    with session_scope() as session:
        codes = [row["code"] for row in rows]
        found = session.scalar(select(func.count()).select_from(DemoOrder).where(DemoOrder.code.in_(codes)))
    assert found == 0


def test_ut_h02_02(client):
    """UT-H02-02 部分提交：同样 10 行，新增 8 条并返回 2 条错误。"""
    rows = _import_rows("H0202")
    body = client.post(
        f"{API}/demo/order/import",
        headers=auth(client, "u_admin"),
        json={"mode": "PARTIAL", "rows": rows},
    ).json()
    assert body["code"] == 0, body
    assert body["data"]["successCount"] == 8
    assert len(body["data"]["errors"]) == 2
    with session_scope() as session:
        stored = set(session.scalars(select(DemoOrder.code).where(DemoOrder.code.like("H0202-%"))))
    assert stored == {row["code"] for index, row in enumerate(rows) if index not in {1, 6}}
    assert "H0202-2" not in stored
    assert "H0202-7" not in stored


def test_ut_h02_03(client):
    """UT-H02-03 超过 5000 行返回 1001，并提示拆分。"""
    rows = [{"name": "n", "status": "ACTIVE"} for _ in range(5001)]
    body = client.post(
        f"{API}/demo/order/import",
        headers=auth(client, "u_admin"),
        json={"rows": rows, "mode": "ALL_OR_NOTHING"},
    ).json()
    assert body["code"] == 1001
    assert "拆分" in body["msg"]


def test_ut_h02_04(client):
    """UT-H02-04 第 5 行字典非法为 1503，第 6 行引用不存在为 1500，原因是对应中文。"""
    rows = [
        {"name": "好1", "status": "ACTIVE", "deptId": D1, "code": "H0204-1"},
        {"name": "好2", "status": "ACTIVE", "deptId": D1, "code": "H0204-2"},
        {"name": "好3", "status": "ACTIVE", "deptId": D1, "code": "H0204-3"},
        {"name": "坏字典", "status": "NOPE", "deptId": D1, "code": "H0204-4"},
        {"name": "坏引用", "status": "ACTIVE", "deptId": D1, "code": "H0204-5", "realnameId": 999999},
    ]
    body = client.post(
        f"{API}/demo/order/import",
        headers=auth(client, "u_admin"),
        json={"mode": "ALL_OR_NOTHING", "rows": rows},
    ).json()
    assert body["code"] == 0, body
    by_row = {item["row"]: item for item in body["data"]["errors"]}
    assert by_row[5]["column"] == "status"
    assert by_row[5]["code"] == 1503
    assert by_row[5]["message"] == get_entry(1503).msg
    assert by_row[6]["column"] == "realnameId"
    assert by_row[6]["code"] == 1500
    assert by_row[6]["message"] == get_entry(1500).msg


def test_ut_h02_05(client):
    """UT-H02-05 u_dept 导出文件行集合等于其列表可见集合，证件号脱敏。"""
    plain = "110101199001011234"
    hidden = "310101198801019999"
    _grant_export(202)
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            visible = session.scalar(select(DemoOrder).where(DemoOrder.code == "OD1"))
            secret = session.scalar(select(DemoOrder).where(DemoOrder.code == "OD11"))
            visible.id_card = plain
            secret.id_card = hidden
    headers = auth(client, "u_dept")
    page = client.get(f"{API}/demo/order/page?pageNo=1&pageSize=100", headers=headers).json()
    assert page["code"] == 0, page
    names = {item["name"] for item in page["data"]["list"]}
    assert "OD1" in names
    assert "OD11" not in names
    exported = client.post(f"{API}/demo/order/export", headers=headers, json={}).json()
    assert exported["code"] == 0, exported
    downloaded = client.get(f"{API}/export-task/download?id={exported['data']['id']}", headers=headers).json()
    assert downloaded["code"] == 0, downloaded
    content = downloaded["data"]["content"]
    lines = [line for line in content.splitlines() if line]
    assert lines[0] == "name,idCard,mobile"
    expected = {f"{item.get('name')},{item.get('idCard') or ''},{item.get('mobile') or ''}" for item in page["data"]["list"]}
    assert set(lines[1:]) == expected
    shown = next(item["idCard"] for item in page["data"]["list"] if item["name"] == "OD1")
    assert shown and "*" in shown
    assert plain not in content
    assert hidden not in content
    assert shown in content


def test_ut_h02_06(client):
    """UT-H02-06 导出执行异常后，我的导出任务状态失败且中文原因可见。"""
    faults.arm("export.fail", RuntimeError("导出失败"))
    headers = auth(client, "u_admin")
    body = client.post(f"{API}/demo/order/export", headers=headers, json={}).json()
    assert body["code"] == 0, body
    assert body["data"]["status"] == "FAILED"
    assert body["data"]["error"]
    page = client.get(f"{API}/export-task/my/page", headers=headers).json()
    assert page["code"] == 0, page
    matched = next(item for item in page["data"]["list"] if item["id"] == body["data"]["id"])
    assert matched["status"] == "FAILED"
    assert matched["error"]
    assert "导出失败" in matched["error"]


def test_ut_h02_07(client):
    """UT-H02-07 B 下载 A 的导出任务返回 1504。"""
    _grant_export(202)
    owner = auth(client, "u_admin")
    exported = client.post(f"{API}/demo/order/export", headers=owner, json={}).json()
    assert exported["code"] == 0, exported
    other = client.get(f"{API}/export-task/download?id={exported['data']['id']}", headers=auth(client, "u_dept")).json()
    assert other["code"] == 1504


def test_ut_h03_01(tmp_path):
    """UT-H03-01 make error-codes 生成 JSON，每个已登记码都有 msg 和 strategy。"""
    proc = subprocess.run(["make", "error-codes"], cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    rows = export_error_codes(tmp_path / "error-codes.json")
    assert rows
    assert all(item.get("msg") and item.get("strategy") for item in rows)
    codes = {item["code"] for item in rows}
    from app.core.error_codes import get_registry

    assert codes == set(get_registry())
    body = json.loads((tmp_path / "error-codes.json").read_text(encoding="utf-8"))
    assert isinstance(body, list)
    assert all(item.get("msg") and item.get("strategy") for item in body)


def test_ut_h03_02(tmp_path):
    """UT-H03-02 登记错误码但不写 strategy 时构建失败。"""
    with pytest.raises(ValueError, match="策略"):
        export_error_codes(tmp_path / "missing.json", entries=[ErrorEntry(1001, "COMMON", "参数校验失败", "")])


def test_ut_h03_03(tmp_path):
    """UT-H03-03 1002/1003 relogin，1008 noPermission，1001 fieldError，1504 toast。"""
    rows = {item["code"]: item["strategy"] for item in export_error_codes(tmp_path / "codes.json")}
    assert rows[1002] == "relogin"
    assert rows[1003] == "relogin"
    assert rows[1008] == "noPermission"
    assert rows[1001] == "fieldError"
    assert rows[1504] == "toast"


def _block_http(monkeypatch):
    calls = {"n": 0}

    class Fake:
        def __init__(self, *args, **kwargs):
            calls["n"] += 1

        def __enter__(self):
            calls["n"] += 1
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            calls["n"] += 1
            raise AssertionError("network")

        def get(self, *args, **kwargs):
            calls["n"] += 1
            raise AssertionError("network")

    def blocked(*args, **kwargs):
        calls["n"] += 1
        raise AssertionError("network")

    monkeypatch.setattr(httpx, "Client", Fake)
    monkeypatch.setattr(httpx, "get", blocked)
    monkeypatch.setattr(httpx, "post", blocked)
    return calls


def test_ut_h04_01(monkeypatch):
    """UT-H04-01 全部 mode=mock 时各适配器返回 Mock 成功数据，且不发外部网络请求。"""
    calls = _block_http(monkeypatch)
    settings = get_settings()
    for name in ("dingtalk", "dingtalk_attendance", "football_web", "collector", "comfyui", "air_ai", "train_ai"):
        settings.integrations.setdefault(name, {})["mode"] = "mock"
    mock_questions.clear()
    ADAPTERS["dingtalk_attendance"].payload = {"leaves": [{"approvalNo": "MOCK-1", "leaveDate": "2026-10-01"}]}
    ding = get_user_by_code("ok")
    leaves = list_leaves([U_ADMIN], "2026-10-01", "2026-10-31")
    room = fetch_room(1)
    collected = collector_pull()
    rendered = comfy_render()
    aired = air_complete("ping")
    quiz = generate_quiz(True, 1, 1)
    assert ding.get("userid")
    assert leaves and leaves[0]["approvalNo"] == "MOCK-1"
    assert room["mode"] == "mock" and room["ok"] is True
    assert collected["mode"] == "mock" and collected["ok"] is True
    assert rendered["mode"] == "mock" and rendered["ok"] is True
    assert aired["mode"] == "mock" and aired["ok"] is True
    assert len(quiz) == 2
    assert calls["n"] == 0
    for gateway in ADAPTERS.values():
        assert gateway.http_calls == 0


def test_ut_h04_02():
    """UT-H04-02 钉钉 Mock 超时配置 1 秒，约 1 秒后返回 5003。"""
    settings = get_settings()
    block = settings.integrations.setdefault("dingtalk", {})
    previous = block.get("timeout_ms")
    gateway = ADAPTERS["dingtalk"]
    try:
        block["mode"] = "mock"
        block["timeout_ms"] = 1000
        gateway.next_error = "timeout"
        started = time.perf_counter()
        with pytest.raises(BizError) as exc:
            gateway.call("ping")
        elapsed = time.perf_counter() - started
        assert exc.value.code == 5003
        assert 0.8 <= elapsed <= 2.0
    finally:
        if previous is None:
            block.pop("timeout_ms", None)
        else:
            block["timeout_ms"] = previous
        gateway.reset()


def test_ut_h04_03():
    """UT-H04-03 Football Mock 依次返回 1271、1272、1273。"""
    gateway = ADAPTERS["football_web"]
    seen = []
    for code in (1271, 1272, 1273):
        gateway.next_error = code
        with pytest.raises(BizError) as exc:
            fetch_room(1)
        seen.append(exc.value.code)
        gateway.next_error = None
    assert seen == [1271, 1272, 1273]


def test_ut_h04_04():
    """UT-H04-04 连续失败 5 次后第 6 次熔断且不发请求，30 秒后恢复尝试。"""
    gateway = ADAPTERS["football_web"]
    gateway.reset()
    freeze(datetime(2026, 10, 12, 8, 0, 0))
    try:
        gateway.next_error = 1271
        for _ in range(5):
            with pytest.raises(BizError) as exc:
                gateway.call()
            assert exc.value.code == 1271
            assert "熔断" not in exc.value.msg
        assert gateway.attempts == 5
        with pytest.raises(BizError) as opened:
            gateway.call()
        assert "熔断" in opened.value.msg
        assert gateway.attempts == 5
        advance(timedelta(seconds=30))
        with pytest.raises(BizError) as recovered:
            gateway.call()
        assert recovered.value.code == 1271
        assert "熔断" not in recovered.value.msg
        assert gateway.attempts == 6
    finally:
        unfreeze()
        gateway.reset()


def test_ut_h04_05():
    """UT-H04-05 只改 integrations.football_web.mode=real，即选用 Real 实现。"""
    settings = get_settings()
    block = settings.integrations.setdefault("football_web", {})
    previous = block.get("mode")
    try:
        block["mode"] = "real"
        impl = implementation()
        assert isinstance(impl, RealFootballWeb)
        body = impl.fetch_room(7)
        assert body["mode"] == "real"
        assert body["impl"] == "RealFootballWeb"
    finally:
        block["mode"] = previous or "mock"


def test_ut_h04_06(tmp_path):
    """UT-H04-06 代码中出现 httpx.get(\"http://ops.xxx/ops/api\") 时静态扫描失败。"""
    target = tmp_path / "app"
    target.mkdir()
    (target / "bridge.py").write_text('import httpx\nhttpx.get("http://ops.xxx/ops/api")\n', encoding="utf-8")
    problems = check_ops_http(tmp_path)
    assert problems
    assert any("ops" in item for item in problems)


def _seed_counts(session) -> dict:
    models = (User, Role, Menu, DictType, DictData, Param, Dept, Tenant)
    return {model.__tablename__: int(session.scalar(select(func.count()).select_from(model)) or 0) for model in models}


def test_ut_h05_01():
    """UT-H05-01 空库种子执行两次，行数不变，且 R1～R11、菜单、字典、参数齐全。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(text(f"TRUNCATE TABLE `{table.name}`"))
            session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            apply("test")
            first = _seed_counts(session)
            apply("test")
            second = _seed_counts(session)
            assert first == second
            assert all(value > 0 for value in second.values())
            keys = set(session.scalars(select(Role.role_key)))
            for index in range(1, 12):
                assert f"R{index}" in keys
            names = set(session.scalars(select(Role.name)))
            for _ident, _key, name, _scope in ROLES:
                assert name in names
            menu_count = second[Menu.__tablename__]
            assert menu_count > 0
            dict_types = set(session.scalars(select(DictType.dict_type)))
            assert set(DICT_TYPE_NAMES) <= dict_types
            param_keys = set(session.scalars(select(Param.param_key)))
            for key, *_rest in PARAMS:
                assert key in param_keys


def test_ut_h05_02():
    """UT-H05-02 管理员改过的种子菜单名，再次种子后保持修改值。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == "ims:demo:order:query"))
            menu.name = "订单查询-管理员"
            session.flush()
            apply("test")
            again = session.scalar(select(Menu).where(Menu.perm_code == "ims:demo:order:query"))
            assert again.name == "订单查询-管理员"
            twins = session.scalar(select(func.count()).select_from(Menu).where(Menu.perm_code == "ims:demo:order:query"))
            assert twins == 1


def test_ut_h05_03():
    """UT-H05-03 --env e2e 的角色名带测试-、role_key 带 e2e_，且不与 R1～R11 重名。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            apply("e2e")
            standard_keys = {f"R{index}" for index in range(1, 12)}
            standard_names = {name for _ident, _key, name, _scope in ROLES}
            rows = list(session.scalars(select(Role).where(Role.role_key.like("e2e_%"))))
            assert rows
            for role in rows:
                assert role.name.startswith("测试-")
                assert role.role_key.startswith("e2e_")
                assert role.role_key not in standard_keys
                assert role.name not in standard_names


def test_ut_h05_04(tmp_path):
    """UT-H05-04 service.py 调用种子插入函数时静态检查失败。"""
    folder = tmp_path / "app" / "domains" / "demo"
    folder.mkdir(parents=True)
    (folder / "service.py").write_text("from tools.seed.apply import apply\n\ndef load():\n    apply()\n", encoding="utf-8")
    problems = check_seed_apply_call(tmp_path)
    assert problems
    assert any("种子" in item for item in problems)
    assert check_seed_apply_call(ROOT) == []


def _ops_hundred():
    source = create_engine("sqlite://")
    with source.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE system_dept (id INTEGER PRIMARY KEY, name TEXT, parent_id INTEGER, tenant_id INTEGER, status INTEGER, deleted INTEGER)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE system_users (id INTEGER PRIMARY KEY, username TEXT, nickname TEXT, dept_id INTEGER, tenant_id INTEGER, status INTEGER, deleted INTEGER)"
            )
        )
        conn.execute(text("INSERT INTO system_dept VALUES (77001, '迁部门', 0, 0, 0, 0)"))
        for ident in range(77101, 77200):
            conn.execute(
                text("INSERT INTO system_users VALUES (:id, :username, '迁用户', 77001, 0, 0, 0)"),
                {"id": ident, "username": f"u{ident}"},
            )
        conn.execute(text("INSERT INTO system_users VALUES (77200, 'u77200', '孤儿', 999999, 0, 0, 0)"))
    return source


def _migration_snapshot():
    with session_scope() as session:
        with use_context(system_context(1)):
            users = tuple(sorted(session.scalars(select(User.id))))
            pending = tuple(sorted((row.source_id, row.reason) for row in session.scalars(select(MigrationPending))))
    return users, pending


def test_ut_h05_05():
    """UT-H05-05 100 条 OPS 用户含 1 条坏部门，迁移两次结果一致，保留原主键，创建人是 data-migration。"""
    source = _ops_hundred()
    first = migrate_sample(source, "opsbiz")
    snap = _migration_snapshot()
    second = migrate_sample(source, "opsbiz")
    assert _migration_snapshot() == snap
    assert first["source"] == 100 and first["success"] == 99 and first["pending"] == 1
    assert second["source"] == 100 and second["success"] == 99 and second["pending"] == 1
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            migration_user = session.scalar(select(User).where(User.username == "data-migration"))
            assert migration_user is not None
            for ident in range(77101, 77200):
                row = session.get(User, ident)
                assert row is not None
                assert row.id == ident
                assert row.creator == migration_user.id
            assert session.get(User, 77200) is None
            pending = list(session.scalars(select(MigrationPending).where(MigrationPending.source_id == "77200")))
            assert len(pending) == 1
            assert pending[0].creator == migration_user.id
            max_id = int(session.scalar(select(func.max(User.id))) or 0)
            created = User(username="h05next", nickname="新建", status="ACTIVE", source="LOCAL")
            session.add(created)
            session.flush()
            assert created.id == max_id + 1


def test_ut_h05_06():
    """UT-H05-06 核对报告来源 100、成功 99、待补录 1，并自动巡检一次。"""
    before = _count(IntegrityScan)
    stats = migrate_sample(_ops_hundred(), "opsbiz")
    assert stats["source"] == 100
    assert stats["success"] == 99
    assert stats["pending"] == 1
    assert stats["scanId"]
    assert _count(IntegrityScan) == before + 1


def test_ut_h06_01():
    """UT-H06-01 读仓储读取一行时，拦截器只记录 SELECT。"""
    STATEMENTS.clear()
    QUERIES.clear()
    room = get_room(1, 9101)
    assert room is not None
    assert STATEMENTS
    for statement in STATEMENTS:
        assert statement.lstrip().upper().startswith("SELECT")
        assert not statement.lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE", "ALTER"))
    assert QUERIES
    assert all(sql.lstrip().upper().startswith("SELECT") for sql, _params in QUERIES)


def test_ut_h06_02():
    """UT-H06-02 只读会话执行 UPDATE live_room 抛错，且语句未生效。"""
    before = get_room(1, 9101)
    with pytest.raises(SelectOnlyError):
        with football_engine().connect() as conn:
            conn.exec_driver_sql("UPDATE live_room SET nickname=%s WHERE id=%s", ("x", 9101))
    after = get_room(1, 9101)
    assert after is not None
    assert after["nickname"] == before["nickname"]
    assert str(after["live_name"]).startswith("[STUB]")


def test_ut_h06_03():
    """UT-H06-03 他租户房间 get_room 与 room_exists_for_bind 都视为不存在。"""
    assert get_room(1, 9101) is not None
    assert get_room(1, 9107) is None
    assert room_exists_for_bind(1, 9107) is False


def _hand_duration(author_id: int, start: datetime, end: datetime, *, include_deleted: bool) -> tuple[int, int]:
    from tools.football_stub.seed import SCENARIOS

    count = 0
    minutes = 0
    for row in SCENARIOS:
        if int(row["author_id"]) != author_id:
            continue
        if not include_deleted and int(row.get("deleted") or 0) != 0:
            continue
        created = datetime.fromisoformat(row["create_time"])
        if created < start or created > end:
            continue
        count += 1
        if row.get("start_time") and row.get("end_time"):
            span = datetime.fromisoformat(row["end_time"]) - datetime.fromisoformat(row["start_time"])
            minutes += int(span.total_seconds() // 60)
    return count, minutes


def test_ut_h06_04():
    """UT-H06-04 live_duration 与照抄 SQL 的手工结果逐值相等，已删除房间计入。"""
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 31, 23, 59, 59)
    expected = _hand_duration(501, start, end, include_deleted=True)
    omitted = _hand_duration(501, start, end, include_deleted=False)
    assert expected[0] == omitted[0] + 1
    assert expected[1] > omitted[1]
    assert live_duration(501, start, end) == expected


def test_ut_h06_05(tmp_path):
    """UT-H06-05 app/domains 中出现 live_room 时静态检查失败。"""
    folder = tmp_path / "app" / "domains" / "demo"
    folder.mkdir(parents=True)
    (folder / "model.py").write_text("class Room:\n    __tablename__ = 'live_room'\n", encoding="utf-8")
    problems = check_live_room_leak(tmp_path)
    assert problems
    assert any("live_room" in item for item in problems)


def test_ut_h06_06():
    """UT-H06-06 少 cover 列，或把 status 改成 VARCHAR，启动都拒绝并点名该列。"""
    from tools.football_stub.seed import _writer_engine, seed

    engine = _writer_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE live_room DROP COLUMN cover"))
        with pytest.raises(StartupError, match="cover"):
            create_app_for_schema()
        seed()
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE live_room MODIFY `status` varchar(32) NULL"))
        with pytest.raises(StartupError, match="status"):
            create_app_for_schema()
    finally:
        seed()
        from app.integrations.football_live.reader import _engines

        _engines.clear()


def create_app_for_schema():
    from app.main import create_app

    return create_app(load_settings("test"))


def test_ut_h06_07():
    """UT-H06-07 造数执行两次不重复，8 类场景都有数据。"""
    from tools.football_stub.seed import SCENARIOS, seed

    assert len(SCENARIOS) == 8
    assert len({row["live_name"] for row in SCENARIOS}) == 8
    assert seed() == 8
    assert seed() == 8
    with football_engine().connect() as conn:
        count = int(conn.exec_driver_sql("SELECT COUNT(*) FROM live_room").scalar())
        names = [row[0] for row in conn.exec_driver_sql("SELECT live_name FROM live_room ORDER BY id").all()]
    assert count == 8
    assert names == [row["live_name"] for row in SCENARIOS]
    assert all(str(name).startswith("[STUB]") for name in names)


def test_ut_h06_08():
    """UT-H06-08 IMS_ENV=prod 时建表和造数脚本都拒绝执行，退出码非 0。"""
    env = os.environ.copy()
    env["IMS_ENV"] = "prod"
    for args in (["-m", "tools.football_stub.seed"], ["-m", "tools.football_stub.seed", "create"]):
        proc = subprocess.run([sys.executable, *args], cwd=str(ROOT), env=env, capture_output=True, text=True)
        assert proc.returncode != 0


def test_ut_h06_09(client):
    """UT-H06-09 Football 超时时 merge_live_metrics 返回 IMS 快照和暂不可用，示例场次编辑仍成功。"""

    def timeout():
        raise TimeoutError("football timeout")

    merged = merge_live_metrics({"gmv": 6, "sessionName": "示例场次"}, football_row_or_unavailable(timeout))
    assert merged["gmv"] == 6
    assert merged["sessionName"] == "示例场次"
    assert merged["unavailable"] is True
    assert merged["hint"] == "暂不可用"
    assert UNAVAILABLE == "UNAVAILABLE"
    headers = auth(client, "u_admin")
    created = client.post(f"{API}/demo/order/create", headers=headers, json={"name": "示例场次", "code": "H0609"}).json()
    assert created["code"] == 0, created
    updated = client.put(
        f"{API}/demo/order/update",
        headers=headers,
        json={"id": created["data"]["id"], "name": "示例场次已改"},
    ).json()
    assert updated["code"] == 0, updated
    assert updated["data"]["name"] == "示例场次已改"


def test_ut_h06_10():
    """UT-H06-10 outbox 同步失败记录重试成功后，状态成功，同步状态与时间更新。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(
                Outbox(
                    topic="live.metrics",
                    status="FAILED",
                    payload={"syncKey": "live-metrics", "syncStatus": "FAILED"},
                    retry_count=1,
                )
            )
            session.flush()
            result = run_job("outbox_retry")
            assert result["success"] is True
            row = session.scalar(select(Outbox).where(Outbox.topic == "live.metrics"))
            assert row.status == "SUCCESS"
            assert row.payload["syncStatus"] == "SUCCESS"
            assert row.payload["syncTime"]
            state = session.scalar(select(SyncState).where(SyncState.state_key == "live-metrics"))
            assert state is not None
            assert state.state_value.startswith("SUCCESS ")
            assert row.payload["syncTime"] in state.state_value


def test_ut_h07_01():
    """UT-H07-01 2026-10 工作日 22，节假日与周六调休抵消；考勤未启用时不扣请假。"""
    settings = get_settings()
    previous = dict(settings.dingtalk_attendance)
    try:
        settings.dingtalk_attendance["enabled"] = False
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                update_calendar("2026-10-01", "HOLIDAY")
                update_calendar("2026-10-03", "WORKDAY_ADJUST")
                session.add(LeaveRecord(user_id=U_ADMIN, leave_date="2026-10-06", portion=Decimal("1"), approval_no="H0701"))
                session.flush()
                result = should_days(U_ADMIN, "2026-10")
        assert Decimal(str(result["shouldDays"])) == Decimal("22")
        assert result["degraded"] is False
    finally:
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(previous)


def test_ut_h07_02():
    """UT-H07-02 考勤启用时，整天 1 天加半天 1 次，应提交天数为基础天数减 1.5。"""
    settings = get_settings()
    previous = dict(settings.dingtalk_attendance)
    try:
        settings.dingtalk_attendance["enabled"] = True
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                session.add(LeaveRecord(user_id=U_ADMIN, leave_date="2026-10-05", portion=Decimal("1"), approval_no="H0702-F"))
                session.add(LeaveRecord(user_id=U_ADMIN, leave_date="2026-10-06", portion=Decimal("0.5"), approval_no="H0702-H"))
                session.flush()
                base = should_days(U_ADMIN, "2026-10")
        assert Decimal(str(base["shouldDays"])) == Decimal("20.5")
        assert base["degraded"] is False
    finally:
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(previous)


def test_ut_h07_03():
    """UT-H07-03 请假 10-30 至 11-02，10 月只扣 10-30 一个工作日。"""
    settings = get_settings()
    previous = dict(settings.dingtalk_attendance)
    try:
        settings.dingtalk_attendance["enabled"] = True
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                for day in ("2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"):
                    session.add(LeaveRecord(user_id=U_ADMIN, leave_date=day, portion=Decimal("1"), approval_no="H0703"))
                session.flush()
                result = should_days(U_ADMIN, "2026-10")
        assert Decimal(str(result["shouldDays"])) == Decimal("21")
        assert result["degraded"] is False
    finally:
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(previous)


def test_ut_h07_04():
    """UT-H07-04 当月拉取失败时返回基础天数，且 degraded=true。"""
    settings = get_settings()
    previous = dict(settings.dingtalk_attendance)
    try:
        settings.dingtalk_attendance["enabled"] = True
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                session.add(SyncState(state_key="attendance:2026-10", state_value="同步失败"))
                session.add(LeaveRecord(user_id=U_ADMIN, leave_date="2026-10-06", portion=Decimal("1"), approval_no="H0704"))
                session.flush()
                result = should_days(U_ADMIN, "2026-10")
        assert Decimal(str(result["shouldDays"])) == Decimal("22")
        assert result["degraded"] is True
    finally:
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(previous)


def test_ut_h07_05():
    """UT-H07-05 修改考勤 AppKey 不影响 IMS 钉钉应用配置，反之亦然。"""
    settings = get_settings()
    ding = dict(settings.dingtalk)
    attendance = dict(settings.dingtalk_attendance)
    try:
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                set_attendance_app_key("att-only-key")
                assert settings.dingtalk.get("app_key") == ding.get("app_key")
                assert settings.dingtalk_attendance.get("app_key") == "att-only-key"
                att_row = session.scalar(select(Param).where(Param.param_key == "dingtalk_attendance.app_key"))
                ding_row = session.scalar(select(Param).where(Param.param_key == "dingtalk.app_key"))
                assert att_row.value == "att-only-key"
                assert att_row.group_name == "钉钉考勤"
                assert ding_row.value == "test-app-key"
                assert ding_row.group_name == "钉钉"
                set_dingtalk_app_key("ding-only-key")
                assert settings.dingtalk_attendance.get("app_key") == "att-only-key"
                assert settings.dingtalk.get("app_key") == "ding-only-key"
                session.refresh(att_row)
                session.refresh(ding_row)
                assert att_row.value == "att-only-key"
                assert ding_row.value == "ding-only-key"
    finally:
        settings.dingtalk.clear()
        settings.dingtalk.update(ding)
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(attendance)


def test_ut_h07_06():
    """UT-H07-06 考勤配置读取、操作日志、适配器日志里的 AppSecret 都是 ******。"""
    secret = "AttSecret-h0706"
    ADAPTER_LOGS.clear()
    settings = get_settings()
    attendance = dict(settings.dingtalk_attendance)
    try:
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                viewed = update_attendance_secret(secret)
                listed = {item["paramKey"]: item for item in param_list()}
                list_leaves([U_ADMIN], "2026-10-01", "2026-10-02")
                logs = list(session.scalars(select(OperateLog).where(OperateLog.action == "修改考勤密钥")))
        assert viewed["appSecret"] == "******"
        assert secret not in json.dumps(viewed, ensure_ascii=False)
        assert listed["dingtalk_attendance.app_secret"]["value"] == "******"
        assert logs and len(logs) == 1
        blob = " ".join((row.params_digest or "") for row in logs)
        assert "******" in blob
        assert secret not in blob
        assert ADAPTER_LOGS
        dumped = json.dumps(ADAPTER_LOGS, ensure_ascii=False)
        assert "******" in dumped
        assert secret not in dumped
        assert read_attendance_config()["appSecret"] == "******"
    finally:
        settings.dingtalk_attendance.clear()
        settings.dingtalk_attendance.update(attendance)
        ADAPTER_LOGS.clear()


def test_ut_h07_07(monkeypatch):
    """UT-H07-07 mode=mock 拉取请假时 HTTP 客户端不被调用。"""
    calls = _block_http(monkeypatch)
    gateway = ADAPTERS["dingtalk_attendance"]
    assert gateway.mode() == "mock"
    gateway.payload = {"leaves": []}
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            pulled = pull_leaves()
    assert pulled["count"] == 0
    assert calls["n"] == 0
    assert gateway.http_calls == 0


def test_ut_h07_08():
    """UT-H07-08 Mock 超时：任务失败记日志，当月状态为同步失败。"""
    settings = get_settings()
    block = settings.integrations.setdefault("dingtalk_attendance", {})
    previous = block.get("timeout_ms")
    gateway = ADAPTERS["dingtalk_attendance"]
    freeze(datetime(2026, 10, 12, 1, 30, 0))
    try:
        block["timeout_ms"] = 1
        gateway.next_error = "timeout"
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                result = run_job("attendance_pull")
        assert result["success"] is False
        with session_scope() as session:
            with use_context(system_context(1)):
                log = session.scalar(select(JobLog).where(JobLog.job_name == "attendance_pull", JobLog.success == 0))
                state = session.scalar(select(SyncState).where(SyncState.state_key == "attendance:2026-10"))
        assert log is not None and log.error_digest
        assert state is not None and state.state_value == "同步失败"
    finally:
        unfreeze()
        if previous is None:
            block.pop("timeout_ms", None)
        else:
            block["timeout_ms"] = previous
        gateway.reset()


def test_ut_h07_09():
    """UT-H07-09 每日拉取执行两次，请假记录不重复。"""
    gateway = ADAPTERS["dingtalk_attendance"]
    gateway.payload = {"leaves": [{"userId": U_ADMIN, "leaveDate": "2026-10-08", "portion": 1, "approvalNo": "H0709"}]}
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            pull_leaves()
            pull_leaves()
            count = session.scalar(
                select(func.count()).select_from(LeaveRecord).where(LeaveRecord.approval_no == "H0709")
            )
    assert int(count) == 1


def test_ut_h07_10(client):
    """UT-H07-10 持有日历维护权限修改节假日后写 1 条操作日志，应提交天数随之变化。"""
    with session_scope() as session:
        with use_context(system_context(1)):
            before_days = should_days(U_ADMIN, "2026-10")
            before_logs = session.scalar(
                select(func.count()).select_from(OperateLog).where(OperateLog.action == "修改日历")
            )
    body = client.put(
        f"{API}/system/calendar/update",
        headers=auth(client, "u_admin"),
        json={"date": "2026-10-05", "dayType": "HOLIDAY"},
    ).json()
    assert body["code"] == 0, body
    with session_scope() as session:
        with use_context(system_context(1)):
            after_days = should_days(U_ADMIN, "2026-10")
            after_logs = session.scalar(
                select(func.count()).select_from(OperateLog).where(OperateLog.action == "修改日历")
            )
            marked = session.scalar(select(WorkCalendar).where(WorkCalendar.cal_date == "2026-10-05"))
    assert marked is not None and marked.day_type == "HOLIDAY"
    assert int(after_logs) == int(before_logs) + 1
    assert Decimal(str(before_days["shouldDays"])) - Decimal(str(after_days["shouldDays"])) == Decimal("1")


def test_ut_h08_01():
    """UT-H08-01 Mock 正常生成单选 3 加判断 2，结构与 quiz[] 一致，且不写任务数据。"""
    mock_questions.clear()
    before_todo = _count(Todo)
    before_export = _count(ExportTask)
    got = generate_quiz(True, 3, 2)
    singles = [item for item in got if item.get("type") == "SINGLE"]
    judges = [item for item in got if item.get("type") == "JUDGE"]
    assert len(got) == 5
    assert len(singles) == 3
    assert len(judges) == 2
    for item in singles:
        assert item["stem"]
        assert isinstance(item["options"], list) and item["options"]
        assert isinstance(item["answerIndex"], int)
    for item in judges:
        assert item["stem"]
        assert isinstance(item["answer"], bool)
    assert _count(Todo) == before_todo
    assert _count(ExportTask) == before_export


def test_ut_h08_02():
    """UT-H08-02 Mock 返回 5 题且其中 2 题缺答案时，只返回 3 题。"""
    mock_questions.clear()
    mock_questions.extend(
        [
            {"type": "SINGLE", "stem": "一", "options": ["A", "B"], "answer": "A"},
            {"type": "SINGLE", "stem": "二", "options": ["A", "B"], "answer": "B"},
            {"type": "JUDGE", "stem": "三", "answer": True},
            {"type": "SINGLE", "stem": "缺答案"},
            {"type": "JUDGE", "stem": "空答案", "answer": ""},
        ]
    )
    got = generate_quiz(True, 3, 2)
    assert len(got) == 3
    assert all(item.get("stem") for item in got)


def test_ut_h08_03():
    """UT-H08-03 Mock 全部格式错误，或返回 0 题，都是 1108。"""
    import app.integrations.train_ai.client as train

    mock_questions.clear()
    mock_questions.extend(
        [
            {"type": "SINGLE", "stem": "没有答案"},
            {"type": "JUDGE", "stem": "空", "answer": ""},
            {"stem": ""},
        ]
    )
    with pytest.raises(BizError) as bad:
        generate_quiz(True, 3, 2)
    assert bad.value.code == 1108
    mock_questions.clear()
    train.mock_fault = "empty"
    try:
        with pytest.raises(BizError) as empty:
            generate_quiz(True, 3, 2)
        assert empty.value.code == 1108
    finally:
        train.mock_fault = None


def test_ut_h08_04(monkeypatch):
    """UT-H08-04 Mock 超时返回 1107，且不写任务数据、不发 HTTP。"""
    import app.integrations.train_ai.client as train

    calls = _block_http(monkeypatch)
    train.mock_fault = "timeout"
    before_todo = _count(Todo)
    before_export = _count(ExportTask)
    try:
        with pytest.raises(BizError) as exc:
            generate_quiz(True, 3, 2)
        assert exc.value.code == 1107
        assert calls["n"] == 0
        assert _count(Todo) == before_todo
        assert _count(ExportTask) == before_export
    finally:
        train.mock_fault = None


def test_ut_h08_05():
    """UT-H08-05 Mock 调用失败返回 1106。"""
    import app.integrations.train_ai.client as train

    train.mock_fault = "fail"
    try:
        with pytest.raises(BizError) as exc:
            generate_quiz(True, 1, 1)
        assert exc.value.code == 1106
    finally:
        train.mock_fault = None


def test_ut_h08_06():
    """UT-H08-06 train_ai.enabled=false 时生成返回 1109。"""
    configure(mode="mock", enabled=False)
    mock_questions.clear()
    mock_questions.append({"type": "SINGLE", "stem": "题", "answer": "A"})
    with pytest.raises(BizError) as exc:
        generate_quiz(True, 1, 0)
    assert exc.value.code == 1109


def test_ut_h08_07():
    """UT-H08-07 资料未发布时生成返回 1101。"""
    configure(mode="mock", enabled=True)
    with pytest.raises(BizError) as exc:
        generate_quiz(False, 1, 1)
    assert exc.value.code == 1101


def test_ut_h08_08():
    """UT-H08-08 修改 AIR 连接不影响培训 AI，修改培训 AI 不影响内容 AI Mock。"""
    original = dict(AIR_CONFIG)
    try:
        configure(mode="mock", model="train-kept", api_key="train-key")
        AIR_CONFIG["model"] = "air-changed"
        AIR_CONFIG["base_url"] = "http://air-changed"
        mock_questions.clear()
        generate_quiz(True, 1, 0)
        assert current_config()["model"] == "train-kept"
        assert air_current_config()["model"] == "air-changed"
        configure(model="train-next")
        aired = air_complete("ping")
        assert air_current_config()["model"] == "air-changed"
        assert air_current_config()["base_url"] == "http://air-changed"
        assert current_config()["model"] == "train-next"
        assert aired["model"] == "air-changed"
    finally:
        AIR_CONFIG.clear()
        AIR_CONFIG.update(original)


def test_ut_h08_09(caplog):
    """UT-H08-09 api_key=sk-test-123 不出现在接口响应、日志和调用记录。"""
    from app.domains.system.model import TrainAiCallLog

    secret = "sk-test-123"
    configure(mode="mock", api_key=secret, model="local")
    mock_questions.clear()
    with caplog.at_level("DEBUG"):
        got = generate_quiz(True, 1, 1, material_id=8)
    assert secret not in json.dumps(got, ensure_ascii=False)
    assert secret not in caplog.text
    with session_scope() as session:
        rows = list(session.scalars(select(TrainAiCallLog)))
        blob = " ".join(str(getattr(row, column.name)) for row in rows for column in row.__table__.columns)
    assert secret not in blob
    assert any(row.result_code == 0 and row.material_id == 8 for row in rows)


def test_ut_h08_10(tmp_path):
    """UT-H08-10 TrainQuizAiClient 所在模块 import AIR 时静态检查失败。"""
    folder = tmp_path / "app" / "integrations" / "train_ai"
    folder.mkdir(parents=True)
    (folder / "client.py").write_text(
        "from app.integrations.air_ai.client import CONFIG\n\nclass TrainQuizAiClient:\n    pass\n",
        encoding="utf-8",
    )
    problems = check_train_ai_isolation(tmp_path)
    assert problems
    assert any("air_ai" in item for item in problems)


def test_ut_h08_11():
    from tools.seed.train_ai_default import fill_missing

    filled = fill_missing({"base_url": "", "model": "", "api_key": ""})
    assert filled["base_url"]
    assert filled["model"]
    assert filled["api_key"] == ""
    kept = fill_missing({"base_url": "http://127.0.0.1:9", "api_key": "already", "model": ""})
    assert kept["base_url"] == "http://127.0.0.1:9"
    assert kept["api_key"] == "already"
    assert kept["model"]
    root = Path(__file__).resolve().parents[1]
    assert check_vendor_hardcode(root) == []
    allowed = (root / "tools" / "seed" / "train_ai_default.py").read_text(encoding="utf-8")
    assert VENDOR_HOST in allowed
    assert VENDOR_MODEL in allowed


def test_ut_h08_12(tmp_path):
    bad = tmp_path / "app"
    bad.mkdir()
    (bad / "leak.py").write_text(f"url = 'https://{VENDOR_HOST}'\n", encoding="utf-8")
    problems = check_vendor_hardcode(tmp_path)
    assert any(VENDOR_HOST in item and "leak.py" in item for item in problems)
    clean = tmp_path / "clean"
    seed = clean / "tools" / "seed"
    seed.mkdir(parents=True)
    (seed / "train_ai_default.py").write_text(f"URL = 'https://{VENDOR_HOST}'\nMODEL = '{VENDOR_MODEL}'\n", encoding="utf-8")
    assert check_vendor_hardcode(clean) == []


def test_ut_h08_13(monkeypatch):
    calls = {"n": 0}

    class Fake:
        def __init__(self, *args, **kwargs):
            calls["n"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            calls["n"] += 1
            raise AssertionError("httpx")

    monkeypatch.setattr(httpx, "Client", Fake)
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(Param(param_key="train_ai.mode", name="模式", group_name="培训", value_type="TEXT", value="real", tenant_id=1))
    assert TrainQuizAiClient().config["mode"] == "mock"
    configure(mode="real", api_key="", base_url="")
    with pytest.raises(BizError) as exc:
        generate_quiz(True, 1, 1)
    assert exc.value.code == 1109
    assert calls["n"] == 0
    text = Path("app/integrations/train_ai/client.py").read_text(encoding="utf-8")
    assert "ims_sys_param" not in text


def test_ut_h08_14(monkeypatch):
    seen = {}

    class Fake:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            seen["url"] = url
            class Response:
                status_code = 200

                def json(self_inner):
                    return {"choices": [{"message": {"content": json_lib.dumps([{"type": "SINGLE", "stem": "本地", "answer": "1"}])}}]}

            return Response()

    json_lib = json
    monkeypatch.setattr(httpx, "Client", Fake)
    configure(mode="real", api_key="local-key", base_url="http://127.0.0.1:9", model="local")
    got = generate_quiz(True, 1, 0)
    assert got[0]["answer"] == "1"
    assert seen["url"].startswith("http://127.0.0.1:9/")
    assert VENDOR_HOST not in seen["url"]
