from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of
from app.layout_html import sanitize_layout_html
from app.models import (
    ContentPlan,
    ContentProject,
    ContentPublish,
    ContentPublishSeq,
    ContentReview,
    ContentReviewSeq,
    ContentSop,
    ContentSopNode,
    ContentSopSeq,
    ContentTask,
    Role,
    User,
    UserRole,
)
from app.ops_models import IpGroup, PlatformAccount
from app.content_review_preview import build_content_preview
from app.settings_runtime import get_param, param_bool

router = APIRouter(prefix="/content", tags=["content"])

BJ = timezone(timedelta(hours=8))
DEFAULT_REVIEW_CHECKLIST = [
    {"itemCode": "COMPLIANCE", "itemDesc": "合规性", "required": True},
    {"itemCode": "QUALITY", "itemDesc": "内容质量", "required": True},
    {"itemCode": "BRAND", "itemDesc": "品牌一致性", "required": True},
]
def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def tenant(actor: User) -> int:
    return tenant_of(actor)


def next_seq(db: Session, model, tenant_id: int, prefix: str) -> str:
    now = datetime.now(BJ)
    biz_date = now.strftime("%Y%m%d")
    row = db.scalar(select(model).where(model.tenant_id == tenant_id, model.biz_date == biz_date))
    if row is None:
        row = model(biz_date=biz_date, tenant_id=tenant_id, seq_val=0)
        db.add(row)
        db.flush()
    row.seq_val += 1
    return f"{prefix}{biz_date}{row.seq_val:04d}"


class SopNodeReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    nodeOrder: int
    nodeName: str
    standardDesc: str = ""
    deliverableSpec: dict = Field(default_factory=dict)
    qualityChecklist: list = Field(default_factory=list)
    ownerRole: str = "R6"
    nodeType: str = "NORMAL"
    documentType: str = ""
    predecessors: list[int] = Field(default_factory=list)
    parallelGroup: str = ""
    needReview: int = 0
    reviewerRole: str = ""
    slaHours: int = 24


class SopCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sopName: str
    contentType: str
    sopLevel: str = "STANDARD"
    marketingPlan: str = ""
    nodes: list[SopNodeReq]


class SopNodeCheckBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contentProjectId: int
    checklistResults: list[dict]
    deliverableOssKeys: list[str] = Field(default_factory=list)


class PlanCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    planName: str
    sopId: int
    ipGroupIds: list[int]
    startDate: str
    endDate: str
    description: str | None = ""


class PlanTerminateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reason: str | None = ""


class ReviewConclusionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conclusion: str
    checklistResult: dict
    rejectItems: list[dict] | None = None
    backToNodeName: str | None = None
    remark: str | None = None


class PublishCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contentProjectId: int
    accountId: int
    platform: str
    planPublishAt: str
    caption: str | None = ""
    topicTags: list[str] | None = None


class PublishReceiptBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    publishUrl: str
    publishedAt: str


def sop_vo(row: ContentSop) -> dict:
    return {
        "id": row.id,
        "sopCode": row.sop_code,
        "sopName": row.sop_name,
        "contentType": row.content_type,
        "sopLevel": row.sop_level,
        "version": row.version,
        "status": row.status,
        "nodeCount": row.node_count,
        "marketingPlan": row.marketing_plan or "",
        "createdAt": iso(row.created_at),
    }


def publish_vo(row: ContentPublish, *, archive_id: int | None = None) -> dict:
    return {
        "id": row.id,
        "publishNo": row.publish_no,
        "contentProjectId": row.content_project_id,
        "accountId": row.account_id,
        "accountNo": row.account_no,
        "platform": row.platform,
        "planPublishAt": row.plan_publish_at,
        "publishUrl": row.publish_url,
        "publishStatus": row.publish_status,
        "operatorUserId": row.operator_user_id,
        "archiveId": archive_id if archive_id is not None else (row.id if row.archive_no else None),
        "createdAt": iso(row.created_at),
    }


def node_vo(row: ContentSopNode) -> dict:
    return {
        "id": row.id,
        "sopId": row.sop_id,
        "nodeOrder": row.node_order,
        "nodeName": row.node_name,
        "standardDesc": row.standard_desc,
        "deliverableSpec": row.deliverable_spec or {},
        "qualityChecklist": row.quality_checklist or [],
        "ownerRole": row.owner_role,
        "nodeType": row.node_type or "NORMAL",
        "documentType": row.document_type or "",
        "predecessors": list(row.predecessors or []),
        "parallelGroup": row.parallel_group or "",
        "needReview": int(row.need_review or 0),
        "reviewerRole": row.reviewer_role or "",
        "slaHours": row.sla_hours,
    }


