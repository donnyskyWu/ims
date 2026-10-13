"""账号到作者的解析。禁止用第一条或最小编号猜测。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.errors import BizError
from app.core.serialize import parse_api_id
from app.db.session import get_session
from app.domains.master.model import Author, IpAnchor, IpGroup, PlatformAccount

MSG_1223 = "账号所属 IP 组存在多名作者且未指定主作者（或组内无作者）"


def fail(field: str, message: str) -> None:
    raise BizError(1001, data={"fieldErrors": [{"field": field, "message": message}]})


def anchors_of(group_id: int) -> list[IpAnchor]:
    return list(
        get_session().scalars(select(IpAnchor).where(IpAnchor.ip_group_id == int(group_id)).order_by(IpAnchor.id.asc()))
    )


def require_small_group(raw, *, required: bool = True) -> IpGroup | None:
    if raw in (None, ""):
        if required:
            fail("ipGroupId", "请选择 IP 小组")
        return None
    try:
        ident = int(parse_api_id(raw))
    except BizError:
        fail("ipGroupId", "请选择 IP 小组")
        return None
    row = get_session().get(IpGroup, ident)
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的 IP 组不存在")
    if row.status != "ENABLED":
        raise BizError(1501, "关联的 IP 组已停用，不可选择")
    if (row.group_type or "BIG") != "SMALL":
        raise BizError(1203, "大组不可绑定账号或关联作者")
    return row


def resolve_from_group(group_id: int) -> int:
    rows = anchors_of(group_id)
    primary = [row for row in rows if int(row.is_primary or 0) == 1]
    if primary:
        return int(primary[0].author_id)
    if len(rows) == 1:
        return int(rows[0].author_id)
    raise BizError(1223, MSG_1223)


def load_author(raw, field: str = "authorId") -> Author:
    try:
        ident = int(parse_api_id(raw))
    except BizError:
        fail(field, "请选择作者")
        raise
    row = get_session().get(Author, ident)
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的作者不存在")
    if row.status != "ENABLED":
        raise BizError(1501, "关联的作者已停用，不可选择")
    return row


def materialize_author(group_id: int, *, explicit_author=None, current_author=None) -> int:
    """写账号或绑账号时确定 author_user_id。已有物化值优先于组内推断。"""
    if explicit_author not in (None, ""):
        author = load_author(explicit_author)
        home = int(author.ip_group_id or 0)
        if home and home != int(group_id):
            raise BizError(1127, "作者与账号不在同一 IP 组账号池")
        return int(author.id)
    if current_author not in (None, "", 0):
        return int(current_author)
    return resolve_from_group(group_id)


def assert_same_pool(author_id: int, account_id: int) -> None:
    """供后续上报直接调用。作者归属小组与账号 IP 组必须相同。"""
    author = get_session().get(Author, int(author_id))
    account = get_session().get(PlatformAccount, int(account_id))
    if author is None or int(getattr(author, "deleted", 0) or 0) != 0:
        raise BizError(1500, "关联的作者不存在")
    if account is None or int(getattr(account, "deleted", 0) or 0) != 0:
        raise BizError(1500, "关联的平台账号不存在")
    home = int(author.ip_group_id or 0)
    pool = int(account.ip_group_id or 0)
    if not home or home != pool:
        raise BizError(1127, "作者与账号不在同一 IP 组账号池")
