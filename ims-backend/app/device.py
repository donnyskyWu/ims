from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_mobile, utcnow
from app.crypto import decrypt_text, encrypt_text, sha256_hex
from app.corp import PHONE_RE, check_date, check_enum, count_of, ops_db, page_args, paged, tenant_of, user_names, visible
from app.models import User
from app.ops_models import Phone

router = APIRouter()


def empty_page(pageNo: int = 1, pageSize: int = 10, actor: User = Depends(current_user)):
    page_no, size = page_args(pageNo, pageSize)
    return paged([], 0, page_no, size)


@router.get("/corp/device/office/page")
def office_page(pageNo: int = 1, pageSize: int = 10, actor: User = Depends(current_user)):
    return empty_page(pageNo, pageSize, actor)


@router.get("/corp/device/live/page")
def live_page(pageNo: int = 1, pageSize: int = 10, actor: User = Depends(current_user)):
    return empty_page(pageNo, pageSize, actor)


class PhoneBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    phoneNumber: str | None = None
    phoneCode: str | None = None
    phoneModel: str | None = None
    keeperId: int | None = None
    wechatBound: str | None = None
    status: str | None = None
    deviceNumber: str | None = None
    phoneType: str | None = None
    isAochuang: str | None = None
    handlerName: str | None = None
    purchaseBatch: str | None = None
    purchaseDate: str | None = None
    purchaseTime: str | None = None
    settingsScreenshotKey: str | None = None
    frontImageKey: str | None = None
    backImageKey: str | None = None
    id: int | None = None


def phone_vo(row: Phone, names: dict[int, str]) -> dict:
    number = decrypt_text(row.phone_enc) if row.phone_enc else ""
    return {
        "id": row.id,
        "phoneNumber": mask_mobile(number),
        "phoneCode": row.phone_code,
        "phoneModel": row.phone_model,
        "keeperId": row.keeper_id,
        "keeperName": names.get(row.keeper_id or 0, ""),
        "wechatBound": row.wechat_bound,
        "status": row.status,
        "deviceNumber": row.device_number,
        "phoneType": row.phone_type,
        "isAochuang": row.is_aochuang,
        "handlerName": row.handler_name,
        "purchaseBatch": row.purchase_batch,
        "purchaseDate": row.purchase_date,
        "purchaseTime": row.purchase_time,
        "settingsScreenshotKey": row.settings_screenshot_key,
        "frontImageKey": row.front_image_key,
        "backImageKey": row.back_image_key,
        "linkedAccounts": [],
    }


