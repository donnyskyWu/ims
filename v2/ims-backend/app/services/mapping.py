"""钉钉账号映射。同一钉钉号、同一用户都只能有一条。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.errors import BizError
from app.db.session import get_session
from app.domains.auth.model import UserMapping


def bind_dingtalk(user_id: int, ding_user_id: str) -> dict:
    session = get_session()
    by_ding = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == ding_user_id))
    if by_ding is not None and int(by_ding.user_id) != int(user_id):
        raise BizError(1001, "该钉钉账号已绑定其他用户")
    by_user = session.scalar(select(UserMapping).where(UserMapping.user_id == user_id))
    if by_user is not None and by_user.dingtalk_user_id != ding_user_id:
        raise BizError(1001, "该用户已绑定其他钉钉账号")
    if by_ding is None and by_user is None:
        row = UserMapping(user_id=user_id, dingtalk_user_id=ding_user_id)
        session.add(row)
        session.flush()
        return {"id": row.id, "userId": user_id, "dingtalkUserId": ding_user_id}
    return {"userId": user_id, "dingtalkUserId": ding_user_id}
