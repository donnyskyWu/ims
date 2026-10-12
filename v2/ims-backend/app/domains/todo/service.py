"""待办。同一来源只保留一条，按权限和部门展开处理人。"""
from __future__ import annotations

from sqlalchemy import and_, case, func, or_, select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.system.model import Menu, Role, RoleMenu, User, UserDept, UserRole
from app.domains.todo.model import Todo, TodoAssignee


def users_with_perm(perm_code: str, scope_dept_ids: list[int] | None = None) -> list[int]:
    session = get_session()
    menu_ids = list(session.scalars(select(Menu.id).where(Menu.perm_code == perm_code)))
    if not menu_ids:
        return []
    role_ids = list(session.scalars(select(RoleMenu.role_id).where(RoleMenu.menu_id.in_(menu_ids))))
    if not role_ids:
        return []
    now = now_naive()
    links = list(
        session.scalars(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0))
    )
    found: list[int] = []
    for link in links:
        if link.revoke_at is not None and link.revoke_at <= now:
            continue
        role = session.get(Role, link.role_id)
        if role is None or role.deleted or role.status != "ENABLED":
            continue
        user = session.get(User, link.user_id)
        if user is None or user.deleted or user.status != "ACTIVE":
            continue
        found.append(int(user.id))
    unique = sorted(set(found))
    if scope_dept_ids is None:
        return unique
    wanted = {int(item) for item in scope_dept_ids}
    kept = []
    for user_id in unique:
        dept_ids = set(session.scalars(select(UserDept.dept_id).where(UserDept.user_id == user_id)))
        if dept_ids & wanted:
            kept.append(user_id)
    return kept


def todo_create(
    source_type: str,
    source_id: int,
    type: str,
    title: str,
    user_ids: list[int] | None = None,
    perm_code: str | None = None,
    scope_dept_ids: list[int] | None = None,
    *,
    summary: str | None = None,
    route: str | None = None,
    due_time=None,
    source_module: str | None = None,
) -> dict:
    todo_type = type
    session = get_session()
    existing = session.scalar(
        select(Todo).where(Todo.source_type == source_type, Todo.source_id == int(source_id), Todo.type == todo_type)
    )
    if existing is not None:
        return _view(existing)
    if perm_code:
        assignees = users_with_perm(perm_code, scope_dept_ids)
    else:
        assignees = [int(item) for item in (user_ids or [])]
    if not perm_code and not assignees:
        raise BizError(1001, data={"fieldErrors": [{"field": "userIds", "message": "请指定处理人"}]})
    row = Todo(
        type=todo_type,
        source_module=source_module or _module_of(source_type),
        source_type=source_type,
        source_id=int(source_id),
        title=title or "",
        summary=summary or "",
        route=route or None,
        due_time=due_time,
        status="PENDING",
        assignee_perm_code=perm_code,
    )
    assert_dict_values(row)
    session.add(row)
    session.flush()
    for user_id in assignees:
        link = TodoAssignee(todo_id=row.id, user_id=int(user_id))
        validate_refs_on_write(link)
        session.add(link)
    session.flush()
    return _view(row)


def complete(todo_id: int, user_id: int) -> dict:
    row = _must_assignee(int(todo_id), int(user_id))
    if row.status == "DONE" and int(row.done_by or 0) == int(user_id):
        return _view(row)
    if row.status != "PENDING":
        raise BizError(1504)
    row.status = "DONE"
    row.done_by = int(user_id)
    get_session().flush()
    return _view(row)


def cancel(todo_id: int, user_id: int | None = None) -> dict:
    session = get_session()
    row = session.get(Todo, int(todo_id))
    if row is None or row.deleted:
        raise BizError(1504)
    if user_id is not None and not _is_assignee(row.id, int(user_id)):
        ctx = get_ctx()
        if not (ctx and ctx.system):
            raise BizError(1504)
    if row.status == "PENDING":
        row.status = "CANCELLED"
        session.flush()
    elif row.status != "CANCELLED":
        raise BizError(1504)
    return _view(row)


def complete_mine(todo_id: int, remark: str | None = None) -> dict:
    """本人关闭待办。非待处理返回 1296；不是处理人返回 1504。"""
    uid = _uid()
    row = _must_assignee(int(todo_id), uid)
    if row.status != "PENDING":
        raise BizError(1296)
    text = str(remark or "").strip()
    if len(text) > 200:
        raise BizError(1001, data={"fieldErrors": [{"field": "remark", "message": "备注不能超过 200 字"}]})
    if text:
        row.close_remark = text
    return complete(int(todo_id), uid)


def open_mine(todo_id: int) -> dict:
    """去处理。目标未交付只返回占位，不关闭；单据已删除返回 1297。"""
    from app.domains.workbench.routes import resolve_jump

    uid = _uid()
    row = _must_assignee(int(todo_id), uid)
    jump = resolve_jump(row.source_type, row.type, row.route)
    if jump["state"] == "missing" and row.status == "PENDING":
        raise BizError(1297)
    data = _view(row)
    data["jump"] = jump
    return data


