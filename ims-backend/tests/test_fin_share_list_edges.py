"""#154 分成列表筛选与发放边界：非法枚举 1001、备注长度、重复发放不改备注、已冲销 1150、锁期 1142。"""

from tests.test_fin import (
    _session_in_period,
    approved_session,
    client,
    confirm_cost_for_session,
    headers,
)
from tests.test_live import seed_live_deps


def _rows(auth: dict, **params):
    listed = client.get("/admin-api/ims/fin/share/results", headers=auth, params=params)
    body = listed.json()
    assert body["code"] == 0, body
    return body["data"]


def _audit_both(auth: dict, share_id: int) -> None:
    for role in ("FINANCE", "BUSINESS"):
        res = client.put(
            f"/admin-api/ims/fin/share/result/{share_id}/audit",
            headers=auth,
            json={"conclusion": "APPROVE", "auditRole": role},
        )
        assert res.json()["code"] == 0, res.json()


def test_share_list_filters_reject_unknown_and_page():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    daren = _rows(auth, sessionCode=code, shareTarget="DAREN")
    assert daren["total"] == 1
    assert daren["list"][0]["shareTarget"] == "DAREN"

    team = _rows(auth, sessionCode=code, shareTarget="TEAM")
    assert team["total"] == 0
    assert team["list"] == []

    pending = _rows(auth, sessionCode=code, status="PENDING_AUDIT", pageNo=1, pageSize=1)
    assert pending["total"] == 2
    assert len(pending["list"]) == 1
    page2 = _rows(auth, sessionCode=code, status="PENDING_AUDIT", pageNo=2, pageSize=1)
    assert len(page2["list"]) == 1
    assert page2["list"][0]["id"] != pending["list"][0]["id"]

    paid = _rows(auth, sessionCode=code, status="PAID_OFF")
    assert paid["total"] == 0

    partial = _rows(auth, sessionCode=code[-8:])
    assert any(row["sessionCode"] == code for row in partial["list"])

    bad_target = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"shareTarget": "NOPE"},
    )
    assert bad_target.json()["code"] == 1001
    assert "分成对象" in bad_target.json()["msg"]

    bad_status = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"status": "DONE"},
    )
    assert bad_status.json()["code"] == 1001
    assert "分成状态" in bad_status.json()["msg"]


def test_payoff_note_edges_repeat_keeps_note_and_reversed_blocks():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    rows = _rows(auth, sessionCode=code)["list"]
    assert len(rows) == 2
    first, second = rows[0], rows[1]
    _audit_both(auth, first["id"])
    _audit_both(auth, second["id"])

    trimmed = client.put(
        f"/admin-api/ims/fin/share/result/{first['id']}/payoff",
        headers=auth,
        json={"payoffNote": "  已打款  "},
    )
    assert trimmed.json()["code"] == 0
    echoed = _rows(auth, sessionCode=code, shareTarget=first["shareTarget"])["list"][0]
    assert echoed["status"] == "PAID_OFF"
    assert echoed["payoffNote"] == "已打款"

    again = client.put(
        f"/admin-api/ims/fin/share/result/{first['id']}/payoff",
        headers=auth,
        json={"payoffNote": "不要覆盖"},
    )
    assert again.json()["code"] == 0
    assert again.json()["data"] is None
    kept = _rows(auth, sessionCode=code, shareTarget=first["shareTarget"])["list"][0]
    assert kept["payoffNote"] == "已打款"

    too_long = client.put(
        f"/admin-api/ims/fin/share/result/{second['id']}/payoff",
        headers=auth,
        json={"payoffNote": "备" * 257},
    )
    assert too_long.json()["code"] == 1001
    assert "256" in too_long.json()["msg"]
    still = _rows(auth, sessionCode=code, shareTarget=second["shareTarget"])["list"][0]
    assert still["status"] == "AUDITED"
    assert still["payoffNote"] == ""

    exact = client.put(
        f"/admin-api/ims/fin/share/result/{second['id']}/payoff",
        headers=auth,
        json={"payoffNote": "备" * 256},
    )
    assert exact.json()["code"] == 0
    paid = _rows(auth, sessionCode=code, shareTarget=second["shareTarget"])["list"][0]
    assert paid["payoffNote"] == "备" * 256

    reversed_row = client.put(
        f"/admin-api/ims/fin/share/result/{second['id']}/payoff",
        headers=auth,
        json={"reverse": True, "reverseReason": "金额有误"},
    )
    assert reversed_row.json()["code"] == 0, reversed_row.json()
    blocked = client.put(
        f"/admin-api/ims/fin/share/result/{second['id']}/payoff",
        headers=auth,
        json={"payoffNote": "再发一次"},
    )
    assert blocked.json()["code"] == 1150
    assert "已冲销" in blocked.json()["msg"]


def test_payoff_locked_period_returns_1142():
    auth = headers()
    deps = seed_live_deps()
    code = _session_in_period(auth, "2098-11-15T20:00:00+08:00", deps)
    confirm_cost_for_session(auth, code)
    row = _rows(auth, sessionCode=code, shareTarget="DAREN")["list"][0]
    _audit_both(auth, row["id"])
    closed = client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": "2098-11"})
    assert closed.json()["code"] == 0
    assert closed.json()["data"]["financeStatus"] == "LOCKED"
    denied = client.put(
        f"/admin-api/ims/fin/share/result/{row['id']}/payoff",
        headers=auth,
        json={"payoffNote": "锁后发放"},
    )
    assert denied.json()["code"] == 1142
    assert "财务期间已结账" in denied.json()["msg"]
    kept = _rows(auth, sessionCode=code, shareTarget="DAREN")["list"][0]
    assert kept["status"] == "AUDITED"
    assert kept["payoffNote"] == ""
