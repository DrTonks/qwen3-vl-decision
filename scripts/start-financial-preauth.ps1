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
$preauthRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $preauthRoot 'src'
$preauthPython = Join-Path $preauthRoot '.venv-qwen35/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $preauthPython -PathType Leaf)) {
    throw 'Missing repository .venv-qwen35 Python environment.'
}
$preauthKind = if ($Probe) { 'probe' } else { 'main' }
$preauthRunName = if ($Probe) { 'financial-preauth-probe-v1' } else { 'financial-preauth-v1' }
$preauthLocal = Join-Path $preauthRoot '.local'
New-Item -ItemType Directory -Force -Path $preauthLocal | Out-Null
# One exclusive launch guard covers both namespaces, including the short period
# before a newly created worker has written its own runtime lock and state.
$preauthGuardPath = Join-Path $preauthLocal 'financial-preauth-launch.lock'
$preauthGuard = $null
try {
    $preauthGuard = [System.IO.File]::Open($preauthGuardPath,
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    throw 'Another preauth launch is in progress; inspect progress before retrying.'
}
try {
    foreach ($preauthOtherKind in @('probe', 'main')) {
        $preauthMetadataPath = Join-Path $preauthLocal "financial-preauth-$preauthOtherKind-launch.json"
        if (Test-Path -LiteralPath $preauthMetadataPath) {
            $preauthMetadata = Get-Content -LiteralPath $preauthMetadataPath -Raw | ConvertFrom-Json
            if ($preauthMetadata.pid) {
                $preauthPrior = Get-Process -Id ([int]$preauthMetadata.pid) -ErrorAction SilentlyContinue
                if ($preauthPrior -and $preauthPrior.Path -eq $preauthPython) {
                    throw "A preauth $preauthOtherKind worker is still alive; no duplicate launch."
                }
            }
        }
        $preauthProgressArguments = @('-m', 'qwenlab.financial_preauth_cycle', 'progress')
        if ($preauthOtherKind -eq 'probe') { $preauthProgressArguments += '--probe' }
        $preauthProgressText = & $preauthPython @preauthProgressArguments
        if ($LASTEXITCODE -ne 0) { throw "Cannot verify preauth $preauthOtherKind status." }
        $preauthStatus = $preauthProgressText | ConvertFrom-Json
        if ($preauthStatus.worker_alive) { throw "Preauth $preauthOtherKind is already running." }
        if ($preauthOtherKind -eq $preauthKind) { $preauthCurrent = $preauthStatus }
    }
    if ($preauthCurrent.stage -in @('complete', 'completed', 'probe_complete')) {
        throw 'This preauth run is complete; inspect its result instead of restarting.'
    }
    $preauthRunDirectory = Join-Path $preauthRoot "results/$preauthRunName"
    $preauthExists = (Test-Path -LiteralPath $preauthRunDirectory) -or ($preauthCurrent.run_exists -eq $true)
    if ($preauthExists -and -not $Resume) {
        throw 'An existing preauth run cannot be overwritten. Inspect progress and use -Resume.'
    }
    if ($Resume -and -not $preauthExists) { throw 'No existing preauth run to resume.' }
    $preauthStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $preauthNonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $preauthStdout = ".local/$preauthRunName-$preauthStamp-$preauthNonce-output.txt"
    $preauthStderr = ".local/$preauthRunName-$preauthStamp-$preauthNonce-error.txt"
    $preauthArguments = @('-u', '-m', 'qwenlab.financial_preauth_cycle', 'run')
    if ($Probe) { $preauthArguments += '--probe' }
    if ($Resume) { $preauthArguments += '--resume' }
    if ($PauseAtStep12) { $preauthArguments += @('--pause-at-step', '12') }
    $preauthWorker = Start-Process -FilePath $preauthPython -ArgumentList $preauthArguments `
        -WorkingDirectory $preauthRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $preauthRoot $preauthStdout) `
        -RedirectStandardError (Join-Path $preauthRoot $preauthStderr) -PassThru
    $preauthRecord = @{
        pid = $preauthWorker.Id
        run_name = $preauthRunName
        probe = [bool]$Probe
        resume = [bool]$Resume
        pause_at_step12 = [bool]$PauseAtStep12
        stdout = $preauthStdout
        stderr = $preauthStderr
        started_at = (Get-Date).ToString('o')
    }
    $preauthRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $preauthLocal "financial-preauth-$preauthKind-launch.json")
    # The common pointer is convenience only; per-mode records remain available.
    $preauthRecord | ConvertTo-Json | Set-Content -Encoding utf8 `
        (Join-Path $preauthLocal 'financial-preauth-launch.json')
    Write-Output "Preauth $preauthKind worker launched, PID $($preauthWorker.Id)."
    $preauthProbeFlag = if ($Probe) { ' --probe' } else { '' }
    Write-Output ".\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_preauth_cycle progress$preauthProbeFlag --watch"
    Write-Output "Logs: $preauthStdout ; $preauthStderr"
} finally {
    if ($preauthGuard) { $preauthGuard.Dispose() }
}
