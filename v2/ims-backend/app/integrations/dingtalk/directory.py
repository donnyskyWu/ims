"""钉钉通讯录真实拉取（2026-10-13）。

做法对齐 V1 `pull_org_directory`：OAuth token、部门 BFS（listsubid 失败再 listsub）、
用户详情里的 title 作为岗位。不引用 V1 包。一次拉取复用同一个 HTTP 客户端。
没有部门结果时由 list_directory 中止，避免空目录停用本地部门。
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

OAUTH_ACCESS_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
OAPI_BASE = "https://oapi.dingtalk.com"
TOKEN_TIMEOUT = 10.0
PULL_TIMEOUT = 30.0

AUTH_SCOPE_HINT = (
    "钉钉返回 50004：部门不在通讯录授权范围。"
    "请在开放平台把该应用的通讯录授权范围改为全部员工或包含根部门，保存并重新发布后再同步。"
    "本次已中止，本地部门未改动。"
)

Poster = Callable[..., dict[str, Any]]


def _credentials() -> tuple[str, str]:
    block = get_settings().dingtalk or {}
    return str(block.get("app_key") or "").strip(), str(block.get("app_secret") or "").strip()


def _safe_error(err: str | None) -> str:
    text = (err or "").replace("\n", " ")
    return text[:300]


def _is_scope_error(err: str | None) -> bool:
    return bool(err and "50004" in err)


def _extract_sub_department_ids(result: dict[str, Any]) -> list[int]:
    """listsubid 给 dept_id_list；listsub 的数组会被包进 result.value。"""
    raw = result.get("dept_id_list")
    if isinstance(raw, list):
        return [int(item) for item in raw if str(item).isdigit()]
    value = result.get("value")
    if not isinstance(value, list):
        return []
    ids: list[int] = []
    for item in value:
        if isinstance(item, dict):
            dept_id = item.get("dept_id") if item.get("dept_id") is not None else item.get("deptId")
            if dept_id is not None and str(dept_id).isdigit():
                ids.append(int(dept_id))
        elif str(item).isdigit():
            ids.append(int(item))
    return ids


def _topapi_post(post: Poster, token: str, path: str, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{OAPI_BASE}/topapi/{path}"
    try:
        data = post(url, params={"access_token": token}, json=body, timeout=PULL_TIMEOUT)
    except httpx.TimeoutException as exc:
        return None, f"timeout:{exc}"
    except httpx.HTTPStatusError as exc:
        body_text = exc.response.text[:300] if exc.response is not None else ""
        return None, f"http_{exc.response.status_code}:{body_text}"
    except Exception as exc:  # noqa: BLE001 — 诊断需要原样原因，且不含密钥
        return None, _safe_error(str(exc))
    if not isinstance(data, dict):
        return None, "bad_payload"
    errcode = int(data.get("errcode") or 0)
    if errcode != 0:
        return None, f"dingtalk_{errcode}:{data.get('errmsg', '')}"[:300]
    result = data.get("result")
    if result is None:
        return {}, None
    if not isinstance(result, dict):
        return {"value": result}, None
    return result, None


def _fetch_sub_department_ids(post: Poster, token: str, dept_id: int) -> tuple[list[int], str | None]:
    body = {"dept_id": dept_id, "language": "zh_CN"}
    result, err = _topapi_post(post, token, "v2/department/listsubid", body)
    if not err and result is not None:
        ids = _extract_sub_department_ids(result)
        if ids:
            return ids, None
    listsub_err = err
    result, err = _topapi_post(post, token, "v2/department/listsub", body)
    if err or result is None:
        return [], err or listsub_err
    return _extract_sub_department_ids(result), None


def _resolve_roots(post: Poster, token: str) -> tuple[list[int], str | None, dict[str, Any]]:
    meta: dict[str, Any] = {}
    scopes, scopes_err = _topapi_post(post, token, "auth/scopes", {})
    if scopes_err:
        meta["scopesError"] = scopes_err
    elif scopes is not None:
        nested = scopes.get("auth_org_scopes")
        if not isinstance(nested, dict):
            nested = scopes
        authed = [int(item) for item in (nested.get("authed_dept") or []) if str(item).isdigit()]
        meta["authedDeptIds"] = authed
        if authed:
            meta["rootSource"] = "auth/scopes"
            return authed, None, meta
    _result, probe_err = _topapi_post(post, token, "v2/department/get", {"dept_id": 1, "language": "zh_CN"})
    if probe_err is None:
        meta.setdefault("rootSource", "probe_dept_1")
        return [1], None, meta
    meta["probeDept1Error"] = probe_err
    return [], probe_err, meta


def _fetch_department_tree(post: Poster, token: str) -> tuple[list[dict[str, Any]], str | None, dict[str, Any]]:
    roots, resolve_err, meta = _resolve_roots(post, token)
    if resolve_err and not roots:
        meta.setdefault("authScopeHint", AUTH_SCOPE_HINT)
        return [], resolve_err, meta
    if not roots:
        return [], "no_authorized_departments", meta
    seen: set[int] = set()
    queue = list(dict.fromkeys(roots))
    departments: list[dict[str, Any]] = []
    first_error: str | None = None
    while queue:
        dept_id = queue.pop(0)
        if dept_id in seen:
            continue
        seen.add(dept_id)
        result, err = _topapi_post(post, token, "v2/department/get", {"dept_id": dept_id, "language": "zh_CN"})
        if err:
            if _is_scope_error(err):
                first_error = first_error or err
                meta["partialScope"] = True
                continue
            return departments, err, meta
        parent_id = int(result.get("parent_id") or 0)
        departments.append(
            {
                "dingtalkDeptId": dept_id,
                "deptId": dept_id,
                "name": str(result.get("name") or ""),
                "parentDingtalkDeptId": None if parent_id in (0, None) else parent_id,
                "parentId": parent_id,
            }
        )
        child_ids, err = _fetch_sub_department_ids(post, token, dept_id)
        if err:
            if _is_scope_error(err):
                first_error = first_error or err
                meta["partialScope"] = True
                continue
            return departments, err, meta
        for child in child_ids:
            if child not in seen:
                queue.append(child)
    if first_error:
        meta["firstApiError"] = first_error
    return departments, None, meta


def _fetch_userids(post: Poster, token: str, dept_id: int) -> tuple[list[str], str | None]:
    user_ids: list[str] = []
    cursor = 0
    while True:
        result, err = _topapi_post(
            post,
            token,
            "v2/user/list",
            {
                "dept_id": dept_id,
                "cursor": cursor,
                "size": 100,
                "order_field": "modify_desc",
                "contain_access_limit": False,
            },
        )
        if err or result is None:
            return user_ids, err
        for row in result.get("list") or []:
            if isinstance(row, dict):
                userid = str(row.get("userid") or "").strip()
                if userid:
                    user_ids.append(userid)
        if not result.get("has_more"):
            break
        next_cursor = result.get("next_cursor")
        if next_cursor is None:
            break
        cursor = int(next_cursor)
    return user_ids, None


def _user_row(detail: dict[str, Any], userid: str, dept_ids: set[int]) -> dict[str, Any]:
    raw_depts = detail.get("dept_id_list") or sorted(dept_ids)
    if not isinstance(raw_depts, list):
        raw_depts = sorted(dept_ids)
    parsed = [int(item) for item in raw_depts if str(item).isdigit()] or sorted(dept_ids)
    title = str(detail.get("title") or detail.get("position") or "").strip()[:64]
    row = {
        "dingtalkUserId": str(detail.get("userid") or userid),
        "userid": str(detail.get("userid") or userid),
        "nickname": str(detail.get("name") or ""),
        "name": str(detail.get("name") or ""),
        "mobile": str(detail.get("mobile") or ""),
        "deptIds": parsed,
    }
    job_number = str(detail.get("job_number") or "").strip()
    if job_number:
        row["jobNumber"] = job_number
    if title:
        row["title"] = title
        row["positionCode"] = title
    return row


def pull_org_directory(
    *,
    app_key: str | None = None,
    app_secret: str | None = None,
    post: Poster | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """拉取部门与人员。失败时返回 (payload_or_none, reason)，reason 不含密钥。"""
    if app_key is None or app_secret is None:
        app_key, app_secret = _credentials()
    app_key = app_key.strip()
    app_secret = app_secret.strip()
    if not app_key or not app_secret:
        return None, "missing_credentials"
    poster = post
    owns_client = poster is None
    client: httpx.Client | None = None
    if poster is None:
        client = httpx.Client(timeout=PULL_TIMEOUT)

        def poster(url: str, *, params=None, json=None, timeout=None) -> dict[str, Any]:
            assert client is not None
            response = client.post(url, params=params, json=json, timeout=timeout or PULL_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("bad_payload")
            return body

    try:
        try:
            token_body = poster(
                OAUTH_ACCESS_TOKEN_URL,
                params=None,
                json={"appKey": app_key, "appSecret": app_secret},
                timeout=TOKEN_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            return None, f"timeout:{exc}"
        except httpx.HTTPStatusError as exc:
            body_text = exc.response.text[:300] if exc.response is not None else ""
            return None, f"http_{exc.response.status_code}:{body_text}"
        except Exception as exc:  # noqa: BLE001
            return None, _safe_error(str(exc))
        token = str((token_body or {}).get("accessToken") or (token_body or {}).get("access_token") or "").strip()
        if not token:
            return None, "no_token_in_response"
        departments, tree_err, meta = _fetch_department_tree(poster, token)
        if tree_err and not departments:
            meta.setdefault("authScopeHint", AUTH_SCOPE_HINT)
            return {"departments": [], "users": [], "meta": meta}, tree_err
        if not departments:
            reason = str(meta.get("firstApiError") or meta.get("probeDept1Error") or "no_departments")
            return {"departments": [], "users": [], "meta": meta}, reason
        if _is_scope_error(str(meta.get("firstApiError") or "")):
            return {"departments": departments, "users": [], "meta": meta}, str(meta["firstApiError"])

        userid_to_depts: dict[str, set[int]] = {}
        for dept in departments:
            dept_id = int(dept["dingtalkDeptId"])
            ids, err = _fetch_userids(poster, token, dept_id)
            if err:
                if _is_scope_error(err):
                    meta["partialScope"] = True
                    meta["firstApiError"] = meta.get("firstApiError") or err
                    continue
                return {"departments": departments, "users": [], "meta": meta}, err
            for userid in ids:
                userid_to_depts.setdefault(userid, set()).add(dept_id)
        if _is_scope_error(str(meta.get("firstApiError") or "")):
            return {"departments": departments, "users": [], "meta": meta}, str(meta["firstApiError"])

        users: list[dict[str, Any]] = []
        for userid, dept_ids in userid_to_depts.items():
            detail, err = _topapi_post(poster, token, "v2/user/get", {"userid": userid, "language": "zh_CN"})
            if err or detail is None:
                logger.warning("dingtalk user/get failed userid=%s", userid)
                continue
            users.append(_user_row(detail, userid, dept_ids))
        meta["departmentsFetched"] = len(departments)
        meta["usersFetched"] = len(users)
        logger.info("dingtalk directory dept=%s user=%s", len(departments), len(users))
        return {"departments": departments, "users": users, "meta": meta}, None
    finally:
        if owns_client and client is not None:
            client.close()


def _limited_probe(url: str, *, params=None, json=None, timeout=None) -> dict[str, Any]:
    with httpx.Client(timeout=timeout or TOKEN_TIMEOUT) as client:
        response = client.post(url, params=params, json=json)
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        raise ValueError("bad_payload")
    return body


def probe_token_and_root() -> dict[str, Any]:
    """换 token，并只请求一次根部门子部门列表。失败时带上 50004 说明。"""
    block = get_settings().dingtalk or {}
    app_key = str(block.get("app_key") or "").strip()
    app_secret = str(block.get("app_secret") or "").strip()
    report: dict[str, Any] = {
        "ok": False,
        "stage": "config",
        "mode": str(block.get("mode") or ""),
        "appKeyMasked": (app_key[:4] + "***") if len(app_key) >= 4 else ("***" if app_key else ""),
        "credentials": {
            "clientId": bool(app_key),
            "clientSecret": bool(app_secret),
            "agentId": bool(str(block.get("agent_id") or "").strip()),
            "corpId": bool(str(block.get("corp_id") or "").strip()),
            "appId": bool(str(block.get("app_id") or "").strip()),
        },
    }
    if not app_key or not app_secret:
        report["error"] = "missing_credentials"
        return report
    try:
        token_body = _limited_probe(
            OAUTH_ACCESS_TOKEN_URL,
            json={"appKey": app_key, "appSecret": app_secret},
            timeout=TOKEN_TIMEOUT,
        )
    except httpx.TimeoutException:
        report["stage"] = "token"
        report["error"] = "timeout"
        return report
    except Exception as exc:  # noqa: BLE001
        report["stage"] = "token"
        report["error"] = _safe_error(str(exc))
        return report
    token = str(token_body.get("accessToken") or token_body.get("access_token") or "").strip()
    if not token:
        report["stage"] = "token"
        report["error"] = "no_token_in_response"
        return report
    report["stage"] = "dept"
    report["tokenOk"] = True
    try:
        listed = _limited_probe(
            f"{OAPI_BASE}/topapi/v2/department/listsubid",
            params={"access_token": token},
            json={"dept_id": 1, "language": "zh_CN"},
            timeout=TOKEN_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        report["error"] = _safe_error(str(exc))
        return report
    errcode = int(listed.get("errcode") or 0)
    if errcode != 0:
        report["error"] = f"dingtalk_{errcode}:{listed.get('errmsg', '')}"[:300]
        report["errorCode"] = errcode
        if errcode == 50004:
            report["hint"] = AUTH_SCOPE_HINT
        return report
    result = listed.get("result") if isinstance(listed.get("result"), dict) else {}
    ids = result.get("dept_id_list") if isinstance(result, dict) else []
    report["ok"] = True
    report["rootChildCount"] = len(ids) if isinstance(ids, list) else 0
    return report
