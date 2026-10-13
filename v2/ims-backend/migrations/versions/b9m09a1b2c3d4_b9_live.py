"""b9 live session columns and eight tables

Revision ID: b9m09a1b2c3d4
Revises: b8m08a1b2c3d4
Create Date: 2026-10-13 12:00:00

版本：B9 v1.0。只加列和新表，不建物理外键。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9m09a1b2c3d4"
down_revision: Union[str, None] = "b8m08a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit():
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("updater", sa.BigInteger(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("deleted", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("ims_live_session", sa.Column("platform", sa.String(length=32), nullable=True))
    op.add_column("ims_live_session", sa.Column("responsible_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_live_session", sa.Column("author_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_live_session", sa.Column("topic", sa.String(length=256), nullable=True))
    op.add_column("ims_live_session", sa.Column("plan_start_time", sa.DateTime(), nullable=True))
    op.add_column("ims_live_session", sa.Column("plan_end_time", sa.DateTime(), nullable=True))
    op.add_column("ims_live_session", sa.Column("actual_start_time", sa.DateTime(), nullable=True))
    op.add_column("ims_live_session", sa.Column("actual_end_time", sa.DateTime(), nullable=True))
    op.add_column(
        "ims_live_session",
        sa.Column("session_status", sa.String(length=32), nullable=False, server_default="PENDING_RISK_CHECK"),
    )
    op.add_column("ims_live_session", sa.Column("risk_score", sa.Integer(), nullable=True))
    op.add_column("ims_live_session", sa.Column("risk_level", sa.String(length=16), nullable=True))
    op.add_column("ims_live_session", sa.Column("approver_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_live_session", sa.Column("approve_opinion", sa.String(length=512), nullable=True))
    op.add_column("ims_live_session", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("ims_live_session", sa.Column("cancel_reason", sa.String(length=256), nullable=True))
    op.add_column("ims_live_session", sa.Column("is_supplement", sa.SmallInteger(), nullable=False, server_default="0"))
    op.add_column("ims_live_session", sa.Column("supplement_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "ims_live_session",
        sa.Column("football_sync_status", sa.String(length=16), nullable=False, server_default="UNLINKED"),
    )
    op.add_column("ims_live_session", sa.Column("last_football_sync_at", sa.DateTime(), nullable=True))
    op.add_column("ims_live_session", sa.Column("client_token", sa.String(length=64), nullable=True))
    op.add_column("ims_live_session", sa.Column("overdue_notified", sa.SmallInteger(), nullable=False, server_default="0"))
    op.add_column("ims_live_session", sa.Column("last_remind_at", sa.DateTime(), nullable=True))
    op.create_index("ix_live_session_status", "ims_live_session", ["tenant_id", "session_status"])
    op.create_index("ix_live_session_account", "ims_live_session", ["tenant_id", "account_id"])

    def table(name, columns, unique=None):
        cols = list(columns) + _audit()
        args = [name, *cols, sa.PrimaryKeyConstraint("id")]
        if unique:
            args.append(sa.UniqueConstraint(*unique[0], name=unique[1]))
        op.create_table(*args)

    table(
        "ims_live_session_device",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("asset_id", sa.BigInteger(), nullable=False),
        ],
    )
    table(
        "ims_live_risk_check",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("check_round", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("check_item", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("check_result", sa.String(length=16), nullable=False, server_default="PASS"),
            sa.Column("score_weight", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("detail", sa.String(length=512), nullable=True),
            sa.Column("checked_at", sa.DateTime(), nullable=True),
        ],
    )
    table(
        "ims_live_report",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("actual_start", sa.DateTime(), nullable=True),
            sa.Column("actual_end", sa.DateTime(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("gmv", sa.Numeric(12, 2), nullable=True),
            sa.Column("order_count", sa.Integer(), nullable=True),
            sa.Column("viewer_count", sa.Integer(), nullable=True),
            sa.Column("peak_online", sa.Integer(), nullable=True),
            sa.Column("new_fans", sa.Integer(), nullable=True),
            sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("ad_cost", sa.Numeric(12, 2), nullable=True),
            sa.Column("entry_status", sa.String(length=16), nullable=False, server_default="DRAFT"),
            sa.Column("entry_user_id", sa.BigInteger(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("confirm_user_id", sa.BigInteger(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        ],
        unique=(("tenant_id", "session_id", "deleted"), "uq_live_report_session"),
    )
    table(
        "ims_live_cost",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("cost_type", sa.String(length=16), nullable=False, server_default="AD"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("ref_recharge_id", sa.BigInteger(), nullable=True),
            sa.Column("remark", sa.String(length=256), nullable=True),
        ],
    )
    table(
        "ims_live_report_correction",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("before_json", sa.JSON(), nullable=True),
            sa.Column("after_json", sa.JSON(), nullable=True),
            sa.Column("reason", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("operator_id", sa.BigInteger(), nullable=True),
        ],
    )
    table(
        "ims_live_data_snapshot",
        [
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("source", sa.String(length=16), nullable=False, server_default="FOOTBALL"),
            sa.Column("viewer_count", sa.Integer(), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=True),
            sa.Column("reserve_count", sa.Integer(), nullable=True),
            sa.Column("room_status", sa.String(length=16), nullable=True),
            sa.Column("room_start_time", sa.DateTime(), nullable=True),
            sa.Column("room_end_time", sa.DateTime(), nullable=True),
            sa.Column("captured_at", sa.DateTime(), nullable=True),
        ],
    )
    table(
        "ims_live_alarm_rule",
        [
            sa.Column("rule_name", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("rule_type", sa.String(length=16), nullable=False, server_default="THRESHOLD"),
            sa.Column("metric", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("operator", sa.String(length=16), nullable=False, server_default="GT"),
            sa.Column("threshold", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("window_minutes", sa.Integer(), nullable=True),
            sa.Column("level", sa.String(length=8), nullable=False, server_default="2"),
            sa.Column("notify_role_ids", sa.JSON(), nullable=True),
            sa.Column("notify_user_ids", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="DISABLED"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        ],
        unique=(("tenant_id", "rule_name", "deleted"), "uq_live_alarm_rule_name"),
    )
    table(
        "ims_live_alarm_record",
        [
            sa.Column("rule_id", sa.BigInteger(), nullable=True),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("alarm_level", sa.String(length=8), nullable=False, server_default="2"),
            sa.Column("alarm_content", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("occur_at", sa.DateTime(), nullable=True),
            sa.Column("merge_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_occur_at", sa.DateTime(), nullable=True),
            sa.Column("handle_status", sa.String(length=16), nullable=False, server_default="UNHANDLED"),
            sa.Column("handler_user_id", sa.BigInteger(), nullable=True),
            sa.Column("handle_remark", sa.String(length=512), nullable=True),
            sa.Column("handled_at", sa.DateTime(), nullable=True),
            sa.Column("escalated", sa.SmallInteger(), nullable=False, server_default="0"),
            sa.Column("escalated_at", sa.DateTime(), nullable=True),
        ],
    )
    table(
        "ims_live_supplement",
        [
            sa.Column("register_json", sa.JSON(), nullable=True),
            sa.Column("report_json", sa.JSON(), nullable=True),
            sa.Column("supplement_reason", sa.String(length=256), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
            sa.Column("applicant_id", sa.BigInteger(), nullable=True),
            sa.Column("approver_id", sa.BigInteger(), nullable=True),
            sa.Column("opinion", sa.String(length=512), nullable=True),
            sa.Column("session_id", sa.BigInteger(), nullable=True),
            sa.Column("cost_json", sa.JSON(), nullable=True),
            sa.Column("reject_editable", sa.SmallInteger(), nullable=False, server_default="0"),
        ],
    )


def downgrade() -> None:
    for name in (
        "ims_live_supplement",
        "ims_live_alarm_record",
        "ims_live_alarm_rule",
        "ims_live_data_snapshot",
        "ims_live_report_correction",
        "ims_live_cost",
        "ims_live_report",
        "ims_live_risk_check",
        "ims_live_session_device",
    ):
        op.drop_table(name)
    op.drop_index("ix_live_session_account", table_name="ims_live_session")
    op.drop_index("ix_live_session_status", table_name="ims_live_session")
    for name in (
        "last_remind_at",
        "overdue_notified",
        "client_token",
        "last_football_sync_at",
        "football_sync_status",
        "supplement_id",
        "is_supplement",
        "cancel_reason",
        "approved_at",
        "approve_opinion",
        "approver_user_id",
        "risk_level",
        "risk_score",
        "session_status",
        "actual_end_time",
        "actual_start_time",
        "plan_end_time",
        "plan_start_time",
        "topic",
        "author_id",
        "responsible_user_id",
        "platform",
    ):
        op.drop_column("ims_live_session", name)
