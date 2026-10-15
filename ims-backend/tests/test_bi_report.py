import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_bi_report_catalog_and_preview():
    auth = headers()
    catalog = client.get("/admin-api/ims/bi/report/catalog", headers=auth)
    assert catalog.json()["code"] == 0
    reports = catalog.json()["data"]["reports"]
    assert len(reports) == 8

    preview = client.get("/admin-api/ims/bi/report/unified-account", headers=auth)
    assert preview.json()["code"] == 0
    data = preview.json()["data"]
    assert data["rows"]
    assert data["kpis"]
    assert data["trend"]
    assert "平台" in data["columns"]
    assert "metric" not in data["columns"]
    status = client.get("/admin-api/ims/bi/report/account-status", headers=auth).json()["data"]
    assert status["rows"]
    assert "状态" in status["columns"]
    assert "note" not in status["columns"]
    alert = client.get("/admin-api/ims/bi/report/account-alert", headers=auth).json()["data"]
    total_kpi = next(item for item in alert["kpis"] if item["metric"] == "合计")
    assert total_kpi["value"] == alert["total"]
    assert total_kpi["value"] == 3


def test_bi_report_manage_create_list():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 测试报表", "reportType": "DASHBOARD", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["reportType"] == "DASHBOARD"

    listed = client.get("/admin-api/ims/bi/report/list", headers=auth, params={"keyword": "W9", "pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert any(r["id"] == rid for r in listed.json()["data"]["list"])

    cats = client.get("/admin-api/ims/bi/report/categories", headers=auth)
    assert cats.json()["code"] == 0
    assert cats.json()["data"]["categories"]


def test_bi_legacy_category_falls_under_uncategorized():
    """BUG-C079：分类不在树上的报表（如 RPT-0001~0004 的「内容分析」）查询时归入未分类，不改原值。"""
    auth = headers()
    legacy = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "BUG-C079 内容分析遗留", "reportType": "REPORT", "category": "内容分析"},
    )
    assert legacy.json()["code"] == 0
    rid = legacy.json()["data"]["id"]
    assert legacy.json()["data"]["category"] == "内容分析"

    daily = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "BUG-C079 日报对照", "reportType": "REPORT", "category": "日报"},
    )
    assert daily.json()["code"] == 0
    daily_id = daily.json()["data"]["id"]

    def ids(category: str, keyword: str) -> set[int]:
        listed = client.get(
            "/admin-api/ims/bi/report/list",
            headers=auth,
            params={"category": category, "keyword": keyword, "pageNo": 1, "pageSize": 20},
        )
        assert listed.json()["code"] == 0
        return {item["id"] for item in listed.json()["data"]["list"]}

    assert rid in ids("未分类", "BUG-C079 内容分析遗留")
    assert daily_id not in ids("未分类", "BUG-C079")
    assert rid not in ids("内容", "BUG-C079")
    assert rid not in ids("运营", "BUG-C079")
    assert rid not in ids("财务", "BUG-C079")
    assert rid not in ids("日报", "BUG-C079")
    assert daily_id in ids("日报", "BUG-C079 日报对照")
    assert daily_id in ids("运营", "BUG-C079 日报对照")

    detail = client.get(f"/admin-api/ims/bi/report/{rid}", headers=auth)
    assert detail.json()["data"]["category"] == "内容分析"


