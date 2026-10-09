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


def _window(hours_from: int, hours_to: int) -> dict:
    from datetime import timedelta

    from app.core import utcnow

    now = utcnow()
    start = now + timedelta(hours=hours_from)
    end = now + timedelta(hours=hours_to)
    return {
        "from": start.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "to": end.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
    }


def _question_id(auth: dict, question_no: str) -> int:
    resp = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 100, "questionNo": question_no},
    )
    rows = resp.json()["data"]["list"]
    assert rows, question_no
    return int(rows[0]["id"])


def test_perf_exam_questions_list():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "knowledgeDomain": "LIVE_RULE"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 3
    assert all(row["knowledgeDomain"] == "LIVE_RULE" for row in body["data"]["list"])
    assert any(row["questionNo"] == "EQ-001" for row in body["data"]["list"])
    again = client.get("/admin-api/ims/perf/exam/questions", headers=auth, params={"pageNo": 1, "pageSize": 50})
    listed = again.json()["data"]["list"]
    assert again.json()["data"]["total"] == 10
    assert sum(1 for row in listed if row["questionNo"] == "EQ-001") == 1


def _paper(auth: dict, payload: dict) -> dict:
    resp = client.post("/admin-api/ims/perf/exam/paper", headers=auth, json=payload)
    return resp.json()


