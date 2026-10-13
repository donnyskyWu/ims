"""B2 系统管理页面对应的写接口与查询。复用 B0a 服务，不重做部门树与登录。"""
from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import func, or_, select

from app.api.dump import dump_row
from app.catalog import PERM_CODES
from app.core.clock import now_naive, parse_input_datetime
from app.core.context import get_ctx, system_context, use_context
from app.core.crypto import hmac_hash
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.system import service
from app.domains.system.model import (
    ChangeLog,
    Dept,
    DictData,
    DictType,
    LoginLog,
    Menu,
    OperateLog,
    Param,
    Role,
    RoleMenu,
    RolePermDetail,
    Tenant,
    TenantPackage,
    TenantPackageMenu,
    User,
    UserDept,
    UserRole,
)
from app.services.exchange import remember_export

_USERNAME = re.compile(r"^[A-Za-z0-9_]{4,30}$")
_MOBILE = re.compile(r"^1\d{10}$")
_SCOPES = {"ALL", "DEPT", "IP_GROUP", "SELF"}
_SCOPE_TEXT = {"ALL": "全部数据", "DEPT": "本部门", "IP_GROUP": "本组", "SELF": "仅本人"}
_SOURCE_TEXT = {"MANUAL": "手工", "DINGTALK_AUTO": "钉钉自动"}
_LOGIN_TEXT = {
    "SUCCESS": "成功",
    "BAD_CREDENTIAL": "密码错",
    "LOCKED": "已锁定",
    "DISABLED": "已冻结或离职",
    "UNMAPPED": "未匹配",
    "LOGOUT": "登出",
    "KICKED": "强制下线",
}
_EVENT_TEXT = {
    "user.resigned": "人员离职",
    "DISABLED_EVT": "通知已关闭",
    "EVT": "业务通知",
}


def _ident(value, field="id") -> int:
    try:
        parsed = parse_api_id(value)
    except BizError:
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "编号格式不正确"}]})
    if parsed is None:
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "编号不能为空"}]})
    return int(parsed)


def _ids(values, field: str) -> list[int]:
    return [_ident(item, field) for item in values or []]


def _when(raw, field: str):
    if raw in (None, ""):
        return None
    try:
        return parse_input_datetime(str(raw))
    except ValueError:
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "时间格式不正确"}]})


def _platform() -> None:
    ctx = get_ctx()
    if ctx is None or int(ctx.tenant_id or 0) != 1:
        raise BizError(1291)


def _assert_scope(target: str) -> None:
    if target not in _SCOPES:
        raise BizError(1503, data={"fieldErrors": [{"field": "dataScope", "message": "数据范围不正确"}]})
    ctx = get_ctx()
    owned = set((ctx.data_scopes if ctx else set()) or set())
    if ctx is not None and (ctx.system or "ALL" in owned):
        return
    if target == "SELF" and owned:
        return
    if target not in owned:
        raise BizError(1001, data={"fieldErrors": [{"field": "dataScope", "message": "不能超过您自己的数据范围"}]})


def _user(ident: int) -> User:
    row = get_session().get(User, ident)
    if row is None or row.deleted:
        raise BizError(1504)
    return row


def user_detail(ident: int) -> dict:
    user = _user(ident)
    row = service._user_rows([user])[0]
    session = get_session()
    row["deptIds"] = [link.dept_id for link in session.scalars(select(UserDept).where(UserDept.user_id == ident))]
    row["roleIds"] = [
        link.role_id
        for link in session.scalars(select(UserRole).where(UserRole.user_id == ident, UserRole.manual_removed == 0))
    ]
    row["hasPassword"] = bool(user.password_hash)
    return row


def user_create_full(body: dict) -> dict:
    username = str(body.get("username") or "").strip()
    nickname = str(body.get("nickname") or body.get("name") or "").strip()
    mobile = str(body.get("mobile") or "").strip()
    password = str(body.get("password") or "")
    dept_ids = _ids(body.get("deptIds"), "deptIds")
    main = body.get("mainDeptId")
    if not _USERNAME.match(username):
        raise BizError(1001, data={"fieldErrors": [{"field": "username", "message": "用户名为 4 到 30 位字母、数字或下划线"}]})
    if not nickname:
        raise BizError(1001, data={"fieldErrors": [{"field": "nickname", "message": "请填写姓名"}]})
    if not _MOBILE.match(mobile):
        raise BizError(1001, data={"fieldErrors": [{"field": "mobile", "message": "请填写 11 位手机号"}]})
    if main in (None, ""):
        raise BizError(1287, data={"fieldErrors": [{"field": "mainDeptId", "message": "请先指定主部门"}]})
    main_id = _ident(main, "mainDeptId")
    if main_id not in dept_ids:
        raise BizError(1287, data={"fieldErrors": [{"field": "mainDeptId", "message": "请先指定主部门"}]})
    if not password:
        raise BizError(1001, data={"fieldErrors": [{"field": "password", "message": "请填写初始密码"}]})
    created = service.user_create(
        username,
        nickname,
        dept_ids,
        main_id,
        password,
        mobile,
        body.get("empNo"),
        body.get("positionCode") or None,
    )
    ident = int(created["id"])
    if body.get("roleIds"):
        _set_roles(ident, _ids(body.get("roleIds"), "roleIds"))
    if body.get("positionCode"):
        _apply_position(ident, str(body.get("positionCode")))
    return user_detail(ident)