def test_bi_category_tree_import_and_scope_filter():
    auth = headers()
    cats = client.get("/admin-api/ims/bi/report/categories", headers=auth).json()["data"]["categories"]
    names = {item["name"] for item in cats}
    assert {"运营", "内容", "财务", "未分类"} <= names
    ops = next(item for item in cats if item["name"] == "运营")
    assert {child["name"] for child in ops["children"]} == {"日报", "周报", "大屏"}

    blank = client.post("/admin-api/ims/bi/report/category", headers=auth, json={"action": "add", "name": "  "})
    assert blank.json()["code"] == 1001

    added = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC分类", "parentId": 0},
    )
    assert added.json()["code"] == 0
    parent_id = added.json()["data"]["id"]
    child = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC子类", "parentId": parent_id},
    )
    assert child.json()["code"] == 0
    too_deep = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC三级", "parentId": child.json()["data"]["id"]},
    )
    assert too_deep.json()["code"] == 1001
    assert "两级" in too_deep.json()["msg"]

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "分类迁移报表", "reportType": "REPORT", "category": "TC分类", "shareScope": "ALL"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["shareScope"] == "ALL"
    noted = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={
            "reportName": "口径说明报表",
            "reportType": "REPORT",
            "category": "日报",
            "shareScope": "PRIVATE",
            "metricNote": "GMV 为支付金额",
        },
    )
    assert noted.json()["code"] == 0
    assert noted.json()["data"]["status"] == "DRAFT"
    assert noted.json()["data"]["metricNote"] == "GMV 为支付金额"
    assert noted.json()["data"]["shareScope"] == "PRIVATE"

    scoped = client.get(
        "/admin-api/ims/bi/report/list",
        headers=auth,
        params={"shareScope": "ALL", "status": "DRAFT", "category": "TC分类"},
    )
    assert any(item["id"] == rid for item in scoped.json()["data"]["list"])
    hidden = client.get("/admin-api/ims/bi/report/list", headers=auth, params={"shareScope": "PRIVATE", "keyword": "分类迁移报表"})
    assert all(item["id"] != rid for item in hidden.json()["data"]["list"])

    child_report = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "子类报表", "reportType": "REPORT", "category": "TC子类", "shareScope": "PRIVATE"},
    )
    assert child_report.json()["code"] == 0
    child_rid = child_report.json()["data"]["id"]

    removed = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "delete", "categoryId": parent_id},
    )
    assert removed.json()["code"] == 1001
    assert removed.json()["msg"] == "该分类下有 2 个报表，请先移动"
    detail = client.get(f"/admin-api/ims/bi/report/{rid}", headers=auth)
    assert detail.json()["data"]["category"] == "TC分类"
    assert client.get(f"/admin-api/ims/bi/report/{child_rid}", headers=auth).json()["data"]["category"] == "TC子类"

    uncategorized = next(item for item in cats if item["name"] == "未分类")
    blocked_delete = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "delete", "categoryId": uncategorized["id"]},
    )
    assert blocked_delete.json()["code"] == 1001
    assert blocked_delete.json()["msg"] == "未分类不能删除"
    blocked_rename = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "rename", "categoryId": uncategorized["id"], "name": "其他"},
    )
    assert blocked_rename.json()["code"] == 1001
    assert blocked_rename.json()["msg"] == "未分类不能改名"

    assert client.delete(f"/admin-api/ims/bi/report/{rid}", headers=auth).json()["code"] == 0
    still_blocked = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "delete", "categoryId": parent_id},
    )
    assert still_blocked.json()["msg"] == "该分类下有 1 个报表，请先移动"
    assert client.delete(f"/admin-api/ims/bi/report/{child_rid}", headers=auth).json()["code"] == 0
    cleared = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "delete", "categoryId": parent_id},
    )
    assert cleared.json()["code"] == 0
    assert cleared.json()["data"]["message"] == "分类已删除"
    left = client.get("/admin-api/ims/bi/report/categories", headers=auth).json()["data"]["categories"]
    assert all(item["name"] != "TC分类" for item in left)
    assert any(item["name"] == "未分类" for item in left)

    bad = client.post("/admin-api/ims/bi/report/import", headers=auth, json={"template": {"comps": []}})
    assert bad.json()["code"] == 1001
    imported = client.post(
        "/admin-api/ims/bi/report/import",
        headers=auth,
        json={
            "template": {
                "reportName": "导入日报",
                "reportType": "REPORT",
                "category": "日报",
                "comps": [{"id": "c1", "type": "KPI", "title": "GMV", "dataset": "missing_ds"}],
            }
        },
    )
    assert imported.json()["code"] == 0
    assert imported.json()["data"]["compCount"] == 1
    assert imported.json()["data"]["warnings"]
    assert imported.json()["data"]["reportName"] == "导入日报(导入)"


