"""#207 分成单驳回备注上限，以及 R9 分成金额脱敏（列表与红冲回执）。"""

from tests.test_fin import approved_session, client, confirm_cost_for_session, headers
from tests.test_fin_r9_mask import ANALYST
from tests.test_fin_r9_mask import headers as role_headers

MASK = "***"


def _share(auth: dict, code: str, target: str) -> dict:
    listed = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "shareTarget": target},
    )
    body = listed.json()
    assert body["code"] == 0, body
    assert body["data"]["total"] == 1
    return body["data"]["list"][0]


def test_reject_remark_over_512_keeps_pending():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    row = _share(auth, code, "REALNAME")
    rejected = client.put(
        f"/admin-api/ims/fin/share/result/{row['id']}/audit",
        headers=auth,
        json={"conclusion": "REJECT", "auditRole": "FINANCE", "remark": "注" * 513},
    )
    body = rejected.json()
    assert body["code"] == 1001
    assert "512" in body["msg"]
    again = _share(auth, code, "REALNAME")
    assert again["status"] == "PENDING_AUDIT"
    assert again["shareAmount"] == 1000.0


def test_r9_masks_share_amounts_and_red_entries():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    row = _share(auth, code, "DAREN")
    assert row["shareAmount"] == 3000.0
    assert row["calcDetail"]["shareTotal"] == 4000.0
    assert row["calcDetail"]["partAmount"] == 3000.0

    rejected = client.put(
        f"/admin-api/ims/fin/share/result/{row['id']}/audit",
        headers=auth,
        json={"conclusion": "REJECT", "auditRole": "FINANCE", "remark": "口径不对"},
    )
    assert rejected.json()["code"] == 0
    assert rejected.json()["data"]["status"] == "REVERSED"
    admin_after = _share(auth, code, "DAREN")
    assert admin_after["shareAmount"] == 3000.0
    assert admin_after["redEntries"][0]["amount"] == -3000.0

    masked = _share(role_headers(ANALYST), code, "DAREN")
    assert masked["status"] == "REVERSED"
    assert masked["shareBase"] == MASK
    assert masked["shareAmount"] == MASK
    assert masked["calcDetail"]["shareTotal"] == MASK
    assert masked["calcDetail"]["partAmount"] == MASK
    assert masked["redEntries"][0]["amount"] == MASK
    assert masked["reverseAudit"]["reason"] == "口径不对"
