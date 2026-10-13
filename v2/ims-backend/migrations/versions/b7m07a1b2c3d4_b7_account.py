"""b7 account ledger, borrow, return and recharge

Revision ID: b7m07a1b2c3d4
Revises: b7m07merge01
Create Date: 2026-10-13 08:10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7m07a1b2c3d4"
down_revision: Union[str, None] = "b7m07merge01"
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
    op.add_column("ims_account_platform", sa.Column("account_no", sa.String(length=32), nullable=True))
    op.add_column("ims_account_platform", sa.Column("nickname", sa.String(length=64), nullable=True))
    op.add_column("ims_account_platform", sa.Column("company_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("sim_card_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("phone_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("ip_group_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("author_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_platform", sa.Column("collect_bind_status", sa.String(length=32), nullable=True))
    op.add_column("ims_account_platform", sa.Column("remark", sa.String(length=256), nullable=True))
    op.add_column("ims_account_platform", sa.Column("recharge_total_fen", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("uq_platform_account_no", "ims_account_platform", ["tenant_id", "account_no", "deleted"], unique=True)

    op.add_column("ims_account_personal", sa.Column("account_no", sa.String(length=32), nullable=True))
    op.add_column("ims_account_personal", sa.Column("account_type", sa.String(length=32), nullable=True))
    op.add_column("ims_account_personal", sa.Column("nickname", sa.String(length=64), nullable=True))
    op.add_column("ims_account_personal", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_account_personal", sa.Column("mobile_mask", sa.String(length=32), nullable=True))
    op.add_column("ims_account_personal", sa.Column("mobile_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_account_personal", sa.Column("remark", sa.String(length=256), nullable=True))
    op.create_index("uq_personal_account_no", "ims_account_personal", ["tenant_id", "account_no", "deleted"], unique=True)

    op.create_table(
        "ims_account_collect_credential",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("cookie_enc", sa.Text(), nullable=True),
        sa.Column("token_enc", sa.Text(), nullable=True),
        sa.Column("field_mapping", sa.JSON(), nullable=True),
        sa.Column("last_probe_at", sa.DateTime(), nullable=True),
        sa.Column("last_probe_ok", sa.Integer(), nullable=True),
        sa.Column("collector_account_id", sa.String(length=64), nullable=True),
        sa.Column("probe_message", sa.String(length=255), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "account_id", "deleted", name="uq_collect_account"),
    )
    op.create_table(
        "ims_account_apply",
        sa.Column("apply_no", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_user_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.String(length=256), nullable=False),
        sa.Column("plan_start", sa.Date(), nullable=False),
        sa.Column("plan_end", sa.Date(), nullable=False),
        sa.Column("apply_status", sa.String(length=32), nullable=False),
        sa.Column("flow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("handover_detail", sa.JSON(), nullable=True),
        sa.Column("current_step", sa.String(length=64), nullable=True),
        sa.Column("idle_reminded", sa.Integer(), nullable=False, server_default="0"),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "apply_no", "deleted", name="uq_apply_no"),
    )
    op.create_table(
        "ims_account_transfer",
        sa.Column("transfer_no", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("transfer_type", sa.String(length=32), nullable=False),
        sa.Column("from_user_id", sa.BigInteger(), nullable=True),
        sa.Column("to_user_id", sa.BigInteger(), nullable=True),
        sa.Column("reason_type", sa.String(length=32), nullable=True),
        sa.Column("remark", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.DateTime(), nullable=True),
        sa.Column("sync_assets", sa.Integer(), nullable=False, server_default="0"),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "transfer_no", "deleted", name="uq_transfer_no"),
    )
    op.create_table(
        "ims_account_return_order",
        sa.Column("return_no", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("resign_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("suspend_reason", sa.String(length=256), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "return_no", "deleted", name="uq_return_no"),
    )
    op.create_table(
        "ims_account_return_item",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("item_snapshot", sa.JSON(), nullable=True),
        sa.Column("item_status", sa.String(length=32), nullable=False),
        sa.Column("handler_user_id", sa.BigInteger(), nullable=True),
        sa.Column("transfer_to_user_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(length=256), nullable=True),
        sa.Column("transfer_id", sa.BigInteger(), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_account_recharge",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_fen", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recharge_date", sa.Date(), nullable=False),
        sa.Column("voucher_file_key", sa.String(length=255), nullable=True),
        sa.Column("verify_status", sa.String(length=32), nullable=False),
        sa.Column("verify_diff_fen", sa.Integer(), nullable=True),
        sa.Column("operator_user_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(length=256), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_account_recharge_verify",
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("total_recharge_fen", sa.Integer(), nullable=False),
        sa.Column("platform_consumed_fen", sa.Integer(), nullable=False),
        sa.Column("diff_rate_bp", sa.Integer(), nullable=False),
        sa.Column("diff_detail", sa.JSON(), nullable=True),
        sa.Column("ticket_created", sa.Integer(), nullable=False, server_default="0"),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ims_account_recharge_verify")
    op.drop_table("ims_account_recharge")
    op.drop_table("ims_account_return_item")
    op.drop_table("ims_account_return_order")
    op.drop_table("ims_account_transfer")
    op.drop_table("ims_account_apply")
    op.drop_table("ims_account_collect_credential")
    op.drop_index("uq_personal_account_no", table_name="ims_account_personal")
    for name in ("remark", "mobile_hash", "mobile_mask", "owner_user_id", "nickname", "account_type", "account_no"):
        op.drop_column("ims_account_personal", name)
    op.drop_index("uq_platform_account_no", table_name="ims_account_platform")
    for name in (
        "recharge_total_fen",
        "remark",
        "collect_bind_status",
        "owner_user_id",
        "author_user_id",
        "ip_group_id",
        "phone_id",
        "sim_card_id",
        "company_id",
        "nickname",
        "account_no",
    ):
        op.drop_column("ims_account_platform", name)
