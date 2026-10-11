"""对照脚本：对齐 dict_content_type，并把存量作品类型映射到三项。

可重复执行。启动时 seed() 会走同一套 apply_content_type_compat。

    PYTHONPATH=ims-backend python -m app.content_type_compat
"""

from __future__ import annotations


def main() -> None:
    import app.api  # noqa: F401  先加载 API，避免字典路由的循环导入
    from app.core import SessionLocal
    from app.ops_db import ops_session
    from app.system_dict import apply_content_type_compat

    db = SessionLocal()
    ops = ops_session()
    try:
        changed = apply_content_type_compat(db, ops)
        db.commit()
        ops.commit()
        print(f"dict_content_type aligned; remapped {changed} rows")
    finally:
        db.close()
        ops.close()


if __name__ == "__main__":
    main()
