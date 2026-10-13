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
$full2bRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $full2bRoot 'src'
$full2bPython = Join-Path $full2bRoot '.venv-qwen35/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $full2bPython -PathType Leaf)) {
    throw 'Missing repository .venv-qwen35 Python environment.'
}
$full2bKind = if ($Probe) { 'probe' } else { 'main' }
$full2bRunName = if ($Probe) { 'financial-2b-full-coverage-probe-v1' } else { 'financial-2b-full-coverage-v1' }
$full2bLocal = Join-Path $full2bRoot '.local'
New-Item -ItemType Directory -Force -Path $full2bLocal | Out-Null
# One exclusive launch guard covers both namespaces, including the short period
# before a newly created worker has written its own runtime lock and state.
$full2bGuardPath = Join-Path $full2bLocal 'financial-2b-full-coverage-launch.lock'
$full2bGuard = $null
try {
    $full2bGuard = [System.IO.File]::Open($full2bGuardPath,
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    throw 'Another full2b launch is in progress; inspect progress before retrying.'
}
try {
    foreach ($full2bOtherKind in @('probe', 'main')) {
        $full2bMetadataPath = Join-Path $full2bLocal "financial-2b-full-coverage-$full2bOtherKind-launch.json"
        if (Test-Path -LiteralPath $full2bMetadataPath) {
            $full2bMetadata = Get-Content -LiteralPath $full2bMetadataPath -Raw | ConvertFrom-Json
            if ($full2bMetadata.pid) {
                $full2bPrior = Get-Process -Id ([int]$full2bMetadata.pid) -ErrorAction SilentlyContinue
                if ($full2bPrior -and $full2bPrior.Path -eq $full2bPython) {
                    throw "A full2b $full2bOtherKind worker is still alive; no duplicate launch."
                }
            }
        }
        $full2bProgressArguments = @('-m', 'qwenlab.financial_2b_full_coverage_cycle', 'progress')
        if ($full2bOtherKind -eq 'probe') { $full2bProgressArguments += '--probe' }
        $full2bProgressText = & $full2bPython @full2bProgressArguments
        if ($LASTEXITCODE -ne 0) { throw "Cannot verify full2b $full2bOtherKind status." }
        $full2bStatus = $full2bProgressText | ConvertFrom-Json
        if ($full2bStatus.worker_alive) { throw "Qwen2B $full2bOtherKind is already running." }
        if ($full2bOtherKind -eq $full2bKind) { $full2bCurrent = $full2bStatus }
    }
    if ($full2bCurrent.stage -in @('complete', 'completed', 'probe_complete')) {
        throw 'This full2b run is complete; inspect its result instead of restarting.'
    }
    $full2bRunDirectory = Join-Path $full2bRoot "results/$full2bRunName"
    $full2bExists = (Test-Path -LiteralPath $full2bRunDirectory) -or ($full2bCurrent.run_exists -eq $true)
    if ($full2bExists -and -not $Resume) {
        throw 'An existing full2b run cannot be overwritten. Inspect progress and use -Resume.'
    }
    if ($Resume -and -not $full2bExists) { throw 'No existing full2b run to resume.' }
    $full2bStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $full2bNonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $full2bStdout = ".local/$full2bRunName-$full2bStamp-$full2bNonce-output.txt"
    $full2bStderr = ".local/$full2bRunName-$full2bStamp-$full2bNonce-error.txt"
    $full2bArguments = @('-u', '-m', 'qwenlab.financial_2b_full_coverage_cycle', 'run')
    if ($Probe) { $full2bArguments += '--probe' }
    if ($Resume) { $full2bArguments += '--resume' }
    if ($PauseAtStep12) { $full2bArguments += @('--pause-at-step', '12') }
    $full2bWorker = Start-Process -FilePath $full2bPython -ArgumentList $full2bArguments `
        -WorkingDirectory $full2bRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $full2bRoot $full2bStdout) `
        -RedirectStandardError (Join-Path $full2bRoot $full2bStderr) -PassThru
    $full2bRecord = @{
        pid = $full2bWorker.Id
        run_name = $full2bRunName
        probe = [bool]$Probe
        resume = [bool]$Resume
        pause_at_step12 = [bool]$PauseAtStep12
        stdout = $full2bStdout
        stderr = $full2bStderr
        started_at = (Get-Date).ToString('o')
    }
    $full2bRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $full2bLocal "financial-2b-full-coverage-$full2bKind-launch.json")
    # The common pointer is convenience only; per-mode records remain available.
    $full2bRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $full2bLocal 'financial-2b-full-coverage-launch.json')
    Write-Output "Qwen2B $full2bKind worker launched, PID $($full2bWorker.Id)."
    $full2bProbeFlag = if ($Probe) { ' --probe' } else { '' }
    Write-Output ".\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_2b_full_coverage_cycle progress$full2bProbeFlag --watch"
    Write-Output "Logs: $full2bStdout ; $full2bStderr"
} finally {
    if ($full2bGuard) { $full2bGuard.Dispose() }
}
