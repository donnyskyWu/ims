"""工作台聚合接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.domains.workbench import service

router = APIRouter()


@mark(login_only=True, summary="工作台首页")
def workbench_dashboard():
    return service.dashboard()


router.get("/dashboard", summary="工作台首页")(workbench_dashboard)
