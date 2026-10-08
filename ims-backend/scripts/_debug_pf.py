import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pf", root / "scripts" / "_pytest_preflight.py")
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)
lines = pf._list_python_commands()
pytest_cmds = [ln for ln in lines if "-m pytest" in ln or "pytest.exe" in ln.lower()]
print("count", len(pytest_cmds))
for ln in pytest_cmds:
    print("full?", pf._is_full_suite_pytest(ln))
    print("sig", pf._pytest_tail(ln)[:80])
    print("cmd", ln[:200])
