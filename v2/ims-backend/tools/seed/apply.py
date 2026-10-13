"""幂等种子。已存在的菜单名、参数值不覆盖。培训 AI 不进系统参数。"""
from __future__ import annotations

from sqlalchemy import select

from app.catalog import DICT_ROWS, DICT_TYPE_NAMES, MENU_TREE
from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import get_session
from app.domains.system.model import (
    DictData,
    DictType,
    Menu,
    Param,
    Role,
    RoleMenu,
    Tenant,
    TenantPackage,
    TenantPackageMenu,
    User,
    UserRole,
)
from app.domains.system.service import init_tenant

ROLES = [
    (101, "R1", "系统管理员", "ALL"),
    (102, "R2", "行政管理员", "ALL"),
    (103, "R3", "财务", "ALL"),
    (104, "R4", "运营管理者", "ALL"),
    (105, "R5", "运营组长", "DEPT"),
    (106, "R6", "审核", "DEPT"),
    (107, "R7", "运营人员", "SELF"),
    (108, "R8", "内容编辑", "DEPT"),
    (109, "R9", "数据分析师", "ALL"),
    (110, "R10", "外协", "SELF"),
    (111, "R11", "AI资产管理员", "ALL"),
]

PARAMS = [
    ("perf.grade.excellent", "优秀线", "通用", "NUMBER", "85", "0", "100"),
    ("perf.grade.qualified", "合格线", "通用", "NUMBER", "60", "0", "100"),
    ("content.review.level1.role", "一级审核角色", "内容审核", "ROLE_REF", "", None, None),
    ("content.review.level2.role", "二级审核角色", "内容审核", "ROLE_REF", "", None, None),
    ("work.task.confirm.auto-ai-generate", "任务确认后自动生成", "内容审核", "BOOLEAN", "false", None, None),
    ("dingtalk.notify.enabled", "钉钉工作通知", "钉钉", "BOOLEAN", "true", None, None),
    ("dingtalk.sync.enabled", "组织同步开关", "钉钉", "BOOLEAN", "true", None, None),
    ("dingtalk.app_key", "钉钉应用标识", "钉钉", "TEXT", "test-app-key", None, None),
    ("dingtalk_attendance.enabled", "启用考勤", "钉钉考勤", "BOOLEAN", "true", None, None),
    ("dingtalk_attendance.mode", "考勤模式", "钉钉考勤", "ENUM", "mock", None, None, ["mock", "real"]),
    ("dingtalk_attendance.app_key", "考勤应用标识", "钉钉考勤", "TEXT", "test-att-key", None, None),
    ("dingtalk_attendance.app_secret", "考勤应用密钥", "钉钉考勤", "SECRET", "", None, None),
    ("dingtalk_attendance.base_url", "考勤接口地址", "钉钉考勤", "TEXT", "http://127.0.0.1:9", None, None),
    ("dingtalk_attendance.timeout_ms", "考勤超时毫秒", "钉钉考勤", "NUMBER", "1000", "100", "60000"),
    ("air.key.ip_whitelist.enabled", "内容密钥地址限制", "AI", "BOOLEAN", "false", None, None),
    ("air.model.base_url", "内容模型地址", "内容审核", "TEXT", "http://127.0.0.1:9/air", None, None),
    ("notify.cert.yellow", "证件黄色预警", "证件", "TEXT", "证件将在 30 天内到期，请尽快换证。", None, None),
    ("notify.cert.red", "证件红色预警", "证件", "TEXT", "证件将在 7 天内到期，请立即换证。", None, None),
    ("notify.cert.locked", "证件锁定通知", "证件", "TEXT", "证件已过期并锁定，请完成换证。", None, None),
    ("notify.cert.remind", "证件催办通知", "证件", "TEXT", "请尽快办理证件换证。", None, None),
    ("notify.cert.reject", "证件驳回通知", "证件", "TEXT", "证件审核未通过，请重新上传。", None, None),
    ("notify.asset.checkout", "资产领用通知", "资产", "TEXT", "你已领用资产 {编号}", None, None),
    ("notify.asset.transfer", "资产流转通知", "资产", "TEXT", "资产 {编号} 已流转", None, None),
    ("notify.asset.verify.dispatch", "校验工单派发", "资产", "TEXT", "请处理资产关联异常", None, None),
    ("notify.asset.verify.overdue", "校验逾期升级", "资产", "TEXT", "校验工单已超过限期", None, None),
    ("notify.asset.verify.reject", "校验复审退回", "资产", "TEXT", "校验工单复审未通过", None, None),
]


