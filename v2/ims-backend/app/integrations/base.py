"""外部集成公共约束。第二数据源只允许读取。"""
from __future__ import annotations

from sqlalchemy import create_engine, event


class SelectOnlyError(RuntimeError):
    """只读连接拒绝了非 SELECT 语句。"""


# 只读拦截器记下的语句。测试用来证明读仓储只发出 SELECT。
STATEMENTS: list[str] = []


def reject_non_select(statement: str | None) -> None:
    if statement is None or not statement.strip().upper().startswith("SELECT"):
        raise SelectOnlyError("只允许 SELECT")


def install_select_only(engine) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def _guard(conn, cursor, statement, parameters, context, executemany):
        if statement:
            STATEMENTS.append(statement)
        reject_non_select(statement)


def open_select_engine(url: str):
    engine = create_engine(url, pool_pre_ping=True, future=True)
    install_select_only(engine)
    return engine
