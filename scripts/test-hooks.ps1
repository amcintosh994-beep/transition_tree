Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host ""
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Success([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Normalize-GitPath([string]$Path) {
    return ($Path -replace '\\', '/').Trim()
}

function Remove-IfExists([string]$Path) {
    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force
    }
}

function Restore-BackupFile([string]$BackupPath, [string]$DestPath) {
    if (Test-Path $BackupPath) {
        Move-Item $BackupPath $DestPath -Force
    }
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

$installScript = Join-Path $repoRoot 'scripts/install-hooks.ps1'
if (-not (Test-Path $installScript)) {
    Fail "Installer script not found: $installScript"
}

$hooksDir = Join-Path $gitDir 'hooks'
$deployedWrapper = Join-Path $hooksDir 'pre-commit'
$deployedPs1 = Join-Path $hooksDir 'pre-commit.ps1'

$backupRoot = Join-Path $repoRoot 'tmp/hook_test_backup'
$backupWrapper = Join-Path $backupRoot 'pre-commit.bak'
$backupPs1 = Join-Path $backupRoot 'pre-commit.ps1.bak'

$rootProbe = Join-Path $repoRoot '_hook_root_probe.txt'
$srcProbe = Join-Path $repoRoot 'src/mttt/_hook_src_probe.py'

$madeAllowCommit = $false

try {
    Info "Checking working tree state."
    $statusPorcelain = git status --porcelain=v1
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to read git status."
    }

    # We allow preexisting modifications, but we refuse to proceed if our own probe/temp paths already exist.
    if (Test-Path $rootProbe) {
        Fail "Probe file already exists: $rootProbe"
    }
    if (Test-Path $srcProbe) {
        Fail "Probe file already exists: $srcProbe"
    }
    if (Test-Path $backupRoot) {
        Fail "Temporary backup directory already exists: $backupRoot"
    }

    Info "Backing up currently deployed hooks."
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

    if (Test-Path $deployedWrapper) {
        Move-Item $deployedWrapper $backupWrapper -Force
    }
    if (Test-Path $deployedPs1) {
        Move-Item $deployedPs1 $backupPs1 -Force
    }

    Info "Verifying cold state."
    if (Test-Path $deployedWrapper) {
        Fail "Deployed wrapper still exists after backup."
    }
    if (Test-Path $deployedPs1) {
        Fail "Deployed PowerShell hook still exists after backup."
    }

    Info "Running installer."
    & "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $installScript
    if ($LASTEXITCODE -ne 0) {
        Fail "Hook installer failed."
    }

    Info "Verifying deployed hooks were recreated."
    if (-not (Test-Path $deployedWrapper)) {
        Fail "Installer did not recreate .git/hooks/pre-commit"
    }
    if (-not (Test-Path $deployedPs1)) {
        Fail "Installer did not recreate .git/hooks/pre-commit.ps1"
    }

    Info "Testing allowed case: root-level untracked file should not block commit."
    New-Item -ItemType File -Path $rootProbe | Out-Null
    git commit --allow-empty -m "hook allow probe"
    if ($LASTEXITCODE -ne 0) {
        Fail "Allow-probe commit was unexpectedly blocked."
    }
    $madeAllowCommit = $true
    Remove-IfExists $rootProbe
    Success "Allow case passed."

    Info "Testing blocked case: src-level untracked file should block commit."
    New-Item -ItemType File -Path $srcProbe | Out-Null

    $blockOutput = cmd.exe /c 'git commit --allow-empty -m "hook block probe" 2>&1'
    $blockExit = $LASTEXITCODE

    if ($blockExit -eq 0) {
         Fail "Block-probe commit unexpectedly succeeded."
    }

    if (-not ($blockOutput -join "`n" | Select-String "Refusing commit because untracked critical files exist")) {
         Fail "Block-probe commit failed, but not for the expected hook reason."
    }

    Remove-IfExists $srcProbe
    Success "Block case passed.”

    Success "Hook cold-state test completed successfully."
}
finally {
    Info "Cleaning up probe files."
    Remove-IfExists $rootProbe
    Remove-IfExists $srcProbe

    if ($madeAllowCommit) {
        Info "Removing temporary allow-probe empty commit."
        git reset --soft HEAD~1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] Failed to soft-reset temporary allow-probe commit." -ForegroundColor Yellow
        } else {
            git restore --staged . | Out-Null
        }
    }

    Info "Restoring original deployed hooks backup if present."
    Remove-IfExists $deployedWrapper
    Remove-IfExists $deployedPs1
    Restore-BackupFile $backupWrapper $deployedWrapper
    Restore-BackupFile $backupPs1 $deployedPs1

    Info "Removing temporary backup directory."
    Remove-IfExists $backupRoot

    Write-Host ""
    git status
    Write-Host ""
}

