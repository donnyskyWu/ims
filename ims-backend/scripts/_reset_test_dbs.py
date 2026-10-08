"""One-off: DROP/CREATE ims_test and ims_ops_test."""
import os
import time
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

USER = os.environ.get("IMS_MYSQL_USER", "root")
PASSWORD = os.environ.get("IMS_MYSQL_PASSWORD", "root")
HOST = os.environ.get("IMS_MYSQL_HOST", "127.0.0.1")
PORT = os.environ.get("IMS_MYSQL_PORT", "3306")
auth = f"{quote_plus(USER)}:{quote_plus(PASSWORD)}"
url = f"mysql+pymysql://{auth}@{HOST}:{PORT}/?charset=utf8mb4"
engine = create_engine(url, pool_pre_ping=True)
def _kill_sessions(conn, db: str) -> None:
    rows = conn.execute(
        text(
            "SELECT id FROM information_schema.processlist "
            "WHERE db = :db AND id != CONNECTION_ID()"
        ),
        {"db": db},
    ).fetchall()
    for (pid,) in rows:
        conn.execute(text(f"KILL {int(pid)}"))


for db in ("ims_test", "ims_ops_test"):
    for attempt in range(5):
        with engine.begin() as conn:
            _kill_sessions(conn, db)
            conn.execute(text(f"DROP DATABASE IF EXISTS `{db}`"))
            try:
                conn.execute(text(f"CREATE DATABASE `{db}` CHARACTER SET utf8mb4"))
                print(f"Recreated {db}")
                break
            except Exception as exc:
                if attempt == 4:
                    raise
                print(f"Retry {db} after race: {exc!r}")
                time.sleep(0.5)
engine.dispose()
