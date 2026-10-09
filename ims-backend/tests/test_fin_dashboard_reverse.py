"""#90 利润看板（按月 / 账号等契约维度）与分成冲销红冲。"""

import json
import uuid

from app.core import SessionLocal
from app.models import OperateLog
from tests.test_fin import approved_session, client, confirm_cost_for_session, headers


def share_ids(auth: dict, code: str) -> dict[str, int]:
    listed = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "pageSize": 20},
    )
    assert listed.json()["code"] == 0
    return {row["shareTarget"]: row["id"] for row in listed.json()["data"]["list"]}


def approve_both(auth: dict, share_id: int) -> None:
    for role in ("FINANCE", "BUSINESS"):
        res = client.put(
            f"/admin-api/ims/fin/share/result/{share_id}/audit",
            headers=auth,
            json={"conclusion": "APPROVE", "auditRole": role},
        )
        assert res.json()["code"] == 0
    assert res.json()["data"]["status"] == "AUDITED"


def test_fin_dashboard_groups_month_account_and_exports_xlsx():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    session = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    account_no = session["accountNo"]

    overview = client.get(
        "/admin-api/ims/fin/dashboard/overview",
        headers=auth,
        params={"statPeriod": "2026-10", "profitType": "NET"},
    )
    body = overview.json()
    assert body["code"] == 0
    assert body["data"]["totalGmv"] == 100000.0
    assert body["data"]["totalCost"] == 16600.0
    assert body["data"]["netProfit"] == 81400.0
    assert body["data"]["shownProfit"] == 81400.0
    assert body["data"]["sessionCount"] == 1
    assert body["data"]["netProfitRate"] == 83.06
    assert body["data"]["refreshedAt"].endswith(":00:00+08:00")
    assert body["data"]["costStructureRatio"]["AD"] > 0

    gross = client.get(
        "/admin-api/ims/fin/dashboard/overview",
        headers=auth,
        params={"statPeriod": "2026-10", "profitType": "GROSS"},
    )
    assert gross.json()["data"]["shownProfit"] == 93000.0
    assert gross.json()["data"]["netProfit"] == 81400.0

    bad = client.get("/admin-api/ims/fin/dashboard/overview", headers=auth, params={"statPeriod": "202610"})
    assert bad.json()["code"] == 1001

    drill = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT", "drillToSession": True},
    )
    rows = drill.json()["data"]
    assert len(rows) == 1
    assert rows[0]["dimensionValue"] == account_no
    assert rows[0]["sessionCount"] == 1
    assert rows[0]["netProfit"] == 81400.0
    assert rows[0]["children"][0]["sessionCode"] == code

    owner = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "OWNER"},
    )
    assert owner.json()["data"][0]["dimensionLabel"] == "责任人·管理员"
    daren = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "DAREN"},
    )
    assert daren.json()["data"][0]["dimensionLabel"] == "达人·管理员"
    group = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "IP_GROUP"},
    )
    assert group.json()["data"][0]["dimensionLabel"] == "小球 IP"
    platform = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "PLATFORM"},
    )
    assert platform.json()["data"][0]["dimensionValue"] == "DOUYIN"
    assert platform.json()["data"][0]["dimensionLabel"] == "抖音"

    subject = client.get(
        "/admin-api/ims/fin/dashboard/drilldown",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "SUBJECT"},
    )
    assert subject.json()["code"] == 1001

    structure = client.get(
        "/admin-api/ims/fin/dashboard/cost-structure",
        headers=auth,
        params={"statPeriod": "2026-10"},
    )
    amounts = {item["costItem"]: item["amount"] for item in structure.json()["data"]}
    assert amounts["AD"] == 5000.0
    assert amounts["SHARE_DAREN"] == 3000.0
    assert amounts["COMMISSION"] == 5000.0
    assert round(sum(item["ratio"] for item in structure.json()["data"]), 4) == 1.0

    shares = client.get(
        "/admin-api/ims/fin/dashboard/share-summary",
        headers=auth,
        params={"statPeriod": "2026-10"},
    )
    by_target = {item["shareTarget"]: item for item in shares.json()["data"]}
    assert by_target["DAREN"]["pendingAmount"] == 3000.0
    assert by_target["DAREN"]["paidOffAmount"] == 0.0
    assert by_target["REALNAME"]["totalAmount"] == 1000.0

    trend = client.get(
        "/admin-api/ims/fin/dashboard/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "granularity": "MONTH"},
    )
    assert trend.json()["code"] == 0
    assert trend.json()["data"][0]["statPeriod"] == "2026-10"
    assert trend.json()["data"][0]["gmv"] == 100000.0
    assert trend.json()["data"][0]["netProfit"] == 81400.0
    assert trend.json()["data"][0]["momRate"] is None

    day = client.get(
        "/admin-api/ims/fin/dashboard/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "granularity": "DAY"},
    )
    assert day.json()["code"] == 0
    assert day.json()["data"][0]["statPeriod"] == "2026-10-06"
    assert day.json()["data"][0]["gmv"] == 100000.0
    week = client.get(
        "/admin-api/ims/fin/dashboard/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "granularity": "WEEK"},
    )
    assert week.json()["code"] == 0
    assert week.json()["data"][0]["gmv"] == 100000.0
    assert "周" in week.json()["data"][0]["periodLabel"]
    bad_grain = client.get(
        "/admin-api/ims/fin/dashboard/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "granularity": "YEAR"},
    )
    assert bad_grain.json()["code"] == 1001

    exported = client.get(
        "/admin-api/ims/fin/dashboard/export",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT", "format": "XLSX"},
    )
    assert exported.json()["code"] == 0
    assert exported.json()["data"]["expiresIn"] == 60
    token = exported.json()["data"]["downloadUrl"].split("token=", 1)[1]
    file_res = client.get("/admin-api/ims/fin/dashboard/export/file", headers=auth, params={"token": token})
    assert file_res.status_code == 200
    assert file_res.content[:2] == b"PK"
    pdf = client.get(
        "/admin-api/ims/fin/dashboard/export",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT", "format": "PDF"},
    )
    assert pdf.json()["code"] == 0
    assert pdf.json()["data"]["expiresIn"] == 60
    assert pdf.json()["data"]["fileName"] == "fin_dashboard_2026-10.pdf"
    pdf_token = pdf.json()["data"]["downloadUrl"].split("token=", 1)[1]
    pdf_file = client.get("/admin-api/ims/fin/dashboard/export/file", headers=auth, params={"token": pdf_token})
    assert pdf_file.status_code == 200
    assert pdf_file.headers["content-type"].startswith("application/pdf")
    assert pdf_file.content.startswith(b"%PDF")
    assert b"2026-10" in pdf_file.content
    assert code.encode() in pdf_file.content
    bad_fmt = client.get(
        "/admin-api/ims/fin/dashboard/export",
        headers=auth,
        params={"statPeriod": "2026-10", "format": "CSV"},
    )
    assert bad_fmt.json()["code"] == 1001


