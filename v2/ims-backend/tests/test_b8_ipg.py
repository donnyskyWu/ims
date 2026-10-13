"""B8 IP 组：树、成员、账号绑定、1223、作者与选择器。"""
from __future__ import annotations

from tests.conftest import auth
from tests.test_b7_account import credit

API = "/admin-api/ims"
ROUTES = [
    "GET /admin-api/ims/ip-group/tree",
    "GET /admin-api/ims/ip-group/accessible-tree",
    "GET /admin-api/ims/ip-group/list",
    "POST /admin-api/ims/ip-group/create",
    "PUT /admin-api/ims/ip-group/update",
    "DELETE /admin-api/ims/ip-group/delete",
    "GET /admin-api/ims/ip-group/{ident}/members",
    "POST /admin-api/ims/ip-group/{ident}/members",
    "PUT /admin-api/ims/ip-group/{ident}/members/{member_id}",
    "DELETE /admin-api/ims/ip-group/{ident}/members/{member_id}",
    "GET /admin-api/ims/ip-group/{ident}/accounts",
    "POST /admin-api/ims/ip-group/{ident}/accounts",
    "DELETE /admin-api/ims/ip-group/{ident}/accounts/{account_id}",
    "GET /admin-api/ims/ip-group/{ident}/anchors",
    "POST /admin-api/ims/ip-group/{ident}/anchors",
    "PUT /admin-api/ims/ip-group/{ident}/anchors/{rel_id}/primary",
    "DELETE /admin-api/ims/ip-group/{ident}/anchors/{rel_id}",
    "GET /admin-api/ims/ip-group/{ident}/stats",
    "GET /admin-api/ims/ip-group/author/page",
    "POST /admin-api/ims/ip-group/author",
    "GET /admin-api/ims/ip-group/author/{ident}",
    "PUT /admin-api/ims/ip-group/author/{ident}",
    "PUT /admin-api/ims/ip-group/author/{ident}/status",
    "DELETE /admin-api/ims/ip-group/author/{ident}",
    "GET /admin-api/ims/ip-group/author/export",
    "GET /admin-api/ims/master/selector/ip-group",
    "GET /admin-api/ims/master/selector/author",
]


def _headers(client, token=None):
    # 同一用户最多 3 个会话，重复登录会把最早的令牌挤下线（1003）。
    headers = getattr(client, "_b8_headers", None)
    if headers is None:
        headers = auth(client, "u_admin")
        client._b8_headers = headers
    headers = dict(headers)
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


def _company(client, headers):
    return _ok(
        client.post(
            f"{API}/corp/resource/company",
            headers={**headers, "X-Client-Token": "b8-co"},
            json={"name": "IP组公司", "creditCode": credit("91310000MA1FL2XW8"), "wxOfficialCapacity": 5},
        )
    )


def _person(client, headers):
    return _ok(client.post(f"{API}/corp/resource/realname", headers=headers, json={"name": "IP组实名", "idType": "ID_CARD", "idNo": "110101199003078515"}))


