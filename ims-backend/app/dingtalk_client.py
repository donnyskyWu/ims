"""钉钉 OpenAPI 客户端（L3 联调：OAuth accessToken + 通讯录拉取）。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.settings_runtime import get_param

logger = logging.getLogger(__name__)

OAUTH_ACCESS_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
OAPI_BASE = "https://oapi.dingtalk.com"
DEFAULT_TIMEOUT = 10.0
PULL_TIMEOUT = 30.0

AUTH_SCOPE_HINT = (
    "钉钉返回 50004 表示请求的部门不在「通讯录授权范围」内（与开放平台「接口权限」不同）。"
    "请在开放平台 → 应用 → 权限管理 → 通讯录授权范围 选择「全部员工」或包含根部门的范围，"
    "保存并重新发布应用后再同步。"
)


def fetch_oauth_access_token() -> tuple[str | None, str | None]:
    """使用 Client ID / Client Secret 换取 accessToken。未配置凭证时 (None, reason)。"""
    app_key = get_param("dingtalk.clientId").strip()
    app_secret = get_param("dingtalk.clientSecret").strip()
    if not app_key or not app_secret:
        return None, "missing_credentials"
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(
                OAUTH_ACCESS_TOKEN_URL,
                json={"appKey": app_key, "appSecret": app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        return None, f"http_{exc.response.status_code}:{body}"
    except Exception as exc:  # noqa: BLE001 — L3 诊断需原样返回
        return None, str(exc)

    token = (data.get("accessToken") or data.get("access_token") or "").strip()
    if not token:
        return None, f"no_token_in_response:{data!r}"[:200]
    return token, None


def _topapi_post(token: str, path: str, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """调用 oapi topapi（access_token 来自 OAuth2）。"""
    url = f"{OAPI_BASE}/topapi/{path}"
    try:
        with httpx.Client(timeout=PULL_TIMEOUT) as client:
            resp = client.post(url, params={"access_token": token}, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body_text = exc.response.text[:500] if exc.response is not None else ""
        return None, f"http_{exc.response.status_code}:{body_text}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    errcode = int(data.get("errcode") or 0)
    if errcode != 0:
        return None, f"dingtalk_{errcode}:{data.get('errmsg', '')}"[:500]
    result = data.get("result")
    if result is None:
        return {}, None
    if not isinstance(result, dict):
        return {"value": result}, None
    return result, None


def _is_dept_out_of_scope(err: str | None) -> bool:
    return bool(err and "dingtalk_50004" in err)


def _extract_sub_department_ids(result: dict[str, Any]) -> list[int]:
    """
    listsubid 返回 result.dept_id_list；listsub 常返回 result 为部门对象数组
    （_topapi_post 包装为 result.value）。
    """
    raw = result.get("dept_id_list")
    if isinstance(raw, list):
        return [int(x) for x in raw if str(x).isdigit()]
    value = result.get("value")
    if isinstance(value, list):
        ids: list[int] = []
        for item in value:
            if isinstance(item, dict):
                did = item.get("dept_id") if item.get("dept_id") is not None else item.get("deptId")
                if did is not None and str(did).isdigit():
                    ids.append(int(did))
            elif str(item).isdigit():
                ids.append(int(item))
        return ids
    return []


def _fetch_sub_department_ids(
    token: str,
    dept_id: int,
) -> tuple[list[int], str | None, str]:
    """优先 listsubid（ID 列表）；失败或空时回退 listsub 并解析对象数组。"""
    body = {"dept_id": dept_id, "language": "zh_CN"}
    result, err = _topapi_post(token, "v2/department/listsubid", body)
    if not err:
        ids = _extract_sub_department_ids(result)
        if ids:
            return ids, None, "v2/department/listsubid"
    listsub_err = err
    result, err = _topapi_post(token, "v2/department/listsub", body)
    if err:
        return [], err or listsub_err, "v2/department/listsub"
    return _extract_sub_department_ids(result), None, "v2/department/listsub"


def fetch_auth_org_scopes(token: str) -> tuple[dict[str, Any] | None, str | None]:
    """topapi/auth/scopes：应用可见的通讯录授权部门/人员范围。"""
    result, err = _topapi_post(token, "auth/scopes", {})
    if err:
        return None, err
    scopes = result.get("auth_org_scopes")
    if not isinstance(scopes, dict):
        return {}, None
    return scopes, None


def resolve_authorized_root_dept_ids(token: str) -> tuple[list[int], str | None, dict[str, Any]]:
    """
    解析 BFS 起点部门 id：优先 auth/scopes 的 authed_dept；否则探测 dept_id=1。
    返回 (root_ids, fatal_error, diagnostics)。
    """
    diagnostics: dict[str, Any] = {}
    scopes, scopes_err = fetch_auth_org_scopes(token)
    if scopes_err:
        diagnostics["scopesError"] = scopes_err
        logger.warning("dingtalk auth/scopes failed: %s", scopes_err)
    elif scopes is not None:
        authed_dept_raw = scopes.get("authed_dept") or []
        authed_user_raw = scopes.get("authed_user") or []
        authed_dept = [int(x) for x in authed_dept_raw if str(x).isdigit()]
        diagnostics["authedDeptIds"] = authed_dept
        diagnostics["authedUserCount"] = len(authed_user_raw) if isinstance(authed_user_raw, list) else 0
        if authed_dept:
            diagnostics["rootSource"] = "auth/scopes"
            return authed_dept, None, diagnostics
        if diagnostics["authedUserCount"] > 0:
            diagnostics["rootSource"] = "auth/scopes_user_only"
            diagnostics["authScopeHint"] = (
                "当前授权范围为「部分员工」且未列出 authed_dept；全量部门树同步需改为「全部员工」或按部门授权。"
            )

    _, probe_err = _topapi_post(token, "v2/department/get", {"dept_id": 1, "language": "zh_CN"})
    if probe_err is None:
        diagnostics.setdefault("rootSource", "probe_dept_1")
        return [1], None, diagnostics
    diagnostics["probeDept1Error"] = probe_err
    if _is_dept_out_of_scope(probe_err):
        hint = diagnostics.get("authScopeHint") or AUTH_SCOPE_HINT
        diagnostics["authScopeHint"] = hint
        return [], probe_err, diagnostics
    return [], probe_err, diagnostics


def fetch_department_tree(
    token: str,
    root_dept_ids: list[int] | None = None,
) -> tuple[list[dict[str, Any]], str | None, dict[str, Any]]:
    """BFS 拉取部门子树，返回 [{deptId, name, parentId}, ...] 与诊断信息。"""
    meta: dict[str, Any] = {}
    if root_dept_ids is None:
        root_dept_ids, resolve_err, resolve_meta = resolve_authorized_root_dept_ids(token)
        meta.update(resolve_meta)
        if resolve_err and not root_dept_ids:
            return [], resolve_err, meta

    if not root_dept_ids:
        meta.setdefault("authScopeHint", AUTH_SCOPE_HINT)
        return [], "no_authorized_departments", meta

    meta["authorizedRootDeptIds"] = list(root_dept_ids)
    seen: set[int] = set()
    queue: list[int] = list(dict.fromkeys(root_dept_ids))
    depts: list[dict[str, Any]] = []
    first_error: str | None = None
    skipped: list[dict[str, Any]] = []
    listsub_calls = 0
    sub_ids_discovered = 0

    while queue:
        dept_id = queue.pop(0)
        if dept_id in seen:
            continue
        seen.add(dept_id)
        result, err = _topapi_post(token, "v2/department/get", {"dept_id": dept_id, "language": "zh_CN"})
        if err:
            if _is_dept_out_of_scope(err):
                skipped.append({"deptId": dept_id, "error": err, "phase": "get"})
                if first_error is None:
                    first_error = err
                continue
            return depts, err, meta
        name = str(result.get("name") or "")
        parent_id = int(result.get("parent_id") or 0)
        depts.append({"deptId": dept_id, "name": name, "parentId": parent_id})
        listsub_calls += 1
        child_ids, err, listsub_api = _fetch_sub_department_ids(token, dept_id)
        meta["lastListsubApi"] = listsub_api
        if err:
            if _is_dept_out_of_scope(err):
                skipped.append({"deptId": dept_id, "error": err, "phase": "listsub"})
                if first_error is None:
                    first_error = err
                continue
            return depts, err, meta
        sub_ids_discovered += len(child_ids)
        if dept_id in root_dept_ids and len(root_dept_ids) == 1:
            meta["rootSubDeptIdCount"] = len(child_ids)
        for child in child_ids:
            if child not in seen:
                queue.append(child)

    meta["listsubCalls"] = listsub_calls
    meta["subDepartmentIdsDiscovered"] = sub_ids_discovered

    if skipped:
        meta["skippedDeptErrors"] = skipped[:20]
    if first_error:
        meta["firstApiError"] = first_error
    if first_error and depts:
        meta["partialScope"] = True
        meta.setdefault(
            "authScopeHint",
            "部分子部门不在授权范围内已跳过；如需全组织请在开放平台扩大通讯录授权范围并发布应用。",
        )
    logger.info(
        "dingtalk department tree: roots=%s dept_count=%d skipped=%d first_error=%s",
        root_dept_ids,
        len(depts),
        len(skipped),
        first_error,
    )
    return depts, None, meta


def fetch_userids_in_department(token: str, dept_id: int) -> tuple[list[str], str | None]:
    """分页拉取部门下 userid 列表。"""
    user_ids: list[str] = []
    cursor = 0
    while True:
        result, err = _topapi_post(
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
        if err:
            return user_ids, err
        batch = result.get("list") or []
        for row in batch:
            if isinstance(row, dict):
                uid = str(row.get("userid") or "").strip()
                if uid:
                    user_ids.append(uid)
        if not result.get("has_more"):
            break
        next_cursor = result.get("next_cursor")
        if next_cursor is None:
            break
        cursor = int(next_cursor)
    return user_ids, None


def fetch_user_detail(token: str, userid: str) -> tuple[dict[str, Any] | None, str | None]:
    result, err = _topapi_post(token, "v2/user/get", {"userid": userid, "language": "zh_CN"})
    if err:
        return None, err
    return result, None


def pull_org_directory() -> tuple[dict[str, Any] | None, str | None]:
    """拉取全量部门 + 人员明细（去重）。失败时 (None, reason) 或带 meta 的部分结果。"""
    token, err = fetch_oauth_access_token()
    if err or not token:
        return None, err or "missing_token"
    depts, tree_err, tree_meta = fetch_department_tree(token)
    meta: dict[str, Any] = dict(tree_meta)
    if tree_err and not depts:
        meta.setdefault("authScopeHint", AUTH_SCOPE_HINT)
        return {"departments": [], "users": [], "meta": meta}, tree_err

    userid_to_depts: dict[str, set[int]] = {}
    user_list_errors: list[dict[str, Any]] = []
    for dept in depts:
        dept_id = int(dept["deptId"])
        ids, err = fetch_userids_in_department(token, dept_id)
        if err:
            user_list_errors.append({"deptId": dept_id, "error": err})
            if meta.get("firstApiError") is None:
                meta["firstApiError"] = err
            if _is_dept_out_of_scope(err):
                continue
            return {"departments": depts, "users": [], "meta": meta}, err
        for uid in ids:
            userid_to_depts.setdefault(uid, set()).add(dept_id)

    if user_list_errors:
        meta["userListErrors"] = user_list_errors[:20]
        meta["partialScope"] = True

    users: list[dict[str, Any]] = []
    for uid, dept_ids in userid_to_depts.items():
        detail, err = fetch_user_detail(token, uid)
        if err:
            if meta.get("firstApiError") is None:
                meta["firstApiError"] = err
            logger.warning("dingtalk user/get failed userid=%s: %s", uid, err)
            continue
        if detail is None:
            continue
        dept_id_list = detail.get("dept_id_list") or list(dept_ids)
        if not isinstance(dept_id_list, list):
            dept_id_list = list(dept_ids)
        parsed_depts = [int(x) for x in dept_id_list if str(x).isdigit()]
        if not parsed_depts:
            parsed_depts = sorted(dept_ids)
        users.append(
            {
                "userid": str(detail.get("userid") or uid),
                "name": str(detail.get("name") or ""),
                "mobile": str(detail.get("mobile") or ""),
                "unionid": str(detail.get("unionid") or ""),
                "deptIds": parsed_depts,
            }
        )

    meta["departmentsFetched"] = len(depts)
    meta["usersFetched"] = len(users)
    logger.info(
        "dingtalk pull_org_directory: dept_count=%d user_count=%d first_error=%s",
        len(depts),
        len(users),
        meta.get("firstApiError"),
    )
    return {"departments": depts, "users": users, "meta": meta}, None
