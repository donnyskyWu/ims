"""只读预览用的 layout_html 消毒。存储仍保留原文；列表/详情响应走这里。"""

from __future__ import annotations

from html import escape, unescape
from html.parser import HTMLParser

_DROP_TAGS = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "form",
    "input",
    "button",
    "textarea",
    "select",
    "option",
    "link",
    "meta",
    "base",
    "svg",
    "math",
    "noscript",
    "template",
}
_ALLOWED = {
    "p",
    "div",
    "span",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "sub",
    "sup",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "a",
    "img",
    "figure",
    "figcaption",
    "section",
    "article",
}
_VOID = {"br", "hr", "img"}
_DATA_IMAGES = {
    "data:image/png",
    "data:image/jpeg",
    "data:image/jpg",
    "data:image/gif",
    "data:image/webp",
}


def _compact(value: str) -> str:
    return "".join(unescape(value or "").split()).lower()


def _safe_url(value: str, *, allow_data_image: bool) -> str | None:
    raw = unescape(value or "").strip()
    if not raw:
        return None
    compact = _compact(raw)
    if compact.startswith(("javascript:", "vbscript:")):
        return None
    if compact.startswith("data:"):
        if not allow_data_image:
            return None
        mime = compact.split(";", 1)[0]
        if mime not in _DATA_IMAGES:
            return None
        return raw
    if compact.startswith(("http://", "https://", "mailto:", "/", "./", "../")):
        return raw
    if ":" not in raw.split("/", 1)[0]:
        return raw
    return None


def _safe_style(value: str) -> str | None:
    raw = unescape(value or "").strip()
    if not raw:
        return None
    low = raw.lower()
    if any(token in low for token in ("javascript", "expression", "behavior", "@import", "vbscript", "-moz-binding")):
        return None
    return raw


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, self_closing=True)

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], self_closing: bool) -> None:
        name = (tag or "").lower()
        if name in _DROP_TAGS:
            if not self_closing:
                self.skip += 1
            return
        if self.skip or name not in _ALLOWED:
            return
        rendered: list[str] = []
        for key, val in attrs:
            attr = (key or "").lower()
            if not attr or attr.startswith("on") or attr in {"srcdoc", "formaction"}:
                continue
            text = unescape(val or "")
            if attr in {"class", "title"} or (name in {"td", "th"} and attr in {"colspan", "rowspan"}):
                rendered.append(f'{attr}="{escape(text, quote=True)}"')
                continue
            if name == "a" and attr == "href":
                url = _safe_url(text, allow_data_image=False)
                if url:
                    rendered.append(f'href="{escape(url, quote=True)}"')
                continue
            if name == "a" and attr == "target" and text.strip().lower() == "_blank":
                rendered.append('target="_blank" rel="noopener noreferrer"')
                continue
            if name == "img" and attr == "src":
                url = _safe_url(text, allow_data_image=True)
                if url:
                    rendered.append(f'src="{escape(url, quote=True)}"')
                continue
            if name == "img" and attr in {"alt", "width", "height"}:
                rendered.append(f'{attr}="{escape(text, quote=True)}"')
                continue
            if attr == "style":
                style = _safe_style(text)
                if style:
                    rendered.append(f'style="{escape(style, quote=True)}"')
        if name == "img" and not any(item.startswith("src=") for item in rendered):
            return
        attr_s = (" " + " ".join(rendered)) if rendered else ""
        self.parts.append(f"<{name}{attr_s}>")

    def handle_endtag(self, tag: str) -> None:
        name = (tag or "").lower()
        if name in _DROP_TAGS:
            if self.skip:
                self.skip -= 1
            return
        if self.skip or name not in _ALLOWED or name in _VOID:
            return
        self.parts.append(f"</{name}>")

    def handle_data(self, data: str) -> None:
        if self.skip or not data:
            return
        self.parts.append(escape(data))


def sanitize_layout_html(raw: str | None) -> str:
    text = raw or ""
    if not text.strip():
        return ""
    parser = _Sanitizer()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts).strip()
