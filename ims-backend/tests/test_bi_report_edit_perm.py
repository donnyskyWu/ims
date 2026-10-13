"""BUG-C036：bi:report:edit 只授给会设计报表的标准角色，种子可重复执行。"""

import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app
from app.models import Menu, Role, RolePerm
from app.role_matrix import REPORT_EDIT_PERM, ensure_role_matrix

client = TestClient(app)

DESIGNERS = ("tc_r3", "tc_r4", "tc_r5", "tc_r6", "tc_r9")
VIEWERS = ("tc_r2", "tc_r7", "tc_r8", "tc_r10", "tc_r11")


def login(username: str) -> dict:
    logged = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"})
    assert logged.status_code == 200, logged.text
    return {"Authorization": f"Bearer {logged.json()['data']['accessToken']}"}


def codes(username: str) -> set[str]:
    access = client.get("/admin-api/ims/auth/access", headers=login(username)).json()["data"]
    return set(access["permCodes"])


def test_report_edit_granted_only_to_design_roles():
    db = SessionLocal()
    try:
        menu = db.scalar(select(Menu).where(Menu.perm_code == REPORT_EDIT_PERM, Menu.deleted == 0))
        assert menu is not None
        assert menu.menu_type == "BUTTON"
        assert menu.route == ""
        assert menu.name == "报表设计·编辑"
        r1 = db.scalar(select(Role).where(Role.role_key == "R1", Role.deleted == 0))
        assert r1 is not None
        assert db.scalar(
            select(RolePerm).where(RolePerm.role_id == r1.id, RolePerm.perm_code == REPORT_EDIT_PERM)
        ) is not None
    finally:
        db.close()

    for username in DESIGNERS:
        assert REPORT_EDIT_PERM in codes(username), username
    for username in VIEWERS:
        assert REPORT_EDIT_PERM not in codes(username), username
    admin = codes("admin")
    assert REPORT_EDIT_PERM in admin
    assert "/ims/bi/report/designer" not in client.get("/admin-api/ims/auth/access", headers=login("tc_r2")).json()["data"]["routes"]


def test_report_edit_seed_is_idempotent():
    db = SessionLocal()
    try:
        ensure_role_matrix(db)
        ensure_role_matrix(db)
        db.commit()
        role = db.scalar(select(Role).where(Role.role_key == "R6", Role.deleted == 0))
        assert role is not None
        count = db.scalar(
            select(func.count()).select_from(RolePerm).where(
                RolePerm.role_id == role.id,
                RolePerm.perm_code == REPORT_EDIT_PERM,
            )
        )
        assert count == 1
        r2 = db.scalar(select(Role).where(Role.role_key == "R2", Role.deleted == 0))
        assert r2 is not None
        assert db.scalar(
            select(RolePerm.id).where(RolePerm.role_id == r2.id, RolePerm.perm_code == REPORT_EDIT_PERM)
        ) is None
    finally:
        db.close()
