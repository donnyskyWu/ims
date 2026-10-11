"""tc_r9 只保留标准 R9。启动清理去掉 acct:r3 / fin:r9 绑定，组织人效写操作 1008。"""

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

STANDARD_R9_NAME = "数据分析师"


def _role_keys_of(db, user_id: int) -> set[str]:
    return set(
        db.scalars(
            select(Role.role_key)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.deleted == 0)
        ).all()
    )


def _role_by_key(db, role_key: str) -> Role | None:
    return db.scalar(select(Role).where(func.lower(Role.role_key) == role_key.lower()))


def _get_or_create_role(db, *, role_key: str, role_name: str, data_scope: str = "ALL") -> Role:
    """复用启动种子里已有的角色，避免 role_key 唯一约束冲突。"""
    role = _role_by_key(db, role_key)
    if role is None:
        role = Role(
            role_name=role_name,
            role_key=role_key,
            data_scope=data_scope,
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        return role
    role.deleted = 0
    role.status = "ENABLED"
    if role_key.upper() == "R9":
        role.role_name = STANDARD_R9_NAME
    elif not (role.role_name or "").strip():
        role.role_name = role_name
    return role


def _ensure_user(db, *, username: str, nickname: str, mobile: str) -> User:
    user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
    if user is None:
        user = User(
            username=username,
            nickname=nickname,
            mobile=mobile,
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
        return user
    user.status = "ENABLED"
    user.nickname = nickname
    user.password_hash = hash_password("Admin@123")
    return user


def _bind(db, user: User, role: Role) -> None:
    if db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)) is None:
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))


def _ensure_query_perm(db, role: Role) -> None:
    row = db.scalar(
        select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code == "menu:eff:query")
    )
    if row is None:
        db.add(
            RolePerm(
                role_id=role.id,
                module_code="eff",
                perm_code="menu:eff:query",
                perm_level="R",
                tenant_id=0,
            )
        )


def _preset_tc_r9(db, *, with_standard_r9: bool) -> int:
    user = _ensure_user(db, username="tc_r9", nickname="TC-数据分析", mobile="13900001040")
    acct = _role_by_key(db, "acct:r3")
    fin = _role_by_key(db, "fin:r9")
    assert acct is not None and acct.deleted == 0
    assert fin is not None and fin.deleted == 0
    _bind(db, user, acct)
    _bind(db, user, fin)
    if with_standard_r9:
        standard = _get_or_create_role(db, role_key="R9", role_name=STANDARD_R9_NAME, data_scope="ALL")
        _ensure_query_perm(db, standard)
        _bind(db, user, standard)
    db.commit()
    return user.id


def _assert_eff_write_denied(response) -> None:
    assert response.status_code == 403
    assert response.json()["code"] == 1008


def test_startup_leaves_tc_r9_only_r9_and_eff_writes_denied():
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
        assert {key.upper() for key in _role_keys_of(db, user_id)} == {"R9"}
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
    before = db_count_relations()
    created = client.post("/admin-api/ims/eff/relation", headers=auth, json=body)
    updated = client.put("/admin-api/ims/eff/relation/1", headers=auth, json={"action": "TERMINATE"})
    deleted = client.delete("/admin-api/ims/eff/relation/1", headers=auth)
    _assert_eff_write_denied(created)
    _assert_eff_write_denied(updated)
    _assert_eff_write_denied(deleted)
    assert db_count_relations() == before


def db_count_relations() -> int:
    from app.models import EffRelation

    db = SessionLocal()
    try:
        return int(db.scalar(select(func.count()).select_from(EffRelation).where(EffRelation.deleted == 0)) or 0)
    finally:
        db.close()


def test_startup_unbinds_tc_r9_without_deleting_roles_when_r9_missing(caplog):
    db = SessionLocal()
    hidden: tuple[int, int, str, str] | None = None
    try:
        existing = _role_by_key(db, "R9")
        if existing is not None and existing.deleted == 0:
            hidden = (existing.id, existing.deleted, existing.status, existing.role_name)
            existing.deleted = 1
            db.commit()
        user_id = _preset_tc_r9(db, with_standard_r9=False)
    finally:
        db.close()

    db = SessionLocal()
    try:
        with caplog.at_level(logging.WARNING):
            _keep_tc_r9_on_standard_r9(db)
            db.commit()
        assert _role_keys_of(db, user_id) == set()
        visible = db.scalar(
            select(Role).where(
                func.lower(Role.role_key) == "r9",
                Role.deleted == 0,
                Role.role_name == STANDARD_R9_NAME,
            )
        )
        assert visible is None
        acct = _role_by_key(db, "acct:r3")
        fin = _role_by_key(db, "fin:r9")
        assert acct is not None and acct.deleted == 0
        assert fin is not None and fin.deleted == 0
        finance = db.scalar(select(User).where(User.username == "e2e_acct_r3", User.deleted == 0))
        assert finance is not None and "acct:r3" in _role_keys_of(db, finance.id)
        assert "未创建 R9" in caplog.text
        _keep_tc_r9_on_standard_r9(db)
        db.commit()
        assert _role_keys_of(db, user_id) == set()
    finally:
        db.close()
        if hidden is not None:
            restore = SessionLocal()
            try:
                role = restore.get(Role, hidden[0])
                if role is not None:
                    role.deleted = hidden[1]
                    role.status = hidden[2]
                    role.role_name = hidden[3]
                    restore.commit()
            finally:
                restore.close()