def apply(env: str = "test") -> None:
    session = get_session()
    with use_context(system_context(1)):
        _packages(session)
        _dicts(session)
        menus = _menus(session)
        _bind_pages(session)
        _params(session)
        _roles(session, menus)
        _standard_package(session)
        _users(session)
        _tenant_dept(session)
        if env == "e2e":
            _e2e_roles(session)
        session.flush()
        from app.domains.flow.presets import ensure_presets

        ensure_presets()


def _packages(session):
    if session.get(TenantPackage, 1) is None:
        session.add(TenantPackage(id=1, name="全量", status="ENABLED", tenant_id=1))
    if session.get(Tenant, 1) is None:
        session.add(Tenant(id=1, name="平台", package_id=1, status="ENABLED", tenant_id=1))
    session.flush()


def _dicts(session):
    for key, name in DICT_TYPE_NAMES.items():
        if session.scalar(select(DictType).where(DictType.dict_type == key)) is None:
            session.add(DictType(dict_type=key, name=name, status="ENABLED", tenant_id=1))
    session.flush()
    for dict_type, value, label, color, ext in DICT_ROWS:
        exists = session.scalar(select(DictData).where(DictData.dict_type == dict_type, DictData.dict_value == value))
        if exists is None:
            session.add(
                DictData(
                    dict_type=dict_type,
                    dict_value=value,
                    dict_label=label,
                    color_type=color,
                    status="ENABLED",
                    is_builtin=1,
                    ext_code=ext,
                    tenant_id=1,
                )
            )
    session.flush()


def _menus(session):
    by_perm = {}
    created = []

    def ensure(name, parent_id, type_, perm, path, sort):
        row = None
        if perm:
            row = session.scalar(select(Menu).where(Menu.perm_code == perm))
        if row is None:
            row = session.scalar(select(Menu).where(Menu.name == name, Menu.parent_id == parent_id, Menu.type == type_))
        if row is None:
            row = Menu(
                name=name,
                type=type_,
                perm_code=perm,
                path=path,
                parent_id=parent_id,
                sort=sort,
                status="ENABLED",
                tenant_id=1,
            )
            session.add(row)
            session.flush()
            created.append(row.id)
        if perm:
            by_perm[perm] = row
        return row

    def walk(items, parent_id):
        for index, child in enumerate(items):
            type_ = child.get("type") or "BUTTON"
            row = ensure(child["name"], parent_id, type_, child.get("perm"), child.get("path"), child.get("sort") or index)
            if child.get("children"):
                walk(child["children"], row.id)

    for item in MENU_TREE:
        parent = ensure(item["name"], 0, "DIR", None, item.get("path"), item.get("sort") or 0)
        walk(item.get("children") or [], parent.id)
    linked = set(session.scalars(select(TenantPackageMenu.menu_id).where(TenantPackageMenu.package_id == 1)))
    if not linked:
        created = [menu.id for menu in session.scalars(select(Menu))]
    for menu_id in created:
        if menu_id not in linked:
            session.add(TenantPackageMenu(package_id=1, menu_id=menu_id, tenant_id=1))
    _paint_icons(session)
    session.flush()
    return by_perm


def _paint_icons(session):
    """只给还没有图标的菜单补名字，已有图标保持不动。"""
    from app.menu_icons import icon_for

    for menu in session.scalars(select(Menu)):
        if menu.icon:
            continue
        found = icon_for(menu.path, menu.name)
        if found:
            menu.icon = found


