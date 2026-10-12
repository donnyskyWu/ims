"""camelCase、金额、百分比、主键字符串。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from app.core.clock import format_datetime, parse_input_datetime
from app.core.config import get_settings
from app.core.errors import BizError


def _is_id_key(key: str) -> bool:
    return key == "id" or key.endswith("Id")


def stringify_ids(value: Any) -> Any:
    if not get_settings().id_as_string:
        return value
    if isinstance(value, list):
        return [stringify_ids(item) for item in value]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if _is_id_key(key) and isinstance(item, int) and not isinstance(item, bool):
                out[key] = str(item)
            else:
                out[key] = stringify_ids(item)
        return out
    return value


def parse_api_id(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise BizError(1001, data={"fieldErrors": [{"field": "id", "message": "编号格式不正确"}]})
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise BizError(1001, data={"fieldErrors": [{"field": "id", "message": "编号格式不正确"}]})


def _ser_id(value: int | None):
    if value is None:
        return None
    if get_settings().id_as_string:
        return str(value)
    return value


ApiId = Annotated[int, BeforeValidator(parse_api_id), PlainSerializer(_ser_id, return_type=str)]
ApiIdOptional = Annotated[int | None, BeforeValidator(parse_api_id), PlainSerializer(_ser_id, return_type=str | None)]


def parse_money(value):
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise BizError(1001, data={"fieldErrors": [{"field": "amount", "message": "金额格式不正确"}]}) from exc
    quantized = number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized != number:
        raise BizError(1001, data={"fieldErrors": [{"field": "amount", "message": "金额最多保留两位小数"}]})
    return quantized


def ser_money(value: Decimal | None):
    if value is None:
        return None
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


Money = Annotated[Decimal, BeforeValidator(parse_money), PlainSerializer(ser_money, return_type=str)]
MoneyOptional = Annotated[Decimal | None, BeforeValidator(parse_money), PlainSerializer(ser_money, return_type=str | None)]


def parse_percent(value):
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise BizError(1001, data={"fieldErrors": [{"field": "rate", "message": "百分比格式不正确"}]}) from exc
    return (number / Decimal("100")).quantize(Decimal("0.0001"))


def ser_percent(value: Decimal | None):
    if value is None:
        return None
    shown = (Decimal(value) * Decimal("100")).quantize(Decimal("0.01"))
    if shown == shown.to_integral():
        return int(shown)
    return float(shown)


Percent = Annotated[Decimal | None, BeforeValidator(parse_percent), PlainSerializer(ser_percent)]


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BizError(1001, data={"fieldErrors": [{"field": "bizDate", "message": "日期格式须为年-月-日"}]}) from exc


def ser_date(value: date | None):
    if value is None:
        return None
    return value.strftime("%Y-%m-%d")


ApiDate = Annotated[date | None, BeforeValidator(parse_date), PlainSerializer(ser_date, return_type=str | None)]


def parse_dt(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value
        return parse_input_datetime(value.isoformat())
    try:
        return parse_input_datetime(str(value))
    except ValueError as exc:
        raise BizError(1001, data={"fieldErrors": [{"field": "bizTime", "message": "时间格式不正确"}]}) from exc


def ser_dt(value: datetime | None):
    return format_datetime(value)


ApiDateTime = Annotated[datetime | None, BeforeValidator(parse_dt), PlainSerializer(ser_dt, return_type=str | None)]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=False,
        extra="ignore",
        from_attributes=True,
    )

    def dump(self) -> dict:
        data = self.model_dump(by_alias=True, mode="json")
        return stringify_ids(data)
