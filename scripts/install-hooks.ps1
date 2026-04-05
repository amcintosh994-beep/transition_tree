Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host ""
    exit 1
}

function Write-Utf8NoBomFile([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

$repoRoot = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    Fail "This script must be run from inside a Git repository."
}

Set-Location $repoRoot

$gitDir = git rev-parse --git-dir 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitDir)) {
    Fail "Unable to resolve .git directory."
}

$gitDir = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $gitDir))

$sourceHook = Join-Path $repoRoot 'tools/hooks/pre-commit.ps1'
if (-not (Test-Path $sourceHook)) {
    Fail "Versioned hook source not found: $sourceHook"
}

$hooksDir = Join-Path $gitDir 'hooks'
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir | Out-Null
}

$destPs1 = Join-Path $hooksDir 'pre-commit.ps1'
Copy-Item -Path $sourceHook -Destination $destPs1 -Force

$wrapperPath = Join-Path $hooksDir 'pre-commit'

$wrapper = @'
#!/bin/sh
"/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -ExecutionPolicy Bypass -File ".git/hooks/pre-commit.ps1"
status=$?
if [ $status -ne 0 ]; then
  exit $status
fi
exit 0
'@

Write-Utf8NoBomFile -Path $wrapperPath -Content $wrapper

Write-Host ""
Write-Host "Installed Git hooks from versioned sources." -ForegroundColor Green
Write-Host "  Source : tools/hooks/pre-commit.ps1" -ForegroundColor Green
Write-Host "  Target : .git/hooks/pre-commit(.ps1)" -ForegroundColor Green
Write-Host ""
exit 0
