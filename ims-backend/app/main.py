import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import AuthError, fail, router
from app.core import IMS_DB, OPS_DB, SessionLocal, ensure_databases, engine
from app.core import Base
from sqlalchemy import select

from app.models import Role, User, UserRole
from app.security import hash_password


E2E_OPS_AUTHOR_ID = 900_001


def _ensure_e2e_ops_author(ops) -> None:
    """Playwright 工作任务 closure：固定 ops 作者 id，供 IP 组「关联作者」纯 UI 绑定。"""
    from app.ops_models import AuthorUser

    author = ops.get(AuthorUser, E2E_OPS_AUTHOR_ID)
    if author is not None and author.deleted == 0:
        return
    ops.add(
        AuthorUser(
            id=E2E_OPS_AUTHOR_ID,
            author_name="E2EClosureAuthor",
            status="ENABLED",
            tenant_id=0,
        )
    )


def _ensure_e2e_douyin_account(db, ops) -> None:
    from app.ops_models import Company, IpGroup, PlatformAccount

    exists = ops.scalar(
        select(PlatformAccount.id).where(
            PlatformAccount.platform_type == "DOUYIN",
            PlatformAccount.deleted == 0,
        )
    )
    if exists is not None:
        return
    company = Company(company_name="E2E内容公司", status="ENABLED", tenant_id=0)
    group = IpGroup(group_name="E2E发布组", status="ENABLED", tenant_id=0)
    ops.add_all([company, group])
    ops.flush()
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    holder = admin.id if admin is not None else 1
    ops.add(
        PlatformAccount(
            account_no="AC-E2E-PUB",
            account_name="E2E抖音号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            holder_user_id=holder,
            author_user_id=holder,
            status="IN_USE",
            tenant_id=0,
        )
    )


def _ensure_e2e_author(db) -> None:
    """Playwright 发布督办闭环：审核人( admin ) ≠ 提交人( e2e_author )，规避 1057。"""
    role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
    author = db.scalar(select(User).where(User.username == "e2e_author", User.deleted == 0))
    if author is None:
        author = User(
            username="e2e_author",
            nickname="E2E内容作者",
            mobile="13900000002",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
        )
        db.add(author)
        db.flush()
    if role is not None and not db.scalar(
        select(UserRole).where(UserRole.user_id == author.id, UserRole.role_id == role.id)
    ):
        db.add(UserRole(user_id=author.id, role_id=role.id, tenant_id=0))


def seed() -> None:
    db = SessionLocal()
    try:
        if db.get(User, 1) is None and db.query(User).filter(User.username == "admin").first() is None:
            db.add(
                User(
                    username="admin",
                    nickname="管理员",
                    mobile="13812345678",
                    password_hash=hash_password("Admin@123"),
                    status="ENABLED",
                )
            )
            db.flush()
        from app.system_dict import seed_dict
        from app.system_role import seed_roles

        seed_roles(db)
        seed_dict(db)
        from app.scope import refresh_user_scope

        admin = db.query(User).filter(User.username == "admin", User.deleted == 0).first()
        if admin is not None:
            refresh_user_scope(db, admin.id)
        from app.ops_db import ops_session

        ops = ops_session()
        try:
            _ensure_e2e_douyin_account(db, ops)
            _ensure_e2e_ops_author(ops)
            ops.commit()
        finally:
            ops.close()
        _ensure_e2e_author(db)
        author = db.query(User).filter(User.username == "e2e_author", User.deleted == 0).first()
        if author is not None:
            refresh_user_scope(db, author.id)
        from app.bi_br212_seed import ensure_bi_br212_seed

        ensure_bi_br212_seed(db)
        from app.workbench_seed import refresh_workbench_e2e_seed
        from app.acct_seed import ensure_acct_e2e_pool_account, ensure_acct_schema, refresh_acct_e2e_pool
        from app.live_fin_e2e_seed import ensure_live_fin_e2e_deps, refresh_live_fin_e2e_deps
        from app.cert_e2e_seed import refresh_cert_e2e_seed
        from app.train_stat_e2e_seed import refresh_train_stat_e2e_seed

        ensure_acct_schema()
        admin = db.query(User).filter(User.username == "admin", User.deleted == 0).first()
        if admin is not None:
            refresh_workbench_e2e_seed(db, admin)
            ensure_acct_e2e_pool_account(db, admin)
            refresh_acct_e2e_pool(db, admin)
            ensure_live_fin_e2e_deps(db, admin)
            refresh_live_fin_e2e_deps(db, admin)
            refresh_cert_e2e_seed(db, admin)
            refresh_train_stat_e2e_seed(db, admin)
        db.commit()
    finally:
        db.close()


def ensure_bi_br212_columns() -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    for table in ("ims_bi_report_def", "ims_bi_share_link"):
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        if "dept_id" in cols:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN dept_id BIGINT NOT NULL DEFAULT 0"))
            conn.execute(text(f"CREATE INDEX idx_{table}_dept_id ON {table} (dept_id)"))


def ensure_train_stat_schema() -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "ims_train_task_record" in tables:
        cols = {c["name"] for c in insp.get_columns("ims_train_task_record")}
        if "study_seconds" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE ims_train_task_record ADD COLUMN study_seconds INT NOT NULL DEFAULT 0")
                )


def ensure_asset_purchase_column() -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "ims_asset_ledger" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("ims_asset_ledger")}
    if "purchase_batch_no" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ims_asset_ledger ADD COLUMN purchase_batch_no VARCHAR(32) NOT NULL DEFAULT ''"))
        conn.execute(text("CREATE INDEX idx_asset_ledger_purchase_batch ON ims_asset_ledger (purchase_batch_no)"))


def init_db() -> None:
    ensure_databases()
    Base.metadata.create_all(engine)
    ensure_bi_br212_columns()
    ensure_asset_purchase_column()
    ensure_train_stat_schema()
    from app.ops_db import ensure_ops

    ensure_ops()
    seed()


def create_app() -> FastAPI:
    app = FastAPI(title="IMS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def audit_protected_writes(request: Request, call_next):
        response = await call_next(request)
        operator_id = getattr(request.state, "operator_id", None)
        path = request.url.path
        if not operator_id or request.method not in {"POST", "PUT", "DELETE"} or not path.startswith("/admin-api/ims/"):
            return response
        result_code = 0
        raw = getattr(response, "body", b"") or b""
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and isinstance(parsed.get("code"), int):
                    result_code = parsed["code"]
            except Exception:
                result_code = 0
        from app.audit import write_operate_log

        write_operate_log(
            operator_id=operator_id,
            operator_name=getattr(request.state, "operator_name", ""),
            tenant_id=getattr(request.state, "tenant_id", 0) or 0,
            method=request.method,
            path=path,
            result_code=result_code,
        )
        return response

    @app.exception_handler(AuthError)
    async def auth_error(_: Request, exc: AuthError):
        return fail(exc.code, exc.msg)

    @app.get("/health")
    def root_health():
        return {"code": 0, "msg": "ok", "data": {"status": "up", "db": IMS_DB, "ops": OPS_DB}}

    app.include_router(router, prefix="/admin-api/ims")
    return app


app = create_app()


def main() -> None:
    import os
    import uvicorn

    init_db()
    port = int(os.environ.get("IMS_PORT", "18080"))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
