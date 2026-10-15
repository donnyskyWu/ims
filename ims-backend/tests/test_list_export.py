import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, PlatformAccount, Realname


client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_filtered_exports_follow_current_query_and_mask_secrets():
    auth = headers()
    ops = ops_session()
    try:
        keep = Company(company_name="导出保留公司", credit_code="EXPKEEP000000001", status="ENABLED", tenant_id=0)
        drop = Company(company_name="导出剔除公司", credit_code="EXPDROP000000001", status="DISABLED", tenant_id=0)
        person = Realname(
            real_name="导出实名",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330103199001011234"),
            phone_enc=encrypt_text("13700001111"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([keep, drop, person])
        ops.flush()
        ops.add(
            PlatformAccount(
                account_no="ACCT-EXP-DY",
                account_name="导出抖音",
                platform_type="DOUYIN",
                company_id=keep.id,
                status="IN_POOL",
                tenant_id=0,
            )
        )
        ops.add(
            PlatformAccount(
                account_no="ACCT-EXP-KS",
                account_name="导出快手",
                platform_type="KUAISHOU",
                company_id=keep.id,
                status="IN_POOL",
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()

    issued = client.get(
        "/admin-api/ims/corp/resource/company/export",
        headers=auth,
        params={"status": "ENABLED", "companyName": "导出保留"},
    )
    assert issued.json()["code"] == 0
    download = issued.json()["data"]["downloadUrl"]
    body = client.get(download, headers=auth)
    text = body.content.decode("utf-8-sig")
    assert "导出保留公司" in text
    assert "导出剔除公司" not in text

    people = client.get("/admin-api/ims/corp/resource/realname/export", headers=auth, params={"realName": "导出实名"})
    person_file = client.get(people.json()["data"]["downloadUrl"], headers=auth).content.decode("utf-8-sig")
    assert "330103199001011234" not in person_file
    assert "13700001111" not in person_file
    assert "在职" in person_file

    douyin = client.get("/admin-api/ims/corp/account/export", headers=auth, params={"platformType": "DOUYIN", "keyword": "导出抖音"})
    account_file = client.get(douyin.json()["data"]["downloadUrl"], headers=auth).content.decode("utf-8-sig")
    assert "导出抖音" in account_file
    assert "导出快手" not in account_file
    assert "导出保留公司" in account_file