def user_update_full(body: dict) -> dict:
    ident = _ident(body.get("id"))
    user = _user(ident)
    if body.get("username") not in (None, "", user.username):
        raise BizError(1001, data={"fieldErrors": [{"field": "username", "message": "用户名创建后不能修改"}]})
    if "nickname" in body or "name" in body:
        user.nickname = str(body.get("nickname") or body.get("name") or user.nickname)
    if "empNo" in body:
        user.emp_no = body.get("empNo") or None
    if "mobile" in body and body.get("mobile") not in (None, ""):
        mobile = str(body.get("mobile")).strip()
        if not _MOBILE.match(mobile):
            raise BizError(1001, data={"fieldErrors": [{"field": "mobile", "message": "请填写 11 位手机号"}]})
        service._assert_mobile_free(mobile, ident)
        from app.core.crypto import encrypt

        user.mobile_enc = encrypt(mobile)
        user.mobile_hash = hmac_hash(mobile)
    if "deptIds" in body:
        dept_ids = _ids(body.get("deptIds"), "deptIds")
        if body.get("mainDeptId") in (None, ""):
            raise BizError(1287, data={"fieldErrors": [{"field": "mainDeptId", "message": "请先指定主部门"}]})
        main_id = _ident(body.get("mainDeptId"), "mainDeptId")
        if main_id not in dept_ids:
            raise BizError(1287, data={"fieldErrors": [{"field": "mainDeptId", "message": "请先指定主部门"}]})
        service.update_depts(ident, dept_ids, main_id)
    if "roleIds" in body:
        _set_roles(ident, _ids(body.get("roleIds") or [], "roleIds"))
    if "positionCode" in body and body.get("positionCode") and body.get("positionCode") != user.position_code:
        _apply_position(ident, str(body.get("positionCode")))
    elif "positionCode" in body and not body.get("positionCode"):
        user.position_code = None
    Repository(User).update(user)
    return user_detail(ident)


def _set_roles(user_id: int, role_ids: list[int]) -> None:
    session = get_session()
    for role_id in role_ids:
        role = session.get(Role, role_id)
        if role is None or role.deleted:
            raise BizError(1500, data={"field": "roleIds"})
        if role.status == "DISABLED":
            raise BizError(1501, data={"field": "roleIds"})
    desired = set(role_ids)
    current = list(session.scalars(select(UserRole).where(UserRole.user_id == user_id)))
    for link in current:
        if link.role_id in desired and int(link.manual_removed or 0) == 0:
            continue
        if link.role_id in desired and int(link.manual_removed or 0) == 1 and link.source == "MANUAL":
            link.manual_removed = 0
            continue
        if link.role_id not in desired and int(link.manual_removed or 0) == 0:
            link.manual_removed = 1
    have = {link.role_id for link in current if int(link.manual_removed or 0) == 0 or link.role_id in desired}
    for role_id in desired:
        active = next((link for link in current if link.role_id == role_id and int(link.manual_removed or 0) == 0), None)
        if active is None:
            restored = next((link for link in current if link.role_id == role_id), None)
            if restored is not None and restored.source == "MANUAL":
                restored.manual_removed = 0
            elif restored is None:
                session.add(UserRole(user_id=user_id, role_id=role_id, source="MANUAL", manual_removed=0))
    user = session.get(User, user_id)
    if user is not None:
        user.perm_version = int(user.perm_version or 1) + 1
    session.flush()
    _ = have


def _apply_position(user_id: int, position_code: str) -> None:
    from app.services.position import apply_position_change

    stamp = now_naive().strftime("%Y%m%d%H%M%S%f")
    apply_position_change(user_id, position_code, f"manual-pos:{user_id}:{position_code}:{stamp}")


def freeze_user(ident: int) -> dict:
    return service.user_status(ident, "FROZEN")


def unfreeze_user(ident: int) -> dict:
    user = _user(ident)
    if user.status == "RESIGNED":
        raise BizError(1001, "离职用户不能恢复为在职")
    return service.user_status(ident, "ACTIVE")


def resign_user(ident: int) -> dict:
    return service.user_status(ident, "RESIGNED")


def unlock_user(ident: int) -> dict:
    from app.services.auth_svc import unlock

    user = _user(ident)
    unlock(user.username)
    user.login_fail_count = 0
    user.lock_until = None
    return {"id": user.id, "username": user.username}


def kick_user(ident: int) -> dict:
    from app.services.auth_svc import kick

    _user(ident)
    kick(ident)
    return {"id": ident}


def reset_user_password(ident: int) -> dict:
    from app.services.auth_svc import reset_password

    _user(ident)
    return reset_password(ident)


def delete_user(ident: int) -> dict:
    return service.user_delete(ident)


def export_users(query: dict) -> dict:
    dept = query.get("deptId")
    include = str(query.get("includeChildren", "true")).lower() != "false"
    rows = []
    page_no = 1
    total = 1
    while len(rows) < total:
        page = service.user_page(
            Page(page_no, 100),
            int(dept) if dept else None,
            include,
            query.get("keyword"),
            query.get("status"),
            query.get("username"),
            query.get("nickname"),
            query.get("mobile"),
        )
        total = int(page["total"])
        rows.extend(page["list"])
        page_no += 1
        if page_no > 50:
            break
    header = ["用户名", "姓名", "主部门", "手机", "状态", "最近登录"]
    body = [
        [item.get("username"), item.get("nickname"), item.get("mainDeptName"), item.get("mobile"), item.get("status"), item.get("lastLoginTime")]
        for item in rows
    ]
    return remember_export("users.xlsx", header, body, "sys_user")


