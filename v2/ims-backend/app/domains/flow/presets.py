"""首批预置模板：账号领用、数据上报审核、培训相关审批。不预置请假、报销、开播、内容审核。"""
from __future__ import annotations

from sqlalchemy import select

from app.db.session import get_session
from app.domains.flow.contract import create_template, publish_template
from app.domains.flow.model import FlowTemplate

PRESETS = (
    ("ACCT_BORROW", "账号领用审批", "BUSINESS", "accountName", "领用账号"),
    ("REPORT_REVIEW", "数据上报审核", "BUSINESS", "reportTitle", "上报标题"),
    ("TRAIN_APPROVAL", "培训相关审批", "COMMON", "trainTitle", "培训主题"),
)


def _nodes(field_key: str, field_label: str) -> list[dict]:
    return [
        {
            "nodeOrder": 1,
            "nodeKey": "start",
            "nodeName": "发起",
            "nodeType": "START",
            "formFields": [{"fieldKey": field_key, "fieldLabel": field_label, "fieldType": "text", "required": True}],
            "nextOrders": [2],
        },
        {
            "nodeOrder": 2,
            "nodeKey": "approve",
            "nodeName": "审批",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "LEADER"},
            "slaHours": 24,
            "nextOrders": [3],
        },
        {"nodeOrder": 3, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]


def ensure_presets() -> list[str]:
    session = get_session()
    created = []
    for code, name, domain, field_key, field_label in PRESETS:
        found = session.scalar(select(FlowTemplate).where(FlowTemplate.code == code))
        if found is not None:
            continue
        saved = create_template(
            {
                "templateName": name,
                "businessDomain": domain,
                "bizType": code,
                "nodes": _nodes(field_key, field_label),
            }
        )
        publish_template(int(saved["id"]))
        created.append(code)
    return created
