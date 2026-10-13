"""B9 直播：37 个接口、风控边界、下播、告警与 Football 只读。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.clock import now_naive
from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import session_scope
from app.domains.device.model import AssetLedger
from app.domains.live import risk
from app.domains.master.model import Cert, LiveSession, PlatformAccount, Realname
from app.domains.system.model import User, UserRole
from tests.conftest import auth
from tests.stddata import PASSWORD, U_ADMIN

API = "/admin-api/ims"
ROUTES = [
    "GET /admin-api/ims/live/sessions/stats",
    "GET /admin-api/ims/live/sessions/list",
    "GET /admin-api/ims/live/sessions/{code}",
    "GET /admin-api/ims/live/sessions/{code}/metrics",
    "PUT /admin-api/ims/live/sessions/{code}/football-room",
    "POST /admin-api/ims/live/sessions/{code}/football-sync",
    "GET /admin-api/ims/live/register/realname-precheck",
    "POST /admin-api/ims/live/register",
    "PUT /admin-api/ims/live/register/{code}",
    "POST /admin-api/ims/live/register/{code}/risk-check",
    "PUT /admin-api/ims/live/register/{code}/approve",
    "PUT /admin-api/ims/live/register/{code}/start",
    "PUT /admin-api/ims/live/register/{code}/end",
    "PUT /admin-api/ims/live/register/{code}/cancel",
    "GET /admin-api/ims/live/report/{code}",
    "PUT /admin-api/ims/live/report/{code}",
    "POST /admin-api/ims/live/report/{code}",
    "PUT /admin-api/ims/live/report/{code}/confirm",
    "POST /admin-api/ims/live/report/{code}/correction",
    "GET /admin-api/ims/live/report/{code}/corrections",
    "GET /admin-api/ims/live/report/pending",
    "POST /admin-api/ims/live/report/{code}/remind",
    "GET /admin-api/ims/live/alarm/records",
    "GET /admin-api/ims/live/alarm/record/{ident}",
    "PUT /admin-api/ims/live/alarm/record/{ident}/handle",
    "GET /admin-api/ims/live/alarm/rules",
    "POST /admin-api/ims/live/alarm/rule",
    "PUT /admin-api/ims/live/alarm/rule/{ident}",
    "PUT /admin-api/ims/live/alarm/rule/{ident}/status",
    "DELETE /admin-api/ims/live/alarm/rule/{ident}",
    "GET /admin-api/ims/live/alarm/stats",
    "GET /admin-api/ims/live/ledger/list",
    "POST /admin-api/ims/live/ledger/supplement",
    "GET /admin-api/ims/live/ledger/supplement/{ident}",
    "PUT /admin-api/ims/live/ledger/supplement/{ident}",
    "PUT /admin-api/ims/live/ledger/supplement/{ident}/approve",
    "GET /admin-api/ims/live/ledger/export",
]


def _headers(client, username="u_admin", token=None):
    bag = getattr(client, "_b9_headers", None)
    if bag is None:
        bag = {}
        client._b9_headers = bag
    if username not in bag:
        bag[username] = auth(client, username)
    headers = dict(bag[username])
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


def _world():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            if session.get(User, 3019) is None:
                session.add(
                    User(
                        id=3019,
                        username="u_live_r4",
                        nickname="运营管理者",
                        password_hash=hash_password(PASSWORD),
                        status="ACTIVE",
                        tenant_id=1,
                        source="LOCAL",
                    )
                )
                session.flush()
                session.add(UserRole(user_id=3019, role_id=104, source="MANUAL", tenant_id=1))
            person = Realname(name="开播实名", status="ENABLED", tenant_id=1)
            locked = Realname(name="过期实名", status="ENABLED", tenant_id=1)
            session.add(person)
            session.add(locked)
            session.flush()
            session.add(Cert(name="有效证", cert_type="ID_CARD", status="EFFECTIVE", realname_id=person.id, expire_date=datetime(2099, 1, 1).date(), tenant_id=1))
            session.add(Cert(name="过期证", cert_type="ID_CARD", status="EXPIRED", realname_id=locked.id, expire_date=datetime(2020, 1, 1).date(), tenant_id=1))
            account = PlatformAccount(
                name="在用抖音",
                nickname="在用抖音",
                account_no="AC-DYS-USE",
                code="AC-DYS-USE",
                platform="DOUYIN",
                status="IN_USE",
                realname_id=person.id,
                owner_user_id=U_ADMIN,
                recharge_total_fen=10000,
                tenant_id=1,
            )
            session.add(account)
            asset = AssetLedger(asset_code="AS-LV-1", asset_name="直播机", asset_type="LIVE", status="IN_USE", owner_user_id=U_ADMIN, tenant_id=1)
            session.add(asset)
            session.flush()
            return {"person": person.id, "locked": locked.id, "account": account.id, "asset": asset.id}


def _span(hours=2):
    start = now_naive() + timedelta(hours=hours)
    end = start + timedelta(hours=2)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _register(client, world, token, topic, person=None):
    start, end = _span()
    return _ok(
        client.post(
            f"{API}/live/register",
            headers=_headers(client, token=token),
            json={
                "accountId": world["account"],
                "realnameId": person or world["person"],
                "responsibleUserId": U_ADMIN,
                "assetIds": [world["asset"]],
                "topic": topic,
                "planStartTime": start,
                "planEndTime": end,
            },
        )
    )


def test_route_inventory(client):
    from app.main import _iter_routes

    found = set()
    for path, route in _iter_routes(client.app):
        for method in getattr(route, "methods", set()) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            found.add(f"{method} {path}")
    missing = [item for item in ROUTES if item not in found]
    assert missing == [], missing
    assert "GET /admin-api/ims/live/register/list" not in found
    from app.services.jobs import JOBS

    names = {item.name for item in JOBS}
    assert {"live_auto_end", "live_report_overdue", "live_alarm_escalate", "live_football_sync_retry"} <= names


def test_risk_boundaries_and_flow(client):
    assert risk.level_of(39) == "GREEN"
    assert risk.level_of(40) == "YELLOW"
    assert risk.level_of(69) == "YELLOW"
    assert risk.level_of(70) == "RED"
    world = _world()
    precheck = _ok(client.get(f"{API}/live/register/realname-precheck", headers=_headers(client), params={"realnameId": world["locked"]}))
    assert "判红" in precheck["message"] or "过期" in precheck["message"]
    red = _register(client, world, "b9-red", "红级场次", person=world["locked"])
    assert red["riskLevel"] == "RED"
    assert red["sessionStatus"] == "PENDING_RISK_CHECK"
    _err(client.put(f"{API}/live/register/{red['sessionCode']}/start", headers=_headers(client), json={}), 1043)
    green = _register(client, world, "b9-green", "绿级场次")
    again = _register(client, world, "b9-green", "绿级场次")
    assert again["sessionCode"] == green["sessionCode"]
    assert green["riskLevel"] == "GREEN"
    assert green["sessionStatus"] == "APPROVED"
    assert str(green["sessionCode"]).startswith("IMS")
    started = _ok(client.put(f"{API}/live/register/{green['sessionCode']}/start", headers=_headers(client), json={}))
    assert started["sessionStatus"] == "LIVE"
    ended = _ok(client.put(f"{API}/live/register/{green['sessionCode']}/end", headers=_headers(client), json={}))
    assert ended["sessionStatus"] == "ENDED"
    ended_at = now_naive() - timedelta(minutes=5)
    body = {
        "actualStart": (ended_at - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "actualEnd": ended_at.strftime("%Y-%m-%d %H:%M:%S"),
        "gmv": "100.00",
        "orderCount": 4,
        "viewerCount": 10,
        "peakOnline": 8,
        "newFans": 1,
        "refundAmount": "0.00",
        "adCost": "20.00",
    }
    _ok(client.put(f"{API}/live/report/{green['sessionCode']}", headers=_headers(client), json={"gmv": "1.00"}))
    submitted = _ok(client.post(f"{API}/live/report/{green['sessionCode']}", headers=_headers(client, token="b9-report"), json=body))
    assert submitted["entryStatus"] == "SUBMITTED"
    assert submitted["unitPrice"] == "25.00"
    _err(client.put(f"{API}/live/report/{green['sessionCode']}/confirm", headers=_headers(client), json={}), 1049)
    confirmed = _ok(client.put(f"{API}/live/report/{green['sessionCode']}/confirm", headers=_headers(client, "u_live_r4"), json={}))
    assert confirmed["entryStatus"] == "CONFIRMED"
    corrected = _ok(
        client.post(
            f"{API}/live/report/{green['sessionCode']}/correction",
            headers=_headers(client),
            json={"gmv": "120.00", "reason": "核准后更正"},
        )
    )
    assert corrected["entryStatus"] == "CONFIRMED"
    assert corrected["version"] == 2
    yellow = _register(client, world, "b9-yellow", "含测试违禁词")
    assert yellow["riskLevel"] == "YELLOW"
    _err(client.put(f"{API}/live/register/{yellow['sessionCode']}/start", headers=_headers(client), json={}), 1044)
    approved = _ok(
        client.put(
            f"{API}/live/register/{yellow['sessionCode']}/approve",
            headers=_headers(client, "u_live_r4"),
            json={"approve": True, "opinion": "同意放行"},
        )
    )
    assert approved["sessionStatus"] == "APPROVED"


def test_alarm_and_supplement_and_room(client):
    world = _world()
    _err(
        client.post(
            f"{API}/live/alarm/rule",
            headers=_headers(client),
            json={"ruleName": "坏规则", "ruleType": "THRESHOLD", "metric": "VIEWER_DROP", "operator": "PCT_DROP", "threshold": 30, "windowMinutes": 0, "level": "2", "notifyUserIds": [U_ADMIN]},
        ),
        1050,
    )
    created = _ok(
        client.post(
            f"{API}/live/alarm/rule",
            headers=_headers(client),
            json={"ruleName": "场观测试", "ruleType": "THRESHOLD", "metric": "VIEWER_DROP", "operator": "PCT_DROP", "threshold": 20, "windowMinutes": 10, "level": "2", "notifyUserIds": [U_ADMIN], "status": "ENABLED"},
        )
    )
    green = _register(client, world, "b9-alarm", "告警场次")
    _ok(client.put(f"{API}/live/register/{green['sessionCode']}/start", headers=_headers(client), json={}))
    from app.domains.live.alarm import accept

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.query(LiveSession).filter(LiveSession.session_code == green["sessionCode"]).one()
            accept(row.id, "VIEWER_DROP", value=Decimal("30"))
            accept(row.id, "VIEWER_DROP", value=Decimal("30"))
    records = _ok(client.get(f"{API}/live/alarm/records", headers=_headers(client), params={"sessionCode": green["sessionCode"]}))
    assert records["total"] == 1
    assert records["list"][0]["mergeCount"] == 2
    _ok(client.put(f"{API}/live/alarm/record/{records['list'][0]['id']}/handle", headers=_headers(client, "u_live_r4"), json={"action": "HANDLED", "remark": "已核对"}))
    headers = _headers(client)
    headers["Content-Type"] = "application/json"
    _err(
        client.request(
            "DELETE",
            f"{API}/live/alarm/rule/{created['id']}",
            headers=headers,
            content=json.dumps({"confirmName": "不对"}),
        ),
        1001,
    )
    past = (now_naive() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    past_end = (now_naive() - timedelta(days=2) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    sheet = _ok(
        client.post(
            f"{API}/live/ledger/supplement",
            headers=_headers(client, "u_live_r4", token="b9-sup"),
            json={
                "register": {
                    "accountId": world["account"],
                    "realnameId": world["person"],
                    "responsibleUserId": 3019,
                    "assetIds": [world["asset"]],
                    "topic": "补录主题",
                    "planStartTime": past,
                    "planEndTime": past_end,
                },
                "report": {
                    "actualStart": past,
                    "actualEnd": past_end,
                    "gmv": "10.00",
                    "orderCount": 1,
                    "viewerCount": 2,
                    "peakOnline": 2,
                    "newFans": 0,
                    "refundAmount": "0.00",
                    "adCost": "1.00",
                },
                "supplementReason": "历史补录",
            },
        )
    )
    _err(client.put(f"{API}/live/ledger/supplement/{sheet['id']}/approve", headers=_headers(client, "u_live_r4"), json={"approve": True, "opinion": "自己批"}), 1049)
    from tools.football_stub.live_room_seed import ensure

    ensure()
    _ok(client.put(f"{API}/live/sessions/{green['sessionCode']}/football-room", headers=_headers(client), json={"roomId": "9001"}))
    _err(client.put(f"{API}/live/sessions/{green['sessionCode']}/football-room", headers=_headers(client), json={"roomId": "9999"}), 1041)
    _err(client.put(f"{API}/live/sessions/{green['sessionCode']}/football-room", headers=_headers(client), json={"roomId": "9003"}), 1041)
    _err(client.put(f"{API}/live/sessions/{green['sessionCode']}/football-room", headers=_headers(client), json={"roomId": "9004"}), 1041)


def test_count_by_author_sql():
    from app.integrations.football_live.reader import COUNT_BY_AUTHOR_SQL, FootballLiveReader

    assert COUNT_BY_AUTHOR_SQL == "SELECT count(1) AS cnt FROM live_room WHERE author_id = ? AND create_time BETWEEN ? AND ?"
    seen = {}

    def executor(sql, params):
        seen["sql"] = sql
        return [4]

    assert FootballLiveReader(executor=executor).count_by_author(7, "2026-01-01", "2026-01-02") == 4
    assert seen["sql"] == COUNT_BY_AUTHOR_SQL
