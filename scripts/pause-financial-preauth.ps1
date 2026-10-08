param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$preauthRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $preauthRoot 'src'
$preauthArguments = @('-m', 'qwenlab.financial_preauth_cycle', 'pause')
if ($Probe) { $preauthArguments += '--probe' }
$preauthPython = Join-Path $preauthRoot '.venv-qwen35/Scripts/python.exe'
& $preauthPython @preauthArguments
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; safe shutdown has not been confirmed.' }
$preauthProgressArguments = @('-m', 'qwenlab.financial_preauth_cycle', 'progress')
if ($Probe) { $preauthProgressArguments += '--probe' }
$preauthProgressText = & $preauthPython @preauthProgressArguments
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify post-pause status; safe shutdown has not been confirmed.' }
$preauthStatus = $preauthProgressText | ConvertFrom-Json
if ($preauthStatus.safe_to_shutdown -isnot [bool] -or $preauthStatus.worker_alive -isnot [bool] `
    -or $preauthStatus.safe_to_shutdown -ne $true -or $preauthStatus.worker_alive -ne $false `
    -or $preauthStatus.stage -notin @('paused', 'complete')) {
    throw 'Worker exit and saved paused/complete state are not both confirmed; safe shutdown has not been confirmed.'
}
Write-Output 'Saved paused/complete state is verified and the worker has exited. Normal shutdown is safe.'
