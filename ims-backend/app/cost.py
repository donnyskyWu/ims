from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.account import account_visible, load_scope_ip_groups
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, tenant_of, user_names
from app.football_client import fetch_football_orders, sum_revenue
from app.models import User
from app.ops_models import AccountCost, Company, IpGroup, PlatformAccount

router = APIRouter()

def _date_ok(value: str) -> bool:
    import re

    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value or ""))


def _period_ok(value: str) -> bool:
    import re

    return bool(re.match(r"^\d{4}-\d{2}$", value or ""))


def load_account(ops: Session, actor: User, account_id: int) -> PlatformAccount | None:
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return None
    return row


def football_author_key(account: PlatformAccount) -> str:
    if account.author_user_id:
        return str(account.author_user_id)
    return str(account.id)


def cost_vo(row: AccountCost) -> dict:
    return {
        "id": str(row.id),
        "accountId": str(row.account_id),
        "costType": row.cost_type,
        "processSubtype": row.process_subtype or None,
        "amount": round(float(row.amount or 0), 2),
        "payMethod": row.pay_method or None,
        "payDate": row.pay_date or None,
        "period": row.period or None,
        "handlerUserId": str(row.handler_user_id) if row.handler_user_id else None,
        "remark": row.remark or "",
    }


def account_cost_total(ops: Session, account_id: int, tenant_id: int) -> float:
    stmt = select(func.coalesce(func.sum(AccountCost.amount), 0)).where(
        AccountCost.account_id == account_id,
        AccountCost.deleted == 0,
        AccountCost.tenant_id == tenant_id,
    )
    return round(float(ops.scalar(stmt) or 0), 2)


class PurchaseBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    amount: float
    payMethod: str | None = None
    payDate: str | None = None
    period: str | None = None
    remark: str | None = None
    handlerUserId: int | None = None


class ProcessBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int | None = None
    amount: float
    processSubtype: str | None = None
    payMethod: str | None = None
    payDate: str | None = None
    period: str | None = None
    remark: str | None = None
    handlerUserId: int | None = None