def test_bi_publish_config_grants_tc_r6_and_card_actions():
    from app.bi_br212_seed import _clone_admin_perms
    from app.core import SessionLocal
    from app.models import Role, User, UserRole
    from app.scope import refresh_user_scope
    from app.security import hash_password

    auth = headers()
    db = SessionLocal()
    try:
        viewer = User(
            username="tc_r6",
            nickname="主播R6",
            mobile="13900003636",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(viewer)
        db.flush()
        role = Role(
            role_name="R6本域",
            role_key="bi:tc-r6",
            data_scope="SELF",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        _clone_admin_perms(db, role.id)
        db.add(UserRole(user_id=viewer.id, role_id=role.id, tenant_id=0))
        refresh_user_scope(db, viewer.id)
        db.commit()
        viewer_id = viewer.id
    finally:
        db.close()

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "可见日报", "reportType": "REPORT", "category": "日报"},
    )
    rid = created.json()["data"]["id"]
    bare = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert bare.json()["code"] == 0
    assert bare.json()["data"]["version"] == 1

    published = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={
            "dest": "CENTER",
            "shareScope": "SPECIFIED",
            "opPerm": "READONLY",
            "rowPerm": "INHERIT",
            "viewerIds": [viewer_id],
        },
    )
    body = published.json()
    assert body["code"] == 0
    assert body["data"]["version"] == 2
    assert body["data"]["shareScope"] == "SPECIFIED"
    assert body["data"]["opPerm"] == "READONLY"

    token = client.post("/admin-api/ims/auth/login", json={"username": "tc_r6", "password": "Admin@123"}).json()["data"]["accessToken"]
    viewer_headers = {"Authorization": f"Bearer {token}"}
    listed = client.get("/admin-api/ims/bi/report/list", headers=viewer_headers, params={"keyword": "可见日报"})
    assert any(item["reportName"] == "可见日报" for item in listed.json()["data"]["list"])
    hidden = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "私有草稿", "reportType": "REPORT", "category": "日报"},
    )
    private_id = hidden.json()["data"]["id"]
    missed = client.get("/admin-api/ims/bi/report/list", headers=viewer_headers, params={"keyword": "私有草稿"})
    assert all(item["id"] != private_id for item in missed.json()["data"]["list"])

    copied = client.post(f"/admin-api/ims/bi/report/{rid}/copy", headers=auth)
    assert copied.json()["code"] == 0
    assert copied.json()["data"]["reportName"].endswith("副本")
    assert copied.json()["data"]["version"] == 1
    assert copied.json()["data"]["status"] == "DRAFT"
    exported = client.get(f"/admin-api/ims/bi/report/{rid}/export", headers=auth)
    assert exported.json()["data"]["template"]["reportName"] == "可见日报"
    records = client.get(f"/admin-api/ims/bi/report/{rid}/publish/list", headers=auth)
    assert len(records.json()["data"]["list"]) >= 1
    shared = next(item for item in listed.json()["data"]["list"] if item["reportName"] == "可见日报")
    assert shared["canEdit"] is False
    assert shared["canCopy"] is False
    assert shared["canDelete"] is False
    assert shared["canExport"] is False
    denied = client.post(f"/admin-api/ims/bi/report/{rid}/copy", headers=viewer_headers)
    assert denied.json()["code"] == 1008
    denied_save = client.put(
        f"/admin-api/ims/bi/report/{rid}",
        headers=viewer_headers,
        json={"reportName": "越权改名", "keepVersion": True},
    )
    assert denied_save.status_code == 403
    assert denied_save.json()["code"] == 403
    denied_export = client.get(f"/admin-api/ims/bi/report/{rid}/export", headers=viewer_headers)
    assert denied_export.json()["code"] == 1008
    denied_delete = client.delete(f"/admin-api/ims/bi/report/{rid}", headers=viewer_headers)
    assert denied_delete.status_code == 403
    assert denied_delete.json()["code"] == 403
    viewer_perm = client.get("/admin-api/ims/bi/report/edit-perm", headers=viewer_headers)
    assert viewer_perm.json()["data"]["allowed"] is False
    assert viewer_perm.json()["data"]["permCode"] == "bi:report:edit"
    admin_perm = client.get("/admin-api/ims/bi/report/edit-perm", headers=auth)
    assert admin_perm.json()["data"]["allowed"] is True
    menu_pub = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={
            "dests": ["MENU"],
            "menuName": "只读菜单",
            "shareScope": "SPECIFIED",
            "opPerm": "READONLY",
            "viewerIds": [viewer_id],
        },
    )
    assert menu_pub.json()["code"] == 0
    menus = client.get("/admin-api/ims/bi/report/published-menus", headers=viewer_headers)
    side = next(item for item in menus.json()["data"]["list"] if item["menuName"] == "只读菜单")
    assert side["canDesign"] is False
    assert "/preview" in side["path"]
    assert "designer" not in side["path"]


