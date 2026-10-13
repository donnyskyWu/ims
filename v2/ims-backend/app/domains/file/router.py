"""文件上传、下载与预览。"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.context import get_ctx
from app.domains.file import service

router = APIRouter()


def _q(name, default=None):
    request = current_request()
    if request is None:
        return default
    return request.query_params.get(name, default)


@mark(perm="ims:file:upload", summary="上传文件")
def file_upload(scene: str = Form(...), file: UploadFile = File(...)):
    ctx = get_ctx()
    payload = file.file.read()
    return service.upload(scene, file.filename or "", payload, ctx.user_id if ctx else 0)


# 与资产导入相同：签名跟着 __wrapped__，字符串 UploadFile 解析失败会被当成响应字段。
file_upload.__wrapped__.__annotations__["file"] = UploadFile


@mark(perm="ims:file:query", summary="下载文件")
def file_download():
    return service.download(_q("fileKey") or "")


@mark(perm="ims:file:query", summary="预览文件")
def file_preview():
    return service.preview(_q("fileKey") or "")


router.post("/upload", summary="上传文件")(file_upload)
router.get("/download", summary="下载文件")(file_download)
router.get("/preview", summary="预览文件")(file_preview)
