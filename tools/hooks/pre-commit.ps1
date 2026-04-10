Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$Message) {
    Write-Host ''
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host ''
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Normalize-GitPath([string]$Path) {
    return ($Path -replace '\\', '/').Trim()
}

function Is-CriticalPath([string]$Path, [string[]]$Prefixes) {
    foreach ($prefix in $Prefixes) {
        if ($Path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

$statusLines = git status --porcelain=v1
if ($LASTEXITCODE -ne 0) {
    Fail 'Unable to read git status.'
}

$criticalPrefixes = @(
    'src/',
    'tests/',
    'schema/'
)

$badUntracked = New-Object System.Collections.Generic.List[string]
$badUnstaged = New-Object System.Collections.Generic.List[string]

foreach ($line in $statusLines) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    # Porcelain v1:
    # XY path
    # X = index status
    # Y = worktree status
    $xy = $line.Substring(0, 2)
    $rawPath = $line.Substring(3)
    $path = Normalize-GitPath $rawPath

    if (-not (Is-CriticalPath $path $criticalPrefixes)) {
        continue
    }

    $x = $xy[0]
    $y = $xy[1]

    # Untracked: ?? path
    if ($xy -eq '??') {
        $badUntracked.Add($path)
        continue
    }

    # Unstaged worktree modifications:
    # second column not blank means working tree differs from index
    # examples: " M", " D", "MM", "AM"
    if ($y -ne ' ') {
        $badUnstaged.Add($path)
        continue
    }
}

if ($badUntracked.Count -gt 0 -or $badUnstaged.Count -gt 0) {
    Write-Host ''
    Write-Host 'ERROR: Refusing commit because critical paths are not fully staged.' -ForegroundColor Red
    Write-Host ''

    if ($badUntracked.Count -gt 0) {
        Write-Host 'Untracked critical files:' -ForegroundColor Yellow
        $badUntracked |
            Sort-Object -Unique |
            ForEach-Object { Write-Host "  ?? $_" -ForegroundColor Yellow }
        Write-Host ''
    }

    if ($badUnstaged.Count -gt 0) {
        Write-Host 'Unstaged critical changes:' -ForegroundColor Yellow
        $badUnstaged |
            Sort-Object -Unique |
            ForEach-Object { Write-Host "   M $_" -ForegroundColor Yellow }
        Write-Host ''
    }

    Write-Host 'Stage or discard all critical-path changes before committing.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

exit 0
