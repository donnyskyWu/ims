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
    "/admin-api/ims/home",
    "/admin-api/ims/health",
)
# 菜单表尚未覆盖的功能点 → 前端路由。只登记已有种子在用的码，避免把未授权业务页放出来。
EXTRA_ROUTES = {
    "perf:mine": ("/ims/perf/mine",),
}
# (methods, prefix, perm_code, need) need: R=持有即可，W=级别含 W
RULES = (
    (("GET", "HEAD"), "/admin-api/ims/system/user", "system:user:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/user", "system:user:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/system/role", "system:role:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/role", "system:role:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/system/menu", "ops:system:menu", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/menu", "ops:system:menu", "W"),
    (("GET", "HEAD"), "/admin-api/ims/system/dict", "system:dict:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/dict", "system:dict:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/system/param", "system:param:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/param", "system:param:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/system/operate-log", "system:log:query", "R"),
    (("GET", "HEAD"), "/admin-api/ims/system/login-log", "system:log:query", "R"),
    (("GET", "HEAD"), "/admin-api/ims/system/notify", "system:notify:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/system/notify", "system:notify:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/auth/org", "auth:org:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/auth/org", "auth:org:query", "W"),
    (("GET", "HEAD"), "/admin-api/ims/auth/position", "auth:position:query", "R"),
    (("POST", "PUT", "DELETE"), "/admin-api/ims/auth/position", "auth:position:query", "W"),
)


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


def match_rule(method: str, path: str) -> tuple[str, str] | None:
    found = None
    length = -1
    for methods, prefix, code, need in RULES:
        if method in methods and path.startswith(prefix) and len(prefix) > length:
            found = (code, need)
            length = len(prefix)
    return found


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
    rule = match_rule(request.method, path)
    levels = level_map(db, user)
    if rule is None:
        if not levels:
            deny_perm()
        return
    code, need = rule
    level = levels.get(code, "")
    if not level:
        deny_perm()
    if need == "W" and "W" not in letters_of(level):
        deny_perm()
