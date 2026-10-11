import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_external_account_keyword_and_threshold():
    auth = headers()
    acc = client.post(
        "/admin-api/ims/collect/external/account",
        headers=auth,
        json={
            "configName": "竞品抖音 A",
            "platformType": "DOUYIN",
            "accountIdentifier": "dy_comp_a",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    assert acc.json()["code"] == 0
    acc_id = acc.json()["data"]["id"]
    page = client.get("/admin-api/ims/collect/external/account/page", headers=auth, params={"configName": "竞品"})
    assert page.json()["data"]["total"] == 1

    kw = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={"platformType": "DOUYIN", "keyword": "神鱼", "matchType": "CONTAINS", "status": "ENABLED"},
    )
    assert kw.json()["code"] == 0
    same = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={"platformType": "DOUYIN", "keyword": "神鱼", "matchType": "CONTAINS", "status": "ENABLED"},
    )
    assert same.json()["code"] == 1001
    assert "已存在" in same.json()["msg"]
    other_platform = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={"platformType": "KUAISHOU", "keyword": "神鱼", "matchType": "CONTAINS", "status": "ENABLED"},
    )
    assert other_platform.json()["code"] == 0
    missed = client.get(
        "/admin-api/ims/collect/external/keyword/page",
        headers=auth,
        params={"keyword": "不存在的竞品词", "status": "DISABLED"},
    )
    assert missed.json()["code"] == 0
    assert missed.json()["data"]["total"] == 0

    missing_cat = client.get("/admin-api/ims/collect/threshold/list", headers=auth)
    assert missing_cat.json()["code"] == 1001

    th = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "ALERT",
            "platformType": "DOUYIN",
            "metricName": "collect_fail_rate",
            "thresholdType": "PERCENT",
            "compareOperator": "GT",
            "thresholdValue": "30",
            "status": "ENABLED",
        },
    )
    assert th.json()["code"] == 0
    listed = client.get(
        "/admin-api/ims/collect/threshold/list",
        headers=auth,
        params={"thresholdCategory": "ALERT"},
    )
    assert len(listed.json()["data"]["list"]) == 1

    client.delete(f"/admin-api/ims/collect/external/account/{acc_id}", headers=auth)


def test_metadata_entity_fields_and_bi0_read():
    auth = headers()
    unmapped = client.get("/admin-api/ims/collect/metadata/unmapped-tables", headers=auth)
    assert unmapped.json()["code"] == 0
    table_list = unmapped.json()["data"]["list"]
    assert any(t["tableName"] == "ims_sys_user" for t in table_list)
    assert len(table_list) > 2

    bad_cols = client.get(
        "/admin-api/ims/collect/metadata/table-columns",
        headers=auth,
        params={"tableName": "ims_sys_user;drop"},
    )
    assert bad_cols.json()["code"] == 1001

    cols = client.get(
        "/admin-api/ims/collect/metadata/table-columns",
        headers=auth,
        params={"tableName": "ims_sys_user"},
    )
    assert cols.json()["code"] == 0
    assert len(cols.json()["data"]["list"]) > 0
    assert any(c["columnName"] == "username" for c in cols.json()["data"]["list"])

    missing_table = client.get(
        "/admin-api/ims/collect/metadata/table-columns",
        headers=auth,
        params={"tableName": "ims_table_not_exists_xyz"},
    )
    assert missing_table.json()["code"] == 0
    assert missing_table.json()["data"]["list"] == []

    created = client.post(
        "/admin-api/ims/collect/metadata/create",
        headers=auth,
        json={
            "entityCode": "SYS_USER_META",
            "entityName": "系统用户",
            "tableName": "ims_sys_user",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    entity_id = created.json()["data"]["id"]

    saved = client.put(
        f"/admin-api/ims/collect/metadata/{entity_id}/fields",
        headers=auth,
        json={
            "fields": [
                {
                    "fieldCode": "username",
                    "columnName": "username",
                    "displayName": "登录名",
                    "queryConditionType": "LIKE",
                }
            ]
        },
    )
    assert saved.json()["code"] == 0
    assert len(saved.json()["data"]["fields"]) == 1

    read = client.get("/admin-api/ims/collect/metadata/entity/SYS_USER_META/fields", headers=auth)
    assert read.json()["code"] == 0
    assert read.json()["data"]["entityCode"] == "SYS_USER_META"

    remapped = client.get("/admin-api/ims/collect/metadata/unmapped-tables", headers=auth)
    assert all(t["tableName"] != "ims_sys_user" for t in remapped.json()["data"]["list"])

    missing = client.get("/admin-api/ims/collect/metadata/entity/UNKNOWN/fields", headers=auth)
    assert missing.json()["code"] == 1261
