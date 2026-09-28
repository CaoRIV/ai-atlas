$ErrorActionPreference = "Stop"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

Assert-Command node
Assert-Command corepack
Assert-Command uv
Assert-Command docker

$nodeVersion = (& node --version).TrimStart("v")
if (-not $nodeVersion.StartsWith("22.")) {
    throw "Node.js 22.x is required; found $nodeVersion. See .node-version."
}

$uvVersion = (& uv --version).Trim()
if ($uvVersion -notmatch '^uv 0\.9\.28(?:\s|$)') {
    throw "uv 0.9.28 is required; found $uvVersion."
}

& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker Compose is unavailable." }

& "$PSScriptRoot\pnpm.ps1" install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw "pnpm install failed." }

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$env:UV_CACHE_DIR = Join-Path $repositoryRoot ".cache\uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repositoryRoot ".cache\uv-python"

& uv python find 3.11 *> $null
if ($LASTEXITCODE -ne 0) {
    & uv python install 3.11
    if ($LASTEXITCODE -ne 0) { throw "uv could not install Python 3.11." }
}

& uv sync --python 3.11 --all-groups --frozen
if ($LASTEXITCODE -ne 0) { throw "uv sync failed." }

$pythonVersion = (& uv run python -c "import platform; print(platform.python_version())").Trim()

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example; fill only the secrets needed locally."
}

Write-Host "AI Atlas dependencies are installed."
Write-Host "Node $nodeVersion; Python $pythonVersion; pnpm $(& "$PSScriptRoot\pnpm.ps1" --version); $uvVersion"