def test_fin_share_reverse_writes_red_entry_audit_and_1150():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    ids = share_ids(auth, code)
    daren_id = ids["DAREN"]

    pending = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "未审不能冲"},
    )
    assert pending.json()["code"] == 1150
    assert "未双审" in pending.json()["msg"]

    approve_both(auth, daren_id)
    empty = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "  "},
    )
    assert empty.json()["code"] == 1144

    paid = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"payoffNote": "发放"},
    )
    assert paid.json()["code"] == 0
    assert paid.json()["data"] is None

    reversed_res = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "发放金额有误"},
    )
    body = reversed_res.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "REVERSED"
    assert body["data"]["shareAmount"] == 3000.0
    assert body["data"]["redEntries"] == [{"item": "达人分成", "amount": -3000.0}]
    assert body["data"]["reverseAudit"]["reason"] == "发放金额有误"
    assert body["data"]["reverseAudit"]["fromStatus"] == "PAID_OFF"
    assert body["data"]["reverseAudit"]["actorName"] == "管理员"

    again = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "再冲一次"},
    )
    assert again.json()["code"] == 1150
    assert "已冲销" in again.json()["msg"]

    db = SessionLocal()
    try:
        logs = (
            db.query(OperateLog)
            .filter(OperateLog.action == "冲销分成单", OperateLog.deleted == 0)
            .order_by(OperateLog.id.asc())
            .all()
        )
        codes = [row.result_code for row in logs]
        assert 0 in codes
        assert 1150 in codes
        assert 1144 in codes
        success = next(row for row in logs if row.result_code == 0)
        detail = json.loads(success.detail_json)
        assert detail["sessionCode"] == code
        assert detail["redAmount"] == -3000.0
        assert detail["reason"] == "发放金额有误"
        assert success.module == "财务"
    finally:
        db.close()

    summary = client.get(
        "/admin-api/ims/fin/dashboard/share-summary",
        headers=auth,
        params={"statPeriod": "2026-10"},
    )
    by_target = {item["shareTarget"]: item for item in summary.json()["data"]}
    assert by_target["DAREN"]["totalAmount"] == 0.0
    assert by_target["DAREN"]["paidOffAmount"] == 0.0
    assert by_target["REALNAME"]["pendingAmount"] == 1000.0


def test_fin_share_reject_and_replaced_after_correction():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    ids = share_ids(auth, code)
    rejected = client.put(
        f"/admin-api/ims/fin/share/result/{ids['REALNAME']}/audit",
        headers=auth,
        json={"conclusion": "REJECT", "auditRole": "FINANCE", "remark": "口径不对"},
    )
    assert rejected.json()["code"] == 0
    assert rejected.json()["data"]["status"] == "REVERSED"
    listed = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "shareTarget": "REALNAME"},
    )
    row = listed.json()["data"]["list"][0]
    assert row["redEntries"][0]["amount"] == -1000.0
    assert row["reverseAudit"]["reason"] == "口径不对"

    approve_both(auth, ids["DAREN"])
    daren_reverse = client.put(
        f"/admin-api/ims/fin/share/result/{ids['DAREN']}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "改基数"},
    )
    assert daren_reverse.json()["code"] == 0

    corrected = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "correctionReason": "冲销后补发",
            "corrected": {
                "commissionRate": 0.05,
                "adCost": 5000,
                "rechargeCost": 100,
                "fixedCost": 2000,
                "sampleCost": 500,
                "shareCostType": "MANUAL",
                "shareDaren": 3500,
                "shareRealname": 1000,
            },
        },
    )
    assert corrected.json()["code"] == 0
    after = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "shareTarget": "DAREN"},
    ).json()["data"]["list"][0]
    assert after["status"] == "REVERSED"
    assert after["shareAmount"] == 3000.0
    assert after["replaced"] is True
    assert after["replacementAmount"] == 3500.0
    assert after["replacedNote"] == "已冲销（新单已补）"
