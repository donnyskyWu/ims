"""后台任务进程。消费组织事件 outbox，失败按 1 分钟 / 5 分钟 / 15 分钟 / 1 小时退避，16 次后死信。"""

import time

from app.core import SessionLocal
from app.ops_db import ops_session
from app.main import init_db
from app.content_fb_sync import process_due_outbox
from app.org_sync import process_due


def main() -> None:
    init_db()
    while True:
        db = SessionLocal()
        try:
            process_due(db)
            ops = ops_session()
            try:
                process_due_outbox(db, ops)
            finally:
                ops.close()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        time.sleep(5)


if __name__ == "__main__":
    main()
