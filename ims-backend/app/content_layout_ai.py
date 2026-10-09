"""AI 语义排版。

只生成 layout_html / layout_json。不改写正文纯文本，不调用文案多轮，不回落 jingcai。
文案生成也不从这里自动排版。
"""

from __future__ import annotations

import html
import json
import os
import re
from collections import Counter

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content_production import load_project, project_vo
from app.models import AirModelConfig, ContentProject, User

router = APIRouter(prefix="/content", tags=["content-layout-ai"])

SEGMENT_TYPES = frozenset(
    {
        "ARTICLE_TITLE",
        "MATCH_HEADER",
        "TEAM_VS",
        "MATCH_TIME",
        "MATCH_METADATA",
        "SUBHEADING",
        "ANALYSIS_PARAGRAPH",
        "RECOMMENDATION_LIST",
        "IMAGE_PLACEHOLDER",
        "DIVIDER",
        "DISCLAIMER",
        "QUOTE",
        "ORDERED_LIST",
        "DECORATIVE_SLOGAN",
        "PLAIN_PARAGRAPH",
        "STAT_BAR",
        "ODDS_TABLE",
        "HIGHLIGHT",
    }
)
_ALLOWED_TAGS = frozenset(
    {"section", "article", "h1", "h2", "h3", "p", "br", "strong", "em", "ul", "ol", "li", "blockquote", "div", "span"}
)
_TAG = {
    "ARTICLE_TITLE": "h2",
    "SUBHEADING": "h3",
    "QUOTE": "blockquote",
    "ORDERED_LIST": "ol",
    "RECOMMENDATION_LIST": "ul",
}
_FAITHFUL = frozenset({"1", "true", "yes", "ok", "success", "semantic", "layout"})
_MUTATE = frozenset({"fidelity", "mutate", "2037", "fidelity_fail"})
_OFF = frozenset({"0", "false", "off", "none"})
FIDELITY_MSG = "排版结果与原文不一致，已拒绝；请重试或联系管理员"
EMPTY_MSG = "正文为空"
OVERWRITE_MSG = "将覆盖当前版式，请确认后再写回"
SEGMENT_FAIL_MSG = "AI 分段失败，请稍后重试"
SYSTEM_PROMPT = (
    "你是排版分段器，不是文案作者。不得增删改原文任何字符，不得润色，不得调用文案多轮。"
    "只输出 JSON 对象 {\"segments\":[{\"segmentType\":\"PLAIN_PARAGRAPH\",\"text\":\"...\"}]}。"
    "segmentType 只能取给定枚举。各段 text 按顺序拼接必须与用户原文完全一致，且每段 text 是原文连续子串。"
)


class LayoutAiError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg


class TypesetPreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mode: str = "AUTO"
    body: str | None = None
    templateId: str | None = None


class TypesetApplyBody(TypesetPreviewBody):
    overwrite: bool = False


def normalize_plain(text: str | None) -> str:
    raw = text or ""
    return raw.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")


