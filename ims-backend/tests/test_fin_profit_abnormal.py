"""#106 利润异常净利率（2σ）与利润反查聚合 / 异常清单。"""

import uuid

from sqlalchemy import select

from app.core import SessionLocal
from app.models import LiveSession
from tests.test_fin import client, headers
from tests.test_live import register_payload, seed_live_deps


def open_session(auth: dict, deps: tuple[int, int, int, int]) -> str:
    account_id, person_id, phone_id, room_id = deps
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=register_payload(account_id, person_id, phone_id, room_id),
    )
    assert reg.json()["code"] == 0
    code = reg.json()["data"]["sessionCode"]
    detail = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    if detail.get("sessionStatus") == "PENDING_RISK_CHECK":
        client.put(
            f"/admin-api/ims/live/register/{code}/approve",
            headers=auth,
            json={"approve": True},
        )
    report = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json={
            "actualStart": "2026-10-06T20:00:00+08:00",
            "actualEnd": "2026-10-06T22:00:00+08:00",
            "gmv": 100000.0,
            "refundAmount": 2000.0,
            "orderCount": 120,
            "viewerCount": 5000,
            "peakOnline": 800,
            "newFans": 200,
            "adCost": 5000.0,
        },
    )
    assert report.json()["code"] == 0
    confirm = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirm.json()["code"] == 0
    return code


def post_cost(auth: dict, code: str, ad_cost: float) -> None:
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "commissionRate": 0.05,
            "adCost": ad_cost,
            "rechargeCost": 100,
            "fixedCost": 2000,
            "sampleCost": 500,
            "shareCostType": "MANUAL",
            "shareDaren": 3000,
            "shareRealname": 1000,
        },
    )
    assert created.json()["code"] == 0
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0


def pin_platform(code: str, platform: str) -> None:
    db = SessionLocal()
    try:
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == code))
        assert row is not None
        row.platform = platform
        db.commit()
    finally:
        db.close()


def test_fin_profit_abnormal_two_sigma_and_trace_aggregate():
    auth = headers()
    deps = seed_live_deps()
    platform = f"P{uuid.uuid4().hex[:6].upper()}"
    normal_a = open_session(auth, deps)
    normal_b = open_session(auth, deps)
    outlier = open_session(auth, deps)
    post_cost(auth, normal_a, 5000)
    post_cost(auth, normal_b, 5000)
    post_cost(auth, outlier, 80000)
    for code in (normal_a, normal_b, outlier):
        pin_platform(code, platform)

    lonely = open_session(auth, deps)
    post_cost(auth, lonely, 5000)
    lonely_platform = f"L{uuid.uuid4().hex[:6].upper()}"
    pin_platform(lonely, lonely_platform)
    alone_rows = client.get(
        "/admin-api/ims/fin/profit/abnormal",
        headers=auth,
        params={"platform": lonely_platform},
    )
    assert alone_rows.json()["code"] == 0
    assert alone_rows.json()["data"]["list"] == []

    bad_range = client.get(
        "/admin-api/ims/fin/profit/abnormal",
        headers=auth,
        params={"dateRange": "not-a-range"},
    )
    assert bad_range.json()["code"] == 1001

    empty_window = client.get(
        "/admin-api/ims/fin/profit/abnormal",
        headers=auth,
        params={"platform": platform, "dateRange": "1999-01-01,1999-01-31"},
    )
    assert empty_window.json()["code"] == 0
    assert empty_window.json()["data"]["total"] == 0

    listed = client.get(
        "/admin-api/ims/fin/profit/abnormal",
        headers=auth,
        params={"platform": platform, "pageSize": 50},
    )
    assert listed.json()["code"] == 0
    rows = listed.json()["data"]["list"]
    codes = [row["sessionCode"] for row in rows]
    assert codes == [outlier]
    hit = rows[0]
    assert hit["peerAvgRate"] == 83.06
    assert hit["sigma"] == 0
    assert hit["deviationSigma"] == -99
    assert hit["abnormalCostItem"] == "ad"
    assert hit["netProfitRate"] == 6.53
    assert normal_a not in codes and normal_b not in codes

    trace = client.get(
        "/admin-api/ims/dc/profit-trace/abnormal",
        headers=auth,
        params={"platform": platform},
    )
    assert trace.json()["code"] == 0
    assert [row["sessionCode"] for row in trace.json()["data"]["list"]] == [outlier]
    assert trace.json()["data"]["list"][0]["isAbnormal"] is True
    assert trace.json()["data"]["list"][0]["abnormalCostItem"] == "ad"

    outlier_row = client.get(
        "/admin-api/ims/dc/profit-trace/list",
        headers=auth,
        params={"sessionCode": outlier},
    )
    assert outlier_row.json()["data"]["list"][0]["isAbnormal"] is True
    normal_row = client.get(
        "/admin-api/ims/dc/profit-trace/list",
        headers=auth,
        params={"sessionCode": normal_a},
    )
    assert normal_row.json()["data"]["list"][0]["isAbnormal"] is False

    bad_dim = client.get(
        "/admin-api/ims/dc/profit-trace/aggregate",
        headers=auth,
        params={"aggregateBy": "COMPANY"},
    )
    assert bad_dim.json()["code"] == 1001

    grouped = client.get(
        "/admin-api/ims/dc/profit-trace/aggregate",
        headers=auth,
        params={"aggregateBy": "PERSON"},
    )
    assert grouped.json()["code"] == 0
    bucket = None
    for row in grouped.json()["data"]:
        child_codes = [child["sessionCode"] for child in row["children"]]
        if outlier in child_codes:
            bucket = row
            break
    assert bucket is not None
    child_codes = [child["sessionCode"] for child in bucket["children"]]
    assert normal_a in child_codes and normal_b in child_codes
    assert bucket["sessionCount"] == len(bucket["children"])
    assert bucket["sessionCount"] >= 3

    by_month = client.get(
        "/admin-api/ims/dc/profit-trace/aggregate",
        headers=auth,
        params={"aggregateBy": "MONTH", "dateRange": "2026-10-01,2026-10-31"},
    )
    assert by_month.json()["code"] == 0
    month_codes = [
        child["sessionCode"]
        for row in by_month.json()["data"]
        for child in row["children"]
    ]
    assert outlier in month_codes