@router.get("/account/{account_id}")
def get_account_cost(
    account_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    account = load_account(ops, actor, account_id)
    if account is None:
        return fail(1231, "账号不存在")
    tenant_id = tenant_of(actor)
    purchase = ops.scalar(
        select(AccountCost).where(
            AccountCost.account_id == account_id,
            AccountCost.cost_type == "PURCHASE",
            AccountCost.deleted == 0,
            AccountCost.tenant_id == tenant_id,
        )
    )
    processes = ops.scalars(
        select(AccountCost)
        .where(
            AccountCost.account_id == account_id,
            AccountCost.cost_type == "PROCESS",
            AccountCost.deleted == 0,
            AccountCost.tenant_id == tenant_id,
        )
        .order_by(AccountCost.id.desc())
    ).all()
    process_total = round(sum(float(row.amount or 0) for row in processes), 2)
    return ok(
        {
            "accountId": str(account.id),
            "accountNo": account.account_no,
            "accountName": account.account_name,
            "purchase": cost_vo(purchase) if purchase else None,
            "processCosts": [cost_vo(row) for row in processes],
            "processTotal": process_total,
            "totalCost": round((float(purchase.amount) if purchase else 0) + process_total, 2),
        }
    )


@router.put("/account/{account_id}/purchase")
def upsert_purchase(
    account_id: int,
    body: PurchaseBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    account = load_account(ops, actor, account_id)
    if account is None:
        return fail(1231, "账号不存在")
    if body.amount is None or body.amount < 0.01:
        return fail(2015, "金额非法")
    if body.payDate and not _date_ok(body.payDate):
        return fail(2016, "日期范围非法")
    if body.period and not _period_ok(body.period):
        return fail(2016, "日期范围非法")
    tenant_id = tenant_of(actor)
    row = ops.scalar(
        select(AccountCost).where(
            AccountCost.account_id == account_id,
            AccountCost.cost_type == "PURCHASE",
            AccountCost.deleted == 0,
            AccountCost.tenant_id == tenant_id,
        )
    )
    if row is None:
        row = AccountCost(
            account_id=account_id,
            cost_type="PURCHASE",
            tenant_id=tenant_id,
            handler_user_id=body.handlerUserId or actor.id,
        )
        ops.add(row)
    row.amount = float(body.amount)
    row.pay_method = body.payMethod or ""
    row.pay_date = body.payDate or ""
    row.period = body.period or ""
    row.remark = body.remark or ""
    if body.handlerUserId is not None:
        row.handler_user_id = body.handlerUserId
    row.updated_at = utcnow()
    ops.flush()
    return ok(cost_vo(row))


@router.post("/account/{account_id}/process")
def create_process(
    account_id: int,
    body: ProcessBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    account = load_account(ops, actor, account_id)
    if account is None:
        return fail(1231, "账号不存在")
    if body.amount is None or body.amount < 0.01:
        return fail(2015, "金额非法")
    if body.payDate and not _date_ok(body.payDate):
        return fail(2016, "日期范围非法")
    if body.period and not _period_ok(body.period):
        return fail(2016, "日期范围非法")
    row = AccountCost(
        account_id=account_id,
        cost_type="PROCESS",
        process_subtype=body.processSubtype or "PROCESS_OTHER",
        amount=float(body.amount),
        pay_method=body.payMethod or "",
        pay_date=body.payDate or "",
        period=body.period or "",
        remark=body.remark or "",
        handler_user_id=body.handlerUserId or actor.id,
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(cost_vo(row))


@router.put("/account/{account_id}/process")
def update_process(
    account_id: int,
    body: ProcessBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if body.id is None:
        return fail(1001, "过程成本 id 必填")
    account = load_account(ops, actor, account_id)
    if account is None:
        return fail(1231, "账号不存在")
    row = ops.get(AccountCost, body.id)
    if row is None or row.deleted or row.account_id != account_id or row.cost_type != "PROCESS":
        return fail(1504, "资源不可用")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if body.amount is None or body.amount < 0.01:
        return fail(2015, "金额非法")
    row.amount = float(body.amount)
    row.process_subtype = body.processSubtype or row.process_subtype
    row.pay_method = body.payMethod or row.pay_method
    row.pay_date = body.payDate or row.pay_date
    row.period = body.period or row.period
    row.remark = body.remark or row.remark
    if body.handlerUserId is not None:
        row.handler_user_id = body.handlerUserId
    row.updated_at = utcnow()
    return ok(cost_vo(row))


@router.delete("/account/{account_id}/process")
def delete_process(
    account_id: int,
    id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    account = load_account(ops, actor, account_id)
    if account is None:
        return fail(1231, "账号不存在")
    row = ops.get(AccountCost, id)
    if row is None or row.deleted or row.account_id != account_id or row.cost_type != "PROCESS":
        return fail(1504, "资源不可用")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok({})


@router.get("/roi")
def roi_analysis(
    request: Request,
    startDate: str,
    endDate: str,
    dimension: str = "ACCOUNT",
    ipGroupId: int | None = None,
    accountId: int | None = None,
    companyId: int | None = None,
    userId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not _date_ok(startDate) or not _date_ok(endDate):
        return fail(2016, "日期范围非法")
    load_scope_ip_groups(db, request, actor)
    dim = (dimension or "ACCOUNT").upper()
    if dim not in {"ACCOUNT", "IP_GROUP", "COMPANY", "PERSON"}:
        return fail(1001, "维度非法")
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)

    stmt = select(PlatformAccount).where(PlatformAccount.deleted == 0, PlatformAccount.tenant_id == tenant_id)
    scope = getattr(request.state, "scope", None)
    if scope and scope.kind == "IP_GROUP":
        ids = getattr(scope, "ip_group_ids", None) or []
        if ids:
            stmt = stmt.where(PlatformAccount.ip_group_id.in_(ids))
    if ipGroupId:
        stmt = stmt.where(PlatformAccount.ip_group_id == ipGroupId)
    if accountId:
        stmt = stmt.where(PlatformAccount.id == accountId)
    if companyId:
        stmt = stmt.where(PlatformAccount.company_id == companyId)
    if userId:
        stmt = stmt.where(PlatformAccount.holder_user_id == userId)

    accounts = ops.scalars(stmt.order_by(PlatformAccount.id)).all()
    revenue_delayed = False
    total_revenue: float | None = 0.0
    details: list[dict] = []

    group_ids = {row.ip_group_id for row in accounts if row.ip_group_id}
    company_ids = {row.company_id for row in accounts if row.company_id}
    groups = {
        row.id: row.group_name
        for row in ops.scalars(select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)).all()
    } if group_ids else {}
    companies = {
        row.id: row.company_name
        for row in ops.scalars(select(Company).where(Company.id.in_(company_ids), Company.deleted == 0)).all()
    } if company_ids else {}
    holders = user_names(db, {row.holder_user_id for row in accounts if row.holder_user_id})

    buckets: dict[str, dict] = {}

    def bucket_key(account: PlatformAccount) -> tuple[str, str]:
        if dim == "IP_GROUP":
            gid = account.ip_group_id or 0
            return ("IP_GROUP", str(gid))
        if dim == "COMPANY":
            cid = account.company_id or 0
            return ("COMPANY", str(cid))
        if dim == "PERSON":
            uid = account.holder_user_id or 0
            return ("PERSON", str(uid))
        return ("ACCOUNT", str(account.id))

    def bucket_label(kind: str, key: str, account: PlatformAccount) -> str:
        if kind == "IP_GROUP":
            return groups.get(int(key), f"IP组#{key}") if key != "0" else "未分组"
        if kind == "COMPANY":
            return companies.get(int(key), f"公司#{key}") if key != "0" else "未归属公司"
        if kind == "PERSON":
            return holders.get(int(key), f"用户#{key}") if key != "0" else "未指定人员"
        return f"{account.account_no} {account.account_name}".strip()

    for account in accounts:
        kind, key = bucket_key(account)
        slot = buckets.setdefault(key, {"name": bucket_label(kind, key, account), "cost": 0.0, "revenue": 0.0, "revenueOk": True})
        slot["cost"] = round(slot["cost"] + account_cost_total(ops, account.id, tenant_id), 2)
        rev, err = sum_revenue(
            start_date=startDate,
            end_date=endDate,
            author_id=football_author_key(account),
        )
        if err:
            revenue_delayed = True
            slot["revenueOk"] = False
        elif rev is not None:
            slot["revenue"] = round(slot["revenue"] + rev, 2)

    if revenue_delayed:
        total_revenue = None
    else:
        total_revenue = round(sum(item["revenue"] for item in buckets.values()), 2)

    total_cost = round(sum(item["cost"] for item in buckets.values()), 2)
    for item in buckets.values():
        revenue_val = None if not item["revenueOk"] else round(item["revenue"], 2)
        cost_val = round(item["cost"], 2)
        roi_val = None
        if revenue_val is not None and cost_val > 0:
            roi_val = round(revenue_val / cost_val, 2)
        elif revenue_val is not None and cost_val == 0:
            roi_val = None
        details.append(
            {
                "name": item["name"],
                "cost": cost_val,
                "revenue": revenue_val,
                "roi": roi_val,
                "revenueDelayed": not item["revenueOk"],
            }
        )
    details.sort(key=lambda row: row["name"])
    total = len(details)
    page_rows = details[(page_no - 1) * size : page_no * size]
    roi_total = None
    if total_revenue is not None and total_cost > 0:
        roi_total = round(total_revenue / total_cost, 2)

    return ok(
        {
            "dimension": dim,
            "startDate": startDate,
            "endDate": endDate,
            "totalCost": total_cost,
            "totalRevenue": total_revenue,
            "roi": roi_total,
            "revenueDelayed": revenue_delayed,
            "revenueDelayHint": "数据延迟" if revenue_delayed else None,
            "details": page_rows,
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
            "note": "账号粒度；营收来自 Football 订单 WebAPI",
        }
    )


@router.get("/football-order/list")
def football_orders(
    startDate: str,
    endDate: str,
    authorId: str | None = None,
    status: int | None = None,
    pageNum: int = 1,
    pageSize: int = 10,
    actor: User = Depends(current_user),
):
    if not _date_ok(startDate) or not _date_ok(endDate):
        return fail(2016, "日期范围非法")
    params: dict = {
        "startDate": startDate,
        "endDate": endDate,
        "pageNum": pageNum,
        "pageSize": min(pageSize, 100),
    }
    if authorId:
        params["authorId"] = authorId
    if status is not None:
        params["status"] = status
    data, err = fetch_football_orders(params)
    if err:
        return fail(1232, "营收源超时")
    rows = data.get("list") or []
    total = int(data.get("total") or len(rows))
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "id": str(row.get("id", "")),
                "orderNo": row.get("orderNo"),
                "userId": row.get("userId"),
                "authorId": row.get("authorId"),
                "amount": row.get("amount"),
                "payAmount": row.get("payAmount"),
                "status": row.get("status"),
                "orderType": row.get("orderType"),
                "payTime": row.get("payTime"),
                "createTime": row.get("createTime"),
                "sourceTable": row.get("sourceTable") or "pay_all_order",
            }
        )
    return ok({"list": normalized, "total": total, "pageNum": pageNum, "pageSize": params["pageSize"]})