def role_page(page: Page, keyword: str | None, status: str | None) -> dict:
    session = get_session()
    stmt = select(Role)
    if keyword:
        stmt = stmt.where(or_(Role.name.contains(keyword), Role.role_key.contains(keyword)))
    if status:
        stmt = stmt.where(Role.status == status)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(session.scalars(stmt.order_by(Role.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    return page_result([_role_view(row) for row in rows], int(total or 0), page)


def _position_names(role_id: int) -> list[str]:
    from app.domains.auth.model import PositionRoleRule, PositionRuleRole

    session = get_session()
    codes = set(
        session.scalars(
            select(PositionRoleRule.position_code).where(
                PositionRoleRule.role_id == role_id,
                PositionRoleRule.archived == 0,
                PositionRoleRule.status == "ENABLED",
            )
        )
    )
    rule_ids = list(
        session.scalars(select(PositionRuleRole.rule_id).where(PositionRuleRole.role_id == role_id, PositionRuleRole.role_type == "MAIN"))
    )
    if rule_ids:
        codes.update(
            session.scalars(
                select(PositionRoleRule.position_code).where(
                    PositionRoleRule.id.in_(rule_ids),
                    PositionRoleRule.archived == 0,
                    PositionRoleRule.status == "ENABLED",
                )
            )
        )
    labels = []
    for code in sorted(item for item in codes if item):
        label = service.cache.get_label("dict_position", code) or code
        labels.append(label)
    return labels


def _role_view(role: Role) -> dict:
    session = get_session()
    menu_count = int(session.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.role_id == role.id)) or 0)
    details = list(session.scalars(select(RolePermDetail).where(RolePermDetail.role_id == role.id)))
    read = sum(int(item.r or 0) for item in details)
    write = sum(int(item.w or 0) for item in details)
    delete = sum(int(item.d or 0) for item in details)
    members = int(
        session.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id, UserRole.manual_removed == 0)) or 0
    )
    menu_ids = list(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == role.id)))
    return {
        "id": role.id,
        "roleKey": role.role_key,
        "name": role.name,
        "positionCode": role.position_code,
        "menuIds": menu_ids,
        "permDetails": [
            {"permCode": item.perm_code, "r": int(item.r or 0), "w": int(item.w or 0), "d": int(item.d or 0)} for item in details
        ],
        "menuCount": menu_count,
        "permSummary": f"读 {read} / 写 {write} / 删 {delete}" if details else f"菜单 {menu_count}",
        "dataScope": role.data_scope,
        "dataScopeText": _SCOPE_TEXT.get(role.data_scope or "", "未配置"),
        "positionNames": _position_names(role.id),
        "positionHint": "请到岗位-角色供给规则维护",
        "source": role.source,
        "sourceText": _SOURCE_TEXT.get(role.source, "手工"),
        "status": role.status,
        "memberCount": members,
        "updateTime": role.update_time,
        "remark": role.remark,
        "isStandard": int(role.is_standard or 0),
    }


def role_create(body: dict) -> dict:
    if body.get("dataScope"):
        _assert_scope(str(body.get("dataScope")))
    created = service.role_create(body.get("name") or "", body.get("roleKey") or "", "MANUAL", body.get("dataScope"), None)
    if body.get("remark"):
        role = get_session().get(Role, int(created["id"]))
        role.remark = body.get("remark")
    return _role_view(get_session().get(Role, int(created["id"])))


def role_update(body: dict) -> dict:
    ident = _ident(body.get("id"))
    role = get_session().get(Role, ident)
    if role is None or role.deleted:
        raise BizError(1504)
    name = body.get("name") or role.name
    standards = list(get_session().scalars(select(Role).where(Role.is_standard == 1, Role.id != ident)))
    for item in standards:
        if item.name == name:
            raise BizError(1001, data={"fieldErrors": [{"field": "name", "message": "不能与标准角色重名"}]})
    if body.get("roleKey") and body.get("roleKey") != role.role_key:
        if role.is_standard:
            raise BizError(1001, data={"fieldErrors": [{"field": "roleKey", "message": "标准角色编码不能修改"}]})
        for item in standards:
            if item.role_key == body.get("roleKey"):
                raise BizError(1001, data={"fieldErrors": [{"field": "roleKey", "message": "不能与标准角色重名"}]})
        role.role_key = body.get("roleKey")
    role.name = name
    if "remark" in body:
        role.remark = body.get("remark")
    return {**_role_view(role), "positionHint": "请到岗位-角色供给规则维护"}


def role_menus(ident: int, menu_ids: list[int]) -> dict:
    session = get_session()
    role = session.get(Role, ident)
    if role is None:
        raise BizError(1504)
    session.execute(RoleMenu.__table__.delete().where(RoleMenu.role_id == ident))
    for menu_id in menu_ids:
        menu = session.get(Menu, menu_id)
        if menu is None or menu.deleted:
            raise BizError(1500, data={"field": "menuIds"})
        session.add(RoleMenu(role_id=ident, menu_id=menu_id))
    service._bump_role_members(ident)
    session.flush()
    return {"id": ident, "menuIds": menu_ids}


def role_perm_detail(ident: int, details: list[dict]) -> dict:
    codes = []
    normalized = []
    for item in details or []:
        code = item.get("permCode") or ""
        read = 1 if item.get("r") else 0
        write = 1 if item.get("w") else 0
        delete = 1 if item.get("d") else 0
        if write or delete:
            read = 1
        if not (read or write or delete):
            continue
        codes.append(code)
        normalized.append({"permCode": code, "r": read, "w": write, "d": delete})
    saved = service.role_grant(ident, codes, normalized)
    return saved


