"""tc_r9 只保留标准 R9。启动清理去掉 acct:r3 / fin:r9 绑定，组织人效写操作 403。"""

import logging
import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import _keep_tc_r9_on_standard_r9, app, seed
from app.models import Role, RolePerm, User, UserRole
from app.security import hash_password

client = TestClient(app)


def _role_keys_of(db, user_id: int) -> set[str]:
    return set(
        db.scalars(
            select(Role.role_key)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.deleted == 0)
        ).all()
    )


def _bind(db, user: User, role: Role) -> None:
    if db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)) is None:
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))


def _preset_tc_r9(db, *, with_standard_r9: bool) -> int:
    user = User(
        username="tc_r9",
        nickname="TC-数据分析",
        mobile="13900001040",
        password_hash=hash_password("Admin@123"),
        status="ENABLED",
        tenant_id=0,
    )
    db.add(user)
    db.flush()
    acct = db.scalar(select(Role).where(Role.role_key == "acct:r3", Role.deleted == 0))
    fin = db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0))
    assert acct is not None and fin is not None
    _bind(db, user, acct)
    _bind(db, user, fin)
    if with_standard_r9:
        standard = Role(
            role_name="数据分析师",
            role_key="R9",
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(standard)
        db.flush()
        db.add(
            RolePerm(
                role_id=standard.id,
                module_code="eff",
                perm_code="menu:eff:query",
                perm_level="R",
                tenant_id=0,
            )
        )
        _bind(db, user, standard)
    db.commit()
    return user.id


def test_startup_leaves_tc_r9_only_r9_and_eff_writes_403():
    db = SessionLocal()
    try:
        user_id = _preset_tc_r9(db, with_standard_r9=True)
        acct_id = db.scalar(select(Role.id).where(Role.role_key == "acct:r3", Role.deleted == 0))
        fin_id = db.scalar(select(Role.id).where(Role.role_key == "fin:r9", Role.deleted == 0))
    finally:
        db.close()

    seed()
    seed()

    db = SessionLocal()
    try:
        assert _role_keys_of(db, user_id) == {"R9"}
        assert db.get(Role, acct_id) is not None and db.get(Role, acct_id).deleted == 0
        assert db.get(Role, fin_id) is not None and db.get(Role, fin_id).deleted == 0
        finance = db.scalar(select(User).where(User.username == "e2e_acct_r3", User.deleted == 0))
        analyst = db.scalar(select(User).where(User.username == "e2e_fin_r9", User.deleted == 0))
        assert finance is not None and "acct:r3" in _role_keys_of(db, finance.id)
        assert analyst is not None and "fin:r9" in _role_keys_of(db, analyst.id)
    finally:
        db.close()

    token = client.post("/admin-api/ims/auth/login", json={"username": "tc_r9", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    auth = {"Authorization": f"Bearer {token}"}
    listed = client.get("/admin-api/ims/eff/relation/list", headers=auth)
    assert listed.status_code == 200
    assert listed.json()["code"] == 0

    body = {"userId": user_id, "relationType": "PRIMARY", "targetName": "电竞一组", "shareRatio": 100}
    created = client.post("/admin-api/ims/eff/relation", headers=auth, json=body)
    updated = client.put("/admin-api/ims/eff/relation/1", headers=auth, json={"action": "TERMINATE"})
    deleted = client.delete("/admin-api/ims/eff/relation/1", headers=auth)
    assert created.status_code == 403 and created.json()["code"] == 403
    assert updated.status_code == 403 and updated.json()["code"] == 403
    assert deleted.status_code == 403 and deleted.json()["code"] == 403
    assert db_count_relations() == 0


def db_count_relations() -> int:
    from app.models import EffRelation

    db = SessionLocal()
    try:
        return int(db.scalar(select(func.count()).select_from(EffRelation).where(EffRelation.deleted == 0)) or 0)
    finally:
        db.close()


def test_startup_unbinds_tc_r9_without_deleting_roles_when_r9_missing(caplog):
    db = SessionLocal()
    try:
        user_id = _preset_tc_r9(db, with_standard_r9=False)
    finally:
        db.close()

    with caplog.at_level(logging.WARNING):
        seed()

    db = SessionLocal()
    try:
        assert _role_keys_of(db, user_id) == set()
        assert db.scalar(select(Role).where(Role.role_key == "R9")) is None
        assert db.scalar(select(Role).where(Role.role_key == "acct:r3", Role.deleted == 0)) is not None
        assert db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0)) is not None
        finance = db.scalar(select(User).where(User.username == "e2e_acct_r3", User.deleted == 0))
        assert finance is not None and "acct:r3" in _role_keys_of(db, finance.id)
        assert "未创建 R9" in caplog.text
        _keep_tc_r9_on_standard_r9(db)
        db.commit()
        assert _role_keys_of(db, user_id) == set()
    finally:
        db.close()
