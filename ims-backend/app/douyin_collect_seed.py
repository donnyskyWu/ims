"""抖音内部采集 E2E 主数据：公司与 IP 组（幂等）。账号由页面创建。"""

from sqlalchemy import select

from app.ops_db import ensure_ops, ops_session
from app.ops_models import Company, IpGroup

E2E_DY_COMPANY = "E2E抖音采集公司"
E2E_DY_GROUP = "E2E抖音采集组"


def refresh_douyin_collect_seed() -> None:
    ensure_ops()
    ops = ops_session()
    try:
        company = ops.scalar(
            select(Company).where(Company.company_name == E2E_DY_COMPANY, Company.deleted == 0, Company.tenant_id == 0)
        )
        if company is None:
            company = Company(company_name=E2E_DY_COMPANY, credit_code="E2EDYCOMPANY0001", status="ENABLED", tenant_id=0)
            ops.add(company)
        else:
            company.status = "ENABLED"
        group = ops.scalar(
            select(IpGroup).where(IpGroup.group_name == E2E_DY_GROUP, IpGroup.deleted == 0, IpGroup.tenant_id == 0)
        )
        if group is None:
            group = IpGroup(group_name=E2E_DY_GROUP, group_type="SMALL", status="ENABLED", tenant_id=0)
            ops.add(group)
        else:
            group.status = "ENABLED"
        ops.commit()
    finally:
        ops.close()
