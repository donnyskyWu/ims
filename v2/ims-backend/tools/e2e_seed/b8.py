"""B8 测试环境造数。只允许 test / e2e，不写明文密码。"""
from __future__ import annotations

from tools.e2e_seed.b7 import assert_allowed


def seed() -> None:
    assert_allowed()
    from tools.e2e_seed.b7 import seed as seed_b7

    seed_b7()
    from sqlalchemy import select

    from app.core.context import system_context, use_context
    from app.db.repository import Repository
    from app.db.session import session_scope
    from app.domains.master.model import Author, Company, IpAnchor, IpGroup, IpMember, PlatformAccount, Realname
    from app.domains.system.model import User

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            if session.scalar(select(IpGroup).where(IpGroup.code == "B8-BIG")):
                return
            admin = session.scalar(select(User).where(User.username == "admin"))
            company = session.scalar(select(Company).where(Company.name == "B7样例公司"))
            person = session.scalar(select(Realname).where(Realname.name == "B7样例实名"))
            big = IpGroup(code="B8-BIG", name="B8华东大组", group_name="B8华东大组", group_type="BIG", status="ENABLED", level="S")
            Repository(IpGroup).create(big)
            small_dual = IpGroup(
                code="B8-SMALL-DUAL",
                name="B8双作者组",
                group_name="B8双作者组",
                group_type="SMALL",
                parent_id=big.id,
                status="ENABLED",
            )
            small_one = IpGroup(
                code="B8-SMALL-ONE",
                name="B8单作者组",
                group_name="B8单作者组",
                group_type="SMALL",
                parent_id=big.id,
                status="ENABLED",
            )
            Repository(IpGroup).create(small_dual)
            Repository(IpGroup).create(small_one)
            if admin is not None:
                Repository(IpMember).create(IpMember(group_id=big.id, user_id=admin.id, position="OPS_LEADER", relation_type="PRIMARY", is_leader=1))
                Repository(IpMember).create(IpMember(group_id=small_one.id, user_id=admin.id, position="OPERATOR", relation_type="PRIMARY", is_leader=0))
            authors = []
            for code, name, group, author_type in (
                ("B8-AU-1", "B8作者甲", small_dual, "LIVE"),
                ("B8-AU-2", "B8作者乙", small_dual, "SHORT_VIDEO"),
                ("B8-AU-3", "B8唯一作者", small_one, "BOTH"),
            ):
                row = Author(
                    code=code,
                    name=name,
                    author_no=code,
                    author_name=name,
                    author_type=author_type,
                    ip_group_id=group.id,
                    status="ENABLED",
                )
                Repository(Author).create(row)
                authors.append(row)
            Repository(IpAnchor).create(IpAnchor(ip_group_id=small_dual.id, author_id=authors[0].id, anchor_type="LIVE", is_primary=0))
            Repository(IpAnchor).create(IpAnchor(ip_group_id=small_dual.id, author_id=authors[1].id, anchor_type="SHORT_VIDEO", is_primary=0))
            Repository(IpAnchor).create(IpAnchor(ip_group_id=small_one.id, author_id=authors[2].id, anchor_type="BOTH", is_primary=1))
            if company is not None and person is not None:
                bound = PlatformAccount(
                    code="B8-BOUND",
                    name="B8已绑定",
                    account_no="B8-BOUND",
                    nickname="B8已绑定",
                    platform="DOUYIN",
                    company_id=company.id,
                    realname_id=person.id,
                    ip_group_id=small_one.id,
                    author_user_id=authors[2].id,
                    status="IN_POOL",
                    collect_bind_status="UNBOUND",
                    recharge_total_fen=0,
                )
                Repository(PlatformAccount).create(bound)
                loose = PlatformAccount(
                    code="B8-UNBOUND",
                    name="B8未绑定",
                    account_no="B8-UNBOUND",
                    nickname="B8未绑定",
                    platform="DOUYIN",
                    company_id=company.id,
                    realname_id=person.id,
                    status="IN_POOL",
                    collect_bind_status="UNBOUND",
                    recharge_total_fen=0,
                )
                Repository(PlatformAccount).create(loose)
