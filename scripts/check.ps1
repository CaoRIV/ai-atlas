$ErrorActionPreference = "Stop"

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$env:UV_CACHE_DIR = Join-Path $repositoryRoot ".cache\uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repositoryRoot ".cache\uv-python"

& "$PSScriptRoot\pnpm.ps1" --recursive --if-present lint
if ($LASTEXITCODE -ne 0) { throw "Web lint failed." }
& node --check scripts/run-discover-e2e.mjs
if ($LASTEXITCODE -ne 0) { throw "E2E runner syntax check failed." }

& "$PSScriptRoot\pnpm.ps1" --recursive --if-present typecheck
if ($LASTEXITCODE -ne 0) { throw "Web typecheck failed." }
& "$PSScriptRoot\pnpm.ps1" exec tsc --project tsconfig.e2e.json
if ($LASTEXITCODE -ne 0) { throw "E2E typecheck failed." }

& "$PSScriptRoot\pnpm.ps1" --recursive --if-present test
if ($LASTEXITCODE -ne 0) { throw "Web tests failed." }

& "$PSScriptRoot\pnpm.ps1" --recursive --if-present build
if ($LASTEXITCODE -ne 0) { throw "Web build failed." }

& uv run ruff check apps/api scripts/e2e_database.py
if ($LASTEXITCODE -ne 0) { throw "API and E2E helper lint failed." }

& uv run ruff format --check apps/api scripts/e2e_database.py
if ($LASTEXITCODE -ne 0) { throw "API and E2E helper format check failed." }

& uv run mypy
if ($LASTEXITCODE -ne 0) { throw "API typecheck failed." }

& uv run pytest -m "not integration and not live"
if ($LASTEXITCODE -ne 0) { throw "API unit tests failed." }

Write-Host "All local static and unit checks passed."
