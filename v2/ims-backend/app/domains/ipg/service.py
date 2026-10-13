"""IP 组、成员、账号绑定、关联作者与作者档案。版本 B8 v1.0。"""
from __future__ import annotations

from sqlalchemy import func, or_, select

from app.core.clock import now_naive, today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import page_result
from app.core.serialize import parse_api_id
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.account.support import log_event, require_dict, user_brief, when
from app.domains.ipg.resolve import (
    MSG_1127,
    author_label,
    author_row,
    backfill_empty_authors,
    group_chain,
    group_label,
    group_row,
    require_small_group,
    resolve_author_id,
)
from app.domains.master.model import Author, IpAnchor, IpGroup, IpMember, PlatformAccount
from app.domains.system.model import Timeline, User
from app.services.exchange import remember_export

_TYPE = {"BIG": "大组", "SMALL": "小组"}
_LEVEL = {"S": "S级", "A": "A级", "B": "B级", "C": "C级"}
_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}
_REL = {"PRIMARY": "主职", "PART_TIME": "兼职"}
_POS = {
    "OPS_LEADER": "运营组长",
    "OPERATOR": "运营",
    "ANCHOR": "主播",
    "EDITOR": "编辑",
    "LIVE_OPERATOR": "直播运营",
    "SALES": "销售",
    "OTHER": "其他",
}
_AUTHOR_TYPE = {"SHORT_VIDEO": "短视频", "LIVE": "直播", "BOTH": "短视频+直播", "OTHER": "其他"}
_PLATFORM = {"DOUYIN": "抖音", "KUAISHOU": "快手", "WECHAT_CHANNELS": "视频号", "XIAOHONGSHU": "小红书", "WECHAT_MP": "公众号"}


def _bad(field: str, message: str) -> None:
    raise BizError(1001, data={"fieldErrors": [{"field": field, "message": message}]})


def _pid(value, field: str) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(parse_api_id(value))
    except BizError:
        _bad(field, "编号格式不正确")
        return None


def _text(body: dict, key: str, field: str, label: str, limit: int, required: bool = False) -> str:
    text = str(body.get(key) or "").strip()
    if required and not text:
        _bad(field, f"请填写{label}")
    if len(text) > limit:
        _bad(field, f"{label}最多{limit}个字")
    return text


def _scope_ids() -> set[int] | None:
    """ALL 看全量。仅 IP_GROUP 范围时返回可见组。"""
    ctx = get_ctx()
    if ctx is None:
        return None
    scopes = set(ctx.data_scopes or set())
    if "ALL" in scopes or "IP_GROUP" not in scopes:
        return None
    return {int(item) for item in (ctx.ip_group_ids or [])}


def _operable(group_id: int) -> bool:
    allowed = _scope_ids()
    if allowed is None:
        return True
    return int(group_id) in allowed


def _assert_visible(row: IpGroup) -> None:
    allowed = _scope_ids()
    if allowed is None:
        return
    if int(row.id) in allowed:
        return
    if row.parent_id and int(row.parent_id) in allowed:
        return
    if _is_ancestor(row.id, allowed):
        return
    raise BizError(1008, "您无权查看该 IP 组")


def _assert_write(row: IpGroup) -> None:
    _assert_visible(row)
    if not _operable(row.id):
        raise BizError(1008, "您无权查看该 IP 组")


def _is_ancestor(group_id: int, leaves: set[int]) -> bool:
    rows = _all_groups()
    parents = {int(row.id): int(row.parent_id or 0) for row in rows}
    for leaf in leaves:
        current = leaf
        guard = 0
        while current and guard < 20:
            parent = parents.get(current) or 0
            if parent == int(group_id):
                return True
            current = parent
            guard += 1
    return False


def _all_groups() -> list[IpGroup]:
    return list(get_session().scalars(select(IpGroup).order_by(IpGroup.sort_order.asc(), IpGroup.id.asc())))


def _counts() -> tuple[dict[int, int], dict[int, int], dict[int, int]]:
    session = get_session()
    members = {int(key): int(value) for key, value in session.execute(select(IpMember.group_id, func.count()).group_by(IpMember.group_id))}
    accounts = {
        int(key): int(value)
        for key, value in session.execute(
            select(PlatformAccount.ip_group_id, func.count()).where(PlatformAccount.ip_group_id.is_not(None)).group_by(PlatformAccount.ip_group_id)
        )
        if key
    }
    authors = {
        int(key): int(value)
        for key, value in session.execute(select(IpAnchor.ip_group_id, func.count()).group_by(IpAnchor.ip_group_id))
    }
    return members, accounts, authors


