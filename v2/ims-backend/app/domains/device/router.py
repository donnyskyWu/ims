"""设备与资产。静态路径写在编号路径前面。"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.device import flow, forward, ledger, phone, reverse, verify

router = APIRouter()


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


@mark(perm="ims:device:phone:query", summary="手机列表")
def phone_page():
    return phone.page(_page(), _params())


@mark(perm="ims:device:phone:export", summary="导出手机", operate=("手机设备", "导出"))
def phone_export():
    return phone.export(_params())


@mark(perm="ims:device:phone:create", idempotent=True, summary="登记手机", operate=("手机设备", "登记"))
def phone_create():
    return phone.create(_body())


@mark(perm="ims:device:phone:query", summary="手机详情")
def phone_detail(ident: str):
    return phone.detail(_id(ident))


@mark(perm="ims:device:phone:update", summary="编辑手机", operate=("手机设备", "编辑"))
def phone_update(ident: str):
    return phone.update(_id(ident), _body())


@mark(perm="ims:device:phone:update", summary="手机状态", operate=("手机设备", "状态"))
def phone_status(ident: str):
    return phone.set_status(_id(ident), _body())


@mark(perm="ims:device:phone:delete", summary="删除手机", operate=("手机设备", "删除"))
def phone_delete(ident: str):
    return phone.remove(_id(ident))


@mark(perm="ims:device:phone:bind-sim", summary="绑定手机卡", operate=("手机设备", "绑卡"))
def phone_bind(ident: str):
    return phone.bind_sims(_id(ident), _body())


@mark(perm="ims:device:asset:query", summary="办公设备列表")
def office_page():
    return ledger.page(_page(), _params(), "office")


@mark(perm="ims:device:asset:query", summary="直播设备列表")
def live_page():
    return ledger.page(_page(), _params(), "live")


@mark(perm="ims:device:asset:import", summary="采购导入", operate=("资产", "采购导入"))
def ledger_import(file: UploadFile = File(...), scope: str = Form("office")):
    return ledger.import_csv(file.file.read(), file.filename or "", scope or "office")


# future 注解经 @mark 包装后，FastAPI 按包装函数的全局名解析，UploadFile 会变成未解析 ForwardRef，
# 并被当成响应字段而无法启动。签名跟着 __wrapped__，所以把真实类型写回原函数，只作为 File 参数。
ledger_import.__wrapped__.__annotations__["file"] = UploadFile


@mark(perm="ims:device:asset:export", summary="导出台账", operate=("资产", "导出"))
def ledger_export():
    return ledger.export(_params())


@mark(perm="ims:device:asset:create", idempotent=True, summary="资产登记", operate=("资产", "登记"))
def ledger_create():
    return ledger.create(_body())


@mark(perm="ims:device:asset:query", summary="资产详情")
def ledger_detail(ident: str):
    return ledger.detail(_id(ident))


@mark(perm="ims:device:asset:update", summary="编辑资产", operate=("资产", "编辑"))
def ledger_update(ident: str):
    return ledger.update(_id(ident), _body())


@mark(perm="ims:device:asset:delete", summary="删除资产", operate=("资产", "删除"))
def ledger_delete(ident: str):
    return ledger.remove(_id(ident))


@mark(perm="ims:device:asset:lifecycle", summary="领用资产", operate=("资产", "领用"))
def ledger_checkout(ident: str):
    return flow.checkout(_id(ident), _body())


@mark(perm="ims:device:asset:lifecycle", summary="流转资产", operate=("资产", "流转"))
def ledger_transfer(ident: str):
    return flow.transfer(_id(ident), _body())


@mark(perm="ims:device:asset:lifecycle", summary="归还资产", operate=("资产", "归还"))
def ledger_return(ident: str):
    return flow.give_back(_id(ident), _body())


@mark(perm="ims:device:asset:lifecycle", summary="报废资产", operate=("资产", "报废"))
def ledger_scrap(ident: str):
    return flow.scrap(_id(ident), _body())


@mark(perm="ims:device:asset:lifecycle", summary="标记资产状态", operate=("资产", "标记状态"))
def ledger_status(ident: str):
    return flow.mark_status(_id(ident), _body())


@mark(perm="ims:device:asset:query", summary="资产时间线")
def ledger_timeline(ident: str):
    return flow.events(_id(ident))


@mark(perm="ims:asset:forward:query", summary="分层穿透", operate=("资产穿透", "查询"))
def forward_detail(asset_id: str):
    return forward.detail(_id(asset_id), _params())


@mark(perm="ims:asset:forward:query", summary="穿透关系图")
def forward_trace(asset_id: str):
    return forward.trace(_id(asset_id), _params())


@mark(perm="ims:asset:forward:export", summary="导出穿透报告", operate=("资产穿透", "导出"))
def forward_export(asset_id: str):
    return forward.export_report(_id(asset_id))


@mark(perm="ims:asset:reverse:query", summary="按人反查资产")
def reverse_person(user_id: str):
    return reverse.by_person(_id(user_id), _params())


@mark(perm="ims:asset:reverse:query", summary="按账号反查资产")
def reverse_account(account_id: str):
    return reverse.by_account(_id(account_id))


@mark(perm="ims:asset:reverse:query", summary="按场次反查资产")
def reverse_session(session_id: str):
    return reverse.by_session(_id(session_id))


@mark(perm="ims:asset:reverse:export", summary="导出反查", operate=("资产反查", "导出"))
def reverse_export():
    return reverse.export(_params())


@mark(perm="ims:asset:verify:run", idempotent=True, summary="手动校验", operate=("资产校验", "执行"))
def verify_run():
    return verify.run(_body(), "MANUAL")


@mark(perm="ims:asset:verify:query", summary="校验指标")
def verify_metrics():
    return verify.metrics()


@mark(perm="ims:asset:verify:query", summary="校验批次")
def verify_batches():
    return verify.batches(_page(), _params())


@mark(login_only=True, summary="校验工单")
def verify_errors():
    return verify.errors(_page(), _params())


@mark(login_only=True, summary="工单流转", operate=("资产校验", "流转"))
def verify_act(ident: str):
    return verify.act(_id(ident), _body())


router.get("/corp/device/phone/page", summary="手机列表")(phone_page)
router.get("/corp/device/phone/export", summary="导出手机")(phone_export)
router.post("/corp/device/phone", summary="登记手机")(phone_create)
router.get("/corp/device/phone/{ident}", summary="手机详情")(phone_detail)
router.put("/corp/device/phone/{ident}", summary="编辑手机")(phone_update)
router.put("/corp/device/phone/{ident}/status", summary="手机状态")(phone_status)
router.delete("/corp/device/phone/{ident}", summary="删除手机")(phone_delete)
router.put("/corp/device/phone/{ident}/sim-bind", summary="绑定手机卡")(phone_bind)
router.get("/corp/device/office/page", summary="办公设备列表")(office_page)
router.get("/corp/device/live/page", summary="直播设备列表")(live_page)
router.post("/asset/ledger/import", summary="采购导入")(ledger_import)
router.get("/asset/ledger/export", summary="导出台账")(ledger_export)
router.post("/asset/ledger", summary="资产登记")(ledger_create)
router.get("/asset/ledger/{ident}", summary="资产详情")(ledger_detail)
router.put("/asset/ledger/{ident}", summary="编辑资产")(ledger_update)
router.delete("/asset/ledger/{ident}", summary="删除资产")(ledger_delete)
router.post("/asset/ledger/{ident}/checkout", summary="领用资产")(ledger_checkout)
router.post("/asset/ledger/{ident}/transfer", summary="流转资产")(ledger_transfer)
router.post("/asset/ledger/{ident}/return", summary="归还资产")(ledger_return)
router.post("/asset/ledger/{ident}/scrap", summary="报废资产")(ledger_scrap)
router.put("/asset/ledger/{ident}/status", summary="标记资产状态")(ledger_status)
router.get("/asset/ledger/{ident}/timeline", summary="资产时间线")(ledger_timeline)
router.get("/asset/forward/detail/{asset_id}", summary="分层穿透")(forward_detail)
router.get("/asset/forward/trace/{asset_id}", summary="穿透关系图")(forward_trace)
router.get("/asset/forward/export/{asset_id}", summary="导出穿透报告")(forward_export)
router.get("/asset/reverse/by-person/{user_id}", summary="按人反查资产")(reverse_person)
router.get("/asset/reverse/by-account/{account_id}", summary="按账号反查资产")(reverse_account)
router.get("/asset/reverse/by-session/{session_id}", summary="按场次反查资产")(reverse_session)
router.get("/asset/reverse/export", summary="导出反查")(reverse_export)
router.post("/asset/verify/run", summary="手动校验")(verify_run)
router.get("/asset/verify/metrics", summary="校验指标")(verify_metrics)
router.get("/asset/verify/batches", summary="校验批次")(verify_batches)
router.get("/asset/verify/errors", summary="校验工单")(verify_errors)
router.put("/asset/verify/task/{ident}", summary="工单流转")(verify_act)
