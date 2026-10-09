import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, ok
from app.core import SessionLocal, utcnow
from app.models import LoginLog, Notify, OperateLog, User

router = APIRouter()

CHANNEL_LABEL = {"IN_APP": "站内", "DINGTALK": "钉钉", "BOTH": "站内+钉钉"}
STATUS_LABEL = {"DELIVERED": "已送达", "DEDUPED": "去重跳过"}
CHANNEL_QUERY = {
    "站内": "IN_APP",
    "钉钉": "DINGTALK",
    "站内+钉钉": "BOTH",
    "IN_APP": "IN_APP",
    "DINGTALK": "DINGTALK",
    "BOTH": "BOTH",
}


def clamp_page(page_no: int, page_size: int) -> tuple[int, int]:
    page = page_no if page_no > 0 else 1
    size = page_size if 0 < page_size <= 100 else 10
    return page, size


def clock(value) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def describe(method: str, path: str) -> tuple[str, str, str]:
    rel = path
    prefix = "/admin-api/ims"
    if rel.startswith(prefix):
        rel = rel[len(prefix) :] or "/"
    verb = {"POST": "新增", "PUT": "更新", "DELETE": "删除"}.get(method, method)
    module = "业务"
    if rel.startswith("/system") or rel.startswith("/auth"):
        module = "系统"
    elif rel.startswith("/fin"):
        module = "财务"
    action = verb
    for needle, name in (
        ("/system/user", "用户"),
        ("/system/role", "角色"),
        ("/system/dict-data", "字典"),
        ("/system/param", "参数"),
        ("/auth/position", "岗位供给"),
        ("/auth/org", "组织"),
        ("/auth/workbench", "工作台"),
        ("/dc/dashboard", "全链路看板"),
        ("/fin/dashboard", "利润看板"),
        ("/fin/share/result", "分成单"),
        ("/fin/cost", "成本"),
        ("/fin/profit", "利润"),
    ):
        if needle in rel:
            action = f"{verb}{name}"
            break
    else:
        action = f"{verb} {rel}"
    return module, action, f"{method} {rel}"


def write_login_log(
    db: Session,
    *,
    username: str,
    user_id: int | None,
    success: bool,
    result_code: int,
    message: str,
    login_type: str,
    path: str,
    tenant_id: int = 0,
) -> None:
    now = utcnow()
    db.add(
        LoginLog(
            username=username or "",
            user_id=user_id,
            success=1 if success else 0,
            result_code=result_code,
            message=message,
            login_type=login_type,
            path=path,
            creator=user_id or 0,
            updater=user_id or 0,
            tenant_id=tenant_id or 0,
            created_at=now,
            updated_at=now,
        )
    )


def write_operate_log(
    *,
    operator_id: int,
    operator_name: str,
    tenant_id: int,
    method: str,
    path: str,
    result_code: int,
) -> None:
    module, action, shown = describe(method, path)
    now = utcnow()
    detail = json.dumps({"method": method, "path": shown, "code": result_code}, ensure_ascii=False)
    db = SessionLocal()
    try:
        db.add(
            OperateLog(
                module=module,
                action=action,
                operator_id=operator_id,
                operator_name=operator_name or "",
                path=shown,
                detail_json=detail,
                result_code=result_code,
                creator=operator_id,
                updater=operator_id,
                tenant_id=tenant_id or 0,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    finally:
        db.close()


def publish_notify(
    db: Session,
    *,
    event_type: str,
    biz_key: str,
    receiver: str,
    channel: str = "IN_APP",
    receiver_user_id: int = 0,
    tenant_id: int = 0,
    creator: int = 0,
) -> dict:
    existing = db.scalar(
        select(Notify).where(
            Notify.tenant_id == tenant_id,
            Notify.event_type == event_type,
            Notify.biz_key == biz_key,
            Notify.deleted == 0,
        )
    )
    if existing is not None:
        return {"deduped": True, "id": existing.id}
    now = utcnow()
    row = Notify(
        event_type=event_type,
        biz_key=biz_key,
        receiver=receiver,
        receiver_user_id=receiver_user_id,
        channel=channel if channel in CHANNEL_LABEL else "IN_APP",
        status="DELIVERED",
        creator=creator,
        updater=creator,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return {"deduped": False, "id": row.id}


def operate_vo(row: OperateLog) -> dict:
    return {
        "id": row.id,
        "time": clock(row.created_at),
        "user": row.operator_name,
        "action": row.action,
        "path": row.path,
        "module": row.module,
        "resultCode": row.result_code,
    }


def login_vo(row: LoginLog) -> dict:
    return {
        "id": row.id,
        "time": clock(row.created_at),
        "user": row.username,
        "action": "登录成功" if row.success else "登录失败",
        "path": row.path,
        "module": "登录",
        "resultCode": row.result_code,
        "success": bool(row.success),
    }


def notify_vo(row: Notify) -> dict:
    return {
        "id": row.id,
        "eventType": row.event_type,
        "bizKey": row.biz_key,
        "receiver": row.receiver,
        "channel": CHANNEL_LABEL.get(row.channel, row.channel),
        "channelCode": row.channel,
        "status": STATUS_LABEL.get(row.status, row.status),
        "statusCode": row.status,
        "time": clock(row.created_at),
    }


@router.get("/system/operate-log/page")
def operate_page(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    module: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    page, size = clamp_page(pageNo, pageSize)
    stmt = select(OperateLog).where(OperateLog.deleted == 0, OperateLog.tenant_id == (user.tenant_id or 0))
    if keyword:
        stmt = stmt.where(or_(OperateLog.operator_name.like(f"%{keyword}%"), OperateLog.path.like(f"%{keyword}%")))
    if module and module != "全部":
        stmt = stmt.where(OperateLog.module == module)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(OperateLog.id.desc()).offset((page - 1) * size).limit(size)).all()
    return ok({"list": [operate_vo(row) for row in rows], "total": total, "pageNo": page, "pageSize": size})


@router.get("/system/login-log/page")
def login_page(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    module: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    page, size = clamp_page(pageNo, pageSize)
    if module in ("业务", "系统"):
        return ok({"list": [], "total": 0, "pageNo": page, "pageSize": size})
    stmt = select(LoginLog).where(LoginLog.deleted == 0, LoginLog.tenant_id == (user.tenant_id or 0))
    if keyword:
        stmt = stmt.where(or_(LoginLog.username.like(f"%{keyword}%"), LoginLog.path.like(f"%{keyword}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(LoginLog.id.desc()).offset((page - 1) * size).limit(size)).all()
    return ok({"list": [login_vo(row) for row in rows], "total": total, "pageNo": page, "pageSize": size})


@router.get("/system/notify/page")
def notify_page(
    pageNo: int = 1,
    pageSize: int = 10,
    eventType: str = "",
    channel: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    page, size = clamp_page(pageNo, pageSize)
    stmt = select(Notify).where(Notify.deleted == 0, Notify.tenant_id == (user.tenant_id or 0))
    if eventType and eventType != "全部事件":
        stmt = stmt.where(Notify.event_type == eventType)
    mapped = CHANNEL_QUERY.get(channel, "")
    if mapped:
        stmt = stmt.where(Notify.channel == mapped)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Notify.id.desc()).offset((page - 1) * size).limit(size)).all()
    return ok({"list": [notify_vo(row) for row in rows], "total": total, "pageNo": page, "pageSize": size})
