"""菜单树补图标名，主键按字符串返回，无权限的菜单不出现。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.context import system_context, use_context
from app.db.session import session_scope
from app.domains.system.model import Menu
from tests.conftest import auth
from tools.seed.apply import apply

API = "/admin-api/ims"


def _walk(nodes):
    found = []
    for node in nodes:
        found.append(node)
        found.extend(_walk(node.get("children") or []))
    return found


def test_me_menu_returns_icon_and_string_id(client):
    headers = auth(client, "u_admin")
    me = client.get(f"{API}/auth/me", headers=headers).json()
    assert me["code"] == 0, me
    nodes = _walk(me["data"]["menus"])
    assert nodes
    assert all(isinstance(node["id"], str) and node["id"] for node in nodes)
    by_path = {node.get("path"): node for node in nodes}
    assert by_path["/ims/workbench"]["icon"] == "star"
    assert by_path["/ims/system/user"]["icon"] == "user"
    assert by_path["/ims/flow/task"]["icon"] == "flow"
    assert by_path["/ims/corp/resource/sim-card"]["icon"] == "phone"
    resource = next(node for node in nodes if node["name"] == "资源管理")
    assert resource["icon"] == "id"
    tree = client.get(f"{API}/system/menu/tree", headers=headers).json()
    assert tree["code"] == 0, tree
    admin_nodes = _walk(tree["data"])
    assert all(isinstance(node["id"], str) for node in admin_nodes)
    assert next(node["icon"] for node in admin_nodes if node.get("path") == "/ims/system/role") == "shield"


def test_me_hides_menus_without_permission(client):
    dept = client.get(f"{API}/auth/me", headers=auth(client, "u_dept")).json()
    names = {node["name"] for node in _walk(dept["data"]["menus"])}
    assert "用户" in names
    assert "角色" not in names
    assert "公司管理" not in names
    none = client.get(f"{API}/auth/me", headers=auth(client, "u_none")).json()
    assert none["code"] == 0, none
    assert none["data"]["menus"] == []


def test_seed_fills_missing_icon_and_keeps_custom(client):
    with session_scope(commit=True) as session:
        menu = session.scalar(select(Menu).where(Menu.path == "/ims/flow/board", Menu.type == "MENU"))
        assert menu is not None
        assert menu.icon == "chart"
        menu.icon = "custom"
        blank = session.scalar(select(Menu).where(Menu.path == "/ims/flow/timeout", Menu.type == "MENU"))
        assert blank is not None
        blank.icon = None
    with session_scope(commit=True):
        with use_context(system_context(1)):
            apply("test")
    with session_scope() as session:
        kept = session.scalar(select(Menu).where(Menu.path == "/ims/flow/board", Menu.type == "MENU"))
        filled = session.scalar(select(Menu).where(Menu.path == "/ims/flow/timeout", Menu.type == "MENU"))
        assert kept.icon == "custom"
        assert filled.icon == "clock"
