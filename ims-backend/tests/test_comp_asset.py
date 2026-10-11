import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import ExternalAccount, IpGroup

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_linked_account() -> str:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品库组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ident = "comp_lib_linked"
        ops.add(
            ExternalAccount(
                account_identifier=ident,
                account_name="库联动账号",
                platform_type="DOUYIN",
                ip_group_id=group.id,
                follower_count=320_000,
                work_count=12,
                tenant_id=0,
            )
        )
        ops.commit()
        return ident
    finally:
        ops.close()


def test_comp_asset_list_seeds():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 4
    assert any(row["compName"] == "Keep 官方" for row in body["data"]["list"])
    numbers = [row["assetNo"] for row in body["data"]["list"]]
    assert len(numbers) == len(set(numbers))
    assert all(no.startswith("CP") and len(no) >= 11 for no in numbers)


def test_list_refresh_does_not_change_asset_nos():
    from sqlalchemy import select

    from app.core import SessionLocal
    from app.models import CompAsset

    auth = headers()
    first = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    assert first["code"] == 0
    listed = [(row["id"], row["assetNo"]) for row in first["data"]["list"]]

    db = SessionLocal()
    try:
        before = {
            row.id: (row.asset_no, row.updated_at)
            for row in db.scalars(select(CompAsset).order_by(CompAsset.id)).all()
        }
    finally:
        db.close()

    second = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    assert [(row["id"], row["assetNo"]) for row in second["data"]["list"]] == listed

    db = SessionLocal()
    try:
        after = {
            row.id: (row.asset_no, row.updated_at)
            for row in db.scalars(select(CompAsset).order_by(CompAsset.id)).all()
        }
    finally:
        db.close()
    assert after == before


def test_duplicate_asset_no_rejected_and_allocation_retries():
    from sqlalchemy.exc import IntegrityError

    from app.comp_asset import assign_and_flush, next_asset_no
    from app.core import SessionLocal
    from app.models import CompAsset

    db = SessionLocal()
    try:
        db.add(
            CompAsset(
                asset_no="CP20261011999",
                comp_name_std="占号",
                platform="DOUYIN",
                status="APPROVED",
                tenant_id=0,
                created_by=1,
            )
        )
        db.commit()
        db.add(
            CompAsset(
                asset_no="CP20261011999",
                comp_name_std="再占",
                platform="DOUYIN",
                status="APPROVED",
                tenant_id=0,
                created_by=1,
            )
        )
        try:
            db.commit()
            raised = False
        except IntegrityError:
            db.rollback()
            raised = True
        assert raised

        calls = {"n": 0}
        real_next = next_asset_no

        def flaky(session, tenant_id):
            calls["n"] += 1
            if calls["n"] < 3:
                return "CP20261011999"
            return real_next(session, tenant_id)

        import app.comp_asset as comp_asset

        original = comp_asset.next_asset_no
        comp_asset.next_asset_no = flaky
        try:
            created = CompAsset(
                comp_name_std="重试号",
                platform="DOUYIN",
                status="APPROVED",
                tenant_id=0,
                created_by=1,
            )
            assign_and_flush(db, created)
            db.commit()
        finally:
            comp_asset.next_asset_no = original
        assert created.asset_no != "CP20261011999"
        assert created.asset_no.startswith("CP")
        assert calls["n"] >= 3
    finally:
        db.close()


def test_concurrent_asset_no_allocation():
    from concurrent.futures import ThreadPoolExecutor

    from app.comp_asset import assign_and_flush
    from app.core import SessionLocal
    from app.models import CompAsset

    def allocate(index: int) -> str:
        db = SessionLocal()
        try:
            row = CompAsset(
                comp_name_std=f"并发竞品{index}",
                platform="DOUYIN",
                status="APPROVED",
                tenant_id=0,
                created_by=1,
            )
            number = assign_and_flush(db, row)
            db.commit()
            return number
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        numbers = list(pool.map(allocate, range(6)))
    assert len(numbers) == 6
    assert len(set(numbers)) == 6
    assert all(no.startswith("CP") for no in numbers)


