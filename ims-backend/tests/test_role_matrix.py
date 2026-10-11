import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.menu_catalog import CATALOG
from app.models import Role, RolePerm
from app.role_matrix import ACCOUNTS, grants_for, l1_names

client = TestClient(app)

ANALYSIS = {
    "/ims/analysis/query-tool": "查询工具",
    "/ims/bi/query": "自定义查询",
    "/ims/bi/report/preview": "预览与下钻",
    "/ims/dc/trace": "穿透查询",
    "/ims/dc/dashboard": "全链路看板",
    "/ims/eff": "组织人效",
}


def login(username="admin", password="Admin@123") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_menu_tree_covers_business_and_buttons():
    headers = login()
    tree = client.get("/admin-api/ims/system/menu/tree", headers=headers).json()["data"]

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.get("children") or [])

    flat = list(walk(tree))
    codes = {node["permCode"] for node in flat if node.get("permCode")}
    names = {node["name"] for node in flat}
    assert "menu:live:query" in codes
    assert "menu:contentSop:query" in codes
    assert "menu:flow:query" in codes
    assert "perf:mine" in codes
    assert "menu:bi0Metric:query" in codes
    assert "menu:biList:add" in codes
    assert "数据报表" in names
    assert "数据指标" in names
    assert "组织人效" in names
    assert len(codes) > 80


def test_train_alert_report_and_hidden_content_pages():
    assert "menu:trainMaterial:query" in grants_for("R2")
    assert "menu:trainTask:query" in grants_for("R2")
    assert "menu:contentTopic:query" not in grants_for("R2")
    assert "menu:contentPublish:query" not in grants_for("R2")
    r2 = login("tc_r2")
    for path in ("/admin-api/ims/train/material/list", "/admin-api/ims/train/material/cates", "/admin-api/ims/train/task/list"):
        res = client.get(path, headers=r2)
        assert res.status_code == 200, path
        assert res.json()["code"] == 0, (path, res.json())
    denied_topic = client.get("/admin-api/ims/content/topic/list", headers=r2)
    denied_publish = client.get("/admin-api/ims/content/publish/list", headers=r2)
    assert denied_topic.status_code == 403 and denied_topic.json()["code"] == 403
    assert denied_publish.status_code == 403 and denied_publish.json()["code"] == 403

    director = login("tc_r4")
    rule = client.get("/admin-api/ims/alert/rule/list", headers=director)
    templates = client.get("/admin-api/ims/report/template/list", headers=director)
    assert rule.status_code == 200 and rule.json()["code"] == 0
    assert templates.status_code == 200 and templates.json()["code"] == 0
    saved = client.post(
        "/admin-api/ims/report/template",
        headers=director,
        json={
            "templateName": "业务模板",
            "periodType": "DAILY",
            "deadlineRule": "22:00",
            "deptName": "运营",
            "businessLine": "BUSINESS",
            "status": "ENABLED",
            "fieldsSchema": [{"fieldKey": "metric_value", "fieldLabel": "数值", "fieldType": "NUMBER", "required": True}],
            "assignees": [],
        },
    )
    assert saved.status_code == 200 and saved.json()["code"] == 0, saved.json()
    topic = client.get("/admin-api/ims/content/topic/list", headers=director)
    publish = client.get("/admin-api/ims/content/publish/list", headers=director)
    assert topic.status_code == 200 and topic.json()["code"] == 0
    assert publish.status_code == 200 and publish.json()["code"] == 0

    finance = client.get("/admin-api/ims/auth/access", headers=login("tc_r3")).json()["data"]["routes"]
    short = client.get("/admin-api/ims/auth/access", headers=login("tc_r6")).json()["data"]["routes"]
    director_routes = client.get("/admin-api/ims/auth/access", headers=director).json()["data"]["routes"]
    assert [route for route in ("/ims/alert/rule", "/ims/alert/live", "/ims/alert/stats", "/ims/alert/escalate") if route in finance] == [
        "/ims/alert/rule",
        "/ims/alert/live",
        "/ims/alert/stats",
        "/ims/alert/escalate",
    ]
    assert "/ims/alert/rule" not in short and "/ims/alert/stats" not in short
    assert "/ims/alert/live" in short and "/ims/alert/escalate" in short
    assert "/ims/report/template" in director_routes
    assert "/ims/report/submission" in director_routes or "/ims/report/stat" in director_routes

    opened = {}
    for key in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11"):
        codes = grants_for(key)
        opened[key] = (
            "menu:contentTopic:query" in codes,
            "menu:contentPublish:query" in codes,
        )
    assert opened == {
        "R1": (True, True),
        "R2": (False, False),
        "R3": (False, False),
        "R4": (True, True),
        "R5": (True, False),
        "R6": (True, True),
        "R7": (True, False),
        "R8": (False, True),
        "R9": (True, True),
        "R10": (False, False),
        "R11": (False, False),
    }


