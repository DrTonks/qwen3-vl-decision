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
$fullcoverRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $fullcoverRoot 'src'
$fullcoverPython = Join-Path $fullcoverRoot '.venv-qwen35/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $fullcoverPython -PathType Leaf)) {
    throw 'Missing repository .venv-qwen35 Python environment.'
}
$fullcoverKind = if ($Probe) { 'probe' } else { 'main' }
$fullcoverRunName = if ($Probe) { 'financial-full-coverage-probe-v1' } else { 'financial-full-coverage-v1' }
$fullcoverLocal = Join-Path $fullcoverRoot '.local'
New-Item -ItemType Directory -Force -Path $fullcoverLocal | Out-Null
# One exclusive launch guard covers both namespaces, including the short period
# before a newly created worker has written its own runtime lock and state.
$fullcoverGuardPath = Join-Path $fullcoverLocal 'financial-full-coverage-launch.lock'
$fullcoverGuard = $null
try {
    $fullcoverGuard = [System.IO.File]::Open($fullcoverGuardPath,
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    throw 'Another fullcover launch is in progress; inspect progress before retrying.'
}
try {
    foreach ($fullcoverOtherKind in @('probe', 'main')) {
        $fullcoverMetadataPath = Join-Path $fullcoverLocal "financial-full-coverage-$fullcoverOtherKind-launch.json"
        if (Test-Path -LiteralPath $fullcoverMetadataPath) {
            $fullcoverMetadata = Get-Content -LiteralPath $fullcoverMetadataPath -Raw | ConvertFrom-Json
            if ($fullcoverMetadata.pid) {
                $fullcoverPrior = Get-Process -Id ([int]$fullcoverMetadata.pid) -ErrorAction SilentlyContinue
                if ($fullcoverPrior -and $fullcoverPrior.Path -eq $fullcoverPython) {
                    throw "A fullcover $fullcoverOtherKind worker is still alive; no duplicate launch."
                }
            }
        }
        $fullcoverProgressArguments = @('-m', 'qwenlab.financial_full_coverage_cycle', 'progress')
        if ($fullcoverOtherKind -eq 'probe') { $fullcoverProgressArguments += '--probe' }
        $fullcoverProgressText = & $fullcoverPython @fullcoverProgressArguments
        if ($LASTEXITCODE -ne 0) { throw "Cannot verify fullcover $fullcoverOtherKind status." }
        $fullcoverStatus = $fullcoverProgressText | ConvertFrom-Json
        if ($fullcoverStatus.worker_alive) { throw "Statepair $fullcoverOtherKind is already running." }
        if ($fullcoverOtherKind -eq $fullcoverKind) { $fullcoverCurrent = $fullcoverStatus }
    }
    if ($fullcoverCurrent.stage -in @('complete', 'completed', 'probe_complete')) {
        throw 'This fullcover run is complete; inspect its result instead of restarting.'
    }
    $fullcoverRunDirectory = Join-Path $fullcoverRoot "results/$fullcoverRunName"
    $fullcoverExists = (Test-Path -LiteralPath $fullcoverRunDirectory) -or ($fullcoverCurrent.run_exists -eq $true)
    if ($fullcoverExists -and -not $Resume) {
        throw 'An existing fullcover run cannot be overwritten. Inspect progress and use -Resume.'
    }
    if ($Resume -and -not $fullcoverExists) { throw 'No existing fullcover run to resume.' }
    $fullcoverStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $fullcoverNonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $fullcoverStdout = ".local/$fullcoverRunName-$fullcoverStamp-$fullcoverNonce-output.txt"
    $fullcoverStderr = ".local/$fullcoverRunName-$fullcoverStamp-$fullcoverNonce-error.txt"
    $fullcoverArguments = @('-u', '-m', 'qwenlab.financial_full_coverage_cycle', 'run')
    if ($Probe) { $fullcoverArguments += '--probe' }
    if ($Resume) { $fullcoverArguments += '--resume' }
    if ($PauseAtStep12) { $fullcoverArguments += @('--pause-at-step', '12') }
    $fullcoverWorker = Start-Process -FilePath $fullcoverPython -ArgumentList $fullcoverArguments `
        -WorkingDirectory $fullcoverRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $fullcoverRoot $fullcoverStdout) `
        -RedirectStandardError (Join-Path $fullcoverRoot $fullcoverStderr) -PassThru
    $fullcoverRecord = @{
        pid = $fullcoverWorker.Id
        run_name = $fullcoverRunName
        probe = [bool]$Probe
        resume = [bool]$Resume
        pause_at_step12 = [bool]$PauseAtStep12
        stdout = $fullcoverStdout
        stderr = $fullcoverStderr
        started_at = (Get-Date).ToString('o')
    }
    $fullcoverRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $fullcoverLocal "financial-full-coverage-$fullcoverKind-launch.json")
    # The common pointer is convenience only; per-mode records remain available.
    $fullcoverRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $fullcoverLocal 'financial-full-coverage-launch.json')
    Write-Output "Statepair $fullcoverKind worker launched, PID $($fullcoverWorker.Id)."
    $fullcoverProbeFlag = if ($Probe) { ' --probe' } else { '' }
    Write-Output ".\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_full_coverage_cycle progress$fullcoverProbeFlag --watch"
    Write-Output "Logs: $fullcoverStdout ; $fullcoverStderr"
} finally {
    if ($fullcoverGuard) { $fullcoverGuard.Dispose() }
}
