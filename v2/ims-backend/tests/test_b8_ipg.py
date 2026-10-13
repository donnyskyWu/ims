"""B8 IP 组：树、成员、绑定、主作者、1223 与作者档案。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.context import system_context, use_context
from app.db.session import session_scope
from app.domains.master.model import IpAnchor, PlatformAccount
from app.domains.system.model import Menu, RoleMenu
from tests.stddata import U_ADMIN, U_RESIGNED
from tests.test_b7_account import API, _account, _company, _err, _headers, _ok, _person

ROUTES = [
    "GET /admin-api/ims/ip-group/tree",
    "GET /admin-api/ims/ip-group/accessible-tree",
    "GET /admin-api/ims/ip-group/list",
    "POST /admin-api/ims/ip-group/create",
    "PUT /admin-api/ims/ip-group/update",
    "DELETE /admin-api/ims/ip-group/delete",
    "GET /admin-api/ims/ip-group/author/page",
    "GET /admin-api/ims/ip-group/author/export",
    "POST /admin-api/ims/ip-group/author",
    "GET /admin-api/ims/ip-group/author/{ident}",
    "PUT /admin-api/ims/ip-group/author/{ident}",
    "PUT /admin-api/ims/ip-group/author/{ident}/status",
    "DELETE /admin-api/ims/ip-group/author/{ident}",
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
    "GET /admin-api/ims/master/selector/ip-group",
    "GET /admin-api/ims/master/selector/author",
]


def _grant(code: str, role_id: int = 203) -> None:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menu = session.scalar(select(Menu).where(Menu.perm_code == code))
            assert menu is not None
            session.add(RoleMenu(role_id=role_id, menu_id=menu.id, tenant_id=1))


def _raw_account(number: str, group_id=None, author_id=None) -> str:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = PlatformAccount(
                code=number,
                name=number,
                account_no=number,
                nickname=number,
                platform="DOUYIN",
                status="IN_POOL",
                ip_group_id=int(group_id) if group_id else None,
                author_user_id=int(author_id) if author_id else None,
                collect_bind_status="UNBOUND",
                recharge_total_fen=0,
            )
            session.add(row)
            session.flush()
            return str(row.id)


def _names(nodes) -> list[str]:
    found = []
    for node in nodes:
        found.append(node["groupName"])
        found.extend(_names(node.get("children") or []))
    return found


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
    missing_route = client.get(f"{API}/authors/1/accounts", headers=_headers(client))
    assert missing_route.status_code == 404


def test_tree_create_duplicate_and_scope(client):
    admin = _headers(client)
    big = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, token="g-big"), json={"groupName": "华东大组", "groupType": "BIG", "level": "S"}))
    assert isinstance(big["id"], str)
    assert big["groupType"] == "BIG"
    small = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="g-small"),
            json={"groupName": "直播小组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    assert small["parentId"] == big["id"]
    _err(client.post(f"{API}/ip-group/create", headers=_headers(client, token="g-dup"), json={"groupName": "华东大组", "groupType": "BIG"}), 1001)
    tree = _ok(client.get(f"{API}/ip-group/tree", headers=admin))
    assert "华东大组" in _names(tree["list"])
    assert "直播小组" in _names(tree["list"])
    _grant("ims:ip-group:query")
    scoped = _ok(client.get(f"{API}/ip-group/accessible-tree", headers=_headers(client, "u_ipg")))
    names = _names(scoped["list"])
    assert "G1" in names
    assert "华东大组" not in names
    listed = _ok(client.get(f"{API}/ip-group/list", headers=admin, params={"keyword": "直播"}))
    assert listed["total"] == 1


def test_members_leader_and_resigned(client):
    admin = _headers(client)
    big = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, token="m-big"), json={"groupName": "成员大组", "groupType": "BIG"}))
    added = _ok(
        client.post(
            f"{API}/ip-group/{big['id']}/members",
            headers=_headers(client, token="m-add"),
            json={"userId": str(U_ADMIN), "position": "OPS_LEADER", "relationType": "PRIMARY", "isLeader": True},
        )
    )
    assert added["isLeader"] is True
    _err(
        client.post(
            f"{API}/ip-group/{big['id']}/members",
            headers=_headers(client, token="m-dup"),
            json={"userId": str(U_ADMIN), "position": "OPERATOR"},
        ),
        1001,
    )
    _err(
        client.post(
            f"{API}/ip-group/{big['id']}/members",
            headers=_headers(client, token="m-out"),
            json={"userId": str(U_RESIGNED), "position": "OPERATOR"},
        ),
        1204,
    )
    removed = _ok(client.delete(f"{API}/ip-group/{big['id']}/members/{added['id']}", headers=admin))
    assert removed["leaderCleared"] is True
    detail = _ok(client.get(f"{API}/ip-group/list", headers=admin, params={"keyword": "成员大组"}))
    assert detail["list"][0]["leaderUserId"] in (None, "")


def test_bind_errors_unbind_and_primary(client):
    admin = _headers(client)
    company = _company(client, admin, "绑定公司")
    person = _person(client, admin, "绑定实名")
    big = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, token="b-big"), json={"groupName": "绑定大组", "groupType": "BIG"}))
    empty = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="b-empty"),
            json={"groupName": "无作者组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    dual = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="b-dual"),
            json={"groupName": "双作者组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    other = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="b-other"),
            json={"groupName": "另一小组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    _err(client.post(f"{API}/ip-group/{big['id']}/accounts", headers=_headers(client, token="b-big-acc"), json={"accountIds": ["1"]}), 1203)
    lone = _raw_account("B8-LONE")
    _err(client.post(f"{API}/ip-group/{empty['id']}/accounts", headers=_headers(client, token="b-1223"), json={"accountIds": [lone]}), 1223)
    first = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token="b-au1"),
            json={"authorName": "作者甲", "authorType": "LIVE", "ipGroupId": dual["id"]},
        )
    )
    second = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token="b-au2"),
            json={"authorName": "作者乙", "authorType": "SHORT_VIDEO", "ipGroupId": dual["id"]},
        )
    )
    blank = _raw_account("B8-BLANK", dual["id"])
    kept = _raw_account("B8-KEPT", dual["id"], first["id"])
    _err(client.post(f"{API}/ip-group/{dual['id']}/accounts", headers=_headers(client, token="b-dual-bind"), json={"accountIds": [blank]}), 1223)
    primary = _ok(client.put(f"{API}/ip-group/{dual['id']}/anchors/{_anchor(dual['id'], second['id'])}/primary", headers=admin))
    assert primary["isPrimary"] is True
    with session_scope() as session:
        with use_context(system_context(1)):
            filled = session.get(PlatformAccount, int(blank))
            manual = session.get(PlatformAccount, int(kept))
            assert str(filled.author_user_id) == str(second["id"])
            assert str(manual.author_user_id) == str(first["id"])
    home = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token="b-home"),
            json={"authorName": "唯一作者", "authorType": "BOTH", "ipGroupId": other["id"]},
        )
    )
    owned = _account(client, admin, company["id"], person["id"], nickname="已归属", token="b-owned", ipGroupId=other["id"])
    assert owned["authorUserId"] == home["id"]
    _err(
        client.post(f"{API}/ip-group/{empty['id']}/accounts", headers=_headers(client, token="b-cross"), json={"accountIds": [owned["id"]]}),
        1205,
    )
    unbound = _ok(client.delete(f"{API}/ip-group/{other['id']}/accounts/{owned['id']}", headers=admin))
    assert unbound["authorKept"] is True
    assert "作者引用仍保留" in unbound["message"]
    again = _ok(client.get(f"{API}/corp/account/{owned['id']}", headers=admin))
    assert again["authorUserId"] == home["id"]
    assert again["ipGroupId"] in (None, "")
    rows = _ok(client.get(f"{API}/ip-group/{dual['id']}/anchors", headers=admin))["list"]
    current = next(item for item in rows if item["isPrimary"])
    dropped = _ok(client.delete(f"{API}/ip-group/{dual['id']}/anchors/{current['id']}", headers=admin))
    assert dropped["needPrimary"] is True
    left = _ok(client.get(f"{API}/ip-group/{dual['id']}/anchors", headers=admin))["list"]
    assert left
    assert all(item["isPrimary"] is False for item in left)


def test_delete_group_author_pool_and_stats(client):
    admin = _headers(client)
    company = _company(client, admin, "作者公司")
    person = _person(client, admin, "作者实名")
    big = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, token="d-big"), json={"groupName": "统计大组", "groupType": "BIG"}))
    small = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="d-small"),
            json={"groupName": "统计小组", "groupType": "SMALL", "parentId": big["id"]},
        )
    )
    _err(client.delete(f"{API}/ip-group/delete", headers=admin, params={"id": big["id"]}), 1206)
    empty_stats = _ok(client.get(f"{API}/ip-group/{big['id']}/stats", headers=admin))
    assert empty_stats["mock"] is True
    assert empty_stats["memberCount"] == 0
    assert empty_stats["fans"] == 0
    author = _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token="d-au"),
            json={"authorName": "档案作者", "authorType": "SHORT_VIDEO", "ipGroupId": small["id"]},
        )
    )
    account = _account(client, admin, company["id"], person["id"], nickname="档案号", token="d-acc", ipGroupId=small["id"])
    _err(client.delete(f"{API}/ip-group/author/{author['id']}", headers=admin), 1502)
    other = _ok(client.post(f"{API}/ip-group/create", headers=_headers(client, token="d-other"), json={"groupName": "对照大组", "groupType": "BIG"}))
    other_small = _ok(
        client.post(
            f"{API}/ip-group/create",
            headers=_headers(client, token="d-os"),
            json={"groupName": "对照小组", "groupType": "SMALL", "parentId": other["id"]},
        )
    )
    _ok(
        client.post(
            f"{API}/ip-group/author",
            headers=_headers(client, token="d-au2"),
            json={"authorName": "对照作者", "authorType": "LIVE", "ipGroupId": other_small["id"]},
        )
    )
    foreign = _account(client, admin, company["id"], person["id"], nickname="对照号", token="d-acc2", ipGroupId=other_small["id"])
    _err(client.put(f"{API}/ip-group/author/{author['id']}", headers=admin, json={"primaryAccountId": foreign["id"]}), 1127)
    page = _ok(client.get(f"{API}/ip-group/author/page", headers=admin, params={"keyword": "档案"}))
    assert page["total"] >= 1
    _ok(client.put(f"{API}/ip-group/author/{author['id']}/status", headers=admin, json={"status": "DISABLED"}))
    _ok(client.get(f"{API}/ip-group/author/export", headers=admin))
    counted = _ok(client.get(f"{API}/ip-group/{small['id']}/stats", headers=admin))
    assert counted["accountCount"] >= 1
    assert counted["authorCount"] >= 1
    assert counted["mockLabel"]
    _err(client.get(f"{API}/master/selector/ip-group", headers=admin, params={"keyword": "没有这组"}), 1221)
    _err(client.get(f"{API}/master/selector/author", headers=admin, params={"keyword": "没有作者"}), 1221)
    _err(
        client.post(
            f"{API}/corp/account",
            headers=_headers(client, token="d-nogroup"),
            json={"platform": "DOUYIN", "nickname": "缺组", "companyId": company["id"], "realnameId": person["id"]},
        ),
        1001,
    )
    big_accounts = _ok(client.get(f"{API}/ip-group/{big['id']}/accounts", headers=admin))
    assert big_accounts["readOnly"] is True


def _anchor(group_id: str, author_id: str) -> str:
    with session_scope() as session:
        with use_context(system_context(1)):
            row = session.scalar(select(IpAnchor).where(IpAnchor.ip_group_id == int(group_id), IpAnchor.author_id == int(author_id)))
            assert row is not None
            return str(row.id)


def test_seed_refuses_production():
    import pytest

    from tools.e2e_seed.b8 import assert_allowed

    with pytest.raises(RuntimeError):
        assert_allowed("prod")


def test_platform_create_materializes_single_author(client):
    admin = _headers(client)
    company = _company(client, admin, "物化公司")
    person = _person(client, admin, "物化实名")
    created = _account(client, admin, company["id"], person["id"], nickname="物化号", token="mat-1")
    assert created["ipGroupId"]
    assert created["authorName"] == "回补作者"
    assert created["ipGroupText"]
    edited = _ok(client.put(f"{API}/corp/account/{created['id']}", headers=admin, json={"nickname": "物化改名"}))
    assert edited["nickname"] == "物化改名"
    assert edited["authorUserId"] == created["authorUserId"]
