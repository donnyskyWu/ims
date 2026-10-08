"""钉钉通讯录：授权范围解析与部门树 BFS（单元测试，无 L3）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.dingtalk_client import fetch_department_tree, resolve_authorized_root_dept_ids

pytestmark = pytest.mark.l3  # 跳过 autouse schema reset（纯 mock，无 DB）


def _post_side_effect(token: str, path: str, body: dict):
    if path == "auth/scopes":
        return {"auth_org_scopes": {"authed_dept": [100, 200], "authed_user": []}}, None
    if path == "v2/department/get":
        dept_id = int(body["dept_id"])
        names = {100: "A", 200: "B", 101: "A1"}
        if dept_id not in names:
            return None, "dingtalk_50004:请求的部门id不在授权范围内"
        return {"name": names[dept_id], "parent_id": 100 if dept_id == 101 else 1}, None
    if path in ("v2/department/listsubid", "v2/department/listsub"):
        dept_id = int(body["dept_id"])
        if dept_id == 100:
            return {"dept_id_list": [101, 999]}, None
        return {"dept_id_list": []}, None
    return {}, None


@patch("app.dingtalk_client._topapi_post", side_effect=_post_side_effect)
def test_resolve_roots_from_auth_scopes(_mock):
    roots, err, meta = resolve_authorized_root_dept_ids("tok")
    assert err is None
    assert roots == [100, 200]
    assert meta.get("rootSource") == "auth/scopes"


@patch("app.dingtalk_client._topapi_post", side_effect=_post_side_effect)
def test_fetch_department_tree_skips_out_of_scope_child(_mock):
    depts, err, meta = fetch_department_tree("tok", root_dept_ids=[100])
    assert err is None
    ids = {d["deptId"] for d in depts}
    assert ids == {100, 101}
    assert meta.get("partialScope") is True
    assert meta.get("firstApiError")


@patch("app.dingtalk_client._topapi_post")
def test_probe_dept_1_when_scopes_empty(mock_post):
    def side_effect(token, path, body):
        if path == "auth/scopes":
            return {"auth_org_scopes": {"authed_dept": [], "authed_user": []}}, None
        if path == "v2/department/get" and body.get("dept_id") == 1:
            return {"name": "根", "parent_id": 0}, None
        return {"dept_id_list": []}, None

    mock_post.side_effect = side_effect
    roots, err, meta = resolve_authorized_root_dept_ids("tok")
    assert err is None
    assert roots == [1]
    assert meta.get("rootSource") == "probe_dept_1"


@patch("app.dingtalk_client._topapi_post")
def test_fetch_department_tree_parses_listsub_object_array(mock_post):
    """listsub 的 result 为部门对象数组时须能 BFS（非仅 dept_id_list）。"""

    def side_effect(token, path, body):
        if path == "v2/department/get":
            dept_id = int(body["dept_id"])
            names = {1: "根", 10: "子"}
            return {"name": names[dept_id], "parent_id": 0 if dept_id == 1 else 1}, None
        if path == "v2/department/listsubid":
            return {"dept_id_list": []}, None
        if path == "v2/department/listsub":
            dept_id = int(body["dept_id"])
            if dept_id == 1:
                return {"value": [{"dept_id": 10, "name": "子"}]}, None
            return {"dept_id_list": []}, None
        return {}, None

    mock_post.side_effect = side_effect
    depts, err, meta = fetch_department_tree("tok", root_dept_ids=[1])
    assert err is None
    assert {d["deptId"] for d in depts} == {1, 10}
    assert meta.get("listsubCalls") == 2
    assert meta.get("subDepartmentIdsDiscovered") == 1
    assert meta.get("rootSubDeptIdCount") == 1
