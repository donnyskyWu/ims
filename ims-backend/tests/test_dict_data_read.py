"""BUG-083：能打开实名人等页面的角色可以读字典数据，但看不到字典管理菜单。"""

import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import Menu, Role, RolePerm
from app.role_matrix import grant_dict_data_readers

client = TestClient(app)


def login(username: str) -> dict:
    logged = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"})
    assert logged.status_code == 200, logged.text
    return {"Authorization": f"Bearer {logged.json()['data']['accessToken']}"}


def test_tc_r9_reads_id_type_dict_without_dict_admin():
    headers = login("tc_r9")
    access = client.get("/admin-api/ims/auth/access", headers=headers).json()["data"]
    assert "system:dict:data:query" in access["permCodes"]
    assert "system:dict:query" not in access["permCodes"]
    assert "/ims/system/dict" not in access["routes"]

    listed = client.get("/admin-api/ims/system/dict-data/list", headers=headers, params={"dictType": "dict_id_type"})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["code"] == 0
    assert "ID_CARD" in {row["dictValue"] for row in body["data"]}

    types = client.get("/admin-api/ims/system/dict-type/list", headers=headers)
    assert types.status_code == 403 and types.json()["code"] == 403
    removed = client.delete("/admin-api/ims/system/dict-data/1", headers=headers)
    assert removed.status_code == 403 and removed.json()["code"] == 403

    cert = login("tc_r7")
    cert_list = client.get("/admin-api/ims/system/dict-data/list", headers=cert, params={"dictType": "dict_id_type"})
    assert cert_list.status_code == 200 and cert_list.json()["code"] == 0
    cert_access = client.get("/admin-api/ims/auth/access", headers=cert).json()["data"]
    assert "/ims/system/dict" not in cert_access["routes"]

    hidden = login("tc_r10")
    denied = client.get("/admin-api/ims/system/dict-data/list", headers=hidden, params={"dictType": "dict_id_type"})
    assert denied.status_code == 403 and denied.json()["code"] == 403


def test_custom_role_with_realname_page_gets_dict_data_read():
    db = SessionLocal()
    try:
        role = Role(role_name="实名人只读", role_key="custom:realname", data_scope="ALL", source="MANUAL", status="ENABLED", tenant_id=0)
        db.add(role)
        db.flush()
        page = db.scalar(select(Menu).where(Menu.perm_code == "menu:crRealname:query", Menu.deleted == 0))
        assert page is not None
        db.add(RolePerm(role_id=role.id, module_code="menu", perm_code=page.perm_code, perm_level="R", tenant_id=0))
        db.flush()
        grant_dict_data_readers(db)
        held = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role.id)).all())
        assert "system:dict:data:query" in held
        assert "system:dict:query" not in held
        grant_dict_data_readers(db)
        held_again = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role.id)).all())
        assert held_again == held
    finally:
        db.close()
