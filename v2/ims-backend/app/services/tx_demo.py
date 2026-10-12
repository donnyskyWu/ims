"""事务边界示例，供单测验证整体回滚与嵌套复用。"""
from __future__ import annotations

from app.core.fault import faults
from app.db.session import get_session, transactional
from app.domains.demo.model import DemoNote, DemoOrder


@transactional
def write_two(name: str = "tx") -> None:
    session = get_session()
    session.add(DemoOrder(name=name, code=f"TX-{name}", status="ACTIVE"))
    session.flush()
    faults.raise_if("tx.second")
    session.add(DemoNote(content=name))
    session.flush()


@transactional
def _inner() -> None:
    faults.raise_if("tx.inner")
    get_session().add(DemoNote(content="inner"))
    get_session().flush()


@transactional
def outer_swallows(name: str = "outer") -> None:
    session = get_session()
    session.add(DemoOrder(name=name, code=f"OUT-{name}", status="ACTIVE"))
    session.flush()
    try:
        _inner()
    except Exception:
        session.add(DemoNote(content="after-catch"))
        session.flush()
