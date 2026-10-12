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


@mark(perm="ims:system:job:run", operate=("任务", "手动执行"), summary="手动执行任务")
def job_run():
    body = _body()
    return run_job(body.get("name") or "", "手动")


@mark(perm="ims:system:calendar:update", operate=("日历", "修改日历"), summary="修改工作日历")
def calendar_update():
    body = _body()
    return attendance.update_calendar(body.get("date") or "", body.get("dayType") or "")


router.post("/integrity-scan/run", summary="执行引用巡检")(integrity_run)
router.post("/job/run", summary="手动执行任务")(job_run)
router.put("/calendar/update", summary="修改工作日历")(calendar_update)
