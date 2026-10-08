"""数据上报 REPORT-001 模板 · REPORT-002 填报 · REPORT-003 审核 · REPORT-004 完成率（W7-4~8）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import ReportAudit, ReportSubmission, ReportTemplate, User
from app.ops_models import AuthorUser, IpGroupAnchorRel, PlatformAccount

router = APIRouter(prefix="/report", tags=["report"])

BJ = timezone(timedelta(hours=8))
PERIOD_TYPES = frozenset({"DAILY", "WEEKLY", "MONTHLY"})
STATUSES = frozenset({"ENABLED", "DISABLED"})
BUSINESS_LINES = frozenset({"FINANCE", "BUSINESS", "ADMIN"})
SUBMIT_STATUSES = frozenset({"DRAFT", "SUBMITTED", "APPROVED", "REJECTED"})
AUDIT_CONCLUSIONS = frozenset({"APPROVED", "REJECTED"})
AUDIT_SLA_HOURS = 24


class FieldSchemaItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fieldKey: str
    fieldLabel: str
    fieldType: str = "TEXT"
    required: bool = False
    range: dict | None = None
    options: list[str] | None = None
    crossCheck: dict | None = None


class AssigneeItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    assignType: str = "USER"
    targetIds: list[int] = Field(default_factory=list)
    targetCodes: list[str] | None = None
    rotationList: list[dict] | None = None


class TemplateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateName: str
    fieldsSchema: list[FieldSchemaItem] = Field(default_factory=list)
    periodType: str = "DAILY"
    deadlineRule: str = "22:00"
    assignees: list[AssigneeItem] = Field(default_factory=list)
    status: str = "ENABLED"
    businessLine: str = "BUSINESS"
    deptName: str = ""


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def validate_fields_schema(fields: list[FieldSchemaItem]) -> dict | None:
    keys = {item.fieldKey for item in fields if item.fieldKey}
    for item in fields:
        cc = item.crossCheck
        if not cc:
            continue
        target = cc.get("targetFieldKey") if isinstance(cc, dict) else None
        if target and target not in keys:
            return fail(1121, "勾稽规则引用了不存在的字段")
    return None


def next_template_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"RT{day}"
    count = db.scalar(
        select(func.count())
        .select_from(ReportTemplate)
        .where(
            ReportTemplate.deleted == 0,
            ReportTemplate.tenant_id == tenant_id,
            ReportTemplate.template_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def template_vo(row: ReportTemplate) -> dict:
    fields = row.fields_schema if isinstance(row.fields_schema, list) else []
    return {
        "id": row.id,
        "templateNo": row.template_no,
        "templateName": row.template_name,
        "fieldsSchema": fields,
        "fieldCount": len(fields),
        "periodType": row.period_type,
        "deadlineRule": row.deadline_rule,
        "assignees": row.assignees if isinstance(row.assignees, list) else [],
        "version": row.version,
        "status": row.status,
        "businessLine": row.business_line,
        "deptName": row.dept_name,
        "usageCount": row.usage_count,
        "createdBy": row.created_by,
        "createdAt": iso(row.created_at),
    }


def apply_body(row: ReportTemplate, body: TemplateBody) -> None:
    row.template_name = body.templateName.strip()
    row.fields_schema = [item.model_dump() for item in body.fieldsSchema]
    row.period_type = body.periodType
    row.deadline_rule = body.deadlineRule.strip()
    row.assignees = [item.model_dump() for item in body.assignees]
    row.status = body.status
    row.business_line = body.businessLine
    row.dept_name = body.deptName.strip()
    row.updated_at = utcnow()


@router.post("/template")
def create_template(
    body: TemplateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.periodType not in PERIOD_TYPES:
        return fail(1001, "periodType 无效")
    if body.status not in STATUSES:
        return fail(1001, "status 无效")
    if body.businessLine not in BUSINESS_LINES:
        return fail(1001, "businessLine 无效")
    if not body.templateName.strip():
        return fail(1001, "templateName 必填")
    err = validate_fields_schema(body.fieldsSchema)
    if err:
        return err
    tenant_id = tenant_of(actor)
    row = ReportTemplate(
        template_no=next_template_no(db, tenant_id),
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    apply_body(row, body)
    db.add(row)
    db.flush()
    return ok(template_vo(row))


@router.get("/template/list")
def template_list(
    templateName: str | None = None,
    periodType: str | None = None,
    status: str | None = None,
    businessLine: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ReportTemplate).where(
        ReportTemplate.deleted == 0,
        ReportTemplate.tenant_id == tenant_id,
    )
    if templateName:
        stmt = stmt.where(ReportTemplate.template_name.contains(templateName.strip()))
    if periodType:
        stmt = stmt.where(ReportTemplate.period_type == periodType)
    if status:
        stmt = stmt.where(ReportTemplate.status == status)
    if businessLine:
        stmt = stmt.where(ReportTemplate.business_line == businessLine)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ReportTemplate.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([template_vo(row) for row in rows], total, page_no, size)


@router.put("/template/{template_id}")
def update_template(
    template_id: int,
    body: TemplateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.periodType not in PERIOD_TYPES or body.status not in STATUSES:
        return fail(1001, "参数无效")
    if body.businessLine not in BUSINESS_LINES:
        return fail(1001, "businessLine 无效")
    err = validate_fields_schema(body.fieldsSchema)
    if err:
        return err
    row = db.get(ReportTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1500, "模板不存在")
    apply_body(row, body)
    row.version = (row.version or 1) + 1
    db.flush()
    return ok(template_vo(row))


@router.delete("/template/{template_id}")
def disable_template(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(ReportTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1500, "模板不存在")
    row.status = "DISABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


class AttachmentItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fileName: str = ""
    fileKey: str = ""


class SubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateId: int
    period: str
    authorId: int
    accountId: int
    dataContent: dict = Field(default_factory=dict)
    attachments: list[AttachmentItem] = Field(default_factory=list)
    asDraft: bool = False


def next_submission_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"RS{day}"
    count = db.scalar(
        select(func.count())
        .select_from(ReportSubmission)
        .where(
            ReportSubmission.deleted == 0,
            ReportSubmission.tenant_id == tenant_id,
            ReportSubmission.submission_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def validate_author_account(ops: Session, actor: User, author_id: int, account_id: int):
    if not author_id or not account_id:
        return fail(1001, "authorId 与 accountId 必填")
    author = ops.get(AuthorUser, author_id)
    if not visible(author, actor):
        return fail(1500, "作者不存在")
    if author.status != "ENABLED":
        return fail(1501, "作者已停用")
    account = ops.get(PlatformAccount, account_id)
    if not visible(account, actor):
        return fail(1500, "账号不存在")
    if account.status == "DISABLED":
        return fail(1501, "账号已停用")
    group_id = author.ip_group_id or 0
    if not group_id or (account.ip_group_id or 0) != group_id:
        return fail(1127, "作者与账号 IP 组共池校验失败")
    return None


def validate_submission_data(fields: list, data: dict, strict: bool):
    if not strict:
        return None
    keys = set()
    for item in fields:
        if not isinstance(item, dict):
            continue
        key = item.get("fieldKey")
        if key:
            keys.add(key)
        if item.get("required") and (data.get(key) is None or data.get(key) == ""):
            return fail(1001, f"字段 {key} 必填")
    for item in fields:
        if not isinstance(item, dict):
            continue
        cc = item.get("crossCheck")
        if not cc or not isinstance(cc, dict):
            continue
        target = cc.get("targetFieldKey")
        op = cc.get("operator", "EQ")
        if not target or target not in keys:
            continue
        left = data.get(item.get("fieldKey"))
        right = data.get(target)
        if op == "EQ" and left != right:
            return fail(1122, cc.get("errorMsg") or "勾稽校验失败")
    return None


def find_dedup_row(
    db: Session, tenant_id: int, body: SubmitBody, submitter_id: int
) -> ReportSubmission | None:
    return db.scalar(
        select(ReportSubmission).where(
            ReportSubmission.deleted == 0,
            ReportSubmission.tenant_id == tenant_id,
            ReportSubmission.template_id == body.templateId,
            ReportSubmission.period == body.period.strip(),
            ReportSubmission.submitter_user_id == submitter_id,
            ReportSubmission.author_id == body.authorId,
            ReportSubmission.account_id == body.accountId,
        )
    )


def submission_vo(db: Session, ops: Session, row: ReportSubmission) -> dict:
    template = db.get(ReportTemplate, row.template_id)
    author = ops.get(AuthorUser, row.author_id)
    account = ops.get(PlatformAccount, row.account_id)
    names = user_names(db, {row.submitter_user_id})
    attachments = row.attachments if isinstance(row.attachments, list) else []
    data_content = row.data_content if isinstance(row.data_content, dict) else {}
    return {
        "id": row.id,
        "submissionNo": row.submission_no,
        "templateId": row.template_id,
        "templateName": template.template_name if template else "",
        "templateVersion": row.template_version,
        "period": row.period,
        "submitterUserId": row.submitter_user_id,
        "submitterName": names.get(row.submitter_user_id, ""),
        "authorId": row.author_id,
        "authorName": author.author_name if author else "",
        "accountId": row.account_id,
        "accountLabel": (account.account_no or account.account_name) if account else "",
        "dataContent": data_content,
        "attachments": attachments,
        "submitStatus": row.submit_status,
        "isOnTime": bool(row.is_on_time),
        "submittedAt": iso(row.submitted_at),
        "version": row.version,
        "createdAt": iso(row.created_at),
    }


@router.post("/submit")
def submit_report(
    body: SubmitBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not body.period.strip():
        return fail(1001, "period 必填")
    err = validate_author_account(ops, actor, body.authorId, body.accountId)
    if err:
        return err
    tenant_id = tenant_of(actor)
    template = db.get(ReportTemplate, body.templateId)
    if template is None or template.deleted or template.tenant_id != tenant_id:
        return fail(1500, "模板不存在")
    if template.status != "ENABLED":
        return fail(1501, "模板已停用")
    fields = template.fields_schema if isinstance(template.fields_schema, list) else []
    err = validate_submission_data(fields, body.dataContent, strict=not body.asDraft)
    if err:
        return err
    submitter_id = actor.id
    existing = find_dedup_row(db, tenant_id, body, submitter_id)
    if existing and existing.submit_status in ("SUBMITTED", "APPROVED"):
        if body.asDraft:
            row = existing
        else:
            return fail(1123, "同周期同作者账号填报单已存在")
    elif existing:
        row = existing
        if existing.submit_status == "REJECTED" and not body.asDraft:
            row.version = (row.version or 1) + 1
    else:
        row = ReportSubmission(
            submission_no=next_submission_no(db, tenant_id),
            submitter_user_id=submitter_id,
            tenant_id=tenant_id,
        )
        db.add(row)
    row.template_id = body.templateId
    row.template_version = template.version or 1
    row.period = body.period.strip()
    row.author_id = body.authorId
    row.account_id = body.accountId
    row.data_content = body.dataContent
    row.attachments = [item.model_dump() for item in body.attachments]
    row.is_on_time = 1
    if body.asDraft:
        row.submit_status = "DRAFT"
        row.submitted_at = None
    else:
        row.submit_status = "SUBMITTED"
        row.submitted_at = utcnow()
        template.usage_count = (template.usage_count or 0) + 1
    row.updated_at = utcnow()
    db.flush()
    return ok(submission_vo(db, ops, row))


@router.get("/submit/list")
def submit_list(
    templateId: int | None = None,
    period: str | None = None,
    submitterUserId: int | None = None,
    authorId: int | None = None,
    accountId: int | None = None,
    submitStatus: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ReportSubmission).where(
        ReportSubmission.deleted == 0,
        ReportSubmission.tenant_id == tenant_id,
    )
    if templateId:
        stmt = stmt.where(ReportSubmission.template_id == templateId)
    if period:
        stmt = stmt.where(ReportSubmission.period == period.strip())
    if submitterUserId:
        stmt = stmt.where(ReportSubmission.submitter_user_id == submitterUserId)
    if authorId:
        stmt = stmt.where(ReportSubmission.author_id == authorId)
    if accountId:
        stmt = stmt.where(ReportSubmission.account_id == accountId)
    if submitStatus:
        if submitStatus not in SUBMIT_STATUSES:
            return fail(1001, "submitStatus 无效")
        stmt = stmt.where(ReportSubmission.submit_status == submitStatus)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ReportSubmission.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([submission_vo(db, ops, row) for row in rows], total, page_no, size)


@router.get("/submit/{submission_no}")
def submit_detail(
    submission_no: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(ReportSubmission).where(
            ReportSubmission.submission_no == submission_no,
            ReportSubmission.deleted == 0,
            ReportSubmission.tenant_id == tenant_id,
        )
    )
    if row is None:
        return fail(1500, "填报单不存在")
    return ok(submission_vo(db, ops, row))


def reject_round_count(db: Session, submission_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ReportAudit)
            .where(
                ReportAudit.deleted == 0,
                ReportAudit.submission_id == submission_id,
                ReportAudit.conclusion == "REJECTED",
            )
        )
        or 0
    )


def next_audit_round(db: Session, submission_id: int) -> int:
    mx = db.scalar(
        select(func.max(ReportAudit.audit_round)).where(
            ReportAudit.deleted == 0,
            ReportAudit.submission_id == submission_id,
        )
    )
    return int(mx or 0) + 1


def waiting_hours(submitted_at: datetime | None) -> float:
    if submitted_at is None:
        return 0.0
    ref = submitted_at
    if ref.tzinfo is not None:
        ref = ref.astimezone(timezone.utc).replace(tzinfo=None)
    delta = utcnow() - ref
    return max(0.0, delta.total_seconds() / 3600.0)


def queue_item_vo(db: Session, ops: Session, row: ReportSubmission) -> dict:
    base = submission_vo(db, ops, row)
    template = db.get(ReportTemplate, row.template_id)
    hours = waiting_hours(row.submitted_at)
    base["businessLine"] = template.business_line if template else "BUSINESS"
    base["waitingHours"] = round(hours, 2)
    base["isTimeoutSla"] = hours >= AUDIT_SLA_HOURS
    return base


class AuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conclusion: str
    rejectReason: str = ""
    rejectReasonTags: list[str] = Field(default_factory=list)


@router.get("/audit/queue")
def audit_queue(
    businessLine: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if businessLine and businessLine not in BUSINESS_LINES:
        return fail(1001, "businessLine 无效")
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ReportSubmission).where(
        ReportSubmission.deleted == 0,
        ReportSubmission.tenant_id == tenant_id,
        ReportSubmission.submit_status == "SUBMITTED",
    )
    if businessLine:
        tpl_ids = list(
            db.scalars(
                select(ReportTemplate.id).where(
                    ReportTemplate.deleted == 0,
                    ReportTemplate.tenant_id == tenant_id,
                    ReportTemplate.business_line == businessLine,
                )
            ).all()
        )
        if not tpl_ids:
            return paged([], 0, page_no, size)
        stmt = stmt.where(ReportSubmission.template_id.in_(tpl_ids))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ReportSubmission.submitted_at.asc(), ReportSubmission.id.asc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([queue_item_vo(db, ops, row) for row in rows], total, page_no, size)


@router.put("/audit/{submission_id}")
def audit_submission(
    submission_id: int,
    body: AuditBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if body.conclusion not in AUDIT_CONCLUSIONS:
        return fail(1001, "conclusion 无效")
    tenant_id = tenant_of(actor)
    row = db.get(ReportSubmission, submission_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "填报单不存在")
    if row.submit_status != "SUBMITTED":
        return fail(1001, "当前状态不可审核")
    template = db.get(ReportTemplate, row.template_id)
    if template is None or template.deleted:
        return fail(1500, "模板不存在")
    if body.conclusion == "REJECTED":
        if not body.rejectReason.strip():
            return fail(1124, "退回必须填写原因")
        if reject_round_count(db, row.id) >= 3:
            return fail(1125, "已达 3 轮退回上限，转升级流")
    audit_round = next_audit_round(db, row.id)
    now = utcnow()
    db.add(
        ReportAudit(
            submission_id=row.id,
            auditor_user_id=actor.id,
            audit_round=audit_round,
            conclusion=body.conclusion,
            reject_reason=body.rejectReason.strip(),
            reject_reason_tags=body.rejectReasonTags or [],
            audited_at=now,
            tenant_id=tenant_id,
        )
    )
    if body.conclusion == "APPROVED":
        row.submit_status = "APPROVED"
        next_action = "COMPLETED"
    else:
        row.submit_status = "REJECTED"
        next_action = "BACK_TO_SUBMITTER"
    row.updated_at = now
    db.flush()
    return ok(
        {
            "submissionId": row.id,
            "auditRound": audit_round,
            "newStatus": row.submit_status,
            "nextAction": next_action,
        }
    )


def rate_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator * 100.0 / denominator, 2)


def submission_stat_filters(
    tenant_id: int,
    stat_period: str | None,
    template_id: int | None,
):
    stmt = select(ReportSubmission).where(
        ReportSubmission.deleted == 0,
        ReportSubmission.tenant_id == tenant_id,
        ReportSubmission.submit_status != "DRAFT",
    )
    if stat_period:
        stmt = stmt.where(ReportSubmission.period == stat_period.strip())
    if template_id:
        stmt = stmt.where(ReportSubmission.template_id == template_id)
    return stmt


def aggregate_submission_stats(db: Session, rows: list[ReportSubmission]) -> dict:
    should = len(rows)
    approved = sum(1 for r in rows if r.submit_status == "APPROVED")
    submitted = sum(
        1 for r in rows if r.submit_status in ("SUBMITTED", "APPROVED", "REJECTED")
    )
    on_time = sum(1 for r in rows if r.is_on_time and r.submit_status != "DRAFT")
    return {
        "shouldCount": should,
        "submittedCount": submitted,
        "onTimeCount": on_time,
        "approvedCount": approved,
        "completeRate": rate_pct(approved, should),
    }


@router.get("/stat/complete-rate")
def stat_complete_rate(
    statPeriod: str | None = None,
    templateId: int | None = None,
    deptId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    _ = deptId
    tenant_id = tenant_of(actor)
    rows = list(db.scalars(submission_stat_filters(tenant_id, statPeriod, templateId)).all())
    total = aggregate_submission_stats(db, rows)

    by_tpl: dict[int, list[ReportSubmission]] = {}
    for row in rows:
        by_tpl.setdefault(row.template_id, []).append(row)
    by_template = []
    for tpl_id, group in by_tpl.items():
        template = db.get(ReportTemplate, tpl_id)
        stats = aggregate_submission_stats(db, group)
        by_template.append(
            {
                "templateId": tpl_id,
                "templateName": template.template_name if template else "",
                **stats,
            }
        )
    by_template.sort(key=lambda item: item["completeRate"], reverse=True)

    by_dept: dict[str, list[ReportSubmission]] = {}
    for row in rows:
        template = db.get(ReportTemplate, row.template_id)
        dept_key = (template.dept_name if template else "") or "未分配"
        by_dept.setdefault(dept_key, []).append(row)
    by_dept_list = []
    for dept_name, group in by_dept.items():
        stats = aggregate_submission_stats(db, group)
        by_dept_list.append(
            {
                "deptId": 0,
                "deptName": dept_name,
                "shouldCount": stats["shouldCount"],
                "approvedCount": stats["approvedCount"],
                "completeRate": stats["completeRate"],
            }
        )
    by_dept_list.sort(key=lambda item: item["completeRate"], reverse=True)

    return ok(
        {
            "totalCompleteRate": total["completeRate"],
            "byTemplate": by_template,
            "byDept": by_dept_list,
        }
    )


@router.get("/stat/trend")
def stat_trend(
    dateRange: str | None = None,
    templateId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(ReportSubmission).where(
        ReportSubmission.deleted == 0,
        ReportSubmission.tenant_id == tenant_id,
        ReportSubmission.submit_status != "DRAFT",
    )
    if templateId:
        stmt = stmt.where(ReportSubmission.template_id == templateId)
    rows = list(db.scalars(stmt.order_by(ReportSubmission.period.asc())).all())
    if dateRange:
        parts = [p.strip() for p in dateRange.split(",") if p.strip()]
        if len(parts) == 2:
            rows = [r for r in rows if parts[0] <= r.period <= parts[1]]

    by_period: dict[str, list[ReportSubmission]] = {}
    for row in rows:
        by_period.setdefault(row.period, []).append(row)

    submission_ids = [r.id for r in rows]
    reject_counts: dict[int, int] = {}
    if submission_ids:
        audit_rows = list(
            db.scalars(
                select(ReportAudit).where(
                    ReportAudit.deleted == 0,
                    ReportAudit.submission_id.in_(submission_ids),
                    ReportAudit.conclusion == "REJECTED",
                )
            ).all()
        )
        for audit in audit_rows:
            reject_counts[audit.submission_id] = reject_counts.get(audit.submission_id, 0) + 1

    trend = []
    for period in sorted(by_period.keys()):
        group = by_period[period]
        stats = aggregate_submission_stats(db, group)
        reject_hits = sum(1 for r in group if reject_counts.get(r.id, 0) > 0)
        trend.append(
            {
                "statPeriod": period,
                "shouldCount": stats["shouldCount"],
                "submittedCount": stats["submittedCount"],
                "approvedCount": stats["approvedCount"],
                "completeRate": stats["completeRate"],
                "rejectRate": rate_pct(reject_hits, stats["shouldCount"]),
            }
        )
    return ok(trend)
