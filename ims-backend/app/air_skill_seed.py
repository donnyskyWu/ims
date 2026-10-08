"""技能授权抽屉要能选到部门。部门主数据仍走 01 的组织映射，不新增部门接口。"""

from sqlalchemy import select

from app.models import User, UserDept, UserMapping

AIR_DEPT_ID = 7301
AIR_DEPT_DING = "dt-e2e-air-dept"


def ensure_air_skill_dept_fixture(db) -> None:
    author = db.scalar(select(User).where(User.username == "e2e_author", User.deleted == 0))
    if author is None:
        return
    tenant_id = author.tenant_id or 0
    linked = db.scalar(
        select(UserDept).where(UserDept.user_id == author.id, UserDept.dept_id == AIR_DEPT_ID)
    )
    if linked is None:
        db.add(UserDept(user_id=author.id, dept_id=AIR_DEPT_ID, tenant_id=tenant_id))
    mapping = db.scalar(
        select(UserMapping).where(
            UserMapping.tenant_id == tenant_id,
            UserMapping.dingtalk_user_id == AIR_DEPT_DING,
        )
    )
    if mapping is None:
        db.add(
            UserMapping(
                user_id=author.id,
                dingtalk_user_id=AIR_DEPT_DING,
                union_id="e2e-air-dept",
                dept_ids=[AIR_DEPT_ID],
                sync_status="SUCCESS",
                tenant_id=tenant_id,
                deleted=0,
            )
        )
        return
    mapping.user_id = author.id
    mapping.deleted = 0
    mapping.dept_ids = [AIR_DEPT_ID]
    mapping.sync_status = "SUCCESS"
