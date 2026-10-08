"""系统参数运行时解析（DB > env > 默认）。"""

from __future__ import annotations

import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import SysParam
from app.settings_runtime import get_param, invalidate_param_cache

client = TestClient(app)


def _login_headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_db_overrides_env_for_dingtalk_client_id():
    client.get("/admin-api/ims/system/param", headers=_login_headers())
    os.environ["IMS_DINGTALK_CLIENT_ID"] = "env-client"
    db = SessionLocal()
    try:
        row = db.scalar(select(SysParam).where(SysParam.param_key == "dingtalk.clientId"))
        assert row is not None
        row.param_value = "db-client"
        db.commit()
        invalidate_param_cache()
        assert get_param("dingtalk.clientId", db=db) == "db-client"
    finally:
        db.close()
        os.environ.pop("IMS_DINGTALK_CLIENT_ID", None)
        invalidate_param_cache()


def test_nonempty_db_beats_env_for_football_url():
    client.get("/admin-api/ims/system/param", headers=_login_headers())
    os.environ["IMS_FOOTBALL_WEBAPI_BASE_URL"] = "https://env.example.com"
    db = SessionLocal()
    try:
        row = db.scalar(select(SysParam).where(SysParam.param_key == "football.webapiBaseUrl"))
        assert row is not None
        row.param_value = "https://db.example.com"
        db.commit()
        invalidate_param_cache()
        assert get_param("football.webapiBaseUrl", db=db) == "https://db.example.com"
    finally:
        db.close()
        os.environ.pop("IMS_FOOTBALL_WEBAPI_BASE_URL", None)
        invalidate_param_cache()


def test_football_base_url_falls_back_to_env_when_db_empty():
    from app.football_client import base_url

    client.get("/admin-api/ims/system/param", headers=_login_headers())
    os.environ["IMS_FOOTBALL_WEBAPI_BASE_URL"] = "https://saas.shenyu.com"
    db = SessionLocal()
    try:
        row = db.scalar(select(SysParam).where(SysParam.param_key == "football.webapiBaseUrl"))
        assert row is not None
        row.param_value = ""
        db.commit()
        invalidate_param_cache()
        assert base_url() == "https://saas.shenyu.com"
    finally:
        db.close()
        os.environ.pop("IMS_FOOTBALL_WEBAPI_BASE_URL", None)
        invalidate_param_cache()
