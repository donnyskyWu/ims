"""#219 · 待录入起止、未开播空起止，以及重复核准刷新提示。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from test_live_report_pack import _insert_ended, full_report, headers, register, seed_account

client = TestClient(app)


def test_pending_keeps_recorded_range_and_blank_live_range():
    auth = headers()
    _insert_ended("IMS20261009RNG0219", 30)
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    started = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()

    pending = client.get("/admin-api/ims/live/report/pending", headers=auth, params={"pageNo": 1, "pageSize": 100})
    body = pending.json()
    assert body["code"] in (0, 1048), body
    rows = {item["sessionCode"]: item for item in body["data"]["list"]}

    recorded = rows["IMS20261009RNG0219"]
    assert recorded["entryStatus"] == ""
    assert recorded["actualStart"]
    assert recorded["actualEnd"]
    assert recorded["actualEnd"] > recorded["actualStart"]

    live = rows[code]
    assert live["entryStatus"] == ""
    assert live["actualStart"] == ""
    assert live["actualEnd"] == ""


def test_second_confirm_asks_to_refresh():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    filed = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report())
    assert filed.json()["code"] == 0, filed.json()
    first = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert first.json()["code"] == 0, first.json()
    again = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert again.json()["code"] == 1042
    assert again.json()["msg"] == "报告已核准，请刷新"
    kept = client.get(f"/admin-api/ims/live/report/{code}", headers=auth)
    assert kept.json()["data"]["entryStatus"] == "CONFIRMED"
