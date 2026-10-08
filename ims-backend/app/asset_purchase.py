"""采购 CSV 批量入台账（#68 · E2E-S5-01）。

合法行写入 ims_asset_ledger（待审核）。非法行按文件行号与字段返回。
已成功的行不因后续行失败而回滚（G7 例外：部分成功）。
"""

import csv
import json
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import DATE_RE, dict_enabled, tenant_of
from app.models import AssetLedger, AssetPurchaseBatch, User

router = APIRouter()

MAX_BYTES = 1_000_000
MAX_ROWS = 200
HEADER_ALIAS = {
    "assetcode": "assetCode",
    "资产编号": "assetCode",
    "编号": "assetCode",
    "assetname": "assetName",
    "资产名称": "assetName",
    "名称": "assetName",
    "assettype": "assetType",
    "资产类型": "assetType",
    "类型": "assetType",
    "spec": "spec",
    "规格": "spec",
    "purchasedate": "purchaseDate",
    "采购日期": "purchaseDate",
}
FIELD_LABEL = {
    "assetCode": "资产编号",
    "assetName": "资产名称",
    "assetType": "资产类型",
    "spec": "规格",
    "purchaseDate": "采购日期",
}


def _decode(raw: bytes) -> str | None:
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _header_index(header: list[str]) -> dict[str, int] | None:
    found: dict[str, int] = {}
    for index, cell in enumerate(header):
        key = HEADER_ALIAS.get(cell.strip().lstrip("\ufeff"))
        if key and key not in found:
            found[key] = index
    if "assetName" not in found or "purchaseDate" not in found:
        return None
    return found


def _cell(row: list[str], index: dict[str, int], field: str) -> str:
    pos = index.get(field)
    if pos is None or pos >= len(row):
        return ""
    return (row[pos] or "").strip()


def _row_error(row_no: int, field: str, code: int, message: str, asset_code: str) -> dict:
    return {
        "rowNo": row_no,
        "field": field,
        "fieldLabel": FIELD_LABEL.get(field, field),
        "code": code,
        "message": message,
        "assetCode": asset_code,
    }


def _date_error(value: str) -> str | None:
    if not value:
        return "采购日期必填"
    if not DATE_RE.match(value):
        return "日期格式应为 yyyy-MM-dd"
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return "日期格式应为 yyyy-MM-dd"
    return None


def _validate(db: Session, actor: User, code: str, name: str, asset_type: str, spec: str, purchase_date: str, seen: set[str]):
    from app.asset_ledger import _code_taken

    if not name:
        return _row_error(0, "assetName", 1001, "资产名称必填", code)
    if len(name) > 128:
        return _row_error(0, "assetName", 1001, "资产名称过长", code)
    if not dict_enabled(db, "dict_asset_type", asset_type):
        return _row_error(0, "assetType", 1503, "字典枚举非法", code)
    if len(spec) > 128:
        return _row_error(0, "spec", 1001, "规格过长", code)
    date_msg = _date_error(purchase_date)
    if date_msg:
        return _row_error(0, "purchaseDate", 1001, date_msg, code)
    if len(code) > 64:
        return _row_error(0, "assetCode", 1001, "资产编号过长", code)
    if code and (code in seen or _code_taken(db, actor, code)):
        return _row_error(0, "assetCode", 1012, "资产编号已存在", code)
    return None


def _insert(db: Session, actor: User, batch_no: str, code: str, name: str, asset_type: str, spec: str, purchase_date: str):
    from app.asset_ledger import _add_event

    now = utcnow()
    row = AssetLedger(
        asset_code=code,
        asset_name=name,
        asset_type=asset_type,
        spec=spec,
        status="PENDING_REVIEW",
        owner_user_id=None,
        purchase_date=purchase_date,
        purchase_batch_no=batch_no,
        subject_id=0,
        creator=actor.id,
        updater=actor.id,
        deleted=0,
        tenant_id=tenant_of(actor),
        created_at=now,
        updated_at=now,
    )
    with db.begin_nested():
        db.add(row)
        db.flush()
        _add_event(db, row, actor, "REGISTER", "", "PENDING_REVIEW", "采购入台账", None)
        db.flush()
    return row


@router.post("/asset/ledger/import")
def ledger_import(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if file is None:
        return fail(1001, "请上传 CSV 文件")
    raw = file.file.read(MAX_BYTES + 1)
    if not raw:
        return fail(1001, "文件为空")
    if len(raw) > MAX_BYTES:
        return fail(1001, "文件过大")
    text = _decode(raw)
    if text is None:
        return fail(1001, "文件编码无法识别")
    rows = list(csv.reader(StringIO(text)))
    header_at = None
    for index, row in enumerate(rows):
        if any(cell.strip() for cell in row):
            header_at = index
            break
    if header_at is None:
        return fail(1001, "文件为空")
    columns = _header_index(rows[header_at])
    if columns is None:
        return fail(1001, "缺少列：资产名称、采购日期")
    data_rows = []
    for offset, row in enumerate(rows[header_at + 1 :], start=header_at + 2):
        if not any(cell.strip() for cell in row):
            continue
        data_rows.append((offset, row))
    if not data_rows:
        return fail(1001, "没有可导入的数据行")
    if len(data_rows) > MAX_ROWS:
        return fail(1001, f"单次最多 {MAX_ROWS} 行")

    batch_no = "PB" + utcnow().strftime("%Y%m%d%H%M%S%f")
    seen: set[str] = set()
    errors: list[dict] = []
    imported: list[dict] = []
    for row_no, row in data_rows:
        code = _cell(row, columns, "assetCode")
        name = _cell(row, columns, "assetName")
        asset_type = _cell(row, columns, "assetType") or "OFFICE"
        spec = _cell(row, columns, "spec")
        purchase_date = _cell(row, columns, "purchaseDate")
        problem = _validate(db, actor, code, name, asset_type, spec, purchase_date, seen)
        if problem:
            problem["rowNo"] = row_no
            errors.append(problem)
            continue
        if not code:
            code = f"AS{utcnow().strftime('%Y%m%d%H%M%S%f')}{row_no:04d}"
            if len(code) > 64 or code in seen:
                errors.append(_row_error(row_no, "assetCode", 1012, "资产编号已存在", code))
                continue
        try:
            saved = _insert(db, actor, batch_no, code, name, asset_type, spec, purchase_date)
        except IntegrityError:
            errors.append(_row_error(row_no, "assetCode", 1012, "资产编号已存在", code))
            continue
        seen.add(code)
        imported.append(
            {
                "id": saved.id,
                "assetCode": saved.asset_code,
                "assetName": saved.asset_name,
                "status": saved.status,
                "purchaseDate": saved.purchase_date,
                "purchaseBatchNo": batch_no,
            }
        )

    partial = bool(imported) and bool(errors)
    db.add(
        AssetPurchaseBatch(
            batch_no=batch_no,
            file_name=(file.filename or "")[:128],
            total_count=len(data_rows),
            success_count=len(imported),
            fail_count=len(errors),
            partial=1 if partial else 0,
            error_detail=json.dumps(errors, ensure_ascii=False),
            creator=actor.id,
            deleted=0,
            tenant_id=tenant_of(actor),
            created_at=utcnow(),
        )
    )
    db.flush()
    return ok(
        {
            "batchNo": batch_no,
            "fileName": (file.filename or "")[:128],
            "total": len(data_rows),
            "successCount": len(imported),
            "failCount": len(errors),
            "partial": partial,
            "errors": errors,
            "imported": imported,
        }
    )
