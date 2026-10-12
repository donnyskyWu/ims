"""B4 测试环境造数。只允许 test / e2e。不预置请假、报销、开播、内容审核。"""
from __future__ import annotations

import argparse
import os

ALLOWED = {"test", "e2e"}


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def seed() -> None:
    """预置三类模板、自定义模板，以及进行中、超时、已完成和改派样例。"""
    assert_allowed()
    from sqlalchemy import select

    from app.core.clock import now_naive
    from app.core.context import RequestContext, system_context, use_context
    from app.core.security import hash_password
    from datetime import timedelta

    from app.db.session import session_scope
    from app.domains.flow.contract import create_template, handle_task, publish_template, start_instance
    from app.domains.flow.model import FlowInstance, FlowTask, FlowTemplate
    from app.domains.flow.presets import ensure_presets
    from app.domains.flow.service import scan_overdue
    from app.domains.system.model import Dept
    from app.main import create_app
    from tools.e2e_seed.b2 import _dept, _role, _user

    create_app()
    password = hash_password("Test1234")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            root = session.get(Dept, 10)
            if root is None:
                root = session.scalar(select(Dept).where(Dept.parent_id == 0))
            if root is None:
                raise RuntimeError("请先执行基础种子")
            ensure_presets()
            parent = _dept(session, root, "流程演示部")
            child = _dept(session, parent, "流程演示组")
            starter_role = _role(session, "e2e_flow_start", "测试-流程发起", "DEPT", ["ims:flow:instance:start", "ims:flow:task:handle"])
            owner_role = _role(
                session,
                "e2e_flow_owner",
                "测试-业务域负责人",
                "ALL",
                ["ims:flow:instance:manage", "ims:flow:task:handle", "ims:flow:board:query"],
            )
            owner_role.flow_domain = "BUSINESS"
            boss = _user(session, "flow_boss", "流程上级", "ACTIVE", starter_role, [parent], parent, password)
            starter = _user(session, "flow_self", "流程发起人", "ACTIVE", starter_role, [child], child, password)
            _user(session, "flow_owner", "业务域负责人", "ACTIVE", owner_role, [parent], parent, password)
            parent.leader_user_id = boss.id
            child.leader_user_id = starter.id
            session.flush()
            custom = session.scalar(select(FlowTemplate).where(FlowTemplate.code == "CUSTOM_CONFIRM"))
            if custom is None:
                saved = create_template(
                    {
                        "templateName": "自定义事项确认",
                        "businessDomain": "COMMON",
                        "bizType": "CUSTOM_CONFIRM",
                        "nodes": [
                            {"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START", "nextOrders": [2], "formFields": [{"fieldKey": "title", "fieldLabel": "事项", "required": True}]},
                            {"nodeOrder": 2, "nodeKey": "approve", "nodeName": "确认", "nodeType": "APPROVE", "assigneeRule": {"assignType": "LEADER"}, "slaHours": 4, "nextOrders": [3]},
                            {"nodeOrder": 3, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
                        ],
                    }
                )
                publish_template(int(saved["id"]))
            borrow = session.scalar(select(FlowTemplate).where(FlowTemplate.code == "ACCT_BORROW"))
            if borrow is None:
                raise RuntimeError("账号领用审批未预置")
            ctx = RequestContext(
                user_id=starter.id,
                tenant_id=1,
                perm_codes={"ims:flow:instance:start", "ims:flow:manage"},
                data_scopes={"ALL"},
                username="flow_self",
                nickname="流程发起人",
            )
            with use_context(ctx):
                running = start_instance({"templateId": borrow.id, "formData": {"accountName": "演示账号"}, "businessKey": "b4-running"})
                late = start_instance({"templateId": borrow.id, "formData": {"accountName": "超时账号"}, "businessKey": "b4-late"})
                done = start_instance({"templateId": borrow.id, "formData": {"accountName": "完成账号"}, "businessKey": "b4-done"})
            late_row = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == late["instanceNo"]))
            task = session.scalar(select(FlowTask).where(FlowTask.instance_id == late_row.id, FlowTask.status == "PENDING"))
            if task is not None:
                task.due_time = now_naive() - timedelta(hours=2)
                task.overdue = 0
                task.urge_sent = 0
            done_row = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == done["instanceNo"]))
            done_task = session.scalar(select(FlowTask).where(FlowTask.instance_id == done_row.id, FlowTask.status == "PENDING"))
            if done_task is not None and done_task.assignee:
                with use_context(RequestContext(user_id=int(done_task.assignee), tenant_id=1, perm_codes={"ims:flow:task:handle"}, data_scopes={"ALL"}, username="flow_boss", nickname="流程上级")):
                    handle_task(int(done_task.id), {"action": "APPROVE", "comment": "同意"})
            scan_overdue()
            if running["instanceStatus"] not in {"RUNNING", "TIMEOUT"}:
                raise RuntimeError("进行中样例未生成")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 测试造数")
    parser.add_argument("command", choices=["seed"])
    parser.parse_args(argv)
    seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
