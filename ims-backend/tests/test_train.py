import json
import os
import uuid
from datetime import timedelta, timezone

os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"
os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import (
    Menu,
    OrgEvent,
    Role,
    RoleMenu,
    Todo,
    TrainMaterial,
    TrainMaterialCate,
    TrainTask,
    TrainTaskRecord,
    User,
    UserDept,
    UserMapping,
    UserRole,
)
from app.security import hash_password

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


def test_train_material_file_whitelist_and_position_catalog():
    auth = headers()
    rejected = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "非法扩展名",
            "materialType": "DOC",
            "fileKey": "TB-bad.exe",
            "positionCodes": ["全员通用"],
            "publish": False,
        },
    )
    rejected_body = rejected.json()
    assert rejected_body["code"] == 1001, rejected_body
    assert rejected_body["msg"] == "类型不支持"

    catalog = client.get("/admin-api/ims/train/material/positions", headers=auth)
    catalog_body = catalog.json()
    assert catalog_body["code"] == 0, catalog_body
    codes = [row["code"] for row in catalog_body["data"]]
    assert "全员通用" in codes
    assert any(row["name"] == "直播运营" and row["code"] == "R5" for row in catalog_body["data"])
    assert any(row["code"] == "编导" for row in catalog_body["data"])

    uploaded = client.post(
        "/admin-api/ims/train/material/file",
        headers=auth,
        data={"materialType": "DOC"},
        files={"file": ("note.pdf", b"%PDF-1.4 demo", "application/pdf")},
    )
    uploaded_body = uploaded.json()
    assert uploaded_body["code"] == 0, uploaded_body
    assert uploaded_body["data"]["fileKey"]
    assert uploaded_body["data"]["fileName"] == "note.pdf"

    exe = client.post(
        "/admin-api/ims/train/material/file",
        headers=auth,
        data={"materialType": "DOC"},
        files={"file": ("TB-bad.exe", b"MZ", "application/octet-stream")},
    )
    assert exe.json()["code"] == 1001
    assert exe.json()["msg"] == "类型不支持"

    video = client.post(
        "/admin-api/ims/train/material/file",
        headers=auth,
        data={"materialType": "VIDEO"},
        files={"file": ("clip.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert video.json()["code"] == 1001
    assert video.json()["msg"] == "类型不支持"

    oversized = client.post(
        "/admin-api/ims/train/material/file",
        headers=auth,
        data={"materialType": "DOC"},
        files={"file": ("big.pdf", b"x" * (20 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert oversized.json()["code"] == 5005

    saved = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "岗位多选资料",
            "materialType": "DOC",
            "fileKey": uploaded_body["data"]["fileKey"],
            "positionCodes": ["主播组", "全员通用"],
            "publish": True,
        },
    )
    saved_body = saved.json()
    assert saved_body["code"] == 0, saved_body
    assert saved_body["data"]["positionCodes"] == ["主播组", "全员通用"]

    listed = client.get(
        "/admin-api/ims/train/material/list",
        headers=auth,
        params={"positionCode": "全员通用", "title": "岗位多选资料", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert any(row["id"] == saved_body["data"]["id"] for row in listed.json()["data"]["list"])


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


def test_train_task_pushes_study_todo():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    material = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": f"待办资料 {uuid.uuid4().hex[:6]}",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/todo.pdf",
            "publish": True,
        },
    )
    material_id = material.json()["data"]["id"]
    name = f"学习待办任务 {uuid.uuid4().hex[:6]}"
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": name,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    task_id = body["data"]["id"]
    todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50, "status": "PENDING"},
    )
    assert todos.json()["code"] == 0, todos.json()
    hit = next(
        (
            item
            for item in todos.json()["data"]["list"]
            if item.get("taskType") == "train_study" and item.get("refId") == task_id
        ),
        None,
    )
    assert hit is not None, todos.json()["data"]["list"]
    assert name in hit["title"]

    db = SessionLocal()
    try:
        row = db.scalar(select(Todo).where(Todo.id == hit["id"]))
        assert row is not None
        assert row.status == "PENDING"
    finally:
        db.close()


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

    short = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "watchedSeconds": 10,
            "heartbeatAt": "2026-10-08T12:00:00+08:00",
        },
    )
    assert short.json()["code"] == 0
    assert short.json()["data"]["progress"] < 100
    blocked = client.post(f"/admin-api/ims/train/task/{task_id}/confirm", headers=auth, json={})
    assert blocked.json()["code"] == 1104
    assert "还差" in blocked.json()["msg"]

    prog = client.put(
        f"/admin-api/ims/train/task/{task_id}/progress",
        headers=auth,
        json={
            "materialId": material_id,
            "watchedSeconds": 60,
            "heartbeatAt": "2026-10-08T12:00:15+08:00",
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
            "watchedSeconds": 60,
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


def _dept_learner(nickname: str) -> tuple[dict, int]:
    """部门数据范围、只有工作台菜单，没有培训菜单。对应 tc_r6 这类被指派人。"""
    username = f"r6_{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname=nickname,
            mobile=f"136{uuid.uuid4().int % 10**8:08d}",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
        role = Role(
            role_name=nickname,
            role_key=f"r6_{uuid.uuid4().hex[:10]}",
            data_scope="DEPT",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        menu = db.scalar(select(Menu).where(Menu.deleted == 0, Menu.route == "/ims/workbench"))
        assert menu is not None
        db.add(
            RoleMenu(
                role_id=role.id,
                menu_id=menu.id,
                perm_code=menu.perm_code or "auth:workbench:query",
                tenant_id=0,
            )
        )
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.commit()
        user_id = int(user.id)
    finally:
        db.close()
    logged = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"})
    token = logged.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_train_study_assignee_reads_own_task_stranger_forbidden():
    auth = headers()
    assignee_auth, assignee_id = _dept_learner("内容运营")
    stranger_auth, _stranger_id = _dept_learner("旁听")
    material_id = _published_material(auth, f"学习中心资料 {uuid.uuid4().hex[:6]}")
    name = f"指派学习 {uuid.uuid4().hex[:6]}"
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": name,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [assignee_id],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "QUIZ",
            "quiz": SAMPLE_QUIZ,
            "passScore": 60,
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    task_id = body["data"]["id"]

    opened = client.get(f"/admin-api/ims/train/study/{task_id}", headers=assignee_auth)
    opened_body = opened.json()
    assert opened.status_code == 200, opened_body
    assert opened_body["code"] == 0, opened_body
    task = opened_body["data"]["task"]
    assert task["id"] == task_id
    assert task["confirmType"] == "QUIZ"
    assert task["quiz"][0]["question"] == "开播前要确认什么"
    assert "answerIndex" not in task["quiz"][0]
    assert any(item["id"] == material_id for item in opened_body["data"]["materials"])
    assert opened_body["data"]["progress"]["userId"] == assignee_id
    assert opened_body["data"]["progress"]["confirmStatus"] == "NOT_CONFIRMED"

    stranger = client.get(f"/admin-api/ims/train/study/{task_id}", headers=stranger_auth)
    stranger_body = stranger.json()
    assert stranger.status_code == 403, stranger_body
    assert stranger_body["code"] == 403
    assert stranger_body["msg"] == "仅被指派人可学习本任务"

    admin_denied = client.get(f"/admin-api/ims/train/study/{task_id}", headers=auth)
    admin_body = admin_denied.json()
    assert admin_denied.status_code == 403, admin_body
    assert admin_body["code"] == 403
    assert admin_body["msg"] == "仅被指派人可学习本任务"


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
        ({"quiz": SAMPLE_QUIZ, "passScore": 101}, "及格分须在 0 到 100 之间"),
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
    created = _quiz_task(auth, material_id, name, SAMPLE_QUIZ, 100)
    body = created.json()
    assert body["code"] == 0, body
    data = body["data"]
    task_id = data["id"]
    assert data["questionCount"] == 2
    assert data["passScore"] == 100
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
    assert incomplete.json()["msg"] == "还有 1 题未作答"

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
    assert failed_body["data"]["passScore"] == 100

    half = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 0}, {"questionIndex": 1, "answerIndex": 0}]},
    )
    half_body = half.json()
    assert half_body["code"] == 0, half_body
    assert half_body["data"]["isPassed"] is False
    assert half_body["data"]["confirmScore"] == 50

    records = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "pageNo": 1, "pageSize": 10},
    )
    rec = records.json()["data"]["list"][0]
    assert rec["confirmStatus"] == "NOT_CONFIRMED"
    assert rec["confirmScore"] == 50

    passed = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 0}, {"questionIndex": 1, "answerIndex": 1}]},
    )
    passed_body = passed.json()
    assert passed_body["code"] == 0, passed_body
    assert passed_body["data"]["isPassed"] is True
    assert passed_body["data"]["confirmStatus"] == "CONFIRMED"
    assert passed_body["data"]["confirmScore"] == 100

    again = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 1}, {"questionIndex": 1, "answerIndex": 0}]},
    )
    again_body = again.json()
    assert again_body["code"] == 0, again_body
    assert again_body["data"]["confirmStatus"] == "CONFIRMED"
    assert again_body["data"]["confirmScore"] == 100

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
            "watchedSeconds": 60,
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
    assert dup.json()["msg"] == "选项内容不能重复"


