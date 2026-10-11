"""BUG-C040：复合指标公式白名单。保存、试算、分析都拒绝 DELETE/UPDATE/DROP。"""

import logging
import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from sqlalchemy import func, select

from app.bi_metric_formula import formula_error, quarantine_illegal_metric_formulas
from app.core import SessionLocal, utcnow
from app.main import _retire_bi_tc_r9, app, seed
from app.models import BiMetric, Role, RoleMenu, RolePerm, User, UserRole
from app.security import hash_password

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_formula_parser_allows_codes_functions_and_arithmetic():
    assert formula_error("") is None
    assert formula_error("   ") is None
    assert formula_error("A + B") is None
    assert formula_error("INTERACTION_COUNT / TC_PLAY * 100") is None
    assert formula_error("SUM(TC_PLAY)") is None
    assert formula_error("(AVG(M00001) - MIN(M00002)) / COUNT(M00003)") is None
    assert formula_error("MAX(A) + 1.5") is None


def test_formula_parser_rejects_sql_and_other_text():
    for sample in (
        "DELETE FROM x",
        "delete from x",
        "UPDATE t SET a = 1",
        "DROP TABLE t",
        "INSERT INTO t VALUES (1)",
        "A; DROP TABLE t",
        "SUM(A); DELETE FROM x",
        "1 OR 1",
        "' OR 1=1",
        "A + B -- comment",
    ):
        err = formula_error(sample)
        assert err is not None, sample
        assert "1192" in err
    assert formula_error("SELECT ip_group_name, SUM(play_count) AS metric_value FROM oa_content_metric") is None


def test_tc_r9_save_rejects_delete_and_preview_rejects_stored_formula():
    auth = headers()
    rejected = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={
            "metricName": "TC_C注入",
            "metricType": "COMPOSITE",
            "category": "内容表现",
            "formula": "DELETE FROM x",
        },
    )
    body = rejected.json()
    assert body["code"] == 1192
    assert "DELETE" in body["msg"]
    assert "1192" in body["msg"]

    listed = client.get(
        "/admin-api/ims/bi/metric/list",
        headers=auth,
        params={"keyword": "TC_C注入", "pageNo": 1, "pageSize": 20},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["list"] == []

    kept = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={
            "metricName": "TC互动率",
            "metricType": "COMPOSITE",
            "category": "内容表现",
            "formula": "INTERACTION_COUNT / TC_PLAY * 100",
        },
    )
    assert kept.json()["code"] == 0
    mid = kept.json()["data"]["id"]

    preview = client.post(f"/admin-api/ims/bi/metric/{mid}/preview", headers=auth, json={})
    assert preview.json()["code"] == 0
    assert preview.json()["data"]["value"] > 0

    dropped = client.put(
        f"/admin-api/ims/bi/metric/{mid}",
        headers=auth,
        json={"formula": "DROP TABLE ims_bi_metric"},
    )
    assert dropped.json()["code"] == 1192
    assert "DROP" in dropped.json()["msg"]
    again = client.get(
        "/admin-api/ims/bi/metric/list",
        headers=auth,
        params={"keyword": "TC互动率", "pageNo": 1, "pageSize": 5},
    )
    stored = next(row for row in again.json()["data"]["list"] if row["id"] == mid)
    assert stored["formula"] == "INTERACTION_COUNT / TC_PLAY * 100"

    db = SessionLocal()
    try:
        now = utcnow()
        poisoned = BiMetric(
            metric_code="M00004",
            metric_name="TC_C注入存量",
            metric_type="COMPOSITE",
            category="内容表现",
            calc_freq="DAY",
            status="ENABLED",
            formula="DELETE FROM x",
            ref_count=0,
            creator_id=1,
            tenant_id=0,
            created_at=now,
            updated_at=now,
        )
        db.add(poisoned)
        db.commit()
        poisoned_id = poisoned.id
    finally:
        db.close()

    stale = client.post(f"/admin-api/ims/bi/metric/{poisoned_id}/preview", headers=auth, json={})
    assert stale.json()["code"] == 1192
    assert "value" not in (stale.json().get("data") or {})

    analysis = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [poisoned_id], "dateStart": "2026-09-01", "dateEnd": "2026-09-30"},
    )
    assert analysis.json()["code"] == 1192
    assert analysis.json()["data"] is None or "rows" not in (analysis.json().get("data") or {})

    single = client.get(
        f"/admin-api/ims/bi/metric/{poisoned_id}/analyze",
        headers=auth,
        params={"dateStart": "2026-09-01", "dateEnd": "2026-09-30"},
    )
    assert single.json()["code"] == 1192

    db = SessionLocal()
    try:
        changed = quarantine_illegal_metric_formulas(db)
        db.commit()
        row = db.get(BiMetric, poisoned_id)
        assert changed >= 1
        assert row is not None
        assert row.status == "DISABLED"
        assert row.formula == "DELETE FROM x"
    finally:
        db.close()

    enabled = client.put(
        f"/admin-api/ims/bi/metric/{poisoned_id}",
        headers=auth,
        json={"status": "ENABLED"},
    )
    assert enabled.json()["code"] == 1192