def _params(session):
    for row in PARAMS:
        key, name, group, value_type, value, lo, hi = row[:7]
        options = row[7] if len(row) > 7 else None
        found = session.scalar(select(Param).where(Param.param_key == key))
        if found is None:
            session.add(
                Param(
                    param_key=key,
                    name=name,
                    group_name=group,
                    value_type=value_type,
                    value=value,
                    default_value=value,
                    min_value=lo,
                    max_value=hi,
                    options=options,
                    is_builtin=1,
                    tenant_id=1,
                )
            )
    session.flush()


def _roles(session, menus):
    all_codes = list(menus)
    for ident, key, name, scope in ROLES:
        row = session.get(Role, ident)
        if row is None:
            row = Role(
                id=ident,
                role_key=key,
                name=name,
                source="MANUAL",
                status="ENABLED",
                data_scope=scope,
                is_standard=1,
                tenant_id=1,
            )
            session.add(row)
            session.flush()
        linked = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == ident)))
        codes = _codes_for(key, all_codes)
        domain = _FLOW_DOMAIN_VALUE.get(key)
        if domain and row.flow_domain != domain:
            row.flow_domain = domain
        for code in codes:
            menu = menus[code]
            if menu.id not in linked:
                session.add(RoleMenu(role_id=ident, menu_id=menu.id, tenant_id=1))
    session.flush()


_ORG_QUERY = "ims:system:org-sync:query"
_ORG_RUN = "ims:system:org-sync:run"
_ORG_EXPORT = "ims:system:org-sync:export"
_POS_QUERY = "ims:auth:position-rule:query"
_POS_PREFIX = "ims:auth:position-rule:"


_R2_CODES = {
    "ims:system:user:query",
    "ims:system:user:export",
    "ims:system:dept:query",
    "ims:system:role:query",
    "ims:system:dict:query",
    "ims:system:log:query",
}


_FLOW_DOMAIN_VALUE = {"R2": "ADMIN", "R3": "FINANCE", "R4": "BUSINESS,COMMON"}
_FLOW_OPERATE = [
    "ims:flow:template:query",
    "ims:flow:template:create",
    "ims:flow:template:publish",
    "ims:flow:instance:start",
    "ims:flow:board:query",
    "ims:flow:timeout:query",
    "ims:flow:timeout:urge",
    "ims:flow:task:handle",
    "ims:flow:instance:manage",
]
_FLOW_NARROW_STRIP = {
    "ims:flow:template:query",
    "ims:flow:template:create",
    "ims:flow:template:publish",
    "ims:flow:template:delete",
    "ims:flow:instance:start",
    "ims:flow:instance:cancel",
    "ims:flow:instance:manage",
    "ims:flow:board:query",
    "ims:flow:timeout:query",
    "ims:flow:timeout:urge",
    "ims:flow:version:rollback",
}


def _with_workbench(codes: list[str], all_codes: list[str]) -> list[str]:
    merged = list(codes)
    leaf = "ims:workbench:query"
    if leaf in all_codes and leaf not in merged:
        merged.append(leaf)
    return [code for code in merged if code in all_codes]


def _with_flow(key: str, codes: list[str], all_codes: list[str]) -> list[str]:
    merged = list(codes)
    extra: list[str] = []
    if key in {"R2", "R3", "R4"}:
        extra = list(_FLOW_OPERATE)
    elif key in {"R5", "R6", "R7", "R8", "R10", "R11"}:
        merged = [code for code in merged if code not in _FLOW_NARROW_STRIP]
        extra = ["ims:flow:task:handle"]
    elif key == "R9":
        extra = ["ims:flow:template:query", "ims:flow:board:query", "ims:flow:timeout:query", "ims:flow:task:handle"]
    for code in extra:
        if code in all_codes and code not in merged:
            merged.append(code)
    return merged


