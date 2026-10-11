"""#146 · R9 利润列表与看板金额脱敏；R1/R3 仍见金额。"""

from app.acct_seed import E2E_ACCT_FINANCE_USER
from tests.test_fin import approved_session, client, confirm_cost_for_session

ANALYST = "e2e_fin_r9"
MASK = "***"


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_r9_masks_profit_list_and_dashboard_amounts():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    analyst = headers(ANALYST)
    finance = headers(E2E_ACCT_FINANCE_USER)

    listed = client.get(
        "/admin-api/ims/fin/profit/list",
        headers=analyst,
        params={"sessionCode": code},
    ).json()
    assert listed["code"] == 0
    row = listed["data"]["list"][0]
    assert row["sessionCode"] == code
    assert row["gmv"] == MASK
    assert row["grossProfit"] == MASK
    assert row["operatingProfit"] == MASK
    assert row["netProfit"] == MASK
    assert row["calcRuleSnapshot"]["params"]["revenue"] == MASK
    assert row["calcRuleSnapshot"]["params"]["adCost"] == MASK
    assert row["netProfitRate"] == 83.06
    assert row["calcStatus"] == "CALCULATED"

    summary = client.get("/admin-api/ims/fin/profit/summary", headers=analyst).json()
    assert summary["data"]["totalRevenue"] == MASK
    assert summary["data"]["totalCost"] == MASK
    assert summary["data"]["shownProfit"] == MASK
    assert summary["data"]["sessionCount"] >= 1

    detail = client.get(f"/admin-api/ims/fin/profit/{code}", headers=analyst).json()
    assert detail["data"]["netProfit"] == MASK
    assert detail["data"]["grossProfit"] == MASK
    history = client.get(f"/admin-api/ims/fin/profit/history/{code}", headers=analyst).json()
    assert history["data"][0]["netProfit"] == MASK

    admin_row = client.get(
        "/admin-api/ims/fin/profit/list",
        headers=auth,
        params={"sessionCode": code},
    ).json()["data"]["list"][0]
    assert admin_row["netProfit"] == 81400.0
    assert admin_row["gmv"] == 100000.0

    finance_row = client.get(
        "/admin-api/ims/fin/profit/list",
        headers=finance,
        params={"sessionCode": code},
    ).json()["data"]["list"][0]
    assert finance_row["netProfit"] == 81400.0

    overview = client.get(
        "/admin-api/ims/fin/dashboard/overview",
        headers=analyst,
        params={"statPeriod": "2026-10", "profitType": "NET"},
    ).json()
    assert overview["code"] == 0
    assert overview["data"]["totalGmv"] == MASK
    assert overview["data"]["totalCost"] == MASK
    assert overview["data"]["netProfit"] == MASK
    assert overview["data"]["shownProfit"] == MASK
    assert overview["data"]["netProfitRate"] == 83.06
    assert overview["data"]["sessionCount"] == 1
    assert overview["data"]["costStructureRatio"]["AD"] > 0

    admin_overview = client.get(
        "/admin-api/ims/fin/dashboard/overview",
        headers=auth,
        params={"statPeriod": "2026-10"},
    ).json()
    assert admin_overview["data"]["netProfit"] == 81400.0

    drill = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=analyst,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT", "drillToSession": True},
    ).json()
    child = drill["data"][0]["children"][0]
    assert child["sessionCode"] == code
    assert child["gmv"] == MASK
    assert child["totalCost"] == MASK
    assert child["netProfit"] == MASK
    assert drill["data"][0]["totalGmv"] == MASK
    assert drill["data"][0]["sessionCount"] == 1

    structure = client.get(
        "/admin-api/ims/fin/dashboard/cost-structure",
        headers=analyst,
        params={"statPeriod": "2026-10"},
    ).json()
    ad = next(item for item in structure["data"] if item["costItem"] == "AD")
    assert ad["amount"] == MASK
    assert ad["ratio"] > 0

    shares = client.get(
        "/admin-api/ims/fin/dashboard/share-summary",
        headers=analyst,
        params={"statPeriod": "2026-10"},
    ).json()
    daren = next(item for item in shares["data"] if item["shareTarget"] == "DAREN")
    assert daren["totalAmount"] == MASK
    assert daren["pendingAmount"] == MASK
    assert daren["sessionCount"] >= 1

    trend = client.get(
        "/admin-api/ims/fin/dashboard/trend",
        headers=analyst,
        params={"dateRange": "2026-10-01,2026-10-31", "granularity": "MONTH"},
    ).json()
    assert trend["data"][0]["gmv"] == MASK
    assert trend["data"][0]["cost"] == MASK
    assert trend["data"][0]["netProfit"] == MASK
    assert trend["data"][0]["netProfitRate"] == 83.06

    exported = client.get(
        "/admin-api/ims/fin/dashboard/export",
        headers=analyst,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT", "format": "XLSX"},
    ).json()
    assert exported["code"] == 0
    token = exported["data"]["downloadUrl"].split("token=", 1)[1]
    file_res = client.get("/admin-api/ims/fin/dashboard/export/file", headers=analyst, params={"token": token})
    assert file_res.status_code == 200
    assert b"***" in file_res.content
    assert b"81400" not in file_res.content
    assert b"100000" not in file_res.content


def test_r9_masks_cost_list_and_detail_amounts():
    auth = headers()
    code = approved_session(auth)
    analyst = headers(ANALYST)
    finance = headers(E2E_ACCT_FINANCE_USER)

    pending = client.get("/admin-api/ims/fin/cost/pending-sessions", headers=analyst).json()
    assert pending["code"] == 0
    row = next(item for item in pending["data"]["list"] if item["sessionCode"] == code)
    assert row["gmv"] == MASK
    assert row["refund"] == MASK
    assert row["adCost"] == MASK

    admin_row = next(
        item
        for item in client.get("/admin-api/ims/fin/cost/pending-sessions", headers=auth).json()["data"]["list"]
        if item["sessionCode"] == code
    )
    assert admin_row["gmv"] == 100000.0
    assert admin_row["refund"] == 2000.0

    confirm_cost_for_session(auth, code)
    listed = client.get("/admin-api/ims/fin/cost/list", headers=analyst, params={"sessionCode": code}).json()
    assert listed["code"] == 0
    assert listed["data"]["list"][0]["totalCost"] == MASK
    assert listed["data"]["list"][0]["commissionAmount"] == MASK

    detail = client.get(f"/admin-api/ims/fin/cost/{code}", headers=analyst).json()
    assert detail["code"] == 0
    assert detail["data"]["costGmv"] == MASK
    assert detail["data"]["costRefund"] == MASK
    assert detail["data"]["totalCost"] == MASK
    assert detail["data"]["adCost"] == MASK
    assert detail["data"]["shareDaren"] == MASK
    assert detail["data"]["commissionRate"] == 0.05

    admin_detail = client.get(f"/admin-api/ims/fin/cost/{code}", headers=auth).json()["data"]
    assert admin_detail["costGmv"] == 100000.0
    assert admin_detail["costRefund"] == 2000.0
    assert admin_detail["totalCost"] == 16600.0

    finance_detail = client.get(f"/admin-api/ims/fin/cost/{code}", headers=finance).json()["data"]
    assert finance_detail["costGmv"] == 100000.0
    assert finance_detail["totalCost"] == 16600.0
