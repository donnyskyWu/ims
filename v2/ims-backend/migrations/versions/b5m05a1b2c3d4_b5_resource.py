"""b5 company, realname, sim and certificate columns

Revision ID: b5m05a1b2c3d4
Revises: b4m04c5d6e7f8
Create Date: 2026-10-12 18:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b5m05a1b2c3d4"
down_revision: Union[str, None] = "b4m04c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ims_org_company", sa.Column("company_no", sa.String(length=32), nullable=True))
    op.add_column("ims_org_company", sa.Column("credit_code", sa.String(length=18), nullable=True))
    op.add_column("ims_org_company", sa.Column("legal_person", sa.String(length=32), nullable=True))
    op.add_column("ims_org_company", sa.Column("address", sa.String(length=128), nullable=True))
    op.add_column("ims_org_company", sa.Column("wx_official_capacity", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_org_company", sa.Column("remark", sa.String(length=255), nullable=True))
    op.create_index("uq_company_name", "ims_org_company", ["tenant_id", "name", "deleted"], unique=True)
    op.create_index("uq_company_credit", "ims_org_company", ["tenant_id", "credit_code", "deleted"], unique=True)

    op.add_column("ims_master_realname", sa.Column("realname_no", sa.String(length=32), nullable=True))
    op.add_column("ims_master_realname", sa.Column("id_type", sa.String(length=32), nullable=True))
    op.add_column("ims_master_realname", sa.Column("id_no_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_realname", sa.Column("id_no_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_master_realname", sa.Column("mobile_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_realname", sa.Column("mobile_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_master_realname", sa.Column("agent_name", sa.String(length=32), nullable=True))
    op.add_column("ims_master_realname", sa.Column("agent_mobile_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_realname", sa.Column("remark", sa.Text(), nullable=True))
    op.create_index("uq_realname_idhash", "ims_master_realname", ["tenant_id", "id_no_hash", "deleted"], unique=True)

    op.add_column("ims_master_sim_card", sa.Column("sim_no", sa.String(length=32), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("phone_number_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("phone_number_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("iccid_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("iccid_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("operator", sa.String(length=32), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("is_primary", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_master_sim_card", sa.Column("realname_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("assigned_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("package_name", sa.String(length=64), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("monthly_rent", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_master_sim_card", sa.Column("payment_cycle", sa.String(length=32), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("activated_at", sa.Date(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("next_payment_date", sa.Date(), nullable=True))
    op.add_column("ims_master_sim_card", sa.Column("phone_id", sa.BigInteger(), nullable=True))
    op.create_index("uq_sim_phone", "ims_master_sim_card", ["tenant_id", "phone_number_hash", "deleted"], unique=True)
    op.create_index("uq_sim_iccid", "ims_master_sim_card", ["tenant_id", "iccid_hash", "deleted"], unique=True)

    op.add_column("ims_master_cert", sa.Column("cert_no", sa.String(length=32), nullable=True))
    op.add_column("ims_master_cert", sa.Column("cert_type", sa.String(length=32), nullable=True))
    op.add_column("ims_master_cert", sa.Column("cert_no_enc", sa.Text(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("cert_no_hash", sa.String(length=64), nullable=True))
    op.add_column("ims_master_cert", sa.Column("issue_date", sa.Date(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("expire_date", sa.Date(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("file_key", sa.String(length=255), nullable=True))
    op.add_column("ims_master_cert", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("ims_master_cert", sa.Column("renew_of_cert_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("reviewed_by", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("reject_reason", sa.String(length=255), nullable=True))
    op.add_column("ims_master_cert", sa.Column("uploaded_by", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_cert", sa.Column("ocr_status", sa.String(length=16), nullable=True))

    def audit():
        return [
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("creator", sa.BigInteger(), nullable=False),
            sa.Column("create_time", sa.DateTime(), nullable=False),
            sa.Column("updater", sa.BigInteger(), nullable=False),
            sa.Column("update_time", sa.DateTime(), nullable=False),
            sa.Column("deleted", sa.BigInteger(), nullable=False),
            sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        ]

    op.create_table(
        "ims_org_company_capacity_log",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("before_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("after_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operator_name", sa.String(length=50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_expire_task",
        sa.Column("cert_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="YELLOW"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="WARNING"),
        sa.Column("notified_user_ids", sa.JSON(), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("remind_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trace", sa.JSON(), nullable=True),
        *audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_level_config",
        sa.Column("l2_role_ids", sa.JSON(), nullable=True),
        sa.Column("l3_user_ids", sa.JSON(), nullable=True),
        sa.Column("opacity", sa.Numeric(4, 2), nullable=False, server_default="0.12"),
        sa.Column("position", sa.String(length=32), nullable=False, server_default="BOTTOM_RIGHT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *audit(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_view_log",
        sa.Column("cert_id", sa.BigInteger(), nullable=False),
        sa.Column("viewer_id", sa.BigInteger(), nullable=True),
        sa.Column("viewer_name", sa.String(length=50), nullable=True),
        sa.Column("view_level", sa.String(length=8), nullable=False, server_default="L1"),
        sa.Column("watermark_text", sa.String(length=255), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("device", sa.String(length=255), nullable=True),
        sa.Column("risk_flag", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("holder_label", sa.Text(), nullable=True),
        *audit(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ims_cert_view_log")
    op.drop_table("ims_cert_level_config")
    op.drop_table("ims_cert_expire_task")
    op.drop_table("ims_org_company_capacity_log")
    for name in (
        "ocr_status",
        "uploaded_by",
        "reject_reason",
        "reviewed_at",
        "reviewed_by",
        "renew_of_cert_id",
        "version",
        "file_key",
        "expire_date",
        "issue_date",
        "cert_no_hash",
        "cert_no_enc",
        "cert_type",
        "cert_no",
    ):
        op.drop_column("ims_master_cert", name)
    op.drop_index("uq_sim_iccid", table_name="ims_master_sim_card")
    op.drop_index("uq_sim_phone", table_name="ims_master_sim_card")
    for name in (
        "phone_id",
        "next_payment_date",
        "activated_at",
        "payment_cycle",
        "monthly_rent",
        "package_name",
        "assigned_user_id",
        "realname_id",
        "is_primary",
        "operator",
        "iccid_hash",
        "iccid_enc",
        "phone_number_hash",
        "phone_number_enc",
        "sim_no",
    ):
        op.drop_column("ims_master_sim_card", name)
    op.drop_index("uq_realname_idhash", table_name="ims_master_realname")
    for name in (
        "remark",
        "agent_mobile_enc",
        "agent_name",
        "mobile_hash",
        "mobile_enc",
        "id_no_hash",
        "id_no_enc",
        "id_type",
        "realname_no",
    ):
        op.drop_column("ims_master_realname", name)
    op.drop_index("uq_company_credit", table_name="ims_org_company")
    op.drop_index("uq_company_name", table_name="ims_org_company")
    for name in ("remark", "wx_official_capacity", "address", "legal_person", "credit_code", "company_no"):
        op.drop_column("ims_org_company", name)
