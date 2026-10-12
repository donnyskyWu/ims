from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import plain_id


class FlowTemplate(AuditBase):
    __tablename__ = "ims_flow_template"
    __entity_label__ = "流程模板"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_flow_code"),)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    template_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    business_domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_perm: Mapped[str | None] = mapped_column(String(80), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FlowTemplateVersion(AuditBase):
    __tablename__ = "ims_flow_template_version"
    template_id: Mapped[int] = plain_id(nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    nodes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_desc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_by: Mapped[int | None] = plain_id()
    rolled_back: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FlowInstance(AuditBase):
    __tablename__ = "ims_flow_instance"
    __entity_label__ = "流程实例"
    template_version_id: Mapped[int] = plain_id(nullable=False)
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False)
    biz_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initiator: Mapped[int] = plain_id(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", info={"dict": "dict_flow_status"})
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    instance_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    template_id: Mapped[int | None] = plain_id()
    form_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    business_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version_no: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FlowTask(AuditBase):
    __tablename__ = "ims_flow_task"
    instance_id: Mapped[int] = plain_id(nullable=False)
    node: Mapped[str] = mapped_column(String(64), nullable=False)
    assignee: Mapped[int | None] = plain_id()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urge_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sla_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remind_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reassign_from: Mapped[int | None] = plain_id()
    escalated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parallel_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warn_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FlowTrace(AuditBase):
    __tablename__ = "ims_flow_trace"
    instance_id: Mapped[int] = plain_id(nullable=False)
    task_id: Mapped[int | None] = plain_id()
    node_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[int | None] = plain_id()
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)


class FlowCcRecord(AuditBase):
    __tablename__ = "ims_flow_cc"
    instance_id: Mapped[int] = plain_id(nullable=False)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int] = plain_id(nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
