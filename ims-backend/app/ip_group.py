from __future__ import annotations

from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import check_enum, ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import DictData, User
from app.football_client import sum_revenue
from app.ops_models import (
    AccountCost,
    AuthorUser,
    InternalAccount,
    InternalContent,
    IpGroup,
    IpGroupAnchorRel,
    IpGroupMember,
    PlatformAccount,
)

router = APIRouter(prefix="/ip-group", tags=["ip-group"])
BJ = timezone(timedelta(hours=8))


def bj_text(value) -> str:
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(BJ).strftime("%Y-%m-%d %H:%M:%S")


def status_api(value: str) -> int:
    return 1 if value == "ENABLED" else 0


def status_store(value: int | str | None, default: str = "ENABLED") -> str:
    if value is None:
        return default
    if value in (0, "0", "DISABLED", False):
        return "DISABLED"
    if value in (1, "1", "ENABLED", True):
        return "ENABLED"
    return str(value)


def load_scope_ip_groups(db: Session, request: Request, actor: User) -> None:
    scope = getattr(request.state, "scope", None)
    if scope is None or scope.kind != "IP_GROUP":
        return
    if getattr(scope, "ip_group_ids", None):
        return
    from app.models import UserScope

    rows = db.scalars(
        select(UserScope.scope_value).where(
            UserScope.user_id == actor.id,
            UserScope.deleted == 0,
            UserScope.scope_type == "IP_GROUP",
            UserScope.tenant_id == tenant_of(actor),
        )
    ).all()
    scope.ip_group_ids = sorted({int(row) for row in rows if str(row).isdigit()})


def scoped_group_ids(request: Request) -> list[int] | None:
    scope = getattr(request.state, "scope", None)
    if scope is None or scope.kind != "IP_GROUP":
        return None
    ids = getattr(scope, "ip_group_ids", None) or []
    return ids if ids else []


def group_row_visible(group_id: int, request: Request) -> bool:
    allowed = scoped_group_ids(request)
    if allowed is None:
        return True
    return group_id in allowed


def get_group(ops: Session, actor: User, group_id: int) -> IpGroup | None:
    row = ops.get(IpGroup, group_id)
    if not visible(row, actor):
        return None
    return row


