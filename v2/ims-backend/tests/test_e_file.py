"""文件、消息、待办与定时任务。"""
from __future__ import annotations

import io
import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.clock import freeze, now_naive
from app.core.config import get_settings
from app.core.context import RequestContext, system_context, use_context
from app.core.errors import BizError
from app.core.pagination import Page
from app.db.session import session_scope
from app.domains.file.model import StoredFile
from app.domains.file.router import router as file_router
from app.domains.message.model import Message, NotifyRecord
from app.domains.message.router import router as message_router
from app.domains.system.model import JobLog, Param, UserRole
from app.domains.todo.model import Todo, TodoAssignee
from app.domains.todo.router import router as todo_router
from app.integrations.dingtalk.client import ding_state
from app.services.jobs import JOBS, run_job, watch_state
from app.services import jobs as jobs_mod
from tests.stddata import D1, D2, U_ADMIN, U_DEPT, U_SELF

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _ctx(user_id, perms=None, scopes=None, depts=None, tenant=1, system=False):
    return RequestContext(
        user_id=user_id,
        tenant_id=tenant,
        perm_codes=set(perms or []),
        data_scopes=set(scopes or ["ALL"]),
        dept_ids=list(depts or []),
        system=system,
        skip_scope=system,
        username="tester",
        nickname="tester",
    )


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def storage(app):
    settings = get_settings()
    previous = settings.storage_root
    folder = tempfile.mkdtemp(prefix="ims-file-")
    settings.storage_root = folder
    yield Path(folder)
    settings.storage_root = previous
    shutil.rmtree(folder, ignore_errors=True)


def _route(router, path):
    for route in router.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(path)


def test_scene_registry_and_routers():
    from app.domains.file.service import scene_registry

    registry = scene_registry()
    assert registry["TRAIN_DOC"]["exts"][0] == "pdf"
    assert registry["TRAIN_DOC"]["maxMb"] == 100
    assert registry["TRAIN_VIDEO"]["exts"] == ["mp4"]
    assert registry["TEST_IMAGE"]["watermark"] is True
    assert "png" in registry["TEST_IMAGE"]["exts"] and "jpg" in registry["TEST_IMAGE"]["exts"]
    upload = _route(file_router, "/upload")
    assert upload.methods == {"POST"}
    assert upload.summary == "上传文件"
    assert upload.endpoint.__ims_meta__["perm"] == "ims:file:upload"
    download = _route(file_router, "/download")
    assert download.endpoint.__ims_meta__["perm"] == "ims:file:query"
    assert _route(file_router, "/preview").summary == "预览文件"
    send = _route(message_router, "/send")
    assert send.endpoint.__ims_meta__["login_only"] is True
    assert send.endpoint.__ims_meta__["perm"] is None
    assert _route(message_router, "/my/page").summary == "我的消息"
    assert _route(message_router, "/notify/resend").endpoint.__ims_meta__["perm"] == "ims:system:notify:resend"
    assert _route(todo_router, "/my/page").endpoint.__ims_meta__["login_only"] is True
    assert _route(todo_router, "/my/count").summary == "待办数量"