def _resource_grant(key: str, all_codes: list[str]) -> list[str]:
    resource = [code for code in all_codes if code.startswith("ims:corp:") or code.startswith("ims:cert:")]
    bag = set(resource)
    query = [
        "ims:corp:company:query",
        "ims:corp:realname:query",
        "ims:corp:sim:query",
        "ims:cert:archive:query",
        "ims:cert:expire:query",
    ]
    if key == "R1":
        return sorted(bag)
    if key == "R2":
        return sorted(code for code in bag if not code.startswith("ims:cert:security:"))
    if key == "R4":
        return [code for code in [*query, "ims:cert:archive:metrics"] if code in bag]
    if key == "R9":
        return sorted(code for code in bag if code.endswith(":query") and "plain" not in code and not code.startswith("ims:cert:security:"))
    if key == "R5":
        return [code for code in ("ims:cert:expire:query",) if code in bag]
    if key == "R7":
        return [code for code in ("ims:cert:archive:query", "ims:cert:expire:query") if code in bag]
    return []


def _shape_resource(key: str, codes: list[str], all_codes: list[str]) -> list[str]:
    resource = {code for code in all_codes if code.startswith("ims:corp:") or code.startswith("ims:cert:")}
    kept = [code for code in codes if code not in resource]
    return kept + _resource_grant(key, all_codes)


def _device_codes(all_codes: list[str]) -> set[str]:
    return {code for code in all_codes if code.startswith("ims:device:") or code.startswith("ims:asset:")}


def _device_grant(key: str, all_codes: list[str]) -> list[str]:
    bag = _device_codes(all_codes)

    def keep(codes: list[str]) -> list[str]:
        return [code for code in codes if code in bag]

    phone_query = "ims:device:phone:query"
    asset_query = "ims:device:asset:query"
    forward_query = "ims:asset:forward:query"
    reverse_query = "ims:asset:reverse:query"
    if key == "R1":
        return sorted(bag)
    if key == "R2":
        return sorted(code for code in bag if code != "ims:asset:cost:masked")
    if key == "R3":
        return keep([asset_query, forward_query, reverse_query, "ims:asset:cost:view"])
    if key == "R4":
        return keep(
            [
                phone_query,
                asset_query,
                "ims:device:asset:export",
                forward_query,
                "ims:asset:forward:export",
                reverse_query,
                "ims:asset:reverse:export",
                "ims:asset:cost:view",
                "ims:asset:verify:query",
            ]
        )
    if key == "R5":
        return keep([asset_query, forward_query, reverse_query])
    if key == "R9":
        return keep([phone_query, asset_query, forward_query, reverse_query, "ims:asset:cost:masked", "ims:asset:verify:query"])
    return []


def _shape_device(key: str, codes: list[str], all_codes: list[str]) -> list[str]:
    device = _device_codes(all_codes)
    kept = [code for code in codes if code not in device]
    return kept + _device_grant(key, all_codes)


def _account_codes(all_codes: list[str]) -> set[str]:
    return {code for code in all_codes if code.startswith("ims:corp:account") or code.startswith("ims:account:")}


