"""直播 37 个接口。静态路径写在编号路径前面。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.pagination import parse_page
from app.core.serialize import parse_api_id
from app.domains.live import alarm, service

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


@mark(perm="ims:live:session:query", summary="场次统计卡")
def session_stats():
    return service.stats()


@mark(perm="ims:live:session:query", summary="场次列表")
def session_list():
    return service.session_list(_page(), _params())


@mark(perm="ims:live:session:query", summary="场次详情")
def session_detail(code: str):
    return service.detail(code)


@mark(perm="ims:live:session:query", summary="直播数据")
def session_metrics(code: str):
    return service.metrics(code)


@mark(perm="ims:live:football:bind", summary="绑定直播间", operate=("直播场次", "绑定房间"))
def football_room(code: str):
    return service.bind_room(code, _body())


@mark(perm="ims:live:football:bind", summary="同步直播间", operate=("直播场次", "同步"))
def football_sync(code: str):
    return service.sync_room(code, _body())


@mark(perm="ims:live:session:register", summary="证件预检")
def realname_precheck():
    return service.realname_precheck(_params())


@mark(perm="ims:live:session:register", idempotent=True, summary="新建场次", operate=("直播场次", "登记"))
def register():
    return service.register(_body())


@mark(perm="ims:live:session:register", summary="编辑登记", operate=("直播场次", "编辑"))
def register_update(code: str):
    return service.update_register(code, _body())


@mark(perm="ims:live:session:register", summary="重跑风控", operate=("直播场次", "风控"))
def risk_check(code: str):
    return service.rerun(code)


@mark(perm="ims:live:session:approve", summary="黄级审批", operate=("直播场次", "审批"))
def approve(code: str):
    return service.approve(code, _body())


@mark(perm="ims:live:session:register", summary="确认开播", operate=("直播场次", "开播"))
def start(code: str):
    return service.start(code, _body())


@mark(perm="ims:live:session:register", summary="确认下播", operate=("直播场次", "下播"))
def end(code: str):
    return service.end(code, _body())


@mark(perm="ims:live:session:cancel", summary="取消场次", operate=("直播场次", "取消"))
def cancel(code: str):
    return service.cancel(code, _body())


@mark(any_perm=("ims:live:session:query", "ims:live:report:entry", "ims:live:report:confirm", "ims:live:report:finance"), summary="报告详情")
def report_get(code: str):
    return service.report_detail(code)


@mark(perm="ims:live:report:entry", summary="保存草稿", operate=("下播报告", "草稿"))
def report_draft(code: str):
    return service.save_draft(code, _body())


@mark(perm="ims:live:report:entry", idempotent=True, summary="提交下播", operate=("下播报告", "提交"))
def report_submit(code: str):
    return service.submit_report(code, _body())


@mark(perm="ims:live:report:confirm", summary="核准报告", operate=("下播报告", "核准"))
def report_confirm(code: str):
    return service.confirm_report(code, _body())


@mark(perm="ims:live:report:correct", summary="更正报告", operate=("下播报告", "更正"))
def report_correct(code: str):
    return service.correct(code, _body())


@mark(perm="ims:live:session:query", summary="更正历史")
def report_corrections(code: str):
    return service.corrections(code)


@mark(perm="ims:live:session:query", summary="待录入督办")
def report_pending():
    return service.pending(_page(), _params())


@mark(perm="ims:live:report:confirm", summary="督办提醒", operate=("下播报告", "提醒"))
def report_remind(code: str):
    return service.remind(code)


@mark(perm="ims:live:alarm:query", summary="告警记录")
def alarm_records():
    return alarm.record_page(_page(), _params())


@mark(perm="ims:live:alarm:query", summary="告警详情")
def alarm_detail(ident: str):
    return alarm.record_detail(_id(ident))


@mark(perm="ims:live:alarm:handle", summary="处置告警", operate=("直播告警", "处置"))
def alarm_handle(ident: str):
    return alarm.handle(_id(ident), _body())


@mark(perm="ims:live:alarm:rule", summary="告警规则")
def alarm_rules():
    return alarm.rule_list()


@mark(perm="ims:live:alarm:rule", summary="新建规则", operate=("直播告警", "新建规则"))
def alarm_create():
    return alarm.create_rule(_body())


@mark(perm="ims:live:alarm:rule", summary="编辑规则", operate=("直播告警", "编辑规则"))
def alarm_update(ident: str):
    return alarm.update_rule(_id(ident), _body())


@mark(perm="ims:live:alarm:rule", summary="启停规则", operate=("直播告警", "启停规则"))
def alarm_status(ident: str):
    return alarm.set_status(_id(ident), _body())


@mark(perm="ims:live:alarm:rule", summary="删除规则", operate=("直播告警", "删除规则"))
def alarm_delete(ident: str):
    return alarm.remove_rule(_id(ident), _body())


@mark(perm="ims:live:alarm:query", summary="告警统计")
def alarm_stats():
    return alarm.stats()


@mark(perm="ims:live:ledger:query", summary="台账列表")
def ledger_list():
    return service.ledger_list(_page(), _params())


@mark(perm="ims:live:ledger:supplement", idempotent=True, summary="提交补录", operate=("直播台账", "补录"))
def supplement_create():
    return service.submit_supplement(_body())


@mark(perm="ims:live:ledger:query", summary="补录详情")
def supplement_get(ident: str):
    return service.supplement_detail(_id(ident))


@mark(perm="ims:live:ledger:supplement", summary="修改补录", operate=("直播台账", "修改补录"))
def supplement_put(ident: str):
    return service.supplement_update(_id(ident), _body())


@mark(perm="ims:live:ledger:supplement-approve", summary="审批补录", operate=("直播台账", "审批补录"))
def supplement_approve(ident: str):
    return service.supplement_approve(_id(ident), _body())


@mark(perm="ims:live:ledger:export", summary="导出台账", operate=("直播台账", "导出"))
def ledger_export():
    return service.export_ledger(_params())


router.get("/live/sessions/stats", summary="场次统计卡")(session_stats)
router.get("/live/sessions/list", summary="场次列表")(session_list)
router.get("/live/sessions/{code}/metrics", summary="直播数据")(session_metrics)
router.put("/live/sessions/{code}/football-room", summary="绑定直播间")(football_room)
router.post("/live/sessions/{code}/football-sync", summary="同步直播间")(football_sync)
router.get("/live/sessions/{code}", summary="场次详情")(session_detail)
router.get("/live/register/realname-precheck", summary="证件预检")(realname_precheck)
router.post("/live/register", summary="新建场次")(register)
router.put("/live/register/{code}", summary="编辑登记")(register_update)
router.post("/live/register/{code}/risk-check", summary="重跑风控")(risk_check)
router.put("/live/register/{code}/approve", summary="黄级审批")(approve)
router.put("/live/register/{code}/start", summary="确认开播")(start)
router.put("/live/register/{code}/end", summary="确认下播")(end)
router.put("/live/register/{code}/cancel", summary="取消场次")(cancel)
router.get("/live/report/pending", summary="待录入督办")(report_pending)
router.get("/live/report/{code}/corrections", summary="更正历史")(report_corrections)
router.post("/live/report/{code}/correction", summary="更正报告")(report_correct)
router.put("/live/report/{code}/confirm", summary="核准报告")(report_confirm)
router.post("/live/report/{code}/remind", summary="督办提醒")(report_remind)
router.get("/live/report/{code}", summary="报告详情")(report_get)
router.put("/live/report/{code}", summary="保存草稿")(report_draft)
router.post("/live/report/{code}", summary="提交下播")(report_submit)
router.get("/live/alarm/records", summary="告警记录")(alarm_records)
router.get("/live/alarm/record/{ident}", summary="告警详情")(alarm_detail)
router.put("/live/alarm/record/{ident}/handle", summary="处置告警")(alarm_handle)
router.get("/live/alarm/rules", summary="告警规则")(alarm_rules)
router.post("/live/alarm/rule", summary="新建规则")(alarm_create)
router.put("/live/alarm/rule/{ident}/status", summary="启停规则")(alarm_status)
router.put("/live/alarm/rule/{ident}", summary="编辑规则")(alarm_update)
router.delete("/live/alarm/rule/{ident}", summary="删除规则")(alarm_delete)
router.get("/live/alarm/stats", summary="告警统计")(alarm_stats)
router.get("/live/ledger/list", summary="台账列表")(ledger_list)
router.get("/live/ledger/export", summary="导出台账")(ledger_export)
router.post("/live/ledger/supplement", summary="提交补录")(supplement_create)
router.get("/live/ledger/supplement/{ident}", summary="补录详情")(supplement_get)
router.put("/live/ledger/supplement/{ident}/approve", summary="审批补录")(supplement_approve)
router.put("/live/ledger/supplement/{ident}", summary="修改补录")(supplement_put)
