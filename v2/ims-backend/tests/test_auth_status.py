"""冻结、离职账号不能登录，也不能只进工作台。"""
from app.db.session import session_scope
from app.domains.system.model import User
from tests.conftest import login
from tests.stddata import U_FROZEN, U_RESIGNED


def test_frozen_and_resigned_login_rejected(client):
    for name in ("u_frozen", "u_resigned"):
        wrong = login(client, name, "badpass1").json()
        assert wrong["code"] == 1214
        blocked = login(client, name).json()
        assert blocked["code"] == 1216
        assert not (blocked.get("data") or {}).get("accessToken")


def test_frozen_cannot_refresh_into_workbench(client):
    with session_scope(commit=True) as session:
        user = session.get(User, U_FROZEN)
        user.status = "ACTIVE"
    tokens = login(client, "u_frozen").json()
    assert tokens["code"] == 0
    access = tokens["data"]["accessToken"]
    refresh = tokens["data"]["refreshToken"]
    with session_scope(commit=True) as session:
        user = session.get(User, U_FROZEN)
        user.status = "FROZEN"
    me = client.get("/admin-api/ims/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.json()["code"] == 1002
    again = client.post("/admin-api/ims/auth/refresh-token", json={"refreshToken": refresh})
    body = again.json()
    assert body["code"] == 1216
    assert not (body.get("data") or {}).get("accessToken")
    resigned = login(client, "u_resigned").json()
    assert resigned["code"] == 1216
    assert U_RESIGNED