def parse_layout_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def extract_plain_text(layout_html: str | None) -> str:
    text = layout_html or ""
    text = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", "", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def sanitize_layout_html(layout_html: str | None) -> str:
    """只保留版式标签与 class/data-*，丢掉脚本和事件属性。"""
    source = re.sub(r"(?is)<!--.*?-->", "", layout_html or "")
    source = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", "", source)

    def repl(match: re.Match[str]) -> str:
        slash = match.group(1)
        name = match.group(2).lower()
        if name not in _ALLOWED_TAGS:
            return ""
        if slash:
            return f"</{name}>"
        attrs: list[str] = []
        for attr in re.finditer(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(\"[^\"]*\"|'[^']*')", match.group(3) or ""):
            key = attr.group(1).lower()
            val = attr.group(2)[1:-1]
            if key != "class" and not key.startswith("data-"):
                continue
            if "javascript:" in val.lower():
                continue
            attrs.append(f'{key}="{html.escape(val, quote=True)}"')
        attr_s = (" " + " ".join(attrs)) if attrs else ""
        if name == "br":
            return "<br>"
        return f"<{name}{attr_s}>"

    return re.sub(r"<(/?)([A-Za-z0-9]+)([^>]*)>", repl, source)


def stub_mode() -> str | None:
    """IMS_LAYOUT_AI_STUB 优先；未设置时才读 IMS_CONTENT_AI_STUB。"""
    layout = os.environ.get("IMS_LAYOUT_AI_STUB")
    if layout is not None and layout.strip() != "":
        raw = layout.strip().lower()
    else:
        raw = (os.environ.get("IMS_CONTENT_AI_STUB") or "").strip().lower()
    if not raw or raw in _OFF:
        return None
    return raw


def _classify(line: str, first: bool) -> str:
    text = line.strip()
    if not text:
        return "PLAIN_PARAGRAPH"
    if any(token in text for token in ("免责声明", "仅供参考")):
        return "DISCLAIMER"
    if re.search(r"\bVS\b|对阵", text, re.I) and len(text) <= 40:
        return "TEAM_VS"
    if text.startswith("【") and text.endswith("】") and len(text) <= 24:
        return "SUBHEADING"
    if first and len(text) <= 24 and "。" not in text and "，" not in text:
        return "ARTICLE_TITLE"
    if len(text) <= 16 and text.endswith(("：", ":")):
        return "SUBHEADING"
    return "ANALYSIS_PARAGRAPH"


def heuristic_segments(source: str) -> list[dict]:
    lines = source.split("\n")
    segments: list[dict] = []
    for index, line in enumerate(lines):
        piece = line if index == len(lines) - 1 else line + "\n"
        if piece == "":
            continue
        segments.append(
            {
                "index": len(segments),
                "segmentType": _classify(line, not segments),
                "text": piece,
            }
        )
    if not segments:
        segments.append({"index": 0, "segmentType": "PLAIN_PARAGRAPH", "text": source})
    if "".join(item["text"] for item in segments) != source:
        return [{"index": 0, "segmentType": "PLAIN_PARAGRAPH", "text": source}]
    return segments


def decide_template(source: str) -> dict:
    compact = re.sub(r"\s+", "", source)
    odds = any(token in source for token in ("赔率", "盘口", "亚指", "欧指", "水位", "凯利"))
    if odds or len(compact) >= 400:
        key, name = "analysis-report", "情报分析版"
    else:
        key, name = "decision-scan", "决策扫读版"
    return {
        "selectedFootballTemplate": key,
        "selectedTemplateName": name,
        "templateDecision": {
            "confidence": "HIGH",
            "selectionReason": "SCORE_THRESHOLD",
            "featureSummary": {"bodyCharCount": len(compact), "odds": odds},
        },
    }


def render_html(segments: list[dict], template_key: str) -> str:
    parts = [f'<section class="ims-semantic-layout" data-template="{html.escape(template_key, quote=True)}">']
    for seg in segments:
        tag = _TAG.get(seg["segmentType"], "p")
        parts.append(
            f'<{tag} data-seg="{seg["index"]}" data-type="{html.escape(seg["segmentType"], quote=True)}">'
            f"{html.escape(seg['text'])}</{tag}>"
        )
    parts.append("</section>")
    return "".join(parts)


def _parse_model_segments(raw: str) -> list[dict]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LayoutAiError(2039, SEGMENT_FAIL_MSG) from exc
    if isinstance(data, dict):
        data = data.get("segments")
    if not isinstance(data, list) or not data:
        raise LayoutAiError(2039, SEGMENT_FAIL_MSG)
    segments: list[dict] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise LayoutAiError(2039, SEGMENT_FAIL_MSG)
        seg_type = str(item.get("segmentType") or "")
        seg_text = item.get("text")
        if seg_type not in SEGMENT_TYPES or not isinstance(seg_text, str):
            raise LayoutAiError(2039, SEGMENT_FAIL_MSG)
        segments.append({"index": index, "segmentType": seg_type, "text": seg_text})
    return segments


def _llm_segments(db: Session, tenant_id: int, source: str) -> list[dict]:
    endpoint = (os.environ.get("IMS_LAYOUT_AI_ENDPOINT") or "").strip()
    model = (os.environ.get("IMS_LAYOUT_AI_MODEL") or "").strip()
    api_key = (os.environ.get("IMS_LAYOUT_AI_API_KEY") or os.environ.get("IMS_CONTENT_AI_API_KEY") or "").strip()
    if not endpoint or not model:
        row = db.scalar(
            select(AirModelConfig)
            .where(
                AirModelConfig.deleted == 0,
                AirModelConfig.tenant_id == tenant_id,
                AirModelConfig.status == "CONNECTED",
                AirModelConfig.use_case.in_(("CHAT", "AI_TYPESET_SEMANTIC")),
            )
            .order_by(AirModelConfig.id.desc())
        )
        if row is not None:
            endpoint = endpoint or (row.endpoint_url or "").strip()
            model = model or (row.model_name or "").strip()
    if not endpoint or not model or not api_key:
        raise LayoutAiError(2039, SEGMENT_FAIL_MSG)
    url = endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + " 枚举：" + ",".join(sorted(SEGMENT_TYPES))},
            {"role": "user", "content": source},
        ],
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise LayoutAiError(2039, SEGMENT_FAIL_MSG) from exc
    return _parse_model_segments(str(content))


