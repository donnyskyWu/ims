import os
import uuid

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


def test_flow_template_and_instance_list():
    auth = headers()
    tpl = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "businessDomain": "BUSINESS"},
    )
    body = tpl.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 2
    assert any(row["templateCode"] == "FL-CONTENT" for row in body["data"]["list"])

    inst = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "instanceStatus": "RUNNING"},
    )
    ib = inst.json()
    assert ib["code"] == 0
    assert ib["data"]["total"] >= 2
    assert all(row["instanceStatus"] == "RUNNING" for row in ib["data"]["list"])


def test_flow_instance_start_and_idempotent():
    auth = headers()
    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    assert published["code"] == 0
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")

    drafts = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "DRAFT"},
    ).json()
    assert drafts["code"] == 0
    draft = next(r for r in drafts["data"]["list"] if r["templateCode"] == "FL-LIVE")

    bad = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={"templateId": draft["id"], "formData": {"title": "开播申请"}},
    )
    assert bad.json()["code"] == 1134

    payload = {
        "templateId": leave["id"],
        "formData": {"title": "pytest · 年假 1 天", "days": 1},
        "businessKey": "pytest-flow-leave-001",
    }
    start = client.post("/admin-api/ims/flow/instance", headers=auth, json=payload)
    sb = start.json()
    assert sb["code"] == 0
    assert sb["data"]["instanceStatus"] == "RUNNING"
    assert sb["data"]["currentNodes"][0]["nodeName"] == "部门负责人审批"
    first_no = sb["data"]["instanceNo"]

    again = client.post("/admin-api/ims/flow/instance", headers=auth, json=payload)
    ab = again.json()
    assert ab["code"] == 0
    assert ab["data"]["instanceNo"] == first_no


def test_flow_task_handle_approve_and_reject():
    auth = headers()
    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 5})
    tb = todo.json()
    assert tb["code"] == 0
    assert tb["data"]["total"] >= 1
    task_id = tb["data"]["list"][0]["id"]
    instance_no = tb["data"]["list"][0]["instanceNo"]

    approved = client.put(
        f"/admin-api/ims/flow/task/{task_id}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "pytest approve"},
    )
    ab = approved.json()
    assert ab["code"] == 0
    assert ab["data"]["instanceNo"] == instance_no
    assert ab["data"]["newStatus"] == "APPROVED"
    assert ab["data"]["isInstanceFinished"] is True

    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")
    start = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 驳回用例"},
            "businessKey": "pytest-flow-reject-001",
        },
    )
    assert start.json()["code"] == 0

    todo2 = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 20})
    reject_task = next(
        r for r in todo2.json()["data"]["list"] if r["instanceNo"] == start.json()["data"]["instanceNo"]
    )
    rejected = client.put(
        f"/admin-api/ims/flow/task/{reject_task['id']}/handle",
        headers=auth,
        json={"action": "REJECT", "comment": "pytest reject"},
    )
    rb = rejected.json()
    assert rb["code"] == 0
    assert rb["data"]["newStatus"] == "REJECTED"


def test_flow_timeout_list_and_urge():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    )
    lb = listed.json()
    assert lb["code"] == 0
    assert lb["data"]["total"] >= 1
    row = lb["data"]["list"][0]
    assert row["timeoutDurationMinutes"] >= 0
    assert "remindCount" in row
    before = row["remindCount"]

    urged = client.put(
        f"/admin-api/ims/flow/timeout/{row['id']}/urge",
        headers=auth,
        json={"urgeMessage": "pytest 督办"},
    )
    urged_body = urged.json()
    assert urged_body["code"] == 0
    assert urged_body["data"]["notifyChannel"] == "DINGTALK_STUB"
    assert urged_body["data"]["delivery"] == "STUB_OK"
    assert urged_body["data"]["queued"] is False
    assert urged_body["data"]["remindCount"] == before + 1

    again = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    refreshed = next(r for r in again["data"]["list"] if r["id"] == row["id"])
    assert refreshed["remindCount"] == before + 1


