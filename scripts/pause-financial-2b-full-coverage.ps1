param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$full2bRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $full2bRoot 'src'
$full2bArguments = @('-m', 'qwenlab.financial_2b_full_coverage_cycle', 'pause')
if ($Probe) { $full2bArguments += '--probe' }
$full2bPython = Join-Path $full2bRoot '.venv-qwen35/Scripts/python.exe'
& $full2bPython @full2bArguments
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; safe shutdown has not been confirmed.' }
$full2bProgressArguments = @('-m', 'qwenlab.financial_2b_full_coverage_cycle', 'progress')
if ($Probe) { $full2bProgressArguments += '--probe' }
$full2bProgressText = & $full2bPython @full2bProgressArguments
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify post-pause status; safe shutdown has not been confirmed.' }
$full2bStatus = $full2bProgressText | ConvertFrom-Json
if ($full2bStatus.safe_to_shutdown -isnot [bool] -or $full2bStatus.worker_alive -isnot [bool] `
    -or $full2bStatus.safe_to_shutdown -ne $true -or $full2bStatus.worker_alive -ne $false `
    -or $full2bStatus.stage -notin @('paused', 'complete')) {
    throw 'Worker exit and saved paused/complete state are not both confirmed; safe shutdown has not been confirmed.'
}
Write-Output 'Saved paused/complete state is verified and the worker has exited. Normal shutdown is safe.'