def role_data_scope(ident: int, data_scope: str) -> dict:
    _assert_scope(data_scope)
    role = get_session().get(Role, ident)
    if role is None:
        raise BizError(1504)
    role.data_scope = data_scope
    service._bump_role_members(ident)
    return {"id": role.id, "dataScope": role.data_scope, "dataScopeText": _SCOPE_TEXT.get(data_scope, "")}


def role_members(ident: int) -> list[dict]:
    session = get_session()
    links = list(session.scalars(select(UserRole).where(UserRole.role_id == ident)))
    data = []
    for link in links:
        user = session.get(User, link.user_id)
        if user is None:
            continue
        data.append(
            {
                "userId": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "source": link.source,
                "sourceText": "钉钉自动" if link.source == "DINGTALK_AUTO" else "手工",
                "manualRemoved": int(link.manual_removed or 0),
            }
        )
    return data


def role_add_member(ident: int, user_id: int) -> dict:
    session = get_session()
    if session.get(Role, ident) is None:
        raise BizError(1504)
    if session.get(User, user_id) is None:
        raise BizError(1500, data={"field": "userId"})
    link = session.scalar(select(UserRole).where(UserRole.role_id == ident, UserRole.user_id == user_id, UserRole.source == "MANUAL"))
    if link is None:
        session.add(UserRole(user_id=user_id, role_id=ident, source="MANUAL", manual_removed=0))
    else:
        link.manual_removed = 0
    user = session.get(User, user_id)
    user.perm_version = int(user.perm_version or 1) + 1
    session.flush()
    return {"roleId": ident, "userId": user_id}


def role_remove_member(ident: int, user_id: int) -> dict:
    session = get_session()
    links = list(session.scalars(select(UserRole).where(UserRole.role_id == ident, UserRole.user_id == user_id, UserRole.manual_removed == 0)))
    if not links:
        raise BizError(1504)
    for link in links:
        link.manual_removed = 1
    user = session.get(User, user_id)
    if user is not None:
        user.perm_version = int(user.perm_version or 1) + 1
    session.flush()
    return {"roleId": ident, "userId": user_id}


def role_set_status(ident: int, status: str) -> dict:
    if status not in {"ENABLED", "DISABLED", "PENDING_CONFIG"}:
        raise BizError(1503)
    saved = service.role_status(ident, status)
    service._bump_role_members(ident)
    return saved


def role_delete_named(ident: int, confirm_name: str) -> dict:
    role = get_session().get(Role, ident)
    if role is None:
        raise BizError(1504)
    if (confirm_name or "") != role.name:
        raise BizError(1293)
    session = get_session()
    from app.domains.auth.model import PositionRoleRule, PositionRuleRole

    used = int(
        session.scalar(
            select(func.count()).select_from(PositionRoleRule).where(PositionRoleRule.role_id == ident, PositionRoleRule.archived == 0)
        )
        or 0
    )
    used += int(session.scalar(select(func.count()).select_from(PositionRuleRole).where(PositionRuleRole.role_id == ident)) or 0)
    if used:
        raise BizError(1502, data={"refs": [{"entity": "岗位规则", "count": used}]})
    return service.role_delete(ident)


def role_preview(ident: int, user_id: int) -> dict:
    session = get_session()
    role = session.get(Role, ident)
    user = session.get(User, user_id)
    if role is None or user is None:
        raise BizError(1504)
    role_codes = _codes_of_roles([ident])
    links = list(session.scalars(select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 0)))
    other = [link.role_id for link in links if link.role_id != ident]
    current = _codes_of_roles([link.role_id for link in links])
    others = _codes_of_roles(other)
    has = any(link.role_id == ident for link in links)
    if has:
        added = []
        removed = sorted(role_codes - others)
    else:
        added = sorted(role_codes - current)
        removed = []
    names = _perm_names(set(added) | set(removed) | role_codes)
    return {
        "added": [{"permCode": code, "name": names.get(code, code)} for code in added],
        "removed": [{"permCode": code, "name": names.get(code, code)} for code in removed],
    }


def _codes_of_roles(role_ids: list[int]) -> set[str]:
    if not role_ids:
        return set()
    session = get_session()
    menus = list(session.scalars(select(Menu).join(RoleMenu, RoleMenu.menu_id == Menu.id).where(RoleMenu.role_id.in_(role_ids))))
    return {menu.perm_code for menu in menus if menu.perm_code}


def _perm_names(codes: set[str]) -> dict[str, str]:
    if not codes:
        return {}
    rows = get_session().scalars(select(Menu).where(Menu.perm_code.in_(codes)))
    return {row.perm_code: row.name for row in rows if row.perm_code}


def role_from_position(position_code: str) -> dict:
    code = (position_code or "").strip()
    if not code:
        raise BizError(1001, data={"fieldErrors": [{"field": "positionCode", "message": "请选择岗位"}]})
    session = get_session()
    from app.domains.auth.model import PositionRoleRule

    existing = session.scalar(select(Role).where(Role.position_code == code, Role.deleted == 0))
    rule = session.scalar(
        select(PositionRoleRule).where(PositionRoleRule.position_code == code, PositionRoleRule.archived == 0, PositionRoleRule.status == "ENABLED")
    )
    if existing is not None or rule is not None:
        role_id = existing.id if existing is not None else rule.role_id
        return {"existed": True, "roleId": role_id, "hint": "该岗位已有角色，请到岗位-角色供给规则维护"}
    created = service.role_create(f"待配置-{code}", f"auto_{code}", "DINGTALK_AUTO", None, code)
    from app.services.position import _todo_for_role_admins

    _todo_for_role_admins(int(created["id"]), code)
    return {"existed": False, "roleId": int(created["id"]), "status": "PENDING_CONFIG"}


