"""仅测试环境注册，按查询参数返回指定错误码。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import mark
from app.api.runtime import current_request
from app.core.errors import BizError

router = APIRouter()


@mark(login_only=True, summary="按错误码返回示例")
def demo_error():
    code = int(current_request().query_params.get("code") or 0)
    raise BizError(code)


router.get("/error", summary="按错误码返回示例")(demo_error)
