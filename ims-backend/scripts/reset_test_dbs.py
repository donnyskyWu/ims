"""Drop and recreate ims_test / ims_ops_test (one-off for local pytest)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core import server_url

NAMES = ("ims_test", "ims_ops_test")


def main() -> None:
    engine = create_engine(server_url(), pool_pre_ping=True)
    with engine.begin() as conn:
        for name in NAMES:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{name}`"))
            conn.execute(text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4"))
            print("ok", name)
    engine.dispose()


if __name__ == "__main__":
    main()