def test_bi_republish_menu_access_and_version():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "菜单日报", "reportType": "REPORT", "category": "日报"},
    )
    rid = created.json()["data"]["id"]
    first = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={"dests": ["CENTER"], "shareScope": "ALL", "opPerm": "COPY", "accessType": "SSO", "expireDays": 14},
    )
    assert first.json()["code"] == 0
    assert first.json()["data"]["version"] == 1
    assert first.json()["data"]["shareScope"] == "ALL"
    assert first.json()["data"]["opPerm"] == "COPY"
    assert first.json()["data"]["accessType"] == "SSO"
    assert first.json()["data"]["expireDays"] == 14
    short = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={"dests": ["MENU"], "menuName": "菜单日报", "expireDays": 3},
    )
    assert short.json()["code"] == 1197
    again = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={
            "dests": ["CENTER", "MENU"],
            "menuName": "菜单日报",
            "shareScope": "ALL",
            "opPerm": "COPY",
            "accessType": "SHARE_LINK",
            "expireDays": 7,
            "passwordEnabled": True,
            "password": "Secret123",
        },
    )
    body = again.json()
    assert body["code"] == 0
    assert body["data"]["version"] == 2
    assert body["data"]["publishDest"] == "CENTER,MENU"
    assert body["data"]["shareScope"] == "ALL"
    assert body["data"]["hasPassword"] is True
    menus = client.get("/admin-api/ims/bi/report/published-menus", headers=auth)
    assert any(item["menuName"] == "菜单日报" for item in menus.json()["data"]["list"])
    detail = client.get(f"/admin-api/ims/bi/report/{rid}", headers=auth)
    assert detail.json()["data"]["shareScope"] == "ALL"
    assert detail.json()["data"]["publishDest"] == "CENTER,MENU"

def test_bi_import_report_no_uses_max_existing():
    """BUG-C083：编号取已有最大值 +1，删除中间号后不能按条数撞上仍在用的编号。"""
    auth = headers()
    made = []
    for index in range(3):
        created = client.post(
            "/admin-api/ims/bi/report",
            headers=auth,
            json={"reportName": f"编号种子{index}", "reportType": "REPORT", "category": "日报"},
        )
        assert created.json()["code"] == 0
        made.append(created.json()["data"])
    removed = client.delete(f"/admin-api/ims/bi/report/{made[0]['id']}", headers=auth)
    assert removed.json()["code"] == 0
    imported = client.post(
        "/admin-api/ims/bi/report/import",
        headers=auth,
        json={
            "template": {
                "reportName": "编号导入",
                "reportType": "REPORT",
                "category": "日报",
                "comps": [{"id": "c1", "type": "KPI", "title": "GMV", "dataset": "METRIC_LIB"}],
            }
        },
    )
    assert imported.json()["code"] == 0
    fresh = imported.json()["data"]["reportNo"]
    kept = {made[1]["reportNo"], made[2]["reportNo"]}
    assert fresh not in kept
    assert fresh != made[0]["reportNo"]
    top = max(int(item["reportNo"].split("-")[1]) for item in made)
    assert int(fresh.split("-")[1]) == top + 1


