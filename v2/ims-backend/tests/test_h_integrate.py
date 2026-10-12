"""H 组集成：直播只读、培训出题、租户映射、静态检查与生成器。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import yaml
from sqlalchemy import create_engine, select, text

from app.core.config import get_settings, load_settings
from app.core.context import system_context, use_context
from app.core.error_codes import ErrorEntry
from app.core.errors import BizError, StartupError
from app.db.session import session_scope
from app.domains.system.model import Dept, MigrationPending, Param, TrainAiCallLog, User
from app.integrations.base import SelectOnlyError
from app.integrations.football_live.reader import (
    LIVE_DURATION_SQL,
    QUERIES,
    football_engine,
    get_room,
    live_duration,
    read_deleted,
    room_exists_for_bind,
)
from app.integrations.football_live.schema_check import check_schema
from app.integrations.train_ai.client import TrainQuizAiClient, configure, generate_quiz, mock_questions, reset_config
from tools.export_error_codes import export_error_codes
from tools.migrate.maps import map_tenant
from tools.migrate.run import migrate_sample
from tools.scaffold.generate import ScaffoldError, generate
from tools.static_checks import scan

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clear_train_mock():
    mock_questions.clear()
    reset_config()
    yield
    mock_questions.clear()
    reset_config()


def test_ut_h06_tenant_map_and_deleted_flag():
    settings = load_settings("test")
    assert settings.football_tenant_for(1) == 1
    assert settings.football_tenant_for(9) is None
    QUERIES.clear()
    settings.football_live.tenant_map = {}
    assert get_room(1, 42, settings=settings) is None
    assert QUERIES == []
    settings.football_live.tenant_map = {"1": 9}
    seen = {}

    def executor(sql, params):
        seen["sql"] = sql
        seen["params"] = params
        return None

    assert get_room(1, 42, settings=settings, executor=executor) is None
    assert seen["params"] == (42, 9)
    assert "tenant_id=?" in seen["sql"]
    assert "deleted=0" in seen["sql"]
    assert "avatar_url" in seen["sql"]
    assert "screen_type" in seen["sql"]
    assert "watch_type" in seen["sql"]
    assert "view_url" in seen["sql"]
    assert "playback_url" in seen["sql"]
    assert "reserve_count" in seen["sql"]
    assert "screen_mode" not in seen["sql"]
    assert "watch_url" not in seen["sql"]
    assert read_deleted(b"\x01") == 1
    assert read_deleted(b"\x00") == 0
    assert read_deleted(1) == 1
    assert read_deleted(0) == 0


def test_sys_param_secret_is_attendance_not_train():
    from app.domains.system.service import param_list, param_update

    with session_scope(commit=True) as session:
        keys = list(session.scalars(select(Param.param_key)))
        assert not any(str(key).startswith("train_ai.") for key in keys)
        row = session.scalar(select(Param).where(Param.param_key == "dingtalk_attendance.app_secret"))
        assert row is not None
        assert row.value_type == "SECRET"
        assert row.group_name == "钉钉考勤"
        assert row.value in ("", None)
        row.value = "stored-cipher"
        listed = {item["paramKey"]: item for item in param_list()}
        assert listed["dingtalk_attendance.app_secret"]["value"] == "******"
        assert "培训" not in listed["dingtalk_attendance.app_secret"]["groupName"]
        param_update("dingtalk_attendance.app_secret", "")
        assert row.value == "stored-cipher"


def test_map_tenant_cases():
    assert map_tenant("legacy_ims", 0) == ("ok", 1)
    assert map_tenant("football", 1) == ("ok", 1)
    assert map_tenant("football", 2) == ("skip", None)
    assert map_tenant("football", 3) == ("skip", None)
    assert map_tenant("football", 4) == ("skip", None)
    assert map_tenant("football", 121) == ("skip", None)
    assert map_tenant("football", 122) == ("skip", None)
    assert map_tenant("football", 9) == ("pending", None)
    assert map_tenant("ai_platform", None) == ("ok", 1)
    assert map_tenant("ai_platform", 1) == ("ok", 1)
    assert map_tenant("opsbiz", 0) == ("ok", 1)
    assert map_tenant("opsbiz", 5) == ("pending", None)
    assert map_tenant("football", 2)[0] == "skip"


def test_static_vendor_and_seed_url(tmp_path):
    host = "dashscope" + ".aliyuncs.com"
    model = "qwen3" + ".8-max"
    root = tmp_path
    app = root / "app"
    app.mkdir()
    (app / "bad.py").write_text(f"url = 'https://{host}'\n", encoding="utf-8")
    seed = root / "tools" / "seed"
    seed.mkdir(parents=True)
    (seed / "apply.py").write_text(f"URL = 'https://{host}'\nMODEL = '{model}'\n", encoding="utf-8")
    (seed / "train_ai_default.py").write_text(f"URL = 'https://{host}'\nMODEL = '{model}'\n", encoding="utf-8")
    problems = scan(root)
    assert any(host in item and "app/bad.py" in item for item in problems)
    assert any(host in item and "tools/seed/apply.py" in item for item in problems)
    assert not any("train_ai_default.py" in item for item in problems)
    seed_text = (ROOT / "tools" / "seed" / "apply.py").read_text(encoding="utf-8")
    default_text = (ROOT / "tools" / "seed" / "train_ai_default.py").read_text(encoding="utf-8")
    assert host not in seed_text and model not in seed_text
    assert "train_ai." not in seed_text
    assert host in default_text and model in default_text
    from tools.seed.train_ai_default import fill_missing

    kept = fill_missing({"base_url": "http://127.0.0.1:9", "model": ""})
    assert kept["base_url"] == "http://127.0.0.1:9"
    assert model in kept["model"]
    assert fill_missing({"api_key": "already"})["api_key"] == "already"


def test_train_disabled_mock_and_empty_key(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            calls["n"] += 1

        def __enter__(self):
            calls["n"] += 1
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            calls["n"] += 1
            raise AssertionError("httpx")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert TrainQuizAiClient().config["mode"] == "mock"
    configure(mode="real", api_key="", base_url="http://127.0.0.1:9")
    with pytest.raises(BizError) as empty_key:
        generate_quiz(True, 1, 1)
    assert empty_key.value.code == 1109
    assert calls["n"] == 0

    configure(mode="mock", api_key="unit-test-key")
    mock_questions.append({"type": "SINGLE", "stem": "一加一", "answer": "2"})
    mock_questions.append({"type": "JUDGE", "stem": "天空是蓝的", "answer": True})
    mock_questions.append({"type": "SINGLE", "stem": "缺答案"})
    got = generate_quiz(True, 1, 1, material_id=5)
    assert [item["answer"] for item in got] == ["2", True]
    with session_scope() as session:
        rows = list(session.scalars(select(TrainAiCallLog)))
        blob = " ".join(str(getattr(row, col.name)) for row in rows for col in row.__table__.columns)
    assert "unit-test-key" not in blob
    assert any(row.result_code == 0 and row.question_count == 2 and row.material_id == 5 for row in rows)

    mock_questions.clear()
    mock_questions.append({"type": "SINGLE", "stem": "没有答案"})
    mock_questions.append({"type": "JUDGE", "stem": "空", "answer": ""})
    with pytest.raises(BizError) as empty:
        generate_quiz(True, 1, 1)
    assert empty.value.code == 1108

    with pytest.raises(BizError) as unpublished:
        generate_quiz(False, 1, 1)
    assert unpublished.value.code == 1101


def test_train_timeout_and_call_fail(monkeypatch):
    configure(mode="real", api_key="unit-test-key", base_url="http://127.0.0.1:9")

    class TimeoutClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "Client", TimeoutClient)
    with pytest.raises(BizError) as timeout:
        generate_quiz(True, 1, 0)
    assert timeout.value.code == 1107

    class FailClient(TimeoutClient):
        def post(self, *args, **kwargs):
            raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "Client", FailClient)
    with pytest.raises(BizError) as failed:
        generate_quiz(True, 1, 0)
    assert failed.value.code == 1106


def test_football_stub_duration_and_select_only():
    from tools.football_stub.seed import SCENARIOS, seed

    assert len(SCENARIOS) == 8
    assert all(str(row["live_name"]).startswith("[STUB]") for row in SCENARIOS)
    assert seed() == 8
    assert seed() == 8
    warnings = check_schema(get_settings())
    assert warnings == []
    assert "author_id=? AND create_time BETWEEN ? AND ?" in LIVE_DURATION_SQL
    assert "deleted" not in LIVE_DURATION_SQL
    assert "status" not in LIVE_DURATION_SQL
    count, minutes = live_duration(501, datetime(2026, 1, 1), datetime(2026, 1, 31, 23, 59, 59))
    assert (count, minutes) == (5, 240)
    room = get_room(1, 9101)
    assert room["tenant_id"] == 1
    assert room["avatar_url"].endswith("/avatar/stub")
    assert room["screen_type"] == 1
    assert room["watch_type"] == 1
    assert room["view_url"] == "http://127.0.0.1/watch/9101"
    assert room["reserve_count"] == 0
    assert room["deleted"] == 0
    assert room["bind_mobile_password"] == "******"
    assert room["login_pwd"] == "******"
    assert str(room["live_name"]).startswith("[STUB]")
    assert get_room(1, 9103) is None
    assert room_exists_for_bind(1, 9101) is True
    assert room_exists_for_bind(1, 9103) is False
    assert room_exists_for_bind(2, 9101) is False
    cloned = load_settings("test")
    cloned.football_live.tenant_map = {"1": 9}
    assert get_room(1, 9101, settings=cloned) is None
    with pytest.raises(SelectOnlyError):
        with football_engine().connect() as conn:
            conn.exec_driver_sql("DELETE FROM live_room WHERE id=%s", (9101,))
    assert get_room(1, 9101) is not None


def test_football_schema_mismatch_names_columns():
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


def test_football_stub_seed_twice_eight_scenarios():
    from tools.football_stub.seed import FAKE_BIND_PASSWORD, FAKE_LOGIN_PASSWORD, MISSING_ROOM_ID, SCENARIOS, seed

    assert len({row["live_name"] for row in SCENARIOS}) == 8
    assert {row["status"] for row in SCENARIOS} == {1, 2, 3, 4, 5}
    assert seed() == 8
    assert seed() == 8
    with football_engine().connect() as conn:
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM live_room").scalar()
        names = [row[0] for row in conn.exec_driver_sql("SELECT live_name FROM live_room ORDER BY id").all()]
        secrets = conn.exec_driver_sql(
            "SELECT bind_mobile_password, login_pwd FROM live_room WHERE id=%s",
            (9101,),
        ).one()
    assert count == 8
    assert names == [row["live_name"] for row in SCENARIOS]
    assert all(str(name).startswith("[STUB]") for name in names)
    assert secrets[0] == FAKE_BIND_PASSWORD
    assert secrets[1] == FAKE_LOGIN_PASSWORD
    shown = get_room(1, 9101)
    assert shown["bind_mobile_password"] == "******"
    assert shown["login_pwd"] == "******"
    assert shown["bind_mobile_password"] != secrets[0]
    assert get_room(1, MISSING_ROOM_ID) is None


def test_stub_scripts_refuse_prod():
    env = os.environ.copy()
    env["IMS_ENV"] = "prod"
    for args in (["-m", "tools.football_stub.seed"], ["-m", "tools.football_stub.seed", "create"]):
        proc = subprocess.run([sys.executable, *args], cwd=str(ROOT), env=env, capture_output=True, text=True)
        assert proc.returncode == 2


def _counts():
    with session_scope() as session:
        with use_context(system_context(1)):
            users = list(session.scalars(select(User.id)))
            depts = list(session.scalars(select(Dept.id)))
            pending = list(session.scalars(select(MigrationPending.id)))
    return len(users), len(depts), len(pending)


def _auto(table: str):
    with session_scope() as session:
        value = session.execute(
            text(
                "SELECT AUTO_INCREMENT FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :name"
            ),
            {"name": table},
        ).scalar()
        max_id = session.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM `{table}`")).scalar()
    return int(value), int(max_id)


def test_migrate_opsbiz_keeps_keys_and_pending():
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
        conn.execute(text("INSERT INTO system_dept VALUES (88011, '迁部门', 0, 0, 0, 0)"))
        conn.execute(text("INSERT INTO system_users VALUES (88001, 'mig_ok', '迁用户', 88011, 0, 0, 0)"))
        conn.execute(text("INSERT INTO system_users VALUES (88002, 'mig_orphan', '孤儿', 999999, 0, 0, 0)"))
    migrate_sample(source, "opsbiz")
    with session_scope() as session:
        with use_context(system_context(1)):
            user = session.get(User, 88001)
            dept = session.get(Dept, 88011)
            assert user.creator == 8
            assert user.tenant_id == 1
            assert user.main_dept_id == 88011
            assert user.username == "mig_ok"
            assert dept.creator == 8
            assert session.get(User, 88002) is None
            pending = list(session.scalars(select(MigrationPending)))
            assert any(row.source_id == "88002" and "未知部门" in row.reason for row in pending)
    before = _counts()
    migrate_sample(source, "opsbiz")
    assert _counts() == before
    for table in ("ims_sys_user", "ims_sys_dept"):
        auto, max_id = _auto(table)
        assert auto == max_id + 1


def test_migrate_football_users_by_tenant():
    source = create_engine("sqlite://")
    with source.begin() as conn:
        conn.execute(text("CREATE TABLE system_users (id INTEGER PRIMARY KEY, username TEXT, nickname TEXT, tenant_id INTEGER, deleted INTEGER)"))
        conn.execute(text("INSERT INTO system_users VALUES (88101, 'fb_ok', '可迁', 1, 0)"))
        conn.execute(text("INSERT INTO system_users VALUES (88102, 'fb_skip', '跳过', 2, 0)"))
        conn.execute(text("INSERT INTO system_users VALUES (88103, 'fb_pending', '待定', 9, 0)"))
        conn.execute(text("INSERT INTO system_users VALUES (88104, 'fb_skip2', '跳过二', 121, 0)"))
    migrate_sample(source, "football")
    with session_scope() as session:
        with use_context(system_context(1)):
            kept = session.get(User, 88101)
            assert kept is not None and kept.creator == 8 and kept.tenant_id == 1
            assert session.get(User, 88102) is None
            assert session.get(User, 88103) is None
            assert session.get(User, 88104) is None
            pending_ids = {row.source_id for row in session.scalars(select(MigrationPending))}
            assert "88103" in pending_ids
            assert "88102" not in pending_ids
            assert "88104" not in pending_ids


def _write_def(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_scaffold_rules_and_service_guard(tmp_path):
    sample = _write_def(
        tmp_path / "ok.yaml",
        """