def menu_tree() -> list[dict]:
    rows = list(get_session().scalars(select(Menu).where(Menu.status == "ENABLED")))
    by_parent: dict[int, list] = {}
    for row in rows:
        by_parent.setdefault(int(row.parent_id or 0), []).append(row)

    def node(menu: Menu) -> dict:
        return {
            "id": menu.id,
            "name": menu.name,
            "path": menu.path,
            "permCode": menu.perm_code,
            "type": menu.type,
            "visible": int(menu.visible or 0),
            "sort": menu.sort,
            "icon": menu.icon,
            "keepAlive": int(menu.keep_alive or 0),
            "seedLocked": bool(menu.perm_code and menu.perm_code in PERM_CODES),
            "children": [node(child) for child in sorted(by_parent.get(menu.id, []), key=lambda item: item.sort)],
        }

    roots = [row for row in rows if int(row.parent_id or 0) == 0]
    return [node(row) for row in sorted(roots, key=lambda item: item.sort)]


def menu_save(body: dict, ident: int | None = None) -> dict:
    session = get_session()
    if ident is None:
        created = service.menu_create(body.get("name") or "", body.get("type") or "MENU", body.get("permCode"), int(body.get("parentId") or 0))
        row = session.get(Menu, int(created["id"]))
    else:
        row = session.get(Menu, ident)
        if row is None:
            raise BizError(1504)
        if body.get("id") not in (None, "", ident, str(ident)):
            raise BizError(1211)
        locked = bool(row.perm_code and row.perm_code in PERM_CODES)
        if locked and body.get("path") not in (None, row.path):
            raise BizError(1001, data={"fieldErrors": [{"field": "path", "message": "种子菜单不能修改路由"}]})
        if locked and body.get("permCode") not in (None, "", row.perm_code):
            raise BizError(1001, data={"fieldErrors": [{"field": "permCode", "message": "种子菜单不能修改权限码"}]})
        if body.get("name"):
            row.name = body.get("name")
        if not locked and body.get("permCode"):
            row.perm_code = body.get("permCode")
        if not locked and "path" in body:
            row.path = body.get("path")
        if "parentId" in body and body.get("parentId") is not None:
            row.parent_id = int(body.get("parentId") or 0)
    if body.get("icon") is not None:
        row.icon = body.get("icon") or None
    if body.get("sort") is not None:
        row.sort = int(body.get("sort") or 0)
    if "visible" in body:
        row.visible = 1 if body.get("visible") in (True, 1, "1", "true") else 0
    if "keepAlive" in body:
        row.keep_alive = 1 if body.get("keepAlive") in (True, 1, "1", "true") else 0
    if "component" in body:
        row.component = body.get("component")
    session.flush()
    return dump_row(row, ["id", "name", "path", "perm_code", "type", "visible", "sort", "icon", "keep_alive"])


def menu_delete(ident: int) -> dict:
    session = get_session()
    row = session.get(Menu, ident)
    if row is None:
        raise BizError(1504)
    children = int(session.scalar(select(func.count()).select_from(Menu).where(Menu.parent_id == ident, Menu.deleted == 0)) or 0)
    roles = int(session.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.menu_id == ident)) or 0)
    packages = int(session.scalar(select(func.count()).select_from(TenantPackageMenu).where(TenantPackageMenu.menu_id == ident)) or 0)
    if children or roles or packages:
        raise BizError(1502, data={"refs": [{"entity": "下级或授权", "count": children + roles + packages}]})
    row.deleted = row.id
    return {}


def menu_visible(ident: int, visible: bool) -> dict:
    row = get_session().get(Menu, ident)
    if row is None:
        raise BizError(1504)
    row.visible = 1 if visible else 0
    return {"id": row.id, "visible": int(row.visible)}


def dict_type_update(body: dict) -> dict:
    row = get_session().get(DictType, _ident(body.get("id")))
    if row is None:
        raise BizError(1504)
    if body.get("name"):
        row.name = body.get("name")
    if "remark" in body:
        row.remark = body.get("remark")
    if body.get("status"):
        row.status = body.get("status")
    return dump_row(row)


def dict_type_delete(ident: int) -> dict:
    session = get_session()
    row = session.get(DictType, ident)
    if row is None:
        raise BizError(1504)
    used = int(session.scalar(select(func.count()).select_from(DictData).where(DictData.dict_type == row.dict_type, DictData.deleted == 0)) or 0)
    if used:
        raise BizError(1502, data={"refs": [{"entity": "字典值", "count": used}]})
    row.deleted = row.id
    return {}


def dict_data_save(body: dict, ident: int | None = None) -> dict:
    if ident is None:
        created = service.dict_data_create(body.get("dictType") or "", body.get("dictValue") or "", body.get("dictLabel") or "", body.get("colorType") or "neutral")
        row = get_session().get(DictData, int(created["id"]))
    else:
        service.dict_data_update(ident, body.get("dictValue"), body.get("dictLabel"), body.get("colorType"), body.get("status"))
        row = get_session().get(DictData, ident)
    if body.get("remark") is not None:
        row.remark = body.get("remark")
    if body.get("sort") is not None:
        row.sort = int(body.get("sort") or 0)
    if row.dict_type == "dict_position" and body.get("source") in {"DINGTALK", "LOCAL"}:
        row.source = body.get("source")
    service.cache.invalidate(row.dict_type)
    return dump_row(row)


