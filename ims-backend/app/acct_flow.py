"""ACCT-001 账号领用 / 归还（CORP 详情入口 · 契约 /account/apply）。"""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.ops_db import ops_session
from app.models import AccountApply, AccountTimelineEvent, User
from app.ops_models import PlatformAccount

router = APIRouter()


def _load_account(ops: Session, account_id: int) -> PlatformAccount | None:
    row = ops.get(PlatformAccount, account_id)
    if row is None or row.deleted:
        return None
    return row


def _next_apply_no(db: Session) -> str:
    day = utcnow().strftime("%Y%m%d")
    prefix = f"AP{day}"
    count = db.scalar(select(func.count()).select_from(AccountApply).where(AccountApply.apply_no.like(f"{prefix}%"))) or 0
    return f"{prefix}{int(count) + 1:04d}"


def _append_timeline(
    db: Session,
    *,
    account_id: int,
    event_type: str,
    ref_no: str,
    ref_id: int,
    operator: User,
    summary: str,
    tenant_id: int,
) -> None:
    db.add(
        AccountTimelineEvent(
            account_id=account_id,
            event_type=event_type,
            ref_no=ref_no,
            ref_id=ref_id,
            operator_user_id=operator.id,
            snapshot_summary=summary,
            tenant_id=tenant_id,
            event_time=utcnow(),
        )
    )


def apply_vo(row: AccountApply, applicant_name: str) -> dict:
    handover = {}
    if row.handover_json:
        try:
            handover = json.loads(row.handover_json)
        except json.JSONDecodeError:
            handover = {}
    return {
        "id": row.id,
        "applyNo": row.apply_no,
        "accountId": row.account_id,
        "accountNo": row.account_no,
        "platform": row.platform,
        "applicantUserId": row.applicant_user_id,
        "applicantName": applicant_name,
        "purpose": row.purpose,
        "planStart": row.plan_start,
        "planEnd": row.plan_end,
        "applyStatus": row.apply_status,
        "handoverDetail": handover or None,
        "createdAt": row.created_at.strftime("%Y-%m-%dT%H:%M:%S") if row.created_at else "",
    }


class ApplyCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account_id: int = Field(alias="accountId")
    purpose: str
    plan_start: str = Field(alias="planStart")
    plan_end: str = Field(alias="planEnd")


class ApproveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str
    comment: str | None = None


class ConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    password_reset: bool = Field(alias="passwordReset")
    mobile_rebound: bool = Field(default=False, alias="mobileRebound")
    remark: str | None = None


class ReturnBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account_id: int = Field(alias="accountId")
    remark: str | None = None


