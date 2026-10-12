"""岗位-角色供给规则页。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import page_result, parse_page
from app.db.session import get_session
from app.domains.auth.model import PositionRoleRule, PositionRuleRole, PositionRuleVersion
from app.domains.system.model import Dept, DictData, Menu, Role, RoleMenu, User, UserRole
from app.services.position import _replace_role_rows, _write_version


def overview() -> dict:
    session = get_session()
    positions = list(session.scalars(select(DictData).where(DictData.dict_type == "dict_position", DictData.status == "ENABLED")))
    ding = sum(1 for row in positions if row.source == "DINGTALK")
    local = sum(1 for row in positions if row.source != "DINGTALK")
    enabled_rules = int(
        session.scalar(
            select(func.count()).select_from(PositionRoleRule).where(PositionRoleRule.status == "ENABLED", PositionRoleRule.archived == 0)
        )
        or 0
    )
    pending_roles = {
        row.role_id
        for row in session.scalars(select(PositionRuleRole))
        if (role := session.get(Role, row.role_id)) is not None and role.status == "PENDING_CONFIG"
    }
    occupied = set(
        session.scalars(select(User.position_code).where(User.status.in_(("ACTIVE", "FROZEN")), User.position_code.is_not(None)))
    )
    empty = sum(1 for row in positions if row.dict_value not in occupied)
    return {
        "positionCount": len(positions),
        "dingtalkCount": ding,
        "localCount": local,
        "enabledRuleCount": enabled_rules,
        "pendingRoleCount": len(pending_roles),
        "emptyPositionCount": empty,
    }


def rule_page(params: dict) -> dict:
    page = parse_page(params)
    stmt = select(PositionRoleRule)
    status = str(params.get("status") or "")
    if status == "ARCHIVED":
        stmt = stmt.where(PositionRoleRule.archived == 1)
    elif status in {"ENABLED", "DISABLED"}:
        stmt = stmt.where(PositionRoleRule.status == status, PositionRoleRule.archived == 0)
    else:
        stmt = stmt.where(PositionRoleRule.archived == 0)
    keyword = str(params.get("keyword") or params.get("ruleName") or "").strip()
    if keyword:
        stmt = stmt.where(PositionRoleRule.rule_name.contains(keyword))
    if params.get("positionCode"):
        stmt = stmt.where(PositionRoleRule.position_code == params.get("positionCode"))
    session = get_session()
    rows = list(session.scalars(stmt.order_by(PositionRoleRule.update_time.desc(), PositionRoleRule.id.desc())))
    role_id = _int_or_none(params.get("roleId"))
    if role_id:
        rows = [row for row in rows if row.role_id == role_id or role_id in _extra_ids(row.id)]
    if str(params.get("pendingConfig") or "") in {"1", "true", "True"}:
        rows = [row for row in rows if _has_pending(row)]
    start = (page.page_no - 1) * page.page_size
    return page_result([_rule_row(row) for row in rows[start : start + page.page_size]], len(rows), page)


def rule_detail(ident: int) -> dict:
    row = _get(ident)
    data = _rule_row(row)
    data["description"] = row.description
    data["creator"] = row.creator
    data["createTime"] = _fmt(row.create_time)
    data["updater"] = row.updater
    data["updateTime"] = _fmt(row.update_time)
    data["pendingRoleNames"] = [item["name"] for item in data["roles"] if item["status"] == "PENDING_CONFIG"]
    return data


def rule_versions(ident: int) -> dict:
    _get(ident)
    rows = list(
        get_session().scalars(select(PositionRuleVersion).where(PositionRuleVersion.rule_id == ident).order_by(PositionRuleVersion.id.desc()))
    )
    return {"list": [_version_row(row) for row in rows]}


def rule_users(ident: int, params: dict) -> dict:
    rule = _get(ident)
    page = parse_page(params)
    session = get_session()
    links = list(
        session.scalars(
            select(UserRole).where(UserRole.rule_id == rule.id, UserRole.manual_removed == 0, UserRole.source == "DINGTALK_AUTO")
        )
    )
    grouped: dict[int, UserRole] = {}
    for link in links:
        current = grouped.get(link.user_id)
        if current is None or (link.rule_version or 0) < (current.rule_version or 0):
            grouped[link.user_id] = link
    full = []
    for user_id, link in grouped.items():
        user = session.get(User, user_id)
        if user is None or user.status not in {"ACTIVE", "FROZEN"}:
            continue
        full.append((user, link))
    keyword = str(params.get("keyword") or "").strip()
    only_old = str(params.get("outdated") or "") in {"1", "true", "True"}
    only_moved = str(params.get("positionChanged") or "") in {"1", "true", "True"}
    visible = []
    for user, link in full:
        if not _user_in_scope(user):
            continue
        if keyword and keyword not in " ".join([user.nickname or "", user.username or "", user.emp_no or ""]):
            continue
        if only_old and (link.rule_version or 0) >= rule.version:
            continue
        if only_moved and user.position_code == rule.position_code:
            continue
        visible.append((user, link))
    start = (page.page_no - 1) * page.page_size
    data = page_result([_member(user, link, rule) for user, link in visible[start : start + page.page_size]], len(visible), page)
    data["appliedUserCount"] = len(full)
    data["scopeLimited"] = _dept_ids() is not None
    return data


def create_rule(body: dict) -> dict:
    name = _name(body.get("ruleName"))
    position = _position(body.get("positionCode"))
    main_id, extras = _roles(body.get("mainRoleId"), body.get("extraRoleIds") or [], allow_existing=set())
    _unique_name(name, None)
    existing = _enabled_for(position)
    if existing is not None and not _truthy(body.get("replaceExisting")):
        raise _conflict(existing)
    if existing is not None:
        _disable_replaced(existing)
    rule = PositionRoleRule(
        position_code=position,
        role_id=main_id,
        version=1,
        status="ENABLED",
        archived=0,
        rule_name=name,
        description=_desc(body.get("description")),
        active_slot=position,
    )
    session = get_session()
    session.add(rule)
    prepared = _conflict(existing) if existing is not None else BizError(1281, name="")
    try:
        session.flush()
    except IntegrityError as exc:
        raise prepared from exc
    _replace_role_rows(rule.id, main_id, extras)
    _write_version(rule, extras, "CREATE")
    session.flush()
    data = _rule_row(rule)
    data["pendingWarning"] = [item["name"] for item in data["roles"] if item["status"] == "PENDING_CONFIG"]
    return data


def update_rule(ident: int, body: dict) -> dict:
    rule = _get(ident)
    if rule.archived:
        raise BizError(1001, "已归档的规则不能修改")
    base = _int_or_none(body.get("baseVersion"))
    if base is None or base != rule.version:
        raise BizError(1285, n=rule.version)
    name = _name(body.get("ruleName"))
    _unique_name(name, rule.id)
    previous_roles = {rule.role_id, *_extra_ids(rule.id)}
    main_id, extras = _roles(body.get("mainRoleId"), body.get("extraRoleIds") or [], allow_existing=previous_roles)
    description = _desc(body.get("description"))
    same = name == (rule.rule_name or "") and description == (rule.description or "") and main_id == rule.role_id and extras == _extra_ids(rule.id)
    if same:
        return {"unchanged": True, "version": rule.version}
    rule.rule_name = name
    rule.description = description
    rule.role_id = main_id
    rule.version = int(rule.version or 1) + 1
    _replace_role_rows(rule.id, main_id, extras)
    _write_version(rule, extras, "EDIT")
    get_session().flush()
    data = _rule_row(rule)
    data["unchanged"] = False
    data["appliedUserCount"] = _applied_count(rule.id)
    return data


def enable_rule(ident: int, body: dict | None = None) -> dict:
    rule = _get(ident)
    if rule.archived:
        raise BizError(1001, "已归档的规则不能启用")
    body = body or {}
    other = _enabled_for(rule.position_code)
    if other is not None and other.id != rule.id and not _truthy(body.get("replaceExisting")):
        raise _conflict(other)
    if other is not None and other.id != rule.id:
        _disable_replaced(other)
    rule.status = "ENABLED"
    rule.active_slot = rule.position_code
    _write_version(rule, _extra_ids(rule.id), "ENABLE")
    prepared = _conflict(other) if other is not None and other.id != rule.id else BizError(1281, name="")
    try:
        get_session().flush()
    except IntegrityError as exc:
        raise prepared from exc
    return _rule_row(rule)


def disable_rule(ident: int) -> dict:
    rule = _get(ident)
    if rule.archived:
        raise BizError(1001, "已归档的规则不能停用")
    rule.status = "DISABLED"
    rule.active_slot = None
    _write_version(rule, _extra_ids(rule.id), "DISABLE")
    get_session().flush()
    return _rule_row(rule)


def delete_rule(ident: int, confirm_text: str) -> dict:
    rule = _get(ident)
    count = _applied_count(rule.id)
    if count > 0:
        raise BizError(1282, n=count, data={"appliedUserCount": count})
    if (confirm_text or "") != (rule.rule_name or ""):
        raise BizError(1283)
    rule.active_slot = None
    rule.deleted = rule.id
    get_session().flush()
    return {"id": rule.id}


def refresh_preview(ident: int, body: dict) -> dict:
    rule = _get(ident)
    users = _refresh_targets(rule, body)
    if len(users) > 500:
        raise BizError(1001, "单次最多 500 人，请分批刷新")
    lines = [_preview_line(rule, user) for user in users]
    add_times = sum(len(item["addRoles"]) for item in lines)
    remove_times = sum(len(item["removeRoles"]) for item in lines)
    return {"count": len(lines), "addTimes": add_times, "removeTimes": remove_times, "lines": lines}


def refresh_users(ident: int, body: dict) -> dict:
    rule = _get(ident)
    users = _refresh_targets(rule, body)
    if len(users) > 500:
        raise BizError(1001, "单次最多 500 人，请分批刷新")
    changed = skipped = 0
    failed = []
    session = get_session()
    target = [rule.role_id, *_extra_ids(rule.id)]
    for user in users:
        if user.position_code != rule.position_code:
            skipped += 1
            continue
        removed_ids = {
            row.role_id
            for row in session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 1))
        }
        links = list(session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 0)))
        touched = False
        for link in links:
            if link.rule_id != rule.id or link.source != "DINGTALK_AUTO":
                continue
            if link.role_id not in target:
                session.delete(link)
                touched = True
            else:
                link.rule_version = rule.version
                link.grant_position_code = rule.position_code
        owned = {link.role_id for link in links if link.manual_removed == 0}
        for role_id in target:
            if role_id in removed_ids or role_id in owned:
                continue
            session.add(
                UserRole(
                    user_id=user.id,
                    role_id=role_id,
                    source="DINGTALK_AUTO",
                    grant_position_code=rule.position_code,
                    manual_removed=0,
                    rule_id=rule.id,
                    rule_version=rule.version,
                )
            )
            touched = True
        if touched:
            user.perm_version = int(user.perm_version or 1) + 1
            changed += 1
        else:
            skipped += 1
    session.flush()
    return {"changed": changed, "unchanged": skipped, "failed": failed}


def _refresh_targets(rule: PositionRoleRule, body: dict) -> list[User]:
    session = get_session()
    if _truthy(body.get("allOutdated")):
        links = session.scalars(
            select(UserRole).where(
                UserRole.rule_id == rule.id,
                UserRole.manual_removed == 0,
                or_(UserRole.rule_version.is_(None), UserRole.rule_version < rule.version),
            )
        )
        ids = {row.user_id for row in links}
    else:
        raw = body.get("userIds") or []
        if not raw:
            raise BizError(1001, data={"fieldErrors": [{"field": "userIds", "message": "请选择人员"}]})
        ids = {int(item) for item in raw}
    users = []
    for ident in ids:
        user = session.get(User, ident)
        if user is None or not _user_in_scope(user):
            raise BizError(1504)
        users.append(user)
    return users


def _preview_line(rule: PositionRoleRule, user: User) -> dict:
    session = get_session()
    if user.position_code != rule.position_code:
        return {"userId": user.id, "nickname": user.nickname, "note": "岗位已变化，不刷新", "addRoles": [], "removeRoles": []}
    target = [rule.role_id, *_extra_ids(rule.id)]
    removed = {
        row.role_id for row in session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 1))
    }
    links = list(session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 0)))
    remove_names = []
    for link in links:
        if link.rule_id == rule.id and link.source == "DINGTALK_AUTO" and link.role_id not in target:
            role = session.get(Role, link.role_id)
            remove_names.append(role.name if role else "")
    owned = {link.role_id for link in links}
    add_names = []
    notes = []
    for role_id in target:
        role = session.get(Role, role_id)
        label = role.name if role else ""
        if role_id in removed:
            notes.append(f"{label}已被手工移除，跳过")
            continue
        if role_id not in owned:
            add_names.append(label)
    note = "无变化" if not add_names and not remove_names and not notes else "；".join(notes)
    link = next((item for item in links if item.rule_id == rule.id), None)
    return {
        "userId": user.id,
        "nickname": user.nickname,
        "version": link.rule_version if link else None,
        "addRoles": add_names,
        "removeRoles": remove_names,
        "note": note,
    }


def _get(ident: int) -> PositionRoleRule:
    row = get_session().get(PositionRoleRule, int(ident))
    if row is None or row.deleted:
        raise BizError(1504)
    return row


def _name(value) -> str:
    text = str(value or "").strip()
    if not text:
        raise BizError(1001, data={"fieldErrors": [{"field": "ruleName", "message": "请填写规则名称"}]})
    if len(text) > 64:
        raise BizError(1001, data={"fieldErrors": [{"field": "ruleName", "message": "规则名称不能超过 64 字"}]})
    return text


def _desc(value) -> str:
    text = str(value or "").strip()
    if len(text) > 200:
        raise BizError(1001, data={"fieldErrors": [{"field": "description", "message": "说明不能超过 200 字"}]})
    return text


def _position(value) -> str:
    code = str(value or "").strip()
    if not code:
        raise BizError(1001, data={"fieldErrors": [{"field": "positionCode", "message": "请选择岗位"}]})
    row = get_session().scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == code))
    if row is None or row.status != "ENABLED":
        raise BizError(1503, data={"fieldErrors": [{"field": "positionCode", "message": "岗位不存在或未启用"}]})
    return code


def _roles(main_raw, extra_raw, allow_existing: set[int]) -> tuple[int, list[int]]:
    main_id = _int_or_none(main_raw)
    if main_id is None:
        raise BizError(1001, data={"fieldErrors": [{"field": "mainRoleId", "message": "请选择主角色"}]})
    extras = []
    for item in extra_raw:
        ident = _int_or_none(item)
        if ident is None:
            continue
        if ident == main_id or ident in extras:
            raise BizError(1001, data={"fieldErrors": [{"field": "extraRoleIds", "message": "附加角色不能与主角色重复"}]})
        extras.append(ident)
    if len(extras) > 5:
        raise BizError(1001, data={"fieldErrors": [{"field": "extraRoleIds", "message": "附加角色不能超过 5 个"}]})
    _check_role(main_id, allow_existing)
    for ident in extras:
        _check_role(ident, allow_existing)
    return main_id, extras


def _check_role(ident: int, allow_existing: set[int]) -> None:
    role = get_session().get(Role, ident)
    if role is None or role.deleted:
        raise BizError(1500)
    if role.status != "ENABLED" and ident not in allow_existing:
        raise BizError(1501)


def _unique_name(name: str, ignore_id: int | None) -> None:
    rows = list(get_session().scalars(select(PositionRoleRule).where(PositionRoleRule.rule_name == name)))
    for row in rows:
        if ignore_id is not None and row.id == ignore_id:
            continue
        raise BizError(1284)


def _enabled_for(position: str) -> PositionRoleRule | None:
    return get_session().scalar(
        select(PositionRoleRule).where(
            PositionRoleRule.position_code == position,
            PositionRoleRule.status == "ENABLED",
            PositionRoleRule.archived == 0,
        )
    )


def _disable_replaced(rule: PositionRoleRule) -> None:
    rule.status = "DISABLED"
    rule.active_slot = None
    _write_version(rule, _extra_ids(rule.id), "REPLACED")
    get_session().flush()


def _conflict(existing: PositionRoleRule | None) -> BizError:
    if existing is None:
        return BizError(1281, name="")
    return BizError(
        1281,
        name=existing.rule_name or "",
        data={
            "existingRuleId": existing.id,
            "existingRuleName": existing.rule_name,
            "existingVersion": existing.version,
            "appliedUserCount": _applied_count(existing.id),
        },
    )


def _applied_count(rule_id: int) -> int:
    session = get_session()
    ids = {
        row.user_id
        for row in session.scalars(select(UserRole).where(UserRole.rule_id == rule_id, UserRole.manual_removed == 0))
    }
    count = 0
    for ident in ids:
        user = session.get(User, ident)
        if user is not None and user.status in {"ACTIVE", "FROZEN"}:
            count += 1
    return count


def _outdated_count(rule: PositionRoleRule) -> int:
    session = get_session()
    ids = {
        row.user_id
        for row in session.scalars(
            select(UserRole).where(
                UserRole.rule_id == rule.id,
                UserRole.manual_removed == 0,
                or_(UserRole.rule_version.is_(None), UserRole.rule_version < rule.version),
            )
        )
    }
    count = 0
    for ident in ids:
        user = session.get(User, ident)
        if user is not None and user.status in {"ACTIVE", "FROZEN"}:
            count += 1
    return count


def _extra_ids(rule_id: int) -> list[int]:
    return [
        row.role_id
        for row in get_session().scalars(
            select(PositionRuleRole).where(PositionRuleRole.rule_id == rule_id, PositionRuleRole.role_type == "EXTRA").order_by(PositionRuleRole.id.asc())
        )
    ]


def _has_pending(rule: PositionRoleRule) -> bool:
    ids = [rule.role_id, *_extra_ids(rule.id)]
    session = get_session()
    return any((role := session.get(Role, ident)) is not None and role.status == "PENDING_CONFIG" for ident in ids)


def _role_brief(ident: int, role_type: str) -> dict:
    role = get_session().get(Role, ident)
    return {
        "roleId": ident,
        "name": role.name if role else "",
        "source": role.source if role else "",
        "status": role.status if role else "",
        "roleType": role_type,
    }


def _rule_row(rule: PositionRoleRule) -> dict:
    session = get_session()
    position = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == rule.position_code))
    roles = [_role_brief(rule.role_id, "MAIN")]
    roles.extend(_role_brief(ident, "EXTRA") for ident in _extra_ids(rule.id))
    status = "ARCHIVED" if rule.archived else rule.status
    return {
        "id": rule.id,
        "ruleName": rule.rule_name,
        "positionCode": rule.position_code,
        "positionName": position.dict_label if position else rule.position_code,
        "positionSource": position.source if position else "",
        "version": rule.version,
        "status": status,
        "description": rule.description,
        "appliedUserCount": _applied_count(rule.id),
        "outdatedUserCount": _outdated_count(rule),
        "roles": roles,
        "updateTime": _fmt(rule.update_time),
    }


def _version_row(row: PositionRuleVersion) -> dict:
    session = get_session()
    main = session.get(Role, row.main_role_id) if row.main_role_id else None
    extras = []
    for ident in row.extra_role_ids or []:
        role = session.get(Role, int(ident))
        extras.append(role.name if role else str(ident))
    actor = "钉钉同步" if not row.operator_id else str(row.operator_id)
    return {
        "id": row.id,
        "version": row.version,
        "changeType": row.change_type,
        "ruleName": row.rule_name,
        "mainRoleName": main.name if main else "",
        "extraRoleNames": extras,
        "status": row.status,
        "operatorText": actor,
        "createTime": _fmt(row.create_time),
    }


def _member(user: User, link: UserRole, rule: PositionRoleRule) -> dict:
    dept = get_session().get(Dept, user.main_dept_id) if user.main_dept_id else None
    return {
        "userId": user.id,
        "nickname": user.nickname,
        "empNo": user.emp_no,
        "deptName": dept.name if dept else "",
        "positionCode": user.position_code,
        "ruleVersion": link.rule_version,
        "outdated": (link.rule_version or 0) < rule.version,
        "positionChanged": user.position_code != rule.position_code,
        "grantTime": _fmt(link.create_time),
        "status": user.status,
    }


def _dept_ids():
    ctx = get_ctx()
    if ctx is None or ctx.system or "ALL" in (ctx.data_scopes or set()):
        return None
    return set(ctx.dept_ids or [])


def _user_in_scope(user: User) -> bool:
    allowed = _dept_ids()
    if allowed is None:
        return True
    ctx = get_ctx()
    if ctx and "SELF" in (ctx.data_scopes or set()) and user.id == ctx.user_id:
        return True
    return user.main_dept_id in allowed


def _menu_count(user_id: int) -> int:
    session = get_session()
    role_ids = [row.role_id for row in session.scalars(select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 0))]
    if not role_ids:
        return 0
    menu_ids = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids))))
    if not menu_ids:
        return 0
    return int(session.scalar(select(func.count()).select_from(Menu).where(Menu.id.in_(list(menu_ids)), Menu.status == "ENABLED")) or 0)


def scope_text_for(user: User) -> str:
    session = get_session()
    labels = []
    for link in session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 0)):
        role = session.get(Role, link.role_id)
        if role is None or not role.data_scope:
            continue
        text = {"ALL": "全部数据", "DEPT": "本部门", "SELF": "仅本人", "IP_GROUP": "本组"}.get(role.data_scope, role.data_scope)
        if text not in labels:
            labels.append(text)
    return "、".join(labels)


def _fmt(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _int_or_none(value):
    if value in (None, ""):
        return None
    return int(value)


def _truthy(value) -> bool:
    return value in (True, 1, "1", "true", "True")