def test_flow_timeout_urge_edges():
    """未超时、已处理、超长说明不递增 remindCount；空白说明仍允许（契约可选）。"""
    auth = headers()
    missing = client.put(
        "/admin-api/ims/flow/timeout/99999999/urge",
        headers=auth,
        json={"urgeMessage": "不存在"},
    )
    assert missing.json()["code"] == 1001
    assert "不存在" in missing.json()["msg"]

    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")
    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 未超时不可督办"},
            "businessKey": "pytest-flow-urge-early",
        },
    )
    assert started.json()["code"] == 0
    instance_no = started.json()["data"]["instanceNo"]
    todos = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    early_task = next(r for r in todos["data"]["list"] if r["instanceNo"] == instance_no)
    early = client.put(
        f"/admin-api/ims/flow/timeout/{early_task['id']}/urge",
        headers=auth,
        json={"urgeMessage": "太早"},
    )
    assert early.json()["code"] == 1001
    assert "未超时" in early.json()["msg"]

    handled = client.put(
        f"/admin-api/ims/flow/task/{early_task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "pytest"},
    )
    assert handled.json()["code"] == 0
    late = client.put(
        f"/admin-api/ims/flow/timeout/{early_task['id']}/urge",
        headers=auth,
        json={"urgeMessage": "已处理"},
    )
    assert late.json()["code"] == 1001
    assert "已处理" in late.json()["msg"]

    listed = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    row = listed["data"]["list"][0]
    before = row["remindCount"]
    over = client.put(
        f"/admin-api/ims/flow/timeout/{row['id']}/urge",
        headers=auth,
        json={"urgeMessage": "督" * 257},
    )
    assert over.json()["code"] == 1001
    assert "256" in over.json()["msg"]
    mid = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    refreshed = next(r for r in mid["data"]["list"] if r["id"] == row["id"])
    assert refreshed["remindCount"] == before

    blank = client.put(
        f"/admin-api/ims/flow/timeout/{row['id']}/urge",
        headers=auth,
        json={"urgeMessage": "   "},
    )
    assert blank.json()["code"] == 0
    after = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    refreshed = next(r for r in after["data"]["list"] if r["id"] == row["id"])
    assert refreshed["remindCount"] == before + 1


def test_flow_timeout_rate_br115_stub():
    auth = headers()
    rated = client.get("/admin-api/ims/flow/timeout/rate", headers=auth)
    body = rated.json()
    assert body["code"] == 0
    data = body["data"]
    assert "monthlyTimeoutRate" in data
    assert data["targetRate"] == 0.1
    assert isinstance(data["byDomain"], list)
    assert len(data["trend"]) == 6
    assert data["totalExecuted"] >= 1
    assert data["timeoutCount"] >= 1
    assert 0 <= data["monthlyTimeoutRate"] <= 1
    assert data["urgeCount"] >= 0


