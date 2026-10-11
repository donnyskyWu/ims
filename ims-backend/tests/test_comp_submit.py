import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import Role, RolePerm, User, UserRole
from app.security import hash_password

client = TestClient(app)

BODY = {
    "compName": "TC竞品库A",
    "platform": "DOUYIN",
    "homepageUrl": "https://example.com/a",
    "periodMonth": "2026-10",
    "dataSource": "公开主页与作品列表",
    "dimensionData": {"contentStrategy": "连载挑战"},
    "conclusion": "可借鉴选题节奏",
}


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def ensure_role_user(username: str, role_key: str, nickname: str, extra_roles: tuple[tuple[str, str], ...] = ()) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if user is None:
            user = User(
                username=username,
                nickname=nickname,
                mobile=f"139{abs(hash(username)) % 10_000_000:07d}"[:11],
                password_hash=hash_password("Admin@123"),
                status="ENABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(user)
            db.flush()
        role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
        if role is None:
            role = Role(
                role_name=nickname,
                role_key=role_key,
                data_scope="ALL",
                status="ENABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(role)
            db.flush()
        if db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)) is None:
            db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        if db.scalar(select(RolePerm).where(RolePerm.role_id == role.id)) is None:
            db.add(
                RolePerm(
                    role_id=role.id,
                    module_code="comp",
                    perm_code="comp:analysis:query",
                    perm_level="R",
                    tenant_id=0,
                )
            )
        for extra_key, extra_name in extra_roles:
            extra = db.scalar(select(Role).where(Role.role_key == extra_key, Role.deleted == 0))
            if extra is None:
                extra = Role(
                    role_name=extra_name,
                    role_key=extra_key,
                    data_scope="ALL",
                    status="ENABLED",
                    tenant_id=0,
                    deleted=0,
                )
                db.add(extra)
                db.flush()
            if db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == extra.id)) is None:
                db.add(UserRole(user_id=user.id, role_id=extra.id, tenant_id=0))
            if db.scalar(select(RolePerm).where(RolePerm.role_id == extra.id)) is None:
                db.add(
                    RolePerm(
                        role_id=extra.id,
                        module_code="comp",
                        perm_code="comp:analysis:query",
                        perm_level="R",
                        tenant_id=0,
                    )
                )
        db.commit()
    finally:
        db.close()


def seed_roles() -> None:
    ensure_role_user("tc_r6", "comp:r6", "短视频运营")
    ensure_role_user("tc_r8", "comp:r8", "内容审核")
    ensure_role_user("tc_r4", "comp:r4", "运营总监")


def test_submit_requires_data_source_then_enters_first_audit():
    seed_roles()
    auth = headers("tc_r6")
    missing = client.post("/admin-api/ims/comp/analysis", headers=auth, json={**BODY, "dataSource": ""})
    missing_body = missing.json()
    assert missing_body["code"] == 1171
    assert missing_body["msg"] == "数据来源必填（仅可采集公开数据）"
    assert "1171" not in missing_body["msg"]
    assert "BR-202" not in missing_body["msg"]

    created = client.post("/admin-api/ims/comp/analysis", headers=auth, json=BODY)
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["auditStatus"] == "PENDING_FIRST"
    assert body["data"]["auditStatusLabel"] == "待初审"
    assert body["data"]["analysisNo"].startswith("CA")

    dup = client.post("/admin-api/ims/comp/analysis", headers=auth, json=BODY)
    assert dup.json()["code"] == 1172


