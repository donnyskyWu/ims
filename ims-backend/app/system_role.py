from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.models import Menu, Role, RoleMenu, RolePerm, Todo, User, UserRole

router = APIRouter()

SCOPES = ("ALL", "DEPT", "IP_GROUP", "SELF")
LEVELS = ("R", "W", "D", "RW", "RWD")

MENUS = [
    (10, 0, "系统管理", "DIR", "", "", 1),
    (11, 10, "用户", "MENU", "/ims/system/user", "system:user:query", 2),
    (12, 10, "角色", "MENU", "/ims/system/role", "system:role:query", 3),
    (13, 10, "菜单", "MENU", "/ims/system/menu", "ops:system:menu", 4),
    (14, 10, "字典", "MENU", "/ims/system/dict", "system:dict:query", 5),
    (15, 10, "参数", "MENU", "/ims/system/param", "system:param:query", 6),
    (20, 0, "权限管理", "DIR", "", "", 7),
    (21, 20, "组织架构", "MENU", "/ims/auth/org", "auth:org:query", 8),
    (22, 20, "岗位供给", "MENU", "/ims/auth/position", "auth:position:query", 9),
    (23, 20, "工作台", "MENU", "/ims/workbench", "auth:workbench:query", 10),
    (16, 10, "日志", "MENU", "/ims/system/log", "system:log:query", 11),
    (17, 10, "通知", "MENU", "/ims/system/notify", "system:notify:query", 12),
]


