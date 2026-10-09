"""内容排版第一刀：版式模板套用 + 规则一键排版（不调用 LLM）。

保真：写回的 layout_html 抽纯文本后与正文字符一致，且不改 content.body。
错误码对齐排版产品语义：2036 正文为空 · 2031 需确认覆盖 · 2037 保真失败 · 1501 模板无效。
"""

from __future__ import annotations

import html
import json
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.corp import tenant_of
from app.models import ContentLayoutTemplate, User

router = APIRouter(prefix="/content", tags=["content-typeset"])

PRESET_LABELS: dict[str, str] = {
    "clean-read": "清爽阅读",
    "marketing": "营销引流",
    "decision-scan": "决策扫读",
    "analysis-report": "分析报告",
}
MODES = frozenset({"RULE", "TEMPLATE"})
EDITABLE = frozenset({"DRAFT", "REJECTED"})

_BLOCKED_TAG = re.compile(
    r"<(script|iframe|object|embed)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_ON_ATTR = re.compile(r"\s(on\w+)\s*=", re.IGNORECASE)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK_END = re.compile(r"</(p|div|section|h[1-6]|li|article)>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


class TypesetReq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mode: str = "RULE"
    preset: str = "clean-read"
    templateId: int | None = None
    overwrite: bool = False
    body: str | None = None


def sanitize_layout_html(raw: str) -> str:
    cleaned = _BLOCKED_TAG.sub("", raw or "")
    return _ON_ATTR.sub(" data-blocked=", cleaned)


def normalize_plain(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_plain(layout_html: str) -> str:
    text = _BR.sub("\n", layout_html or "")
    text = _BLOCK_END.sub("\n", text)
    text = _TAG.sub("", text)
    return html.unescape(text)


def fidelity_ok(source: str, layout_html: str) -> bool:
    return normalize_plain(extract_plain(layout_html)) == normalize_plain(source)


def _blocks(body: str) -> list[str]:
    text = (body or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    blocks: list[str] = []
    for part in re.split(r"\n\s*\n", text):
        chunk = part.strip()
        if chunk:
            blocks.append(chunk)
    return blocks


def render_layout(preset: str, body: str, template_name: str = "") -> tuple[str, dict]:
    blocks = _blocks(body)
    name_attr = html.escape(template_name or PRESET_LABELS.get(preset, ""), quote=True)
    if preset == "marketing" and blocks:
        parts = [f'<p class="ims-lead">{html.escape(blocks[0]).replace(chr(10), "<br/>")}</p>']
        parts.extend(f"<p>{html.escape(block).replace(chr(10), '<br/>')}</p>" for block in blocks[1:])
        inner = "".join(parts)
    elif preset == "decision-scan":
        lines = [html.escape(line.strip()) for block in blocks for line in block.split("\n") if line.strip()]
        inner = "".join(f'<div class="ims-scan-line">{line}</div>' for line in lines)
    elif preset == "analysis-report":
        inner = "".join(
            f'<section class="ims-analysis"><p>{html.escape(block).replace(chr(10), "<br/>")}</p></section>'
            for block in blocks
        )
    else:
        inner = "".join(f"<p>{html.escape(block).replace(chr(10), '<br/>')}</p>" for block in blocks)
    layout_html = (
        f'<article class="ims-layout ims-layout-{preset}" data-preset="{html.escape(preset, quote=True)}" '
        f'data-template="{name_attr}">{inner}</article>'
    )
    layout_json = {
        "version": 1,
        "preset": preset,
        "blocks": [{"type": "paragraph", "text": block} for block in blocks],
    }
    return sanitize_layout_html(layout_html), layout_json


def ensure_layout_presets(db: Session, tenant_id: int, user_id: int) -> None:
    for code, label in PRESET_LABELS.items():
        existing = db.scalar(
            select(ContentLayoutTemplate.id).where(
                ContentLayoutTemplate.deleted == 0,
                ContentLayoutTemplate.tenant_id == tenant_id,
                ContentLayoutTemplate.preset_code == code,
            )
        )
        if existing is not None:
            continue
        token = code.upper().replace("-", "")
        db.add(
            ContentLayoutTemplate(
                template_no=f"LTPRESET{token}"[:32],
                template_name=label,
                source="PRESET",
                status="ENABLED",
                preset_code=code,
                preview_html=f'<article class="ims-layout" data-preset="{code}"><p>示例正文</p></article>',
                layout_json=json.dumps({"version": 1, "preset": code}, ensure_ascii=False),
                created_by=user_id,
                tenant_id=tenant_id,
            )
        )
    db.flush()


def _source_text(row, req: TypesetReq) -> str:
    if req.body is not None:
        return req.body
    return row.body or ""


def _resolve_template(db: Session, actor: User, req: TypesetReq):
    mode = (req.mode or "RULE").strip().upper()
    if mode not in MODES:
        return None, None, 1500, "参数校验失败"
    tenant_id = tenant_of(actor)
    if mode == "TEMPLATE":
        if req.templateId is None:
            return None, None, 1500, "请选择版式模板"
        tpl = db.get(ContentLayoutTemplate, req.templateId)
        if (
            tpl is None
            or tpl.deleted
            or tpl.tenant_id != tenant_id
            or tpl.status != "ENABLED"
        ):
            return None, None, 1501, "模板不存在或未启用"
        preset = tpl.preset_code if tpl.preset_code in PRESET_LABELS else "clean-read"
        return tpl, preset, 0, ""
    preset = (req.preset or "").strip()
    if preset not in PRESET_LABELS:
        return None, None, 1500, "排版预设无效"
    tpl = db.scalar(
        select(ContentLayoutTemplate).where(
            ContentLayoutTemplate.deleted == 0,
            ContentLayoutTemplate.tenant_id == tenant_id,
            ContentLayoutTemplate.preset_code == preset,
            ContentLayoutTemplate.status == "ENABLED",
        )
    )
    return tpl, preset, 0, ""


def _typeset(db: Session, actor: User, row, req: TypesetReq, *, write: bool):
    from app.content_production import project_vo

    source = _source_text(row, req)
    if not normalize_plain(source):
        return fail(2036, "正文为空，无法排版")
    if write and row.content_status not in EDITABLE:
        return fail(1502, "仅草稿或已驳回内容可排版")
    if write and (row.body_format or "PLAIN") == "LAYOUT" and not req.overwrite:
        return fail(2031, "已有版式，需确认覆盖；正文文字不会改动")
    tpl, preset, code, msg = _resolve_template(db, actor, req)
    if code:
        return fail(code, msg)
    template_name = tpl.template_name if tpl is not None else PRESET_LABELS[preset]
    layout_html, layout_json = render_layout(preset, source, template_name)
    if not fidelity_ok(source, layout_html):
        return fail(2037, "保真校验失败，已拒绝写回")
    layout_json["templateId"] = tpl.id if tpl is not None else None
    layout_json["templateName"] = template_name
    layout_json["mode"] = (req.mode or "RULE").strip().upper()
    if not write:
        return ok(
            {
                "mode": layout_json["mode"],
                "preset": preset,
                "presetName": PRESET_LABELS[preset],
                "templateId": layout_json["templateId"],
                "templateName": template_name,
                "layoutHtml": layout_html,
                "layoutJson": layout_json,
                "bodyFormat": "LAYOUT",
                "plainTextBefore": normalize_plain(source),
                "plainTextAfter": normalize_plain(extract_plain(layout_html)),
                "fidelityCheck": {"passed": True},
                "body": row.body or "",
            }
        )
    stored_body = row.body or ""
    row.layout_html = layout_html
    row.layout_json = json.dumps(layout_json, ensure_ascii=False)
    row.body_format = "LAYOUT"
    row.layout_template_id = tpl.id if tpl is not None else None
    row.body = stored_body
    if tpl is not None:
        tpl.usage_count = int(tpl.usage_count or 0) + 1
    db.flush()
    return ok(project_vo(row))


@router.post("/{content_id}/typeset/preview")
def typeset_preview(
    content_id: int,
    req: TypesetReq,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.content_production import load_project

    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    return _typeset(db, actor, row, req, write=False)


@router.post("/{content_id}/typeset/apply")
def typeset_apply(
    content_id: int,
    req: TypesetReq,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.content_production import load_project

    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    return _typeset(db, actor, row, req, write=True)
