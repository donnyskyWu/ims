"""#74 · 正向穿透报告 PDF 与反查 xlsx。层级和入口错误码与穿透接口一致。"""

import os
import zipfile
from io import BytesIO
from xml.etree import ElementTree

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core import SessionLocal
from app.crypto import encrypt_text, sha256_hex
from app.main import app
from app.models import LiveSession
from app.ops_db import ops_session
from app.ops_models import PlatformAccount, Realname

client = TestClient(app)

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
STATUS_LABEL = {
    "PENDING_REVIEW": "待审核",
    "IN_USE": "在用",
    "RETURNED": "已归还",
    "SCRAPPED": "已报废",
}
BIND_LABEL = {"HOLD": "持有", "GUARANTEE": "担保", "CUSTODY": "代管"}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    return int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])


def _person() -> int:
    ops = ops_session()
    try:
        row = Realname(
            real_name="导出实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800002222"),
            phone_sha256=sha256_hex("13800002222"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _create(auth: dict, code: str, **extra) -> dict:
    body = {"assetCode": code, "assetName": code, "assetType": "OFFICE", **extra}
    return client.post("/admin-api/ims/asset/ledger", headers=auth, json=body).json()


def _download(auth: dict, payload: dict):
    assert payload["code"] == 0, payload
    data = payload["data"]
    assert data["exportTaskId"]
    assert data["message"]
    assert data["downloadUrl"].endswith(f"token={data['exportTaskId']}")
    resp = client.get(data["downloadUrl"], headers=auth)
    assert resp.status_code == 200, resp.text
    disposition = resp.headers["content-disposition"]
    assert data["fileName"] in disposition
    return data, resp.content, resp.headers["content-type"]


def _pdf_text(blob: bytes) -> str:
    return PdfReader(BytesIO(blob)).pages[0].extract_text() or ""


def _xlsx_rows(blob: bytes) -> list[list[str]]:
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


def _summary_line(summary: dict) -> str:
    return (
        f"命中 {summary['total']} 条（在用 {summary['inUse']} / "
        f"已归还 {summary['returned']} / 已报废 {summary['scrapped']}）"
    )


def test_forward_export_pdf_matches_chain_and_blocks_layer_six():
    auth = headers()
    person_id = _person()
    root = _create(auth, "AS-EX-L1", realnameId=person_id)
    assert root["code"] == 0, root
    parent = "AS-EX-L1"
    ids = {1: root["data"]["id"]}
    for level in range(2, 6):
        code = f"AS-EX-L{level}"
        created = _create(auth, code, parentAssetCode=parent)
        assert created["code"] == 0, created
        ids[level] = created["data"]["id"]
        parent = code

    trace = client.get(f"/admin-api/ims/asset/forward/trace/{ids[5]}", headers=auth).json()
    assert trace["code"] == 0, trace
    exported = client.get(f"/admin-api/ims/asset/forward/export/{ids[5]}", headers=auth).json()
    data, blob, media = _download(auth, exported)
    assert data["fileName"] == "asset_forward_report.pdf"
    assert data["message"] == "穿透报告已生成"
    assert media.startswith("application/pdf")
    assert blob.startswith(b"%PDF")
    text = _pdf_text(blob)
    assert "资产穿透报告" in text
    for node in trace["data"]["nodes"]:
        if node["layer"] == "PERSON":
            line = f"实名人 · {node['label']}"
        else:
            line = f"第{node['level']}层 · {node['label']}"
        assert line in text
    assert "第5层" in text
    assert "第6层" not in text

    over = client.get(
        f"/admin-api/ims/asset/forward/export/{ids[1]}",
        headers=auth,
        params={"layers": "L1,L2,L3,L4,L5,L6"},
    ).json()
    assert over["code"] == 1013
    assert over.get("data") in (None, {})

    sixth = _create(auth, "AS-EX-L6", parentAssetCode="AS-EX-L5")
    assert sixth["code"] == 0, sixth
    blocked = client.get(f"/admin-api/ims/asset/forward/export/{sixth['data']['id']}", headers=auth).json()
    assert blocked["code"] == 1013
    person_blocked = client.get(
        "/admin-api/ims/asset/forward/export/0",
        headers=auth,
        params={"realnameId": person_id},
    ).json()
    assert person_blocked["code"] == 1013

    missing_asset = client.get("/admin-api/ims/asset/forward/export/99999999", headers=auth).json()
    assert missing_asset["code"] == 1011
    missing_person = client.get(
        "/admin-api/ims/asset/forward/export/0",
        headers=auth,
        params={"realnameId": 999999},
    ).json()
    assert missing_person["code"] == 1500
    expired = client.get(
        "/admin-api/ims/asset/forward/export/file",
        headers=auth,
        params={"token": "missing-token"},
    ).json()
    assert expired["code"] == 1002


def _account(account_no: str, holder_id: int) -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            holder_user_id=holder_id,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _session(account_id: int, account_no: str, code: str, owner_id: int) -> int:
    db = SessionLocal()
    try:
        row = LiveSession(
            session_code=code,
            account_id=account_id,
            account_no=account_no,
            responsible_user_id=owner_id,
            device_asset_ids="[]",
            platform="DOUYIN",
            topic="导出场次",
            session_status="ENDED",
            tenant_id=0,
            creator=owner_id,
            deleted=0,
        )
        db.add(row)
        db.commit()
        return int(row.id)
    finally:
        db.close()


def _assert_sheet_matches(rows: list[list[str]], listed: dict) -> None:
    assert rows[0][0] == "汇总"
    assert rows[0][1] == _summary_line(listed["summary"])
    assert rows[1] == ["资产编号", "名称", "状态", "绑定", "账号"]
    body = rows[2:]
    assert [item[0] for item in body] == [item["assetCode"] for item in listed["list"]]
    for sheet, item in zip(body, listed["list"]):
        assert sheet[1] == item["assetName"]
        assert sheet[2] == STATUS_LABEL[item["status"]]
        assert sheet[3] == BIND_LABEL[item["bindType"]]
        assert sheet[4] == (item["relatedAccountNo"] or "—")


def test_reverse_export_xlsx_covers_person_account_and_session():
    auth = headers()
    admin_id = _admin_id(auth)
    account_id = _account("AC-EX-74", admin_id)
    session_id = _session(account_id, "AC-EX-74", "IMS20261008DYE0074", admin_id)

    missing_type = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "OTHER", "entryId": 1},
    ).json()
    assert missing_type["code"] == 1001
    missing_person = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "PERSON", "entryId": 999999},
    ).json()
    assert missing_person["code"] == 1500
    missing_account = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "accountNo": "AC-NO-SUCH-74"},
    ).json()
    assert missing_account["code"] == 1500
    bad_session = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "SESSION", "sessionCode": "NOT-A-CODE"},
    ).json()
    assert bad_session["code"] == 1001
    missing_session = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "SESSION", "sessionCode": "IMS20261008AAA0001"},
    ).json()
    assert missing_session["code"] == 1500

    office = _create(auth, "AS-EX-ACC", accountNo="AC-EX-74")
    assert office["code"] == 0, office
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{office['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    shoot = _create(auth, "AS-EX-SES", sessionCode="IMS20261008DYE0074")
    assert shoot["code"] == 0, shoot

    person_list = client.get(f"/admin-api/ims/asset/reverse/by-person/{admin_id}", headers=auth, params={"pageSize": 50}).json()
    person_export = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "PERSON", "entryId": admin_id},
    ).json()
    data, blob, media = _download(auth, person_export)
    assert data["fileName"] == "asset_reverse_report.xlsx"
    assert data["message"] == "反查结果已生成"
    assert media.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert blob[:2] == b"PK"
    _assert_sheet_matches(_xlsx_rows(blob), person_list["data"])
    assert any(row[0] == "AS-EX-ACC" and row[2] == "在用" for row in _xlsx_rows(blob)[2:])

    account_list = client.get(
        f"/admin-api/ims/asset/reverse/by-account/{account_id}",
        headers=auth,
        params={"pageSize": 50},
    ).json()
    account_export = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id},
    ).json()
    _data, account_blob, _media = _download(auth, account_export)
    account_rows = _xlsx_rows(account_blob)
    _assert_sheet_matches(account_rows, account_list["data"])
    assert {row[0] for row in account_rows[2:]} == {"AS-EX-ACC", "AS-EX-SES"}

    by_no = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "accountNo": "AC-EX-74"},
    ).json()
    _data, by_no_blob, _media = _download(auth, by_no)
    assert [row[0] for row in _xlsx_rows(by_no_blob)[2:]] == [row[0] for row in account_rows[2:]]

    session_list = client.get(
        f"/admin-api/ims/asset/reverse/by-session/{session_id}",
        headers=auth,
        params={"pageSize": 50},
    ).json()
    session_export = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "SESSION", "entryId": session_id},
    ).json()
    _data, session_blob, _media = _download(auth, session_export)
    session_rows = _xlsx_rows(session_blob)
    _assert_sheet_matches(session_rows, session_list["data"])
    assert [row[0] for row in session_rows[2:]] == ["AS-EX-SES"]
    assert session_rows[2][2] == "待审核"
    assert session_rows[2][4] == "AC-EX-74"