def test_air_center_matrix_for_r11_r6_and_r4():
    asset = client.get("/admin-api/ims/auth/access", headers=login("tc_r11")).json()["data"]
    assert asset["admin"] is False
    assert asset["fullCatalog"] is False
    air_routes = [route for route in asset["routes"] if route.startswith("/ims/air/")]
    assert air_routes == ["/ims/air/cfg", "/ims/air/expert", "/ims/air/kb", "/ims/air/skill"]
    assert "/ims/system/user" not in asset["routes"]
    assert "/ims/live/sessions" not in asset["routes"]
    assert l1_names("R11") == ["工作台", "AI 资源中心"]

    short = client.get("/admin-api/ims/auth/access", headers=login("tc_r6")).json()["data"]
    assert not any(route.startswith("/ims/air/") for route in short["routes"])
    denied = client.get("/admin-api/ims/air/skill/list", headers=login("tc_r6"))
    assert denied.status_code == 403 and denied.json()["code"] == 403

    listed = client.get("/admin-api/ims/air/skill/list", headers=login("tc_r4"))
    assert listed.status_code == 200 and listed.json()["code"] == 0, listed.json()
    names = [row["skillName"] for row in listed.json()["data"]["list"]]
    assert "运营技能" in names


def test_r7_and_r10_cannot_open_ops_board():
    assert "menu:home:query" not in grants_for("R7")
    assert "menu:home:query" not in grants_for("R10")
    assert "auth:workbench:query" in grants_for("R7")
    assert "auth:workbench:query" in grants_for("R10")
    assert "menu:home:query" in grants_for("R6")
    assert "menu:flow:query" not in grants_for("R7")
    for username in ("tc_r7", "tc_r10"):
        access = client.get("/admin-api/ims/auth/access", headers=login(username)).json()["data"]
        assert "/ims/home" not in access["routes"]
        assert "/ims/workbench" in access["routes"]
        for path in ("/admin-api/ims/home/dashboard", "/admin-api/ims/home/todos", "/admin-api/ims/home/shortcuts"):
            denied = client.get(path, headers=login(username))
            assert denied.status_code == 403, path
            assert denied.json()["code"] == 403, (path, denied.json())
            assert denied.json()["msg"] == "无操作权限"
    kept = client.get("/admin-api/ims/home/dashboard", headers=login("tc_r6"))
    assert kept.status_code == 200 and kept.json()["code"] == 0, kept.json()
    director = client.get("/admin-api/ims/auth/access", headers=login("tc_r4")).json()["data"]
    assert "/ims/home" in director["routes"]


def test_r5_analysis_menu_is_prd_subset():
    codes = grants_for("R5")
    assert "menu:queryTool:query" in codes
    assert "menu:biPreview:query" in codes
    assert "menu:dc:query" in codes
    assert "menu:dcDashboard:query" in codes
    assert "menu:bi0Query:query" not in codes
    assert "menu:eff:query" not in codes
    assert "menu:bi0Metric:query" not in codes
    assert "menu:bi0Analysis:query" not in codes
    assert "menu:biList:query" not in codes or codes["menu:biList:query"]
    assert "menu:biList:query" in codes


def test_r8_has_no_report_menu_and_r4_can_open_flow_and_review():
    assert "menu:biList:query" not in grants_for("R8")
    assert "menu:bi0Report:query" not in grants_for("R8")
    assert "menu:bi0Metric:query" not in grants_for("R8")
    assert "menu:flow:query" in grants_for("R4")
    assert "menu:dailyReview:query" in grants_for("R4")
    headers = login("tc_r8")
    access = client.get("/admin-api/ims/auth/access", headers=headers).json()["data"]
    assert "/ims/bi/report/list" not in access["routes"]
    assert "/ims/bi/report" not in access["routes"]
    denied = client.get("/admin-api/ims/bi/report/list", headers=headers)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403

    director = login("tc_r4")
    for path in ("/admin-api/ims/flow/instance/list", "/admin-api/ims/flow/task/my-todo", "/admin-api/ims/meet/review/queue"):
        res = client.get(path, headers=director)
        assert res.status_code == 200, path
        assert res.json()["code"] == 0, (path, res.json())


def test_tc_accounts_follow_matrix_and_custom_role_survives():
    headers = login()
    custom = client.post(
        "/admin-api/ims/system/role",
        headers=headers,
        json={"roleName": "自定义勿动", "roleKey": "custom:keep", "dataScope": "SELF"},
    )
    assert custom.json()["code"] == 0, custom.json()
    role_id = custom.json()["data"]["id"]
    client.put(
        f"/admin-api/ims/system/role/{role_id}/perm-detail",
        headers=headers,
        json={"permDetail": {"system:user:query": "R"}},
    )
    from app.main import init_db

    init_db()
    db = SessionLocal()
    try:
        role = db.scalar(select(Role).where(Role.role_key == "custom:keep", Role.deleted == 0))
        assert role is not None
        held = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role.id)).all())
        assert held == {"system:user:query"}
    finally:
        db.close()

    seen = {}
    for username, _nick, role_key, _mobile in ACCOUNTS:
        access = client.get("/admin-api/ims/auth/access", headers=login(username)).json()["data"]
        assert access["admin"] is False
        assert access["fullCatalog"] is False
        routes = set(access["routes"])
        if username in ("tc_r5", "tc_r5b"):
            analysis = [ANALYSIS[route] for route in ANALYSIS if route in routes]
            assert analysis == ["查询工具", "预览与下钻", "穿透查询", "全链路看板"]
            assert "/ims/bi/metric" not in routes
            assert "/ims/bi/analysis" not in routes
        if username == "tc_r8":
            assert "/ims/bi/report/list" not in routes
        seen[username] = l1_names(role_key)
    assert "数据决策" in seen["tc_r5"]
    assert "数据决策" not in seen["tc_r8"]
    assert "协同与成长" in seen["tc_r4"]


def test_catalog_has_button_rows():
    buttons = [row for row in CATALOG if row[3] == "BUTTON"]
    assert len(buttons) >= 100