def _subtree_ids(root_id: int, rows: list[IpGroup] | None = None) -> set[int]:
    rows = rows if rows is not None else _all_groups()
    children: dict[int, list[int]] = {}
    for row in rows:
        children.setdefault(int(row.parent_id or 0), []).append(int(row.id))
    found: set[int] = set()
    stack = list(children.get(int(root_id), []))
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


def _timeline(biz_id: int, event_type: str, title: str) -> None:
    ctx = get_ctx()
    get_session().add(
        Timeline(
            biz_type="IPG",
            biz_id=int(biz_id),
            event_type=event_type,
            title=title[:100],
            operator_id=ctx.user_id if ctx else None,
            event_time=now_naive(),
        )
    )


def _group_view(row: IpGroup, counts=None, *, operable: bool | None = None) -> dict:
    members, accounts, authors = counts or _counts()
    leader = user_brief(row.leader_user_id)
    parent = group_row(row.parent_id)
    level = row.level or ""
    name = group_label(row)
    suffix = f"[{_LEVEL.get(level, level)}]" if level else ""
    member_count = members.get(int(row.id), 0)
    account_count = accounts.get(int(row.id), 0)
    author_count = authors.get(int(row.id), 0)
    return {
        "id": row.id,
        "groupName": name,
        "groupType": row.group_type,
        "groupTypeLabel": _TYPE.get(row.group_type, row.group_type),
        "parentId": row.parent_id,
        "parentName": group_label(parent),
        "leaderUserId": row.leader_user_id,
        "leaderName": leader["name"] or "—",
        "level": level or None,
        "levelLabel": _LEVEL.get(level, "") if level else "未分级",
        "sortOrder": int(row.sort_order or 0),
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "remark": row.remark or "",
        "memberCount": member_count,
        "accountCount": account_count,
        "authorCount": author_count,
        "label": f"{name} ({member_count}/{account_count}/{author_count}){suffix}",
        "operable": _operable(row.id) if operable is None else operable,
        "readOnly": not (_operable(row.id) if operable is None else operable),
        "createTime": when(row.create_time),
        "updateTime": when(row.update_time),
    }


def _tree_nodes(rows: list[IpGroup], operable_ids: set[int] | None) -> list[dict]:
    counts = _counts()
    nodes = []
    for row in rows:
        operable = True if operable_ids is None else int(row.id) in operable_ids
        item = _group_view(row, counts, operable=operable)
        item["readOnly"] = not operable
        nodes.append(item)
    by_parent: dict[int, list[dict]] = {}
    for item in nodes:
        by_parent.setdefault(int(item["parentId"] or 0), []).append(item)
    for item in nodes:
        item["children"] = by_parent.get(int(item["id"]), [])
    return by_parent.get(0, [])


def tree() -> dict:
    allowed = _scope_ids()
    if allowed is not None:
        raise BizError(1008, "您无权查看该 IP 组")
    return {"list": _tree_nodes(_all_groups(), None)}


def accessible_tree() -> dict:
    rows = _all_groups()
    allowed = _scope_ids()
    if allowed is None:
        return {"list": _tree_nodes(rows, None)}
    visible = set(allowed)
    parents = {int(row.id): int(row.parent_id or 0) for row in rows}
    for leaf in list(allowed):
        current = leaf
        guard = 0
        while current and guard < 20:
            parent = parents.get(current) or 0
            if not parent:
                break
            visible.add(parent)
            current = parent
            guard += 1
    picked = [row for row in rows if int(row.id) in visible]
    return {"list": _tree_nodes(picked, allowed)}


def group_list(page, params: dict) -> dict:
    rows = _all_groups()
    allowed = _scope_ids()
    if allowed is not None:
        rows = [row for row in rows if int(row.id) in allowed or _is_ancestor(row.id, allowed)]
    keyword = str(params.get("keyword") or "").strip()
    group_type = str(params.get("groupType") or "").strip()
    status = str(params.get("status") or "").strip()
    if keyword:
        rows = [row for row in rows if keyword in group_label(row)]
    if group_type:
        rows = [row for row in rows if row.group_type == group_type]
    if status:
        rows = [row for row in rows if row.status == status]
    counts = _counts()
    chunk, total = _slice(rows, page)
    return page_result([_group_view(row, counts) for row in chunk], total, page)


def _slice(rows, page):
    total = len(rows)
    start = (page.page_no - 1) * page.page_size
    return rows[start : start + page.page_size], total


