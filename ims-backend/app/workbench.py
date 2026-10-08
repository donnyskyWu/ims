"""个人工作台。已登录即可，只返回本人待办和消息。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import tenant_of
from app.flow import seed_flow, sync_seed_tasks
from app.models import FlowInstance, FlowTask, Todo, User, WorkMessage

router = APIRouter()


class TodoBody(BaseModel):
    action: str
    remark: str | None = None


def clamp_page(page_no: int, page_size: int) -> tuple[int, int]:
    page_no = page_no if page_no > 0 else 1
    page_size = page_size if 0 < page_size <= 100 else 10
    return page_no, page_size


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def overdue(todo: Todo, now: datetime) -> bool:
    return bool(todo.deadline and todo.status == "PENDING" and todo.deadline < now)


def todo_vo(todo: Todo, now: datetime) -> dict:
    return {
        "id": todo.id,
        "taskType": todo.task_type,
        "refType": todo.ref_type,
        "refId": todo.ref_id,
        "title": todo.title,
        "content": todo.content,
        "status": todo.status,
        "deadline": iso(todo.deadline),
        "createdAt": iso(todo.created_at),
        "overdue": overdue(todo, now),
    }


def flow_pending_count(db: Session, user: User) -> int:
    tenant_id = tenant_of(user)
    seed_flow(db, tenant_id, user.id)
    sync_seed_tasks(db, tenant_id, user.id)
    return int(
        db.scalar(
            select(func.count())
            .select_from(FlowTask)
            .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
            .where(
                FlowTask.deleted == 0,
                FlowTask.tenant_id == tenant_id,
                FlowTask.assignee_user_id == user.id,
                FlowTask.task_status == "PENDING",
                FlowInstance.deleted == 0,
            )
        )
        or 0
    )


def message_vo(row: WorkMessage) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "channel": row.channel,
        "read": bool(row.read_flag),
        "sourceModule": row.source_module,
        "refType": row.ref_type,
        "refId": row.ref_id,
        "createdAt": iso(row.created_at),
    }


@router.get("/auth/workbench/dashboard")
def dashboard(db: Session = Depends(db_session), user: User = Depends(current_user)):
    todo_count = db.scalar(
        select(func.count()).select_from(Todo).where(Todo.assignee_user_id == user.id, Todo.status == "PENDING")
    ) or 0
    unread = db.scalar(
        select(func.count()).select_from(WorkMessage).where(WorkMessage.user_id == user.id, WorkMessage.read_flag == 0)
    ) or 0
    flow_todo = flow_pending_count(db, user)
    return ok(
        {
            "todoCount": todo_count,
            "flowTodoCount": flow_todo,
            "unreadMessageCount": unread,
            "myAccountCount": 0,
            "myAssetCount": 0,
            "myCertCount": 0,
            "myLiveSessionCount": 0,
        }
    )


@router.get("/auth/workbench/todos")
def todos(
    pageNo: int = 1,
    pageSize: int = 10,
    taskType: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    page_no, size = clamp_page(pageNo, pageSize)
    now = utcnow()
    stmt = select(Todo).where(Todo.assignee_user_id == user.id)
    if taskType:
        stmt = stmt.where(Todo.task_type == taskType)
    if status:
        stmt = stmt.where(Todo.status == status)
    rows = list(db.scalars(stmt).all())
    rows.sort(key=lambda row: (0 if overdue(row, now) else 1, row.deadline or datetime.max, row.id))
    start = (page_no - 1) * size
    page = rows[start : start + size]
    return ok({"list": [todo_vo(row, now) for row in page], "total": len(rows), "pageNo": page_no, "pageSize": size})


@router.put("/auth/workbench/todos/{todo_id}")
def close_todo(todo_id: int, body: TodoBody, db: Session = Depends(db_session), user: User = Depends(current_user)):
    if body.action not in ("DONE", "CLOSE"):
        return fail(1001, "动作不合法")
    todo = db.get(Todo, todo_id)
    if todo is None or todo.assignee_user_id != user.id:
        return fail(1504, "资源不可用")
    todo.status = "DONE"
    if body.remark:
        todo.content = body.remark[:512]
    return ok(None)


@router.get("/auth/workbench/messages")
def messages(
    pageNo: int = 1,
    pageSize: int = 10,
    read: bool | None = None,
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    page_no, size = clamp_page(pageNo, pageSize)
    stmt = select(WorkMessage).where(WorkMessage.user_id == user.id)
    if read is not None:
        stmt = stmt.where(WorkMessage.read_flag == (1 if read else 0))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(WorkMessage.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return ok({"list": [message_vo(row) for row in rows], "total": total, "pageNo": page_no, "pageSize": size})


@router.put("/auth/workbench/messages/read-all")
def read_all(db: Session = Depends(db_session), user: User = Depends(current_user)):
    rows = db.scalars(select(WorkMessage).where(WorkMessage.user_id == user.id, WorkMessage.read_flag == 0)).all()
    for row in rows:
        row.read_flag = 1
    return ok({"updated": len(rows)})


@router.put("/auth/workbench/messages/{message_id}/read")
def read_message(message_id: int, db: Session = Depends(db_session), user: User = Depends(current_user)):
    row = db.get(WorkMessage, message_id)
    if row is None or row.user_id != user.id:
        return fail(1504, "资源不可用")
    row.read_flag = 1
    return ok(None)
