import os
import uuid
from datetime import timedelta

os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"
os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import TrainMaterial, TrainMaterialCate, TrainTask, TrainTaskRecord, User, UserRole

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_train_material_cates_create_list_offline():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    assert cates.json()["code"] == 0
    roots = cates.json()["data"]
    assert len(roots) >= 1
    leaf = roots[0]["children"][0]
    cate_id = leaf["id"]

    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "开播 SOP 2026",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/demo.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["materialNo"].startswith("MT")
    assert body["data"]["status"] == "PUBLISHED"
    material_id = body["data"]["id"]

    listed = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"cateId": cate_id, "title": "开播", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1

    offline = client.delete(f"/admin-api/ims/train/material/{material_id}", headers=auth)
    assert offline.json()["code"] == 0

    again = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"cateId": cate_id, "status": "OFFLINE", "pageNo": 1, "pageSize": 10},
    )
    assert again.json()["code"] == 0
    assert any(row["id"] == material_id for row in again.json()["data"]["list"])


def test_train_material_list_filters_type_status_position_and_empty():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    token = uuid.uuid4().hex[:8]
    doc_title = f"筛选文档 {token}"
    link_title = f"筛选外链 {token}"

    doc = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": doc_title,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/filter-doc.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    link = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": link_title,
            "cateId": cate_id,
            "materialType": "LINK",
            "linkUrl": "https://example.com/train-filter",
            "positionCodes": ["R6"],
            "publish": False,
        },
    )
    assert doc.json()["code"] == 0
    assert link.json()["code"] == 0
    doc_id = doc.json()["data"]["id"]
    link_id = link.json()["data"]["id"]

    listed = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": token, "pageNo": 1, "pageSize": 20},
    )
    listed_body = listed.json()
    assert listed_body["code"] == 0
    ids = {row["id"] for row in listed_body["data"]["list"]}
    assert ids == {doc_id, link_id}
    assert listed_body["data"]["total"] == 2

    by_type = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": token, "materialType": "LINK", "pageNo": 1, "pageSize": 20},
    )
    type_body = by_type.json()
    assert type_body["code"] == 0
    assert [row["id"] for row in type_body["data"]["list"]] == [link_id]
    assert type_body["data"]["total"] == 1

    by_status = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": token, "status": "DRAFT", "pageNo": 1, "pageSize": 20},
    )
    status_rows = by_status.json()["data"]["list"]
    assert [row["id"] for row in status_rows] == [link_id]
    assert status_rows[0]["status"] == "DRAFT"

    by_pos = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": token, "positionCode": "R5", "pageNo": 1, "pageSize": 20},
    )
    pos_body = by_pos.json()
    assert pos_body["code"] == 0
    assert [row["id"] for row in pos_body["data"]["list"]] == [doc_id]
    assert pos_body["data"]["list"][0]["positionCodes"] == ["R5"]

    mismatch = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": token, "materialType": "DOC", "positionCode": "R6", "pageNo": 1, "pageSize": 20},
    )
    assert mismatch.json()["code"] == 0
    assert mismatch.json()["data"]["total"] == 0
    assert mismatch.json()["data"]["list"] == []

    missing = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"title": f"missing-{token}", "pageNo": 1, "pageSize": 20},
    )
    assert missing.json()["data"]["total"] == 0

    bad_type = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"materialType": "PDF"},
    )
    assert bad_type.json()["code"] == 1001

    bad_pos = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"positionCode": 'R5"'},
    )
    assert bad_pos.json()["code"] == 1001


def test_train_task_create_and_list():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "任务关联资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/task.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]

    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "新人 onboarding",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["taskNo"].startswith("TT")
    assert body["data"]["assignedCount"] == 1

    listed = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": "onboarding", "pageNo": 1, "pageSize": 10},
    )
    list_body = listed.json()
    assert list_body["code"] == 0
    assert list_body["data"]["total"] >= 1
    row = next(r for r in list_body["data"]["list"] if r["taskName"] == "新人 onboarding")
    assert row["finishRate"] == 0.0
    assert row["materialCount"] == 1


