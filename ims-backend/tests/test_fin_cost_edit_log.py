"""BUG-054：草稿和已提交的成本编辑留下修改记录，详情可查看。"""

import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from tests.test_fin import approved_session
from tests.test_live import headers

client = TestClient(app)

BJ = timezone(timedelta(hours=8))


def cost_body(**overrides) -> dict:
    body = {
        "commissionRate": 0.05,
        "adCost": 10,
        "rechargeCost": 0,
        "fixedCost": 0,
        "sampleCost": 0,
        "shareCostType": "MANUAL",
        "shareDaren": 0,
        "shareRealname": 0,
        "asDraft": True,
    }
    body.update(overrides)
    return body


def post_cost(auth: dict, code: str, **overrides) -> dict:
    res = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=cost_body(**overrides),
    )
    assert res.json()["code"] == 0, res.json()
    return res.json()["data"]


def put_cost(auth: dict, code: str, **overrides) -> dict:
    res = client.put(
        f"/admin-api/ims/fin/cost/{code}",
        headers=auth,
        json=cost_body(**overrides),
    )
    assert res.json()["code"] == 0, res.json()
    return res.json()["data"]


def detail_logs(auth: dict, code: str) -> tuple[dict, list[dict]]:
    res = client.get(f"/admin-api/ims/fin/cost/{code}", headers=auth)
    body = res.json()
    assert body["code"] == 0, body
    return body["data"], body["data"]["editLogs"]


def test_draft_and_submitted_edits_keep_field_history():
    auth = headers()
    code = approved_session(auth)
    created = post_cost(auth, code, asDraft=True)
    assert created["entryStatus"] == "DRAFT"
    _, logs = detail_logs(auth, code)
    assert logs == []

    token = uuid.uuid4().hex
    edited = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": token},
        json=cost_body(rechargeCost=30, asDraft=True),
    )
    assert edited.json()["code"] == 0
    replay = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": token},
        json=cost_body(rechargeCost=99, asDraft=True),
    )
    assert replay.json()["data"]["rechargeCost"] == 30

    put_cost(auth, code, adCost=80, rechargeCost=30, asDraft=True)
    put_cost(auth, code, adCost=80, rechargeCost=30, asDraft=False)
    put_cost(auth, code, adCost=80, rechargeCost=30, sampleCost=12, asDraft=False)

    data, logs = detail_logs(auth, code)
    assert data["entryStatus"] == "SUBMITTED"
    fields = [row["field"] for row in logs]
    assert fields.count("冲话费摊销") == 1
    assert fields.count("投放成本") == 1
    assert fields.count("录入状态") == 1
    assert fields.count("样品成本") == 1
    by_field = {row["field"]: row for row in logs}
    assert by_field["冲话费摊销"]["oldValue"] == "0.00"
    assert by_field["冲话费摊销"]["newValue"] == "30.00"
    assert by_field["投放成本"]["oldValue"] == "10.00"
    assert by_field["投放成本"]["newValue"] == "80.00"
    assert by_field["录入状态"]["oldValue"] == "草稿"
    assert by_field["录入状态"]["newValue"] == "已提交"
    assert by_field["样品成本"]["oldValue"] == "0.00"
    assert by_field["样品成本"]["newValue"] == "12.00"
    assert logs[0]["field"] == "样品成本"
    for row in logs:
        assert row["editorName"] == data["entryUserName"]
        assert row["editorName"]
        shown = datetime.strptime(row["editedAt"], "%Y-%m-%d %H:%M:%S")
        now_bj = datetime.now(timezone.utc).astimezone(BJ).replace(tzinfo=None)
        assert abs((now_bj - shown).total_seconds()) < 180

    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0
    blocked = client.put(
        f"/admin-api/ims/fin/cost/{code}",
        headers=auth,
        json=cost_body(adCost=1, rechargeCost=30, sampleCost=12, asDraft=False),
    )
    assert blocked.json()["code"] == 1141
    assert blocked.json()["msg"] == "成本已核准，请走更正单"
    _, after_confirm = detail_logs(auth, code)
    assert [row["field"] for row in after_confirm] == fields


def test_submitted_edit_keeps_status_and_approved_update_is_rejected():
    auth = headers()
    code = approved_session(auth)
    created = post_cost(auth, code, asDraft=False, adCost=10)
    assert created["entryStatus"] == "SUBMITTED"

    updated = client.put(
        f"/admin-api/ims/fin/cost/{code}",
        headers=auth,
        json=cost_body(adCost=40, asDraft=True),
    )
    body = updated.json()
    assert body["code"] == 0
    assert body["data"]["entryStatus"] == "SUBMITTED"
    assert body["data"]["adCost"] == 40
    log = next(row for row in body["data"]["editLogs"] if row["field"] == "投放成本")
    assert log["oldValue"] == "10.00"
    assert log["newValue"] == "40.00"
    assert log["editorName"]
    assert "T" not in log["editedAt"]
    shown = datetime.strptime(log["editedAt"], "%Y-%m-%d %H:%M:%S")
    now_bj = datetime.now(timezone.utc).astimezone(BJ).replace(tzinfo=None)
    assert abs((now_bj - shown).total_seconds()) < 180

    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0
    blocked = client.put(
        f"/admin-api/ims/fin/cost/{code}",
        headers=auth,
        json=cost_body(adCost=1, asDraft=False),
    )
    assert blocked.json()["code"] == 1141
    assert blocked.json()["msg"] == "成本已核准，请走更正单"
    data, logs = detail_logs(auth, code)
    assert data["entryStatus"] == "CONFIRMED"
    assert data["adCost"] == 40
    assert [row["field"] for row in logs] == ["投放成本"]
