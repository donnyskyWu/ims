"""岗位供给与巡检等补充接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.services import position

router = APIRouter()


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(perm="ims:system:role:update", summary="投递岗位变更")
def position_event():
    body = _body()
    return position.apply_position_change(int(body["userId"]), body["positionCode"], body["eventId"])


@mark(perm="ims:system:role:update", summary="保存岗位供给规则")
def position_rule():
    body = _body()
    return position.set_rule_roles(body["positionCode"], int(body["roleId"]), [int(item) for item in body.get("extraRoleIds") or []])


router.post("/position/event", summary="投递岗位变更")(position_event)
router.post("/position/rule", summary="保存岗位供给规则")(position_rule)
