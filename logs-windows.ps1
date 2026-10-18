$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host 'Docker Desktop is required.' -ForegroundColor Red; exit 1 }
Write-Host 'Following logs; press Ctrl+C to stop viewing logs (containers will keep running).' -ForegroundColor Cyan
docker compose logs -f --tail=100
exit $LASTEXITCODE
