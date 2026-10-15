"""勾稽 / 字段校验表达式白名单。

口径与数据指标公式（C040 / 1192）一致：只允许字段或指标代码、白名单函数
（SUM / AVG / COUNT / MAX / MIN）以及四则运算和比较。拒绝 SQL 关键字
（DELETE / DROP / UPDATE / SELECT 等）和任意表达式。

保存、预览校验、提交执行三处都调用本模块。已写入库的非法表达式在执行时同样拒绝，
不进入求值。求值只走语法树，不使用 eval。
"""

from __future__ import annotations

import re

SAFE_FUNCS = frozenset({"SUM", "AVG", "COUNT", "MAX", "MIN"})

SQL_KEYWORDS = frozenset(
    {
        "DELETE",
        "DROP",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "SELECT",
        "FROM",
        "WHERE",
        "TABLE",
        "INTO",
        "CREATE",
        "GRANT",
        "REVOKE",
        "MERGE",
        "CALL",
        "DECLARE",
        "SHUTDOWN",
        "SLEEP",
        "OR",
        "AND",
        "XOR",
        "NOT",
        "LIKE",
        "JOIN",
        "HAVING",
        "GROUP",
        "ORDER",
        "BY",
        "LIMIT",
        "OFFSET",
        "DATABASE",
        "SCHEMA",
        "SCRIPT",
        "EVAL",
        "SYSTEM",
        "INFORMATION_SCHEMA",
        "LOAD_FILE",
        "OUTFILE",
        "BENCHMARK",
        "WAITFOR",
        "CHAR",
        "CAST",
        "CONVERT",
        "CONCAT",
        "SUBSTRING",
        "USER",
        "PASSWORD",
        "NULL",
        "IS",
        "IN",
        "BETWEEN",
        "EXISTS",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "REPLACE",
        "EXPLAIN",
        "SHOW",
        "USE",
        "SET",
        "VALUES",
        "DISTINCT",
        "IGNORE",
        "PROCEDURE",
        "FUNCTION",
        "TRIGGER",
        "INDEX",
        "VIEW",
        "DATABASES",
        "SLEEP",
        "BENCHMARK",
    }
)

_SHORTHAND = re.compile(r"^(>=|<=|>|<|==|=)\s*(-?\d+(?:\.\d+)?)$")
_ILLEGAL_MSG = "非法表达式"


class ExprError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def _is_ident_start(ch: str) -> bool:
    return ch.isascii() and (ch.isalpha() or ch == "_") or "\u4e00" <= ch <= "\u9fff"


def _is_ident_part(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch == "_") or "\u4e00" <= ch <= "\u9fff"


def tokenize(src: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "(),":
            tokens.append((ch, ch))
            i += 1
            continue
        two = src[i : i + 2]
        if two in {"==", "!=", ">=", "<="}:
            tokens.append(("CMP", two))
            i += 2
            continue
        if ch in "+-*/><=":
            kind = "CMP" if ch in "><=" else "OP"
            tokens.append((kind, ch))
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i + 1
            dot = ch == "."
            while j < n and (src[j].isdigit() or (src[j] == "." and not dot)):
                if src[j] == ".":
                    dot = True
                j += 1
            tokens.append(("NUM", src[i:j]))
            i = j
            continue
        if _is_ident_start(ch):
            j = i + 1
            while j < n and _is_ident_part(src[j]):
                j += 1
            tokens.append(("IDENT", src[i:j]))
            i = j
            continue
        raise ExprError(1192, _ILLEGAL_MSG)
    return tokens


def _reject_keyword(name: str) -> None:
    if name.upper() in SQL_KEYWORDS:
        raise ExprError(1192, _ILLEGAL_MSG)


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.i = 0
        self.names: list[str] = []

    def peek(self) -> tuple[str, str] | None:
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def pop(self) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ExprError(1192, _ILLEGAL_MSG)
        self.i += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise ExprError(1192, _ILLEGAL_MSG)
        node = self.parse_cmp()
        if self.peek() is not None:
            raise ExprError(1192, _ILLEGAL_MSG)
        return node

    def parse_cmp(self):
        left = self.parse_sum()
        tok = self.peek()
        if tok and tok[0] == "CMP":
            self.pop()
            right = self.parse_sum()
            return ("cmp", tok[1], left, right)
        return left

    def parse_sum(self):
        node = self.parse_prod()
        while True:
            tok = self.peek()
            if not tok or tok[0] != "OP" or tok[1] not in "+-":
                break
            self.pop()
            node = ("bin", tok[1], node, self.parse_prod())
        return node

    def parse_prod(self):
        node = self.parse_unary()
        while True:
            tok = self.peek()
            if not tok or tok[0] != "OP" or tok[1] not in "*/":
                break
            self.pop()
            node = ("bin", tok[1], node, self.parse_unary())
        return node

    def parse_unary(self):
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] in "+-":
            self.pop()
            node = self.parse_unary()
            if tok[1] == "-":
                return ("neg", node)
            return node
        return self.parse_primary()

    def parse_primary(self):
        tok = self.pop()
        kind, text = tok
        if kind == "NUM":
            return ("num", float(text))
        if kind == "(":
            node = self.parse_cmp()
            close = self.pop()
            if close != (")", ")"):
                raise ExprError(1192, _ILLEGAL_MSG)
            return node
        if kind != "IDENT":
            raise ExprError(1192, _ILLEGAL_MSG)
        _reject_keyword(text)
        nxt = self.peek()
        if nxt == ("(", "("):
            upper = text.upper()
            if upper not in SAFE_FUNCS:
                raise ExprError(1192, _ILLEGAL_MSG)
            self.pop()
            args = []
            if self.peek() != (")", ")"):
                args.append(self.parse_cmp())
                while self.peek() == (",", ","):
                    self.pop()
                    args.append(self.parse_cmp())
            close = self.pop()
            if close != (")", ")"):
                raise ExprError(1192, _ILLEGAL_MSG)
            if not args:
                raise ExprError(1192, _ILLEGAL_MSG)
            return ("call", upper, args)
        self.names.append(text)
        return ("name", text)