def _unique_name(name: str, parent_id: int | None, current: int | None) -> None:
    stmt = select(IpGroup).where(IpGroup.group_name == name)
    if parent_id:
        stmt = stmt.where(IpGroup.parent_id == int(parent_id))
    else:
        stmt = stmt.where(IpGroup.parent_id.is_(None))
    found = get_session().scalar(stmt)
    if found is not None and found.id != current:
        _bad("groupName", "同一上级下组名已存在")


def _leader(value) -> int | None:
    number = _pid(value, "leaderUserId")
    if not number:
        return None
    user = get_session().get(User, number)
    if user is None or int(user.deleted or 0) != 0 or user.status != "ACTIVE":
        raise BizError(1204, "成员用户不存在或已停用/离职")
    return int(user.id)


def create_group(body: dict) -> dict:
    group_type = str(body.get("groupType") or ("SMALL" if body.get("parentId") else "BIG")).strip()
    require_dict("dict_ip_group_type", group_type, "groupType", "组类型")
    name = _text(body, "groupName", "groupName", "组名", 50, required=True)
    remark = _text(body, "remark", "remark", "备注", 255)
    level = str(body.get("level") or "").strip()
    if level:
        require_dict("dict_ip_group_level", level, "level", "等级")
    parent_id = _pid(body.get("parentId"), "parentId")
    if group_type == "BIG":
        if parent_id:
            _bad("parentId", "大组不能选择上级")
        parent_id = None
    else:
        if not parent_id:
            _bad("parentId", "请选择上级大组")
        parent = group_row(parent_id)
        if parent is None:
            raise BizError(1500, "关联的上级组不存在")
        if parent.group_type != "BIG":
            _bad("parentId", "上级必须是大组")
        if parent.status != "ENABLED":
            raise BizError(1501, "关联的上级组已停用，不可选择")
    _unique_name(name, parent_id, None)
    leader = _leader(body.get("leaderUserId"))
    sort_order = int(body.get("sortOrder") or 0)
    row = IpGroup(
        name=name,
        group_name=name,
        group_type=group_type,
        parent_id=parent_id,
        leader_user_id=leader,
        level=level or None,
        sort_order=sort_order,
        status="ENABLED",
        remark=remark or None,
    )
    Repository(IpGroup).create(row)
    row.code = f"IPG{row.id}"
    get_session().flush()
    _timeline(row.id, "CREATE", f"创建{name}")
    return _group_view(row)


def update_group(body: dict) -> dict:
    ident = _pid(body.get("id"), "id")
    if not ident:
        _bad("id", "请选择 IP 组")
    row = group_row(ident)
    if row is None:
        raise BizError(1500, "关联的IP组不存在")
    _assert_write(row)
    if "groupType" in body and str(body.get("groupType") or "") not in {"", row.group_type}:
        _bad("groupType", "组类型不可修改")
    if "groupName" in body:
        name = _text(body, "groupName", "groupName", "组名", 50, required=True)
        parent_for_name = row.parent_id
        if "parentId" in body and row.group_type == "SMALL":
            parent_for_name = _pid(body.get("parentId"), "parentId")
        _unique_name(name, parent_for_name, row.id)
        row.group_name = name
        row.name = name
    if "level" in body:
        level = str(body.get("level") or "").strip()
        if level:
            require_dict("dict_ip_group_level", level, "level", "等级")
        row.level = level or None
    if "sortOrder" in body:
        row.sort_order = int(body.get("sortOrder") or 0)
    if "remark" in body:
        row.remark = _text(body, "remark", "remark", "备注", 255) or None
    if "leaderUserId" in body:
        row.leader_user_id = _leader(body.get("leaderUserId"))
    if "status" in body:
        status = str(body.get("status") or "").strip()
        require_dict("dict_ip_group_status", status, "status", "状态")
        if status != row.status and status == "DISABLED":
            _timeline(row.id, "DISABLE", f"停用{group_label(row)}")
        row.status = status
    if row.group_type == "BIG":
        row.parent_id = None
    elif "parentId" in body:
        parent_id = _pid(body.get("parentId"), "parentId")
        if not parent_id:
            _bad("parentId", "请选择上级大组")
        if parent_id == row.id or parent_id in _subtree_ids(row.id):
            _bad("parentId", "不能选择自己或下级组")
        parent = group_row(parent_id)
        if parent is None:
            raise BizError(1500, "关联的上级组不存在")
        if parent.group_type != "BIG":
            _bad("parentId", "上级必须是大组")
        if parent.status != "ENABLED" and parent.id != row.parent_id:
            raise BizError(1501, "关联的上级组已停用，不可选择")
        row.parent_id = parent.id
    get_session().flush()
    return _group_view(row)


