"""#76 培训统计看板：部门日汇总、时长排行、逾期、资料热度。口径与 finish-rate 一致。"""

import os
from datetime import datetime

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import TrainStatDaily, TrainTask
from app.train_stat_e2e_seed import E2E_OVERDUE_TASK_NAME

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _material_and_task(auth: dict, title: str, task_name: str) -> tuple[int, int]:
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": title,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/stat-tab.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": task_name,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    return material_id, created.json()["data"]["id"]


def _shift_task(task_id: int, created_at: datetime, deadline: datetime | None = None) -> None:
    db = SessionLocal()
    try:
        task = db.get(TrainTask, task_id)
        assert task is not None
        task.created_at = created_at
        if deadline is not None:
            task.deadline = deadline
        db.commit()
    finally:
        db.close()


def test_dept_rank_heat_match_finish_rate_caliber():
    auth = headers()
    material_id, task_id = _material_and_task(auth, "看板热度资料", "看板完成率任务")
    progress = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "currentPage": 1,
            "totalPages": 1,
            "watchedSeconds": 120,
            "heartbeatAt": "2026-10-08T12:00:00+08:00",
        },
    )
    assert progress.json()["code"] == 0
    confirmed = client.post(f"/admin-api/ims/train/task/{task_id}/confirm", headers=auth, json={})
    assert confirmed.json()["data"]["confirmStatus"] == "CONFIRMED"

    today = utcnow().strftime("%Y-%m-%d")
    window = f"{today},{today}"
    rate = client.get(
        "/admin-api/ims/train/stat/finish-rate",
        headers=auth,
        params={"dateRange": window},
    ).json()
    dept = client.get(
        "/admin-api/ims/train/stat/dept",
        headers=auth,
        params={"statDateRange": window},
    ).json()
    assert rate["code"] == 0
    assert dept["code"] == 0
    assert sum(row["assignedCount"] for row in rate["data"]["byDept"]) == sum(
        row["assignedCount"] for row in dept["data"]
    )
    assert sum(row["finishedCount"] for row in rate["data"]["byDept"]) == sum(
        row["finishedCount"] for row in dept["data"]
    )
    hit = next(row for row in rate["data"]["byTask"] if row["taskName"] == "看板完成率任务")
    assert hit["finishRate"] == 100.0
    today_rows = [row for row in dept["data"] if row["statDate"] == today]
    assert today_rows
    assert today_rows[0]["avgDurationMinutes"] == 2
    assert today_rows[0]["alertPushed"] is False

    rank = client.get(
        "/admin-api/ims/train/stat/rank",
        headers=auth,
        params={"dimension": "PERSON", "dateRange": window, "topN": 10},
    ).json()
    assert rank["code"] == 0
    person = next(row for row in rank["data"] if row["userId"] == 1)
    assert person["rank"] == 1
    assert person["totalDurationMinutes"] == 2
    assert person["finishRate"] == 100.0

    dept_rank = client.get(
        "/admin-api/ims/train/stat/rank",
        headers=auth,
        params={"dimension": "DEPT", "dateRange": window},
    ).json()
    assert dept_rank["code"] == 0
    assert dept_rank["data"][0]["totalDurationMinutes"] == 2
    assert dept_rank["data"][0]["finishRate"] == 100.0

    heat = client.get(
        "/admin-api/ims/train/stat/material-heat",
        headers=auth,
        params={"dateRange": window, "topN": 10},
    ).json()
    assert heat["code"] == 0
    material = next(row for row in heat["data"] if row["title"] == "看板热度资料")
    assert material["studyCount"] == 1
    assert material["avgDurationMinutes"] == 2
    assert material["materialType"] == "DOC"

    db = SessionLocal()
    try:
        stored = db.scalar(
            select(TrainStatDaily).where(
                TrainStatDaily.deleted == 0,
                TrainStatDaily.stat_date == datetime.strptime(today, "%Y-%m-%d").date(),
            )
        )
        assert stored is not None
        assert stored.finished_count == today_rows[0]["finishedCount"]
    finally:
        db.close()


def test_overdue_list_filters_and_invalid_params():
    auth = headers()
    overdue = client.get(
        "/admin-api/ims/train/stat/overdue",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    assert overdue["code"] == 0
    row = next(item for item in overdue["data"]["list"] if item["taskName"] == E2E_OVERDUE_TASK_NAME)
    assert row["taskNo"] == "TTE2EOD76"
    assert row["progress"] == 40
    assert row["overdueDays"] >= 10
    assert row["userName"] == "管理员"

    by_task = client.get(
        "/admin-api/ims/train/stat/overdue",
        headers=auth,
        params={"taskId": row["taskId"], "pageNo": 1, "pageSize": 10},
    ).json()
    assert by_task["data"]["total"] == 1
    assert by_task["data"]["list"][0]["taskId"] == row["taskId"]

    other_dept = client.get(
        "/admin-api/ims/train/stat/overdue",
        headers=auth,
        params={"deptId": 999999, "pageNo": 1, "pageSize": 10},
    ).json()
    assert all(item["taskName"] != E2E_OVERDUE_TASK_NAME for item in other_dept["data"]["list"])

    assert client.get("/admin-api/ims/train/stat/rank", headers=auth).json()["code"] == 1001
    assert (
        client.get(
            "/admin-api/ims/train/stat/rank",
            headers=auth,
            params={"dimension": "TEAM"},
        ).json()["code"]
        == 1001
    )
    assert (
        client.get(
            "/admin-api/ims/train/stat/dept",
            headers=auth,
            params={"statDateRange": "2026-10-10,2026-10-01"},
        ).json()["code"]
        == 1001
    )
    assert (
        client.get(
            "/admin-api/ims/train/stat/material-heat",
            headers=auth,
            params={"topN": 99},
        ).json()["code"]
        == 1001
    )


def test_dept_marks_two_consecutive_weeks_under_85():
    auth = headers()
    _, first = _material_and_task(auth, "低完成率资料甲", "低完成率任务甲")
    _, second = _material_and_task(auth, "低完成率资料乙", "低完成率任务乙")
    _shift_task(first, datetime(2026, 9, 4, 10, 0, 0))
    _shift_task(second, datetime(2026, 9, 11, 10, 0, 0))

    dept = client.get(
        "/admin-api/ims/train/stat/dept",
        headers=auth,
        params={"statDateRange": "2026-09-01,2026-09-30"},
    ).json()
    assert dept["code"] == 0
    flagged = [row for row in dept["data"] if row["alertPushed"]]
    assert flagged
    assert all(row["finishRate"] < 85 for row in flagged)
    assert {row["statDate"] for row in flagged} >= {"2026-09-04", "2026-09-11"}
