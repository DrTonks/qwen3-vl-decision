param([switch]$Resume)
$ErrorActionPreference = 'Stop'
$qwenTaskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$qwenPython = Join-Path $qwenTaskRoot '.venv/Scripts/python.exe'
$qwenRunStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$qwenOutLog = Join-Path $qwenTaskRoot ".local/support-v8-observe-$qwenRunStamp-console.txt"
$qwenErrorLog = Join-Path $qwenTaskRoot ".local/support-v8-observe-$qwenRunStamp-errors.txt"
$qwenRunArgs = @('-u', '-m', 'qwenlab.support_v8_observe', 'run')
if ($Resume) { $qwenRunArgs += '--resume' }
$qwenWorker = Start-Process -FilePath $qwenPython -ArgumentList $qwenRunArgs -WorkingDirectory $qwenTaskRoot -WindowStyle Hidden -RedirectStandardOutput $qwenOutLog -RedirectStandardError $qwenErrorLog -PassThru
@{pid=$qwenWorker.Id; started_at=(Get-Date).ToString('o'); stdout=$qwenOutLog; stderr=$qwenErrorLog; resume=[bool]$Resume} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $qwenTaskRoot '.local/support-v8-observe-launch.json')
Write-Output "V8 observation worker launched. PID: $($qwenWorker.Id)"
Write-Output 'Progress: .\.venv\Scripts\python.exe -m qwenlab.support_v8_observe progress --watch'
