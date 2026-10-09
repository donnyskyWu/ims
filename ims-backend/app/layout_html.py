"""审核/查看用 layout_html 消毒（BR-033 · 只读展示，保留已插入图片）。"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_ALLOWED = frozenset(
    {
        "p",
        "br",
        "div",
        "span",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "blockquote",
        "pre",
        "code",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
        "img",
        "hr",
        "figure",
        "figcaption",
        "section",
        "article",
        "sup",
        "sub",
    }
)
_VOID = frozenset({"br", "img", "hr"})
_DROP = frozenset(
    {
        "script",
        "style",
        "iframe",
        "object",
        "embed",
        "noscript",
        "template",
        "svg",
        "math",
        "form",
        "input",
        "button",
        "textarea",
        "select",
        "option",
        "video",
        "audio",
        "source",
        "canvas",
        "link",
        "meta",
        "base",
    }
)
_ATTR_ORDER = (
    "src",
    "alt",
    "title",
    "href",
    "width",
    "height",
    "colspan",
    "rowspan",
    "data-w",
    "data-file-key",
    "data-zone",
    "data-paywall",
    "data-preset",
    "class",
    "style",
)
_STYLE_DECL = re.compile(r"(width|max-width|height)\s*:\s*(\d+(?:\.\d+)?)(px|%)", re.I)
_CLASS = re.compile(r"^[A-Za-z0-9 _-]+$")
_FILE_KEY = re.compile(r"^[A-Za-z0-9_./-]{1,256}$")
_DIGITS = re.compile(r"^\d{1,4}$")
_SPAN = re.compile(r"^\d{1,3}$")


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _safe_style(style: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for match in _STYLE_DECL.finditer(style or ""):
        prop = match.group(1).lower()
        if prop in seen:
            continue
        seen.add(prop)
        parts.append(f"{prop}:{match.group(2)}{match.group(3).lower()}")
    return ";".join(parts)


def _safe_url(value: str, kind: str) -> str:
    url = (value or "").replace("\x00", "").strip()
    lower = url.lower()
    if not url or lower.startswith(("javascript:", "vbscript:", "data:text")):
        return ""
    if kind == "src":
        if lower.startswith("data:image/"):
            mime = lower[len("data:image/") :].split(";", 1)[0]
            if mime not in ("png", "jpeg", "jpg", "gif", "webp"):
                return ""
            if ";base64," not in lower:
                return ""
            return url
        if lower.startswith(("https://", "http://")):
            return url
        if lower.startswith("/") and not lower.startswith("//"):
            return url
        return ""
    if lower.startswith(("https://", "http://", "mailto:", "#")):
        return url
    return ""


def _clean_attrs(tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str]]:
    raw: dict[str, str] = {}
    for key, value in attrs:
        if not key:
            continue
        raw[key.lower()] = "" if value is None else value
    cleaned: dict[str, str] = {}
    if tag == "img":
        src = _safe_url(raw.get("src", ""), "src")
        if not src:
            return []
        cleaned["src"] = src
        alt = raw.get("alt", "")
        if alt:
            cleaned["alt"] = alt.replace("\x00", "")
        if raw.get("title"):
            cleaned["title"] = raw["title"].replace("\x00", "")[:128]
        for key in ("width", "height"):
            value = raw.get(key, "").strip().lower()
            if re.fullmatch(r"\d{1,4}(px)?", value):
                cleaned[key] = value
        data_w = raw.get("data-w", "").strip()
        if _DIGITS.fullmatch(data_w):
            cleaned["data-w"] = data_w
        file_key = raw.get("data-file-key", "").strip()
        if file_key and ".." not in file_key and _FILE_KEY.fullmatch(file_key):
            cleaned["data-file-key"] = file_key
        style = _safe_style(raw.get("style", ""))
        if "data-w" in cleaned and "width:" not in style:
            width = f"width:{cleaned['data-w']}px"
            style = f"{width};{style}" if style else width
        if style:
            cleaned["style"] = style
    elif tag == "a":
        href = _safe_url(raw.get("href", ""), "href")
        if href:
            cleaned["href"] = href
        if raw.get("title"):
            cleaned["title"] = raw["title"].replace("\x00", "")[:128]
    elif tag in ("td", "th"):
        for key in ("colspan", "rowspan"):
            if _SPAN.fullmatch(raw.get(key, "").strip()):
                cleaned[key] = raw[key].strip()
    if _CLASS.fullmatch(raw.get("class", "").strip()):
        cleaned["class"] = raw["class"].strip()
    zone = raw.get("data-zone", "").strip().lower()
    if zone in ("paid", "body_paid", "free", "free_body"):
        cleaned["data-zone"] = zone
    paywall = raw.get("data-paywall", "").strip().lower()
    if paywall in ("1", "true", "yes", "paid", "0", "false", "no", "free"):
        cleaned["data-paywall"] = paywall
    preset = raw.get("data-preset", "").strip().lower()
    if preset in ("clean-read", "marketing", "decision-scan", "analysis-report"):
        cleaned["data-preset"] = preset
    if tag != "img":
        style = _safe_style(raw.get("style", ""))
        if style and tag in ("p", "div", "span", "figure", "section", "td", "th"):
            cleaned["style"] = style
    ordered = [(key, cleaned[key]) for key in _ATTR_ORDER if key in cleaned]
    return ordered


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _DROP:
            self._skip += 1
            return
        if self._skip or tag not in _ALLOWED:
            return
        cleaned = _clean_attrs(tag, attrs)
        if tag == "img" and not cleaned:
            return
        attr_s = "".join(f' {key}="{_esc(value)}"' for key, value in cleaned)
        self.parts.append(f"<{tag}{attr_s}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _DROP:
            if self._skip:
                self._skip -= 1
            return
        if self._skip or tag not in _ALLOWED or tag in _VOID:
            return
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        self.parts.append(_esc(data))


def sanitize_layout_html(raw: str | None) -> str:
    if not raw:
        return ""
    parser = _Sanitizer()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return ""
    return "".join(parser.parts)
