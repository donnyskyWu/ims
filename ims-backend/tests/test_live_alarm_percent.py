"""BUG-039 · 降幅阈值按百分数比较，30 表示 30% 而不是 3000%。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from types import SimpleNamespace

from app.main import app  # noqa: F401
from app.live_alarm import expr_summary, hit_text


def test_summary_keeps_percent_threshold():
    text = expr_summary(
        "THRESHOLD",
        {"metric": "viewer_drop", "operator": "PCT_DROP", "threshold": 30, "window": 5},
    )
    assert text == "场观降幅 ≥ 30%（窗口 5 分钟）"
    assert "3000" not in text


def test_forty_percent_drop_hits_thirty_percent_rule():
    rule = SimpleNamespace(rule_expr={"metric": "viewer_count", "operator": "PCT_DROP", "threshold": 30})
    session = SimpleNamespace(topic="普通专场")
    snap = SimpleNamespace(viewer_count=100, gmv_from_platform=None, peak_online=None)
    hit = hit_text(rule, session, SimpleNamespace(viewer_count=60), snap)
    assert hit is not None
    assert "40" in hit
    assert "30%" in hit
    miss = hit_text(rule, session, SimpleNamespace(viewer_count=80), snap)
    assert miss is None
