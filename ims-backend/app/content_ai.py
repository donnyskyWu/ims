"""内容工作区 AI 文案 + ComfyUI 视频最小闭环。

端点对齐《CONTENT-内容生产-API契约》脚本 / AI 生产 / ai-job，以及补充契约
`POST /content/{id}/retry-ai-generate`。桩开关见 content_ai_client / comfyui_client。
结果写入内容草稿 `body`（文案）与草稿媒体表 `video_file_key`（成片相对路径）。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from app.api import current_user, db_session, fail, ok
from app.content import iso
from app.content_ai_client import CopyJob, copy_status, submit_copy
from app.content_ai_models import ContentAiJob, ContentAiTask, ContentDraftMedia, ContentScript, ContentWorkflow
from app.comfyui_client import VideoJob, prompt_status, provider_name, submit_prompt
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ContentProject, User

router = APIRouter(prefix="/content", tags=["content-ai"])

BJ = timezone(timedelta(hours=8))
CHAIN_TIMEOUT = timedelta(minutes=60)
SCRIPT_TYPES = frozenset({"MONOLOGUE", "STORY", "SALES_PITCH"})
PRIORITIES = frozenset({"P0", "P1", "P2", "P3", "P4"})
DAG_NODES = frozenset({"分镜生成", "视频合成", "配音字幕", "成片"})
EDITABLE = frozenset({"DRAFT", "REJECTED"})
WORKFLOW_CODE = "T2V_DEFAULT"


class ScriptGenerateReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    topicId: int
    contentRequirement: str
    scriptType: str
    candidateCount: int | None = 2


class ScriptEditReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    content: str


class AiTaskCreateReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskNo: str | None = None
    topicId: int | None = None
    scriptId: int | None = None
    requirement: str
    workflowId: int


class PromptReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    promptFinal: str


class ReviewReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    pass_: bool = Field(alias="pass")
    comment: str | None = None


class RetryNodeReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    nodeName: str


class AiJobSubmitReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskNo: str
    workflowId: int
    nodeName: str
    params: dict = Field(default_factory=dict)
    priority: str = "P2"


def _tenant(actor: User) -> int:
    return tenant_of(actor)


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _project(db: Session, content_id: int, actor: User) -> ContentProject | None:
    row = db.get(ContentProject, content_id)
    if row is None or row.deleted or (row.tenant_id or 0) != _tenant(actor):
        return None
    return row


def ensure_workflow(db: Session) -> ContentWorkflow:
    row = db.scalar(
        select(ContentWorkflow).where(ContentWorkflow.workflow_code == WORKFLOW_CODE, ContentWorkflow.deleted == 0)
    )
    if row is None:
        row = ContentWorkflow(
            workflow_code=WORKFLOW_CODE,
            workflow_name="图生视频（默认）",
            enabled=1,
            param_schema={"required": []},
            tenant_id=0,
        )
        db.add(row)
        db.flush()
    return row


def _media(db: Session, project: ContentProject) -> ContentDraftMedia:
    row = db.scalar(select(ContentDraftMedia).where(ContentDraftMedia.content_project_id == project.id))
    if row is None:
        row = ContentDraftMedia(content_project_id=project.id, tenant_id=project.tenant_id or 0)
        db.add(row)
        db.flush()
    return row


def media_fields(project: ContentProject) -> dict:
    empty = {
        "videoJobStatus": None,
        "videoFileKey": None,
        "videoJobError": None,
        "videoTaskNo": None,
        "videoJobId": None,
        "videoRetryHint": None,
        "defaultWorkflowId": None,
    }
    db = object_session(project)
    if db is None:
        return empty
    wf = ensure_workflow(db)
    empty["defaultWorkflowId"] = wf.id
    media = db.scalar(select(ContentDraftMedia).where(ContentDraftMedia.content_project_id == project.id))
    if media is None:
        return empty
    status = media.video_status
    hint = None
    if status in ("FAILED", "REVIEW_REJECTED"):
        hint = media.video_error or "可重新发起"
        if "重新发起" not in hint:
            hint = f"{hint}，可重新发起"
    empty.update(
        {
            "videoJobStatus": status,
            "videoFileKey": media.video_file_key,
            "videoJobError": media.video_error,
            "videoTaskNo": media.video_task_no or None,
            "videoJobId": media.video_job_id,
            "videoRetryHint": hint,
        }
    )
    return empty


def ai_publish_block(db: Session, project: ContentProject) -> str | None:
    task = db.scalar(
        select(ContentAiTask)
        .where(ContentAiTask.content_project_id == project.id, ContentAiTask.deleted == 0)
        .order_by(ContentAiTask.id.desc())
    )
    if task is None:
        return None
    if task.task_status != "REVIEW_PASSED":
        return "终审未通过禁止发布"
    return None


def _script_vo(row: ContentScript) -> dict:
    return {
        "id": row.id,
        "topicId": row.topic_id,
        "scriptType": row.script_type,
        "content": row.content,
        "version": row.version,
        "aiGenerated": bool(row.ai_generated),
        "promptSnapshot": row.prompt_snapshot or "",
        "status": row.status,
        "authorUserId": row.author_user_id,
        "createdAt": iso(row.created_at),
    }


def _workflow(db: Session, workflow_id: int) -> ContentWorkflow | None:
    row = db.get(ContentWorkflow, workflow_id)
    if row is None or row.deleted:
        return None
    return row


def _task_by_no(db: Session, task_no: str, actor: User) -> ContentAiTask | None:
    row = db.scalar(
        select(ContentAiTask).where(
            ContentAiTask.task_no == task_no,
            ContentAiTask.deleted == 0,
            ContentAiTask.tenant_id == _tenant(actor),
        )
    )
    return row


def _task_vo(row: ContentAiTask, wf: ContentWorkflow | None = None) -> dict:
    return {
        "id": row.id,
        "taskNo": row.task_no,
        "topicId": row.topic_id,
        "scriptId": row.script_id,
        "requirement": row.requirement,
        "promptInitial": row.prompt_initial,
        "promptFinal": row.prompt_final,
        "workflowId": row.workflow_id,
        "workflowCode": wf.workflow_code if wf else "",
        "taskStatus": row.task_status,
        "outputFileUrl": row.output_file_url,
        "reviewerUserId": row.reviewer_user_id,
        "createdBy": row.creator,
        "createdAt": iso(row.created_at),
        "errorCode": row.error_code,
        "errorMsg": row.error_msg,
        "retryHint": "可重新发起" if row.task_status in ("FAILED", "REVIEW_REJECTED") else None,
    }


def _job_vo(row: ContentAiJob, task: ContentAiTask | None = None) -> dict:
    ready = row.queue_status == "SUCCESS" and bool(row.result_file_key)
    bound_id = task.content_project_id if task is not None and ready else None
    return {
        "id": row.id,
        "taskNo": row.task_no,
        "workflowId": row.workflow_id,
        "nodeName": row.node_name,
        "priority": row.priority,
        "queueStatus": row.queue_status,
        "gpuNode": row.gpu_node,
        "resultFileKey": row.result_file_key,
        "submittedAt": iso(row.submitted_at) if row.submitted_at else iso(row.created_at),
        "progress": row.progress,
        "queuePosition": 1 if row.queue_status == "WAITING" else None,
        "etaMinutes": None,
        "errorCode": row.error_code,
        "errorMsg": row.error_msg,
        "retryHint": "可重新发起" if row.queue_status == "FAILED" else None,
        "provider": provider_name(),
        "boundContentId": bound_id,
        "preview": {"fileKey": row.result_file_key, "kind": "video", "ready": True} if ready else None,
    }


def _next_task_no(db: Session) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"AIP{day}"
    count = db.scalar(select(func.count()).select_from(ContentAiTask).where(ContentAiTask.task_no.like(f"{prefix}%")))
    return f"{prefix}{int(count or 0) + 1:04d}"


def _link_project(db: Session, topic_id: int | None, actor: User) -> ContentProject | None:
    if not topic_id:
        return None
    return _project(db, topic_id, actor)


def _require_matches(project: ContentProject):
    scheme = project.match_scheme or []
    if not isinstance(scheme, list) or len(scheme) < 1:
        return fail(1500, "请先选择比赛")
    return None


def _apply_copy(
    db: Session,
    actor: User,
    project: ContentProject | None,
    job: CopyJob,
    script_type: str,
    snapshot: str,
    topic_id: int,
):
    if project is not None:
        media = _media(db, project)
        if job.upstream_id:
            media.copy_upstream_id = job.upstream_id[:64]
    if not job.ok or job.status == "FAILED":
        if project is not None:
            project.ai_generate_status = "FAILED"
            project.ai_generate_error = (job.message or "文案生成失败，可重新发起")[:512]
        return None
    if job.status != "SUCCESS":
        if project is not None:
            project.ai_generate_status = "GENERATING" if job.status == "GENERATING" else "QUEUED"
            project.ai_generate_error = None
        return None
    rows: list[ContentScript] = []
    topic_id = project.id if project is not None else topic_id
    for text in job.copies:
        row = ContentScript(
            topic_id=topic_id,
            script_type=script_type,
            content=text,
            version=1,
            ai_generated=1,
            prompt_snapshot=snapshot,
            status="DRAFT",
            content_hash=_hash(text),
            author_user_id=actor.id,
            creator=actor.id,
            tenant_id=_tenant(actor),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    if project is not None and rows:
        project.body = rows[0].content
        project.ai_generate_status = "SUCCESS"
        project.ai_generate_error = None
    return rows


def _settle_copy(requirement: str, script_type: str, count: int, upstream_id: str | None) -> CopyJob:
    if upstream_id:
        job = copy_status(upstream_id)
    else:
        job = submit_copy(requirement=requirement, script_type=script_type, candidate_count=count)
    for _ in range(4):
        if not job.ok or job.status in ("SUCCESS", "FAILED"):
            return job
        if not job.upstream_id:
            return job
        job = copy_status(job.upstream_id)
    return job


def _run_copy(
    db: Session,
    actor: User,
    *,
    project: ContentProject | None,
    requirement: str,
    script_type: str,
    candidate_count: int,
    resume: bool,
) -> tuple[CopyJob, list[ContentScript] | None]:
    upstream = None
    if resume and project is not None and project.ai_generate_status in ("QUEUED", "GENERATING"):
        media = _media(db, project)
        upstream = media.copy_upstream_id or None
    elif project is not None:
        project.ai_generate_status = "QUEUED"
        project.ai_generate_error = None
    snapshot = f"content-ai/{script_type}/n={candidate_count}"
    job = _settle_copy(requirement, script_type, candidate_count, upstream)
    topic_id = project.id if project is not None else 0
    rows = _apply_copy(db, actor, project, job, script_type, snapshot, topic_id)
    return job, rows


def retry_copy(content_id: int, db: Session, actor: User):
    project = _project(db, content_id, actor)
    if project is None:
        return fail(1504, "资源不可用")
    if project.ai_generate_status in ("QUEUED", "GENERATING"):
        return fail(1502, "生成进行中，请稍后")
    if project.ai_generate_status != "FAILED":
        return fail(1502, "当前不可重试")
    blocked = _require_matches(project)
    if blocked is not None:
        return blocked
    requirement = (project.body or project.title or "内容草稿").strip()
    job, _rows = _run_copy(
        db,
        actor,
        project=project,
        requirement=requirement,
        script_type="MONOLOGUE",
        candidate_count=2,
        resume=False,
    )
    if not job.ok or job.status == "FAILED":
        return fail(job.code or 1001, job.message or "文案生成失败，可重新发起")
    from app.content_production import project_vo

    return ok(project_vo(project))


def _sync_task_from_job(db: Session, task: ContentAiTask, job: ContentAiJob) -> None:
    project = db.get(ContentProject, task.content_project_id) if task.content_project_id else None
    media = _media(db, project) if project is not None else None
    if job.queue_status == "SUCCESS" and job.result_file_key:
        task.task_status = "PENDING_FINAL_REVIEW"
        task.output_file_url = job.result_file_key
        task.error_code = None
        task.error_msg = None
        if media is not None:
            media.video_status = task.task_status
            media.video_file_key = job.result_file_key
            media.video_error = None
            media.video_task_no = task.task_no
            media.video_job_id = job.id
            media.updated_at = utcnow()
        return
    if job.queue_status == "FAILED":
        task.task_status = "FAILED"
        task.error_code = job.error_code
        task.error_msg = job.error_msg
        if media is not None:
            media.video_status = "FAILED"
            media.video_error = job.error_msg
            media.video_task_no = task.task_no
            media.video_job_id = job.id
            media.updated_at = utcnow()
        return
    if job.queue_status == "GENERATING":
        task.task_status = "GENERATING"
    elif job.queue_status == "WAITING":
        task.task_status = "WAITING"
    if media is not None:
        media.video_status = task.task_status
        media.video_task_no = task.task_no
        media.video_job_id = job.id
        media.updated_at = utcnow()


def _timed_out(job: ContentAiJob) -> bool:
    if job.queue_status in ("SUCCESS", "FAILED"):
        return False
    started = job.submitted_at or job.created_at
    if started is None:
        return False
    return utcnow() - started > CHAIN_TIMEOUT


def _fail_timeout(db: Session, task: ContentAiTask, job: ContentAiJob):
    message = "全链路超时，可重新发起"
    job.queue_status = "FAILED"
    job.error_code = 1056
    job.error_msg = message
    job.progress = None
    task.task_status = "FAILED"
    task.error_code = 1056
    task.error_msg = message
    project = db.get(ContentProject, task.content_project_id) if task.content_project_id else None
    if project is not None:
        media = _media(db, project)
        media.video_status = "FAILED"
        media.video_error = message
        media.video_task_no = task.task_no
        media.video_job_id = job.id
        media.updated_at = utcnow()
    return fail(1056, message, _job_vo(job, task))


def _pull_job(db: Session, task: ContentAiTask, job: ContentAiJob):
    if _timed_out(job):
        return _fail_timeout(db, task, job)
    upstream = prompt_status(job.upstream_id) if job.upstream_id else VideoJob(False, 1001, "视频任务不存在", status="FAILED")
    _apply_upstream(job, upstream)
    _sync_task_from_job(db, task, job)
    if not upstream.ok or job.queue_status == "FAILED":
        return fail(upstream.code or job.error_code or 1001, upstream.message or job.error_msg or "视频生成失败，可重新发起", _job_vo(job, task))
    return ok(_job_vo(job, task))


def _apply_upstream(job: ContentAiJob, upstream: VideoJob) -> None:
    if upstream.upstream_id and not job.upstream_id:
        job.upstream_id = upstream.upstream_id[:64]
    job.progress = upstream.progress
    job.gpu_node = None
    if not upstream.ok or upstream.status == "FAILED":
        job.queue_status = "FAILED"
        job.error_code = upstream.code or 1001
        job.error_msg = (upstream.message or "视频生成失败，可重新发起")[:512]
        return
    job.queue_status = upstream.status or "WAITING"
    if upstream.status == "SUCCESS":
        job.result_file_key = upstream.file_key or job.result_file_key
        job.error_code = None
        job.error_msg = None


def _submit_job_row(db: Session, actor: User, task: ContentAiTask, wf: ContentWorkflow, node_name: str, params: dict, priority: str):
    required = []
    schema = wf.param_schema or {}
    if isinstance(schema, dict):
        required = list(schema.get("required") or [])
    for key in required:
        if key not in params or params.get(key) in ("", None):
            return None, fail(1001, "params 不符合 paramSchema")
    upstream = submit_prompt(params)
    job = ContentAiJob(
        task_no=task.task_no,
        workflow_id=wf.id,
        node_name=node_name[:64],
        priority=priority,
        queue_status="WAITING",
        gpu_node=None,
        upstream_id=(upstream.upstream_id or "")[:64],
        progress=upstream.progress,
        params=params,
        submitted_at=utcnow(),
        tenant_id=_tenant(actor),
    )
    if not upstream.ok or upstream.status == "FAILED":
        job.queue_status = "FAILED"
        job.error_code = upstream.code or 1001
        job.error_msg = (upstream.message or "视频生成失败，可重新发起")[:512]
    db.add(job)
    db.flush()
    task.submitted_at = job.submitted_at
    _sync_task_from_job(db, task, job)
    if job.queue_status == "FAILED":
        return job, fail(job.error_code or 1001, job.error_msg or "视频生成失败，可重新发起", _job_vo(job, task))
    return job, None


def _latest_job(db: Session, task_no: str) -> ContentAiJob | None:
    return db.scalar(select(ContentAiJob).where(ContentAiJob.task_no == task_no).order_by(ContentAiJob.id.desc()))


@router.post("/script/generate")
def script_generate(body: ScriptGenerateReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    requirement = (body.contentRequirement or "").strip()
    if body.topicId <= 0 or not requirement or len(requirement) > 4000:
        return fail(1500, "参数校验失败")
    script_type = (body.scriptType or "").strip().upper()
    if script_type not in SCRIPT_TYPES:
        return fail(1500, "参数校验失败")
    count = body.candidateCount if body.candidateCount is not None else 2
    if count < 2 or count > 3:
        return fail(1500, "参数校验失败")
    project = _link_project(db, body.topicId, actor)
    if project is not None:
        if project.content_status not in EDITABLE:
            return fail(1502, "业务规则冲突")
        blocked = _require_matches(project)
        if blocked is not None:
            return blocked
        if project.ai_generate_status in ("QUEUED", "GENERATING"):
            return fail(1502, "生成进行中，请稍后")
    job, rows = _run_copy(
        db,
        actor,
        project=project,
        requirement=requirement,
        script_type=script_type,
        candidate_count=count,
        resume=False,
    )
    if not job.ok or job.status == "FAILED":
        return fail(job.code or 1001, job.message or "文案生成失败，可重新发起")
    if job.status != "SUCCESS" or not rows:
        return ok({"candidates": [], "promptSnapshot": f"content-ai/{script_type}/n={count}", "aiGenerateStatus": "GENERATING"})
    return ok({"candidates": [_script_vo(row) for row in rows], "promptSnapshot": rows[0].prompt_snapshot})


@router.get("/script/list")
def script_list(
    topicId: int | None = None,
    scriptType: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentScript).where(ContentScript.deleted == 0, ContentScript.tenant_id == _tenant(actor))
    if topicId:
        stmt = stmt.where(ContentScript.topic_id == topicId)
    if scriptType:
        stmt = stmt.where(ContentScript.script_type == scriptType.strip().upper())
    if status:
        stmt = stmt.where(ContentScript.status == status.strip().upper())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(stmt.order_by(ContentScript.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([_script_vo(row) for row in rows], total, page_no, size)


@router.put("/script/{script_id}")
def script_edit(script_id: int, body: ScriptEditReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = db.get(ContentScript, script_id)
    if row is None or row.deleted or (row.tenant_id or 0) != _tenant(actor):
        return fail(1504, "资源不可用")
    if row.status == "FINALIZED":
        return fail(1502, "业务规则冲突")
    text = (body.content or "").strip()
    if not text:
        return fail(1500, "参数校验失败")
    if text == (row.content or "").strip():
        return fail(1001, "请先人工润色后再定稿")
    newer = ContentScript(
        topic_id=row.topic_id,
        script_type=row.script_type,
        content=text,
        version=row.version + 1,
        ai_generated=0,
        prompt_snapshot=row.prompt_snapshot,
        status="DRAFT",
        content_hash=_hash(text),
        author_user_id=actor.id,
        creator=actor.id,
        tenant_id=_tenant(actor),
    )
    db.add(newer)
    db.flush()
    return ok(_script_vo(newer))


@router.put("/script/{script_id}/finalize")
def script_finalize(script_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = db.get(ContentScript, script_id)
    if row is None or row.deleted or (row.tenant_id or 0) != _tenant(actor):
        return fail(1504, "资源不可用")
    if row.status == "FINALIZED":
        return ok(None)
    if row.ai_generated and _hash(row.content or "") == (row.content_hash or ""):
        return fail(1001, "请先人工润色后再定稿")
    row.status = "FINALIZED"
    return ok(None)


@router.get("/script/{script_id}/versions")
def script_versions(script_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = db.get(ContentScript, script_id)
    if row is None or row.deleted or (row.tenant_id or 0) != _tenant(actor):
        return fail(1504, "资源不可用")
    rows = db.scalars(
        select(ContentScript)
        .where(
            ContentScript.deleted == 0,
            ContentScript.tenant_id == _tenant(actor),
            ContentScript.topic_id == row.topic_id,
            ContentScript.script_type == row.script_type,
        )
        .order_by(ContentScript.version, ContentScript.id)
    ).all()
    versions = [
        {
            "id": item.id,
            "version": item.version,
            "aiGenerated": bool(item.ai_generated),
            "content": item.content,
            "authorUserId": item.author_user_id,
            "createdAt": iso(item.created_at),
        }
        for item in rows
    ]
    return ok({"versions": versions})


@router.post("/ai-production/task")
def ai_task_create(body: AiTaskCreateReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    requirement = (body.requirement or "").strip()
    if not requirement or len(requirement) > 4000:
        return fail(1500, "参数校验失败")
    wf = _workflow(db, body.workflowId)
    if wf is None or not wf.enabled:
        return fail(1051, "工作流不存在或未启用")
    script_id = body.scriptId
    if script_id:
        script = db.get(ContentScript, script_id)
        if script is None or script.deleted or (script.tenant_id or 0) != _tenant(actor):
            return fail(1053, "脚本未定稿")
        if script.status != "FINALIZED":
            return fail(1053, "脚本未定稿")
    project = _link_project(db, body.topicId, actor)
    if project is not None:
        blocked = _require_matches(project)
        if blocked is not None:
            return blocked
    prompt = requirement[:2000]
    task = ContentAiTask(
        task_no=(body.taskNo or "").strip() or _next_task_no(db),
        topic_id=body.topicId,
        script_id=script_id,
        content_project_id=project.id if project is not None else None,
        requirement=requirement,
        prompt_initial=prompt,
        prompt_final=prompt,
        workflow_id=wf.id,
        task_status="WAITING",
        creator=actor.id,
        tenant_id=_tenant(actor),
    )
    db.add(task)
    db.flush()
    if project is not None:
        media = _media(db, project)
        media.video_task_no = task.task_no
        media.video_status = "WAITING"
        media.video_error = None
        media.updated_at = utcnow()
    return ok(_task_vo(task, wf))


@router.get("/ai-production/task/page")
def ai_task_page(
    pageNum: int = 1,
    pageNo: int = 0,
    pageSize: int = 20,
    keyword: str | None = None,
    taskStatus: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo or pageNum, pageSize)
    stmt = select(ContentAiTask).where(ContentAiTask.deleted == 0, ContentAiTask.tenant_id == _tenant(actor))
    if keyword:
        stmt = stmt.where(ContentAiTask.task_no.contains(keyword.strip()))
    if taskStatus:
        stmt = stmt.where(ContentAiTask.task_status == taskStatus.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(stmt.order_by(ContentAiTask.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    wf_ids = {row.workflow_id for row in rows}
    workflows = {}
    if wf_ids:
        for wf in db.scalars(select(ContentWorkflow).where(ContentWorkflow.id.in_(wf_ids))).all():
            workflows[wf.id] = wf
    return ok(
        {
            "total": total,
            "records": [_task_vo(row, workflows.get(row.workflow_id)) for row in rows],
        }
    )


def _dag(db: Session, task: ContentAiTask) -> list[dict]:
    jobs = db.scalars(select(ContentAiJob).where(ContentAiJob.task_no == task.task_no).order_by(ContentAiJob.id)).all()
    nodes = []
    for job in jobs:
        run_status = {"WAITING": "PENDING", "GENERATING": "RUNNING", "SUCCESS": "SUCCESS", "FAILED": "FAILED"}.get(
            job.queue_status, "PENDING"
        )
        nodes.append(
            {
                "id": job.id,
                "taskNo": task.task_no,
                "nodeName": job.node_name,
                "nodeType": "COMFYUI",
                "inputUrl": None,
                "outputUrl": job.result_file_key,
                "runStatus": run_status,
                "retryCount": job.retry_count,
                "startedAt": iso(job.submitted_at) if job.submitted_at else None,
                "finishedAt": iso(job.created_at) if job.queue_status in ("SUCCESS", "FAILED") else None,
                "errorMsg": job.error_msg,
            }
        )
    return nodes


@router.get("/ai-production/task/{task_no}")
def ai_task_detail(task_no: str, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    wf = _workflow(db, task.workflow_id)
    data = _task_vo(task, wf)
    data["dagNodes"] = _dag(db, task)
    return ok(data)


@router.get("/ai-production/runs/{task_no}")
def ai_task_runs(task_no: str, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    return ok(_dag(db, task))


@router.put("/ai-production/task/{task_no}/prompt")
def ai_task_prompt(task_no: str, body: PromptReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    text = (body.promptFinal or "").strip()
    if not text:
        return fail(1500, "参数校验失败")
    task.prompt_final = text[:4000]
    return ok(None)


@router.post("/ai-production/task/{task_no}/run")
def ai_task_run(task_no: str, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    if task.task_status in ("GENERATING", "PENDING_FINAL_REVIEW", "REVIEW_PASSED"):
        return fail(1502, "业务规则冲突")
    wf = _workflow(db, task.workflow_id)
    if wf is None or not wf.enabled:
        return fail(1051, "工作流不存在或未启用")
    params = {"text": task.prompt_final or task.requirement}
    job, err = _submit_job_row(db, actor, task, wf, "成片", params, "P2")
    if err is not None:
        return err
    assert job is not None
    response = ok(_job_vo(job, task))
    for _ in range(4):
        if job.queue_status in ("SUCCESS", "FAILED"):
            break
        response = _pull_job(db, task, job)
        if job.queue_status == "FAILED":
            return response
    return ok({"jobIds": [job.id], "message": "已提交", "taskStatus": task.task_status})


@router.put("/ai-production/task/{task_no}/review")
def ai_task_review(task_no: str, body: ReviewReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    if task.task_status != "PENDING_FINAL_REVIEW":
        return fail(1502, "业务规则冲突")
    task.reviewer_user_id = actor.id
    if body.pass_:
        task.task_status = "REVIEW_PASSED"
        task.error_code = None
        task.error_msg = None
    else:
        task.task_status = "REVIEW_REJECTED"
        note = (body.comment or "终审打回，可重新发起").strip()
        if "重新发起" not in note:
            note = f"{note}，可重新发起"
        task.error_msg = note[:512]
    project = db.get(ContentProject, task.content_project_id) if task.content_project_id else None
    if project is not None:
        media = _media(db, project)
        media.video_status = task.task_status
        media.video_error = task.error_msg
        media.video_task_no = task.task_no
        media.updated_at = utcnow()
    return ok(None)


@router.post("/ai-production/task/{task_no}/retry-node")
def ai_task_retry_node(task_no: str, body: RetryNodeReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    task = _task_by_no(db, task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    node = (body.nodeName or "").strip()
    if node not in DAG_NODES:
        return fail(1055, "节点非法")
    if task.task_status in ("GENERATING", "REVIEW_PASSED"):
        return fail(1502, "业务规则冲突")
    wf = _workflow(db, task.workflow_id)
    if wf is None or not wf.enabled:
        return fail(1051, "工作流不存在或未启用")
    prev = _latest_job(db, task.task_no)
    params = {"text": task.prompt_final or task.requirement, "nodeName": node}
    job, err = _submit_job_row(db, actor, task, wf, node, params, "P2")
    if err is not None:
        return err
    assert job is not None
    if prev is not None:
        job.retry_count = (prev.retry_count or 0) + 1
    for _ in range(4):
        if job.queue_status in ("SUCCESS", "FAILED"):
            break
        pulled = _pull_job(db, task, job)
        if job.queue_status == "FAILED":
            return pulled
    return ok(None)


@router.post("/ai-job/submit")
def ai_job_submit(body: AiJobSubmitReq, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    priority = (body.priority or "").strip().upper()
    if priority not in PRIORITIES:
        return fail(1001, "params 不符合 paramSchema")
    node = (body.nodeName or "").strip()
    if not node:
        return fail(1001, "params 不符合 paramSchema")
    task = _task_by_no(db, (body.taskNo or "").strip(), actor)
    if task is None:
        return fail(1504, "资源不可用")
    wf = _workflow(db, body.workflowId)
    if wf is None or not wf.enabled:
        return fail(1051, "工作流不存在或未启用")
    if task.workflow_id != wf.id:
        return fail(1051, "工作流不存在或未启用")
    params = body.params or {}
    job, err = _submit_job_row(db, actor, task, wf, node, params, priority)
    if err is not None:
        return err
    return ok(_job_vo(job, task))


@router.get("/ai-job/{job_id}/status")
def ai_job_status(job_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    job = db.get(ContentAiJob, job_id)
    if job is None or (job.tenant_id or 0) != _tenant(actor):
        return fail(1504, "资源不可用")
    task = _task_by_no(db, job.task_no, actor)
    if task is None:
        return fail(1504, "资源不可用")
    if job.queue_status in ("SUCCESS", "FAILED"):
        return ok(_job_vo(job, task))
    return _pull_job(db, task, job)
