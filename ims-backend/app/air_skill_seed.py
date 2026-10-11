"""技能授权抽屉要能选到部门。部门主数据仍走 01 的组织映射，不新增部门接口。"""

from sqlalchemy import select

from app.core import utcnow
from app.models import AirSkill, AirSkillGrant, Role, User, UserDept, UserMapping

R4_SKILL_NO = "SKL-R4-SEED"

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


def ensure_r4_skill_grant(db) -> None:
    """种一条已发布、并授权给 R4 角色的技能。运营总监按授权能看到，不是空列表。"""
    role = db.scalar(select(Role).where(Role.role_key == "R4", Role.deleted == 0))
    owner = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    if role is None or owner is None:
        return
    tenant_id = owner.tenant_id or 0
    skill = db.scalar(
        select(AirSkill).where(AirSkill.skill_no == R4_SKILL_NO, AirSkill.tenant_id == tenant_id, AirSkill.deleted == 0)
    )
    now = utcnow()
    if skill is None:
        skill = AirSkill(
            skill_no=R4_SKILL_NO,
            skill_name="运营技能",
            category="内容生产",
            version_label="v1.0",
            status="PUBLISHED",
            audit_status="APPROVED",
            owner_user_id=owner.id,
            grant_count=1,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(skill)
        db.flush()
    else:
        skill.status = "PUBLISHED"
        skill.audit_status = "APPROVED"
        skill.deleted = 0
    grant = db.scalar(
        select(AirSkillGrant).where(
            AirSkillGrant.skill_id == skill.id,
            AirSkillGrant.grant_type == "ROLE",
            AirSkillGrant.grant_id_ref == role.id,
            AirSkillGrant.deleted == 0,
        )
    )
    if grant is None:
        db.add(
            AirSkillGrant(
                skill_id=skill.id,
                grant_type="ROLE",
                grant_id_ref=role.id,
                grant_name=role.role_name or "运营总监",
                all_staff=0,
                status="ACTIVE",
                granted_by=owner.id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
        skill.grant_count = 1