def test_train_task_1102_deadline_past():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "过期测试资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/past.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]
    bad = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "过期任务",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2020-01-01T00:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert bad.json()["code"] == 1102
    assert bad.json()["msg"] == "截止时间早于当前时间"

    malformed = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "坏截止时间",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "昨天",
            "confirmType": "DURATION",
        },
    )
    assert malformed.json()["code"] == 1001
    assert malformed.json()["msg"] == "deadline 无效"


def test_train_material_requires_position_when_category_has_none():
    auth = headers()
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        assert admin is not None
        cate = TrainMaterialCate(
            cate_name=f"无岗位 {uuid.uuid4().hex[:6]}",
            parent_id=None,
            position_code="",
            sort_order=99,
            tenant_id=admin.tenant_id or 0,
            deleted=0,
        )
        db.add(cate)
        db.commit()
        cate_id = cate.id
    finally:
        db.close()

    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "无岗位资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/no-position.pdf",
            "positionCodes": [],
            "publish": True,
        },
    )
    body = created.json()
    assert body["code"] == 1001, body
    assert body["msg"] == "岗位必填"


def test_train_task_progress_confirm_and_records():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "进度确认资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/progress.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]

    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "进度闭环任务",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    task_id = created.json()["data"]["id"]

    prog = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "currentPage": 1,
            "totalPages": 1,
            "heartbeatAt": "2026-10-08T12:00:00+08:00",
        },
    )
    assert prog.json()["code"] == 0
    assert prog.json()["data"]["progress"] == 100

    bad_confirm = client.post(f"/admin-api/ims/train/task/{task_id}/confirm", headers=auth, json={})
    assert bad_confirm.json()["code"] == 0
    assert bad_confirm.json()["data"]["confirmStatus"] == "CONFIRMED"

    records = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "confirmStatus": "CONFIRMED", "pageNo": 1, "pageSize": 10},
    )
    assert records.json()["code"] == 0
    assert records.json()["data"]["total"] >= 1
    assert records.json()["data"]["list"][0]["confirmStatus"] == "CONFIRMED"


def test_train_stat_summary():
    auth = headers()
    summary = client.get("/admin-api/ims/train/stat/summary", headers=auth)
    assert summary.json()["code"] == 0
    data = summary.json()["data"]
    assert "taskCount" in data
    assert "avgFinishRate" in data


def test_train_stat_finish_rate_after_confirm():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "完成率统计资料",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/rate.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "完成率统计任务",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    task_id = created.json()["data"]["id"]
    client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "currentPage": 1,
            "totalPages": 1,
            "heartbeatAt": "2026-10-08T12:00:00+08:00",
        },
    )
    client.post(f"/admin-api/ims/train/task/{task_id}/confirm", headers=auth, json={})

    rate = client.get("/admin-api/ims/train/stat/finish-rate", headers=auth)
    assert rate.json()["code"] == 0
    data = rate.json()["data"]
    assert "totalFinishRate" in data
    assert data["totalFinishRate"] >= 0
    hit = next((row for row in data["byTask"] if row["taskName"] == "完成率统计任务"), None)
    assert hit is not None
    assert hit["finishedCount"] == 1
    assert hit["assignedCount"] == 1
    assert hit["finishRate"] == 100.0


def _published_material(auth: dict, title: str) -> int:
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": title,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/quiz.pdf",
            "publish": True,
        },
    )
    body = material.json()
    assert body["code"] == 0, body
    return body["data"]["id"]


def _quiz_task(auth: dict, material_id: int, name: str, quiz: list, pass_score: int | None):
    payload = {
        "taskName": name,
        "materialIds": [material_id],
        "assignScope": "BY_USER",
        "assignTargetUserIds": [1],
        "deadline": "2026-12-31T18:00:00+08:00",
        "confirmType": "QUIZ",
        "quiz": quiz,
    }
    if pass_score is not None:
        payload["passScore"] = pass_score
    return client.post("/admin-api/ims/train/task", headers=auth, json=payload)


