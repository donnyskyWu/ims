"""勾稽表达式白名单：注入用例在解析阶段拒绝，不求值。"""

import pytest

from app.report_expr import ExprError, check_expression, evaluate_expression

ALLOWED = {"gmv", "orders", "cost", "detail_sum", "summary", "tb_x", "t"}

INJECTION = [
    "DELETE FROM tb_x",
    "DROP TABLE tb_x",
    "delete from tb_x",
    "Drop Table tb_x",
    "UPDATE t SET a=1",
    "INSERT INTO t VALUES (1)",
    "SELECT * FROM t",
    "'; DROP TABLE tb_x; --",
    "__import__('os').system('id')",
    'eval("1")',
    "gmv; DROP TABLE tb_x",
    "1 OR 1=1",
    "SUM(gmv); DELETE FROM t",
    "gmv + (SELECT 1)",
    "EXEC('cmd')",
    "TRUNCATE TABLE tb_x",
]


@pytest.mark.parametrize("expr", INJECTION)
def test_injection_rejected_on_check(expr: str):
    with pytest.raises(ExprError) as raised:
        check_expression(expr, ALLOWED)
    assert raised.value.code == 1192
    assert raised.value.msg == "非法表达式"


@pytest.mark.parametrize("expr", ["DELETE FROM tb_x", "DROP TABLE tb_x", "UPDATE t SET gmv=1"])
def test_injection_rejected_on_execute_even_if_stored(expr: str):
    """库里已经写下的非法表达式，执行前再次拦截，不会进入求值。"""
    with pytest.raises(ExprError) as raised:
        evaluate_expression(expr, {"gmv": 1, "tb_x": 1, "t": 1}, ALLOWED)
    assert raised.value.code == 1192


def test_unknown_field_is_1121_not_1192():
    with pytest.raises(ExprError) as raised:
        check_expression("missing_detail == summary", {"summary"})
    assert raised.value.code == 1121


def test_whitelist_arithmetic_and_functions_pass():
    check_expression("gmv + orders", ALLOWED)
    check_expression("(SUM(gmv) - SUM(cost)) / SUM(gmv)", ALLOWED)
    check_expression("detail_sum == summary", ALLOWED)
    check_expression("detail_sum = summary", ALLOWED)
    check_expression("AVG(gmv, orders)", ALLOWED)
    check_expression(">=0", ALLOWED, bind_name="gmv")


def test_eval_comparison_and_sum():
    assert evaluate_expression("detail_sum == summary", {"detail_sum": 10, "summary": 10}, ALLOWED) is True
    assert evaluate_expression("detail_sum == summary", {"detail_sum": 9, "summary": 10}, ALLOWED) is False
    assert evaluate_expression("SUM(gmv, orders) - cost", {"gmv": 8, "orders": 2, "cost": 3}, ALLOWED) == 7
    assert evaluate_expression(">=0", {"gmv": 3}, ALLOWED, bind_name="gmv") is True
    assert evaluate_expression(">=0", {"gmv": -1}, ALLOWED, bind_name="gmv") is False


def test_arbitrary_call_rejected():
    with pytest.raises(ExprError) as raised:
        check_expression("ABS(gmv)", ALLOWED)
    assert raised.value.code == 1192
    with pytest.raises(ExprError) as raised:
        check_expression("gmv.drop()", ALLOWED)
    assert raised.value.code == 1192


def test_alert_call_is_illegal_expression_not_unknown_field():
    with pytest.raises(ExprError) as raised:
        check_expression("alert(1)", ALLOWED)
    assert raised.value.code == 1192
    assert raised.value.msg == "非法表达式"
    assert "不存在的字段" not in raised.value.msg
