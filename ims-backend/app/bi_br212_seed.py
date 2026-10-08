"""BR-212 E2E/UAT 种子：固定前缀报表 + bi_r4_viewer（DEPT·11）。"""

from __future__ import annotations

import secrets

from sqlalchemy import func, select

from app.core import utcnow
from app.models import BiReportDef, BiShareLink, Role, RoleMenu, RolePerm, User, UserDept, UserRole
from app.scope import refresh_user_scope
from app.security import hash_password

BR212_PREFIX = "BR212-"
SEED_REPORTS = (
    ("dept11-A", 11),
    ("dept11-B", 11),
    ("dept12-C", 12),
)


def _next_report_no(db, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(BiReportDef).where(
            BiReportDef.deleted == 0, BiReportDef.tenant_id == tenant_id
        )
    )
    return f"RPT-{int(count or 0) + 1:04d}"


def _clone_admin_perms(db, role_id: int) -> None:
    admin_role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
    if admin_role is None:
        return
    for rm in db.scalars(select(RoleMenu).where(RoleMenu.role_id == admin_role.id)).all():
        if db.scalar(select(RoleMenu).where(RoleMenu.role_id == role_id, RoleMenu.menu_id == rm.menu_id)):
            continue
        db.add(
            RoleMenu(
                role_id=role_id,
                menu_id=rm.menu_id,
                perm_code=rm.perm_code,
                tenant_id=rm.tenant_id,
            )
        )
    for rp in db.scalars(select(RolePerm).where(RolePerm.role_id == admin_role.id)).all():
        exists = db.scalar(
            select(RolePerm).where(
                RolePerm.role_id == role_id,
                RolePerm.module_code == rp.module_code,
                RolePerm.perm_code == rp.perm_code,
            )
        )
        if exists is None:
            db.add(
                RolePerm(
                    role_id=role_id,
                    module_code=rp.module_code,
                    perm_code=rp.perm_code,
                    perm_level=rp.perm_level,
                    tenant_id=rp.tenant_id,
                )
            )


def ensure_bi_r4_viewer(db) -> None:
    viewer = db.scalar(select(User).where(User.username == "bi_r4_viewer", User.deleted == 0))
    if viewer is None:
        viewer = User(
            username="bi_r4_viewer",
            nickname="BI部门查看者",
            mobile="13900000011",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
        )
        db.add(viewer)
        db.flush()
    role = db.scalar(select(Role).where(Role.role_key == "bi:dept-viewer", Role.deleted == 0))
    if role is None:
        role = Role(
            role_name="BI 本部门查看",
            role_key="bi:dept-viewer",
            data_scope="DEPT",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        _clone_admin_perms(db, role.id)
    if not db.scalar(select(UserDept).where(UserDept.user_id == viewer.id, UserDept.dept_id == 11)):
        db.add(UserDept(user_id=viewer.id, dept_id=11, tenant_id=0))
    if not db.scalar(select(UserRole).where(UserRole.user_id == viewer.id, UserRole.role_id == role.id)):
        db.add(UserRole(user_id=viewer.id, role_id=role.id, tenant_id=0))
    refresh_user_scope(db, viewer.id)


def seed_br212_reports(db, admin: User) -> None:
    tenant_id = admin.tenant_id or 0
    marker = db.scalar(
        select(BiReportDef.id).where(
            BiReportDef.deleted == 0,
            BiReportDef.tenant_id == tenant_id,
            BiReportDef.report_name.like(f"{BR212_PREFIX}%"),
        )
    )
    if marker is not None:
        return
    now = utcnow()
    report_ids: list[tuple[int, int, str]] = []
    for suffix, dept_id in SEED_REPORTS:
        name = f"{BR212_PREFIX}{suffix}"
        row = BiReportDef(
            report_no=_next_report_no(db, tenant_id),
            report_name=name,
            report_type="REPORT",
            category="内容分析",
            sub_category="BR-212",
            status="PUBLISHED",
            layout_json="{}",
            creator_id=admin.id,
            dept_id=dept_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        report_ids.append((row.id, dept_id, name))
    for rid, dept_id, name in report_ids:
        if name != f"{BR212_PREFIX}dept11-A":
            continue
        db.add(
            BiShareLink(
                link_token=secrets.token_hex(8),
                target_type="REPORT",
                target_id=rid,
                target_name=name,
                approval_status="APPROVED",
                expire_at="2099-12-31T23:59:59+08:00",
                creator_user_id=admin.id,
                dept_id=dept_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    if any(d == 12 for _, d, _ in report_ids):
        rid12 = next(rid for rid, d, _ in report_ids if d == 12)
        name12 = next(n for rid, d, n in report_ids if d == 12)
        db.add(
            BiShareLink(
                link_token=secrets.token_hex(8),
                target_type="REPORT",
                target_id=rid12,
                target_name=name12,
                approval_status="APPROVED",
                expire_at="2099-12-31T23:59:59+08:00",
                creator_user_id=admin.id,
                dept_id=12,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    db.flush()


def ensure_bi_br212_seed(db) -> None:
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    if admin is None:
        return
    ensure_bi_r4_viewer(db)
    seed_br212_reports(db, admin)