def segment_source(db: Session, tenant_id: int, source: str) -> list[dict]:
    mode = stub_mode()
    if mode is None:
        segments = _llm_segments(db, tenant_id, source)
    elif mode in _MUTATE:
        segments = [{"index": 0, "segmentType": "PLAIN_PARAGRAPH", "text": source + "改"}]
    elif mode in _FAITHFUL:
        segments = heuristic_segments(source)
    else:
        raise LayoutAiError(2039, SEGMENT_FAIL_MSG)
    joined = "".join(item["text"] for item in segments)
    if normalize_plain(joined) != normalize_plain(source):
        raise LayoutAiError(2037, FIDELITY_MSG)
    return segments


def build_preview(db: Session, tenant_id: int, source: str) -> dict:
    segments = segment_source(db, tenant_id, source)
    decision = decide_template(source)
    layout_html = sanitize_layout_html(render_html(segments, decision["selectedFootballTemplate"]))
    plain_after = normalize_plain(extract_plain_text(layout_html))
    plain_before = normalize_plain(source)
    if plain_after != plain_before:
        raise LayoutAiError(2037, FIDELITY_MSG)
    counts = Counter(item["segmentType"] for item in segments)
    layout_json = {
        "version": 2,
        "bodyFormat": "LAYOUT",
        "selectedFootballTemplate": decision["selectedFootballTemplate"],
        "blocks": segments,
    }
    return {
        "mode": "AUTO",
        "selectedFootballTemplate": decision["selectedFootballTemplate"],
        "selectedTemplateName": decision["selectedTemplateName"],
        "templateDecision": decision["templateDecision"],
        "segments": segments,
        "fidelityCheck": {"passed": True, "plainTextBefore": plain_before, "plainTextAfter": plain_after},
        "segmentationReport": {"segmentCount": len(segments), "segmentTypeCounts": dict(counts)},
        "layoutJson": layout_json,
        "layoutHtml": layout_html,
        "bodyFormat": "LAYOUT",
    }


def resolve_source(row: ContentProject, request_body: str | None) -> str:
    source = row.body if request_body is None else request_body
    source = normalize_plain(source)
    if not source.strip():
        raise LayoutAiError(2036, EMPTY_MSG)
    return source


def guard_article(row: ContentProject) -> None:
    if (row.content_type or "").upper() != "ARTICLE":
        raise LayoutAiError(1500, "仅文章类型可语义排版")
    if row.content_status not in ("DRAFT", "REJECTED"):
        raise LayoutAiError(1502, "业务规则冲突")


def has_layout(row: ContentProject) -> bool:
    return (row.body_format or "PLAIN") == "LAYOUT" or bool((row.layout_html or "").strip())


def run_typeset(db: Session, row: ContentProject, request_body: str | None, *, writing: bool) -> dict:
    guard_article(row)
    source = resolve_source(row, request_body)
    if writing and normalize_plain(row.body) != source:
        raise LayoutAiError(2037, FIDELITY_MSG)
    preview = build_preview(db, row.tenant_id or 0, source)
    if writing and normalize_plain(extract_plain_text(preview["layoutHtml"])) != normalize_plain(row.body):
        raise LayoutAiError(2037, FIDELITY_MSG)
    return preview


def _fail(exc: LayoutAiError):
    return fail(exc.code, exc.msg)


@router.post("/{content_id}/typeset/preview")
def typeset_preview(
    content_id: int,
    body: TypesetPreviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if (body.mode or "AUTO").upper() != "AUTO":
        return fail(1500, "参数校验失败")
    try:
        preview = run_typeset(db, row, body.body, writing=False)
    except LayoutAiError as exc:
        return _fail(exc)
    return ok(preview)


@router.post("/{content_id}/typeset/apply")
def typeset_apply(
    content_id: int,
    body: TypesetApplyBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if (body.mode or "AUTO").upper() != "AUTO":
        return fail(1500, "参数校验失败")
    original_body = row.body
    try:
        if has_layout(row) and not body.overwrite:
            raise LayoutAiError(2031, OVERWRITE_MSG)
        preview = run_typeset(db, row, body.body, writing=True)
    except LayoutAiError as exc:
        return _fail(exc)
    row.layout_html = preview["layoutHtml"]
    row.layout_json = json.dumps(preview["layoutJson"], ensure_ascii=False)
    row.body_format = "LAYOUT"
    row.body = original_body
    db.flush()
    return ok(project_vo(row))
