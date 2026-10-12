"""导出前端错误码。策略为空则失败。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT.parent / "ims-web" / "src" / "api" / "error-codes.json"


def export_error_codes(path=None, entries=None) -> list[dict]:
    if entries is None:
        from app.core.error_codes import get_registry

        registry = get_registry()
        ordered = [registry[code] for code in sorted(registry)]
    else:
        ordered = list(entries)
    rows = []
    for entry in ordered:
        strategy = getattr(entry, "front_strategy", None)
        if strategy is None and isinstance(entry, dict):
            strategy = entry.get("strategy")
        code = entry["code"] if isinstance(entry, dict) else entry.code
        msg = entry["msg"] if isinstance(entry, dict) else entry.msg
        if not str(strategy or "").strip():
            raise ValueError(f"错误码 {code} 缺少前端策略")
        rows.append({"code": int(code), "msg": msg, "strategy": str(strategy)})
    rows.sort(key=lambda item: item["code"])
    target = Path(path) if path else DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def main(argv=None) -> int:
    export_error_codes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
