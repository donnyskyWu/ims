import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_FOOTBALL_WEBAPI_BASE_URL", None)

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.crypto import encrypt_text
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import Company, IpGroup, PlatformAccount, Realname

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account() -> int:
    ops = ops_session()
    try:
        company = Company(company_name="甲公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="IP-A", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="张三",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-COST-01",
            account_name="成本测试号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            author_user_id=9001,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        return account.id
    finally:
        ops.close()


def test_cost_purchase_process_and_missing_account():
    auth = headers()
    account_id = seed_account()
    missing = client.get("/admin-api/ims/cost/account/99999", headers=auth)
    assert missing.json()["code"] == 1231

    purchase = client.put(
        f"/admin-api/ims/cost/account/{account_id}/purchase",
        headers=auth,
        json={"amount": 12000, "period": "2026-09", "payMethod": "WECHAT"},
    )
    assert purchase.json()["code"] == 0
    assert purchase.json()["data"]["costType"] == "PURCHASE"

    process = client.post(
        f"/admin-api/ims/cost/account/{account_id}/process",
        headers=auth,
        json={"amount": 860, "period": "2026-09", "processSubtype": "PROCESS_RECHARGE"},
    )
    assert process.json()["code"] == 0
    pid = int(process.json()["data"]["id"])

    detail = client.get(f"/admin-api/ims/cost/account/{account_id}", headers=auth)
    body = detail.json()["data"]
    assert body["purchase"]["amount"] == 12000
    assert body["processTotal"] == 860
    assert body["totalCost"] == 12860

    updated = client.put(
        f"/admin-api/ims/cost/account/{account_id}/process",
        headers=auth,
        json={"id": pid, "amount": 900, "period": "2026-09"},
    )
    assert updated.json()["data"]["amount"] == 900

    deleted = client.delete(f"/admin-api/ims/cost/account/{account_id}/process?id={pid}", headers=auth)
    assert deleted.json()["code"] == 0
    after = client.get(f"/admin-api/ims/cost/account/{account_id}", headers=auth).json()["data"]
    assert after["processTotal"] == 0


def test_roi_revenue_delay_without_football():
    auth = headers()
    account_id = seed_account()
    client.put(
        f"/admin-api/ims/cost/account/{account_id}/purchase",
        headers=auth,
        json={"amount": 1000, "period": "2026-09"},
    )
    roi = client.get(
        "/admin-api/ims/cost/roi",
        headers=auth,
        params={"startDate": "2026-09-01", "endDate": "2026-09-30", "dimension": "ACCOUNT"},
    )
    data = roi.json()["data"]
    assert roi.json()["code"] == 0
    assert data["revenueDelayed"] is True
    assert data["totalRevenue"] is None
    assert data["revenueDelayHint"] == "数据延迟"
    assert data["totalCost"] == 1000
    assert data["details"][0]["revenue"] is None

    orders = client.get(
        "/admin-api/ims/cost/football-order/list",
        headers=auth,
        params={"startDate": "2026-09-01", "endDate": "2026-09-30"},
    )
    assert orders.json()["code"] == 1232


def test_roi_with_football_stub(monkeypatch):
    auth = headers()
    account_id = seed_account()

    def fake_sum(**kwargs):
        if kwargs.get("author_id") == "9001":
            return 5000.0, None
        return 0.0, None

    monkeypatch.setattr("app.cost.sum_revenue", fake_sum)
    client.put(
        f"/admin-api/ims/cost/account/{account_id}/purchase",
        headers=auth,
        json={"amount": 1000, "period": "2026-09"},
    )
    roi = client.get(
        "/admin-api/ims/cost/roi",
        headers=auth,
        params={"startDate": "2026-09-01", "endDate": "2026-09-30", "dimension": "ACCOUNT"},
    ).json()["data"]
    assert roi["revenueDelayed"] is False
    assert roi["totalRevenue"] == 5000
    assert roi["roi"] == 5.0
