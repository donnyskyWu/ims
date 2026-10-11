import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login() -> dict:
    res = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert res.json()["code"] == 0, res.json()
    return {"Authorization": f"Bearer {res.json()['data']['accessToken']}"}


def test_create_role_required_unique_and_listed():
    headers = login()
    empty = client.post("/admin-api/ims/system/role", headers=headers, json={})
    assert empty.json()["code"] == 1001
    assert empty.json()["msg"] == "请先完成必填项"
    assert empty.json()["data"]["roleName"] == "必填项，请填写"
    assert empty.json()["data"]["roleKey"] == "必填项，请填写"
    created = client.post(
        "/admin-api/ims/system/role",
        headers=headers,
        json={
            "roleName": "TC-行政管理员",
            "roleKey": "tc_r2",
            "dataScope": "ALL",
            "dingtalkPosition": "行政岗",
            "remark": "功能测试",
        },
    )
    assert created.json()["code"] == 0, created.json()
    body = created.json()["data"]
    assert body["roleName"] == "TC-行政管理员"
    assert body["roleKey"] == "tc_r2"
    assert body["dataScope"] == "ALL"
    assert body["dingtalkPosition"] == "行政岗"
    assert body["remark"] == "功能测试"
    assert body["source"] == "MANUAL"
    assert body["status"] == "ENABLED"
    assert body["menuIds"] == []
    duplicate = client.post(
        "/admin-api/ims/system/role",
        headers=headers,
        json={"roleName": "另一个", "roleKey": "tc_r2"},
    )
    assert duplicate.json()["code"] == 1001
    assert duplicate.json()["msg"] == "角色编码已存在"
    listed = client.get("/admin-api/ims/system/role/list", headers=headers).json()["data"]
    row = next(item for item in listed if item["roleKey"] == "tc_r2")
    assert row["roleName"] == "TC-行政管理员"
    assert row["source"] == "MANUAL"
    assert row["status"] == "ENABLED"
    bad_scope = client.post(
        "/admin-api/ims/system/role",
        headers=headers,
        json={"roleName": "坏范围", "roleKey": "tc_bad_scope", "dataScope": "DEPT_AND_CHILD"},
    )
    assert bad_scope.json()["code"] == 1008
