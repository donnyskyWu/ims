import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("IMS_DB", "ims_test")
os.environ.setdefault("IMS_OPS_DB", "ims_ops_test")

out_path = Path(__file__).resolve().parents[1] / "reset_log.txt"
try:
    from tests.schema_reset import reset_ims_test_schema

    reset_ims_test_schema()
    out_path.write_text("OK\n", encoding="utf-8")
except Exception:
    out_path.write_text(traceback.format_exc(), encoding="utf-8")
    raise
