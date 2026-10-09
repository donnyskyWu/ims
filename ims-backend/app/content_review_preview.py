"""审核抽屉付费/免费双栏只读派生（#119）。

假设：`ims_content_project` 没有独立 `paid_body` / `free_body` 列。
ADR-077 的 `isPaywall` 只存在于生成请求上下文，不落库；原型编辑态字段名是
`body_paid` 与 `free_body`。本模块不新增表列、不新增 REST，只在既有
`GET /admin-api/ims/content/review/{reviewNo}` 的 `contentPreview` 里给出只读双栏。

派生顺序（先命中先用）：

1. `layout_html` 分区标记：`data-zone="paid"|"free"`（亦接受 `body_paid` / `free_body`），
   或付费标记 `data-paywall="true"|"false"`。`columnSplit=layout-zone`。
2. 正文分隔行 `---FREE---`：分隔前为付费区，分隔后为免费区。
   与现有内容编辑「正文」单栏兼容。`columnSplit=body-marker`。
3. `documentType=OFFICIAL_PLAN`（ADR-077 付费标记）：全文进付费栏。
   `columnSplit=paywall-doc`。
4. 其余：全文进免费栏（非官方方案默认 `free_body`）。`columnSplit=default-free`。

全文优先取 `body`；`body` 为空时从 `layout_html` 抽纯文本。
`layoutHtml` 原样回传，供只读预览；没有版式时前端用 `body` 纯文本 fallback。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_FREE_MARK = "---FREE---"
_PAID_DOC_TYPES = {"OFFICIAL_PLAN"}
_SKIP_TAGS = {"script", "style", "noscript"}
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "br", "blockquote"}
_VOID_TAGS = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "col"}


def empty_preview() -> dict:
    return {
        "layoutHtml": "",
        "body": "",
        "documentType": "",
        "contentType": "",
        "matchType": None,
        "matchScheme": [],
        "matchSummary": "",
        "paidBody": "",
        "freeBody": "",
        "paywall": False,
        "columnSplit": "default-free",
    }


def build_content_preview(project) -> dict:
    if project is None:
        return empty_preview()
    body = project.body or ""
    layout_html = project.layout_html or ""
    document_type = project.document_type or ""
    columns = split_paid_free(body, layout_html, document_type)
    summary = (project.match_summary or project.competition_name or "") if project else ""
    return {
        "layoutHtml": layout_html,
        "body": body,
        "documentType": document_type,
        "contentType": project.content_type or "",
        "matchType": project.match_type,
        "matchScheme": list(project.match_scheme or []),
        "matchSummary": summary,
        **columns,
    }


def split_paid_free(body: str, layout_html: str, document_type: str) -> dict:
    paid_html, free_html, zoned = _extract_zones(layout_html or "")
    if zoned:
        paid = _norm(paid_html)
        free = _norm(free_html)
        return _columns(paid, free, "layout-zone", document_type)
    marked = _split_body_marker(body or "")
    if marked is not None:
        paid, free = marked
        return _columns(paid, free, "body-marker", document_type)
    plain = (body or "").strip() or _plain_text(layout_html or "")
    if (document_type or "").strip() in _PAID_DOC_TYPES:
        return _columns(plain, "", "paywall-doc", document_type)
    return _columns("", plain, "default-free", document_type)


def _columns(paid: str, free: str, split: str, document_type: str) -> dict:
    paywall = bool(paid.strip()) or (document_type or "").strip() in _PAID_DOC_TYPES
    return {
        "paidBody": paid.strip(),
        "freeBody": free.strip(),
        "paywall": paywall,
        "columnSplit": split,
    }


def _split_body_marker(body: str) -> tuple[str, str] | None:
    if _FREE_MARK not in body:
        return None
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == _FREE_MARK:
            paid = "\n".join(lines[:idx]).strip()
            free = "\n".join(lines[idx + 1 :]).strip()
            return paid, free
    paid, free = body.split(_FREE_MARK, 1)
    return paid.strip(), free.strip()


def _zone_name(attrs: list[tuple[str, str | None]]) -> str | None:
    bag = {key.lower(): (value or "") for key, value in attrs}
    if "data-zone" in bag:
        zone = bag["data-zone"].strip().lower()
        if zone in ("paid", "body_paid"):
            return "paid"
        if zone in ("free", "free_body"):
            return "free"
    if "data-paywall" in bag:
        flag = bag["data-paywall"].strip().lower()
        if flag in ("1", "true", "yes", "paid"):
            return "paid"
        if flag in ("0", "false", "no", "free"):
            return "free"
    return None


class _ZoneTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paid: list[str] = []
        self.free: list[str] = []
        self.found = False
        self._zone: str | None = None
        self._depth = 0
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, void=tag.lower() in _VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, void=True)

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], void: bool) -> None:
        name = tag.lower()
        if self._skip:
            self._skip += 1
            return
        if name in _SKIP_TAGS:
            self._skip = 1
            return
        if self._zone is None:
            zone = _zone_name(attrs)
            if zone:
                self.found = True
                self._zone = zone
                self._depth = 0 if void else 1
                if void:
                    self._zone = None
                return
        elif not void:
            self._depth += 1
        if self._zone and name in _BLOCK_TAGS:
            self._append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip:
            self._skip -= 1
            return
        if not self._zone:
            return
        if tag.lower() in _BLOCK_TAGS:
            self._append("\n")
        self._depth -= 1
        if self._depth <= 0:
            self._zone = None
            self._depth = 0

    def handle_data(self, data: str) -> None:
        if self._skip or not self._zone or not data:
            return
        self._append(data)

    def _append(self, text: str) -> None:
        if self._zone == "paid":
            self.paid.append(text)
        elif self._zone == "free":
            self.free.append(text)


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if self._skip:
            self._skip += 1
            return
        if name in _SKIP_TAGS:
            self._skip = 1
            return
        if name in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip:
            self._skip -= 1
            return
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        self.parts.append(data)


def _extract_zones(layout_html: str) -> tuple[str, str, bool]:
    if not layout_html or ("data-zone" not in layout_html.lower() and "data-paywall" not in layout_html.lower()):
        return "", "", False
    parser = _ZoneTextParser()
    parser.feed(layout_html)
    parser.close()
    if not parser.found:
        return "", "", False
    return "".join(parser.paid), "".join(parser.free), True


def _plain_text(layout_html: str) -> str:
    if not layout_html.strip():
        return ""
    parser = _PlainTextParser()
    parser.feed(layout_html)
    parser.close()
    return _norm("".join(parser.parts))


def _norm(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r\n", "\n").splitlines()]
    kept: list[str] = []
    for line in lines:
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept).strip()