def test_flow_timeout_list_domain_assignee_and_empty_month():
    """#216：超时清单按业务域、处理人姓名筛选；空白姓名不筛选；空统计月无执行节点。"""
    auth = headers()
    listed = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    assert listed["code"] == 0
    assert listed["data"]["total"] >= 1
    sample = listed["data"]["list"][0]
    name = (sample.get("assigneeName") or "").strip()
    assert name

    blank = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "assigneeName": "   "},
    ).json()
    assert blank["code"] == 0
    assert blank["data"]["total"] == listed["data"]["total"]

    missed = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "assigneeName": "no-such-assignee-216"},
    ).json()
    assert missed["code"] == 0
    assert missed["data"]["total"] == 0

    hit = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "assigneeName": f"  {name}  "},
    ).json()
    assert hit["code"] == 0
    assert any(row["id"] == sample["id"] for row in hit["data"]["list"])

    templates = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    tpl = next(row for row in templates["data"]["list"] if row["templateName"] == sample["templateName"])
    domain = tpl["businessDomain"]
    same_domain = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "businessDomain": domain, "assigneeName": name},
    ).json()
    assert same_domain["code"] == 0
    assert any(row["id"] == sample["id"] for row in same_domain["data"]["list"])

    common = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "businessDomain": "COMMON", "assigneeName": name},
    ).json()
    assert common["code"] == 0
    assert common["data"]["total"] == 0
    assert all(row["id"] != sample["id"] for row in common["data"]["list"])

    empty_month = client.get(
        "/admin-api/ims/flow/timeout/rate",
        headers=auth,
        params={"statMonth": "2000-01"},
    ).json()
    assert empty_month["code"] == 0
    assert empty_month["data"]["statMonth"] == "2000-01"
    assert empty_month["data"]["totalExecuted"] == 0
    assert empty_month["data"]["timeoutCount"] == 0
    assert empty_month["data"]["monthlyTimeoutRate"] == 0

    empty_dist = client.get(
        "/admin-api/ims/flow/timeout/distribution",
        headers=auth,
        params={"statMonth": "2000-01"},
    ).json()
    assert empty_dist["code"] == 0
    assert empty_dist["data"]["timeoutTotal"] == 0
    assert sum(bucket["count"] for bucket in empty_dist["data"]["durationBuckets"]) == 0


def test_flow_timeout_distribution_stub():
    auth = headers()
    dist = client.get("/admin-api/ims/flow/timeout/distribution", headers=auth)
    body = dist.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["slaHours"] == 24
    assert data["groupBy"] == "duration"
    assert len(data["durationBuckets"]) == 3
    assert sum(b["count"] for b in data["durationBuckets"]) == data["timeoutTotal"]
    assert data["timeoutTotal"] >= 1
    assert isinstance(data["byDomain"], list)
    assert isinstance(data["byTemplate"], list)

    by_dom = client.get(
        "/admin-api/ims/flow/timeout/distribution",
        headers=auth,
        params={"groupBy": "domain"},
    ).json()
    assert by_dom["code"] == 0
    assert by_dom["data"]["groupBy"] == "domain"


def test_flow_sla_tone_thresholds():
    from datetime import timedelta

    from app.core import utcnow
    from app.flow import sla_view
    from app.models import FlowTask

    now = utcnow()
    fresh = sla_view(FlowTask(started_at=now - timedelta(hours=1)), now=now)
    assert fresh["slaTone"] == "normal"
    assert fresh["isTimeout"] is False
    warn = sla_view(FlowTask(started_at=now - timedelta(hours=20)), now=now)
    assert warn["slaTone"] == "warn"
    assert warn["isTimeout"] is False
    late = sla_view(FlowTask(started_at=now - timedelta(hours=26)), now=now)
    assert late["slaTone"] == "timeout"
    assert late["isTimeout"] is True
    assert late["slaDeadline"]


def test_flow_todo_sla_and_empty_domain():
    auth = headers()
    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 20})
    body = todo.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    tones = {row["slaTone"] for row in body["data"]["list"]}
    assert tones <= {"normal", "warn", "timeout"}
    assert any(row["isTimeout"] for row in body["data"]["list"])
    assert any(row["slaTone"] == "warn" for row in body["data"]["list"])
    assert all(row["slaDeadline"] for row in body["data"]["list"])

    empty = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "businessDomain": "COMMON"},
    ).json()
    assert empty["code"] == 0
    assert empty["data"]["total"] == 0
    assert empty["data"]["list"] == []