def delete_group(ident: int) -> dict:
    row = group_row(ident)
    if row is None:
        raise BizError(1500, "关联的IP组不存在")
    _assert_write(row)
    session = get_session()
    if session.scalar(select(IpGroup.id).where(IpGroup.parent_id == row.id)):
        raise BizError(1206, "该 IP 组下仍有成员、账号、关联作者或子小组，禁止删除")
    if session.scalar(select(IpMember.id).where(IpMember.group_id == row.id)):
        raise BizError(1206, "该 IP 组下仍有成员、账号、关联作者或子小组，禁止删除")
    if session.scalar(select(PlatformAccount.id).where(PlatformAccount.ip_group_id == row.id)):
        raise BizError(1206, "该 IP 组下仍有成员、账号、关联作者或子小组，禁止删除")
    if session.scalar(select(IpAnchor.id).where(IpAnchor.ip_group_id == row.id)):
        raise BizError(1206, "该 IP 组下仍有成员、账号、关联作者或子小组，禁止删除")
    if session.scalar(select(Author.id).where(Author.ip_group_id == row.id)):
        raise BizError(1206, "该 IP 组下仍有成员、账号、关联作者或子小组，禁止删除")
    _timeline(row.id, "DELETE", f"删除{group_label(row)}")
    Repository(IpGroup).soft_delete(row.id)
    return {}


def _member_view(row: IpMember) -> dict:
    user = user_brief(row.user_id)
    return {
        "id": row.id,
        "ipGroupId": row.group_id,
        "userId": row.user_id,
        "userName": user["name"] or "—",
        "position": row.position or "",
        "positionLabel": _POS.get(row.position or "", row.position or "—"),
        "relationType": row.relation_type or "PRIMARY",
        "relationLabel": _REL.get(row.relation_type or "PRIMARY", "主职"),
        "isLeader": int(row.is_leader or 0) == 1,
    }


def members(group_id: int) -> dict:
    row = _readable_group(group_id)
    rows = list(get_session().scalars(select(IpMember).where(IpMember.group_id == row.id).order_by(IpMember.id.asc())))
    return {"list": [_member_view(item) for item in rows], "total": len(rows)}


def _readable_group(group_id: int) -> IpGroup:
    row = group_row(group_id)
    if row is None:
        raise BizError(1500, "关联的IP组不存在")
    _assert_visible(row)
    return row


def _writable_group(group_id: int) -> IpGroup:
    row = _readable_group(group_id)
    _assert_write(row)
    return row


def add_member(group_id: int, body: dict) -> dict:
    group = _writable_group(group_id)
    user_id = _pid(body.get("userId"), "userId")
    if not user_id:
        _bad("userId", "请选择成员")
    user = get_session().get(User, user_id)
    if user is None or int(user.deleted or 0) != 0 or user.status != "ACTIVE":
        raise BizError(1204, "成员用户不存在或已停用/离职")
    position = require_dict("dict_position", str(body.get("position") or ""), "position", "岗位")
    relation = str(body.get("relationType") or "PRIMARY").strip()
    require_dict("dict_member_relation", relation, "relationType", "主兼")
    session = get_session()
    exists = session.scalar(select(IpMember).where(IpMember.group_id == group.id, IpMember.user_id == user.id))
    if exists is not None:
        _bad("userId", "该用户已在本组，不能重复添加")
    leader = bool(body.get("isLeader"))
    row = IpMember(group_id=group.id, user_id=user.id, position=position, relation_type=relation, is_leader=1 if leader else 0)
    session.add(row)
    if leader:
        group.leader_user_id = user.id
    session.flush()
    return _member_view(row)


def update_member(group_id: int, member_id: int, body: dict) -> dict:
    group = _writable_group(group_id)
    row = get_session().get(IpMember, member_id)
    if row is None or int(row.group_id) != int(group.id):
        raise BizError(1500, "关联的成员不存在")
    if "position" in body:
        row.position = require_dict("dict_position", str(body.get("position") or ""), "position", "岗位")
    if "relationType" in body:
        relation = str(body.get("relationType") or "").strip()
        require_dict("dict_member_relation", relation, "relationType", "主兼")
        row.relation_type = relation
    if "isLeader" in body:
        leader = bool(body.get("isLeader"))
        row.is_leader = 1 if leader else 0
        if leader:
            group.leader_user_id = row.user_id
        elif group.leader_user_id == row.user_id:
            group.leader_user_id = None
    get_session().flush()
    return _member_view(row)


