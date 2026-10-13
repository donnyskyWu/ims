"""IP 组运营、作者档案与选择器。"""
from __future__ import annotations

from sqlalchemy import or_, select

from app.core.clock import format_datetime, now_naive, today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import page_result
from app.core.serialize import parse_api_id
from app.db.repository import Repository, assert_dict_values, protect_counts, validate_refs_on_write
from app.db.session import get_session
from app.domains.account.support import ACCOUNT_STATUS, PLATFORM_LABEL, log_event
from app.domains.ipg.resolve import anchors_of, fail, load_author, materialize_author, require_small_group
from app.domains.master.model import Author, IpAnchor, IpGroup, IpMember, PlatformAccount
from app.domains.system.model import DictData, Timeline, User
from app.services.exchange import remember_export

LEVEL_TEXT = {"S": "S级", "A": "A级", "B": "B级", "C": "C级"}
RELATION_TEXT = {"PRIMARY": "主职", "PART_TIME": "兼职"}
TYPE_TEXT = {"BIG": "大组", "SMALL": "小组"}


def _session():
    return get_session()


def _save(row) -> None:
    validate_refs_on_write(row)
    assert_dict_values(row)
    session = _session()
    session.add(row)
    session.flush()


def _when(value) -> str:
    return format_datetime(value) or ""


def _text(body: dict, key: str) -> str:
    value = body.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _limit(value: str, field: str, label: str, max_len: int, required: bool = False) -> str:
    if required and not value:
        fail(field, f"请填写{label}")
    if len(value) > max_len:
        fail(field, f"{label}不能超过 {max_len} 字")
    return value


def _ident(raw, field: str) -> int:
    try:
        return int(parse_api_id(raw))
    except BizError:
        fail(field, "编号格式不正确")
        return 0


def _id_list(raw, field: str) -> list[int]:
    if isinstance(raw, (str, int)) and raw not in ("", None):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        fail(field, "请选择数据")
    return [_ident(item, field) for item in raw]


def _dict_label(dict_type: str, value: str | None) -> str:
    if not value:
        return ""
    row = _session().scalar(
        select(DictData).where(DictData.dict_type == dict_type, DictData.dict_value == value).execution_options(skip_tenant=True)
    )
    return row.dict_label if row else value


