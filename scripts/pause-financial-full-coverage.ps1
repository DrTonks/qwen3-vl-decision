param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$fullcoverRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $fullcoverRoot 'src'
$fullcoverArguments = @('-m', 'qwenlab.financial_full_coverage_cycle', 'pause')
if ($Probe) { $fullcoverArguments += '--probe' }
$fullcoverPython = Join-Path $fullcoverRoot '.venv-qwen35/Scripts/python.exe'
& $fullcoverPython @fullcoverArguments
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; safe shutdown has not been confirmed.' }
$fullcoverProgressArguments = @('-m', 'qwenlab.financial_full_coverage_cycle', 'progress')
if ($Probe) { $fullcoverProgressArguments += '--probe' }
$fullcoverProgressText = & $fullcoverPython @fullcoverProgressArguments
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify post-pause status; safe shutdown has not been confirmed.' }
$fullcoverStatus = $fullcoverProgressText | ConvertFrom-Json
if ($fullcoverStatus.safe_to_shutdown -isnot [bool] -or $fullcoverStatus.worker_alive -isnot [bool] `
    -or $fullcoverStatus.safe_to_shutdown -ne $true -or $fullcoverStatus.worker_alive -ne $false `
    -or $fullcoverStatus.stage -notin @('paused', 'complete')) {
    throw 'Worker exit and saved paused/complete state are not both confirmed; safe shutdown has not been confirmed.'
}
Write-Output 'Saved paused/complete state is verified and the worker has exited. Normal shutdown is safe.'
