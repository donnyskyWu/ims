"""#239 空表导出、负数定位、告警已处置请刷新。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from tests.test_live_alarm import client as alarm_client
from tests.test_live_alarm import headers as alarm_headers
from tests.test_live_alarm import register_and_report, rule_body
from tests.test_live_report_pack import client, full_report, headers, register, seed_account


def test_empty_filter_exports_header_only_message():
    auth = headers()
    exported = client.get(
        "/admin-api/ims/live/ledger/export",
        headers=auth,
        params={"sessionCode": "IMS19990101DYS0000"},
    )
    body = exported.json()
    assert body["code"] == 0, body
    assert body["data"]["message"] == "当前筛选没有场次，已导出空表（仅表头）"
    downloaded = client.get(body["data"]["downloadUrl"], headers=auth)
    assert downloaded.status_code == 200
    assert "live_ledger.xlsx" in downloaded.headers["content-disposition"]


def test_negative_number_names_the_field():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    negative = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(refundAmount=-1),
    )
    body = negative.json()
    assert body["code"] == 1001
    assert body["msg"] == "数值不能为负"
    assert body["data"]["field"] == "refundAmount"

    cost = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(costDetails=[{"costType": "GIFT", "amount": -2}]),
    )
    cost_body = cost.json()
    assert cost_body["code"] == 1001
    assert cost_body["data"]["field"] == "amount"


def test_blank_rule_name_and_repeat_handle_refresh_copy():
    auth = alarm_headers()
    blank = alarm_client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json=rule_body(ruleName="  "),
    )
    assert blank.json()["code"] == 1001
    assert "ruleName" in blank.json()["msg"]

    created = alarm_client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json=rule_body(ruleName="刷新文案", level=2),
    )
    assert created.json()["code"] == 0, created.json()
    code = register_and_report(auth, viewer=10, topic="刷新文案场")
    listed = alarm_client.get(
        "/admin-api/ims/live/alarm/records",
        headers=auth,
        params={"sessionCode": code},
    )
    record_id = listed.json()["data"]["list"][0]["id"]
    first = alarm_client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "HANDLED", "handleRemark": "已处理"},
    )
    assert first.json()["code"] == 0
    again = alarm_client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "FALSE_ALARM", "handleRemark": "再点一次"},
    )
    body = again.json()
    assert body["code"] == 1001
    assert body["msg"] == "告警已处置，请刷新"
