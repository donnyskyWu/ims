"""#82 · 台账异步 Excel 导出、财务角色裁剪报告、下播成本明细校验。"""

import os
import uuid
import zipfile
from io import BytesIO
from xml.etree import ElementTree

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import E2E_ACCT_FINANCE_USER, E2E_ACCT_PEER_USER, _ensure_cloned_user
from app.core import SessionLocal
from app.crypto import encrypt_text
from app.live_fin_e2e_seed import E2E_LEDGER_SESSION
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname
from app.live import _LEDGER_EXPORTS

client = TestClient(app)
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ANALYST = "e2e_live_r9"


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def ensure_analyst() -> None:
    db = SessionLocal()
    try:
        _ensure_cloned_user(
            db,
            username=ANALYST,
            nickname="数据分析师",
            mobile="13900000082",
            role_key="live:r9",
            role_name="数据分析师",
        )
        db.commit()
    finally:
        db.close()


def seed_account() -> tuple[int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="导出公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="导出组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="导出实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011082"),
            phone_enc=encrypt_text("13800001082"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600001082"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-LIVE-0082",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-PY-0082",
            account_name="导出台",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        return account.id, person.id, phone.id
    finally:
        ops.close()


def register(auth: dict, account_id: int, person_id: int, phone_id: int) -> str:
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "realnamePersonId": person_id,
            "responsibleUserId": 1,
            "deviceAssetIds": [phone_id],
            "platform": "DOUYIN",
            "topic": "成本明细专场",
            "planStartTime": "2026-10-08T18:00:00+08:00",
            "planEndTime": "2026-10-08T19:00:00+08:00",
        },
    )
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]["sessionCode"]


def full_report(**overrides) -> dict:
    body = {
        "actualStart": "2026-10-08T18:00:00+08:00",
        "actualEnd": "2026-10-08T19:00:00+08:00",
        "gmv": 100,
        "refundAmount": 0,
        "orderCount": 4,
        "viewerCount": 80,
        "peakOnline": 20,
        "newFans": 3,
        "adCost": 50,
    }
    body.update(overrides)
    return body


def xlsx_rows(blob: bytes) -> list[list[str]]:
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml")
    root = ElementTree.fromstring(xml)
    rows = []
    for row in root.findall("m:sheetData/m:row", NS):
        cells = []
        for cell in row.findall("m:c", NS):
            node = cell.find("m:is/m:t", NS)
            cells.append("" if node is None or node.text is None else node.text)
        rows.append(cells)
    return rows


def test_cost_details_reject_then_drive_roas_and_summary():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    negative = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(costDetails=[{"costType": "GIFT", "amount": -1}]),
    )
    assert negative.json()["code"] == 1001
    assert negative.json()["data"]["field"] == "amount"
    illegal = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(costDetails=[{"costType": "BONUS", "amount": 1}]),
    )
    assert illegal.json()["code"] == 1001
    assert illegal.json()["data"]["field"] == "costType"
    long_remark = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(costDetails=[{"costType": "AD", "amount": 1, "remark": "注" * 257}]),
    )
    assert long_remark.json()["code"] == 1001
    assert long_remark.json()["data"]["field"] == "remark"
    saved = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(
            costDetails=[
                {"costType": "ad", "amount": 10.126, "remark": "投放"},
                {"costType": "GIFT", "amount": 9.87, "refRecordId": 0},
            ]
        ),
    )
    body = saved.json()
    assert body["code"] == 0, body
    assert body["data"]["fieldScope"] == "FULL"
    assert body["data"]["viewerCount"] == 80
    assert body["data"]["roas"] == 5.0
    assert body["data"]["costDetails"][0]["costType"] == "AD"
    assert body["data"]["costDetails"][0]["amount"] == 10.13
    assert body["data"]["costDetails"][1]["amount"] == 9.87
    detail = client.get(f"/admin-api/ims/live/ledger/{code}", headers=auth)
    summary = detail.json()["data"]["costSummary"]
    assert summary["totalCost"] == 20.0
    assert summary["byType"]["AD"] == 10.13
    assert summary["byType"]["GIFT"] == 9.87
    assert summary["costMasked"] is False


