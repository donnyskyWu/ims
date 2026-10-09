import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import AirMcpLog, User

client = TestClient(app)

TOOLS = ["skills.list", "skills.get", "experts.list", "experts.assemble"]


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def stat(auth: dict, **params):
    return client.get("/admin-api/ims/air/usage/stat", headers=auth, params=params)


def tool_of(rows: list[dict], name: str) -> dict:
    return next(item for item in rows if item["tool"] == name)


def test_usage_stat_aggregates_local_mcp_logs():
    auth = headers()
    moment = (utcnow() - timedelta(days=40)).replace(hour=11, minute=0, second=0, microsecond=0)
    day = moment.strftime("%Y-%m-%d")
    marker = f"usage-182-{moment.strftime('%H%M%S')}"
    before = stat(auth, by="TOOL", dateRange=f"{day},{day}")
    assert before.json()["code"] == 0, before.text
    before_tools = before.json()["data"]
    assert [item["tool"] for item in before_tools] == TOOLS

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        assert admin is not None
        admin_id = int(admin.id)
        tenant_id = admin.tenant_id or 0
        db.add(
            AirMcpLog(
                key_id=0,
                user_id=admin_id,
                tool="experts.assemble",
                param_digest=marker,
                result_code="0",
                cost_ms=100,
                token_cnt=0,
                filter_hit=1,
                tenant_id=tenant_id,
                created_at=moment,
            )
        )
        db.add(
            AirMcpLog(
                key_id=0,
                user_id=admin_id,
                tool="skills.get",
                param_digest=marker + "-fail",
                result_code="403",
                cost_ms=50,
                token_cnt=4,
                filter_hit=0,
                tenant_id=tenant_id,
                created_at=moment,
            )
        )
        db.commit()
    finally:
        db.close()

    tools = stat(auth, by="TOOL", dateRange=f"{day},{day}").json()["data"]
    assemble = tool_of(tools, "experts.assemble")
    skill_get = tool_of(tools, "skills.get")
    assert assemble["callCnt"] == tool_of(before_tools, "experts.assemble")["callCnt"] + 1
    assert assemble["failCnt"] == tool_of(before_tools, "experts.assemble")["failCnt"]
    assert skill_get["callCnt"] == tool_of(before_tools, "skills.get")["callCnt"] + 1
    assert skill_get["failCnt"] == tool_of(before_tools, "skills.get")["failCnt"] + 1
    if tool_of(before_tools, "experts.assemble")["callCnt"] == 0:
        assert assemble["avgCostMs"] == 100
    if tool_of(before_tools, "skills.get")["callCnt"] == 0:
        assert skill_get["avgCostMs"] == 50

    people = stat(auth, by="PERSON", dateRange=f"{day},{day}").json()["data"]
    person = next(item for item in people if item["userId"] == admin_id)
    assert person["callCnt"] >= 2
    assert person["tokenCnt"] >= 4
    assert person["deptName"]
    assert person["userName"]

    days = stat(auth, by="DAY", dateRange=f"{day},{day}").json()["data"]
    assert len(days) == 1
    assert days[0]["statDate"] == day
    assert days[0]["callCnt"] >= 2
    assert days[0]["tokenCnt"] >= 4

    listed = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"tool": "experts.assemble", "dateRange": f"{day},{day}", "pageNo": 1, "pageSize": 100},
    )
    assert listed.json()["code"] == 0, listed.text
    matched = [item for item in listed.json()["data"]["list"] if item["paramDigest"] == marker]
    assert matched
    assert matched[0]["resultCode"] == "SUCCESS"
    assert matched[0]["tokenCnt"] == 0


def test_usage_stat_default_week_and_retention():
    auth = headers()
    week = stat(auth, by="DAY")
    assert week.json()["code"] == 0, week.text
    assert len(week.json()["data"]) == 7
    assert all("statDate" in item and "callCnt" in item and "tokenCnt" in item for item in week.json()["data"])

    bad_by = stat(auth, by="WEEK")
    assert bad_by.json()["code"] == 1001
    assert "TOOL" in bad_by.json()["msg"]

    bad_range = stat(auth, by="DAY", dateRange="2026-01-01")
    assert bad_range.json()["code"] == 1001
    assert "开始日,结束日" in bad_range.json()["msg"]

    today = utcnow().date()
    wide_start = today - timedelta(days=200)
    wide = stat(auth, by="DAY", dateRange=f"{wide_start.isoformat()},{today.isoformat()}")
    assert wide.json()["code"] == 1001
    assert "不能超过 180 天" in wide.json()["msg"]

    old = today - timedelta(days=200)
    purged = stat(auth, by="DAY", dateRange=f"{old.isoformat()},{old.isoformat()}")
    assert purged.json()["code"] == 1001
    assert "已清理" in purged.json()["msg"]
