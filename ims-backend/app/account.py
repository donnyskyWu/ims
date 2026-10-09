from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_name, utcnow
from app.corp import (
    check_assigned,
    check_enum,
    check_realname,
    count_of,
    ops_db,
    page_args,
    paged,
    realname_masked,
    tenant_of,
    user_names,
    visible,
)
from app.models import User
from app.ops_models import CollectorAccountBind, Company, IpGroup, Phone, PlatformAccount, Realname, SimCard

router = APIRouter()

CORP_PLATFORMS = frozenset(
    {"WECHAT_OFFICIAL", "WECHAT_CHANNELS", "DOUYIN", "KUAISHOU", "XIAOHONGSHU"}
)
COLLECT_PLATFORMS = frozenset({"DOUYIN", "KUAISHOU", "WECHAT_OFFICIAL", "WECHAT_CHANNELS", "XIAOHONGSHU"})


def account_visible(row: PlatformAccount | None, actor: User) -> bool:
    return visible(row, actor)


def scope_ip_groups(request: Request) -> list[int] | None:
    scope = getattr(request.state, "scope", None)
    if scope is None or scope.kind != "IP_GROUP":
        return None
    ids = getattr(scope, "ip_group_ids", None) or []
    if not ids:
        values = getattr(request.state, "scope_ip_group_ids", None)
        if values:
            return values
    return ids


def load_scope_ip_groups(db: Session, request: Request, actor: User) -> None:
    scope = getattr(request.state, "scope", None)
    if scope is None or scope.kind != "IP_GROUP":
        return
    from app.models import UserScope

    rows = db.scalars(
        select(UserScope.scope_value).where(
            UserScope.user_id == actor.id,
            UserScope.deleted == 0,
            UserScope.scope_type == "IP_GROUP",
            UserScope.tenant_id == (actor.tenant_id or 0),
        )
    ).all()
    scope.ip_group_ids = sorted({int(row) for row in rows if str(row).isdigit()})


def bind_summary(row: PlatformAccount, bind: CollectorAccountBind | None) -> str:
    if row.platform_type not in COLLECT_PLATFORMS:
        return "—"
    if bind and bind.conn_status == "COOKIE_EXPIRED":
        return "Cookie 已失效"
    if bind and bind.conn_status == "ENGINE_UNAVAILABLE":
        return "浏览器引擎不可用"
    if not row.cookie_enc:
        if bind and bind.bind_status == "BOUND" and bind.conn_status == "FAILED":
            return "Cookie 失效"
        if bind and bind.bind_status == "BOUND":
            return "已绑定"
        return "未绑定"
    if bind is None or bind.bind_status != "BOUND":
        return "未绑定"
    if bind.conn_status == "FAILED":
        return "连接失败"
    return "已绑定"


