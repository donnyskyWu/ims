"""One-shot: write dingtalk/football params from process env (loaded from .env by caller)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import init_db
from app.models import SysParam
from app.settings_runtime import invalidate_param_cache

MAP = {
    "dingtalk.corpId": "IMS_DINGTALK_CORP_ID",
    "dingtalk.clientId": "IMS_DINGTALK_CLIENT_ID",
    "dingtalk.clientSecret": "IMS_DINGTALK_CLIENT_SECRET",
    "dingtalk.agentId": "IMS_DINGTALK_AGENT_ID",
    "dingtalk.appId": "IMS_DINGTALK_APP_ID",
    "dingtalk.callbackToken": "IMS_DINGTALK_TOKEN",
    "dingtalk.callbackAesKey": "IMS_DINGTALK_AES_KEY",
    "dingtalk.l3Enabled": "IMS_DINGTALK_L3",
    "football.webapiBaseUrl": "IMS_FOOTBALL_WEBAPI_BASE_URL",
}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for key, env_name in MAP.items():
            val = (os.environ.get(env_name) or "").strip()
            if not val:
                continue
            row = db.scalar(select(SysParam).where(SysParam.param_key == key))
            if row is None:
                print(f"skip unknown key (run init_db seed first): {key}")
                continue
            row.param_value = val
            row.updated_at = utcnow()
            print(f"set {key} from {env_name}")
        db.commit()
        invalidate_param_cache()
    finally:
        db.close()


if __name__ == "__main__":
    main()