def my_page(page: Page, status: str | None = None, *, todo_type: str | None = None, keyword: str | None = None, overdue: str | None = None) -> dict:
    from app.domains.workbench.routes import normalize_type

    uid = _uid()
    session = get_session()
    current = now_naive()
    stmt = select(Todo).join(TodoAssignee, TodoAssignee.todo_id == Todo.id).where(TodoAssignee.user_id == uid)
    raw_status = (status or "").strip().upper()
    overdue_only = raw_status in {"OVERDUE", "EXPIRED"} or str(overdue or "").strip().lower() in {"1", "true", "yes"}
    if overdue_only:
        stmt = stmt.where(Todo.status == "PENDING", Todo.due_time.is_not(None), Todo.due_time < current)
    elif raw_status and raw_status not in {"ALL"}:
        stmt = stmt.where(Todo.status == raw_status)
    kind = normalize_type(todo_type)
    if kind:
        stmt = stmt.where(Todo.type == kind)
    text = (keyword or "").strip()
    if text:
        if len(text) > 100:
            raise BizError(1001, data={"fieldErrors": [{"field": "keyword", "message": "关键词过长"}]})
        stmt = stmt.where(or_(Todo.title.contains(text), Todo.summary.contains(text)))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    overdue_rank = case((and_(Todo.status == "PENDING", Todo.due_time.is_not(None), Todo.due_time < current), 0), else_=1)
    null_due = case((Todo.due_time.is_(None), 1), else_=0)
    rows = list(
        session.scalars(
            stmt.order_by(overdue_rank.asc(), null_due.asc(), Todo.due_time.asc(), Todo.create_time.desc(), Todo.id.desc())
            .offset((page.page_no - 1) * page.page_size)
            .limit(page.page_size)
        )
    )
    return page_result([_view(row) for row in rows], int(total or 0), page)


def detail(todo_id: int) -> dict:
    uid = _uid()
    row = get_session().get(Todo, int(todo_id))
    if row is None or row.deleted or not _is_assignee(row.id, uid):
        raise BizError(1504)
    return _view(row)


def my_count() -> dict:
    uid = _uid()
    rows = list(
        get_session().scalars(
            select(Todo).join(TodoAssignee, TodoAssignee.todo_id == Todo.id).where(TodoAssignee.user_id == uid, Todo.status == "PENDING")
        )
    )
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.type] = by_type.get(row.type, 0) + 1
    return {"total": len(rows), "byType": by_type}


def _must_assignee(todo_id: int, user_id: int) -> Todo:
    session = get_session()
    row = session.get(Todo, todo_id)
    if row is None or row.deleted or not _is_assignee(row.id, user_id):
        raise BizError(1504)
    return row


def _is_assignee(todo_id: int, user_id: int) -> bool:
    link = get_session().scalar(select(TodoAssignee).where(TodoAssignee.todo_id == todo_id, TodoAssignee.user_id == user_id))
    return link is not None


def _uid() -> int:
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    return int(ctx.user_id)


def _module_of(source_type: str) -> str:
    text = source_type or ""
    if text.startswith("FLOW"):
        return "flow"
    return text.split("_")[0].lower() if text else ""


def _view(row: Todo) -> dict:
    from app.domains.workbench.routes import module_label, resolve_jump

    assignees = list(get_session().scalars(select(TodoAssignee.user_id).where(TodoAssignee.todo_id == row.id)))
    current = now_naive()
    overdue = bool(row.status == "PENDING" and row.due_time is not None and row.due_time < current)
    days = 0
    if overdue and row.due_time is not None:
        days = max(1, (current.date() - row.due_time.date()).days)
    due = row.due_time.isoformat() if row.due_time else None
    deadline_text = ""
    if row.due_time is not None:
        deadline_text = row.due_time.strftime("%Y-%m-%d %H:%M")
        if overdue:
            deadline_text = f"{deadline_text} 逾期 {days} 天"
    return {
        "id": row.id,
        "type": row.type,
        "title": row.title,
        "summary": row.summary or "",
        "status": row.status,
        "sourceType": row.source_type,
        "sourceId": row.source_id,
        "sourceModule": row.source_module,
        "sourceModuleLabel": module_label(row.source_module),
        "route": row.route or "",
        "doneBy": row.done_by,
        "assigneeIds": assignees,
        "dueTime": due,
        "deadline": due,
        "deadlineText": deadline_text,
        "overdue": overdue,
        "overdueDays": days,
        "createTime": row.create_time.isoformat() if row.create_time else None,
        "jump": resolve_jump(row.source_type, row.type, row.route),
    }
