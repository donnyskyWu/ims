"""#149 · 资产台账列表筛选：责任人、待补关联、绑定账号数，并按当前筛选导出。"""

import os
import uuid
import zipfile
from io import BytesIO

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import AssetBind
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    page = client.get("/admin-api/ims/system/user/page", headers=auth, params={"pageNo": 1, "pageSize": 100}).json()
    for user in page["data"]["list"]:
        if user.get("username") == "admin":
            return int(user["id"])
    raise AssertionError(page)


def _account(account_no: str, holder_id: int) -> None:
    ops = ops_session()
    try:
        ops.add(
            PlatformAccount(
                account_no=account_no,
                account_name=account_no,
                platform_type="DOUYIN",
                holder_user_id=holder_id,
                status="IN_USE",
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()


def _create(auth: dict, code: str, **extra) -> dict:
    body = {"assetCode": code, "assetName": code, "assetType": "OFFICE", "spec": "筛选", **extra}
    return client.post("/admin-api/ims/asset/ledger", headers=auth, json=body).json()


def _page(auth: dict, **params) -> dict:
    listed = client.get("/admin-api/ims/corp/device/office/page", headers=auth, params={"pageSize": 50, **params}).json()
    assert listed["code"] == 0, listed
    return listed["data"]


def _by_code(data: dict) -> dict[str, dict]:
    return {item["assetCode"]: item for item in data["list"]}


def test_owner_status_and_link_gap_filters_count_active_binds():
    auth = headers()
    admin_id = _admin_id(auth)
    mark = uuid.uuid4().hex[:8]
    prefix = f"AS149{mark}"
    gap_code = f"{prefix}G"
    bound_code = f"{prefix}B"
    account_no = f"AC149{mark}"
    _account(account_no, admin_id)

    gap = _create(auth, gap_code)
    assert gap["code"] == 0, gap
    bound = _create(auth, bound_code, accountNo=account_no)
    assert bound["code"] == 0, bound
    assert bound["data"]["bindCount"] == 1
    assert bound["data"]["linkGap"] is True

    checked = client.post(
        f"/admin-api/ims/asset/ledger/{bound['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    assert checked["data"]["bindCount"] == 1
    assert checked["data"]["linkGap"] is False

    both = _page(auth, keyword=prefix)
    rows = _by_code(both)
    assert set(rows) >= {gap_code, bound_code}
    assert rows[gap_code]["bindCount"] == 0
    assert rows[gap_code]["linkGap"] is True
    assert rows[bound_code]["bindCount"] == 1
    assert rows[bound_code]["linkGap"] is False
    assert both["linkGapTotal"] >= 1

    owned = _by_code(_page(auth, keyword=prefix, ownerUserId=admin_id))
    assert bound_code in owned
    assert gap_code not in owned

    unassigned = _by_code(_page(auth, keyword=prefix, unassigned=1))
    assert gap_code in unassigned
    assert bound_code not in unassigned

    in_use = _by_code(_page(auth, keyword=prefix, status="IN_USE"))
    assert set(in_use) == {bound_code}

    gaps = _page(auth, keyword=prefix, linkGap=1)
    gap_rows = _by_code(gaps)
    assert gap_code in gap_rows
    assert bound_code not in gap_rows
    assert gaps["linkGapTotal"] == gaps["total"]
    assert all(item["linkGap"] for item in gaps["list"])

    invalid = client.get(
        "/admin-api/ims/asset/ledger/page",
        headers=auth,
        params={"ownerUserId": -1},
    ).json()
    assert invalid["code"] == 1001

    db = SessionLocal()
    try:
        bind = db.scalar(select(AssetBind).where(AssetBind.asset_id == bound["data"]["id"], AssetBind.deleted == 0))
        assert bind is not None
        bind.bind_status = "RELEASED"
        db.commit()
    finally:
        db.close()
    released = _by_code(_page(auth, keyword=bound_code, ownerUserId=admin_id))
    assert released[bound_code]["bindCount"] == 0
    assert released[bound_code]["linkGap"] is True


def test_ledger_export_follows_current_filters():
    auth = headers()
    admin_id = _admin_id(auth)
    mark = uuid.uuid4().hex[:8]
    prefix = f"AS149X{mark}"
    gap_code = f"{prefix}G"
    kept_code = f"{prefix}K"
    account_no = f"AC149X{mark}"
    _account(account_no, admin_id)
    assert _create(auth, gap_code)["code"] == 0
    bound = _create(auth, kept_code, accountNo=account_no)
    assert bound["code"] == 0, bound
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{bound['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked

    bad = client.get("/admin-api/ims/asset/ledger/export", headers=auth, params={"format": "PDF"}).json()
    assert bad["code"] == 1001

    exported = client.get(
        "/admin-api/ims/asset/ledger/export",
        headers=auth,
        params={"keyword": prefix, "assetType": "OFFICE", "linkGap": 1, "format": "XLSX"},
    ).json()
    assert exported["code"] == 0, exported
    assert exported["data"]["fileName"] == "asset_ledger.xlsx"
    assert exported["data"]["exported"] >= 1
    assert "台账已按当前筛选导出" in exported["data"]["message"]
    file_res = client.get(exported["data"]["downloadUrl"], headers=auth)
    assert file_res.status_code == 200
    assert file_res.content[:2] == b"PK"
    sheet = zipfile.ZipFile(BytesIO(file_res.content)).read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert gap_code in sheet
    assert kept_code not in sheet
    assert "待补关联" in sheet

    csv_export = client.get(
        "/admin-api/ims/asset/ledger/export",
        headers=auth,
        params={"keyword": prefix, "assetType": "OFFICE", "ownerUserId": admin_id, "format": "CSV"},
    ).json()
    assert csv_export["code"] == 0, csv_export
    csv_res = client.get(csv_export["data"]["downloadUrl"], headers=auth)
    text = csv_res.content.decode("utf-8-sig")
    assert kept_code in text
    assert gap_code not in text
    assert "在用" in text

    expired = client.get("/admin-api/ims/asset/ledger/export/file", headers=auth, params={"token": "missing"}).json()
    assert expired["code"] == 1002

    live = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": f"{prefix}L", "assetName": "直播灯", "assetType": "LIVE"},
    ).json()
    assert live["code"] == 0, live
    office_only = _by_code(_page(auth, keyword=prefix))
    assert f"{prefix}L" not in office_only
    live_page = client.get(
        "/admin-api/ims/corp/device/live/page",
        headers=auth,
        params={"keyword": prefix, "assetType": "LIVE", "pageSize": 50},
    ).json()
    assert live_page["code"] == 0, live_page
    live_codes = {item["assetCode"] for item in live_page["data"]["list"]}
    assert live_codes == {f"{prefix}L"}


def test_ledger_export_empty_filter_says_zero_hits():
    """#220 · 筛选无命中时导出台账标明空表，xlsx/csv 只留表头和空行说明。"""
    auth = headers()
    keyword = f"AS220NONE{uuid.uuid4().hex[:8]}"
    exported = client.get(
        "/admin-api/ims/asset/ledger/export",
        headers=auth,
        params={"keyword": keyword, "assetType": "OFFICE", "status": "SCRAPPED", "linkGap": 1, "format": "XLSX"},
    ).json()
    assert exported["code"] == 0, exported
    assert exported["data"]["empty"] is True
    assert exported["data"]["exported"] == 0
    assert exported["data"]["total"] == 0
    assert exported["data"]["message"] == "已导出空台账（当前筛选命中 0 条）"
    file_res = client.get(exported["data"]["downloadUrl"], headers=auth)
    assert file_res.status_code == 200
    assert file_res.content[:2] == b"PK"
    sheet = zipfile.ZipFile(BytesIO(file_res.content)).read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "暂无资产记录" in sheet
    assert keyword not in sheet

    csv_export = client.get(
        "/admin-api/ims/asset/ledger/export",
        headers=auth,
        params={"keyword": keyword, "assetType": "LIVE,SHOOT", "unassigned": 1, "format": "CSV"},
    ).json()
    assert csv_export["code"] == 0, csv_export
    assert csv_export["data"]["empty"] is True
    assert csv_export["data"]["message"] == "已导出空台账（当前筛选命中 0 条）"
    text = client.get(csv_export["data"]["downloadUrl"], headers=auth).content.decode("utf-8-sig")
    assert "暂无资产记录" in text
    assert keyword not in text
