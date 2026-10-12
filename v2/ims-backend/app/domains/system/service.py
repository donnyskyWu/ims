"""部门、用户、角色、字典、参数。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select

from app.api.dump import dump_row
from app.catalog import COLOR_TYPES, PERM_RE
from app.core.clock import now_naive
from app.core.crypto import encrypt, hmac_hash
from app.core.errors import BizError
from app.core.events import events
from app.core.pagination import Page, page_result
from app.core.security import hash_password, validate_password_policy
from app.db.repository import Repository, protect_counts
from app.db.session import get_session
from app.domains.system.model import (
    Dept,
    DictData,
    DictType,
    Menu,
    Param,
    Role,
    RoleMenu,
    RolePermDetail,
    User,
    UserDept,
    UserRole,
)
from app.services.sessions import revoke_user

_DICT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_DICT_VALUE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PERM_RE = re.compile(PERM_RE)


def init_tenant(tenant_id: int, *, root_id: int | None = None, pending_id: int | None = None) -> tuple[Dept, Dept]:
    session = get_session()
    root = Dept(id=root_id, parent_id=0, name="根部门", source="LOCAL", status="ENABLED", path="/", tenant_id=tenant_id, sort=0)
    session.add(root)
    session.flush()
    root.path = f"/{root.id}/"
    pending = Dept(
        id=pending_id,
        parent_id=root.id,
        name="待分配",
        source="SYSTEM",
        status="ENABLED",
        path="/",
        tenant_id=tenant_id,
        sort=999,
    )
    session.add(pending)
    session.flush()
    pending.path = f"{root.path}{pending.id}/"
    return root, pending


def _is_pending(dept: Dept) -> bool:
    return dept.source == "SYSTEM" and dept.name == "待分配"


def _children(dept_id: int) -> list[Dept]:
    return list(get_session().scalars(select(Dept).where(Dept.parent_id == dept_id)))


def _subtree_ids(root_id: int, rows: list[Dept]) -> set[int]:
    by_parent: dict[int, list[int]] = {}
    for row in rows:
        by_parent.setdefault(int(row.parent_id or 0), []).append(row.id)
    found = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(by_parent.get(current, []))
    return found


def dept_tree(keyword: str | None = None, status: str | None = None) -> list[dict]:
    session = get_session()
    rows = list(session.scalars(select(Dept)))
    show_disabled = (status or "").upper() == "ALL"
    if not show_disabled:
        rows = [row for row in rows if row.status != "DISABLED"]
    memberships = list(
        session.execute(
            select(UserDept.dept_id, UserDept.user_id, User.status).join(User, User.id == UserDept.user_id)
        )
    )
    active = {(dept_id, user_id) for dept_id, user_id, ustatus in memberships if ustatus in {"ACTIVE", "FROZEN"}}
    by_id = {row.id: row for row in rows}
    if keyword:
        matched = {row.id for row in rows if keyword in row.name}
        keep = set()
        for ident in matched:
            cursor = ident
            while cursor and cursor in by_id and cursor not in keep:
                keep.add(cursor)
                cursor = int(by_id[cursor].parent_id or 0)
        rows = [row for row in rows if row.id in keep]
        by_id = {row.id: row for row in rows}
    direct: dict[int, set[int]] = {}
    for dept_id, user_id in active:
        if dept_id in by_id:
            direct.setdefault(dept_id, set()).add(user_id)
    by_parent: dict[int, list[Dept]] = {}
    child_ids: dict[int, list[int]] = {}
    for row in rows:
        parent_id = int(row.parent_id or 0)
        by_parent.setdefault(parent_id, []).append(row)
        child_ids.setdefault(parent_id, []).append(row.id)
    memo: dict[int, set[int]] = {}

    def users_under(dept_id: int, seen: set[int] | None = None) -> set[int]:
        cached = memo.get(dept_id)
        if cached is not None:
            return cached
        seen = seen or set()
        if dept_id in seen:
            return set()
        seen.add(dept_id)
        found = set(direct.get(dept_id, ()))
        for child_id in child_ids.get(dept_id, []):
            found |= users_under(child_id, seen)
        memo[dept_id] = found
        return found

    def node(row: Dept) -> dict:
        data = dump_row(row, ["id", "parent_id", "name", "source", "status", "path", "sort", "leader_user_id", "dingtalk_dept_id", "local_orphan"])
        data["memberCount"] = len(users_under(row.id))
        data["directMemberCount"] = len(direct.get(row.id, set()))
        data["children"] = [node(child) for child in sorted(by_parent.get(row.id, []), key=lambda item: (item.sort, item.id))]
        return data

    roots = [row for row in rows if int(row.parent_id or 0) not in by_id]
    return [node(row) for row in sorted(roots, key=lambda item: (item.sort, item.id))]


def dept_create(name: str, parent_id: int, source: str = "LOCAL") -> dict:
    session = get_session()
    parent = session.get(Dept, parent_id)
    if parent is None:
        raise BizError(1500, data={"field": "parentId"})
    if _is_pending(parent):
        raise BizError(1220)
    if parent.status != "ENABLED":
        raise BizError(1501)
    if source != "LOCAL":
        raise BizError(1001, data={"fieldErrors": [{"field": "source", "message": "手工新建的部门来源只能是本地"}]})
    sibling = session.scalar(select(Dept).where(Dept.parent_id == parent_id, Dept.name == name))
    if sibling:
        raise BizError(1219)
    row = Dept(parent_id=parent_id, name=name, source="LOCAL", status="ENABLED", path="/", dingtalk_dept_id=None)
    session.add(row)
    session.flush()
    row.path = f"{parent.path}{row.id}/"
    return {**dump_row(row), "syncOverrideHint": False}


def dept_update(ident: int, name: str | None = None, leader_user_id: int | None = None, sort: int | None = None) -> dict:
    row = get_session().get(Dept, ident)
    if row is None:
        raise BizError(1504)
    if _is_pending(row) and name and name != row.name:
        raise BizError(1220)
    if name and name != row.name:
        sibling = get_session().scalar(select(Dept).where(Dept.parent_id == row.parent_id, Dept.name == name, Dept.id != row.id))
        if sibling:
            raise BizError(1219)
        row.name = name
    if leader_user_id is not None:
        row.leader_user_id = leader_user_id
    if sort is not None:
        row.sort = sort
    hint = row.source == "DINGTALK" and name is not None
    return {**dump_row(row), "syncOverrideHint": hint}


def dept_move(ident: int, parent_id: int) -> dict:
    session = get_session()
    row = session.get(Dept, ident)
    parent = session.get(Dept, parent_id)
    if row is None or parent is None:
        raise BizError(1504)
    if _is_pending(row):
        raise BizError(1220)
    if parent.path.startswith(row.path) or parent.id == row.id:
        raise BizError(1218)
    if row.source == "DINGTALK" and parent.source == "LOCAL":
        raise BizError(1220)
    sibling = session.scalar(select(Dept).where(Dept.parent_id == parent_id, Dept.name == row.name, Dept.id != row.id))
    if sibling:
        raise BizError(1219)
    row.parent_id = parent_id
    _rewrite_paths(row, parent.path)
    return dump_row(row)


def _rewrite_paths(row: Dept, parent_path: str) -> None:
    session = get_session()
    old = row.path
    row.path = f"{parent_path}{row.id}/"
    children = list(session.scalars(select(Dept).where(Dept.path.like(old + "%"), Dept.id != row.id)))
    for child in children:
        suffix = child.path[len(old) :]
        child.path = row.path + suffix


def dept_status(ident: int, status: str) -> dict:
    row = get_session().get(Dept, ident)
    if row is None:
        raise BizError(1504)
    if _is_pending(row):
        raise BizError(1220)
    if status == "DISABLED":
        enabled_children = get_session().scalar(
            select(func.count()).select_from(Dept).where(Dept.parent_id == ident, Dept.status == "ENABLED")
        )
        if int(enabled_children or 0) > 0:
            raise BizError(1502, data={"refs": [{"entity": "下级部门", "count": int(enabled_children)}]})
    row.status = status
    return dump_row(row)


def dept_delete(ident: int) -> dict:
    session = get_session()
    row = session.get(Dept, ident)
    if row is None:
        raise BizError(1504)
    if _is_pending(row):
        raise BizError(1220)
    child_count = int(session.scalar(select(func.count()).select_from(Dept).where(Dept.parent_id == ident)) or 0)
    people = int(session.scalar(select(func.count()).select_from(UserDept).where(UserDept.dept_id == ident)) or 0)
    refs = []
    if child_count:
        refs.append({"entity": "下级部门", "count": child_count})
    if people:
        refs.append({"entity": "人员", "count": people})
    if refs:
        raise BizError(1502, data={"refs": refs})
    row.deleted = row.id
    return {}


def confirm_orphan(ident: int) -> dict:
    from app.domains.todo.model import Todo

    row = get_session().get(Dept, ident)
    if row is None:
        raise BizError(1504)
    row.local_orphan = 0
    todos = list(get_session().scalars(select(Todo).where(Todo.source_type == "DEPT_ORPHAN", Todo.source_id == ident, Todo.status == "PENDING")))
    for todo in todos:
        todo.status = "DONE"
    return dump_row(row)


def user_page(page: Page, dept_id: int | None, include_children: bool, keyword: str | None, status: str | None) -> dict:
    session = get_session()
    repo = Repository(User)
    where = []
    if status:
        where.append(User.status == status)
    if keyword:
        where.append(or_(User.username.contains(keyword), User.nickname.contains(keyword), User.emp_no.contains(keyword)))
    if dept_id:
        rows = list(session.scalars(select(Dept)))
        ids = _subtree_ids(dept_id, rows) if include_children else {dept_id}
        where.append(User.id.in_(select(UserDept.user_id).where(UserDept.dept_id.in_(ids))))
    order = [User.id.desc()]
    items, total = repo.page(page, *where, order=order)
    data = [dump_row(item, ["id", "username", "nickname", "emp_no", "status", "main_dept_id", "position_code"]) for item in items]
    return page_result(data, total, page)


def user_simple(page: Page) -> dict:
    """选人组件：登录即可，不套数据范围，只露出 id、姓名、主部门、状态。"""
    session = get_session()
    stmt = select(User).order_by(User.id.desc())
    total = session.scalar(select(func.count()).select_from(User))
    rows = list(session.scalars(stmt.offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    data = [{"id": item.id, "nickname": item.nickname, "mainDeptId": item.main_dept_id, "status": item.status} for item in rows]
    return page_result(data, int(total or 0), page)


def _ensure_depts(dept_ids: list[int]) -> None:
    session = get_session()
    for ident in dept_ids:
        dept = session.get(Dept, ident)
        if dept is None or dept.deleted:
            raise BizError(1500, data={"field": "deptIds"})
        if dept.status != "ENABLED":
            raise BizError(1501, data={"field": "deptIds"})


def user_create(username: str, nickname: str, dept_ids: list[int], main_dept_id: int, password: str, mobile: str | None = None, emp_no: str | None = None, position_code: str | None = None) -> dict:
    policy = validate_password_policy(password)
    if policy:
        raise BizError(1001, data={"fieldErrors": [{"field": "password", "message": policy}]})
    if main_dept_id not in dept_ids:
        dept_ids = list(dept_ids) + [main_dept_id]
    _ensure_depts(dept_ids)
    session = get_session()
    user = User(
        username=username,
        nickname=nickname,
        password_hash=hash_password(password),
        status="ACTIVE",
        main_dept_id=main_dept_id,
        emp_no=emp_no,
        position_code=position_code,
        source="LOCAL",
    )
    if mobile:
        user.mobile_enc = encrypt(mobile)
        user.mobile_hash = hmac_hash(mobile)
    Repository(User).create(user)
    for ident in dept_ids:
        session.add(UserDept(user_id=user.id, dept_id=ident, is_main=1 if ident == main_dept_id else 0, source="LOCAL"))
    session.flush()
    return dump_row(user, ["id", "username", "nickname", "status", "main_dept_id"])


def update_depts(user_id: int, dept_ids: list[int], main_dept_id: int | None) -> dict:
    session = get_session()
    user = session.get(User, user_id)
    if user is None:
        raise BizError(1504)
    current = list(session.scalars(select(UserDept).where(UserDept.user_id == user_id)))
    current_ids = {row.dept_id for row in current}
    if not dept_ids:
        pending = session.scalar(select(Dept).where(Dept.source == "SYSTEM", Dept.name == "待分配"))
        if pending is None:
            raise BizError(1001, "没有待分配部门")
        dept_ids = [pending.id]
        main_dept_id = pending.id
    if main_dept_id is None:
        raise BizError(1001, "请先指定其他主部门")
    if main_dept_id not in dept_ids:
        raise BizError(1001, data={"fieldErrors": [{"field": "mainDeptId", "message": "主部门必须在所属部门中"}]})
    adding = [ident for ident in dept_ids if ident not in current_ids]
    _ensure_depts(adding)
    for row in current:
        if row.dept_id not in dept_ids:
            session.delete(row)
    for ident in dept_ids:
        existing = next((row for row in current if row.dept_id == ident), None)
        if existing:
            existing.is_main = 1 if ident == main_dept_id else 0
        else:
            session.add(UserDept(user_id=user_id, dept_id=ident, is_main=1 if ident == main_dept_id else 0, source="LOCAL"))
    user.main_dept_id = main_dept_id
    session.flush()
    return {"id": user.id, "mainDeptId": main_dept_id, "deptIds": dept_ids}


def user_update(path_id: int, body_id: int | None, values: dict) -> dict:
    if body_id is not None and int(body_id) != int(path_id):
        raise BizError(1211)
    user = get_session().get(User, path_id)
    if user is None:
        raise BizError(1504)
    for key in ("nickname", "emp_no", "email", "position_code", "avatar"):
        if key in values and values[key] is not None:
            setattr(user, key, values[key])
    Repository(User).update(user)
    return dump_row(user, ["id", "username", "nickname", "emp_no", "position_code", "status"])


def user_delete(ident: int) -> dict:
    user = get_session().get(User, ident)
    if user is None:
        raise BizError(1504)
    if user.status == "RESIGNED":
        raise BizError(1502, data={"refs": [{"entity": "离职用户", "count": 1}]})
    refs = protect_counts(user)
    if refs:
        raise BizError(1502, data={"refs": refs})
    user.deleted = user.id
    return {}


def user_status(ident: int, status: str) -> dict:
    user = get_session().get(User, ident)
    if user is None:
        raise BizError(1504)
    if user.status == "RESIGNED" and status == "ACTIVE":
        raise BizError(1001, "离职用户不能恢复为在职")
    if status == "RESIGNED" and user.status != "RESIGNED":
        user.status = "RESIGNED"
        revoke_user(user.id)
        events.publish("user.resigned", {"userId": user.id})
    elif status == "FROZEN":
        user.status = "FROZEN"
        revoke_user(user.id)
    else:
        user.status = status
    return dump_row(user, ["id", "status"])


def role_create(name: str, role_key: str, source: str = "MANUAL", data_scope: str | None = None, position_code: str | None = None) -> dict:
    if source not in {"MANUAL", "DINGTALK_AUTO"}:
        raise BizError(1503)
    session = get_session()
    if position_code:
        taken = session.scalar(select(Role).where(Role.position_code == position_code, Role.deleted == 0))
        if taken is not None:
            raise BizError(1001, data={"fieldErrors": [{"field": "positionCode", "message": "该岗位已绑定其他角色"}]})
    standards = list(session.scalars(select(Role).where(Role.is_standard == 1)))
    for item in standards:
        if item.role_key == role_key or item.name == name:
            raise BizError(1001, data={"fieldErrors": [{"field": "roleKey", "message": "不能与标准角色重名"}]})
    row = Role(name=name, role_key=role_key, source=source, data_scope=data_scope, position_code=position_code, status="ENABLED" if source == "MANUAL" else "PENDING_CONFIG")
    Repository(Role).create(row)
    return dump_row(row)


def role_delete(ident: int) -> dict:
    session = get_session()
    role = session.get(Role, ident)
    if role is None:
        raise BizError(1504)
    if role.is_standard:
        raise BizError(1502, data={"refs": [{"entity": "标准角色", "count": 1}]})
    members = int(session.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id == ident, UserRole.manual_removed == 0)) or 0)
    if members:
        raise BizError(1502, data={"refs": [{"entity": "成员", "count": members}]})
    refs = protect_counts(role)
    if refs:
        raise BizError(1502, data={"refs": refs})
    role.deleted = role.id
    return {}


def role_status(ident: int, status: str) -> dict:
    role = get_session().get(Role, ident)
    if role is None:
        raise BizError(1504)
    role.status = status
    return dump_row(role, ["id", "status", "name"])


def role_grant(role_id: int, perm_codes: list[str], details: list[dict] | None = None) -> dict:
    session = get_session()
    role = session.get(Role, role_id)
    if role is None:
        raise BizError(1504)
    menus = {menu.perm_code: menu for menu in session.scalars(select(Menu)) if menu.perm_code}
    for code in perm_codes:
        if code not in menus:
            raise BizError(1212)
    session.execute(RoleMenu.__table__.delete().where(RoleMenu.role_id == role_id))
    session.execute(RolePermDetail.__table__.delete().where(RolePermDetail.role_id == role_id))
    for code in perm_codes:
        session.add(RoleMenu(role_id=role_id, menu_id=menus[code].id))
    for item in details or []:
        read = int(item.get("r") or 0)
        write = int(item.get("w") or 0)
        delete = int(item.get("d") or 0)
        if write or delete:
            read = 1
        code = item["permCode"]
        if code not in menus:
            raise BizError(1212)
        session.add(RolePermDetail(role_id=role_id, perm_code=code, r=read, w=write, d=delete))
        if menus[code].id:
            exists = session.scalar(select(RoleMenu).where(RoleMenu.role_id == role_id, RoleMenu.menu_id == menus[code].id))
            if exists is None:
                session.add(RoleMenu(role_id=role_id, menu_id=menus[code].id))
    session.flush()
    saved = list(session.scalars(select(RolePermDetail).where(RolePermDetail.role_id == role_id)))
    return {"details": [{"permCode": row.perm_code, "r": row.r, "w": row.w, "d": row.d} for row in saved]}


def role_simple() -> list[dict]:
    rows = get_session().scalars(select(Role).where(Role.status == "ENABLED"))
    return [{"id": row.id, "name": row.name, "source": row.source} for row in rows]


def menu_create(name: str, type_: str, perm_code: str | None, parent_id: int = 0) -> dict:
    if type_ in {"MENU", "BUTTON"} and not perm_code:
        raise BizError(1001, data={"fieldErrors": [{"field": "permCode", "message": "菜单权限码不能为空"}]})
    if perm_code and not _PERM_RE.match(perm_code):
        raise BizError(1001, data={"fieldErrors": [{"field": "permCode", "message": "权限码格式不正确"}]})
    row = Menu(name=name, type=type_, perm_code=perm_code, parent_id=parent_id, status="ENABLED")
    Repository(Menu).create(row)
    return dump_row(row)


def dict_type_create(dict_type: str, name: str) -> dict:
    if not _DICT_TYPE_RE.match(dict_type):
        raise BizError(1001, data={"fieldErrors": [{"field": "dictType", "message": "字典类型格式不正确"}]})
    row = DictType(dict_type=dict_type, name=name, status="ENABLED")
    Repository(DictType).create(row)
    return dump_row(row)


def dict_data_create(dict_type: str, dict_value: str, dict_label: str, color_type: str = "neutral") -> dict:
    if not _DICT_VALUE_RE.match(dict_value):
        raise BizError(1001, data={"fieldErrors": [{"field": "dictValue", "message": "字典值格式不正确"}]})
    if color_type not in COLOR_TYPES:
        raise BizError(1001, data={"fieldErrors": [{"field": "colorType", "message": "颜色类型不在允许范围内"}]})
    if get_session().scalar(select(DictType).where(DictType.dict_type == dict_type)) is None:
        raise BizError(1503)
    row = DictData(dict_type=dict_type, dict_value=dict_value, dict_label=dict_label, color_type=color_type, status="ENABLED", is_builtin=0, source="LOCAL")
    Repository(DictData).create(row)
    cache.invalidate(dict_type)
    return dump_row(row)


def dict_data_update(ident: int, dict_value: str | None = None, dict_label: str | None = None, color_type: str | None = None, status: str | None = None) -> dict:
    row = get_session().get(DictData, ident)
    if row is None:
        raise BizError(1504)
    if dict_value and dict_value != row.dict_value:
        if row.is_builtin:
            raise BizError(1001, "内置字典值不能修改")
        if not _DICT_VALUE_RE.match(dict_value):
            raise BizError(1001, data={"fieldErrors": [{"field": "dictValue", "message": "字典值格式不正确"}]})
        row.dict_value = dict_value
    if color_type:
        if color_type not in COLOR_TYPES:
            raise BizError(1001, data={"fieldErrors": [{"field": "colorType", "message": "颜色类型不在允许范围内"}]})
        row.color_type = color_type
    if dict_label:
        row.dict_label = dict_label
    if status:
        row.status = status
    cache.invalidate(row.dict_type)
    return dump_row(row)


def dict_data_delete(ident: int) -> dict:
    row = get_session().get(DictData, ident)
    if row is None:
        raise BizError(1504)
    if row.status != "ENABLED":
        raise BizError(1502, data={"refs": [{"entity": "字典值", "count": 1}]})
    if _dict_value_used(row.dict_type, row.dict_value):
        raise BizError(1502, data={"refs": [{"entity": "业务数据", "count": 1}]})
    row.deleted = row.id
    cache.invalidate(row.dict_type)
    return {}


def _dict_value_used(dict_type: str, dict_value: str) -> bool:
    from app.domains import all_models

    session = get_session()
    for model in all_models():
        for column in model.__table__.columns:
            if (column.info or {}).get("dict") != dict_type:
                continue
            count = session.scalar(select(func.count()).select_from(model).where(column == dict_value).execution_options(skip_tenant=True))
            if int(count or 0) > 0:
                return True
    return False


def param_list() -> list[dict]:
    rows = list(get_session().scalars(select(Param)))
    data = []
    for row in rows:
        item = dump_row(row, ["id", "param_key", "name", "value_type", "value", "group_name"])
        if row.value_type == "SECRET":
            item["value"] = "******"
        data.append(item)
    return data


def param_update(param_key: str, value: str | None) -> dict:
    row = get_session().scalar(select(Param).where(Param.param_key == param_key))
    if row is None:
        raise BizError(1213)
    if row.value_type == "SECRET" and (value is None or value == ""):
        return {"paramKey": param_key, "value": "******"}
    if row.value_type == "NUMBER":
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise BizError(1001, data={"fieldErrors": [{"field": "value", "message": "须为数字"}]})
        lo = float(row.min_value) if row.min_value not in (None, "") else None
        hi = float(row.max_value) if row.max_value not in (None, "") else None
        if (lo is not None and number < lo) or (hi is not None and number > hi):
            raise BizError(1001, data={"fieldErrors": [{"field": "value", "message": "超出允许范围"}]})
    if row.value_type == "ROLE_REF" and value:
        role = get_session().get(Role, int(value))
        if role is None or role.deleted:
            raise BizError(1500, data={"field": "value"})
    if row.value_type == "SECRET" and value:
        row.value = encrypt(value)
    else:
        row.value = value
    return {"paramKey": param_key, "value": "******" if row.value_type == "SECRET" else row.value}


class DictCache:
    def __init__(self):
        self.local: dict[str, tuple[datetime, dict]] = {}

    def get_label(self, dict_type: str, value: str) -> str | None:
        mapping = self.get_map(dict_type)
        return mapping.get(value)

    def get_map(self, dict_type: str) -> dict:
        item = self.local.get(dict_type)
        if item is not None and now_naive() - item[0] < timedelta(seconds=60):
            return item[1]
        rows = get_session().scalars(select(DictData).where(DictData.dict_type == dict_type, DictData.status == "ENABLED"))
        mapping = {row.dict_value: row.dict_label for row in rows}
        self.local[dict_type] = (now_naive(), mapping)
        return mapping

    def invalidate(self, dict_type: str) -> None:
        self.local.pop(dict_type, None)


cache = DictCache()
other_cache = DictCache()