def _peer_headers() -> dict:
    username = f"quiz_{uuid.uuid4().hex[:8]}"
    mobile = f"137{uuid.uuid4().int % 10**8:08d}"
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers(),
        json={"username": username, "nickname": "问卷旁听", "mobile": mobile, "password": "Admin@123"},
    )
    body = created.json()
    assert body["code"] == 0, body
    user_id = int(body["data"]["id"])
    db = SessionLocal()
    try:
        role_id = db.scalar(select(UserRole.role_id).where(UserRole.user_id == 1))
        assert role_id
        db.add(UserRole(user_id=user_id, role_id=role_id, tenant_id=0))
        db.commit()
    finally:
        db.close()
    logged = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"})
    token = logged.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_QUIZ = [
    {"question": "开播前要确认什么", "options": ["设备与网络", "随便开"], "answerIndex": 0},
    {"question": "话术可以照着念吗", "options": ["可以", "不行"], "answerIndex": 1},
]


def test_train_quiz_compose_rejects_bad_paper():
    auth = headers()
    material_id = _published_material(auth, "组卷校验资料")
    cases = [
        ({"quiz": [], "passScore": 1}, "quiz 必填"),
        ({"quiz": SAMPLE_QUIZ}, "passScore 必填"),
        ({"quiz": SAMPLE_QUIZ, "passScore": 3}, "及格分须在 1 到题目数之间"),
        (
            {"quiz": [{"question": "只有一项", "options": ["甲"], "answerIndex": 0}], "passScore": 1},
            "每题选项至少 2 项",
        ),
        (
            {"quiz": [{"question": "空选项", "options": ["甲", "  "], "answerIndex": 0}], "passScore": 1},
            "选项内容不能为空",
        ),
        (
            {"quiz": [{"question": "下标越界", "options": ["甲", "乙"], "answerIndex": 2}], "passScore": 1},
            "答案下标超出选项",
        ),
        (
            {"quiz": [{"question": "   ", "options": ["甲", "乙"], "answerIndex": 0}], "passScore": 1},
            "题目必填且不超过 256 字",
        ),
    ]
    for extra, message in cases:
        payload = {
            "taskName": "坏卷",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "QUIZ",
            **extra,
        }
        bad = client.post("/admin-api/ims/train/task", headers=auth, json=payload)
        body = bad.json()
        assert body["code"] == 1001, body
        assert body["msg"] == message


def test_train_quiz_grade_retake_hides_answer_and_blocks_stranger():
    auth = headers()
    material_id = _published_material(auth, "问卷判分资料")
    name = f"问卷判分 {uuid.uuid4().hex[:6]}"
    created = _quiz_task(auth, material_id, name, SAMPLE_QUIZ, 2)
    body = created.json()
    assert body["code"] == 0, body
    data = body["data"]
    task_id = data["id"]
    assert data["questionCount"] == 2
    assert data["passScore"] == 2
    assert data["quiz"][0] == {"question": "开播前要确认什么", "options": ["设备与网络", "随便开"]}
    assert "answerIndex" not in data["quiz"][0]

    listed = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": name, "pageNo": 1, "pageSize": 10},
    )
    row = next(item for item in listed.json()["data"]["list"] if item["id"] == task_id)
    assert "answerIndex" not in row["quiz"][1]

    stranger = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=_peer_headers(),
        json={"answers": [{"questionIndex": 0, "answerIndex": 0}, {"questionIndex": 1, "answerIndex": 1}]},
    )
    assert stranger.json()["code"] == 1105

    incomplete = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 0}]},
    )
    assert incomplete.json()["code"] == 1001
    assert incomplete.json()["msg"] == "问卷未答完"

    failed = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 1}, {"questionIndex": 1, "answerIndex": 0}]},
    )
    failed_body = failed.json()
    assert failed_body["code"] == 0, failed_body
    assert failed_body["data"]["isPassed"] is False
    assert failed_body["data"]["confirmStatus"] == "NOT_CONFIRMED"
    assert failed_body["data"]["confirmScore"] == 0
    assert failed_body["data"]["passScore"] == 2

    records = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "pageNo": 1, "pageSize": 10},
    )
    rec = records.json()["data"]["list"][0]
    assert rec["confirmStatus"] == "NOT_CONFIRMED"
    assert rec["confirmScore"] == 0

    passed = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 0}, {"questionIndex": 1, "answerIndex": 1}]},
    )
    passed_body = passed.json()
    assert passed_body["code"] == 0, passed_body
    assert passed_body["data"]["isPassed"] is True
    assert passed_body["data"]["confirmStatus"] == "CONFIRMED"
    assert passed_body["data"]["confirmScore"] == 2

    again = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 1}, {"questionIndex": 1, "answerIndex": 0}]},
    )
    again_body = again.json()
    assert again_body["code"] == 0, again_body
    assert again_body["data"]["confirmStatus"] == "CONFIRMED"
    assert again_body["data"]["confirmScore"] == 2

    listed_after = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": name, "pageNo": 1, "pageSize": 10},
    )
    done = next(item for item in listed_after.json()["data"]["list"] if item["id"] == task_id)
    assert done["finishRate"] == 100.0

    bare = _quiz_task(auth, material_id, f"空卷 {uuid.uuid4().hex[:6]}", SAMPLE_QUIZ, 1)
    bare_id = bare.json()["data"]["id"]
    db = SessionLocal()
    try:
        row = db.get(TrainTask, bare_id)
        assert row is not None
        row.quiz = []
        db.commit()
    finally:
        db.close()
    missing = client.post(f"/admin-api/ims/train/task/{bare_id}/confirm", headers=auth, json={"answers": []})
    assert missing.json()["code"] == 1104
    assert missing.json()["msg"] == "问卷未配置"