def test_train_task_filter_blank_confirm_and_record_overdue_edges():
    auth = headers()
    material = _publish_material(auth, f"筛选资料 {uuid.uuid4().hex[:6]}")
    quiz_name = f"问卷筛选 {uuid.uuid4().hex[:6]}"
    duration_name = f"学时筛选 {uuid.uuid4().hex[:6]}"
    quiz = _quiz_task(auth, material["id"], quiz_name, SAMPLE_QUIZ, 1)
    assert quiz.json()["code"] == 0, quiz.json()
    duration = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": duration_name,
            "materialIds": [material["id"]],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert duration.json()["code"] == 0, duration.json()
    task_id = duration.json()["data"]["id"]

    blank = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": "   ", "pageNo": 1, "pageSize": 10},
    )
    assert blank.json()["code"] == 0
    assert blank.json()["data"]["total"] >= 2

    only_quiz = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": "筛选", "confirmType": "QUIZ", "pageNo": 1, "pageSize": 20},
    )
    quiz_names = [row["taskName"] for row in only_quiz.json()["data"]["list"]]
    assert quiz_name in quiz_names
    assert duration_name not in quiz_names

    missing = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": f"不存在{uuid.uuid4().hex}", "pageNo": 1, "pageSize": 10},
    )
    assert missing.json()["data"]["total"] == 0
    assert missing.json()["data"]["list"] == []

    db = SessionLocal()
    try:
        row = db.get(TrainTask, task_id)
        assert row is not None
        row.deadline = utcnow() - timedelta(days=2)
        db.commit()
    finally:
        db.close()

    overdue = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "overdue": True, "pageNo": 1, "pageSize": 10},
    )
    overdue_body = overdue.json()
    assert overdue_body["code"] == 0, overdue_body
    assert overdue_body["data"]["total"] == 1
    rec = overdue_body["data"]["list"][0]
    assert rec["isOverdue"] is True
    assert rec["overdueDays"] >= 1
    assert rec["deptName"]
    assert rec["confirmStatus"] == "NOT_CONFIRMED"

    confirmed = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "confirmStatus": "CONFIRMED", "pageNo": 1, "pageSize": 10},
    )
    assert confirmed.json()["data"]["total"] == 0


