"""注册领用流程回调和离职归还监听。监听在 events.clear 之后仍然保留。"""
from __future__ import annotations

_ready = False


def register() -> None:
    global _ready
    if _ready:
        return
    _ready = True
    from app.core.events import events
    from app.domains.account.apply import on_finished
    from app.domains.account.returns import on_resigned
    from app.domains.flow.service import callbacks

    def _flow(payload: dict) -> None:
        if payload.get("bizType") != "ACCT_BORROW":
            return
        biz_id = payload.get("bizId")
        if biz_id is None:
            return
        on_finished(int(biz_id), str(payload.get("result") or ""))

    callbacks.append(_flow)
    events.subscribe("user.resigned", on_resigned)
