"""b8 ip group, member, anchor and author columns

Revision ID: b8m08a1b2c3d4
Revises: b7m07a1b2c3d4
Create Date: 2026-10-13 10:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8m08a1b2c3d4"
down_revision: Union[str, None] = "b7m07a1b2c3d4"
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
    op.add_column("ims_ipg_group", sa.Column("group_name", sa.String(length=50), nullable=True))
    op.add_column("ims_ipg_group", sa.Column("group_type", sa.String(length=16), nullable=False, server_default="BIG"))
    op.add_column("ims_ipg_group", sa.Column("parent_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_ipg_group", sa.Column("leader_user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_ipg_group", sa.Column("level", sa.String(length=16), nullable=True))
    op.add_column("ims_ipg_group", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ims_ipg_group", sa.Column("remark", sa.String(length=255), nullable=True))
    op.add_column("ims_ipg_group", sa.Column("ding_dept_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE ims_ipg_group SET group_name = name WHERE group_name IS NULL")

    op.add_column("ims_ipg_member", sa.Column("position", sa.String(length=32), nullable=True))
    op.add_column("ims_ipg_member", sa.Column("relation_type", sa.String(length=16), nullable=False, server_default="PRIMARY"))
    op.add_column("ims_ipg_member", sa.Column("is_leader", sa.Integer(), nullable=False, server_default="0"))

    op.add_column("ims_master_author", sa.Column("author_no", sa.String(length=32), nullable=True))
    op.add_column("ims_master_author", sa.Column("author_name", sa.String(length=64), nullable=True))
    op.add_column("ims_master_author", sa.Column("author_type", sa.String(length=32), nullable=True))
    op.add_column("ims_master_author", sa.Column("ip_group_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_author", sa.Column("user_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_author", sa.Column("primary_account_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_author", sa.Column("football_author_id", sa.BigInteger(), nullable=True))
    op.add_column("ims_master_author", sa.Column("remark", sa.String(length=255), nullable=True))
    op.execute("UPDATE ims_master_author SET author_name = name WHERE author_name IS NULL")

    op.create_table(
        "ims_ipg_anchor",
        sa.Column("ip_group_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("anchor_type", sa.String(length=32), nullable=True),
        sa.Column("is_primary", sa.Integer(), nullable=False, server_default="0"),
        *_audit(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "ip_group_id", "author_id", "deleted", name="uq_ipg_anchor"),
    )


def downgrade() -> None:
    op.drop_table("ims_ipg_anchor")
    for name in (
        "remark",
        "football_author_id",
        "primary_account_id",
        "user_id",
        "ip_group_id",
        "author_type",
        "author_name",
        "author_no",
    ):
        op.drop_column("ims_master_author", name)
    for name in ("is_leader", "relation_type", "position"):
        op.drop_column("ims_ipg_member", name)
    for name in (
        "ding_dept_id",
        "remark",
        "sort_order",
        "level",
        "leader_user_id",
        "parent_id",
        "group_type",
        "group_name",
    ):
        op.drop_column("ims_ipg_group", name)
