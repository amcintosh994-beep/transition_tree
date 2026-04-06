Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$Message) {
    Write-Host ''
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host ''
    exit 1
}

function Normalize-GitPath([string]$Path) {
    return ($Path -replace '\\', '/').Trim()
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

foreach ($line in $statusLines) {
    if ($line -match '^\?\?\s+(.+)$') {
        $path = Normalize-GitPath $Matches[1]

        foreach ($prefix in $criticalPrefixes) {
            if ($path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $badUntracked.Add($path)
                break
            }
        }
    }
}

if ($badUntracked.Count -gt 0) {
    Write-Host ''
    Write-Host 'ERROR: Refusing commit because untracked critical files exist.' -ForegroundColor Red
    Write-Host ''

    $badUntracked |
        Sort-Object -Unique |
        ForEach-Object { Write-Host "  ?? $_" -ForegroundColor Yellow }

    Write-Host ''
    Write-Host 'Stage them explicitly with git add, or remove them intentionally.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

exit 0
