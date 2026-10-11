"""BUG-C039：指标表单字段、编码、名称长度、生成公式、预览、编辑与停用。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_tc_r9_metric_form_code_length_formula_and_disable():
    auth = headers()
    long_name = "测" * 51
    rejected = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": long_name, "metricCode": "TC_LONG", "metricType": "BASIC"},
    )
    assert rejected.json()["code"] == 1001
    assert "50" in rejected.json()["msg"]

    generated = client.post(
        "/admin-api/ims/bi/metric/formula/generate",
        headers=auth,
        json={
            "dataSource": "oa_content_metric",
            "calcMethod": "SUM",
            "calcField": "play_count",
            "summaryField": "ip_group_name",
            "conditions": [{"field": "stat_date", "op": "介于", "value": "", "param": True}],
        },
    )
    sql = generated.json()["data"]["formula"]
    assert generated.json()["code"] == 0
    assert sql.upper().startswith("SELECT")
    assert "DELETE" not in sql.upper()
    assert ":p_stat_date" in sql

    preview = client.post(
        "/admin-api/ims/bi/metric/preview-draft",
        headers=auth,
        json={"formula": sql},
    )
    assert preview.json()["code"] == 0
    assert len(preview.json()["data"]["rows"]) >= 1
    assert "未接 DW" not in str(preview.json()["data"])

    poisoned = client.post(
        "/admin-api/ims/bi/metric/preview-draft",
        headers=auth,
        json={"formula": "DELETE FROM x"},
    )
    assert poisoned.json()["code"] == 1192

    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={
            "metricName": "TC播放量",
            "metricCode": "TC_PLAY",
            "metricType": "BASIC",
            "category": "内容表现",
            "unit": "次",
            "calcFreq": "DAILY",
            "dataSource": "oa_content_metric",
            "calcMethod": "SUM",
            "calcField": "play_count",
            "summaryField": "ip_group_name",
            "formula": sql,
            "conditions": [{"field": "stat_date", "op": "介于", "value": "", "param": True}],
        },
    )
    body = created.json()
    assert body["code"] == 0
    mid = body["data"]["id"]
    assert body["data"]["metricCode"] == "TC_PLAY"
    assert body["data"]["unit"] == "次"
    assert body["data"]["dataSource"] == "oa_content_metric"
    assert body["data"]["conditions"][0]["param"] is True

    dup = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "再来一个", "metricCode": "TC_PLAY", "metricType": "BASIC"},
    )
    assert dup.json()["code"] == 1001
    assert "编码已存在" in dup.json()["msg"]

    edited = client.put(
        f"/admin-api/ims/bi/metric/{mid}",
        headers=auth,
        json={"metricName": "TC播放量改", "unit": "次"},
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["metricName"] == "TC播放量改"

    disabled = client.put(f"/admin-api/ims/bi/metric/{mid}", headers=auth, json={"status": "DISABLED"})
    assert disabled.json()["code"] == 0
    fields = client.get("/admin-api/ims/bi/metric/fields", headers=auth)
    codes = [item["metricCode"] for item in fields.json()["data"]["fields"]]
    assert "TC_PLAY" not in codes
