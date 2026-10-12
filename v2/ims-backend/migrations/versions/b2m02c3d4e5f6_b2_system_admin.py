"""b2 system admin fields

Revision ID: b2m02c3d4e5f6
Revises: b1m01a1b2c3d4
Create Date: 2026-10-12 18:40:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2m02c3d4e5f6"
down_revision: Union[str, None] = "b1m01a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ims_sys_tenant", sa.Column("contact_name", sa.String(length=50), nullable=True))
    op.add_column("ims_sys_tenant_package", sa.Column("remark", sa.String(length=255), nullable=True))
    op.add_column("ims_sys_menu", sa.Column("keep_alive", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("ims_sys_menu", "keep_alive")
    op.drop_column("ims_sys_tenant_package", "remark")
    op.drop_column("ims_sys_tenant", "contact_name")
