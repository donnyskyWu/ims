import os

os.environ["IMS_DB"] = "ims_test"

from sqlalchemy import select
from starlette.requests import Request

from app.api import AuthError
from app.core import SessionLocal
from app.models import User
from app.perm import FUNCTION_SKIP, enforce_function
from app.role_matrix import grants_for


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
        }
    )


def test_study_skips_train_menu_for_assignee_check():
    assert "/admin-api/ims/train/study" in FUNCTION_SKIP
    assert "menu:trainTask:query" not in grants_for("R8")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "tc_r8", User.deleted == 0))
        assert user is not None
        enforce_function(db, _request("/admin-api/ims/train/study"), user)
        enforce_function(db, _request("/admin-api/ims/train/study/42"), user)
        try:
            enforce_function(db, _request("/admin-api/ims/train/task"), user)
        except AuthError as exc:
            assert exc.code == 403
            assert exc.msg == "无操作权限"
        else:
            raise AssertionError("学习任务列表仍应要求 menu:trainTask:query")
    finally:
        db.close()
