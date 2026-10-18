$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host 'Docker Desktop is required.' -ForegroundColor Red; exit 1 }
docker compose stop
if ($LASTEXITCODE -ne 0) { Write-Host 'Could not stop services. Check Docker Desktop.' -ForegroundColor Red; exit $LASTEXITCODE }
Write-Host 'JomiProman stopped. Database volumes/data were kept.' -ForegroundColor Green
