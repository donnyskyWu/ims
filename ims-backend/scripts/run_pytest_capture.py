"""Run pytest once and write combined output to pytest_result.txt."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pytest_result.txt"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    body = (proc.stdout or "") + (proc.stderr or "")
    OUT.write_text(body, encoding="utf-8")
    print(body[-4000:] if len(body) > 4000 else body)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
