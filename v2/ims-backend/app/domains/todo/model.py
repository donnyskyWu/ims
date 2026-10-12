from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssocBase, AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref


class Todo(AuditBase):
    __tablename__ = "ims_sys_todo"
    __entity_label__ = "待办"
    type: Mapped[str] = mapped_column(String(32), nullable=False, info={"dict": "dict_todo_type"})
    source_module: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    route: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", info={"dict": "dict_todo_status"})
    due_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_by: Mapped[int | None] = plain_id()
    assignee_perm_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class TodoAssignee(AssocBase):
    __tablename__ = "ims_sys_todo_assignee"
    todo_id: Mapped[int] = ref_column(Ref("ims_sys_todo", "CASCADE_SOFT"), nullable=False)
    user_id: Mapped[int] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False), nullable=False)
