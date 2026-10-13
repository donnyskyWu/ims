"""B8 测试环境造数。只允许 test / e2e，不写密码。"""
from __future__ import annotations

import os

ALLOWED = {"test", "e2e"}


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def seed() -> None:
    """大组 1、小组 2、作者 4、账号样例，覆盖 1223 / 单作者物化。"""
    assert_allowed()
    from tools.e2e_seed.b7 import seed as seed_b7

    seed_b7()
    from sqlalchemy import select

    from app.core.context import system_context, use_context
    from app.db.repository import Repository
    from app.db.session import session_scope
    from app.domains.master.model import Author, IpAnchor, IpGroup, IpMember, PlatformAccount
    from app.domains.system.model import User

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            if session.scalar(select(IpGroup).where(IpGroup.group_name == "测试大组甲")):
                return
            big = IpGroup(name="测试大组甲", group_name="测试大组甲", group_type="BIG", status="ENABLED", level="A", sort_order=1)
            Repository(IpGroup).create(big)
            big.code = f"IPG{big.id}"
            left = IpGroup(name="测试小组甲", group_name="测试小组甲", group_type="SMALL", parent_id=big.id, status="ENABLED", sort_order=1)
            right = IpGroup(name="测试小组乙", group_name="测试小组乙", group_type="SMALL", parent_id=big.id, status="ENABLED", sort_order=2)
            stopped = IpGroup(name="停用大组", group_name="停用大组", group_type="BIG", status="DISABLED", sort_order=9)
            Repository(IpGroup).create(left)
            Repository(IpGroup).create(right)
            Repository(IpGroup).create(stopped)
            for row in (left, right, stopped):
                row.code = f"IPG{row.id}"
            r5 = session.scalar(select(User).where(User.username == "test_r5"))
            r5b = session.scalar(select(User).where(User.username == "test_r5b"))
            if r5 is not None:
                session.add(IpMember(group_id=left.id, user_id=r5.id, position="LIVE_OPERATOR", relation_type="PRIMARY", is_leader=1))
                left.leader_user_id = r5.id
            if r5b is not None:
                session.add(IpMember(group_id=right.id, user_id=r5b.id, position="OPERATOR", relation_type="PRIMARY", is_leader=0))

            def author(name: str, group_id: int, status: str = "ENABLED") -> Author:
                row = Author(name=name, author_name=name, author_type="LIVE", ip_group_id=group_id, status=status, author_no=f"AU-SEED-{name}", code=f"AU-SEED-{name}")
                Repository(Author).create(row)
                return row

            single = author("作者-单", left.id)
            primary = author("作者-主", left.id)
            dual_a = author("作者-双A", right.id)
            dual_b = author("作者-双B", right.id)
            author("停用作者", left.id, "DISABLED")
            session.add(IpAnchor(ip_group_id=left.id, author_id=single.id, anchor_type="LIVE", is_primary=0))
            session.add(IpAnchor(ip_group_id=left.id, author_id=primary.id, anchor_type="LIVE", is_primary=1))
            session.add(IpAnchor(ip_group_id=right.id, author_id=dual_a.id, anchor_type="LIVE", is_primary=0))
            session.add(IpAnchor(ip_group_id=right.id, author_id=dual_b.id, anchor_type="LIVE", is_primary=0))
            pool = session.scalar(select(PlatformAccount).where(PlatformAccount.account_no == "AC-DYS-POOL"))
            if pool is None:
                pool = session.scalar(select(PlatformAccount).where(PlatformAccount.account_no.like("B7-DOU-IN_POOL")))
            if pool is not None and pool.ip_group_id is None:
                pool.nickname = pool.nickname or "AC-DYS-POOL"
            bound = session.scalar(select(PlatformAccount).where(PlatformAccount.account_no == "AC-DYS-BOUND"))
            if bound is None and pool is not None:
                bound = PlatformAccount(
                    code="AC-DYS-BOUND",
                    name="已绑定样例",
                    account_no="AC-DYS-BOUND",
                    nickname="已绑定样例",
                    platform=pool.platform or "DOUYIN",
                    company_id=pool.company_id,
                    realname_id=pool.realname_id,
                    status="IN_POOL",
                    ip_group_id=left.id,
                    author_user_id=single.id,
                    collect_bind_status="UNBOUND",
                    recharge_total_fen=0,
                )
                Repository(PlatformAccount).create(bound)
            session.flush()
