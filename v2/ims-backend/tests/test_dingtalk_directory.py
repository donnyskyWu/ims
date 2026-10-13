"""钉钉通讯录适配器。全部走假 HTTP，不访问公网。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import load_settings, v1_dotenv_file
from app.core.errors import BizError
from app.integrations.dingtalk.client import ding_state, list_directory
from app.integrations.dingtalk.directory import OAUTH_ACCESS_TOKEN_URL, pull_org_directory
from app.services.org_sync import _remote_position


def test_v1_env_names_switch_dev_to_real_without_writing_yaml():
    """IMS_DINGTALK_CLIENT_ID 等覆盖 yaml，并在 dev 下把 mode 设为 real。"""
    settings = load_settings(
        "dev",
        extra_env={
            "IMS_DINGTALK_CLIENT_ID": "cid-unit",
            "IMS_DINGTALK_CLIENT_SECRET": "sec-unit",
            "IMS_DINGTALK_AGENT_ID": "4242",
            "IMS_DINGTALK_CORP_ID": "corp-unit",
            "IMS_DINGTALK_APP_ID": "app-unit",
        },
    )
    assert settings.dingtalk["mode"] == "real"
    assert settings.dingtalk["app_key"] == "cid-unit"
    assert settings.dingtalk["app_secret"] == "sec-unit"
    assert settings.dingtalk["agent_id"] == "4242"
    assert settings.dingtalk["corp_id"] == "corp-unit"
    assert settings.dingtalk["app_id"] == "app-unit"
    yaml_text = Path("config/dev.yaml").read_text(encoding="utf-8")
    assert "sec-unit" not in yaml_text
    assert "cid-unit" not in yaml_text


def test_test_env_stays_mock_when_v1_credentials_exist():
    settings = load_settings(
        "test",
        extra_env={
            "IMS_DINGTALK_CLIENT_ID": "cid-unit",
            "IMS_DINGTALK_CLIENT_SECRET": "sec-unit",
        },
    )
    assert settings.dingtalk["mode"] == "mock"
    assert settings.dingtalk["app_key"] == "test-app-key"


def test_dotenv_path_points_at_v1_env_file():
    path = v1_dotenv_file()
    assert path.name == ".env"
    assert path.parent.name == "ims-backend"
    assert path.parent.parent.name != "v2"


def test_remote_position_reads_dingtalk_title():
    assert _remote_position({"title": "主播"}) == "主播"
    assert _remote_position({"positionCode": "POS", "title": "主播"}) == "POS"
    assert _remote_position({}) == ""


def _fake_directory(url, *, params=None, json=None, timeout=None):
    """内存里的钉钉：一个根部门、一个子部门和一名带职务的员工。"""
    del params, timeout
    if url == OAUTH_ACCESS_TOKEN_URL:
        assert json["appKey"] == "cid-unit"
        assert json["appSecret"] == "sec-unit"
        return {"accessToken": "token-unit"}
    path = url.split("/topapi/")[-1]
    if path == "auth/scopes":
        return {"errcode": 0, "result": {"auth_org_scopes": {"authed_dept": [1], "authed_user": []}}}
    if path == "v2/department/get":
        dept_id = json["dept_id"]
        if dept_id == 1:
            return {"errcode": 0, "result": {"name": "总公司", "parent_id": 0}}
        if dept_id == 10:
            return {"errcode": 0, "result": {"name": "研发部", "parent_id": 1}}
        raise AssertionError(dept_id)
    if path == "v2/department/listsubid":
        children = [10] if json["dept_id"] == 1 else []
        return {"errcode": 0, "result": {"dept_id_list": children}}
    if path == "v2/department/listsub":
        return {"errcode": 0, "result": []}
    if path == "v2/user/list":
        rows = [{"userid": "u1"}] if json["dept_id"] == 10 else []
        return {"errcode": 0, "result": {"list": rows, "has_more": False}}
    if path == "v2/user/get":
        return {
            "errcode": 0,
            "result": {
                "userid": "u1",
                "name": "张三",
                "mobile": "13800000000",
                "dept_id_list": [10],
                "title": "主播",
                "job_number": "E100",
            },
        }
    raise AssertionError(path)


def test_pull_maps_departments_users_and_title_without_network():
    payload, err = pull_org_directory(app_key="cid-unit", app_secret="sec-unit", post=_fake_directory)
    assert err is None
    assert payload is not None
    assert [row["dingtalkDeptId"] for row in payload["departments"]] == [1, 10]
    assert payload["departments"][1]["parentDingtalkDeptId"] == 1
    user = payload["users"][0]
    assert user["dingtalkUserId"] == "u1"
    assert user["title"] == "主播"
    assert user["positionCode"] == "主播"
    assert user["deptIds"] == [10]
    assert user["jobNumber"] == "E100"
    assert "token-unit" not in str(payload["meta"])


def _scope_denied(url, *, params=None, json=None, timeout=None):
    del params, json, timeout
    if url == OAUTH_ACCESS_TOKEN_URL:
        return {"accessToken": "token-unit"}
    path = url.split("/topapi/")[-1]
    if path == "auth/scopes":
        return {"errcode": 0, "result": {"auth_org_scopes": {"authed_dept": [1], "authed_user": []}}}
    if path == "v2/department/get":
        return {"errcode": 50004, "errmsg": "部门不在授权范围"}
    return {"errcode": 50004, "errmsg": "部门不在授权范围"}


def test_scope_error_does_not_yield_an_empty_directory(monkeypatch):
    """50004 必须失败返回，对账拿不到空部门列表。"""
    payload, err = pull_org_directory(app_key="cid-unit", app_secret="sec-unit", post=_scope_denied)
    assert payload is not None
    assert payload["departments"] == []
    assert err is not None and "50004" in err

    from app.core.config import get_settings

    settings = get_settings()
    previous = dict(settings.dingtalk)
    settings.dingtalk = {**previous, "mode": "real", "app_key": "cid-unit", "app_secret": "sec-unit"}
    monkeypatch.setattr(
        "app.integrations.dingtalk.client.pull_org_directory",
        lambda: pull_org_directory(app_key="cid-unit", app_secret="sec-unit", post=_scope_denied),
    )
    try:
        with pytest.raises(BizError) as exc:
            list_directory()
        assert exc.value.code == 1006
        assert "50004" in exc.value.msg
    finally:
        settings.dingtalk = previous


def test_mock_list_directory_ignores_real_pull(monkeypatch):
    called = {"n": 0}

    def _boom():
        called["n"] += 1
        raise AssertionError("mock 模式不应访问钉钉")

    monkeypatch.setattr("app.integrations.dingtalk.client.pull_org_directory", _boom)
    ding_state.departments = [{"dingtalkDeptId": 100, "name": "市场部", "parentDingtalkDeptId": None}]
    ding_state.users = [{"dingtalkUserId": "dt_a", "title": "主播"}]
    payload = list_directory()
    assert called["n"] == 0
    assert payload["departments"][0]["dingtalkDeptId"] == 100
    assert payload["users"][0]["title"] == "主播"