def _account(client, headers, company_id, person_id, group_id, token, nickname):
    return _ok(
        client.post(
            f"{API}/corp/account",
            headers={**headers, "X-Client-Token": token},
            json={"platform": "DOUYIN", "nickname": nickname, "companyId": company_id, "realnameId": person_id, "ipGroupId": group_id},
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
    assert len(ROUTES) == 27


def test_group_member_author_bind_and_1223(client):
    headers = _headers(client)
    big = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, "b8-big"), json={"groupName": "测试大组甲", "groupType": "BIG", "level": "S"}))
    assert big["groupTypeLabel"] == "大组"
    assert big["memberCount"] == 0
    small = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, "b8-small"),
            json={"groupName": "测试小组甲", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    assert small["groupTypeLabel"] == "小组"
    _err(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, "b8-dup"),
            json={"groupName": "测试小组甲", "groupType": "SMALL", "parentId": big["id"]},
        ),
        1001,
    )
    tree = _ok(client.get(f"{API}/ip-group/tree", headers=headers))
    assert tree["list"]
    edited = _ok(client.put(f"{API}/ip-group/update", headers=headers, json={"id": small["id"], "remark": "备注甲", "level": "A"}))
    assert edited["remark"] == "备注甲"
    assert edited["groupType"] == "SMALL"
    member = _ok(
        client.post(
            f"{API}/ip-group/{small['id']}/members",
            headers=_headers(client, "b8-mem"),
            json={"userId": "1002", "position": "LIVE_OPERATOR", "relationType": "PRIMARY"},
        )
    )
    assert member["positionLabel"] == "直播运营"
    _err(
        client.post(
            f"{API}/ip-group/{small['id']}/members",
            headers=_headers(client, "b8-mem2"),
            json={"userId": "1002", "position": "OPERATOR", "relationType": "PART_TIME"},
        ),
        1001,
    )
    _err(
        client.post(
            f"{API}/ip-group/{small['id']}/members",
            headers=_headers(client, "b8-resigned"),
            json={"userId": "1008", "position": "OPERATOR", "relationType": "PRIMARY"},
        ),
        1204,
    )
    author = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, "b8-au"),
            json={"authorName": "作者-单", "authorType": "SHORT_VIDEO", "ipGroupId": small["id"]},
        )
    )
    assert str(author["authorNo"]).startswith("AU-")
    _ok(client.post(f"{API}/ip-group/{small['id']}/anchors", headers=_headers(client, "b8-anc"), json={"authorId": author["id"]}))
    company = _company(client, headers)
    person = _person(client, headers)
    _err(
        client.post(
            f"{API}/corp/account",
            headers=_headers(client, "b8-no-group"),
            json={"platform": "DOUYIN", "nickname": "无组", "companyId": company["id"], "realnameId": person["id"]},
        ),
        1001,
    )
    _err(
        client.post(
            f"{API}/corp/account",
            headers=_headers(client, "b8-big-acc"),
            json={"platform": "DOUYIN", "nickname": "大组号", "companyId": company["id"], "realnameId": person["id"], "ipGroupId": big["id"]},
        ),
        1203,
    )
    bound = _account(client, headers, company["id"], person["id"], small["id"], "b8-acc", "小组号")
    assert bound["authorName"] == "作者-单"
    assert "测试大组甲" in bound["ipGroupText"]
    assert "测试小组甲" in bound["ipGroupText"]
    _err(client.post(f"{API}/ip-group/{big['id']}/accounts", headers=_headers(client, "b8-big-bind"), json={"accountIds": [bound["id"]]}), 1203)
    other = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, "b8-small-b"),
            json={"groupName": "测试小组乙", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    dual_a = _ok(client.post(f"{API}/ip-group/author", headers=_headers(client, "b8-a"), json={"authorName": "作者-双A", "authorType": "LIVE", "ipGroupId": other["id"]}))
    dual_b = _ok(client.post(f"{API}/ip-group/author", headers=_headers(client, "b8-b"), json={"authorName": "作者-双B", "authorType": "LIVE", "ipGroupId": other["id"]}))
    _ok(client.post(f"{API}/ip-group/{other['id']}/anchors", headers=_headers(client, "b8-anc-a"), json={"authorIds": [dual_a["id"], dual_b["id"]]}))
    pool = _ok(
        client.post(
            f"{API}/corp/resource/company",
            headers={**headers, "X-Client-Token": "b8-co2"},
            json={"name": "IP组公司乙", "creditCode": credit("91310000MA1FL2XW9"), "wxOfficialCapacity": 5},
        )
    )
    # 小组乙无主作者，登记账号应 1223。先造一个临时单作者组给容量校验之外的账号，再直接绑池账号。
    loose = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, "b8-loose"),
            json={"groupName": "临时小组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    loose_author = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, "b8-loose-au"),
            json={"authorName": "临时作者", "authorType": "OTHER", "ipGroupId": loose["id"]},
        )
    )
    _ok(client.post(f"{API}/ip-group/{loose['id']}/anchors", headers=_headers(client, "b8-loose-anc"), json={"authorId": loose_author["id"]}))
    movable = _account(client, headers, pool["id"], person["id"], loose["id"], "b8-move", "待改绑")
    _ok(client.delete(f"{API}/ip-group/{loose['id']}/accounts/{movable['id']}", headers=headers))
    from app.core.context import system_context, use_context
    from app.db.session import session_scope
    from app.domains.master.model import PlatformAccount

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.get(PlatformAccount, int(movable["id"]))
            row.author_user_id = None
    _err(client.post(f"{API}/ip-group/{other['id']}/accounts", headers=_headers(client, "b8-1223"), json={"accountIds": [movable["id"]]}), 1223)
    primary = _ok(client.get(f"{API}/ip-group/{other['id']}/anchors", headers=headers))
    rel = next(item for item in primary["list"] if item["authorName"] == "作者-双A")
    _ok(client.put(f"{API}/ip-group/{other['id']}/anchors/{rel['id']}/primary", headers=headers))
    rebound = _ok(client.post(f"{API}/ip-group/{other['id']}/accounts", headers=_headers(client, "b8-rebind"), json={"accountIds": [movable["id"]]}))
    assert rebound["list"][0]["authorName"] == "作者-双A"
    _err(client.post(f"{API}/ip-group/{small['id']}/accounts", headers=_headers(client, "b8-cross"), json={"accountIds": [movable["id"]]}), 1205)
    freed = _ok(client.delete(f"{API}/ip-group/{other['id']}/accounts/{movable['id']}", headers=headers))
    assert freed["ipGroupText"] == "—"
    assert freed["authorName"] == "作者-双A"
    assert "保留" in freed["hint"]
    stats = _ok(client.get(f"{API}/ip-group/{small['id']}/stats", headers=headers))
    assert stats["memberCount"] >= 1
    assert stats["mock"] is True
    assert "示意" in stats["mockLabel"]
    _err(client.delete(f"{API}/ip-group/delete?id={small['id']}", headers=headers), 1206)
    empty = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, "b8-empty"), json={"groupName": "空小组", "groupType": "SMALL", "parentId": big["id"]}))
    assert _ok(client.get(f"{API}/ip-group/{empty['id']}/stats", headers=headers))["accountCount"] == 0
    _ok(client.delete(f"{API}/ip-group/delete?id={empty['id']}", headers=headers))
    page = _ok(client.get(f"{API}/ip-group/author/page", headers=headers, params={"keyword": "作者-单"}))
    assert page["total"] >= 1
    detail = _ok(client.get(f"{API}/ip-group/author/{author['id']}", headers=headers))
    assert detail["groups"]
    _err(
        client.put(
            f"{API}/ip-group/author/{author['id']}",
            headers=headers,
            json={"primaryAccountId": movable["id"]},
        ),
        1127,
    )
    exported = _ok(client.get(f"{API}/ip-group/author/export", headers=headers))
    assert exported["fileKey"].endswith(".xlsx")
    options = _ok(client.get(f"{API}/master/selector/ip-group", headers=headers, params={"onlySmall": "true", "keyword": "小组甲"}))
    assert any("测试大组甲 / 测试小组甲" == item["label"] or "测试小组甲" in item["label"] for item in options["list"])
    _ok(client.put(f"{API}/ip-group/author/{loose_author['id']}/status", headers=headers, json={"status": "DISABLED"}))
    hidden = _ok(client.get(f"{API}/master/selector/author", headers=headers, params={"keyword": "临时作者"}))
    assert all(item["authorName"] != "临时作者" for item in hidden["list"])
    _err(client.delete(f"{API}/ip-group/author/{author['id']}", headers=headers), 1502)