def test_bi_report_no_startup_repair_is_idempotent(caplog):
    """BUG-C083：启动时把重复编号改成 max+1，再建立唯一索引。跑两次结果不变。"""
    import logging

    from sqlalchemy import inspect, text

    from app.core import SessionLocal, engine, utcnow
    from app.main import ensure_bi_report_scope_column
    from app.models import BiReportDef

    def index_names() -> set[str]:
        return {item.get("name") for item in inspect(engine).get_indexes("ims_bi_report_def")}

    if "uk_bi_report_no" in index_names():
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ims_bi_report_def DROP INDEX uk_bi_report_no"))

    now = utcnow()
    db = SessionLocal()
    try:
        first = BiReportDef(
            report_no="RPT-9099",
            report_name="重复编号保留",
            report_type="REPORT",
            category="日报",
            tenant_id=0,
            creator_id=1,
            created_at=now,
            updated_at=now,
        )
        second = BiReportDef(
            report_no="RPT-9099",
            report_name="重复编号改号",
            report_type="REPORT",
            category="日报",
            tenant_id=0,
            creator_id=1,
            created_at=now,
            updated_at=now,
        )
        db.add(first)
        db.add(second)
        db.commit()
        keep_id, move_id = first.id, second.id
    finally:
        db.close()

    caplog.set_level(logging.INFO, logger="app.bi_report")
    ensure_bi_report_scope_column()
    text_log = caplog.text
    assert f"tenant=0 report_id={move_id} old=RPT-9099 new=" in text_log
    assert f"report_id={keep_id} old=" not in text_log

    db = SessionLocal()
    try:
        kept = db.get(BiReportDef, keep_id)
        moved = db.get(BiReportDef, move_id)
        assert kept is not None and moved is not None
        assert kept.report_no == "RPT-9099"
        assert moved.report_no != "RPT-9099"
        assert moved.report_no.startswith("RPT-")
        new_no = moved.report_no
        dupes = db.execute(
            text(
                "SELECT report_no FROM ims_bi_report_def WHERE tenant_id = 0 "
                "GROUP BY report_no HAVING COUNT(*) > 1"
            )
        ).all()
        assert dupes == []
    finally:
        db.close()
    assert "uk_bi_report_no" in index_names()

    caplog.clear()
    ensure_bi_report_scope_column()
    assert "报表编号去重" not in caplog.text
    db = SessionLocal()
    try:
        assert db.get(BiReportDef, keep_id).report_no == "RPT-9099"
        assert db.get(BiReportDef, move_id).report_no == new_no
    finally:
        db.close()
    assert "uk_bi_report_no" in index_names()


def _self_user(username: str, nickname: str, role_key: str, mobile: str) -> int:
    from sqlalchemy import select

    from app.bi_br212_seed import _clone_admin_perms
    from app.core import SessionLocal
    from app.models import Role, User, UserRole
    from app.scope import refresh_user_scope
    from app.security import hash_password

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                nickname=nickname,
                mobile=mobile,
                password_hash=hash_password("Admin@123"),
                status="ENABLED",
                tenant_id=0,
            )
            db.add(user)
            db.flush()
        user.nickname = nickname
        user.mobile = mobile
        user.password_hash = hash_password("Admin@123")
        user.status = "ENABLED"
        user.deleted = 0
        user.tenant_id = 0
        role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
        if role is None:
            role = Role(
                role_name=role_key,
                role_key=role_key,
                data_scope="SELF",
                source="MANUAL",
                status="ENABLED",
                tenant_id=0,
            )
            db.add(role)
            db.flush()
            _clone_admin_perms(db, role.id)
        if not db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)):
            db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        refresh_user_scope(db, user.id)
        db.commit()
        return int(user.id)
    finally:
        db.close()


