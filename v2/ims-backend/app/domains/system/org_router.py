"""组织同步接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.context import get_ctx
from app.services import org_sync

router = APIRouter()


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(perm="ims:system:org-sync:run", summary="组织对账")
def org_reconcile():
    ctx = get_ctx()
    return org_sync.reconcile(trigger_type="MANUAL", operator_id=ctx.user_id if ctx else None)


@mark(perm="ims:system:org-sync:query", summary="最近同步批次")
def org_latest_batch():
    return org_sync.latest_batch()


@mark(perm="ims:system:org-sync:run", summary="处理组织事件")
def org_process():
    return org_sync.process_event(_body())


router.post("/org-sync/reconcile", summary="组织对账")(org_reconcile)
router.get("/org-sync/latest-batch", summary="最近同步批次")(org_latest_batch)
router.post("/org-sync/process", summary="处理组织事件")(org_process)


def _install() -> None:
    from app import main as main_mod

    mounts = getattr(main_mod, "MOUNTS", None)
    if not mounts:
        return
    if any(item[1] is router for item in mounts):
        return
    mounts.append(("/admin-api/ims/system", router))


_install()
