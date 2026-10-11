"""数据上报 REPORT-001 模板 · REPORT-002 填报 · REPORT-003 审核 · REPORT-004 完成率（W7-4~8）。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import ReportAudit, ReportSubmission, ReportTemplate, Todo, User
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


@router.get("/submit/context")
def submit_context(
    templateId: int | None = None,
    authorId: int | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    """填报下拉。先选启用中的模板，再给出作者，账号只含该作者 IP 组已绑定账号。"""
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
