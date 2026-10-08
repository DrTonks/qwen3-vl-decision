param(
    [switch]$Probe,
    [switch]$Resume,
    [switch]$PauseAtStep12
)
$ErrorActionPreference = 'Stop'
if ($PauseAtStep12 -and (-not $Probe -or $Resume)) {
    throw '-PauseAtStep12 is only valid for a fresh -Probe launch.'
}
$samplingRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $samplingRoot 'src'
$samplingPython = Join-Path $samplingRoot '.venv-qwen35/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $samplingPython -PathType Leaf)) {
    throw 'Missing repository .venv-qwen35 Python environment.'
}
$samplingKind = if ($Probe) { 'probe' } else { 'main' }
$samplingRunName = if ($Probe) { 'financial-sampling-probe-v1' } else { 'financial-sampling-v1' }
$samplingLocal = Join-Path $samplingRoot '.local'
New-Item -ItemType Directory -Force -Path $samplingLocal | Out-Null
# One exclusive launch guard covers both namespaces, including the short period
# before a newly created worker has written its own runtime lock and state.
$samplingGuardPath = Join-Path $samplingLocal 'financial-sampling-launch.lock'
$samplingGuard = $null
try {
    $samplingGuard = [System.IO.File]::Open($samplingGuardPath,
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    throw 'Another sampling launch is in progress; inspect progress before retrying.'
}
try {
    foreach ($samplingOtherKind in @('probe', 'main')) {
        $samplingMetadataPath = Join-Path $samplingLocal "financial-sampling-$samplingOtherKind-launch.json"
        if (Test-Path -LiteralPath $samplingMetadataPath) {
            $samplingMetadata = Get-Content -LiteralPath $samplingMetadataPath -Raw | ConvertFrom-Json
            if ($samplingMetadata.pid) {
                $samplingPrior = Get-Process -Id ([int]$samplingMetadata.pid) -ErrorAction SilentlyContinue
                if ($samplingPrior -and $samplingPrior.Path -eq $samplingPython) {
                    throw "A sampling $samplingOtherKind worker is still alive; no duplicate launch."
                }
            }
        }
        $samplingProgressArguments = @('-m', 'qwenlab.financial_sampling_cycle', 'progress')
        if ($samplingOtherKind -eq 'probe') { $samplingProgressArguments += '--probe' }
        $samplingProgressText = & $samplingPython @samplingProgressArguments
        if ($LASTEXITCODE -ne 0) { throw "Cannot verify sampling $samplingOtherKind status." }
        $samplingStatus = $samplingProgressText | ConvertFrom-Json
        if ($samplingStatus.worker_alive) { throw "Sampling $samplingOtherKind is already running." }
        if ($samplingOtherKind -eq $samplingKind) { $samplingCurrent = $samplingStatus }
    }
    if ($samplingCurrent.stage -in @('complete', 'completed', 'probe_complete')) {
        throw 'This sampling run is complete; inspect its result instead of restarting.'
    }
    $samplingRunDirectory = Join-Path $samplingRoot "results/$samplingRunName"
    $samplingExists = (Test-Path -LiteralPath $samplingRunDirectory) -or ($samplingCurrent.run_exists -eq $true)
    if ($samplingExists -and -not $Resume) {
        throw 'An existing sampling run cannot be overwritten. Inspect progress and use -Resume.'
    }
    if ($Resume -and -not $samplingExists) { throw 'No existing sampling run to resume.' }
    $samplingStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $samplingNonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $samplingStdout = ".local/$samplingRunName-$samplingStamp-$samplingNonce-output.txt"
    $samplingStderr = ".local/$samplingRunName-$samplingStamp-$samplingNonce-error.txt"
    $samplingArguments = @('-u', '-m', 'qwenlab.financial_sampling_cycle', 'run')
    if ($Probe) { $samplingArguments += '--probe' }
    if ($Resume) { $samplingArguments += '--resume' }
    if ($PauseAtStep12) { $samplingArguments += @('--pause-at-step', '12') }
    $samplingWorker = Start-Process -FilePath $samplingPython -ArgumentList $samplingArguments `
        -WorkingDirectory $samplingRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $samplingRoot $samplingStdout) `
        -RedirectStandardError (Join-Path $samplingRoot $samplingStderr) -PassThru
    $samplingRecord = @{
        pid = $samplingWorker.Id
        run_name = $samplingRunName
        probe = [bool]$Probe
        resume = [bool]$Resume
        pause_at_step12 = [bool]$PauseAtStep12
        stdout = $samplingStdout
        stderr = $samplingStderr
        started_at = (Get-Date).ToString('o')
    }
    $samplingRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $samplingLocal "financial-sampling-$samplingKind-launch.json")
    # The common pointer is convenience only; per-mode records remain available.
    $samplingRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $samplingLocal 'financial-sampling-launch.json')
    Write-Output "Sampling $samplingKind worker launched, PID $($samplingWorker.Id)."
    $samplingProbeFlag = if ($Probe) { ' --probe' } else { '' }
    Write-Output ".\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_sampling_cycle progress$samplingProbeFlag --watch"
    Write-Output "Logs: $samplingStdout ; $samplingStderr"
} finally {
    if ($samplingGuard) { $samplingGuard.Dispose() }
}
