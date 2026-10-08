param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$samplingRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $samplingRoot 'src'
$samplingArguments = @('-m', 'qwenlab.financial_sampling_cycle', 'pause')
if ($Probe) { $samplingArguments += '--probe' }
$samplingPython = Join-Path $samplingRoot '.venv-qwen35/Scripts/python.exe'
& $samplingPython @samplingArguments
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; safe shutdown has not been confirmed.' }
$samplingProgressArguments = @('-m', 'qwenlab.financial_sampling_cycle', 'progress')
if ($Probe) { $samplingProgressArguments += '--probe' }
$samplingProgressText = & $samplingPython @samplingProgressArguments
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify post-pause status; safe shutdown has not been confirmed.' }
$samplingStatus = $samplingProgressText | ConvertFrom-Json
if ($samplingStatus.safe_to_shutdown -isnot [bool] -or $samplingStatus.worker_alive -isnot [bool] `
    -or $samplingStatus.safe_to_shutdown -ne $true -or $samplingStatus.worker_alive -ne $false `
    -or $samplingStatus.stage -notin @('paused', 'complete')) {
    throw 'Worker exit and saved paused/complete state are not both confirmed; safe shutdown has not been confirmed.'
}
Write-Output 'Saved paused/complete state is verified and the worker has exited. Normal shutdown is safe.'
