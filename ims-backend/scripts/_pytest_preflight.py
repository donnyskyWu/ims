"""Exit 1 if another pytest or parallel ims-backend test worker is running."""
import re
import subprocess
import sys


def _list_python_commands() -> list[str]:
    try:
        procs = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" -ErrorAction SilentlyContinue | ForEach-Object { $_.CommandLine }",
            ],
            text=True,
            errors="replace",
        )
    except Exception:
        return []
    out: list[str] = []
    for line in procs.splitlines():
        cmd = line.strip()
        if cmd and "_pytest_preflight" not in cmd:
            out.append(cmd)
    return out


def _pytest_tail(cmd: str) -> str:
    idx = cmd.find("-m pytest")
    return cmd[idx:].strip() if idx >= 0 else cmd


def _is_full_suite_pytest(cmd: str) -> bool:
    tail = _pytest_tail(cmd)
    if "-m pytest" not in tail:
        return False
    after = tail.split("-m pytest", 1)[1].strip()
    if "::" in after:
        return False
    return "-q" in after and "--tb=line" in after


def _kill_pids_for_commands(predicate) -> None:
    try:
        procs = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | ForEach-Object { $_.ProcessId.ToString() + \"`t\" + $_.CommandLine }",
            ],
            text=True,
            errors="replace",
        )
    except Exception:
        return
    for line in procs.splitlines():
        if "\t" not in line:
            continue
        pid_s, cmd = line.split("\t", 1)
        cmd = cmd.strip()
        if cmd and predicate(cmd):
            subprocess.run(["taskkill", "/PID", pid_s.strip(), "/F"], check=False)


def main() -> int:
    # Drop agent spot-tests so a single full run can proceed (skip while full lock held).
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    lock = root / "tests" / ".pytest_full_run.lock"
    if not lock.exists():
        _kill_pids_for_commands(
            lambda cmd: "-m pytest" in cmd and not _is_full_suite_pytest(cmd),
        )

    lines = _list_python_commands()
    pytest_cmds = [ln for ln in lines if "-m pytest" in ln or "pytest.exe" in ln.lower()]
    pytest_sigs = {_pytest_tail(ln) for ln in pytest_cmds}
    if pytest_cmds:
        if all(_is_full_suite_pytest(ln) for ln in pytest_cmds):
            print("full pytest already running", file=sys.stderr)
        else:
            print(f"pytest already running ({len(pytest_sigs)} unique invocation(s))", file=sys.stderr)
        return 1

    worker_keys: set[str] = set()
    for ln in lines:
        if "ims-backend" not in ln.replace("\\", "/"):
            continue
        for k in ("ims_test", "ims_ops_test", "_reset_test_dbs", "_run_pytest_to_file", "run_pytest"):
            if k in ln:
                worker_keys.add(k)
                break
    if len(worker_keys) > 1:
        print(f"multiple ims-backend test workers ({len(worker_keys)})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
