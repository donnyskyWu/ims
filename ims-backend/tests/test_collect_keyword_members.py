import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_keyword_collect_flag_joins_external_members_and_retry_hint():
    auth = headers()
    stamp = "神鱼关键词尾"
    created = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "keyword": stamp,
            "matchType": "CONTAINS",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    body = created.json()["data"]
    assert body["collectEnabled"] is True
    assert body["updatedAt"]
    keyword_id = body["id"]

    off = client.put(
        f"/admin-api/ims/collect/external/keyword/{keyword_id}",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "keyword": stamp,
            "matchType": "FUZZY",
            "collectEnabled": False,
            "status": "ENABLED",
        },
    )
    assert off.json()["code"] == 0
    assert off.json()["data"]["collectEnabled"] is False
    assert off.json()["data"]["matchType"] == "FUZZY"

    account = client.post(
        "/admin-api/ims/collect/external/account",
        headers=auth,
        json={
            "configName": "尾部竞品号",
            "platformType": "KUAISHOU",
            "accountIdentifier": "ks_tail_1",
            "collectEnabled": False,
            "status": "ENABLED",
        },
    )
    assert account.json()["code"] == 0

    ensured = client.post("/admin-api/ims/collect/task/ensure-external-unified", headers=auth)
    assert ensured.json()["code"] == 0
    task_id = ensured.json()["data"]["id"]
    assert ensured.json()["data"]["isExternalUnified"] is True

    hidden = client.get(f"/admin-api/ims/collect/task/{task_id}/members", headers=auth)
    assert hidden.json()["code"] == 0
    names = [item["memberName"] for item in hidden.json()["data"]["list"]]
    assert f"关键词「{stamp}」" not in names
    assert "尾部竞品号" not in names

    client.put(
        f"/admin-api/ims/collect/external/keyword/{keyword_id}",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "keyword": stamp,
            "matchType": "CONTAINS",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    client.put(
        f"/admin-api/ims/collect/external/account/{account.json()['data']['id']}",
        headers=auth,
        json={
            "configName": "尾部竞品号",
            "platformType": "KUAISHOU",
            "accountIdentifier": "ks_tail_1",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    shown = client.get(f"/admin-api/ims/collect/task/{task_id}/members", headers=auth).json()["data"]["list"]
    kinds = {(item["memberKind"], item["memberName"], item["platformType"]) for item in shown}
    assert ("KEYWORD", f"关键词「{stamp}」", "DOUYIN") in kinds
    assert ("ACCOUNT", "尾部竞品号", "KUAISHOU") in kinds

    listed = client.get("/admin-api/ims/collect/task/page", headers=auth, params={"method": "EXTERNAL"})
    external = next(row for row in listed.json()["data"]["list"] if row["id"] == task_id)
    assert external["memberCount"] == len(shown)

    from tests.test_collect import seed_account

    account_id = seed_account(bound=True)
    single = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "单账号不可看外部成员",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
            "status": "ENABLED",
        },
    )
    assert single.json()["code"] == 0
    denied = client.get(f"/admin-api/ims/collect/task/{single.json()['data']['id']}/members", headers=auth)
    assert denied.json()["code"] == 1001

    page = client.get(
        "/admin-api/ims/collect/external/keyword/page",
        headers=auth,
        params={"keyword": stamp, "status": "ENABLED"},
    )
    assert page.json()["data"]["total"] == 1
    assert page.json()["data"]["list"][0]["collectEnabled"] is True


def test_failed_log_retry_hint_without_retry_action():
    auth = headers()
    from tests.test_collect import seed_account

    account_id = seed_account(bound=False)
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "重试文案任务",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    task_id = created.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert run.json()["code"] == 0
    log_id = run.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth).json()["data"]
    assert detail["status"] == "FAILED"
    assert detail["retryCount"] == 0
    assert detail["retryHint"] == "尚未重试"
