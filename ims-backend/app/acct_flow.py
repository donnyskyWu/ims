"""ACCT-001 账号领用 / 归还、ACCT-002 流转、ACCT-004 冲话费登记（CORP 账号页）。"""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.acct_seed import FINANCE_ROLE_KEY
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.ops_db import ops_session
from app.models import AccountApply, AccountRecharge, AccountTimelineEvent, AccountTransfer, Role, User, UserRole
from app.ops_models import PlatformAccount

VOUCHER_LIMIT = Decimal("5000")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TRANSFER_REASONS = frozenset({"TRANSFER_POSITION", "PRE_RESIGN", "VIOLATION", "BUSINESS_ADJUST"})

router = APIRouter()


def _load_account(ops: Session, account_id: int) -> PlatformAccount | None:
    row = ops.get(PlatformAccount, account_id)
    if row is None or row.deleted:
        return None
    return row


def _next_doc_no(db: Session, model, column, prefix_letter: str) -> str:
    day = utcnow().strftime("%Y%m%d")
    prefix = f"{prefix_letter}{day}"
    count = db.scalar(select(func.count()).select_from(model).where(column.like(f"{prefix}%"))) or 0
    return f"{prefix}{int(count) + 1:04d}"


def _next_apply_no(db: Session) -> str:
    return _next_doc_no(db, AccountApply, AccountApply.apply_no, "AP")


def _next_transfer_no(db: Session) -> str:
    return _next_doc_no(db, AccountTransfer, AccountTransfer.transfer_no, "TR")


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


def _is_admin(db: Session, actor: User) -> bool:
    if actor.username == "admin":
        return True
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == actor.id)).all())
    if not role_ids:
        return False
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.deleted == 0, Role.status == "ENABLED")).all()
    return any(role.role_key == "sys:admin" for role in roles)


