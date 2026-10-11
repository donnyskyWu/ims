"""功能权限：角色菜单/功能点并集。空权限 fail-closed，R1（sys:admin）放行。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Menu, Role, RoleMenu, RolePerm, User, UserRole
from app.scope import enabled_roles

PUBLIC_ROUTES = (
    "/ims/workbench",
    "/ims/workbench/todos",
    "/ims/workbench/messages",
)
FUNCTION_SKIP = (
    "/admin-api/ims/auth/workbench",
    "/admin-api/ims/auth/access",
    # 个人工作台「流程待办」只返回当前用户的任务，不要求流程菜单。其余 /flow 仍校验 menu:flow:query。
    "/admin-api/ims/flow/task/my-todo",
    "/admin-api/ims/health",
    # 学习只认被指派人，不要求培训菜单。
    "/admin-api/ims/train/study",
)
# 菜单表尚未覆盖的功能点 → 前端路由。只登记已有种子在用的码，避免把未授权业务页放出来。
EXTRA_ROUTES = {
    "perf:mine": ("/ims/perf/mine",),
}
def _buttons(code: str) -> dict[str, str]:
    if code.endswith(":query"):
        base = code[: -len("query")]
    else:
        base = f"{code}:"
    return {"add": base + "add", "edit": base + "edit", "remove": base + "remove"}


def match_code(path: str) -> str | None:
    from app.menu_catalog import API_RULES

    found = None
    length = -1
    for prefix, code in API_RULES:
        if path.startswith(prefix) and len(prefix) > length:
            found = code
            length = len(prefix)
    return found


def allows(levels: dict[str, str], code: str, method: str) -> bool:
    letters = letters_of(levels.get(code, ""))
    buttons = _buttons(code)
    if method in ("GET", "HEAD"):
        return bool(letters)
    if method == "DELETE":
        return "D" in letters or "W" in letters or bool(levels.get(buttons["remove"]))
    if "W" in letters:
        return True
    if method == "PUT":
        return bool(levels.get(buttons["edit"]))
    return bool(levels.get(buttons["add"]) or levels.get(buttons["edit"]))


# 用户新增/编辑表单要读角色和部门，但不因此放出角色管理或组织菜单。
USER_FORM_READS = (
    "/admin-api/ims/system/role/list",
    "/admin-api/ims/auth/org/users",
)


def holds_user_form(levels: dict[str, str]) -> bool:
    if levels.get("system:user:add") or levels.get("system:user:edit"):
        return True
    letters = letters_of(levels.get("system:user:query", ""))
    return "W" in letters or "D" in letters


def deny_perm():
    from app.api import AuthError

    raise AuthError(403, "无操作权限")


def letters_of(level: str) -> set[str]:
    text = (level or "").upper()
    return {item for item in "RWD" if item in text}


def merge_level(left: str, right: str) -> str:
    found = letters_of(left) | letters_of(right)
    return "".join(item for item in "RWD" if item in found)


def is_admin(db: Session, user: User) -> bool:
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
    if not role_ids:
        return False
    role = db.scalar(
        select(Role).where(
            Role.id.in_(role_ids),
            Role.role_key == "sys:admin",
            Role.deleted == 0,
            Role.status == "ENABLED",
        )
    )
    return role is not None


def level_map(db: Session, user: User) -> dict[str, str]:
    levels: dict[str, str] = {}
    for role in enabled_roles(db, user):
        for row in db.scalars(select(RoleMenu).where(RoleMenu.role_id == role.id)).all():
            if row.perm_code:
                levels[row.perm_code] = merge_level(levels.get(row.perm_code, ""), "R")
        for row in db.scalars(select(RolePerm).where(RolePerm.role_id == role.id)).all():
            if row.perm_code:
                levels[row.perm_code] = merge_level(levels.get(row.perm_code, ""), row.perm_level or "")
    return levels


def describe(db: Session, user: User) -> dict:
    admin = is_admin(db, user)
    levels = level_map(db, user)
    controlled = {
        code
        for code in db.scalars(select(Menu.perm_code).where(Menu.deleted == 0, Menu.perm_code != "")).all()
        if code
    }
    full = admin or (bool(controlled) and controlled <= set(levels))
    routes: set[str] = set(PUBLIC_ROUTES)
    if not full:
        codes = set(levels)
        if codes:
            rows = db.scalars(
                select(Menu).where(Menu.deleted == 0, Menu.visible == 1, Menu.perm_code.in_(codes), Menu.route != "")
            ).all()
            routes.update(row.route for row in rows if row.route)
        for code, extra in EXTRA_ROUTES.items():
            if code in codes:
                routes.update(extra)
    return {
        "admin": admin,
        "fullCatalog": full,
        "permCodes": sorted(levels),
        "permLevels": levels,
        "routes": sorted(routes),
    }


def enforce_function(db: Session, request, user: User) -> None:
    path = request.url.path
    if any(path.startswith(prefix) for prefix in FUNCTION_SKIP):
        return
    if is_admin(db, user):
        return
    levels = level_map(db, user)
    if request.method in ("GET", "HEAD") and path in USER_FORM_READS and holds_user_form(levels):
        return
    code = match_code(path)
    if code is None:
        deny_perm()
    if not allows(levels, code, request.method):
        deny_perm()
