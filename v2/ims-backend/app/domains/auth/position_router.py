"""岗位-角色供给规则页。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.services import b1_position

router = APIRouter()


def _q() -> dict:
    return dict(current_request().query_params)


def _body() -> dict:
    return getattr(current_request().state, "json_body", None) or {}


@mark(perm="ims:auth:position-rule:query", summary="岗位规则概览")
def position_overview():
    return b1_position.overview()


@mark(perm="ims:auth:position-rule:query", summary="岗位规则列表")
def position_rules():
    return b1_position.rule_page(_q())


@mark(perm="ims:auth:position-rule:query", summary="岗位规则详情")
def position_rule_get(ident: int):
    return b1_position.rule_detail(ident)


@mark(perm="ims:auth:position-rule:query", summary="岗位规则版本")
def position_rule_versions(ident: int):
    return b1_position.rule_versions(ident)


@mark(perm="ims:auth:position-rule:query", summary="岗位规则套用人员")
def position_rule_users(ident: int):
    return b1_position.rule_users(ident, _q())


@mark(perm="ims:auth:position-rule:create", idempotent=True, operate=("岗位规则", "新建规则"), summary="新建岗位规则")
def position_rule_create():
    return b1_position.create_rule(_body())


@mark(perm="ims:auth:position-rule:update", operate=("岗位规则", "修改规则"), summary="修改岗位规则")
def position_rule_update(ident: int):
    return b1_position.update_rule(ident, _body())


@mark(perm="ims:auth:position-rule:update", operate=("岗位规则", "启用规则"), summary="启用岗位规则")
def position_rule_enable(ident: int):
    return b1_position.enable_rule(ident, _body())


@mark(perm="ims:auth:position-rule:update", operate=("岗位规则", "停用规则"), summary="停用岗位规则")
def position_rule_disable(ident: int):
    return b1_position.disable_rule(ident)


@mark(perm="ims:auth:position-rule:delete", operate=("岗位规则", "删除规则"), summary="删除岗位规则")
def position_rule_delete(ident: int):
    return b1_position.delete_rule(ident, current_request().query_params.get("confirmText") or "")


@mark(perm="ims:auth:position-rule:refresh", summary="刷新预览")
def position_refresh_preview(ident: int):
    return b1_position.refresh_preview(ident, _body())


@mark(perm="ims:auth:position-rule:refresh", idempotent=True, operate=("岗位规则", "刷新人员"), summary="按新版本刷新")
def position_refresh(ident: int):
    return b1_position.refresh_users(ident, _body())


router.get("/position/overview", summary="岗位规则概览")(position_overview)
router.get("/position/rules", summary="岗位规则列表")(position_rules)
router.get("/position/rules/{ident}", summary="岗位规则详情")(position_rule_get)
router.get("/position/rules/{ident}/versions", summary="岗位规则版本")(position_rule_versions)
router.get("/position/rules/{ident}/users", summary="岗位规则套用人员")(position_rule_users)
router.post("/position/rules", summary="新建岗位规则")(position_rule_create)
router.put("/position/rules/{ident}", summary="修改岗位规则")(position_rule_update)
router.post("/position/rules/{ident}/enable", summary="启用岗位规则")(position_rule_enable)
router.post("/position/rules/{ident}/disable", summary="停用岗位规则")(position_rule_disable)
router.delete("/position/rules/{ident}", summary="删除岗位规则")(position_rule_delete)
router.post("/position/rules/{ident}/refresh-preview", summary="刷新预览")(position_refresh_preview)
router.post("/position/rules/{ident}/refresh", summary="按新版本刷新")(position_refresh)
