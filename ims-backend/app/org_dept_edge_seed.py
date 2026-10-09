"""#194 部门边角夹具。模拟入职写入父子两个部门，并准备本部门查看账号。

不调用钉钉。closure 随后只在页面上筛选、看空态和本地重放。
"""

from __future__ import annotations

import json

from sqlalchemy import delete, select

from app.core import SessionLocal, utcnow
from app.dingtalk_crypto import decrypt_encrypt, pack
from app.models import OrgEvent, Role, RolePerm, User, UserDept, UserRole
from app.security import hash_password

PARENT = 19410
CHILD = 19411
R2_USER = "e2e_org_r2"
PASSWORD = "Admin@123"
PARENT_NAME = "部门边父"
CHILD_NAME = "部门边子"


def _post(db, payload: dict) -> None:
    import app.api  # noqa: F401
    from app.org_sync import enqueue, process_due

    plain = json.dumps(payload, ensure_ascii=False)
    body, _headers = pack(plain, "1700000000000", "nonce-org-194")
    accepted, message = enqueue(db, decrypt_encrypt(body["encrypt"]))
    if not accepted:
        raise RuntimeError(message or "事件未入队")
    db.flush()
    process_due(db)


def _hire(db, event_id: str, ding: str, mobile: str, dept: int, name: str) -> None:
    _post(
        db,
        {
            "eventType": "hire",
            "dingtalkEventId": event_id,
            "unionId": ding,
            "payloadJson": {
                "dingtalkUserId": ding,
                "nickname": name,
                "mobile": mobile,
                "deptIds": [dept],
                "deptNames": [name],
                "afterDept": name,
            },
        },
    )


def _r2(db) -> None:
    role = db.scalar(select(Role).where(Role.role_key == "org:e2e-r2", Role.deleted == 0))
    if role is None:
        role = Role(
            role_name="组织本部门",
            role_key="org:e2e-r2",
            data_scope="DEPT",
            status="ENABLED",
            source="MANUAL",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    else:
        role.data_scope = "DEPT"
        role.status = "ENABLED"
    if db.scalar(select(RolePerm.id).where(RolePerm.role_id == role.id, RolePerm.perm_code == "auth:org:query")) is None:
        db.add(RolePerm(role_id=role.id, module_code="auth", perm_code="auth:org:query", perm_level="R", tenant_id=0))
    user = db.scalar(select(User).where(User.username == R2_USER, User.deleted == 0))
    if user is None:
        user = User(
            username=R2_USER,
            nickname="组织本部门",
            mobile="13900019402",
            password_hash=hash_password(PASSWORD),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
    else:
        user.password_hash = hash_password(PASSWORD)
        user.status = "ENABLED"
        user.mobile = "13900019402"
    if db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_id == role.id)) is None:
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
    existing = db.scalars(select(UserDept).where(UserDept.user_id == user.id)).all()
    if not any(row.dept_id == PARENT for row in existing):
        db.add(UserDept(user_id=user.id, dept_id=PARENT, tenant_id=0))


def _blank(db) -> None:
    row = db.scalar(select(OrgEvent).where(OrgEvent.dingtalk_event_id == "e2e-org-194-blank"))
    now = utcnow()
    if row is None:
        db.add(
            OrgEvent(
                dingtalk_event_id="e2e-org-194-blank",
                event_type="dept_change",
                idempotency_key="e2e-org-194-blank|dept_change",
                payload_json="{}",
                sync_status="SUCCESS",
                retry_count=0,
                dead_letter=0,
                tenant_id=0,
                created_at=now,
                updated_at=now,
                synced_at=now,
            )
        )


def deliver() -> dict:
    db = SessionLocal()
    try:
        db.execute(delete(OrgEvent).where(OrgEvent.event_type == "reconcile"))
        _hire(db, "evt-194-p", "dt-org-194-p", "13700019410", PARENT, PARENT_NAME)
        _hire(db, "evt-194-c", "dt-org-194-c", "13700019411", CHILD, CHILD_NAME)
        _r2(db)
        _blank(db)
        db.commit()
        return {"parent": PARENT, "child": CHILD, "r2": R2_USER}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(deliver(), ensure_ascii=False))
