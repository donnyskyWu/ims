"""A 组工程用例。"""
import uuid

from tests.conftest import auth, login


def test_ut_a01_07(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "UP"
    assert body["data"]["db"] == "UP"
    assert body["data"]["redis"] == "UP"
    assert "mysql" not in response.text
    assert "password" not in response.text.lower()


def test_ut_a02_01(client):
    headers = auth(client, "u_admin")
    response = client.get("/admin-api/ims/demo/order/page", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "成功"
    assert "list" in body["data"]


def test_ut_d01_01(client):
    """UT-D01-01 正确密码登录：令牌、过期秒数、成功日志、失败计数清零。"""
    from sqlalchemy import func, select

    from app.core.redis_client import get_redis
    from app.db.session import session_scope
    from app.domains.system.model import LoginLog

    response = login(client, "u_admin")
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["expiresIn"] == 7200
    assert body["data"]["accessToken"]
    assert body["data"]["refreshToken"]
    assert get_redis().get("ims:login:fail:u_admin") is None
    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(LoginLog).where(LoginLog.username == "u_admin", LoginLog.result == "SUCCESS"))
    assert count == 1


def test_ut_a01_10(client):
    headers = auth(client, "u_admin")
    headers["X-Trace-Id"] = "t-1"
    response = client.get("/admin-api/ims/demo/order/page", headers=headers)
    assert response.headers["x-trace-id"] == "t-1"


def test_ut_a01_11(client):
    headers = auth(client, "u_admin")
    response = client.get("/admin-api/ims/demo/order/page", headers=headers)
    uuid.UUID(response.headers["x-trace-id"])


def test_ut_a04_09(client):
    """默认把主键和外键 id 按字符串输出，无需再打开开关。"""
    headers = auth(client, "u_admin")
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "字符串主键", "ownerUserId": "1001", "amount": "1.00"},
    )
    assert created.json()["code"] == 0, created.text
    ident = created.json()["data"]["id"]
    assert isinstance(ident, str)
    detail = client.get(f"/admin-api/ims/demo/order/get?id={ident}", headers=headers)
    body = detail.json()["data"]
    assert isinstance(body["id"], str)
    assert isinstance(body["ownerUserId"], str)


def test_ut_a04_10(client):
    """雪花 ID 2059567794397171712 写入、读取、再作为入参，值不变。"""
    headers = auth(client, "u_admin")
    snow = "2059567794397171712"
    from app.core.context import system_context, use_context
    from app.db.session import session_scope
    from app.domains.system.model import User
    from app.core.security import hash_password

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(User(id=int(snow), username="snow", nickname="雪花", password_hash=hash_password("Abc12345"), status="ACTIVE", tenant_id=1))
    created = client.post(
        "/admin-api/ims/demo/order/create",
        headers=headers,
        json={"name": "雪花", "ownerUserId": snow, "amount": "1.00"},
    )
    assert created.json()["code"] == 0, created.text
    assert created.json()["data"]["ownerUserId"] == snow
    ident = created.json()["data"]["id"]
    updated = client.put(
        "/admin-api/ims/demo/order/update",
        headers=headers,
        json={"id": ident, "ownerUserId": snow, "name": "雪花"},
    )
    assert updated.json()["code"] == 0, updated.text
    assert updated.json()["data"]["ownerUserId"] == snow
    detail = client.get(f"/admin-api/ims/demo/order/get?id={ident}", headers=headers)
    assert detail.json()["data"]["ownerUserId"] == snow
