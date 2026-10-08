"""培训统计看板 E2E 种子：一条逾期未完成记录（幂等）。

截止时间在过去，创建时间在 40 天前，避免挤进看板默认近 30 天的完成率口径。
"""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import utcnow
from app.models import TrainMaterial, TrainStatDaily, TrainTask, TrainTaskRecord, User

E2E_OVERDUE_TASK_NAME = "E2E-TRAIN-OD-76"
E2E_OVERDUE_TASK_NO = "TTE2EOD76"
E2E_OVERDUE_MATERIAL = "E2E-TRAIN-OD-76-MAT"


def _purge_prior_closure_rows(db: Session, tenant_id: int) -> None:
    """清掉上一轮 closure 留下的 E2E 学习数据。

    资料热度固定 Top10，且同分按资料编号升序。重复跑全量后旧资料会占满名额，
    新学完的资料进不了看板。逾期种子单独保留。
    """
    task_ids = list(
        db.scalars(
            select(TrainTask.id).where(
                TrainTask.tenant_id == tenant_id,
                TrainTask.task_no != E2E_OVERDUE_TASK_NO,
                TrainTask.task_name.like("E2E%"),
            )
        ).all()
    )
    if task_ids:
        db.execute(delete(TrainTaskRecord).where(TrainTaskRecord.task_id.in_(task_ids)))
        db.execute(delete(TrainTask).where(TrainTask.id.in_(task_ids)))
    material_ids = list(
        db.scalars(
            select(TrainMaterial.id).where(
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.material_no != "MTE2EOD76",
                TrainMaterial.title.like("E2E%"),
            )
        ).all()
    )
    if material_ids:
        db.execute(delete(TrainMaterial).where(TrainMaterial.id.in_(material_ids)))
    db.execute(delete(TrainStatDaily).where(TrainStatDaily.tenant_id == tenant_id))


def refresh_train_stat_e2e_seed(db: Session, admin: User) -> None:
    if admin.username != "admin":
        return
    tenant_id = admin.tenant_id or 0
    _purge_prior_closure_rows(db, tenant_id)
    material = db.scalar(
        select(TrainMaterial).where(
            TrainMaterial.deleted == 0,
            TrainMaterial.tenant_id == tenant_id,
            TrainMaterial.material_no == "MTE2EOD76",
        )
    )
    if material is None:
        material = TrainMaterial(
            material_no="MTE2EOD76",
            title=E2E_OVERDUE_MATERIAL,
            cate_id=0,
            material_type="DOC",
            file_key="train/e2e-overdue.pdf",
            position_codes=["R2"],
            version=1,
            status="PUBLISHED",
            uploader_user_id=admin.id,
            tenant_id=tenant_id,
        )
        db.add(material)
        db.flush()
    else:
        material.title = E2E_OVERDUE_MATERIAL
        material.status = "PUBLISHED"

    now = utcnow()
    created_at = now - timedelta(days=40)
    deadline = now - timedelta(days=10)
    task = db.scalar(
        select(TrainTask).where(
            TrainTask.deleted == 0,
            TrainTask.tenant_id == tenant_id,
            TrainTask.task_no == E2E_OVERDUE_TASK_NO,
        )
    )
    if task is None:
        task = TrainTask(
            task_no=E2E_OVERDUE_TASK_NO,
            task_name=E2E_OVERDUE_TASK_NAME,
            material_ids=[material.id],
            assign_scope="BY_USER",
            assign_targets=[admin.id],
            deadline=deadline,
            confirm_type="DURATION",
            quiz=[],
            pass_score=0,
            assigned_count=1,
            status="IN_PROGRESS",
            creator_user_id=admin.id,
            tenant_id=tenant_id,
            created_at=created_at,
        )
        db.add(task)
        db.flush()
    else:
        task.task_name = E2E_OVERDUE_TASK_NAME
        task.material_ids = [material.id]
        task.deadline = deadline
        task.assigned_count = 1
        task.status = "IN_PROGRESS"
        task.created_at = created_at
        task.deleted = 0

    record = db.scalar(
        select(TrainTaskRecord).where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTaskRecord.task_id == task.id,
            TrainTaskRecord.user_id == admin.id,
        )
    )
    if record is None:
        record = TrainTaskRecord(
            task_id=task.id,
            user_id=admin.id,
            tenant_id=tenant_id,
            created_at=created_at,
        )
        db.add(record)
    record.progress = 40
    record.material_progress = {str(material.id): 40}
    record.confirm_status = 0
    record.confirm_score = None
    record.finished_at = None
    record.study_seconds = 0
    record.deleted = 0
    record.updated_at = now
    db.flush()
