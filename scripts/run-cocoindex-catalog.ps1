$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$cocoindex = Join-Path $backendDir ".venv\Scripts\cocoindex.exe"

if (-not (Test-Path $python)) {
    throw "Không tìm thấy Python virtualenv ở backend\.venv."
}

if (-not (Test-Path $cocoindex)) {
    & $python -m pip install -e $backendDir
}

if (-not $env:COCOINDEX_DB) {
    $env:COCOINDEX_DB = Join-Path $backendDir "var\cocoindex\cocoindex.db"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Push-Location $backendDir
try {
    & $cocoindex update app\application\ai\cocoindex_catalog.py
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
