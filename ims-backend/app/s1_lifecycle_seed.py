"""S1 模拟钉钉事件。只用仓库里已有的本地验签默认值，不写真实密钥。

入职 / 调岗 / 离职由本模块验签入队再 process_due。
closure 里随后的领用、归还、证件操作仍走页面。
"""

from __future__ import annotations

import json
import sys

from sqlalchemy import delete, select

from app.core import SessionLocal
from app.dingtalk_crypto import pack
from app.models import (
    AccountApply,
    AssetLedger,
    CertArchive,
    CertExpireLog,
    OrgEvent,
    PositionRule,
    Role,
    RolePerm,
    Todo,
    User,
    UserDept,
    UserRole,
    WorkMessage,
)
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount
from app.security import hash_password

DING_ID = "dt-e2e-s1"
NICKNAME = "E2E主播小周"
MOBILE = "13900007301"
USERNAME = "e2e_s1_anchor"
PASSWORD = "Admin@123"
ACCOUNT_NO = "AC-E2E-S1"
ACCOUNT_NICK = "E2E-S1抖音"
POSITION = "主播运营"
NEXT_POSITION = "编导"
ANCHOR_ROLE_KEY = "e2e:anchor-ops"
DIRECTOR_ROLE_KEY = "e2e:director-ops"
ANCHOR_PERM = "auth:workbench:query"
DIRECTOR_PERM = "content:plan:query"
DEPT_CONTENT = 7301
DEPT_LIVE = 7302
EVENT_IDS = {
    "hire": "e2e-s1-hire",
    "transfer": "e2e-s1-transfer",
    "resign": "e2e-s1-resign",
}


