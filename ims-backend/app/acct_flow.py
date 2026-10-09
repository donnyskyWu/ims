"""ACCT-001 账号领用 / 归还、ACCT-002 流转 / 收回 / 解冻回池、ACCT-004 冲话费登记、账实核对与成本汇总（CORP 账号页）。"""

import csv
import io
import json
import re
import secrets
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.acct_seed import FINANCE_ROLE_KEY
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.flow import ensure_pending_task, next_instance_no, seed_flow
from app.ops_db import ops_session
from app.models import (
    AccountApply,
    AccountRecharge,
    AccountRechargeVerify,
    AccountTimelineEvent,
    AccountTransfer,
    AssetBind,
    AssetLedger,
    FlowInstance,
    FlowTask,
    FlowTemplate,
    Role,
    Todo,
    User,
    UserDept,
    UserRole,
    WorkMessage,
)
from app.ops_models import PlatformAccount

VOUCHER_LIMIT = Decimal("5000")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
DIFF_RATE_LIMIT = Decimal("2.00")
TRANSFER_REASONS = frozenset({"TRANSFER_POSITION", "PRE_RESIGN", "VIOLATION", "BUSINESS_ADJUST"})
ASSET_TRANSFER_REF = "acct_asset_transfer"
SUMMARY_GROUPS = frozenset({"ACCOUNT", "DEPT", "PLATFORM"})
PLATFORM_LABELS = {
    "DOUYIN": "抖音",
    "KUAISHOU": "快手",
    "XIAOHONGSHU": "小红书",
    "WECHAT_OFFICIAL": "公众号",
    "WECHAT_CHANNELS": "视频号",
}

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


TIMELINE_EVENT_TYPES = (
    "REGISTER",
    "APPLY",
    "TRANSFER",
    "RETURN",
    "RECHARGE",
    "FREEZE",
    "UNFREEZE",
    "CANCEL",
    "RECYCLE",
)


def _parse_timeline_dt(value: str) -> datetime | None:
    text = (value or "").strip().replace("T", " ")
    if not text:
        return None
    try:
        if len(text) <= 10:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


