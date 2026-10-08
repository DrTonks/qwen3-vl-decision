param(
    [switch]$Resume,
    [ValidatePattern('^[a-z][a-z0-9-]{0,63}$')]
    [string]$RunName = 'financial-eight-actions-pilot-v2'
)
$ErrorActionPreference = 'Stop'
$financialTaskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$financialPython = Join-Path $financialTaskRoot '.venv/Scripts/python.exe'
$financialCurrent = & $financialPython -m qwenlab.financial_train progress --run-name $RunName | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Unable to verify current pilot status.' }
if ($financialCurrent.worker_alive) { throw 'Pilot already running; do not launch another worker.' }
if ($financialCurrent.stage -eq 'pilot_complete') { throw 'Pilot complete; read report instead of rerunning.' }
$financialProtocol = Join-Path $financialTaskRoot "results/$RunName/protocol.json"
if ((Test-Path -LiteralPath $financialProtocol) -and -not $Resume) { throw 'Existing pilot: inspect progress and use -Resume for an interrupted run.' }
if ($Resume -and -not (Test-Path -LiteralPath $financialProtocol)) { throw 'No existing pilot to resume.' }
$financialStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$financialStdoutRelative = ".local/$RunName-$financialStamp-console.txt"
$financialStderrRelative = ".local/$RunName-$financialStamp-errors.txt"
$financialArguments = @('-u', '-m', 'qwenlab.financial_train', 'run', '--run-name', $RunName)
if ($Resume) { $financialArguments += '--resume' }
$financialWorker = Start-Process -FilePath $financialPython -ArgumentList $financialArguments -WorkingDirectory $financialTaskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $financialTaskRoot $financialStdoutRelative) -RedirectStandardError (Join-Path $financialTaskRoot $financialStderrRelative) -PassThru
@{pid=$financialWorker.Id; run_name=$RunName; started_at=(Get-Date).ToString('o'); stdout=$financialStdoutRelative; stderr=$financialStderrRelative; resume=[bool]$Resume} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $financialTaskRoot '.local/financial-eight-actions-v2/pilot-launch.json')
Write-Output "Financial pilot launched. PID: $($financialWorker.Id); run: $RunName"
Write-Output 'Progress: & .\.venv\Scripts\python.exe -m qwenlab.financial_train progress --watch'
Write-Output 'Pause safely: & .\scripts\pause-financial-pilot.ps1'