def dict_types() -> list[dict]:
    rows = list(get_session().scalars(select(DictType).order_by(DictType.id.asc())))
    return [dump_row(row) for row in rows]


def dict_values(dict_type: str) -> list[dict]:
    rows = list(get_session().scalars(select(DictData).where(DictData.dict_type == dict_type).order_by(DictData.sort.asc(), DictData.id.asc())))
    return [dump_row(row) for row in rows]


def dict_simple_list(dict_type: str, status: str | None = None) -> list[dict]:
    """登录态字典简表。按类型一次查出，默认只返回启用值（含 colorType）。"""
    wanted = (status or "ENABLED").strip() or "ENABLED"
    rows = list(
        get_session().scalars(
            select(DictData)
            .where(DictData.dict_type == dict_type, DictData.status == wanted)
            .order_by(DictData.sort.asc(), DictData.id.asc())
        )
    )
    return [dump_row(row, ["dict_value", "dict_label", "color_type", "status", "sort"]) for row in rows]


def _window(params: dict, default_days: int, max_days: int | None):
    end = now_naive()
    start = end - timedelta(days=default_days)
    if params.get("startTime"):
        start = _when(params.get("startTime"), "startTime")
    if params.get("endTime"):
        end = _when(params.get("endTime"), "endTime")
    if max_days is not None and (end - start).days > max_days:
        raise BizError(1001, data={"fieldErrors": [{"field": "startTime", "message": "时间跨度不能超过 90 天"}]})
    floor = now_naive() - timedelta(days=180)
    if start < floor:
        start = floor
    return start, end


