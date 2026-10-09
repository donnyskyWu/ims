"""#230 组织基座表单边角：供给规则字数、待配置角色、岗位长度。"""

import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login(username="admin", password="Admin@123") -> dict:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return {"Authorization": f"Bearer {res.json()['data']['accessToken']}"}


def admin_role_id(headers: dict) -> int:
    rows = client.get("/admin-api/ims/system/role/list", headers=headers).json()["data"]
    for row in rows:
        if row["status"] == "ENABLED":
            return row["id"]
    raise AssertionError("no enabled role")


def test_position_rule_rejects_length_blank_and_pending_role():
    headers = login()
    role_id = admin_role_id(headers)
    long_name = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "规" * 65, "dingtalkPosition": "场控甲", "grantRoleIds": [role_id]},
    )
    assert long_name.json()["code"] == 1001
    assert long_name.json()["msg"] == "规则名不能超过 64 字"

    blank = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "   ", "dingtalkPosition": "场控甲", "grantRoleIds": [role_id]},
    )
    assert blank.json()["msg"] == "规则名必填"

    long_pos = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "场控供给", "dingtalkPosition": "岗" * 65, "grantRoleIds": [role_id]},
    )
    assert long_pos.json()["msg"] == "钉钉岗位不能超过 64 字"

    long_desc = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={
            "ruleName": "场控供给",
            "dingtalkPosition": "场控甲",
            "description": "说" * 201,
            "grantRoleIds": [role_id],
        },
    )
    assert long_desc.json()["msg"] == "说明不能超过 200 字"

    missing_role = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "场控供给", "dingtalkPosition": "场控甲", "grantRoleIds": []},
    )
    assert missing_role.json()["msg"] == "请选择授予角色"

    pending = client.post(
        "/admin-api/ims/system/role/from-position",
        headers=headers,
        json={"dingtalkPosition": "待配岗"},
    )
    assert pending.json()["data"]["status"] == "PENDING_CONFIG"
    rejected = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={
            "ruleName": "待配供给",
            "dingtalkPosition": "待配岗",
            "description": "说" * 200,
            "grantRoleIds": [pending.json()["data"]["roleId"]],
        },
    )
    assert rejected.json()["code"] == 1002
    assert rejected.json()["msg"] == "角色「待配岗」尚未配置权限，用户将无任何权限"

    created = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={
            "ruleName": "规" * 64,
            "dingtalkPosition": "岗" * 64,
            "description": "说" * 200,
            "grantRoleIds": [role_id],
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["description"] == "说" * 200


def test_role_position_length_and_idempotent_copy():
    headers = login()
    too_long = client.post(
        "/admin-api/ims/system/role/from-position",
        headers=headers,
        json={"dingtalkPosition": "岗" * 65},
    )
    assert too_long.json()["code"] == 1001
    assert too_long.json()["msg"] == "钉钉岗位不能超过 64 字"

    blank = client.post(
        "/admin-api/ims/system/role/from-position",
        headers=headers,
        json={"dingtalkPosition": "  "},
    )
    assert blank.json()["msg"] == "钉钉岗位必填"

    created = client.post(
        "/admin-api/ims/system/role/from-position",
        headers=headers,
        json={"dingtalkPosition": "边角岗"},
    )
    assert created.json()["data"]["created"] is True
    role_id = created.json()["data"]["roleId"]
    again = client.post(
        "/admin-api/ims/system/role/from-position",
        headers=headers,
        json={"dingtalkPosition": "边角岗"},
    )
    assert again.json()["data"]["created"] is False
    assert again.json()["data"]["roleId"] == role_id

    bound = client.put(
        f"/admin-api/ims/system/role/{role_id}/dingtalk-position",
        headers=headers,
        json={"dingtalkPosition": "岗" * 65},
    )
    assert bound.json()["code"] == 1001
    assert bound.json()["msg"] == "钉钉岗位不能超过 64 字"
