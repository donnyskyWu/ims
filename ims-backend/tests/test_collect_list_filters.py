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


def test_keyword_and_account_collect_filter_and_task_running_empty():
    auth = headers()
    stamp = "筛213"

    on_kw = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "keyword": f"{stamp}-开",
            "matchType": "CONTAINS",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    assert on_kw.json()["code"] == 0
    off_kw = client.post(
        "/admin-api/ims/collect/external/keyword",
        headers=auth,
        json={
            "platformType": "KUAISHOU",
            "keyword": f"{stamp}-关",
            "matchType": "EXACT",
            "collectEnabled": False,
            "status": "DISABLED",
        },
    )
    assert off_kw.json()["code"] == 0

    only_on = client.get(
        "/admin-api/ims/collect/external/keyword/page",
        headers=auth,
        params={"keyword": stamp, "collectEnabled": "1"},
    )
    assert only_on.json()["code"] == 0
    on_names = [row["keyword"] for row in only_on.json()["data"]["list"]]
    assert on_names == [f"{stamp}-开"]

    only_off = client.get(
        "/admin-api/ims/collect/external/keyword/page",
        headers=auth,
        params={"keyword": stamp, "collectEnabled": "0", "status": "DISABLED"},
    )
    off_names = [row["keyword"] for row in only_off.json()["data"]["list"]]
    assert off_names == [f"{stamp}-关"]
    assert only_off.json()["data"]["list"][0]["collectEnabled"] is False

    on_acc = client.post(
        "/admin-api/ims/collect/external/account",
        headers=auth,
        json={
            "configName": f"{stamp}号开",
            "platformType": "DOUYIN",
            "accountIdentifier": f"{stamp}-id-on",
            "collectEnabled": True,
            "status": "ENABLED",
        },
    )
    assert on_acc.json()["code"] == 0
    off_acc = client.post(
        "/admin-api/ims/collect/external/account",
        headers=auth,
        json={
            "configName": f"{stamp}号关",
            "platformType": "XIAOHONGSHU",
            "accountIdentifier": f"{stamp}-id-off",
            "collectEnabled": False,
            "status": "ENABLED",
        },
    )
    assert off_acc.json()["code"] == 0

    acc_off = client.get(
        "/admin-api/ims/collect/external/account/page",
        headers=auth,
        params={"configName": stamp, "collectEnabled": "0"},
    )
    assert [row["configName"] for row in acc_off.json()["data"]["list"]] == [f"{stamp}号关"]
    acc_miss = client.get(
        "/admin-api/ims/collect/external/account/page",
        headers=auth,
        params={"configName": f"{stamp}-没有", "platformType": "DOUYIN"},
    )
    assert acc_miss.json()["data"]["total"] == 0

    ensured = client.post("/admin-api/ims/collect/task/ensure-external-unified", headers=auth)
    assert ensured.json()["code"] == 0
    assert ensured.json()["data"]["platformType"] == "MULTI"
    assert ensured.json()["data"]["status"] == "ENABLED"

    running = client.get("/admin-api/ims/collect/task/page", headers=auth, params={"status": "RUNNING"})
    assert running.json()["code"] == 0
    assert running.json()["data"]["total"] == 0

    multi = client.get("/admin-api/ims/collect/task/page", headers=auth, params={"platformType": "MULTI"})
    multi_names = [row["taskName"] for row in multi.json()["data"]["list"]]
    assert "外部竞品统一任务" in multi_names
    assert all(row["status"] != "RUNNING" for row in multi.json()["data"]["list"])

    internal = client.get(
        "/admin-api/ims/collect/task/page",
        headers=auth,
        params={"platformType": "MULTI", "method": "INTERNAL"},
    )
    assert internal.json()["data"]["total"] == 0
