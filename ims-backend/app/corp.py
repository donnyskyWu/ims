import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_cert_no, mask_id_card, mask_mobile, mask_name, utcnow
from app.crypto import decrypt_text, encrypt_text, sha256_hex
from app.models import CertArchive, DictData, User
from app.ops_db import ops_session
from app.ops_models import Company, Phone, PlatformAccount, Realname, SimCard

router = APIRouter()

PHONE_RE = re.compile(r"^1\d{10}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
USABLE_PHONE = {"IN_USE", "IDLE"}


def ops_db():
    db = ops_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def page_args(page_no: int, page_size: int) -> tuple[int, int]:
    number = page_no if page_no > 0 else 1
    size = page_size if 0 < page_size <= 100 else 10
    return number, size


def paged(rows: list, total: int, page_no: int, size: int):
    return ok({"list": rows, "total": total, "pageNo": page_no, "pageSize": size})


def tenant_of(actor: User) -> int:
    return actor.tenant_id or 0


def visible(row, actor: User) -> bool:
    if row is None or row.deleted:
        return False
    return (row.tenant_id or 0) == tenant_of(actor)


def count_of(db: Session, stmt) -> int:
    return int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def dict_enabled(db: Session, dict_type: str, value: str) -> bool:
    found = db.scalar(
        select(DictData.id).where(
            DictData.dict_type == dict_type,
            DictData.dict_value == value,
            DictData.status == "ENABLED",
            DictData.deleted == 0,
        )
    )
    return found is not None


def check_enum(db: Session, dict_type: str, value: str | None, required: bool):
    if value is None or value == "":
        if required:
            return fail(1001, "必填项缺失")
        return None
    if not dict_enabled(db, dict_type, value):
        return fail(1503, "字典枚举非法")
    return None


def check_date(value: str | None, required: bool = False):
    if value is None or value == "":
        if required:
            return fail(1001, "必填项缺失")
        return None
    if not DATE_RE.match(value):
        return fail(1001, "日期格式应为 yyyy-MM-dd")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return fail(1001, "日期格式应为 yyyy-MM-dd")
    return None


def user_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    rows = db.scalars(select(User).where(User.id.in_(user_ids), User.deleted == 0)).all()
    return {row.id: row.nickname or row.username for row in rows}


def realname_masked(ops: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = ops.scalars(select(Realname).where(Realname.id.in_(ids), Realname.deleted == 0)).all()
    return {row.id: mask_name(row.real_name) for row in rows}


def company_vo(row: Company) -> dict:
    capacity = row.mp_capacity_standard or 0
    registered = 0
    history = []
    try:
        parsed = json.loads(row.expansion_history or "[]")
        if isinstance(parsed, list):
            history = parsed
    except json.JSONDecodeError:
        history = []
    return {
        "id": row.id,
        "companyName": row.company_name,
        "creditCode": row.credit_code,
        "industry": row.industry,
        "address": row.address,
        "legalName": row.legal_name,
        "mpCapacityStandard": capacity,
        "mpRegisteredCount": registered,
        "mpRemaining": capacity - registered,
        "expansionHistory": history,
        "status": row.status,
    }


def realname_vo(row: Realname) -> dict:
    return {
        "id": row.id,
        "realName": mask_name(row.real_name),
        "idType": row.id_type,
        "idCardMasked": mask_id_card(decrypt_text(row.id_card_enc)),
        "phoneMasked": mask_mobile(decrypt_text(row.phone_enc)),
        "wechat": row.wechat,
        "gender": row.gender,
        "status": row.status,
        "companyId": row.company_id,
    }


def sim_linked(ops: Session, actor: User, row: SimCard) -> tuple[int, list]:
    stmt = select(PlatformAccount).where(
        PlatformAccount.deleted == 0,
        PlatformAccount.tenant_id == tenant_of(actor),
    )
    if row.phone_id:
        stmt = stmt.where(PlatformAccount.phone_id == row.phone_id)
    else:
        return 0, []
    accounts = ops.scalars(stmt.limit(20)).all()
    items = [
        {
            "accountId": item.id,
            "accountNo": item.account_no,
            "platformType": item.platform_type,
            "nickname": item.account_name,
            "status": item.status,
        }
        for item in accounts
    ]
    return len(items), items


def sim_vo(row: SimCard, names: dict[int, str], persons: dict[int, str], linked: tuple[int, list] | None = None) -> dict:
    number = decrypt_text(row.phone_enc) if row.phone_enc else ""
    return {
        "id": row.id,
        "phoneId": row.phone_id,
        "phoneNumber": mask_mobile(number),
        "isPrimary": row.is_primary,
        "operator": row.operator,
        "assignedUserId": row.assigned_user_id,
        "assignedUserName": names.get(row.assigned_user_id, ""),
        "iccid": "****" if row.iccid_enc else "",
        "packageName": row.package_name,
        "status": row.status,
        "realnameId": row.realname_id,
        "realNameMasked": persons.get(row.realname_id or 0, ""),
        "activatedAt": row.activated_at,
        "monthlyRent": row.monthly_rent,
        "paymentCycle": row.payment_cycle,
        "nextPaymentDate": row.next_payment_date,
        "totalLinkedAccounts": linked[0] if linked else 0,
        "linkedAccounts": linked[1] if linked else [],
    }


def cert_vo(row: CertArchive) -> dict:
    plain = decrypt_text(row.cert_no_enc) if row.cert_no_enc else ""
    return {
        "id": row.id,
        "holderUserId": row.holder_user_id,
        "holderName": row.holder_name,
        "certType": row.cert_type,
        "certNoMasked": mask_cert_no(plain),
        "certNoHashPrefix": (row.cert_no_hash or "")[:16],
        "issueDate": row.issue_date,
        "expireDate": row.expire_date,
        "status": row.status,
        "uploadedBy": row.uploaded_by,
        "createdAt": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else "",
    }


class SimBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    phoneId: int | None = None
    phoneNumber: str | None = None
    isPrimary: str | None = None
    operator: str | None = None
    assignedUserId: int | None = None
    iccid: str | None = None
    packageName: str | None = None
    status: str | None = None
    realnameId: int | None = None
    activatedAt: str | None = None
    monthlyRent: float | int | str | None = None
    paymentCycle: str | None = None
    nextPaymentDate: str | None = None
    id: int | None = None


def check_assigned(db: Session, actor: User, user_id: int | None):
    if not user_id:
        return fail(1001, "归属人必填")
    user = db.get(User, user_id)
    if user is None or user.deleted:
        return fail(1500, "归属人不存在")
    if (user.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if user.status != "ENABLED":
        return fail(1501, "归属人已停用")
    return None


def check_realname(ops: Session, actor: User, realname_id: int | None):
    if not realname_id:
        return None
    row = ops.get(Realname, realname_id)
    if row is None or row.deleted:
        return fail(1500, "实名人不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1501, "实名人已停用")
    return None


def resolve_number(ops: Session, actor: User, phone_id: int | None, phone_number: str | None):
    if phone_id:
        phone = ops.get(Phone, phone_id)
        if phone is None or phone.deleted:
            return fail(1500, "手机不存在"), None
        if (phone.tenant_id or 0) != tenant_of(actor):
            return fail(1504, "资源不可用"), None
        if phone.status not in USABLE_PHONE:
            return fail(1501, "手机已停用"), None
        return None, decrypt_text(phone.phone_enc)
    number = (phone_number or "").strip()
    if not number:
        return fail(1001, "手机号或手机必填"), None
    if not PHONE_RE.match(number):
        return fail(1001, "手机号须为 11 位"), None
    return None, number


def check_rent(value):
    if value is None or value == "":
        return None, ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fail(1001, "月租须为数字"), ""
    if number < 0:
        return fail(1001, "月租不能为负"), ""
    return None, f"{number:.2f}"


def phone_taken(ops: Session, actor: User, digest: str, current_id: int | None) -> bool:
    stmt = select(SimCard.id).where(
        SimCard.deleted == 0,
        SimCard.tenant_id == tenant_of(actor),
        SimCard.phone_sha256 == digest,
    )
    if current_id:
        stmt = stmt.where(SimCard.id != current_id)
    return ops.scalar(stmt) is not None


@router.get("/corp/resource/company/page")
def company_page(
    pageNo: int = 1,
    pageSize: int = 10,
    companyName: str = "",
    creditCode: str = "",
    status: str = "",
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(Company).where(Company.deleted == 0, Company.tenant_id == tenant_of(actor))
    if companyName:
        stmt = stmt.where(Company.company_name.like(f"%{companyName}%"))
    if creditCode:
        stmt = stmt.where(Company.credit_code.like(f"%{creditCode}%"))
    if status:
        stmt = stmt.where(Company.status == status)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(Company.id).offset((page_no - 1) * size).limit(size)).all()
    return paged([company_vo(row) for row in rows], total, page_no, size)


@router.get("/corp/resource/company/{company_id}")
def company_detail(company_id: int, ops: Session = Depends(ops_db), actor: User = Depends(current_user)):
    row = ops.get(Company, company_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    return ok(company_vo(row))


@router.get("/corp/resource/realname/page")
def realname_page(
    pageNo: int = 1,
    pageSize: int = 10,
    realName: str = "",
    status: str = "",
    idType: str = "",
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(Realname).where(Realname.deleted == 0, Realname.tenant_id == tenant_of(actor))
    if realName:
        stmt = stmt.where(Realname.real_name.like(f"%{realName}%"))
    if status:
        stmt = stmt.where(Realname.status == status)
    if idType:
        stmt = stmt.where(Realname.id_type == idType)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(Realname.id).offset((page_no - 1) * size).limit(size)).all()
    return paged([realname_vo(row) for row in rows], total, page_no, size)


@router.get("/corp/resource/realname/{realname_id}")
def realname_detail(realname_id: int, ops: Session = Depends(ops_db), actor: User = Depends(current_user)):
    row = ops.get(Realname, realname_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    data = realname_vo(row)
    data["intermediaries"] = []
    data["linkedAccounts"] = []
    return ok(data)


@router.get("/corp/resource/sim-card/page")
def sim_page(
    pageNo: int = 1,
    pageSize: int = 10,
    phoneNumber: str = "",
    operator: str = "",
    status: str = "",
    realnameId: int | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(SimCard).where(SimCard.deleted == 0, SimCard.tenant_id == tenant_of(actor))
    number = phoneNumber.strip()
    if number:
        if PHONE_RE.match(number):
            stmt = stmt.where(SimCard.phone_sha256 == sha256_hex(number))
        else:
            stmt = stmt.where(SimCard.id < 0)
    if operator:
        stmt = stmt.where(SimCard.operator == operator)
    if status:
        stmt = stmt.where(SimCard.status == status)
    if realnameId:
        stmt = stmt.where(SimCard.realname_id == realnameId)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(SimCard.id).offset((page_no - 1) * size).limit(size)).all()
    names = user_names(db, {row.assigned_user_id for row in rows if row.assigned_user_id})
    persons = realname_masked(ops, {row.realname_id for row in rows if row.realname_id})
    payload = []
    for row in rows:
        payload.append(sim_vo(row, names, persons, sim_linked(ops, actor, row)))
    return paged(payload, total, page_no, size)


@router.get("/corp/resource/sim-card/{sim_id}")
def sim_detail(
    sim_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(SimCard, sim_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    names = user_names(db, {row.assigned_user_id} if row.assigned_user_id else set())
    persons = realname_masked(ops, {row.realname_id} if row.realname_id else set())
    return ok(sim_vo(row, names, persons, sim_linked(ops, actor, row)))


def validate_sim(body: SimBody, db: Session, ops: Session, actor: User, current_id: int | None, creating: bool):
    if body.id is not None and current_id is not None and body.id != current_id:
        return fail(1211, "主键不可修改"), None
    number_error, number = resolve_number(
        ops,
        actor,
        body.phoneId,
        body.phoneNumber if creating or body.phoneNumber else None,
    )
    if creating and number_error:
        return number_error, None
    if not creating and body.phoneId is None and not (body.phoneNumber or "").strip():
        number_error, number = None, None
    elif number_error:
        return number_error, None
    for item in (
        check_enum(db, "dict_yes_no", body.isPrimary, creating),
        check_enum(db, "dict_sim_operator", body.operator, creating),
        check_enum(db, "dict_sim_status", body.status, creating),
        check_enum(db, "dict_payment_cycle", body.paymentCycle, False),
        check_assigned(db, actor, body.assignedUserId if creating or body.assignedUserId else None)
        if creating or body.assignedUserId
        else None,
        check_realname(ops, actor, body.realnameId),
        check_date(body.activatedAt),
        check_date(body.nextPaymentDate),
    ):
        if item is not None:
            return item, None
    rent_error, rent = check_rent(body.monthlyRent)
    if rent_error:
        return rent_error, None
    digest = sha256_hex(number) if number else None
    if digest and phone_taken(ops, actor, digest, current_id):
        return fail(1001, "手机号已存在"), None
    return None, {"number": number, "digest": digest, "rent": rent}


def apply_sim(row: SimCard, body: SimBody, prepared: dict) -> None:
    if prepared["number"]:
        row.phone_enc = encrypt_text(prepared["number"])
        row.phone_sha256 = prepared["digest"]
        row.phone_id = body.phoneId
    if body.isPrimary is not None:
        row.is_primary = body.isPrimary
    if body.operator is not None:
        row.operator = body.operator
    if body.assignedUserId:
        row.assigned_user_id = body.assignedUserId
    if body.iccid is not None:
        row.iccid_enc = encrypt_text(body.iccid) if body.iccid else ""
    if body.packageName is not None:
        row.package_name = body.packageName
    if body.status is not None:
        row.status = body.status
    if body.realnameId is not None:
        row.realname_id = body.realnameId or None
    if body.activatedAt is not None:
        row.activated_at = body.activatedAt
    if body.monthlyRent is not None and body.monthlyRent != "":
        row.monthly_rent = prepared["rent"]
    if body.paymentCycle is not None:
        row.payment_cycle = body.paymentCycle
    if body.nextPaymentDate is not None:
        row.next_payment_date = body.nextPaymentDate
    row.updated_at = utcnow()


@router.post("/corp/resource/sim-card")
def sim_create(
    body: SimBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    error, prepared = validate_sim(body, db, ops, actor, None, True)
    if error:
        return error
    row = SimCard(tenant_id=tenant_of(actor), deleted=0, created_at=utcnow())
    apply_sim(row, body, prepared)
    ops.add(row)
    ops.flush()
    names = user_names(db, {row.assigned_user_id})
    persons = realname_masked(ops, {row.realname_id} if row.realname_id else set())
    return ok(sim_vo(row, names, persons, sim_linked(ops, actor, row)))


@router.put("/corp/resource/sim-card/{sim_id}")
def sim_update(
    sim_id: int,
    body: SimBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(SimCard, sim_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    error, prepared = validate_sim(body, db, ops, actor, sim_id, False)
    if error:
        return error
    apply_sim(row, body, prepared)
    names = user_names(db, {row.assigned_user_id})
    persons = realname_masked(ops, {row.realname_id} if row.realname_id else set())
    return ok(sim_vo(row, names, persons, sim_linked(ops, actor, row)))


def cert_stmt(actor: User, request: Request):
    stmt = select(CertArchive).where(CertArchive.deleted == 0, CertArchive.tenant_id == tenant_of(actor))
    scope = getattr(request.state, "scope", None)
    if scope is not None and scope.kind == "SELF":
        stmt = stmt.where(CertArchive.holder_user_id == actor.id)
    return stmt


@router.get("/corp/resource/certificate/page")
def certificate_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    holderName: str = "",
    certType: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.cert_e2e_seed import ensure_cert_e2e_seed

    ensure_cert_e2e_seed(db, actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = cert_stmt(actor, request)
    if holderName:
        stmt = stmt.where(CertArchive.holder_name.like(f"%{holderName}%"))
    if certType:
        stmt = stmt.where(CertArchive.cert_type == certType)
    if status:
        stmt = stmt.where(CertArchive.status == status)
    total = count_of(db, stmt)
    rows = db.scalars(stmt.order_by(CertArchive.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([cert_vo(row) for row in rows], total, page_no, size)


@router.get("/corp/resource/certificate/{cert_id}/view")
def certificate_view(
    cert_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(CertArchive, cert_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    scope = getattr(request.state, "scope", None)
    if scope is not None and scope.kind == "SELF" and row.holder_user_id != actor.id:
        return fail(1504, "资源不可用")
    from app.cert_view import enforce_view_frequency, record_cert_view

    blocked = enforce_view_frequency(db, actor, row)
    if blocked is not None:
        return blocked
    stamp = utcnow().isoformat(sep=" ", timespec="seconds")
    watermark = f"{actor.username} {actor.nickname or actor.username} {stamp}"
    record_cert_view(db, actor, row, watermark, request)
    return ok(
        {
            "viewLevel": 2,
            "indexInfo": cert_vo(row),
            "watermarkText": watermark,
            "watermark": {"text": watermark, "opacity": 0.15, "position": "center"},
        }
    )
