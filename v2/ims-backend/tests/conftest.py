import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.clock import unfreeze
from app.core.config import load_settings, set_settings
from app.core.events import events
from app.core.fault import faults
from app.core.redis_client import configure_redis, get_redis
from app.db.base import Base
from app.db.session import init_engine, session_scope
from app.domains import all_models
from app.main import create_app
from tests.stddata import PASSWORD, build

all_models()


@pytest.fixture(scope="session")
def app():
    settings = load_settings("test")
    set_settings(settings)
    init_engine(settings)
    configure_redis(settings)
    from tools.football_stub.seed import seed

    seed()
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset(app):
    unfreeze()
    events.clear()
    faults.clear()
    from app.integrations.dingtalk.client import ding_state

    ding_state.reset()
    from app.integrations.train_ai.client import reset_config
    from app.integrations.runtime import reset_breakers

    reset_config()
    reset_breakers()
    for item in __import__("app.integrations.runtime", fromlist=["ADAPTERS"]).ADAPTERS.values():
        item.reset()
    get_redis().flushdb()
    with session_scope(commit=True) as session:
        session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        build()
    yield
    unfreeze()


def login(client, username, password=PASSWORD):
    response = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    return response


def auth(client, username):
    body = login(client, username).json()
    token = body["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
