"""BUG-081：E2E 遗留角色改显示名，并去掉组织人效建立/变更/删除。角色和登录用户保留。"""

import os

os.environ["IMS_DB"] = "ims_test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app, seed
from app.models import Role, RoleMenu, RolePerm, User
from app.role_matrix import (
    E2E_LEGACY_ROLE_NAMES,
    EFF_RELATION_CREATE,
    EFF_RELATION_DELETE,
    EFF_RELATION_QUERY,
    EFF_RELATION_UPDATE,
    normalize_e2e_legacy_roles,
)

client = TestClient(app)

WRITE_CODES = (
    EFF_RELATION_CREATE,
    EFF_RELATION_UPDATE,
    EFF_RELATION_DELETE,
    "menu:eff:add",
    "menu:eff:edit",
    "menu:eff:remove",
)
BEFORE_NAMES = {
    "fin:r9": "数据分析师",
    "acct:r3": "财务管理员",
    "acct:peer": "账号流转同事",
    "acct:sum": "账号汇总同事",
    "bi:dept-viewer": "BI 本部门查看",
    "live:r4": "运营总监",
}


def _codes(db, role_id: int) -> set[str]:
    held = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role_id)).all())
    held.update(db.scalars(select(RoleMenu.perm_code).where(RoleMenu.role_id == role_id)).all())
    return {code for code in held if code}


def test_e2e_legacy_roles_renamed_and_eff_writes_removed():
    db = SessionLocal()
    try:
        for role_key, display in E2E_LEGACY_ROLE_NAMES.items():
            role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
            assert role is not None, role_key
            assert role.role_name == display
            assert not (_codes(db, role.id) & set(WRITE_CODES))
            query = db.scalar(
                select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code == "menu:eff:query")
            )
            if query is not None:
                assert query.perm_level == "R"
        fin = db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0))
        assert EFF_RELATION_QUERY in _codes(db, fin.id)
        count = db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id == fin.id)) or 0
        assert count > 50
        for username in ("e2e_fin_r9", "e2e_acct_r3", "e2e_acct_peer", "e2e_acct_sum", "bi_r4_viewer", "live_director"):
            assert db.scalar(select(User).where(User.username == username, User.deleted == 0)) is not None

        r1 = db.scalar(select(Role).where(Role.role_key == "R1", Role.deleted == 0))
        assert r1 is not None and r1.role_name == "系统管理员"
        assert EFF_RELATION_DELETE in _codes(db, r1.id)
        r9 = db.scalar(select(Role).where(Role.role_key == "R9", Role.deleted == 0))
        assert r9 is not None and r9.role_name == "数据分析师"
        assert not (_codes(db, r9.id) & {EFF_RELATION_CREATE, EFF_RELATION_UPDATE, EFF_RELATION_DELETE})

        other = Role(
            role_name="数据分析师",
            role_key="dc:r9-keep",
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(other)
        db.flush()
        fin.role_name = BEFORE_NAMES["fin:r9"]
        db.add(
            RolePerm(
                role_id=fin.id,
                module_code="ims",
                perm_code=EFF_RELATION_CREATE,
                perm_level="R",
                tenant_id=0,
            )
        )
        db.flush()
        normalize_e2e_legacy_roles(db)
        db.refresh(fin)
        db.refresh(other)
        assert fin.role_name == E2E_LEGACY_ROLE_NAMES["fin:r9"]
        assert EFF_RELATION_CREATE not in _codes(db, fin.id)
        assert other.role_name == "数据分析师"
        normalize_e2e_legacy_roles(db)
        db.refresh(fin)
        assert fin.role_name == E2E_LEGACY_ROLE_NAMES["fin:r9"]
        assert not (_codes(db, fin.id) & set(WRITE_CODES))
    finally:
        db.close()


def test_startup_seed_keeps_rename_when_later_seed_fails():
    """已提交的旧显示名必须在启动后改掉。后续种子失败不能把改名一起回滚，也不能叠两层前缀。"""
    db = SessionLocal()
    try:
        for role_key, old in BEFORE_NAMES.items():
            role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
            assert role is not None, role_key
            role.role_name = old
        fin = db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0))
        db.add(
            RolePerm(
                role_id=fin.id,
                module_code="ims",
                perm_code=EFF_RELATION_CREATE,
                perm_level="R",
                tenant_id=0,
            )
        )
        db.commit()
        kept_ids = {
            role_key: db.scalar(select(Role.id).where(Role.role_key == role_key, Role.deleted == 0))
            for role_key in E2E_LEGACY_ROLE_NAMES
        }
    finally:
        db.close()

    import app.douyin_collect_seed as dy

    original = dy.refresh_douyin_collect_seed

    def boom() -> None:
        raise RuntimeError("collect seed failed")

    dy.refresh_douyin_collect_seed = boom
    try:
        with pytest.raises(RuntimeError, match="collect seed failed"):
            seed()
    finally:
        dy.refresh_douyin_collect_seed = original

    db = SessionLocal()
    try:
        for role_key, display in E2E_LEGACY_ROLE_NAMES.items():
            role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
            assert role is not None and role.id == kept_ids[role_key]
            assert role.role_name == display
            assert role.role_name.count("E2E专用-") == 1
            assert not (_codes(db, role.id) & set(WRITE_CODES))
        for username in ("e2e_fin_r9", "e2e_acct_r3", "e2e_acct_peer", "e2e_acct_sum", "bi_r4_viewer", "live_director"):
            assert db.scalar(select(User).where(User.username == username, User.deleted == 0)) is not None
        r9 = db.scalar(select(Role).where(Role.role_key == "R9", Role.deleted == 0))
        assert r9 is not None and r9.role_name == "数据分析师"
        fin = db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0))
        fin.role_name = "E2E专用-" + E2E_LEGACY_ROLE_NAMES["fin:r9"]
        db.commit()
    finally:
        db.close()

    seed()

    db = SessionLocal()
    try:
        fin = db.scalar(select(Role).where(Role.role_key == "fin:r9", Role.deleted == 0))
        assert fin.role_name == E2E_LEGACY_ROLE_NAMES["fin:r9"]
        assert fin.role_name.count("E2E专用-") == 1
    finally:
        db.close()

    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    listed = client.get("/admin-api/ims/system/role/list", headers={"Authorization": f"Bearer {token}"}).json()
    assert listed["code"] == 0
    found = {row["roleKey"]: row["roleName"] for row in listed["data"]}
    for role_key, display in E2E_LEGACY_ROLE_NAMES.items():
        assert found[role_key] == display
