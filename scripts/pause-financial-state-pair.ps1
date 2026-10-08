param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$statepairRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $statepairRoot 'src'
$statepairArguments = @('-m', 'qwenlab.financial_state_pair_cycle', 'pause')
if ($Probe) { $statepairArguments += '--probe' }
$statepairPython = Join-Path $statepairRoot '.venv-qwen35/Scripts/python.exe'
& $statepairPython @statepairArguments
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; safe shutdown has not been confirmed.' }
$statepairProgressArguments = @('-m', 'qwenlab.financial_state_pair_cycle', 'progress')
if ($Probe) { $statepairProgressArguments += '--probe' }
$statepairProgressText = & $statepairPython @statepairProgressArguments
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify post-pause status; safe shutdown has not been confirmed.' }
$statepairStatus = $statepairProgressText | ConvertFrom-Json
if ($statepairStatus.safe_to_shutdown -isnot [bool] -or $statepairStatus.worker_alive -isnot [bool] `
    -or $statepairStatus.safe_to_shutdown -ne $true -or $statepairStatus.worker_alive -ne $false `
    -or $statepairStatus.stage -notin @('paused', 'complete')) {
    throw 'Worker exit and saved paused/complete state are not both confirmed; safe shutdown has not been confirmed.'
}
Write-Output 'Saved paused/complete state is verified and the worker has exited. Normal shutdown is safe.'
