from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.account import COLLECT_PLATFORMS, bind_summary
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import check_enum, count_of, ops_db, page_args, paged, tenant_of, visible
from app.models import User
from app.ops_models import (
    CollectConfig,
    CollectLog,
    CollectTask,
    CollectTaskMember,
    CollectorAccountBind,
    PlatformAccount,
)

router = APIRouter(prefix="/collect", tags=["collect"])

from app.collect_config import router as collect_config_router  # noqa: E402

router.include_router(collect_config_router)

UNIFIED_CRON = "0 2 * * *"
EXT_UNIFIED_CRON = "0 0 22 * * ?"
TASK_STATUS_LABEL = {
    "ENABLED": "启用",
    "DISABLED": "停用",
    "RUNNING": "运行中",
}
RETRYABLE_LOG_STATUS = {"FAILED", "PARTIAL", "COOKIE_EXPIRED", "ENGINE_UNAVAILABLE"}


class TaskBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskName: str
    platformType: str
    accountId: int | None = None
    collectConfigId: int | None = None
    credentialProfile: str | None = "default"
    method: str | None = None
    frequency: str
    cron: str
    status: str = "ENABLED"


class EnsureUnifiedBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    platformType: str | None = None


class ManualFillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskId: int
    accountId: int | None = None
    recordCount: int = 1
    dataType: str = "WORK"
    remark: str = ""


def load_task(ops: Session, actor: User, task_id: int) -> CollectTask | None:
    row = ops.get(CollectTask, task_id)
    if not visible(row, actor):
        return None
    return row


def member_count(ops: Session, task_id: int, tenant_id: int) -> int:
    return int(
        ops.scalar(
            select(func.count(CollectTaskMember.id)).where(
                CollectTaskMember.task_id == task_id,
                CollectTaskMember.deleted == 0,
                CollectTaskMember.tenant_id == tenant_id,
            )
        )
        or 0
    )


def bind_of(ops: Session, account_id: int | None) -> CollectorAccountBind | None:
    if not account_id:
        return None
    return ops.scalar(
        select(CollectorAccountBind).where(
            CollectorAccountBind.oa_account_id == account_id,
            CollectorAccountBind.deleted == 0,
        )
    )


def account_label(ops: Session, account_id: int | None) -> str:
    if not account_id:
        return ""
    row = ops.get(PlatformAccount, account_id)
    if row is None:
        return str(account_id)
    return f"{row.platform_type} / {row.account_no or row.id} {row.account_name}"


def schedule_next(frequency: str) -> str:
    from app.internal_collect import initial_next_run

    return initial_next_run(frequency or "DAILY")


def account_health_label(ops: Session, account_id: int | None) -> str:
    if not account_id:
        return ""
    from app.internal_collect import health_label

    return health_label(bind_of(ops, account_id))


def bind_warning(ops: Session, account_id: int | None) -> str | None:
    if not account_id:
        return None
    account = ops.get(PlatformAccount, account_id)
    if account is None:
        return None
    summary = bind_summary(account, bind_of(ops, account_id))
    if summary in ("未绑定", "Cookie 失效", "Cookie 已失效", "连接失败", "浏览器引擎不可用"):
        return f"{summary} Collector，任务可保存但执行将失败"
    return None


