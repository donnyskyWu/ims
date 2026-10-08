"""PERF-001 指标集：1151 编码唯一、1152 得分规则、1153 竞品锁定、1154 权重合计。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COMPETE = "COMPETE_SUBMIT_RATE"
LINEAR_OK = {
    "ruleType": "LINEAR",
    "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 100},
}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def create_metric(auth: dict, code: str, weight: float, score_rule: dict | None = None, status: str = "ENABLED"):
    return client.post(
        "/admin-api/ims/perf/metric",
        headers=auth,
        json={
            "metricCode": code,
            "metricName": code,
            "dataSource": "MANUAL",
            "weight": weight,
            "scoreRule": score_rule or LINEAR_OK,
            "status": status,
        },
    )


def test_metric_code_score_rule_and_compete_lock():
    auth = headers()
    listed = client.get("/admin-api/ims/perf/metric/list", headers=auth)
    assert listed.json()["code"] == 0
    compete = next(row for row in listed.json()["data"]["list"] if row["metricCode"] == COMPETE)
    assert compete["status"] == "DISABLED"
    assert "BR-110" in compete["enableNote"]
    assert compete["version"] == 1

    created = create_metric(auth, "TRAIN_FINISH_RATE", 60)
    assert created.json()["code"] == 0
    assert created.json()["data"]["metricCode"] == "TRAIN_FINISH_RATE"
    assert created.json()["data"]["status"] == "ENABLED"
    metric_id = created.json()["data"]["id"]

    dup = create_metric(auth, "TRAIN_FINISH_RATE", 10)
    assert dup.json()["code"] == 1151
    assert dup.json()["msg"] == "指标编码已存在"

    overlap = create_metric(
        auth,
        "OVERLAP_RATE",
        10,
        {
            "ruleType": "SEGMENT",
            "segments": [
                {"minValue": 0, "maxValue": 80, "score": 40},
                {"minValue": 50, "maxValue": 100, "score": 80},
            ],
        },
    )
    assert overlap.json()["code"] == 1152
    assert "重叠" in overlap.json()["msg"]

    out_of_range = create_metric(
        auth,
        "SCORE_OVERFLOW",
        10,
        {
            "ruleType": "SEGMENT",
            "segments": [{"minValue": 0, "maxValue": 100, "score": 100.01}],
        },
    )
    assert out_of_range.json()["code"] == 1152
    assert "越界" in out_of_range.json()["msg"]

    negative = create_metric(
        auth,
        "SCORE_NEGATIVE",
        10,
        {"ruleType": "LINEAR", "linear": {"minMetric": 0, "maxMetric": 100, "minScore": -1, "maxScore": 100}},
    )
    assert negative.json()["code"] == 1152

    adjacent = create_metric(
        auth,
        "ADJACENT_BAND",
        10,
        {
            "ruleType": "SEGMENT",
            "segments": [
                {"minValue": 0, "maxValue": 50, "score": 40},
                {"minValue": 50, "maxValue": 100, "score": 100},
            ],
        },
    )
    assert adjacent.json()["code"] == 0

    enabled = client.put(
        f"/admin-api/ims/perf/metric/{compete['id']}",
        headers=auth,
        json={
            "metricCode": COMPETE,
            "metricName": "竞品分析提交率",
            "dataSource": "MANUAL",
            "weight": 0,
            "scoreRule": LINEAR_OK,
            "status": "ENABLED",
        },
    )
    assert enabled.json()["code"] == 1153
    assert "BR-110" in enabled.json()["msg"]

    created_enabled = create_metric(auth, COMPETE, 0, status="ENABLED")
    assert created_enabled.json()["code"] == 1153

    removed = client.delete(f"/admin-api/ims/perf/metric/{compete['id']}", headers=auth)
    assert removed.json()["code"] == 1153

    again = client.get("/admin-api/ims/perf/metric/list", headers=auth, params={"metricName": "竞品分析提交率"})
    locked = next(row for row in again.json()["data"]["list"] if row["metricCode"] == COMPETE)
    assert locked["status"] == "DISABLED"
    assert locked["version"] == 1

    disabled = client.delete(f"/admin-api/ims/perf/metric/{metric_id}", headers=auth)
    assert disabled.json()["code"] == 0
    after = client.get("/admin-api/ims/perf/metric/list", headers=auth, params={"status": "DISABLED"})
    assert any(row["id"] == metric_id and row["status"] == "DISABLED" for row in after.json()["data"]["list"])


def test_position_bind_weight_total_boundaries():
    auth = headers()
    left = create_metric(auth, "GMV_RATE", 60)
    right = create_metric(auth, "LIVE_COUNT", 40)
    third = create_metric(auth, "EXTRA_RATE", 10)
    assert left.json()["code"] == 0
    left_id = left.json()["data"]["id"]
    right_id = right.json()["data"]["id"]
    third_id = third.json()["data"]["id"]

    def bind(items: list[dict]):
        return client.post(
            "/admin-api/ims/perf/metric/bind-position",
            headers=auth,
            json={"positionCode": "R5", "metricBindings": items},
        )

    low = bind(
        [
            {"metricId": left_id, "weightOverride": 49.99},
            {"metricId": right_id, "weightOverride": 50},
        ]
    )
    assert low.json()["code"] == 1154
    assert low.json()["data"]["totalWeight"] == 99.99
    assert "99.99%" in low.json()["msg"]

    high = bind(
        [
            {"metricId": left_id, "weightOverride": 50.01},
            {"metricId": right_id, "weightOverride": 50},
        ]
    )
    assert high.json()["code"] == 1154
    assert high.json()["data"]["totalWeight"] == 100.01

    ninety_nine = bind(
        [
            {"metricId": left_id, "weightOverride": 60},
            {"metricId": right_id, "weightOverride": 39},
        ]
    )
    assert ninety_nine.json()["code"] == 1154
    assert "99.00%" in ninety_nine.json()["msg"]

    one_oh_one = bind(
        [
            {"metricId": left_id, "weightOverride": 60},
            {"metricId": right_id, "weightOverride": 41},
        ]
    )
    assert one_oh_one.json()["code"] == 1154
    assert "101.00%" in one_oh_one.json()["msg"]

    exact = bind(
        [
            {"metricId": left_id, "weightOverride": 33.33},
            {"metricId": right_id, "weightOverride": 33.33},
            {"metricId": third_id, "weightOverride": 33.34},
        ]
    )
    body = exact.json()
    assert body["code"] == 0
    assert body["data"]["boundCount"] == 3
    assert body["data"]["totalWeight"] == 100
    assert body["data"]["positionCode"] == "R5"

    by_global = bind([{"metricId": left_id}, {"metricId": right_id}])
    assert by_global.json()["code"] == 0
    assert by_global.json()["data"]["boundCount"] == 2
    assert by_global.json()["data"]["totalWeight"] == 100

    dup = bind(
        [
            {"metricId": left_id, "weightOverride": 50},
            {"metricId": left_id, "weightOverride": 50},
        ]
    )
    assert dup.json()["code"] == 1001