def test_submit_requires_three_essentials_without_internal_code():
    seed_roles()
    auth = headers("tc_r6")
    missing_dim = client.post(
        "/admin-api/ims/comp/analysis",
        headers=auth,
        json={**BODY, "compName": "TC缺维度", "dimensionData": {}},
    ).json()
    assert missing_dim["code"] == 1174
    assert missing_dim["msg"] == "来源、维度字段、结论均须明确"
    assert "1174" not in missing_dim["msg"]

    missing_conclusion = client.post(
        "/admin-api/ims/comp/analysis",
        headers=auth,
        json={**BODY, "compName": "TC缺结论", "conclusion": "  "},
    ).json()
    assert missing_conclusion["code"] == 1174
    assert "1174" not in missing_conclusion["msg"]

    listed = client.get("/admin-api/ims/comp/analysis/list", headers=auth, params={"pageNo": 1, "pageSize": 20}).json()
    names = {item["compName"] for item in listed["data"]["list"]}
    assert "TC缺维度" not in names
    assert "TC缺结论" not in names


def test_two_level_audit_stores_and_subscribes():
    seed_roles()
    r6 = headers("tc_r6")
    created = client.post("/admin-api/ims/comp/analysis", headers=r6, json=BODY).json()
    assert created["code"] == 0, created
    no = created["data"]["analysisNo"]

    blocked = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=r6,
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    blocked_body = blocked.json()
    assert blocked_body["code"] == 1176
    assert blocked_body["msg"] == "越级审核：初审仅内容审核员"
    assert "R8" not in blocked_body["msg"]
    assert "1176" not in blocked_body["msg"]

    first = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r8"),
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    first_body = first.json()
    assert first_body["code"] == 0, first_body
    assert first_body["data"]["auditStatusLabel"] == "待终审"
    assert first_body["data"]["nextAction"] == "TO_FINAL"

    early = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r4"),
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    assert early.json()["code"] == 1176

    final = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r4"),
        json={"auditLevel": "FINAL", "conclusion": "STORED"},
    )
    final_body = final.json()
    assert final_body["code"] == 0, final_body
    assert final_body["data"]["newStatus"] == "STORED"
    assert final_body["data"]["auditStatusLabel"] == "已入库"
    assert final_body["data"]["mergeInfo"]["monitorSubscribed"] is True
    assert len(final_body["data"]["auditRounds"]) == 2


def test_final_approve_succeeds_on_first_call_from_clean_seq():
    """序号表为空时，终审通过的第一次请求就要入库。"""
    from sqlalchemy import func, select, text

    from app.core import engine
    from app.models import CompAnalysis, CompAssetSeq

    seed_roles()
    r6 = headers("tc_r6")
    created = client.post(
        "/admin-api/ims/comp/analysis",
        headers=r6,
        json={**BODY, "compName": "TC终审首点"},
    ).json()
    assert created["code"] == 0, created
    no = created["data"]["analysisNo"]
    first = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r8"),
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    assert first.json()["code"] == 0, first.json()

    db = SessionLocal()
    try:
        assert (db.scalar(select(func.count()).select_from(CompAssetSeq)) or 0) == 0
    finally:
        db.close()

    turned_on = False
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("SET GLOBAL innodb_snapshot_isolation=ON"))
        turned_on = True
        engine.dispose()

        final = client.put(
            f"/admin-api/ims/comp/audit/{no}",
            headers=headers("tc_r4"),
            json={"auditLevel": "FINAL", "conclusion": "STORED"},
        )
        final_body = final.json()
        assert final.status_code == 200
        assert final_body["code"] == 0, final_body
        assert final_body["data"]["newStatus"] == "STORED"
        assert str(final_body["data"]["mergeInfo"]["assetNo"]).startswith("CP")

        db = SessionLocal()
        try:
            row = db.scalar(select(CompAnalysis).where(CompAnalysis.analysis_no == no))
            assert row is not None
            assert row.submit_status == "STORED"
        finally:
            db.close()
    finally:
        if turned_on:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("SET GLOBAL innodb_snapshot_isolation=OFF"))
            engine.dispose()


