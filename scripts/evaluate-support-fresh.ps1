$ErrorActionPreference = 'Stop'
$qwenTaskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$qwenPython = Join-Path $qwenTaskRoot '.venv/Scripts/python.exe'
$qwenRunStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$qwenOutLog = Join-Path $qwenTaskRoot ".local/support-fresh-eval-$qwenRunStamp-console.txt"
$qwenErrorLog = Join-Path $qwenTaskRoot ".local/support-fresh-eval-$qwenRunStamp-errors.txt"
$qwenWorker = Start-Process -FilePath $qwenPython -ArgumentList @('-u','-m','qwenlab.support_fresh_eval','run') -WorkingDirectory $qwenTaskRoot -WindowStyle Hidden -RedirectStandardOutput $qwenOutLog -RedirectStandardError $qwenErrorLog -PassThru
@{pid=$qwenWorker.Id; started_at=(Get-Date).ToString('o'); stdout=$qwenOutLog; stderr=$qwenErrorLog} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $qwenTaskRoot '.local/support-fresh-eval-launch.json')
Write-Output "Offline candidate evaluation launched. PID: $($qwenWorker.Id)"
Write-Output 'Progress: .\.venv\Scripts\python.exe -m qwenlab.support_fresh_eval progress'