def remove_member(group_id: int, member_id: int) -> dict:
    group = _writable_group(group_id)
    row = get_session().get(IpMember, member_id)
    if row is None or int(row.group_id) != int(group.id):
        raise BizError(1500, "关联的成员不存在")
    hint = ""
    if group.leader_user_id and int(group.leader_user_id) == int(row.user_id or 0):
        group.leader_user_id = None
        hint = "请重新指定组长"
    get_session().delete(row)
    get_session().flush()
    return {"hint": hint}


def _account_view(row: PlatformAccount) -> dict:
    return {
        "id": row.id,
        "accountNo": row.account_no or row.code or "",
        "nickname": row.nickname or row.name,
        "platform": row.platform or "",
        "platformLabel": _PLATFORM.get(row.platform or "", row.platform or ""),
        "status": row.status,
        "ownerUserId": row.owner_user_id,
        "ownerName": user_brief(row.owner_user_id)["name"] or "—",
        "authorId": row.author_user_id,
        "authorName": author_label(row.author_user_id) or "—",
        "ipGroupId": row.ip_group_id,
        "ipGroupText": group_chain(row.ip_group_id) or "—",
    }


def accounts(group_id: int) -> dict:
    group = _readable_group(group_id)
    session = get_session()
    if group.group_type == "BIG":
        child_ids = [row.id for row in session.scalars(select(IpGroup).where(IpGroup.parent_id == group.id))]
        rows = []
        if child_ids:
            rows = list(session.scalars(select(PlatformAccount).where(PlatformAccount.ip_group_id.in_(child_ids)).order_by(PlatformAccount.id.desc())))
        return {"list": [_account_view(item) for item in rows], "total": len(rows), "readOnly": True, "hint": "请在小组下绑定账号"}
    rows = list(session.scalars(select(PlatformAccount).where(PlatformAccount.ip_group_id == group.id).order_by(PlatformAccount.id.desc())))
    return {"list": [_account_view(item) for item in rows], "total": len(rows), "readOnly": False, "hint": ""}


def bind_accounts(group_id: int, body: dict) -> dict:
    group = _writable_group(group_id)
    if group.group_type != "SMALL":
        raise BizError(1203, "大组不可绑定账号")
    raw = body.get("accountIds")
    if raw is None and body.get("accountId"):
        raw = [body.get("accountId")]
    if not isinstance(raw, list) or not raw:
        _bad("accountIds", "请选择账号")
    session = get_session()
    bound = []
    for item in raw:
        account = session.get(PlatformAccount, _pid(item, "accountIds") or 0)
        if account is None or int(account.deleted or 0) != 0:
            raise BizError(1500, "关联的账号不存在")
        if account.status == "CANCELLED":
            raise BizError(1501, "关联的账号已停用，不可选择")
        if account.ip_group_id and int(account.ip_group_id) != int(group.id):
            other = group_label(group_row(account.ip_group_id)) or "其他组"
            raise BizError(1205, f"账号已属于其他 IP 组：{other}")
        author_id = resolve_author_id(group.id, current_author_id=account.author_user_id)
        account.ip_group_id = group.id
        account.author_user_id = author_id
        log_event(account.id, "IP_BIND", "绑定IP组", group_label(group))
        bound.append(_account_view(account))
    session.flush()
    return {"list": bound}


def unbind_account(group_id: int, account_id: int) -> dict:
    group = _writable_group(group_id)
    account = get_session().get(PlatformAccount, account_id)
    if account is None or int(account.ip_group_id or 0) != int(group.id):
        raise BizError(1500, "关联的账号不存在")
    account.ip_group_id = None
    log_event(account.id, "IP_UNBIND", "解绑IP组", "作者引用仍保留")
    get_session().flush()
    data = _account_view(account)
    data["hint"] = "作者引用仍保留，可在账号详情调整"
    return data


def _anchor_view(row: IpAnchor) -> dict:
    author = author_row(row.author_id)
    return {
        "id": row.id,
        "ipGroupId": row.ip_group_id,
        "authorId": row.author_id,
        "authorName": author_label(row.author_id) or "—",
        "authorType": row.anchor_type or (author.author_type if author else ""),
        "authorTypeLabel": _AUTHOR_TYPE.get(row.anchor_type or (author.author_type if author else ""), "—"),
        "isPrimary": int(row.is_primary or 0) == 1,
        "userName": user_brief(author.user_id)["name"] if author and author.user_id else "—",
        "primaryAccountNo": _account_no(author.primary_account_id) if author else "—",
    }


def _account_no(ident: int | None) -> str:
    if not ident:
        return "—"
    row = get_session().get(PlatformAccount, int(ident))
    if row is None:
        return "—"
    return row.account_no or row.nickname or "—"


