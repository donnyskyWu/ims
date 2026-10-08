"""一次性导入用户。CSV 列：id,username,nickname,mobile,status。按 id 幂等。"""

import csv
import sys

from app.core import SessionLocal
from app.main import init_db
from app.models import ImportBatch, User
from app.security import hash_password


def import_file(path: str, source: str = "football") -> int:
    init_db()
    db = SessionLocal()
    count = 0
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                source_id = int(row["id"])
                done = db.query(ImportBatch).filter_by(source=source, source_id=source_id).first()
                if done:
                    continue
                user = db.get(User, source_id)
                if user is None:
                    user = User(id=source_id, username=row["username"], password_hash=hash_password("Import@123"))
                    db.add(user)
                user.nickname = row.get("nickname") or row["username"]
                user.mobile = row.get("mobile") or ""
                user.status = row.get("status") or "ENABLED"
                db.add(ImportBatch(source=source, source_id=source_id, user_id=source_id))
                count += 1
        db.commit()
    finally:
        db.close()
    return count


if __name__ == "__main__":
    print(import_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "football"))
