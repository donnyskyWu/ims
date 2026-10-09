"""#225 · 绩效本地空态与边角文案所依赖的接口契约。"""

import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import utcnow
from app.main import app

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_calc_observation_and_mine_empty_period():
    auth = headers()
    staff = headers("e2e_perf_staff")

    early = client.post("/admin-api/ims/perf/calc/run", headers=auth, json={"periodMonth": "2026-05"})
    assert early.json()["code"] == 1156
    assert early.json()["msg"] == "观察期不足：第 23 周前无基线数据"

    mine = client.get("/admin-api/ims/perf/calc/2031-08/mine", headers=staff)
    assert mine.json()["code"] == 0
    assert mine.json()["data"] is None

    empty_approve = client.put(
        "/admin-api/ims/perf/calc/2031-08/approve",
        headers=auth,
        json={"approve": False, "remark": ""},
    )
    assert empty_approve.json()["code"] == 1001
    assert "没有可核准" in empty_approve.json()["msg"]


def test_exam_filter_empty_and_inverted_window():
    auth = headers()
    login = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]
    user_id = int(login["profile"]["userId"])

    questions = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "stemKeyword": "没有这道题zzz"},
    )
    assert questions.json()["code"] == 0
    assert questions.json()["data"]["list"] == []
    assert questions.json()["data"]["total"] == 0

    papers = client.get(
        "/admin-api/ims/perf/exam/paper",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "paperName": "没有这张卷zzz"},
    )
    assert papers.json()["code"] == 0
    assert papers.json()["data"]["list"] == []

    bank = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 1, "questionNo": "EQ-001"},
    )
    question_id = int(bank.json()["data"]["list"][0]["id"])
    created = client.post(
        "/admin-api/ims/perf/exam/paper",
        headers=auth,
        json={
            "paperName": "窗口边角卷",
            "paperType": "FIXED",
            "questionIds": [question_id],
            "totalScore": 10,
            "passScore": 6,
            "durationMinutes": 20,
        },
    )
    assert created.json()["code"] == 0, created.json()
    paper_id = created.json()["data"]["id"]
    published = client.put(f"/admin-api/ims/perf/exam/paper/{paper_id}/publish", headers=auth)
    assert published.json()["code"] == 0, published.json()

    now = utcnow()
    later = (now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    earlier = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    inverted = client.post(
        f"/admin-api/ims/perf/exam/paper/{paper_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": {"from": later, "to": earlier}},
    )
    assert inverted.json()["code"] == 1001
    assert "早于结束" in inverted.json()["msg"]
