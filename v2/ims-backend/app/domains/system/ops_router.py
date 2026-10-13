"""巡检、任务、日历。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.services import attendance, integrity
from app.services.jobs import run_job

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


@mark(perm="ims:system:integrity:run", summary="执行引用巡检")
def integrity_run():
    body = _body()
    tenant = body.get("tenantId")
    return integrity.run_scan(int(tenant) if tenant not in (None, "") else None, body.get("tables"))


_JOB_LABELS = {
    "asset_verify_full": "资产校验全量",
    "asset_verify_increment": "资产校验增量",
    "asset_verify_overdue": "资产校验逾期扫描",
    "account_apply_idle_remind": "领用后长期未使用",
    "account_return_overdue": "归还逾期",
}


@mark(perm="ims:system:job:query", summary="定时任务列表")
def job_page():
    from app.services.jobs import JOBS

    return {
        "list": [{"name": item.name, "cron": item.cron, "label": _JOB_LABELS.get(item.name, item.name)} for item in JOBS],
        "total": len(JOBS),
    }


@mark(perm="ims:system:job:run", operate=("任务", "手动执行"), summary="手动执行任务")
def job_run():
    body = _body()
    return run_job(body.get("name") or "", "手动")


@mark(perm="ims:system:calendar:update", operate=("日历", "修改日历"), summary="修改工作日历")
def calendar_update():
    body = _body()
    return attendance.update_calendar(body.get("date") or "", body.get("dayType") or "")


router.post("/integrity-scan/run", summary="执行引用巡检")(integrity_run)
router.get("/job/page", summary="定时任务列表")(job_page)
router.post("/job/run", summary="手动执行任务")(job_run)
router.put("/calendar/update", summary="修改工作日历")(calendar_update)
