"""内容 AI / ComfyUI 桩与任务表。与 SOP/计划模型分文件，避免并片改同一模型块。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core import Base, utcnow


class ContentScript(Base):
    __tablename__ = "ims_content_script"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    script_type: Mapped[str] = mapped_column(String(32), default="MONOLOGUE")
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    ai_generated: Mapped[int] = mapped_column(Integer, default=1)
    prompt_snapshot: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    author_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentWorkflow(Base):
    __tablename__ = "ims_content_workflow"
    __table_args__ = (UniqueConstraint("workflow_code", name="uk_content_workflow_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workflow_code: Mapped[str] = mapped_column(String(64), default="")
    workflow_name: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    param_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentAiTask(Base):
    __tablename__ = "ims_content_ai_task"
    __table_args__ = (UniqueConstraint("task_no", name="uk_content_ai_task_no"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_no: Mapped[str] = mapped_column(String(32), default="")
    topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    script_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_project_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    requirement: Mapped[str] = mapped_column(Text, default="")
    prompt_initial: Mapped[str] = mapped_column(Text, default="")
    prompt_final: Mapped[str] = mapped_column(Text, default="")
    workflow_id: Mapped[int] = mapped_column(BigInteger, default=0)
    task_status: Mapped[str] = mapped_column(String(32), default="WAITING")
    output_file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentAiJob(Base):
    __tablename__ = "ims_content_ai_job"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_no: Mapped[str] = mapped_column(String(32), index=True, default="")
    workflow_id: Mapped[int] = mapped_column(BigInteger, default=0)
    node_name: Mapped[str] = mapped_column(String(64), default="")
    priority: Mapped[str] = mapped_column(String(8), default="P2")
    queue_status: Mapped[str] = mapped_column(String(16), default="WAITING")
    gpu_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    upstream_id: Mapped[str] = mapped_column(String(64), default="")
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(512), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentDraftMedia(Base):
    __tablename__ = "ims_content_draft_media"
    __table_args__ = (UniqueConstraint("content_project_id", name="uk_content_draft_media"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content_project_id: Mapped[int] = mapped_column(BigInteger, index=True)
    copy_upstream_id: Mapped[str] = mapped_column(String(64), default="")
    video_task_no: Mapped[str] = mapped_column(String(32), default="")
    video_job_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    video_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    video_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
