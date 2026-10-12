"""B6 设备：手机、台账、生命周期、穿透与校验。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.clock import today
from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import session_scope
from app.domains.device.model import AssetLedger, AssetVerifyTask
from app.domains.message.model import Message
from app.domains.system.model import Dept, ExportTask, User, UserRole
from app.domains.todo.model import Todo
from tests.conftest import auth
from tests.stddata import D1, PASSWORD, U_ADMIN, U_DEPT, U_RESIGNED

API = "/admin-api/ims"


def _headers(client, username="u_admin", token=None, base=None):
    headers = dict(base or auth(client, username))
    if token:
        headers["X-Client-Token"] = token
    return headers


def _ok(response):
    body = response.json()
    assert body["code"] == 0, body
    return body["data"]


def _err(response, code):
    body = response.json()
    assert body["code"] == code, body
    return body


def _user(ident: int, username: str, role_id: int):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            if session.get(User, ident) is None:
                session.add(
                    User(
                        id=ident,
                        username=username,
                        nickname=username,
                        password_hash=hash_password(PASSWORD),
                        status="ACTIVE",
                        tenant_id=1,
                        main_dept_id=D1,
                        source="LOCAL",
                    )
                )
                session.flush()
                session.add(UserRole(user_id=ident, role_id=role_id, source="MANUAL", tenant_id=1))


def _phone(client, headers, **extra):
    body = {"model": "iPhone 15", "osType": "IOS", "custodianUserId": U_DEPT, "purchaseDate": "2026-01-01"}
    body.update(extra)
    return _ok(client.post(f"{API}/corp/device/phone", json=body, headers=headers))


def _asset(client, headers, **extra):
    body = {
        "assetName": "麦克风",
        "scope": "office",
        "purchaseDate": "2026-01-02",
        "ownerUserId": U_DEPT,
        "purchaseAmount": "12.50",
    }
    body.update(extra)
    return _ok(client.post(f"{API}/asset/ledger", json=body, headers=headers))


def _realname(client, headers, name="测试实名甲", number="110101199003078515"):
    return _ok(client.post(f"{API}/corp/resource/realname", json={"name": name, "idType": "ID_CARD", "idNo": number}, headers=headers))


def _sim(client, headers, phone, realname_id=None):
    body = {"phoneNumber": phone, "operator": "CMCC", "realnameId": realname_id}
    return _ok(client.post(f"{API}/corp/resource/sim-card", json=body, headers=headers))


def test_phone_register_bind_and_block(client):
    admin = auth(client, "u_admin")
    headers = _headers(client, token="ph-1", base=admin)
    first = _phone(client, headers, imei="860000000000001")
    assert first["status"] == "IN_USE"
    assert str(first["deviceNo"]).startswith("PH-2026-")
    replay = _ok(client.post(f"{API}/corp/device/phone", json={"model": "x", "osType": "IOS", "custodianUserId": U_DEPT}, headers=headers))
    assert replay["id"] == first["id"]
    dup = _headers(client, token="ph-dup", base=admin)
    _err(client.post(f"{API}/corp/device/phone", json={"model": "A", "osType": "IOS", "custodianUserId": U_DEPT, "imei": "860000000000001"}, headers=dup), 1001)
    person = _realname(client, admin)
    card_a = _sim(client, admin, "13800001001", person["id"])
    card_b = _sim(client, admin, "13800001002", person["id"])
    card_c = _sim(client, admin, "13800001003", person["id"])
    bound = _ok(client.put(f"{API}/corp/device/phone/{first['id']}/sim-bind", json={"simIds": [card_a["id"], card_b["id"]]}, headers=admin))
    assert bound["simCount"] == 2
    other = _phone(client, _headers(client, token="ph-2", base=admin), model="Pixel", osType="ANDROID")
    _err(client.put(f"{API}/corp/device/phone/{other['id']}/sim-bind", json={"simIds": [card_a["id"]]}, headers=admin), 1012)
    _err(client.put(f"{API}/corp/device/phone/{first['id']}/sim-bind", json={"simIds": [card_a["id"], card_b["id"], card_c["id"]]}, headers=admin), 1001)
    _err(client.put(f"{API}/corp/device/phone/{first['id']}/status", json={"status": "SCRAPPED", "reason": "坏了"}, headers=admin), 1502)
    _err(client.put(f"{API}/corp/resource/sim-card/{card_a['id']}/status", json={"status": "DISABLED"}, headers=admin), 1502)
    page = _ok(client.get(f"{API}/corp/resource/sim-card/page", headers=admin))
    hit = next(item for item in page["list"] if item["id"] == card_a["id"])
    assert hit["phoneName"] == first["deviceNo"]
    _ok(client.put(f"{API}/corp/device/phone/{first['id']}/sim-bind", json={"simIds": []}, headers=admin))
    _err(client.delete(f"{API}/corp/device/phone/{first['id']}", headers=admin), 1502)


def test_asset_lifecycle_and_scope(client):
    admin = auth(client, "u_admin")
    headers = _headers(client, token="as-1", base=admin)
    row = _asset(client, headers)
    assert row["status"] == "PENDING_REVIEW"
    assert row["needLink"] is True
    used = _ok(client.post(f"{API}/asset/ledger/{row['id']}/checkout", json={"userId": U_DEPT, "checkoutDate": "2026-01-03", "purpose": "直播", "version": row["version"]}, headers=admin))
    assert used["status"] == "IN_USE"
    _err(client.post(f"{API}/asset/ledger/{row['id']}/checkout", json={"userId": U_ADMIN, "checkoutDate": "2026-01-04", "version": used["version"]}, headers=admin), 1012)
    _err(client.post(f"{API}/asset/ledger/{row['id']}/scrap", json={"reason": "坏了", "version": used["version"]}, headers=admin), 1015)
    moved = _ok(client.post(f"{API}/asset/ledger/{row['id']}/transfer", json={"userId": U_ADMIN, "reason": "工作调整", "version": used["version"]}, headers=admin))
    back = _ok(client.post(f"{API}/asset/ledger/{row['id']}/return", json={"returnDate": "2026-01-05", "condition": "GOOD", "version": moved["version"]}, headers=admin))
    assert back["status"] == "RETURNED"
    assert str(back["ownerUserId"]) == str(U_ADMIN)
    _err(client.post(f"{API}/asset/ledger/{row['id']}/return", json={"returnDate": "2026-01-05", "condition": "GOOD", "version": 1}, headers=admin), 1001)
    idle = _ok(client.put(f"{API}/asset/ledger/{row['id']}/status", json={"status": "IDLE", "version": back["version"]}, headers=admin))
    assert idle["status"] == "IDLE"
    scrapped = _ok(client.post(f"{API}/asset/ledger/{row['id']}/scrap", json={"reason": "报废", "version": idle["version"]}, headers=admin))
    assert scrapped["status"] == "SCRAPPED"
    _user(3205, "b6_r5", 105)
    own = _asset(client, _headers(client, token="as-r5", base=admin), assetName="组长的设备", ownerUserId=3205)
    other = _asset(client, _headers(client, token="as-other", base=admin), assetName="别人的设备", ownerUserId=U_ADMIN)
    r5 = auth(client, "b6_r5")
    page = _ok(client.get(f"{API}/corp/device/office/page", headers=r5))
    codes = {item["assetCode"] for item in page["list"]}
    assert own["assetCode"] in codes
    assert other["assetCode"] not in codes
    _err(client.get(f"{API}/asset/ledger/{other['id']}", headers=r5), 1008)
    with session_scope() as session:
        sent = session.scalar(select(Message).where(Message.receiver_id == U_DEPT, Message.title == "资产领用"))
        assert sent is not None
        assert "你已领用资产" in (sent.content or "")


def test_import_partial_and_limits(client):
    headers = auth(client, "u_admin")
    mixed = "资产编号,资产名称,资产类型,规格,采购日期,责任人工号\nAS-M-1,麦克风,办公设备,手持,2026-01-01,u_dept\nAS-M-2,灯光,,支架,2026-01-02,\n,,办公设备,,2026-01-03,\nAS-M-4,日期坏,办公设备,,2026-13-40,\nAS-M-1,重复,办公设备,,2026-01-04,\n"
    saved = _ok(client.post(f"{API}/asset/ledger/import", files={"file": ("mixed.csv", mixed.encode(), "text/csv")}, data={"scope": "office"}, headers=headers))
    assert saved["successCount"] == 2
    assert saved["failCount"] == 3
    assert saved["message"] == "成功 2 条，失败 3 条"
    live = "资产编号,资产名称,资产类型,规格,采购日期,责任人工号\n,缺类型,,,2026-01-01,\n"
    failed = _ok(client.post(f"{API}/asset/ledger/import", files={"file": ("live.csv", live.encode(), "text/csv")}, data={"scope": "live"}, headers=headers))
    assert failed["successCount"] == 0
    assert failed["errors"][0]["code"] == 1503
    big = "资产名称,资产类型,采购日期\n" + "".join(f"设备{i},办公设备,2026-01-01\n" for i in range(201))
    _err(client.post(f"{API}/asset/ledger/import", files={"file": ("big.csv", big.encode(), "text/csv")}, data={"scope": "office"}, headers=headers), 1001)
    _err(client.post(f"{API}/asset/ledger/import", files={"file": ("bad.csv", "只有一列\n".encode(), "text/csv")}, data={"scope": "office"}, headers=headers), 1001)


def test_forward_reverse_and_export_expiry(client):
    headers = _headers(client, token="fw-1")
    person = _realname(client, headers)
    row = _asset(client, headers, realnameId=person["id"], purchaseAmount="88.00")
    detail = _ok(client.get(f"{API}/asset/forward/detail/{row['id']}", headers=headers))
    assert {item["layer"] for item in detail["layers"]} == {"L1", "L2", "L3", "L4", "L5"}
    _err(client.get(f"{API}/asset/forward/detail/{row['id']}?layers=L9", headers=headers), 1013)
    _user(3209, "b6_r9", 109)
    masked = _ok(client.get(f"{API}/asset/forward/detail/{row['id']}", headers=auth(client, "b6_r9")))
    cost = next(item for item in masked["layers"] if item["layer"] == "L5")
    assert cost["costMasked"] is True
    assert cost["amount"] == "¥****"
    _user(3205, "b6_r5", 105)
    _err(client.get(f"{API}/asset/forward/detail/{row['id']}", headers=auth(client, "b6_r5")), 1008)
    report = _ok(client.get(f"{API}/asset/forward/export/{row['id']}", headers=headers))
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            task = session.get(ExportTask, int(report["id"]))
            task.query_json = {"expiresAt": "2000-01-01 00:00:00"}
    _err(client.get(f"{API}/export-task/download", params={"id": report["id"]}, headers=headers), 1001)
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.get(User, U_RESIGNED)
            user.status = "RESIGNED"
            asset = session.get(AssetLedger, int(row["id"]))
            asset.status = "IN_USE"
            asset.owner_user_id = U_RESIGNED
    found = _ok(client.get(f"{API}/asset/reverse/by-person/{U_RESIGNED}", headers=headers))
    assert "离职归还未闭环" in found["banner"]
    assert any(item["frozen"] for item in found["list"])
    chain = _ok(client.get(f"{API}/asset/forward/trace/0", params={"realnameId": person["id"]}, headers=headers))
    assert chain["nodes"]


def test_verify_flow_and_overdue(client):
    admin = auth(client, "u_admin")
    bare = _asset(client, _headers(client, token="vf-asset", base=admin), assetName="缺实名")
    _err(client.post(f"{API}/asset/verify/run", json={"verifyTypes": ["asset_account"]}, headers=_headers(client, token="vf-bad", base=admin)), 1001)
    first = _ok(client.post(f"{API}/asset/verify/run", json={"verifyTypes": ["asset_person"], "scope": "FULL"}, headers=_headers(client, token="vf-1", base=admin)))
    assert first["errorCount"] >= 1
    second = _ok(client.post(f"{API}/asset/verify/run", json={"verifyTypes": ["asset_person"], "scope": "FULL"}, headers=_headers(client, token="vf-2", base=admin)))
    assert second["createdCount"] == 0
    errors = _ok(client.get("/admin-api/ims/asset/verify/errors", params={"batchNo": first["batchNo"]}, headers=admin))
    task = next(item for item in errors["list"] if item["assetId"] == bare["id"])
    deadline = (today() + timedelta(days=1)).isoformat()
    dispatched = _ok(client.put(f"{API}/asset/verify/task/{task['id']}", json={"action": "DISPATCH", "ownerUserId": U_DEPT, "deadline": deadline}, headers=admin))
    assert dispatched["taskStatus"] == "REPAIRING"
    _err(client.put(f"{API}/asset/verify/task/{task['id']}", json={"action": "SUBMIT_FIX", "remark": "已补"}, headers=admin), 1008)
    _err(client.put(f"{API}/asset/verify/task/{task['id']}", json={"action": "RECHECK_PASS"}, headers=admin), 1014)
    dept = auth(client, "u_dept")
    submitted = _ok(client.put(f"{API}/asset/verify/task/{task['id']}", json={"action": "SUBMIT_FIX", "remark": "已补实名"}, headers=dept))
    assert submitted["taskStatus"] == "PENDING_RECHECK"
    closed = _ok(client.put(f"{API}/asset/verify/task/{task['id']}", json={"action": "RECHECK_PASS"}, headers=admin))
    assert closed["taskStatus"] == "CLOSED"
    with session_scope() as session:
        todo = session.scalar(select(Todo).where(Todo.source_type == "ASSET_VERIFY", Todo.source_id == int(task["id"])))
        assert todo is not None and todo.status == "DONE"
    metrics = _ok(client.get(f"{API}/asset/verify/metrics", headers=admin))
    assert metrics["completeness"] != ""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept_row = session.get(Dept, D1)
            dept_row.leader_user_id = U_ADMIN
            row = session.get(AssetVerifyTask, int(task["id"]))
            row.task_status = "REPAIRING"
            row.deadline = today() - timedelta(days=2)
            row.escalated_at = None
            row.owner_user_id = U_DEPT
    from app.domains.device.verify import scan_overdue

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            result = scan_overdue()
    assert result["escalated"] == 1
    again = None
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            again = scan_overdue()
    assert again["escalated"] == 0
