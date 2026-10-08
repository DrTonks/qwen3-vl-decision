param(
    [switch]$Probe,
    [switch]$Resume,
    [switch]$PauseAtStep12
)
$ErrorActionPreference = 'Stop'
if ($Probe -and -not $Resume) { $PauseAtStep12 = $true }
if ($PauseAtStep12 -and (-not $Probe -or $Resume)) {
    throw '-PauseAtStep12 is only valid for a fresh -Probe launch.'
}
$statepairRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $statepairRoot 'src'
$statepairPython = Join-Path $statepairRoot '.venv-qwen35/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $statepairPython -PathType Leaf)) {
    throw 'Missing repository .venv-qwen35 Python environment.'
}
$statepairKind = if ($Probe) { 'probe' } else { 'main' }
$statepairRunName = if ($Probe) { 'financial-state-pair-probe-v1' } else { 'financial-state-pair-v1' }
$statepairLocal = Join-Path $statepairRoot '.local'
New-Item -ItemType Directory -Force -Path $statepairLocal | Out-Null
# One exclusive launch guard covers both namespaces, including the short period
# before a newly created worker has written its own runtime lock and state.
$statepairGuardPath = Join-Path $statepairLocal 'financial-state-pair-launch.lock'
$statepairGuard = $null
try {
    $statepairGuard = [System.IO.File]::Open($statepairGuardPath,
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    throw 'Another statepair launch is in progress; inspect progress before retrying.'
}
try {
    foreach ($statepairOtherKind in @('probe', 'main')) {
        $statepairMetadataPath = Join-Path $statepairLocal "financial-state-pair-$statepairOtherKind-launch.json"
        if (Test-Path -LiteralPath $statepairMetadataPath) {
            $statepairMetadata = Get-Content -LiteralPath $statepairMetadataPath -Raw | ConvertFrom-Json
            if ($statepairMetadata.pid) {
                $statepairPrior = Get-Process -Id ([int]$statepairMetadata.pid) -ErrorAction SilentlyContinue
                if ($statepairPrior -and $statepairPrior.Path -eq $statepairPython) {
                    throw "A statepair $statepairOtherKind worker is still alive; no duplicate launch."
                }
            }
        }
        $statepairProgressArguments = @('-m', 'qwenlab.financial_state_pair_cycle', 'progress')
        if ($statepairOtherKind -eq 'probe') { $statepairProgressArguments += '--probe' }
        $statepairProgressText = & $statepairPython @statepairProgressArguments
        if ($LASTEXITCODE -ne 0) { throw "Cannot verify statepair $statepairOtherKind status." }
        $statepairStatus = $statepairProgressText | ConvertFrom-Json
        if ($statepairStatus.worker_alive) { throw "Statepair $statepairOtherKind is already running." }
        if ($statepairOtherKind -eq $statepairKind) { $statepairCurrent = $statepairStatus }
    }
    if ($statepairCurrent.stage -in @('complete', 'completed', 'probe_complete')) {
        throw 'This statepair run is complete; inspect its result instead of restarting.'
    }
    $statepairRunDirectory = Join-Path $statepairRoot "results/$statepairRunName"
    $statepairExists = (Test-Path -LiteralPath $statepairRunDirectory) -or ($statepairCurrent.run_exists -eq $true)
    if ($statepairExists -and -not $Resume) {
        throw 'An existing statepair run cannot be overwritten. Inspect progress and use -Resume.'
    }
    if ($Resume -and -not $statepairExists) { throw 'No existing statepair run to resume.' }
    $statepairStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $statepairNonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $statepairStdout = ".local/$statepairRunName-$statepairStamp-$statepairNonce-output.txt"
    $statepairStderr = ".local/$statepairRunName-$statepairStamp-$statepairNonce-error.txt"
    $statepairArguments = @('-u', '-m', 'qwenlab.financial_state_pair_cycle', 'run')
    if ($Probe) { $statepairArguments += '--probe' }
    if ($Resume) { $statepairArguments += '--resume' }
    if ($PauseAtStep12) { $statepairArguments += @('--pause-at-step', '12') }
    $statepairWorker = Start-Process -FilePath $statepairPython -ArgumentList $statepairArguments `
        -WorkingDirectory $statepairRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $statepairRoot $statepairStdout) `
        -RedirectStandardError (Join-Path $statepairRoot $statepairStderr) -PassThru
    $statepairRecord = @{
        pid = $statepairWorker.Id
        run_name = $statepairRunName
        probe = [bool]$Probe
        resume = [bool]$Resume
        pause_at_step12 = [bool]$PauseAtStep12
        stdout = $statepairStdout
        stderr = $statepairStderr
        started_at = (Get-Date).ToString('o')
    }
    $statepairRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $statepairLocal "financial-state-pair-$statepairKind-launch.json")
    # The common pointer is convenience only; per-mode records remain available.
    $statepairRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $statepairLocal 'financial-state-pair-launch.json')
    Write-Output "Statepair $statepairKind worker launched, PID $($statepairWorker.Id)."
    $statepairProbeFlag = if ($Probe) { ' --probe' } else { '' }
    Write-Output ".\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_state_pair_cycle progress$statepairProbeFlag --watch"
    Write-Output "Logs: $statepairStdout ; $statepairStderr"
} finally {
    if ($statepairGuard) { $statepairGuard.Dispose() }
}
