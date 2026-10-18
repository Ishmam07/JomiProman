$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
# Reuse the same bootstrapper: it installs/starts Docker if needed and then starts the app.
if (-not (Test-Path '.env')) {
    & (Join-Path $ProjectRoot 'setup-windows.ps1')
} else {
    & (Join-Path $ProjectRoot 'setup-windows.ps1') -NoBuild
}
exit $LASTEXITCODE
