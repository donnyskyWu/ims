import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import DictData, DictType
from app.ops_db import ops_session
from app.ops_models import Company

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_sim_form_rejects_phone_rent_and_unknown_operator():
    auth = headers()
    admin_id = client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"]
    base = {
        "isPrimary": "YES",
        "operator": "MOBILE",
        "assignedUserId": int(admin_id),
        "status": "IN_USE",
    }

    missing = client.post("/admin-api/ims/corp/resource/sim-card", headers=auth, json=base)
    assert missing.json()["code"] == 1001
    assert "手机号" in missing.json()["msg"]

    short = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={**base, "phoneNumber": "12345"},
    )
    assert short.json()["code"] == 1001
    assert short.json()["msg"] == "手机号须为 11 位"

    bad_rent = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={**base, "phoneNumber": "13900002222", "monthlyRent": "abc"},
    )
    assert bad_rent.json()["code"] == 1001
    assert bad_rent.json()["msg"] == "月租须为数字"

    negative = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={**base, "phoneNumber": "13900002222", "monthlyRent": -3},
    )
    assert negative.json()["code"] == 1001
    assert negative.json()["msg"] == "月租不能为负"

    unknown = client.post(
        "/admin-api/ims/corp/resource/sim-card",
        headers=auth,
        json={**base, "phoneNumber": "13900002222", "operator": "NO_SUCH"},
    )
    assert unknown.json()["code"] == 1503
    assert unknown.json()["msg"] == "字典枚举非法"


def test_company_industry_raw_value_ignores_disabled_dict():
    auth = headers()
    db = SessionLocal()
    ops = ops_session()
    try:
        found = db.scalar(select(DictType).where(DictType.dict_type == "dict_industry", DictType.deleted == 0))
        if found is None:
            db.add(DictType(dict_type="dict_industry", type_name="行业", status="ENABLED", tenant_id=0, deleted=0))
            db.flush()
        values = set(
            db.scalars(
                select(DictData.dict_value).where(DictData.dict_type == "dict_industry", DictData.deleted == 0)
            ).all()
        )
        if "SPORT" not in values:
            db.add(
                DictData(
                    dict_type="dict_industry",
                    dict_label="体育",
                    dict_value="SPORT",
                    sort=1,
                    status="ENABLED",
                    tenant_id=0,
                    deleted=0,
                )
            )
        if "LEGACY" not in values:
            db.add(
                DictData(
                    dict_type="dict_industry",
                    dict_label="旧行业",
                    dict_value="LEGACY",
                    sort=9,
                    status="DISABLED",
                    tenant_id=0,
                    deleted=0,
                )
            )
        db.commit()
        row = Company(
            company_name="行业边角公司",
            industry="FINANCE",
            credit_code="91330100MA2290001X",
            status="ENABLED",
            tenant_id=0,
            deleted=0,
        )
        blank_row = Company(
            company_name="未填行业公司",
            industry="",
            credit_code="91330100MA2290002X",
            status="ENABLED",
            tenant_id=0,
            deleted=0,
        )
        ops.add(row)
        ops.add(blank_row)
        ops.commit()
        company_id = row.id
        blank_id = blank_row.id

        detail = client.get(f"/admin-api/ims/corp/resource/company/{company_id}", headers=auth)
        assert detail.json()["code"] == 0
        assert detail.json()["data"]["industry"] == "FINANCE"

        listed = client.get(
            "/admin-api/ims/system/dict-data/list",
            headers=auth,
            params={"dictType": "dict_industry"},
        )
        assert listed.json()["code"] == 0
        enabled = {item["dictValue"] for item in listed.json()["data"] if item["status"] == "ENABLED"}
        disabled = {item["dictValue"] for item in listed.json()["data"] if item["status"] == "DISABLED"}
        assert "SPORT" in enabled
        assert "LEGACY" in disabled
        assert "LEGACY" not in enabled
        assert "FINANCE" not in enabled

        blank = client.get(f"/admin-api/ims/corp/resource/company/{blank_id}", headers=auth)
        assert blank.json()["code"] == 0
        assert blank.json()["data"]["industry"] == ""
    finally:
        ops.close()
        db.close()


def test_realname_detail_relation_lists_stay_empty():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/corp/resource/realname/page",
        headers=auth,
        params={"realName": "E2E财务实名人"},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    person_id = listed.json()["data"]["list"][0]["id"]
    detail = client.get(f"/admin-api/ims/corp/resource/realname/{person_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["intermediaries"] == []
    assert detail.json()["data"]["linkedAccounts"] == []
