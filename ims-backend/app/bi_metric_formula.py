"""指标公式白名单（BUG-C040）。

试算 ``POST /bi/metric/{id}/preview`` 和指标分析都不读取 ``formula`` 去拼 SQL，
也不 ``eval`` / ``exec``。采集调度（``start_scheduler`` / ``tick_local_tasks``）
只跑采集任务，不读 ``ims_bi_metric``。因此已入库的 ``DELETE FROM x`` 不会被自动执行。

这里仍在保存、试算、分析三条入口拒绝非白名单公式，并在启动时把已存非法公式停用，
避免以后若有人把公式接进计算时被带上。
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import utcnow
from app.models import BiMetric

WHITELIST_FUNCS = frozenset({"SUM", "AVG", "COUNT", "MAX", "MIN"})
_RESERVED = frozenset(
    {
        "DELETE",
        "UPDATE",
        "DROP",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "SELECT",
        "UNION",
        "FROM",
        "WHERE",
        "INTO",
        "TABLE",
        "DATABASE",
        "GRANT",
        "REVOKE",
        "MERGE",
        "CALL",
        "SLEEP",
        "BENCHMARK",
        "CREATE",
        "REPLACE",
        "RENAME",
        "SET",
        "SHOW",
        "USE",
        "WITH",
        "HAVING",
        "GROUP",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "JOIN",
        "AND",
        "OR",
        "NOT",
        "IN",
        "LIKE",
        "BETWEEN",
        "IS",
        "NULL",
        "TRUE",
        "FALSE",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "CAST",
        "CONVERT",
        "INFORMATION_SCHEMA",
        "OUTFILE",
        "DUMPFILE",
        "LOAD_FILE",
        "PROCEDURE",
        "FUNCTION",
        "TRIGGER",
        "VIEW",
        "INDEX",
        "SCHEMA",
        "VALUES",
        "DISTINCT",
        "ALL",
        "ANY",
        "EXISTS",
        "INTERSECT",
        "EXCEPT",
        "WINDOW",
        "OVER",
        "PARTITION",
        "BY",
        "ASC",
        "DESC",
        "INNER",
        "LEFT",
        "RIGHT",
        "OUTER",
        "ON",
        "AS",
        "IF",
        "XOR",
        "REGEXP",
        "RLIKE",
    }
)
_DML = ("DELETE", "UPDATE", "DROP", "INSERT", "ALTER", "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "CALL")
_BASE_MSG = "计算公式非法（1192）：仅允许指标编码、白名单函数（SUM/AVG/COUNT/MAX/MIN）和四则运算"
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def formula_error(formula: str | None) -> str | None:
    """空公式视为未配置，允许。非法时返回可直接展示的 1192 文案。"""
    text = formula or ""
    if not text.strip():
        return None
    if len(text) > 512:
        return _BASE_MSG + "，公式过长"
    if "--" in text or "/*" in text or "*/" in text:
        return _BASE_MSG
    upper = text.upper()
    for word in _DML:
        if re.search(rf"\b{word}\b", upper):
            return f"{_BASE_MSG}，不允许 {word} 等语句"
    if _forbidden_char(text) or not _parse(text):
        return _BASE_MSG
    return None


def quarantine_illegal_metric_formulas(db: Session) -> int:
    """已存非法公式改为停用，公式原文保留，便于人工核对后删除。不执行公式。"""
    rows = list(db.scalars(select(BiMetric).where(BiMetric.deleted == 0)).all())
    changed = 0
    now = utcnow()
    for row in rows:
        if formula_error(row.formula or "") is None:
            continue
        if row.status != "DISABLED":
            row.status = "DISABLED"
            row.updated_at = now
            changed += 1
    return changed


def _forbidden_char(text: str) -> bool:
    for ch in text:
        if ch.isspace():
            continue
        if ch in "+-*/()":
            continue
        if ch.isascii() and (ch.isalnum() or ch == "_" or ch == "."):
            continue
        return True
    return False


def _parse(text: str) -> bool:
    tokens = _tokenize(text)
    if tokens is None:
        return False
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take() -> str | None:
        nonlocal pos
        if pos >= len(tokens):
            return None
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_expr() -> bool:
        if not parse_term():
            return False
        while peek() in {"+", "-"}:
            take()
            if not parse_term():
                return False
        return True

    def parse_term() -> bool:
        if not parse_unary():
            return False
        while peek() in {"*", "/"}:
            take()
            if not parse_unary():
                return False
        return True

    def parse_unary() -> bool:
        if peek() in {"+", "-"}:
            take()
            return parse_unary()
        return parse_factor()

    def parse_factor() -> bool:
        tok = peek()
        if tok is None:
            return False
        if tok.startswith("#n:"):
            take()
            return True
        if tok.startswith("#i:"):
            name = tok[3:]
            upper = name.upper()
            take()
            if upper in WHITELIST_FUNCS:
                if take() != "(" or not parse_expr() or take() != ")":
                    return False
                return True
            return upper not in _RESERVED and upper not in WHITELIST_FUNCS
        if tok == "(":
            take()
            if not parse_expr() or take() != ")":
                return False
            return True
        return False

    if not parse_expr():
        return False
    return peek() is None


def _tokenize(text: str) -> list[str] | None:
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "+-*/()":
            tokens.append(ch)
            i += 1
            continue
        if ch.isdigit():
            match = _NUMBER.match(text, i)
            if match is None:
                return None
            tokens.append("#n:" + match.group(0))
            i = match.end()
            continue
        if ch.isascii() and (ch.isalpha() or ch == "_"):
            match = _IDENT.match(text, i)
            if match is None:
                return None
            tokens.append("#i:" + match.group(0))
            i = match.end()
            continue
        return None
    return tokens
