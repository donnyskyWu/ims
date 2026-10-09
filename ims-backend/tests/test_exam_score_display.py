"""#148 成绩展示：客观待阅、超时置顶、阅卷、姓名筛选、考试待办。"""

import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core import SessionLocal, utcnow
from app.exam_paper import exam_metric_value
from app.models import ExamRecord, User

client = TestClient(app)


def headers() -> dict:
    login = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]
    return {"Authorization": f"Bearer {login['accessToken']}"}, int(login["profile"]["userId"])


def window() -> dict:
    now = utcnow()
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=2)
    return {
        "from": start.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "to": end.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
    }


def question_id(auth: dict, question_no: str) -> int:
    resp = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 100, "questionNo": question_no},
    )
    rows = resp.json()["data"]["list"]
    assert rows, question_no
    return int(rows[0]["id"])


def publish_fixed(auth: dict, name: str, question_nos: list[str], total: float, pass_score: float) -> int:
    created = client.post(
        "/admin-api/ims/perf/exam/paper",
        headers=auth,
        json={
            "paperName": name,
            "paperType": "FIXED",
            "questionIds": [question_id(auth, no) for no in question_nos],
            "totalScore": total,
            "passScore": pass_score,
            "durationMinutes": 30,
        },
    )
    assert created.json()["code"] == 0, created.json()
    paper_id = created.json()["data"]["id"]
    published = client.put(f"/admin-api/ims/perf/exam/paper/{paper_id}/publish", headers=auth)
    assert published.json()["code"] == 0
    return paper_id


def test_score_display_grade_overdue_keyword_and_exam_todo():
    auth, user_id = headers()
    stamp = utcnow().strftime("%H%M%S%f")
    overdue_name = f"待阅超时{stamp}"
    fresh_name = f"待阅新卷{stamp}"
    overdue_id = publish_fixed(auth, overdue_name, ["EQ-001", "EQ-006"], 30, 30)
    fresh_id = publish_fixed(auth, fresh_name, ["EQ-001", "EQ-006"], 30, 30)

    assigned = client.post(
        f"/admin-api/ims/perf/exam/paper/{overdue_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": window()},
    )
    assert assigned.json()["code"] == 0
    assert assigned.json()["data"]["assignedCount"] >= 1
    again = client.post(
        f"/admin-api/ims/perf/exam/paper/{overdue_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": window()},
    )
    assert again.json()["code"] == 0

    todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"taskType": "exam", "status": "PENDING", "pageSize": 50},
    ).json()
    pending = [row for row in todos["data"]["list"] if row["title"] == f"考试待办：{overdue_name}"]
    assert len(pending) == 1
    assert pending[0]["taskType"] == "exam"

    started = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": overdue_id}).json()
    assert started["code"] == 0, started
    record_id = started["data"]["id"]
    essay = next(q for q in started["data"]["questions"] if q["questionType"] == "ESSAY")
    single = next(q for q in started["data"]["questions"] if q["questionType"] == "SINGLE")
    submitted = client.post(
        "/admin-api/ims/perf/exam/record/submit",
        headers=auth,
        json={
            "recordId": record_id,
            "switchScreenCount": 3,
            "answers": [
                {"questionId": single["questionId"], "answer": 0},
                {"questionId": essay["questionId"], "answer": "先测人群再放量"},
            ],
        },
    ).json()
    assert submitted["code"] == 0, submitted
    assert submitted["data"]["examStatus"] == "SUBMITTED"
    assert submitted["data"]["totalScore"] is None
    assert submitted["data"]["objectiveScore"] == 0
    assert submitted["data"]["forcedSubmit"] is True

    closed = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"taskType": "exam", "status": "PENDING", "pageSize": 50},
    ).json()
    assert all(row["title"] != f"考试待办：{overdue_name}" for row in closed["data"]["list"])

    client.post(
        f"/admin-api/ims/perf/exam/paper/{fresh_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": window()},
    )
    fresh_started = client.post(
        "/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": fresh_id}
    ).json()
    fresh_record = fresh_started["data"]["id"]
    fresh_essay = next(q for q in fresh_started["data"]["questions"] if q["questionType"] == "ESSAY")
    fresh_single = next(q for q in fresh_started["data"]["questions"] if q["questionType"] == "SINGLE")
    client.post(
        "/admin-api/ims/perf/exam/record/submit",
        headers=auth,
        json={
            "recordId": fresh_record,
            "switchScreenCount": 0,
            "answers": [
                {"questionId": fresh_single["questionId"], "answer": 0},
                {"questionId": fresh_essay["questionId"], "answer": "另一份简答"},
            ],
        },
    )

    db = SessionLocal()
    try:
        row = db.get(ExamRecord, record_id)
        assert row is not None
        row.submit_at = utcnow() - timedelta(hours=49)
        db.commit()
        user = db.scalar(select(User).where(User.id == user_id))
        assert user is not None
        tenant_id = user.tenant_id or 0
    finally:
        db.close()

    scores = client.get(
        "/admin-api/ims/perf/exam/record/scores",
        headers=auth,
        params={"pageNo": 1, "pageSize": 100},
    ).json()
    assert scores["code"] == 0
    ordered = [row["id"] for row in scores["data"]["list"]]
    assert ordered.index(record_id) < ordered.index(fresh_record)

    listed = client.get(
        "/admin-api/ims/perf/exam/record/scores",
        headers=auth,
        params={"paperId": overdue_id, "userKeyword": "管理员"},
    ).json()["data"]["list"]
    assert len(listed) == 1
    row = listed[0]
    assert row["gradeOverdue"] is True
    assert row["canGrade"] is True
    assert row["hasSubjective"] is True
    assert row["switchScreenCount"] == 3
    assert row["forcedSubmit"] is True
    assert row["score"] is None
    assert row["objectiveScore"] == 0
    assert row["subjectiveItems"]
    assert row["subjectiveItems"][0]["answer"] == "先测人群再放量"
    assert "reference" in row["subjectiveItems"][0]

    missed = client.get(
        "/admin-api/ims/perf/exam/record/scores",
        headers=auth,
        params={"paperId": overdue_id, "userKeyword": "没有这个人"},
    ).json()
    assert missed["data"]["list"] == []

    too_high = client.put(
        f"/admin-api/ims/perf/exam/record/{record_id}/grade",
        headers=auth,
        json={"gradings": [{"questionId": essay["questionId"], "score": 99}]},
    ).json()
    assert too_high["code"] == 1001

    before = SessionLocal()
    try:
        prior = exam_metric_value(before, tenant_id, user_id, utcnow().strftime("%Y-%m"))
    finally:
        before.close()

    graded = client.put(
        f"/admin-api/ims/perf/exam/record/{record_id}/grade",
        headers=auth,
        json={"gradings": [{"questionId": essay["questionId"], "score": 10, "comment": "要点齐全"}]},
    ).json()
    assert graded["code"] == 0
    assert graded["data"] is None

    after_list = client.get(
        "/admin-api/ims/perf/exam/record/scores",
        headers=auth,
        params={"paperId": overdue_id},
    ).json()["data"]["list"][0]
    assert after_list["examStatus"] == "GRADED"
    assert after_list["score"] == 10
    assert after_list["subjectiveScore"] == 10
    assert after_list["canGrade"] is False
    assert after_list["gradeOverdue"] is False

    checked = SessionLocal()
    try:
        value = exam_metric_value(checked, tenant_id, user_id, utcnow().strftime("%Y-%m"))
    finally:
        checked.close()
    assert value is not None
    if prior is None:
        assert value == round(10 / 30 * 100, 2)
    else:
        assert value != prior
