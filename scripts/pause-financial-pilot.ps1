$ErrorActionPreference = 'Stop'
$financialTaskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
& (Join-Path $financialTaskRoot '.venv/Scripts/python.exe') -m qwenlab.financial_train pause --wait
if ($LASTEXITCODE -ne 0) { throw 'Pause NOT confirmed; inspect pilot progress and logs before shutdown.' }