def test_upload_download_preview_and_guard(storage):
    from app.domains.demo.model import DemoOrder
    from app.domains.file.service import bind, download, preview, scene_registry, unbind, upload

    user = _ctx(U_ADMIN)
    with session_scope(commit=True) as session:
        with use_context(user):
            with pytest.raises(BizError) as unknown:
                upload("NO_SUCH", "a.pdf", PDF, U_ADMIN)
            assert unknown.value.code == 1001
            assert "不支持的上传场景" in unknown.value.msg
            with pytest.raises(BizError) as exe:
                upload("TRAIN_DOC", "a.exe", b"MZ" + b"\x00" * 8, U_ADMIN)
            assert exe.value.code == 5005
            assert "仅支持 pdf" in exe.value.msg
            with pytest.raises(BizError) as magic:
                upload("TRAIN_DOC", "a.pdf", b"hello-not-pdf", U_ADMIN)
            assert magic.value.code == 5005
            assert magic.value.msg == "文件内容与格式不符"
            limit = scene_registry()["TRAIN_DOC"]["maxBytes"]
            with pytest.raises(BizError) as over:
                upload("TRAIN_DOC", "big.pdf", b"0" * (limit + 1), U_ADMIN)
            assert over.value.code == 5005
            assert over.value.msg == "文件不能超过 100 MB"
            saved = upload("TRAIN_DOC", "guide.pdf", PDF, U_ADMIN)
            row = session.get(StoredFile, saved["id"])
            assert row.creator == U_ADMIN
            assert row.file_key.startswith("TRAIN_DOC/1/")
            assert row.file_key.endswith(".pdf")
            target = storage / row.file_key
            assert target.is_file()
            assert target.read_bytes() == PDF
            assert not list(storage.rglob(".write_probe_*"))
            assert not list(storage.rglob(".*.tmp"))
            resp = download(row.file_key)
            assert resp.body == PDF
            assert "guide.pdf" in resp.headers["content-disposition"]
            with pytest.raises(BizError) as other:
                with use_context(_ctx(U_DEPT, scopes=["ALL"], depts=[D1, D2])):
                    download(row.file_key)
            assert other.value.code == 1504
            order = session.scalar(select(DemoOrder).where(DemoOrder.code == "OD1"))
            bind(row.file_key, "ims_demo_order", order.id)
            session.refresh(row)
            assert row.ever_bound == 1
            assert row.biz_id == order.id
            with use_context(_ctx(U_SELF, scopes=["SELF"], depts=[D2])):
                with pytest.raises(BizError) as denied:
                    download(row.file_key)
                assert denied.value.code == 1504
            with use_context(_ctx(U_DEPT, scopes=["DEPT"], depts=[D1, D2])):
                allowed = download(row.file_key)
                assert allowed.body == PDF
            with patch("pathlib.Path.read_bytes", side_effect=AssertionError("不应读取文件")):
                with use_context(_ctx(2001, tenant=2, scopes=["ALL"])):
                    with pytest.raises(BizError) as cross:
                        download(row.file_key)
                    assert cross.value.code == 1504
                with pytest.raises(BizError) as escaped:
                    download("../../etc/passwd")
                assert escaped.value.code == 1001
            unbind(row.file_key)
            session.refresh(row)
            assert row.biz_id is None
            assert row.orphan_since is not None
            assert row.ever_bound == 1
            image = upload("TEST_IMAGE", "shot.png", _png(), U_ADMIN)
            image_path = storage / image["fileKey"]
            before = image_path.read_bytes()
            shown = preview(image["fileKey"])
            assert shown.body != before
            assert image_path.read_bytes() == before
            upload("TRAIN_DOC", "a.docx", b"PK\x03\x04" + b"\x00" * 16, U_ADMIN)
            upload("TRAIN_VIDEO", "a.mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8, U_ADMIN)


def test_storage_not_writable_leaves_no_temp(storage):
    from app.domains.file.service import upload

    blocker = storage / "not-dir"
    blocker.write_text("x", encoding="utf-8")
    settings = get_settings()
    settings.storage_root = str(blocker)
    try:
        with session_scope(commit=True):
            with use_context(_ctx(U_ADMIN)):
                with pytest.raises(BizError) as exc:
                    upload("TRAIN_DOC", "a.pdf", PDF, U_ADMIN)
                assert exc.value.code == 5005
        names = [item.name for item in storage.iterdir()]
        assert names == ["not-dir"]
        assert not list(storage.rglob(".write_probe_*"))
        assert not list(storage.rglob("*.tmp"))
    finally:
        settings.storage_root = str(storage)


def test_cleanup_keeps_bound_history(storage):
    from app.domains.file.service import bind, cleanup_expired, unbind, upload

    with session_scope(commit=True) as session:
        with use_context(_ctx(U_ADMIN)):
            fresh = upload("TRAIN_DOC", "fresh.pdf", PDF, U_ADMIN)
            orphan = upload("TRAIN_DOC", "orphan.pdf", PDF, U_ADMIN)
            bound = upload("TRAIN_DOC", "bound.pdf", PDF, U_ADMIN)
            bind(bound["fileKey"], "ims_demo_order", 1)
            unbind(bound["fileKey"])
            past = now_naive() - timedelta(hours=25)
            for key in (orphan["fileKey"], bound["fileKey"]):
                row = session.scalar(select(StoredFile).where(StoredFile.file_key == key))
                row.create_time = past
            session.flush()
            removed = cleanup_expired()
            assert removed == 1
            orphan_row = session.scalar(
                select(StoredFile).where(StoredFile.file_key == orphan["fileKey"]).execution_options(include_deleted=True)
            )
            assert orphan_row.deleted != 0
            assert not (storage / orphan["fileKey"]).exists()
            fresh_row = session.scalar(select(StoredFile).where(StoredFile.file_key == fresh["fileKey"]))
            bound_row = session.scalar(select(StoredFile).where(StoredFile.file_key == bound["fileKey"]))
            assert fresh_row.deleted == 0
            assert bound_row.deleted == 0
            assert bound_row.ever_bound == 1
            assert (storage / fresh["fileKey"]).is_file()
            assert (storage / bound["fileKey"]).is_file()


def test_notify_dedup_disable_and_retry():
    from app.domains.message.service import mark_read, my_page, read_all, resend, retry_pending, send_notify, unread_count

    with session_scope(commit=True) as session:
        with use_context(_ctx(U_DEPT)):
            param = session.scalar(select(Param).where(Param.param_key == "dingtalk.notify.enabled"))
            param.value = "false"
            session.flush()
            before = len(ding_state.notify_calls)
            disabled = send_notify(U_DEPT, "关闭", "内容", "DISABLED_EVT", "biz-off")
            assert disabled["dingStatus"] == "DISABLED"
            assert len(ding_state.notify_calls) == before
            ding = session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "biz-off", NotifyRecord.channel == "DINGTALK"))
            assert ding.status == "DISABLED"
            assert unread_count()["count"] == 1
            param.value = "true"
            session.flush()
            send_notify(U_DEPT, "第一次", "正文", "EVT", "biz-1")
            send_notify(U_DEPT, "第二次", "正文", "EVT", "biz-1")
            assert unread_count()["count"] == 2
            skipped = session.scalar(select(NotifyRecord).where(NotifyRecord.status == "SKIPPED_DUP", NotifyRecord.biz_key == "biz-1"))
            assert skipped is not None
            messages = list(session.scalars(select(Message).where(Message.receiver_id == U_DEPT)))
            assert len(messages) == 2
            freeze(now_naive() + timedelta(hours=25))
            send_notify(U_DEPT, "过窗", "正文", "EVT", "biz-1")
            assert unread_count()["count"] == 3
            ding_state.error = "notify_fail"
            failed = send_notify(U_SELF, "失败", "请重试", "FAIL_EVT", "biz-fail")
            assert failed["dingStatus"] == "RETRYING"
            site = session.scalar(select(Message).where(Message.receiver_id == U_SELF, Message.title == "失败"))
            assert site is not None and site.read_status == "UNREAD"
            record = session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "biz-fail", NotifyRecord.channel == "DINGTALK"))
            assert record.retry_count == 1
            retry_pending()
            retry_pending()
            session.refresh(record)
            assert record.status == "FAILED"
            assert record.retry_count == 3
            ding_state.error = None
            resent = resend(record.id)
            assert resent["status"] == "SENT"
            with pytest.raises(BizError) as again:
                resend(record.id)
            assert again.value.code == 1001
            with use_context(_ctx(U_ADMIN)):
                with pytest.raises(BizError) as hidden:
                    mark_read(site.id)
                assert hidden.value.code == 1504
            with use_context(_ctx(U_SELF)):
                page = my_page(Page(1, 10), "UNREAD")
                assert page["total"] >= 1
                mark_read(site.id)
                assert unread_count()["count"] == 0
                read_page = my_page(Page(1, 10), "READ")
                assert any(item["id"] == site.id for item in read_page["list"])
                send_notify(U_SELF, "另一条", "x", "OTHER", "biz-other")
                assert read_all()["count"] == 1
                assert unread_count()["count"] == 0