def _display_name(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    if user is None:
        return ""
    return user.nickname or user.username


def transfer_vo(row: AccountTransfer, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "transferNo": row.transfer_no,
        "accountId": row.account_id,
        "accountNo": row.account_no,
        "fromUserId": row.from_user_id,
        "toUserId": row.to_user_id or None,
        "fromUserName": names.get(row.from_user_id, ""),
        "toUserName": names.get(row.to_user_id, "") if row.to_user_id else None,
        "transferType": row.transfer_type,
        "reasonType": row.reason_type,
        "remark": row.remark,
        "status": row.status,
        "createdAt": row.created_at.strftime("%Y-%m-%dT%H:%M:%S") if row.created_at else "",
        "effectiveAt": row.effective_at.strftime("%Y-%m-%dT%H:%M:%S") if row.effective_at else None,
    }


class TransferCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account_id: int = Field(alias="accountId")
    transfer_type: str = Field(default="TRANSFER", alias="transferType")
    to_user_id: int | None = Field(default=None, alias="toUserId")
    reason_type: str = Field(alias="reasonType")
    remark: str | None = None


class TransferConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    accept: bool = True
    remark: str | None = None


class TransferRevokeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: str


@router.post("/account/transfer")
def create_transfer(
    body: TransferCreateBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    if body.transfer_type != "TRANSFER":
        return fail(1001, "流转类型不合法")
    if body.reason_type not in TRANSFER_REASONS:
        return fail(1001, "原因分类不合法")
    remark = (body.remark or "").strip()
    if not remark or len(remark) > 512:
        return fail(1001, "交接说明必填")
    if body.to_user_id is None:
        return fail(1001, "新责任人必填")
    target = db.get(User, body.to_user_id)
    if target is None or target.deleted or target.status != "ENABLED":
        return fail(1504, "资源不可用")
    ops = ops_session()
    try:
        account = _load_account(ops, body.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "FROZEN":
            return fail(1022, "账号处于冻结态")
        if account.status != "IN_USE":
            return fail(1023, "账号不在用，无法流转")
        if actor.id != account.holder_user_id and not _is_admin(db, actor):
            return fail(1008, "仅当前责任人可发起流转")
        if target.id == account.holder_user_id:
            return fail(1001, "不可流转给当前责任人")
        pending = db.scalar(
            select(AccountTransfer.id).where(
                AccountTransfer.account_id == account.id,
                AccountTransfer.status == "PENDING_CONFIRM",
            )
        )
        if pending is not None:
            return fail(1023, "流转单状态非法")
        row = AccountTransfer(
            transfer_no=_next_transfer_no(db),
            account_id=account.id,
            account_no=account.account_no or str(account.id),
            from_user_id=account.holder_user_id or actor.id,
            to_user_id=target.id,
            transfer_type="TRANSFER",
            reason_type=body.reason_type,
            remark=remark,
            status="PENDING_CONFIRM",
            tenant_id=tenant_of(actor),
        )
        db.add(row)
        db.flush()
        names = {
            row.from_user_id: _display_name(db, row.from_user_id),
            row.to_user_id: target.nickname or target.username,
        }
        return ok(transfer_vo(row, names))
    finally:
        ops.close()


@router.get("/account/transfer/list")
def list_transfer(
    pageNo: int = 1,
    pageSize: int = 20,
    accountId: int | None = None,
    status: str | None = None,
    transferType: str | None = None,
    fromUserId: int | None = None,
    toUserId: int | None = None,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AccountTransfer).order_by(AccountTransfer.id.desc())
    if accountId is not None:
        stmt = stmt.where(AccountTransfer.account_id == accountId)
    if status:
        stmt = stmt.where(AccountTransfer.status == status)
    if transferType:
        stmt = stmt.where(AccountTransfer.transfer_type == transferType)
    if fromUserId is not None:
        stmt = stmt.where(AccountTransfer.from_user_id == fromUserId)
    if toUserId is not None:
        stmt = stmt.where(AccountTransfer.to_user_id == toUserId)
    rows = list(db.scalars(stmt).all())
    user_ids = {r.from_user_id for r in rows} | {r.to_user_id for r in rows if r.to_user_id}
    names = {
        u.id: u.nickname or u.username
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    } if user_ids else {}
    start = (page_no - 1) * size
    page = rows[start : start + size]
    return paged([transfer_vo(r, names) for r in page], len(rows), page_no, size)


@router.put("/account/transfer/{transfer_id}/confirm")
def confirm_transfer(
    transfer_id: int,
    body: TransferConfirmBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    row = db.get(AccountTransfer, transfer_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.status != "PENDING_CONFIRM":
        return fail(1023, "流转单状态非法")
    if actor.id != row.to_user_id:
        return fail(1008, "仅新责任人可确认")
    if not body.accept:
        row.status = "REVOKED"
        row.updated_at = utcnow()
        return ok(None)
    ops = ops_session()
    try:
        account = _load_account(ops, row.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "FROZEN":
            return fail(1022, "账号处于冻结态")
        if account.status != "IN_USE" or account.holder_user_id != row.from_user_id:
            return fail(1023, "账号状态已变化，请刷新")
        from_name = _display_name(db, row.from_user_id)
        to_name = _display_name(db, row.to_user_id)
        account.holder_user_id = row.to_user_id
        account.updated_at = utcnow()
        row.status = "EFFECTIVE"
        row.effective_at = utcnow()
        row.updated_at = utcnow()
        if body.remark and body.remark.strip():
            extra = body.remark.strip()
            merged = f"{row.remark}；{extra}" if row.remark else extra
            row.remark = merged[:512]
        ops.commit()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="TRANSFER",
            ref_no=row.transfer_no,
            ref_id=row.id,
            operator=actor,
            summary=f"流转生效 · 责任人 {from_name} → {to_name}",
            tenant_id=tenant_of(actor),
        )
        return ok(None)
    finally:
        ops.close()


@router.put("/account/transfer/{transfer_id}/revoke")
def revoke_transfer(
    transfer_id: int,
    body: TransferRevokeBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    remark = (body.remark or "").strip()
    if not remark or len(remark) > 256:
        return fail(1001, "撤销原因必填")
    row = db.get(AccountTransfer, transfer_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.status != "PENDING_CONFIRM":
        return fail(1023, "流转单状态非法")
    if actor.id != row.from_user_id and not _is_admin(db, actor):
        return fail(1008, "仅发起人或管理员可撤销")
    row.status = "REVOKED"
    row.updated_at = utcnow()
    note = f"{row.remark}；撤销：{remark}" if row.remark else f"撤销：{remark}"
    row.remark = note[:512]
    return ok(None)


def _money(value: float) -> Decimal | None:
    try:
        quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    if quantized <= 0 or quantized > Decimal("9999999999.99"):
        return None
    return quantized


def _money_out(value: float) -> float:
    quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _is_finance(db: Session, actor: User) -> bool:
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == actor.id)).all())
    if not role_ids:
        return False
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.deleted == 0, Role.status == "ENABLED")).all()
    for role in roles:
        if role.role_key == FINANCE_ROLE_KEY or "财务" in (role.role_name or ""):
            return True
    return False


def recharge_vo(row: AccountRecharge, operator_name: str, *, reveal_voucher: bool) -> dict:
    attached = bool((row.voucher_url or "").strip())
    return {
        "id": row.id,
        "accountId": row.account_id,
        "accountNo": row.account_no,
        "amount": _money_out(row.amount),
        "channel": row.channel,
        "voucherUrl": row.voucher_url if reveal_voucher and attached else None,
        "voucherAttached": attached,
        "rechargeDate": row.recharge_date,
        "verifyStatus": row.verify_status,
        "verifyDiff": _money_out(row.verify_diff) if row.verify_diff is not None else None,
        "operatorUserId": row.operator_user_id,
        "operatorName": operator_name,
        "remark": row.remark or "",
        "createdAt": row.created_at.strftime("%Y-%m-%dT%H:%M:%S") if row.created_at else "",
    }


class RechargeCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account_id: int = Field(alias="accountId")
    amount: float
    channel: str
    voucher_url: str | None = Field(default=None, alias="voucherUrl")
    recharge_date: str = Field(alias="rechargeDate")
    remark: str | None = None


@router.post("/account/recharge")
def create_recharge(
    body: RechargeCreateBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
    clientToken: str | None = Header(default=None),
):
    token = (clientToken or "").strip()
    if not token or len(token) > 64:
        return fail(1001, "clientToken 必填")
    reveal = _is_finance(db, actor)
    existing = db.scalar(select(AccountRecharge).where(AccountRecharge.client_token == token))
    if existing is not None:
        name = actor.nickname or actor.username
        if existing.operator_user_id != actor.id:
            owner = db.get(User, existing.operator_user_id)
            name = (owner.nickname or owner.username) if owner is not None else ""
        return ok(recharge_vo(existing, name, reveal_voucher=reveal))

    amount = _money(body.amount)
    if amount is None:
        return fail(1001, "金额格式不合法")
    channel = (body.channel or "").strip()
    if not channel or len(channel) > 64:
        return fail(1001, "充值渠道必填")
    voucher = (body.voucher_url or "").strip()
    if len(voucher) > 512:
        return fail(1001, "凭证地址过长")
    remark = (body.remark or "").strip()
    if len(remark) > 256:
        return fail(1001, "备注过长")
    if not DATE_RE.match(body.recharge_date or ""):
        return fail(1001, "充值日期格式不合法")
    try:
        recharge_day = date.fromisoformat(body.recharge_date)
    except ValueError:
        return fail(1001, "充值日期格式不合法")
    if recharge_day > utcnow().date():
        return fail(1001, "充值日期不得晚于今日")
    if amount > VOUCHER_LIMIT and not voucher:
        return fail(1025, "冲话费凭证必填（金额 > 5000 元）")

    ops = ops_session()
    try:
        account = _load_account(ops, body.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "CANCELLED":
            return fail(1001, "已注销账号不可冲话费")
        row = AccountRecharge(
            account_id=account.id,
            account_no=account.account_no or str(account.id),
            amount=float(amount),
            channel=channel,
            voucher_url=voucher,
            recharge_date=body.recharge_date,
            verify_status="UNVERIFIED",
            operator_user_id=actor.id,
            client_token=token,
            remark=remark,
            tenant_id=tenant_of(actor),
        )
        db.add(row)
        db.flush()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="RECHARGE",
            ref_no=f"RC{row.id}",
            ref_id=row.id,
            operator=actor,
            summary=f"冲话费登记 · ¥{amount} · {channel}",
            tenant_id=tenant_of(actor),
        )
        name = actor.nickname or actor.username
        return ok(recharge_vo(row, name, reveal_voucher=reveal))
    finally:
        ops.close()


@router.get("/account/recharge/list")
def list_recharge(
    pageNo: int = 1,
    pageSize: int = 20,
    accountId: int | None = None,
    verifyStatus: str | None = None,
    month: str | None = None,
    channel: str | None = None,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AccountRecharge).order_by(AccountRecharge.id.desc())
    if accountId is not None:
        stmt = stmt.where(AccountRecharge.account_id == accountId)
    if verifyStatus:
        stmt = stmt.where(AccountRecharge.verify_status == verifyStatus)
    if month:
        stmt = stmt.where(AccountRecharge.recharge_date.like(f"{month}%"))
    if channel:
        stmt = stmt.where(AccountRecharge.channel == channel)
    rows = list(db.scalars(stmt).all())
    reveal = _is_finance(db, actor)
    operator_ids = {r.operator_user_id for r in rows}
    names: dict[int, str] = {}
    if operator_ids:
        names = {
            u.id: u.nickname or u.username
            for u in db.scalars(select(User).where(User.id.in_(operator_ids))).all()
        }
    start = (page_no - 1) * size
    page = rows[start : start + size]
    return paged(
        [recharge_vo(r, names.get(r.operator_user_id, ""), reveal_voucher=reveal) for r in page],
        len(rows),
        page_no,
        size,
    )
