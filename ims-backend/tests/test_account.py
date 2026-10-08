import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.crypto import encrypt_text
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import CollectorAccountBind, Company, IpGroup, PlatformAccount, Realname


client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def seed_account(platform: str = "DOUYIN", tenant: int = 0) -> int:
    ops = ops_session()
    try:
        company = Company(company_name="甲公司", status="ENABLED", tenant_id=tenant)
        group = IpGroup(group_name="小球 IP", status="ENABLED", tenant_id=tenant)
        person = Realname(
            real_name="张三",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            status="ENABLED",
            tenant_id=tenant,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="ACCT-2026-0001",
            account_name="神鱼体育",
            platform_type=platform,
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            cookie_enc=encrypt_text("cookie-demo"),
            status="IN_USE",
            tenant_id=tenant,
        )
        ops.add(account)
        ops.flush()
        ops.add(
            CollectorAccountBind(
                oa_account_id=account.id,
                collector_account_id=f"acc_douyin_{account.id}",
                bind_status="BOUND",
                conn_status="SUCCESS",
                last_probe_at="2026-09-29 08:00:00",
                tenant_id=tenant,
            )
        )
        ops.commit()
        return account.id
    finally:
        ops.close()


def test_account_page_requires_platform_and_filters():
    auth = headers()
    missing = client.get("/admin-api/ims/corp/account/page", headers=auth)
    assert missing.json()["code"] == 1001
    empty = client.get("/admin-api/ims/corp/account/page", headers=auth, params={"platformType": "DOUYIN"})
    assert empty.json()["data"]["total"] == 0

    account_id = seed_account("DOUYIN")
    ops = ops_session()
    try:
        company = ops.get(Company, 1)
        group = ops.get(IpGroup, 1)
        ops.add(
            PlatformAccount(
                account_no="ACCT-2026-0002",
                account_name="其他平台",
                platform_type="KUAISHOU",
                ip_group_id=group.id,
                company_id=company.id,
                status="IN_USE",
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()

    page = client.get("/admin-api/ims/corp/account/page", headers=auth, params={"platformType": "DOUYIN"})
    body = page.json()["data"]
    assert body["total"] == 1
    assert body["list"][0]["platformType"] == "DOUYIN"
    assert body["list"][0]["collectBindSummary"] == "已绑定"
    assert body["list"][0]["realNameMasked"] == "张*"

    detail = client.get(f"/admin-api/ims/corp/account/{account_id}", headers=auth)
    assert detail.json()["data"]["nickname"] == "神鱼体育"
    assert detail.json()["data"]["hasCookie"] is True

    bind = client.get(f"/admin-api/ims/corp/account/{account_id}/collector-bind", headers=auth)
    assert bind.json()["data"]["collectorAccountId"].startswith("acc_douyin_")
    assert bind.json()["data"]["bindStatus"] == "BOUND"

    foreign = client.get("/admin-api/ims/corp/account/999", headers=auth)
    assert foreign.json()["code"] == 1504


def test_platform_account_write_rejects_bad_company():
    auth = headers()
    ops = ops_session()
    try:
        group = IpGroup(group_name="G1", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.commit()
        group_id = group.id
    finally:
        ops.close()

    bad = client.post(
        "/admin-api/ims/master/platform-account",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "accountName": "测试号",
            "ipGroupId": group_id,
            "companyId": 999,
            "holderUserId": 1,
            "status": "IN_USE",
        },
    )
    assert bad.json()["code"] == 1500
    assert bad.json()["msg"] == "公司不存在"