def test_finance_trims_report_and_cannot_export_while_r9_masks_cost():
    ensure_analyst()
    admin = headers()
    finance = headers(E2E_ACCT_FINANCE_USER)
    analyst = headers(ANALYST)
    peer = headers(E2E_ACCT_PEER_USER)
    code = E2E_LEDGER_SESSION

    admin_report = client.get(f"/admin-api/ims/live/report/{code}", headers=admin)
    assert admin_report.json()["code"] == 0, admin_report.json()
    assert admin_report.json()["data"]["fieldScope"] == "FULL"
    assert admin_report.json()["data"]["viewerCount"] == 4321
    assert admin_report.json()["data"]["adCost"] == 860
    assert admin_report.json()["data"]["gmv"] == 12800.5

    trimmed = client.get(f"/admin-api/ims/live/report/{code}", headers=finance)
    data = trimmed.json()["data"]
    assert trimmed.json()["code"] == 0, trimmed.json()
    assert data["fieldScope"] == "FINANCE"
    assert data["gmv"] == 12800.5
    assert data["adCost"] == 860
    assert data["refundAmount"] == 20
    assert {item["costType"] for item in data["costDetails"]} == {"AD", "GIFT"}
    assert "viewerCount" not in data
    assert "orderCount" not in data
    assert "actualStart" not in data
    assert "peakOnline" not in data
    session = client.get(f"/admin-api/ims/live/sessions/{code}", headers=finance)
    summary = session.json()["data"]["reportSummary"]
    assert set(summary) == {"gmv", "roas", "entryStatus"}
    assert session.json()["data"]["report"]["fieldScope"] == "FINANCE"
    assert session.json()["data"]["costSummary"]["costMasked"] is False
    listing = client.get("/admin-api/ims/live/ledger/list", headers=finance, params={"sessionCode": code})
    assert "orderCount" not in listing.json()["data"]["list"][0]["reportSummary"]

    masked = client.get(f"/admin-api/ims/live/report/{code}", headers=analyst)
    masked_data = masked.json()["data"]
    assert masked.json()["code"] == 0, masked.json()
    assert masked_data["fieldScope"] == "MASKED"
    assert masked_data["viewerCount"] == 4321
    assert masked_data["gmv"] == 12800.5
    assert masked_data["adCost"] == "***"
    assert masked_data["roas"] == "***"
    assert {item["amount"] for item in masked_data["costDetails"]} == {"***"}
    masked_session = client.get(f"/admin-api/ims/live/ledger/{code}", headers=analyst)
    assert masked_session.json()["data"]["costSummary"]["totalCost"] == "***"
    assert masked_session.json()["data"]["costSummary"]["costMasked"] is True

    denied = client.get("/admin-api/ims/live/ledger/export", headers=finance, params={"sessionCode": code})
    assert denied.json()["code"] == 1008
    peer_denied = client.get("/admin-api/ims/live/ledger/export", headers=peer, params={"sessionCode": code})
    assert peer_denied.json()["code"] == 1008

    exported = client.get("/admin-api/ims/live/ledger/export", headers=admin, params={"sessionCode": code})
    payload = exported.json()
    assert payload["code"] == 0, payload
    assert payload["data"]["message"] == "导出任务已提交"
    assert payload["data"]["exportTaskId"]
    assert payload["data"]["fileName"] == "live_ledger.xlsx"
    downloaded = client.get(payload["data"]["downloadUrl"], headers=admin)
    assert downloaded.status_code == 200
    assert "live_ledger.xlsx" in downloaded.headers["content-disposition"]
    rows = xlsx_rows(downloaded.content)
    assert rows[0][0] == "场次ID"
    assert rows[1][0] == code
    assert rows[1][8] == "12800.50"
    assert rows[1][10] == "860.00"
    assert rows[1][12] == "4321"
    assert rows[1][16] != "***"

    other = client.get(payload["data"]["downloadUrl"], headers=finance)
    assert other.json()["code"] == 1008
    token = payload["data"]["exportTaskId"]
    _LEDGER_EXPORTS[token] = (0, b"", 1, "")
    expired = client.get(payload["data"]["downloadUrl"], headers=admin)
    assert expired.json()["code"] == 1002

    analyst_export = client.get("/admin-api/ims/live/ledger/export", headers=analyst, params={"sessionCode": code})
    analyst_file = client.get(analyst_export.json()["data"]["downloadUrl"], headers=analyst)
    analyst_rows = xlsx_rows(analyst_file.content)
    assert analyst_rows[1][0] == code
    assert analyst_rows[1][8] == "12800.50"
    assert analyst_rows[1][10] == "***"
    assert analyst_rows[1][12] == "4321"
    assert analyst_rows[1][16] == "***"

    outside = client.get(
        "/admin-api/ims/live/ledger/export",
        headers=admin,
        params={"sessionCode": code, "timeRange": ["2020-01-01T00:00:00+08:00", "2020-01-02T00:00:00+08:00"]},
    )
    outside_rows = xlsx_rows(client.get(outside.json()["data"]["downloadUrl"], headers=admin).content)
    assert len(outside_rows) == 1
