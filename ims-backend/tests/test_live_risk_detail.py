"""BUG-034 · 五项风控检查落库说明，证件明细不再丢弃。"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from app.main import app
from test_live_session_board import headers, seed

client = TestClient(app)


def test_risk_checks_store_detail():
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
            "topic": "违禁专场",
            "planStartTime": "2026-10-20T20:00:00+08:00",
            "planEndTime": "",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    checks = {
        item["checkItem"]: item
        for item in client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]["riskCheckResults"]
    }
    assert checks["BLACKLIST"]["checkResult"] == "FAIL"
    assert "违禁词" in checks["BLACKLIST"]["detail"]
    assert checks["ACCOUNT_STATUS"]["detail"] == "账号使用中"
    assert checks["CERT_VALID"]["detail"]
    assert checks["DEVICE_OWNER"]["detail"] == "设备归属正常"
    assert checks["BALANCE"]["detail"] == "话费余额正常"