def test_final_approve_once_when_monitor_account_was_removed():
    """软删的监控账号仍占唯一键。终审不能因此回滚，再点一次也不再加审核轮次。"""
    from datetime import datetime, timedelta, timezone

    from app.ops_db import ops_session
    from app.ops_models import ExternalAccount

    seed_roles()
    created = client.post(
        "/admin-api/ims/comp/analysis",
        headers=headers("tc_r6"),
        json={**BODY, "compName": "TB竞品B077终审"},
    ).json()
    assert created["code"] == 0, created
    no = created["data"]["analysisNo"]
    first = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r8"),
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    assert first.json()["code"] == 0, first.json()

    day = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    ident = f"ca-CP{day}001"
    ops = ops_session()
    try:
        ops.add(
            ExternalAccount(
                account_identifier=ident,
                account_name="已停用监控",
                platform_type="DOUYIN",
                deleted=1,
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()

    final = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r4"),
        json={"auditLevel": "FINAL", "conclusion": "STORED"},
    )
    final_body = final.json()
    assert final.status_code == 200
    assert final_body["code"] == 0, final_body
    assert final_body["data"]["newStatus"] == "STORED"
    assert final_body["data"]["mergeInfo"]["assetNo"] == f"CP{day}001"
    assert len(final_body["data"]["auditRounds"]) == 2

    again = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=headers("tc_r4"),
        json={"auditLevel": "FINAL", "conclusion": "STORED"},
    )
    again_body = again.json()
    assert again.status_code == 200
    assert again_body["code"] == 0, again_body
    assert again_body["data"]["newStatus"] == "STORED"
    assert len(again_body["data"]["auditRounds"]) == 2

    ops = ops_session()
    try:
        account = ops.scalar(select(ExternalAccount).where(ExternalAccount.account_identifier == ident))
        assert account is not None
        assert account.deleted == 0
    finally:
        ops.close()


def test_reject_requires_reason_and_resubmit_keeps_timeline():
    seed_roles()
    r6 = headers("tc_r6")
    no = client.post("/admin-api/ims/comp/analysis", headers=r6, json={**BODY, "compName": "TC竞品库B"}).json()["data"][
        "analysisNo"
    ]
    r8 = headers("tc_r8")
    empty = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=r8,
        json={"auditLevel": "FIRST", "conclusion": "REJECTED", "rejectReason": ""},
    )
    assert empty.json()["code"] == 1173

    rejected = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=r8,
        json={"auditLevel": "FIRST", "conclusion": "REJECTED", "rejectReason": "来源不可追溯"},
    )
    rejected_body = rejected.json()
    assert rejected_body["code"] == 0, rejected_body
    assert rejected_body["data"]["auditStatusLabel"] == "已退回"

    detail = client.get(f"/admin-api/ims/comp/analysis/{no}", headers=r6).json()
    assert detail["data"]["rejectReason"] == "来源不可追溯"
    assert len(detail["data"]["auditRounds"]) == 1

    again = client.put(
        f"/admin-api/ims/comp/analysis/{no}",
        headers=r6,
        json={**BODY, "compName": "TC竞品库B", "conclusion": "补充公开来源后重提"},
    )
    again_body = again.json()
    assert again_body["code"] == 0, again_body
    assert again_body["data"]["auditStatus"] == "PENDING_FIRST"
    assert again_body["data"]["rejectReason"] == ""
    rounds = again_body["data"]["auditRounds"]
    assert len(rounds) == 2
    assert rounds[0]["conclusion"] == "REJECTED"
    assert rounds[0]["rejectReason"] == "来源不可追溯"
    assert rounds[1]["auditLevel"] == "RESUBMIT"
    assert rounds[1]["conclusion"] == "RESUBMITTED"

    detail_after = client.get(f"/admin-api/ims/comp/analysis/{no}", headers=r6).json()
    assert detail_after["data"]["rejectReason"] == ""
    assert detail_after["data"]["auditRounds"][0]["rejectReason"] == "来源不可追溯"

    records = client.get(
        "/admin-api/ims/comp/audit/records",
        headers=r6,
        params={"analysisNo": no},
    ).json()
    listed = records["data"]["list"]
    assert any(item["auditLevel"] == "RESUBMIT" for item in listed)
    assert any(item["conclusion"] == "REJECTED" and item["rejectReason"] == "来源不可追溯" for item in listed)


