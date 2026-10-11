"""绩效考核分档。本模块只用 PerfGradeLevel，不使用 S～D（PerfGrade）。

默认优秀线 85、合格线 60，可在系统参数 perf.grade.excellent / perf.grade.qualified 调整。
低于合格线为待改进，并触发预警。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

DEFAULT_EXCELLENT = Decimal("85")
DEFAULT_QUALIFIED = Decimal("60")
GRADE_LEVELS = frozenset({"EXCELLENT", "QUALIFIED", "IMPROVE"})


def _decimal(raw: str, fallback: Decimal) -> Decimal:
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return fallback
    if value != value.to_integral_value() and value.as_tuple().exponent < -2:
        value = value.quantize(Decimal("0.01"))
    return value


def grade_lines(db: Session | None = None) -> tuple[Decimal, Decimal]:
    from app.settings_runtime import get_param

    excellent = _decimal(get_param("perf.grade.excellent", "85", db=db), DEFAULT_EXCELLENT)
    qualified = _decimal(get_param("perf.grade.qualified", "60", db=db), DEFAULT_QUALIFIED)
    if qualified < 0 or excellent > 100 or excellent <= qualified:
        return DEFAULT_EXCELLENT, DEFAULT_QUALIFIED
    return excellent, qualified


def _fmt(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def level_of(score: Decimal | float | None, excellent: Decimal, qualified: Decimal) -> str:
    if score is None:
        return "IMPROVE"
    value = Decimal(str(score))
    if value >= excellent:
        return "EXCELLENT"
    if value >= qualified:
        return "QUALIFIED"
    return "IMPROVE"


def edge_text(level: str, excellent: Decimal, qualified: Decimal) -> str:
    excellent_text = _fmt(excellent)
    qualified_text = _fmt(qualified)
    if excellent == excellent.to_integral_value():
        qualified_upper = _fmt(excellent - 1)
    else:
        qualified_upper = excellent_text
    if level == "EXCELLENT":
        return f"优秀 ≥{excellent_text}"
    if level == "QUALIFIED":
        return f"合格 {qualified_text}~{qualified_upper}"
    return f"待改进 <{qualified_text}"


def grade_line_text(excellent: Decimal, qualified: Decimal) -> str:
    return " · ".join(
        edge_text(level, excellent, qualified) for level in ("EXCELLENT", "QUALIFIED", "IMPROVE")
    )


def alert_triggered(level: str) -> bool:
    return level == "IMPROVE"