def _account_grant(key: str, all_codes: list[str]) -> list[str]:
    bag = _account_codes(all_codes)
    if key == "R1":
        return sorted(bag)
    groups = {
        "R2": [
            "ims:corp:account:query",
            "ims:corp:account:create",
            "ims:corp:account:update",
            "ims:corp:account:delete",
            "ims:corp:account:export",
            "ims:corp:account:collect",
            "ims:corp:account:personal:query",
            "ims:corp:account:personal:create",
            "ims:corp:account:personal:update",
            "ims:corp:account:personal:delete",
            "ims:corp:account:personal:export",
            "ims:account:apply:query",
            "ims:account:apply:create",
            "ims:account:apply:confirm",
            "ims:account:transfer:query",
            "ims:account:transfer:create",
            "ims:account:transfer:confirm",
            "ims:account:transfer:revoke",
            "ims:account:return:query",
            "ims:account:return:generate",
            "ims:account:return:handle",
            "ims:account:return:close",
            "ims:account:timeline:query",
            "ims:account:timeline:export",
        ],
        "R3": [
            "ims:corp:account:query",
            "ims:account:return:query",
            "ims:account:recharge:query",
            "ims:account:recharge:create",
            "ims:account:recharge:update",
            "ims:account:recharge:verify",
            "ims:account:recharge:export",
            "ims:account:recharge:voucher",
            "ims:account:timeline:query",
        ],
        "R4": [
            "ims:corp:account:query",
            "ims:corp:account:export",
            "ims:corp:account:personal:query",
            "ims:account:apply:query",
            "ims:account:apply:confirm",
            "ims:account:apply:approve",
            "ims:account:transfer:query",
            "ims:account:transfer:create",
            "ims:account:transfer:confirm",
            "ims:account:transfer:revoke",
            "ims:account:return:query",
            "ims:account:recharge:query",
            "ims:account:recharge:export",
            "ims:account:timeline:query",
            "ims:account:timeline:export",
        ],
        "R5": [
            "ims:corp:account:query",
            "ims:account:apply:query",
            "ims:account:apply:create",
            "ims:account:transfer:query",
            "ims:account:transfer:create",
            "ims:account:transfer:confirm",
            "ims:account:timeline:query",
        ],
        "R6": [
            "ims:corp:account:query",
            "ims:account:apply:query",
            "ims:account:apply:create",
            "ims:account:transfer:query",
            "ims:account:transfer:confirm",
            "ims:account:timeline:query",
        ],
        "R7": [
            "ims:corp:account:query",
            "ims:account:apply:query",
            "ims:account:apply:create",
            "ims:account:transfer:query",
            "ims:account:transfer:confirm",
            "ims:account:timeline:query",
        ],
        "R9": [
            "ims:corp:account:query",
            "ims:corp:account:personal:query",
            "ims:account:apply:query",
            "ims:account:transfer:query",
            "ims:account:return:query",
            "ims:account:recharge:query",
            "ims:account:timeline:query",
        ],
    }
    return [code for code in groups.get(key, []) if code in bag]


def _shape_account(key: str, codes: list[str], all_codes: list[str]) -> list[str]:
    account = _account_codes(all_codes)
    kept = [code for code in codes if code not in account]
    return kept + _account_grant(key, all_codes)


def _ipg_codes(all_codes: list[str]) -> set[str]:
    return {code for code in all_codes if code.startswith("ims:ip-group:")}


def _ipg_grant(key: str, all_codes: list[str]) -> list[str]:
    """IP 组权限按角色补齐。R8/R10 不授菜单。"""
    bag = _ipg_codes(all_codes)
    query = sorted(code for code in bag if code.endswith(":query"))
    operate = [code for code in ("ims:ip-group:member", "ims:ip-group:account", "ims:ip-group:anchor") if code in bag]
    write = [
        code
        for code in (
            "ims:ip-group:create",
            "ims:ip-group:update",
            "ims:ip-group:delete",
            "ims:ip-group:author:create",
            "ims:ip-group:author:update",
            "ims:ip-group:author:delete",
            "ims:ip-group:author:export",
        )
        if code in bag
    ]
    if key == "R1":
        return sorted(bag)
    if key in {"R8", "R10", "R11"}:
        return []
    if key in {"R2", "R3", "R9"}:
        return query
    if key == "R4":
        return query + write + operate
    if key in {"R5", "R6", "R7"}:
        return query + operate
    return []


def _shape_ipg(key: str, codes: list[str], all_codes: list[str]) -> list[str]:
    owned = _ipg_codes(all_codes)
    kept = [code for code in codes if code not in owned]
    return kept + _ipg_grant(key, all_codes)