def _role(db, name: str, key: str, perm: str, scope: str) -> Role:
    role = db.scalar(select(Role).where(Role.role_key == key, Role.deleted == 0))
    if role is None:
        role = Role(
            role_name=name,
            role_key=key,
            data_scope=scope,
            status="ENABLED",
            source="MANUAL",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    else:
        role.role_name = name
        role.data_scope = scope
        role.status = "ENABLED"
    exists = db.scalar(select(RolePerm).where(RolePerm.role_id == role.id, RolePerm.perm_code == perm))
    if exists is None:
        db.add(RolePerm(role_id=role.id, module_code="auth", perm_code=perm, perm_level="R", tenant_id=0))
    return role


def _rule(db, position: str, role: Role, title: str) -> None:
    rule = db.scalar(
        select(PositionRule).where(
            PositionRule.dingtalk_position == position,
            PositionRule.status == "ENABLED",
            PositionRule.deleted == 0,
        )
    )
    if rule is None:
        db.add(
            PositionRule(
                template_name=title,
                dingtalk_position=position,
                version=1,
                status="ENABLED",
                grant_role_ids=[role.id],
                description="S1 模拟事件供给",
                applied_user_count=0,
                created_by=0,
                tenant_id=0,
            )
        )
        return
    ids = [int(item) for item in (rule.grant_role_ids or [])]
    if role.id not in ids:
        rule.grant_role_ids = ids + [role.id]


def _ensure_pool_account(admin: User) -> None:
    ops = ops_session()
    try:
        row = ops.scalar(
            select(PlatformAccount).where(PlatformAccount.account_no == ACCOUNT_NO, PlatformAccount.deleted == 0)
        )
        if row is None:
            company = ops.scalar(select(Company).where(Company.deleted == 0).limit(1))
            group = ops.scalar(select(IpGroup).where(IpGroup.deleted == 0).limit(1))
            if company is None or group is None:
                company = Company(company_name="E2E领用公司", status="ENABLED", tenant_id=0)
                group = IpGroup(group_name="E2E领用组", status="ENABLED", tenant_id=0)
                ops.add_all([company, group])
                ops.flush()
            row = PlatformAccount(
                account_no=ACCOUNT_NO,
                account_name=ACCOUNT_NICK,
                platform_type="DOUYIN",
                ip_group_id=group.id,
                company_id=company.id,
                holder_user_id=admin.id,
                status="IN_POOL",
                tenant_id=0,
            )
            ops.add(row)
        ops.commit()
    finally:
        ops.close()


def ensure_s1_fixtures(db) -> User | None:
    """岗位供给与池内账号。不投递事件，也不覆盖已有钉钉回调密钥。"""
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    anchor = _role(db, POSITION, ANCHOR_ROLE_KEY, ANCHOR_PERM, "ALL")
    director = _role(db, NEXT_POSITION, DIRECTOR_ROLE_KEY, DIRECTOR_PERM, "SELF")
    _rule(db, POSITION, anchor, "主播运营岗供给")
    _rule(db, NEXT_POSITION, director, "编导岗供给")
    db.flush()
    if admin is not None:
        _ensure_pool_account(admin)
    return admin


def _subject(db) -> User | None:
    return db.scalar(select(User).where(User.dingtalk_user_id == DING_ID, User.deleted == 0))


def reset_pool_account(admin_id: int) -> None:
    ops = ops_session()
    try:
        row = ops.scalar(
            select(PlatformAccount).where(PlatformAccount.account_no == ACCOUNT_NO, PlatformAccount.deleted == 0)
        )
        if row is not None:
            row.status = "IN_POOL"
            row.holder_user_id = admin_id
            ops.commit()
    finally:
        ops.close()


def reset_s1_subject(db) -> None:
    user = _subject(db)
    db.execute(delete(OrgEvent).where(OrgEvent.dingtalk_event_id.in_(tuple(EVENT_IDS.values()))))
    if user is None:
        return
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    db.execute(delete(UserDept).where(UserDept.user_id == user.id))
    db.execute(delete(Todo).where(Todo.ref_type == "org_resign", Todo.ref_id == user.id))
    db.execute(
        delete(WorkMessage).where(
            WorkMessage.user_id == user.id,
            WorkMessage.ref_type == "org_transfer_buffer",
        )
    )
    user.status = "ENABLED"
    certs = db.scalars(select(CertArchive).where(CertArchive.holder_name == NICKNAME, CertArchive.deleted == 0)).all()
    cert_ids = [row.id for row in certs]
    for row in certs:
        row.deleted = 1
    if cert_ids:
        logs = db.scalars(select(CertExpireLog).where(CertExpireLog.cert_id.in_(cert_ids), CertExpireLog.deleted == 0)).all()
        for log in logs:
            log.deleted = 1
    applies = db.scalars(select(AccountApply).where(AccountApply.account_no == ACCOUNT_NO)).all()
    for apply in applies:
        if apply.apply_status in ("PENDING_APPROVAL", "PENDING_HANDOVER", "APPROVED"):
            apply.apply_status = "RETURNED"
    # 中途超时的 closure 会留下 IN_USE 台账。下一次入职要清掉，否则名下「资产在用」不为 0。
    assets = db.scalars(
        select(AssetLedger).where(
            AssetLedger.owner_user_id == user.id,
            AssetLedger.deleted == 0,
            AssetLedger.status == "IN_USE",
        )
    ).all()
    for asset in assets:
        asset.status = "RETURNED"


def _post(db, payload: dict) -> None:
    import app.api  # noqa: F401  先装载 api，避免 org_sync 与 api 的环在脚本入口断开
    from app.org_sync import enqueue, process_due

    plain = json.dumps(payload, ensure_ascii=False)
    body, _headers = pack(plain, "1700000000000", "nonce-s1")
    from app.dingtalk_crypto import decrypt_encrypt

    accepted, message = enqueue(db, decrypt_encrypt(body["encrypt"]))
    if not accepted:
        raise RuntimeError(message or "事件未入队")
    db.flush()
    process_due(db)


def _pin_login(db, user: User) -> None:
    taken = db.scalar(select(User).where(User.username == USERNAME, User.id != user.id, User.deleted == 0))
    if taken is None:
        user.username = USERNAME
    user.password_hash = hash_password(PASSWORD)
    if not user.mobile:
        user.mobile = MOBILE


def expire_buffer(db) -> None:
    from datetime import timedelta

    import app.api  # noqa: F401  先装载 api，避免 org_sync 与 api 的环在脚本入口断开
    from app.org_sync import expire_transfer_buffers

    user = _subject(db)
    if user is None:
        raise RuntimeError("没有可到期的调岗人员")
    from app.models import UserMapping

    mapping = db.scalar(
        select(UserMapping).where(UserMapping.user_id == user.id, UserMapping.deleted == 0)
    )
    if mapping is None or mapping.buffer_until is None:
        raise RuntimeError("没有待到期的调岗缓冲")
    expire_transfer_buffers(db, mapping.buffer_until + timedelta(seconds=1))


def deliver(phase: str) -> dict:
    if phase not in EVENT_IDS and phase not in ("fixtures", "expire-buffer"):
        raise SystemExit(f"unknown phase {phase}")
    db = SessionLocal()
    try:
        ensure_s1_fixtures(db)
        if phase == "fixtures":
            db.commit()
            return {"phase": phase}
        if phase == "expire-buffer":
            expire_buffer(db)
        elif phase == "hire":
            reset_s1_subject(db)
            admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
            if admin is not None:
                reset_pool_account(admin.id)
            db.flush()
            _post(
                db,
                {
                    "eventType": "hire",
                    "dingtalkEventId": EVENT_IDS["hire"],
                    "unionId": "union-e2e-s1",
                    "payloadJson": {
                        "dingtalkUserId": DING_ID,
                        "nickname": NICKNAME,
                        "mobile": MOBILE,
                        "dingtalkPosition": POSITION,
                        "deptIds": [DEPT_CONTENT],
                        "deptNames": ["内容部"],
                        "afterDept": "内容部",
                    },
                },
            )
            user = _subject(db)
            if user is None:
                raise RuntimeError("入职未写入本地用户")
            _pin_login(db, user)
        elif phase == "transfer":
            _post(
                db,
                {
                    "eventType": "transfer",
                    "dingtalkEventId": EVENT_IDS["transfer"],
                    "unionId": "union-e2e-s1",
                    "beforeDept": "内容部",
                    "payloadJson": {
                        "dingtalkUserId": DING_ID,
                        "nickname": NICKNAME,
                        "dingtalkPosition": NEXT_POSITION,
                        "deptIds": [DEPT_LIVE],
                        "deptNames": ["直播部"],
                        "beforeDept": "内容部",
                        "afterDept": "直播部",
                    },
                },
            )
        else:
            _post(
                db,
                {
                    "eventType": "resign",
                    "dingtalkEventId": EVENT_IDS["resign"],
                    "unionId": "union-e2e-s1",
                    "payloadJson": {"dingtalkUserId": DING_ID},
                },
            )
        user = _subject(db)
        db.commit()
        return {
            "phase": phase,
            "username": user.username if user else "",
            "nickname": user.nickname if user else "",
            "userId": user.id if user else None,
            "status": user.status if user else "",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "fixtures"
    print(json.dumps(deliver(phase), ensure_ascii=False))


if __name__ == "__main__":
    main()