def task_vo(
    ops: Session,
    row: CollectTask,
    accounts: dict[int, PlatformAccount] | None = None,
) -> dict:
    bind_target = None
    platform_account = ""
    if row.is_unified or row.is_external_unified:
        mc = member_count(ops, row.id, row.tenant_id or 0)
        if row.is_external_unified:
            platform_account = f"外部多成员（成员 {mc}）"
        else:
            platform_account = f"多账号（成员 {mc}）"
    elif row.collect_config_id:
        cfg = ops.get(CollectConfig, row.collect_config_id)
        platform_account = cfg.config_name if cfg else f"config#{row.collect_config_id}"
    elif row.account_id:
        acct = accounts.get(row.account_id) if accounts else ops.get(PlatformAccount, row.account_id)
        if acct:
            platform_account = f"{acct.platform_type} / {acct.account_no or acct.id} {acct.account_name}"
        bind_target = row.account_id

    warning = bind_warning(ops, bind_target or row.account_id)
    return {
        "id": str(row.id),
        "taskName": row.task_name,
        "platformType": row.platform_type,
        "accountId": str(row.account_id) if row.account_id else None,
        "collectConfigId": str(row.collect_config_id) if row.collect_config_id else None,
        "platformAccountLabel": platform_account,
        "method": row.method,
        "frequency": row.frequency,
        "cron": row.cron,
        "status": row.status,
        "isUnified": bool(row.is_unified),
        "isExternalUnified": bool(row.is_external_unified),
        "lastRunAt": row.last_run_at or None,
        "nextRunAt": row.next_run_at or None,
        "successCount": row.success_count,
        "failCount": row.fail_count,
        "memberCount": member_count(ops, row.id, row.tenant_id or 0) if (row.is_unified or row.is_external_unified) else None,
        "bindWarning": warning,
        "healthLabel": account_health_label(ops, row.account_id),
        "statusLabel": TASK_STATUS_LABEL.get(row.status, row.status),
    }


def log_vo(ops: Session, row: CollectLog, tasks: dict[int, CollectTask] | None = None) -> dict:
    task = tasks.get(row.task_id) if tasks else ops.get(CollectTask, row.task_id)
    task_name = task.task_name if task else f"task#{row.task_id}"
    try:
        type_results = json.loads(row.type_results_json or "[]")
    except json.JSONDecodeError:
        type_results = []
    repair_account_id = None
    if row.account_id and (
        (row.error_summary and "未绑定" in row.error_summary) or row.status == "COOKIE_EXPIRED"
    ):
        repair_account_id = str(row.account_id)
    return {
        "id": str(row.id),
        "taskId": str(row.task_id),
        "taskName": task_name,
        "accountId": str(row.account_id) if row.account_id else None,
        "status": row.status,
        "startedAt": row.started_at,
        "durationMs": row.duration_ms,
        "recordCount": row.record_count,
        "retryCount": row.retry_count,
        "retryable": row.status in RETRYABLE_LOG_STATUS,
        "errorSummary": row.error_summary or None,
        "repairAccountId": repair_account_id,
        "statusLabel": {
            "SUCCESS": "成功",
            "FAILED": "失败",
            "PARTIAL": "部分成功",
            "COOKIE_EXPIRED": "Cookie 已失效",
            "ENGINE_UNAVAILABLE": "浏览器引擎不可用",
        }.get(row.status, row.status),
    }


def log_detail_vo(ops: Session, row: CollectLog) -> dict:
    data = log_vo(ops, row)
    try:
        type_results = json.loads(row.type_results_json or "[]")
    except json.JSONDecodeError:
        type_results = []
    data["typeResults"] = type_results
    data["result"] = {"typeResults": type_results}
    return data