def anchors(group_id: int) -> dict:
    group = _readable_group(group_id)
    rows = list(get_session().scalars(select(IpAnchor).where(IpAnchor.ip_group_id == group.id).order_by(IpAnchor.id.asc())))
    return {"list": [_anchor_view(item) for item in rows], "total": len(rows), "readOnly": group.group_type != "SMALL"}


def add_anchors(group_id: int, body: dict) -> dict:
    group = _writable_group(group_id)
    if group.group_type != "SMALL":
        raise BizError(1203, "大组不可关联作者")
    raw = body.get("authorIds")
    if raw is None and body.get("authorId"):
        raw = [body.get("authorId")]
    if not isinstance(raw, list) or not raw:
        _bad("authorId", "请选择作者")
    primary = bool(body.get("isPrimary"))
    anchor_type = str(body.get("anchorType") or "").strip()
    session = get_session()
    created = []
    for item in raw:
        author = author_row(_pid(item, "authorId"))
        if author is None:
            raise BizError(1500, "关联的作者不存在")
        if author.status != "ENABLED":
            raise BizError(1501, "关联的作者已停用，不可选择")
        exists = session.scalar(select(IpAnchor).where(IpAnchor.ip_group_id == group.id, IpAnchor.author_id == author.id))
        if exists is not None:
            _bad("authorId", "该作者已关联本组")
        kind = anchor_type or author.author_type or None
        if kind:
            require_dict("dict_author_type", kind, "anchorType", "作者类型")
        row = IpAnchor(ip_group_id=group.id, author_id=author.id, anchor_type=kind, is_primary=0)
        session.add(row)
        session.flush()
        if primary:
            _promote(group.id, row)
            primary = False
        created.append(_anchor_view(row))
    return {"list": created}


def _promote(group_id: int, row: IpAnchor) -> None:
    session = get_session()
    others = list(session.scalars(select(IpAnchor).where(IpAnchor.ip_group_id == int(group_id), IpAnchor.is_primary == 1)))
    for other in others:
        if other.id != row.id:
            other.is_primary = 0
    row.is_primary = 1
    _timeline(group_id, "PRIMARY", f"主作者改为{author_label(row.author_id)}")
    backfill_empty_authors(group_id, row.author_id)


def set_primary(group_id: int, rel_id: int) -> dict:
    group = _writable_group(group_id)
    row = get_session().get(IpAnchor, rel_id)
    if row is None or int(row.ip_group_id) != int(group.id):
        raise BizError(1500, "关联的作者不存在")
    _promote(group.id, row)
    get_session().flush()
    return _anchor_view(row)


def remove_anchor(group_id: int, rel_id: int) -> dict:
    group = _writable_group(group_id)
    row = get_session().get(IpAnchor, rel_id)
    if row is None or int(row.ip_group_id) != int(group.id):
        raise BizError(1500, "关联的作者不存在")
    hint = ""
    if int(row.is_primary or 0) == 1:
        hint = "请重新指定主作者"
    Repository(IpAnchor).soft_delete(row.id)
    return {"hint": hint}


def stats(group_id: int) -> dict:
    group = _readable_group(group_id)
    members, accounts, authors = _counts()
    ids = [group.id]
    if group.group_type == "BIG":
        ids = list(_subtree_ids(group.id)) or []
    return {
        "memberCount": sum(members.get(int(item), 0) for item in ids),
        "accountCount": sum(accounts.get(int(item), 0) for item in ids),
        "authorCount": sum(authors.get(int(item), 0) for item in ids),
        "fanCount": 0,
        "workCount": 0,
        "contentCount": 0,
        "roi": 0,
        "cost": 0,
        "revenue": 0,
        "mock": True,
        "mockLabel": "示意数据，采集/财务上线后替换",
    }


def _author_no() -> str:
    day = today().strftime("%Y%m%d")
    prefix = f"AU-{day}-"
    rows = list(get_session().scalars(select(Author.author_no).where(Author.author_no.like(f"{prefix}%"))))
    highest = 0
    for item in rows:
        tail = str(item or "")[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:03d}"


def _author_groups(author_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(IpAnchor).where(IpAnchor.author_id == int(author_id))))
    return [{"ipGroupId": row.ip_group_id, "groupName": group_chain(row.ip_group_id), "isPrimary": int(row.is_primary or 0) == 1} for row in rows]