def check_keeper(db: Session, actor: User, keeper_id: int | None):
    if not keeper_id:
        return fail(1001, "保管人必填")
    user = db.get(User, keeper_id)
    if user is None or user.deleted:
        return fail(1500, "保管人不存在")
    if (user.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if user.status != "ENABLED":
        return fail(1501, "保管人已停用")
    return None


def number_taken(ops: Session, actor: User, digest: str, current_id: int | None) -> bool:
    stmt = select(Phone.id).where(
        Phone.deleted == 0,
        Phone.tenant_id == tenant_of(actor),
        Phone.phone_sha256 == digest,
    )
    if current_id:
        stmt = stmt.where(Phone.id != current_id)
    return ops.scalar(stmt) is not None


def validate_phone(body: PhoneBody, db: Session, ops: Session, actor: User, current_id: int | None, creating: bool):
    if body.id is not None and current_id is not None and body.id != current_id:
        return fail(1211, "主键不可修改"), None
    number = (body.phoneNumber or "").strip()
    if creating and not number:
        return fail(1001, "手机号必填"), None
    if number and not PHONE_RE.match(number):
        return fail(1001, "手机号须为 11 位"), None
    digest = sha256_hex(number) if number else None
    if digest and number_taken(ops, actor, digest, current_id):
        return fail(1001, "手机号已存在"), None
    for item in (
        check_enum(db, "dict_phone_status", body.status, creating),
        check_enum(db, "dict_phone_type", body.phoneType, False),
        check_enum(db, "dict_yes_no", body.isAochuang, False),
        check_keeper(db, actor, body.keeperId if creating or body.keeperId else None) if creating or body.keeperId else None,
        check_date(body.purchaseDate),
    ):
        if item is not None:
            return item, None
    return None, {"number": number, "digest": digest}


def apply_phone(row: Phone, body: PhoneBody, prepared: dict) -> None:
    if prepared["number"]:
        row.phone_enc = encrypt_text(prepared["number"])
        row.phone_sha256 = prepared["digest"]
    if body.phoneCode is not None:
        row.phone_code = body.phoneCode
    if body.phoneModel is not None:
        row.phone_model = body.phoneModel
    if body.keeperId:
        row.keeper_id = body.keeperId
    if body.wechatBound is not None:
        row.wechat_bound = body.wechatBound
    if body.status is not None:
        row.status = body.status
    if body.deviceNumber is not None:
        row.device_number = body.deviceNumber
    if body.phoneType is not None:
        row.phone_type = body.phoneType
    if body.isAochuang is not None:
        row.is_aochuang = body.isAochuang
    if body.handlerName is not None:
        row.handler_name = body.handlerName
    if body.purchaseBatch is not None:
        row.purchase_batch = body.purchaseBatch
    if body.purchaseDate is not None:
        row.purchase_date = body.purchaseDate
    if body.purchaseTime is not None:
        row.purchase_time = body.purchaseTime
    if body.settingsScreenshotKey is not None:
        row.settings_screenshot_key = body.settingsScreenshotKey
    if body.frontImageKey is not None:
        row.front_image_key = body.frontImageKey
    if body.backImageKey is not None:
        row.back_image_key = body.backImageKey
    row.updated_at = utcnow()


def list_phones(
    pageNo: int,
    pageSize: int,
    phoneType: str,
    deviceNumber: str,
    phoneModel: str,
    status: str,
    db: Session,
    ops: Session,
    actor: User,
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(Phone).where(Phone.deleted == 0, Phone.tenant_id == tenant_of(actor))
    if phoneType:
        stmt = stmt.where(Phone.phone_type == phoneType)
    if deviceNumber:
        stmt = stmt.where(Phone.device_number.like(f"%{deviceNumber}%"))
    if phoneModel:
        stmt = stmt.where(Phone.phone_model.like(f"%{phoneModel}%"))
    if status:
        stmt = stmt.where(Phone.status == status)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(Phone.id).offset((page_no - 1) * size).limit(size)).all()
    names = user_names(db, {row.keeper_id for row in rows if row.keeper_id})
    return paged([phone_vo(row, names) for row in rows], total, page_no, size)


@router.get("/master/phone/page")
@router.get("/corp/device/phone/page")
def phone_page(
    pageNo: int = 1,
    pageSize: int = 10,
    phoneType: str = "",
    deviceNumber: str = "",
    phoneModel: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    return list_phones(pageNo, pageSize, phoneType, deviceNumber, phoneModel, status, db, ops, actor)


@router.get("/master/phone/{phone_id}")
@router.get("/corp/device/phone/{phone_id}")
def phone_detail(
    phone_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(Phone, phone_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    names = user_names(db, {row.keeper_id} if row.keeper_id else set())
    return ok(phone_vo(row, names))


@router.post("/master/phone")
def phone_create(
    body: PhoneBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    error, prepared = validate_phone(body, db, ops, actor, None, True)
    if error:
        return error
    row = Phone(tenant_id=tenant_of(actor), deleted=0, created_at=utcnow())
    apply_phone(row, body, prepared)
    ops.add(row)
    ops.flush()
    names = user_names(db, {row.keeper_id} if row.keeper_id else set())
    return ok(phone_vo(row, names))


@router.put("/master/phone/{phone_id}")
def phone_update(
    phone_id: int,
    body: PhoneBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(Phone, phone_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    error, prepared = validate_phone(body, db, ops, actor, phone_id, False)
    if error:
        return error
    apply_phone(row, body, prepared)
    names = user_names(db, {row.keeper_id} if row.keeper_id else set())
    return ok(phone_vo(row, names))
