"""Run a small pytest subset (for environments that kill bare pytest CLI)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

TESTS = [
    "tests/test_api.py::test_health",
    "tests/test_api.py::test_login_and_user_mask",
    "tests/test_flow.py::test_flow_timeout_list_and_urge",
    "tests/test_flow.py::test_flow_timeout_rate_br115_stub",
    "tests/test_flow.py::test_flow_timeout_distribution_stub",
    "tests/test_perf.py::test_perf_result_export_csv",
    "tests/test_alert.py::test_alert_rule_trial_alias_matches_run",
]

if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", "--tb=line", *TESTS]))
