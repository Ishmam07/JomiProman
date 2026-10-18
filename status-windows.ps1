$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host 'Docker Desktop is required.' -ForegroundColor Red; exit 1 }
docker compose ps
if (Test-Path '.env') {
  $webPort = '3100'; $apiPort = '8101'
  foreach ($line in Get-Content '.env') {
    if ($line -match '^WEB_PORT=(.+)$') { $webPort = $Matches[1].Trim() }
    if ($line -match '^API_PORT=(.+)$') { $apiPort = $Matches[1].Trim() }
  }
  Write-Host "`nWebsite: http://localhost:$webPort"
  try { $r = Invoke-RestMethod "http://localhost:$apiPort/api/health" -TimeoutSec 4; Write-Host 'API health response:'; $r | ConvertTo-Json -Depth 5 } catch { Write-Host "API health check failed: $($_.Exception.Message)" -ForegroundColor Yellow }
}
