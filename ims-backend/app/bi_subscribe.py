"""BI-003 订阅与分享（W9-10 首片 · 三 Tab API）。"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import (
    primary_dept_id,
    report_row_visible,
    restrict_report_def,
    restrict_share_link,
    share_row_visible,
)
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiReportDef, BiShareLink, BiSubscription, SysParam, User

router = APIRouter(prefix="/bi/subscribe", tags=["bi-subscribe"])

DINGTALK_WEBHOOK_PARAM = "bi.dingtalk.webhook.url"
DINGTALK_WEBHOOK_ENV = "IMS_BI_DINGTALK_WEBHOOK_URL"

BJ = timezone(timedelta(hours=8))
# 库存仍用 DAY/WEEK/MONTH。页面与契约写 DAILY/WEEKLY/MONTHLY，写入时归一，避免另开调度。
PERIOD_CANON = {
    "DAY": "DAY",
    "DAILY": "DAY",
    "WEEK": "WEEK",
    "WEEKLY": "WEEK",
    "MONTH": "MONTH",
    "MONTHLY": "MONTH",
}
PERIOD_CODE = {"DAY": "DAILY", "WEEK": "WEEKLY", "MONTH": "MONTHLY"}
SUB_STATUSES = frozenset({"ACTIVE", "PAUSED"})
APPROVAL_STATUSES = frozenset({"NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED", "EXPIRED"})


class SubscribeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    subName: str
    reportId: int
    period: str = "WEEK"
    pushTime: str = "09:00"
    channels: str = "SITE+DING"


class SubscribeUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    subName: str | None = None
    period: str | None = None
    pushTime: str | None = None
    channels: str | None = None
    status: str | None = None


class ShareLinkBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int
    sensitive: bool = False
    expireDays: int = Field(default=7, ge=1, le=30)


class ShareApprovalBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    approvalStatus: str
    note: str = ""


def canon_period(raw: str) -> str | None:
    return PERIOD_CANON.get((raw or "").strip().upper())


def next_push_stub(period: str, push_time: str, status: str) -> str:
    """按周期与时刻估算下次推送。只给界面展示，不注册外部定时任务。"""
    if (status or "").upper() != "ACTIVE":
        return ""
    clock = "09:00"
    for token in (push_time or "").replace("：", ":").split():
        if ":" in token and len(token) >= 4:
            clock = token[:5]
            break
    try:
        hour_text, minute_text = clock.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
        if hour > 23 or minute > 59:
            raise ValueError
    except ValueError:
        hour, minute = 9, 0
    now = datetime.now(BJ)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if period == "WEEK":
        candidate = candidate + timedelta(days=(0 - candidate.weekday()) % 7)
        if candidate <= now:
            candidate += timedelta(days=7)
    elif period == "MONTH":
        if candidate <= now:
            month = candidate.month + 1
            year = candidate.year
            if month > 12:
                month = 1
                year += 1
            candidate = candidate.replace(year=year, month=month, day=1)
    elif candidate <= now:
        candidate += timedelta(days=1)
    return candidate.strftime("%Y-%m-%d %H:%M")


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def expire_str(days: int) -> str:
    return (datetime.now(BJ) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def dingtalk_webhook_url(db: Session) -> str:
    from app.settings_runtime import get_param

    return get_param(DINGTALK_WEBHOOK_PARAM, db=db).strip()


def post_dingtalk_webhook(url: str, payload: dict) -> tuple[bool, dict]:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            body: dict = {}
            if resp.headers.get("content-type", "").startswith("application/json"):
                parsed = resp.json()
                if isinstance(parsed, dict):
                    body = parsed
            return True, {"httpStatus": resp.status_code, "body": body}
    except Exception as exc:
        return False, {"error": str(exc)[:200]}


def sub_vo(row: BiSubscription) -> dict:
    return {
        "id": row.id,
        "subName": row.sub_name,
        "targetType": row.target_type,
        "reportId": row.report_id,
        "reportName": row.report_name,
        "period": row.period,
        "periodCode": PERIOD_CODE.get(row.period, row.period),
        "pushTime": row.push_time,
        "nextPushAt": next_push_stub(row.period, row.push_time, row.status),
        "channels": row.channels,
        "status": row.status,
        "lastPushStatus": row.last_push_status or "—",
        "lastPushAt": row.last_push_at or "—",
    }


def share_vo(row: BiShareLink, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "linkToken": row.link_token,
        "shareUrl": f"/ims/bi/report/preview?token={row.link_token}",
        "targetType": row.target_type,
        "targetId": row.target_id,
        "targetName": row.target_name,
        "approvalStatus": row.approval_status,
        "expireAt": row.expire_at,
        "creatorName": names.get(row.creator_user_id, ""),
        "createdAt": iso(row.created_at),
    }


def get_report(
    db: Session,
    tenant_id: int,
    report_id: int,
    actor: User,
    scope,
) -> BiReportDef | None:
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    if not report_row_visible(db, row, actor, scope):
        return None
    return row


def seed_subscriptions(db: Session, tenant_id: int, user_id: int) -> None:
    exists = db.scalar(
        select(func.count()).select_from(BiSubscription).where(
            BiSubscription.deleted == 0, BiSubscription.tenant_id == tenant_id
        )
    )
    if exists:
        return
    now = utcnow()
    samples = [
        {
            "sub_name": "直播周报",
            "report_name": "场次分析",
            "period": "WEEK",
            "push_time": "周一 09:00",
            "channels": "SITE+DING",
            "status": "ACTIVE",
            "last_push_status": "",
            "last_push_at": "",
        },
        {
            "sub_name": "GMV 日报",
            "report_name": "经营总览",
            "period": "DAY",
            "push_time": "09:00",
            "channels": "SITE+DING",
            "status": "PAUSED",
            "last_push_status": "FAILED_RETRIED",
            "last_push_at": iso(now - timedelta(days=1)),
        },
    ]
    for item in samples:
        db.add(
            BiSubscription(
                sub_name=item["sub_name"],
                target_type="REPORT",
                report_id=0,
                report_name=item["report_name"],
                period=item["period"],
                push_time=item["push_time"],
                channels=item["channels"],
                status=item["status"],
                last_push_status=item["last_push_status"],
                last_push_at=item["last_push_at"],
                subscriber_user_id=user_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    db.flush()


def seed_share_links(db: Session, tenant_id: int, user_id: int) -> None:
    exists = db.scalar(
        select(func.count()).select_from(BiShareLink).where(
            BiShareLink.deleted == 0, BiShareLink.tenant_id == tenant_id
        )
    )
    if exists:
        return
    now = utcnow()
    db.add(
        BiShareLink(
            link_token=secrets.token_hex(8),
            target_type="REPORT",
            target_id=0,
            target_name="运营日报",
            approval_status="APPROVED",
            expire_at=expire_str(7),
            creator_user_id=user_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        BiShareLink(
            link_token=secrets.token_hex(8),
            target_type="REPORT",
            target_id=0,
            target_name="成本分摊看板",
            approval_status="PENDING",
            expire_at=expire_str(7),
            creator_user_id=user_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()


@router.get("/list")
def subscribe_list(
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_subscriptions(db, tenant_id, actor.id)
    q = select(BiSubscription).where(
        BiSubscription.deleted == 0,
        BiSubscription.tenant_id == tenant_id,
        BiSubscription.subscriber_user_id == actor.id,
    )
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiSubscription.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    return paged([sub_vo(r) for r in rows], total, page_no, size)


@router.post("")
def subscribe_create(
    body: SubscribeBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    name = body.subName.strip()
    if not name:
        return fail(1001, "订阅名称必填")
    report = get_report(db, tenant_id, body.reportId, actor, request.state.scope)
    if report is None:
        row = db.get(BiReportDef, body.reportId)
        if row and not row.deleted and row.tenant_id == tenant_id:
            return fail(1008, "无权查看该报表")
        return fail(1001, "报表不存在")
    period = canon_period(body.period)
    if period is None:
        return fail(1001, "周期无效")
    now = utcnow()
    row = BiSubscription(
        sub_name=name,
        target_type=report.report_type,
        report_id=report.id,
        report_name=report.report_name,
        period=period,
        push_time=body.pushTime.strip() or "09:00",
        channels=body.channels.strip() or "SITE+DING",
        status="ACTIVE",
        subscriber_user_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return ok(sub_vo(row))


@router.put("/{sub_id:int}")
def subscribe_update(
    sub_id: int,
    body: SubscribeUpdateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiSubscription, sub_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "订阅不存在")
    if row.subscriber_user_id != actor.id:
        return fail(1201, "无权修改他人订阅")
    if body.subName is not None and body.subName.strip():
        row.sub_name = body.subName.strip()
    if body.period is not None:
        p = canon_period(body.period)
        if p is None:
            return fail(1001, "周期无效")
        row.period = p
    if body.pushTime is not None:
        row.push_time = body.pushTime.strip()
    if body.channels is not None:
        row.channels = body.channels.strip()
    if body.status is not None:
        st = body.status.strip().upper()
        if st not in SUB_STATUSES:
            return fail(1001, "状态无效")
        row.status = st
    row.updated_at = utcnow()
    return ok(sub_vo(row))


@router.delete("/{sub_id:int}")
def subscribe_delete(
    sub_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    tenant_id = tenant_of(actor)
    row = db.get(BiSubscription, sub_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "订阅不存在")
    if row.subscriber_user_id != actor.id:
        return fail(1201, "无权取消他人订阅")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(True)


@router.get("/share-link/list")
def share_link_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_share_links(db, tenant_id, actor.id)
    q = restrict_share_link(
        select(BiShareLink).where(BiShareLink.deleted == 0, BiShareLink.tenant_id == tenant_id),
        request.state.scope,
        tenant_id,
    )
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiShareLink.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_user_id for r in rows])
    return paged([share_vo(r, names) for r in rows], total, page_no, size)


@router.post("/share-link")
def share_link_create(
    body: ShareLinkBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    report = get_report(db, tenant_id, body.reportId, actor, request.state.scope)
    if report is None:
        row = db.get(BiReportDef, body.reportId)
        if row and not row.deleted and row.tenant_id == tenant_id:
            return fail(1008, "无权查看该报表")
        return fail(1001, "报表不存在")
    approval = "PENDING" if body.sensitive else "APPROVED"
    now = utcnow()
    row = BiShareLink(
        link_token=secrets.token_hex(8),
        target_type=report.report_type,
        target_id=report.id,
        target_name=report.report_name,
        approval_status=approval,
        expire_at=expire_str(body.expireDays),
        creator_user_id=actor.id,
        dept_id=report.dept_id or primary_dept_id(db, actor.id, tenant_id),
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_user_id])
    return ok(share_vo(row, names))


@router.put("/share-approval/{link_id:int}")
def share_link_approval(
    link_id: int,
    body: ShareApprovalBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiShareLink, link_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "分享链接不存在")
    if not share_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权处理该分享链接")
    st = body.approvalStatus.strip().upper()
    if st not in {"APPROVED", "REJECTED", "EXPIRED"}:
        return fail(1001, "审批状态无效")
    row.approval_status = st
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_user_id])
    return ok(share_vo(row, names))


@router.get("/publish/list")
def publish_manage_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    q = restrict_report_def(
        select(BiReportDef).where(
            BiReportDef.deleted == 0,
            BiReportDef.tenant_id == tenant_id,
            BiReportDef.status == "PUBLISHED",
        ),
        request.state.scope,
        tenant_id,
    )
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiReportDef.updated_at.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    items = []
    for r in rows:
        sub_cnt = int(
            db.scalar(
                select(func.count()).select_from(BiSubscription).where(
                    BiSubscription.deleted == 0,
                    BiSubscription.tenant_id == tenant_id,
                    BiSubscription.report_id == r.id,
                )
            )
            or 0
        )
        items.append(
            {
                "reportId": r.id,
                "reportNo": r.report_no,
                "reportName": r.report_name,
                "reportType": r.report_type,
                "status": r.status,
                "creatorName": names.get(r.creator_id, ""),
                "updatedAt": iso(r.updated_at),
                "subscriptionCount": sub_cnt,
            }
        )
    return paged(items, total, page_no, size)


@router.post("/{sub_id}/push-now")
def subscribe_push_now(
    sub_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """钉钉推送：可配置 Webhook URL（系统参数或 env）；未配置时本地桩。"""
    tenant_id = tenant_of(actor)
    row = db.get(BiSubscription, sub_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "订阅不存在")
    if row.status != "ACTIVE":
        return fail(1001, "订阅未生效，无法推送")
    now = iso(datetime.now(BJ))
    channels = (row.channels or "").upper()
    ding = "DING" in channels
    snapshot = {
        "subscriptionId": row.id,
        "subName": row.sub_name,
        "reportName": row.report_name,
        "snapshotAt": now,
        "summary": {"gmv": 4128000, "sessions": 14, "note": "即时推送快照占位 · BIS-R1"},
        "rows": [
            {"platform": "抖音", "gmv": 186400},
            {"platform": "视频号", "gmv": 412800},
        ],
    }
    ding_stub = None
    webhook_url = dingtalk_webhook_url(db) if ding else ""
    if ding:
        if webhook_url:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"IMS 报表订阅 · {row.sub_name}",
                    "text": (
                        f"### {row.report_name}\n"
                        f"- 订阅：{row.sub_name}\n"
                        f"- 快照时间：{now}\n"
                        f"- GMV 摘要：{snapshot['summary']['gmv']}"
                    ),
                },
            }
            ok_push, detail = post_dingtalk_webhook(webhook_url, payload)
            row.last_push_status = "DING_OK" if ok_push else "DING_FAIL"
            body = detail.get("body") or {}
            msg_id = str(body.get("errmsg") or body.get("msgId") or f"ding-webhook-{row.id}-{secrets.token_hex(4)}")
            ding_stub = {
                "msgId": msg_id,
                "channel": "DINGTALK",
                "status": "WEBHOOK_SENT" if ok_push else "WEBHOOK_FAILED",
                "webhookConfigured": True,
                "httpStatus": detail.get("httpStatus"),
                "hint": "已 POST 钉钉 Webhook" if ok_push else detail.get("error", "Webhook 调用失败"),
            }
        else:
            row.last_push_status = "DING_OK"
            ding_stub = {
                "msgId": f"ding-stub-{row.id}-{secrets.token_hex(4)}",
                "channel": "DINGTALK",
                "status": "ACCEPTED",
                "webhookConfigured": False,
                "hint": f"未配置 {DINGTALK_WEBHOOK_PARAM} / {DINGTALK_WEBHOOK_ENV}，本地桩已受理",
            }
    else:
        row.last_push_status = "SITE_OK"
    row.last_push_at = now
    row.updated_at = utcnow()
    db.flush()
    return ok(
        {
            "subscriptionId": row.id,
            "lastPushStatus": row.last_push_status,
            "lastPushAt": row.last_push_at,
            "snapshot": snapshot,
            "dingTalk": ding_stub,
        }
    )


@router.get("/snapshot/{sub_id:int}")
def subscribe_snapshot(
    sub_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    tenant_id = tenant_of(actor)
    row = db.get(BiSubscription, sub_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "订阅不存在")
    return ok(
        {
            "subscriptionId": row.id,
            "subName": row.sub_name,
            "reportName": row.report_name,
            "snapshotAt": iso(row.updated_at),
            "summary": {"gmv": 4128000, "sessions": 14, "note": "推送快照摘要占位 · BIS-R1"},
            "rows": [
                {"platform": "抖音", "gmv": 186400},
                {"platform": "视频号", "gmv": 412800},
            ],
        }
    )