def _leaf_cate(auth: dict) -> int:
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    return cates.json()["data"][0]["children"][0]["id"]


def _publish_material(auth: dict, title: str, file_key: str = "train/v1.pdf") -> dict:
    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": title,
            "cateId": _leaf_cate(auth),
            "materialType": "DOC",
            "fileKey": file_key,
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]


def test_train_material_new_version_keeps_snapshot_and_weekly_rate():
    auth = headers()
    original = _publish_material(auth, "周更资料原文", "train/week-v1.pdf")
    assert original["version"] == 1
    assert original["versions"] == []

    revised = client.put(
        f"/admin-api/ims/train/material/{original['id']}",
        headers=auth,
        json={
            "title": "周更资料修订",
            "cateId": original["cateId"],
            "materialType": "DOC",
            "fileKey": "train/week-v2.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    body = revised.json()
    assert body["code"] == 0, body
    assert body["data"]["version"] == 2
    assert body["data"]["materialNo"] == original["materialNo"]
    assert body["data"]["versions"][0]["version"] == 1
    assert body["data"]["versions"][0]["title"] == "周更资料原文"
    assert body["data"]["versions"][0]["materialType"] == "DOC"
    assert body["data"]["versions"][0]["fileKey"] == "train/week-v1.pdf"

    third = client.put(
        f"/admin-api/ims/train/material/{original['id']}",
        headers=auth,
        json={
            "title": "周更资料再修订",
            "cateId": original["cateId"],
            "materialType": "DOC",
            "fileKey": "train/week-v3.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    third_body = third.json()
    assert third_body["code"] == 0, third_body
    history = {item["version"]: item for item in third_body["data"]["versions"]}
    assert history[1]["title"] == "周更资料原文"
    assert history[1]["fileKey"] == "train/week-v1.pdf"
    assert history[2]["title"] == "周更资料修订"

    stale = _publish_material(auth, "上周未更新资料", "train/stale.pdf")
    db = SessionLocal()
    try:
        material = db.get(TrainMaterial, stale["id"])
        assert material is not None
        material.updated_at = utcnow() - timedelta(days=10)
        db.commit()
    finally:
        db.close()

    metrics = client.get("/admin-api/ims/train/material/weekly-update-metrics", headers=auth)
    data = metrics.json()
    assert data["code"] == 0, data
    assert data["data"]["shouldUpdateCount"] >= 2
    assert data["data"]["weeklyUpdateRate"] < 100
    numbers = {item["materialNo"] for item in data["data"]["unupdatedList"]}
    assert stale["materialNo"] in numbers
    assert original["materialNo"] not in numbers

    bad = client.get(
        "/admin-api/ims/train/material/weekly-update-metrics",
        headers=auth,
        params={"weekStart": "2026/10/09"},
    )
    assert bad.json()["code"] == 1001

    missing = client.put(
        "/admin-api/ims/train/material/99999999",
        headers=auth,
        json={
            "title": "不存在",
            "cateId": original["cateId"],
            "materialType": "DOC",
            "fileKey": "train/missing.pdf",
            "positionCodes": ["R5"],
            "publish": True,
        },
    )
    assert missing.json()["code"] == 1101


def test_train_task_edit_before_deadline_keeps_progress():
    auth = headers()
    material = _publish_material(auth, "任务编辑资料", "train/task-edit.pdf")
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "编辑前任务",
            "materialIds": [material["id"]],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert created.json()["code"] == 0, created.json()
    task_id = created.json()["data"]["id"]
    prog = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material["id"],
            "currentPage": 1,
            "totalPages": 1,
            "heartbeatAt": "2026-10-09T12:00:00+08:00",
        },
    )
    assert prog.json()["data"]["progress"] == 100

    renamed = client.put(
        f"/admin-api/ims/train/task/{task_id}",
        headers=auth,
        json={
            "taskName": "编辑后任务",
            "materialIds": [material["id"]],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    renamed_body = renamed.json()
    assert renamed_body["code"] == 0, renamed_body
    assert renamed_body["data"]["taskName"] == "编辑后任务"
    assert renamed_body["data"]["status"] == "IN_PROGRESS"

    db = SessionLocal()
    try:
        record = db.scalar(select(TrainTaskRecord).where(TrainTaskRecord.task_id == task_id, TrainTaskRecord.user_id == 1))
        assert record is not None
        assert record.progress == 100
        assert record.deleted == 0
    finally:
        db.close()

    past = client.put(
        f"/admin-api/ims/train/task/{task_id}",
        headers=auth,
        json={
            "taskName": "编辑后任务",
            "materialIds": [material["id"]],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2020-01-01T00:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert past.json()["code"] == 1102
    assert past.json()["msg"] == "截止时间早于当前时间"

    db = SessionLocal()
    try:
        task = db.get(TrainTask, task_id)
        assert task is not None
        task.deadline = utcnow() - timedelta(hours=1)
        db.commit()
    finally:
        db.close()
    locked = client.put(
        f"/admin-api/ims/train/task/{task_id}",
        headers=auth,
        json={
            "taskName": "过期后再改",
            "materialIds": [material["id"]],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert locked.json()["code"] == 1102
    assert locked.json()["msg"] == "已过截止时间，不能编辑"


def test_train_link_preview_snapshot_and_quiz_duplicate_options():
    auth = headers()
    cate_id = _leaf_cate(auth)
    bad = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "坏外链",
            "cateId": cate_id,
            "materialType": "LINK",
            "linkUrl": "notaurl",
            "publish": True,
        },
    )
    assert bad.json()["code"] == 1001
    assert bad.json()["msg"] == "linkUrl 须为 http(s) 地址"

    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "外链原文",
            "cateId": cate_id,
            "materialType": "LINK",
            "linkUrl": "https://example.com/ims-186-v1",
            "publish": True,
        },
    )
    original = created.json()
    assert original["code"] == 0, original
    assert original["data"]["versions"] == []
    assert original["data"]["linkUrl"] == "https://example.com/ims-186-v1"

    revised = client.put(
        f"/admin-api/ims/train/material/{original['data']['id']}",
        headers=auth,
        json={
            "title": "外链修订",
            "cateId": cate_id,
            "materialType": "LINK",
            "linkUrl": "https://example.com/ims-186-v2",
            "publish": True,
        },
    )
    body = revised.json()
    assert body["code"] == 0, body
    assert body["data"]["version"] == 2
    assert body["data"]["linkUrl"] == "https://example.com/ims-186-v2"
    snap = body["data"]["versions"][0]
    assert snap["version"] == 1
    assert snap["title"] == "外链原文"
    assert snap["materialType"] == "LINK"
    assert snap["linkUrl"] == "https://example.com/ims-186-v1"
    assert snap["fileKey"] in (None, "")

    material_id = _published_material(auth, "重复选项资料")
    dup = _quiz_task(
        auth,
        material_id,
        "重复选项",
        [{"question": "只留一个对", "options": ["对", "对"], "answerIndex": 0}],
        1,
    )
    assert dup.json()["code"] == 1001
    assert dup.json()["msg"] == "选项不能重复"
