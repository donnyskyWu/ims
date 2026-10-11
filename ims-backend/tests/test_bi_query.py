import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, SessionLocal, engine
from app.main import app, init_db
from app.models import Notify
from app.ops_db import OpsBase, ops_engine

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_platform_account_entity(auth: dict) -> None:
    created = client.post(
        "/admin-api/ims/collect/metadata/create",
        headers=auth,
        json={
            "entityCode": "SYS_ROLE_BI",
            "entityName": "系统角色",
            "tableName": "ims_sys_role",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    entity_id = created.json()["data"]["id"]
    client.put(
        f"/admin-api/ims/collect/metadata/{entity_id}/fields",
        headers=auth,
        json={
            "fields": [
                {
                    "fieldCode": "role_key",
                    "columnName": "role_key",
                    "displayName": "角色标识",
                    "queryConditionType": "LIKE",
                },
                {
                    "fieldCode": "role_name",
                    "columnName": "role_name",
                    "displayName": "角色名称",
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
            "entityCode": "SYS_ROLE_BI",
            "config": {
                "selectFields": ["role_key", "role_name"],
                "conditions": [{"fieldCode": "role_key", "operator": "LIKE", "value": "admin"}],
                "limit": 50,
            },
        },
    )
    assert saved.json()["code"] == 0
    qid = saved.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/bi/query/{qid}/run", headers=auth)
    assert run.json()["code"] == 0
    assert run.json()["data"]["columns"] == ["role_key", "role_name"]
    assert "sql" in run.json()["data"]
    assert "`ims_sys_role`" in run.json()["data"]["sql"]


def seed_sys_user_entity(auth: dict) -> None:
    created = client.post(
        "/admin-api/ims/collect/metadata/create",
        headers=auth,
        json={
            "entityCode": "SYS_USER",
            "entityName": "系统用户",
            "tableName": "ims_sys_user",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    entity_id = created.json()["data"]["id"]
    client.put(
        f"/admin-api/ims/collect/metadata/{entity_id}/fields",
        headers=auth,
        json={
            "fields": [
                {
                    "fieldCode": "username",
                    "columnName": "username",
                    "displayName": "登录名",
                    "queryConditionType": "LIKE",
                },
                {
                    "fieldCode": "nickname",
                    "columnName": "nickname",
                    "displayName": "昵称",
                    "queryConditionType": "EQ",
                },
            ]
        },
    )


def test_bi_query_run_ims_sys_user():
    auth = headers()
    seed_sys_user_entity(auth)
    saved = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "用户探查",
            "entityCode": "SYS_USER",
            "config": {
                "selectFields": ["username", "nickname"],
                "conditions": [{"fieldCode": "username", "operator": "EQ", "value": "admin"}],
                "limit": 20,
            },
        },
    )
    assert saved.json()["code"] == 0
    qid = saved.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/bi/query/{qid}/run", headers=auth)
    assert run.json()["code"] == 0, run.json()
    assert run.json()["data"]["columns"] == ["username", "nickname"]
    assert "`ims_sys_user`" in run.json()["data"]["sql"]
    assert len(run.json()["data"]["rows"]) >= 1


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


def test_bi_query_run_pagination_and_cost():
    auth = headers()
    seed_sys_user_entity(auth)
    saved = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "分页探查",
            "entityCode": "SYS_USER",
            "config": {
                "selectFields": ["username", "nickname"],
                "conditions": [],
                "limit": 50,
            },
        },
    )
    assert saved.json()["code"] == 0
    qid = saved.json()["data"]["id"]
    run = client.post(
        f"/admin-api/ims/bi/query/{qid}/run",
        headers=auth,
        json={"pageNo": 1, "pageSize": 1},
    )
    assert run.json()["code"] == 0, run.json()
    data = run.json()["data"]
    assert data["pageNo"] == 1
    assert data["pageSize"] == 1
    assert "queryCostMs" in data
    assert len(data["rows"]) <= 1
    assert data["total"] >= len(data["rows"])


def test_bi_query_sources_and_agg_join_preview():
    auth = headers()
    sources = client.get("/admin-api/ims/bi/query/sources", headers=auth)
    assert sources.json()["code"] == 0
    codes = {row["entityCode"] for row in sources.json()["data"]["list"]}
    assert "IP_GROUP" in codes
    assert "CONTENT_METRIC" in codes
    ip = next(row for row in sources.json()["data"]["list"] if row["entityCode"] == "IP_GROUP")
    assert any(j["table"] == "oa_internal_content" for j in ip["joins"])

    preview = client.post(
        "/admin-api/ims/bi/query/preview",
        headers=auth,
        json={
            "entityCode": "IP_GROUP",
            "config": {
                "selectFields": ["group_name"],
                "aggFunc": "SUM",
                "aggField": "play_count",
                "groupBy": ["group_name"],
                "joinTable": "oa_internal_content",
                "conditions": [{"fieldCode": "group_name", "operator": "EQ", "value": "电竞一组"}],
                "limit": 100,
            },
        },
    )
    assert preview.json()["code"] == 0, preview.json()
    sql = preview.json()["data"]["sql"]
    assert "SUM(" in sql
    assert "GROUP BY" in sql
    assert "`oa_ip_group`" in sql
    assert "`oa_internal_content`" in sql
    assert ":tenant_id" in sql
    assert ":p0" in sql
    assert "电竞一组" not in sql


def test_bi_query_limit_and_timeout_export():
    auth = headers()
    client.get("/admin-api/ims/bi/query/sources", headers=auth)
    too_big = client.post(
        "/admin-api/ims/bi/query/run",
        headers=auth,
        json={"entityCode": "IP_GROUP", "config": {"selectFields": ["group_name"], "limit": 100001}},
    )
    assert too_big.json()["code"] == 1001
    assert "100000" in too_big.json()["msg"]
    os.environ["IMS_BI_QUERY_TIMEOUT_MS"] = "0"
    try:
        timed = client.post(
            "/admin-api/ims/bi/query/run",
            headers=auth,
            json={"entityCode": "IP_GROUP", "config": {"selectFields": ["group_name"], "limit": 100000}},
        )
        body = timed.json()
        assert body["code"] == 1262, body
        assert body["msg"] == "导出任务已提交"
        task_id = body["data"]["exportTaskId"]
        db = SessionLocal()
        try:
            note = db.query(Notify).filter(Notify.event_type == "BI_QUERY_EXPORT", Notify.biz_key == task_id).one()
            assert note.deleted == 0
        finally:
            db.close()
    finally:
        os.environ.pop("IMS_BI_QUERY_TIMEOUT_MS", None)


def test_bi_query_adhoc_run_does_not_create_row():
    auth = headers()
    client.get("/admin-api/ims/bi/query/sources", headers=auth)
    before = client.get("/admin-api/ims/bi/query/page", headers=auth, params={"pageNo": 1, "pageSize": 1})
    before_total = before.json()["data"]["total"]
    run = client.post(
        "/admin-api/ims/bi/query/run",
        headers=auth,
        json={
            "entityCode": "IP_GROUP",
            "config": {"selectFields": ["group_name"], "limit": 10},
            "pageNo": 1,
            "pageSize": 5,
        },
    )
    assert run.json()["code"] == 0, run.json()
    assert "queryCostMs" in run.json()["data"]
    assert "临时查询" not in str(run.json()["data"])
    after = client.get("/admin-api/ims/bi/query/page", headers=auth, params={"pageNo": 1, "pageSize": 1})
    assert after.json()["data"]["total"] == before_total


def test_bi_query_save_and_publish():
    auth = headers()
    seed_platform_account_entity(auth)
    saved = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "发布用例",
            "entityCode": "SYS_ROLE_BI",
            "config": {"selectFields": ["role_key"], "limit": 10},
        },
    )
    qid = saved.json()["data"]["id"]
    pub = client.put(f"/admin-api/ims/bi/query/{qid}/publish", headers=auth)
    assert pub.json()["code"] == 0
    assert pub.json()["data"]["status"] == "PUBLISHED"
    page = client.get("/admin-api/ims/bi/query/page", headers=auth, params={"status": "PUBLISHED"})
    assert page.json()["data"]["total"] >= 1
