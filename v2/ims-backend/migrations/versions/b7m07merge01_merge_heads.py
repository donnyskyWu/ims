"""merge menu-icon head and device head

Revision ID: b7m07merge01
Revises: b5m06menuicon01, b6m06a1b2c3d4
Create Date: 2026-10-13 08:00:00
"""
from typing import Sequence, Union

revision: str = "b7m07merge01"
down_revision: Union[str, Sequence[str], None] = ("b5m06menuicon01", "b6m06a1b2c3d4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
