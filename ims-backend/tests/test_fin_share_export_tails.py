"""#196 FIN 分成规则空页、看板导出空月/过期链接、发放备注与凭证边界。"""

import uuid

from tests.test_fin import approved_session, client, confirm_cost_for_session, headers
from tests.test_fin_dashboard_reverse import approve_both, share_ids
from tests.test_fin_share_rule import rule_body


def test_fin_share_rules_blank_page_and_unmatched_filter():
    auth = headers()
    blank = client.get(
        "/admin-api/ims/fin/share/rules",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    assert blank.json()["code"] == 0
    assert blank.json()["data"]["list"] == []
    assert blank.json()["data"]["total"] == 0

    created = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(clientToken=uuid.uuid4().hex, ruleName="空页对照"),
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]

    page = client.get(
        "/admin-api/ims/fin/share/rules",
        headers=auth,
        params={"pageNo": 2, "pageSize": 20},
    )
    assert page.json()["code"] == 0
    assert page.json()["data"]["list"] == []
    assert page.json()["data"]["total"] >= 1
    assert page.json()["data"]["pageNo"] == 2

    unmatched = client.get(
        "/admin-api/ims/fin/share/rules",
        headers=auth,
        params={"shareTarget": "TEAM", "status": "DISABLED"},
    )
    assert unmatched.json()["code"] == 0
    assert unmatched.json()["data"]["list"] == []
    assert unmatched.json()["data"]["total"] == 0
    listed = client.get(
        "/admin-api/ims/fin/share/rules",
        headers=auth,
        params={"shareTarget": "DAREN", "status": "ENABLED", "pageNo": 1, "pageSize": 20},
    )
    assert any(row["id"] == rule_id for row in listed.json()["data"]["list"])


def test_fin_dashboard_export_empty_month_and_expired_link():
    auth = headers()
    exported = client.get(
        "/admin-api/ims/fin/dashboard/export",
        headers=auth,
        params={"statPeriod": "1999-01", "dimensionType": "ACCOUNT", "format": "XLSX"},
    )
    body = exported.json()
    assert body["code"] == 0
    assert body["data"]["empty"] is True
    assert body["data"]["rowCount"] == 0
    assert body["data"]["expiresIn"] == 60
    assert body["data"]["fileName"] == "fin_dashboard_1999-01.xlsx"
    token = body["data"]["downloadUrl"].split("token=", 1)[1]
    file_res = client.get("/admin-api/ims/fin/dashboard/export/file", headers=auth, params={"token": token})
    assert file_res.status_code == 200
    assert file_res.content[:2] == b"PK"

    missing = client.get(
        "/admin-api/ims/fin/dashboard/export/file",
        headers=auth,
        params={"token": "missing-token"},
    )
    assert missing.json()["code"] == 1002
    assert "过期" in missing.json()["msg"]


def test_fin_payoff_rejects_long_note_and_blank_voucher():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    daren_id = share_ids(auth, code)["DAREN"]
    approve_both(auth, daren_id)

    long_note = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"payoffNote": "备" * 257},
    )
    assert long_note.json()["code"] == 1001
    assert "256" in long_note.json()["msg"]

    blank_voucher = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"payoffNote": "仍待发放", "payoffVoucher": {"fileName": " ", "fileKey": ""}},
    )
    assert blank_voucher.json()["code"] == 1001
    assert "凭证" in blank_voucher.json()["msg"]

    still = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "shareTarget": "DAREN"},
    )
    row = still.json()["data"]["list"][0]
    assert row["status"] == "AUDITED"
    assert row["payoffNote"] in ("", None)

    paid = client.put(
        f"/admin-api/ims/fin/share/result/{daren_id}/payoff",
        headers=auth,
        json={"payoffNote": "发" * 256},
    )
    assert paid.json()["code"] == 0
    listed = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "shareTarget": "DAREN"},
    )
    paid_row = listed.json()["data"]["list"][0]
    assert paid_row["status"] == "PAID_OFF"
    assert paid_row["payoffNote"] == "发" * 256
    assert paid_row["payoffVoucher"] is None
