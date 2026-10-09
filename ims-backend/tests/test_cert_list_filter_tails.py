"""#221 · 证件列表按类型和有效期筛选，倒置或单边日期拒绝。"""

import os
import time
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload(auth: dict, holder: str, cert_type: str, days: int, number: str):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": cert_type,
            "certNoPlain": number,
            "fileKey": "local/cert/upload",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def listed(auth: dict, params: list[tuple[str, str]]):
    return client.get("/admin-api/ims/corp/resource/certificate/page", headers=auth, params=params)


def test_certificate_page_filters_type_and_expire_range():
    auth = headers()
    stamp = str(int(time.time()))
    holder = f"E2E-Cert-221-{stamp}"
    near = upload(auth, holder, "IDCARD", 20, f"221{stamp}01".ljust(12, "0"))
    far = upload(auth, holder, "PASSPORT", 400, f"221{stamp}02".ljust(12, "0"))
    assert near.json()["code"] == 0, near.json()
    assert far.json()["code"] == 0, far.json()

    today = date.today()
    near_day = (today + timedelta(days=20)).isoformat()
    far_day = (today + timedelta(days=400)).isoformat()
    passport = listed(
        auth,
        [("holderName", holder), ("certType", "PASSPORT"), ("pageNo", "1"), ("pageSize", "20")],
    ).json()
    assert passport["code"] == 0
    assert [row["certType"] for row in passport["data"]["list"]] == ["PASSPORT"]
    assert passport["data"]["list"][0]["expireDate"] == far_day

    window = listed(
        auth,
        [
            ("holderName", holder),
            ("expireDateRange", (today + timedelta(days=300)).isoformat()),
            ("expireDateRange", (today + timedelta(days=500)).isoformat()),
            ("pageNo", "1"),
            ("pageSize", "20"),
        ],
    ).json()
    assert window["code"] == 0
    assert [row["expireDate"] for row in window["data"]["list"]] == [far_day]

    near_only = listed(
        auth,
        [
            ("holderName", holder),
            ("certType", "IDCARD"),
            ("expireDateRange", (today + timedelta(days=1)).isoformat()),
            ("expireDateRange", (today + timedelta(days=30)).isoformat()),
            ("pageNo", "1"),
            ("pageSize", "20"),
        ],
    ).json()
    assert near_only["code"] == 0
    assert [row["expireDate"] for row in near_only["data"]["list"]] == [near_day]

    other = listed(auth, [("holderName", holder), ("certType", "OTHER")]).json()
    assert other["code"] == 0
    assert other["data"]["list"] == []

    bad_type = listed(auth, [("certType", "NOPE")]).json()
    assert bad_type["code"] == 1001
    assert bad_type["msg"] == "证件类型无效"

    inverted = listed(
        auth,
        [
            ("expireDateRange", "2026-12-01"),
            ("expireDateRange", "2026-10-01"),
        ],
    ).json()
    assert inverted["code"] == 1001
    assert inverted["msg"] == "开始日期不能晚于结束日期"

    one_side = listed(auth, [("expireDateRange", "2026-10-01")]).json()
    assert one_side["code"] == 1001
    assert one_side["msg"] == "请同时填写开始和结束日期"

    bad_day = listed(
        auth,
        [("expireDateRange", "2026/10/01"), ("expireDateRange", "2026-10-02")],
    ).json()
    assert bad_day["code"] == 1001
    assert bad_day["msg"] == "有效期范围不合法"
