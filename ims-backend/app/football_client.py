"""Football WebAPI 客户端（订单只读 + 方案写路径桩）。"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.core import FOOTBALL_TIMEOUT_SEC
from app.settings_runtime import get_param

ORDER_PATH = "/admin-api/ops/football-order/list"
ARTICLE_CREATE_PATH = "/rpc-api/member/article/create"
ARTICLE_UPDATE_PATH = "/rpc-api/member/article/update"
ARTICLE_STATUS_PATH = "/rpc-api/member/article/status-change"
DEFAULT_TIMEOUT = FOOTBALL_TIMEOUT_SEC


def base_url() -> str:
    return get_param("football.webapiBaseUrl").strip().rstrip("/")


def fetch_football_orders(params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """成功返回 (payload, None)；失败返回 (None, reason)。"""
    root = base_url()
    if not root:
        return None, "unconfigured"
    url = f"{root}{ORDER_PATH}"
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            body = resp.json()
    except Exception:
        return None, "timeout"
    if not isinstance(body, dict):
        return None, "bad_payload"
    code = body.get("code")
    if code not in (0, "0", None):
        return None, "upstream_error"
    data = body.get("data")
    if not isinstance(data, dict):
        return None, "bad_payload"
    return data, None


def sum_revenue(
    *,
    start_date: str,
    end_date: str,
    author_id: str | None = None,
    status: int = 1,
) -> tuple[float | None, str | None]:
    """按 authorId 汇总成功订单实付；失败时 revenue=None。"""
    params: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "status": status,
        "pageNum": 1,
        "pageSize": 500,
    }
    if author_id:
        params["authorId"] = author_id
    data, err = fetch_football_orders(params)
    if err or data is None:
        return None, err or "unknown"
    rows = data.get("list") or []
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if status is not None and row.get("status") not in (status, str(status)):
            continue
        try:
            total += float(row.get("payAmount") or row.get("amount") or 0)
        except (TypeError, ValueError):
            continue
    return round(total, 2), None


def article_stub_mode() -> str:
    """unconfigured | success | fail — 未配置基址时默认 fail（进补偿队列）。"""
    explicit = (os.environ.get("IMS_FOOTBALL_ARTICLE_STUB") or "").strip().lower()
    if explicit:
        return explicit
    if base_url():
        return "http"
    return "unconfigured"


def sync_article_upsert(payload: dict[str, Any]) -> tuple[bool, str | None, int | None, str | None]:
    mode = article_stub_mode()
    if mode == "unconfigured":
        return False, None, 1271, "Football WebAPI 未配置"
    if mode == "fail":
        return False, None, 1272, "Football 对端拒绝"
    if mode == "http":
        root = base_url()
        existing = payload.get("existingArticleId")
        path = ARTICLE_UPDATE_PATH if existing else ARTICLE_CREATE_PATH
        body = {
            "authorId": payload.get("authorId"),
            "title": payload.get("title"),
            "content": payload.get("content"),
            "status": payload.get("status", -1),
        }
        if existing:
            body["id"] = existing
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.request("PUT" if existing else "POST", f"{root}{path}", json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return False, None, 1271, "Football 请求超时"
        if isinstance(data, dict) and data.get("code") not in (0, "0", None):
            msg = str(data.get("msg") or "Football 业务失败")[:200]
            return False, None, 1272, msg
        article_id = existing
        if not article_id and isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, dict):
                article_id = inner.get("id") or inner.get("articleId")
            elif inner is not None:
                article_id = str(inner)
        if not article_id:
            article_id = f"FA{payload.get('contentId')}"
        return True, str(article_id), None, None
    article_id = payload.get("existingArticleId") or f"FA{payload.get('contentId')}"
    return True, str(article_id), None, None


def sync_article_shelf_off(article_id: str) -> tuple[bool, int | None, str | None]:
    mode = article_stub_mode()
    if mode == "unconfigured":
        return False, 1271, "Football WebAPI 未配置"
    if mode == "fail":
        return False, 1272, "Football 下架失败"
    if mode == "http":
        root = base_url()
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{root}{ARTICLE_STATUS_PATH}", json={"id": article_id, "status": 0})
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return False, 1271, "Football 请求超时"
        if isinstance(data, dict) and data.get("code") not in (0, "0", None):
            return False, 1272, str(data.get("msg") or "Football 业务失败")[:200]
        return True, None, None
    return True, None, None
