import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, SessionLocal, engine
from app.crypto import encrypt_text, sha256_hex
from app.main import app, init_db
from app.models import CertArchive, Role, RolePerm, User, UserRole
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import Company, Realname
from app.scope import refresh_user_scope


client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_company_and_realname_are_query_only_and_masked():
    auth = headers()
    empty = client.get("/admin-api/ims/corp/resource/company/page", headers=auth)
    assert empty.json()["code"] == 0
    seeded_names = [row["companyName"] for row in empty.json()["data"]["list"]]
    assert "E2E内容公司" in seeded_names
    assert "甲公司" not in seeded_names
    missing = client.get("/admin-api/ims/corp/resource/company/999", headers=auth)
    assert missing.json()["code"] == 1504
    assert missing.json()["msg"] == "资源不可用"
    blocked = client.post("/admin-api/ims/corp/resource/company", headers=auth, json={"companyName": "甲"})
    assert blocked.status_code == 404

    ops = ops_session()
    try:
        ops.add(Company(company_name="甲公司", credit_code="91330100MA0000001X", legal_name="李四", status="ENABLED", tenant_id=0))
        foreign_company = Company(company_name="乙公司", credit_code="91330100MA0000002X", status="ENABLED", tenant_id=9)
        ops.add(foreign_company)
        ops.flush()
        foreign_company_id = foreign_company.id
        for index in range(11):
            number = f"1380000{index:04d}"
            card = f"33010119900101{index:04d}"
            ops.add(
                Realname(
                    real_name=f"张{index}三",
                    id_type="ID_CARD",
                    id_card_enc=encrypt_text(card),
                    phone_enc=encrypt_text(number),
                    phone_sha256=sha256_hex(number),
                    status="ENABLED",
                    tenant_id=0,
                )
            )
        ops.commit()
    finally:
        ops.close()

    listed = client.get("/admin-api/ims/corp/resource/company/page", headers=auth, params={"companyName": "甲"})
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["list"][0]["companyName"] == "甲公司"
    foreign = client.get("/admin-api/ims/corp/resource/company/page", headers=auth, params={"companyName": "乙"})
    assert foreign.json()["data"]["total"] == 0
    other = client.get(f"/admin-api/ims/corp/resource/company/{foreign_company_id}", headers=auth)
    assert other.json()["code"] == 1504

    page = client.get(
        "/admin-api/ims/corp/resource/realname/page",
        headers=auth,
        params={"pageNo": 2, "pageSize": 10, "realName": "张"},
    )
    body = page.json()["data"]
    assert body["total"] == 11
    assert len(body["list"]) == 1
    row = body["list"][0]
    assert "idCard" not in row
    assert "phone" not in row
    assert row["idCardMasked"].startswith("330101")
    assert "****" in row["phoneMasked"]
    assert "1380000" not in page.text
    detail = client.get(f"/admin-api/ims/corp/resource/realname/{row['id']}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["intermediaries"] == []
    assert "idCard" not in detail.json()["data"]


def test_sim_write_rules_and_certificate_view():
    auth = headers()
    admin_id = client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"]
    bad_enum = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={"phoneNumber": "13900001111", "isPrimary": "YES", "operator": "NO_SUCH", "assignedUserId": int(admin_id), "status": "IN_USE"},
    )
    assert bad_enum.json()["code"] == 1503
    missing_user = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={"phoneNumber": "13900001111", "isPrimary": "YES", "operator": "MOBILE", "assignedUserId": 99999, "status": "IN_USE"},
    )
    assert missing_user.json()["code"] == 1500

    ops = ops_session()
    try:
        person = Realname(real_name="停用的人", id_type="ID_CARD", status="DISABLED", tenant_id=0)
        ops.add(person)
        ops.commit()
        person_id = person.id
    finally:
        ops.close()
    stopped = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={
            "phoneNumber": "13900001111",
            "isPrimary": "YES",
            "operator": "MOBILE",
            "assignedUserId": int(admin_id),
            "status": "IN_USE",
            "realnameId": person_id,
        },
    )
    assert stopped.json()["code"] == 1501

    created = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={
            "phoneNumber": "13900001111",
            "isPrimary": "YES",
            "operator": "MOBILE",
            "assignedUserId": int(admin_id),
            "iccid": "898601234567890",
            "packageName": "5G畅享",
            "status": "IN_USE",
            "monthlyRent": 29,
        },
    )
    assert created.json()["code"] == 0, created.json()
    card = created.json()["data"]
    assert card["phoneNumber"] == "139****1111"
    assert card["iccid"] == "****"
    assert "898601234567890" not in created.text
    assert card["linkedAccounts"] == []
    listed = client.get("/admin-api/ims/corp/resource/sim-card/page", headers=auth, params={"phoneNumber": "13900001111"})
    assert listed.json()["data"]["total"] == 1
    assert "13900001111" not in listed.text

    db = SessionLocal()
    try:
        plain = "110101199001011234"
        db.add(
            CertArchive(
                holder_user_id=int(admin_id),
                holder_name="管理员",
                cert_type="IDCARD",
                cert_no_enc=encrypt_text(plain),
                cert_no_hash=sha256_hex(plain),
                issue_date="2020-01-01",
                expire_date="2030-01-01",
                status="EFFECTIVE",
                uploaded_by=int(admin_id),
                tenant_id=0,
            )
        )
        db.add(
            CertArchive(
                holder_name="外租户",
                cert_type="IDCARD",
                cert_no_enc=encrypt_text("110101199002021111"),
                cert_no_hash=sha256_hex("110101199002021111"),
                status="EFFECTIVE",
                tenant_id=9,
            )
        )
        db.commit()
        cert_id = (
            db.query(CertArchive)
            .filter(CertArchive.tenant_id == 0, CertArchive.cert_no_hash == sha256_hex(plain))
            .one()
            .id
        )
        foreign_id = db.query(CertArchive).filter(CertArchive.tenant_id == 9).one().id
    finally:
        db.close()

    certs = client.get(
        "/admin-api/ims/corp/resource/certificate/page",
        headers=auth,
        params={"holderName": "管理员"},
    )
    assert certs.json()["data"]["total"] == 1
    item = certs.json()["data"]["list"][0]
    assert item["certNoMasked"].startswith("110")
    assert plain not in certs.text
    view = client.get(f"/admin-api/ims/corp/resource/certificate/{cert_id}/view", headers=auth)
    assert view.json()["code"] == 0
    assert "管理员" in view.json()["data"]["watermarkText"]
    assert view.json()["data"]["indexInfo"]["certNoMasked"] != plain
    assert "signedUrl" not in view.text
    hidden = client.get(f"/admin-api/ims/corp/resource/certificate/{foreign_id}/view", headers=auth)
    assert hidden.json()["code"] == 1504


