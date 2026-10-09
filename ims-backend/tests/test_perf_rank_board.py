"""PERF-004 排名边缘：同分并列、分档线、红榜前三、末位预警桩、空态。"""

import os
from decimal import Decimal

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import PerfRank, User
from app.perf_calc import assign_ranks, grade_level_of

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


class _Row:
    def __init__(self, user_id: int, dept_id: int, score: str):
        self.user_id = user_id
        self.dept_id = dept_id
        self.total_score = Decimal(score)
        self.rank_in_dept = None


def test_grade_lines_and_tied_ranks():
    assert grade_level_of(Decimal("85")) == "EXCELLENT"
    assert grade_level_of(Decimal("84.99")) == "QUALIFIED"
    assert grade_level_of(Decimal("60")) == "QUALIFIED"
    assert grade_level_of(Decimal("59.99")) == "IMPROVE"
    assert grade_level_of(None) == "IMPROVE"

    same = [
        _Row(2, 11, "90.00"),
        _Row(1, 11, "90.00"),
        _Row(3, 11, "70.00"),
    ]
    other = [_Row(9, 22, "100")]
    assign_ranks(same + other)
    by_user = {row.user_id: row.rank_in_dept for row in same + other}
    assert by_user[1] == 1
    assert by_user[2] == 1
    assert by_user[3] == 3
    assert by_user[9] == 1


def _add(db, tenant: int, **kwargs) -> None:
    db.add(
        PerfRank(
            period_month="2026-08",
            consecutive_months=0,
            version=1,
            is_current=1,
            tenant_id=tenant,
            **kwargs,
        )
    )


def test_rank_board_edges_empty_and_tail_stub():
    auth = headers()
    staff = headers("e2e_perf_staff")
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        assert admin is not None
        tenant = int(admin.tenant_id or 0)
        _add(
            db,
            tenant,
            dept_id=11,
            dept_name="主播组",
            user_id=8101,
            user_name="并列甲",
            total_score=Decimal("90.00"),
            rank_no=1,
            grade_level="EXCELLENT",
            alert_status="NONE",
        )
        _add(
            db,
            tenant,
            dept_id=11,
            dept_name="主播组",
            user_id=8102,
            user_name="并列乙",
            total_score=Decimal("90.00"),
            rank_no=1,
            grade_level="EXCELLENT",
            alert_status="NONE",
        )
        _add(
            db,
            tenant,
            dept_id=11,
            dept_name="主播组",
            user_id=8103,
            user_name="末位丙",
            total_score=Decimal("50.00"),
            rank_no=3,
            grade_level="IMPROVE",
            alert_status="ALERTED",
        )
        _add(
            db,
            tenant,
            dept_id=22,
            dept_name="运营中心",
            user_id=8104,
            user_name="铜牌丁",
            total_score=Decimal("88.00"),
            rank_no=1,
            grade_level="EXCELLENT",
            alert_status="NONE",
        )
        db.commit()
    finally:
        db.close()

    empty = client.get("/admin-api/ims/perf/rank/period/2026-07", headers=auth)
    assert empty.json()["code"] == 0, empty.json()
    assert empty.json()["data"]["total"] == 0
    assert empty.json()["data"]["rankBoard"]["emptyReason"] == "UNPUBLISHED"
    assert empty.json()["data"]["rankBoard"]["top3"] == []

    denied = client.get("/admin-api/ims/perf/rank/period/2026-08", headers=staff)
    assert denied.json()["code"] == 403

    board = client.get(
        "/admin-api/ims/perf/rank/period/2026-08",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    assert board.json()["code"] == 0, board.json()
    data = board.json()["data"]
    assert data["total"] == 4
    summary = data["rankBoard"]
    assert summary["emptyReason"] == ""
    assert summary["deptAverage"] == 79.5
    assert summary["gradeLine"].startswith("优秀 ≥85")
    assert "不外发钉钉" in summary["pipStub"]
    medals = [(row["userName"], row["medal"], row["boardRank"]) for row in summary["top3"]]
    assert medals == [("并列甲", "GOLD", 1), ("并列乙", "GOLD", 1), ("铜牌丁", "BRONZE", 3)]
    assert summary["tail"][0]["userName"] == "末位丙"
    assert summary["tail"][0]["belowLine"] is True
    assert {item["deptName"] for item in summary["deptAverages"]} == {"主播组", "运营中心"}

    one = client.get(
        "/admin-api/ims/perf/rank/period/2026-08",
        headers=auth,
        params={"deptId": 22},
    )
    one_board = one.json()["data"]["rankBoard"]
    assert one_board["deptAverage"] == 88.0
    assert [row["userName"] for row in one_board["top3"]] == ["铜牌丁"]
    assert one_board["top3"][0]["medal"] == "GOLD"
    assert one_board["tail"] == []
    assert len(one_board["depts"]) == 2

    missing = client.get(
        "/admin-api/ims/perf/rank/period/2026-08",
        headers=auth,
        params={"deptId": 99999},
    )
    assert missing.json()["data"]["rankBoard"]["emptyReason"] == "DEPT_EMPTY"
    assert missing.json()["data"]["total"] == 0