def load_sop(db: Session, sop_id: int, actor: User) -> ContentSop | None:
    row = db.get(ContentSop, sop_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


_NODE_TYPES = {"NORMAL", "CONTENT_GENERATION", "CONTENT_PUBLISH"}


def validate_sop_nodes(nodes: list[SopNodeReq]) -> str | None:
    """SOP 节点与 DAG。环、缺执行岗位等返回 1500 文案；通过则 None。"""
    if not nodes:
        return "参数校验失败"
    names: list[str] = []
    orders: list[int] = []
    for item in nodes:
        name = (item.nodeName or "").strip()
        if not name or len(name) > 64:
            return "参数校验失败"
        if name in names:
            return "节点名重复"
        names.append(name)
        if item.nodeOrder in orders:
            return "参数校验失败"
        orders.append(item.nodeOrder)
        ntype = (item.nodeType or "NORMAL").strip() or "NORMAL"
        if ntype not in _NODE_TYPES:
            return "参数校验失败"
        if ntype == "CONTENT_GENERATION" and not (item.documentType or "").strip():
            return "内容生成节点须填写文档类型"
        if not (item.ownerRole or "").strip():
            return "节点缺执行岗位"
        if int(item.slaHours or 0) < 1:
            return "参数校验失败"
        if int(item.needReview or 0) not in (0, 1):
            return "参数校验失败"
        if int(item.needReview or 0) == 1 and not (item.reviewerRole or "").strip():
            return "审核岗位必填"
    order_set = set(orders)
    graph: dict[int, list[int]] = {}
    for item in nodes:
        preds = [int(p) for p in (item.predecessors or [])]
        if item.nodeOrder in preds:
            return "DAG 存在环"
        for pred in preds:
            if pred not in order_set:
                return "前置节点不存在"
        graph[item.nodeOrder] = preds
    color = {order: 0 for order in order_set}

    def walk(node_order: int) -> bool:
        color[node_order] = 1
        for pred in graph[node_order]:
            if color[pred] == 1:
                return True
            if color[pred] == 0 and walk(pred):
                return True
        color[node_order] = 2
        return False

    for order in order_set:
        if color[order] == 0 and walk(order):
            return "DAG 存在环"
    return None


def save_nodes(db: Session, sop: ContentSop, nodes: list[SopNodeReq]) -> None:
    if not nodes:
        raise ValueError("empty nodes")
    ordered = sorted(nodes, key=lambda item: item.nodeOrder)
    for item in ordered:
        ntype = (item.nodeType or "NORMAL").strip() or "NORMAL"
        db.add(
            ContentSopNode(
                sop_id=sop.id,
                node_order=item.nodeOrder,
                node_name=item.nodeName[:64],
                standard_desc=item.standardDesc[:4000],
                deliverable_spec=item.deliverableSpec or {},
                quality_checklist=item.qualityChecklist or [],
                owner_role=item.ownerRole[:16],
                node_type=ntype[:32],
                document_type=(item.documentType or "")[:32],
                predecessors=[int(p) for p in (item.predecessors or [])],
                parallel_group=(item.parallelGroup or "")[:64],
                need_review=1 if int(item.needReview or 0) else 0,
                reviewer_role=(item.reviewerRole or "")[:32],
                sla_hours=max(1, int(item.slaHours or 24)),
                tenant_id=sop.tenant_id,
            )
        )
    sop.node_count = len(ordered)


def ip_group_names(ops: Session, ids: list[int]) -> tuple[list[str], list[dict]]:
    names: list[str] = []
    groups: list[dict] = []
    for gid in ids:
        group = ops.get(IpGroup, int(gid))
        if group is None or group.deleted:
            continue
        names.append(group.group_name)
        groups.append({"ipGroupId": group.id, "ipGroupName": group.group_name})
    return names, groups


def plan_vo(db: Session, ops: Session, row: ContentPlan) -> dict:
    sop = db.get(ContentSop, row.sop_id)
    ids = list(row.ip_group_ids or [])
    names, groups = ip_group_names(ops, ids)
    return {
        "id": row.id,
        "planName": row.plan_name,
        "sopId": row.sop_id,
        "sopName": sop.sop_name if sop else "",
        "status": row.plan_status,
        "startDate": row.start_date,
        "endDate": row.end_date,
        "description": row.description,
        "terminateReason": (row.terminate_reason or "")[:512],
        "ipGroupId": ids[0] if ids else None,
        "ipGroupName": "、".join(names),
        "ipGroupIds": ids,
        "ipGroupNames": names,
        "ipGroups": groups,
        "createdAt": iso(row.created_at),
    }


def review_match_fields(db: Session, project_id: int, *, include_scheme: bool) -> dict:
    """审核抽屉只读场次：沿用内容项目已有 matchType / matchScheme / matchSummary。"""
    project = db.get(ContentProject, project_id) if project_id else None
    if project is None or project.deleted:
        fields: dict = {"matchType": None, "matchSummary": "", "competitionName": ""}
        if include_scheme:
            fields["matchScheme"] = []
        return fields
    summary = (project.match_summary or "").strip() or (project.competition_name or "")
    fields = {
        "matchType": project.match_type,
        "matchSummary": summary,
        "competitionName": project.competition_name or "",
    }
    if include_scheme:
        fields["matchScheme"] = list(project.match_scheme or [])
    return fields


def review_vo(db: Session, row: ContentReview, *, include_scheme: bool = False) -> dict:
    submitter = db.get(User, row.submitter_user_id)
    data = {
        "id": row.id,
        "reviewNo": row.review_no,
        "contentProjectId": row.content_project_id,
        "contentTitle": row.content_title,
        "submitterUserId": row.submitter_user_id,
        "submitterName": (submitter.nickname or submitter.username) if submitter else "",
        "reviewerUserId": row.reviewer_user_id,
        "reviewRound": row.review_round,
        "checklistResult": row.checklist_result,
        "conclusion": row.conclusion,
        "rejectItems": row.reject_items,
        "remark": row.remark or "",
        "firstPass": bool(row.first_pass) if row.first_pass is not None else None,
        "reviewedAt": row.reviewed_at,
        "createdAt": iso(row.created_at),
    }
    data.update(review_match_fields(db, row.content_project_id, include_scheme=include_scheme))
    return data


_REVIEW_ROLE_LABELS = {
    "OPS_LEADER": "运营组长",
    "ip_group_leader": "IP组长",
    "OPS_DIRECTOR": "运营总监",
    "DEPT_HEAD": "部门负责人",
    "ops_manager": "运营经理",
}
_LEADER_ROLE_KEYS = {"OPS_LEADER", "ip_group_leader"}
_FB_STATUS_LABELS = {
    "NONE": "未同步",
    "PENDING": "待同步",
    "SYNCED": "成功",
    "COMPENSATING": "补偿中",
    "FAILED": "失败",
}


def _role_label(code: str) -> str:
    text = (code or "").strip()
    return _REVIEW_ROLE_LABELS.get(text, text or "审核人")


def _user_label(user: User | None) -> str:
    if user is None or user.deleted or user.status != "ENABLED":
        return ""
    return (user.nickname or user.username or "").strip()


def _names_for_role(db: Session, role_key: str) -> list[str]:
    key = (role_key or "").strip()
    if not key:
        return []
    role = db.scalar(select(Role).where(Role.role_key == key, Role.deleted == 0))
    if role is None:
        return []
    user_ids = list(db.scalars(select(UserRole.user_id).where(UserRole.role_id == role.id)).all())
    if not user_ids:
        return []
    users = db.scalars(select(User).where(User.id.in_(user_ids), User.deleted == 0)).all()
    names: list[str] = []
    seen: set[str] = set()
    for user in users:
        name = _user_label(user)
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _ip_leader_name(db: Session, ops: Session, project: ContentProject | None) -> str:
    if project is None or not project.ip_group_id:
        return ""
    group = ops.get(IpGroup, int(project.ip_group_id))
    if group is None or group.deleted or not group.leader_user_id:
        return ""
    return _user_label(db.get(User, int(group.leader_user_id)))


def _latest_review_for_round(rows: list[ContentReview], round_no: int) -> ContentReview | None:
    matched = [row for row in rows if row.review_round == round_no]
    if not matched:
        return None
    pending = [row for row in matched if row.conclusion is None]
    pool = pending or matched
    return max(pool, key=lambda row: row.id)


def build_review_steps(
    db: Session,
    ops: Session,
    project: ContentProject | None,
    reviews: list[ContentReview],
) -> list[dict]:
    stages: list[tuple[int, str]] = []
    if param_bool("content.review.level1.enabled", db=db):
        stages.append((1, get_param("content.review.level1.role", "OPS_LEADER", db=db)))
    if param_bool("content.review.level2.enabled", db=db):
        stages.append((2, get_param("content.review.level2.role", "OPS_DIRECTOR", db=db)))
    steps: list[dict] = []
    for round_no, role_code in stages:
        names = _names_for_role(db, role_code)
        if round_no == 1 and role_code in _LEADER_ROLE_KEYS:
            leader = _ip_leader_name(db, ops, project)
            if leader and leader not in names:
                names = [leader, *names]
        role_name = _role_label(role_code)
        current = _latest_review_for_round(reviews, round_no)
        if current is None:
            status = "PENDING"
            conclusion = None
            remark = ""
        elif current.conclusion is None:
            status = "CURRENT"
            conclusion = None
            remark = current.remark or ""
        else:
            status = "DONE"
            conclusion = current.conclusion
            remark = current.remark or ""
        joined = "、".join(names) if names else "—"
        steps.append(
            {
                "round": round_no,
                "roleCode": role_code,
                "roleName": role_name,
                "reviewerNames": names,
                "label": f"{role_name}：{joined}",
                "status": status,
                "conclusion": conclusion,
                "remark": remark,
            }
        )
    return steps


def review_preview(ops: Session, project: ContentProject | None, author_name: str) -> dict:
    if project is None:
        return {
            "body": "",
            "layoutHtml": "",
            "documentType": "",
            "contentType": "",
            "matchType": None,
            "matchSummary": "",
            "matchScheme": [],
            "ipGroupName": "",
            "authorName": author_name,
            "fbSyncStatus": "NONE",
            "fbSyncStatusLabel": _FB_STATUS_LABELS["NONE"],
        }
    ip_name = ""
    if project.ip_group_id:
        group = ops.get(IpGroup, int(project.ip_group_id))
        if group is not None and not group.deleted:
            ip_name = group.group_name or ""
    status = project.fb_sync_status or "NONE"
    return {
        "body": project.body or "",
        "layoutHtml": project.layout_html or "",
        "documentType": project.document_type or "",
        "contentType": project.content_type or "",
        "matchType": project.match_type,
        "matchSummary": project.match_summary or project.competition_name or "",
        "matchScheme": project.match_scheme or [],
        "ipGroupName": ip_name,
        "authorName": author_name,
        "fbSyncStatus": status,
        "fbSyncStatusLabel": _FB_STATUS_LABELS.get(status, status),
    }


@router.get("/sop/list")
def sop_list(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str | None = None,
    contentType: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentSop).where(ContentSop.deleted == 0, ContentSop.tenant_id == tenant(actor))
    if keyword:
        stmt = stmt.where(ContentSop.sop_name.contains(keyword.strip()))
    if contentType:
        stmt = stmt.where(ContentSop.content_type == contentType.strip())
    if status:
        stmt = stmt.where(ContentSop.status == status.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(ContentSop.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    return paged([sop_vo(row) for row in rows], total, page_no, size)


@router.post("/sop")
def sop_create(body: SopCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    name = (body.sopName or "").strip()
    if not name or len(name) > 128 or not (body.contentType or "").strip():
        return fail(1500, "参数校验失败")
    if body.sopLevel not in ("STANDARD", "GUIDE"):
        return fail(1500, "参数校验失败")
    node_err = validate_sop_nodes(body.nodes)
    if node_err:
        return fail(1500, node_err)
    code = next_seq(db, ContentSopSeq, tenant(actor), "SP")
    sop = ContentSop(
        sop_code=code,
        sop_name=name,
        content_type=body.contentType.strip(),
        sop_level=body.sopLevel,
        marketing_plan=(body.marketingPlan or "").strip()[:32],
        version=1,
        status="ENABLED",
        creator=actor.id,
        tenant_id=tenant(actor),
    )
    db.add(sop)
    db.flush()
    try:
        save_nodes(db, sop, body.nodes)
    except ValueError:
        return fail(1500, "参数校验失败")
    return ok(sop_vo(sop))


@router.put("/sop/{sop_id}")
def sop_update(
    sop_id: int, body: SopCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    old = load_sop(db, sop_id, actor)
    if old is None:
        return fail(1504, "资源不可用")
    name = (body.sopName or old.sop_name).strip()
    if not name:
        return fail(1500, "参数校验失败")
    node_err = validate_sop_nodes(body.nodes)
    if node_err:
        return fail(1500, node_err)
    tid = tenant(actor)
    max_ver = db.scalar(
        select(func.max(ContentSop.version)).where(
            ContentSop.sop_code == old.sop_code,
            ContentSop.tenant_id == tid,
        )
    )
    next_version = int(max_ver or old.version) + 1
    for prev in db.scalars(
        select(ContentSop).where(
            ContentSop.sop_code == old.sop_code,
            ContentSop.tenant_id == tid,
            ContentSop.deleted == 0,
            ContentSop.status == "ENABLED",
        )
    ).all():
        prev.status = "DISABLED"
    sop = ContentSop(
        sop_code=old.sop_code,
        sop_name=name,
        content_type=(body.contentType or old.content_type).strip(),
        sop_level=body.sopLevel if body.sopLevel in ("STANDARD", "GUIDE") else old.sop_level,
        marketing_plan=(body.marketingPlan or old.marketing_plan or "").strip()[:32],
        version=next_version,
        status="ENABLED",
        creator=actor.id,
        tenant_id=tid,
    )
    db.add(sop)
    db.flush()
    try:
        save_nodes(db, sop, body.nodes)
    except ValueError:
        return fail(1500, "参数校验失败")
    return ok(sop_vo(sop))


@router.delete("/sop/{sop_id}")
def sop_delete(
    sop_id: int,
    confirmText: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if confirmText != "DELETE":
        return fail(1500, "参数校验失败")
    sop = load_sop(db, sop_id, actor)
    if sop is None:
        return fail(1504, "资源不可用")
    sop.deleted = 1
    for node in db.scalars(select(ContentSopNode).where(ContentSopNode.sop_id == sop.id)).all():
        node.deleted = 1
    return ok(None)


@router.get("/sop/{sop_id}/nodes")
def sop_nodes(sop_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    sop = load_sop(db, sop_id, actor)
    if sop is None:
        return fail(1504, "资源不可用")
    rows = db.scalars(
        select(ContentSopNode)
        .where(ContentSopNode.sop_id == sop.id, ContentSopNode.deleted == 0)
        .order_by(ContentSopNode.node_order.asc())
    ).all()
    return ok([node_vo(row) for row in rows])


@router.post("/sop/node/{node_id}/check")
def sop_node_check(
    node_id: int, body: SopNodeCheckBody, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    node = db.get(ContentSopNode, node_id)
    if node is None or node.deleted:
        return fail(1504, "资源不可用")
    sop = load_sop(db, node.sop_id, actor)
    if sop is None:
        return fail(1504, "资源不可用")
    project = db.get(ContentProject, body.contentProjectId)
    if project is None or project.deleted or (project.tenant_id or 0) != tenant(actor):
        return fail(1504, "资源不可用")
    checklist = node.quality_checklist or []
    required_codes = {item.get("itemCode") for item in checklist if item.get("required")}
    results = {item.get("itemCode"): bool(item.get("passed")) for item in body.checklistResults}
    failed: list[str] = []
    for code in required_codes:
        if not code or not results.get(code):
            failed.append(code)
    if body.deliverableOssKeys is None:
        failed.append("DELIVERABLE")
    elif checklist and not body.deliverableOssKeys:
        failed.append("DELIVERABLE")
    passed = len(failed) == 0
    if not passed:
        return fail(1007, "SOP 步骤不合规")
    return ok({"nodePassed": True, "failedItems": []})


@router.get("/plan")
def plan_list(
    pageNo: int = 1,
    pageSize: int = 10,
    planName: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentPlan).where(ContentPlan.deleted == 0, ContentPlan.tenant_id == tenant(actor))
    if planName:
        stmt = stmt.where(ContentPlan.plan_name.contains(planName.strip()))
    if status:
        stmt = stmt.where(ContentPlan.plan_status == status.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(ContentPlan.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    return paged([plan_vo(db, ops, row) for row in rows], total, page_no, size)


@router.post("/plan")
def plan_create(
    body: PlanCreateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    name = (body.planName or "").strip()
    if not name or len(name) > 128:
        return fail(1500, "参数校验失败")
    if not body.ipGroupIds:
        return fail(1500, "参数校验失败")
    if body.endDate < body.startDate:
        return fail(1500, "参数校验失败")
    sop = load_sop(db, body.sopId, actor)
    if sop is None or sop.status != "ENABLED":
        return fail(1501, "关联资源不可用或已停用")
    seen: list[int] = []
    for gid in body.ipGroupIds:
        gid = int(gid)
        if gid in seen:
            continue
        seen.append(gid)
        group = ops.get(IpGroup, gid)
        if group is None or group.deleted or (group.tenant_id or 0) != tenant(actor):
            return fail(1500, "参数校验失败")
        if group.status != "ENABLED":
            return fail(1501, "关联资源不可用或已停用")
    row = ContentPlan(
        plan_name=name,
        sop_id=sop.id,
        ip_group_ids=seen,
        start_date=body.startDate[:10],
        end_date=body.endDate[:10],
        description=(body.description or "")[:512],
        plan_status="DRAFT",
        creator=actor.id,
        tenant_id=tenant(actor),
    )
    db.add(row)
    db.flush()
    return ok(plan_vo(db, ops, row))


def resolve_plan_assignee(group: IpGroup, node: ContentSopNode) -> int:
    if group.leader_user_id:
        return int(group.leader_user_id)
    return 1


def load_plan(db: Session, plan_id: int, actor: User) -> ContentPlan | None:
    row = db.get(ContentPlan, plan_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


@router.post("/plan/{plan_id}/start")
def plan_start(
    plan_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_plan(db, plan_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.plan_status != "DRAFT":
        return fail(1502, "业务规则冲突")
    sop = load_sop(db, row.sop_id, actor)
    if sop is None or sop.status != "ENABLED":
        return fail(1501, "关联资源不可用或已停用")
    nodes = db.scalars(
        select(ContentSopNode)
        .where(ContentSopNode.sop_id == sop.id, ContentSopNode.deleted == 0)
        .order_by(ContentSopNode.node_order.asc())
    ).all()
    if not nodes:
        return fail(1502, "业务规则冲突")
    tid = tenant(actor)
    generated = 0
    for gid in list(row.ip_group_ids or []):
        group = ops.get(IpGroup, int(gid))
        if group is None or group.deleted or (group.tenant_id or 0) != tid:
            return fail(1500, "参数校验失败")
        if group.status != "ENABLED":
            return fail(1501, "关联资源不可用或已停用")
        author_id = int(group.leader_user_id or actor.id or 1)
        work_date = (row.start_date or "")[:10] or datetime.now(BJ).strftime("%Y-%m-%d")
        for node in nodes:
            assignee = resolve_plan_assignee(group, node)
            db.add(
                ContentTask(
                    assignment_id=0,
                    sop_id=sop.id,
                    sop_node_id=node.id,
                    ip_group_id=int(gid),
                    author_id=author_id,
                    assignee_user_id=assignee,
                    node_name=node.node_name,
                    node_type=node.node_type or "NORMAL",
                    task_status="PENDING",
                    visible_in_list=1,
                    marketing_plan=(sop.marketing_plan or "")[:32],
                    work_date=work_date,
                    plan_name=row.plan_name,
                    tenant_id=tid,
                )
            )
            generated += 1
    row.plan_status = "IN_PROGRESS"
    db.flush()
    vo = plan_vo(db, ops, row)
    vo["tasksGenerated"] = generated
    return ok(vo)


def terminate_plan_tasks(db: Session, plan_name: str, tid: int) -> int:
    """计划批准终止：未完成关联任务 → TERMINATED（对齐 OPS 计划终止语义）。"""
    rows = db.scalars(
        select(ContentTask).where(
            ContentTask.plan_name == plan_name,
            ContentTask.tenant_id == tid,
            ContentTask.task_status.not_in(("DONE", "TERMINATED", "CANCELLED")),
        )
    ).all()
    for task in rows:
        task.task_status = "TERMINATED"
    return len(rows)


def assert_plan_terminate_approver(actor: User) -> bool:
    """桩：终止审批人（OPS_LEADER）；E2E/联调默认 admin id=1 通过。"""
    return int(actor.id or 0) == 1


@router.post("/plan/{plan_id}/terminate")
def plan_terminate(
    plan_id: int,
    body: PlanTerminateBody | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_plan(db, plan_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.plan_status != "IN_PROGRESS":
        return fail(1502, "业务规则冲突")
    reason = ((body.reason if body else None) or "").strip()[:512]
    row.plan_status = "TERMINATE_PENDING"
    row.terminate_reason = reason
    db.flush()
    return ok(plan_vo(db, ops, row))


@router.post("/plan/{plan_id}/terminate/approve")
def plan_terminate_approve(
    plan_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not assert_plan_terminate_approver(actor):
        return fail(1503, "无操作权限")
    row = load_plan(db, plan_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.plan_status != "TERMINATE_PENDING":
        return fail(1502, "业务规则冲突")
    tid = tenant(actor)
    tasks_terminated = terminate_plan_tasks(db, row.plan_name, tid)
    row.plan_status = "TERMINATED"
    db.flush()
    vo = plan_vo(db, ops, row)
    vo["tasksTerminated"] = tasks_terminated
    return ok(vo)


@router.post("/plan/{plan_id}/terminate/reject")
def plan_terminate_reject(
    plan_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not assert_plan_terminate_approver(actor):
        return fail(1503, "无操作权限")
    row = load_plan(db, plan_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.plan_status != "TERMINATE_PENDING":
        return fail(1502, "业务规则冲突")
    row.plan_status = "IN_PROGRESS"
    row.terminate_reason = ""
    db.flush()
    return ok(plan_vo(db, ops, row))


@router.get("/review/queue")
def review_queue(
    pageNo: int = 1,
    pageSize: int = 10,
    reviewerUserId: int | None = None,
    overdueOnly: bool = False,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentReview).where(
        ContentReview.deleted == 0,
        ContentReview.tenant_id == tenant(actor),
        ContentReview.conclusion.is_(None),
    )
    if reviewerUserId is not None:
        stmt = stmt.where(ContentReview.reviewer_user_id == reviewerUserId)
    rows_all = db.scalars(stmt.order_by(ContentReview.created_at.asc())).all()
    filtered = []
    now = datetime.now(BJ)
    for row in rows_all:
        if overdueOnly:
            created = row.created_at.replace(tzinfo=BJ) if row.created_at.tzinfo is None else row.created_at
            if (now - created.astimezone(BJ)).total_seconds() < 12 * 3600:
                continue
        filtered.append(row)
    total = len(filtered)
    page_rows = filtered[(page_no - 1) * size : page_no * size]
    return paged([review_vo(db, row) for row in page_rows], total, page_no, size)


@router.get("/review/{review_no}")
def review_detail(
    review_no: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = db.scalar(
        select(ContentReview).where(
            ContentReview.review_no == review_no,
            ContentReview.deleted == 0,
            ContentReview.tenant_id == tenant(actor),
        )
    )
    if row is None:
        return fail(1504, "资源不可用")
    data = review_vo(db, row, include_scheme=True)
    checklist = []
    for item in DEFAULT_REVIEW_CHECKLIST:
        passed = None
        if row.checklist_result and item["itemCode"] in row.checklist_result:
            passed = bool(row.checklist_result[item["itemCode"]])
        checklist.append({**item, "passed": passed})
    project = db.get(ContentProject, row.content_project_id)
    if project is not None and (project.deleted or (project.tenant_id or 0) != tenant(actor)):
        project = None
    history = list(
        db.scalars(
            select(ContentReview).where(
                ContentReview.content_project_id == row.content_project_id,
                ContentReview.deleted == 0,
                ContentReview.tenant_id == tenant(actor),
            )
        ).all()
    )
    data["checklist"] = checklist
    if project is None:
        data["layoutHtml"] = ""
        data["body"] = ""
    else:
        data["layoutHtml"] = sanitize_layout_html(project.layout_html or "")
        data["body"] = project.body or ""
    data["preview"] = review_preview(ops, project, data["submitterName"])
    data["reviewSteps"] = build_review_steps(db, ops, project, history)
    data["contentPreview"] = build_content_preview(project)
    return ok(data)


@router.put("/review/{review_no}/conclusion")
def review_conclusion(
    review_no: str,
    body: ReviewConclusionBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.scalar(
        select(ContentReview).where(
            ContentReview.review_no == review_no,
            ContentReview.deleted == 0,
            ContentReview.tenant_id == tenant(actor),
        )
    )
    if row is None:
        return fail(1504, "资源不可用")
    if row.conclusion is not None:
        return fail(1500, "参数校验失败")
    if row.submitter_user_id == actor.id:
        return fail(1057, "审核人不可审自己提交的内容")
    if body.conclusion not in ("PASS", "REJECT_BACK", "TERMINATE"):
        return fail(1500, "参数校验失败")
    if body.conclusion == "REJECT_BACK" and not body.rejectItems:
        return fail(1058, "打回缺少结构化未通过项")
    remark = (body.remark or "").strip()
    if body.conclusion in ("REJECT_BACK", "TERMINATE"):
        if not remark:
            return fail(1500, "驳回意见必填")
        if len(remark) > 512:
            return fail(1500, "驳回意见超过 512 字")
    else:
        remark = ""
    reject_items = body.rejectItems
    if remark and reject_items:
        filled = []
        for item in reject_items:
            reason = str(item.get("reason") or "").strip()
            filled.append({**item, "reason": reason or remark})
        reject_items = filled
    row.conclusion = body.conclusion
    row.checklist_result = body.checklistResult or {}
    row.reject_items = reject_items
    row.remark = remark
    row.reviewer_user_id = actor.id
    row.reviewed_at = iso(utcnow())
    row.first_pass = 1 if body.conclusion == "PASS" and row.review_round == 1 else 0
    project = db.get(ContentProject, row.content_project_id)
    level2_on = param_bool("content.review.level2.enabled", db=db)
    if project is not None and body.conclusion == "PASS":
        if level2_on and row.review_round == 1:
            review_no_l2 = next_seq(db, ContentReviewSeq, tenant(actor), "RV")
            db.add(
                ContentReview(
                    review_no=review_no_l2,
                    content_project_id=row.content_project_id,
                    content_title=row.content_title,
                    submitter_user_id=row.submitter_user_id,
                    review_round=2,
                    creator=actor.id,
                    tenant_id=tenant(actor),
                )
            )
            project.content_status = "PENDING_REVIEW"
            project.review_passed = 0
        else:
            project.review_passed = 1
            project.content_status = "PENDING_PUBLISH"
    elif project is not None and body.conclusion == "REJECT_BACK":
        project.content_status = "REJECTED"
        project.review_passed = 0
    elif project is not None and body.conclusion == "TERMINATE":
        project.review_passed = 0
    return ok(None)


@router.get("/review/first-pass-stats")
def review_first_pass_stats(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    rows = db.scalars(
        select(ContentReview).where(
            ContentReview.deleted == 0,
            ContentReview.tenant_id == tenant(actor),
            ContentReview.conclusion.is_not(None),
        )
    ).all()
    total = len(rows)
    first_pass = sum(1 for row in rows if row.first_pass)
    rate = round(first_pass / total, 4) if total else 0.0
    return ok({"firstPassRate": rate, "total": total, "trend": []})


@router.get("/review/reject-analysis")
def review_reject_analysis(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    rows = db.scalars(
        select(ContentReview).where(
            ContentReview.deleted == 0,
            ContentReview.tenant_id == tenant(actor),
            ContentReview.conclusion == "REJECT_BACK",
        )
    ).all()
    counts: dict[str, int] = {}
    for row in rows:
        for item in row.reject_items or []:
            code = item.get("itemCode") or "UNKNOWN"
            counts[code] = counts.get(code, 0) + 1
    total = sum(counts.values()) or 1
    by_item = []
    for item in DEFAULT_REVIEW_CHECKLIST:
        code = item["itemCode"]
        count = counts.get(code, 0)
        by_item.append(
            {
                "itemCode": code,
                "itemDesc": item["itemDesc"],
                "count": count,
                "ratio": round(count / total, 4),
            }
        )
    return ok({"byItem": by_item})


@router.post("/publish")
def publish_create(
    body: PublishCreateBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    project = db.get(ContentProject, body.contentProjectId)
    if project is None or project.deleted or (project.tenant_id or 0) != tenant(actor):
        return fail(1504, "资源不可用")
    if not project.review_passed:
        return fail(1054, "终审未通过禁止发布")
    from app.content_ai import ai_publish_block

    blocked = ai_publish_block(db, project)
    if blocked:
        return fail(1054, blocked)
    account = ops.get(PlatformAccount, body.accountId)
    if account is None or account.deleted or (account.tenant_id or 0) != tenant(actor):
        return fail(1500, "参数校验失败")
    if account.status not in ("IN_USE", "ENABLED"):
        return fail(1501, "关联资源不可用或已停用")
    publish_no = next_seq(db, ContentPublishSeq, tenant(actor), "PB")
    row = ContentPublish(
        publish_no=publish_no,
        content_project_id=project.id,
        account_id=account.id,
        account_no=account.account_no,
        platform=body.platform.strip().upper(),
        plan_publish_at=body.planPublishAt,
        caption=(body.caption or "")[:512],
        publish_status="PENDING_PUBLISH",
        operator_user_id=actor.id,
        creator=actor.id,
        tenant_id=tenant(actor),
    )
    db.add(row)
    db.flush()
    return ok(publish_vo(row, archive_id=None))


def _parse_plan_at(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ)


def _overdue_hours(plan_at: str, now: datetime) -> float:
    planned = _parse_plan_at(plan_at)
    if planned is None:
        return 0.0
    delta = now - planned
    return max(0.0, round(delta.total_seconds() / 3600, 1))


@router.get("/publish/list")
def publish_list(
    pageNo: int = 1,
    pageSize: int = 10,
    publishStatus: str | None = None,
    accountId: int | None = None,
    platform: str | None = None,
    timeFrom: str | None = None,
    timeTo: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentPublish).where(
        ContentPublish.deleted == 0,
        ContentPublish.tenant_id == tenant(actor),
    )
    if publishStatus:
        stmt = stmt.where(ContentPublish.publish_status == publishStatus.strip().upper())
    if accountId is not None:
        stmt = stmt.where(ContentPublish.account_id == accountId)
    if platform:
        stmt = stmt.where(ContentPublish.platform == platform.strip().upper())
    if timeFrom:
        stmt = stmt.where(ContentPublish.plan_publish_at >= timeFrom)
    if timeTo:
        stmt = stmt.where(ContentPublish.plan_publish_at <= timeTo)
    rows_all = db.scalars(stmt.order_by(ContentPublish.id.desc())).all()
    total = len(rows_all)
    page_rows = rows_all[(page_no - 1) * size : page_no * size]
    return paged([publish_vo(row) for row in page_rows], total, page_no, size)


@router.get("/publish/pending")
def publish_pending(
    pageNo: int = 1,
    pageSize: int = 10,
    overdueOnly: bool = False,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, page_size = page_args(pageNo, pageSize)
    now = datetime.now(BJ)
    stmt = select(ContentPublish).where(
        ContentPublish.deleted == 0,
        ContentPublish.tenant_id == tenant(actor),
        ContentPublish.publish_status.in_(("PENDING_PUBLISH", "PUBLISH_FAILED")),
    )
    stmt = stmt.order_by(ContentPublish.plan_publish_at.asc())
    rows = list(db.scalars(stmt).all())
    project_ids = {row.content_project_id for row in rows}
    projects = {}
    if project_ids:
        for proj in db.scalars(select(ContentProject).where(ContentProject.id.in_(project_ids))).all():
            projects[proj.id] = proj
    operators = {row.operator_user_id for row in rows}
    users = {}
    if operators:
        for user in db.scalars(select(User).where(User.id.in_(operators))).all():
            users[user.id] = user.nickname or user.username
    items = []
    for row in rows:
        hours = _overdue_hours(row.plan_publish_at, now)
        if overdueOnly and hours < 24:
            continue
        proj = projects.get(row.content_project_id)
        items.append(
            {
                "publishNo": row.publish_no,
                "contentTitle": proj.title if proj else "",
                "planPublishAt": row.plan_publish_at,
                "operatorName": users.get(row.operator_user_id, ""),
                "publishStatus": row.publish_status,
                "overdueHours": hours,
                "id": row.id,
            }
        )
    total = len(items)
    start = (page_no - 1) * page_size
    page_rows = items[start : start + page_size]
    return ok({"list": page_rows, "total": total, "pageNo": page_no, "pageSize": page_size})


@router.put("/publish/{publish_id}/receipt")
def publish_receipt(
    publish_id: int,
    body: PublishReceiptBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(ContentPublish, publish_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return fail(1504, "资源不可用")
    if row.publish_status not in ("PENDING_PUBLISH", "PUBLISH_FAILED"):
        return fail(1500, "参数校验失败")
    url = (body.publishUrl or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return fail(1500, "参数校验失败")
    project = db.get(ContentProject, row.content_project_id)
    review = db.scalar(
        select(ContentReview)
        .where(
            ContentReview.content_project_id == row.content_project_id,
            ContentReview.deleted == 0,
            ContentReview.conclusion == "PASS",
        )
        .order_by(ContentReview.id.desc())
        .limit(1)
    )
    row.publish_url = url[:512]
    row.published_at = body.publishedAt or iso(datetime.now(BJ))
    row.publish_status = "ARCHIVED"
    row.archive_no = next_seq(db, ContentPublishSeq, tenant(actor), "AR")
    row.archive_package_url = f"/admin-api/ims/content/publish/{row.id}/archive/download"
    title = project.title if project else row.publish_no
    row.archive_file_list = {
        "files": [
            {"fileName": f"{title}.mp4", "fileType": "VIDEO", "fileKey": f"archive/{row.id}/video"},
            {"fileName": f"{title}-script.txt", "fileType": "SCRIPT", "fileKey": f"archive/{row.id}/script"},
            {
                "fileName": f"review-{review.review_no if review else 'na'}.json",
                "fileType": "REVIEW",
                "fileKey": f"archive/{row.id}/review",
            },
            {"fileName": "receipt.json", "fileType": "RECEIPT", "fileKey": f"archive/{row.id}/receipt"},
        ]
    }
    row.archived_at = iso(datetime.now(BJ))
    return ok(None)


@router.get("/publish/{publish_id}/archive")
def publish_archive(
    publish_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(ContentPublish, publish_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return fail(1504, "资源不可用")
    if not row.archive_no:
        return fail(1500, "参数校验失败")
    files = (row.archive_file_list or {}).get("files") or []
    return ok(
        {
            "id": row.id,
            "archiveNo": row.archive_no,
            "contentProjectId": row.content_project_id,
            "packageUrl": row.archive_package_url or "",
            "fileList": files,
            "archivedAt": row.archived_at or "",
        }
    )
