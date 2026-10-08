import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


MYSQL_USER = _env("IMS_MYSQL_USER", "root")
MYSQL_PASSWORD = _env("IMS_MYSQL_PASSWORD", "root")
MYSQL_HOST = _env("IMS_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = _env("IMS_MYSQL_PORT", "3306")
IMS_DB = _env("IMS_DB", "ims")
OPS_DB = _env("IMS_OPS_DB", "opsbiz")
JWT_SECRET = _env("IMS_JWT_SECRET", "ims-dev-secret-change-me")
ACCESS_MINUTES = 120
REFRESH_DAYS = 7

# 钉钉 / Football：运行时见 app.settings_runtime.get_param（DB 系统参数 > IMS_* env > 默认）
DINGTALK_TOKEN = _env("IMS_DINGTALK_TOKEN", "ims-dev-dingtalk-token")
DINGTALK_AES_KEY = _env(
    "IMS_DINGTALK_AES_KEY", "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"
)
DINGTALK_CORP_ID = _env("IMS_DINGTALK_CORP_ID", "ims-corp")
DINGTALK_CLIENT_ID = _env("IMS_DINGTALK_CLIENT_ID", "")
DINGTALK_CLIENT_SECRET = _env("IMS_DINGTALK_CLIENT_SECRET", "")
DINGTALK_AGENT_ID = _env("IMS_DINGTALK_AGENT_ID", "")
DINGTALK_APP_ID = _env("IMS_DINGTALK_APP_ID", "")
FOOTBALL_WEBAPI_BASE_URL = _env("IMS_FOOTBALL_WEBAPI_BASE_URL", "")
FOOTBALL_TIMEOUT_SEC = float(_env("IMS_FOOTBALL_TIMEOUT_SEC", "3"))


def server_url(database: str | None = None) -> str:
    auth = f"{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
    base = f"mysql+pymysql://{auth}@{MYSQL_HOST}:{MYSQL_PORT}"
    if database:
        return f"{base}/{database}?charset=utf8mb4"
    return f"{base}/?charset=utf8mb4"


def ensure_databases() -> None:
    engine = create_engine(server_url(), pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{IMS_DB}` CHARACTER SET utf8mb4"))
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{OPS_DB}` CHARACTER SET utf8mb4"))
    engine.dispose()


class Base(DeclarativeBase):
    pass


engine = create_engine(server_url(IMS_DB), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def mask_mobile(mobile: str | None) -> str:
    if not mobile or len(mobile) < 7:
        return mobile or ""
    return mobile[:3] + "****" + mobile[-4:]


def mask_name(name: str | None) -> str:
    text = (name or "").strip()
    if not text:
        return ""
    if len(text) == 1:
        return "*"
    if len(text) == 2:
        return text[0] + "*"
    return text[0] + ("*" * (len(text) - 2)) + text[-1]


def mask_id_card(value: str | None) -> str:
    text = value or ""
    if len(text) < 8:
        return "****" if text else ""
    return text[:6] + "********" + text[-4:]


def mask_cert_no(value: str | None) -> str:
    text = value or ""
    if len(text) < 8:
        return "****" if text else ""
    return text[:3] + ("*" * (len(text) - 7)) + text[-4:]