def _preset_bi_tc_r9(db, *, with_standard_r9: bool) -> tuple[int, int]:
    user = User(
        username="tc_r9",
        nickname="TC-数据分析",
        mobile="13900001040",
        password_hash=hash_password("Admin@123"),
        status="ENABLED",
        tenant_id=0,
    )
    role = Role(
        role_name="数据分析师",
        role_key="bi:tc_r9",
        data_scope="ALL",
        source="MANUAL",
        status="ENABLED",
        tenant_id=0,
    )
    db.add_all([user, role])
    db.flush()
    if with_standard_r9:
        db.add(
            Role(
                role_name="数据分析师",
                role_key="R9",
                data_scope="ALL",
                source="MANUAL",
                status="ENABLED",
                tenant_id=0,
            )
        )
        db.flush()
    db.add(
        RolePerm(
            role_id=role.id,
            module_code="system",
            perm_code="system:user:query",
            perm_level="RWD",
            tenant_id=0,
        )
    )
    db.add(RoleMenu(role_id=role.id, menu_id=11, perm_code="system:user:query", tenant_id=0))
    db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
    db.commit()
    return user.id, role.id


def _role_keys_of(db, user_id: int) -> list[str]:
    return list(
        db.scalars(
            select(Role.role_key)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.role_key)
        ).all()
    )


def test_retire_bi_tc_r9_unbinds_and_logs_when_standard_r9_missing(caplog):
    db = SessionLocal()
    try:
        user_id, role_id = _preset_bi_tc_r9(db, with_standard_r9=False)
        with caplog.at_level(logging.WARNING):
            _retire_bi_tc_r9(db)
            db.commit()
        assert db.get(Role, role_id) is None
        assert db.scalar(select(Role).where(Role.role_key == "bi:tc_r9")) is None
        assert db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id == role_id)) == 0
        assert db.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.role_id == role_id)) == 0
        assert _role_keys_of(db, user_id) == []
        assert db.scalar(select(Role).where(Role.role_key == "R9")) is None
        assert "未创建 R9" in caplog.text
        _retire_bi_tc_r9(db)
        db.commit()
        assert _role_keys_of(db, user_id) == []
    finally:
        db.close()


def test_startup_deletes_bi_tc_r9_and_rebinds_tc_r9_to_standard_r9():
    db = SessionLocal()
    try:
        user_id, role_id = _preset_bi_tc_r9(db, with_standard_r9=True)
    finally:
        db.close()

    seed()
    seed()

    db = SessionLocal()
    try:
        assert db.get(Role, role_id) is None
        assert db.scalar(select(Role).where(Role.role_key == "bi:tc_r9")) is None
        assert db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id == role_id)) == 0
        assert db.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.role_id == role_id)) == 0
        assert _role_keys_of(db, user_id) == ["R9"]
        kept = db.get(User, user_id)
        assert kept is not None and kept.deleted == 0 and kept.username == "tc_r9"
    finally:
        db.close()
