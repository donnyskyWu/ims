"""工作台 E2E closure 种子：admin 待办关闭 + 未读消息（幂等）。"""

from datetime import timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core import utcnow
from app.models import Todo, User, WorkMessage

E2E_WB_TODO_TITLE = "E2E-WB-CLOSE"
E2E_WB_MSG_TITLE = "E2E-WB-MSG"


def _upsert_workbench_e2e_rows(db: Session, user: User, *, fresh: bool) -> None:
    now = utcnow()
    todo = db.scalar(
        select(Todo).where(
            Todo.assignee_user_id == user.id,
            Todo.title == E2E_WB_TODO_TITLE,
        )
    )
    msg = db.scalar(
        select(WorkMessage).where(
            WorkMessage.user_id == user.id,
            WorkMessage.title == E2E_WB_MSG_TITLE,
        )
    )
    if todo is None:
        db.add(
            Todo(
                assignee_user_id=user.id,
                task_type="WORKBENCH_E2E",
                title=E2E_WB_TODO_TITLE,
                content="Playwright closure：关闭后应从预览消失",
                status="PENDING",
                deadline=now + timedelta(days=7),
                tenant_id=0,
            )
        )
    elif fresh:
        todo.status = "PENDING"
        todo.deadline = now + timedelta(days=7)

    if msg is None:
        db.add(
            WorkMessage(
                user_id=user.id,
                title=E2E_WB_MSG_TITLE,
                content="Playwright closure：标为已读后未读数减 1",
                channel="IN_APP",
                read_flag=0,
                source_module="E2E",
                tenant_id=0,
            )
        )
    elif fresh:
        msg.read_flag = 0


def ensure_workbench_e2e_seed(db: Session, user: User) -> None:
    if user.username != "admin":
        return
    _upsert_workbench_e2e_rows(db, user, fresh=False)


def refresh_workbench_e2e_seed(db: Session, user: User) -> None:
    """API init / 启动时恢复 E2E closure 种子（勿在 dashboard 调用）。"""
    if user.username != "admin":
        return
    _upsert_workbench_e2e_rows(db, user, fresh=True)


def prune_closure_alert_inbox(db: Session) -> None:
    """全量 E2E 开跑前清掉 closure 留下的证件、账实、离职待办和消息。

    工作台预览各取 20 条。这些行按 id 或逾期排在种子前面，重复跑全量后会把
    E2E-WB-MSG / E2E-WB-CLOSE 挤出第一页。只给 E2E 刷新脚本调用，不进 API 启动 seed()。
    """
    title_is_closure_alert = (
        lambda column: or_(
            column.like("证件%"),
            column.like("账实核对%"),
            column.like("离职待归还%"),
        )
    )
    db.execute(delete(WorkMessage).where(title_is_closure_alert(WorkMessage.title)))
    db.execute(delete(Todo).where(title_is_closure_alert(Todo.title)))
