import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_master_overview_blocks():
    auth = headers()
    res = client.get("/admin-api/ims/master/overview", headers=auth)
    assert res.json()["code"] == 0
    blocks = res.json()["data"]["blocks"]
    assert len(blocks) >= 6
    assert any(b["key"] == "company" for b in blocks)


def test_company_industry_dict_filter_edge():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/system/dict-data/list",
        headers=auth,
        params={"dictType": "dict_industry"},
    )
    assert listed.json()["code"] == 0
    values = {row["dictValue"] for row in listed.json()["data"] if row["status"] == "ENABLED"}
    assert {"SPORT", "ESPORTS", "MEDIA", "OTHER"} <= values

    from app.ops_db import ops_session
    from app.ops_models import Company

    ops = ops_session()
    row = Company(
        company_name="行业筛选公司",
        industry="SPORT",
        credit_code="91330100MAIND0001X",
        status="ENABLED",
        tenant_id=0,
        deleted=0,
    )
    ops.add(row)
    ops.commit()
    company_id = row.id
    ops.close()
    try:
        hit = client.get(
            "/admin-api/ims/corp/resource/company/page",
            headers=auth,
            params={"industry": "SPORT", "companyName": "行业筛选公司"},
        )
        assert hit.json()["code"] == 0
        names = [item["companyName"] for item in hit.json()["data"]["list"]]
        assert names == ["行业筛选公司"]
        assert hit.json()["data"]["list"][0]["industry"] == "SPORT"

        other = client.get(
            "/admin-api/ims/corp/resource/company/page",
            headers=auth,
            params={"industry": "ESPORTS", "companyName": "行业筛选公司"},
        )
        assert other.json()["code"] == 0
        assert other.json()["data"]["total"] == 0

        unknown = client.get(
            "/admin-api/ims/corp/resource/company/page",
            headers=auth,
            params={"industry": "___no_such_industry___"},
        )
        assert unknown.json()["code"] == 0
        assert unknown.json()["data"]["total"] == 0
    finally:
        ops = ops_session()
        found = ops.get(Company, company_id)
        if found is not None:
            ops.delete(found)
            ops.commit()
        ops.close()
