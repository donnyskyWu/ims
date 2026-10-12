"""b6 device ledger, phone columns and verify tasks

Revision ID: b6m06a1b2c3d4
Revises: b5m05a1b2c3d4
Create Date: 2026-10-12 16:10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b6m06a1b2c3d4"
down_revision: Union[str, None] = "b5m05a1b2c3d4"
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
    op.add_column("ims_master_phone", sa.Column("device_no", sa.String(length=32), nullable=True))
    op.add_column("ims_master_phone", sa.Column("model", sa.String(length=64), nullable=True))
    op.add_column("ims_master_phone", sa.Column("os_type", sa.String(length=32), nullable=True))
    op.add_column("ims_master_phone", sa.Column("imei", sa.String(length=15), nullable=True))
    op.add_column("ims_master_phone", sa.Column("custodian_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_phone", sa.Column("purchase_date", sa.Date(), nullable=True))
    op.add_column("ims_master_phone", sa.Column("purchase_amount", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_master_phone", sa.Column("remark", sa.String(length=256), nullable=True))
    op.create_index("uq_phone_device_no", "ims_master_phone", ["tenant_id", "device_no", "deleted"], unique=True)
    op.create_index("uq_phone_imei", "ims_master_phone", ["tenant_id", "imei", "deleted"], unique=True)

    op.create_table(
        "ims_asset_ledger",
        sa.Column("asset_code", sa.String(length=32), nullable=False),
        sa.Column("asset_name", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("spec", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("realname_id", sa.BigInteger(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_file_keys", sa.JSON(), nullable=True),
        sa.Column("purchase_batch_no", sa.String(length=32), nullable=True),
        sa.Column("remark", sa.String(length=256), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "asset_code", "deleted", name="uq_asset_code"),
    )
    op.create_table(
        "ims_asset_event",
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("from_owner_id", sa.BigInteger(), nullable=True),
        sa.Column("to_owner_id", sa.BigInteger(), nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("detail", sa.String(length=512), nullable=True),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_asset_bind",
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("bind_type", sa.String(length=32), nullable=False),
        sa.Column("bind_status", sa.String(length=32), nullable=False),
        sa.Column("effective_time", sa.DateTime(), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_asset_purchase_batch",
        sa.Column("batch_no", sa.String(length=32), nullable=False),
        sa.Column("file_name", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", sa.JSON(), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_asset_verify_batch",
        sa.Column("batch_no", sa.String(length=32), nullable=False),
        sa.Column("verify_type", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "batch_no", "deleted", name="uq_verify_batch"),
    )
    op.create_table(
        "ims_asset_verify_task",
        sa.Column("task_no", sa.String(length=32), nullable=False),
        sa.Column("batch_no", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("ref_type", sa.String(length=32), nullable=False),
        sa.Column("inconsistent_fields", sa.JSON(), nullable=True),
        sa.Column("task_status", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("fix_remark", sa.String(length=512), nullable=True),
        sa.Column("recheck_remark", sa.String(length=512), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("batch_id", sa.BigInteger(), nullable=True),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ims_asset_verify_task")
    op.drop_table("ims_asset_verify_batch")
    op.drop_table("ims_asset_purchase_batch")
    op.drop_table("ims_asset_bind")
    op.drop_table("ims_asset_event")
    op.drop_table("ims_asset_ledger")
    op.drop_index("uq_phone_imei", table_name="ims_master_phone")
    op.drop_index("uq_phone_device_no", table_name="ims_master_phone")
    for name in ("remark", "purchase_amount", "purchase_date", "custodian_user_id", "imei", "os_type", "model", "device_no"):
        op.drop_column("ims_master_phone", name)
