"""月度绩效闭环基础数据：R5 员工、部门、培训完成与日报按时。

只补岗位和多源取数底账。指标、绑定、计算、核准仍走页面。
任务创建时间固定在 2026-09-01，避开培训看板默认近 30 天。
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    FlowInstance,
    MeetDailyReport,
    PerfCalcDetail,
    PerfCalcResult,
    PerfPeriod,
    PerfRank,
    Role,
    RolePerm,
    TrainTask,
    TrainTaskRecord,
    User,
    UserDept,
    UserRole,
)
from app.scope import refresh_user_scope
from app.security import hash_password

E2E_PERIOD = "2026-09"
E2E_DEPT_ID = 9501
E2E_DEPT_NAME = "直播部"
STAFF_USER = "e2e_perf_staff"
PEER_USER = "e2e_perf_peer"
STAFF_NAME = "绩效员工甲"
PEER_NAME = "绩效员工乙"
ROLE_KEY = "R5"
TASK_NO = "TTE2EPERF95"
HIRED_AT = datetime(2026, 1, 15, 9, 0, 0)
TASK_AT = datetime(2026, 9, 1, 8, 0, 0)


def _ensure_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.role_key == ROLE_KEY, Role.deleted == 0))
    if role is None:
        taken = db.scalar(select(Role.id).where(Role.dingtalk_position == ROLE_KEY, Role.deleted == 0))
        role = Role(
            role_name="直播运营",
            role_key=ROLE_KEY,
            data_scope="SELF",
            dingtalk_position=None if taken else ROLE_KEY,
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    if role.status != "ENABLED":
        role.status = "ENABLED"
    if role.data_scope != "SELF":
        role.data_scope = "SELF"
    if not db.scalar(select(RolePerm.id).where(RolePerm.role_id == role.id)):
        db.add(
            RolePerm(
                role_id=role.id,
                module_code="PERF",
                perm_code="perf:mine",
                perm_level="R",
                tenant_id=0,
            )
        )
    return role


def _ensure_user(db: Session, role: Role, username: str, nickname: str, mobile: str) -> User:
    user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
    if user is None:
        user = User(
            username=username,
            nickname=nickname,
            mobile=mobile,
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
            created_at=HIRED_AT,
        )
        db.add(user)
        db.flush()
    user.nickname = nickname
    user.status = "ENABLED"
    user.created_at = HIRED_AT
    if not db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)):
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
    if not db.scalar(select(UserDept).where(UserDept.user_id == user.id, UserDept.dept_id == E2E_DEPT_ID)):
        db.add(UserDept(user_id=user.id, dept_id=E2E_DEPT_ID, tenant_id=0))
    refresh_user_scope(db, user.id)
    return user


def _daily(
    db: Session,
    user: User,
    report_date: str,
    on_time: int,
) -> None:
    row = db.scalar(
        select(MeetDailyReport).where(
            MeetDailyReport.tenant_id == 0,
            MeetDailyReport.user_id == user.id,
            MeetDailyReport.report_date == report_date,
        )
    )
    if row is None:
        row = MeetDailyReport(
            user_id=user.id,
            dept_id=E2E_DEPT_ID,
            user_name=user.nickname,
            dept_name=E2E_DEPT_NAME,
            report_date=report_date,
            content_done="月度绩效取数底账",
            content_plan="—",
            submit_status="SUBMITTED",
            is_on_time=on_time,
            submitted_at=datetime(2026, 9, 2, 18, 0, 0),
            tenant_id=0,
        )
        db.add(row)
        return
    row.deleted = 0
    row.dept_id = E2E_DEPT_ID
    row.dept_name = E2E_DEPT_NAME
    row.user_name = user.nickname
    row.submit_status = "SUBMITTED"
    row.is_on_time = on_time


def _train(db: Session, staff: User) -> None:
    task = db.scalar(select(TrainTask).where(TrainTask.task_no == TASK_NO, TrainTask.tenant_id == 0))
    if task is None:
        task = TrainTask(
            task_no=TASK_NO,
            task_name="PERF95-TRAIN",
            material_ids=[],
            assign_scope="BY_USER",
            assign_targets=[staff.id],
            confirm_type="DURATION",
            assigned_count=1,
            status="DONE",
            creator_user_id=staff.id,
            tenant_id=0,
            created_at=TASK_AT,
        )
        db.add(task)
        db.flush()
    task.deleted = 0
    task.created_at = TASK_AT
    task.assign_targets = [staff.id]
    task.assigned_count = 1
    task.status = "DONE"
    record = db.scalar(
        select(TrainTaskRecord).where(
            TrainTaskRecord.task_id == task.id,
            TrainTaskRecord.user_id == staff.id,
        )
    )
    if record is None:
        record = TrainTaskRecord(
            task_id=task.id,
            user_id=staff.id,
            progress=100,
            confirm_status=1,
            finished_at=TASK_AT,
            tenant_id=0,
            created_at=TASK_AT,
        )
        db.add(record)
    else:
        record.deleted = 0
        record.progress = 100
        record.confirm_status = 1
        record.finished_at = TASK_AT


def _reset_period(db: Session) -> None:
    result_ids = list(
        db.scalars(select(PerfCalcResult.id).where(PerfCalcResult.period_month == E2E_PERIOD, PerfCalcResult.tenant_id == 0)).all()
    )
    if result_ids:
        db.execute(delete(PerfCalcDetail).where(PerfCalcDetail.result_id.in_(result_ids)))
        db.execute(delete(PerfCalcResult).where(PerfCalcResult.id.in_(result_ids)))
    db.execute(delete(PerfRank).where(PerfRank.period_month == E2E_PERIOD, PerfRank.tenant_id == 0))
    db.execute(delete(PerfPeriod).where(PerfPeriod.period_month == E2E_PERIOD, PerfPeriod.tenant_id == 0))
    db.execute(
        delete(FlowInstance).where(
            FlowInstance.tenant_id == 0,
            FlowInstance.business_key == f"PERF-LOCK-{E2E_PERIOD}",
        )
    )


def refresh_perf_e2e_seed(db: Session, admin: User | None = None) -> None:
    if admin is not None and admin.username != "admin":
        return
    role = _ensure_role(db)
    staff = _ensure_user(db, role, STAFF_USER, STAFF_NAME, "13900009501")
    peer = _ensure_user(db, role, PEER_USER, PEER_NAME, "13900009502")
    _daily(db, staff, "2026-09-02", 1)
    _daily(db, staff, "2026-09-03", 1)
    _daily(db, peer, "2026-09-04", 0)
    _train(db, staff)
    _reset_period(db)
