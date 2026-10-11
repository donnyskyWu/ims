"""数据上报 REPORT-001 模板 · REPORT-002 填报 · REPORT-003 审核 · REPORT-004 完成率（W7-4~8）。"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import ReportAudit, ReportSubmission, ReportTemplate, Role, Todo, User, UserDept, UserRole
from app.ops_models import AuthorUser, IpGroupAnchorRel, PlatformAccount
from app.report_expr import ExprError, check_expression, evaluate_expression

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
    validateExpr: str | None = None
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


def is_rule_field(item) -> bool:
    if isinstance(item, dict):
        return item.get("fieldType") == "CROSS_RULE"
    return getattr(item, "fieldType", "") == "CROSS_RULE"


def business_fields(fields: list) -> list:
    return [item for item in fields if not is_rule_field(item)]


def field_key_of(item) -> str:
    if isinstance(item, dict):
        return str(item.get("fieldKey") or "")
    return str(getattr(item, "fieldKey", "") or "")


def schema_field_keys(fields: list) -> set[str]:
    return {field_key_of(item) for item in business_fields(fields) if field_key_of(item)}


def cross_check_of(item) -> dict | None:
    raw = item.get("crossCheck") if isinstance(item, dict) else getattr(item, "crossCheck", None)
    return raw if isinstance(raw, dict) else None


def validate_expr_of(item) -> str:
    raw = item.get("validateExpr") if isinstance(item, dict) else getattr(item, "validateExpr", None)
    return str(raw or "").strip()


def guard_expression(expr: str, allowed: set[str], bind_name: str | None = None):
    try:
        check_expression(expr, allowed, bind_name=bind_name)
    except ExprError as exc:
        return fail(exc.code, exc.msg)
    return None


def validate_fields_schema(fields: list[FieldSchemaItem]):
    keys = schema_field_keys(fields)
    seen: set[str] = set()
    for item in business_fields(fields):
        key = field_key_of(item)
        if not key:
            return fail(1001, "字段键必填")
        if key in seen:
            return fail(1001, f"字段键重复：{key}")
        seen.add(key)
        if not (item.fieldLabel or "").strip():
            return fail(1001, "字段名称必填")
    for item in fields:
        expr = validate_expr_of(item)
        if expr:
            err = guard_expression(expr, keys, bind_name=field_key_of(item) or None)
            if err:
                return err
        cc = cross_check_of(item)
        if not cc:
            continue
        target = cc.get("targetFieldKey")
        if target and target not in keys:
            return fail(1121, "勾稽规则引用了不存在的字段")
        expression = str(cc.get("expression") or "").strip()
        if expression:
            err = guard_expression(expression, keys)
            if err:
                return err
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
        "fieldCount": len(business_fields(fields)),
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


def sync_fill_todos(db: Session, template: ReportTemplate) -> None:
    """被指定的填报人出现待办；从名单移除的人不再保留待处理待办。"""
    user_ids: set[int] = set()
    assignees = template.assignees if isinstance(template.assignees, list) else []
    for item in assignees:
        if not isinstance(item, dict) or str(item.get("assignType") or "USER").upper() != "USER":
            continue
        for raw in item.get("targetIds") or []:
            try:
                uid = int(raw)
            except (TypeError, ValueError):
                continue
            if uid > 0:
                user_ids.add(uid)
    existing = list(
        db.scalars(
            select(Todo).where(
                Todo.ref_type == "report_template",
                Todo.ref_id == template.id,
                Todo.task_type == "report_fill",
                Todo.status == "PENDING",
            )
        ).all()
    )
    have = {row.assignee_user_id for row in existing}
    title = f"填报待办 · {template.template_name}"
    for uid in user_ids - have:
        user = db.get(User, uid)
        if user is None or user.deleted:
            continue
        db.add(
            Todo(
                assignee_user_id=uid,
                task_type="report_fill",
                ref_type="report_template",
                ref_id=template.id,
                title=title,
                content="请按上报模板完成填报",
                status="PENDING",
                tenant_id=template.tenant_id or 0,
            )
        )
    for row in existing:
        if row.assignee_user_id not in user_ids:
            row.status = "DONE"


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
    err = validate_filler_assignees(db, body.assignees, tenant_id)
    if err:
        return err
    row = ReportTemplate(
        template_no=next_template_no(db, tenant_id),
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    apply_body(row, body)
    db.add(row)
    db.flush()
    sync_fill_todos(db, row)
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
    err = validate_filler_assignees(db, body.assignees, tenant_of(actor))
    if err:
        return err
    row = db.get(ReportTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1500, "模板不存在")
    apply_body(row, body)
    row.version = (row.version or 1) + 1
    sync_fill_todos(db, row)
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
    return ok({"id": row.id, "status": row.status, "templateName": row.template_name})


class PreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    version: int | None = None
    sampleData: dict = Field(default_factory=dict)


@router.post("/template/{template_id}/preview")
def preview_template(
    template_id: int,
    body: PreviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """校验环节：重新检查已保存的表达式，并用样例数据跑字段/勾稽规则。"""
    row = db.get(ReportTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1500, "模板不存在")
    fields = row.fields_schema if isinstance(row.fields_schema, list) else []
    parsed: list[FieldSchemaItem] = []
    for item in fields:
        if isinstance(item, dict) and item.get("fieldKey"):
            parsed.append(FieldSchemaItem.model_validate(item))
    err = validate_fields_schema(parsed)
    if err:
        return err
    rendered = business_fields(fields)
    checked = validate_submission_data(fields, body.sampleData or {}, strict=bool(body.sampleData))
    if checked is not None:
        payload = json.loads(checked.body)
        if payload.get("code") == 1192:
            return checked
        errors = (payload.get("data") or {}).get("errors") or [
            {"fieldKey": "", "errorMsg": payload.get("msg") or "勾稽校验失败"}
        ]
        return ok(
            {
                "renderedFields": rendered,
                "validationResult": {"passed": False, "errors": errors},
            }
        )
    return ok({"renderedFields": rendered, "validationResult": {"passed": True, "errors": []}})


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


def _num(value):
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _cmp(left, right, op: str) -> bool:
    if op == "EQ":
        return left == right
    left_n, right_n = _num(left), _num(right)
    if left_n is None or right_n is None:
        return False
    if op == "LTE":
        return left_n <= right_n
    if op == "GTE":
        return left_n >= right_n
    return left == right


def validate_submission_data(fields: list, data: dict, strict: bool):
    if not strict:
        return None
    keys = schema_field_keys(fields)
    errors: list[dict] = []
    for item in business_fields(fields):
        if not isinstance(item, dict):
            continue
        key = item.get("fieldKey")
        if not key:
            continue
        value = data.get(key)
        if item.get("required") and (value is None or value == ""):
            errors.append({"fieldKey": key, "errorMsg": f"字段 {key} 必填"})
            continue
        if value is None or value == "":
            continue
        rng = item.get("range") if isinstance(item.get("range"), dict) else {}
        ftype = str(item.get("fieldType") or "TEXT")
        if ftype in {"NUMBER", "INTEGER", "MONEY"}:
            num = _num(value)
            if num is None:
                errors.append({"fieldKey": key, "errorMsg": "须为数值"})
            else:
                if ftype == "INTEGER" and num != int(num):
                    errors.append({"fieldKey": key, "errorMsg": "须为整数"})
                if rng.get("min") is not None and num < float(rng["min"]):
                    errors.append({"fieldKey": key, "errorMsg": f"须 ≥ {rng['min']}"})
                if rng.get("max") is not None and num > float(rng["max"]):
                    errors.append({"fieldKey": key, "errorMsg": f"须 ≤ {rng['max']}"})
        if ftype == "TEXT" and rng.get("maxLength") is not None and len(str(value)) > int(rng["maxLength"]):
            errors.append({"fieldKey": key, "errorMsg": f"不超过 {rng['maxLength']} 字"})
        vexpr = validate_expr_of(item)
        if vexpr:
            try:
                result = evaluate_expression(vexpr, data, keys, bind_name=key)
            except ExprError as exc:
                if exc.code == 1192:
                    return fail(1192, "非法表达式，拒绝执行")
                errors.append({"fieldKey": key, "errorMsg": exc.msg})
            else:
                if result is not True:
                    errors.append({"fieldKey": key, "errorMsg": "字段校验未通过"})
    for item in fields:
        if not isinstance(item, dict):
            continue
        cc = cross_check_of(item)
        if not cc:
            continue
        expression = str(cc.get("expression") or "").strip()
        anchor = item.get("fieldKey") or ""
        if expression:
            try:
                result = evaluate_expression(expression, data, keys)
            except ExprError as exc:
                if exc.code == 1192:
                    return fail(1192, "非法表达式，拒绝执行")
                return fail(exc.code, exc.msg)
            if result is not True:
                errors.append({"fieldKey": anchor, "errorMsg": cc.get("errorMsg") or "勾稽校验失败"})
            continue
        target = cc.get("targetFieldKey")
        op = cc.get("operator", "EQ")
        if not target or target not in keys or is_rule_field(item):
            continue
        if not _cmp(data.get(item.get("fieldKey")), data.get(target), op):
            errors.append({"fieldKey": anchor, "errorMsg": cc.get("errorMsg") or "勾稽校验失败"})
    if errors:
        return fail(1122, errors[0]["errorMsg"], data={"errors": errors})
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


def data_volume(data_content: dict, fields: list) -> int:
    raw = data_content.get("_rowCount")
    if raw not in (None, ""):
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    keys = schema_field_keys(fields)
    if keys:
        return sum(1 for key in keys if data_content.get(key) not in (None, ""))
    return sum(
        1
        for key, value in data_content.items()
        if not str(key).startswith("_") and value not in (None, "")
    )


def submission_vo(db: Session, ops: Session, row: ReportSubmission) -> dict:
    template = db.get(ReportTemplate, row.template_id)
    author = ops.get(AuthorUser, row.author_id)
    account = ops.get(PlatformAccount, row.account_id)
    names = user_names(db, {row.submitter_user_id})
    attachments = row.attachments if isinstance(row.attachments, list) else []
    data_content = row.data_content if isinstance(row.data_content, dict) else {}
    fields = template.fields_schema if template and isinstance(template.fields_schema, list) else []
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
        "dataVolume": data_volume(data_content, fields),
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
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not body.period.strip():
        return fail(1001, "period 必填")
    err = require_fill_access(request, db, actor, body.templateId)
    if err:
        return err
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
    request: Request,
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
    if scope_kind(request) != "ALL":
        stmt = stmt.where(ReportSubmission.submitter_user_id == actor.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ReportSubmission.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([submission_vo(db, ops, row) for row in rows], total, page_no, size)


@router.get("/submit/context")
def submit_context(
    request: Request,
    templateId: int | None = None,
    authorId: int | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    """填报下拉。先选启用中的模板，再给出作者，账号只含该作者 IP 组已绑定账号。

    作者按租户列出，不按填报人的数据范围裁剪，否则被指派的人会看不到可用作者。
    非全量账号只能看到指派给自己的模板。
    """
    tenant_id = tenant_of(actor)
    templates = list(
        db.scalars(
            select(ReportTemplate)
            .where(
                ReportTemplate.deleted == 0,
                ReportTemplate.tenant_id == tenant_id,
                ReportTemplate.status == "ENABLED",
            )
            .order_by(ReportTemplate.id.desc())
        ).all()
    )
    if scope_kind(request) != "ALL":
        allowed = filler_template_ids(db, actor)
        templates = [row for row in templates if row.id in allowed]
    template_rows = [
        {
            "id": row.id,
            "templateNo": row.template_no,
            "templateName": row.template_name,
            "periodType": row.period_type,
            "deadlineRule": row.deadline_rule,
            "deptName": row.dept_name,
            "fieldsSchema": business_fields(row.fields_schema if isinstance(row.fields_schema, list) else []),
        }
        for row in templates
    ]
    authors: list[dict] = []
    accounts: list[dict] = []
    if templateId:
        chosen = next((row for row in templates if row.id == templateId), None)
        if chosen is None:
            denied = require_fill_access(request, db, actor, templateId)
            if denied:
                return denied
            raw = db.get(ReportTemplate, templateId)
            if raw is None or raw.deleted or raw.tenant_id != tenant_id:
                return fail(1500, "模板不存在")
            return fail(1501, "模板已停用")
        author_rows = list(
            ops.scalars(
                select(AuthorUser)
                .where(
                    AuthorUser.deleted == 0,
                    AuthorUser.tenant_id == tenant_id,
                    AuthorUser.status == "ENABLED",
                )
                .order_by(AuthorUser.author_name.asc(), AuthorUser.id.asc())
            ).all()
        )
        authors = [
            {"id": row.id, "authorName": row.author_name, "ipGroupId": row.ip_group_id or 0}
            for row in author_rows
        ]
        if authorId:
            author = next((row for row in author_rows if row.id == authorId), None)
            if author is None:
                return fail(1500, "作者不存在")
            group_id = author.ip_group_id or 0
            if group_id:
                account_rows = list(
                    ops.scalars(
                        select(PlatformAccount)
                        .where(
                            PlatformAccount.deleted == 0,
                            PlatformAccount.tenant_id == tenant_id,
                            PlatformAccount.ip_group_id == group_id,
                            PlatformAccount.status != "DISABLED",
                        )
                        .order_by(PlatformAccount.account_name.asc(), PlatformAccount.id.asc())
                    ).all()
                )
                accounts = [
                    {
                        "id": row.id,
                        "accountName": row.account_name,
                        "accountNo": row.account_no,
                        "label": row.account_name or row.account_no,
                    }
                    for row in account_rows
                ]
    return ok({"templates": template_rows, "authors": authors, "accounts": accounts})


@router.get("/submit/{submission_no}")
def submit_detail(
    submission_no: str,
    request: Request,
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
    if scope_kind(request) != "ALL" and row.submitter_user_id != actor.id:
        return fail(1008, "无数据权限")
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
    """已提交单据范围。通过率仍用这批单据，不拿它当完成率分母。"""
    stmt = select(ReportSubmission).where(
        ReportSubmission.deleted == 0,
        ReportSubmission.tenant_id == tenant_id,
    )
    if stat_period:
        stmt = stmt.where(ReportSubmission.period == stat_period.strip())
    if template_id:
        stmt = stmt.where(ReportSubmission.template_id == template_id)
    return stmt


def aggregate_submission_stats(db: Session, rows: list[ReportSubmission]) -> dict:
    """已建单据的计数。完成率分母不使用这里的 shouldCount。"""
    should = len(rows)
    approved = sum(1 for r in rows if r.submit_status == "APPROVED")
    submitted = sum(
        1 for r in rows if r.submit_status in ("SUBMITTED", "APPROVED", "REJECTED")
    )
    on_time = sum(1 for r in rows if r.is_on_time and r.submit_status != "DRAFT")
    rejected = sum(1 for r in rows if r.submit_status == "REJECTED")
    return {
        "shouldCount": should,
        "submittedCount": submitted,
        "onTimeCount": on_time,
        "approvedCount": approved,
        "rejectCount": rejected,
        "completeRate": rate_pct(approved, should),
        "passRate": rate_pct(approved, submitted),
    }


def bj_day(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BJ).strftime("%Y-%m-%d")


def field_value_ok(item: dict, value) -> bool:
    if item.get("required") and (value is None or value == ""):
        return False
    if value is None or value == "":
        return True
    rng = item.get("range") if isinstance(item.get("range"), dict) else {}
    ftype = str(item.get("fieldType") or "TEXT")
    if ftype in {"NUMBER", "INTEGER", "MONEY"}:
        num = _num(value)
        if num is None:
            return False
        if ftype == "INTEGER" and num != int(num):
            return False
        if rng.get("min") is not None and num < float(rng["min"]):
            return False
        if rng.get("max") is not None and num > float(rng["max"]):
            return False
    if ftype == "TEXT" and rng.get("maxLength") is not None and len(str(value)) > int(rng["maxLength"]):
        return False
    return True


def field_check_hit_rate(db: Session, rows: list[ReportSubmission]) -> float:
    hits = 0
    checks = 0
    for row in rows:
        template = db.get(ReportTemplate, row.template_id)
        fields = template.fields_schema if template and isinstance(template.fields_schema, list) else []
        data = row.data_content if isinstance(row.data_content, dict) else {}
        for item in business_fields(fields):
            if not isinstance(item, dict):
                continue
            if not (item.get("required") or item.get("range") or validate_expr_of(item)):
                continue
            checks += 1
            if field_value_ok(item, data.get(item.get("fieldKey"))):
                hits += 1
    return rate_pct(hits, checks)


def average_audit_hours(db: Session, rows: list[ReportSubmission]) -> float:
    submitted_at = {row.id: row.submitted_at for row in rows if row.submitted_at}
    if not submitted_at:
        return 0.0
    audits = list(
        db.scalars(
            select(ReportAudit).where(
                ReportAudit.deleted == 0,
                ReportAudit.submission_id.in_(list(submitted_at)),
            )
        ).all()
    )
    latest: dict[int, datetime] = {}
    for audit in audits:
        if audit.audited_at is None:
            continue
        prev = latest.get(audit.submission_id)
        if prev is None or audit.audited_at > prev:
            latest[audit.submission_id] = audit.audited_at
    hours: list[float] = []
    for submission_id, audited_at in latest.items():
        start = submitted_at.get(submission_id)
        if start is None:
            continue
        delta = (audited_at - start).total_seconds() / 3600.0
        if delta >= 0:
            hours.append(delta)
    if not hours:
        return 0.0
    return round(sum(hours) / len(hours), 2)


class ExpectSlot(NamedTuple):
    template_id: int
    template_name: str
    dept_name: str
    deadline_rule: str
    period: str
    user_id: int


def period_key(period_type: str, day: date) -> str:
    kind = (period_type or "DAILY").upper()
    if kind == "WEEKLY":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if kind == "MONTHLY":
        return f"{day.year:04d}-{day.month:02d}"
    return day.isoformat()


def period_index(period_type: str, day: date) -> int:
    """轮值下标。同一周、同一月内不变，每日按公历日推进。"""
    kind = (period_type or "DAILY").upper()
    if kind == "WEEKLY":
        iso = day.isocalendar()
        return iso.year * 53 + iso.week
    if kind == "MONTHLY":
        return day.year * 12 + day.month
    return day.toordinal()


def scope_days(stat_period: str | None) -> list[date]:
    """未传周期时只算北京时间当天，避免把历史每一天都摊进分母。"""
    raw = (stat_period or "").strip()
    today = datetime.now(BJ).date()
    if not raw:
        return [today]
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            return [date.fromisoformat(raw)]
        if len(raw) == 7 and raw[4] == "-" and raw[5:].isdigit():
            year = int(raw[:4])
            month = int(raw[5:7])
            if not 1 <= month <= 12:
                return [today]
            start = date(year, month, 1)
            nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
            days: list[date] = []
            cur = start
            while cur < nxt:
                days.append(cur)
                cur += timedelta(days=1)
            return days
        upper = raw.upper()
        if "-W" in upper:
            year_s, week_s = upper.split("-W", 1)
            monday = date.fromisocalendar(int(year_s), int(week_s), 1)
            return [monday + timedelta(days=offset) for offset in range(7)]
    except (TypeError, ValueError):
        return [today]
    return [today]


def days_in_range(date_range: str | None) -> list[date] | None:
    if not date_range:
        return None
    parts = [part.strip() for part in date_range.split(",") if part.strip()]
    if len(parts) != 2:
        return None
    try:
        start = date.fromisoformat(parts[0][:10])
        end = date.fromisoformat(parts[1][:10])
    except ValueError:
        return None
    if end < start:
        start, end = end, start
    if (end - start).days > 366:
        end = start + timedelta(days=366)
    days: list[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def periods_in(period_type: str, days: list[date]) -> list[tuple[str, date]]:
    found: dict[str, date] = {}
    for day in days:
        found.setdefault(period_key(period_type, day), day)
    return list(found.items())


def parse_user_ids(raw_list) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for raw in raw_list or []:
        try:
            uid = int(raw)
        except (TypeError, ValueError):
            continue
        if uid > 0 and uid not in seen:
            seen.add(uid)
            ordered.append(uid)
    return ordered


def enabled_user_ids(db: Session, ordered: list[int], tenant_id: int) -> list[int]:
    if not ordered:
        return []
    rows = db.scalars(
        select(User).where(
            User.id.in_(ordered),
            User.deleted == 0,
            User.status == "ENABLED",
            User.tenant_id == tenant_id,
        )
    ).all()
    alive = {row.id for row in rows}
    result: list[int] = []
    seen: set[int] = set()
    for uid in ordered:
        if uid in alive and uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result


def users_for_position_codes(db: Session, codes: set[str], tenant_id: int) -> list[int]:
    cleaned = {str(code).strip() for code in codes if str(code).strip()}
    if not cleaned:
        return []
    roles = db.scalars(
        select(Role).where(
            Role.deleted == 0,
            Role.status == "ENABLED",
            Role.tenant_id == tenant_id,
        )
    ).all()
    role_ids = [
        role.id
        for role in roles
        if (role.dingtalk_position or "") in cleaned or (role.role_key or "") in cleaned
    ]
    if not role_ids:
        return []
    links = db.scalars(
        select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.tenant_id == tenant_id)
    ).all()
    return enabled_user_ids(db, sorted({link.user_id for link in links}), tenant_id)


def stable_and_rotations(
    db: Session, template: ReportTemplate, tenant_id: int
) -> tuple[list[int], list[list[int]]]:
    """USER / POSITION 展开成稳定名单；DEPT_ROTATION 保留有序花名册，每期再取 1 人。"""
    assignees = template.assignees if isinstance(template.assignees, list) else []
    stable: list[int] = []
    seen: set[int] = set()
    rotations: list[list[int]] = []

    def add_stable(ids: list[int]) -> None:
        for uid in ids:
            if uid not in seen:
                seen.add(uid)
                stable.append(uid)

    for item in assignees:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("assignType") or "USER").upper()
        if kind == "POSITION":
            codes = {str(code).strip() for code in (item.get("targetCodes") or []) if str(code).strip()}
            codes.update(str(uid) for uid in parse_user_ids(item.get("targetIds")))
            add_stable(users_for_position_codes(db, codes, tenant_id))
        elif kind == "DEPT_ROTATION":
            rotation = item.get("rotationList") if isinstance(item.get("rotationList"), list) else []
            pairs: list[tuple[int, int]] = []
            for entry in rotation:
                if not isinstance(entry, dict):
                    continue
                try:
                    uid = int(entry.get("userId"))
                except (TypeError, ValueError):
                    continue
                try:
                    order = int(entry.get("order") or 0)
                except (TypeError, ValueError):
                    order = 0
                if uid > 0:
                    pairs.append((order, uid))
            pairs.sort(key=lambda pair: (pair[0], pair[1]))
            candidates = [uid for _, uid in pairs] or parse_user_ids(item.get("targetIds"))
            roster = enabled_user_ids(db, candidates, tenant_id)
            if roster:
                rotations.append(roster)
        else:
            add_stable(enabled_user_ids(db, parse_user_ids(item.get("targetIds")), tenant_id))
    return stable, rotations


def filler_template_ids(db: Session, user: User) -> set[int]:
    """被指定的填报人。岗位展开到人，轮值花名册里的人都算被指派。"""
    tenant_id = tenant_of(user)
    found: set[int] = set()
    templates = list(
        db.scalars(
            select(ReportTemplate).where(
                ReportTemplate.deleted == 0,
                ReportTemplate.tenant_id == tenant_id,
                ReportTemplate.status == "ENABLED",
            )
        ).all()
    )
    for template in templates:
        stable, rotations = stable_and_rotations(db, template, tenant_id)
        people = set(stable)
        for roster in rotations:
            people.update(roster)
        if user.id in people:
            found.add(template.id)
    return found


def scope_kind(request: Request) -> str:
    scope = getattr(request.state, "scope", None)
    return str(getattr(scope, "kind", "") or "")


FILLER_ROLE_KEYS = frozenset({"R2", "R3", "R5", "R6", "R10"})
NOT_FILLER_MSG = "该人员角色不可作为填报人"


def _enabled_roles(db: Session, user: User) -> list[Role]:
    from app.scope import enabled_roles

    return enabled_roles(db, user)


def is_filler_user(db: Session, user: User | None) -> bool:
    """契约：可指派填报人只有 R2 / R3 / R5 / R6 / R10。"""
    if user is None or user.deleted or user.status != "ENABLED":
        return False
    for role in _enabled_roles(db, user):
        marks = {
            (role.role_key or "").strip().upper(),
            (role.dingtalk_position or "").strip().upper(),
        }
        if marks & FILLER_ROLE_KEYS:
            return True
    return False


def validate_filler_assignees(db: Session, assignees: list, tenant_id: int):
    """按人、按岗位、轮值都只接受填报角色。已有的历史指派不在这里改写。"""
    people: set[int] = set()
    for item in assignees:
        raw = item.model_dump() if hasattr(item, "model_dump") else item
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("assignType") or "USER").upper()
        if kind == "POSITION":
            codes = [str(code).strip() for code in (raw.get("targetCodes") or []) if str(code).strip()]
            if any(code.upper() not in FILLER_ROLE_KEYS for code in codes):
                return fail(1001, NOT_FILLER_MSG)
            people.update(users_for_position_codes(db, set(codes), tenant_id))
        elif kind == "DEPT_ROTATION":
            rotation = raw.get("rotationList") if isinstance(raw.get("rotationList"), list) else []
            ids: list[int] = []
            for entry in rotation:
                if not isinstance(entry, dict):
                    continue
                try:
                    uid = int(entry.get("userId"))
                except (TypeError, ValueError):
                    continue
                if uid > 0:
                    ids.append(uid)
            people.update(ids or parse_user_ids(raw.get("targetIds")))
        else:
            people.update(parse_user_ids(raw.get("targetIds")))
    for uid in people:
        if not is_filler_user(db, db.get(User, uid)):
            return fail(1001, NOT_FILLER_MSG)
    return None


def require_fill_access(request: Request, db: Session, actor: User, template_id: int):
    """全量范围沿用原权限。其余账号须是被指派的填报角色，不看菜单权限码。"""
    if scope_kind(request) == "ALL":
        return None
    if template_id not in filler_template_ids(db, actor):
        return fail(1008, "无数据权限")
    if not is_filler_user(db, actor):
        return fail(1008, NOT_FILLER_MSG)
    return None


def obliged_for_period(
    stable: list[int], rotations: list[list[int]], period_type: str, day: date
) -> list[int]:
    ordered = list(stable)
    seen = set(ordered)
    for roster in rotations:
        duty = roster[period_index(period_type, day) % len(roster)]
        if duty not in seen:
            seen.add(duty)
            ordered.append(duty)
    return ordered


def user_dept_map(db: Session, user_ids: set[int]) -> dict[int, set[int]]:
    if not user_ids:
        return {}
    rows = db.scalars(select(UserDept).where(UserDept.user_id.in_(user_ids))).all()
    mapping: dict[int, set[int]] = {}
    for row in rows:
        mapping.setdefault(row.user_id, set()).add(row.dept_id)
    return mapping


def enabled_templates(db: Session, tenant_id: int, template_id: int | None) -> list[ReportTemplate]:
    stmt = select(ReportTemplate).where(
        ReportTemplate.deleted == 0,
        ReportTemplate.tenant_id == tenant_id,
        ReportTemplate.status == "ENABLED",
    )
    if template_id:
        stmt = stmt.where(ReportTemplate.id == template_id)
    return list(db.scalars(stmt).all())


def expectation_slots(
    db: Session,
    tenant_id: int,
    days: list[date],
    template_id: int | None,
    dept_id: int | None,
) -> list[ExpectSlot]:
    """应提交槽位：启用模板 × 周期 × 责任人。

    V2-A1 周期待办在本仓库不可用。sync_fill_todos 只按模板给 USER 写一条不带周期的待办，
    不能表达每日/每周/每月，也不展开岗位和部门轮值。这里按模板规则直接推算，不把待办当成分母。
    """
    plans = [
        (tpl, *stable_and_rotations(db, tpl, tenant_id))
        for tpl in enabled_templates(db, tenant_id, template_id)
    ]
    candidate_ids: set[int] = set()
    for _, stable, rotations in plans:
        candidate_ids.update(stable)
        for roster in rotations:
            candidate_ids.update(roster)
    depts = user_dept_map(db, candidate_ids) if dept_id else {}
    slots: list[ExpectSlot] = []
    for tpl, stable, rotations in plans:
        period_type = tpl.period_type or "DAILY"
        for period, day in periods_in(period_type, days):
            for uid in obliged_for_period(stable, rotations, period_type, day):
                if dept_id:
                    owned = depts.get(uid) or set()
                    if dept_id not in owned:
                        continue
                slots.append(
                    ExpectSlot(
                        template_id=tpl.id,
                        template_name=tpl.template_name or "",
                        dept_name=tpl.dept_name or "",
                        deadline_rule=(tpl.deadline_rule or "").strip(),
                        period=period,
                        user_id=uid,
                    )
                )
    return slots


def submissions_for_slots(db: Session, tenant_id: int, slots: list[ExpectSlot]) -> list[ReportSubmission]:
    if not slots:
        return []
    template_ids = {slot.template_id for slot in slots}
    periods = {slot.period for slot in slots}
    return list(
        db.scalars(
            select(ReportSubmission).where(
                ReportSubmission.deleted == 0,
                ReportSubmission.tenant_id == tenant_id,
                ReportSubmission.template_id.in_(template_ids),
                ReportSubmission.period.in_(periods),
            )
        ).all()
    )


def submission_index(rows: list[ReportSubmission]) -> dict[tuple[int, str, int], list[ReportSubmission]]:
    grouped: dict[tuple[int, str, int], list[ReportSubmission]] = {}
    for row in rows:
        key = (row.template_id, (row.period or "").strip(), row.submitter_user_id)
        grouped.setdefault(key, []).append(row)
    return grouped


def non_draft(rows: list[ReportSubmission]) -> list[ReportSubmission]:
    return [row for row in rows if row.submit_status != "DRAFT"]


def slot_approved(rows: list[ReportSubmission]) -> bool:
    return any(row.submit_status == "APPROVED" for row in rows)


def missed_status(rows: list[ReportSubmission]) -> str | None:
    if slot_approved(rows):
        return None
    filed = non_draft(rows)
    if not filed:
        return "MISSED"
    if any(not row.is_on_time for row in filed):
        return "LATE"
    return "PENDING_AUDIT"


def slot_rollup(slots: list[ExpectSlot], index: dict[tuple[int, str, int], list[ReportSubmission]]) -> dict:
    approved = sum(
        1 for slot in slots if slot_approved(index.get((slot.template_id, slot.period, slot.user_id), []))
    )
    should = len(slots)
    return {
        "shouldCount": should,
        "approvedCount": approved,
        "completeRate": rate_pct(approved, should),
    }


def filed_slot_counts(
    slots: list[ExpectSlot], index: dict[tuple[int, str, int], list[ReportSubmission]]
) -> tuple[int, int]:
    submitted = 0
    on_time = 0
    for slot in slots:
        filed = non_draft(index.get((slot.template_id, slot.period, slot.user_id), []))
        if not filed:
            continue
        submitted += 1
        if all(row.is_on_time for row in filed):
            on_time += 1
    return submitted, on_time


def missed_dept_name(db: Session, slot: ExpectSlot, cache: dict[int, str]) -> str:
    if slot.dept_name:
        return slot.dept_name
    if slot.user_id in cache:
        return cache[slot.user_id]
    link = db.scalar(select(UserDept).where(UserDept.user_id == slot.user_id))
    label = f"部门#{link.dept_id}" if link is not None else ""
    cache[slot.user_id] = label
    return label


@router.get("/stat/complete-rate")
def stat_complete_rate(
    statPeriod: str | None = None,
    templateId: int | None = None,
    deptId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    slots = expectation_slots(db, tenant_id, scope_days(statPeriod), templateId, deptId)
    index = submission_index(submissions_for_slots(db, tenant_id, slots))
    total = slot_rollup(slots, index)

    by_template = []
    grouped_tpl: dict[int, list[ExpectSlot]] = {}
    for slot in slots:
        grouped_tpl.setdefault(slot.template_id, []).append(slot)
    for tpl_id, group in grouped_tpl.items():
        stats = slot_rollup(group, index)
        submitted, on_time = filed_slot_counts(group, index)
        by_template.append(
            {
                "templateId": tpl_id,
                "templateName": group[0].template_name,
                "shouldCount": stats["shouldCount"],
                "submittedCount": submitted,
                "onTimeCount": on_time,
                "approvedCount": stats["approvedCount"],
                "completeRate": stats["completeRate"],
            }
        )
    by_template.sort(key=lambda item: (-item["completeRate"], item["templateId"]))

    by_dept_groups: dict[str, list[ExpectSlot]] = {}
    for slot in slots:
        by_dept_groups.setdefault(slot.dept_name or "未分配", []).append(slot)
    by_dept_list = []
    for dept_name, group in by_dept_groups.items():
        stats = slot_rollup(group, index)
        by_dept_list.append(
            {
                "deptId": deptId or 0,
                "deptName": dept_name,
                "shouldCount": stats["shouldCount"],
                "approvedCount": stats["approvedCount"],
                "completeRate": stats["completeRate"],
            }
        )
    by_dept_list.sort(key=lambda item: (-item["completeRate"], item["deptName"]))

    pass_rows = list(db.scalars(submission_stat_filters(tenant_id, statPeriod, templateId)).all())
    pass_stats = aggregate_submission_stats(db, pass_rows)
    today = datetime.now(BJ).strftime("%Y-%m-%d")
    today_rows = [row for row in pass_rows if row.period == today or bj_day(row.submitted_at) == today]
    filed_rows = non_draft(pass_rows)
    today_slots = expectation_slots(db, tenant_id, [datetime.now(BJ).date()], templateId, deptId)
    today_stats = slot_rollup(today_slots, submission_index(submissions_for_slots(db, tenant_id, today_slots)))

    return ok(
        {
            "totalCompleteRate": total["completeRate"],
            "shouldCount": total["shouldCount"],
            "completeApprovedCount": total["approvedCount"],
            "submittedCount": pass_stats["submittedCount"],
            "approvedCount": pass_stats["approvedCount"],
            "passRate": pass_stats["passRate"],
            "rejectCount": pass_stats["rejectCount"],
            "todayCount": sum(1 for row in today_rows if row.submit_status != "DRAFT"),
            "todayCompleteRate": today_stats["completeRate"],
            "fieldCheckHitRate": field_check_hit_rate(db, filed_rows),
            "avgAuditHours": average_audit_hours(db, filed_rows),
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
    )
    if templateId:
        stmt = stmt.where(ReportSubmission.template_id == templateId)
    rows = list(db.scalars(stmt.order_by(ReportSubmission.period.asc())).all())
    if dateRange:
        parts = [part.strip() for part in dateRange.split(",") if part.strip()]
        if len(parts) == 2:
            rows = [row for row in rows if parts[0] <= (row.period or "") <= parts[1]]

    by_period: dict[str, list[ReportSubmission]] = {}
    for row in rows:
        by_period.setdefault(row.period or "", []).append(row)

    range_days = days_in_range(dateRange)
    slots = expectation_slots(db, tenant_id, range_days, templateId, None) if range_days else []
    slot_index = submission_index(submissions_for_slots(db, tenant_id, slots))
    slots_by_period: dict[str, list[ExpectSlot]] = {}
    for slot in slots:
        slots_by_period.setdefault(slot.period, []).append(slot)

    trend = []
    for period in sorted(set(by_period) | set(slots_by_period)):
        group = by_period.get(period, [])
        submitted = sum(1 for row in group if row.submit_status != "DRAFT")
        approved = sum(1 for row in group if row.submit_status == "APPROVED")
        rejected = sum(1 for row in group if row.submit_status == "REJECTED")
        rollup = slot_rollup(slots_by_period.get(period, []), slot_index)
        trend.append(
            {
                "statPeriod": period,
                "shouldCount": rollup["shouldCount"],
                "submittedCount": submitted,
                "approvedCount": approved,
                "completeRate": rollup["completeRate"],
                "rejectRate": rate_pct(rejected, submitted),
            }
        )
    return ok(trend)


@router.get("/stat/missed")
def stat_missed(
    statPeriod: str | None = None,
    templateId: int | None = None,
    deptId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """未交清单。审核通过的槽位不算未交；同一槽位多份填报单只占一行。"""
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    slots = expectation_slots(db, tenant_id, scope_days(statPeriod), templateId, deptId)
    index = submission_index(submissions_for_slots(db, tenant_id, slots))
    names = user_names(db, {slot.user_id for slot in slots})
    dept_cache: dict[int, str] = {}
    items = []
    for slot in slots:
        status = missed_status(index.get((slot.template_id, slot.period, slot.user_id), []))
        if status is None:
            continue
        due = f"{slot.period} {slot.deadline_rule}".strip()
        items.append(
            {
                "userId": slot.user_id,
                "userName": names.get(slot.user_id, ""),
                "deptName": missed_dept_name(db, slot, dept_cache),
                "templateName": slot.template_name,
                "period": slot.period,
                "dueTime": due,
                "status": status,
            }
        )
    items.sort(key=lambda row: (row["period"], row["templateName"], row["userId"]))
    start = (page_no - 1) * size
    return paged(items[start : start + size], len(items), page_no, size)
