"""b3 workbench display fields

Revision ID: b3m03a7c3d4e5
Revises: b2m02c3d4e5f6
Create Date: 2026-10-12 12:10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b3m03a7c3d4e5"
down_revision: Union[str, None] = "b2m02c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ims_sys_todo", sa.Column("summary", sa.String(length=500), nullable=True))
    op.add_column("ims_sys_todo", sa.Column("close_remark", sa.String(length=200), nullable=True))
    op.add_column("ims_sys_message", sa.Column("source_module", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("ims_sys_message", "source_module")
    op.drop_column("ims_sys_todo", "close_remark")
    op.drop_column("ims_sys_todo", "summary")
