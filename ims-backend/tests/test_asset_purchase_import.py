"""#68 · E2E-S5-01 / UT-ASSET-003-02：采购入台账批量导入，行级错误，部分成功不回滚。"""

import json
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


def _import(auth: dict, text: str, name: str = "purchase.csv"):
    return client.post(
        "/admin-api/ims/asset/ledger/import",
        headers=auth,
        files={"file": (name, text.encode("utf-8"), "text/csv")},
    )


def _codes(auth: dict) -> dict[str, dict]:
    page = client.get("/admin-api/ims/asset/ledger/page", headers=auth, params={"pageNo": 1, "pageSize": 100})
    body = page.json()
    assert body["code"] == 0, body
    return {item["assetCode"]: item for item in body["data"]["list"]}


def test_purchase_import_partial_success_keeps_good_rows_and_locates_errors():
    auth = headers()
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": "AS-PY-68-OLD", "assetName": "已在台账", "assetType": "OFFICE", "purchaseDate": "2026-10-01"},
    )
    assert created.json()["code"] == 0, created.json()

    csv = "\n".join(
        [
            "assetCode,assetName,assetType,spec,purchaseDate",
            "AS-PY-68-A,采购笔记本,OFFICE,14寸,2026-10-08",
            "AS-PY-68-BAD,,OFFICE,坏行,2026-13-01",
            "AS-PY-68-A,重复编号,OFFICE,冲突,2026-10-08",
            "AS-PY-68-OLD,撞库,OFFICE,已有,2026-10-08",
            "AS-PY-68-DATE,日期坏了,OFFICE,行,2026-02-31",
            "AS-PY-68-TYPE,类型坏了,NO_TYPE,行,2026-10-08",
            "AS-PY-68-C,采购显示器,OFFICE,27寸,2026-10-08",
        ]
    )
    imported = _import(auth, csv)
    body = imported.json()
    assert body["code"] == 0, body
    data = body["data"]
    assert data["partial"] is True
    assert data["successCount"] == 2
    assert data["failCount"] == 5
    assert data["total"] == 7
    assert data["batchNo"].startswith("PB")
    by_row = {item["rowNo"]: item for item in data["errors"]}
    assert by_row[3]["field"] == "assetName"
    assert by_row[3]["code"] == 1001
    assert by_row[4]["field"] == "assetCode"
    assert by_row[4]["code"] == 1012
    assert by_row[5]["field"] == "assetCode"
    assert by_row[5]["code"] == 1012
    assert by_row[6]["field"] == "purchaseDate"
    assert by_row[7]["field"] == "assetType"
    assert by_row[7]["code"] == 1503
    codes = {item["assetCode"] for item in data["imported"]}
    assert codes == {"AS-PY-68-A", "AS-PY-68-C"}

    ledger = _codes(auth)
    assert ledger["AS-PY-68-A"]["status"] == "PENDING_REVIEW"
    assert ledger["AS-PY-68-A"]["purchaseDate"] == "2026-10-08"
    assert ledger["AS-PY-68-A"]["purchaseBatchNo"] == data["batchNo"]
    assert ledger["AS-PY-68-C"]["purchaseBatchNo"] == data["batchNo"]
    assert "AS-PY-68-BAD" not in ledger
    assert "AS-PY-68-DATE" not in ledger
    assert "AS-PY-68-TYPE" not in ledger
    assert ledger["AS-PY-68-OLD"]["purchaseBatchNo"] == ""

    detail = client.get(f"/admin-api/ims/asset/ledger/{ledger['AS-PY-68-A']['id']}", headers=auth)
    timeline = detail.json()["data"]["timeline"]
    assert timeline[0]["eventType"] == "REGISTER"
    assert timeline[0]["remark"] == "采购入台账"

    from app.core import SessionLocal
    from app.models import AssetPurchaseBatch

    db = SessionLocal()
    try:
        batch = db.query(AssetPurchaseBatch).filter(AssetPurchaseBatch.batch_no == data["batchNo"]).one()
        stored = json.loads(batch.error_detail)
        assert batch.partial == 1
        assert batch.success_count == 2
        assert any(item["rowNo"] == 3 and item["field"] == "assetName" for item in stored)
    finally:
        db.close()


def test_purchase_import_rejects_empty_file_and_all_fail_inserts_nothing():
    auth = headers()
    empty = _import(auth, "")
    assert empty.json()["code"] == 1001

    missing = _import(auth, "assetCode,spec\nAS-X,仅规格\n")
    assert missing.json()["code"] == 1001
    assert "采购日期" in missing.json()["msg"] or "资产名称" in missing.json()["msg"]

    before = set(_codes(auth))
    failed = _import(
        auth,
        "\n".join(
            [
                "资产编号,资产名称,资产类型,规格,采购日期",
                "AS-PY-68-NONE,,OFFICE,无名称,2026-10-08",
                "AS-PY-68-BAD-DATE,有名称,OFFICE,坏日期,不是日期",
            ]
        ),
    )
    body = failed.json()
    assert body["code"] == 0, body
    assert body["data"]["partial"] is False
    assert body["data"]["successCount"] == 0
    assert body["data"]["failCount"] == 2
    assert {item["field"] for item in body["data"]["errors"]} == {"assetName", "purchaseDate"}
    after = set(_codes(auth))
    assert after == before