def operate_log_page(page: Page, params: dict) -> dict:
    start, end = _window(params, 180, None)
    session = get_session()
    stmt = select(OperateLog).where(OperateLog.create_time >= start, OperateLog.create_time <= end)
    if params.get("operator"):
        stmt = stmt.where(OperateLog.operator_name.contains(str(params.get("operator"))))
    if params.get("module"):
        stmt = stmt.where(OperateLog.module == params.get("module"))
    if params.get("success") in {"1", "0", 1, 0}:
        stmt = stmt.where(OperateLog.success == int(params.get("success")))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(session.scalars(stmt.order_by(OperateLog.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    data = []
    for row in rows:
        data.append(
            {
                "id": row.id,
                "createTime": row.create_time,
                "operatorName": row.operator_name,
                "module": row.module,
                "action": row.action,
                "objectId": row.object_id,
                "success": int(row.success or 0),
                "resultText": "成功" if row.success else f"失败 {row.error_code or ''}".strip(),
                "errorCode": row.error_code,
                "ip": row.ip,
                "costMs": row.cost_ms,
            }
        )
    return page_result(data, int(total or 0), page)


def operate_log_detail(ident: int) -> dict:
    row = get_session().get(OperateLog, ident)
    if row is None:
        raise BizError(1504)
    return {
        "id": row.id,
        "createTime": row.create_time,
        "operatorName": row.operator_name,
        "module": row.module,
        "action": row.action,
        "objectId": row.object_id,
        "success": int(row.success or 0),
        "resultText": "成功" if row.success else "失败",
        "errorCode": row.error_code,
        "ip": row.ip,
        "costMs": row.cost_ms,
        "path": row.path,
        "method": row.method,
        "paramsDigest": row.params_digest,
    }


def login_log_page(page: Page, params: dict) -> dict:
    start, end = _window(params, 180, None)
    session = get_session()
    stmt = select(LoginLog).where(LoginLog.create_time >= start, LoginLog.create_time <= end)
    if params.get("username"):
        stmt = stmt.where(LoginLog.username.contains(str(params.get("username"))))
    if params.get("result"):
        stmt = stmt.where(LoginLog.result == params.get("result"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(session.scalars(stmt.order_by(LoginLog.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    data = []
    for row in rows:
        channel = row.channel or row.login_type or ""
        way = "钉钉" if "DING" in channel.upper() else "账号密码"
        data.append(
            {
                "id": row.id,
                "createTime": row.create_time,
                "username": row.username,
                "loginWay": way,
                "result": row.result,
                "resultText": _LOGIN_TEXT.get(row.result, "失败"),
                "ip": row.ip,
                "device": (row.user_agent or "")[:80],
            }
        )
    return page_result(data, int(total or 0), page)


def export_operate_logs(params: dict) -> dict:
    start, end = _window(params, 90, 90)
    page = operate_log_page(Page(1, 100), {**params, "startTime": start.strftime("%Y-%m-%d %H:%M:%S"), "endTime": end.strftime("%Y-%m-%d %H:%M:%S")})
    header = ["时间", "操作人", "模块", "操作", "结果", "地址"]
    body = [[item.get("createTime"), item.get("operatorName"), item.get("module"), item.get("action"), item.get("resultText"), item.get("ip")] for item in page["list"]]
    return remember_export("operate-log.xlsx", header, body, "operate_log")


def export_login_logs(params: dict) -> dict:
    start, end = _window(params, 90, 90)
    page = login_log_page(Page(1, 100), {**params, "startTime": start.strftime("%Y-%m-%d %H:%M:%S"), "endTime": end.strftime("%Y-%m-%d %H:%M:%S")})
    header = ["时间", "用户", "方式", "结果", "地址"]
    body = [[item.get("createTime"), item.get("username"), item.get("loginWay"), item.get("resultText"), item.get("ip")] for item in page["list"]]
    return remember_export("login-log.xlsx", header, body, "login_log")


def notify_page(page: Page, params: dict) -> dict:
    from app.domains.message.model import NotifyRecord

    session = get_session()
    stmt = select(NotifyRecord)
    if params.get("eventType"):
        stmt = stmt.where(NotifyRecord.event_type == params.get("eventType"))
    if params.get("receiverId"):
        stmt = stmt.where(NotifyRecord.receiver_id == _ident(params.get("receiverId"), "receiverId"))
    if params.get("channel"):
        stmt = stmt.where(NotifyRecord.channel == params.get("channel"))
    if params.get("status"):
        stmt = stmt.where(NotifyRecord.status == params.get("status"))
    if params.get("startTime"):
        stmt = stmt.where(NotifyRecord.create_time >= _when(params.get("startTime"), "startTime"))
    if params.get("endTime"):
        stmt = stmt.where(NotifyRecord.create_time <= _when(params.get("endTime"), "endTime"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(session.scalars(stmt.order_by(NotifyRecord.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    users = {}
    ids = {row.receiver_id for row in rows if row.receiver_id}
    if ids:
        users = {user.id: user.nickname for user in session.scalars(select(User).where(User.id.in_(ids)))}
    channel_text = {"SITE": "站内", "DINGTALK": "钉钉"}
    status_text = {"SENT": "成功", "FAILED": "失败", "DISABLED": "已关闭", "SKIPPED_DUP": "去重跳过", "RETRYING": "失败"}
    data = []
    for row in rows:
        event = _EVENT_TEXT.get(row.event_type)
        if event is None:
            event = row.event_type if row.event_type and any("\u4e00" <= ch <= "\u9fff" for ch in row.event_type) else "业务通知"
        data.append(
            {
                "id": row.id,
                "eventType": event,
                "bizSummary": row.title or "业务记录",
                "receiverName": users.get(row.receiver_id, ""),
                "channel": channel_text.get(row.channel, "站内"),
                "status": row.status,
                "statusText": status_text.get(row.status, "失败"),
                "createTime": row.create_time,
            }
        )
    return page_result(data, int(total or 0), page)


def notify_resend(ident: int) -> dict:
    from app.domains.message.model import NotifyRecord
    from app.domains.message.service import resend

    session = get_session()
    row = session.get(NotifyRecord, ident)
    if row is None or row.deleted:
        raise BizError(1504)
    if row.status != "FAILED":
        raise BizError(1001, "只有失败的通知可以补发")
    sent = session.scalar(
        select(NotifyRecord).where(
            NotifyRecord.biz_key == row.biz_key,
            NotifyRecord.channel == row.channel,
            NotifyRecord.receiver_id == row.receiver_id,
            NotifyRecord.status == "SENT",
            NotifyRecord.id != row.id,
        )
    )
    if sent is not None:
        row.status = "SENT"
        session.flush()
        return {"id": row.id, "status": "SENT", "duplicated": True}
    return resend(ident)


def tenant_page(page: Page) -> dict:
    _platform()
    session = get_session()
    stmt = select(Tenant).execution_options(skip_tenant=True)
    total = session.scalar(select(func.count()).select_from(Tenant).execution_options(skip_tenant=True))
    rows = list(session.scalars(stmt.order_by(Tenant.id.asc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    packages = {row.id: row.name for row in session.scalars(select(TenantPackage).execution_options(skip_tenant=True))}
    data = []
    for row in rows:
        data.append(
            {
                "id": row.id,
                "name": row.name,
                "contactName": row.contact_name,
                "packageId": row.package_id,
                "packageName": packages.get(row.package_id, ""),
                "expireTime": row.expire_time,
                "status": row.status,
            }
        )
    return page_result(data, int(total or 0), page)


def tenant_create(body: dict) -> dict:
    _platform()
    name = str(body.get("name") or "").strip()
    if not name:
        raise BizError(1001, data={"fieldErrors": [{"field": "name", "message": "请填写租户名称"}]})
    package_id = _ident(body.get("packageId"), "packageId")
    session = get_session()
    package = session.get(TenantPackage, package_id)
    if package is None or package.deleted or package.status != "ENABLED":
        raise BizError(1500, data={"field": "packageId"})
    expire = _when(body.get("expireTime"), "expireTime")
    tenant = Tenant(name=name, contact_name=body.get("contactName") or "", package_id=package_id, status="ENABLED", expire_time=expire, tenant_id=1)
    session.add(tenant)
    session.flush()
    username = str(body.get("adminUsername") or "").strip()
    if not _USERNAME.match(username):
        raise BizError(1001, data={"fieldErrors": [{"field": "adminUsername", "message": "管理员用户名不合法"}]})
    mobile = str(body.get("adminMobile") or "").strip()
    if mobile and not _MOBILE.match(mobile):
        raise BizError(1001, data={"fieldErrors": [{"field": "adminMobile", "message": "手机号格式不正确"}]})
    with use_context(system_context(tenant.id)):
        root, _pending = service.init_tenant(tenant.id)
        role = Role(role_key="TENANT_ADMIN", name="租户管理员", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=tenant.id)
        session.add(role)
        session.flush()
        menu_ids = list(session.scalars(select(TenantPackageMenu.menu_id).where(TenantPackageMenu.package_id == package_id).execution_options(skip_tenant=True)))
        for menu_id in menu_ids:
            session.add(RoleMenu(role_id=role.id, menu_id=menu_id, tenant_id=tenant.id))
        created = service.user_create(
            username,
            str(body.get("adminNickname") or name),
            [root.id],
            root.id,
            str(body.get("adminPassword") or ""),
            mobile or None,
        )
        session.add(UserRole(user_id=int(created["id"]), role_id=role.id, source="MANUAL", tenant_id=tenant.id))
        session.flush()
    return {"id": tenant.id, "name": tenant.name, "adminUserId": int(created["id"])}


def tenant_update(ident: int, body: dict) -> dict:
    _platform()
    if ident == 1 and body.get("status") in {"DISABLED", "DELETED"}:
        raise BizError(1290)
    row = get_session().get(Tenant, ident)
    if row is None:
        raise BizError(1504)
    if body.get("name"):
        row.name = body.get("name")
    if "contactName" in body:
        row.contact_name = body.get("contactName")
    if "expireTime" in body:
        row.expire_time = _when(body.get("expireTime"), "expireTime")
    if body.get("status"):
        if ident == 1 and body.get("status") != "ENABLED":
            raise BizError(1290)
        row.status = body.get("status")
    return {"id": row.id, "name": row.name, "status": row.status, "contactName": row.contact_name}


def tenant_assign_package(ident: int, package_id: int) -> dict:
    _platform()
    row = get_session().get(Tenant, ident)
    package = get_session().get(TenantPackage, package_id)
    if row is None or package is None:
        raise BizError(1500)
    row.package_id = package_id
    return {"id": row.id, "packageId": package_id, "packageName": package.name}


def package_page(page: Page) -> dict:
    _platform()
    session = get_session()
    total = session.scalar(select(func.count()).select_from(TenantPackage))
    rows = list(session.scalars(select(TenantPackage).order_by(TenantPackage.id.asc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    data = []
    for row in rows:
        menu_ids = list(session.scalars(select(TenantPackageMenu.menu_id).where(TenantPackageMenu.package_id == row.id).execution_options(skip_tenant=True)))
        data.append({"id": row.id, "packageName": row.name, "status": row.status, "remark": row.remark, "menuIds": menu_ids})
    return page_result(data, int(total or 0), page)


def package_save(body: dict, ident: int | None = None) -> dict:
    _platform()
    name = str(body.get("packageName") or body.get("name") or "").strip()
    if not name:
        raise BizError(1001, data={"fieldErrors": [{"field": "packageName", "message": "请填写套餐名称"}]})
    session = get_session()
    if ident is None:
        row = TenantPackage(name=name, status=body.get("status") or "ENABLED", remark=body.get("remark"), tenant_id=1)
        session.add(row)
        session.flush()
    else:
        row = session.get(TenantPackage, ident)
        if row is None:
            raise BizError(1504)
        row.name = name
        if body.get("status"):
            row.status = body.get("status")
        if "remark" in body:
            row.remark = body.get("remark")
    return {"id": row.id, "packageName": row.name, "status": row.status, "remark": row.remark}


def package_menus(ident: int, menu_ids: list[int]) -> dict:
    _platform()
    session = get_session()
    if session.get(TenantPackage, ident) is None:
        raise BizError(1504)
    session.execute(TenantPackageMenu.__table__.delete().where(TenantPackageMenu.package_id == ident))
    for menu_id in menu_ids:
        if session.get(Menu, menu_id) is None:
            raise BizError(1500, data={"field": "menuIds"})
        session.add(TenantPackageMenu(package_id=ident, menu_id=menu_id, tenant_id=1))
    session.flush()
    return {"id": ident, "menuIds": menu_ids}


def package_delete(ident: int, confirm_name: str) -> dict:
    _platform()
    session = get_session()
    row = session.get(TenantPackage, ident)
    if row is None:
        raise BizError(1504)
    if (confirm_name or "") != row.name:
        raise BizError(1293)
    used = int(session.scalar(select(func.count()).select_from(Tenant).where(Tenant.package_id == ident).execution_options(skip_tenant=True)) or 0)
    if used:
        raise BizError(1289)
    row.deleted = row.id
    return {}


def review_members(param_key: str) -> list[dict]:
    """审核级别参数里的角色成员，再按当前操作者的数据范围过滤。"""
    row = get_session().scalar(select(Param).where(Param.param_key == param_key))
    if row is None or row.value_type != "ROLE_REF" or not row.value:
        return []
    role_id = int(row.value)
    session = get_session()
    user_ids = list(session.scalars(select(UserRole.user_id).where(UserRole.role_id == role_id, UserRole.manual_removed == 0)))
    if not user_ids:
        return []
    ctx = get_ctx()
    scopes = set((ctx.data_scopes if ctx else set()) or set())
    users = list(session.scalars(select(User).where(User.id.in_(user_ids), User.status == "ACTIVE")))
    if ctx and "ALL" not in scopes and not ctx.system:
        if "DEPT" in scopes:
            allowed = set(ctx.dept_ids or [])
            users = [user for user in users if user.main_dept_id in allowed or user.id == ctx.user_id]
        elif "SELF" in scopes:
            users = [user for user in users if user.id == ctx.user_id]
        else:
            users = []
    role = session.get(Role, role_id)
    return [{"id": user.id, "nickname": user.nickname, "roleName": role.name if role else ""} for user in users]


def param_history(param_key: str) -> list[dict]:
    row = get_session().scalar(select(Param).where(Param.param_key == param_key))
    if row is None:
        raise BizError(1213)
    logs = list(get_session().scalars(select(ChangeLog).where(ChangeLog.biz_type == "PARAM", ChangeLog.biz_id == row.id).order_by(ChangeLog.id.desc()).limit(20)))
    return [{"field": item.field_label, "before": item.before_value, "after": item.after_value, "time": item.create_time} for item in logs]
