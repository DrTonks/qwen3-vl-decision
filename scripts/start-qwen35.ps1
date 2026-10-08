param([switch]$Resume,[string]$RunName='financial-qwen35-v1')
$ErrorActionPreference='Stop'
if ($RunName -notmatch '^financial-qwen35-[a-z0-9-]+$') { throw 'Invalid Qwen3.5 run name.' }
$qwen35Root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$qwen35Python=Join-Path $qwen35Root '.venv-qwen35/Scripts/python.exe'
$qwen35Current=& $qwen35Python -m qwenlab.qwen35_cycle progress --run-name $RunName | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify current status.' }
if ($qwen35Current.worker_alive) { throw 'Worker is already running.' }
if ($qwen35Current.stage -eq 'complete') { throw 'Experiment complete; read report.' }
$qwen35Protocol=Join-Path $qwen35Root "results/$RunName/protocol.json"
if ((Test-Path -LiteralPath $qwen35Protocol) -and -not $Resume) { throw 'Use resume for an existing interrupted experiment.' }
if ($Resume -and -not (Test-Path -LiteralPath $qwen35Protocol)) { throw 'No experiment to resume.' }
$qwen35Stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$qwen35Stdout=".local/$RunName-$qwen35Stamp-output.txt"
$qwen35Stderr=".local/$RunName-$qwen35Stamp-error.txt"
$qwen35Arguments=@('-u','-m','qwenlab.qwen35_cycle','run','--run-name',$RunName)
if ($Resume) { $qwen35Arguments+='--resume' }
$qwen35Worker=Start-Process -FilePath $qwen35Python -ArgumentList $qwen35Arguments -WorkingDirectory $qwen35Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $qwen35Root $qwen35Stdout) -RedirectStandardError (Join-Path $qwen35Root $qwen35Stderr) -PassThru
@{pid=$qwen35Worker.Id;run_name=$RunName;stdout=$qwen35Stdout;stderr=$qwen35Stderr;started_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $qwen35Root '.local/qwen35-launch.json')
Write-Output "Qwen3.5 experiment launched: $RunName; PID $($qwen35Worker.Id)"
Write-Output 'Progress: .\.venv-qwen35\Scripts\python.exe -m qwenlab.qwen35_cycle progress --watch'