@router.post("/account/apply")
def create_apply(body: ApplyCreateBody, actor: User = Depends(current_user), db: Session = Depends(db_session)):
    if not body.purpose.strip():
        return fail(1001, "用途说明必填")
    ops = ops_session()
    try:
        account = _load_account(ops, body.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "FROZEN":
            return fail(1022, "账号处于冻结态")
        if account.status not in ("IN_POOL",):
            return fail(1021, "账号已被领用")
        pending = db.scalar(
            select(AccountApply.id).where(
                AccountApply.account_id == body.account_id,
                AccountApply.apply_status.in_(("PENDING_APPROVAL", "PENDING_HANDOVER")),
            )
        )
        if pending is not None:
            return fail(1023, "领用单状态非法")
        row = AccountApply(
            apply_no=_next_apply_no(db),
            account_id=account.id,
            account_no=account.account_no or str(account.id),
            platform=account.platform_type,
            applicant_user_id=actor.id,
            purpose=body.purpose.strip(),
            plan_start=body.plan_start,
            plan_end=body.plan_end,
            apply_status="PENDING_APPROVAL",
            tenant_id=tenant_of(actor),
        )
        db.add(row)
        db.flush()
        name = actor.nickname or actor.username
        return ok(apply_vo(row, name))
    finally:
        ops.close()


@router.put("/account/apply/{apply_id}/approve")
def approve_apply(
    apply_id: int,
    body: ApproveBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    row = db.get(AccountApply, apply_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.apply_status != "PENDING_APPROVAL":
        return fail(1023, "领用单状态非法")
    if body.action == "REJECT":
        row.apply_status = "REJECTED"
        row.updated_at = utcnow()
        return ok(None)
    if body.action != "APPROVE":
        return fail(1001, "动作不合法")
    row.apply_status = "PENDING_HANDOVER"
    row.updated_at = utcnow()
    return ok(None)


@router.put("/account/apply/{apply_id}/confirm")
def confirm_apply(
    apply_id: int,
    body: ConfirmBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    if not body.password_reset:
        return fail(1001, "须确认密码已重置")
    row = db.get(AccountApply, apply_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.apply_status != "PENDING_HANDOVER":
        return fail(1023, "领用单状态非法")
    ops = ops_session()
    try:
        account = _load_account(ops, row.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status != "IN_POOL":
            return fail(1021, "账号已被领用")
        handover = {
            "passwordReset": body.password_reset,
            "mobileRebound": body.mobile_rebound,
            "remark": body.remark or "",
        }
        row.handover_json = json.dumps(handover, ensure_ascii=False)
        row.apply_status = "APPROVED"
        row.updated_at = utcnow()
        account.status = "IN_USE"
        account.holder_user_id = row.applicant_user_id
        account.updated_at = utcnow()
        ops.commit()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="APPLY",
            ref_no=row.apply_no,
            ref_id=row.id,
            operator=actor,
            summary=f"领用生效 · 责任人 userId={row.applicant_user_id}",
            tenant_id=tenant_of(actor),
        )
        return ok(None)
    finally:
        ops.close()


@router.get("/account/apply/list")
def list_apply(
    pageNo: int = 1,
    pageSize: int = 20,
    accountId: int | None = None,
    applyStatus: str | None = None,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AccountApply).order_by(AccountApply.id.desc())
    if accountId is not None:
        stmt = stmt.where(AccountApply.account_id == accountId)
    if applyStatus:
        stmt = stmt.where(AccountApply.apply_status == applyStatus)
    rows = list(db.scalars(stmt).all())
    names = {
        u.id: u.nickname or u.username
        for u in db.scalars(select(User).where(User.id.in_({r.applicant_user_id for r in rows}))).all()
    }
    start = (page_no - 1) * size
    page = rows[start : start + size]
    return paged([apply_vo(r, names.get(r.applicant_user_id, "")) for r in page], len(rows), page_no, size)


@router.get("/account/timeline/{account_id}")
def timeline(account_id: int, actor: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.scalars(
        select(AccountTimelineEvent)
        .where(AccountTimelineEvent.account_id == account_id)
        .order_by(AccountTimelineEvent.event_time.desc())
    ).all()
    return ok(
        {
            "list": [
                {
                    "id": r.id,
                    "accountId": r.account_id,
                    "eventType": r.event_type,
                    "refNo": r.ref_no,
                    "refId": r.ref_id,
                    "operatorUserId": r.operator_user_id,
                    "snapshotSummary": r.snapshot_summary,
                    "remark": r.remark,
                    "eventTime": r.event_time.strftime("%Y-%m-%dT%H:%M:%S") if r.event_time else "",
                }
                for r in rows
            ],
            "total": len(rows),
        }
    )


@router.post("/account/return/submit")
def return_account(body: ReturnBody, actor: User = Depends(current_user), db: Session = Depends(db_session)):
    ops = ops_session()
    try:
        account = _load_account(ops, body.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status != "IN_USE":
            return fail(1023, "领用单状态非法")
        apply_row = db.scalar(
            select(AccountApply)
            .where(
                AccountApply.account_id == body.account_id,
                AccountApply.apply_status == "APPROVED",
            )
            .order_by(AccountApply.id.desc())
        )
        account.status = "RETURNED"
        account.updated_at = utcnow()
        if apply_row is not None:
            apply_row.apply_status = "RETURNED"
            apply_row.updated_at = utcnow()
            ref_no = apply_row.apply_no
            ref_id = apply_row.id
        else:
            ref_no = "RT-MANUAL"
            ref_id = 0
        ops.commit()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="RETURN",
            ref_no=ref_no,
            ref_id=ref_id,
            operator=actor,
            summary="账号归还 · 状态 RETURNED",
            tenant_id=tenant_of(actor),
        )
        return ok({"accountId": account.id, "status": account.status})
    finally:
        ops.close()
