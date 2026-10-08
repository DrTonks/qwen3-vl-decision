param([switch]$Resume)
$ErrorActionPreference='Stop'
$boundaryRoot=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$boundaryPython=Join-Path $boundaryRoot '.venv-qwen35/Scripts/python.exe'
$boundaryStatus=& $boundaryPython -m qwenlab.qwen35_boundary_study progress | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify current study status.' }
if ($boundaryStatus.worker_alive) { throw 'Study worker is already running.' }
if ($boundaryStatus.stage -eq 'complete') { throw 'Study complete; read its report.' }
$boundaryProtocol=Join-Path $boundaryRoot 'results/financial-qwen35-boundary-v1/protocol.json'
if ((Test-Path -LiteralPath $boundaryProtocol) -and -not $Resume) { throw 'Explicit resume required for an existing study.' }
if ($Resume -and -not (Test-Path -LiteralPath $boundaryProtocol)) { throw 'No study to resume.' }
$boundaryStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$boundaryStdout=".local/qwen35-boundary-$boundaryStamp-output.txt"
$boundaryStderr=".local/qwen35-boundary-$boundaryStamp-error.txt"
$boundaryArgs=@('-u','-m','qwenlab.qwen35_boundary_study','run')
if ($Resume) { $boundaryArgs+='--resume' }
$boundaryWorker=Start-Process -FilePath $boundaryPython -ArgumentList $boundaryArgs -WorkingDirectory $boundaryRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $boundaryRoot $boundaryStdout) -RedirectStandardError (Join-Path $boundaryRoot $boundaryStderr) -PassThru
@{pid=$boundaryWorker.Id;stdout=$boundaryStdout;stderr=$boundaryStderr;started_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $boundaryRoot '.local/qwen35-boundary-launch.json')
Write-Output "Qwen3.5 boundary study launched: PID $($boundaryWorker.Id)"
Write-Output 'Progress: .\.venv-qwen35\Scripts\python.exe -m qwenlab.qwen35_boundary_study progress --watch'