def test_train_quiz_duplicate_and_invalid_option_copy():
    auth = headers()
    material_id = _published_material(auth, "问卷边界资料")
    dup_opt = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "重复选项",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "QUIZ",
            "passScore": 1,
            "quiz": [{"question": "唯一题", "options": ["相同", "相同"], "answerIndex": 0}],
        },
    )
    assert dup_opt.json()["code"] == 1001
    assert dup_opt.json()["msg"] == "选项内容不能重复"

    dup_q = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "重复题目",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "QUIZ",
            "passScore": 1,
            "quiz": [
                {"question": "同一题", "options": ["甲", "乙"], "answerIndex": 0},
                {"question": "同一题", "options": ["丙", "丁"], "answerIndex": 1},
            ],
        },
    )
    assert dup_q.json()["code"] == 1001
    assert dup_q.json()["msg"] == "题目不能重复"

    created = _quiz_task(auth, material_id, f"越界作答 {uuid.uuid4().hex[:6]}", SAMPLE_QUIZ, 1)
    task_id = created.json()["data"]["id"]
    bad = client.post(
        f"/admin-api/ims/train/task/{task_id}/confirm",
        headers=auth,
        json={"answers": [{"questionIndex": 0, "answerIndex": 9}, {"questionIndex": 1, "answerIndex": 0}]},
    )
    assert bad.json()["code"] == 1001
    assert bad.json()["msg"] == "选项无效，请重新选择"


