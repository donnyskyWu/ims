"""流程模板与办理。B0a 四个入口保留；B4 按 FLOW 契约追加。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.flow import contract, service

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


def _params() -> dict:
    return dict(current_request().query_params)


def _page(default_size: int = 20) -> object:
    params = _params()
    if not params.get("pageSize"):
        params["pageSize"] = default_size
    return parse_page(params)


def _b4_create(body: dict) -> bool:
    return "templateName" in body or "businessDomain" in body


@mark(perm="ims:flow:manage", any_perm=("ims:flow:template:create",), summary="发布流程模板")
def flow_template():
    body = _body()
    ctx = get_ctx()
    perms = set(ctx.perm_codes or []) if ctx else set()
    if _b4_create(body):
        if ctx and not getattr(ctx, "system", False) and not ({"ims:flow:manage", "ims:flow:template:create"} & perms):
            raise BizError(1008)
        return contract.create_template(body)
    if ctx and not getattr(ctx, "system", False) and "ims:flow:manage" not in perms:
        raise BizError(1008)
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


@mark(perm="ims:flow:template:query", summary="模板列表")
def template_list():
    params = _params()
    return contract.list_templates(_page(), params.get("templateName"), params.get("businessDomain"), params.get("status"))


@mark(perm="ims:flow:template:create", summary="编辑草稿模板")
def template_update(ident: str):
    return contract.update_template(int(ident), _body())


@mark(perm="ims:flow:template:publish", summary="发布模板")
def template_publish(ident: str):
    return contract.publish_template(int(ident))


@mark(perm="ims:flow:template:publish", summary="停用模板")
def template_disable(ident: str):
    return contract.disable_template(int(ident))


@mark(perm="ims:flow:template:delete", summary="删除草稿模板")
def template_delete(ident: str):
    return contract.delete_template(int(ident))


@mark(perm="ims:flow:template:create", summary="复制为新版本草稿")
def template_revise(ident: str):
    return contract.revise_template(int(ident))


@mark(perm="ims:flow:template:query", summary="预览流程图")
def template_preview(ident: str):
    version = _params().get("version")
    return contract.preview_template(int(ident), int(version) if version else None)


@mark(login_only=True, summary="发起流程实例")
def instance_start():
    return contract.start_instance(_body())


@mark(login_only=True, summary="我的待办")
def task_todo():
    return contract.my_todo(_page(), _params().get("businessDomain"))


@mark(login_only=True, summary="我发起的")
def task_initiated():
    return contract.my_initiated(_page(), _params().get("instanceStatus"))


@mark(login_only=True, summary="我已处理")
def task_handled():
    return contract.my_handled(_page(), _params().get("taskStatus"))


@mark(login_only=True, summary="待办角标")
def task_badge():
    return contract.todo_badge()


@mark(perm="ims:flow:task:handle", any_perm=("ims:flow:act",), summary="处理任务")
def task_handle(ident: str):
    return contract.handle_task(int(ident), _body())


@mark(perm="ims:flow:task:handle", any_perm=("ims:flow:act",), summary="转交任务")
def task_transfer(ident: str):
    return contract.transfer_task(int(ident), _body())


@mark(login_only=True, summary="流程看板")
def instance_board():
    params = _params()
    raw = params.get("dateRange") or ""
    start, end = params.get("dateFrom"), params.get("dateTo")
    if raw and "," in raw:
        start, end = raw.split(",", 1)
    return contract.board(params.get("businessDomain"), start, end)


@mark(login_only=True, summary="实例详情")
def instance_detail(instance_no: str):
    return contract.instance_detail(instance_no)


@mark(login_only=True, summary="撤销实例")
def instance_revoke(instance_no: str):
    return contract.revoke(instance_no)


@mark(perm="ims:flow:template:query", summary="版本列表")
def version_list():
    template_id = parse_api_id(_params().get("templateId"))
    if template_id is None:
        raise BizError(1001, data={"fieldErrors": [{"field": "templateId", "message": "请选择模板"}]})
    return contract.version_list(int(template_id))


@mark(perm="ims:flow:template:query", summary="版本对比")
def version_diff():
    params = _params()
    return contract.version_diff(int(parse_api_id(params.get("templateId"))), int(params.get("fromVersion")), int(params.get("toVersion")))


@mark(perm="ims:flow:version:rollback", summary="版本回滚")
def version_rollback(template_id: str):
    return contract.rollback(int(template_id), _body())


@mark(perm="ims:flow:template:query", summary="版本快照")
def version_snapshot():
    params = _params()
    return contract.version_snapshot(int(parse_api_id(params.get("templateId"))), int(params.get("version")))


@mark(login_only=True, summary="超时清单")
def timeout_list():
    params = _params()
    assignee = parse_api_id(params.get("assigneeUserId")) if params.get("assigneeUserId") else None
    return contract.timeout_list(_page(), params.get("businessDomain"), assignee, params.get("templateName"))


@mark(perm="ims:flow:timeout:query", summary="超时率")
def timeout_rate():
    return contract.timeout_rate(_params().get("statMonth"))


@mark(perm="ims:flow:timeout:query", summary="超时分布")
def timeout_distribution():
    params = _params()
    return contract.timeout_distribution(params.get("statMonth"), params.get("dimension") or "")


@mark(perm="ims:flow:timeout:urge", summary="手动督办")
def timeout_urge(ident: str):
    return contract.urge(int(ident), _body())


router.post("/template", summary="发布流程模板")(flow_template)
router.post("/start", summary="发起流程")(flow_start)
router.post("/act", summary="办理流程")(flow_act)
router.post("/cancel", summary="撤销流程")(flow_cancel)
router.get("/template/list", summary="模板列表")(template_list)
router.put("/template/{ident}", summary="编辑草稿模板")(template_update)
router.post("/template/{ident}/publish", summary="发布模板")(template_publish)
router.post("/template/{ident}/disable", summary="停用模板")(template_disable)
router.delete("/template/{ident}", summary="删除草稿模板")(template_delete)
router.post("/template/{ident}/revise", summary="复制为新版本草稿")(template_revise)
router.get("/template/{ident}/preview", summary="预览流程图")(template_preview)
router.post("/instance", summary="发起流程实例")(instance_start)
router.get("/task/my-todo", summary="我的待办")(task_todo)
router.get("/task/my-initiated", summary="我发起的")(task_initiated)
router.get("/task/my-handled", summary="我已处理")(task_handled)
router.get("/task/badge", summary="待办角标")(task_badge)
router.put("/task/{ident}/handle", summary="处理任务")(task_handle)
router.put("/task/{ident}/transfer", summary="转交任务")(task_transfer)
router.get("/instance/board", summary="流程看板")(instance_board)
router.get("/instance/{instance_no}", summary="实例详情")(instance_detail)
router.put("/instance/{instance_no}/revoke", summary="撤销实例")(instance_revoke)
router.get("/version/list", summary="版本列表")(version_list)
router.get("/version/diff", summary="版本对比")(version_diff)
router.post("/version/{template_id}/rollback", summary="版本回滚")(version_rollback)
router.get("/version/snapshot", summary="版本快照")(version_snapshot)
router.get("/timeout/list", summary="超时清单")(timeout_list)
router.get("/timeout/rate", summary="超时率")(timeout_rate)
router.get("/timeout/distribution", summary="超时分布")(timeout_distribution)
router.put("/timeout/{ident}/urge", summary="手动督办")(timeout_urge)
