"""PERF-003 试卷：固定/随机组卷（1159/1160）与补考（MAKEUP_EXAM，PER-E-R3）。"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ExamAssignment, ExamPaper, ExamQuestion, ExamRecord, Todo, User

router = APIRouter(tags=["perf-exam"])

BJ = timezone(timedelta(hours=8))
DOMAINS = frozenset({"LIVE_RULE", "CONTENT_SKILL", "LIVE_SKILL", "DATA_SKILL", "COMPLIANCE"})
TYPE_ALIAS = {
    "SINGLE": "SINGLE",
    "MULTI": "MULTIPLE",
    "MULTIPLE": "MULTIPLE",
    "JUDGE": "JUDGE",
    "SHORT_ANSWER": "ESSAY",
    "ESSAY": "ESSAY",
}
SUBJECTIVE = frozenset({"ESSAY"})
GRADE_OVERDUE = timedelta(hours=48)
EXAM_TASK = "exam"
EXAM_REF = "exam_paper"
# 种子题答案。题库没有难度字段，抽题只按知识域 + 题型，题目 id 去重。
SEED_ANSWERS: dict[str, dict] = {
    "EQ-001": {
        "options": ["观众数不低于开播前预告的 50%", "在线人数不低于峰值 30%", "没有硬性红线", "达到 1,000 人"],
        "answer": 1,
    },
    "EQ-002": {
        "options": ["引导线下交易", "口播极限词", "未报备更换直播场地", "挂小黄车"],
        "answer": [0, 1],
    },
    "EQ-003": {"options": ["对", "错"], "answer": False},
    "EQ-004": {"options": ["前 3 秒", "第 15 秒", "第 30 秒", "第 60 秒"], "answer": 0},
    "EQ-005": {"options": ["先讲产品参数", "开头先说用户痛点", "结尾才抛问题", "只放字幕"], "answer": 1},
    "EQ-006": {"options": None, "answer": "先测人群再放量"},
    "EQ-007": {"options": ["消耗/成交", "成交金额/消耗", "曝光/点击", "点击/成交"], "answer": 1},
    "EQ-008": {"options": None, "answer": "净 GMV 扣除退款"},
    "EQ-009": {"options": ["20:00", "22:00", "23:00", "次日 09:00"], "answer": 1},
    "EQ-010": {"options": ["对", "错"], "answer": False},
}


def q2(value) -> Decimal:
    return Decimal(str(0 if value is None else value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def parse_instant(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BJ)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def canonical_type(raw: str) -> str | None:
    return TYPE_ALIAS.get((raw or "").strip().upper())


def ensure_bank(db: Session, actor: User) -> None:
    from app.perf import ensure_exam_questions

    ensure_exam_questions(db, tenant_of(actor), actor.id)


def backfill_question_answers(db: Session, tenant_id: int) -> None:
    rows = db.scalars(
        select(ExamQuestion).where(ExamQuestion.deleted == 0, ExamQuestion.tenant_id == tenant_id)
    ).all()
    changed = False
    for row in rows:
        seed = SEED_ANSWERS.get(row.question_no)
        if seed is None or row.answer is not None:
            continue
        row.options = seed["options"]
        row.answer = seed["answer"]
        row.updated_at = utcnow()
        changed = True
    if changed:
        db.flush()


def stock_questions(db: Session, tenant_id: int, domain: str, qtype: str) -> list[ExamQuestion]:
    return list(
        db.scalars(
            select(ExamQuestion)
            .where(
                ExamQuestion.deleted == 0,
                ExamQuestion.tenant_id == tenant_id,
                ExamQuestion.knowledge_domain == domain,
                ExamQuestion.question_type == qtype,
            )
            .order_by(ExamQuestion.id.asc())
        ).all()
    )


class StrategyRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    knowledge_domain: str = Field(alias="knowledgeDomain")
    question_type: str = Field(alias="questionType")
    count: int
    score_per_question: float = Field(alias="scorePerQuestion")


class PaperBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    paper_name: str = Field(alias="paperName")
    paper_type: str = Field(alias="paperType")
    question_ids: list[int] | None = Field(default=None, alias="questionIds")
    strategy: list[StrategyRow] | None = None
    total_score: float = Field(alias="totalScore")
    pass_score: float = Field(alias="passScore")
    duration_minutes: int = Field(alias="durationMinutes")


class WindowBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    start: str = Field(alias="from")
    to: str


class AssignBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_ids: list[int] = Field(alias="userIds")
    exam_window: WindowBody = Field(alias="examWindow")


class StartBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    paper_id: int = Field(alias="paperId")


class AnswerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    question_id: int = Field(alias="questionId")
    answer: object


class SubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    record_id: int = Field(alias="recordId")
    answers: list[AnswerBody]
    switch_screen_count: int = Field(default=0, alias="switchScreenCount")


class GradeItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    question_id: int = Field(alias="questionId")
    score: float
    comment: str | None = None


class GradeBody(BaseModel):
    gradings: list[GradeItem]


def paper_of(db: Session, tenant_id: int, paper_id: int) -> ExamPaper | None:
    row = db.get(ExamPaper, paper_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


def paper_vo(row: ExamPaper) -> dict:
    strategy = row.strategy or []
    question_ids = row.question_ids or []
    if row.paper_type == "RANDOM":
        question_count = sum(int(item.get("count") or 0) for item in strategy)
    else:
        question_count = len(question_ids)
    data = {
        "id": row.id,
        "paperNo": row.paper_no,
        "paperName": row.paper_name,
        "paperType": row.paper_type,
        "totalScore": row.total_score,
        "passScore": row.pass_score,
        "durationMinutes": row.duration_minutes,
        "status": row.status,
        "assignedCount": row.assigned_count,
        "questionCount": question_count,
    }
    if row.paper_type == "FIXED":
        data["questionIds"] = question_ids
    else:
        data["strategy"] = strategy
    return data


def next_paper_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"EP{day}"
    count = db.scalar(
        select(func.count())
        .select_from(ExamPaper)
        .where(ExamPaper.tenant_id == tenant_id, ExamPaper.paper_no.like(f"{prefix}%"))
    )
    return f"{prefix}{int(count or 0) + 1:04d}"


def check_strategy(db: Session, tenant_id: int, rows: list[StrategyRow]):
    if not rows:
        return fail(1001, "随机组卷策略必填"), None
    normalized = []
    reserved: dict[tuple[str, str], int] = {}
    total = Decimal("0")
    for row in rows:
        domain = (row.knowledge_domain or "").strip().upper()
        qtype = canonical_type(row.question_type)
        if domain not in DOMAINS:
            return fail(1001, "知识域无效"), None
        if qtype is None:
            return fail(1001, "题型无效"), None
        if row.count < 1:
            return fail(1001, "抽题数须大于 0"), None
        if q2(row.score_per_question) <= 0:
            return fail(1001, "每题分值须大于 0"), None
        pool = stock_questions(db, tenant_id, domain, qtype)
        key = (domain, qtype)
        used = reserved.get(key, 0)
        available = len(pool) - used
        if row.count > available:
            return fail(1160, f"题库存量仅 {max(available, 0)} 题"), None
        reserved[key] = used + row.count
        total += q2(row.score_per_question) * row.count
        normalized.append(
            {
                "knowledgeDomain": domain,
                "questionType": qtype,
                "count": row.count,
                "scorePerQuestion": float(q2(row.score_per_question)),
            }
        )
    return None, (normalized, total)


def draw_questions(db: Session, tenant_id: int, paper: ExamPaper):
    picked: list[tuple[ExamQuestion, Decimal]] = []
    if paper.paper_type == "FIXED":
        ids = [int(item) for item in (paper.question_ids or [])]
        rows = {
            row.id: row
            for row in db.scalars(
                select(ExamQuestion).where(
                    ExamQuestion.id.in_(ids),
                    ExamQuestion.deleted == 0,
                    ExamQuestion.tenant_id == tenant_id,
                )
            ).all()
        }
        for qid in ids:
            question = rows.get(qid)
            if question is None:
                return fail(1001, "题目不存在"), None
            picked.append((question, q2(question.score)))
        return None, picked

    used: set[int] = set()
    for item in paper.strategy or []:
        domain = item["knowledgeDomain"]
        qtype = item["questionType"]
        count = int(item["count"])
        pool = [row for row in stock_questions(db, tenant_id, domain, qtype) if row.id not in used]
        if len(pool) < count:
            return fail(1160, f"题库存量仅 {len(pool)} 题"), None
        chosen = random.sample(pool, count)
        for question in chosen:
            used.add(question.id)
            picked.append((question, q2(item["scorePerQuestion"])))
    return None, picked


def snapshot(picked: list[tuple[ExamQuestion, Decimal]]) -> tuple[list[dict], dict]:
    questions = []
    answer_key = {}
    for question, score in picked:
        item = {
            "questionId": int(question.id),
            "questionType": question.question_type,
            "content": question.stem,
            "score": float(score),
        }
        if question.options:
            item["options"] = list(question.options)
        questions.append(item)
        answer_key[str(question.id)] = question.answer
    return questions, answer_key


def same_answer(expected, given) -> bool:
    if isinstance(expected, bool):
        if isinstance(given, bool):
            return expected is given
        text = str(given).strip()
        if text in {"true", "True", "对"}:
            return expected is True
        if text in {"false", "False", "错"}:
            return expected is False
        return False
    if isinstance(expected, list):
        if not isinstance(given, list):
            return False
        try:
            return sorted(int(item) for item in expected) == sorted(int(item) for item in given)
        except (TypeError, ValueError):
            return False
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return int(expected) == int(given)
        except (TypeError, ValueError):
            return False
    if isinstance(expected, str):
        return str(given).strip() == expected.strip()
    return False


def record_public(row: ExamRecord, paper: ExamPaper) -> dict:
    return {
        "id": row.id,
        "paperId": paper.id,
        "paperName": paper.paper_name,
        "userId": row.user_id,
        "questions": row.questions or [],
        "startAt": iso_utc(row.start_at),
        "deadline": iso_utc(row.deadline),
        "switchScreenCount": row.switch_screen_count or 0,
        "examStatus": row.exam_status,
    }


def assignment_of(db: Session, tenant_id: int, paper_id: int, user_id: int) -> ExamAssignment | None:
    return db.scalar(
        select(ExamAssignment).where(
            ExamAssignment.deleted == 0,
            ExamAssignment.tenant_id == tenant_id,
            ExamAssignment.paper_id == paper_id,
            ExamAssignment.user_id == user_id,
        )
    )


def pending_exam_todo(db: Session, tenant_id: int, user_id: int, paper_id: int) -> Todo | None:
    return db.scalar(
        select(Todo).where(
            Todo.tenant_id == tenant_id,
            Todo.assignee_user_id == user_id,
            Todo.task_type == EXAM_TASK,
            Todo.ref_type == EXAM_REF,
            Todo.ref_id == paper_id,
            Todo.status == "PENDING",
        )
    )


def upsert_exam_todo(db: Session, tenant_id: int, user_id: int, paper: ExamPaper, deadline: datetime) -> None:
    title = f"考试待办：{paper.paper_name}"[:128]
    content = "工作台考试待办，进入在线考试作答"
    row = pending_exam_todo(db, tenant_id, user_id, paper.id)
    if row is None:
        db.add(
            Todo(
                assignee_user_id=user_id,
                task_type=EXAM_TASK,
                ref_type=EXAM_REF,
                ref_id=paper.id,
                title=title,
                content=content,
                status="PENDING",
                deadline=deadline,
                tenant_id=tenant_id,
            )
        )
        return
    row.title = title
    row.content = content
    row.deadline = deadline


def close_exam_todo(db: Session, tenant_id: int, user_id: int, paper_id: int) -> None:
    row = pending_exam_todo(db, tenant_id, user_id, paper_id)
    if row is not None:
        row.status = "DONE"


def essay_questions(record: ExamRecord) -> list[dict]:
    return [item for item in (record.questions or []) if item.get("questionType") in SUBJECTIVE]


def grade_overdue(record: ExamRecord, now: datetime) -> bool:
    if record.exam_status != "SUBMITTED" or record.submit_at is None:
        return False
    return record.submit_at <= now - GRADE_OVERDUE


def answer_text(record: ExamRecord, question_id: int):
    for item in record.answers or []:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("questionId")) == question_id:
                return item.get("answer")
        except (TypeError, ValueError):
            continue
    return ""


def subjective_items(record: ExamRecord, include_reference: bool) -> list[dict]:
    key = record.answer_key or {}
    items = []
    for question in essay_questions(record):
        try:
            question_id = int(question.get("questionId"))
        except (TypeError, ValueError):
            continue
        item = {
            "questionId": question_id,
            "content": question.get("content") or "",
            "maxScore": question.get("score"),
            "answer": answer_text(record, question_id),
        }
        if include_reference:
            item["reference"] = key.get(str(question_id), "")
        items.append(item)
    return items


def can_grade(request: Request) -> bool:
    scope = getattr(request.state, "scope", None)
    return scope is None or getattr(scope, "kind", "") != "SELF"


def exam_metric_value(db: Session, tenant_id: int, user_id: int, period: str) -> float | None:
    """已判分考试折成百分制，供考试成绩类指标取数（PER-E-R4）。"""
    text = (period or "").strip()
    if len(text) != 7:
        return None
    rows = db.scalars(
        select(ExamRecord).where(
            ExamRecord.deleted == 0,
            ExamRecord.tenant_id == tenant_id,
            ExamRecord.user_id == user_id,
            ExamRecord.exam_status.in_(("GRADED", "MAKEUP_EXAM")),
            ExamRecord.score.is_not(None),
        )
    ).all()
    percents: list[float] = []
    for row in rows:
        if row.submit_at is None or row.submit_at.strftime("%Y-%m") != text:
            continue
        paper = db.get(ExamPaper, row.paper_id)
        total = float(paper.total_score) if paper is not None and paper.total_score else 0
        if total <= 0 or row.score is None:
            continue
        percents.append(float(row.score) / total * 100)
    if not percents:
        return None
    return round(sum(percents) / len(percents), 2)


def open_attempt(paper: ExamPaper, record: ExamRecord, questions: list, answer_key: dict, status: str) -> None:
    now = utcnow()
    record.questions = questions
    record.answer_key = answer_key
    record.answers = []
    record.start_at = now
    record.submit_at = None
    record.deadline = now + timedelta(minutes=int(paper.duration_minutes or 0))
    record.switch_screen_count = 0
    record.forced_submit = 0
    record.exam_status = status
    record.attempt_open = 1
    record.updated_at = now


@router.get("/exam/paper")
def list_papers(
    pageNo: int = 1,
    pageSize: int = 10,
    paperName: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_bank(db, actor)
    stmt = select(ExamPaper).where(ExamPaper.deleted == 0, ExamPaper.tenant_id == tenant_id)
    if paperName.strip():
        stmt = stmt.where(ExamPaper.paper_name.like(f"%{paperName.strip()}%"))
    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(ExamPaper.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([paper_vo(row) for row in rows], int(total or 0), page_no, size)


@router.post("/exam/paper")
def create_paper(
    body: PaperBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_bank(db, actor)
    name = (body.paper_name or "").strip()
    if not name or len(name) > 128:
        return fail(1001, "试卷名称必填且不超过 128 字")
    paper_type = (body.paper_type or "").strip().upper()
    if paper_type not in {"FIXED", "RANDOM"}:
        return fail(1001, "组卷方式无效")
    if body.duration_minutes < 1:
        return fail(1001, "限时须大于 0")
    if q2(body.pass_score) < 0 or q2(body.pass_score) > q2(body.total_score):
        return fail(1001, "及格分须在 0 到总分之间")

    question_ids: list[int] = []
    strategy: list[dict] = []
    if paper_type == "FIXED":
        raw_ids = body.question_ids or []
        if not raw_ids:
            return fail(1001, "固定卷须选择题目")
        if len(raw_ids) != len(set(raw_ids)):
            return fail(1001, "题目重复")
        rows = list(
            db.scalars(
                select(ExamQuestion).where(
                    ExamQuestion.id.in_(raw_ids),
                    ExamQuestion.deleted == 0,
                    ExamQuestion.tenant_id == tenant_id,
                )
            ).all()
        )
        found = {row.id: row for row in rows}
        if any(qid not in found for qid in raw_ids):
            return fail(1001, "题目不存在")
        question_ids = [int(qid) for qid in raw_ids]
        summed = sum((q2(found[qid].score) for qid in question_ids), Decimal("0"))
        if summed != q2(body.total_score):
            return fail(1159, "总分校验失败（Σ题目分 ≠ totalScore）")
    else:
        error, packed = check_strategy(db, tenant_id, body.strategy or [])
        if error is not None:
            return error
        strategy, summed = packed
        if summed != q2(body.total_score):
            return fail(1159, "总分校验失败（Σ题目分 ≠ totalScore）")

    row = ExamPaper(
        paper_no=next_paper_no(db, tenant_id),
        paper_name=name,
        paper_type=paper_type,
        question_ids=question_ids,
        strategy=strategy,
        total_score=float(q2(body.total_score)),
        pass_score=float(q2(body.pass_score)),
        duration_minutes=body.duration_minutes,
        status="DRAFT",
        assigned_count=0,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(paper_vo(row))


@router.put("/exam/paper/{paper_id}/publish")
def publish_paper(
    paper_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = paper_of(db, tenant_of(actor), paper_id)
    if row is None:
        return fail(1001, "试卷不存在")
    if row.status == "PUBLISHED":
        return fail(1001, "试卷已发布")
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.post("/exam/paper/{paper_id}/assign")
def assign_paper(
    paper_id: int,
    body: AssignBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = paper_of(db, tenant_id, paper_id)
    if row is None:
        return fail(1001, "试卷不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "请先发布试卷")
    user_ids = list(dict.fromkeys(body.user_ids or []))
    if not user_ids:
        return fail(1001, "请选择考生")
    window_from = parse_instant(body.exam_window.start)
    window_to = parse_instant(body.exam_window.to)
    if window_from is None or window_to is None:
        return fail(1001, "考试窗口时间无效")
    if window_from >= window_to:
        return fail(1001, "考试窗口开始时间须早于结束时间")
    users = list(
        db.scalars(
            select(User).where(User.id.in_(user_ids), User.deleted == 0, User.tenant_id == tenant_id)
        ).all()
    )
    found = {user.id for user in users}
    if any(uid not in found for uid in user_ids):
        return fail(1001, "考生不存在")
    now = utcnow()
    for uid in user_ids:
        current = assignment_of(db, tenant_id, row.id, uid)
        if current is None:
            db.add(
                ExamAssignment(
                    paper_id=row.id,
                    user_id=uid,
                    window_from=window_from,
                    window_to=window_to,
                    tenant_id=tenant_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            current.window_from = window_from
            current.window_to = window_to
            current.updated_at = now
        upsert_exam_todo(db, tenant_id, uid, row, window_to)
    db.flush()
    assigned = db.scalar(
        select(func.count())
        .select_from(ExamAssignment)
        .where(
            ExamAssignment.deleted == 0,
            ExamAssignment.tenant_id == tenant_id,
            ExamAssignment.paper_id == row.id,
        )
    )
    row.assigned_count = int(assigned or 0)
    row.updated_at = now
    db.flush()
    return ok({"assignedCount": row.assigned_count})


@router.post("/exam/record/start")
def start_exam(
    body: StartBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_bank(db, actor)
    paper = paper_of(db, tenant_id, body.paper_id)
    if paper is None:
        return fail(1001, "试卷不存在")
    if paper.status != "PUBLISHED":
        return fail(1001, "试卷未发布")
    assignment = assignment_of(db, tenant_id, paper.id, actor.id)
    now = utcnow()
    if assignment is None or now < assignment.window_from or now > assignment.window_to:
        window = ""
        if assignment is not None:
            window = f"（{iso_utc(assignment.window_from)} ~ {iso_utc(assignment.window_to)}）"
        return fail(1161, f"不在考试窗口内{window}")

    record = db.scalar(
        select(ExamRecord).where(
            ExamRecord.deleted == 0,
            ExamRecord.tenant_id == tenant_id,
            ExamRecord.paper_id == paper.id,
            ExamRecord.user_id == actor.id,
        )
    )
    if record is not None and record.attempt_open:
        return fail(1162, "已有进行中答卷", record_public(record, paper))

    makeup = False
    if record is not None:
        if record.makeup_consumed or record.exam_status == "MAKEUP_EXAM":
            return fail(1001, "补考仅一次（PER-E-R3）")
        if record.exam_status == "SUBMITTED":
            return fail(1001, "主观题待阅卷，暂不可补考")
        if record.exam_status != "GRADED":
            return fail(1001, "当前不可开始考试")
        if q2(record.score) >= q2(paper.pass_score):
            return fail(1001, "已及格，无需补考")
        makeup = True

    error, picked = draw_questions(db, tenant_id, paper)
    if error is not None:
        return error
    questions, answer_key = snapshot(picked)
    if makeup and record is not None:
        record.is_makeup = 1
        open_attempt(paper, record, questions, answer_key, "MAKEUP_EXAM")
    else:
        record = ExamRecord(
            paper_id=paper.id,
            user_id=actor.id,
            tenant_id=tenant_id,
            is_makeup=0,
            makeup_consumed=0,
        )
        open_attempt(paper, record, questions, answer_key, "IN_PROGRESS")
        db.add(record)
    db.flush()
    return ok(record_public(record, paper))


@router.post("/exam/record/submit")
def submit_exam(
    body: SubmitBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    record = db.get(ExamRecord, body.record_id)
    if record is None or record.deleted or record.tenant_id != tenant_id:
        return fail(1001, "答卷不存在")
    if record.user_id != actor.id:
        return fail(1163, "答卷非本人")
    if not record.attempt_open:
        return fail(1164, "已交卷不可重复提交")
    if body.switch_screen_count < 0:
        return fail(1001, "切屏次数无效")
    paper = paper_of(db, tenant_id, record.paper_id)
    if paper is None:
        return fail(1001, "试卷不存在")

    given = {item.question_id: item.answer for item in body.answers}
    key = record.answer_key or {}
    objective = Decimal("0")
    has_subjective = False
    for item in record.questions or []:
        qtype = item.get("questionType")
        if qtype in SUBJECTIVE:
            has_subjective = True
            continue
        qid = int(item["questionId"])
        expected = key.get(str(qid))
        if qid in given and same_answer(expected, given[qid]):
            objective += q2(item.get("score"))

    now = utcnow()
    forced = body.switch_screen_count >= 3
    record.answers = [{"questionId": item.question_id, "answer": item.answer} for item in body.answers]
    record.switch_screen_count = body.switch_screen_count
    record.forced_submit = 1 if forced else 0
    record.objective_score = float(objective)
    record.submit_at = now
    record.attempt_open = 0
    record.updated_at = now
    if has_subjective:
        record.subjective_score = None
        record.score = None
        record.exam_status = "SUBMITTED"
        total = None
        subjective = None
    else:
        record.subjective_score = None
        record.score = float(objective)
        subjective = None
        total = float(objective)
        if record.is_makeup:
            record.exam_status = "MAKEUP_EXAM"
            record.makeup_consumed = 1
        else:
            record.exam_status = "GRADED"
    close_exam_todo(db, tenant_id, actor.id, paper.id)
    db.flush()
    return ok(
        {
            "recordId": record.id,
            "examStatus": record.exam_status,
            "objectiveScore": record.objective_score,
            "subjectiveScore": subjective,
            "totalScore": total,
            "forcedSubmit": forced,
        }
    )


@router.put("/exam/record/{record_id}/grade")
def grade_record(
    record_id: int,
    body: GradeBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_grade(request):
        return fail(403, "考生不能阅卷")
    tenant_id = tenant_of(actor)
    record = db.get(ExamRecord, record_id)
    if record is None or record.deleted or record.tenant_id != tenant_id:
        return fail(1001, "答卷不存在")
    if record.exam_status != "SUBMITTED":
        return fail(1001, "仅已交卷的主观题可阅卷")
    essays = essay_questions(record)
    if not essays:
        return fail(1001, "本卷没有简答题")
    expected = {}
    for question in essays:
        try:
            question_id = int(question.get("questionId"))
        except (TypeError, ValueError):
            return fail(1001, "题目无效")
        expected[question_id] = q2(question.get("score"))
    if not body.gradings:
        return fail(1001, "请评完主观题")
    seen: set[int] = set()
    subjective = Decimal("0")
    comments: dict[int, str] = {}
    for item in body.gradings:
        if item.question_id in seen:
            return fail(1001, "题目重复")
        seen.add(item.question_id)
        if item.question_id not in expected:
            return fail(1001, "题目不是简答题")
        score = q2(item.score)
        if score < 0 or score > expected[item.question_id]:
            return fail(1001, "评分须在 0 到该题分值之间")
        comment = (item.comment or "").strip()
        if len(comment) > 200:
            return fail(1001, "评语不超过 200 字")
        subjective += score
        comments[item.question_id] = comment
    if seen != set(expected):
        return fail(1001, "主观题未评完")
    questions = list(record.questions or [])
    for question in questions:
        try:
            question_id = int(question.get("questionId"))
        except (TypeError, ValueError):
            continue
        if question_id not in comments:
            continue
        question["gradedScore"] = float(q2(next(item.score for item in body.gradings if item.question_id == question_id)))
        question["gradeComment"] = comments[question_id]
    record.questions = questions
    flag_modified(record, "questions")
    objective = q2(record.objective_score)
    record.subjective_score = float(subjective)
    record.score = float(objective + subjective)
    record.exam_status = "GRADED"
    if record.is_makeup:
        record.makeup_consumed = 1
    record.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.get("/exam/record/scores")
def list_scores(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    paperId: int = 0,
    userId: int = 0,
    userKeyword: str = "",
    examStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(ExamRecord).where(ExamRecord.deleted == 0, ExamRecord.tenant_id == tenant_id)
    scope = getattr(request.state, "scope", None)
    if scope is not None and scope.kind == "SELF":
        stmt = stmt.where(ExamRecord.user_id == actor.id)
    elif userId:
        stmt = stmt.where(ExamRecord.user_id == userId)
    keyword = (userKeyword or "").strip()
    if keyword:
        like = f"%{keyword}%"
        matched = list(
            db.scalars(
                select(User.id).where(
                    User.deleted == 0,
                    User.tenant_id == tenant_id,
                    or_(User.nickname.like(like), User.username.like(like)),
                )
            ).all()
        )
        if keyword.isdigit():
            matched.append(int(keyword))
        stmt = stmt.where(ExamRecord.user_id.in_(matched or [-1]))
    if paperId:
        stmt = stmt.where(ExamRecord.paper_id == paperId)
    status = (examStatus or "").strip().upper()
    if status:
        stmt = stmt.where(ExamRecord.exam_status == status)
    page_no, size = page_args(pageNo, pageSize)
    now = utcnow()
    overdue_rank = case(
        (
            (ExamRecord.exam_status == "SUBMITTED")
            & ExamRecord.submit_at.is_not(None)
            & (ExamRecord.submit_at <= now - GRADE_OVERDUE),
            0,
        ),
        else_=1,
    )
    ordered = stmt.order_by(overdue_rank.asc(), ExamRecord.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(ordered.offset((page_no - 1) * size).limit(size)).all()
    paper_ids = {row.paper_id for row in rows}
    user_ids = {row.user_id for row in rows}
    papers = {
        row.id: row
        for row in db.scalars(select(ExamPaper).where(ExamPaper.id.in_(paper_ids or [0]))).all()
    }
    users = {row.id: row for row in db.scalars(select(User).where(User.id.in_(user_ids or [0]))).all()}
    manager = can_grade(request)
    data = []
    for row in rows:
        paper = papers.get(row.paper_id)
        user = users.get(row.user_id)
        essays = essay_questions(row)
        overdue = grade_overdue(row, now)
        item = {
            "id": row.id,
            "paperId": row.paper_id,
            "paperName": paper.paper_name if paper else "",
            "userId": row.user_id,
            "userName": (user.nickname or user.username) if user else str(row.user_id),
            "score": row.score,
            "objectiveScore": row.objective_score,
            "subjectiveScore": row.subjective_score,
            "switchScreenCount": row.switch_screen_count or 0,
            "forcedSubmit": bool(row.forced_submit) or (row.switch_screen_count or 0) >= 3,
            "examStatus": row.exam_status,
            "isMakeup": bool(row.is_makeup) or row.exam_status == "MAKEUP_EXAM",
            "hasSubjective": bool(essays),
            "gradeOverdue": overdue,
            "canGrade": manager and row.exam_status == "SUBMITTED" and bool(essays),
            "startAt": iso_utc(row.start_at),
            "submitAt": iso_utc(row.submit_at) if row.submit_at else "",
        }
        if manager and essays and row.exam_status == "SUBMITTED":
            item["subjectiveItems"] = subjective_items(row, True)
        data.append(item)
    return paged(data, int(total or 0), page_no, size)
