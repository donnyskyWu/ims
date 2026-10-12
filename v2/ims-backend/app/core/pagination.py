"""分页与排序白名单。"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import BizError


@dataclass
class Page:
    page_no: int = 1
    page_size: int = 10
    sort_field: str | None = None
    sort_order: str = "desc"


def parse_page(params: dict, allowed_sort: list[str] | None = None, default_sort: list[tuple[str, str]] | None = None) -> Page:
    errors = []

    def _int(name, default, minimum, maximum=None):
        raw = params.get(name, None)
        if raw is None or raw == "":
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError):
            errors.append({"field": name, "message": "须为整数"})
            return default
        if value < minimum or (maximum is not None and value > maximum):
            errors.append({"field": name, "message": "超出允许范围"})
            return default
        return value

    page_no = _int("pageNo", 1, 1)
    page_size = _int("pageSize", 10, 1, 100)
    sort_field = params.get("sortField") or None
    sort_order = (params.get("sortOrder") or "desc").lower()
    if sort_order not in ("asc", "desc"):
        errors.append({"field": "sortOrder", "message": "排序方向不正确"})
        sort_order = "desc"
    if sort_field:
        if not allowed_sort or sort_field not in allowed_sort:
            errors.append({"field": "sortField", "message": "不支持该排序字段"})
    if errors:
        raise BizError(1001, data={"fieldErrors": errors})
    return Page(page_no, page_size, sort_field, sort_order)


def page_result(rows, total: int, page: Page) -> dict:
    return {"list": rows, "total": total, "pageNo": page.page_no, "pageSize": page.page_size}
