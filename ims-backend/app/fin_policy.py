"""场次财务口径。改这里才会改佣金基数、核准前能否改成本和净利率分母。"""

from __future__ import annotations


# 核准前（已提交、未核准）可以直接改成本。已核准必须走更正单。
EDIT_COST_BEFORE_CONFIRM = True


def commission_amount(gmv: float, refund: float, rate: float) -> float:
    """平台佣金按 GMV 全额计算，不扣退款。"""
    del refund
    return round(float(gmv or 0) * float(rate or 0), 2)


def net_rate_denominator(gmv: float, refund: float) -> float:
    """净利率分母 = GMV − 退款。"""
    return round(float(gmv or 0) - float(refund or 0), 2)
