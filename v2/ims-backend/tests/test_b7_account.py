"""B7 公司账号：登记、领用、流转、归还、充值、采集与时间线。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.context import system_context, use_context
from app.core.events import events
from app.core.security import hash_password
from app.db.session import session_scope
from app.domains.master.model import PlatformAccount
from app.domains.system.model import Dept, User, UserRole
from app.services.jobs import JOBS
from tests.conftest import auth
from tests.stddata import D1, PASSWORD, U_ADMIN, U_DEPT, U_RESIGNED

API = "/admin-api/ims"
_CC = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_CW = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
ROUTES = [
    "GET /admin-api/ims/corp/account/page",
    "GET /admin-api/ims/corp/account/{ident}",
    "POST /admin-api/ims/corp/account",
    "PUT /admin-api/ims/corp/account/{ident}",
    "PUT /admin-api/ims/corp/account/{ident}/cancel",
    "DELETE /admin-api/ims/corp/account/{ident}",
    "GET /admin-api/ims/corp/account/export",
    "PUT /admin-api/ims/corp/account/{ident}/asset-bind",
    "GET /admin-api/ims/corp/account/{ident}/assets",
    "GET /admin-api/ims/master/selector/account",
    "GET /admin-api/ims/corp/account/personal/page",
    "GET /admin-api/ims/corp/account/personal/{ident}",
    "POST /admin-api/ims/corp/account/personal",
    "PUT /admin-api/ims/corp/account/personal/{ident}",
    "PUT /admin-api/ims/corp/account/personal/{ident}/status",
    "DELETE /admin-api/ims/corp/account/personal/{ident}",
    "GET /admin-api/ims/corp/account/personal/export",
    "POST /admin-api/ims/account/apply",
    "GET /admin-api/ims/account/apply/page",
    "GET /admin-api/ims/account/apply/{ident}",
    "PUT /admin-api/ims/account/apply/{ident}/confirm",
    "POST /admin-api/ims/account/transfer",
    "GET /admin-api/ims/account/transfer/page",
    "PUT /admin-api/ims/account/transfer/{ident}/confirm",
    "PUT /admin-api/ims/account/transfer/{ident}/revoke",
    "POST /admin-api/ims/account/{ident}/unfreeze",
    "POST /admin-api/ims/account/return/generate",
    "GET /admin-api/ims/account/return/page",
    "GET /admin-api/ims/account/return/{ident}",
    "PUT /admin-api/ims/account/return/item/{item_id}",
    "PUT /admin-api/ims/account/return/{ident}/close",
    "PUT /admin-api/ims/account/return/{ident}/suspend",
    "POST /admin-api/ims/account/recharge",
    "GET /admin-api/ims/account/recharge/page",
    "PUT /admin-api/ims/account/recharge/{ident}",
    "POST /admin-api/ims/account/recharge/verify",
    "GET /admin-api/ims/account/recharge/summary",
    "GET /admin-api/ims/account/recharge/export",
    "GET /admin-api/ims/account/recharge/overview",
    "PUT /admin-api/ims/corp/account/{ident}/collect/credential",
    "DELETE /admin-api/ims/corp/account/{ident}/collect/credential",
    "POST /admin-api/ims/corp/account/{ident}/collect/probe",
    "POST /admin-api/ims/corp/account/{ident}/collect/import",
    "POST /admin-api/ims/corp/account/{ident}/collect/qr-login",
    "GET /admin-api/ims/account/timeline/{account_id}",
    "GET /admin-api/ims/account/timeline/{account_id}/export",
    "GET /admin-api/ims/account/timeline/events",
]


_ID_W = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
_ID_M = "10X98765432"


def _id_card(body: str) -> str:
    return body[:17] + _ID_M[sum(int(ch) * weight for ch, weight in zip(body[:17], _ID_W)) % 11]


def credit(body: str) -> str:
    text = body[:17].upper()
    total = sum(_CC.index(char) * weight for char, weight in zip(text, _CW))
    return text + _CC[(31 - total % 31) % 31]


def _headers(client, username="u_admin", token=None, base=None):
    state = getattr(client, "_b7_auth_state", None)
    if state is None:
        state = {"user": None, "headers": None}
        client._b7_auth_state = state
    if base is not None and state["user"] == username:
        headers = dict(base)
    elif state["user"] != username or state["headers"] is None:
        state["headers"] = auth(client, username)
        state["user"] = username
        headers = dict(state["headers"])
    else:
        headers = dict(state["headers"])
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


def _company(client, headers, name="星河账号"):
    return _ok(
        client.post(
            f"{API}/corp/resource/company",
            headers=headers,
            json={"name": name, "creditCode": credit("91310000MA1FL2XW3"), "wxOfficialCapacity": 5, "clientToken": "b7-co"},
        )
    )


def _person(client, headers, name="账号实名", number="110101199003078515"):
    return _ok(client.post(f"{API}/corp/resource/realname", headers=headers, json={"name": name, "idType": "ID_CARD", "idNo": number}))


def _pool(client, headers):
    cached = getattr(client, "_b8_pool", None)
    if cached:
        return cached
    big = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token=f"b8-pool-big-{id(client)}", base=headers),
            json={"groupName": "回补大组", "groupType": "BIG"},
        )
    )
    small = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token=f"b8-pool-small-{id(client)}", base=headers),
            json={"groupName": "回补小组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    author = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token=f"b8-pool-author-{id(client)}", base=headers),
            json={"authorName": "回补作者", "authorType": "SHORT_VIDEO", "ipGroupId": small["id"]},
        )
    )
    client._b8_pool = {"ipGroupId": small["id"], "authorId": author["id"]}
    return client._b8_pool


def _account(client, headers, company_id, realname_id, **extra):
    body = {"platform": "DOUYIN", "nickname": "星河抖音", "companyId": company_id, "realnameId": realname_id}
    body.update(extra)
    token = extra.pop("token", "b7-acc")
    body.pop("token", None)
    if not body.get("ipGroupId"):
        body["ipGroupId"] = _pool(client, headers)["ipGroupId"]
    return _ok(client.post(f"{API}/corp/account", headers=_headers(client, token=token, base=headers), json=body))


def _leader():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept = session.get(Dept, D1)
            dept.leader_user_id = U_ADMIN
            if session.get(User, 3011) is None:
                session.add(
                    User(
                        id=3011,
                        username="u_apply",
                        nickname="领用申请人",
                        password_hash=hash_password(PASSWORD),
                        status="ACTIVE",
                        tenant_id=1,
                        main_dept_id=D1,
                        source="LOCAL",
                    )
                )
                session.flush()
                session.add(UserRole(user_id=3011, role_id=105, source="MANUAL", tenant_id=1))


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
    assert len(ROUTES) == 47


def test_register_capacity_edit_delete_and_personal(client):
    admin = _headers(client)
    company = _company(client, admin)
    person = _person(client, admin)
    other = _person(client, admin, "另一实名", _id_card("11010119900307483"))
    created = _account(client, admin, company["id"], person["id"], token="acc-1")
    assert created["status"] == "IN_POOL"
    assert created["accountNo"]
    assert isinstance(created["id"], str)
    again = _account(client, admin, company["id"], person["id"], token="acc-1", nickname="不会再建")
    assert again["id"] == created["id"]
    aliased = _account(client, admin, company["id"], person["id"], platform="WECHAT_OFFICIAL", nickname="公众号甲", token="acc-mp")
    assert aliased["platform"] == "WECHAT_MP"
    detail = _ok(client.get(f"{API}/corp/resource/company/{company['id']}", headers=admin))
    assert any(item["platform"] == "WECHAT_MP" for item in detail["accountSummary"])
    sim = _ok(
        client.post(
            f"{API}/corp/resource/sim-card",
            headers=admin,
            json={"phoneNumber": "13900003001", "operator": "CMCC", "realnameId": other["id"], "clientToken": "b7-sim"},
        )
    )
    warned = _account(client, admin, company["id"], person["id"], simCardId=sim["id"], nickname="实名不一致", token="acc-sim")
    assert "REALNAME_MISMATCH" in warned["warnings"]
    sim_detail = _ok(client.get(f"{API}/corp/resource/sim-card/{sim['id']}", headers=admin))
    assert "REALNAME_MISMATCH" in sim_detail["warnings"]
    assert sim_detail["linkedAccounts"]
    edited = _ok(client.put(f"{API}/corp/account/{created['id']}", headers=admin, json={"nickname": "星河改名"}))
    assert edited["nickname"] == "星河改名"
    page = _ok(client.get(f"{API}/corp/account/page", headers=admin, params={"platform": "DOUYIN"}))
    assert page["total"] >= 1
    exported = _ok(client.get(f"{API}/corp/account/export", headers=admin, params={"platform": "DOUYIN"}))
    assert exported["fileKey"].endswith(".xlsx")
    _ok(client.delete(f"{API}/corp/account/{created['id']}", headers=admin))
    _err(client.get(f"{API}/corp/account/{created['id']}", headers=admin), 1504)
    tight = _company(client, _headers(client, token="co-tight"), name="容量公司")
    # 容量公司复用幂等令牌会返回第一家。单独再建。
    tight = _ok(
        client.post(
            f"{API}/corp/resource/company",
            headers=_headers(client, token="co-tight"),
            json={"name": "容量公司", "creditCode": credit("91310000MA1FL2XW4"), "wxOfficialCapacity": 1},
        )
    )
    _account(client, admin, tight["id"], person["id"], platform="WECHAT_MP", nickname="容量一", token="cap-1")
    _err(
        client.post(
            f"{API}/corp/account",
            headers=_headers(client, token="cap-2"),
            json={"platform": "WECHAT_MP", "nickname": "容量二", "companyId": tight["id"], "realnameId": person["id"], "ipGroupId": client._b8_pool["ipGroupId"]},
        ),
        1222,
    )
    personal = _ok(
        client.post(
            f"{API}/corp/account/personal",
            headers=_headers(client, token="per-1"),
            json={"accountType": "WECHAT", "nickname": "私人微信", "mobile": "13800138000"},
        )
    )
    assert personal["accountNo"].startswith("PA-")
    assert personal["mobileMask"] != "13800138000"
    assert "13800138000" not in str(personal)
    stopped = _ok(client.put(f"{API}/corp/account/personal/{personal['id']}/status", headers=admin, json={"status": "DISABLED"}))
    assert stopped["status"] == "DISABLED"
    _ok(client.get(f"{API}/corp/account/personal/export", headers=admin))
    _ok(client.delete(f"{API}/corp/account/personal/{personal['id']}", headers=admin))


def test_apply_transfer_recall_and_unfreeze(client):
    _leader()
    admin = _headers(client)
    applicant = _headers(client, "u_apply")
    company = _company(client, admin, "领用公司")
    person = _person(client, admin, "领用实名")
    account = _account(client, admin, company["id"], person["id"], nickname="待领用", token="borrow-acc")
    frozen = _account(client, admin, company["id"], person["id"], nickname="已冻结号", token="frozen-acc")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.get(PlatformAccount, int(frozen["id"]))
            row.status = "FROZEN"
    _err(
        client.post(
            f"{API}/account/apply",
            headers=_headers(client, "u_apply", token="apply-frozen"),
            json={"accountId": frozen["id"], "purpose": "试用", "planStart": "2026-10-01", "planEnd": "2026-10-20"},
        ),
        1022,
    )
    opened = _ok(
        client.post(
            f"{API}/account/apply",
            headers=_headers(client, "u_apply", token="apply-1"),
            json={"accountId": account["id"], "purpose": "直播", "planStart": "2026-10-01", "planEnd": "2026-10-20"},
        )
    )
    assert opened["applyStatus"] == "PENDING_APPROVAL"
    _err(
        client.post(
            f"{API}/account/apply",
            headers=_headers(client, "u_apply", token="apply-dup"),
            json={"accountId": account["id"], "purpose": "再领", "planStart": "2026-10-02", "planEnd": "2026-10-21"},
        ),
        1021,
    )
    todo = _ok(client.get(f"{API}/flow/task/my-todo", headers=admin))
    task_id = todo["list"][0]["id"]
    _ok(client.put(f"{API}/flow/task/{task_id}/handle", headers=admin, json={"action": "APPROVE", "comment": "同意"}))
    pending = _ok(client.get(f"{API}/account/apply/{opened['id']}", headers=applicant))
    assert pending["applyStatus"] == "PENDING_HANDOVER"
    _err(client.put(f"{API}/account/apply/{opened['id']}/confirm", headers=applicant, json={"handover": {"passwordReset": False}}), 1001)
    confirmed = _ok(client.put(f"{API}/account/apply/{opened['id']}/confirm", headers=applicant, json={"handover": {"passwordReset": True, "note": "已交接"}}))
    assert confirmed["applyStatus"] == "APPROVED"
    assert confirmed["passwordReset"] is True
    assert "password" not in str(confirmed["handoverNote"]).lower()
    owned = _ok(client.get(f"{API}/corp/account/{account['id']}", headers=admin))
    assert owned["status"] == "IN_USE"
    _err(client.put(f"{API}/corp/account/{account['id']}/cancel", headers=admin, json={"reason": "停用"}), 1001)
    moved = _ok(
        client.post(
            f"{API}/account/transfer",
            headers=_headers(client, "u_apply", token="tr-1"),
            json={"transferType": "TRANSFER", "accountId": account["id"], "toUserId": U_ADMIN, "reasonType": "TRANSFER_POSITION", "remark": "交给管理"},
        )
    )
    assert moved["status"] == "PENDING_CONFIRM"
    accepted = _ok(client.put(f"{API}/account/transfer/{moved['id']}/confirm", headers=admin, json={"accept": True}))
    assert accepted["status"] == "EFFECTIVE"
    recalled = _ok(
        client.post(
            f"{API}/account/transfer",
            headers=_headers(client, token="recall-1"),
            json={"transferType": "RECALL", "accountId": account["id"], "remark": "收回"},
        )
    )
    assert recalled["status"] == "EFFECTIVE"
    frozen_row = _ok(client.get(f"{API}/corp/account/{account['id']}", headers=admin))
    assert frozen_row["status"] == "FROZEN"
    assert not frozen_row["ownerUserId"]
    pooled = _ok(client.post(f"{API}/account/{account['id']}/unfreeze", headers=admin, json={"remark": "回池"}))
    assert pooled["status"] == "IN_POOL"
    line = _ok(client.get(f"{API}/account/timeline/{account['id']}", headers=admin))
    kinds = {item["eventType"] for item in line["list"]}
    assert {"REGISTER", "APPLY", "TRANSFER", "FREEZE", "UNFREEZE"} <= kinds
    pdf = _ok(client.get(f"{API}/account/timeline/{account['id']}/export", headers=admin))
    assert pdf["contentType"] == "application/pdf"
    assert pdf["filename"].endswith(".pdf")


def test_return_does_not_unfreeze_and_dispute_blocks_close(client):
    admin = _headers(client)
    company = _company(client, admin, "归还公司")
    person = _person(client, admin, "归还实名")
    account = _account(client, admin, company["id"], person["id"], nickname="离职号", token="ret-acc")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.get(PlatformAccount, int(account["id"]))
            row.status = "IN_USE"
            row.owner_user_id = U_RESIGNED
    events.publish("user.resigned", {"userId": U_DEPT})
    empty = _ok(client.get(f"{API}/account/return/page", headers=admin))
    assert empty["total"] == 0
    events.publish("user.resigned", {"userId": U_RESIGNED})
    listed = _ok(client.get(f"{API}/account/return/page", headers=admin))
    assert listed["total"] == 1
    order = _ok(client.get(f"{API}/account/return/{listed['list'][0]['id']}", headers=admin))
    item = order["items"][0]
    disputed = _ok(client.put(f"{API}/account/return/item/{item['id']}", headers=admin, json={"action": "DISPUTE", "remark": "对不上"}))
    _err(client.put(f"{API}/account/return/{order['id']}/close", headers=admin), 1024)
    _ok(client.put(f"{API}/account/return/item/{item['id']}", headers=admin, json={"action": "RETURN"}))
    closed = _ok(client.put(f"{API}/account/return/{order['id']}/close", headers=admin))
    assert closed["status"] == "CLOSED"
    stayed = _ok(client.get(f"{API}/corp/account/{account['id']}", headers=admin))
    assert stayed["status"] == "FROZEN"
    assert disputed["items"][0]["itemStatus"] == "DISPUTED"


def test_recharge_collect_selector_bind(client):
    admin = _headers(client)
    company = _company(client, admin, "充值公司")
    person = _person(client, admin, "充值实名")
    account = _account(client, admin, company["id"], person["id"], nickname="充值号", token="rch-acc")
    _err(
        client.post(
            f"{API}/account/recharge",
            headers=_headers(client, token="rch-big"),
            json={"accountId": account["id"], "amount": "5000.01", "channel": "ALIPAY", "rechargeDate": "2026-10-12"},
        ),
        1025,
    )
    saved = _ok(
        client.post(
            f"{API}/account/recharge",
            headers=_headers(client, token="rch-ok"),
            json={"accountId": account["id"], "amount": "100.00", "channel": "ALIPAY", "rechargeDate": "2026-10-12", "voucherFileKey": "ACCOUNT/1/202610/voucher.pdf"},
        )
    )
    assert saved["amount"] == "100.00"
    checked = _ok(client.post(f"{API}/account/recharge/verify", headers=admin, json={"month": "2026-10", "simulate": "diff"}))
    assert checked["hintCode"] == 1026
    overview = _ok(client.get(f"{API}/account/recharge/overview", headers=admin))
    assert "pendingCount" in overview
    summary = _ok(client.get(f"{API}/account/recharge/summary", headers=admin, params={"dimension": "platform"}))
    assert summary["list"]
    secret = "session-cookie-value"
    stored = _ok(client.put(f"{API}/corp/account/{account['id']}/collect/credential", headers=admin, json={"cookie": secret}))
    assert stored["cookieMask"] == "******"
    assert secret not in str(stored)
    assert stored["collectBindStatus"] == "UNBOUND"
    probed = _ok(client.post(f"{API}/corp/account/{account['id']}/collect/probe", headers=admin, json={}))
    assert probed["collectBindStatus"] == "BOUND"
    options = _ok(client.get(f"{API}/master/selector/account", headers=admin, params={"platform": "DOUYIN", "keyword": "充值"}))
    assert options["list"]
    asset = _ok(
        client.post(
            f"{API}/asset/ledger",
            headers=_headers(client, token="asset-b7"),
            json={"assetName": "补光灯", "scope": "office", "purchaseDate": "2026-10-01", "ownerUserId": U_DEPT},
        )
    )
    _ok(client.put(f"{API}/corp/account/{account['id']}/asset-bind", headers=admin, json={"assetIds": [asset["id"]]}))
    assets = _ok(client.get(f"{API}/corp/account/{account['id']}/assets", headers=admin))
    assert assets[0]["assetId"] == asset["id"]
    reverse = _ok(client.get(f"{API}/asset/reverse/by-account/{account['id']}", headers=admin))
    assert reverse["list"]
    ledger = _ok(client.get(f"{API}/asset/ledger/{asset['id']}", headers=admin))
    assert ledger["accountCount"] == 1
    names = {item.name for item in JOBS}
    assert {"account_apply_idle_remind", "account_return_overdue"} <= names
    from app.domains.account.apply import idle_scan
    from app.domains.account.returns import overdue_scan

    with session_scope() as _session:
        with use_context(system_context(1)):
            assert idle_scan() == 0
            assert overdue_scan() == 0
