"""证件档案、到期预警与分级审计。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.cert import archive, expire, security

router = APIRouter()

_READ = ("ims:cert:archive:query", "ims:cert:expire:query", "ims:cert:archive:review")


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


def _params() -> dict:
    return dict(current_request().query_params)


def _page():
    params = _params()
    if not params.get("pageSize"):
        params["pageSize"] = 20
    return parse_page(params)


def _id(ident: str) -> int:
    return int(parse_api_id(ident))


@mark(perm="ims:cert:archive:upload", summary="上传证件档案", operate=("证件", "上传"))
def archive_upload():
    return archive.upload(_body())


@mark(perm="ims:cert:archive:query", summary="证件档案列表")
def archive_list():
    return archive.page(_page(), _params())


@mark(perm="ims:cert:archive:metrics", summary="证件数字化率")
def archive_metrics():
    return archive.metrics()


@mark(perm="ims:cert:archive:query", summary="证件档案详情")
def archive_detail(ident: str):
    return archive.detail(_id(ident))


@mark(perm="ims:cert:archive:review", summary="审核证件档案", operate=("证件", "审核"))
def archive_review(ident: str):
    return archive.review(_id(ident), _body())


@mark(perm="ims:cert:archive:query", any_perm=_READ, summary="证件水印地址")
def archive_file_url(ident: str):
    return security.file_url(_id(ident), _params())


@mark(perm="ims:cert:expire:query", summary="证件预警列表")
def expire_list():
    return expire.page(_page(), _params())


@mark(perm="ims:cert:expire:query", summary="证件预警看板")
def expire_stats():
    return expire.stats()


@mark(perm="ims:cert:expire:scan", summary="手动扫描证件到期", operate=("证件", "扫描"))
def expire_scan():
    return expire.manual_scan()


@mark(perm="ims:cert:expire:renew", summary="证件换证", operate=("证件", "换证"))
def expire_renew(ident: str):
    return expire.renew(_id(ident), _body())


@mark(perm="ims:cert:expire:remind", summary="证件催办", operate=("证件", "催办"))
def expire_remind(ident: str):
    return expire.remind(_id(ident), _body())


@mark(perm="ims:cert:archive:query", any_perm=_READ, summary="分级查看证件")
def security_view(cert_id: str):
    return security.open_view(_id(cert_id), _params())


@mark(perm="ims:cert:security:config", summary="读取证件级别配置")
def level_get():
    return security.get_config()


@mark(perm="ims:cert:security:config", summary="保存证件级别配置", operate=("证件", "分级"))
def level_save():
    return security.save_config(_body())


@mark(perm="ims:cert:security:log", summary="证件查看日志")
def view_logs():
    return security.view_logs(_page(), _params())


@mark(perm="ims:cert:security:log", summary="证件异常访问报告", operate=("证件", "异常报告"))
def risk_report():
    return security.risk_report(_params())


router.post("/archive/upload", summary="上传证件档案")(archive_upload)
router.get("/archive/list", summary="证件档案列表")(archive_list)
router.get("/archive/digital-metrics", summary="证件数字化率")(archive_metrics)
router.get("/archive/{ident}", summary="证件档案详情")(archive_detail)
router.put("/archive/{ident}/review", summary="审核证件档案")(archive_review)
router.get("/archive/{ident}/file-url", summary="证件水印地址")(archive_file_url)
router.get("/expire/list", summary="证件预警列表")(expire_list)
router.get("/expire/stats", summary="证件预警看板")(expire_stats)
router.post("/expire/scan", summary="手动扫描证件到期")(expire_scan)
router.put("/expire/{ident}/renew", summary="证件换证")(expire_renew)
router.put("/expire/{ident}/remind", summary="证件催办")(expire_remind)
router.get("/security/view/{cert_id}", summary="分级查看证件")(security_view)
router.get("/security/level-config", summary="读取证件级别配置")(level_get)
router.put("/security/level-config", summary="保存证件级别配置")(level_save)
router.get("/security/view-logs", summary="证件查看日志")(view_logs)
router.get("/security/risk-report", summary="证件异常访问报告")(risk_report)
