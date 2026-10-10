"""大屏 bi0Screen 首片 · 只读配置/展示（reportType=DASHBOARD）。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import primary_dept_id, report_row_visible, restrict_report_def
from app.bi_report import iso, next_report_no, parse_layout, report_def_vo
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiReportDef, User

router = APIRouter(prefix="/bi/screen", tags=["bi-screen"])

DEFAULT_WIDGETS = [
    {"type": "KPI", "title": "今日 GMV", "value": "128.6万", "unit": "元", "trend": "+12%"},
    {"type": "KPI", "title": "直播场次", "value": "24", "unit": "场", "trend": "+3"},
    {"type": "CHART", "title": "近7日互动趋势", "chartType": "LINE"},
    {"type": "LIST", "title": "账号 TOP5", "rows": ["抖音官方", "快手体育", "视频号赛事"]},
]


def widgets_of(layout: dict) -> list:
    raw = layout.get("comps")
    if isinstance(raw, list):
        return raw
    return list(DEFAULT_WIDGETS)


def widget_flags(widgets: list) -> dict:
    empty = len(widgets) == 0
    return {
        "widgets": widgets,
        "empty": empty,
        "emptyReason": "暂无组件" if empty else "",
    }


def seed_screens(db: Session, tenant_id: int, creator_id: int) -> None:
    count = int(
        db.scalar(
            select(func.count()).select_from(BiReportDef).where(
                BiReportDef.deleted == 0,
                BiReportDef.tenant_id == tenant_id,
                BiReportDef.report_type == "DASHBOARD",
            )
        )
        or 0
    )
    if count > 0:
        return
    now = utcnow()
    seeds = [
        ("运营驾驶舱", "内容分析", "PUBLISHED"),
        ("直播实时大屏", "经营财务", "DRAFT"),
    ]
    for name, cat, status in seeds:
        layout = {
            "layoutMode": "GRID",
            "theme": "dark",
            "comps": DEFAULT_WIDGETS,
        }
        db.add(
            BiReportDef(
                report_no=next_report_no(db, tenant_id),
                report_name=name,
                report_type="DASHBOARD",
                category=cat,
                sub_category="大屏",
                status=status,
                layout_json=json.dumps(layout, ensure_ascii=False),
                creator_id=creator_id,
                dept_id=primary_dept_id(db, creator_id, tenant_id),
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    db.flush()


@router.get("/list")
def screen_list(
    request: Request,
    keyword: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_screens(db, tenant_id, actor.id)
    q = restrict_report_def(
        select(BiReportDef).where(
            BiReportDef.deleted == 0,
            BiReportDef.tenant_id == tenant_id,
            BiReportDef.report_type == "DASHBOARD",
        ),
        request.state.scope,
        tenant_id,
    )
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((BiReportDef.report_name.like(kw)) | (BiReportDef.report_no.like(kw)))
    if status:
        q = q.where(BiReportDef.status == status.strip().upper())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiReportDef.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([report_def_vo(r, names) for r in rows], total, page_no, size)


@router.get("/{screen_id:int}")
def screen_detail(
    screen_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_screens(db, tenant_id, actor.id)
    row = db.get(BiReportDef, screen_id)
    if row is None or row.deleted or row.tenant_id != tenant_id or row.report_type != "DASHBOARD":
        return fail(1001, "大屏不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    names = user_names(db, [row.creator_id])
    layout = parse_layout(row.layout_json)
    widgets = widgets_of(layout)
    return ok(
        {
            **report_def_vo(row, names),
            "theme": layout.get("theme", "dark"),
            "previewUrl": f"/ims/bi/screen/{row.id}/view",
            **widget_flags(widgets),
        }
    )


@router.get("/{screen_id:int}/preview")
def screen_preview_runtime(
    screen_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiReportDef, screen_id)
    if row is None or row.deleted or row.tenant_id != tenant_id or row.report_type != "DASHBOARD":
        return fail(1001, "大屏不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    layout = parse_layout(row.layout_json)
    widgets = widgets_of(layout)
    return ok(
        {
            "reportId": row.id,
            "reportName": row.report_name,
            "refreshedAt": iso(row.updated_at),
            **widget_flags(widgets),
        }
    )
