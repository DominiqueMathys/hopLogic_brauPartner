$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root ".venv")
}

& $Python -m pip install -r (Join-Path $Root "backend\requirements-dev.txt")
& $Python -m pytest