def _visible_author(row: Author) -> bool:
    allowed = _scope_ids()
    if allowed is None:
        return True
    if row.ip_group_id and int(row.ip_group_id) in allowed:
        return True
    linked = {int(item.ip_group_id) for item in get_session().scalars(select(IpAnchor).where(IpAnchor.author_id == row.id))}
    return bool(linked & allowed)


def _author_view(row: Author, *, detail: bool = False) -> dict:
    data = {
        "id": row.id,
        "authorNo": row.author_no or row.code or "",
        "authorName": row.author_name or row.name,
        "authorType": row.author_type or "",
        "authorTypeLabel": _AUTHOR_TYPE.get(row.author_type or "", row.author_type or "—"),
        "ipGroupId": row.ip_group_id,
        "ipGroupText": group_chain(row.ip_group_id) or "—",
        "userId": row.user_id,
        "userName": user_brief(row.user_id)["name"] or "—",
        "primaryAccountId": row.primary_account_id,
        "primaryAccountNo": _account_no(row.primary_account_id),
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "remark": row.remark or "",
        "updateTime": when(row.update_time),
    }
    if detail:
        data["groups"] = _author_groups(row.id)
        data["dashboardHint"] = "看板指标随后续直播与分析模块提供"
    return data


def author_page(page, params: dict) -> dict:
    stmt = select(Author).order_by(Author.update_time.desc(), Author.id.desc())
    keyword = str(params.get("keyword") or "").strip()
    if keyword:
        stmt = stmt.where(or_(Author.author_name.contains(keyword), Author.author_no.contains(keyword), Author.name.contains(keyword)))
    status = str(params.get("status") or "").strip()
    if status:
        stmt = stmt.where(Author.status == status)
    author_type = str(params.get("authorType") or "").strip()
    if author_type:
        stmt = stmt.where(Author.author_type == author_type)
    group_id = _pid(params.get("ipGroupId"), "ipGroupId")
    if group_id:
        linked = select(IpAnchor.author_id).where(IpAnchor.ip_group_id == group_id)
        stmt = stmt.where(or_(Author.ip_group_id == group_id, Author.id.in_(linked)))
    user_id = _pid(params.get("userId"), "userId")
    if user_id:
        stmt = stmt.where(Author.user_id == user_id)
    rows = [row for row in get_session().scalars(stmt) if _visible_author(row)]
    chunk, total = _slice(rows, page)
    return page_result([_author_view(row) for row in chunk], total, page)


def _apply_author(row: Author, body: dict, *, creating: bool) -> None:
    if creating or "authorName" in body:
        name = _text(body, "authorName", "authorName", "作者名", 64, required=True)
        row.author_name = name
        row.name = name
    if creating or "authorType" in body:
        kind = str(body.get("authorType") or "").strip()
        require_dict("dict_author_type", kind, "authorType", "作者类型")
        row.author_type = kind
    if "ipGroupId" in body:
        raw = body.get("ipGroupId")
        if raw in (None, ""):
            row.ip_group_id = None
        else:
            group = require_small_group(raw)
            row.ip_group_id = group.id
    if "userId" in body:
        row.user_id = _leader(body.get("userId"))
    if "remark" in body:
        row.remark = _text(body, "remark", "remark", "备注", 255) or None
    if "status" in body and not creating:
        status = str(body.get("status") or "").strip()
        require_dict("dict_author_status", status, "status", "状态")
        row.status = status
    if "primaryAccountId" in body:
        account_id = _pid(body.get("primaryAccountId"), "primaryAccountId")
        row.primary_account_id = account_id
        if account_id:
            _check_pool(row, account_id)


def create_author(body: dict) -> dict:
    row = Author(status="ENABLED")
    number = str(body.get("authorNo") or "").strip() or _author_no()
    row.author_no = number
    row.code = number
    _apply_author(row, body, creating=True)
    Repository(Author).create(row)
    return _author_view(row, detail=True)


def author_detail(ident: int) -> dict:
    row = author_row(ident)
    if row is None:
        raise BizError(1500, "关联的作者不存在")
    if not _visible_author(row):
        raise BizError(1008, "您无权查看该作者")
    return _author_view(row, detail=True)


def update_author(ident: int, body: dict) -> dict:
    row = author_row(ident)
    if row is None:
        raise BizError(1500, "关联的作者不存在")
    if not _visible_author(row):
        raise BizError(1008, "您无权查看该作者")
    _apply_author(row, body, creating=False)
    get_session().flush()
    return _author_view(row, detail=True)


def author_status(ident: int, body: dict) -> dict:
    status = str(body.get("status") or "").strip()
    require_dict("dict_author_status", status, "status", "状态")
    return update_author(ident, {"status": status})


