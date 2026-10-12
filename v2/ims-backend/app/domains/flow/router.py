"""流程模板与办理。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.domains.flow import service

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


@mark(perm="ims:flow:manage", summary="发布流程模板")
def flow_template():
    body = _body()
    if body.get("versionId"):
        return service.edit_nodes(int(body["versionId"]), body.get("nodes") or [])
    return service.publish_template(body.get("code") or "", body.get("name") or "", body.get("nodes") or [], body.get("bizType") or "")


@mark(perm="ims:flow:start", summary="发起流程")
def flow_start():
    body = _body()
    return service.start(body.get("code") or "", body.get("bizType") or "", int(body.get("bizId") or 0))


@mark(perm="ims:flow:act", summary="办理流程")
def flow_act():
    body = _body()
    return service.act(int(body["instanceId"]), body.get("action") or "", body.get("comment"))


@mark(perm="ims:flow:cancel", summary="撤销流程")
def flow_cancel():
    return service.cancel(int(_body()["instanceId"]))


router.post("/template", summary="发布流程模板")(flow_template)
router.post("/start", summary="发起流程")(flow_start)
router.post("/act", summary="办理流程")(flow_act)
router.post("/cancel", summary="撤销流程")(flow_cancel)
