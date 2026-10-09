"""#226 成本录入校验、更正原因长度、结账重复标记。不覆盖 #196 导出或 #207 筛选空态。"""

import uuid

from tests.test_fin import approved_session, client, confirm_cost_for_session, headers


def _body(**overrides) -> dict:
    body = {
        "commissionRate": 0.05,
        "adCost": 5000,
        "rechargeCost": 100,
        "fixedCost": 2000,
        "sampleCost": 500,
        "shareCostType": "MANUAL",
        "shareDaren": 3000,
        "shareRealname": 1000,
    }
    body.update(overrides)
    return body


def _post_cost(auth: dict, code: str, body: dict):
    return client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=body,
    )


def test_cost_entry_validation_and_repeat_period_close():
    auth = headers()
    code = approved_session(auth)

    zero = _post_cost(auth, code, _body(commissionRate=0))
    assert zero.json()["code"] == 1001
    assert zero.json()["msg"] == "佣金率须大于 0 且不超过 1"

    high = _post_cost(auth, code, _body(commissionRate=1.2))
    assert high.json()["code"] == 1001
    assert "佣金率" in high.json()["msg"]

    negative = _post_cost(auth, code, _body(adCost=-1))
    assert negative.json()["code"] == 1001
    assert negative.json()["msg"] == "金额不能为负"

    cents = _post_cost(auth, code, _body(sampleCost=1.239))
    assert cents.json()["code"] == 1001
    assert cents.json()["msg"] == "金额最多两位小数"

    edge = _post_cost(auth, code, _body(commissionRate=1, adCost=10.5))
    assert edge.json()["code"] == 0, edge.json()
    assert edge.json()["data"]["commissionRate"] == 1

    confirm_cost_for_session(auth, code)
    long_reason = "测" * 513
    corrected = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"correctionReason": long_reason, "corrected": _body()},
    )
    assert corrected.json()["code"] == 1001
    assert corrected.json()["msg"] == "更正原因不超过 512 字"

    blank = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"correctionReason": "   ", "corrected": _body()},
    )
    assert blank.json()["code"] == 1144
    assert blank.json()["msg"] == "更正原因必填"

    month = "2098-11"
    first = client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": month})
    assert first.json()["code"] == 0, first.json()
    assert first.json()["data"]["financeStatus"] == "LOCKED"
    assert first.json()["data"].get("repeated") is not True

    again = client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": month})
    assert again.json()["code"] == 0, again.json()
    assert again.json()["data"]["financeStatus"] == "LOCKED"
    assert again.json()["data"]["repeated"] is True
