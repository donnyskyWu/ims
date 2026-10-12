"""E/F/G 单测：每个 test_ut_* 对应 02-单测用例.md 的一行。"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.clock import advance, freeze, now_naive
from app.core.config import get_settings
from app.core.context import RequestContext, system_context, use_context
from app.core.errors import BizError
from app.core.redis_client import get_redis
from app.db.session import session_scope
from app.domains.demo.model import DemoOrder
from app.domains.file.model import StoredFile
from app.domains.file.service import SCENES, bind, export_scene_registry, scene_registry, unbind, upload
from app.domains.flow.model import FlowInstance, FlowTask
from app.domains.flow.service import callbacks
from app.domains.flow.service import cancel as flow_cancel
from app.domains.message.model import Message, NotifyRecord
from app.domains.message.service import retry_pending
from app.domains.system.model import (
    ChangeLog,
    Dept,
    DictData,
    LoginLog,
    Menu,
    OperateLog,
    Param,
    Role,
    RoleMenu,
    SensitiveViewLog,
    Timeline,
    UserDept,
    UserRole,
)
from app.domains.todo.model import Todo, TodoAssignee
from app.domains.todo.service import cancel as todo_cancel
from app.domains.todo.service import complete, detail, todo_create, users_with_perm
from app.integrations.dingtalk.client import ding_state
from app.services.timeline import query_timeline
from tests.conftest import auth, login
from tests.stddata import D1, D2, ROOT, T2_ADMIN, U_ADMIN, U_DEPT, U_SELF

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8
DOC_LIMIT = "仅支持 pdf、doc、docx、ppt、pptx、xls、xlsx 格式"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _viewer_name(data: bytes) -> str:
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    pixels = image.load()
    length = int(pixels[0, 0][0])
    raw = bytes(int(pixels[index + 1, 0][0]) for index in range(length))
    return raw.decode("utf-8")


@pytest.fixture
def storage():
    settings = get_settings()
    previous = settings.storage_root
    folder = Path(tempfile.mkdtemp(prefix="ims-ut-file-"))
    settings.storage_root = str(folder)
    yield folder
    settings.storage_root = previous
    shutil.rmtree(folder, ignore_errors=True)


def _ctx(user_id, perms=None, username="tester", nickname=None, scopes=None, depts=None):
    return RequestContext(
        user_id=user_id,
        tenant_id=1,
        perm_codes=set(perms or []),
        data_scopes=set(scopes or ["ALL"]),
        dept_ids=list(depts or []),
        username=username,
        nickname=nickname or username,
    )


def _grant(role_id: int, codes: list[str]) -> None:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menus = {menu.perm_code: menu.id for menu in session.scalars(select(Menu)) if menu.perm_code}
            have = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == role_id)))
            for code in codes:
                if menus[code] not in have:
                    session.add(RoleMenu(role_id=role_id, menu_id=menus[code], tenant_id=1))


def _revoke(role_id: int, code: str) -> None:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu_id = session.scalar(select(Menu.id).where(Menu.perm_code == code))
            link = session.scalar(select(RoleMenu).where(RoleMenu.role_id == role_id, RoleMenu.menu_id == menu_id))
            if link is not None:
                session.delete(link)


def _label(session, dict_type: str, value: str) -> str:
    row = session.scalar(select(DictData).where(DictData.dict_type == dict_type, DictData.dict_value == value))
    assert row is not None, value
    return row.dict_label


def _upload(client, headers, scene, name, payload, content_type="application/octet-stream"):
    return client.post(
        "/admin-api/ims/file/upload",
        headers={"Authorization": headers["Authorization"]},
        data={"scene": scene},
        files={"file": (name, payload, content_type)},
    )


def _send(client, headers, receiver, title, event, key):
    return client.post(
        "/admin-api/ims/message/send",
        headers=headers,
        json={"receiverId": str(receiver), "title": title, "content": "正文", "eventType": event, "bizKey": key},
    ).json()


def _publish(client, headers, code, nodes, name="流程"):
    return client.post(
        "/admin-api/ims/flow/template",
        headers=headers,
        json={"code": code, "name": name, "bizType": "leave", "nodes": nodes},
    ).json()


def _start(client, headers, code, biz_id=1):
    return client.post(
        "/admin-api/ims/flow/start",
        headers=headers,
        json={"code": code, "bizType": "leave", "bizId": str(biz_id)},
    ).json()


def _act(client, headers, instance_id, action, comment=None):
    body = {"instanceId": instance_id, "action": action}
    if comment is not None:
        body["comment"] = comment
    return client.post("/admin-api/ims/flow/act", headers=headers, json=body).json()


def _job(client, headers, name):
    return client.post("/admin-api/ims/system/job/run", headers=headers, json={"name": name}).json()


def test_ut_e01_01(client):
    """UT-E01-01"""
    # UT-E01-01
    settings = get_settings()
    previous = settings.storage_root
    root = Path("/tmp/ims")
    if root.exists():
        shutil.rmtree(root)
    settings.storage_root = "/tmp/ims"
    freeze(datetime(2026, 10, 8, 9, 0, 0))
    try:
        body = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", "a.pdf", PDF, "application/pdf").json()
        assert body["code"] == 0, body
        file_key = body["data"]["fileKey"]
        assert re.fullmatch(r"TRAIN_DOC/1/202610/[0-9a-f]{32}\.pdf", file_key)
        assert not file_key.startswith("/")
        target = root / file_key
        assert target.is_file()
        assert str(target) == f"/tmp/ims/{file_key}"
        assert target.read_bytes() == PDF
        with session_scope() as session:
            row = session.scalar(select(StoredFile).where(StoredFile.file_key == file_key))
            assert row.scene == "TRAIN_DOC"
            assert row.original_name == "a.pdf"
            assert row.size == len(PDF)
            assert row.content_type == "application/pdf"
            assert row.creator == U_ADMIN
            assert row.tenant_id == 1
            assert row.sha256 == hashlib.sha256(PDF).hexdigest()
    finally:
        settings.storage_root = previous
        shutil.rmtree(root, ignore_errors=True)


def test_ut_e01_02(client):
    """UT-E01-02"""
    # UT-E01-02
    settings = get_settings()
    previous = settings.storage_root
    folder = Path("/tmp/ims-e01-02-ro")
    if folder.exists():
        folder.chmod(0o755)
        shutil.rmtree(folder)
    folder.mkdir()
    folder.chmod(0o555)
    settings.storage_root = str(folder)
    try:
        body = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", "a.pdf", PDF, "application/pdf").json()
        assert body["code"] == 5005
        assert list(folder.rglob(".write_probe_*")) == []
        assert list(folder.rglob("*.tmp")) == []
        assert [item for item in folder.rglob("*") if item.is_file()] == []
    finally:
        settings.storage_root = previous
        folder.chmod(0o755)
        shutil.rmtree(folder, ignore_errors=True)


def test_ut_e01_03(client, storage):
    """UT-E01-03"""
    # UT-E01-03
    with session_scope(commit=True) as session:
        with use_context(RequestContext(user_id=T2_ADMIN, tenant_id=2, username="t2_admin", nickname="租户二管理员", data_scopes={"ALL"})):
            saved = upload("TRAIN_DOC", "a.pdf", PDF, T2_ADMIN)
        row = session.scalar(select(StoredFile).where(StoredFile.file_key == saved["fileKey"]))
        assert row.tenant_id == 2
    body = client.get(
        "/admin-api/ims/file/download",
        headers=auth(client, "u_admin"),
        params={"fileKey": saved["fileKey"]},
    ).json()
    assert body["code"] == 1504


def test_ut_e01_04(client):
    """UT-E01-04"""
    # UT-E01-04
    headers = auth(client, "u_admin")
    with patch("app.domains.file.service.Path.read_bytes", side_effect=AssertionError("不应读取文件")):
        for key in ("../../etc/passwd", "/etc/passwd", "..%2F..%2Fetc"):
            body = client.get("/admin-api/ims/file/download", headers=headers, params={"fileKey": key}).json()
            assert body["code"] == 1001, key


def test_ut_e01_05(client, storage):
    """UT-E01-05"""
    # UT-E01-05
    _grant(202, ["ims:file:query"])
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            link = session.scalar(select(UserDept).where(UserDept.user_id == U_DEPT, UserDept.dept_id == D2))
            session.delete(link)
    headers = auth(client, "u_admin")
    uploaded = _upload(client, headers, "TRAIN_DOC", "a.pdf", PDF, "application/pdf").json()
    key = uploaded["data"]["fileKey"]
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            order_id = session.scalar(select(DemoOrder.id).where(DemoOrder.code == "OD2"))
            bind(key, "ims_demo_order", int(order_id))
    body = client.get("/admin-api/ims/file/download", headers=auth(client, "u_dept"), params={"fileKey": key}).json()
    assert body["code"] == 1504


def test_ut_e01_06(client, storage):
    """UT-E01-06"""
    # UT-E01-06
    _grant(202, ["ims:file:query"])
    original = "资料.pdf"
    uploaded = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", original, PDF, "application/pdf").json()
    assert uploaded["code"] == 0, uploaded
    key = uploaded["data"]["fileKey"]
    denied = client.get("/admin-api/ims/file/download", headers=auth(client, "u_dept"), params={"fileKey": key}).json()
    assert denied["code"] == 1504
    downloaded = client.get("/admin-api/ims/file/download", headers=auth(client, "u_admin"), params={"fileKey": key})
    assert downloaded.status_code == 200
    assert downloaded.content == PDF
    disposition = downloaded.headers["content-disposition"]
    assert unquote(disposition.split("filename*=UTF-8''", 1)[1]) == original


def test_ut_e01_07(client, storage):
    """UT-E01-07"""
    # UT-E01-07
    headers = auth(client, "u_admin")
    created = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "绑定文件"}).json()
    assert created["code"] == 0, created
    ident = int(created["data"]["id"])
    uploaded = _upload(client, headers, "TRAIN_DOC", "a.pdf", PDF, "application/pdf").json()
    key = uploaded["data"]["fileKey"]
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            bind(key, "ims_demo_order", ident)
    removed = client.delete(f"/admin-api/ims/demo/order/delete?id={ident}", headers=headers).json()
    assert removed["code"] == 0, removed
    assert (storage / key).is_file()
    with session_scope() as session:
        row = session.scalar(select(StoredFile).where(StoredFile.file_key == key))
        assert row.biz_id is None
        assert row.orphan_since is not None


def test_ut_e01_08(client, storage):
    """UT-E01-08"""
    # UT-E01-08
    freeze(datetime(2026, 10, 1, 0, 0, 0))
    headers = auth(client, "u_admin")
    orphan = _upload(client, headers, "TRAIN_DOC", "orphan.pdf", PDF, "application/pdf").json()["data"]["fileKey"]
    bound = _upload(client, headers, "TRAIN_DOC", "bound.pdf", PDF, "application/pdf").json()["data"]["fileKey"]
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            bind(bound, "ims_demo_order", 1)
            unbind(bound)
    advance(timedelta(hours=25))
    ran = _job(client, auth(client, "u_admin"), "file_cleanup")
    assert ran["code"] == 0, ran
    assert not (storage / orphan).exists()
    assert (storage / bound).is_file()


def test_ut_e02_01(client, storage):
    """UT-E02-01"""
    # UT-E02-01
    body = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", "a.exe", b"MZ" + b"\x00" * 8).json()
    assert body["code"] == 5005
    assert body["msg"] == DOC_LIMIT


def test_ut_e02_02(client, storage):
    """UT-E02-02"""
    # UT-E02-02
    body = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", "a.pdf", b"MZ" + b"\x00" * 16).json()
    assert body["code"] == 5005
    assert body["msg"] == "文件内容与格式不符"


def test_ut_e02_03(client, storage):
    """UT-E02-03"""
    # UT-E02-03
    header = b"%PDF-1.4\n"
    payload = header + b"0" * (101 * 1024 * 1024 - len(header))
    body = _upload(client, auth(client, "u_admin"), "TRAIN_DOC", "big.pdf", payload, "application/pdf").json()
    assert body["code"] == 5005
    assert body["msg"] == "文件不能超过 100 MB"


def test_ut_e02_04(client, storage):
    """UT-E02-04"""
    # UT-E02-04
    body = _upload(client, auth(client, "u_admin"), "NOPE", "a.pdf", PDF, "application/pdf").json()
    assert body["code"] == 1001
    assert body["msg"] == "不支持的上传场景"


def test_ut_e02_05(client, storage):
    """UT-E02-05"""
    # UT-E02-05
    body = _upload(client, auth(client, "u_admin"), "TRAIN_VIDEO", "a.mp4", MP4, "video/mp4").json()
    assert body["code"] == 0, body
    assert body["data"]["fileKey"].endswith(".mp4")
    with session_scope() as session:
        row = session.scalar(select(StoredFile).where(StoredFile.file_key == body["data"]["fileKey"]))
        assert row.scene == "TRAIN_VIDEO"


def test_ut_e02_06():
    """UT-E02-06"""
    # UT-E02-06
    payload = json.loads(export_scene_registry())
    assert set(payload) == set(SCENES) == set(scene_registry())
    for code, spec in SCENES.items():
        exts = [item for item in spec["exts"] if item != "jpeg"]
        assert payload[code]["exts"] == exts
        assert payload[code]["maxBytes"] == spec["max_bytes"]
        assert payload[code]["maxMb"] == spec["max_bytes"] // (1024 * 1024)
    assert payload == scene_registry()


def test_ut_e02_07(client, storage):
    """UT-E02-07"""
    # UT-E02-07
    assert scene_registry()["TEST_IMAGE"]["watermark"] is True
    payload = _png()
    uploaded = _upload(client, auth(client, "u_admin"), "TEST_IMAGE", "shot.png", payload, "image/png").json()
    assert uploaded["code"] == 0, uploaded
    key = uploaded["data"]["fileKey"]
    preview = client.get("/admin-api/ims/file/preview", headers=auth(client, "u_admin"), params={"fileKey": key})
    assert preview.status_code == 200
    assert preview.content != payload
    assert _viewer_name(preview.content) == "管理员"
    assert (storage / key).read_bytes() == payload


def test_ut_f01_01(client):
    """UT-F01-01"""
    # UT-F01-01
    headers = auth(client, "u_admin")
    created = client.post("/admin-api/ims/demo/order/create", headers=headers, json={"name": "新建一单", "amount": "1.00"}).json()
    assert created["code"] == 0, created
    with session_scope() as session:
        rows = list(session.scalars(select(OperateLog)))
        assert len(rows) == 1
        row = rows[0]
        assert row.operator_id == U_ADMIN
        assert row.operator_name == "管理员"
        assert row.module == "示例"
        assert row.action == "新建订单"
        assert row.object_id == str(created["data"]["id"])
        assert row.success == 1
        assert row.ip == "testclient"
        assert isinstance(row.cost_ms, int) and row.cost_ms >= 0


def test_ut_f01_02(client):
    """UT-F01-02"""
    # UT-F01-02
    headers = auth(client, "u_admin")
    body = client.post("/admin-api/ims/demo/order/create", headers=headers, json={}).json()
    assert body["code"] == 1001
    with session_scope() as session:
        rows = list(session.scalars(select(OperateLog)))
        assert len(rows) == 1
        assert rows[0].success == 0
        assert rows[0].error_code == 1001


def test_ut_f01_03(client):
    """UT-F01-03"""
    # UT-F01-03
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "脱敏", "mobile": "13812345678", "idCard": "110101199001011234", "password": "SecretPwd1"},
    ).json()
    assert created["code"] == 0, created
    with session_scope() as session:
        row = session.scalar(select(OperateLog).where(OperateLog.action == "新建订单"))
        digest = json.loads(row.params_digest)
        assert digest["mobile"] == "138****5678"
        assert digest["idCard"] == "110***********1234"
        assert digest["password"] == "******"
        assert "13812345678" not in row.params_digest
        assert "110101199001011234" not in row.params_digest
        assert "SecretPwd1" not in row.params_digest


def test_ut_f01_04(client, monkeypatch):
    """UT-F01-04"""
    # UT-F01-04
    def boom(*args, **kwargs):
        raise RuntimeError("log write failed")

    monkeypatch.setattr("app.domains.system.model.OperateLog", boom)
    body = client.post(
        "/admin-api/ims/demo/order/create",
        headers=auth(client, "u_admin"),
        json={"name": "日志失败仍成功"},
    ).json()
    assert body["code"] == 0, body
    assert body["data"]["id"]


def test_ut_f01_05(client):
    """UT-F01-05"""
    # UT-F01-05
    headers = auth(client, "u_admin")
    with session_scope() as session:
        before = list(session.scalars(select(OperateLog.id)))
    got = client.get("/admin-api/ims/demo/order/page", headers=headers)
    assert got.status_code == 200
    with session_scope() as session:
        after = list(session.scalars(select(OperateLog.id)))
    assert before == after


def test_ut_f01_06(client):
    """UT-F01-06"""
    # UT-F01-06
    freeze(datetime(2026, 10, 12, 8, 0, 0))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            old = OperateLog(module="示例", action="新建订单", success=1, create_time=now_naive() - timedelta(days=181))
            recent = OperateLog(module="示例", action="修改订单", success=1, create_time=now_naive() - timedelta(days=179))
            session.add(old)
            session.add(recent)
            session.flush()
            old_id, recent_id = old.id, recent.id
    ran = _job(client, auth(client, "u_admin"), "log_cleanup")
    assert ran["code"] == 0, ran
    with session_scope() as session:
        gone = session.scalar(select(OperateLog).where(OperateLog.id == old_id).execution_options(include_deleted=True))
        kept = session.scalar(select(OperateLog).where(OperateLog.id == recent_id))
        assert gone is not None and gone.deleted != 0
        assert kept is not None and kept.deleted == 0
        assert session.scalar(select(OperateLog).where(OperateLog.id == old_id)) is None


def test_ut_f01_07(app):
    """UT-F01-07"""
    # UT-F01-07
    hits = []
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        methods = set(getattr(route, "methods", None) or set())
        summary = getattr(route, "summary", "") or ""
        lowered = f"{path} {summary}".lower().replace("_", "").replace("-", "")
        if ("操作日志" in f"{path} {summary}" or "operatelog" in lowered) and methods & {"PUT", "PATCH", "DELETE"}:
            hits.append(path)
    assert hits == []


def test_ut_f01_08(client):
    """UT-F01-08"""
    # UT-F01-08
    login(client, "u_ro", "bad-pass")
    get_redis().set(
        "ims:login:fail:u_self",
        json.dumps({"count": 5, "first": now_naive().isoformat(timespec="seconds")}),
        ex=1000,
    )
    login(client, "u_self", "bad-pass")
    login(client, "u_frozen")
    token = login(client, "u_dept").json()["data"]["accessToken"]
    client.post("/admin-api/ims/auth/logout", headers={"Authorization": f"Bearer {token}"})
    with session_scope() as session:
        logs = list(session.scalars(select(LoginLog).order_by(LoginLog.id)))
        labels = [_label(session, "dict_login_result", row.result) for row in logs]
    assert labels == ["密码错", "已锁定", "已冻结", "成功", "登出"]


def test_ut_f02_01(client):
    """UT-F02-01"""
    # UT-F02-01
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "金额", "amount": "10.00"},
    ).json()
    assert created["code"] == 0, created
    ident = created["data"]["id"]
    updated = client.put(
        "/admin-api/ims/demo/order/update",
        headers=headers,
        json={"id": ident, "amount": "12.00"},
    ).json()
    assert updated["code"] == 0, updated
    with session_scope() as session:
        rows = list(session.scalars(select(ChangeLog).where(ChangeLog.biz_id == int(ident), ChangeLog.field == "amount")))
        assert len(rows) == 1
        row = rows[0]
        assert row.field == "amount"
        assert row.field_label == "金额"
        assert row.before_value == "10.00"
        assert row.after_value == "12.00"
        assert row.reason == "USER_EDIT"


def test_ut_f02_02(client):
    """UT-F02-02"""
    # UT-F02-02
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "手机", "mobile": "13812345678"},
    ).json()
    ident = created["data"]["id"]
    updated = client.put(
        "/admin-api/ims/demo/order/update",
        headers=headers,
        json={"id": ident, "mobile": "13912345678"},
    ).json()
    assert updated["code"] == 0, updated
    with session_scope() as session:
        rows = list(session.scalars(select(ChangeLog).where(ChangeLog.biz_id == int(ident), ChangeLog.field == "mobile")))
        assert len(rows) == 1
        assert rows[0].before_value == "138****5678"
        assert rows[0].after_value == "139****5678"
        assert "13812345678" not in (rows[0].before_value or "")
        assert "13912345678" not in (rows[0].after_value or "")


def test_ut_f02_03(client):
    """UT-F02-03"""
    # UT-F02-03
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "证件", "idCard": "110101199001011234"},
    ).json()
    ident = created["data"]["id"]
    plain = client.get(f"/admin-api/ims/demo/order/plain?id={ident}", headers=headers).json()
    assert plain["code"] == 0, plain
    with session_scope() as session:
        rows = list(session.scalars(select(SensitiveViewLog).where(SensitiveViewLog.biz_id == int(ident))))
        assert len(rows) == 1
        row = rows[0]
        assert row.viewer_id == U_ADMIN
        assert row.create_time is not None
        assert row.ip == "testclient"
        assert row.biz_type == "ims_demo_order"
        assert row.biz_id == int(ident)


def test_ut_f02_04(tmp_path):
    """UT-F02-04"""
    # UT-F02-04
    from tools.static_checks import check_plain_without_log

    folder = tmp_path / "app" / "domains" / "demo"
    folder.mkdir(parents=True)
    (folder / "router.py").write_text("def view():\n    return mark(returns_plain=True)\n", encoding="utf-8")
    problems = check_plain_without_log(tmp_path)
    assert problems


def test_ut_f02_05():
    """UT-F02-05"""
    # UT-F02-05
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            for hour in (10, 9, 11):
                session.add(
                    Timeline(
                        biz_type="demo_order",
                        biz_id=7,
                        event_type="NOTE",
                        title=f"{hour:02d}:00",
                        event_time=datetime(2026, 10, 12, hour, 0, 0),
                        operator_id=U_ADMIN,
                    )
                )
            session.flush()
            rows = query_timeline("demo_order", 7)
    assert [item["eventTime"] for item in rows] == [
        datetime(2026, 10, 12, 11, 0, 0),
        datetime(2026, 10, 12, 10, 0, 0),
        datetime(2026, 10, 12, 9, 0, 0),
    ]


def test_ut_g01_01(client):
    """UT-G01-01"""
    # UT-G01-01
    headers = auth(client, "u_admin")
    before_unread = client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"]
    before_calls = len(ding_state.notify_calls)
    body = _send(client, headers, U_ADMIN, "通知甲", "EVT_A", "g01-01")
    assert body["code"] == 0, body
    assert body["data"]["skipped"] is False
    after_unread = client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"]
    assert after_unread == before_unread + 1
    assert len(ding_state.notify_calls) == before_calls + 1
    with session_scope() as session:
        rows = list(session.scalars(select(NotifyRecord).where(NotifyRecord.biz_key == "g01-01")))
        assert {row.channel for row in rows} == {"SITE", "DINGTALK"}
        assert {row.status for row in rows} == {"SENT"}
        assert _label(session, "dict_notify_status", "SENT") == "已发送"


def test_ut_g01_02(client):
    """UT-G01-02"""
    # UT-G01-02
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.scalar(select(Param).where(Param.param_key == "dingtalk.notify.enabled"))
            row.value = "false"
    before = len(ding_state.notify_calls)
    headers = auth(client, "u_admin")
    body = _send(client, headers, U_ADMIN, "关闭通知", "EVT_OFF", "g01-02")
    assert body["code"] == 0, body
    assert len(ding_state.notify_calls) == before
    with session_scope() as session:
        record = session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "g01-02", NotifyRecord.channel == "DINGTALK"))
        assert record.status == "DISABLED"
        assert _label(session, "dict_notify_status", record.status) == "已关闭"
        assert session.scalar(select(Message).where(Message.receiver_id == U_ADMIN, Message.title == "关闭通知")) is not None


def test_ut_g01_03(client):
    """UT-G01-03"""
    # UT-G01-03
    ding_state.error = "notify_fail"
    headers = auth(client, "u_admin")
    body = _send(client, headers, U_ADMIN, "失败通知", "EVT_FAIL", "g01-03")
    assert body["code"] == 0, body
    assert body["data"]["dingStatus"] == "RETRYING"
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            site = session.scalar(select(Message).where(Message.receiver_id == U_ADMIN, Message.title == "失败通知"))
            assert site is not None
            retry_pending()
            retry_pending()
            record = session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "g01-03", NotifyRecord.channel == "DINGTALK"))
            assert record.status == "FAILED"
            assert record.retry_count == 3
            assert _label(session, "dict_notify_status", "FAILED") == "失败"


def test_ut_g01_04(client):
    """UT-G01-04"""
    # UT-G01-04
    headers = auth(client, "u_admin")
    before = client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"]
    first = _send(client, headers, U_ADMIN, "第一次", "EVT_DUP", "g01-04")
    second = _send(client, headers, U_ADMIN, "第二次", "EVT_DUP", "g01-04")
    after = client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"]
    assert first["data"]["skipped"] is False
    assert second["data"]["skipped"] is True
    assert second["data"]["status"] == "SKIPPED_DUP"
    assert after == before + 1
    with session_scope() as session:
        assert _label(session, "dict_notify_status", "SKIPPED_DUP") == "去重跳过"
        skipped = session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "g01-04", NotifyRecord.status == "SKIPPED_DUP"))
        assert skipped is not None


def test_ut_g01_05(client):
    """UT-G01-05"""
    # UT-G01-05
    headers = auth(client, "u_admin")
    _send(client, headers, U_ADMIN, "已发送", "EVT_OK", "g01-05-ok")
    ding_state.error = "notify_fail"
    _send(client, headers, U_ADMIN, "待补发", "EVT_BAD", "g01-05-bad")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            retry_pending()
            retry_pending()
            failed_id = session.scalar(
                select(NotifyRecord.id).where(NotifyRecord.biz_key == "g01-05-bad", NotifyRecord.channel == "DINGTALK")
            )
            sent_id = session.scalar(
                select(NotifyRecord.id).where(NotifyRecord.biz_key == "g01-05-ok", NotifyRecord.channel == "DINGTALK")
            )
            failed = session.get(NotifyRecord, failed_id)
            assert failed.status == "FAILED"
    ding_state.error = None
    resent = client.post("/admin-api/ims/message/notify/resend", headers=headers, json={"id": str(failed_id)}).json()
    assert resent["code"] == 0, resent
    assert resent["data"]["status"] == "SENT"
    again = client.post("/admin-api/ims/message/notify/resend", headers=headers, json={"id": str(sent_id)}).json()
    assert again["code"] == 1001


def test_ut_g01_06(client):
    """UT-G01-06"""
    # UT-G01-06
    headers = auth(client, "u_admin")
    ids = []
    for index in range(3):
        sent = _send(client, headers, U_ADMIN, f"未读{index}", "EVT_READ", f"g01-06-{index}")
        ids.append(sent["data"]["messageId"])
    marked = client.post("/admin-api/ims/message/read", headers=headers, json={"id": ids[0]}).json()
    assert marked["code"] == 0, marked
    unread = client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"]
    assert unread == 2
    cleared = client.post("/admin-api/ims/message/read-all", headers=headers).json()
    assert cleared["code"] == 0, cleared
    assert client.get("/admin-api/ims/message/unread-count", headers=headers).json()["data"]["count"] == 0


def test_ut_g01_07(client):
    """UT-G01-07"""
    # UT-G01-07
    sent = _send(client, auth(client, "u_dept"), U_DEPT, "别人的", "EVT_OTHER", "g01-07")
    body = client.post(
        "/admin-api/ims/message/read",
        headers=auth(client, "u_admin"),
        json={"id": sent["data"]["messageId"]},
    ).json()
    assert body["code"] == 1504


def test_ut_g01_08(client):
    """UT-G01-08"""
    # UT-G01-08
    headers = auth(client, "u_admin")
    ids = []
    for index, title in enumerate(("已读甲", "已读乙", "未读丙")):
        sent = _send(client, headers, U_ADMIN, title, "EVT_PAGE", f"g01-08-{index}")
        ids.append(sent["data"]["messageId"])
    client.post("/admin-api/ims/message/read", headers=headers, json={"id": ids[0]})
    client.post("/admin-api/ims/message/read", headers=headers, json={"id": ids[1]})
    unread = client.get("/admin-api/ims/message/my/page?readStatus=UNREAD", headers=headers).json()
    read = client.get("/admin-api/ims/message/my/page?readStatus=READ", headers=headers).json()
    entire = client.get("/admin-api/ims/message/my/page?readStatus=ALL", headers=headers).json()
    assert unread["data"]["total"] == 1
    assert read["data"]["total"] == 2
    assert entire["data"]["total"] == 3


def test_ut_g02_01(client):
    """UT-G02-01"""
    # UT-G02-01
    headers = auth(client, "u_admin")
    before = client.get("/admin-api/ims/todo/my/count", headers=headers).json()["data"]["total"]
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            created = todo_create("MANUAL", 801, "APPROVAL", "待办甲", user_ids=[U_ADMIN])
    after = client.get("/admin-api/ims/todo/my/count", headers=headers).json()["data"]["total"]
    assert after == before + 1
    assert created["status"] == "PENDING"
    with session_scope() as session:
        assert _label(session, "dict_todo_status", "PENDING") == "待处理"


def test_ut_g02_02():
    """UT-G02-02"""
    # UT-G02-02
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            first = todo_create("MANUAL", 802, "APPROVAL", "已有", user_ids=[U_DEPT])
            second = todo_create("MANUAL", 802, "APPROVAL", "重复", user_ids=[U_SELF])
            assert first["id"] == second["id"]
            count = session.scalar(select(Todo.id).where(Todo.source_type == "MANUAL", Todo.source_id == 802, Todo.type == "APPROVAL"))
            rows = list(session.scalars(select(Todo).where(Todo.source_type == "MANUAL", Todo.source_id == 802, Todo.type == "APPROVAL")))
            assert len(rows) == 1
            assert count == first["id"]


def test_ut_g02_03():
    """UT-G02-03"""
    # UT-G02-03
    _grant(204, ["ims:demo:order:audit"])
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            holders = users_with_perm("ims:demo:order:audit")
            assert U_ADMIN in holders and U_SELF in holders
            created = todo_create("ORDER", 803, "APPROVAL", "按范围", perm_code="ims:demo:order:audit", scope_dept_ids=[D1])
    assert set(created["assigneeIds"]) == {U_ADMIN}


def test_ut_g02_04(client):
    """UT-G02-04"""
    # UT-G02-04
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            created = todo_create("MANUAL", 804, "APPROVAL", "共同", user_ids=[U_ADMIN, U_SELF])
            done = complete(created["id"], U_SELF)
            assert done["status"] == "DONE"
            assert done["doneBy"] == U_SELF
            row = session.get(Todo, created["id"])
            assert row.done_by == U_SELF
    page = client.get("/admin-api/ims/todo/my/page?status=PENDING", headers=auth(client, "u_admin")).json()
    assert all(item["id"] != str(created["id"]) for item in page["data"]["list"])


def test_ut_g02_05(client):
    """UT-G02-05"""
    # UT-G02-05
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            created = todo_create("MANUAL", 805, "APPROVAL", "作废", user_ids=[U_ADMIN])
            stopped = todo_cancel(created["id"], U_ADMIN)
            assert stopped["status"] == "CANCELLED"
            assert _label(session, "dict_todo_status", stopped["status"]) == "已作废"
    counted = client.get("/admin-api/ims/todo/my/count", headers=auth(client, "u_admin")).json()
    assert counted["data"]["total"] == 0


def test_ut_g02_06():
    """UT-G02-06"""
    # UT-G02-06
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            created = todo_create("MANUAL", 806, "APPROVAL", "他人", user_ids=[U_DEPT])
        with use_context(_ctx(U_ADMIN, username="u_admin", nickname="管理员")):
            with pytest.raises(BizError) as queried:
                detail(created["id"])
            assert queried.value.code == 1504
            with pytest.raises(BizError) as handled:
                complete(created["id"], U_ADMIN)
            assert handled.value.code == 1504


def test_ut_g02_07(client):
    """UT-G02-07"""
    # UT-G02-07
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            for index in (1, 2):
                todo_create("DOC", index, "APPROVAL", f"审批{index}", user_ids=[U_ADMIN])
            todo_create("DOC", 3, "RETURN", "归还", user_ids=[U_ADMIN])
            for index in (4, 5, 6):
                todo_create("DOC", index, "WARNING", f"预警{index}", user_ids=[U_ADMIN])
    counted = client.get("/admin-api/ims/todo/my/count", headers=auth(client, "u_admin")).json()
    assert counted["code"] == 0, counted
    by_type = counted["data"]["byType"]
    with session_scope() as session:
        assert _label(session, "dict_todo_type", "APPROVAL") == "审批"
        assert _label(session, "dict_todo_type", "RETURN") == "归还"
        assert _label(session, "dict_todo_type", "WARNING") == "预警"
    assert by_type["APPROVAL"] == 2
    assert by_type["RETURN"] == 1
    assert by_type["WARNING"] == 3


def test_ut_g03_01(client):
    """UT-G03-01"""
    # UT-G03-01
    callbacks.clear()
    seen = []
    callbacks.append(lambda payload: seen.append(dict(payload)))
    _revoke(101, "ims:demo:order:audit")
    _grant(202, ["ims:flow:start"])
    _grant(204, ["ims:demo:order:audit", "ims:flow:act"])
    admin = auth(client, "u_admin")
    published = _publish(
        client,
        admin,
        "G301",
        [{"key": "n1", "assigneeUserId": U_ADMIN}, {"key": "n2", "permCode": "ims:demo:order:audit"}],
    )
    assert published["code"] == 0, published
    started = _start(client, auth(client, "u_dept"), "G301", 1)
    assert started["data"]["status"] == "RUNNING"
    moved = _act(client, admin, started["data"]["id"], "APPROVE")
    assert moved["code"] == 0, moved
    done = _act(client, auth(client, "u_self"), started["data"]["id"], "APPROVE")
    assert done["code"] == 0, done
    assert done["data"]["status"] == "APPROVED"
    approved = [item for item in seen if item.get("result") == "APPROVED"]
    assert len(approved) == 1
    with session_scope() as session:
        tasks = list(session.scalars(select(FlowTask).where(FlowTask.instance_id == int(started["data"]["id"]))))
        assert len(tasks) == 2
        todos = list(
            session.scalars(select(Todo).where(Todo.source_type == "FLOW_TASK", Todo.source_id.in_([task.id for task in tasks])))
        )
        assert len(todos) == 2
        assert all(item.status == "DONE" for item in todos)
    callbacks.clear()


def test_ut_g03_02(client):
    """UT-G03-02"""
    # UT-G03-02
    callbacks.clear()
    seen = []
    callbacks.append(lambda payload: seen.append(dict(payload)))
    _grant(202, ["ims:flow:start"])
    admin = auth(client, "u_admin")
    _publish(client, admin, "G302", [{"key": "n1", "assigneeUserId": U_ADMIN}])
    started = _start(client, auth(client, "u_dept"), "G302", 1)
    rejected = _act(client, admin, started["data"]["id"], "REJECT", "不同意")
    assert rejected["data"]["status"] == "REJECTED"
    assert len(seen) == 1 and seen[0]["result"] == "REJECTED"
    with session_scope() as session:
        mail = session.scalar(select(Message).where(Message.receiver_id == U_DEPT, Message.title == "流程已驳回"))
        assert mail is not None
    callbacks.clear()


def test_ut_g03_03(client):
    """UT-G03-03"""
    # UT-G03-03
    _grant(202, ["ims:flow:start"])
    admin = auth(client, "u_admin")
    _publish(
        client,
        admin,
        "G303",
        [{"key": "n1", "assigneeUserId": U_ADMIN}, {"key": "n2", "assigneeUserId": U_ADMIN}],
    )
    started = _start(client, auth(client, "u_dept"), "G303", 1)
    with session_scope() as session:
        first_id = session.scalar(
            select(FlowTask.id).where(FlowTask.instance_id == int(started["data"]["id"]), FlowTask.node == "n1")
        )
    _act(client, admin, started["data"]["id"], "APPROVE")
    returned = _act(client, admin, started["data"]["id"], "RETURN", "请补充")
    assert returned["code"] == 0, returned
    assert returned["data"]["status"] == "RUNNING"
    assert returned["data"]["currentNode"] == "n1"
    with session_scope() as session:
        pending = list(
            session.scalars(
                select(FlowTask).where(FlowTask.instance_id == int(started["data"]["id"]), FlowTask.status == "PENDING")
            )
        )
        assert len(pending) == 1
        assert pending[0].node == "n1"
        assert pending[0].id != first_id


def test_ut_g03_04(client):
    """UT-G03-04"""
    # UT-G03-04
    _grant(202, ["ims:flow:start"])
    admin = auth(client, "u_admin")
    _publish(client, admin, "G304", [{"key": "n1", "assigneeUserId": U_ADMIN}])
    started = _start(client, auth(client, "u_dept"), "G304", 1)
    with session_scope(commit=True) as session:
        with use_context(_ctx(U_SELF, username="u_self", nickname="本人用户")):
            with pytest.raises(BizError) as exc:
                flow_cancel(int(started["data"]["id"]))
            assert exc.value.code == 1139
        row = session.get(FlowInstance, int(started["data"]["id"]))
        assert row.status == "RUNNING"


def test_ut_g03_05(client):
    """UT-G03-05"""
    # UT-G03-05
    _grant(202, ["ims:flow:start"])
    admin = auth(client, "u_admin")
    _publish(client, admin, "G305", [{"key": "n1", "assigneeUserId": U_ADMIN}])
    started = _start(client, auth(client, "u_dept"), "G305", 1)
    with session_scope(commit=True) as session:
        with use_context(_ctx(U_DEPT, ["ims:flow:start"], username="u_dept", nickname="部门用户")):
            stopped = flow_cancel(int(started["data"]["id"]))
        assert stopped["status"] == "CANCELLED"
        task_ids = list(session.scalars(select(FlowTask.id).where(FlowTask.instance_id == int(started["data"]["id"]))))
        todos = list(session.scalars(select(Todo).where(Todo.source_type == "FLOW_TASK", Todo.source_id.in_(task_ids))))
        assert todos
        assert all(item.status == "CANCELLED" for item in todos)


def test_ut_g03_06(client):
    """UT-G03-06"""
    # UT-G03-06
    _grant(202, ["ims:flow:start"])
    admin = auth(client, "u_admin")
    first = _publish(
        client,
        admin,
        "G306",
        [{"key": "n1", "assigneeUserId": U_ADMIN}, {"key": "n2", "assigneeUserId": U_SELF}],
    )
    started = _start(client, auth(client, "u_dept"), "G306", 1)
    second = _publish(client, admin, "G306", [{"key": "z9", "assigneeUserId": U_ADMIN}], name="修订")
    moved = _act(client, admin, started["data"]["id"], "APPROVE")
    assert moved["data"]["currentNode"] == "n2"
    assert moved["data"]["templateVersionId"] == first["data"]["versionId"]
    latest = _start(client, auth(client, "u_dept"), "G306", 2)
    assert latest["data"]["templateVersionId"] == second["data"]["versionId"]
    assert latest["data"]["currentNode"] == "z9"
    assert latest["data"]["templateVersionId"] != started["data"]["templateVersionId"]


def test_ut_g03_07(client):
    """UT-G03-07"""
    # UT-G03-07
    headers = auth(client, "u_admin")
    published = _publish(client, headers, "G307", [{"key": "n1", "assigneeUserId": U_ADMIN}])
    assert published["code"] == 0, published
    edited = client.post(
        "/admin-api/ims/flow/template",
        headers=headers,
        json={"versionId": published["data"]["versionId"], "nodes": [{"key": "changed", "assigneeUserId": U_DEPT}]},
    ).json()
    assert edited["code"] == 1001


def test_ut_g03_08(client):
    """UT-G03-08"""
    # UT-G03-08
    _grant(202, ["ims:flow:start"])
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Dept, D1).leader_user_id = U_ADMIN
            session.get(Dept, ROOT).leader_user_id = U_SELF
    admin = auth(client, "u_admin")
    _publish(client, admin, "G308", [{"key": "lead", "rule": "LEADER"}])
    dept_headers = auth(client, "u_dept")
    first = _start(client, dept_headers, "G308", 1)
    assert first["data"]["status"] == "RUNNING", first
    with session_scope() as session:
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == int(first["data"]["id"]), FlowTask.status == "PENDING"))
        assert task.assignee == U_ADMIN
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Dept, D1).leader_user_id = U_DEPT
    second = _start(client, dept_headers, "G308", 2)
    assert second["data"]["status"] == "RUNNING", second
    with session_scope() as session:
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == int(second["data"]["id"]), FlowTask.status == "PENDING"))
        assert task.assignee == U_SELF


def test_ut_g03_09(client):
    """UT-G03-09"""
    # UT-G03-09
    _revoke(101, "ims:demo:order:audit")
    _grant(202, ["ims:flow:start", "ims:demo:order:audit"])
    _grant(204, ["ims:demo:order:audit"])
    admin = auth(client, "u_admin")
    _publish(client, admin, "G309", [{"key": "check", "permCode": "ims:demo:order:audit"}])
    started = _start(client, auth(client, "u_dept"), "G309", 1)
    assert started["data"]["status"] == "RUNNING", started
    with session_scope() as session:
        names = list(
            session.scalars(
                select(FlowTask.assignee).where(FlowTask.instance_id == int(started["data"]["id"]), FlowTask.status == "PENDING")
            )
        )
    assert names == [U_SELF]


def test_ut_g03_10(client):
    """UT-G03-10"""
    # UT-G03-10
    _revoke(101, "ims:demo:order:audit")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu_id = session.scalar(select(Menu.id).where(Menu.perm_code == "ims:demo:order:audit"))
            session.add(Role(id=301, role_key="ut_only_a", name="仅发起人", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1))
            session.flush()
            session.add(RoleMenu(role_id=301, menu_id=menu_id, tenant_id=1))
            session.add(UserRole(user_id=U_ADMIN, role_id=301, source="MANUAL", tenant_id=1))
    headers = auth(client, "u_admin")
    _publish(client, headers, "G310", [{"key": "solo", "permCode": "ims:demo:order:audit"}])
    started = _start(client, headers, "G310", 1)
    assert started["data"]["status"] == "SUSPENDED", started
    with session_scope() as session:
        with use_context(system_context(1)):
            holders = set(users_with_perm("ims:flow:manage"))
        todo = session.scalar(select(Todo).where(Todo.source_type == "FLOW_INSTANCE", Todo.source_id == int(started["data"]["id"])))
        assert todo is not None
        assert todo.assignee_perm_code == "ims:flow:manage"
        ids = set(session.scalars(select(TodoAssignee.user_id).where(TodoAssignee.todo_id == todo.id)))
        assert ids == holders
    body = _act(client, headers, started["data"]["id"], "APPROVE")
    assert body["code"] == 1008


def test_ut_g03_11(client):
    """UT-G03-11"""
    # UT-G03-11
    _grant(202, ["ims:flow:start"])
    freeze(datetime(2026, 10, 12, 9, 0, 0))
    admin = auth(client, "u_admin")
    _publish(client, admin, "G311", [{"key": "n1", "assigneeUserId": U_ADMIN, "dueHours": 2}])
    started = _start(client, auth(client, "u_dept"), "G311", 1)
    advance(timedelta(hours=2, minutes=1))
    admin = auth(client, "u_admin")
    first = _job(client, admin, "flow_overdue")
    second = _job(client, admin, "flow_overdue")
    assert first["code"] == 0, first
    assert second["code"] == 0, second
    with session_scope() as session:
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == int(started["data"]["id"])))
        assert task.overdue == 1
        mails = list(session.scalars(select(Message).where(Message.receiver_id == U_ADMIN, Message.title == "审批已超时")))
        todos = list(session.scalars(select(Todo).where(Todo.title == "督办", Todo.type == "WARNING")))
        assert len(mails) == 1
        assert "督办" in (mails[0].content or "")
        assert len(todos) == 1
