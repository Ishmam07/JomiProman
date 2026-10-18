$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host 'Docker Desktop is required.' -ForegroundColor Red; exit 1 }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host 'Open Docker Desktop and wait until the engine is running.' -ForegroundColor Red; exit 1 }
if (-not (Test-Path '.env')) { & (Join-Path $ProjectRoot 'setup-windows.ps1'); exit $LASTEXITCODE }
& (Join-Path $ProjectRoot 'setup-windows.ps1') -NoBuild
exit $LASTEXITCODE
