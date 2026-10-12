"""示例域接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.clock import parse_input_datetime
from app.core.errors import BizError
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id, parse_date, parse_money, parse_percent
from app.domains.demo import service
from app.domains.demo.model import DemoOrder

router = APIRouter()


def _body() -> dict:
    request = current_request()
    return getattr(request.state, "json_body", None) or {}


def _take(body, key, parser, field):
    if key not in body or body[key] in (None, ""):
        return None
    try:
        return parser(body[key])
    except BizError as exc:
        errors = (exc.data or {}).get("fieldErrors") or [{"field": field, "message": exc.msg}]
        for item in errors:
            item["field"] = field
        raise BizError(1001, data={"fieldErrors": errors})


@mark(perm="ims:demo:order:query", scope_model=DemoOrder, summary="示例订单分页")
def order_page():
    request = current_request()
    page = parse_page(dict(request.query_params), ["createTime", "amount"])
    return service.page_orders(page)


@mark(perm="ims:demo:order:query", scope_model=DemoOrder, summary="示例订单详情")
def order_get():
    return service.get_order(int(parse_api_id(current_request().query_params.get("id"))))


@mark(perm="ims:demo:order:create", scope_model=DemoOrder, operate=("示例", "新建订单"), idempotent=False, summary="新建示例订单")
def order_create():
    body = _body()
    errors = []
    if not body.get("name"):
        errors.append({"field": "name", "message": "不能为空"})
    payload = {"name": body.get("name")}
    for key, parser, field in (
        ("amount", parse_money, "amount"),
        ("rate", parse_percent, "rate"),
        ("ownerUserId", parse_api_id, "ownerUserId"),
        ("deptId", parse_api_id, "deptId"),
        ("ipGroupId", parse_api_id, "ipGroupId"),
        ("realnameId", parse_api_id, "realnameId"),
        ("id", parse_api_id, "id"),
        ("cost", parse_money, "cost"),
    ):
        if key in body and body[key] not in (None, ""):
            try:
                payload[key] = parser(body[key])
            except BizError as exc:
                found = (exc.data or {}).get("fieldErrors") or [{"field": field, "message": exc.msg}]
                for item in found:
                    item["field"] = field
                errors.extend(found)
    if "bizTime" in body and body["bizTime"]:
        try:
            payload["bizTime"] = parse_input_datetime(str(body["bizTime"]))
        except ValueError:
            errors.append({"field": "bizTime", "message": "时间格式不正确"})
    if "bizDate" in body and body["bizDate"]:
        try:
            payload["bizDate"] = parse_date(body["bizDate"])
        except BizError:
            errors.append({"field": "bizDate", "message": "日期格式须为年-月-日"})
    for key in ("code", "status", "idCard", "mobile", "testDelayMs"):
        if key in body:
            payload[key] = body[key]
    if errors:
        raise BizError(1001, data={"fieldErrors": errors})
    return service.create_order(payload)


@mark(perm="ims:demo:order:update", scope_model=DemoOrder, operate=("示例", "修改订单"), summary="修改示例订单")
def order_update():
    body = _body()
    payload = {"id": int(parse_api_id(body.get("id")))}
    if "amount" in body:
        payload["amount"] = parse_money(body["amount"])
    if "name" in body:
        payload["name"] = body["name"]
    if "mobile" in body:
        payload["mobile"] = body["mobile"]
    if "status" in body:
        payload["status"] = body["status"]
    if "ownerUserId" in body:
        payload["ownerUserId"] = parse_api_id(body["ownerUserId"])
    if "code" in body:
        payload["code"] = body["code"]
    return service.update_order(payload)


@mark(perm="ims:demo:order:delete", scope_model=DemoOrder, operate=("示例", "删除订单"), summary="删除示例订单")
def order_delete():
    return service.delete_order(int(parse_api_id(current_request().query_params.get("id") or _body().get("id"))))


@mark(perm="ims:demo:order:plain", sensitive_view=True, returns_plain=True, scope_model=DemoOrder, summary="查看证件原件")
def order_plain():
    return service.plain_order(int(parse_api_id(current_request().query_params.get("id"))))


@mark(perm="ims:demo:order:create", idempotent=True, operate=("示例", "幂等提交"), summary="幂等示例")
def order_echo():
    body = _body()
    payload = {"name": body.get("name") or "echo", "code": body.get("code"), "realnameId": body.get("realnameId")}
    if body.get("realnameId"):
        payload["realnameId"] = int(body["realnameId"])
    if body.get("testDelayMs"):
        payload["testDelayMs"] = body["testDelayMs"]
    return service.create_order(payload)


@mark(perm="ims:demo:order:query", summary="示例分享列表")
def share_page():
    return service.page_shares()


@mark(perm="ims:demo:order:import", summary="导入示例订单")
def order_import():
    body = _body()
    from app.services.exchange import import_orders

    return import_orders(body.get("rows") or [], body.get("mode") or "ALL_OR_NOTHING")


@mark(perm="ims:demo:order:export", summary="导出示例订单")
def order_export():
    from app.services.exchange import run_export, start_export

    task = start_export(_body())
    return run_export(int(task["id"]))


@mark(perm="ims:demo:order:create", summary="发布示例分享")
def share_create():
    body = _body()
    return service.create_share(body.get("name") or "", body.get("deptId"))


router.get("/order/page", summary="示例订单分页")(order_page)
router.get("/order/get", summary="示例订单详情")(order_get)
router.post("/order/create", summary="新建示例订单")(order_create)
router.put("/order/update", summary="修改示例订单")(order_update)
router.delete("/order/delete", summary="删除示例订单")(order_delete)
router.get("/order/plain", summary="查看证件原件")(order_plain)
router.post("/order/echo", summary="幂等示例")(order_echo)
router.get("/share/page", summary="示例分享列表")(share_page)
router.post("/share/create", summary="发布示例分享")(share_create)
router.post("/order/import", summary="导入示例订单")(order_import)
router.post("/order/export", summary="导出示例订单")(order_export)