@router.get("/account/timeline/{account_id}")
def timeline(
    account_id: int,
    eventTypes: list[str] = Query(default=[]),
    timeRange: list[str] = Query(default=[]),
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """单账号时间线。eventTypes / timeRange 缺省时返回全部事件。"""
    selected: list[str] = []
    for raw in eventTypes:
        code = (raw or "").strip().upper()
        if not code:
            continue
        if code not in TIMELINE_EVENT_TYPES:
            return fail(1001, "事件类型不合法")
        if code not in selected:
            selected.append(code)
    start = end = None
    if any((item or "").strip() for item in timeRange):
        if len(timeRange) < 2 or not (timeRange[0] or "").strip() or not (timeRange[1] or "").strip():
            return fail(1001, "时间范围不合法")
        start = _parse_timeline_dt(timeRange[0])
        end = _parse_timeline_dt(timeRange[1])
        if start is None or end is None:
            return fail(1001, "时间范围不合法")
        if len((timeRange[1] or "").strip()) <= 10:
            end = end.replace(hour=23, minute=59, second=59)
        if end < start:
            return fail(1001, "时间范围不合法")
    stmt = select(AccountTimelineEvent).where(AccountTimelineEvent.account_id == account_id)
    if selected:
        stmt = stmt.where(AccountTimelineEvent.event_type.in_(selected))
    if start is not None and end is not None:
        stmt = stmt.where(AccountTimelineEvent.event_time >= start, AccountTimelineEvent.event_time <= end)
    rows = db.scalars(stmt.order_by(AccountTimelineEvent.event_time.desc())).all()
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


def _bound_account_assets(db: Session, actor: User, account_id: int) -> list[dict]:
    """账号上仍有效的资产绑定（ims_asset_bind）。已报废不再提示转移。"""
    tenant = tenant_of(actor)
    rows = db.execute(
        select(AssetLedger)
        .join(AssetBind, AssetBind.asset_id == AssetLedger.id)
        .where(
            AssetBind.deleted == 0,
            AssetBind.tenant_id == tenant,
            AssetBind.bind_status == "ACTIVE",
            AssetBind.account_id == account_id,
            AssetLedger.deleted == 0,
            AssetLedger.tenant_id == tenant,
            AssetLedger.status != "SCRAPPED",
        )
        .order_by(AssetLedger.id)
    ).scalars()
    return [
        {
            "assetId": row.id,
            "assetCode": row.asset_code,
            "assetName": row.asset_name,
            "assetType": row.asset_type,
            "status": row.status,
            "ownerUserId": row.owner_user_id,
        }
        for row in rows
    ]


def _notify_asset_transfer(db: Session, actor: User, transfer: AccountTransfer, assets: list[dict]) -> None:
    """向原责任人、新责任人、资产保管人发工作台消息。不建待办。同一流转单每人只发一次。"""
    if not assets:
        return
    codes = "、".join(item["assetCode"] for item in assets if item.get("assetCode"))
    title = f"资产同步转移：{transfer.account_no}"[:128]
    content = (
        f"账号 {transfer.account_no} 绑定了 {len(assets)} 项资产（{codes}），请同步办理资产转移。"
    )[:512]
    recipients: set[int] = set()
    if transfer.from_user_id:
        recipients.add(int(transfer.from_user_id))
    if transfer.to_user_id:
        recipients.add(int(transfer.to_user_id))
    for item in assets:
        owner = item.get("ownerUserId")
        if owner:
            recipients.add(int(owner))
    tenant = tenant_of(actor)
    for user_id in sorted(recipients):
        user = db.get(User, user_id)
        if user is None or user.deleted or user.status != "ENABLED":
            continue
        if (user.tenant_id or 0) != tenant:
            continue
        exists = db.scalar(
            select(WorkMessage.id).where(
                WorkMessage.user_id == user_id,
                WorkMessage.ref_type == ASSET_TRANSFER_REF,
                WorkMessage.ref_id == transfer.id,
            )
        )
        if exists is not None:
            continue
        db.add(
            WorkMessage(
                user_id=user_id,
                title=title,
                content=content,
                channel="IN_APP",
                read_flag=0,
                source_module="ACCT",
                ref_type=ASSET_TRANSFER_REF,
                ref_id=transfer.id,
                tenant_id=tenant,
            )
        )


def _attach_asset_hint(db: Session, actor: User, transfer: AccountTransfer, payload: dict) -> dict:
    assets = _bound_account_assets(db, actor, transfer.account_id)
    _notify_asset_transfer(db, actor, transfer, assets)
    hinted = dict(payload)
    hinted["boundAssets"] = assets
    hinted["assetTransferHint"] = (
        f"该账号绑定了 {len(assets)} 项资产，是否同步发起资产转移？" if assets else None
    )
    return hinted


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


TRANSFER_FLOW_CODE = "FL-ACCT-TRF"
TRANSFER_FLOW_NODE = "新责任人确认"


def _transfer_flow_key(transfer_id: int) -> str:
    return f"ACCT-TRF-{transfer_id}"


def _ensure_transfer_flow_template(db: Session, tenant_id: int, creator_id: int) -> FlowTemplate:
    row = db.scalar(
        select(FlowTemplate).where(
            FlowTemplate.deleted == 0,
            FlowTemplate.tenant_id == tenant_id,
            FlowTemplate.template_code == TRANSFER_FLOW_CODE,
        )
    )
    if row is not None:
        return row
    now = utcnow()
    row = FlowTemplate(
        template_code=TRANSFER_FLOW_CODE,
        template_name="账号流转确认",
        business_domain="BUSINESS",
        status="PUBLISHED",
        version_label="v1.0",
        node_count=1,
        creator_id=creator_id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _open_transfer_followups(
    db: Session,
    actor: User,
    row: AccountTransfer,
    account: PlatformAccount,
    target: User,
) -> None:
    """流转待确认：新责任人工作台待办 + 流程待办。确认仍走既有 PUT …/confirm。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    platform = (account.platform_type or "DOUYIN").upper()
    title = f"账号流转待确认 {row.account_no}"[:128]
    content = f"{platform}|{row.account_no}|{row.transfer_no}|确认接收后责任人变更"[:512]
    db.add(
        Todo(
            assignee_user_id=target.id,
            task_type="acct_transfer",
            ref_type="acct_transfer",
            ref_id=row.id,
            title=title,
            content=content,
            status="PENDING",
            deadline=utcnow() + timedelta(days=1),
            tenant_id=tenant_id,
        )
    )
    tpl = _ensure_transfer_flow_template(db, tenant_id, actor.id)
    now = utcnow()
    inst = FlowInstance(
        instance_no=next_instance_no(db, tenant_id),
        template_id=tpl.id,
        template_name=tpl.template_name,
        title=f"账号流转 {row.account_no}"[:256],
        business_key=_transfer_flow_key(row.id),
        form_data={
            "title": f"账号流转 {row.account_no}",
            "transferId": row.id,
            "accountId": row.account_id,
            "accountNo": row.account_no,
            "platform": platform,
        },
        instance_status="RUNNING",
        current_node_name=TRANSFER_FLOW_NODE,
        initiator_user_id=actor.id,
        tenant_id=tenant_id,
        started_at=now,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(inst)
    db.flush()
    ensure_pending_task(db, inst, tenant_id, target.id, TRANSFER_FLOW_NODE)


def _close_transfer_followups(db: Session, row: AccountTransfer, *, accepted: bool) -> None:
    now = utcnow()
    todos = db.scalars(
        select(Todo).where(
            Todo.ref_type == "acct_transfer",
            Todo.ref_id == row.id,
            Todo.status == "PENDING",
        )
    ).all()
    for todo in todos:
        todo.status = "DONE"
    inst = db.scalar(
        select(FlowInstance).where(
            FlowInstance.deleted == 0,
            FlowInstance.tenant_id == (row.tenant_id or 0),
            FlowInstance.business_key == _transfer_flow_key(row.id),
        )
    )
    if inst is None or inst.instance_status != "RUNNING":
        return
    inst.instance_status = "APPROVED" if accepted else "CANCELLED"
    inst.current_node_name = "—"
    inst.finished_at = now
    inst.updated_at = now
    tasks = db.scalars(
        select(FlowTask).where(
            FlowTask.deleted == 0,
            FlowTask.instance_id == inst.id,
            FlowTask.task_status == "PENDING",
        )
    ).all()
    for task in tasks:
        task.task_status = "APPROVED" if accepted else "REJECTED"
        task.comment = "确认接收" if accepted else "流转未生效"
        task.handled_at = now
        task.updated_at = now


def _create_recall(body: TransferCreateBody, remark: str, actor: User, db: Session):
    """收回单：管理员发起后直接生效，账号 IN_USE → FROZEN（TRF-R2）。"""
    if body.to_user_id is not None:
        return fail(1001, "收回单不指定新责任人")
    if not _is_admin(db, actor):
        return fail(1008, "仅管理员可收回")
    ops = ops_session()
    try:
        account = _load_account(ops, body.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "FROZEN":
            return fail(1022, "账号处于冻结态")
        if account.status != "IN_USE":
            return fail(1023, "账号不在用，无法收回")
        pending = db.scalar(
            select(AccountTransfer.id).where(
                AccountTransfer.account_id == account.id,
                AccountTransfer.status == "PENDING_CONFIRM",
            )
        )
        if pending is not None:
            return fail(1023, "流转单状态非法")
        from_id = account.holder_user_id or actor.id
        now = utcnow()
        row = AccountTransfer(
            transfer_no=_next_transfer_no(db),
            account_id=account.id,
            account_no=account.account_no or str(account.id),
            from_user_id=from_id,
            to_user_id=0,
            transfer_type="RECALL",
            reason_type=body.reason_type,
            remark=remark,
            status="EFFECTIVE",
            effective_at=now,
            tenant_id=tenant_of(actor),
        )
        db.add(row)
        db.flush()
        account.status = "FROZEN"
        account.updated_at = now
        ops.commit()
        from_name = _display_name(db, from_id)
        _append_timeline(
            db,
            account_id=account.id,
            event_type="FREEZE",
            ref_no=row.transfer_no,
            ref_id=row.id,
            operator=actor,
            summary=f"收回冻结 · 原责任人 {from_name} · 状态 FROZEN",
            tenant_id=tenant_of(actor),
        )
        return ok(_attach_asset_hint(db, actor, row, transfer_vo(row, {from_id: from_name})))
    finally:
        ops.close()


@router.post("/account/transfer")
def create_transfer(
    body: TransferCreateBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    if body.transfer_type not in ("TRANSFER", "RECALL"):
        return fail(1001, "流转类型不合法")
    if body.reason_type not in TRANSFER_REASONS:
        return fail(1001, "原因分类不合法")
    remark = (body.remark or "").strip()
    if not remark or len(remark) > 512:
        return fail(1001, "交接说明必填")
    if body.transfer_type == "RECALL":
        return _create_recall(body, remark, actor, db)
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
        _open_transfer_followups(db, actor, row, account, target)
        names = {
            row.from_user_id: _display_name(db, row.from_user_id),
            row.to_user_id: target.nickname or target.username,
        }
        return ok(_attach_asset_hint(db, actor, row, transfer_vo(row, names)))
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
        _close_transfer_followups(db, row, accepted=False)
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
        _close_transfer_followups(db, row, accepted=True)
        return ok(
            _attach_asset_hint(
                db,
                actor,
                row,
                {"transferNo": row.transfer_no, "status": row.status},
            )
        )
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
    _close_transfer_followups(db, row, accepted=False)
    return ok(None)


class UnfreezeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: str


@router.post("/account/{account_id}/unfreeze")
def unfreeze_account(
    account_id: int,
    body: UnfreezeBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """TRF-R2：管理员把收回冻结账号解冻回池（FROZEN → IN_POOL）。"""
    remark = (body.remark or "").strip()
    if not remark or len(remark) > 512:
        return fail(1001, "解冻说明必填")
    if not _is_admin(db, actor):
        return fail(1008, "仅管理员可解冻")
    ops = ops_session()
    try:
        account = _load_account(ops, account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status != "FROZEN":
            return fail(1023, "账号未冻结，无法解冻")
        now = utcnow()
        account.status = "IN_POOL"
        account.holder_user_id = None
        account.updated_at = now
        ops.commit()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="UNFREEZE",
            ref_no=f"UF{account.id}",
            ref_id=account.id,
            operator=actor,
            summary=f"管理员解冻 · 状态 IN_POOL · {remark}",
            tenant_id=tenant_of(actor),
        )
        return ok(
            {
                "accountId": account.id,
                "accountNo": account.account_no or str(account.id),
                "status": "IN_POOL",
            }
        )
    finally:
        ops.close()


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


def _recharge_fields(body: RechargeCreateBody) -> tuple[dict | None, object | None]:
    amount = _money(body.amount)
    if amount is None:
        return None, fail(1001, "金额格式不合法")
    channel = (body.channel or "").strip()
    if not channel or len(channel) > 64:
        return None, fail(1001, "充值渠道必填")
    voucher = (body.voucher_url or "").strip()
    if len(voucher) > 512:
        return None, fail(1001, "凭证地址过长")
    remark = (body.remark or "").strip()
    if len(remark) > 256:
        return None, fail(1001, "备注过长")
    if not DATE_RE.match(body.recharge_date or ""):
        return None, fail(1001, "充值日期格式不合法")
    try:
        date.fromisoformat(body.recharge_date)
    except ValueError:
        return None, fail(1001, "充值日期格式不合法")
    if date.fromisoformat(body.recharge_date) > utcnow().date():
        return None, fail(1001, "充值日期不得晚于今日")
    if amount > VOUCHER_LIMIT and not voucher:
        return None, fail(1025, "冲话费凭证必填（金额 > 5000 元）")
    return {
        "amount": amount,
        "channel": channel,
        "voucher": voucher,
        "remark": remark,
        "recharge_date": body.recharge_date,
    }, None


def _load_recharge(db: Session, actor: User, recharge_id: int) -> AccountRecharge | None:
    row = db.get(AccountRecharge, recharge_id)
    if row is None or row.tenant_id != tenant_of(actor):
        return None
    return row


def _can_edit_recharge(db: Session, actor: User) -> bool:
    return _is_admin(db, actor) or _is_finance(db, actor)


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

    parsed, err = _recharge_fields(body)
    if err is not None:
        return err
    amount = parsed["amount"]
    channel = parsed["channel"]
    voucher = parsed["voucher"]
    remark = parsed["remark"]

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


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate_percent(diff: Decimal, platform: Decimal) -> tuple[Decimal, str, Decimal]:
    """差异率 = |冲话费 − 平台消费| / 平台消费。返回（百分数、文案、四位小数比率）。"""
    shown = ((diff / platform) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ratio = (shown / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return shown, f"{shown}%", ratio


def _finance_recipients(db: Session, actor: User) -> list[int]:
    role_ids = list(
        db.scalars(
            select(Role.id).where(
                Role.deleted == 0,
                Role.status == "ENABLED",
                or_(Role.role_key == FINANCE_ROLE_KEY, Role.role_name.contains("财务")),
            )
        ).all()
    )
    wanted = {actor.id}
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0, User.status == "ENABLED"))
    if admin is not None:
        wanted.add(admin.id)
    if role_ids:
        wanted.update(
            int(item)
            for item in db.scalars(select(UserRole.user_id).where(UserRole.role_id.in_(role_ids))).all()
        )
    tenant = tenant_of(actor)
    found: list[int] = []
    for user_id in sorted(wanted):
        user = db.get(User, user_id)
        if user is None or user.deleted or user.status != "ENABLED":
            continue
        if (user.tenant_id or 0) != tenant:
            continue
        found.append(user.id)
    return found


def _open_reconcile_ticket(
    db: Session,
    actor: User,
    verify: AccountRechargeVerify,
    rate_text: str,
) -> int:
    title = f"账实核对 {rate_text}（1026）"[:128]
    content = (
        f"1026 差异率 {rate_text} ≥ 2% · {verify.month} · {verify.account_no} · "
        f"冲话费 {verify.total_recharge:.2f} · 平台 {verify.platform_consumed:.2f}"
    )[:512]
    actor_todo_id = 0
    for user_id in _finance_recipients(db, actor):
        todo = Todo(
            assignee_user_id=user_id,
            task_type="acct_reconcile",
            ref_type="acct_recharge_verify",
            ref_id=verify.id,
            title=title,
            content=content,
            status="PENDING",
            deadline=utcnow(),
            tenant_id=tenant_of(actor),
        )
        db.add(todo)
        db.flush()
        if user_id == actor.id:
            actor_todo_id = todo.id
        db.add(
            WorkMessage(
                user_id=user_id,
                title=title,
                content=content,
                channel="IN_APP",
                read_flag=0,
                source_module="ACCT",
                ref_type="acct_recharge_verify",
                ref_id=verify.id,
                tenant_id=tenant_of(actor),
            )
        )
    return actor_todo_id


class RechargeVerifyBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    month: str
    account_ids: list[int] | None = Field(default=None, alias="accountIds")
    platform_consumed: float | None = Field(default=None, alias="platformConsumed")


@router.post("/account/recharge/verify")
def verify_recharge(
    body: RechargeVerifyBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """月度账实核对。本地无平台拉取时由请求携带平台实际消费；差异率 ≥ 2% 返回 1026。"""
    month = (body.month or "").strip()
    if not MONTH_RE.match(month):
        return fail(1001, "核对月份格式不合法")
    if body.platform_consumed is None:
        return fail(1001, "平台消费数据拉取失败，请稍后重试")
    platform = _money(body.platform_consumed)
    if platform is None:
        return fail(1001, "平台实际消费须大于 0")

    stmt = select(AccountRecharge).where(
        AccountRecharge.tenant_id == tenant_of(actor),
        AccountRecharge.recharge_date.like(f"{month}%"),
    )
    if body.account_ids:
        stmt = stmt.where(AccountRecharge.account_id.in_(body.account_ids))
    rows = list(db.scalars(stmt.order_by(AccountRecharge.id.asc())).all())
    if not rows:
        return fail(1001, "该月无冲话费记录")

    total = _quantize_money(sum((Decimal(str(row.amount)) for row in rows), Decimal("0")))
    if total <= 0:
        return fail(1001, "该月无冲话费记录")
    diff = _quantize_money(abs(total - platform))
    shown, rate_text, ratio = _rate_percent(diff, platform)
    over = shown >= DIFF_RATE_LIMIT
    status = "DIFF" if over else "MATCHED"

    remaining = diff
    for index, row in enumerate(rows):
        if index == len(rows) - 1:
            share = remaining
        else:
            share = _quantize_money(Decimal(str(row.amount)) / total * diff)
            remaining = _quantize_money(remaining - share)
        row.verify_status = status
        row.verify_diff = float(share)
        row.updated_at = utcnow()

    account_ids = sorted({row.account_id for row in rows})
    scoped_id = account_ids[0] if len(account_ids) == 1 else 0
    account_no = rows[0].account_no if len(account_ids) == 1 else "多账号"
    verify = AccountRechargeVerify(
        verify_no=_next_doc_no(db, AccountRechargeVerify, AccountRechargeVerify.verify_no, "VR"),
        month=month,
        account_id=scoped_id,
        account_no=account_no,
        total_recharge=float(total),
        platform_consumed=float(platform),
        diff_amount=float(diff),
        diff_rate=float(ratio),
        status=status,
        operator_user_id=actor.id,
        tenant_id=tenant_of(actor),
    )
    db.add(verify)
    db.flush()

    work_order_id = 0
    if over:
        work_order_id = _open_reconcile_ticket(db, actor, verify, rate_text)
        verify.work_order_id = work_order_id

    grouped: dict[int, list[AccountRecharge]] = {}
    for row in rows:
        grouped.setdefault(row.account_id, []).append(row)
    items = []
    for account_id, group in grouped.items():
        recharge_amount = _quantize_money(sum((Decimal(str(item.amount)) for item in group), Decimal("0")))
        if len(grouped) == 1:
            platform_amount = platform
            item_diff = diff
        else:
            platform_amount = _quantize_money(recharge_amount / total * platform)
            item_diff = _quantize_money(abs(recharge_amount - platform_amount))
        items.append(
            {
                "accountId": account_id,
                "accountNo": group[0].account_no,
                "rechargeAmount": float(recharge_amount),
                "platformAmount": float(platform_amount),
                "diff": float(item_diff),
            }
        )

    message = (
        f"账实核对差异率超阈值（{rate_text} ≥ 2%）"
        if over
        else f"核对完成，差异率 {rate_text}（阈值 < 2%）"
    )
    payload = {
        "verifyTaskId": verify.verify_no,
        "message": message,
        "month": month,
        "totalRecharge": float(total),
        "platformConsumed": float(platform),
        "diffAmount": float(diff),
        "diffRate": float(ratio),
        "diffRateText": rate_text,
        "overThreshold": over,
        "verifyStatus": status,
        "workOrderId": work_order_id or None,
        "diffItems": items,
    }
    if over:
        return fail(1026, message, payload)
    return ok(payload)


def _primary_dept_id(db: Session, user_id: int, tenant_id: int) -> int:
    if not user_id:
        return 0
    dept = db.scalar(
        select(UserDept.dept_id)
        .where(UserDept.user_id == user_id, UserDept.tenant_id == tenant_id)
        .order_by(UserDept.dept_id.asc())
        .limit(1)
    )
    return int(dept or 0)


def _summary_accounts(account_ids: set[int]) -> dict[int, PlatformAccount]:
    if not account_ids:
        return {}
    ops = ops_session()
    try:
        rows = ops.scalars(select(PlatformAccount).where(PlatformAccount.id.in_(account_ids))).all()
        return {int(row.id): row for row in rows if not row.deleted}
    finally:
        ops.close()


def _summary_query(month: str, group_by: str) -> tuple[str, str] | object:
    period = (month or "").strip()
    if not MONTH_RE.match(period):
        return fail(1001, "汇总月份格式不合法")
    grouped = (group_by or "").strip().upper()
    if grouped not in SUMMARY_GROUPS:
        return fail(1001, "汇总维度不合法")
    return period, grouped


def _summary_payload(db: Session, actor: User, period: str, group_by: str) -> dict:
    """成本汇总。期间为 month（yyyy-MM）；维度 ACCOUNT / DEPT / PLATFORM（契约 2.4.5）。"""
    tenant = tenant_of(actor)
    rows = list(
        db.scalars(
            select(AccountRecharge)
            .where(
                AccountRecharge.tenant_id == tenant,
                AccountRecharge.recharge_date.like(f"{period}%"),
            )
            .order_by(AccountRecharge.id.asc())
        ).all()
    )
    accounts = _summary_accounts({int(row.account_id) for row in rows})
    buckets: dict[str, dict] = {}
    total_amount = Decimal("0")
    total_diff = Decimal("0")
    for row in rows:
        amount = Decimal(str(row.amount or 0))
        diff = Decimal(str(row.verify_diff)) if row.verify_diff is not None else Decimal("0")
        account = accounts.get(int(row.account_id))
        if group_by == "ACCOUNT":
            key = str(row.account_id)
            name = (account.account_name if account is not None else "") or ""
            number = (account.account_no if account is not None else "") or row.account_no or key
            label = f"{number} · {name}".strip(" ·") if name else number
        elif group_by == "DEPT":
            holder = int(account.holder_user_id or 0) if account is not None else 0
            owner = holder or int(row.operator_user_id or 0)
            dept_id = _primary_dept_id(db, owner, tenant)
            key = str(dept_id)
            label = "未分配" if dept_id == 0 else f"部门#{dept_id}"
        else:
            platform = ((account.platform_type if account is not None else "") or "").strip()
            key = platform or "UNKNOWN"
            label = PLATFORM_LABELS.get(key, platform or "未识别平台")
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {"dimKey": key, "dimLabel": label, "amount": Decimal("0"), "count": 0, "diff": Decimal("0")}
            buckets[key] = bucket
        bucket["amount"] += amount
        bucket["count"] += 1
        bucket["diff"] += diff
        total_amount += amount
        total_diff += diff

    ordered = sorted(buckets.values(), key=lambda item: (-item["amount"], item["dimKey"]))
    payload_rows = [
        {
            "dimKey": item["dimKey"],
            "dimLabel": item["dimLabel"],
            "totalAmount": _money_out(item["amount"]),
            "recordCount": int(item["count"]),
            "diffAmount": _money_out(item["diff"]),
        }
        for item in ordered
    ]
    return {
        "groupBy": group_by,
        "month": period,
        "rows": payload_rows,
        "totals": {
            "totalAmount": _money_out(total_amount),
            "recordCount": len(rows),
            "diffAmount": _money_out(total_diff),
        },
    }


@router.get("/account/recharge/summary")
def recharge_summary(
    month: str = "",
    groupBy: str = "",
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    parsed = _summary_query(month, groupBy)
    if not isinstance(parsed, tuple):
        return parsed
    period, group_by = parsed
    return ok(_summary_payload(db, actor, period, group_by))


def _summary_matrix(payload: dict) -> list[list[str]]:
    header = ["维度键", "维度", "金额", "笔数", "差异金额"]
    body = [header]
    for row in payload["rows"]:
        body.append(
            [
                str(row["dimKey"]),
                str(row["dimLabel"]),
                f"{float(row['totalAmount']):.2f}",
                str(row["recordCount"]),
                f"{float(row['diffAmount']):.2f}",
            ]
        )
    totals = payload["totals"]
    body.append(
        [
            "合计",
            str(payload["groupBy"]),
            f"{float(totals['totalAmount']):.2f}",
            str(totals["recordCount"]),
            f"{float(totals['diffAmount']):.2f}",
        ]
    )
    return body


def _build_csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


EXPORT_TTL_SEC = 600
CSV_MEDIA = "text/csv; charset=utf-8"
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_EXPORTS: dict[str, tuple] = {}


def _purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        _EXPORTS.pop(key, None)


@router.get("/account/recharge/summary/export")
def recharge_summary_export(
    month: str = "",
    groupBy: str = "",
    format: str = "XLSX",
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """成本汇总导出。复用汇总查询，格式 XLSX / CSV。"""
    parsed = _summary_query(month, groupBy)
    if not isinstance(parsed, tuple):
        return parsed
    period, group_by = parsed
    fmt = (format or "").strip().upper()
    if fmt not in {"XLSX", "CSV"}:
        return fail(1001, "format 仅支持 XLSX 或 CSV")
    payload = _summary_payload(db, actor, period, group_by)
    matrix = _summary_matrix(payload)
    if fmt == "CSV":
        body = _build_csv(matrix)
        media = CSV_MEDIA
        suffix = "csv"
    else:
        from app.dc_trace import build_xlsx

        body = build_xlsx(matrix)
        media = XLSX_MEDIA
        suffix = "xlsx"
    now = time.time()
    _purge_exports(now)
    token = secrets.token_urlsafe(24)
    filename = f"recharge_summary_{period}_{group_by}.{suffix}"
    _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, media, filename, actor.id)
    return ok(
        {
            "downloadUrl": f"/admin-api/ims/account/recharge/summary/export/file?token={token}",
            "expiresIn": EXPORT_TTL_SEC,
            "fileName": filename,
            "month": period,
            "groupBy": group_by,
            "format": fmt,
        }
    )


@router.get("/account/recharge/summary/export/file")
def recharge_summary_export_file(token: str, actor: User = Depends(current_user)):
    now = time.time()
    _purge_exports(now)
    item = _EXPORTS.get(token)
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[4] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, media, filename, _user_id = item
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/account/recharge/{recharge_id}")
def update_recharge(
    recharge_id: int,
    body: RechargeCreateBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """编辑冲话费。契约 2.4.3：仅未核对可改；已核对须先由管理员解锁。"""
    if not _can_edit_recharge(db, actor):
        return fail(1008, "仅财务或管理员可编辑冲话费")
    row = _load_recharge(db, actor, recharge_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.verify_status != "UNVERIFIED":
        return fail(1001, "已核对记录不可直接编辑，请先解锁")
    if body.account_id != row.account_id:
        return fail(1001, "不可变更账号")
    parsed, err = _recharge_fields(body)
    if err is not None:
        return err
    ops = ops_session()
    try:
        account = _load_account(ops, row.account_id)
        if account is None:
            return fail(1504, "资源不可用")
        if account.status == "CANCELLED":
            return fail(1001, "已注销账号不可冲话费")
    finally:
        ops.close()
    row.amount = float(parsed["amount"])
    row.channel = parsed["channel"]
    row.voucher_url = parsed["voucher"]
    row.recharge_date = parsed["recharge_date"]
    row.remark = parsed["remark"]
    row.updated_at = utcnow()
    _append_timeline(
        db,
        account_id=row.account_id,
        event_type="RECHARGE",
        ref_no=f"RC{row.id}",
        ref_id=row.id,
        operator=actor,
        summary=f"冲话费更正 · ¥{parsed['amount']} · {parsed['channel']}",
        tenant_id=tenant_of(actor),
    )
    return ok(None)


def _diff_ticket_ready(db: Session, actor: User, row: AccountRecharge) -> bool:
    month = (row.recharge_date or "")[:7]
    if not MONTH_RE.match(month):
        return False
    ticket = db.scalar(
        select(AccountRechargeVerify.id).where(
            AccountRechargeVerify.tenant_id == tenant_of(actor),
            AccountRechargeVerify.month == month,
            AccountRechargeVerify.status == "DIFF",
            AccountRechargeVerify.work_order_id > 0,
            or_(
                AccountRechargeVerify.account_id == row.account_id,
                AccountRechargeVerify.account_id == 0,
            ),
        )
    )
    return ticket is not None


@router.post("/account/recharge/{recharge_id}/unlock")
def unlock_recharge(
    recharge_id: int,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """已核对记录解锁。管理员（R1）把 MATCHED / DIFF 退回未核对后再编辑。

    一致记录直接解锁。差异记录须已生成财务核查工单（1026）。财务角色不能解锁。
    """
    if not _is_admin(db, actor):
        return fail(1008, "仅管理员可解锁已核对记录")
    row = _load_recharge(db, actor, recharge_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.verify_status == "UNVERIFIED":
        return fail(1001, "未核对记录无需解锁")
    if row.verify_status not in {"MATCHED", "DIFF"}:
        return fail(1001, "核对状态不可解锁")
    if row.verify_status == "DIFF" and not _diff_ticket_ready(db, actor, row):
        return fail(1001, "差异记录须先生成财务核查工单")
    previous = row.verify_status
    row.verify_status = "UNVERIFIED"
    row.verify_diff = None
    row.updated_at = utcnow()
    _append_timeline(
        db,
        account_id=row.account_id,
        event_type="RECHARGE",
        ref_no=f"RC{row.id}",
        ref_id=row.id,
        operator=actor,
        summary=f"解锁已核对记录 · 原状态 {previous}",
        tenant_id=tenant_of(actor),
    )
    return ok(
        {
            "id": row.id,
            "verifyStatus": "UNVERIFIED",
            "previousStatus": previous,
            "message": "已解锁，可再次编辑",
        }
    )


import app.acct_pool  # noqa: E402,F401  — 注册池状态、回收回池、时间线导出
