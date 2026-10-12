"""分环境配置。环境变量用大写下划线覆盖同名路径，不回显配置值。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.core.errors import StartupError

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

REQUIRED = [
    "db.host",
    "db.port",
    "db.user",
    "db.password",
    "db.name",
    "redis.host",
    "redis.port",
    "jwt.secret",
    "security.field_key",
    "security.hash_key",
    "file.storage_root",
]


def _flatten(data, prefix=""):
    out = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(value, path))
    else:
        out[prefix] = data
    return out


def _set_path(tree: dict, path: str, value):
    parts = path.split(".")
    cur = tree
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


@dataclass
class DbConf:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = ""
    password: str = ""
    name: str = ""

    def url(self, name: str | None = None) -> str:
        db = name or self.name
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{db}?charset=utf8mb4"


@dataclass
class FootballConf:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = ""
    password: str = ""
    name: str = ""
    schema_file: str = ""
    enabled: bool = True
    schema_check: str = "strict"  # strict | warn | off
    tenant_map: dict = field(default_factory=lambda: {"1": 1})

    def url(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?charset=utf8mb4"


@dataclass
class Settings:
    env: str = "dev"
    version: str = "2.0.0-b0a"
    raw: dict = field(default_factory=dict)
    db: DbConf = field(default_factory=DbConf)
    football_live: FootballConf = field(default_factory=FootballConf)
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_memory: bool = False
    jwt_secret: str = ""
    jwt_access_seconds: int = 7200
    jwt_refresh_seconds: int = 604800
    storage_root: str = "/tmp/ims-files"
    field_key: str = ""
    field_keys: dict = field(default_factory=dict)
    hash_key: str = ""
    id_as_string: bool = True
    dingtalk: dict = field(default_factory=dict)
    dingtalk_attendance: dict = field(default_factory=dict)
    train_ai: dict = field(default_factory=dict)
    integrations: dict = field(default_factory=dict)
    docs_enabled: bool = True

    def football_tenant_for(self, ims_tenant_id: int) -> int | None:
        mapping = self.football_live.tenant_map or {}
        if str(ims_tenant_id) in mapping:
            return int(mapping[str(ims_tenant_id)])
        if ims_tenant_id in mapping:
            return int(mapping[ims_tenant_id])
        return None


def load_settings(env: str | None = None, config_path: str | None = None, extra_env: dict | None = None) -> Settings:
    env_name = env or os.environ.get("IMS_ENV", "dev")
    path = Path(config_path) if config_path else CONFIG_DIR / f"{env_name}.yaml"
    if not path.exists():
        raise StartupError(f"配置文件不存在: {path.name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    env_map = dict(os.environ)
    if extra_env:
        env_map.update(extra_env)
    flat = _flatten(data)
    for key in list(flat):
        upper = key.replace(".", "_").upper()
        if upper in env_map and env_map[upper] != "":
            _set_path(data, key, env_map[upper])
        elif f"IMS_{upper}" in env_map and env_map[f"IMS_{upper}"] != "":
            _set_path(data, key, env_map[f"IMS_{upper}"])
    flat = _flatten(data)
    missing = [key for key in REQUIRED if flat.get(key) in (None, "")]
    if missing:
        raise StartupError("缺少必填配置: " + ", ".join(missing))
    db = data.get("db") or {}
    fb = data.get("football_live") or {}
    redis = data.get("redis") or {}
    jwt = data.get("jwt") or {}
    sec = data.get("security") or {}
    file_conf = data.get("file") or {}
    api = data.get("api") or {}
    tenant_map = fb.get("tenant_map") or {"1": 1}
    if isinstance(tenant_map, dict):
        tenant_map = {str(k): int(v) for k, v in tenant_map.items()}
    settings = Settings(
        env=env_name,
        version=str(data.get("version") or "2.0.0-b0a"),
        raw=data,
        db=DbConf(str(db["host"]), int(db["port"]), str(db["user"]), str(db["password"]), str(db["name"])),
        football_live=FootballConf(
            str(fb.get("host") or "127.0.0.1"),
            int(fb.get("port") or 3306),
            str(fb.get("user") or ""),
            str(fb.get("password") or ""),
            str(fb.get("name") or ""),
            str(fb.get("schema_file") or ""),
            bool(fb.get("enabled", True)),
            str(fb.get("schema_check") or "strict"),
            tenant_map,
        ),
        redis_host=str(redis.get("host")),
        redis_port=int(redis.get("port")),
        redis_db=int(redis.get("db") or 0),
        jwt_secret=str(jwt.get("secret")),
        jwt_access_seconds=int(jwt.get("access_seconds") or 7200),
        jwt_refresh_seconds=int(jwt.get("refresh_seconds") or 604800),
        storage_root=str(file_conf.get("storage_root")),
        field_key=str(sec.get("field_key")),
        field_keys=dict(sec.get("field_keys") or {}),
        hash_key=str(sec.get("hash_key")),
        id_as_string=str(api.get("id_as_string", True)).lower() not in ("0", "false", "no"),
        dingtalk=dict(data.get("dingtalk") or {}),
        dingtalk_attendance=dict(data.get("dingtalk_attendance") or {}),
        train_ai=dict(data.get("train_ai") or {}),
        integrations=dict(data.get("integrations") or {}),
        docs_enabled=env_name != "prod",
    )
    if not settings.field_keys:
        settings.field_keys = {"v1": settings.field_key}
    return settings


_current: Settings | None = None


def get_settings() -> Settings:
    global _current
    if _current is None:
        _current = load_settings()
    return _current


def set_settings(settings: Settings) -> None:
    global _current
    _current = settings
