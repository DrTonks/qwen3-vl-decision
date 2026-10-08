$ErrorActionPreference = 'Stop'
$qwenTaskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$qwenPython = Join-Path $qwenTaskRoot '.venv/Scripts/python.exe'
& $qwenPython -m qwenlab.financial_jev_reference prepare
if ($LASTEXITCODE -ne 0) { throw 'Reference preparation failed; no API calls started.' }
$qwenRunStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$qwenOutLog = Join-Path $qwenTaskRoot ".local/financial-jev-reference-$qwenRunStamp-output.txt"
$qwenErrorLog = Join-Path $qwenTaskRoot ".local/financial-jev-reference-$qwenRunStamp-error.txt"
$qwenWorker = Start-Process -FilePath $qwenPython -ArgumentList @('-u','-m','qwenlab.financial_jev_reference','run') -WorkingDirectory $qwenTaskRoot -WindowStyle Hidden -RedirectStandardOutput $qwenOutLog -RedirectStandardError $qwenErrorLog -PassThru
@{pid=$qwenWorker.Id; started_at=(Get-Date).ToString('o'); stdout=$qwenOutLog; stderr=$qwenErrorLog} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $qwenTaskRoot '.local/financial-jev-reference-launch.json')
Write-Output "Bounded Jev reference launched. PID: $($qwenWorker.Id)"
Write-Output 'Progress: .\.venv\Scripts\python.exe -m qwenlab.financial_jev_reference progress'
