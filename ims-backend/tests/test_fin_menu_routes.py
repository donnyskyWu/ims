"""BUG-084：账号财务 /ims/cost，场次财务目录不占用这条路由，成本核算走 /ims/fin/cost。"""

import os

os.environ["IMS_DB"] = "ims_test"

from sqlalchemy import select

from app.core import SessionLocal
from app.models import Menu
from app.role_matrix import ensure_menus


def test_session_finance_dir_does_not_keep_account_cost_route():
    db = SessionLocal()
    try:
        cost = db.scalar(select(Menu).where(Menu.perm_code == "menu:cost:query", Menu.deleted == 0))
        fin = db.scalar(select(Menu).where(Menu.perm_code == "nav:fin:query", Menu.deleted == 0))
        fin_cost = db.scalar(select(Menu).where(Menu.perm_code == "menu:finCost:query", Menu.deleted == 0))
        assert cost is not None and cost.route == "/ims/cost" and cost.name == "账号财务"
        assert fin_cost is not None and fin_cost.route == "/ims/fin/cost" and fin_cost.name == "成本核算"
        assert fin is not None and fin.name == "场次财务" and fin.menu_type == "DIR" and fin.route == ""
        fin.route = "/ims/cost"
        db.flush()
        ensure_menus(db)
        db.refresh(fin)
        db.refresh(cost)
        db.refresh(fin_cost)
        assert fin.route == ""
        assert cost.route == "/ims/cost"
        assert fin_cost.route == "/ims/fin/cost"
        assert fin.id != cost.id
    finally:
        db.close()