def test_todo_assign_complete_and_isolation():
    from app.domains.todo.service import cancel, complete, my_count, my_page, todo_create

    with session_scope(commit=True) as session:
        with use_context(_ctx(U_DEPT, depts=[D1, D2])):
            first = todo_create("MANUAL", 9, "APPROVAL", "审批甲", user_ids=[U_DEPT])
            second = todo_create("MANUAL", 9, "APPROVAL", "不应新建", user_ids=[U_SELF])
            assert first["id"] == second["id"]
            links = list(session.scalars(select(TodoAssignee.user_id).where(TodoAssignee.todo_id == first["id"])))
            assert links == [U_DEPT]
            scoped = todo_create("PERM", 3, "REVIEW", "按部门", perm_code="ims:flow:manage", scope_dept_ids=[D1])
            assert U_ADMIN in scoped["assigneeIds"]
            assert 1 not in scoped["assigneeIds"]
            everyone = todo_create("PERM", 4, "REVIEW", "全部", perm_code="ims:flow:manage")
            assert 1 in everyone["assigneeIds"] and U_ADMIN in everyone["assigneeIds"]
            todo_create("MANUAL", 10, "WARNING", "预警", user_ids=[U_DEPT])
            counted = my_count()
            assert counted["byType"]["APPROVAL"] == 1
            assert counted["byType"]["WARNING"] == 1
            assert counted["total"] == 2
            with pytest.raises(BizError) as blocked:
                complete(first["id"], U_SELF)
            assert blocked.value.code == 1504
            with use_context(_ctx(U_SELF)):
                assert my_page(Page(1, 10))["total"] == 0
                assert my_count()["total"] == 0
            done = complete(first["id"], U_DEPT)
            assert done["status"] == "DONE"
            row = session.get(Todo, first["id"])
            assert row.done_by == U_DEPT
            assert my_count()["total"] == 1
            cancelled = cancel(session.scalar(select(Todo.id).where(Todo.source_id == 10, Todo.type == "WARNING")), U_DEPT)
            assert cancelled["status"] == "CANCELLED"
            assert my_count()["total"] == 0


