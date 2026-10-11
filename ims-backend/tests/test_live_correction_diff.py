"""BUG-038 · 更正单只记录实际变化的字段。"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from app.main import app
from test_live_session_board import headers, seed

client = TestClient(app)

REPORT = {
    "actualStart": "2026-10-20T20:00:00+08:00",
    "actualEnd": "2026-10-20T22:00:00+08:00",
    "gmv": 1000,
    "refundAmount": 0,
    "orderCount": 10,
    "viewerCount": 500,
    "peakOnline": 80,
    "newFans": 300,
    "adCost": 100,
}


def test_correction_lists_only_changed_fields():
    auth = headers()
    ids = seed()
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": ids["account"],
            "realnamePersonId": ids["person"],
            "responsibleUserId": 1,
            "deviceAssetIds": [ids["phone"]],
            "platform": "DOUYIN",
            "topic": "更正对比专场",
            "planStartTime": "2026-10-20T20:00:00+08:00",
            "planEndTime": "",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    assert client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth).json()["code"] == 0
    assert client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth).json()["code"] == 0
    submitted = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=REPORT)
    assert submitted.json()["code"] == 0, submitted.json()
    changed = dict(REPORT)
    changed["newFans"] = 310
    corrected = client.post(
        f"/admin-api/ims/live/report/{code}/correction",
        headers=auth,
        json={**changed, "correctionReason": "涨粉复核"},
    )
    body = corrected.json()
    assert body["code"] == 0, body
    assert body["data"]["changes"] == ["涨粉 300 → 310"]
    slips = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]["corrections"]
    assert slips[0]["changes"] == ["涨粉 300 → 310"]
