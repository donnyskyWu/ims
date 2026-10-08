"""Run pytest and write combined output to pytest_result.txt in repo root."""
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    tests_dir = root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / ".ims_test_ddl.lock").unlink(missing_ok=True)
    lock = tests_dir / ".pytest_full_run.lock"
    lock.touch()
    out = root / "pytest_result.txt"
    cmd = [sys.executable, "-u", "-m", "pytest", "-q", "--tb=line", "-s"]
    env = {**os.environ, "PYTEST_ADDOPTS": ""}

    print("[pytest] launching full suite …", flush=True)
    with out.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        while proc.poll() is None:
            print(f"[pytest] running pid={proc.pid} …", flush=True)
            time.sleep(5)
        rc = proc.returncode

    text = out.read_text(encoding="utf-8")
    print(text[-2000:] if len(text) > 2000 else text)
    lock.unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        lock = Path(__file__).resolve().parents[1] / "tests" / ".pytest_full_run.lock"
        lock.unlink(missing_ok=True)
