"""组织架构同步页。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.services import b1_org

router = APIRouter()


def _q() -> dict:
    return dict(current_request().query_params)


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(perm="ims:system:org-sync:query", summary="同步概览")
def sync_metrics():
    return b1_org.sync_metrics()


@mark(perm="ims:system:org-sync:query", summary="同步差异汇总")
def diff_summary():
    return b1_org.diff_summary()


@mark(perm="ims:system:org-sync:query", summary="同步差异列表")
def diff_page():
    return b1_org.diff_page(_q())


@mark(perm="ims:system:org-sync:query", summary="同步事件列表")
def event_page():
    return b1_org.event_page(_q())


@mark(perm="ims:system:org-sync:query", summary="同步事件详情")
def event_detail(ident: int):
    return b1_org.event_detail(ident)


@mark(perm="ims:system:org-sync:run", idempotent=True, operate=("组织同步", "重试事件"), summary="重试同步事件")
def event_retry(ident: int):
    return b1_org.retry_event(ident)


@mark(perm="ims:system:org-sync:run", summary="重放预览")
def replay_preview():
    return b1_org.replay_preview(_q())


@mark(perm="ims:system:org-sync:run", idempotent=True, operate=("组织同步", "重放事件"), summary="重放失败事件")
def replay_events():
    return b1_org.replay_events(_body())


@mark(perm="ims:system:org-sync:query", summary="对账批次列表")
def batch_page():
    return b1_org.batch_page(_q())


@mark(perm="ims:system:org-sync:query", summary="对账批次详情")
def batch_detail(ident: int):
    return b1_org.batch_detail(ident)


@mark(perm="ims:system:org-sync:query", summary="对账明细")
def batch_items(ident: int):
    return b1_org.batch_items(ident, _q())


@mark(perm="ims:system:org-sync:export", operate=("组织同步", "导出事件"), summary="导出同步事件")
def export_events():
    return b1_org.export_events(_body() or _q())


@mark(perm="ims:system:org-sync:export", operate=("组织同步", "导出对账"), summary="导出对账明细")
def export_batch(ident: int):
    return b1_org.export_batch(ident)


@mark(perm="ims:system:org-sync:query", summary="同步人员详情")
def user_detail(ident: int):
    return b1_org.user_detail(ident)


router.get("/org/sync-metrics", summary="同步概览")(sync_metrics)
router.get("/org/diffs/summary", summary="同步差异汇总")(diff_summary)
router.get("/org/diffs", summary="同步差异列表")(diff_page)
router.get("/org/events", summary="同步事件列表")(event_page)
router.get("/org/events/replay-preview", summary="重放预览")(replay_preview)
router.get("/org/events/{ident}", summary="同步事件详情")(event_detail)
router.post("/org/events/{ident}/retry", summary="重试同步事件")(event_retry)
router.post("/org/events/replay", summary="重放失败事件")(replay_events)
router.get("/org/reconcile-batches", summary="对账批次列表")(batch_page)
router.get("/org/reconcile-batches/{ident}", summary="对账批次详情")(batch_detail)
router.get("/org/reconcile-batches/{ident}/items", summary="对账明细")(batch_items)
router.post("/org/events/export", summary="导出同步事件")(export_events)
router.post("/org/reconcile-batches/{ident}/export", summary="导出对账明细")(export_batch)
router.get("/org/users/{ident}", summary="同步人员详情")(user_detail)