name: org_unit
entity: OrgUnit
table: ims_org_unit
perm: ims:org:unit
registry:
  - ims_org_unit
fields:
  - name: name
    type: string
    length: 50
  - name: parent_id
    type: ref
    target: self
    on_delete: RESTRICT
""",
    )
    out = tmp_path / "out"
    generate(sample, out)
    model = (out / "model.py").read_text(encoding="utf-8")
    assert "generator-version:" in model
    assert "def-hash:" in model
    assert "generated-at:" in model
    assert "parent_id" in model and "RESTRICT" in model
    service = out / "service.py"
    original = service.read_text(encoding="utf-8")
    service.write_text(original + "\n# edited\n", encoding="utf-8")
    generate(sample, out)
    assert "# edited" in service.read_text(encoding="utf-8")
    generated = (out / "service.py.generated").read_text(encoding="utf-8")
    assert "# edited" not in generated
    assert "def-hash:" in generated
    generate(sample, out, force=True)
    assert "# edited" not in service.read_text(encoding="utf-8")

    missing = _write_def(tmp_path / "missing.yaml", sample.read_text(encoding="utf-8").replace("ims_org_unit", "ims_other", 1))
    with pytest.raises(ScaffoldError, match="表未登记"):
        generate(missing, tmp_path / "bad-table")
    bad_perm = _write_def(tmp_path / "perm.yaml", sample.read_text(encoding="utf-8").replace("ims:org:unit", "sys:org:unit"))
    with pytest.raises(ScaffoldError, match="权限码前缀"):
        generate(bad_perm, tmp_path / "bad-perm")
    bad_dict = _write_def(
        tmp_path / "dict.yaml",
        """
