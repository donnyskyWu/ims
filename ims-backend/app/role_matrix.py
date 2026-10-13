"""R1–R11 按 PRD 角色矩阵幂等写入菜单和权限。标准角色与矩阵对齐；自定义角色不改。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.menu_catalog import CATALOG, LEGACY_CODES
from app.models import Menu, Role, RoleMenu, RolePerm, User, UserRole
from app.security import hash_password, password_hash_usable

STANDARD_KEYS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11")

ACCOUNTS = (
    ("tc_r2", "行政管理员", "R2", "13900001002"),
    ("tc_r3", "财务管理员", "R3", "13900001003"),
    ("tc_r4", "运营总监", "R4", "13900001004"),
    ("tc_r5", "直播运营", "R5", "13900001005"),
    ("tc_r5b", "直播运营乙", "R5", "13900001015"),
    ("tc_r6", "短视频运营", "R6", "13900001006"),
    ("tc_r7", "主播", "R7", "13900001007"),
    ("tc_r8", "内容审核员", "R8", "13900001008"),
    ("tc_r9", "数据分析师", "R9", "13900001009"),
    ("tc_r10", "外协人员", "R10", "13900001010"),
    ("tc_r11", "AI 资产管理员", "R11", "13900001011"),
)

SEED_PASSWORD = "Admin@123"
# 标准验收账号。哈希为空或不是 pbkdf2 时补回 SEED_PASSWORD，避免登录接口 500。
SEED_LOGIN_USERS = {username for username, _nickname, _role_key, _mobile in ACCOUNTS} | {"admin"}


def _pack(*pairs: tuple[str, tuple[str, ...]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for level, mods in pairs:
        for mod in mods:
            out[mod] = level
    return out


_ASSETS = (
    "caWechatOfficial", "caWechatChannels", "caDouyin", "caKuaishou", "caXhs",
    "crCompany", "crRealname", "crSim", "crCert",
    "cdOffice", "cdLive", "cdPhone",
)
_ACCOUNTS = ("caWechatOfficial", "caWechatChannels", "caDouyin", "caKuaishou", "caXhs")
_CONTENT = (
    "contentSop", "contentPlan", "contentWork", "contentTask",
    "contentList", "contentLayout", "contentReview", "contentPublish",
)
_FIN = ("finCost", "finProfit", "finDashboard", "finProfitTrace", "finShareRule", "finShareResult", "finLedger")
_BI_REPORT = ("biList", "bi0Report")
_BI_METRIC = ("bi0Metric", "bi0Analysis")
_BI_ANALYSIS = ("queryTool", "bi0Query", "biPreview", "dc", "dcDashboard", "eff")

# None 表示全部菜单 RWD（R1）。数据指标只给 R1/R4/R9，不给 R5/R8。数据报表不给 R8。
ROLE_SPEC: dict[str, tuple[str, str, dict[str, str] | None]] = {
    "R1": ("系统管理员", "ALL", None),
    "R2": (
        "行政管理员",
        "ALL",
        _pack(
            ("R", ("home", "workbench", "authOrg", "authPosition", "live", "liveAlarm", "dailyMine", "dailyTeam", "dailyReview", "dailyStat", "trainStat", "biList", "bi0Report", "alertLive", "alertStats", "alertEscalate", "reportRate")),
            ("RW", _ASSETS + ("meet", "trainMaterial", "trainTask", "flow", "reportSub")),
        ),
    ),
    "R3": (
        "财务管理员",
        "ALL",
        _pack(
            ("R", ("home", "workbench", "live", "liveAlarm") + _ASSETS + ("alertLive", "alertStats", "alertEscalate", "dc", "dcDashboard", "reportRate")),
            ("RWD", ("cost",) + _FIN),
            ("RW", _BI_REPORT + ("flow", "alertRule", "reportTpl", "reportSub")),
        ),
    ),
    "R4": (
        "运营总监",
        "ALL",
        _pack(
            ("R", ("home", "workbench", "authOrg", "authPosition", "ipg") + _ASSETS + ("trainMaterial", "trainStat", "airSkill", "airExpert", "airKb", "airCfg", "alertLive", "alertStats")),
            ("RW", ("live", "liveAlarm") + _CONTENT + ("collectTask", "collectLog", "intWork", "intAccount", "compWork", "compAccount", "comp", "mon", "cost") + _FIN + ("meet", "dailyMine", "dailyTeam", "reportTpl", "reportSub", "reportRate") + _BI_REPORT + _BI_ANALYSIS + ("alertRule", "alertEscalate")),
            ("RWD", ("contentTopic", "dailyReview", "dailyStat", "flow", "perfMetric", "perfCalc", "perfRank", "perfMine", "perfScheme", "perfExec", "perfResult", "perfExam") + _BI_METRIC),
        ),
    ),
    "R5": (
        "直播运营",
        "SELF",
        _pack(
            ("R", ("home", "workbench", "ipg", "liveAlarm", "contentSop", "contentTopic", "contentPlan", "contentWork", "contentTask", "contentList", "contentLayout", "crCert", "cdOffice", "cdLive", "cdPhone", "meet", "perfRank", "perfResult", "bi0Report", "alertLive", "alertEscalate", "comp", "compAccount")),
            ("RW", ("live",) + _ACCOUNTS + ("dailyMine", "flow", "perfExam", "biList", "compWork", "reportSub")),
            ("R", ("perfMine",)),
        ),
    ),
    "R6": (
        "短视频运营",
        "SELF",
        _pack(
            ("R", ("home", "workbench", "contentReview", "meet", "perfRank", "perfResult", "bi0Report", "dcDashboard", "trainMaterial", "alertLive", "alertEscalate", "reportRate", "comp", "compAccount")),
            ("RW", ("contentSop", "contentTopic", "contentPlan", "contentWork", "contentTask", "contentList", "contentLayout", "contentPublish") + _ACCOUNTS + ("dailyMine", "flow", "perfExam", "biList", "compWork", "trainTask", "reportSub")),
            ("R", ("perfMine",)),
        ),
    ),
    "R7": (
        "主播",
        "SELF",
        _pack(
            ("R", ("workbench", "liveAlarm", "contentSop", "contentTask", "contentList", "crCert", "meet", "perfRank", "perfResult", "trainMaterial", "finProfit", "finDashboard", "dc", "alertLive", "alertEscalate")),
            ("RW", ("live", "contentTopic") + _ACCOUNTS + ("perfExam", "trainTask")),
            ("R", ("perfMine",)),
        ),
    ),
    "R8": (
        "内容审核员",
        "ALL",
        _pack(
            ("R", ("home", "workbench", "contentList", "contentPublish", "meet", "comp", "compAccount", "compWork", "perfExam")),
            ("RWD", ("contentReview",)),
            ("RW", ("reportSub", "flow")),
        ),
    ),
    "R9": (
        "数据分析师",
        "ALL",
        _pack(
            ("R", ("home", "workbench", "ipg", "live", "liveAlarm", "contentTopic", "contentList", "contentPublish", "mon") + _ASSETS + ("cost",) + _FIN + ("collectTask", "collectLog", "collectMetadata", "intWork", "intAccount", "compWork", "compAccount", "comp") + _BI_REPORT + _BI_METRIC + _BI_ANALYSIS + ("alertLive", "alertStats", "reportTpl", "reportSub", "reportRate", "trainStat", "meet", "dailyStat", "airSkill", "airExpert", "airKb", "airCfg", "perfRank", "perfResult")),
        ),
    ),
    "R10": (
        "外协人员",
        "SELF",
        _pack(
            ("R", ("workbench", "contentSop", "contentList", "trainMaterial")),
            ("RW", ("contentWork", "contentTask", "dailyMine", "flow", "trainTask", "perfExam", "reportSub")),
        ),
    ),
    "R11": (
        "AI 资产管理员",
        "ALL",
        _pack(
            ("R", ("home", "workbench")),
            ("RWD", ("airSkill", "airExpert", "airKb", "airCfg")),
        ),
    ),
}


def _index():
    by_perm = {row[0]: row for row in CATALOG}
    menu_of: dict[str, str] = {}
    for perm, _parent, _name, menu_type, _route, mod_id, _sort in CATALOG:
        if menu_type == "MENU" and mod_id:
            menu_of[mod_id] = perm
    return by_perm, menu_of


def _ancestors(perm: str, by_perm: dict) -> list[str]:
    found = []
    parent = by_perm[perm][1]
    while parent:
        found.append(parent)
        parent = by_perm[parent][1]
    return found


def _button(perm: str, action: str) -> str:
    if perm.endswith(":query"):
        return perm[: -len("query")] + action
    return f"{perm}:{action}"


def _raise(levels: dict[str, str], code: str, level: str) -> None:
    rank = {"R": 1, "RW": 2, "RWD": 3}
    current = levels.get(code, "")
    if rank.get(level, 0) >= rank.get(current, 0):
        levels[code] = level


def grants_for(role_key: str) -> dict[str, str]:
    """权限码 → 级别。含目录、菜单和应勾选的按钮。"""
    _name, _scope, mods = ROLE_SPEC[role_key]
    by_perm, menu_of = _index()
    if mods is None:
        mods = {mod_id: "RWD" for mod_id in menu_of}
    levels: dict[str, str] = {}

    def put(code: str, level: str) -> None:
        current = levels.get(code, "")
        rank = {"R": 1, "RW": 2, "RWD": 3}
        if rank.get(level, 0) >= rank.get(current, 0):
            levels[code] = level

    for mod_id, level in mods.items():
        perm = menu_of[mod_id]
        put(perm, level)
        for parent in _ancestors(perm, by_perm):
            put(parent, "R")
        if "W" in level:
            put(_button(perm, "add"), "R")
            put(_button(perm, "edit"), "R")
        if "D" in level:
            put(_button(perm, "remove"), "R")
    _apply_eff_relation(role_key, levels)
    _apply_comp_review(role_key, levels)
    _apply_dict_data_read(levels)
    _apply_report_edit(role_key, levels)
    return levels


# EFF-001：查看归属与看板 R1/R2/R4/R5/R6/R7/R9；建立/变更仅 R1、R2；删除仅 R1。
EFF_RELATION_QUERY = "ims:eff:relation:query"
EFF_RELATION_CREATE = "ims:eff:relation:create"
EFF_RELATION_UPDATE = "ims:eff:relation:update"
EFF_RELATION_DELETE = "ims:eff:relation:delete"
_EFF_RELATION_READ = frozenset({"R1", "R2", "R4", "R5", "R6", "R7", "R9"})
_EFF_RELATION_WRITE = frozenset({"R1", "R2"})


def _apply_eff_relation(role_key: str, levels: dict[str, str]) -> None:
    """查看含菜单 menu:eff:query 及其父级。建立/变更只给 R1、R2。删除只给 R1。"""
    by_perm, _menu_of = _index()
    if role_key in _EFF_RELATION_READ:
        _raise(levels, "menu:eff:query", "R")
        for parent in _ancestors("menu:eff:query", by_perm):
            _raise(levels, parent, "R")
        levels[EFF_RELATION_QUERY] = "R"
    if role_key in _EFF_RELATION_WRITE:
        _raise(levels, "menu:eff:add", "R")
        _raise(levels, "menu:eff:edit", "R")
        levels[EFF_RELATION_CREATE] = "R"
        levels[EFF_RELATION_UPDATE] = "R"
    if role_key == "R1":
        _raise(levels, "menu:eff:remove", "R")
        levels[EFF_RELATION_DELETE] = "R"


# 能打开会读字典的页面，就给字典数据读取。不给 system:dict:query，避免放出字典管理菜单。
_DICT_PAGE_PERMS = frozenset({
    "menu:crCompany:query",
    "menu:crRealname:query",
    "menu:crSim:query",
    "menu:crCert:query",
    "menu:cdOffice:query",
    "menu:cdLive:query",
    "menu:cdPhone:query",
    "system:dict:query",
})


def _apply_dict_data_read(levels: dict[str, str]) -> None:
    if _DICT_PAGE_PERMS & set(levels):
        _raise(levels, "system:dict:data:query", "R")


def grant_dict_data_readers(db: Session) -> None:
    """非标准角色同样补字典数据读取。标准角色已由矩阵写入。"""
    menu = db.scalar(select(Menu).where(Menu.deleted == 0, Menu.perm_code == "system:dict:data:query"))
    if menu is None:
        return
    roles = db.scalars(select(Role).where(Role.deleted == 0)).all()
    for role in roles:
        held = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role.id)).all())
        if "system:dict:data:query" in held or not (_DICT_PAGE_PERMS & held):
            continue
        _link(db, role, menu, "R")
    db.flush()


# BI-001：设计/维护报表。R2 仅使用，R7/R8/R10/R11 不设计。分享只读不靠这个码。
REPORT_EDIT_PERM = "bi:report:edit"
_REPORT_EDIT_ROLES = frozenset({"R1", "R3", "R4", "R5", "R6", "R9"})


def _apply_report_edit(role_key: str, levels: dict[str, str]) -> None:
    if role_key in _REPORT_EDIT_ROLES:
        _raise(levels, REPORT_EDIT_PERM, "R")


def _apply_comp_review(role_key: str, levels: dict[str, str]) -> None:
    """竞品提交与初审走按钮码。页面码保持 R，避免 W 连带放行删除。"""
    if role_key in {"R5", "R6"}:
        levels["menu:comp:add"] = "R"
        levels["menu:comp:edit"] = "R"
    elif role_key == "R8":
        levels["menu:comp:edit"] = "R"


def l1_names(role_key: str) -> list[str]:
    """该角色菜单会点亮的侧栏 L1。工作台因公开入口始终可见，这里只列授权菜单所在组。"""
    by_perm, _menu_of = _index()
    names: list[str] = []
    for code in grants_for(role_key):
        row = by_perm.get(code)
        if row is None or row[1]:
            continue
        if row[2] not in names:
            names.append(row[2])
    return names


def _module_of(code: str) -> str:
    return code.split(":", 1)[0] or "sys"


def ensure_menus(db: Session) -> None:
    by_perm = {row.perm_code: row for row in db.scalars(select(Menu).where(Menu.deleted == 0, Menu.perm_code != "")).all() if row.perm_code}
    id_of: dict[str, int] = {}
    for perm, parent, name, menu_type, route, _mod, sort in CATALOG:
        row = by_perm.get(perm)
        if row is None and menu_type == "DIR":
            row = db.scalar(
                select(Menu).where(Menu.deleted == 0, Menu.menu_type == "DIR", Menu.name == name, Menu.perm_code == "")
            )
        if row is None and route and menu_type == "MENU":
            row = db.scalar(select(Menu).where(Menu.deleted == 0, Menu.route == route, Menu.menu_type == "MENU"))
        if row is None:
            row = Menu(
                parent_id=0,
                name=name,
                menu_type=menu_type,
                route=route,
                perm_code=perm,
                visible=1,
                sort=sort,
                tenant_id=0,
            )
            db.add(row)
            db.flush()
        else:
            row.name = name
            row.menu_type = menu_type
            row.perm_code = perm
            row.sort = sort
            row.route = route
            row.deleted = 0
        by_perm[perm] = row
        id_of[perm] = row.id
    for perm, parent, _name, _menu_type, _route, _mod, _sort in CATALOG:
        row = by_perm[perm]
        row.parent_id = id_of.get(parent, 0)
    db.flush()


def _link(db: Session, role: Role, menu: Menu, level: str) -> None:
    linked = db.scalar(select(RoleMenu).where(RoleMenu.role_id == role.id, RoleMenu.menu_id == menu.id))
    if linked is None:
        db.add(RoleMenu(role_id=role.id, menu_id=menu.id, perm_code=menu.perm_code, tenant_id=role.tenant_id or 0))
    held = db.scalar(select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code == menu.perm_code))
    if held is None:
        db.add(
            RolePerm(
                role_id=role.id,
                module_code=_module_of(menu.perm_code),
                perm_code=menu.perm_code,
                perm_level=level,
                tenant_id=role.tenant_id or 0,
            )
        )


def _sync_grants(db: Session, role: Role, levels: dict[str, str]) -> None:
    """标准角色以矩阵为准：补缺、改级别、去掉矩阵外的旧授权。"""
    for row in list(db.scalars(select(RolePerm).where(RolePerm.role_id == role.id)).all()):
        wanted = levels.get(row.perm_code or "")
        if wanted is None:
            db.delete(row)
        elif (row.perm_level or "") != wanted:
            row.perm_level = wanted
    for row in list(db.scalars(select(RoleMenu).where(RoleMenu.role_id == role.id)).all()):
        if (row.perm_code or "") not in levels:
            db.delete(row)
    db.flush()
    _grant_missing(db, role, levels)


def _grant_missing(db: Session, role: Role, levels: dict[str, str]) -> None:
    menus = {
        row.perm_code: row
        for row in db.scalars(select(Menu).where(Menu.deleted == 0, Menu.perm_code != "")).all()
    }
    for code, level in levels.items():
        menu = menus.get(code)
        if menu is None:
            continue
        _link(db, role, menu, level)


def _ensure_role(db: Session, role_key: str) -> Role:
    name, scope, _mods = ROLE_SPEC[role_key]
    role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
    if role is None:
        role = Role(
            role_name=name,
            role_key=role_key,
            data_scope=scope,
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    else:
        if role.data_scope != scope:
            role.data_scope = scope
        if role.status != "ENABLED":
            role.status = "ENABLED"
        if not role.role_name:
            role.role_name = name
    _sync_grants(db, role, grants_for(role_key))
    return role


def _grant_admin(db: Session) -> None:
    role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
    if role is None:
        return
    levels = {perm: "RWD" for perm, _parent, _name, _typ, _route, _mod, _sort in CATALOG}
    _grant_missing(db, role, levels)


def _backfill_full_clones(db: Session) -> None:
    """原先克隆了全部系统菜单的角色，补上新增业务菜单，避免升级后从全量变成只剩系统管理。"""
    levels = {perm: "RWD" for perm, _parent, _name, _typ, _route, _mod, _sort in CATALOG}
    roles = db.scalars(select(Role).where(Role.deleted == 0)).all()
    for role in roles:
        if role.role_key in STANDARD_KEYS or role.role_key == "sys:admin":
            continue
        held = set(db.scalars(select(RolePerm.perm_code).where(RolePerm.role_id == role.id)).all())
        if LEGACY_CODES <= held:
            _grant_missing(db, role, levels)


def restore_seed_password(user: User, password: str) -> None:
    """验收账号哈希缺失时，用种子密码补上。空哈希进 verify_password 会抛 TypeError，登录变成 500。"""
    if user.username not in SEED_LOGIN_USERS or password != SEED_PASSWORD:
        return
    if password_hash_usable(user.password_hash):
        return
    user.password_hash = hash_password(SEED_PASSWORD)


def repair_seed_passwords(db: Session) -> None:
    users = db.scalars(select(User).where(User.username.in_(SEED_LOGIN_USERS), User.deleted == 0)).all()
    for user in users:
        restore_seed_password(user, SEED_PASSWORD)


def commit_seed_passwords() -> None:
    """单独提交。后面的种子失败回滚时，验收账号仍能用种子密码登录。"""
    from sqlalchemy import inspect

    from app.core import SessionLocal, engine

    if "ims_sys_user" not in set(inspect(engine).get_table_names()):
        return
    db = SessionLocal()
    try:
        repair_seed_passwords(db)
        db.commit()
    finally:
        db.close()


def _ensure_accounts(db: Session) -> None:
    from app.scope import refresh_user_scope

    roles = {key: db.scalar(select(Role).where(Role.role_key == key, Role.deleted == 0)) for key in STANDARD_KEYS}
    for username, nickname, role_key, mobile in ACCOUNTS:
        role = roles[role_key]
        if role is None:
            continue
        user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if user is None:
            user = User(
                username=username,
                nickname=nickname,
                mobile=mobile,
                password_hash=hash_password(SEED_PASSWORD),
                status="ENABLED",
                tenant_id=0,
            )
            db.add(user)
            db.flush()
        else:
            user.status = "ENABLED"
            if not user.nickname:
                user.nickname = nickname
            if not password_hash_usable(user.password_hash):
                user.password_hash = hash_password(SEED_PASSWORD)
        links = list(db.scalars(select(UserRole).where(UserRole.user_id == user.id)).all())
        keep = None
        for link in links:
            if link.role_id == role.id:
                keep = link
            else:
                db.delete(link)
        if keep is None:
            db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.flush()
        refresh_user_scope(db, user.id)


# 给 E2E 留的非标准角色。不删除（e2e_fin_r9 / e2e_acct_r3 等仍登录），只改显示名并去掉组织人效写权限。
E2E_LEGACY_ROLE_NAMES = {
    "fin:r9": "E2E专用-数据分析师",
    "acct:r3": "E2E专用-财务管理员",
    "acct:peer": "E2E专用-账号流转同事",
    "acct:sum": "E2E专用-账号汇总同事",
    "bi:dept-viewer": "E2E专用-BI 本部门查看",
    "live:r4": "E2E专用-运营总监",
}
_EFF_WRITE_CODES = (
    EFF_RELATION_CREATE,
    EFF_RELATION_UPDATE,
    EFF_RELATION_DELETE,
    "menu:eff:add",
    "menu:eff:edit",
    "menu:eff:remove",
)


def normalize_e2e_legacy_roles(db: Session) -> None:
    """幂等：显示名写成映射全称，去掉这些角色的组织人效建立/变更/删除。

    赋的是完整显示名，已有前缀不会再叠一层。
    """
    for role_key, display in E2E_LEGACY_ROLE_NAMES.items():
        role = db.scalar(select(Role).where(Role.role_key == role_key, Role.deleted == 0))
        if role is None:
            continue
        if role.role_name != display:
            role.role_name = display
        for row in list(
            db.scalars(
                select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code.in_(_EFF_WRITE_CODES))
            ).all()
        ):
            db.delete(row)
        for row in list(
            db.scalars(
                select(RoleMenu).where(RoleMenu.role_id == role.id, RoleMenu.perm_code.in_(_EFF_WRITE_CODES))
            ).all()
        ):
            db.delete(row)
        query = db.scalar(
            select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code == "menu:eff:query")
        )
        if query is not None and ("W" in (query.perm_level or "") or "D" in (query.perm_level or "")):
            query.perm_level = "R"
    db.flush()


def commit_e2e_legacy_roles() -> None:
    """单独提交改名。后面的种子失败回滚时，显示名和人效写权限不再被一起撤掉。"""
    from sqlalchemy import inspect

    from app.core import SessionLocal, engine

    if "ims_sys_role" not in set(inspect(engine).get_table_names()):
        return
    db = SessionLocal()
    try:
        normalize_e2e_legacy_roles(db)
        db.commit()
    finally:
        db.close()


def ensure_role_matrix(db: Session) -> None:
    ensure_menus(db)
    _grant_admin(db)
    for role_key in STANDARD_KEYS:
        _ensure_role(db, role_key)
    _backfill_full_clones(db)
    _ensure_accounts(db)
    normalize_e2e_legacy_roles(db)
    grant_dict_data_readers(db)
    db.flush()