def _codes_for(key: str, all_codes: list[str]) -> list[str]:
    if key == "R2":
        codes = [code for code in all_codes if code in _R2_CODES]
        codes.extend([code for code in (_ORG_QUERY, _ORG_EXPORT, _POS_QUERY) if code in all_codes])
        shaped = _shape_account(key, _shape_device(key, _shape_resource(key, _with_flow(key, _with_workbench(codes, all_codes), all_codes), all_codes), all_codes), all_codes)
        return _shape_ipg(key, shaped, all_codes)
    if key == "R1":
        base = list(all_codes)
    elif key == "R9":
        base = [code for code in all_codes if code.endswith(":query") and "plain" not in code]
    elif key == "R3":
        base = [code for code in all_codes if "plain" in code or code.endswith(":query") or code.startswith("ims:system:")]
    elif key in {"R5", "R7", "R10"}:
        base = [code for code in all_codes if code.endswith(":query")]
    else:
        base = [code for code in all_codes if code.startswith("ims:system:")]
    managed = {code for code in all_codes if code.startswith(_POS_PREFIX) or code in {_ORG_QUERY, _ORG_RUN, _ORG_EXPORT}}
    codes = [code for code in base if code not in managed]
    if key == "R1":
        codes.extend(sorted(managed))
    elif key in {"R2", "R4"}:
        codes.extend([_ORG_QUERY, _ORG_EXPORT, _POS_QUERY])
    shaped = _shape_account(key, _shape_device(key, _shape_resource(key, _with_flow(key, _with_workbench(codes, all_codes), all_codes), all_codes), all_codes), all_codes)
    return _shape_ipg(key, shaped, all_codes)


def _users(session):
    password = hash_password("Abc12345")
    if session.get(User, 1) is None:
        session.add(User(id=1, username="admin", nickname="超级管理员", password_hash=password, status="ACTIVE", tenant_id=1, source="LOCAL"))
        session.flush()
        session.add(UserRole(user_id=1, role_id=101, source="MANUAL", tenant_id=1))
    if session.get(User, 8) is None:
        session.add(User(id=8, username="data-migration", nickname="数据迁移", password_hash=password, status="ACTIVE", tenant_id=1, source="LOCAL"))
    session.flush()


def _tenant_dept(session):
    from app.domains.system.model import Dept

    if session.get(Dept, 10) is None:
        init_tenant(1, root_id=10, pending_id=15)


_PAGE_BIND = {
    "ims:system:user:query": ("/ims/system/user", "用户"),
    "ims:system:role:query": ("/ims/system/role", "角色"),
    "ims:system:menu:query": ("/ims/system/menu", "菜单"),
    "ims:system:dict:query": ("/ims/system/dict", "字典"),
    "ims:system:param:query": ("/ims/system/param", "参数"),
    "ims:system:log:query": ("/ims/system/log", "日志"),
    "ims:system:notify:query": ("/ims/system/notify", "通知"),
    "ims:tenant:query": ("/ims/system/tenant", "租户套餐"),
}


def _bind_pages(session):
    """已有按钮补上页面路由。种子菜单的权限码仍唯一，不另建一条。"""
    for perm, (path, name) in _PAGE_BIND.items():
        row = session.scalar(select(Menu).where(Menu.perm_code == perm))
        if row is None:
            continue
        if not row.path:
            row.path = path
        if row.type == "BUTTON":
            row.type = "MENU"
        if row.name.endswith("查询") and row.type == "MENU":
            row.name = name
    session.flush()


def _standard_package(session):
    row = session.scalar(select(TenantPackage).where(TenantPackage.name == "标准套餐"))
    if row is None:
        row = TenantPackage(name="标准套餐", status="ENABLED", remark="本期已交付菜单", tenant_id=1)
        session.add(row)
        session.flush()
    root = session.scalar(select(Menu).where(Menu.name == "系统管理", Menu.type == "DIR"))
    if root is None:
        return
    menus = list(session.scalars(select(Menu)))
    by_parent: dict[int, list] = {}
    for menu in menus:
        by_parent.setdefault(int(menu.parent_id or 0), []).append(menu)
    stack = [root.id]
    wanted = []
    while stack:
        current = stack.pop()
        wanted.append(current)
        for child in by_parent.get(current, []):
            stack.append(child.id)
    linked = set(session.scalars(select(TenantPackageMenu.menu_id).where(TenantPackageMenu.package_id == row.id)))
    for menu_id in wanted:
        if menu_id not in linked:
            session.add(TenantPackageMenu(package_id=row.id, menu_id=menu_id, tenant_id=1))
    session.flush()


def _e2e_roles(session):
    if session.scalar(select(Role).where(Role.role_key == "e2e_admin")) is None:
        session.add(Role(role_key="e2e_admin", name="测试-管理员", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1))
