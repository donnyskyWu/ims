"""公司账号。静态路径写在编号路径前面。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.account import apply, collect, personal, platform, recharge, returns, timeline_api, transfer
from app.domains.account.hooks import register

register()

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


@mark(perm="ims:corp:account:query", summary="平台账号列表")
def account_page():
    return platform.page(_page(), _params())


@mark(perm="ims:corp:account:export", summary="导出平台账号", operate=("平台账号", "导出"))
def account_export():
    return platform.export(_params())


@mark(perm="ims:corp:account:create", idempotent=True, summary="登记平台账号", operate=("平台账号", "登记"))
def account_create():
    return platform.create(_body())


@mark(perm="ims:corp:account:query", summary="平台账号详情")
def account_detail(ident: str):
    return platform.detail(_id(ident))


@mark(perm="ims:corp:account:update", summary="编辑平台账号", operate=("平台账号", "编辑"))
def account_update(ident: str):
    return platform.update(_id(ident), _body())


@mark(perm="ims:corp:account:update", summary="注销平台账号", operate=("平台账号", "注销"))
def account_cancel(ident: str):
    return platform.cancel(_id(ident), _body())


@mark(perm="ims:corp:account:delete", summary="删除平台账号", operate=("平台账号", "删除"))
def account_delete(ident: str):
    return platform.remove(_id(ident))


@mark(perm="ims:corp:account:update", summary="绑定账号资产", operate=("平台账号", "绑定资产"))
def account_bind(ident: str):
    return platform.bind_assets(_id(ident), _body())


@mark(perm="ims:corp:account:query", summary="账号关联资产")
def account_assets(ident: str):
    return platform.assets(_id(ident))


@mark(perm="ims:corp:account:collect", summary="更新采集凭证")
def collect_put(ident: str):
    return collect.credential_put(_id(ident), _body())


@mark(perm="ims:corp:account:collect", summary="清空采集凭证")
def collect_delete(ident: str):
    return collect.credential_delete(_id(ident))


@mark(perm="ims:corp:account:collect", summary="测试采集连接", operate=("采集凭证", "测试连接"))
def collect_probe(ident: str):
    return collect.probe(_id(ident), _body())


@mark(perm="ims:corp:account:collect", summary="导入 Collector", operate=("采集凭证", "导入"))
def collect_import(ident: str):
    return collect.import_collector(_id(ident), _body())


@mark(perm="ims:corp:account:collect", summary="扫码登录", operate=("采集凭证", "扫码"))
def collect_qr(ident: str):
    return collect.qr_login(_id(ident), _body())


@mark(perm="ims:corp:account:personal:query", summary="个人账号列表")
def personal_page():
    return personal.page(_page(), _params())


@mark(perm="ims:corp:account:personal:export", summary="导出个人账号", operate=("个人账号", "导出"))
def personal_export():
    return personal.export(_params())


@mark(perm="ims:corp:account:personal:create", idempotent=True, summary="新建个人账号", operate=("个人账号", "新建"))
def personal_create():
    return personal.create(_body())


@mark(perm="ims:corp:account:personal:query", summary="个人账号详情")
def personal_detail(ident: str):
    return personal.detail(_id(ident))


@mark(perm="ims:corp:account:personal:update", summary="编辑个人账号", operate=("个人账号", "编辑"))
def personal_update(ident: str):
    return personal.update(_id(ident), _body())


@mark(perm="ims:corp:account:personal:update", summary="个人账号状态", operate=("个人账号", "状态"))
def personal_status(ident: str):
    return personal.set_status(_id(ident), _body())


@mark(perm="ims:corp:account:personal:delete", summary="删除个人账号", operate=("个人账号", "删除"))
def personal_delete(ident: str):
    return personal.remove(_id(ident))


@mark(perm="ims:account:apply:query", summary="领用单列表")
def apply_page():
    return apply.page(_page(), _params())


@mark(perm="ims:account:apply:create", idempotent=True, summary="发起领用", operate=("账号领用", "发起"))
def apply_create():
    return apply.create(_body())


@mark(perm="ims:account:apply:query", summary="领用单详情")
def apply_detail(ident: str):
    return apply.detail(_id(ident))


@mark(perm="ims:account:apply:query", summary="交接确认", operate=("账号领用", "交接确认"))
def apply_confirm(ident: str):
    return apply.confirm(_id(ident), _body())


@mark(perm="ims:account:transfer:query", summary="流转单列表")
def transfer_page():
    return transfer.page(_page(), _params())


@mark(perm="ims:account:transfer:create", idempotent=True, summary="发起流转", operate=("账号流转", "发起"))
def transfer_create():
    return transfer.create(_body())


@mark(perm="ims:account:transfer:confirm", summary="确认流转", operate=("账号流转", "确认"))
def transfer_confirm(ident: str):
    return transfer.confirm(_id(ident), _body())


@mark(perm="ims:account:transfer:revoke", summary="撤销流转", operate=("账号流转", "撤销"))
def transfer_revoke(ident: str):
    return transfer.revoke(_id(ident), _body())


@mark(perm="ims:account:unfreeze", summary="解冻账号", operate=("平台账号", "解冻"))
def account_unfreeze(ident: str):
    return transfer.unfreeze(_id(ident), _body())


@mark(perm="ims:account:return:query", summary="归还单列表")
def return_page():
    return returns.page(_page(), _params())


@mark(perm="ims:account:return:generate", idempotent=True, summary="补建归还单", operate=("账号归还", "补建"))
def return_generate():
    return returns.generate(_body())


@mark(perm="ims:account:return:query", summary="归还单详情")
def return_detail(ident: str):
    return returns.detail(_id(ident))


@mark(perm="ims:account:return:handle", summary="处理归还项", operate=("账号归还", "处理"))
def return_item(item_id: str):
    return returns.handle_item(_id(item_id), _body())


@mark(perm="ims:account:return:close", summary="闭环归还单", operate=("账号归还", "闭环"))
def return_close(ident: str):
    return returns.close(_id(ident))


@mark(perm="ims:account:return:handle", summary="挂起归还单", operate=("账号归还", "挂起"))
def return_suspend(ident: str):
    return returns.suspend(_id(ident), _body())


@mark(perm="ims:account:recharge:query", summary="充值列表")
def recharge_page():
    return recharge.page(_page(), _params())


@mark(perm="ims:account:recharge:query", summary="充值核对概览")
def recharge_overview():
    return recharge.overview()


@mark(perm="ims:account:recharge:query", summary="充值成本汇总")
def recharge_summary():
    return recharge.summary(_params())


@mark(perm="ims:account:recharge:export", summary="导出充值", operate=("冲话费", "导出"))
def recharge_export():
    return recharge.export(_params())


@mark(perm="ims:account:recharge:create", idempotent=True, summary="登记充值", operate=("冲话费", "登记"))
def recharge_create():
    return recharge.create(_body())


@mark(perm="ims:account:recharge:verify", summary="月度核对", operate=("冲话费", "核对"))
def recharge_verify():
    return recharge.verify(_body())


@mark(perm="ims:account:recharge:update", summary="编辑充值", operate=("冲话费", "编辑"))
def recharge_update(ident: str):
    return recharge.update(_id(ident), _body())


@mark(perm="ims:account:timeline:query", summary="事件检索")
def timeline_events():
    return timeline_api.events(_page(), _params())


@mark(perm="ims:account:timeline:export", summary="导出交接凭证", operate=("账号时间线", "导出"))
def timeline_export(account_id: str):
    return timeline_api.export_pdf(_id(account_id))


@mark(perm="ims:account:timeline:query", summary="账号时间线")
def timeline_account(account_id: str):
    return timeline_api.by_account(_id(account_id))


router.get("/corp/account/page", summary="平台账号列表")(account_page)
router.get("/corp/account/export", summary="导出平台账号")(account_export)
router.get("/corp/account/personal/page", summary="个人账号列表")(personal_page)
router.get("/corp/account/personal/export", summary="导出个人账号")(personal_export)
router.post("/corp/account/personal", summary="新建个人账号")(personal_create)
router.get("/corp/account/personal/{ident}", summary="个人账号详情")(personal_detail)
router.put("/corp/account/personal/{ident}", summary="编辑个人账号")(personal_update)
router.put("/corp/account/personal/{ident}/status", summary="个人账号状态")(personal_status)
router.delete("/corp/account/personal/{ident}", summary="删除个人账号")(personal_delete)
router.post("/corp/account", summary="登记平台账号")(account_create)
router.get("/corp/account/{ident}", summary="平台账号详情")(account_detail)
router.put("/corp/account/{ident}", summary="编辑平台账号")(account_update)
router.put("/corp/account/{ident}/cancel", summary="注销平台账号")(account_cancel)
router.delete("/corp/account/{ident}", summary="删除平台账号")(account_delete)
router.put("/corp/account/{ident}/asset-bind", summary="绑定账号资产")(account_bind)
router.get("/corp/account/{ident}/assets", summary="账号关联资产")(account_assets)
router.put("/corp/account/{ident}/collect/credential", summary="更新采集凭证")(collect_put)
router.delete("/corp/account/{ident}/collect/credential", summary="清空采集凭证")(collect_delete)
router.post("/corp/account/{ident}/collect/probe", summary="测试采集连接")(collect_probe)
router.post("/corp/account/{ident}/collect/import", summary="导入 Collector")(collect_import)
router.post("/corp/account/{ident}/collect/qr-login", summary="扫码登录")(collect_qr)
router.get("/account/apply/page", summary="领用单列表")(apply_page)
router.post("/account/apply", summary="发起领用")(apply_create)
router.get("/account/apply/{ident}", summary="领用单详情")(apply_detail)
router.put("/account/apply/{ident}/confirm", summary="交接确认")(apply_confirm)
router.get("/account/transfer/page", summary="流转单列表")(transfer_page)
router.post("/account/transfer", summary="发起流转")(transfer_create)
router.put("/account/transfer/{ident}/confirm", summary="确认流转")(transfer_confirm)
router.put("/account/transfer/{ident}/revoke", summary="撤销流转")(transfer_revoke)
router.post("/account/{ident}/unfreeze", summary="解冻账号")(account_unfreeze)
router.get("/account/return/page", summary="归还单列表")(return_page)
router.post("/account/return/generate", summary="补建归还单")(return_generate)
router.put("/account/return/item/{item_id}", summary="处理归还项")(return_item)
router.get("/account/return/{ident}", summary="归还单详情")(return_detail)
router.put("/account/return/{ident}/close", summary="闭环归还单")(return_close)
router.put("/account/return/{ident}/suspend", summary="挂起归还单")(return_suspend)
router.get("/account/recharge/page", summary="充值列表")(recharge_page)
router.get("/account/recharge/overview", summary="充值核对概览")(recharge_overview)
router.get("/account/recharge/summary", summary="充值成本汇总")(recharge_summary)
router.get("/account/recharge/export", summary="导出充值")(recharge_export)
router.post("/account/recharge", summary="登记充值")(recharge_create)
router.post("/account/recharge/verify", summary="月度核对")(recharge_verify)
router.put("/account/recharge/{ident}", summary="编辑充值")(recharge_update)
router.get("/account/timeline/events", summary="事件检索")(timeline_events)
router.get("/account/timeline/{account_id}/export", summary="导出交接凭证")(timeline_export)
router.get("/account/timeline/{account_id}", summary="账号时间线")(timeline_account)