def test_train_finish_rate_rejects_inverted_range():
    auth = headers()
    bad = client.get(
        "/admin-api/ims/train/stat/finish-rate",
        headers=auth,
        params={"dateRange": "2026-12-31,2026-01-01"},
    )
    assert bad.json()["code"] == 1001
    assert bad.json()["msg"] == "日期范围起大于止"
    malformed = client.get(
        "/admin-api/ims/train/stat/finish-rate",
        headers=auth,
        params={"dateRange": "not-a-range"},
    )
    assert malformed.json()["code"] == 1001
    assert malformed.json()["msg"] == "日期范围无效"


def test_train_title_and_task_name_length():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    too_long = "资" * 129
    rejected = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": too_long,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/long.pdf",
            "publish": True,
        },
    )
    assert rejected.json()["code"] == 1001
    assert rejected.json()["msg"] == "标题不超过 128 字"

    ok_title = "资" * 128
    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": ok_title,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/long.pdf",
            "publish": True,
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    material_id = body["data"]["id"]

    renamed = client.put(
        f"/admin-api/ims/train/material/{material_id}",
        headers=auth,
        json={
            "title": "更" * 129,
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/long.pdf",
            "publish": True,
        },
    )
    assert renamed.json()["code"] == 1001
    assert renamed.json()["msg"] == "标题不超过 128 字"

    long_task = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "任" * 129,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert long_task.json()["code"] == 1001
    assert long_task.json()["msg"] == "任务名称不超过 128 字"

    short = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "任" * 128,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    short_body = short.json()
    assert short_body["code"] == 0, short_body
    edited = client.put(
        f"/admin-api/ims/train/task/{short_body['data']['id']}",
        headers=auth,
        json={
            "taskName": "改" * 129,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert edited.json()["code"] == 1001
    assert edited.json()["msg"] == "任务名称不超过 128 字"


def test_train_draft_material_cannot_offline():
    auth = headers()
    cates = client.get("/admin-api/ims/train/material/cates", headers=auth)
    cate_id = cates.json()["data"][0]["children"][0]["id"]
    created = client.post(
        "/admin-api/ims/train/material",
        headers=auth,
        json={
            "title": "TB资料草稿",
            "cateId": cate_id,
            "materialType": "DOC",
            "fileKey": "train/draft.pdf",
            "publish": False,
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["status"] == "DRAFT"
    material_id = body["data"]["id"]
    offline = client.delete(f"/admin-api/ims/train/material/{material_id}", headers=auth)
    assert offline.json()["code"] == 1001
    assert offline.json()["msg"] == "仅已发布资料可下架"
    db = SessionLocal()
    try:
        row = db.get(TrainMaterial, material_id)
        assert row is not None
        assert row.status == "DRAFT"
    finally:
        db.close()


def test_train_offline_keeps_referenced_material():
    auth = headers()
    material_id = _published_material(auth, f"引用下架 {uuid.uuid4().hex[:6]}")
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": f"引用任务 {uuid.uuid4().hex[:6]}",
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [1],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    created_body = created.json()
    assert created_body["code"] == 0, created_body
    task_id = created_body["data"]["id"]

    offline = client.delete(f"/admin-api/ims/train/material/{material_id}", headers=auth)
    assert offline.json()["code"] == 0
    assert offline.json()["data"] is None

    db = SessionLocal()
    try:
        row = db.get(TrainMaterial, material_id)
        assert row is not None
        assert row.deleted == 0
        assert row.status == "OFFLINE"
        task = db.get(TrainTask, task_id)
        assert task is not None
        assert material_id in list(task.material_ids or [])
    finally:
        db.close()


def test_train_assign_by_position_preview_and_filter():
    auth = headers()
    material_id = _published_material(auth, f"岗位指派 {uuid.uuid4().hex[:6]}")
    username = f"pos_{uuid.uuid4().hex[:8]}"
    created_user = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": username, "nickname": "岗位学员", "mobile": f"136{uuid.uuid4().int % 10**8:08d}", "password": "Admin@123"},
    )
    assert created_user.json()["code"] == 0, created_user.json()
    user_id = int(created_user.json()["data"]["id"])
    db = SessionLocal()
    try:
        db.add(
            UserMapping(
                user_id=user_id,
                dingtalk_user_id=f"dt-{username}",
                dingtalk_position="编导",
                tenant_id=0,
                deleted=0,
            )
        )
        db.commit()
    finally:
        db.close()

    preview = client.get(
        "/admin-api/ims/train/task/assign-preview",
        headers=auth,
        params={"positionCodes": "编导"},
    )
    assert preview.json()["code"] == 0, preview.json()
    assert preview.json()["data"]["count"] >= 1
    everyone = client.get(
        "/admin-api/ims/train/task/assign-preview",
        headers=auth,
        params={"positionCodes": "全员通用"},
    )
    assert everyone.json()["data"]["count"] >= preview.json()["data"]["count"]

    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": f"按岗位 {uuid.uuid4().hex[:6]}",
            "materialIds": [material_id],
            "assignScope": "BY_POSITION",
            "assignTargetPositionCodes": ["编导"],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["assignedCount"] == preview.json()["data"]["count"]
    assert body["data"]["assignScope"] == "BY_POSITION"

    missing = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": "空岗位",
            "materialIds": [material_id],
            "assignScope": "BY_POSITION",
            "assignTargetPositionCodes": ["没有这个岗位"],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    assert missing.json()["code"] == 1001
    assert missing.json()["msg"] == "岗位下无可用用户"


def test_train_quiz_ai_generate_stub_and_adopt():
    auth = headers()
    material_id = _published_material(auth, f"AI样题 {uuid.uuid4().hex[:6]}")
    empty = client.post(
        "/admin-api/ims/train/quiz/ai-generate",
        headers=auth,
        json={"materialIds": [], "questionCount": 10},
    )
    assert empty.json()["code"] == 1001
    assert empty.json()["msg"] == "请至少选择 1 份已发布资料"
    missing = client.post(
        "/admin-api/ims/train/quiz/ai-generate",
        headers=auth,
        json={"materialIds": [99999999], "questionCount": 5},
    )
    assert missing.json()["code"] == 1111
    zero = client.post(
        "/admin-api/ims/train/quiz/ai-generate",
        headers=auth,
        json={"materialIds": [material_id], "questionCount": 0},
    )
    assert zero.json()["code"] == 1114
    generated = client.post(
        "/admin-api/ims/train/quiz/ai-generate",
        headers=auth,
        json={"materialIds": [material_id], "questionCount": 5, "difficulty": "EASY"},
    )
    body = generated.json()
    assert body["code"] == 0, body
    assert len(body["data"]["questions"]) == 5
    assert body["data"]["meta"]["modelCode"] == "stub-train-quiz"
    adopted = client.post(
        "/admin-api/ims/train/quiz/ai-adopt",
        headers=auth,
        json={"draftId": body["data"]["draftId"]},
    )
    adopted_body = adopted.json()
    assert adopted_body["code"] == 0, adopted_body
    quiz = adopted_body["data"]["quiz"]
    assert len(quiz) == 5
    assert "answerIndex" in quiz[0]
    created = _quiz_task(auth, material_id, f"AI卷 {uuid.uuid4().hex[:6]}", quiz, len(quiz))
    assert created.json()["code"] == 0, created.json()


def test_train_task_list_beijing_time_finished_count_and_dept_name():
    auth = headers()
    material_id = _published_material(auth, "列与部门资料")
    username = f"dept_{uuid.uuid4().hex[:8]}"
    created_user = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": username, "nickname": "内容部学员", "mobile": f"136{uuid.uuid4().int % 10**8:08d}", "password": "Admin@123"},
    )
    user_body = created_user.json()
    assert user_body["code"] == 0, user_body
    user_id = int(user_body["data"]["id"])
    db = SessionLocal()
    try:
        db.add(UserDept(user_id=user_id, dept_id=7301, tenant_id=0))
        db.add(
            UserMapping(
                user_id=user_id,
                dingtalk_user_id=f"dt-{username}",
                dept_ids=[7301],
                tenant_id=0,
            )
        )
        db.add(
            OrgEvent(
                dingtalk_event_id=f"evt-{username}",
                event_type="hire",
                idempotency_key=f"idem-{username}",
                user_id=user_id,
                after_dept="内容部",
                payload_json=json.dumps({"deptIds": [7301], "deptNames": ["内容部"]}, ensure_ascii=False),
                sync_status="SUCCESS",
                tenant_id=0,
            )
        )
        db.commit()
    finally:
        db.close()

    name = f"列展示 {uuid.uuid4().hex[:6]}"
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": name,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [user_id],
            "deadline": "2026-12-31T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    task_id = body["data"]["id"]
    listed = client.get(
        "/admin-api/ims/train/task/list",
        headers=auth,
        params={"taskName": name, "pageNo": 1, "pageSize": 10},
    )
    row = next(item for item in listed.json()["data"]["list"] if item["id"] == task_id)
    assert row["assignScope"] == "BY_USER"
    assert row["finishedCount"] == 0
    assert row["deadline"] == "2026-12-31T18:00:00+08:00"
    created_at = datetime_from_iso(row["createdAt"])
    assert abs((created_at - utcnow().replace(tzinfo=timezone.utc)).total_seconds()) < 180

    records = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "pageNo": 1, "pageSize": 10},
    )
    rec = records.json()["data"]["list"][0]
    assert rec["deptName"] == "内容部"
    assert rec["confirmStatus"] == "NOT_CONFIRMED"
    assert rec["startedAt"]
    assert rec["finishedAt"] in (None, "")