def calc_success_rate_24h(ops: Session, tenant_id: int) -> float | None:
    since = (utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    recent = ops.scalars(
        select(CollectLog.status).where(
            CollectLog.tenant_id == tenant_id,
            CollectLog.deleted == 0,
            CollectLog.started_at >= since,
        )
    ).all()
    if not recent:
        return None
    ok_n = sum(1 for s in recent if s == "SUCCESS")
    return round(ok_n * 100.0 / len(recent), 1)


def consecutive_failure_top(ops: Session, tenant_id: int, *, limit: int = 5) -> list[dict]:
    account_ids = ops.scalars(
        select(CollectLog.account_id)
        .where(
            CollectLog.tenant_id == tenant_id,
            CollectLog.deleted == 0,
            CollectLog.account_id.isnot(None),
        )
        .distinct()
    ).all()
    ranked: list[dict] = []
    for account_id in account_ids:
        if not account_id:
            continue
        status_rows = ops.execute(
            select(CollectLog.status, CollectLog.error_summary)
            .where(
                CollectLog.tenant_id == tenant_id,
                CollectLog.deleted == 0,
                CollectLog.account_id == account_id,
            )
            .order_by(CollectLog.id.desc())
            .limit(32)
        ).all()
        streak = 0
        last_error = ""
        for status, err in status_rows:
            if status == "FAILED":
                streak += 1
                if not last_error and err:
                    last_error = err
            else:
                break
        if streak < 1:
            continue
        ranked.append(
            {
                "accountId": str(account_id),
                "accountLabel": account_label(ops, account_id),
                "failStreak": streak,
                "lastError": last_error or None,
            }
        )
    ranked.sort(key=lambda x: x["failStreak"], reverse=True)
    return ranked[:limit]


def validate_task_body(body: TaskBody, ims: Session, *, external: bool = False):
    if not body.taskName.strip():
        return fail(1001, "必填项缺失")
    if body.platformType not in COLLECT_PLATFORMS and body.platformType != "MULTI":
        return fail(1503, "字典枚举非法")
    method = body.method or ("EXTERNAL" if external or body.collectConfigId else "INTERNAL")
    if err := check_enum(ims, "dict_collect_method", method, True):
        return err
    if err := check_enum(ims, "dict_collect_frequency", body.frequency, True):
        return err
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    if method == "EXTERNAL":
        if body.accountId is not None:
            return fail(1001, "外部任务 accountId 必须为 null")
        if not body.collectConfigId:
            return fail(1001, "collect_config_id 必填")
    else:
        if not body.accountId:
            return fail(1001, "单账号任务 accountId 必填")
        if body.collectConfigId:
            return fail(1001, "内部任务不可填 collect_config_id")
    return None


def simulate_run(
    ops: Session,
    task: CollectTask,
    *,
    account_id: int | None = None,
) -> tuple[str, list[dict], int, str, int | None]:
    """Return status, typeResults, record_count, error_summary, log_account_id."""
    target_account = account_id or task.account_id
    if task.method == "EXTERNAL":
        return (
            "SUCCESS",
            [{"dataType": "EXT_KUAISHOU_USER_VIDEOS", "status": "SUCCESS", "recordCount": 8}],
            8,
            "",
            None,
        )
    if not target_account:
        return ("FAILED", [], 0, "任务未绑定账号", None)
    account = ops.get(PlatformAccount, target_account)
    bind = bind_of(ops, target_account)
    summary = bind_summary(account, bind) if account else "未绑定"
    if summary == "未绑定":
        return (
            "FAILED",
            [{"dataType": "VIDEO", "status": "FAILED", "recordCount": 0, "error": "未绑定 Collector"}],
            0,
            "未绑定 Collector（oa_collector_account_bind）",
            target_account,
        )
    if summary == "Cookie 失效":
        return (
            "FAILED",
            [{"dataType": "VIDEO", "status": "FAILED", "recordCount": 0, "errorCode": 1241}],
            0,
            "凭据无效（1241）",
            target_account,
        )
    if task.is_unified:
        members = ops.scalars(
            select(CollectTaskMember).where(
                CollectTaskMember.task_id == task.id,
                CollectTaskMember.deleted == 0,
            )
        ).all()
        results = []
        ok_count = 0
        for member in members:
            acct = ops.get(PlatformAccount, member.account_id or 0)
            b = bind_of(ops, member.account_id)
            st = bind_summary(acct, b) if acct else "未绑定"
            if st == "已绑定":
                results.append({"dataType": "VIDEO", "status": "SUCCESS", "recordCount": 3, "accountId": member.account_id})
                ok_count += 1
            else:
                results.append({"dataType": "VIDEO", "status": "FAILED", "recordCount": 0, "accountId": member.account_id})
        if ok_count == len(results) and results:
            status = "SUCCESS"
        elif ok_count == 0:
            status = "FAILED"
        else:
            status = "PARTIAL"
        err = "" if status == "SUCCESS" else "部分成员未绑定或凭据失效"
        return status, results, sum(r.get("recordCount", 0) for r in results), err, None
    return (
        "SUCCESS",
        [
            {"dataType": "VIDEO", "status": "SUCCESS", "recordCount": 5},
            {"dataType": "FAN", "status": "SUCCESS", "recordCount": 1},
        ],
        6,
        "",
        target_account,
    )


@router.get("/task/page")
def task_page(
    pageNo: int = 1,
    pageSize: int = 10,
    taskName: str = "",
    platformType: str = "",
    method: str = "",
    frequency: str = "",
    status: str = "",
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(CollectTask).where(CollectTask.deleted == 0, CollectTask.tenant_id == tenant_id)
    if taskName.strip():
        stmt = stmt.where(CollectTask.task_name.contains(taskName.strip()))
    if platformType:
        stmt = stmt.where(CollectTask.platform_type == platformType)
    if method:
        stmt = stmt.where(CollectTask.method == method)
    if frequency:
        stmt = stmt.where(CollectTask.frequency == frequency)
    if status:
        stmt = stmt.where(CollectTask.status == status)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(CollectTask.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    account_ids = {row.account_id for row in rows if row.account_id}
    accounts = {}
    if account_ids:
        for acct in ops.scalars(select(PlatformAccount).where(PlatformAccount.id.in_(account_ids))).all():
            accounts[acct.id] = acct
    return paged([task_vo(ops, row, accounts) for row in rows], total, page_no, size)


@router.get("/task/{task_id}")
def task_get(
    task_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    return ok(task_vo(ops, row))


@router.post("/task")
def task_create(
    body: TaskBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    external = body.method == "EXTERNAL" or bool(body.collectConfigId)
    if err := validate_task_body(body, ims, external=external):
        return err
    tenant_id = tenant_of(actor)
    if body.accountId:
        account = ops.get(PlatformAccount, body.accountId)
        if not visible(account, actor):
            return fail(1504, "资源不可用")
        if account.platform_type != body.platformType:
            return fail(1001, "平台与账号不一致")
    if body.collectConfigId:
        cfg = ops.get(CollectConfig, body.collectConfigId)
        if not visible(cfg, actor) or cfg.status != "ENABLED":
            return fail(1500, "外部配置不存在")
    method = body.method or ("EXTERNAL" if body.collectConfigId else "INTERNAL")
    warning = bind_warning(ops, body.accountId)
    source = "API" if method == "INTERNAL" else "EXTERNAL"
    data_type = None
    if method == "INTERNAL" and body.platformType == "KUAISHOU":
        source = "KUAISHOU_OPEN_API"
        data_type = "KUAISHOU_VIDEO_LIST"
    next_run = "" if body.status == "DISABLED" else schedule_next(body.frequency)
    row = CollectTask(
        task_name=body.taskName.strip(),
        platform_type=body.platformType,
        account_id=body.accountId,
        collect_config_id=body.collectConfigId,
        credential_profile=body.credentialProfile or "default",
        method=method,
        source=source,
        data_type=data_type,
        frequency=body.frequency,
        cron=body.cron.strip(),
        status=body.status,
        next_run_at=next_run,
        tenant_id=tenant_id,
    )
    ops.add(row)
    ops.flush()
    data = task_vo(ops, row)
    if warning:
        data["bindWarning"] = warning
    return ok(data)


@router.put("/task/{task_id}")
def task_update(
    task_id: int,
    body: TaskBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.is_unified or row.is_external_unified:
        return fail(1001, "统一任务不可编辑")
    external = body.method == "EXTERNAL" or bool(body.collectConfigId)
    if err := validate_task_body(body, ims, external=external):
        return err
    if body.accountId:
        account = ops.get(PlatformAccount, body.accountId)
        if not visible(account, actor):
            return fail(1504, "资源不可用")
    method = body.method or ("EXTERNAL" if body.collectConfigId else "INTERNAL")
    row.task_name = body.taskName.strip()
    row.platform_type = body.platformType
    row.account_id = body.accountId
    row.collect_config_id = body.collectConfigId
    row.method = method
    row.frequency = body.frequency
    row.cron = body.cron.strip()
    row.status = body.status
    if body.status == "DISABLED":
        row.next_run_at = ""
    elif body.status == "ENABLED" and not row.next_run_at:
        row.next_run_at = schedule_next(row.frequency)
    row.updated_at = utcnow()
    data = task_vo(ops, row)
    warning = bind_warning(ops, row.account_id)
    if warning:
        data["bindWarning"] = warning
    return ok(data)


@router.delete("/task/{task_id}")
def task_delete(
    task_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.is_unified or row.is_external_unified:
        return fail(1001, "统一任务不可删除")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(None)


def _platform_owned(row: CollectTask) -> bool:
    """C1–C5 内部作品任务由平台定时器执行，本地桩调度不再重复跑。"""
    from app.internal_collect import profiles

    owned = {item.source for item in profiles()}
    return (
        row.method == "INTERNAL"
        and not row.collect_config_id
        and not row.is_external_unified
        and (row.source or "") in owned
    )


def perform_task_run(ops: Session, row: CollectTask) -> dict:
    if (
        row.platform_type == "KUAISHOU"
        and row.method != "EXTERNAL"
        and not row.collect_config_id
        and not row.is_external_unified
    ):
        from app.kuaishou_collect import execute_kuaishou_task

        return execute_kuaishou_task(ops, row)
    # 抖音采集页创建的内部作品任务走 Collector。任务页 / 统一任务 / 外部任务仍走 simulate_run。
    if (
        row.platform_type == "DOUYIN"
        and (row.source or "") == "DOUYIN_OPEN_API"
        and row.method != "EXTERNAL"
        and not row.collect_config_id
        and not row.is_external_unified
    ):
        from app.douyin_collect import execute_douyin_task

        return execute_douyin_task(ops, row)
    # 视频号采集页创建的内部作品任务走 Collector。任务页 / 统一任务 / 外部任务仍走 simulate_run。
    if (
        row.platform_type == "WECHAT_CHANNELS"
        and (row.source or "") == "WECHAT_CHANNELS_API"
        and row.method != "EXTERNAL"
        and not row.collect_config_id
        and not row.is_external_unified
    ):
        from app.wechat_channels_collect import execute_wechat_channels_task

        return execute_wechat_channels_task(ops, row)
    from app.internal_collect import retry_count_for_run

    started = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status, type_results, record_count, error_summary, log_account = simulate_run(ops, row)
    retries = retry_count_for_run(ops, row.id)
    duration_ms = 8200 if status == "FAILED" else 45000
    log = CollectLog(
        task_id=row.id,
        account_id=log_account or row.account_id,
        status=status,
        started_at=started,
        duration_ms=duration_ms,
        record_count=record_count,
        retry_count=retries,
        error_summary=error_summary,
        type_results_json=json.dumps(type_results, ensure_ascii=False),
        tenant_id=row.tenant_id or 0,
    )
    ops.add(log)
    row.last_run_at = started
    if status == "SUCCESS":
        row.success_count += 1
    else:
        row.fail_count += 1
    if row.status == "ENABLED":
        row.next_run_at = schedule_next(row.frequency)
    row.updated_at = utcnow()
    ops.flush()
    return {"logId": str(log.id), "taskId": str(row.id), "status": status, "retryCount": retries}


def tick_local_tasks(now=None) -> int:
    """到期的任务页 / 外部桩任务。平台 source 仍交给 C1–C5 定时器。"""
    from app.ops_db import ops_session

    stamp = (now or utcnow()).strftime("%Y-%m-%d %H:%M:%S")
    ops = ops_session()
    ran = 0
    try:
        due = ops.scalars(
            select(CollectTask).where(
                CollectTask.deleted == 0,
                CollectTask.status == "ENABLED",
                CollectTask.next_run_at != "",
                CollectTask.next_run_at <= stamp,
            )
        ).all()
        ids = [row.id for row in due if not _platform_owned(row)]
        for task_id in ids:
            task = ops.get(CollectTask, task_id)
            if task is None or task.deleted or task.status != "ENABLED":
                continue
            if not task.next_run_at or task.next_run_at > stamp:
                continue
            try:
                perform_task_run(ops, task)
                ops.commit()
                ran += 1
            except Exception:
                ops.rollback()
        return ran
    except Exception:
        ops.rollback()
        raise
    finally:
        ops.close()


@router.post("/task/{task_id}/start")
def task_start(
    task_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.status == "DISABLED":
        row.status = "ENABLED"
        row.next_run_at = schedule_next(row.frequency)
        row.updated_at = utcnow()
    elif not row.next_run_at:
        row.next_run_at = schedule_next(row.frequency)
        row.updated_at = utcnow()
    return ok(task_vo(ops, row))


@router.post("/task/{task_id}/stop")
def task_stop(
    task_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    row.status = "DISABLED"
    row.next_run_at = ""
    row.updated_at = utcnow()
    return ok(task_vo(ops, row))


@router.post("/task/{task_id}/run")
def task_run(
    task_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, task_id)
    if row is None:
        return fail(1504, "资源不可用")
    if row.status == "DISABLED":
        return fail(1001, "任务已停用")
    try:
        return ok(perform_task_run(ops, row))
    except Exception:
        return fail(2022, "采集失败")


@router.post("/task/ensure-unified")
def ensure_unified(
    body: EnsureUnifiedBody | None = None,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    platform = (body.platformType if body else None) or "DOUYIN"
    existing = ops.scalar(
        select(CollectTask).where(
            CollectTask.tenant_id == tenant_id,
            CollectTask.deleted == 0,
            CollectTask.is_unified == 1,
            CollectTask.platform_type == platform,
        )
    )
    if existing is None:
        existing = CollectTask(
            task_name=f"{platform} 统一 nightly",
            platform_type=platform,
            method="INTERNAL",
            source="API",
            frequency="DAILY",
            cron=UNIFIED_CRON,
            status="ENABLED",
            is_unified=1,
            next_run_at=schedule_next("DAILY"),
            tenant_id=tenant_id,
        )
        ops.add(existing)
        ops.flush()
    bound_accounts = ops.scalars(
        select(PlatformAccount).where(
            PlatformAccount.tenant_id == tenant_id,
            PlatformAccount.deleted == 0,
            PlatformAccount.platform_type == platform,
        )
    ).all()
    for acct in bound_accounts:
        bind = bind_of(ops, acct.id)
        if bind_summary(acct, bind) != "已绑定":
            continue
        found = ops.scalar(
            select(CollectTaskMember.id).where(
                CollectTaskMember.task_id == existing.id,
                CollectTaskMember.account_id == acct.id,
                CollectTaskMember.deleted == 0,
            )
        )
        if found is None:
            ops.add(
                CollectTaskMember(
                    task_id=existing.id,
                    account_id=acct.id,
                    tenant_id=tenant_id,
                )
            )
    ops.flush()
    return ok(task_vo(ops, existing))


@router.post("/task/ensure-external-unified")
def ensure_external_unified(
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    existing = ops.scalar(
        select(CollectTask).where(
            CollectTask.tenant_id == tenant_id,
            CollectTask.deleted == 0,
            CollectTask.is_external_unified == 1,
        )
    )
    if existing is None:
        existing = CollectTask(
            task_name="外部竞品统一任务",
            platform_type="MULTI",
            method="EXTERNAL",
            source="EXTERNAL",
            frequency="DAILY",
            cron=EXT_UNIFIED_CRON,
            status="ENABLED",
            is_external_unified=1,
            next_run_at=schedule_next("DAILY"),
            tenant_id=tenant_id,
        )
        ops.add(existing)
        ops.flush()
    configs = ops.scalars(
        select(CollectConfig).where(
            CollectConfig.tenant_id == tenant_id,
            CollectConfig.deleted == 0,
            CollectConfig.scope == "EXTERNAL",
            CollectConfig.status == "ENABLED",
        )
    ).all()
    for cfg in configs:
        found = ops.scalar(
            select(CollectTaskMember.id).where(
                CollectTaskMember.task_id == existing.id,
                CollectTaskMember.collect_config_id == cfg.id,
                CollectTaskMember.deleted == 0,
            )
        )
        if found is None:
            ops.add(
                CollectTaskMember(
                    task_id=existing.id,
                    collect_config_id=cfg.id,
                    tenant_id=tenant_id,
                )
            )
    ops.flush()
    return ok(task_vo(ops, existing))


@router.get("/quality/summary")
def quality_summary(
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    top = consecutive_failure_top(ops, tenant_id)
    return ok(
        {
            "successRate24h": calc_success_rate_24h(ops, tenant_id),
            "consecutiveFailureAccountCount": len(top),
            "consecutiveFailureTop": top,
        }
    )


@router.post("/manual-fill")
def manual_fill(
    body: ManualFillBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_task(ops, actor, body.taskId)
    if row is None:
        return fail(1504, "资源不可用")
    account_id = body.accountId if body.accountId is not None else row.account_id
    if account_id is None:
        return fail(1001, "accountId 必填")
    if body.recordCount < 1:
        return fail(1001, "recordCount 须 ≥ 1")
    started = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    data_type = (body.dataType or "WORK").strip().upper()
    type_results = [
        {
            "dataType": data_type,
            "status": "SUCCESS",
            "recordCount": body.recordCount,
            "source": "MANUAL_FILL",
            "remark": body.remark or None,
        }
    ]
    log = CollectLog(
        task_id=row.id,
        account_id=account_id,
        status="SUCCESS",
        started_at=started,
        duration_ms=1200,
        record_count=body.recordCount,
        retry_count=0,
        error_summary="",
        type_results_json=json.dumps(type_results, ensure_ascii=False),
        tenant_id=tenant_of(actor),
    )
    ops.add(log)
    row.last_run_at = started
    row.success_count += 1
    row.updated_at = utcnow()
    ops.flush()
    return ok({"logId": str(log.id), "taskId": str(row.id), "status": "SUCCESS"})


@router.get("/log/page")
def log_page(
    pageNo: int = 1,
    pageSize: int = 10,
    taskId: int | None = None,
    accountId: int | None = None,
    status: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(CollectLog).where(CollectLog.deleted == 0, CollectLog.tenant_id == tenant_id)
    if taskId:
        stmt = stmt.where(CollectLog.task_id == taskId)
    if accountId:
        stmt = stmt.where(CollectLog.account_id == accountId)
    if status:
        stmt = stmt.where(CollectLog.status == status)
    if dateFrom:
        stmt = stmt.where(CollectLog.started_at >= dateFrom)
    if dateTo:
        stmt = stmt.where(CollectLog.started_at <= dateTo + " 23:59:59")
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(CollectLog.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    task_ids = {row.task_id for row in rows}
    tasks = {}
    if task_ids:
        for task in ops.scalars(select(CollectTask).where(CollectTask.id.in_(task_ids))).all():
            tasks[task.id] = task
    rate_24h = calc_success_rate_24h(ops, tenant_id)
    resp = paged([log_vo(ops, row, tasks) for row in rows], total, page_no, size)
    resp["data"]["successRate24h"] = rate_24h
    return resp


@router.get("/log/{log_id}")
def log_get(
    log_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectLog, log_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    return ok(log_detail_vo(ops, row))


from app.kuaishou_collect import router as kuaishou_collect_router  # noqa: E402
from app.douyin_collect import router as douyin_collect_router  # noqa: E402
from app.wechat_channels_collect import router as wechat_channels_collect_router  # noqa: E402

router.include_router(kuaishou_collect_router)
router.include_router(douyin_collect_router)
router.include_router(wechat_channels_collect_router)
