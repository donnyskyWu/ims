"""#237 · 登记表单边角：名称/编号/规格长度、空编号自动生成、坏场次与坏日期。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_register_rejects_blank_name_long_fields_and_bad_session_before_insert():
    auth = headers()
    blank = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetName": "  ", "assetType": "OFFICE"},
    ).json()
    assert blank["code"] == 1001
    assert blank["msg"] == "资产名称必填"

    long_name = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-237-NAME", "assetName": "名" * 129, "assetType": "OFFICE"},
    ).json()
    assert long_name["code"] == 1001
    assert long_name["msg"] == "资产名称过长"

    long_code = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "C" * 65, "assetName": "编号过长", "assetType": "OFFICE"},
    ).json()
    assert long_code["code"] == 1001
    assert long_code["msg"] == "资产编号过长"

    long_spec = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-237-SPEC", "assetName": "规格过长", "assetType": "OFFICE", "spec": "规" * 129},
    ).json()
    assert long_spec["code"] == 1001
    assert long_spec["msg"] == "规格过长"

    bad_session = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-237-SES", "assetName": "坏场次", "assetType": "OFFICE", "sessionCode": "not-a-session"},
    ).json()
    assert bad_session["code"] == 1001
    assert bad_session["msg"] == "场次编号格式不正确"

    bad_date = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-237-DATE", "assetName": "坏日期", "assetType": "OFFICE", "purchaseDate": "2026-02-31"},
    ).json()
    assert bad_date["code"] == 1001
    assert "yyyy-MM-dd" in bad_date["msg"]

    listed = client.get(
        "/admin-api/ims/asset/ledger/page",
        headers=auth,
        params={"keyword": "AS-PY-237", "pageNo": 1, "pageSize": 20},
    ).json()
    assert listed["code"] == 0, listed
    assert listed["data"]["list"] == []


def test_register_keeps_full_spec_and_generates_code_when_blank():
    auth = headers()
    spec = "规" * 128
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetName": "  自动编号显示器  ", "assetType": "OFFICE", "spec": f"  {spec}  "},
    ).json()
    assert created["code"] == 0, created
    data = created["data"]
    assert data["assetCode"].startswith("AS")
    assert data["assetName"] == "自动编号显示器"
    assert data["spec"] == spec
    assert data["status"] == "PENDING_REVIEW"
    assert data["timeline"][0]["remark"] == "登记入台账"