def _user(ident: int | None) -> User | None:
    if not ident:
        return None
    row = _session().get(User, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        return None
    return row


def _user_name(ident: int | None) -> str:
    row = _user(ident)
    if row is None:
        return ""
    return row.nickname or row.username or ""


def _active_user(raw, field: str = "userId") -> User:
    if raw in (None, ""):
        fail(field, "请选择用户")
    row = _user(_ident(raw, field))
    if row is None or row.status != "ACTIVE":
        raise BizError(1204)
    return row


def _mark(biz_id: int, event: str, title: str, detail: str = "") -> None:
    _session().add(
        Timeline(
            biz_type="IPG",
            biz_id=int(biz_id),
            event_type=event,
            title=title[:100],
            detail={"text": detail} if detail else None,
            operator_id=(get_ctx().user_id if get_ctx() and get_ctx().user_id else None),
            event_time=now_naive(),
        )
    )


def _groups() -> list[IpGroup]:
    return list(_session().scalars(select(IpGroup).order_by(IpGroup.sort_order.asc(), IpGroup.id.asc())))


def _by_id(rows: list[IpGroup] | None = None) -> dict[int, IpGroup]:
    return {row.id: row for row in (rows if rows is not None else _groups())}


def access():
    """返回 (可见集合, 可写集合)。None 表示不限制。祖先大组只出现在可见集合。"""
    ctx = get_ctx()
    if ctx is None or ctx.system or ctx.skip_scope or "ALL" in (ctx.data_scopes or set()):
        return None, None
    rows = _groups()
    by_id = {row.id: row for row in rows}
    direct = {int(item) for item in (ctx.ip_group_ids or []) if int(item) in by_id}
    visible: set[int] = set()
    writable: set[int] = set()
    for gid in direct:
        visible.add(gid)
        writable.add(gid)
        if (by_id[gid].group_type or "BIG") == "BIG":
            for child in rows:
                if child.parent_id == gid:
                    visible.add(child.id)
                    writable.add(child.id)
    for gid in list(visible):
        parent = by_id[gid].parent_id if gid in by_id else None
        while parent:
            visible.add(int(parent))
            parent = by_id[parent].parent_id if parent in by_id else None
    return visible, writable


def _group_row(ident: int) -> IpGroup:
    row = _session().get(IpGroup, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的 IP 组不存在")
    return row


def group_of(raw, *, write: bool = False) -> IpGroup:
    row = _group_row(_ident(raw, "id"))
    visible, writable = access()
    if visible is not None and row.id not in visible:
        raise BizError(1008, "您无权查看该 IP 组")
    if write and writable is not None and row.id not in writable:
        raise BizError(1008, "您无权查看该 IP 组")
    return row


def _name_of(row: IpGroup) -> str:
    return row.group_name or row.name or ""


def _path(row: IpGroup, by_id: dict[int, IpGroup] | None = None) -> str:
    found = by_id if by_id is not None else _by_id()
    parent = found.get(int(row.parent_id or 0))
    name = _name_of(row)
    if parent is None:
        return name
    return f"{_name_of(parent)} / {name}"


def _counts(rows: list[IpGroup]) -> dict[int, dict]:
    session = _session()
    members = list(session.scalars(select(IpMember)))
    accounts = list(session.scalars(select(PlatformAccount.ip_group_id)))
    anchors = list(session.scalars(select(IpAnchor.ip_group_id)))
    member_n: dict[int, int] = {}
    for item in members:
        member_n[int(item.group_id)] = member_n.get(int(item.group_id), 0) + 1
    account_n: dict[int, int] = {}
    for item in accounts:
        if item:
            account_n[int(item)] = account_n.get(int(item), 0) + 1
    author_n: dict[int, int] = {}
    for item in anchors:
        author_n[int(item)] = author_n.get(int(item), 0) + 1
    children: dict[int, list[int]] = {}
    for row in rows:
        if row.parent_id:
            children.setdefault(int(row.parent_id), []).append(row.id)

    def roll(gid: int) -> dict:
        ids = [gid, *children.get(gid, [])]
        if rows and next((item for item in rows if item.id == gid and (item.group_type or "") == "BIG"), None):
            ids = [gid, *children.get(gid, [])]
        return {
            "memberCount": sum(member_n.get(item, 0) for item in ids),
            "accountCount": sum(account_n.get(item, 0) for item in ids),
            "authorCount": sum(author_n.get(item, 0) for item in ids),
        }

    return {row.id: roll(row.id) for row in rows}


def _node(row: IpGroup, by_id: dict[int, IpGroup], counts: dict, *, readonly: bool, children: list) -> dict:
    counted = counts.get(row.id) or {"memberCount": 0, "accountCount": 0, "authorCount": 0}
    return {
        "id": row.id,
        "groupName": _name_of(row),
        "groupType": row.group_type or "BIG",
        "groupTypeLabel": TYPE_TEXT.get(row.group_type or "BIG", row.group_type or ""),
        "parentId": row.parent_id,
        "parentName": _name_of(by_id[row.parent_id]) if row.parent_id and row.parent_id in by_id else "",
        "path": _path(row, by_id),
        "leaderUserId": row.leader_user_id,
        "leaderName": _user_name(row.leader_user_id) or "—",
        "level": row.level or "",
        "levelLabel": LEVEL_TEXT.get(row.level or "", ""),
        "sortOrder": int(row.sort_order or 0),
        "status": row.status,
        "statusLabel": _dict_label("dict_ip_group_status", row.status),
        "remark": row.remark or "",
        "readonly": readonly,
        "memberCount": counted["memberCount"],
        "accountCount": counted["accountCount"],
        "authorCount": counted["authorCount"],
        "createTime": _when(row.create_time),
        "updateTime": _when(row.update_time),
        "children": children,
    }


def _tree(only_accessible: bool) -> list[dict]:
    rows = _groups()
    by_id = {row.id: row for row in rows}
    counts = _counts(rows)
    visible, writable = access()
    if only_accessible and visible is None:
        visible = None
    chosen = rows if visible is None else [row for row in rows if row.id in visible]

    def build(parent_id):
        nodes = []
        for row in chosen:
            if int(row.parent_id or 0) != int(parent_id or 0):
                continue
            readonly = bool(writable is not None and row.id not in writable)
            nodes.append(_node(row, by_id, counts, readonly=readonly, children=build(row.id)))
        return nodes

    roots = build(0)
    placed: set[int] = set()

    def collect(nodes):
        for node in nodes:
            placed.add(int(node["id"]))
            collect(node.get("children") or [])

    collect(roots)
    for row in chosen:
        if row.id in placed:
            continue
        readonly = bool(writable is not None and row.id not in writable)
        roots.append(_node(row, by_id, counts, readonly=readonly, children=build(row.id)))
    return roots


def tree() -> dict:
    return {"list": _tree(False)}


def accessible_tree() -> dict:
    return {"list": _tree(True)}


def _view_group(row: IpGroup) -> dict:
    by_id = _by_id()
    counts = _counts(list(by_id.values()))
    _, writable = access()
    readonly = bool(writable is not None and row.id not in writable)
    data = _node(row, by_id, counts, readonly=readonly, children=[])
    data.pop("children", None)
    return data


def list_groups(page_query, params: dict) -> dict:
    visible, _ = access()
    rows = _groups()
    keyword = (params.get("keyword") or "").strip()
    group_type = (params.get("groupType") or "").strip()
    status = (params.get("status") or "").strip()
    found = []
    for row in rows:
        if visible is not None and row.id not in visible:
            continue
        if keyword and keyword not in _name_of(row):
            continue
        if group_type and (row.group_type or "") != group_type:
            continue
        if status and row.status != status:
            continue
        found.append(_view_group(row))
    start = (page_query.page_no - 1) * page_query.page_size
    return page_result(found[start : start + page_query.page_size], len(found), page_query)


def _next_code(prefix: str, column) -> str:
    day = today().strftime("%Y%m%d")
    head = f"{prefix}-{day}-"
    rows = list(_session().scalars(select(column).where(column.like(f"{head}%"))))
    highest = 0
    for item in rows:
        tail = str(item or "")[len(head) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{head}{highest + 1:03d}"


def _unique_name(name: str, parent_id: int | None, exclude: int | None = None) -> None:
    stmt = select(IpGroup).where(IpGroup.group_name == name)
    if parent_id:
        stmt = stmt.where(IpGroup.parent_id == int(parent_id))
    else:
        stmt = stmt.where(IpGroup.parent_id.is_(None))
    if exclude:
        stmt = stmt.where(IpGroup.id != int(exclude))
    if _session().scalar(stmt.limit(1)):
        fail("groupName", "同级组名已存在")


def _parent_for(group_type: str, raw, *, current: IpGroup | None = None) -> int | None:
    if group_type == "BIG":
        if raw not in (None, ""):
            fail("parentId", "大组不能有上级")
        return None
    if raw in (None, ""):
        fail("parentId", "请选择上级大组")
    parent = _group_row(_ident(raw, "parentId"))
    if parent.status != "ENABLED":
        raise BizError(1501, "关联的 IP 组已停用，不可选择")
    if (parent.group_type or "") != "BIG":
        fail("parentId", "上级必须是大组")
    if current is not None:
        if parent.id == current.id:
            fail("parentId", "不能选择自己作为上级")
        if parent.id in _descendant_ids(current.id):
            fail("parentId", "不能选择下级作为上级")
    _, writable = access()
    if writable is not None and parent.id not in writable:
        raise BizError(1008, "您无权查看该 IP 组")
    return parent.id


def _descendant_ids(gid: int) -> set[int]:
    rows = _groups()
    found = {int(gid)}
    changed = True
    while changed:
        changed = False
        for row in rows:
            if row.parent_id and int(row.parent_id) in found and row.id not in found:
                found.add(row.id)
                changed = True
    found.discard(int(gid))
    return found


def _sort_of(raw) -> int:
    if raw in (None, ""):
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        fail("sortOrder", "排序须为整数")
        return 0


def _leader(raw):
    if raw in (None, ""):
        return None
    return _active_user(raw, "leaderUserId").id


def create_group(body: dict) -> dict:
    group_type = _text(body, "groupType") or "BIG"
    if group_type not in {"BIG", "SMALL"}:
        raise BizError(1503, data={"field": "groupType"})
    name = _limit(_text(body, "groupName") or _text(body, "name"), "groupName", "组名", 50, required=True)
    parent_id = _parent_for(group_type, body.get("parentId"))
    _unique_name(name, parent_id)
    level = _text(body, "level") or None
    remark = _limit(_text(body, "remark"), "remark", "备注", 255)
    code = _next_code("IPG", IpGroup.code)
    row = IpGroup(
        code=code,
        name=name[:100],
        group_name=name,
        group_type=group_type,
        parent_id=parent_id,
        leader_user_id=_leader(body.get("leaderUserId")),
        level=level,
        sort_order=_sort_of(body.get("sortOrder")),
        status="ENABLED",
        remark=remark or None,
    )
    _save(row)
    _mark(row.id, "CREATE", "创建 IP 组", name)
    return _view_group(row)


def update_group(body: dict) -> dict:
    row = group_of(body.get("id"), write=True)
    if "groupType" in body and _text(body, "groupType") not in {"", row.group_type or ""}:
        fail("groupType", "组类型不可修改")
    if "groupName" in body or "name" in body:
        name = _limit(_text(body, "groupName") or _text(body, "name"), "groupName", "组名", 50, required=True)
        parent_id = row.parent_id
        if "parentId" in body:
            parent_id = _parent_for(row.group_type or "BIG", body.get("parentId"), current=row)
        _unique_name(name, parent_id, exclude=row.id)
        row.group_name = name
        row.name = name[:100]
    elif "parentId" in body:
        parent_id = _parent_for(row.group_type or "BIG", body.get("parentId"), current=row)
        _unique_name(_name_of(row), parent_id, exclude=row.id)
        row.parent_id = parent_id
    if "parentId" in body and ("groupName" in body or "name" in body):
        row.parent_id = _parent_for(row.group_type or "BIG", body.get("parentId"), current=row)
    if "level" in body:
        row.level = _text(body, "level") or None
    if "sortOrder" in body:
        row.sort_order = _sort_of(body.get("sortOrder"))
    if "remark" in body:
        row.remark = _limit(_text(body, "remark"), "remark", "备注", 255) or None
    if "leaderUserId" in body:
        row.leader_user_id = _leader(body.get("leaderUserId"))
    if "status" in body:
        status = _text(body, "status")
        if status not in {"ENABLED", "DISABLED"}:
            raise BizError(1503, data={"field": "status"})
        if status != row.status:
            row.status = status
            _mark(row.id, "DISABLE" if status == "DISABLED" else "ENABLE", "停用 IP 组" if status == "DISABLED" else "启用 IP 组", _name_of(row))
    _save(row)
    return _view_group(row)


def remove_group(raw) -> dict:
    row = group_of(raw, write=True)
    session = _session()
    members = session.scalar(select(IpMember.id).where(IpMember.group_id == row.id).limit(1))
    accounts = session.scalar(select(PlatformAccount.id).where(PlatformAccount.ip_group_id == row.id).limit(1))
    anchors = session.scalar(select(IpAnchor.id).where(IpAnchor.ip_group_id == row.id).limit(1))
    children = session.scalar(select(IpGroup.id).where(IpGroup.parent_id == row.id).limit(1))
    authors = session.scalar(select(Author.id).where(Author.ip_group_id == row.id).limit(1))
    if members or accounts or anchors or children or authors:
        raise BizError(1206)
    _mark(row.id, "DELETE", "删除 IP 组", _name_of(row))
    Repository(IpGroup).soft_delete(row.id)
    return {}


def _member_view(row: IpMember) -> dict:
    user = _user(row.user_id)
    return {
        "id": row.id,
        "ipGroupId": row.group_id,
        "userId": row.user_id,
        "userName": (user.nickname or user.username) if user else "—",
        "position": row.position or "",
        "positionLabel": _dict_label("dict_position", row.position),
        "relationType": row.relation_type or "PRIMARY",
        "relationLabel": RELATION_TEXT.get(row.relation_type or "PRIMARY", row.relation_type or ""),
        "isLeader": int(row.is_leader or 0) == 1,
    }


def members(raw) -> dict:
    group = group_of(raw)
    rows = list(_session().scalars(select(IpMember).where(IpMember.group_id == group.id).order_by(IpMember.id.asc())))
    return {"list": [_member_view(row) for row in rows]}


def add_member(raw, body: dict) -> dict:
    group = group_of(raw, write=True)
    user = _active_user(body.get("userId"))
    position = _text(body, "position")
    if not position:
        fail("position", "请选择岗位")
    relation = _text(body, "relationType") or "PRIMARY"
    if relation not in {"PRIMARY", "PART_TIME"}:
        raise BizError(1503, data={"field": "relationType"})
    exists = _session().scalar(select(IpMember).where(IpMember.group_id == group.id, IpMember.user_id == user.id))
    if exists is not None:
        fail("userId", "该用户已在本组")
    leader = bool(body.get("isLeader") or body.get("setLeader"))
    row = IpMember(group_id=group.id, user_id=user.id, position=position, relation_type=relation, is_leader=1 if leader else 0)
    _save(row)
    if leader:
        group.leader_user_id = user.id
        _save(group)
    return _member_view(row)


def update_member(group_raw, member_raw, body: dict) -> dict:
    group = group_of(group_raw, write=True)
    row = _session().get(IpMember, _ident(member_raw, "memberId"))
    if row is None or int(row.group_id) != group.id:
        raise BizError(1500, "关联的成员不存在")
    if "position" in body:
        position = _text(body, "position")
        if not position:
            fail("position", "请选择岗位")
        row.position = position
    if "relationType" in body:
        relation = _text(body, "relationType") or "PRIMARY"
        if relation not in {"PRIMARY", "PART_TIME"}:
            raise BizError(1503, data={"field": "relationType"})
        row.relation_type = relation
    if "isLeader" in body or "setLeader" in body:
        leader = bool(body.get("isLeader") if "isLeader" in body else body.get("setLeader"))
        row.is_leader = 1 if leader else 0
        if leader:
            group.leader_user_id = row.user_id
        elif group.leader_user_id == row.user_id:
            group.leader_user_id = None
        _save(group)
    _save(row)
    return _member_view(row)


def remove_member(group_raw, member_raw) -> dict:
    group = group_of(group_raw, write=True)
    row = _session().get(IpMember, _ident(member_raw, "memberId"))
    if row is None or int(row.group_id) != group.id:
        raise BizError(1500, "关联的成员不存在")
    cleared = False
    if group.leader_user_id and int(group.leader_user_id) == int(row.user_id or 0):
        group.leader_user_id = None
        cleared = True
        _save(group)
    _session().delete(row)
    _session().flush()
    return {"leaderCleared": cleared, "message": "请重新指定组长" if cleared else ""}


def _account_view(row: PlatformAccount) -> dict:
    author = _session().get(Author, int(row.author_user_id)) if row.author_user_id else None
    owner = _user(row.owner_user_id)
    return {
        "id": row.id,
        "accountNo": row.account_no or row.code or "",
        "nickname": row.nickname or row.name or "",
        "platform": row.platform or "",
        "platformLabel": PLATFORM_LABEL.get(row.platform or "", row.platform or ""),
        "status": row.status,
        "statusLabel": ACCOUNT_STATUS.get(row.status, row.status),
        "ownerUserId": row.owner_user_id,
        "ownerName": (owner.nickname or owner.username) if owner else "—",
        "authorUserId": row.author_user_id,
        "authorName": (author.author_name or author.name) if author else "—",
        "ipGroupId": row.ip_group_id,
    }


def account_labels(ip_group_id, author_user_id) -> dict:
    by_id = _by_id()
    group = by_id.get(int(ip_group_id)) if ip_group_id else None
    author = _session().get(Author, int(author_user_id)) if author_user_id else None
    return {
        "ipGroupId": int(ip_group_id) if ip_group_id else None,
        "ipGroupText": _path(group, by_id) if group else "—",
        "authorUserId": int(author_user_id) if author_user_id else None,
        "authorName": (author.author_name or author.name) if author else "—",
    }


def accounts(raw) -> dict:
    group = group_of(raw)
    session = _session()
    if (group.group_type or "") == "BIG":
        child_ids = [row.id for row in _groups() if row.parent_id == group.id]
        rows = list(session.scalars(select(PlatformAccount).where(PlatformAccount.ip_group_id.in_(child_ids or [-1])))) if child_ids else []
        return {"readOnly": True, "hint": "请在小组下绑定账号", "list": [_account_view(row) for row in rows]}
    rows = list(session.scalars(select(PlatformAccount).where(PlatformAccount.ip_group_id == group.id).order_by(PlatformAccount.id.desc())))
    return {"readOnly": False, "hint": "", "list": [_account_view(row) for row in rows]}


def bind_accounts(raw, body: dict) -> dict:
    group = group_of(raw, write=True)
    if (group.group_type or "") != "SMALL":
        raise BizError(1203)
    if group.status != "ENABLED":
        raise BizError(1501, "关联的 IP 组已停用，不可选择")
    idents = _id_list(body.get("accountIds"), "accountIds")
    session = _session()
    saved = []
    for ident in idents:
        account = session.get(PlatformAccount, ident)
        if account is None or int(account.deleted or 0) != 0:
            raise BizError(1500, "关联的平台账号不存在")
        if account.status == "CANCELLED":
            raise BizError(1501, "关联的平台账号已停用，不可选择")
        if account.ip_group_id and int(account.ip_group_id) != group.id:
            other = session.get(IpGroup, int(account.ip_group_id))
            raise BizError(1205, f"账号已属于其他 IP 组：{_name_of(other) if other else account.ip_group_id}")
        author_id = materialize_author(group.id, current_author=account.author_user_id)
        account.ip_group_id = group.id
        if not account.author_user_id:
            account.author_user_id = author_id
        _save(account)
        log_event(account.id, "BIND_GROUP", "绑定 IP 组", _name_of(group))
        saved.append(_account_view(account))
    return {"list": saved}


def unbind_account(group_raw, account_raw) -> dict:
    group = group_of(group_raw, write=True)
    if (group.group_type or "") != "SMALL":
        raise BizError(1203)
    account = _session().get(PlatformAccount, _ident(account_raw, "accountId"))
    if account is None or int(account.deleted or 0) != 0:
        raise BizError(1500, "关联的平台账号不存在")
    if int(account.ip_group_id or 0) != group.id:
        raise BizError(1500, "关联的平台账号不存在")
    account.ip_group_id = None
    _save(account)
    log_event(account.id, "UNBIND_GROUP", "解绑 IP 组", "作者引用仍保留，可在账号详情调整")
    return {"authorKept": True, "message": "作者引用仍保留，可在账号详情调整", "account": _account_view(account)}


def _anchor_view(row: IpAnchor) -> dict:
    author = _session().get(Author, int(row.author_id))
    account = None
    if author and author.primary_account_id:
        account = _session().get(PlatformAccount, int(author.primary_account_id))
    return {
        "id": row.id,
        "ipGroupId": row.ip_group_id,
        "authorId": row.author_id,
        "authorName": (author.author_name or author.name) if author else "—",
        "authorType": (row.anchor_type or (author.author_type if author else "") or ""),
        "authorTypeLabel": _dict_label("dict_author_type", row.anchor_type or (author.author_type if author else "")),
        "isPrimary": int(row.is_primary or 0) == 1,
        "userId": author.user_id if author else None,
        "userName": _user_name(author.user_id) if author and author.user_id else "—",
        "primaryAccountId": author.primary_account_id if author else None,
        "primaryAccountName": (account.nickname or account.account_no) if account else "—",
    }


def anchors(raw) -> dict:
    group = group_of(raw)
    if (group.group_type or "") == "BIG":
        child_ids = [row.id for row in _groups() if row.parent_id == group.id]
        rows = list(_session().scalars(select(IpAnchor).where(IpAnchor.ip_group_id.in_(child_ids or [-1])))) if child_ids else []
        return {"readOnly": True, "hint": "请在小组下关联作者", "list": [_anchor_view(row) for row in rows]}
    rows = anchors_of(group.id)
    return {"readOnly": False, "hint": "", "list": [_anchor_view(row) for row in rows]}


def _demote(group_id: int, keep_id: int | None, title: str) -> None:
    for row in anchors_of(group_id):
        if keep_id and row.id == keep_id:
            continue
        if int(row.is_primary or 0) == 1:
            row.is_primary = 0
            _save(row)
    _mark(group_id, "PRIMARY", title)


def _fill_empty(group_id: int, author_id: int) -> int:
    rows = list(
        _session().scalars(
            select(PlatformAccount).where(PlatformAccount.ip_group_id == int(group_id), PlatformAccount.author_user_id.is_(None))
        )
    )
    for row in rows:
        row.author_user_id = int(author_id)
        _save(row)
    return len(rows)


def add_anchors(raw, body: dict) -> dict:
    group = group_of(raw, write=True)
    if (group.group_type or "") != "SMALL":
        raise BizError(1203)
    if group.status != "ENABLED":
        raise BizError(1501, "关联的 IP 组已停用，不可选择")
    raw_ids = body.get("authorIds")
    if raw_ids in (None, "") and body.get("authorId") not in (None, ""):
        raw_ids = [body.get("authorId")]
    idents = _id_list(raw_ids, "authorId")
    want_primary = bool(body.get("isPrimary"))
    anchor_type = _text(body, "anchorType") or None
    saved = []
    for ident in idents:
        author = load_author(ident)
        exists = _session().scalar(select(IpAnchor).where(IpAnchor.ip_group_id == group.id, IpAnchor.author_id == author.id))
        if exists is not None:
            fail("authorId", "作者已关联到本组")
        row = IpAnchor(
            ip_group_id=group.id,
            author_id=author.id,
            anchor_type=anchor_type or author.author_type,
            is_primary=1 if want_primary else 0,
        )
        _save(row)
        if want_primary:
            _demote(group.id, row.id, f"主作者调整为 {author.author_name or author.name}")
            row.is_primary = 1
            _save(row)
            _fill_empty(group.id, author.id)
            want_primary = False
        if not author.ip_group_id:
            author.ip_group_id = group.id
            _save(author)
        saved.append(_anchor_view(row))
    return {"list": saved}


def set_primary(group_raw, rel_raw) -> dict:
    group = group_of(group_raw, write=True)
    if (group.group_type or "") != "SMALL":
        raise BizError(1203)
    row = _session().get(IpAnchor, _ident(rel_raw, "relId"))
    if row is None or int(row.ip_group_id) != group.id:
        raise BizError(1500, "关联的作者不存在")
    author = load_author(row.author_id)
    _demote(group.id, row.id, f"主作者调整为 {author.author_name or author.name}")
    row.is_primary = 1
    _save(row)
    filled = _fill_empty(group.id, author.id)
    data = _anchor_view(row)
    data["filled"] = filled
    return data


def remove_anchor(group_raw, rel_raw) -> dict:
    group = group_of(group_raw, write=True)
    row = _session().get(IpAnchor, _ident(rel_raw, "relId"))
    if row is None or int(row.ip_group_id) != group.id:
        raise BizError(1500, "关联的作者不存在")
    was_primary = int(row.is_primary or 0) == 1
    Repository(IpAnchor).soft_delete(row.id)
    left = anchors_of(group.id)
    accounts = _session().scalar(select(PlatformAccount.id).where(PlatformAccount.ip_group_id == group.id).limit(1))
    warning = ""
    if not left and accounts:
        warning = "组内仍有账号，下次保存账号需重新指定主作者"
    message = "请重新指定主作者" if was_primary else warning
    return {"needPrimary": was_primary, "warning": warning, "message": message}


def _child_ids(group: IpGroup) -> list[int]:
    if (group.group_type or "") != "BIG":
        return [group.id]
    return [group.id, *[row.id for row in _groups() if row.parent_id == group.id]]


def stats(raw) -> dict:
    group = group_of(raw)
    ids = _child_ids(group)
    session = _session()
    member_count = len(list(session.scalars(select(IpMember.id).where(IpMember.group_id.in_(ids)))))
    account_count = len(list(session.scalars(select(PlatformAccount.id).where(PlatformAccount.ip_group_id.in_(ids)))))
    author_count = len(list(session.scalars(select(IpAnchor.id).where(IpAnchor.ip_group_id.in_(ids)))))
    return {
        "memberCount": member_count,
        "accountCount": account_count,
        "authorCount": author_count,
        "fans": 0,
        "works": 0,
        "innerContents": 0,
        "roi": "0",
        "cost": "0",
        "revenue": "0",
        "mock": True,
        "mockLabel": "示意数据，采集/财务上线后替换",
    }


def _author_scope_ok(row: Author) -> bool:
    visible, _ = access()
    if visible is None:
        return True
    if row.ip_group_id and int(row.ip_group_id) in visible:
        return True
    linked = list(_session().scalars(select(IpAnchor.ip_group_id).where(IpAnchor.author_id == row.id)))
    return any(int(item) in visible for item in linked)


def _author_of(raw, *, write: bool = False) -> Author:
    row = _session().get(Author, _ident(raw, "id"))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的作者不存在")
    if not _author_scope_ok(row):
        raise BizError(1008, "您无权查看该作者")
    if write:
        _, writable = access()
        home = int(row.ip_group_id or 0)
        if writable is not None and home and home not in writable:
            raise BizError(1008, "您无权查看该作者")
    return row


def _author_view(row: Author, *, detail: bool = False) -> dict:
    by_id = _by_id()
    group = by_id.get(int(row.ip_group_id)) if row.ip_group_id else None
    account = _session().get(PlatformAccount, int(row.primary_account_id)) if row.primary_account_id else None
    data = {
        "id": row.id,
        "authorNo": row.author_no or row.code or "",
        "authorName": row.author_name or row.name,
        "authorType": row.author_type or "",
        "authorTypeLabel": _dict_label("dict_author_type", row.author_type),
        "ipGroupId": row.ip_group_id,
        "ipGroupText": _path(group, by_id) if group else "—",
        "userId": row.user_id,
        "userName": _user_name(row.user_id) or "—",
        "primaryAccountId": row.primary_account_id,
        "primaryAccountName": (account.nickname or account.account_no) if account else "—",
        "footballAuthorId": row.football_author_id,
        "status": row.status,
        "statusLabel": _dict_label("dict_author_status", row.status),
        "remark": row.remark or "",
        "updateTime": _when(row.update_time),
    }
    if detail:
        links = list(_session().scalars(select(IpAnchor).where(IpAnchor.author_id == row.id)))
        data["groups"] = [
            {
                "id": item.id,
                "ipGroupId": item.ip_group_id,
                "groupName": _path(by_id[item.ip_group_id], by_id) if item.ip_group_id in by_id else "",
                "isPrimary": int(item.is_primary or 0) == 1,
            }
            for item in links
        ]
        data["dashboardHint"] = "看板指标随内部分析与直播模块提供"
    return data


def _filter_group_ids(raw) -> list[int] | None:
    if raw in (None, ""):
        return None
    gid = _ident(raw, "ipGroupId")
    group = _session().get(IpGroup, gid)
    if group is None:
        return [gid]
    if (group.group_type or "") == "BIG":
        return [group.id, *[row.id for row in _groups() if row.parent_id == group.id]]
    return [group.id]


def _author_rows(params: dict) -> list[Author]:
    stmt = select(Author).order_by(Author.update_time.desc(), Author.id.desc())
    status = (params.get("status") or "").strip()
    if status:
        stmt = stmt.where(Author.status == status)
    author_type = (params.get("authorType") or "").strip()
    if author_type:
        stmt = stmt.where(Author.author_type == author_type)
    user_id = (params.get("userId") or "").strip()
    if user_id:
        stmt = stmt.where(Author.user_id == _ident(user_id, "userId"))
    group_ids = _filter_group_ids(params.get("ipGroupId"))
    if group_ids is not None:
        stmt = stmt.where(Author.ip_group_id.in_(group_ids))
    keyword = (params.get("keyword") or params.get("authorName") or "").strip()
    if keyword:
        stmt = stmt.where(or_(Author.author_name.contains(keyword), Author.name.contains(keyword), Author.author_no.contains(keyword)))
    return [row for row in _session().scalars(stmt) if _author_scope_ok(row)]


def author_page(page_query, params: dict) -> dict:
    rows = _author_rows(params)
    start = (page_query.page_no - 1) * page_query.page_size
    return page_result([_author_view(row) for row in rows[start : start + page_query.page_size]], len(rows), page_query)


def author_detail(raw) -> dict:
    return _author_view(_author_of(raw), detail=True)


def _sync_anchor(author: Author, previous: int | None) -> None:
    session = _session()
    if previous and previous != int(author.ip_group_id or 0):
        old = session.scalar(select(IpAnchor).where(IpAnchor.ip_group_id == int(previous), IpAnchor.author_id == author.id))
        if old is not None:
            Repository(IpAnchor).soft_delete(old.id)
    if not author.ip_group_id:
        return
    group = _group_row(int(author.ip_group_id))
    if (group.group_type or "") != "SMALL":
        raise BizError(1203)
    exists = session.scalar(select(IpAnchor).where(IpAnchor.ip_group_id == group.id, IpAnchor.author_id == author.id))
    if exists is None:
        _save(IpAnchor(ip_group_id=group.id, author_id=author.id, anchor_type=author.author_type, is_primary=0))


def _apply_author(row: Author, body: dict, *, creating: bool) -> None:
    if creating or "authorName" in body or "name" in body:
        name = _limit(_text(body, "authorName") or _text(body, "name"), "authorName", "作者名", 64, required=True)
        row.author_name = name
        row.name = name[:100]
    if creating or "authorType" in body:
        author_type = _text(body, "authorType")
        if creating and not author_type:
            fail("authorType", "请选择作者类型")
        if author_type:
            row.author_type = author_type
    if "ipGroupId" in body or creating:
        raw_group = body.get("ipGroupId")
        if raw_group in (None, ""):
            row.ip_group_id = None
        else:
            group = require_small_group(raw_group)
            _, writable = access()
            if writable is not None and group.id not in writable:
                raise BizError(1008, "您无权查看该 IP 组")
            row.ip_group_id = group.id
    if "userId" in body:
        if body.get("userId") in (None, ""):
            row.user_id = None
        else:
            row.user_id = _active_user(body.get("userId")).id
    if "primaryAccountId" in body:
        if body.get("primaryAccountId") in (None, ""):
            row.primary_account_id = None
        else:
            account_id = _ident(body.get("primaryAccountId"), "primaryAccountId")
            if row.ip_group_id:
                assert_same_pool_values(int(row.ip_group_id), account_id)
            else:
                raise BizError(1127, "作者与账号不在同一 IP 组账号池")
            row.primary_account_id = account_id
    if "remark" in body or creating:
        row.remark = _limit(_text(body, "remark"), "remark", "备注", 255) or None
    if "footballAuthorId" in body:
        raw = body.get("footballAuthorId")
        row.football_author_id = None if raw in (None, "") else _ident(raw, "footballAuthorId")
    if "status" in body and not creating:
        status = _text(body, "status")
        if status not in {"ENABLED", "DISABLED"}:
            raise BizError(1503, data={"field": "status"})
        row.status = status


def assert_same_pool_values(group_id: int, account_id: int) -> None:
    account = _session().get(PlatformAccount, int(account_id))
    if account is None or int(account.deleted or 0) != 0:
        raise BizError(1500, "关联的平台账号不存在")
    if account.status == "CANCELLED":
        raise BizError(1501, "关联的平台账号已停用，不可选择")
    if int(account.ip_group_id or 0) != int(group_id):
        raise BizError(1127, "作者与账号不在同一 IP 组账号池")


def create_author(body: dict) -> dict:
    number = _text(body, "authorNo")
    if number:
        number = _limit(number, "authorNo", "作者编号", 32)
    else:
        number = _next_code("AU", Author.author_no)
    row = Author(code=number, author_no=number, name="", status="ENABLED")
    _apply_author(row, body, creating=True)
    previous = None
    _save(row)
    _sync_anchor(row, previous)
    return _author_view(row, detail=True)


def update_author(raw, body: dict) -> dict:
    row = _author_of(raw, write=True)
    if "authorNo" in body and _text(body, "authorNo") not in {"", row.author_no or ""}:
        fail("authorNo", "作者编号不可修改")
    previous = int(row.ip_group_id) if row.ip_group_id else None
    _apply_author(row, body, creating=False)
    _save(row)
    if "ipGroupId" in body:
        _sync_anchor(row, previous)
    return _author_view(row, detail=True)


def author_status(raw, body: dict) -> dict:
    row = _author_of(raw, write=True)
    status = _text(body, "status")
    if status not in {"ENABLED", "DISABLED"}:
        raise BizError(1503, data={"field": "status"})
    row.status = status
    _save(row)
    return _author_view(row)


def remove_author(raw) -> dict:
    row = _author_of(raw, write=True)
    refs = protect_counts(row)
    if refs:
        raise BizError(1502, "该作者已被账号或 IP 组引用，不能删除")
    Repository(Author).soft_delete(row.id)
    return {}


def author_export(params: dict) -> dict:
    rows = [_author_view(row) for row in _author_rows(params)]
    header = ["作者编号", "作者名", "类型", "归属 IP 组", "绑定用户", "主推号", "状态", "更新时间"]
    body = [
        [
            item["authorNo"],
            item["authorName"],
            item["authorTypeLabel"],
            item["ipGroupText"],
            item["userName"],
            item["primaryAccountName"],
            item["statusLabel"],
            item["updateTime"],
        ]
        for item in rows
    ]
    return remember_export("作者.xlsx", header, body, "ipg_author")


def selector_groups(page_query, params: dict) -> dict:
    only_small = str(params.get("onlySmall") or "").lower() in {"1", "true", "yes"}
    keyword = (params.get("keyword") or "").strip()
    raw_ids = (params.get("ids") or "").strip()
    visible, _ = access()
    rows = _groups()
    by_id = {row.id: row for row in rows}
    if raw_ids:
        wanted = []
        for item in raw_ids.split(","):
            if item.strip():
                wanted.append(_ident(item.strip(), "ids"))
        rows = [row for row in rows if row.id in wanted]
    else:
        rows = [row for row in rows if row.status == "ENABLED"]
        if only_small:
            rows = [row for row in rows if (row.group_type or "") == "SMALL"]
        if visible is not None:
            rows = [row for row in rows if row.id in visible]
        if keyword:
            rows = [row for row in rows if keyword in _name_of(row) or keyword in _path(row, by_id)]
        if not rows:
            raise BizError(1221, "选择器暂无可选数据")
    start = (page_query.page_no - 1) * page_query.page_size
    chunk = rows[start : start + page_query.page_size]
    listed = [
        {
            "id": row.id,
            "label": _path(row, by_id),
            "groupName": _name_of(row),
            "groupType": row.group_type or "BIG",
            "parentId": row.parent_id,
            "parentLabel": _name_of(by_id[row.parent_id]) if row.parent_id and row.parent_id in by_id else "",
            "status": row.status,
        }
        for row in chunk
    ]
    return page_result(listed, len(rows), page_query)


def selector_authors(page_query, params: dict) -> dict:
    keyword = (params.get("keyword") or "").strip()
    raw_ids = (params.get("ids") or "").strip()
    stmt = select(Author).where(Author.status == "ENABLED").order_by(Author.id.desc())
    if raw_ids:
        wanted = [_ident(item.strip(), "ids") for item in raw_ids.split(",") if item.strip()]
        rows = list(_session().scalars(select(Author).where(Author.id.in_(wanted or [-1]))))
    else:
        group_raw = (params.get("ipGroupId") or "").strip()
        if group_raw:
            ids = _filter_group_ids(group_raw) or [-1]
            linked = list(_session().scalars(select(IpAnchor.author_id).where(IpAnchor.ip_group_id.in_(ids))))
            stmt = stmt.where(or_(Author.ip_group_id.in_(ids), Author.id.in_(linked or [-1])))
        account_raw = (params.get("accountId") or "").strip()
        if account_raw:
            account = _session().get(PlatformAccount, _ident(account_raw, "accountId"))
            if account is None or not account.ip_group_id:
                rows = []
            else:
                ids = [int(account.ip_group_id)]
                linked = list(_session().scalars(select(IpAnchor.author_id).where(IpAnchor.ip_group_id.in_(ids))))
                stmt = stmt.where(or_(Author.ip_group_id.in_(ids), Author.id.in_(linked or [-1])))
                rows = [row for row in _session().scalars(stmt) if _author_scope_ok(row)]
        else:
            rows = [row for row in _session().scalars(stmt) if _author_scope_ok(row)]
        if keyword:
            rows = [row for row in rows if keyword in (row.author_name or "") or keyword in (row.name or "")]
        if not rows:
            raise BizError(1221, "选择器暂无可选数据")
    start = (page_query.page_no - 1) * page_query.page_size
    chunk = rows[start : start + page_query.page_size]
    listed = [
        {
            "id": row.id,
            "label": row.author_name or row.name,
            "authorName": row.author_name or row.name,
            "ipGroupId": row.ip_group_id,
            "authorType": row.author_type or "",
            "status": row.status,
        }
        for row in chunk
    ]
    return page_result(listed, len(rows), page_query)
