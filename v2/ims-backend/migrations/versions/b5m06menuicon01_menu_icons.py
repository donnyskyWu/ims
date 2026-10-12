"""fill empty menu icons

Revision ID: b5m06menuicon01
Revises: b5m05a1b2c3d4
Create Date: 2026-10-12 16:20:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.menu_icons import NAME_ICONS, PATH_ICONS

revision: str = "b5m06menuicon01"
down_revision: Union[str, None] = "b5m05a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for path, icon in PATH_ICONS.items():
        conn.execute(
            sa.text("UPDATE ims_sys_menu SET icon = :icon WHERE icon IS NULL AND path = :path"),
            {"icon": icon, "path": path},
        )
    for name, icon in NAME_ICONS.items():
        conn.execute(
            sa.text("UPDATE ims_sys_menu SET icon = :icon WHERE icon IS NULL AND name = :name AND (path IS NULL OR path = '')"),
            {"icon": icon, "name": name},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for path, icon in PATH_ICONS.items():
        conn.execute(
            sa.text("UPDATE ims_sys_menu SET icon = NULL WHERE path = :path AND icon = :icon"),
            {"icon": icon, "path": path},
        )
    for name, icon in NAME_ICONS.items():
        conn.execute(
            sa.text("UPDATE ims_sys_menu SET icon = NULL WHERE name = :name AND icon = :icon AND (path IS NULL OR path = '')"),
            {"icon": icon, "name": name},
        )
