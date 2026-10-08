import re, subprocess
procs = subprocess.check_output(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Select-Object ProcessId, CommandLine | Format-List"],
    text=True, errors="replace",
)
for line in procs.splitlines():
    if "pytest" in line.lower() or "_run_pytest" in line:
        print(line[:350])
