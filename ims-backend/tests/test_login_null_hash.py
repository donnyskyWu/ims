import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core import SessionLocal, engine
from app.main import app
from app.models import User
from app.role_matrix import commit_seed_passwords
from app.security import hash_password, password_hash_usable, verify_password

client = TestClient(app)


def _allow_null_hash() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ims_sys_user MODIFY password_hash varchar(128) NULL"))


def _set_hash(username: str, stored) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE ims_sys_user SET password_hash=:stored WHERE username=:username"),
            {"stored": stored, "username": username},
        )


def test_verify_password_rejects_null_and_bytes_without_raising():
    assert verify_password("Admin@123", None) is False
    assert verify_password("Admin@123", b"\xff") is False
    stored = hash_password("Admin@123")
    assert verify_password("Admin@123", stored.encode()) is True


def test_tc_r6_null_hash_login_twice_then_keeps_seed_password():
    _allow_null_hash()
    _set_hash("tc_r6", None)
    first = client.post("/admin-api/ims/auth/login", json={"username": "tc_r6", "password": "Admin@123"})
    assert first.status_code == 200, first.text
    assert first.json()["code"] == 0, first.json()
    second = client.post("/admin-api/ims/auth/login", json={"username": "tc_r6", "password": "Admin@123"})
    assert second.status_code == 200, second.text
    assert second.json()["code"] == 0, second.json()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "tc_r6", User.deleted == 0))
        assert password_hash_usable(user.password_hash)
        assert verify_password("Admin@123", user.password_hash)
        kept = user.password_hash
    finally:
        db.close()
    commit_seed_passwords()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "tc_r6", User.deleted == 0))
        assert user.password_hash == kept
    finally:
        db.close()


def test_outsider_null_hash_is_business_error_not_500():
    _allow_null_hash()
    db = SessionLocal()
    try:
        db.add(
            User(
                username="outsider",
                nickname="外人",
                mobile="13900001999",
                password_hash="x",
                status="ENABLED",
                tenant_id=0,
            )
        )
        db.commit()
    finally:
        db.close()
    _set_hash("outsider", None)
    res = client.post("/admin-api/ims/auth/login", json={"username": "outsider", "password": "Admin@123"})
    assert res.status_code == 200, res.text
    assert res.json()["code"] == 1006
    assert res.json()["msg"] == "用户名或密码错误"