def test_flow_template_preview_draft_and_published():
    auth = headers()
    drafts = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "DRAFT"},
    ).json()
    draft = next(r for r in drafts["data"]["list"] if r["templateCode"] == "FL-LIVE")
    preview = client.get(f"/admin-api/ims/flow/template/{draft['id']}/preview", headers=auth).json()
    assert preview["code"] == 0
    data = preview["data"]
    assert data["canStart"] is False
    assert data["status"] == "DRAFT"
    assert data["graphType"] == "SERIAL"
    assert any(n["nodeName"] == "直属领导审批" for n in data["nodes"])
    assert len(data["edges"]) == len(data["nodes"]) - 1

    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")
    leave_preview = client.get(f"/admin-api/ims/flow/template/{leave['id']}/preview", headers=auth).json()
    assert leave_preview["code"] == 0
    assert leave_preview["data"]["canStart"] is True
    assert len(leave_preview["data"]["nodes"]) == 4

    missing = client.get("/admin-api/ims/flow/template/999999/preview", headers=auth).json()
    assert missing["code"] == 1001


def test_flow_reject_edges_and_repeat_handle():
    auth = headers()
    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")
    start = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 驳回边界"},
            "businessKey": "pytest-flow-reject-edge-001",
        },
    ).json()
    assert start["code"] == 0
    instance_no = start["data"]["instanceNo"]
    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=auth, params={"pageNo": 1, "pageSize": 50}).json()
    task = next(r for r in todo["data"]["list"] if r["instanceNo"] == instance_no)
    assert task["slaTone"] == "normal"

    bad_node = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "REJECT", "comment": "退回", "rejectToNodeOrder": 0},
    ).json()
    assert bad_node["code"] == 1001
    assert "退回目标节点" in bad_node["msg"]

    rejected = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "REJECT", "comment": "   "},
    ).json()
    assert rejected["code"] == 0
    assert rejected["data"]["newStatus"] == "REJECTED"
    assert rejected["data"]["rejectToNodeOrder"] == 1
    assert rejected["data"]["commentHint"] == "退回建议填写意见"

    again = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "再次处理"},
    ).json()
    assert again["code"] == 1001
    assert "已处理" in again["msg"]


def test_flow_urge_dingtalk_timeout_queues():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/flow/timeout/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    assert listed["code"] == 0
    assert listed["data"]["total"] >= 1
    row = listed["data"]["list"][0]
    before = row["remindCount"]
    urged = client.put(
        f"/admin-api/ims/flow/timeout/{row['id']}/urge",
        headers=auth,
        json={"urgeMessage": "__DINGTALK_TIMEOUT__"},
    ).json()
    assert urged["code"] == 5003
    assert urged["msg"] == "钉钉推送失败已入补发队列"
    assert urged["data"]["queued"] is True
    assert urged["data"]["delivery"] == "QUEUED"
    assert urged["data"]["notifyChannel"] == "DINGTALK_STUB"
    assert urged["data"]["remindCount"] == before + 1


