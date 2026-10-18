[CmdletBinding()]
param(
    [switch]$NoBuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

function Stop-WithMessage {
    param([string]$Message, [int]$Code = 1)
    Write-Host "`nERROR: $Message" -ForegroundColor Red
    exit $Code
}

function Get-DotEnvValue {
    param([string]$Name, [string]$DefaultValue)
    $envFile = Join-Path $ProjectRoot '.env'
    if (-not (Test-Path -LiteralPath $envFile)) { return $DefaultValue }
    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^\s*$escaped=" } | Select-Object -Last 1
    if ($null -eq $line) { return $DefaultValue }
    return (($line -replace "^\s*$escaped=", '').Trim().Trim('"').Trim("'"))
}

Write-Host "`nJomiProman for Windows" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-WithMessage "Docker was not found. Install Docker Desktop for Windows, enable its WSL 2 backend, start Docker Desktop, then run this script again. https://www.docker.com/products/docker-desktop/"
}

docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage "Docker Compose plugin is unavailable. Update/reinstall Docker Desktop, then reopen PowerShell."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage "Docker Engine is not running. Open Docker Desktop, wait until it says Engine running, then double-click SETUP-Windows.bat again."
}

$envPath = Join-Path $ProjectRoot '.env'
$examplePath = Join-Path $ProjectRoot '.env.example'
if (-not (Test-Path -LiteralPath $envPath)) {
    if (-not (Test-Path -LiteralPath $examplePath)) {
        Stop-WithMessage "Missing .env.example. Make sure you extracted the complete JomiProman project and run this script from its root."
    }
    Copy-Item -LiteralPath $examplePath -Destination $envPath
    Write-Host "Created local .env from .env.example." -ForegroundColor Green
}

# Generate a private local admin key, but preserve an already configured key.
$lines = @(Get-Content -LiteralPath $envPath)
$adminIndex = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s*ADMIN_KEY=') { $adminIndex = $i }
}
$currentAdmin = ''
if ($adminIndex -ge 0) { $currentAdmin = ($lines[$adminIndex] -replace '^\s*ADMIN_KEY=', '').Trim().Trim('"').Trim("'") }
if ([string]::IsNullOrWhiteSpace($currentAdmin) -or $currentAdmin -eq 'demo-admin-change-me') {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $newAdminKey = ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
    if ($adminIndex -ge 0) { $lines[$adminIndex] = "ADMIN_KEY=$newAdminKey" }
    else { $lines += "ADMIN_KEY=$newAdminKey" }
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($envPath, (($lines -join "`r`n") + "`r`n"), $utf8NoBom)
    Write-Host "Generated a private ADMIN_KEY in .env (not printed)." -ForegroundColor Green
}

# Prevent confusing SQLAlchemy URL parsing caused by reserved characters in this project's simple URL template.
$dbPassword = Get-DotEnvValue -Name 'MYSQL_PASSWORD' -DefaultValue 'jomi_pass'
if ($dbPassword -notmatch '^[A-Za-z0-9_-]+$') {
    Write-Host "WARNING: MYSQL_PASSWORD contains URL-reserved characters. This project currently embeds it in a SQLAlchemy URL; use letters, numbers, underscore or hyphen, or URL-encode it in the connection string." -ForegroundColor Yellow
}

Write-Host "Validating Docker Compose configuration..."
docker compose config -q
if ($LASTEXITCODE -ne 0) { Stop-WithMessage "docker compose config failed. Check .env and docker-compose.yml; see the error above." }

if ($NoBuild) {
    Write-Host "Starting existing images..."
    docker compose up -d
} else {
    Write-Host "Building and starting the first-time setup. This can take several minutes..."
    docker compose up --build -d
}
if ($LASTEXITCODE -ne 0) { Stop-WithMessage "Docker could not start the services. Run STATUS-Windows.bat and LOGS-Windows.bat, or see WINDOWS-QUICKSTART.md." }

$webPort = Get-DotEnvValue -Name 'WEB_PORT' -DefaultValue '3100'
$apiPort = Get-DotEnvValue -Name 'API_PORT' -DefaultValue '8101'
$webUrl = "http://localhost:$webPort"
$apiUrl = "http://localhost:$apiPort/api/health"
$deadline = (Get-Date).AddSeconds(150)
$healthy = $false
Write-Host "Waiting for frontend and API health checks" -NoNewline
while ((Get-Date) -lt $deadline) {
    $webOkay = $false
    $apiOkay = $false
    try { Invoke-WebRequest -Uri "$webUrl/" -UseBasicParsing -TimeoutSec 4 | Out-Null; $webOkay = $true } catch {}
    try { Invoke-RestMethod -Uri $apiUrl -TimeoutSec 4 | Out-Null; $apiOkay = $true } catch {}
    if ($webOkay -and $apiOkay) { $healthy = $true; break }
    Write-Host '.' -NoNewline
    Start-Sleep -Seconds 2
}
Write-Host ''

if (-not $healthy) {
    Write-Host "Services did not become fully responsive within 150 seconds." -ForegroundColor Yellow
    Write-Host "Current Docker status:"
    docker compose ps
    Write-Host "Recent backend/frontend logs:"
    docker compose logs --tail=60 backend frontend
    Stop-WithMessage "Startup verification did not pass. See the status/logs above; do not delete database volumes."
}

Write-Host "`nJomiProman is running!" -ForegroundColor Green
Write-Host "Website:      $webUrl"
Write-Host "Admin panel:  $webUrl/admin (ADMIN_KEY is stored in .env)"
Write-Host "API docs:     http://localhost:$apiPort/api/docs"
Write-Host "Health check: $apiUrl"
Write-Host "MySQL host:   127.0.0.1:$(Get-DotEnvValue -Name 'MYSQL_PORT' -DefaultValue '13306')"
Write-Host "Redis host:   127.0.0.1:$(Get-DotEnvValue -Name 'REDIS_PORT' -DefaultValue '16379')"
Write-Host "`nContainer status:"
docker compose ps
if (-not $NoBrowser) {
    try { Start-Process $webUrl } catch { Write-Host "Open this URL manually: $webUrl" -ForegroundColor Yellow }
}
Write-Host "`nStop later with STOP-JomiProman.bat. Data is kept in Docker volumes." -ForegroundColor Cyan
