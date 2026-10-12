"""我的导出任务。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.services import exchange

router = APIRouter()


@mark(perm="ims:demo:order:export", summary="我的导出任务")
def export_my_page():
    return exchange.my_exports()


@mark(perm="ims:demo:order:export", summary="下载导出文件")
def export_download():
    request = current_request()
    return {"content": exchange.export_body(int(request.query_params.get("id") or 0))}


router.get("/my/page", summary="我的导出任务")(export_my_page)
router.get("/download", summary="下载导出文件")(export_download)