def test_random_paper_1159_1160_dedup_makeup_and_window():
    login = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]
    auth = {"Authorization": f"Bearer {login['accessToken']}"}
    user_id = int(login["profile"]["userId"])
    q1 = _question_id(auth, "EQ-001")
    q9 = _question_id(auth, "EQ-009")

    over = _paper(
        auth,
        {
            "paperName": "随机超额",
            "paperType": "RANDOM",
            "strategy": [
                {"knowledgeDomain": "LIVE_RULE", "questionType": "SINGLE", "count": 5, "scorePerQuestion": 10}
            ],
            "totalScore": 50,
            "passScore": 30,
            "durationMinutes": 30,
        },
    )
    assert over["code"] == 1160
    assert "1" in over["msg"]

    overlap = _paper(
        auth,
        {
            "paperName": "随机去重超额",
            "paperType": "RANDOM",
            "strategy": [
                {"knowledgeDomain": "LIVE_RULE", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10},
                {"knowledgeDomain": "LIVE_RULE", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10},
            ],
            "totalScore": 20,
            "passScore": 10,
            "durationMinutes": 30,
        },
    )
    assert overlap["code"] == 1160

    mismatch = _paper(
        auth,
        {
            "paperName": "随机总分",
            "paperType": "RANDOM",
            "strategy": [
                {"knowledgeDomain": "LIVE_RULE", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10}
            ],
            "totalScore": 99,
            "passScore": 6,
            "durationMinutes": 30,
        },
    )
    assert mismatch["code"] == 1159

    created = _paper(
        auth,
        {
            "paperName": "随机去重",
            "paperType": "RANDOM",
            "strategy": [
                {"knowledgeDomain": "CONTENT_SKILL", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10},
                {"knowledgeDomain": "CONTENT_SKILL", "questionType": "MULTI", "count": 0, "scorePerQuestion": 10},
            ],
            "totalScore": 10,
            "passScore": 6,
            "durationMinutes": 30,
        },
    )
    assert created["code"] == 1001

    created = _paper(
        auth,
        {
            "paperName": "随机去重",
            "paperType": "RANDOM",
            "strategy": [
                {"knowledgeDomain": "CONTENT_SKILL", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10},
                {"knowledgeDomain": "CONTENT_SKILL", "questionType": "SINGLE", "count": 1, "scorePerQuestion": 10},
            ],
            "totalScore": 20,
            "passScore": 10,
            "durationMinutes": 30,
        },
    )
    assert created["code"] == 0
    paper_id = created["data"]["id"]
    assert created["data"]["paperNo"].startswith("EP")
    assert created["data"]["paperType"] == "RANDOM"
    client.put(f"/admin-api/ims/perf/exam/paper/{paper_id}/publish", headers=auth)
    assigned = client.post(
        f"/admin-api/ims/perf/exam/paper/{paper_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": _window(-1, 2)},
    ).json()
    assert assigned["code"] == 0
    started = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": paper_id}).json()
    assert started["code"] == 0
    questions = started["data"]["questions"]
    assert len(questions) == 2
    assert len({item["questionId"] for item in questions}) == 2
    assert "answer" not in questions[0]

    blocked = client.post(
        "/admin-api/ims/perf/exam/paper",
        headers=auth,
        json={
            "paperName": "窗口外",
            "paperType": "FIXED",
            "questionIds": [q1],
            "totalScore": 10,
            "passScore": 6,
            "durationMinutes": 20,
        },
    ).json()
    assert blocked["code"] == 0
    late_id = blocked["data"]["id"]
    client.put(f"/admin-api/ims/perf/exam/paper/{late_id}/publish", headers=auth)
    client.post(
        f"/admin-api/ims/perf/exam/paper/{late_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": _window(2, 3)},
    )
    outside = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": late_id}).json()
    assert outside["code"] == 1161

    fixed = _paper(
        auth,
        {
            "paperName": "补考卷",
            "paperType": "FIXED",
            "questionIds": [q1, q9],
            "totalScore": 20,
            "passScore": 20,
            "durationMinutes": 30,
        },
    )
    assert fixed["code"] == 0
    fixed_id = fixed["data"]["id"]
    bad_total = _paper(
        auth,
        {
            "paperName": "固定分不符",
            "paperType": "FIXED",
            "questionIds": [q1, q9],
            "totalScore": 15,
            "passScore": 10,
            "durationMinutes": 30,
        },
    )
    assert bad_total["code"] == 1159
    client.put(f"/admin-api/ims/perf/exam/paper/{fixed_id}/publish", headers=auth)
    client.post(
        f"/admin-api/ims/perf/exam/paper/{fixed_id}/assign",
        headers=auth,
        json={"userIds": [user_id], "examWindow": _window(-1, 2)},
    )
    first = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": fixed_id}).json()["data"]
    wrong = client.post(
        "/admin-api/ims/perf/exam/record/submit",
        headers=auth,
        json={
            "recordId": first["id"],
            "switchScreenCount": 0,
            "answers": [{"questionId": item["questionId"], "answer": 0} for item in first["questions"]],
        },
    ).json()
    assert wrong["code"] == 0
    assert wrong["data"]["examStatus"] == "GRADED"
    assert wrong["data"]["totalScore"] == 0
    again = client.post(
        "/admin-api/ims/perf/exam/record/submit",
        headers=auth,
        json={"recordId": first["id"], "switchScreenCount": 0, "answers": []},
    ).json()
    assert again["code"] == 1164

    makeup = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": fixed_id}).json()
    assert makeup["code"] == 0
    assert makeup["data"]["examStatus"] == "MAKEUP_EXAM"
    passed = client.post(
        "/admin-api/ims/perf/exam/record/submit",
        headers=auth,
        json={
            "recordId": makeup["data"]["id"],
            "switchScreenCount": 0,
            "answers": [{"questionId": item["questionId"], "answer": 1} for item in makeup["data"]["questions"]],
        },
    ).json()
    assert passed["code"] == 0
    assert passed["data"]["examStatus"] == "MAKEUP_EXAM"
    assert passed["data"]["totalScore"] == 20
    third = client.post("/admin-api/ims/perf/exam/record/start", headers=auth, json={"paperId": fixed_id}).json()
    assert third["code"] == 1001
    scores = client.get(
        "/admin-api/ims/perf/exam/record/scores",
        headers=auth,
        params={"paperId": fixed_id, "examStatus": "MAKEUP_EXAM"},
    ).json()
    assert scores["code"] == 0
    assert scores["data"]["total"] == 1
    assert scores["data"]["list"][0]["isMakeup"] is True
    assert scores["data"]["list"][0]["score"] == 20
