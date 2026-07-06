$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Không tìm thấy Python virtualenv ở backend\.venv."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Push-Location $backendDir
try {
    & $python -m app.application.ai.catalog_index_status
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