def ip_group_names(ops: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = ops.scalars(select(IpGroup).where(IpGroup.id.in_(ids), IpGroup.deleted == 0)).all()
    return {row.id: row.group_name for row in rows}


def company_names(ops: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = ops.scalars(select(Company).where(Company.id.in_(ids), Company.deleted == 0)).all()
    return {row.id: row.company_name for row in rows}


def list_vo(
    row: PlatformAccount,
    groups: dict[int, str],
    companies: dict[int, str],
    persons: dict[int, str],
    holders: dict[int, str],
    bind: CollectorAccountBind | None,
) -> dict:
    return {
        "id": row.id,
        "accountNo": row.account_no or str(row.id),
        "nickname": row.account_name,
        "platformType": row.platform_type,
        "ipGroupName": groups.get(row.ip_group_id or 0, ""),
        "realNameMasked": persons.get(row.realname_id or 0, ""),
        "companyName": companies.get(row.company_id or 0, ""),
        "holderUserId": row.holder_user_id,
        "holderUserName": holders.get(row.holder_user_id or 0, ""),
        "status": row.status,
        "collectBindSummary": bind_summary(row, bind),
    }


def _credential_mask(enc: str) -> str:
    from app.internal_collect import credential_mask

    return credential_mask(enc)


def _health_label(bind: CollectorAccountBind | None) -> str:
    from app.internal_collect import health_label

    return health_label(bind)


def detail_vo(
    row: PlatformAccount,
    groups: dict[int, str],
    companies: dict[int, str],
    persons: dict[int, str],
    holders: dict[int, str],
    bind: CollectorAccountBind | None,
) -> dict:
    data = list_vo(row, groups, companies, persons, holders, bind)
    data.update(
        {
            "platformAccountId": row.platform_account_id,
            "ipGroupId": row.ip_group_id,
            "companyId": row.company_id,
            "realnameId": row.realname_id,
            "phoneId": row.phone_id,
            "simCardId": row.sim_card_id,
            "holderUserId": row.holder_user_id,
            "authorUserId": row.author_user_id,
            "hasCookie": bool(row.cookie_enc),
            "credentialRef": row.credential_ref or "",
            "credentialMask": _credential_mask(row.cookie_enc),
            "healthLabel": _health_label(bind),
            "collectBindSummary": bind_summary(row, bind),
        }
    )
    return data


def bind_vo(bind: CollectorAccountBind | None) -> dict | None:
    if bind is None or bind.deleted:
        return None
    return {
        "collectorAccountId": bind.collector_account_id,
        "bindStatus": bind.bind_status,
        "connStatus": bind.conn_status or "",
        "lastProbeAt": bind.last_probe_at or "",
    }


def binds_map(ops: Session, account_ids: list[int]) -> dict[int, CollectorAccountBind]:
    if not account_ids:
        return {}
    rows = ops.scalars(
        select(CollectorAccountBind).where(
            CollectorAccountBind.deleted == 0,
            CollectorAccountBind.oa_account_id.in_(account_ids),
        )
    ).all()
    return {row.oa_account_id: row for row in rows}


def check_platform(platform_type: str | None):
    if not platform_type:
        return fail(1001, "platformType 必填")
    if platform_type not in CORP_PLATFORMS:
        return fail(1503, "字典枚举非法")
    return None


def check_company(ops: Session, actor: User, company_id: int | None, required: bool):
    if not company_id:
        if required:
            return fail(1001, "公司必填")
        return None
    row = ops.get(Company, company_id)
    if row is None or row.deleted:
        return fail(1500, "公司不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1501, "公司已停用")
    return None


def check_ip_group(ops: Session, actor: User, group_id: int | None, required: bool):
    if not group_id:
        if required:
            return fail(1001, "IP 组必填")
        return None
    row = ops.get(IpGroup, group_id)
    if row is None or row.deleted:
        return fail(1500, "IP 组不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1501, "IP 组已停用")
    return None


def check_phone(ops: Session, actor: User, phone_id: int | None):
    if not phone_id:
        return None
    row = ops.get(Phone, phone_id)
    if row is None or row.deleted:
        return fail(1500, "手机不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.status not in {"IN_USE", "IDLE"}:
        return fail(1501, "手机已停用")
    return None


def check_sim(ops: Session, actor: User, sim_id: int | None):
    if not sim_id:
        return None
    row = ops.get(SimCard, sim_id)
    if row is None or row.deleted:
        return fail(1500, "手机卡不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.status not in {"IN_USE", "IDLE"}:
        return fail(1501, "手机卡已停用")
    return None


class PlatformAccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int | None = None
    platformType: str | None = None
    accountName: str | None = None
    platformAccountId: str | None = None
    ipGroupId: int | None = None
    companyId: int | None = None
    realnameId: int | None = None
    phoneId: int | None = None
    simCardId: int | None = None
    holderUserId: int | None = None
    status: str | None = None
    cookie: str | None = None


def validate_account_body(
    body: PlatformAccountBody,
    db: Session,
    ops: Session,
    actor: User,
    current_id: int | None,
    creating: bool,
    fixed_platform: str | None = None,
):
    if body.id is not None and current_id is not None and body.id != current_id:
        return fail(1211, "主键不可修改"), None
    platform = fixed_platform or body.platformType
    for item in (
        check_platform(platform),
        check_enum(db, "dict_account_status", body.status if creating or body.status else None, creating),
        check_company(ops, actor, body.companyId if creating or body.companyId else None, creating),
        check_ip_group(ops, actor, body.ipGroupId if creating or body.ipGroupId else None, creating),
        check_realname(ops, actor, body.realnameId),
        check_phone(ops, actor, body.phoneId),
        check_sim(ops, actor, body.simCardId),
        check_assigned(db, actor, body.holderUserId if creating or body.holderUserId else None)
        if creating or body.holderUserId
        else None,
    ):
        if item is not None:
            return item, None
    name = (body.accountName or "").strip()
    if creating and not name:
        return fail(1001, "昵称必填"), None
    return None, {"platform": platform, "name": name}


def apply_account(row: PlatformAccount, body: PlatformAccountBody, prepared: dict, creating: bool) -> None:
    if creating:
        row.platform_type = prepared["platform"]
    if prepared["name"]:
        row.account_name = prepared["name"]
    if body.platformAccountId is not None:
        row.platform_account_id = body.platformAccountId
    if body.ipGroupId is not None:
        row.ip_group_id = body.ipGroupId
    if body.companyId is not None:
        row.company_id = body.companyId
    if body.realnameId is not None:
        row.realname_id = body.realnameId or None
    if body.phoneId is not None:
        row.phone_id = body.phoneId or None
    if body.simCardId is not None:
        row.sim_card_id = body.simCardId or None
    if body.holderUserId is not None:
        row.holder_user_id = body.holderUserId
    if body.status is not None:
        row.status = body.status
    if body.cookie is not None:
        from app.crypto import encrypt_text

        row.cookie_enc = encrypt_text(body.cookie) if body.cookie else ""
    row.updated_at = utcnow()


def enrich_and_return(row: PlatformAccount, db: Session, ops: Session, bind: CollectorAccountBind | None = None):
    if bind is None:
        bind = ops.scalar(
            select(CollectorAccountBind).where(
                CollectorAccountBind.oa_account_id == row.id,
                CollectorAccountBind.deleted == 0,
            )
        )
    groups = ip_group_names(ops, {row.ip_group_id} if row.ip_group_id else set())
    companies = company_names(ops, {row.company_id} if row.company_id else set())
    persons = realname_masked(ops, {row.realname_id} if row.realname_id else set())
    holders = user_names(db, {row.holder_user_id} if row.holder_user_id else set())
    data = detail_vo(row, groups, companies, persons, holders, bind)
    from app.internal_collect import follower_public, video_snapshot_public

    data.update(follower_public(ops, row))
    data.update(video_snapshot_public(ops, row))
    return data


@router.get("/corp/account/page")
def account_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    platformType: str = "",
    keyword: str = "",
    ipGroupId: int | None = None,
    companyId: int | None = None,
    status: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    platform_error = check_platform(platformType)
    if platform_error:
        return platform_error
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(PlatformAccount).where(
        PlatformAccount.deleted == 0,
        PlatformAccount.tenant_id == tenant_of(actor),
        PlatformAccount.platform_type == platformType,
    )
    scoped_groups = scope_ip_groups(request)
    if scoped_groups is not None:
        if not scoped_groups:
            return paged([], 0, page_no, size)
        stmt = stmt.where(PlatformAccount.ip_group_id.in_(scoped_groups))
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(PlatformAccount.account_no.like(like), PlatformAccount.account_name.like(like)))
    if ipGroupId:
        stmt = stmt.where(PlatformAccount.ip_group_id == ipGroupId)
    if companyId:
        stmt = stmt.where(PlatformAccount.company_id == companyId)
    if status:
        stmt = stmt.where(PlatformAccount.status == status)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(PlatformAccount.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    bind_map = binds_map(ops, [row.id for row in rows])
    groups = ip_group_names(ops, {row.ip_group_id for row in rows if row.ip_group_id})
    companies = company_names(ops, {row.company_id for row in rows if row.company_id})
    persons = realname_masked(ops, {row.realname_id for row in rows if row.realname_id})
    holders = user_names(db, {row.holder_user_id for row in rows if row.holder_user_id})
    return paged(
        [list_vo(row, groups, companies, persons, holders, bind_map.get(row.id)) for row in rows],
        total,
        page_no,
        size,
    )


@router.get("/corp/account/{account_id}")
def account_detail(
    account_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return fail(1504, "资源不可用")
    scoped_groups = scope_ip_groups(request)
    if scoped_groups is not None and (row.ip_group_id or 0) not in scoped_groups:
        return fail(1504, "资源不可用")
    return ok(enrich_and_return(row, db, ops))


@router.get("/corp/account/{account_id}/collector-bind")
def collector_bind_get(
    account_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return fail(1504, "资源不可用")
    bind = ops.scalar(
        select(CollectorAccountBind).where(
            CollectorAccountBind.oa_account_id == account_id,
            CollectorAccountBind.deleted == 0,
        )
    )
    return ok(bind_vo(bind))


class CollectorBindBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reason: str | None = None


@router.post("/corp/account/{account_id}/collector-bind")
def collector_bind_import(
    account_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return fail(1504, "资源不可用")
    if row.platform_type == "KUAISHOU":
        from app.kuaishou_collect import import_kuaishou_bind

        return import_kuaishou_bind(ops, row, actor)
    if row.platform_type == "DOUYIN":
        from app.douyin_collect import import_douyin_bind, is_internal_account

        if is_internal_account(row):
            return import_douyin_bind(ops, row, actor)
    if not row.cookie_enc:
        return fail(1001, "凭证未配置")
    bind = ops.scalar(
        select(CollectorAccountBind).where(
            CollectorAccountBind.oa_account_id == account_id,
            CollectorAccountBind.deleted == 0,
        )
    )
    stamp = utcnow().isoformat(sep=" ", timespec="seconds")
    collector_id = f"acc_{row.platform_type.lower()}_{account_id}"
    if bind is None:
        bind = CollectorAccountBind(
            oa_account_id=account_id,
            tenant_id=tenant_of(actor),
            deleted=0,
            created_at=utcnow(),
        )
        ops.add(bind)
    bind.collector_account_id = collector_id
    bind.bind_status = "BOUND"
    bind.conn_status = "SUCCESS"
    bind.last_probe_at = stamp
    bind.updated_at = utcnow()
    return ok(bind_vo(bind))


@router.post("/corp/account/{account_id}/collector-bind/test-connection")
def collector_bind_test(
    account_id: int,
    request: Request,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    load_scope_ip_groups(db, request, actor)
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return fail(1504, "资源不可用")
    bind = ops.scalar(
        select(CollectorAccountBind).where(
            CollectorAccountBind.oa_account_id == account_id,
            CollectorAccountBind.deleted == 0,
        )
    )
    if row.platform_type == "KUAISHOU":
        from app.kuaishou_collect import probe_kuaishou

        return probe_kuaishou(ops, row)
    if row.platform_type == "DOUYIN":
        from app.douyin_collect import is_internal_account, probe_douyin

        if is_internal_account(row):
            return probe_douyin(ops, row)
    if bind is None or bind.bind_status != "BOUND":
        return fail(1001, "未绑定 Collector")
    bind.conn_status = "SUCCESS" if row.cookie_enc else "FAILED"
    bind.last_probe_at = utcnow().isoformat(sep=" ", timespec="seconds")
    bind.updated_at = utcnow()
    if bind.conn_status == "FAILED":
        return fail(1001, "探活失败")
    return ok(bind_vo(bind))


@router.post("/master/platform-account")
def platform_account_create(
    body: PlatformAccountBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    error, prepared = validate_account_body(body, db, ops, actor, None, True)
    if error:
        return error
    row = PlatformAccount(tenant_id=tenant_of(actor), deleted=0, status="IN_USE", created_at=utcnow())
    ops.add(row)
    ops.flush()
    row.account_no = f"ACCT-{utcnow().strftime('%Y')}-{row.id:04d}"
    apply_account(row, body, prepared, True)
    return ok(enrich_and_return(row, db, ops))


@router.put("/master/platform-account/{account_id}")
def platform_account_update(
    account_id: int,
    body: PlatformAccountBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(PlatformAccount, account_id)
    if not account_visible(row, actor):
        return fail(1504, "资源不可用")
    error, prepared = validate_account_body(body, db, ops, actor, account_id, False, row.platform_type)
    if error:
        return error
    apply_account(row, body, prepared, False)
    return ok(enrich_and_return(row, db, ops))