def test_cert_e2e_seed_watermark_view():
    """#55 · cert_e2e_seed 幂等 + 查看水印（与 Playwright closure 同源）。"""
    auth = headers()
    page = client.get("/admin-api/ims/corp/resource/certificate/page", headers=auth, params={"holderName": "E2E-Cert-Watermark"})
    assert page.json()["code"] == 0
    assert page.json()["data"]["total"] >= 1
    item = page.json()["data"]["list"][0]
    cert_id = item["id"]
    assert item["holderName"] == "E2E-Cert-Watermark"
    assert "110101199888011234" not in page.text
    view = client.get(f"/admin-api/ims/corp/resource/certificate/{cert_id}/view", headers=auth)
    assert view.json()["code"] == 0
    assert "admin" in view.json()["data"]["watermarkText"].lower()
    assert view.json()["data"]["indexInfo"]["certNoMasked"] != "110101199888011234"
    assert "signedUrl" not in view.text


def test_company_scope_without_all_is_1008():
    auth = headers()
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": "corpself", "nickname": "仅本人", "mobile": "13700001111", "password": "Pass@123"},
    )
    user_id = int(created.json()["data"]["id"])
    db = SessionLocal()
    try:
        role = Role(role_name="corp-self", role_key="corp-self", data_scope="SELF", status="ENABLED", source="MANUAL")
        db.add(role)
        db.flush()
        db.add(RolePerm(role_id=role.id, module_code="corp", perm_code="corp:resource:query", perm_level="R"))
        db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        db.commit()
        refresh_user_scope(db, user_id)
        db.commit()
    finally:
        db.close()
    token = client.post("/admin-api/ims/auth/login", json={"username": "corpself", "password": "Pass@123"}).json()["data"]["accessToken"]
    denied = client.get("/admin-api/ims/corp/resource/company/page", headers={"Authorization": f"Bearer {token}"})
    assert denied.json()["code"] == 1008