def seed_roles(db: Session) -> None:
    if db.get(Menu, 11) is None:
        for menu_id, parent_id, name, menu_type, route, perm_code, sort in MENUS:
            db.add(
                Menu(
                    id=menu_id,
                    parent_id=parent_id,
                    name=name,
                    menu_type=menu_type,
                    route=route,
                    perm_code=perm_code,
                    visible=1,
                    sort=sort,
                    tenant_id=0,
                )
            )
        db.flush()
    if db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0)) is None:
        role = Role(
            role_name="系统管理员",
            role_key="sys:admin",
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        for menu in db.scalars(select(Menu).where(Menu.deleted == 0, Menu.perm_code != "")).all():
            db.add(RoleMenu(role_id=role.id, menu_id=menu.id, perm_code=menu.perm_code, tenant_id=0))
            db.add(
                RolePerm(
                    role_id=role.id,
                    module_code=module_of(menu.perm_code),
                    perm_code=menu.perm_code,
                    perm_level="RWD",
                    tenant_id=0,
                )
            )
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        if admin is not None:
            db.add(UserRole(user_id=admin.id, role_id=role.id, tenant_id=0))
    ensure_log_menus(db)


def ensure_log_menus(db: Session) -> None:
    db.flush()
    wanted = [row for row in MENUS if row[0] in (16, 17)]
    role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
    for menu_id, parent_id, name, menu_type, route, perm_code, sort in wanted:
        if db.get(Menu, menu_id) is None:
            db.add(
                Menu(
                    id=menu_id,
                    parent_id=parent_id,
                    name=name,
                    menu_type=menu_type,
                    route=route,
                    perm_code=perm_code,
                    visible=1,
                    sort=sort,
                    tenant_id=0,
                )
            )
            db.flush()
        if role is None:
            continue
        linked = db.scalar(select(RoleMenu).where(RoleMenu.role_id == role.id, RoleMenu.menu_id == menu_id))
        if linked is None:
            db.add(RoleMenu(role_id=role.id, menu_id=menu_id, perm_code=perm_code, tenant_id=0))
            db.add(
                RolePerm(
                    role_id=role.id,
                    module_code=module_of(perm_code),
                    perm_code=perm_code,
                    perm_level="RWD",
                    tenant_id=0,
                )
            )


def module_of(code: str) -> str:
    return code.split(":", 1)[0] or "sys"


def live_role(db: Session, role_id: int) -> Role | None:
    role = db.get(Role, role_id)
    if role is None or role.deleted:
        return None
    return role


def role_menus(db: Session, role_id: int) -> list[RoleMenu]:
    return list(db.scalars(select(RoleMenu).where(RoleMenu.role_id == role_id).order_by(RoleMenu.menu_id)).all())


def role_perms(db: Session, role_id: int) -> list[RolePerm]:
    return list(db.scalars(select(RolePerm).where(RolePerm.role_id == role_id).order_by(RolePerm.perm_code)).all())


def role_vo(db: Session, role: Role) -> dict:
    menus = role_menus(db, role.id)
    perms = role_perms(db, role.id)
    return {
        "id": role.id,
        "roleName": role.role_name,
        "roleKey": role.role_key,
        "menuIds": [row.menu_id for row in menus],
        "permDetail": {row.perm_code: row.perm_level for row in perms},
        "dataScope": role.data_scope,
        "dingtalkPosition": role.dingtalk_position,
        "source": role.source,
        "status": role.status,
    }


def known_menu(db: Session, menu_id: int) -> Menu | None:
    menu = db.get(Menu, menu_id)
    if menu is None or menu.deleted:
        return None
    return menu


def known_code(db: Session, code: str) -> Menu | None:
    return db.scalar(select(Menu).where(Menu.perm_code == code, Menu.deleted == 0))


def refresh_status(db: Session, role: Role) -> None:
    menus = db.scalar(select(func.count(RoleMenu.id)).where(RoleMenu.role_id == role.id)) or 0
    perms = db.scalar(select(func.count(RolePerm.id)).where(RolePerm.role_id == role.id)) or 0
    if menus or perms:
        if role.status == "PENDING_CONFIG":
            role.status = "ENABLED"
    elif role.source == "DINGTALK_AUTO":
        role.status = "PENDING_CONFIG"
    role.updated_at = utcnow()


def user_perm_codes(db: Session, user_id: int) -> list[str]:
    links = db.scalars(select(UserRole).where(UserRole.user_id == user_id)).all()
    codes: set[str] = set()
    for link in links:
        role = live_role(db, link.role_id)
        if role is None or role.status != "ENABLED":
            continue
        for row in role_menus(db, role.id):
            if row.perm_code:
                codes.add(row.perm_code)
        for row in role_perms(db, role.id):
            codes.add(row.perm_code)
    return sorted(codes)


def menu_node(menu: Menu) -> dict:
    return {
        "id": menu.id,
        "name": menu.name,
        "parentId": menu.parent_id,
        "menuType": menu.menu_type,
        "route": menu.route,
        "permCode": menu.perm_code,
        "visible": menu.visible,
        "children": [],
    }


def r1_user_id(db: Session) -> int:
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    return admin.id if admin is not None else 1


def auto_create_role(db: Session, position: str) -> tuple[Role, bool, int | None]:
    existing = db.scalar(select(Role).where(Role.dingtalk_position == position, Role.deleted == 0))
    if existing is not None:
        todo = db.scalar(select(Todo).where(Todo.ref_type == "role", Todo.ref_id == existing.id).order_by(Todo.id.desc()))
        return existing, False, todo.id if todo is not None else None
    role_key = f"dt:{position}"[:64]
    if db.scalar(select(Role).where(Role.role_key == role_key)):
        role_key = f"dt:{position}"[:48] + f":{abs(hash(position)) % 100000}"
    role = Role(
        role_name=position[:64],
        role_key=role_key[:64],
        data_scope="SELF",
        dingtalk_position=position,
        source="DINGTALK_AUTO",
        status="PENDING_CONFIG",
        tenant_id=0,
    )
    db.add(role)
    db.flush()
    todo = Todo(
        assignee_user_id=r1_user_id(db),
        task_type="review",
        ref_type="role",
        ref_id=role.id,
        title=f"新岗位 {position} 已自动建角色，请配置权限",
        content="PENDING_CONFIG 空权限，配置前不放行",
        status="PENDING",
        tenant_id=0,
    )
    db.add(todo)
    db.flush()
    return role, True, todo.id


class MenuBody(BaseModel):
    menuIds: list[int]


class PermBody(BaseModel):
    permDetail: dict[str, str]


class ScopeBody(BaseModel):
    dataScope: str


class PositionBody(BaseModel):
    dingtalkPosition: str | None = None


class FromBody(BaseModel):
    dingtalkPosition: str


class PreviewBody(BaseModel):
    userId: int | str | None = None
    menuIds: list[int] | None = None
    permDetail: dict[str, str] | None = None
    dataScope: str | None = None


@router.get("/system/role/list")
def role_list(db: Session = Depends(db_session), _: User = Depends(current_user)):
    rows = db.scalars(select(Role).where(Role.deleted == 0).order_by(Role.id)).all()
    return ok([role_vo(db, row) for row in rows])


@router.get("/system/menu/tree")
def menu_tree(db: Session = Depends(db_session), _: User = Depends(current_user)):
    rows = db.scalars(select(Menu).where(Menu.deleted == 0).order_by(Menu.sort, Menu.id)).all()
    nodes = {row.id: menu_node(row) for row in rows}
    roots: list[dict] = []
    for row in rows:
        node = nodes[row.id]
        parent = nodes.get(row.parent_id)
        if parent is None:
            roots.append(node)
        else:
            parent["children"].append(node)
    return ok(roots)


@router.put("/system/role/{role_id}/menus")
def save_menus(role_id: int, body: MenuBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    role = live_role(db, role_id)
    if role is None:
        return fail(1504, "资源不可用")
    chosen: list[Menu] = []
    for menu_id in body.menuIds:
        menu = known_menu(db, menu_id)
        if menu is None or not menu.perm_code:
            return fail(1212, "权限码不存在")
        chosen.append(menu)
    db.execute(delete(RoleMenu).where(RoleMenu.role_id == role.id))
    db.flush()
    for menu in chosen:
        db.add(RoleMenu(role_id=role.id, menu_id=menu.id, perm_code=menu.perm_code, tenant_id=role.tenant_id))
    db.flush()
    refresh_status(db, role)
    return ok(role_vo(db, role))


@router.put("/system/role/{role_id}/perm-detail")
def save_perms(role_id: int, body: PermBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    role = live_role(db, role_id)
    if role is None:
        return fail(1504, "资源不可用")
    for code, level in body.permDetail.items():
        if level not in LEVELS:
            return fail(1001, "权限级别非法")
        if known_code(db, code) is None:
            return fail(1212, "权限码不存在")
    db.execute(delete(RolePerm).where(RolePerm.role_id == role.id))
    db.flush()
    for code, level in body.permDetail.items():
        db.add(
            RolePerm(
                role_id=role.id,
                module_code=module_of(code),
                perm_code=code,
                perm_level=level,
                tenant_id=role.tenant_id,
            )
        )
    db.flush()
    refresh_status(db, role)
    return ok(role_vo(db, role))


@router.put("/system/role/{role_id}/data-scope")
def save_scope(role_id: int, body: ScopeBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    role = live_role(db, role_id)
    if role is None:
        return fail(1504, "资源不可用")
    if body.dataScope not in SCOPES:
        return fail(1008, "数据范围非法")
    role.data_scope = body.dataScope
    role.updated_at = utcnow()
    from app.scope import refresh_role_holders

    refresh_role_holders(db, role.id)
    return ok(role_vo(db, role))


@router.put("/system/role/{role_id}/dingtalk-position")
def save_position(role_id: int, body: PositionBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    role = live_role(db, role_id)
    if role is None:
        return fail(1504, "资源不可用")
    position = (body.dingtalkPosition or "").strip() or None
    if position and len(position) > 64:
        return fail(1001, "钉钉岗位不能超过 64 字")
    if position:
        other = db.scalar(
            select(Role).where(Role.dingtalk_position == position, Role.deleted == 0, Role.id != role.id)
        )
        if other is not None:
            return fail(1001, "钉钉岗位已绑定角色")
    role.dingtalk_position = position
    role.updated_at = utcnow()
    return ok(role_vo(db, role))


@router.post("/system/role/from-position")
def from_position(body: FromBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    position = (body.dingtalkPosition or "").strip()
    if not position:
        return fail(1001, "钉钉岗位必填")
    if len(position) > 64:
        return fail(1001, "钉钉岗位不能超过 64 字")
    role, created, todo_id = auto_create_role(db, position)
    return ok(
        {
            "roleId": role.id,
            "roleName": role.role_name,
            "source": role.source,
            "status": role.status,
            "created": created,
            "todoId": todo_id,
            "menuIds": [row.menu_id for row in role_menus(db, role.id)],
            "permDetail": {row.perm_code: row.perm_level for row in role_perms(db, role.id)},
        }
    )


@router.post("/system/role/{role_id}/preview")
def preview(role_id: int, body: PreviewBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    role = live_role(db, role_id)
    if role is None:
        return fail(1504, "资源不可用")
    current_ids = {row.menu_id for row in role_menus(db, role.id)}
    target_ids = set(body.menuIds) if body.menuIds is not None else set(current_ids)
    target_menus: dict[int, Menu] = {}
    for menu_id in target_ids:
        menu = known_menu(db, menu_id)
        if menu is None or not menu.perm_code:
            return fail(1212, "权限码不存在")
        target_menus[menu_id] = menu
    if body.dataScope is not None and body.dataScope not in SCOPES:
        return fail(1008, "数据范围非法")

    def pack(menu_id: int) -> dict:
        menu = known_menu(db, menu_id) or target_menus[menu_id]
        return {"type": "menu", "id": menu.id, "permCode": menu.perm_code, "name": menu.name}

    added = [pack(menu_id) for menu_id in sorted(target_ids - current_ids)]
    removed = [pack(menu_id) for menu_id in sorted(current_ids - target_ids)]
    if body.dataScope and body.dataScope != role.data_scope:
        added.append({"type": "dataScope", "from": role.data_scope, "to": body.dataScope})
    user_codes: list[str] = []
    if body.userId is not None and str(body.userId) != "":
        try:
            user_id = int(body.userId)
        except (TypeError, ValueError):
            return fail(1001, "用户不存在")
        user = db.get(User, user_id)
        if user is None or user.deleted:
            return fail(1504, "资源不可用")
        user_codes = user_perm_codes(db, user_id)
    return ok(
        {
            "added": added,
            "removed": removed,
            "userPermCodes": user_codes,
            "rolePermCodes": sorted({row.perm_code for row in role_menus(db, role.id) if row.perm_code}),
            "pendingIgnored": role.status != "ENABLED",
        }
    )