def test_bi_viewer_picker_and_readonly_entry():
    auth = headers()
    viewer_id = _self_user("tc_r2", "只读同事", "bi:tc-r2", "13900002002")
    outsider_id = _self_user("tc_r2_out", "范围外", "bi:tc-r2-out", "13900002003")

    by_account = client.get(
        "/admin-api/ims/bi/report/viewers",
        headers=auth,
        params={"keyword": "tc_r2", "pageSize": 100},
    )
    assert by_account.status_code == 200
    picked = next(item for item in by_account.json()["data"]["list"] if item["username"] == "tc_r2")
    assert picked["id"] == str(viewer_id)
    assert picked["nickname"] == "只读同事"
    assert "mobile" not in picked
    by_name = client.get(
        "/admin-api/ims/bi/report/viewers",
        headers=auth,
        params={"keyword": "只读同事"},
    )
    assert any(item["username"] == "tc_r2" for item in by_name.json()["data"]["list"])
    pinned = client.get(
        "/admin-api/ims/bi/report/viewers",
        headers=auth,
        params={"keyword": "没有这个人", "includeId": viewer_id},
    )
    assert any(item["id"] == str(viewer_id) for item in pinned.json()["data"]["list"])

    outsider_token = client.post(
        "/admin-api/ims/auth/login", json={"username": "tc_r2_out", "password": "Admin@123"}
    ).json()["data"]["accessToken"]
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    scoped_users = client.get("/admin-api/ims/system/user/page", headers=outsider_headers, params={"pageSize": 100})
    assert scoped_users.status_code == 200
    scoped_names = {item["username"] for item in scoped_users.json()["data"]["list"]}
    assert "tc_r2" not in scoped_names
    assert scoped_users.json()["data"]["list"][0]["id"]
    visible = client.get(
        "/admin-api/ims/bi/report/viewers",
        headers=outsider_headers,
        params={"keyword": "tc_r2"},
    )
    assert any(item["username"] == "tc_r2" for item in visible.json()["data"]["list"])

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "只读授权日报", "reportType": "REPORT", "category": "日报"},
    )
    rid = created.json()["data"]["id"]
    published = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={
            "dests": ["CENTER"],
            "shareScope": "SPECIFIED",
            "opPerm": "READONLY",
            "rowPerm": "INHERIT",
            "viewerIds": [viewer_id],
            "accessType": "SHARE_LINK",
            "expireDays": 7,
        },
    )
    body = published.json()
    assert body["code"] == 0
    assert f"highlight={rid}" in body["data"]["shareUrl"]

    viewer_token = client.post(
        "/admin-api/ims/auth/login", json={"username": "tc_r2", "password": "Admin@123"}
    ).json()["data"]["accessToken"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    listed = client.get(
        "/admin-api/ims/bi/report/list",
        headers=viewer_headers,
        params={"status": "PUBLISHED", "keyword": "只读授权日报", "pageSize": 50},
    )
    shared = next(item for item in listed.json()["data"]["list"] if item["id"] == rid)
    assert shared["reportNo"]
    assert "CENTER" in shared["publishDest"]
    assert shared["opPerm"] == "READONLY"
    assert shared["canEdit"] is False
    assert shared["canDelete"] is False
    assert shared["canPublish"] is False
    detail = client.get(f"/admin-api/ims/bi/report/{rid}", headers=viewer_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["canEdit"] is False
    denied_save = client.put(
        f"/admin-api/ims/bi/report/{rid}",
        headers=viewer_headers,
        json={"reportName": "越权改名", "keepVersion": True},
    )
    assert denied_save.status_code == 403
    assert denied_save.json()["code"] == 403
    denied_delete = client.delete(f"/admin-api/ims/bi/report/{rid}", headers=viewer_headers)
    assert denied_delete.status_code == 403
    hidden = client.get(f"/admin-api/ims/bi/report/{rid}", headers=outsider_headers)
    assert hidden.status_code == 403
    assert hidden.json()["code"] == 1008
    assert outsider_id != viewer_id
