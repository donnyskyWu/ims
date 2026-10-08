"""#78 · BR-014 红级 1043 / 黄级审批 1044 / 补录 1049。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.live import risk_level_of
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname, SimCard

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_bundle() -> dict:
    ops = ops_session()
    try:
        company = Company(company_name="风控公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="风控组", status="ENABLED", tenant_id=0)
        green_person = Realname(
            real_name="绿级实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001010001"),
            phone_enc=encrypt_text("13800002001"),
            status="ENABLED",
            tenant_id=0,
        )
        yellow_person = Realname(
            real_name="黄级实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001010044"),
            phone_enc=encrypt_text("13800002044"),
            status="ENABLED",
            tenant_id=0,
        )
        red_person = Realname(
            real_name="红级实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001010043"),
            phone_enc=encrypt_text("13800002043"),
            status="DISABLED",
            tenant_id=0,
        )
        edge_person = Realname(
            real_name="边界实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001010040"),
            phone_enc=encrypt_text("13800002040"),
            status="DISABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600002001"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-RISK-OK",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        idle_phone = Phone(
            phone_enc=encrypt_text("13600002070"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-RISK-IDLE",
            status="SCRAPPED",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, green_person, yellow_person, red_person, edge_person, phone, idle_phone])
        ops.flush()
        stopped_sim = SimCard(
            phone_enc=encrypt_text("13600002040"),
            phone_sha256=uuid.uuid4().hex,
            status="STOPPED",
            tenant_id=0,
        )
        ops.add(stopped_sim)
        ops.flush()

        def account(no: str, person_id: int, status: str, sim_id: int | None = None) -> PlatformAccount:
            row = PlatformAccount(
                account_no=no,
                account_name=no,
                platform_type="DOUYIN",
                ip_group_id=group.id,
                company_id=company.id,
                realname_id=person_id,
                holder_user_id=1,
                sim_card_id=sim_id,
                status=status,
                tenant_id=0,
            )
            ops.add(row)
            return row

        green = account("AC-PY-GREEN", green_person.id, "IN_USE")
        yellow = account("AC-PY-YELLOW", yellow_person.id, "FROZEN")
        red = account("AC-PY-RED", red_person.id, "FROZEN")
        edge40 = account("AC-PY-40", edge_person.id, "IN_USE", stopped_sim.id)
        edge70 = account("AC-PY-70", green_person.id, "FROZEN", stopped_sim.id)
        ops.commit()
        return {
            "green_account": green.id,
            "green_person": green_person.id,
            "yellow_account": yellow.id,
            "yellow_person": yellow_person.id,
            "red_account": red.id,
            "red_person": red_person.id,
            "edge40_account": edge40.id,
            "edge40_person": edge_person.id,
            "edge70_account": edge70.id,
            "edge70_person": green_person.id,
            "phone": phone.id,
            "idle_phone": idle_phone.id,
        }
    finally:
        ops.close()


def payload(account_id: int, person_id: int, phone_id: int, topic: str, plan: str = "2026-10-08T20:00:00+08:00") -> dict:
    return {
        "accountId": account_id,
        "realnamePersonId": person_id,
        "responsibleUserId": 1,
        "deviceAssetIds": [phone_id],
        "platform": "DOUYIN",
        "topic": topic,
        "planStartTime": plan,
        "planEndTime": "2026-10-08T22:00:00+08:00",
    }


def register(auth: dict, body: dict):
    return client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=body,
    )


def report_body() -> dict:
    return {
        "actualStart": "2020-01-15T20:00:00+08:00",
        "actualEnd": "2020-01-15T22:00:00+08:00",
        "durationMinutes": 120,
        "gmv": 10,
        "refundAmount": 0,
        "orderCount": 1,
        "viewerCount": 10,
        "peakOnline": 3,
        "newFans": 1,
        "adCost": 0,
    }


def test_risk_level_boundaries():
    assert risk_level_of(39) == "GREEN"
    assert risk_level_of(40) == "YELLOW"
    assert risk_level_of(69) == "YELLOW"
    assert risk_level_of(70) == "RED"


def test_yellow_approval_and_red_block():
    auth = headers()
    ids = seed_bundle()

    green = register(auth, payload(ids["green_account"], ids["green_person"], ids["phone"], "正常专场"))
    assert green.json()["code"] == 0, green.json()
    assert green.json()["data"]["riskLevel"] == "GREEN"
    assert green.json()["data"]["riskScore"] < 40
    assert green.json()["data"]["sessionStatus"] == "APPROVED"
    green_code = green.json()["data"]["sessionCode"]
    not_yellow = client.put(
        f"/admin-api/ims/live/register/{green_code}/approve",
        headers=auth,
        json={"approve": True, "comment": "不必审批"},
    )
    assert not_yellow.json()["code"] == 1042

    yellow = register(auth, payload(ids["yellow_account"], ids["yellow_person"], ids["phone"], "含违禁词专场"))
    assert yellow.json()["code"] == 0, yellow.json()
    y = yellow.json()["data"]
    assert y["riskLevel"] == "YELLOW"
    assert y["riskScore"] == 45
    assert y["sessionStatus"] == "PENDING_RISK_CHECK"
    y_code = y["sessionCode"]
    risk = client.post(f"/admin-api/ims/live/register/{y_code}/risk-check", headers=auth, json={})
    assert risk.json()["code"] == 1044
    assert risk.json()["data"]["riskLevel"] == "YELLOW"
    blocked = client.put(f"/admin-api/ims/live/register/{y_code}/start", headers=auth)
    assert blocked.json()["code"] == 1044
    still = client.get(f"/admin-api/ims/live/register/{y_code}", headers=auth)
    assert still.json()["data"]["sessionStatus"] == "PENDING_RISK_CHECK"
    approved = client.put(
        f"/admin-api/ims/live/register/{y_code}/approve",
        headers=auth,
        json={"approve": True, "comment": "同意放行"},
    )
    assert approved.json()["code"] == 0, approved.json()
    released = client.get(f"/admin-api/ims/live/register/{y_code}", headers=auth)
    assert released.json()["data"]["sessionStatus"] == "APPROVED"
    assert released.json()["data"]["approverUserId"]
    assert released.json()["data"]["approveComment"] == "同意放行"
    started = client.put(f"/admin-api/ims/live/register/{y_code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()
    live = client.get(f"/admin-api/ims/live/register/{y_code}", headers=auth)
    assert live.json()["data"]["sessionStatus"] == "LIVE"

    red = register(auth, payload(ids["red_account"], ids["red_person"], ids["phone"], "再含违禁词"))
    assert red.json()["code"] == 0, red.json()
    r = red.json()["data"]
    assert r["riskScore"] == 75
    assert r["riskLevel"] == "RED"
    assert r["sessionStatus"] == "PENDING_RISK_CHECK"
    r_code = r["sessionCode"]
    red_risk = client.post(f"/admin-api/ims/live/register/{r_code}/risk-check", headers=auth, json={})
    assert red_risk.json()["code"] == 1043
    assert red_risk.json()["data"]["riskScore"] >= 70
    red_start = client.put(f"/admin-api/ims/live/register/{r_code}/start", headers=auth)
    assert red_start.json()["code"] == 1043
    red_approve = client.put(
        f"/admin-api/ims/live/register/{r_code}/approve",
        headers=auth,
        json={"approve": True, "comment": "不能放行"},
    )
    assert red_approve.json()["code"] == 1043
    red_still = client.get(f"/admin-api/ims/live/register/{r_code}", headers=auth)
    assert red_still.json()["data"]["sessionStatus"] == "PENDING_RISK_CHECK"

    band40 = register(auth, payload(ids["edge40_account"], ids["edge40_person"], ids["phone"], "刚好四十"))
    assert band40.json()["code"] == 0, band40.json()
    assert band40.json()["data"]["riskScore"] == 40
    assert band40.json()["data"]["riskLevel"] == "YELLOW"
    band70 = register(auth, payload(ids["edge70_account"], ids["edge70_person"], ids["idle_phone"], "违禁且停机"))
    assert band70.json()["code"] == 0, band70.json()
    assert band70.json()["data"]["riskScore"] == 70
    assert band70.json()["data"]["riskLevel"] == "RED"


def test_supplement_missing_reason_and_unapproved():
    auth = headers()
    ids = seed_bundle()
    create = payload(ids["green_account"], ids["green_person"], ids["phone"], "历史补录专场", "2020-01-15T20:00:00+08:00")
    missing = client.post(
        "/admin-api/ims/live/ledger/supplement",
        headers=auth,
        json={"sessionCreate": create, "sessionReport": report_body(), "supplementReason": "   "},
    )
    assert missing.json()["code"] == 1049

    created = client.post(
        "/admin-api/ims/live/ledger/supplement",
        headers=auth,
        json={"sessionCreate": create, "sessionReport": report_body(), "supplementReason": "历史漏登，补台账"},
    )
    assert created.json()["code"] == 0, created.json()
    data = created.json()["data"]
    assert data["sessionCode"].startswith("IMS20200115DYS")
    code = data["sessionCode"]
    supplement_id = data["supplementId"]

    start = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert start.json()["code"] == 1049
    confirm = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirm.json()["code"] == 1049
    resubmit = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=report_body())
    assert resubmit.json()["code"] == 1049

    green = register(auth, payload(ids["green_account"], ids["green_person"], ids["phone"], "非补录"))
    assert green.json()["code"] == 0
    wrong = client.put(
        f"/admin-api/ims/live/ledger/supplement/{green.json()['data']['id']}/approve",
        headers=auth,
        json={"approve": True, "comment": "不是补录"},
    )
    assert wrong.json()["code"] == 1042

    approved = client.put(
        f"/admin-api/ims/live/ledger/supplement/{supplement_id}/approve",
        headers=auth,
        json={"approve": True, "comment": "补录通过"},
    )
    assert approved.json()["code"] == 0, approved.json()
    detail = client.get(f"/admin-api/ims/live/ledger/{code}", headers=auth)
    body = detail.json()["data"]
    assert body["isSupplement"] is True
    assert body["supplementReason"] == "历史漏登，补台账"
    assert body["sessionStatus"] == "ENDED"
    assert body["approverUserId"]
    assert body["report"]["entryStatus"] == "CONFIRMED"
    assert body["reportEntryStatus"] == "CONFIRMED"
