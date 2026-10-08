import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
proc = subprocess.Popen(
    [sys.executable, "-m", "pytest", "-q", "--tb=line"],
    cwd=root,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(3)
r = subprocess.run([sys.executable, str(root / "scripts" / "_pytest_preflight.py")])
print("preflight_rc", r.returncode)
print("pytest_poll", proc.poll())
if proc.poll() is None:
    proc.terminate()
    proc.wait(timeout=10)
else:
    print("pytest_already_dead", proc.returncode)
