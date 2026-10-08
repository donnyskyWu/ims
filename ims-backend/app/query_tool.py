"""QT-001 查询工具（W9-9 首片 · 模板列表 + run 占位）。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import QueryTemplate, User

router = APIRouter(prefix="/analysis/query-tool", tags=["query-tool"])

BJ = timezone(timedelta(hours=8))
MODES = frozenset({"DRILL", "TRACE", "FLAT"})
STATUSES = frozenset({"DRAFT", "PUBLISHED"})


class TemplateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    mode: str = "DRILL"
    desc: str = ""
    payloadJson: dict = Field(default_factory=dict)


class TemplateUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    desc: str | None = None
    payloadJson: dict | None = None


class RunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mode: str
    templateCode: str | None = None
    runtime: dict | None = None


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_template_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(QueryTemplate).where(
            QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id
        )
    )
    return f"QT-TPL-{int(count or 0) + 1:04d}"


def template_vo(row: QueryTemplate, names: dict[int, str]) -> dict:
    menu_label = ""
    if row.menu_seed and row.menu_route:
        menu_label = "已挂 L3"
    elif row.menu_seed:
        menu_label = "已挂 L3"
    return {
        "templateCode": row.template_code,
        "name": row.name,
        "mode": row.mode,
        "status": row.status,
        "menuSeed": bool(row.menu_seed),
        "menuRoute": row.menu_route or "",
        "menuPathLabel": menu_label or ("未挂菜单" if row.status == "PUBLISHED" else "—"),
        "permCode": row.perm_code or "",
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "desc": row.desc or "",
        "updatedAt": iso(row.updated_at),
    }


def seed_templates(db: Session, tenant_id: int, owner_id: int) -> None:
    exists = db.scalar(
        select(func.count()).select_from(QueryTemplate).where(
            QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id
        )
    )
    if exists:
        return
    now = utcnow()
    samples = [
        {
            "template_code": "QT-TPL-0001",
            "name": "IP 组周产出（标准）",
            "mode": "DRILL",
            "status": "PUBLISHED",
            "desc": "下钻 L0→L1 占位",
            "payload_json": {"levels": [{"levelIndex": 0, "label": "IP 组", "entityCode": "ip_group"}]},
        },
        {
            "template_code": "QT-TPL-0002",
            "name": "IP 组→场次下钻",
            "mode": "DRILL",
            "status": "DRAFT",
            "payload_json": {"levels": []},
        },
        {
            "template_code": "QT-TPL-0003",
            "name": "实名人成本 TRACE",
            "mode": "TRACE",
            "status": "DRAFT",
            "payload_json": {"pathSteps": [{"entity": "PERSON"}, {"entity": "SESSION"}]},
        },
        {
            "template_code": "QT-TPL-0004",
            "name": "财务穿透 · 场次成本",
            "mode": "TRACE",
            "status": "PUBLISHED",
            "menu_seed": 1,
            "menu_route": "/ims/analysis/query-tool/run/QT-TPL-0004",
            "desc": "挂数据分析 L3",
            "payload_json": {"pathSteps": [{"entity": "SESSION"}, {"entity": "COST"}]},
        },
    ]
    for item in samples:
        row = QueryTemplate(
            template_code=item["template_code"],
            name=item["name"],
            mode=item["mode"],
            status=item["status"],
            menu_seed=int(item.get("menu_seed") or 0),
            menu_route=item.get("menu_route") or "",
            desc=item.get("desc") or "",
            payload_json=item.get("payload_json") or {},
            owner_user_id=owner_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.flush()


def get_template(db: Session, tenant_id: int, template_code: str) -> QueryTemplate | None:
    return db.scalar(
        select(QueryTemplate).where(
            QueryTemplate.deleted == 0,
            QueryTemplate.tenant_id == tenant_id,
            QueryTemplate.template_code == template_code.strip(),
        )
    )


@router.get("/template/page")
def template_page(
    keyword: str | None = None,
    status: str | None = None,
    mode: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_templates(db, tenant_id, actor.id)
    q = select(QueryTemplate).where(QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((QueryTemplate.name.like(kw)) | (QueryTemplate.template_code.like(kw)))
    if status:
        st = status.strip().upper()
        if st in STATUSES:
            q = q.where(QueryTemplate.status == st)
    if mode:
        md = mode.strip().upper()
        if md in MODES:
            q = q.where(QueryTemplate.mode == md)
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(QueryTemplate.updated_at.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.owner_user_id for r in rows])
    return paged([template_vo(r, names) for r in rows], total, page_no, size)


@router.get("/template/{template_code}")
def template_detail(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    names = user_names(db, [row.owner_user_id])
    data = template_vo(row, names)
    data["payloadJson"] = row.payload_json if isinstance(row.payload_json, dict) else {}
    return ok(data)


@router.post("/template")
def template_create(
    body: TemplateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = body.name.strip()
    if not name:
        return fail(1001, "模板名称必填")
    mode = body.mode.strip().upper()
    if mode not in MODES:
        return fail(1001, "模式无效")
    tenant_id = tenant_of(actor)
    now = utcnow()
    row = QueryTemplate(
        template_code=next_template_code(db, tenant_id),
        name=name,
        mode=mode,
        status="DRAFT",
        desc=body.desc.strip(),
        payload_json=body.payloadJson or {},
        owner_user_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.put("/template/{template_code}")
def template_update(
    template_code: str,
    body: TemplateUpdateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            return fail(1001, "模板名称必填")
        row.name = name
    if body.desc is not None:
        row.desc = body.desc.strip()
    if body.payloadJson is not None:
        row.payload_json = body.payloadJson
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.post("/template/{template_code}/publish")
def template_publish(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.post("/template/{template_code}/unpublish")
def template_unpublish(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    row.status = "DRAFT"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.delete("/template/{template_code}")
def template_delete(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    if row.menu_seed:
        return fail(1265, "模板已挂菜单，请先撤销侧栏")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok({"templateCode": template_code})


@router.post("/run")
def query_run(body: RunBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    mode = body.mode.strip().upper()
    if mode not in MODES:
        return fail(1001, "mode 无效")
    tenant_id = tenant_of(actor)
    template = None
    if body.templateCode:
        template = get_template(db, tenant_id, body.templateCode)
        if template is None:
            return fail(1263, "查询模板不存在或未发布")
        if template.status != "PUBLISHED":
            return fail(1263, "查询模板不存在或未发布")
        mode = template.mode
    t0 = time.perf_counter()
    if mode == "TRACE":
        columns = [
            {"key": "nodeType", "label": "节点类型"},
            {"key": "nodeLabel", "label": "名称"},
        ]
        rows = [
            {"nodeType": "PERSON", "nodeLabel": "实名人 · 示例"},
            {"nodeType": "SESSION", "nodeLabel": "场次 · DEMO-001"},
        ]
        level_state = {"activeLevel": 1, "breadcrumbs": ["入口", "场次"]}
    else:
        columns = [
            {"key": "dimName", "label": "维度"},
            {"key": "metricValue", "label": "指标值"},
        ]
        rows = [
            {"dimName": "电竞一组", "metricValue": 1280},
            {"dimName": "体育二组", "metricValue": 960},
        ]
        level_state = {"activeLevel": 0, "breadcrumbs": ["IP 组"]}
    cost_ms = int((time.perf_counter() - t0) * 1000) + 12
    return ok(
        {
            "columns": columns,
            "rows": rows,
            "levelState": level_state,
            "queryCostMs": cost_ms,
            "queryMode": "SYNC",
            "templateCode": template.template_code if template else None,
            "note": "QT run 占位 · 未接 DW/DC 逐步编排",
        }
    )
