"""#76 培训统计看板：部门日汇总、时长排行、逾期、资料热度。

完成率总览是截至时刻的人次汇总，不再按近 N 天裁掉更早发布的任务。
"""

import os
import re
import uuid
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import TrainStatDaily, TrainTask, TrainTaskRecord
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
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", rate["data"]["asOf"])
    names = {row["taskName"] for row in rate["data"]["byTask"]}
    assert "看板完成率任务" in names
    assert E2E_OVERDUE_TASK_NAME in names
    assert "PERF95-TRAIN" in names
    assigned = sum(row["assignedCount"] for row in rate["data"]["byTask"])
    finished = sum(row["finishedCount"] for row in rate["data"]["byTask"])
    assert rate["data"]["totalFinishRate"] == round(finished * 100.0 / assigned, 2)
    hit = next(row for row in rate["data"]["byTask"] if row["taskName"] == "看板完成率任务")
    assert hit["finishRate"] == 100.0
    overdue = next(row for row in rate["data"]["byTask"] if row["taskName"] == E2E_OVERDUE_TASK_NAME)
    assert overdue["assignedCount"] == 1
    assert overdue["finishedCount"] == 0
    perf = next(row for row in rate["data"]["byTask"] if row["taskName"] == "PERF95-TRAIN")
    assert perf["assignedCount"] == 1
    assert perf["finishedCount"] == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00", perf["createdAt"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00", hit["createdAt"])
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


def test_finish_rollup_person_times_exclude_draft_and_revoked():
    auth = headers()
    material_id, task_id = _material_and_task(auth, "人次口径资料", "人次口径任务")
    progress = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "watchedSeconds": 60,
            "heartbeatAt": "2026-10-11T12:00:00+08:00",
        },
    )
    assert progress.json()["code"] == 0
    confirmed = client.post(f"/admin-api/ims/train/task/{task_id}/confirm", headers=auth, json={})
    assert confirmed.json()["data"]["confirmStatus"] == "CONFIRMED"

    db = SessionLocal()
    try:
        task = db.get(TrainTask, task_id)
        assert task is not None
        task.created_at = utcnow() - timedelta(days=60)
        for extra_user in (9101, 9102):
            db.add(
                TrainTaskRecord(
                    task_id=task_id,
                    user_id=extra_user,
                    tenant_id=task.tenant_id,
                    confirm_status=0,
                )
            )
        task.assigned_count = 3
        draft = TrainTask(
            task_no=f"TTDRAFT{uuid.uuid4().hex[:6]}",
            task_name="草稿任务不入汇总",
            material_ids=[material_id],
            assign_scope="BY_USER",
            assign_targets=[1],
            confirm_type="DURATION",
            assigned_count=1,
            status="DRAFT",
            creator_user_id=1,
            tenant_id=task.tenant_id,
            created_at=utcnow() - timedelta(days=2),
        )
        revoked = TrainTask(
            task_no=f"TTREVOKE{uuid.uuid4().hex[:6]}",
            task_name="撤销任务不入汇总",
            material_ids=[material_id],
            assign_scope="BY_USER",
            assign_targets=[1],
            confirm_type="DURATION",
            assigned_count=1,
            status="REVOKED",
            creator_user_id=1,
            tenant_id=task.tenant_id,
            created_at=utcnow() - timedelta(days=2),
        )
        db.add(draft)
        db.add(revoked)
        db.flush()
        db.add(TrainTaskRecord(task_id=draft.id, user_id=1, tenant_id=task.tenant_id, confirm_status=1))
        db.add(TrainTaskRecord(task_id=revoked.id, user_id=1, tenant_id=task.tenant_id, confirm_status=1))
        db.commit()
    finally:
        db.close()

    today = utcnow().strftime("%Y-%m-%d")
    rate = client.get(
        "/admin-api/ims/train/stat/finish-rate",
        headers=auth,
        params={"dateRange": f"{today},{today}"},
    ).json()
    assert rate["code"] == 0
    by_task = rate["data"]["byTask"]
    names = {row["taskName"] for row in by_task}
    assert "人次口径任务" in names
    assert "草稿任务不入汇总" not in names
    assert "撤销任务不入汇总" not in names
    assert E2E_OVERDUE_TASK_NAME in names
    wide = next(row for row in by_task if row["taskName"] == "人次口径任务")
    assert wide["assignedCount"] == 3
    assert wide["finishedCount"] == 1
    assert wide["finishRate"] == 33.33
    assigned = sum(row["assignedCount"] for row in by_task)
    finished = sum(row["finishedCount"] for row in by_task)
    assert rate["data"]["totalFinishRate"] == round(finished * 100.0 / assigned, 2)
    mean = round(sum(row["finishRate"] for row in by_task) / len(by_task), 2)
    assert rate["data"]["totalFinishRate"] != mean
