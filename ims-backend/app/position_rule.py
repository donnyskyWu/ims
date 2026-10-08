"""岗位 → 角色供给规则。权限明细仍在角色上，这里只挂角色和版本。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.models import PositionRule, Role, User
from app.org_sync import is_r1
from app.system_role import auto_create_role

router = APIRouter()


class RuleBody(BaseModel):
    ruleName: str
    dingtalkPosition: str
    description: str | None = ""
    grantRoleIds: list[int]


class AutoBody(BaseModel):
    dingtalkPosition: str


def rule_vo(db: Session, rule: PositionRule) -> dict:
    roles = []
    for role_id in list(rule.grant_role_ids or []):
        role = db.get(Role, int(role_id))
        if role is None or role.deleted:
            continue
        roles.append(
            {
                "roleId": role.id,
                "roleName": role.role_name,
                "source": role.source,
                "status": role.status,
            }
        )
    return {
        "id": rule.id,
        "ruleName": rule.template_name,
        "dingtalkPosition": rule.dingtalk_position,
        "version": rule.version,
        "status": rule.status,
        "grantRoles": roles,
        "appliedUserCount": rule.applied_user_count,
        "createdBy": rule.created_by,
        "createdAt": rule.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        "description": rule.description,
    }


def validate_grant(db: Session, body: RuleBody) -> list[Role] | None:
    name = (body.ruleName or "").strip()
    position = (body.dingtalkPosition or "").strip()
    if not name or len(name) > 64 or not position or len(position) > 64:
        return None
    if body.description and len(body.description) > 200:
        return None
    if not body.grantRoleIds:
        return None
    roles: list[Role] = []
    for role_id in body.grantRoleIds:
        role = db.get(Role, int(role_id))
        if role is None or role.deleted:
            raise LookupError(str(role_id))
        if role.status == "PENDING_CONFIG":
            raise PermissionError(role.role_name)
        roles.append(role)
    return roles


def enabled_conflict(db: Session, position: str, ignore_id: int | None = None) -> bool:
    rows = db.scalars(
        select(PositionRule).where(
            PositionRule.dingtalk_position == position,
            PositionRule.status == "ENABLED",
            PositionRule.deleted == 0,
        )
    ).all()
    return any(row.id != ignore_id for row in rows)


def require_r1(db: Session, user: User):
    if not is_r1(db, user):
        return fail(403, "仅 R1 可维护供给规则")
    return None


@router.get("/auth/position/rules")
@router.get("/auth/position/templates")
def list_rules(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    dingtalkPosition: str = "",
    grantRoleId: int | None = None,
    status: str = "",
    db: Session = Depends(db_session),
    _: User = Depends(current_user),
):
    page_no = pageNo if pageNo > 0 else 1
    size = pageSize if 0 < pageSize <= 100 else 10
    rows = db.scalars(select(PositionRule).where(PositionRule.deleted == 0).order_by(PositionRule.id.desc())).all()
    items = []
    for row in rows:
        if status and row.status != status:
            continue
        if dingtalkPosition and row.dingtalk_position != dingtalkPosition:
            continue
        if keyword and keyword not in row.template_name and keyword not in row.dingtalk_position:
            continue
        if grantRoleId is not None and int(grantRoleId) not in [int(item) for item in (row.grant_role_ids or [])]:
            continue
        items.append(rule_vo(db, row))
    start = (page_no - 1) * size
    return ok({"list": items[start : start + size], "total": len(items), "pageNo": page_no, "pageSize": size})


@router.post("/auth/position/rule")
@router.post("/auth/position/template")
def create_rule(body: RuleBody, db: Session = Depends(db_session), user: User = Depends(current_user)):
    denied = require_r1(db, user)
    if denied:
        return denied
    try:
        roles = validate_grant(db, body)
    except LookupError:
        return fail(1504, "资源不可用")
    except PermissionError:
        return fail(1002, "待配置角色不可授予")
    if roles is None:
        return fail(1001, "供给规则字段不合法")
    position = body.dingtalkPosition.strip()
    if enabled_conflict(db, position):
        return fail(1001, "该岗位已有启用版本")
    rule = PositionRule(
        template_name=body.ruleName.strip(),
        dingtalk_position=position,
        version=1,
        status="ENABLED",
        grant_role_ids=[role.id for role in roles],
        description=(body.description or "").strip(),
        applied_user_count=0,
        created_by=user.id,
        tenant_id=0,
    )
    db.add(rule)
    db.flush()
    return ok(rule_vo(db, rule))


@router.put("/auth/position/rule/{rule_id}")
@router.put("/auth/position/template/{rule_id}")
def edit_rule(rule_id: int, body: RuleBody, db: Session = Depends(db_session), user: User = Depends(current_user)):
    denied = require_r1(db, user)
    if denied:
        return denied
    current = db.get(PositionRule, rule_id)
    if current is None or current.deleted:
        return fail(1504, "资源不可用")
    try:
        roles = validate_grant(db, body)
    except LookupError:
        return fail(1504, "资源不可用")
    except PermissionError:
        return fail(1002, "待配置角色不可授予")
    if roles is None:
        return fail(1001, "供给规则字段不合法")
    position = body.dingtalkPosition.strip()
    if enabled_conflict(db, position, ignore_id=current.id):
        return fail(1001, "该岗位已有启用版本")
    current.status = "DISABLED"
    newer = PositionRule(
        template_name=body.ruleName.strip(),
        dingtalk_position=position,
        version=current.version + 1,
        status="ENABLED",
        grant_role_ids=[role.id for role in roles],
        description=(body.description or "").strip(),
        applied_user_count=0,
        created_by=user.id,
        tenant_id=0,
        created_at=utcnow(),
    )
    db.add(newer)
    db.flush()
    return ok(rule_vo(db, newer))


@router.delete("/auth/position/rule/{rule_id}")
@router.delete("/auth/position/template/{rule_id}")
def delete_rule(
    rule_id: int,
    confirmText: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    denied = require_r1(db, user)
    if denied:
        return denied
    rule = db.get(PositionRule, rule_id)
    if rule is None or rule.deleted:
        return fail(1504, "资源不可用")
    if confirmText != "DELETE":
        return fail(1001, "请确认删除")
    if rule.applied_user_count:
        return fail(1001, "在用用户非零，不能删除")
    rule.deleted = 1
    rule.status = "DISABLED"
    return ok(None)


@router.post("/auth/position/role-auto-create")
def role_auto_create(body: AutoBody, db: Session = Depends(db_session), user: User = Depends(current_user)):
    denied = require_r1(db, user)
    if denied:
        return denied
    position = (body.dingtalkPosition or "").strip()
    if not position:
        return fail(1001, "钉钉岗位必填")
    role, created, todo_id = auto_create_role(db, position)
    return ok(
        {
            "roleId": role.id,
            "roleName": role.role_name,
            "source": role.source,
            "status": role.status,
            "created": created,
            "todoId": todo_id,
        }
    )