def test_flow_detail_revoke_and_timeout_filter():
    """#203 实例详情边界、撤销 1139/1140、已超时筛选。不改审批通过/驳回主路径。"""
    from app.acct_seed import _ensure_cloned_user
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        _ensure_cloned_user(
            db,
            username="e2e_flow_peer",
            nickname="流程同事",
            mobile="13900000203",
            role_key="flow:peer",
            role_name="流程同事",
        )
        db.commit()
    finally:
        db.close()

    auth = headers()
    peer = headers_for("e2e_flow_peer")

    seeded = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "keyword": "赛事集锦"},
    ).json()
    assert seeded["code"] == 0
    assert seeded["data"]["total"] >= 1
    approved = seeded["data"]["list"][0]
    detail = client.get(f"/admin-api/ims/flow/instance/{approved['instanceNo']}", headers=auth).json()
    assert detail["code"] == 0
    body = detail["data"]
    assert body["formEmpty"] is True
    assert body["ccRecords"] == []
    assert body["canRevoke"] is False
    assert body["edgeCopy"] == "实例已结束不可撤销。"
    assert "traceLog" in body

    missing = client.get("/admin-api/ims/flow/instance/FI-NOT-A-REAL-NO", headers=auth).json()
    assert missing["code"] == 1001

    timed = client.get(
        "/admin-api/ims/flow/instance/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "instanceStatus": "TIMEOUT"},
    ).json()
    assert timed["code"] == 0
    assert all(row["instanceStatus"] == "TIMEOUT" for row in timed["data"]["list"])

    published = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PUBLISHED"},
    ).json()
    leave = next(r for r in published["data"]["list"] if r["templateCode"] == "FL-LEAVE")

    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 撤销边界"},
            "businessKey": f"pytest-flow-revoke-203-{uuid.uuid4().hex[:10]}",
        },
    ).json()
    assert started["code"] == 0
    instance_no = started["data"]["instanceNo"]

    denied = client.put(f"/admin-api/ims/flow/instance/{instance_no}/revoke", headers=peer).json()
    assert denied["code"] == 1139

    peer_view = client.get(f"/admin-api/ims/flow/instance/{instance_no}", headers=peer).json()
    assert peer_view["code"] == 0
    assert peer_view["data"]["canRevoke"] is False
    assert "仅发起人或管理员可撤销" in peer_view["data"]["edgeCopy"]

    running = client.get(f"/admin-api/ims/flow/instance/{instance_no}", headers=auth).json()
    assert running["data"]["canRevoke"] is True
    assert "撤销后已完成节点留痕" in running["data"]["edgeCopy"]
    assert running["data"]["formEmpty"] is False

    revoked = client.put(f"/admin-api/ims/flow/instance/{instance_no}/revoke", headers=auth).json()
    assert revoked["code"] == 0
    assert revoked["data"] is None

    again = client.put(f"/admin-api/ims/flow/instance/{instance_no}/revoke", headers=auth).json()
    assert again["code"] == 1140

    after = client.get(f"/admin-api/ims/flow/instance/{instance_no}", headers=auth).json()["data"]
    assert after["instanceStatus"] == "CANCELLED"
    assert after["canRevoke"] is False
    assert after["edgeCopy"] == "已撤销，已完成节点留痕，不可再次撤销。"
    assert any(item["action"] == "CANCELLED" for item in after["traceLog"])
    assert any("未办结" in (item.get("comment") or "") for item in after["traceLog"])

    todos = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    assert all(row["instanceNo"] != instance_no for row in todos["data"]["list"])

    peer_started = client.post(
        "/admin-api/ims/flow/instance",
        headers=peer,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 管理员代撤"},
            "businessKey": f"pytest-flow-revoke-r1-203-{uuid.uuid4().hex[:10]}",
        },
    ).json()
    assert peer_started["code"] == 0
    peer_no = peer_started["data"]["instanceNo"]
    admin_revoke = client.put(f"/admin-api/ims/flow/instance/{peer_no}/revoke", headers=auth).json()
    assert admin_revoke["code"] == 0
    peer_todos = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=peer,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    assert all(row["instanceNo"] != peer_no for row in peer_todos["data"]["list"])

    rejected_start = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": leave["id"],
            "formData": {"title": "pytest · 空意见驳回"},
            "businessKey": f"pytest-flow-reject-empty-203-{uuid.uuid4().hex[:10]}",
        },
    ).json()
    assert rejected_start["code"] == 0
    reject_no = rejected_start["data"]["instanceNo"]
    todo = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    task = next(row for row in todo["data"]["list"] if row["instanceNo"] == reject_no)
    rejected = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "REJECT", "comment": ""},
    ).json()
    assert rejected["code"] == 0
    assert rejected["data"]["newStatus"] == "REJECTED"
    assert rejected["data"]["rejectToNodeOrder"] == 1
    assert rejected["data"]["commentHint"] == "退回建议填写意见"

    rejected_detail = client.get(f"/admin-api/ims/flow/instance/{reject_no}", headers=auth).json()["data"]
    assert rejected_detail["edgeCopy"] == "实例已驳回结束，不可撤销。"
    assert rejected_detail["canRevoke"] is False
    blocked = client.put(f"/admin-api/ims/flow/instance/{reject_no}/revoke", headers=auth).json()
    assert blocked["code"] == 1140


def headers_for(username: str) -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