def test_empty_reverse_xlsx_and_pdf_are_stub_files_and_history_switch_matches_list():
    """入口存在但没有资产时仍给出可下载的空表/空报告。已归还可从使用人导出里关掉。"""
    auth = headers()
    admin_id = _admin_id(auth)
    empty_account = _account("AC-EX-EMPTY-167", admin_id)
    listed = client.get(
        f"/admin-api/ims/asset/reverse/by-account/{empty_account}",
        headers=auth,
    ).json()
    assert listed["code"] == 0, listed
    assert listed["data"]["list"] == []
    assert listed["data"]["summary"]["total"] == 0

    exported = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": empty_account},
    ).json()
    data, blob, media = _download(auth, exported)
    assert data["empty"] is True
    assert data["summary"]["total"] == 0
    assert media.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rows = _xlsx_rows(blob)
    assert rows[0] == ["汇总", _summary_line(listed["data"]["summary"])]
    assert rows[1] == ["资产编号", "名称", "状态", "绑定", "账号"]
    assert rows[2][0] == "暂无绑定资产"

    bare = _person()
    pdf = client.get(
        "/admin-api/ims/asset/forward/export/0",
        headers=auth,
        params={"realnameId": bare},
    ).json()
    pdf_data, pdf_blob, pdf_media = _download(auth, pdf)
    assert pdf_data["empty"] is True
    assert pdf_media.startswith("application/pdf")
    text = _pdf_text(pdf_blob)
    assert "资产穿透报告" in text
    assert "实名人 ·" in text
    assert "暂无资产层级" in text
    assert "第1层" not in text

    code = "AS-EX-HIST-167"
    created = _create(auth, code)
    assert created["code"] == 0, created
    asset_id = created["data"]["id"]
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
        headers=auth,
        json={"ownerUserId": admin_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    used = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/use",
        headers=auth,
        json={"remark": "现场使用"},
    ).json()
    assert used["code"] == 0, used
    returned = client.post(
        f"/admin-api/ims/asset/ledger/{asset_id}/return",
        headers=auth,
        json={"remark": "归还入库"},
    ).json()
    assert returned["code"] == 0, returned

    with_history = client.get(
        f"/admin-api/ims/asset/reverse/by-person/{admin_id}",
        headers=auth,
        params={"includeHistory": True, "pageSize": 50},
    ).json()
    assert with_history["code"] == 0, with_history
    assert any(item["assetCode"] == code and item["status"] == "RETURNED" for item in with_history["data"]["list"])

    current_only = client.get(
        f"/admin-api/ims/asset/reverse/by-person/{admin_id}",
        headers=auth,
        params={"includeHistory": False, "pageSize": 50},
    ).json()
    assert current_only["code"] == 0, current_only
    assert all(item["assetCode"] != code for item in current_only["data"]["list"])

    hidden = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "PERSON", "entryId": admin_id, "includeHistory": False},
    ).json()
    _hidden_data, hidden_blob, _media = _download(auth, hidden)
    assert all(row[0] != code for row in _xlsx_rows(hidden_blob))

    shown = client.get(
        "/admin-api/ims/asset/reverse/export",
        headers=auth,
        params={"entryType": "PERSON", "entryId": admin_id, "includeHistory": True},
    ).json()
    _shown_data, shown_blob, _media = _download(auth, shown)
    assert any(row[0] == code and row[2] == "已归还" for row in _xlsx_rows(shown_blob))