def delete_author(ident: int) -> dict:
    row = author_row(ident)
    if row is None:
        raise BizError(1500, "关联的作者不存在")
    session = get_session()
    accounts = session.scalar(select(func.count()).select_from(PlatformAccount).where(PlatformAccount.author_user_id == row.id)) or 0
    anchors = session.scalar(select(func.count()).select_from(IpAnchor).where(IpAnchor.author_id == row.id)) or 0
    if int(accounts) or int(anchors):
        total = int(accounts) + int(anchors)
        raise BizError(1502, f"该作者已被{total}条账号或组关联引用，不能删除")
    Repository(Author).soft_delete(row.id)
    return {}


def _check_pool(author: Author, account_id: int) -> None:
    if not author.ip_group_id:
        raise BizError(1001, data={"fieldErrors": [{"field": "primaryAccountId", "message": "请先为作者指定归属小组"}]})
    account = get_session().get(PlatformAccount, int(account_id))
    if account is None or int(account.deleted or 0) != 0:
        raise BizError(1500, "关联的账号不存在")
    if int(account.ip_group_id or 0) != int(author.ip_group_id):
        raise BizError(1127, MSG_1127)


def export_authors(params: dict) -> dict:
    from app.core.pagination import Page

    data = author_page(Page(1, 5000), params)
    header = ["作者编号", "作者名", "类型", "归属IP组", "绑定用户", "主推号", "状态", "更新时间"]
    body = [
        [
            item["authorNo"],
            item["authorName"],
            item["authorTypeLabel"],
            item["ipGroupText"],
            item["userName"],
            item["primaryAccountNo"],
            item["statusLabel"],
            item["updateTime"],
        ]
        for item in data["list"]
    ]
    return remember_export("作者列表.xlsx", header, body, "ipg_author")


def selector_groups(page, params: dict) -> dict:
    only_small = str(params.get("onlySmall") or "").lower() in {"1", "true", "yes"}
    only_big = str(params.get("onlyBig") or "").lower() in {"1", "true", "yes"}
    keyword = str(params.get("keyword") or "").strip()
    raw_ids = str(params.get("ids") or "").strip()
    rows = [row for row in _all_groups() if row.status == "ENABLED"]
    if only_small:
        rows = [row for row in rows if row.group_type == "SMALL"]
    if only_big:
        rows = [row for row in rows if row.group_type == "BIG"]
    if raw_ids:
        wanted = set()
        for item in raw_ids.split(","):
            number = _pid(item.strip(), "ids")
            if number:
                wanted.add(number)
        rows = [row for row in _all_groups() if int(row.id) in wanted]
    elif keyword:
        rows = [row for row in rows if keyword in group_label(row) or keyword in group_chain(row.id)]
    if not rows and not keyword and not raw_ids:
        raise BizError(1221, "选择器暂无可选数据")
    options = []
    for row in rows:
        chain = group_chain(row.id)
        options.append(
            {
                "id": row.id,
                "groupName": group_label(row),
                "groupType": row.group_type,
                "parentId": row.parent_id,
                "label": chain,
                "status": row.status,
            }
        )
    chunk, total = _slice(options, page)
    return page_result(chunk, total, page)


def selector_authors(page, params: dict) -> dict:
    keyword = str(params.get("keyword") or "").strip()
    raw_ids = str(params.get("ids") or "").strip()
    stmt = select(Author).where(Author.status == "ENABLED").order_by(Author.id.desc())
    group_id = _pid(params.get("ipGroupId"), "ipGroupId")
    if raw_ids:
        wanted = []
        for item in raw_ids.split(","):
            number = _pid(item.strip(), "ids")
            if number:
                wanted.append(number)
        rows = list(get_session().scalars(select(Author).where(Author.id.in_(wanted)))) if wanted else []
    else:
        if group_id:
            linked = select(IpAnchor.author_id).where(IpAnchor.ip_group_id == group_id)
            stmt = stmt.where(or_(Author.ip_group_id == group_id, Author.id.in_(linked)))
        rows = list(get_session().scalars(stmt))
        if keyword:
            rows = [row for row in rows if keyword in (row.author_name or "") or keyword in (row.name or "")]
    if not rows and not keyword and not raw_ids:
        raise BizError(1221, "选择器暂无可选数据")
    options = [
        {
            "id": row.id,
            "authorName": row.author_name or row.name,
            "ipGroupId": row.ip_group_id,
            "authorType": row.author_type or "",
            "label": row.author_name or row.name,
        }
        for row in rows
    ]
    chunk, total = _slice(options, page)
    return page_result(chunk, total, page)