def test_train_record_dept_name_comes_from_org_catalog_not_id():
    """本人事件没有部门名时，仍用同一部门编号在其他组织事件里的名称。"""
    auth = headers()
    material_id = _published_material(auth, "部门目录资料")
    username = f"deptcat_{uuid.uuid4().hex[:8]}"
    created_user = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": username, "nickname": "只挂编号", "mobile": f"135{uuid.uuid4().int % 10**8:08d}", "password": "Admin@123"},
    )
    user_body = created_user.json()
    assert user_body["code"] == 0, user_body
    user_id = int(user_body["data"]["id"])
    db = SessionLocal()
    try:
        db.add(UserDept(user_id=user_id, dept_id=7301, tenant_id=0))
        db.add(
            UserMapping(
                user_id=user_id,
                dingtalk_user_id=f"dt-{username}",
                dept_ids=[7301],
                tenant_id=0,
            )
        )
        db.add(
            OrgEvent(
                dingtalk_event_id=f"evt-cat-{username}",
                event_type="hire",
                idempotency_key=f"idem-cat-{username}",
                user_id=None,
                after_dept="内容部",
                payload_json=json.dumps({"deptIds": [7301], "deptNames": ["内容部"]}, ensure_ascii=False),
                sync_status="SUCCESS",
                tenant_id=0,
            )
        )
        db.commit()
    finally:
        db.close()

    name = f"部门名 {uuid.uuid4().hex[:6]}"
    created = client.post(
        "/admin-api/ims/train/task",
        headers=auth,
        json={
            "taskName": name,
            "materialIds": [material_id],
            "assignScope": "BY_USER",
            "assignTargetUserIds": [user_id],
            "deadline": "2026-10-18T18:00:00+08:00",
            "confirmType": "DURATION",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    task_id = body["data"]["id"]
    records = client.get(
        "/admin-api/ims/train/task/records",
        headers=auth,
        params={"taskId": task_id, "pageNo": 1, "pageSize": 10},
    )
    rec = records.json()["data"]["list"][0]
    assert rec["deptName"] == "内容部"
    assert "7301" not in rec["deptName"]

    db = SessionLocal()
    try:
        task = db.get(TrainTask, task_id)
        from app.train import deadline_text

        assert deadline_text(task.deadline) == "2026-10-18 18:00"
    finally:
        db.close()


def datetime_from_iso(text: str):
    from datetime import datetime

    return datetime.fromisoformat(text)
