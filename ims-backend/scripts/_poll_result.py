import time
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "pytest_result.txt"
last = -1
for _ in range(60):
    if p.exists():
        n = p.stat().st_size
        if n != last:
            print("size", n)
            last = n
        if n > 500:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines and any(" passed" in ln for ln in lines[-3:]):
                print("\n".join(lines[-3:]))
                raise SystemExit(0)
    time.sleep(30)
if p.exists() and p.stat().st_size:
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[-8:]))
else:
    print("no result yet")
raise SystemExit(1)