table: ims_org_unit
perm: ims:org:unit
registry: [ims_org_unit]
fields:
  - name: status
    type: dict
    dict: dict_not_a_real_type
""",
    )
    with pytest.raises(ScaffoldError, match="字典类型不存在"):
        generate(bad_dict, tmp_path / "bad-dict")
    bad_ref = _write_def(
        tmp_path / "ref.yaml",
        """
table: ims_org_unit
perm: ims:org:unit
registry: [ims_org_unit]
fields:
  - name: owner_user_id
    type: ref
    target: ims_sys_user
""",
    )
    with pytest.raises(ScaffoldError, match="缺少删除策略"):
        generate(bad_ref, tmp_path / "bad-ref")


def test_docs_error_codes_and_openapi(tmp_path):
    from app.catalog import SHARED_TABLES
    from tools.api_gen import dump_openapi
    from tools.docs_gen import write_docs

    assert len(SHARED_TABLES) == 12
    docs = write_docs(tmp_path / "docs")
    tables = next(path.read_text(encoding="utf-8") for path in docs if path.name.startswith("表名"))
    for table, prefix, title in SHARED_TABLES:
        assert f"| {table} | {prefix} | {title} |" in tables
    refs = next(path.read_text(encoding="utf-8") for path in docs if path.name.startswith("外键"))
    assert "RESTRICT" in refs
    er = next(path.read_text(encoding="utf-8") for path in docs if path.name == "ER.md")
    assert "erDiagram" in er
    assert SHARED_TABLES[0][0] in er
    rows = export_error_codes(tmp_path / "error-codes.json")
    assert rows[0]["code"] == 1001
    assert all(row["strategy"] for row in rows)
    with pytest.raises(ValueError):
        export_error_codes(tmp_path / "empty.json", entries=[ErrorEntry(1001, "COMMON", "提示", "")])
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    dump_openapi(first, tmp_path / "a.ts")
    dump_openapi(second, tmp_path / "b.ts")
    assert first.read_bytes() == second.read_bytes()
    body = json.loads(first.read_text(encoding="utf-8"))
    assert "paths" in body
    client = (tmp_path / "a.ts").read_text(encoding="utf-8")
    assert "export const operations" in client
    assert "generated-at" not in client
    parsed = yaml.safe_load("ok: true")
    assert parsed["ok"] is True
