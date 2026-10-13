"""账号到作者的解析。禁止按第一条或最小编号猜测。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.errors import BizError
from app.core.serialize import parse_api_id
from app.db.session import get_session
from app.domains.master.model import Author, IpAnchor, IpGroup, PlatformAccount

MSG_1223 = "账号所属 IP 组存在多名作者且未指定主作者（或组内无作者）"
MSG_1127 = "作者与账号不在同一 IP 组账号池"


def _pid(value) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    return int(parse_api_id(value))


def group_row(ident: int | None) -> IpGroup | None:
    if not ident:
        return None
    return get_session().get(IpGroup, int(ident))


def author_row(ident: int | None) -> Author | None:
    if not ident:
        return None
    return get_session().get(Author, int(ident))


def group_label(row: IpGroup | None) -> str:
    if row is None:
        return ""
    return (row.group_name or row.name or "").strip()


def group_chain(ident: int | None) -> str:
    """小组展示成「大组 / 小组」。"""
    row = group_row(ident)
    if row is None:
        return ""
    own = group_label(row)
    if row.parent_id:
        parent = group_row(int(row.parent_id))
        parent_name = group_label(parent)
        if parent_name:
            return f"{parent_name} / {own}"
    return own


def author_label(ident: int | None) -> str:
    row = author_row(ident)
    if row is None:
        return ""
    return (row.author_name or row.name or "").strip()


def _anchors(group_id: int) -> list[IpAnchor]:
    return list(
        get_session().scalars(
            select(IpAnchor).where(IpAnchor.ip_group_id == int(group_id)).order_by(IpAnchor.id.asc())
        )
    )


def linked_author_ids(group_id: int) -> list[int]:
    return [int(row.author_id) for row in _anchors(group_id)]


def author_in_group(author_id: int, group_id: int) -> bool:
    author = author_row(author_id)
    if author is not None and int(author.ip_group_id or 0) == int(group_id):
        return True
    return author_id in linked_author_ids(group_id)


def resolve_author_id(group_id: int, current_author_id: int | None = None, explicit_author_id: int | None = None) -> int:
    """按清单优先级解析作者。显式指定最高，其次已物化，再主作者，再唯一作者。"""
    if explicit_author_id:
        author = author_row(explicit_author_id)
        if author is None or int(author.deleted or 0) != 0:
            raise BizError(1500, "关联的作者不存在")
        if author.status != "ENABLED":
            raise BizError(1501, "关联的作者已停用，不可选择")
        if not author_in_group(author.id, group_id):
            raise BizError(1127, MSG_1127)
        return int(author.id)
    if current_author_id:
        return int(current_author_id)
    rows = _anchors(group_id)
    primary = next((row for row in rows if int(row.is_primary or 0) == 1), None)
    if primary is not None:
        return int(primary.author_id)
    if len(rows) == 1:
        return int(rows[0].author_id)
    raise BizError(1223, MSG_1223)


def require_small_group(ident, *, field: str = "ipGroupId") -> IpGroup:
    """绑定和新建账号只接受启用中的小组。"""
    number = _pid(ident)
    if not number:
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "请选择 IP 小组"}]})
    row = group_row(number)
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的IP组不存在")
    if row.group_type != "SMALL":
        raise BizError(1203, "大组不可绑定账号")
    if row.status != "ENABLED":
        raise BizError(1501, "关联的IP组已停用，不可选择")
    return row


def assign_platform_author(body: dict, row: PlatformAccount | None) -> tuple[int, int]:
    """写账号时强制小组，并物化作者。"""
    if "ipGroupId" in body:
        group = require_small_group(body.get("ipGroupId"))
    elif row is not None and row.ip_group_id:
        group = require_small_group(row.ip_group_id)
    else:
        raise BizError(1001, data={"fieldErrors": [{"field": "ipGroupId", "message": "请选择 IP 小组"}]})
    submitted = "authorId" in body or "authorUserId" in body
    explicit = None
    if submitted:
        raw = body.get("authorId")
        if raw in (None, ""):
            raw = body.get("authorUserId")
        explicit = _pid(raw)
    current = None if submitted or row is None else row.author_user_id
    author_id = resolve_author_id(group.id, current_author_id=current, explicit_author_id=explicit)
    return int(group.id), int(author_id)


def assert_same_pool(author_id: int, account_id: int) -> None:
    """作者主推号必须落在作者归属小组的账号池。供本批和后续上报复用。"""
    author = author_row(author_id)
    account = get_session().get(PlatformAccount, int(account_id))
    if author is None or int(author.deleted or 0) != 0:
        raise BizError(1500, "关联的作者不存在")
    if account is None or int(account.deleted or 0) != 0:
        raise BizError(1500, "关联的账号不存在")
    if not author.ip_group_id:
        raise BizError(1001, data={"fieldErrors": [{"field": "primaryAccountId", "message": "请先为作者指定归属小组"}]})
    if int(account.ip_group_id or 0) != int(author.ip_group_id):
        raise BizError(1127, MSG_1127)


def backfill_empty_authors(group_id: int, author_id: int) -> int:
    """主作者变更后，只回填作者为空的账号。"""
    session = get_session()
    rows = list(
        session.scalars(
            select(PlatformAccount).where(
                PlatformAccount.ip_group_id == int(group_id),
                PlatformAccount.author_user_id.is_(None),
            )
        )
    )
    for row in rows:
        row.author_user_id = int(author_id)
    return len(rows)
