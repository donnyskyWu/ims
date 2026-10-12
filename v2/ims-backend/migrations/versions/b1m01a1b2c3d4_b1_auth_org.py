"""b1 auth org and position rules

Revision ID: b1m01a1b2c3d4
Revises: a8ea91bf512c
Create Date: 2026-10-12 08:40:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1m01a1b2c3d4"
down_revision: Union[str, None] = "a8ea91bf512c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ims_sys_user_role", sa.Column("rule_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_sys_user_role", sa.Column("rule_version", sa.Integer(), nullable=True))
    op.create_index("ix_user_emp_no", "ims_sys_user", ["tenant_id", "emp_no"])
    op.add_column("ims_sys_login_log", sa.Column("channel", sa.String(length=32), nullable=True))
    op.add_column("ims_sys_login_log", sa.Column("fail_code", sa.Integer(), nullable=True))
    op.add_column("ims_auth_position_role_rule", sa.Column("rule_name", sa.String(length=64), nullable=True))
    op.add_column("ims_auth_position_role_rule", sa.Column("description", sa.String(length=200), nullable=True))
    op.add_column("ims_auth_position_role_rule", sa.Column("active_slot", sa.String(length=64), nullable=True))
    with op.batch_alter_table("ims_auth_position_role_rule") as batch:
        batch.create_unique_constraint("uq_pos_rule_name", ["tenant_id", "rule_name", "deleted"])
        batch.create_unique_constraint("uq_pos_rule_active", ["tenant_id", "active_slot", "deleted"])
    op.add_column("ims_auth_org_sync_event", sa.Column("biz_type", sa.String(length=32), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("subject_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("subject_name", sa.String(length=80), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("dept_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("before_dept_names", sa.String(length=500), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("after_dept_names", sa.String(length=500), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("received_time", sa.DateTime(), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("processed_time", sa.DateTime(), nullable=True))
    op.add_column("ims_auth_org_sync_event", sa.Column("delay_seconds", sa.Integer(), nullable=True))
    op.add_column("ims_auth_org_sync_batch", sa.Column("trigger_type", sa.String(length=16), nullable=True))
    op.add_column("ims_auth_org_sync_batch", sa.Column("operator_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_auth_org_sync_batch", sa.Column("diff_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_auth_org_sync_batch", sa.Column("fixed_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_auth_org_sync_batch", sa.Column("fail_reason", sa.String(length=255), nullable=True))
    op.create_table(
        "ims_auth_position_rule_role",
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("role_type", sa.String(length=16), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "role_id", name="uq_rule_role"),
    )
    op.create_table(
        "ims_auth_position_rule_version",
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rule_name", sa.String(length=64), nullable=True),
        sa.Column("main_role_id", sa.BigInteger(), nullable=True),
        sa.Column("extra_role_ids", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
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
        "ims_auth_org_sync_event_attempt",
        sa.Column("event_row_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.String(length=255), nullable=True),
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
        "ims_auth_org_sync_batch_item",
        sa.Column("batch_id", sa.BigInteger(), nullable=True),
        sa.Column("object_type", sa.String(length=16), nullable=False),
        sa.Column("object_id", sa.String(length=64), nullable=True),
        sa.Column("object_name", sa.String(length=80), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("before_value", sa.String(length=255), nullable=True),
        sa.Column("after_value", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("error_msg", sa.String(length=255), nullable=True),
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
    op.drop_table("ims_auth_org_sync_batch_item")
    op.drop_table("ims_auth_org_sync_event_attempt")
    op.drop_table("ims_auth_position_rule_version")
    op.drop_table("ims_auth_position_rule_role")
    op.drop_column("ims_auth_org_sync_batch", "fail_reason")
    op.drop_column("ims_auth_org_sync_batch", "fixed_count")
    op.drop_column("ims_auth_org_sync_batch", "diff_count")
    op.drop_column("ims_auth_org_sync_batch", "operator_id")
    op.drop_column("ims_auth_org_sync_batch", "trigger_type")
    op.drop_column("ims_auth_org_sync_event", "delay_seconds")
    op.drop_column("ims_auth_org_sync_event", "processed_time")
    op.drop_column("ims_auth_org_sync_event", "received_time")
    op.drop_column("ims_auth_org_sync_event", "after_dept_names")
    op.drop_column("ims_auth_org_sync_event", "before_dept_names")
    op.drop_column("ims_auth_org_sync_event", "dept_id")
    op.drop_column("ims_auth_org_sync_event", "subject_name")
    op.drop_column("ims_auth_org_sync_event", "subject_user_id")
    op.drop_column("ims_auth_org_sync_event", "biz_type")
    with op.batch_alter_table("ims_auth_position_role_rule") as batch:
        batch.drop_constraint("uq_pos_rule_active", type_="unique")
        batch.drop_constraint("uq_pos_rule_name", type_="unique")
    op.drop_column("ims_auth_position_role_rule", "active_slot")
    op.drop_column("ims_auth_position_role_rule", "description")
    op.drop_column("ims_auth_position_role_rule", "rule_name")
    op.drop_column("ims_sys_login_log", "fail_code")
    op.drop_column("ims_sys_login_log", "channel")
    op.drop_index("ix_user_emp_no", table_name="ims_sys_user")
    op.drop_column("ims_sys_user_role", "rule_version")
    op.drop_column("ims_sys_user_role", "rule_id")
