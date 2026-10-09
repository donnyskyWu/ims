"""PERF-002 月度闭环：计算、1156/1158/1157/1155、核准发布、员工只看本人。"""

import os
from datetime import datetime

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import User

client = TestClient(app)

LINEAR = {
    "ruleType": "LINEAR",
    "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 100},
}
PERIOD = "2026-09"


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def create_metric(auth: dict, code: str, name: str, source: dict) -> int:
    created = client.post(
        "/admin-api/ims/perf/metric",
        headers=auth,
        json={
            "metricCode": code,
            "metricName": name,
            "dataSource": "AUTO",
            "sourceConfig": source,
            "weight": 50,
            "scoreRule": LINEAR,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]["id"]


def row_of(payload: dict, name: str) -> dict:
    return next(row for row in payload["data"]["list"] if row["userName"] == name)


def test_perf_month_close_grades_lock_and_self_view():
    auth = headers()
    staff = headers("e2e_perf_staff")

    early = client.post("/admin-api/ims/perf/calc/run", headers=auth, json={"periodMonth": "2026-05"})
    assert early.json()["code"] == 1156
    assert "第 23 周" in early.json()["msg"]

    train_id = create_metric(
        auth,
        "E2E_TRAIN_FINISH",
        "培训完成率",
        {"module": "TRAIN", "metricExpression": "finish_rate", "periodType": "MONTHLY"},
    )
    meet_id = create_metric(
        auth,
        "E2E_MEET_ON_TIME",
        "日报按时率",
        {"module": "MEET", "metricExpression": "on_time_rate", "periodType": "MONTHLY"},
    )
    bound = client.post(
        "/admin-api/ims/perf/metric/bind-position",
        headers=auth,
        json={
            "positionCode": "R5",
            "metricBindings": [
                {"metricId": train_id, "weightOverride": 50},
                {"metricId": meet_id, "weightOverride": 50},
            ],
        },
    )
    assert bound.json()["code"] == 0, bound.json()

    run = client.post("/admin-api/ims/perf/calc/run", headers=auth, json={"periodMonth": PERIOD})
    assert run.json()["code"] == 0, run.json()
    assert run.json()["data"]["targetUserCount"] == 2
    assert "2 人" in run.json()["data"]["message"]

    listed = client.get(f"/admin-api/ims/perf/calc/{PERIOD}", headers=auth, params={"pageNo": 1, "pageSize": 100})
    assert listed.json()["code"] == 0, listed.json()
    staff_row = row_of(listed.json(), "绩效员工甲")
    peer_row = row_of(listed.json(), "绩效员工乙")
    assert staff_row["resultStatus"] == "PENDING_APPROVE"
    assert staff_row["totalScore"] == 100
    assert staff_row["gradeLevel"] == "EXCELLENT"
    assert staff_row["rankInDept"] == 1
    assert staff_row["deptName"] == "直播部"
    by_code = {item["metricCode"]: item for item in staff_row["details"]}
    assert by_code["E2E_TRAIN_FINISH"]["dataStatus"] == "AUTO"
    assert by_code["E2E_TRAIN_FINISH"]["metricValue"] == 100
    assert by_code["E2E_MEET_ON_TIME"]["dataStatus"] == "AUTO"
    assert by_code["E2E_MEET_ON_TIME"]["metricValue"] == 100
    assert by_code["E2E_TRAIN_FINISH"]["contribution"] == 50
    assert "COMPETE_SUBMIT_RATE" not in by_code
    assert staff_row["gradeLevel"] not in {"S", "A", "B", "C", "D"}

    assert peer_row["resultStatus"] == "PENDING_MANUAL"
    assert peer_row["totalScore"] == 0
    assert peer_row["gradeLevel"] == "IMPROVE"
    assert peer_row["missingCount"] == 1
    missing = next(item for item in peer_row["details"] if item["dataStatus"] == "MISSING")
    assert missing["metricCode"] == "E2E_TRAIN_FINISH"

    blank = client.put(
        f"/admin-api/ims/perf/calc/detail/{peer_row['id']}/manual",
        headers=auth,
        json={"metricId": missing["metricId"], "manualValue": 80, "supplementReason": "  "},
    )
    assert blank.json()["code"] == 1158
    filled = client.put(
        f"/admin-api/ims/perf/calc/detail/{peer_row['id']}/manual",
        headers=auth,
        json={"metricId": missing["metricId"], "manualValue": 80, "supplementReason": "现场补录"},
    )
    assert filled.json()["code"] == 0, filled.json()
    after = client.get(f"/admin-api/ims/perf/calc/{PERIOD}", headers=auth, params={"pageNo": 1, "pageSize": 100})
    peer_ready = row_of(after.json(), "绩效员工乙")
    assert peer_ready["resultStatus"] == "PENDING_APPROVE"
    assert peer_ready["totalScore"] == 40
    assert peer_ready["gradeLevel"] == "IMPROVE"

    hidden = client.get(f"/admin-api/ims/perf/calc/{PERIOD}/mine", headers=staff)
    assert hidden.json()["code"] == 1157
    staff_list = client.get(
        f"/admin-api/ims/perf/calc/{PERIOD}",
        headers=staff,
        params={"pageNo": 1, "pageSize": 100},
    ).json()
    assert staff_list["code"] == 0
    assert staff_list["data"]["list"] == []
    denied = client.put(
        f"/admin-api/ims/perf/calc/{PERIOD}/approve",
        headers=staff,
        json={"approve": True},
    )
    assert denied.json()["code"] == 1008

    approved = client.put(
        f"/admin-api/ims/perf/calc/{PERIOD}/approve",
        headers=auth,
        json={"approve": True, "remark": "核准发布"},
    )
    assert approved.json()["code"] == 0, approved.json()
    assert approved.json()["data"]["publishedCount"] == 2
    assert approved.json()["data"]["pendingManualCount"] == 0

    mine = client.get(f"/admin-api/ims/perf/calc/{PERIOD}/mine", headers=staff)
    assert mine.json()["code"] == 0, mine.json()
    assert mine.json()["data"]["userName"] == "绩效员工甲"
    assert mine.json()["data"]["totalScore"] == 100
    assert mine.json()["data"]["gradeLevel"] == "EXCELLENT"
    assert "绩效员工乙" not in mine.text

    rank = client.get("/admin-api/ims/perf/rank/mine", headers=staff, params={"periodMonth": PERIOD})
    assert rank.json()["code"] == 0, rank.json()
    assert rank.json()["data"]["rankNo"] == 1
    assert rank.json()["data"]["gradeLevel"] == "EXCELLENT"
    assert rank.json()["data"]["deptTotalCount"] == 2
    assert rank.json()["data"]["scoreDistribution"] == {"excellent": 1, "qualified": 0, "improve": 1}
    private = client.get(f"/admin-api/ims/perf/rank/period/{PERIOD}", headers=staff)
    assert private.json()["code"] == 403
    board = client.get(
        f"/admin-api/ims/perf/rank/period/{PERIOD}",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    assert board.json()["code"] == 0
    peer_rank = next(row for row in board.json()["data"]["list"] if row["userName"] == "绩效员工乙")
    assert peer_rank["alertStatus"] == "ALERTED"
    assert peer_rank["gradeLevel"] == "IMPROVE"

    locked = client.post("/admin-api/ims/perf/calc/run", headers=auth, json={"periodMonth": PERIOD})
    assert locked.json()["code"] == 1155
    assert "R4" in locked.json()["msg"]
    locked_manual = client.put(
        f"/admin-api/ims/perf/calc/detail/{staff_row['id']}/manual",
        headers=auth,
        json={"metricId": train_id, "manualValue": 1, "supplementReason": "锁后改"},
    )
    assert locked_manual.json()["code"] == 1155

    templates = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"templateName": "费用报销", "status": "PUBLISHED", "pageNo": 1, "pageSize": 10},
    )
    tpl = next(row for row in templates.json()["data"]["list"] if row["templateCode"] == "FL-REIMB")
    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": tpl["id"],
            "businessKey": f"PERF-LOCK-{PERIOD}",
            "formData": {"title": f"绩效锁后更正 {PERIOD}"},
        },
    )
    assert started.json()["code"] == 0, started.json()
    todos = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 100},
    ).json()["data"]["list"]
    task = next(row for row in todos if (row.get("formData") or {}).get("title") == f"绩效锁后更正 {PERIOD}")
    handled = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "R4 绩效更正"},
    )
    assert handled.json()["code"] == 0, handled.json()

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "e2e_perf_staff", User.deleted == 0))
        assert user is not None
        user.created_at = datetime(2026, 9, 16, 9, 0, 0)
        db.commit()
    finally:
        db.close()

    rerun = client.post("/admin-api/ims/perf/calc/run", headers=auth, json={"periodMonth": PERIOD})
    assert rerun.json()["code"] == 0, rerun.json()
    latest = client.get(f"/admin-api/ims/perf/calc/{PERIOD}", headers=auth, params={"pageNo": 1, "pageSize": 100})
    staff_new = row_of(latest.json(), "绩效员工甲")
    assert staff_new["version"] == 2
    assert staff_new["resultStatus"] == "PENDING_APPROVE"
    assert staff_new["totalScore"] == 50
    assert staff_new["gradeLevel"] == "IMPROVE"
    assert staff_new["calcSnapshot"]["tenureRatio"] == 0.5
    assert any(item["version"] == 1 and item["resultStatus"] == "PUBLISHED" for item in staff_new["versionHistory"])
    again = client.get(f"/admin-api/ims/perf/calc/{PERIOD}/mine", headers=staff)
    assert again.json()["code"] == 1157
