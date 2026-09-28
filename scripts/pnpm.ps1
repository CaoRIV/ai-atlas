param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PnpmArgs
)

$ErrorActionPreference = "Stop"

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$env:COREPACK_HOME = Join-Path $repositoryRoot ".cache\corepack"
$pnpmVersion = "12.6.0"
$pnpmRoot = Join-Path $env:COREPACK_HOME "v1\pnpm\$pnpmVersion"
$pnpmEntrypoint = Join-Path $pnpmRoot "bin\pnpm.mjs"
$pnpmExecutable = Join-Path $pnpmRoot "pnpm-native.exe"
$pnpmShim = Join-Path $pnpmRoot "pnpm.cmd"

if (-not (Test-Path -LiteralPath $pnpmEntrypoint)) {
    & corepack prepare "pnpm@$pnpmVersion" --activate
    if ($LASTEXITCODE -ne 0) { throw "Corepack could not download pnpm $pnpmVersion." }
}

if (-not (Test-Path -LiteralPath $pnpmExecutable)) {
    & node $pnpmEntrypoint --version
    if ($LASTEXITCODE -ne 0) { throw "pnpm could not install its Windows binary." }
}

if (-not (Test-Path -LiteralPath $pnpmShim)) {
    Set-Content -LiteralPath $pnpmShim -Value '@"%~dp0pnpm-native.exe" %*' -Encoding ascii
}

$env:PATH = "$pnpmRoot;$env:PATH"
& $pnpmExecutable @PnpmArgs
exit $LASTEXITCODE