def test_job_registry_lock_watchdog_and_failure():
    names = [item.name for item in JOBS]
    for name in [
        "integrity",
        "org_reconcile",
        "file_cleanup",
        "log_cleanup",
        "flow_overdue",
        "attendance_pull",
        "outbox_retry",
        "notify_retry",
        "org_event_retry",
        "export_retry",
        "position_role_revoke",
    ]:
        assert name in names
    crons = {item.name: item.cron for item in JOBS}
    assert crons["integrity"] == "0 3 * * *"
    assert crons["org_reconcile"] == "0 2 * * *"
    assert crons["flow_overdue"] == "*/10 * * * *"
    assert crons["attendance_pull"] == "30 1 * * *"
    assert crons["position_role_revoke"] == "*/10 * * * *"
    spec = next(item for item in JOBS if item.name == "integrity")
    original = spec.fn

    def nested():
        again = run_job("integrity")
        assert again["skipped"] is True
        assert "已在其他实例执行" in again["message"]

    spec.fn = nested
    previous_interval = jobs_mod.WATCH_INTERVAL
    try:
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                first = run_job("integrity")
                assert first["success"] is True
                spec.fn = original
                manual = run_job("org_reconcile", trigger="MANUAL")
                assert manual["success"] is True
                log = session.scalar(select(JobLog).where(JobLog.job_name == "org_reconcile"))
                assert log.trigger_mode == "MANUAL" and log.success == 1
                run_job("attendance_pull")
                run_job("attendance_pull")
                assert len(list(session.scalars(select(JobLog).where(JobLog.job_name == "attendance_pull")))) == 2

                def boom():
                    raise RuntimeError("任务炸了")

                spec.fn = boom
                failed = run_job("integrity")
                assert failed["success"] is False
                bad = session.scalar(select(JobLog).where(JobLog.job_name == "integrity", JobLog.success == 0))
                assert bad is not None and bad.trigger_mode == "SCHEDULE"
                texts = list(session.scalars(select(Message.title)))
                assert any("失败" in title for title in texts)
                spec.fn = lambda: time.sleep(0.45)
                jobs_mod.WATCH_INTERVAL = 0.05
                watch_state["extends"] = 0
                watched = run_job("integrity")
                assert watched["success"] is True
                assert watch_state["extends"] >= 1
                session.add(
                    UserRole(
                        user_id=U_DEPT,
                        role_id=204,
                        source="DINGTALK_AUTO",
                        revoke_at=now_naive() - timedelta(minutes=1),
                        manual_removed=0,
                        tenant_id=1,
                    )
                )
                session.flush()
                run_job("position_role_revoke")
                left = list(session.scalars(select(UserRole).where(UserRole.user_id == U_DEPT, UserRole.role_id == 204)))
                assert left == []
    finally:
        spec.fn = original
        jobs_mod.WATCH_INTERVAL = previous_interval
