param(
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Push-Location (Join-Path $root "backend")
try {
    & ".\.venv\Scripts\python.exe" -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Backend test thất bại."
    }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $root "frontend")
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend type-check thất bại."
    }
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build thất bại."
    }
    if (-not $SkipBrowser) {
        npm run test:e2e
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend E2E test thất bại."
        }
    }
}
finally {
    Pop-Location
}
