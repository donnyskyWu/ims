import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.bi_br212_seed import BR212_PREFIX
from app.main import app

client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0, res.json()
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def br212_report_names(token: str) -> set[str]:
    res = client.get(
        "/admin-api/ims/bi/report/list",
        headers=auth(token),
        params={"keyword": BR212_PREFIX, "pageNo": 1, "pageSize": 50},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0, body
    return {row["reportName"] for row in body["data"]["list"]}


def test_bi_br212_admin_sees_all_seed_reports():
    token = login()
    names = br212_report_names(token)
    assert f"{BR212_PREFIX}dept11-A" in names
    assert f"{BR212_PREFIX}dept11-B" in names
    assert f"{BR212_PREFIX}dept12-C" in names


def test_bi_br212_dept_viewer_sees_subset():
    token = login("bi_r4_viewer", "Admin@123")
    names = br212_report_names(token)
    assert f"{BR212_PREFIX}dept11-A" in names
    assert f"{BR212_PREFIX}dept11-B" in names
    assert f"{BR212_PREFIX}dept12-C" not in names


def test_bi_br212_share_link_list_respects_dept():
    admin = login()
    viewer = login("bi_r4_viewer", "Admin@123")
    admin_shares = client.get(
        "/admin-api/ims/bi/subscribe/share-link/list",
        headers=auth(admin),
        params={"pageNo": 1, "pageSize": 50},
    ).json()["data"]["list"]
    viewer_shares = client.get(
        "/admin-api/ims/bi/subscribe/share-link/list",
        headers=auth(viewer),
        params={"pageNo": 1, "pageSize": 50},
    ).json()["data"]["list"]
    admin_br = [r for r in admin_shares if BR212_PREFIX in (r.get("targetName") or "")]
    viewer_br = [r for r in viewer_shares if BR212_PREFIX in (r.get("targetName") or "")]
    assert len(admin_br) >= 2
    assert len(viewer_br) == 1
    assert viewer_br[0]["targetName"] == f"{BR212_PREFIX}dept11-A"
