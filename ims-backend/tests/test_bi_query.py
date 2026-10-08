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


def seed_platform_account_entity(auth: dict) -> None:
    client.post(
        "/admin-api/ims/collect/metadata/create",
        headers=auth,
        json={
            "entityCode": "PLATFORM_ACCOUNT",
            "entityName": "平台账号",
            "tableName": "oa_platform_account",
            "status": "ENABLED",
        },
    )
    listed = client.get("/admin-api/ims/collect/metadata/list", headers=auth)
    entity_id = listed.json()["data"]["list"][0]["id"]
    client.put(
        f"/admin-api/ims/collect/metadata/{entity_id}/fields",
        headers=auth,
        json={
            "fields": [
                {
                    "fieldCode": "account_no",
                    "columnName": "account_no",
                    "displayName": "账号编号",
                    "queryConditionType": "LIKE",
                },
                {
                    "fieldCode": "platform_type",
                    "columnName": "platform_type",
                    "displayName": "平台",
                    "queryConditionType": "EQ",
                },
            ]
        },
    )


def test_bi_query_run_mapped_entity():
    auth = headers()
    seed_platform_account_entity(auth)

    saved = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "账号探查",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {
                "selectFields": ["account_no", "platform_type"],
                "conditions": [{"fieldCode": "platform_type", "operator": "EQ", "value": "DOUYIN"}],
                "limit": 50,
            },
        },
    )
    assert saved.json()["code"] == 0
    qid = saved.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/bi/query/{qid}/run", headers=auth)
    assert run.json()["code"] == 0
    assert run.json()["data"]["columns"] == ["account_no", "platform_type"]
    assert "sql" in run.json()["data"]
    assert "`account_no`" in run.json()["data"]["sql"]


def test_bi_query_unmapped_entity_1261():
    auth = headers()
    bad = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "未映射",
            "entityCode": "UNKNOWN_ENTITY",
            "config": {"selectFields": ["x"], "limit": 10},
        },
    )
    assert bad.json()["code"] == 1261


def test_bi_query_save_and_publish():
    auth = headers()
    seed_platform_account_entity(auth)
    saved = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "发布用例",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {"selectFields": ["account_no"], "limit": 10},
        },
    )
    qid = saved.json()["data"]["id"]
    pub = client.put(f"/admin-api/ims/bi/query/{qid}/publish", headers=auth)
    assert pub.json()["code"] == 0
    assert pub.json()["data"]["status"] == "PUBLISHED"
    page = client.get("/admin-api/ims/bi/query/page", headers=auth, params={"status": "PUBLISHED"})
    assert page.json()["data"]["total"] >= 1
