param([string]$RunName='financial-service-v2-main')
$qwen35Root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
& (Join-Path $qwen35Root '.venv-qwen35/Scripts/python.exe') -m qwenlab.financial_service_v2_cycle pause --run-name $RunName
if ($LASTEXITCODE -ne 0) { throw 'Pause was not confirmed; inspect status before shutdown.' }
