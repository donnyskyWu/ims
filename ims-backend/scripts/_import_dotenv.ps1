# Dotenv loader for ims-backend/.env (KEY=VALUE; # comments; optional "quotes")
function Import-ImsDotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $false
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if ($val.StartsWith('"') -and $val.EndsWith('"')) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
    return $true
}
