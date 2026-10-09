"""工作任务确认后的文案草稿。

只写 ``ContentProject.body`` 与 ``ai_generate_status`` / ``ai_generate_error``。
不改 ``layout_html``，不改内容状态，不创建审核单。

状态：
- ``GENERATING`` 生成中（请求内占用，提交后变为终态）
- ``GENERATED`` 已生成
- ``FAILED`` 失败，可经 retry-ai-generate 重试

同一内容在 ``GENERATED`` / ``GENERATING`` 时再次进入本函数不会调用客户端。
"""

from __future__ import annotations

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.content_ai_client import generate_copy, stub_models
from app.models import ContentProject, ContentSopNode, ContentTask, ContentWorkTaskAssignment

GENERATED = "GENERATED"
GENERATING = "GENERATING"
FAILED = "FAILED"
QUEUED = "QUEUED"

_DOC_LABEL = {"COPY": "文案", "SCRIPT": "脚本"}


def default_model_name() -> str:
    rows = stub_models()
    if rows:
        return rows[0]["modelName"]
    return "qwen-plus"


def build_draft_prompt(
    project: ContentProject,
    task: ContentTask | None,
    node: ContentSopNode | None,
    assignment: ContentWorkTaskAssignment | None,
) -> str:
    """用营销计划、SOP 节点与选题（赛事）拼首稿提示。"""
    doc = ""
    if node is not None and node.document_type:
        doc = node.document_type
    elif project.document_type:
        doc = project.document_type
    doc_label = _DOC_LABEL.get(doc, doc or "文案")
    topics: list[str] = []
    source = []
    if assignment is not None and assignment.competitions:
        source = list(assignment.competitions)
    elif task is not None and task.competitions:
        source = list(task.competitions)
    for comp in source:
        if not isinstance(comp, dict):
            continue
        name = str(comp.get("competitionName") or comp.get("leagueName") or comp.get("competitionId") or "").strip()
        league = str(comp.get("leagueName") or "").strip()
        when = str(comp.get("matchTime") or "").strip()
        piece = " ".join(part for part in (name, league, when) if part)
        if piece:
            topics.append(piece)
    marketing = (task.marketing_plan if task else "") or (assignment.marketing_plan if assignment else "")
    plan_name = task.plan_name if task else ""
    work_date = (task.work_date if task else "") or (assignment.work_date if assignment else "")
    node_name = (task.node_name if task else "") or (node.node_name if node else "")
    instruction = ""
    if node is not None:
        instruction = (node.instruction_text or node.standard_desc or "").strip()
    lines = [
        f"请撰写{doc_label}草稿。",
        f"营销计划：{marketing}",
        f"计划：{plan_name}",
        f"工作日：{work_date}",
        f"SOP节点：{node_name}",
        f"文档类型：{doc or 'COPY'}",
        f"选题：{'；'.join(topics) if topics else '未填选题'}",
    ]
    if project.title:
        lines.append(f"标题：{project.title}")
    if instruction:
        lines.append(f"执行说明：{instruction[:500]}")
    lines.append("只输出正文，不要排版，不要提审。")
    return "\n".join(lines)


def _claim(db: Session, project: ContentProject, *, retry: bool) -> bool:
    allowed = [QUEUED]
    if retry:
        allowed.append(FAILED)
    stmt = (
        update(ContentProject)
        .where(
            ContentProject.id == project.id,
            ContentProject.deleted == 0,
            or_(
                ContentProject.ai_generate_status.is_(None),
                ContentProject.ai_generate_status.in_(allowed),
            ),
        )
        .values(ai_generate_status=GENERATING, ai_generate_error=None)
    )
    db.flush()
    result = db.execute(stmt)
    if result.rowcount != 1:
        db.expire(project)
        db.refresh(project)
        return False
    db.expire(project)
    db.refresh(project)
    return True


def generate_draft_for_project(
    db: Session,
    project: ContentProject,
    task: ContentTask | None,
    node: ContentSopNode | None,
    assignment: ContentWorkTaskAssignment | None,
    *,
    retry: bool = False,
) -> str:
    """幂等生成。已生成或生成中直接返回当前状态，不第二次调用客户端。"""
    if not _claim(db, project, retry=retry):
        return project.ai_generate_status or ""
    prompt = build_draft_prompt(project, task, node, assignment)
    generated, err = generate_copy(
        model_name=default_model_name(),
        prompt=prompt,
        round_count=1,
        current_body="",
        history=[],
    )
    if err or generated is None or not str(generated.get("markdown") or "").strip():
        project.ai_generate_status = FAILED
        project.ai_generate_error = (err or "AI 文案生成失败")[:512]
        return FAILED
    project.body = str(generated["markdown"])
    project.ai_generate_status = GENERATED
    project.ai_generate_error = None
    return GENERATED


def retry_project_draft(db: Session, project: ContentProject) -> str:
    task = db.get(ContentTask, project.task_id) if project.task_id else None
    node = db.get(ContentSopNode, task.sop_node_id) if task is not None else None
    assignment = None
    if task is not None and task.assignment_id:
        assignment = db.get(ContentWorkTaskAssignment, task.assignment_id)
    return generate_draft_for_project(db, project, task, node, assignment, retry=True)
