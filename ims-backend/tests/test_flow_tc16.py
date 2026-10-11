"""TC-16 工作流：C024/C030 处理人、C027 退回转交、C025 模板、C026 看板、C031 催办。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import Role, RolePerm, User, UserDept, UserRole, UserScope, WorkMessage
from app.scope import refresh_user_scope

client = TestClient(app)


def login(username="admin", password="Admin@123") -> dict:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0, res.json()
    return {"Authorization": f"Bearer {res.json()['data']['accessToken']}"}


def create_user(headers: dict, username: str, mobile: str) -> int:
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": username, "nickname": username, "mobile": mobile, "password": "Pass@123"},
    )
    assert created.json()["code"] == 0, created.json()
    return int(created.json()["data"]["id"])


def bind(
    user_id: int,
    *,
    key: str,
    name: str,
    scope: str,
    perm: bool = True,
    flow: bool | None = None,
    depts: list[int] | None = None,
) -> None:
    db = SessionLocal()
    try:
        role = Role(role_name=name, role_key=key, data_scope=scope, status="ENABLED", source="MANUAL")
        db.add(role)
        db.flush()
        if perm:
            db.add(RolePerm(role_id=role.id, module_code="system", perm_code="system:user:query", perm_level="R"))
        # #165 先校验功能权限：流程接口需要 menu:flow:query，W 覆盖发起/处理。
        if perm if flow is None else flow:
            db.add(RolePerm(role_id=role.id, module_code="flow", perm_code="menu:flow:query", perm_level="W"))
        db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        for dept_id in depts or []:
            db.add(UserDept(user_id=user_id, dept_id=dept_id, tenant_id=0))
        db.commit()
        refresh_user_scope(db, user_id)
        db.commit()
    finally:
        db.close()


def published_leave(headers: dict) -> dict:
    listed = client.get(
        "/admin-api/ims/flow/template/list",
        headers=headers,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    return next(row for row in listed["data"]["list"] if row["templateCode"] == "FL-LEAVE")


def start_leave(headers: dict, title: str, key: str) -> dict:
    leave = published_leave(login())
    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=headers,
        json={"templateId": leave["id"], "formData": {"title": title}, "businessKey": key},
    ).json()
    assert started["code"] == 0, started
    return started["data"]


def test_c024_c030_handler_not_initiator_admin_can_see_detail():
    admin = login()
    leader_id = create_user(admin, "tc_r4_head", "13616000001")
    staff_id = create_user(admin, "tc_r6_staff", "13616000002")
    bind(leader_id, key="dept:leader", name="部门负责人", scope="ALL", depts=[88021])
    bind(staff_id, key="flow:staff", name="员工", scope="ALL", depts=[88021])
    staff = login("tc_r6_staff", "Pass@123")
    leader = login("tc_r4_head", "Pass@123")

    started = start_leave(staff, "C024 请假", "c024-leave")
    node = started["currentNodes"][0]
    assert node["nodeName"] == "部门负责人审批"
    assert node["assigneeUserId"] == leader_id
    assert node["assigneeName"] == "tc_r4_head"
    assert node["assigneeUserId"] != staff_id

    staff_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=staff, params={"pageSize": 50}).json()
    assert all(row["instanceNo"] != started["instanceNo"] for row in staff_todo["data"]["list"])

    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    task = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == started["instanceNo"])
    assert task["assigneeUserId"] == leader_id

    denied = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=staff,
        json={"action": "APPROVE", "comment": "发起人不能批"},
    ).json()
    assert denied["code"] == 1135

    admin_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=admin, params={"pageSize": 50}).json()
    assert all(row["instanceNo"] != started["instanceNo"] for row in admin_todo["data"]["list"])

    detail = client.get(f"/admin-api/ims/flow/instance/{started['instanceNo']}", headers=admin).json()
    assert detail["code"] == 0
    assert detail["data"]["currentAssigneeName"] == "tc_r4_head"
    assert detail["data"]["currentNodes"][0]["assigneeName"] == "tc_r4_head"

    listed = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=admin,
        params={"keyword": started["instanceNo"], "pageSize": 10},
    ).json()
    row = next(item for item in listed["data"]["list"] if item["instanceNo"] == started["instanceNo"])
    assert row["currentAssigneeName"] == "tc_r4_head"
    assert row["pendingTaskId"] == task["id"]

    approved = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=leader,
        json={"action": "APPROVE", "comment": "负责人通过"},
    ).json()
    assert approved["code"] == 0
    assert approved["data"]["newStatus"] == "RUNNING"
    assert approved["data"]["isInstanceFinished"] is False
    assert approved["data"]["nextNodes"][0]["nodeName"] == "人事备案"


def test_c024_dept_with_flow_perm_opens_todo_ip_group_stays_denied():
    """本部门且有 menu:flow:query 可打开待办。规格不按 IP 组收窄流程表。"""
    admin = login()
    dept_id = create_user(admin, "flow_dept_ok", "13616000003")
    bare_id = create_user(admin, "flow_norole", "13616000004")
    ip_id = create_user(admin, "flow_ip_scope", "13616000005")
    bind(dept_id, key="flow-dept-ok", name="部门流程", scope="DEPT", perm=False, flow=True, depts=[88022])
    bind(ip_id, key="flow-ip", name="IP组流程", scope="IP_GROUP", perm=False, flow=True)
    db = SessionLocal()
    try:
        db.add(UserScope(user_id=ip_id, scope_type="IP_GROUP", scope_value="8801", tenant_id=0))
        db.commit()
    finally:
        db.close()
    assert bare_id > 0

    dept = login("flow_dept_ok", "Pass@123")
    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=dept)
    assert todo.status_code == 200
    assert todo.json()["code"] == 0

    system = client.get("/admin-api/ims/system/user/page", headers=dept)
    assert system.status_code == 403
    assert system.json()["code"] == 403
    assert system.json()["msg"] == "无操作权限"

    bare = login("flow_norole", "Pass@123")
    denied = client.get("/admin-api/ims/flow/task/my-todo", headers=bare)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403
    assert denied.json()["msg"] == "无操作权限"

    ip_user = login("flow_ip_scope", "Pass@123")
    ip_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=ip_user)
    assert ip_todo.status_code == 403
    assert ip_todo.json()["code"] == 1008


def test_c027_return_requires_comment_and_transfer_once():
    admin = login()
    leader_id = create_user(admin, "tc_r4_move", "13616000011")
    staff_id = create_user(admin, "tc_r6_move", "13616000012")
    peer_id = create_user(admin, "tc_peer_move", "13616000013")
    bind(leader_id, key="dept:leader", name="部门负责人", scope="ALL", depts=[88031])
    bind(staff_id, key="flow:staff", name="员工", scope="ALL", depts=[88031])
    bind(peer_id, key="flow:peer", name="同事", scope="ALL", depts=[88031])
    staff = login("tc_r6_move", "Pass@123")
    leader = login("tc_r4_move", "Pass@123")
    peer = login("tc_peer_move", "Pass@123")

    started = start_leave(staff, "C027 退回", "c027-return")
    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    task = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == started["instanceNo"])

    empty = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=leader,
        json={"action": "REJECT", "comment": "  "},
    ).json()
    assert empty["code"] == 1001
    assert "退回意见必填" in empty["msg"]

    returned = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=leader,
        json={"action": "REJECT", "comment": "请补充附件"},
    ).json()
    assert returned["code"] == 0
    assert returned["data"]["newStatus"] == "REJECTED"
    assert returned["data"]["isInstanceFinished"] is False
    assert returned["data"]["nextNodes"][0]["assigneeUserId"] == staff_id

    detail = client.get(f"/admin-api/ims/flow/instance/{started['instanceNo']}", headers=staff).json()["data"]
    assert detail["instanceStatus"] == "RUNNING"
    staff_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=staff, params={"pageSize": 50}).json()
    assert any(row["instanceNo"] == started["instanceNo"] for row in staff_todo["data"]["list"])
    leader_left = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    assert all(row["instanceNo"] != started["instanceNo"] for row in leader_left["data"]["list"])

    db = SessionLocal()
    try:
        note = db.query(WorkMessage).filter(WorkMessage.user_id == staff_id, WorkMessage.title == "流程已退回").one()
        assert "请补充附件" in note.content
    finally:
        db.close()

    moved = start_leave(staff, "C027 转交", "c027-transfer")
    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    task = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == moved["instanceNo"])
    missing = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/transfer",
        headers=leader,
        json={"transferReason": "人不对"},
    ).json()
    assert missing["code"] == 1138
    same = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/transfer",
        headers=leader,
        json={"toUserId": leader_id, "transferReason": "给自己"},
    ).json()
    assert same["code"] == 1138
    no_reason = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/transfer",
        headers=leader,
        json={"toUserId": peer_id, "transferReason": "  "},
    ).json()
    assert no_reason["code"] == 1001

    moved_ok = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/transfer",
        headers=leader,
        json={"toUserId": peer_id, "transferReason": "请同事代审"},
    ).json()
    assert moved_ok["code"] == 0
    peer_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=peer, params={"pageSize": 50}).json()
    peer_task = next(row for row in peer_todo["data"]["list"] if row["instanceNo"] == moved["instanceNo"])
    assert peer_task["assigneeUserId"] == peer_id
    assert peer_task["allowTransfer"] is False
    again = client.put(
        f"/admin-api/ims/flow/task/{peer_task['id']}/transfer",
        headers=peer,
        json={"toUserId": leader_id, "transferReason": "再转一次"},
    ).json()
    assert again["code"] == 1138
    assert "一次" in again["msg"]


def test_c025_template_publish_version_and_disable():
    admin = login()
    created = client.post(
        "/admin-api/ims/flow/template",
        headers=admin,
        json={
            "templateName": "出差审批",
            "businessDomain": "ADMIN",
            "slaHours": 24,
            "nodeChain": "发起申请、部门审批、归档确认",
        },
    ).json()
    assert created["code"] == 0, created
    tpl_id = created["data"]["id"]
    assert created["data"]["status"] == "DRAFT"
    assert created["data"]["templateNo"].startswith("FT")

    missing = client.post(
        "/admin-api/ims/flow/template",
        headers=admin,
        json={"templateName": "缺链", "businessDomain": "COMMON", "slaHours": 24},
    ).json()
    assert missing["code"] == 1001

    cyclic = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "发起申请",
                    "nodeType": "TASK",
                    "assigneeRule": {"assignType": "USER", "targetIds": []},
                },
                {
                    "nodeOrder": 2,
                    "nodeName": "部门审批",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]},
                    "conditionExpr": [{"expression": "back", "nextNodeOrder": 1}],
                },
                {
                    "nodeOrder": 3,
                    "nodeName": "归档确认",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "NOPE"},
                },
            ]
        },
    ).json()
    assert cyclic["code"] == 1131

    bad_rule = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "发起申请",
                    "nodeType": "TASK",
                    "assigneeRule": {"assignType": "USER", "targetIds": []},
                },
                {
                    "nodeOrder": 2,
                    "nodeName": "归档确认",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "NOPE"},
                },
            ]
        },
    ).json()
    assert bad_rule["code"] == 1132

    published = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"changeDesc": "首发"},
    ).json()
    assert published["code"] == 0, published
    assert published["data"]["status"] == "PUBLISHED"
    assert published["data"]["version"] == 1

    edited = client.put(
        f"/admin-api/ims/flow/template/{tpl_id}",
        headers=admin,
        json={"templateName": "出差审批", "nodeChain": "发起申请、加签、归档确认"},
    ).json()
    assert edited["code"] == 1133

    moved = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"nodeChain": "归档确认、部门审批、发起申请", "changeDesc": "对调首尾"},
    ).json()
    assert moved["code"] == 1001
    assert "首" in moved["msg"]

    bumped = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"nodeChain": "发起申请、加签、归档确认", "changeDesc": "插入加签"},
    ).json()
    assert bumped["code"] == 0, bumped
    assert bumped["data"]["version"] == 2

    versions = client.get("/admin-api/ims/flow/version/list", headers=admin, params={"templateId": tpl_id}).json()
    assert versions["code"] == 0
    assert {row["version"] for row in versions["data"]} >= {1, 2}

    diff = client.get(
        "/admin-api/ims/flow/version/diff",
        headers=admin,
        params={"templateId": tpl_id, "fromVersion": 1, "toVersion": 2},
    ).json()
    assert diff["code"] == 0
    assert diff["data"]["nodeChanges"]

    rolled = client.post(
        f"/admin-api/ims/flow/version/{tpl_id}/rollback",
        headers=admin,
        json={"targetVersion": 1, "changeDesc": "回到首发"},
    ).json()
    assert rolled["code"] == 0
    assert rolled["data"]["newVersion"] == 3
    assert rolled["data"]["targetVersion"] == 1

    illegal = client.post(
        f"/admin-api/ims/flow/version/{tpl_id}/rollback",
        headers=admin,
        json={"targetVersion": 99, "changeDesc": "不存在"},
    ).json()
    assert illegal["code"] == 1134

    disabled = client.put(
        f"/admin-api/ims/flow/template/{tpl_id}",
        headers=admin,
        json={"status": "DISABLED"},
    ).json()
    assert disabled["code"] == 0
    assert disabled["data"]["status"] == "DISABLED"
    blocked = client.post(
        "/admin-api/ims/flow/instance",
        headers=admin,
        json={"templateId": tpl_id, "formData": {"title": "停用不可发起"}},
    ).json()
    assert blocked["code"] == 1134

    enabled = client.put(
        f"/admin-api/ims/flow/template/{tpl_id}",
        headers=admin,
        json={"status": "PUBLISHED"},
    ).json()
    assert enabled["code"] == 0
    assert enabled["data"]["status"] == "PUBLISHED"


def test_c025_draft_version_and_publish_guards():
    """草稿每次保存升版本；重名链 1131、无审批人 1132，发布前拦住。"""
    admin = login()
    created = client.post(
        "/admin-api/ims/flow/template",
        headers=admin,
        json={
            "templateName": "C025 草稿升版",
            "businessDomain": "ADMIN",
            "slaHours": 24,
            "nodeChain": "发起申请、部门审批、归档确认",
        },
    ).json()
    assert created["code"] == 0, created
    tpl_id = created["data"]["id"]
    assert created["data"]["version"] == 1

    first = client.put(
        f"/admin-api/ims/flow/template/{tpl_id}",
        headers=admin,
        json={"templateName": "C025 草稿升版", "nodeChain": "发起申请、部门审批、归档确认"},
    ).json()
    assert first["code"] == 0, first
    assert first["data"]["version"] == 2
    second = client.put(
        f"/admin-api/ims/flow/template/{tpl_id}",
        headers=admin,
        json={"templateName": "C025 草稿升版", "nodeChain": "发起申请、部门审批、归档确认"},
    ).json()
    assert second["code"] == 0, second
    assert second["data"]["version"] == 3

    published = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"changeDesc": "首发"},
    ).json()
    assert published["code"] == 0, published
    assert published["data"]["version"] == 3

    duplicate = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"nodeChain": "发起申请、部门审批、部门审批、归档确认", "changeDesc": "重名"},
    ).json()
    assert duplicate["code"] == 1131
    assert "重复" in duplicate["msg"]

    missing_approver = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"nodeChain": "发起申请、TC_C无审批人节点、归档确认", "changeDesc": "无审批人"},
    ).json()
    assert missing_approver["code"] == 1132

    empty_rule = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "发起申请",
                    "nodeType": "TASK",
                    "assigneeRule": {"assignType": "USER", "targetIds": []},
                },
                {
                    "nodeOrder": 2,
                    "nodeName": "TC_C无审批人节点",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": ""},
                },
                {
                    "nodeOrder": 3,
                    "nodeName": "归档确认",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]},
                },
            ]
        },
    ).json()
    assert empty_rule["code"] == 1132

    stayed = client.get(
        "/admin-api/ims/flow/template/list",
        headers=admin,
        params={"templateName": "C025 草稿升版", "pageNo": 1, "pageSize": 10},
    ).json()
    row = next(item for item in stayed["data"]["list"] if item["id"] == tpl_id)
    assert row["version"] == 3
    assert row["slaHours"] == 24
    assert "startCount" in row

    bumped = client.post(
        f"/admin-api/ims/flow/template/{tpl_id}/publish",
        headers=admin,
        json={"nodeChain": "发起申请、财务复核、归档确认", "changeDesc": "换中节点"},
    ).json()
    assert bumped["code"] == 0, bumped
    assert bumped["data"]["version"] == 4
    diff = client.get(
        "/admin-api/ims/flow/version/diff",
        headers=admin,
        params={"templateId": tpl_id, "fromVersion": 3, "toVersion": 4},
    ).json()
    assert diff["code"] == 0, diff
    changes = diff["data"]["nodeChanges"]
    assert changes
    assert all(item.get("changeType") and item.get("nodeName") for item in changes)
    modified = next(item for item in changes if item["changeType"] == "MODIFIED")
    assert modified["detail"]["nodeName"]["oldValue"] == "部门审批"
    assert modified["detail"]["nodeName"]["newValue"] == "财务复核"


def test_c026_kanban_advance_then_finish():
    admin = login()
    leader_id = create_user(admin, "c026_r4", "13616000031")
    staff_id = create_user(admin, "c026_r6", "13616000032")
    bind(leader_id, key="dept:leader", name="部门负责人", scope="ALL", depts=[88051])
    bind(staff_id, key="flow:staff", name="员工", scope="ALL", depts=[88051])
    staff = login("c026_r6", "Pass@123")
    leader = login("c026_r4", "Pass@123")
    created = client.post(
        "/admin-api/ims/flow/template",
        headers=admin,
        json={
            "templateName": "三节点看板",
            "businessDomain": "COMMON",
            "slaHours": 12,
            "nodeChain": "发起、初审、终审",
        },
    ).json()
    assert created["code"] == 0, created
    tpl_id = created["data"]["id"]
    published = client.post(f"/admin-api/ims/flow/template/{tpl_id}/publish", headers=admin, json={}).json()
    assert published["code"] == 0, published

    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=staff,
        json={"templateId": tpl_id, "formData": {"title": "看板单"}, "businessKey": "c026-board"},
    ).json()
    assert started["code"] == 0, started
    instance_no = started["data"]["instanceNo"]
    assert started["data"]["currentNodes"][0]["nodeName"] == "初审"
    assert started["data"]["currentNodes"][0]["assigneeUserId"] == leader_id

    board = client.get("/admin-api/ims/flow/instance/board", headers=admin).json()
    assert board["code"] == 0
    column = next(col for col in board["data"]["columns"] if col["nodeName"] == "初审")
    card = next(item for item in column["cards"] if item["instanceNo"] == instance_no)
    assert card["canAdvance"] is True
    assert card["currentAssigneeName"]

    advanced = client.put(
        f"/admin-api/ims/flow/task/{card['pendingTaskId']}/handle",
        headers=leader,
        json={"action": "APPROVE", "advance": True, "comment": "到终审"},
    ).json()
    assert advanced["code"] == 0, advanced
    assert advanced["data"]["isInstanceFinished"] is False
    assert advanced["data"]["newStatus"] == "RUNNING"
    assert advanced["data"]["nextNodes"][0]["nodeName"] == "终审"

    board2 = client.get("/admin-api/ims/flow/instance/board", headers=admin).json()
    column2 = next(col for col in board2["data"]["columns"] if col["nodeName"] == "终审")
    card2 = next(item for item in column2["cards"] if item["instanceNo"] == instance_no)
    assert card2["canAdvance"] is False

    finished = client.put(
        f"/admin-api/ims/flow/task/{card2['pendingTaskId']}/handle",
        headers=leader,
        json={"action": "APPROVE", "comment": "归档"},
    ).json()
    assert finished["data"]["newStatus"] == "APPROVED"
    assert finished["data"]["isInstanceFinished"] is True

    listed = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=admin,
        params={"keyword": instance_no, "pageSize": 10},
    ).json()
    row = next(item for item in listed["data"]["list"] if item["instanceNo"] == instance_no)
    assert row["instanceStatus"] == "APPROVED"
    assert row["instanceStatusLabel"] == "已完成"


def test_c031_instance_urge_without_waiting_for_timeout():
    admin = login()
    leader_id = create_user(admin, "c031_r4", "13616000041")
    staff_id = create_user(admin, "c031_r6", "13616000042")
    bind(leader_id, key="dept:leader", name="部门负责人", scope="ALL", depts=[88061])
    bind(staff_id, key="flow:staff", name="员工", scope="ALL", depts=[88061])
    staff = login("c031_r6", "Pass@123")
    started = start_leave(staff, "C031 催办", "c031-urge")
    task_id = started["currentNodes"][0]["assigneeUserId"]
    listed = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=admin,
        params={"keyword": started["instanceNo"], "pageSize": 5},
    ).json()
    row = next(item for item in listed["data"]["list"] if item["instanceNo"] == started["instanceNo"])
    assert row["pendingTaskId"]
    early = client.put(
        f"/admin-api/ims/flow/timeout/{row['pendingTaskId']}/urge",
        headers=admin,
        json={"urgeMessage": "普通督办"},
    ).json()
    assert early["code"] == 1001
    assert "未超时" in early["msg"]

    urged = client.put(
        f"/admin-api/ims/flow/timeout/{row['pendingTaskId']}/urge",
        headers=admin,
        json={"urgeMessage": "请尽快审批", "fromInstance": True},
    ).json()
    assert urged["code"] == 0, urged
    assert urged["data"]["remindCount"] == 1
    assert urged["data"]["notifyChannel"] == "DINGTALK_STUB"

    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").one()
        assert task_id == admin_user.id or task_id
        note = (
            db.query(WorkMessage)
            .filter(WorkMessage.title == "流程催办", WorkMessage.ref_id == row["id"])
            .one()
        )
        assert "请尽快审批" in note.content
    finally:
        db.close()


def test_c077_leave_walks_bound_version_until_last_node():
    """请假审批 4 节点：部门负责人通过后进入人事备案，抄送办完才归档。"""
    admin = login()
    leader_id = create_user(admin, "c077_r4", "13616000021")
    staff_id = create_user(admin, "c077_r6", "13616000022")
    bind(leader_id, key="dept:leader", name="部门负责人", scope="ALL", depts=[88041])
    bind(staff_id, key="flow:staff", name="员工", scope="ALL", depts=[88041])
    staff = login("c077_r6", "Pass@123")
    leader = login("c077_r4", "Pass@123")

    leave = published_leave(admin)
    preview = client.get(f"/admin-api/ims/flow/template/{leave['id']}/preview", headers=admin).json()
    assert preview["code"] == 0
    assert len(preview["data"]["nodes"]) == 4
    assert [node["nodeName"] for node in preview["data"]["nodes"]] == [
        "发起申请",
        "部门负责人审批",
        "人事备案",
        "归档",
    ]

    started = start_leave(staff, "C077 请假", "c077-leave")
    assert started["templateVersion"] == leave["version"]
    assert started["currentNodes"][0]["nodeName"] == "部门负责人审批"
    assert started["currentNodes"][0]["assigneeUserId"] == leader_id
    assert started["instanceStatus"] == "RUNNING"

    detail = client.get(f"/admin-api/ims/flow/instance/{started['instanceNo']}", headers=admin).json()
    assert detail["data"]["templateVersion"] == leave["version"]

    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    task = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == started["instanceNo"])
    first = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=leader,
        json={"action": "APPROVE", "comment": "部门通过"},
    ).json()
    assert first["code"] == 0, first
    assert first["data"]["isInstanceFinished"] is False
    assert first["data"]["newStatus"] == "RUNNING"
    assert first["data"]["nextNodes"][0]["nodeName"] == "人事备案"
    assert first["data"]["nextNodes"][0]["assigneeUserId"] == leader_id

    running = client.get(f"/admin-api/ims/flow/instance/{started['instanceNo']}", headers=staff).json()["data"]
    assert running["instanceStatus"] == "RUNNING"
    assert running["currentNodes"][0]["nodeName"] == "人事备案"

    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    cc = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == started["instanceNo"])
    assert cc["nodeName"] == "人事备案"
    done = client.put(
        f"/admin-api/ims/flow/task/{cc['id']}/handle",
        headers=leader,
        json={"action": "APPROVE", "comment": "备案"},
    ).json()
    assert done["code"] == 0, done
    assert done["data"]["newStatus"] == "APPROVED"
    assert done["data"]["isInstanceFinished"] is True

    finished = client.get(f"/admin-api/ims/flow/instance/{started['instanceNo']}", headers=admin).json()["data"]
    assert finished["instanceStatus"] == "APPROVED"
    assert finished["instanceStatusLabel"] == "已完成"
    assert finished["templateVersion"] == leave["version"]


def test_c078_admin_cannot_approve_own_leave():
    """解析到发起人时跳过审批/抄送。PRD 未规定改派对象，跳到下一节点并留痕。"""
    admin = login()
    started = start_leave(admin, "C078 管理员请假", "c078-admin")
    assert started["instanceStatus"] == "RUNNING"
    node = started["currentNodes"][0]
    assert node["nodeName"] == "部门负责人审批"
    assert node["assigneeName"] != "admin"
    assert node["assigneeUserId"] != started["initiatorUserId"]

    denied = client.put(
        "/admin-api/ims/flow/task/0/handle",
        headers=admin,
        json={"action": "APPROVE", "comment": "自己批"},
    ).json()
    assert denied["code"] == 1001

    leader = login("tc_r4", "Admin@123")
    leader_todo = client.get("/admin-api/ims/flow/task/my-todo", headers=leader, params={"pageSize": 50}).json()
    task = next(row for row in leader_todo["data"]["list"] if row["instanceNo"] == started["instanceNo"])
    blocked = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=admin,
        json={"action": "APPROVE", "comment": "管理员不能批自己的单"},
    ).json()
    assert blocked["code"] == 1135

    admin_id = started["initiatorUserId"]
    created = client.post(
        "/admin-api/ims/flow/template",
        headers=admin,
        json={
            "templateName": "指定本人审批",
            "businessDomain": "ADMIN",
            "slaHours": 24,
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "发起申请",
                    "nodeType": "TASK",
                    "assigneeRule": {"assignType": "USER", "targetIds": []},
                },
                {
                    "nodeOrder": 2,
                    "nodeName": "本人审批",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "USER", "targetIds": [admin_id]},
                },
                {
                    "nodeOrder": 3,
                    "nodeName": "部门负责人审批",
                    "nodeType": "APPROVE",
                    "assigneeRule": {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]},
                },
            ],
        },
    ).json()
    assert created["code"] == 0, created
    published = client.post(
        f"/admin-api/ims/flow/template/{created['data']['id']}/publish",
        headers=admin,
        json={"changeDesc": "指定本人"},
    ).json()
    assert published["code"] == 0, published
    own = client.post(
        "/admin-api/ims/flow/instance",
        headers=admin,
        json={
            "templateId": created["data"]["id"],
            "formData": {"title": "C078 指定本人"},
            "businessKey": "c078-self",
        },
    ).json()
    assert own["code"] == 0, own
    assert own["data"]["instanceStatus"] == "RUNNING"
    assert "本人审批" in own["data"]["skippedNodes"]
    assert own["data"]["currentNodes"][0]["nodeName"] == "部门负责人审批"
    assert own["data"]["currentNodes"][0]["assigneeUserId"] != admin_id
    detail = client.get(f"/admin-api/ims/flow/instance/{own['data']['instanceNo']}", headers=admin).json()["data"]
    assert any("已跳过" in (item.get("comment") or "") for item in detail["traceLog"])
