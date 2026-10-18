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

function Refresh-DockerPath {
    # winget can install Docker after this PowerShell process has already inherited PATH.
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:PATH = "$machinePath;$userPath"
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $binDir = Split-Path -Parent $candidate
            if (($env:PATH -split ';') -notcontains $binDir) { $env:PATH = "$binDir;$env:PATH" }
            break
        }
    }
}

function Ensure-DockerDesktop {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCommand) {
        Write-Host "`nDocker was not found. JomiProman uses Docker to download and run its services." -ForegroundColor Yellow
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) {
            try { Start-Process 'https://www.docker.com/products/docker-desktop/' } catch {}
            Stop-WithMessage 'Neither Docker nor winget is available. Install Docker Desktop from https://www.docker.com/products/docker-desktop/, enable the WSL 2 backend, restart if requested, then run SETUP-Windows.bat again.'
        }

        $choice = Read-Host 'Install Docker Desktop automatically with winget now? This installs system software and may require administrator approval/restart. [Y/n]'
        if ($choice -and $choice -notmatch '^(?i:y|yes)$') {
            try { Start-Process 'https://www.docker.com/products/docker-desktop/' } catch {}
            Stop-WithMessage 'Docker Desktop was not installed. Install it, start Docker Desktop, then rerun SETUP-Windows.bat.'
        }

        Write-Host 'Installing Docker Desktop. Follow any Windows/UAC installer prompts...' -ForegroundColor Cyan
        & $winget.Source install --exact --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
        $installCode = $LASTEXITCODE
        if ($installCode -ne 0 -and $installCode -ne 3010 -and $installCode -ne 1641) {
            Stop-WithMessage "winget could not finish Docker Desktop installation (exit code $installCode). Install it manually from https://www.docker.com/products/docker-desktop/ and rerun setup."
        }
        Refresh-DockerPath
        $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
        if (-not $dockerCommand) {
            Stop-WithMessage 'Docker Desktop was installed, but this terminal cannot find docker.exe yet. Close this window, open a new terminal (or restart Windows if requested), then double-click SETUP-Windows.bat again.'
        }
        Write-Host 'Docker CLI found.' -ForegroundColor Green
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage 'Docker Compose plugin is unavailable. Update/reinstall Docker Desktop, reopen the terminal, then rerun setup.'
    }

    docker info *> $null
    if ($LASTEXITCODE -eq 0) { return }

    $desktopCandidates = @(
        (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe')
    )
    $desktopExe = $desktopCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $desktopProcess = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
    if ($desktopExe -and -not $desktopProcess) {
        Write-Host 'Starting Docker Desktop...' -ForegroundColor Cyan
        try { Start-Process -FilePath $desktopExe | Out-Null } catch { Write-Host "Could not automatically start Docker Desktop: $($_.Exception.Message)" -ForegroundColor Yellow }
    } else {
        Write-Host 'Waiting for the Docker Engine to start...' -ForegroundColor Cyan
    }

    $deadline = (Get-Date).AddSeconds(180)
    $engineReady = $false
    Write-Host 'Waiting for Docker Engine' -NoNewline
    while ((Get-Date) -lt $deadline) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { $engineReady = $true; break }
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 3
    }
    Write-Host ''
    if (-not $engineReady) {
        Write-Host 'Docker Desktop is installed but the engine is not ready.' -ForegroundColor Yellow
        Write-Host 'If this is the first run, finish the Docker Desktop welcome screens and enable WSL 2.'
        Write-Host 'If WSL is missing, open PowerShell as Administrator, run: wsl --install --no-distribution, then restart Windows.'
        Stop-WithMessage 'Start Docker Desktop, wait until its engine is running, then double-click SETUP-Windows.bat again. No database volumes were deleted.'
    }
}

Write-Host "`nJomiProman for Windows" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

# Bootstrap Docker Desktop if needed, then launch it and wait for its engine.
Ensure-DockerDesktop

$envPath = Join-Path $ProjectRoot '.env'
$examplePath = Join-Path $ProjectRoot '.env.example'
if (-not (Test-Path -LiteralPath $envPath)) {
    if (-not (Test-Path -LiteralPath $examplePath)) {
        Stop-WithMessage 'Missing .env.example. Make sure you cloned/extracted the complete project and are running this script from its root.'
    }
    Copy-Item -LiteralPath $examplePath -Destination $envPath
    Write-Host 'Created local .env from .env.example.' -ForegroundColor Green
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
    Write-Host 'Generated a private ADMIN_KEY in .env (not printed).' -ForegroundColor Green
}

$dbPassword = Get-DotEnvValue -Name 'MYSQL_PASSWORD' -DefaultValue 'jomi_pass'
if ($dbPassword -notmatch '^[A-Za-z0-9_-]+$') {
    Write-Host 'WARNING: MYSQL_PASSWORD contains URL-reserved characters. Use letters/numbers/_/- or URL-encode the password in DATABASE_URL.' -ForegroundColor Yellow
}

Write-Host 'Validating Docker Compose configuration...'
docker compose config -q
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'docker compose config failed. Check .env and docker-compose.yml; see the error above.' }

if ($NoBuild) {
    Write-Host 'Starting existing images...'
    docker compose up -d
} else {
    Write-Host 'Building and starting the first-time setup. This can take several minutes...'
    docker compose up --build -d
}
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Docker could not start the services. Run STATUS-JomiProman.bat and LOGS-JomiProman.bat, or see WINDOWS-QUICKSTART.md.' }

$webPort = Get-DotEnvValue -Name 'WEB_PORT' -DefaultValue '3100'
$apiPort = Get-DotEnvValue -Name 'API_PORT' -DefaultValue '8101'
$webUrl = "http://localhost:$webPort"
$apiUrl = "http://localhost:$apiPort/api/health"
$deadline = (Get-Date).AddSeconds(180)
$healthy = $false
Write-Host 'Waiting for frontend and API health checks' -NoNewline
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
    Write-Host 'Services did not become fully responsive within 180 seconds.' -ForegroundColor Yellow
    Write-Host 'Current Docker status:'
    docker compose ps
    Write-Host 'Recent backend/frontend logs:'
    docker compose logs --tail=60 backend frontend
    Stop-WithMessage 'Startup verification did not pass. See status/logs above; do not delete database volumes.'
}

Write-Host "`nJomiProman is running!" -ForegroundColor Green
Write-Host "Website:      $webUrl"
Write-Host "Admin panel:  $webUrl/admin (ADMIN_KEY is stored locally in .env)"
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
