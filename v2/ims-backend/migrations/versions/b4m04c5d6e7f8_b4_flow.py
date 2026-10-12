"""b4 flow template, task and trace columns

Revision ID: b4m04c5d6e7f8
Revises: b3m03a7c3d4e5
Create Date: 2026-10-12 14:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b4m04c5d6e7f8"
down_revision: Union[str, None] = "b3m03a7c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _widen_template_name() -> None:
    """SQLite 不支持改列类型。VARCHAR 在 SQLite 中不截断，跳过不影响 MySQL 扩列。"""
    if op.get_bind().dialect.name == "sqlite":
        return
    op.alter_column("ims_flow_template", "name", existing_type=sa.String(length=100), type_=sa.String(length=128), existing_nullable=False)


def _narrow_template_name() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    op.alter_column("ims_flow_template", "name", existing_type=sa.String(length=128), type_=sa.String(length=100), existing_nullable=False)


def upgrade() -> None:
    op.add_column("ims_sys_role", sa.Column("flow_domain", sa.String(length=64), nullable=True))
    _widen_template_name()
    op.add_column("ims_flow_template", sa.Column("template_no", sa.String(length=32), nullable=True))
    op.add_column("ims_flow_template", sa.Column("business_domain", sa.String(length=32), nullable=True))
    op.add_column("ims_flow_template", sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_flow_template", sa.Column("start_perm", sa.String(length=80), nullable=True))
    op.add_column("ims_flow_template", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.add_column("ims_flow_template_version", sa.Column("change_desc", sa.String(length=512), nullable=True))
    op.add_column("ims_flow_template_version", sa.Column("published_by", sa.BigInteger(), nullable=True))
    op.add_column("ims_flow_template_version", sa.Column("rolled_back", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_flow_instance", sa.Column("instance_no", sa.String(length=32), nullable=True))
    op.add_column("ims_flow_instance", sa.Column("template_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_flow_instance", sa.Column("form_data", sa.JSON(), nullable=True))
    op.add_column("ims_flow_instance", sa.Column("business_key", sa.String(length=128), nullable=True))
    op.add_column("ims_flow_instance", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.add_column("ims_flow_instance", sa.Column("version_no", sa.Integer(), nullable=True))
    op.add_column("ims_flow_task", sa.Column("node_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_flow_task", sa.Column("node_name", sa.String(length=64), nullable=True))
    op.add_column("ims_flow_task", sa.Column("node_type", sa.String(length=16), nullable=True))
    op.add_column("ims_flow_task", sa.Column("sla_hours", sa.Integer(), nullable=True))
    op.add_column("ims_flow_task", sa.Column("remind_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_flow_task", sa.Column("reassign_from", sa.BigInteger(), nullable=True))
    op.add_column("ims_flow_task", sa.Column("escalated", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_flow_task", sa.Column("handled_at", sa.DateTime(), nullable=True))
    op.add_column("ims_flow_task", sa.Column("parallel_group", sa.String(length=64), nullable=True))
    op.add_column("ims_flow_task", sa.Column("warn_sent", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "ims_flow_trace",
        sa.Column("instance_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column("node_key", sa.String(length=64), nullable=True),
        sa.Column("node_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("node_name", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("detail", sa.String(length=512), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("updater", sa.BigInteger(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("deleted", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_flow_cc",
        sa.Column("instance_id", sa.BigInteger(), nullable=False),
        sa.Column("node_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("node_name", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("notified_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("updater", sa.BigInteger(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("deleted", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ims_flow_cc")
    op.drop_table("ims_flow_trace")
    for name in (
        "warn_sent",
        "parallel_group",
        "handled_at",
        "escalated",
        "reassign_from",
        "remind_count",
        "sla_hours",
        "node_type",
        "node_name",
        "node_order",
    ):
        op.drop_column("ims_flow_task", name)
    for name in ("version_no", "finished_at", "business_key", "form_data", "template_id", "instance_no"):
        op.drop_column("ims_flow_instance", name)
    op.drop_column("ims_flow_template_version", "rolled_back")
    op.drop_column("ims_flow_template_version", "published_by")
    op.drop_column("ims_flow_template_version", "change_desc")
    op.drop_column("ims_flow_template", "published_at")
    op.drop_column("ims_flow_template", "start_perm")
    op.drop_column("ims_flow_template", "current_version")
    op.drop_column("ims_flow_template", "business_domain")
    op.drop_column("ims_flow_template", "template_no")
    _narrow_template_name()
    op.drop_column("ims_sys_role", "flow_domain")