def test_self_audit_blocked_and_merge_preview():
    seed_roles()
    ensure_role_user("tc_r68", "comp:r6", "短视频兼审核", extra_roles=(("comp:r8", "内容审核"),))
    r8 = headers("tc_r68")
    created = client.post(
        "/admin-api/ims/comp/analysis",
        headers=r8,
        json={**BODY, "compName": "Keep 官方"},
    ).json()
    assert created["code"] == 0, created
    no = created["data"]["analysisNo"]
    self_audit = client.put(
        f"/admin-api/ims/comp/audit/{no}",
        headers=r8,
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    assert self_audit.json()["code"] == 1057

    listed = client.get("/admin-api/ims/comp/asset/list", headers=headers(), params={"pageNo": 1, "pageSize": 10})
    assert listed.json()["code"] == 0
    preview = client.get(
        "/admin-api/ims/comp/audit/merge-preview",
        headers=r8,
        params={"compName": "Keep 官方"},
    ).json()
    assert preview["code"] == 0
    assert preview["data"]["matched"] is True
    assert preview["data"]["compNameStd"] == "Keep 官方"


def _store(name: str, period: str) -> tuple[str, str]:
    created = client.post(
        "/admin-api/ims/comp/analysis",
        headers=headers("tc_r6"),
        json={**BODY, "compName": name, "periodMonth": period},
    ).json()
    assert created["code"] == 0, created
    analysis_no = created["data"]["analysisNo"]
    first = client.put(
        f"/admin-api/ims/comp/audit/{analysis_no}",
        headers=headers("tc_r8"),
        json={"auditLevel": "FIRST", "conclusion": "STORED"},
    )
    assert first.json()["code"] == 0, first.json()
    final = client.put(
        f"/admin-api/ims/comp/audit/{analysis_no}",
        headers=headers("tc_r4"),
        json={"auditLevel": "FINAL", "conclusion": "STORED"},
    )
    final_body = final.json()
    assert final_body["code"] == 0, final_body
    return analysis_no, final_body["data"]["mergeInfo"]["assetNo"]


def test_archive_detail_lists_merged_submissions_and_review_rounds():
    seed_roles()
    first_no, asset_no = _store("TC归并档案", "2026-09")
    second_no, again = _store("TC归并档案", "2026-10")
    assert again == asset_no

    detail = client.get(f"/admin-api/ims/comp/asset/{asset_no}", headers=headers("tc_r4")).json()
    assert detail["code"] == 0, detail
    data = detail["data"]
    assert data["sourceAnalysisNos"] == [first_no, second_no]
    rounds = data["auditRounds"]
    assert {item["analysisNo"] for item in rounds} == {first_no, second_no}
    levels = {(item["analysisNo"], item["auditLevel"]) for item in rounds}
    assert (first_no, "FIRST") in levels
    assert (first_no, "FINAL") in levels
    assert (second_no, "FIRST") in levels
    assert (second_no, "FINAL") in levels
    final_round = next(item for item in rounds if item["analysisNo"] == second_no and item["auditLevel"] == "FINAL")
    assert final_round["auditorName"]
    assert final_round["auditedAt"]


def test_stored_submission_exposes_archive_no():
    seed_roles()
    analysis_no, asset_no = _store("TC送审指向档案", "2026-08")
    detail = client.get(f"/admin-api/ims/comp/analysis/{analysis_no}", headers=headers("tc_r6")).json()
    assert detail["code"] == 0, detail
    assert detail["data"]["analysisNo"] == analysis_no
    assert detail["data"]["assetNo"] == asset_no
    assert detail["data"]["auditStatus"] == "STORED"
    assert detail["data"]["auditStatusLabel"] == "已入库"
    listed = client.get(
        "/admin-api/ims/comp/analysis/list",
        headers=headers("tc_r6"),
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    row = next(item for item in listed["data"]["list"] if item["analysisNo"] == analysis_no)
    assert row["assetNo"] == asset_no