def check_local_user(db: Session, actor: User, user_id: int | None, required: bool = False):
    if user_id is None:
        if required:
            return fail(1001, "组长用户必填")
        return None
    user = db.get(User, user_id)
    if user is None or user.deleted or user.status != "ENABLED":
        return fail(1204, "成员用户不存在")
    if (user.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    return None


def clean_group_name(name: str | None):
    text = (name or "").strip()
    if not text:
        return None, fail(1001, "IP 组名称必填")
    if len(text) > 50:
        return None, fail(1001, "名称长度 1-50 字符")
    return text, None


def clean_description(text: str | None):
    value = (text or "").strip()
    if len(value) > 200:
        return None, fail(1001, "描述长度 0-200 字符")
    return value, None


def clean_level(db: Session, level: str | None):
    text = (level or "").strip()
    if not text:
        return "", None
    err = check_enum(db, "dict_ip_group_level", text, False)
    if err is not None:
        return None, err
    return text, None


RELATION_TYPES = {"PRIMARY": "主职", "PART_TIME": "兼职"}


def position_labels(db: Session) -> dict[str, str]:
    rows = db.scalars(
        select(DictData).where(DictData.dict_type == "dict_position", DictData.deleted == 0, DictData.status == "ENABLED")
    ).all()
    return {row.dict_value: row.dict_label for row in rows}


def clean_position(db: Session, position: str | None, required: bool):
    text = (position or "").strip()
    err = check_enum(db, "dict_position", text, required)
    if err is not None:
        return None, err
    return text, None


def clean_relation(value: str | None):
    text = (value or "PRIMARY").strip().upper()
    if text not in RELATION_TYPES:
        return None, fail(1001, "主/兼取值非法")
    return text, None


def sibling_name_taken(ops: Session, actor: User, parent_id: int | None, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(IpGroup.id).where(
        IpGroup.deleted == 0,
        IpGroup.tenant_id == tenant_of(actor),
        IpGroup.group_name == name,
        IpGroup.parent_id == parent_id,
    )
    if exclude_id is not None:
        stmt = stmt.where(IpGroup.id != exclude_id)
    return ops.scalar(stmt) is not None


def descendant_ids(ops: Session, root_id: int, tenant_id: int) -> set[int]:
    rows = ops.execute(
        select(IpGroup.id, IpGroup.parent_id).where(IpGroup.deleted == 0, IpGroup.tenant_id == tenant_id)
    ).all()
    children: dict[int | None, list[int]] = {}
    for gid, parent in rows:
        children.setdefault(parent, []).append(gid)
    found: set[int] = set()

    def walk(node: int) -> None:
        for child in children.get(node, []):
            found.add(child)
            walk(child)

    walk(root_id)
    return found


def counts_for(ops: Session, group_ids: list[int], tenant_id: int) -> dict[int, dict[str, int]]:
    if not group_ids:
        return {}
    members = ops.execute(
        select(IpGroupMember.ip_group_id, func.count())
        .where(
            IpGroupMember.deleted == 0,
            IpGroupMember.tenant_id == tenant_id,
            IpGroupMember.ip_group_id.in_(group_ids),
        )
        .group_by(IpGroupMember.ip_group_id)
    ).all()
    accounts = ops.execute(
        select(PlatformAccount.ip_group_id, func.count())
        .where(
            PlatformAccount.deleted == 0,
            PlatformAccount.tenant_id == tenant_id,
            PlatformAccount.ip_group_id.in_(group_ids),
        )
        .group_by(PlatformAccount.ip_group_id)
    ).all()
    anchors = ops.execute(
        select(IpGroupAnchorRel.ip_group_id, func.count())
        .where(
            IpGroupAnchorRel.deleted == 0,
            IpGroupAnchorRel.tenant_id == tenant_id,
            IpGroupAnchorRel.ip_group_id.in_(group_ids),
        )
        .group_by(IpGroupAnchorRel.ip_group_id)
    ).all()
    out: dict[int, dict[str, int]] = {gid: {"memberCount": 0, "accountCount": 0, "anchorCount": 0} for gid in group_ids}
    for gid, count in members:
        out[gid]["memberCount"] = int(count)
    for gid, count in accounts:
        out[gid]["accountCount"] = int(count)
    for gid, count in anchors:
        out[gid]["anchorCount"] = int(count)
    return out


def tree_nodes(
    ops: Session,
    db: Session,
    actor: User,
    request: Request,
    *,
    accessible_only: bool,
) -> list[dict]:
    tenant_id = tenant_of(actor)
    rows = ops.scalars(
        select(IpGroup).where(IpGroup.deleted == 0, IpGroup.tenant_id == tenant_id).order_by(IpGroup.sort_order, IpGroup.id)
    ).all()
    allowed = scoped_group_ids(request)
    if accessible_only and allowed is not None:
        keep: set[int] = set()
        by_id = {row.id: row for row in rows}
        for gid in allowed:
            if gid not in by_id:
                continue
            keep.add(gid)
            parent = by_id[gid].parent_id
            while parent and parent in by_id:
                keep.add(parent)
                parent = by_id[parent].parent_id
        rows = [row for row in rows if row.id in keep]
    ids = [row.id for row in rows]
    stats = counts_for(ops, ids, tenant_id)
    leader_ids = {row.leader_user_id for row in rows if row.leader_user_id}
    leaders = user_names(db, leader_ids)
    by_parent: dict[int | None, list[IpGroup]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def build(parent_id: int | None) -> list[dict]:
        nodes: list[dict] = []
        for row in by_parent.get(parent_id, []):
            cnt = stats.get(row.id, {})
            nodes.append(
                {
                    "id": row.id,
                    "groupName": row.group_name,
                    "groupType": row.group_type,
                    "parentId": row.parent_id,
                    "leaderUserName": leaders.get(row.leader_user_id or 0, ""),
                    "memberCount": cnt.get("memberCount", 0),
                    "accountCount": cnt.get("accountCount", 0),
                    "anchorCount": cnt.get("anchorCount", 0),
                    "leaderUserId": row.leader_user_id,
                    "level": row.level or "",
                    "sortOrder": row.sort_order,
                    "remark": row.remark or "",
                    "status": status_api(row.status),
                    "createdAt": bj_text(row.created_at),
                    "updatedAt": bj_text(row.updated_at),
                    "children": build(row.id),
                }
            )
        return nodes

    return build(None)


class GroupCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    groupName: str
    groupType: str
    parentId: int | None = None
    leaderUserId: int | None = None
    level: str | None = None
    description: str | None = None
    remark: str | None = None
    status: int | str | None = 1
    sortOrder: int | None = 0
    dingDeptId: int | None = None


class GroupUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int
    groupName: str | None = None
    parentId: int | None = None
    leaderUserId: int | None = None
    leaderId: int | None = None
    level: str | None = None
    remark: str | None = None
    description: str | None = None
    status: int | str | None = None
    sortOrder: int | None = None
    dingDeptId: int | None = None


class MemberBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: int
    position: str = ""
    relationType: str | None = "PRIMARY"
    isLeader: bool | None = None


class MemberUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    position: str | None = None
    relationType: str | None = None
    isLeader: bool | None = None


class AccountsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    accountIds: list[int] = Field(default_factory=list)
    accountRole: str | None = None


class AnchorsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    anchorUserIds: list[int] = Field(default_factory=list)
    authorId: int | None = None
    anchorType: str | None = None
    isPrimary: bool | None = None


@router.get("/tree")
def ip_group_tree(
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    return ok(tree_nodes(ops, db, actor, request, accessible_only=False))


@router.get("/accessible-tree")
def ip_group_accessible_tree(
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    return ok(tree_nodes(ops, db, actor, request, accessible_only=True))


@router.get("/list")
def ip_group_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    page: int | None = None,
    size: int | None = None,
    keyword: str = "",
    groupType: str = "",
    status: int | str | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    page_no = page if page and page > 0 else pageNo
    page_size = size if size and size > 0 else pageSize
    page_no, page_size = page_args(page_no, min(page_size, 200))
    stmt = select(IpGroup).where(IpGroup.deleted == 0, IpGroup.tenant_id == tenant_of(actor))
    allowed = scoped_group_ids(request)
    if allowed is not None:
        if not allowed:
            return paged([], 0, page_no, page_size)
        stmt = stmt.where(IpGroup.id.in_(allowed))
    if keyword:
        stmt = stmt.where(IpGroup.group_name.like(f"%{keyword}%"))
    if groupType:
        stmt = stmt.where(IpGroup.group_type == groupType)
    if status is not None and status != "":
        stmt = stmt.where(IpGroup.status == status_store(status))
    else:
        stmt = stmt.where(IpGroup.status == "ENABLED")
    total = int(ops.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = ops.scalars(stmt.order_by(IpGroup.sort_order, IpGroup.id).offset((page_no - 1) * page_size).limit(page_size)).all()
    stats = counts_for(ops, [row.id for row in rows], tenant_of(actor))
    leaders = user_names(db, {row.leader_user_id for row in rows if row.leader_user_id})
    items = [
        {
            "id": row.id,
            "groupName": row.group_name,
            "groupType": row.group_type,
            "parentId": row.parent_id,
            "leaderUserId": row.leader_user_id,
            "leaderUserName": leaders.get(row.leader_user_id or 0, ""),
            "level": row.level,
            "sortOrder": row.sort_order,
            "remark": row.remark,
            "dingDeptId": row.ding_dept_id,
            "status": status_api(row.status),
            "memberCount": stats.get(row.id, {}).get("memberCount", 0),
            "accountCount": stats.get(row.id, {}).get("accountCount", 0),
            "anchorCount": stats.get(row.id, {}).get("anchorCount", 0),
        }
        for row in rows
    ]
    return paged(items, total, page_no, page_size)


@router.post("/create")
def ip_group_create(
    body: GroupCreateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    name, name_err = clean_group_name(body.groupName)
    if name_err is not None:
        return name_err
    description, desc_err = clean_description(body.remark if body.remark is not None else body.description)
    if desc_err is not None:
        return desc_err
    level, level_err = clean_level(db, body.level)
    if level_err is not None:
        return level_err
    group_type = (body.groupType or "").upper()
    if group_type not in ("BIG", "SMALL"):
        return fail(1003, "组类型非法")
    parent_id = body.parentId
    if group_type == "BIG":
        parent_id = None
    elif parent_id is None:
        return fail(1003, "小组必须指定上级大组")
    else:
        parent = get_group(ops, actor, parent_id)
        if parent is None or parent.group_type != "BIG":
            return fail(1003, "上级组必须为大组")
    if sibling_name_taken(ops, actor, parent_id, name):
        return fail(1002, "同父级下名称重复")
    err = check_local_user(db, actor, body.leaderUserId)
    if err is not None:
        return err
    now = utcnow()
    row = IpGroup(
        group_name=name,
        group_type=group_type,
        parent_id=parent_id,
        leader_user_id=body.leaderUserId,
        level=level or "",
        sort_order=body.sortOrder or 0,
        remark=description or "",
        ding_dept_id=body.dingDeptId,
        status=status_store(body.status),
        tenant_id=tenant_of(actor),
        created_at=now,
        updated_at=now,
    )
    ops.add(row)
    ops.flush()
    return ok(row.id)


@router.put("/update")
def ip_group_update(
    body: GroupUpdateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_group(ops, actor, body.id)
    if row is None:
        return fail(1504, "资源不可用")
    if "leaderUserId" in body.model_fields_set or "leaderId" in body.model_fields_set:
        leader_id = body.leaderUserId if "leaderUserId" in body.model_fields_set else body.leaderId
        if leader_id is not None:
            err = check_local_user(db, actor, leader_id)
            if err is not None:
                return err
        row.leader_user_id = leader_id
    parent_id = row.parent_id if body.parentId is None else body.parentId
    if body.parentId is not None:
        if row.group_type == "BIG":
            return fail(1003, "大组不可修改上级")
        if body.parentId == row.id:
            return fail(1003, "上级组不能是自己")
        if body.parentId in descendant_ids(ops, row.id, tenant_of(actor)):
            return fail(1003, "上级组不能是子孙节点")
        parent = get_group(ops, actor, body.parentId)
        if parent is None or parent.group_type != "BIG":
            return fail(1003, "上级组必须为大组")
        parent_id = body.parentId
        row.parent_id = parent_id
    if body.groupName is None:
        new_name = row.group_name
    else:
        new_name, name_err = clean_group_name(body.groupName)
        if name_err is not None:
            return name_err
    if body.level is not None:
        level, level_err = clean_level(db, body.level)
        if level_err is not None:
            return level_err
        row.level = level or ""
    if body.remark is not None or body.description is not None:
        description, desc_err = clean_description(body.remark if body.remark is not None else body.description)
        if desc_err is not None:
            return desc_err
        row.remark = description or ""
    if sibling_name_taken(ops, actor, parent_id, new_name, exclude_id=row.id):
        return fail(1002, "同父级下名称重复")
    row.group_name = new_name
    if body.sortOrder is not None:
        row.sort_order = body.sortOrder
    if body.dingDeptId is not None:
        row.ding_dept_id = body.dingDeptId
    if body.status is not None:
        row.status = status_store(body.status)
    row.updated_at = utcnow()
    return ok(True)


@router.delete("/delete")
def ip_group_delete(
    id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = get_group(ops, actor, id)
    if row is None:
        return fail(1504, "资源不可用")
    tenant_id = tenant_of(actor)
    has_member = ops.scalar(
        select(IpGroupMember.id).where(
            IpGroupMember.ip_group_id == id, IpGroupMember.deleted == 0, IpGroupMember.tenant_id == tenant_id
        )
    )
    has_account = ops.scalar(
        select(PlatformAccount.id).where(
            PlatformAccount.ip_group_id == id, PlatformAccount.deleted == 0, PlatformAccount.tenant_id == tenant_id
        )
    )
    has_anchor = ops.scalar(
        select(IpGroupAnchorRel.id).where(
            IpGroupAnchorRel.ip_group_id == id, IpGroupAnchorRel.deleted == 0, IpGroupAnchorRel.tenant_id == tenant_id
        )
    )
    if has_member or has_account or has_anchor:
        return fail(1005, "该 IP 组下存在数据，禁止删除")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(True)


def ensure_group_access(request: Request, db: Session, actor: User, group_id: int, ops: Session) -> IpGroup | None:
    load_scope_ip_groups(db, request, actor)
    row = get_group(ops, actor, group_id)
    if row is None:
        return None
    if not group_row_visible(group_id, request):
        return None
    return row


@router.get("/{group_id}/members")
def ip_group_members(
    group_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    members = ops.scalars(
        select(IpGroupMember).where(
            IpGroupMember.ip_group_id == group_id,
            IpGroupMember.deleted == 0,
            IpGroupMember.tenant_id == tenant_of(actor),
        )
    ).all()
    names = user_names(db, {m.user_id for m in members})
    labels = position_labels(db)
    return ok(
        [
            {
                "id": m.id,
                "userId": m.user_id,
                "userName": names.get(m.user_id, ""),
                "position": m.position,
                "positionName": labels.get(m.position, m.position),
                "relationType": m.relation_type,
                "relationTypeName": RELATION_TYPES.get(m.relation_type, m.relation_type),
                "isLeader": m.is_leader == 1,
            }
            for m in members
        ]
    )


@router.post("/{group_id}/members")
def ip_group_add_member(
    group_id: int,
    body: MemberBody,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    err = check_local_user(db, actor, body.userId, required=True)
    if err is not None:
        return err
    position, pos_err = clean_position(db, body.position, True)
    if pos_err is not None:
        return pos_err
    relation, rel_err = clean_relation(body.relationType)
    if rel_err is not None:
        return rel_err
    exists = ops.scalar(
        select(IpGroupMember.id).where(
            IpGroupMember.ip_group_id == group_id,
            IpGroupMember.user_id == body.userId,
            IpGroupMember.deleted == 0,
            IpGroupMember.tenant_id == tenant_of(actor),
        )
    )
    if exists:
        return fail(1001, "成员已存在")
    is_leader = 1 if body.isLeader else 0
    ops.add(
        IpGroupMember(
            ip_group_id=group_id,
            user_id=body.userId,
            position=position or "",
            relation_type=relation or "PRIMARY",
            is_leader=is_leader,
            tenant_id=tenant_of(actor),
        )
    )
    return ok(True)


@router.put("/{group_id}/members/{member_id}")
def ip_group_update_member(
    group_id: int,
    member_id: int,
    body: MemberUpdateBody,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    member = ops.get(IpGroupMember, member_id)
    if member is None or member.deleted or member.ip_group_id != group_id or member.tenant_id != tenant_of(actor):
        return fail(1504, "资源不可用")
    if body.position is not None:
        position, pos_err = clean_position(db, body.position, True)
        if pos_err is not None:
            return pos_err
        member.position = position or ""
    if body.relationType is not None:
        relation, rel_err = clean_relation(body.relationType)
        if rel_err is not None:
            return rel_err
        member.relation_type = relation or "PRIMARY"
    if body.isLeader is not None:
        member.is_leader = 1 if body.isLeader else 0
    member.updated_at = utcnow()
    return ok(True)


@router.delete("/{group_id}/members/{member_id}")
def ip_group_delete_member(
    group_id: int,
    member_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    member = ops.get(IpGroupMember, member_id)
    if member is None or member.deleted or member.ip_group_id != group_id:
        return fail(1504, "资源不可用")
    member.deleted = 1
    member.updated_at = utcnow()
    return ok(True)


def account_vo(row: PlatformAccount) -> dict:
    return {
        "id": row.id,
        "accountNo": row.account_no,
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "platformAccountId": row.platform_account_id,
        "authorUserId": row.author_user_id,
        "status": row.status,
    }


@router.get("/{group_id}/accounts")
def ip_group_accounts(
    group_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    accounts = ops.scalars(
        select(PlatformAccount).where(
            PlatformAccount.ip_group_id == group_id,
            PlatformAccount.deleted == 0,
            PlatformAccount.tenant_id == tenant_of(actor),
        )
    ).all()
    return ok([account_vo(item) for item in accounts])


@router.post("/{group_id}/accounts")
def ip_group_bind_accounts(
    group_id: int,
    body: AccountsBody,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1501, "IP 组已停用")
    if row.group_type != "SMALL":
        return fail(1203, "大组不可绑定账号")
    if not body.accountIds:
        return fail(1001, "账号必填")
    tenant_id = tenant_of(actor)
    for account_id in body.accountIds:
        account = ops.get(PlatformAccount, account_id)
        if not visible(account, actor):
            return fail(1500, "账号不存在")
        if account.status == "DISABLED":
            return fail(1501, "账号已停用")
        other_group = account.ip_group_id or 0
        if other_group and other_group != group_id:
            other = ops.get(IpGroup, other_group)
            other_name = other.group_name if other else str(other_group)
            return fail(1007, f"账号已属于其他 IP 组：{other_name}")
        account.ip_group_id = group_id
        account.updated_at = utcnow()
    return ok(True)


@router.get("/{group_id}/anchors")
def ip_group_anchors(
    group_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    rels = ops.scalars(
        select(IpGroupAnchorRel).where(
            IpGroupAnchorRel.ip_group_id == group_id,
            IpGroupAnchorRel.deleted == 0,
            IpGroupAnchorRel.tenant_id == tenant_of(actor),
        )
    ).all()
    author_ids = {rel.anchor_user_id for rel in rels}
    authors = {
        item.id: item
        for item in ops.scalars(
            select(AuthorUser).where(AuthorUser.id.in_(author_ids), AuthorUser.deleted == 0)
        ).all()
    }
    user_ids = {a.user_id for a in authors.values() if a.user_id}
    names = user_names(db, user_ids)
    items = []
    for rel in rels:
        author = authors.get(rel.anchor_user_id)
        items.append(
            {
                "id": rel.id,
                "authorId": rel.anchor_user_id,
                "authorName": author.author_name if author else "",
                "anchorUserId": rel.anchor_user_id,
                "anchorUserName": author.author_name if author else "",
                "anchorType": rel.anchor_type or (author.author_type if author else ""),
                "isPrimary": rel.is_primary == 1,
                "bindUserName": names.get(author.user_id, "") if author and author.user_id else "",
            }
        )
    return ok(items)


@router.post("/{group_id}/anchors")
def ip_group_bind_anchors(
    group_id: int,
    body: AnchorsBody,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    author_ids = list(body.anchorUserIds)
    if body.authorId is not None:
        author_ids.append(body.authorId)
    author_ids = [aid for aid in author_ids if aid]
    if not author_ids:
        return fail(1001, "作者必填")
    tenant_id = tenant_of(actor)
    for author_id in author_ids:
        author = ops.get(AuthorUser, author_id)
        if not visible(author, actor) or author.status != "ENABLED":
            return fail(1500, "作者不存在")
        exists = ops.scalar(
            select(IpGroupAnchorRel.id).where(
                IpGroupAnchorRel.ip_group_id == group_id,
                IpGroupAnchorRel.anchor_user_id == author_id,
                IpGroupAnchorRel.deleted == 0,
                IpGroupAnchorRel.tenant_id == tenant_id,
            )
        )
        if not exists:
            ops.add(
                IpGroupAnchorRel(
                    ip_group_id=group_id,
                    anchor_user_id=author_id,
                    anchor_type=(body.anchorType or author.author_type or "").strip(),
                    is_primary=0,
                    tenant_id=tenant_id,
                )
            )
        if author.ip_group_id != group_id:
            author.ip_group_id = group_id
    ops.flush()
    if body.isPrimary:
        primary_id = int(author_ids[-1])
        for rel_row in ops.scalars(
            select(IpGroupAnchorRel).where(
                IpGroupAnchorRel.ip_group_id == group_id,
                IpGroupAnchorRel.deleted == 0,
                IpGroupAnchorRel.tenant_id == tenant_id,
            )
        ).all():
            rel_row.is_primary = 1 if int(rel_row.anchor_user_id) == primary_id else 0
        ops.flush()
    return ok(True)


def _sum_int(ops: Session, column, *where) -> int:
    value = ops.scalar(select(func.coalesce(func.sum(column), 0)).where(*where))
    return int(value or 0)


def group_stats(ops: Session, group_id: int, tenant_id: int) -> dict:
    """BR-M1-004：当前组加上全部下级组，计数与成本按子项相加。"""
    ids = descendant_ids(ops, group_id, tenant_id)
    ids.add(group_id)
    id_list = list(ids)
    account_where = (
        PlatformAccount.deleted == 0,
        PlatformAccount.tenant_id == tenant_id,
        PlatformAccount.ip_group_id.in_(id_list),
    )
    account_rows = ops.scalars(select(PlatformAccount).where(*account_where)).all()
    account_ids = [row.id for row in account_rows]
    cost_total = 0.0
    if account_ids:
        cost_total = round(
            float(
                ops.scalar(
                    select(func.coalesce(func.sum(AccountCost.amount), 0)).where(
                        AccountCost.deleted == 0,
                        AccountCost.tenant_id == tenant_id,
                        AccountCost.account_id.in_(account_ids),
                    )
                )
                or 0
            ),
            2,
        )
    revenue_delayed = False
    revenue_total = 0.0
    seen_authors: set[str] = set()
    end = utcnow().date()
    start = end - timedelta(days=29)
    for account in account_rows:
        author_key = str(account.author_user_id) if account.author_user_id else str(account.id)
        if author_key in seen_authors:
            continue
        seen_authors.add(author_key)
        revenue, err = sum_revenue(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            author_id=author_key,
        )
        if err:
            revenue_delayed = True
            break
        revenue_total = round(revenue_total + float(revenue or 0), 2)
    roi_avg = None
    revenue_out: float | None = None if revenue_delayed else revenue_total
    if revenue_out is not None and cost_total > 0:
        roi_avg = round(revenue_out / cost_total, 2)
    internal_where = (
        InternalAccount.deleted == 0,
        InternalAccount.tenant_id == tenant_id,
        InternalAccount.ip_group_id.in_(id_list),
    )
    content_where = (
        InternalContent.deleted == 0,
        InternalContent.tenant_id == tenant_id,
        InternalContent.ip_group_id.in_(id_list),
    )
    return {
        "ipGroupId": group_id,
        "followerCount": _sum_int(ops, InternalAccount.follower_count, *internal_where),
        "contentCount": _sum_int(ops, InternalAccount.content_count, *internal_where),
        "accountCount": len(account_rows),
        "internalContentCount": int(
            ops.scalar(select(func.count()).select_from(InternalContent).where(*content_where)) or 0
        ),
        "roiAvg": roi_avg,
        "costTotal": cost_total,
        "revenueTotal": revenue_out,
        "revenueDelayed": revenue_delayed,
        "last7DaysTrend": [],
        "last30DaysTrend": [],
    }


@router.get("/{group_id}/stats")
def ip_group_stats(
    group_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ensure_group_access(request, db, actor, group_id, ops)
    if row is None:
        return fail(1504, "资源不可用")
    return ok(group_stats(ops, group_id, tenant_of(actor)))