def test_repair_script_mapping():
    import importlib.util
    import sys
    from pathlib import Path

    from sqlalchemy import select, text

    from app.core import SessionLocal, engine
    from app.models import CompAsset

    script = Path(__file__).resolve().parents[1] / "scripts" / "repair_comp_asset_no.py"
    spec = importlib.util.spec_from_file_location("repair_comp_asset_no", script)
    repair = importlib.util.module_from_spec(spec)
    sys.modules["repair_comp_asset_no"] = repair
    spec.loader.exec_module(repair)

    planned = repair.plan_repairs(
        [
            repair.AssetNoRow(1, "Keep 官方", "CP20261011001"),
            repair.AssetNoRow(2, "咕咚运动", "CP20261011002"),
            repair.AssetNoRow(3, "悦跑圈", "CP20261011001"),
        ]
    )
    assert [(item.id, item.old_no, item.new_no) for item in planned] == [
        (3, "CP20261011001", "CP20261011003"),
    ]
    log = repair.format_log(planned, mode="dry-run", scanned=3)
    assert "asset_id\tname\told_no\tnew_no" in log
    assert "3\t悦跑圈\tCP20261011001\tCP20261011003" in log
    assert "no changes" in repair.format_log([], mode="dry-run", scanned=4)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ims_comp_asset DROP INDEX uk_comp_asset_no"))
    db = SessionLocal()
    try:
        for name in ("重复甲", "重复乙", "重复丙"):
            db.add(
                CompAsset(
                    asset_no="CP20261011001",
                    comp_name_std=name,
                    platform="DOUYIN",
                    status="APPROVED",
                    tenant_id=0,
                    created_by=1,
                )
            )
        db.commit()
        rows = repair.load_rows(db)
        changes = repair.plan_repairs(rows)
        kept = min(row.id for row in rows if row.asset_no == "CP20261011001")
        assert all(change.id != kept for change in changes)
        assert {change.old_no for change in changes} == {"CP20261011001"}
        assert len({change.new_no for change in changes}) == len(changes)
        repair.apply_changes(db, changes)
        db.commit()
        stored = {
            row.comp_name_std: row.asset_no
            for row in db.scalars(select(CompAsset).where(CompAsset.comp_name_std.like("重复%"))).all()
        }
        assert stored["重复甲"] == "CP20261011001"
        assert len(set(stored.values())) == 3
        applied = repair.format_log(changes, mode="apply", scanned=len(rows))
        assert "重复乙" in applied and "重复丙" in applied
    finally:
        db.close()


def test_comp_asset_create_enriched_from_ops():
    ident = seed_linked_account()
    auth = headers()
    created = client.post(
        "/admin-api/ims/comp/asset",
        headers=auth,
        json={
            "compName": "健身教练艾伦",
            "platform": "DOUYIN",
            "compAccountId": ident,
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["assetNo"].startswith("CP")
    assert body["data"]["followerCount"] == 320_000

    listed = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"compName": "健身教练", "pageNo": 1, "pageSize": 5},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1


def test_comp_asset_detail_and_compare():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    numbers = [row["assetNo"] for row in listed["data"]["list"][:2]]
    detail = client.get(f"/admin-api/ims/comp/asset/{numbers[0]}", headers=auth).json()
    assert detail["code"] == 0, detail
    assert detail["data"]["auditStatusLabel"] == "已入库"
    assert detail["data"]["monitorSubscribed"] is True
    assert isinstance(detail["data"]["interactionTrend"], list)
    assert "topWorks" in detail["data"]

    compared = client.get(
        "/admin-api/ims/comp/asset/compare",
        headers=auth,
        params={"assetNos": ",".join(numbers)},
    ).json()
    assert compared["code"] == 0, compared
    assert compared["data"]["assetNos"] == numbers
    assert any(item["dimensionKey"] == "followerCount" for item in compared["data"]["dimensionMatrix"])