def _normalize(expr: str, bind_name: str | None) -> str:
    text = (expr or "").strip()
    matched = _SHORTHAND.match(text)
    if matched and bind_name:
        return f"{bind_name} {matched.group(1)} {matched.group(2)}"
    return text


def parse_expression(expr: str, bind_name: str | None = None):
    text = _normalize(expr, bind_name)
    if _SHORTHAND.match(text) and not bind_name:
        return ("shorthand", text), []
    if not text:
        raise ExprError(1192, _ILLEGAL_MSG)
    parser = _Parser(tokenize(text))
    return parser.parse(), parser.names


def check_expression(expr: str, allowed_names: set[str] | None = None, bind_name: str | None = None) -> None:
    """保存 / 校验入口。空串视为未配置。未知字段 1121，关键字或任意表达式 1192。"""
    text = (expr or "").strip()
    if not text:
        return
    _node, names = parse_expression(text, bind_name)
    if allowed_names is None:
        return
    allowed = set(allowed_names)
    if bind_name:
        allowed.add(bind_name)
    for name in names:
        if name not in allowed:
            raise ExprError(1121, "勾稽规则引用了不存在的字段")


def _as_number(value) -> float:
    if isinstance(value, bool) or value is None or value == "":
        raise ExprError(1122, "勾稽校验失败")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ExprError(1122, "勾稽校验失败") from exc
    if isinstance(value, (list, tuple)):
        raise ExprError(1122, "勾稽校验失败")
    raise ExprError(1122, "勾稽校验失败")


def _eval_node(node, values: dict):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        if node[1] not in values:
            raise ExprError(1122, "勾稽校验失败")
        return _as_number(values.get(node[1]))
    if kind == "neg":
        return -_as_number(_eval_node(node[1], values))
    if kind == "bin":
        left = _as_number(_eval_node(node[2], values))
        right = _as_number(_eval_node(node[3], values))
        op = node[1]
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if right == 0:
            raise ExprError(1122, "勾稽校验失败")
        return left / right
    if kind == "cmp":
        left = _as_number(_eval_node(node[2], values))
        right = _as_number(_eval_node(node[3], values))
        op = node[1]
        if op in {"==", "="}:
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        raise ExprError(1192, _ILLEGAL_MSG)
    if kind == "call":
        nums = [_as_number(_eval_node(arg, values)) for arg in node[2]]
        func = node[1]
        if func == "SUM":
            return sum(nums)
        if func == "AVG":
            return sum(nums) / len(nums)
        if func == "COUNT":
            return float(len(nums))
        if func == "MAX":
            return max(nums)
        if func == "MIN":
            return min(nums)
        raise ExprError(1192, _ILLEGAL_MSG)
    raise ExprError(1192, _ILLEGAL_MSG)


def evaluate_expression(expr: str, values: dict, allowed_names: set[str] | None = None, bind_name: str | None = None):
    """执行入口。先重新过白名单，库内非法表达式在求值前拒绝。"""
    check_expression(expr, allowed_names, bind_name=bind_name)
    node, _names = parse_expression(expr, bind_name)
    if isinstance(node, tuple) and node and node[0] == "shorthand":
        raise ExprError(1192, _ILLEGAL_MSG)
    return _eval_node(node, values)
