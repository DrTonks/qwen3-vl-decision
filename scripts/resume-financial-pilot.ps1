$ErrorActionPreference = 'Stop'
$financialTaskRoot = Split-Path -Parent $PSScriptRoot
$financialActivePath = Join-Path $financialTaskRoot '.local/financial-eight-actions-v2/active-run.json'
if (-not (Test-Path -LiteralPath $financialActivePath)) { throw 'No active pilot recorded.' }
$financialActive = Get-Content -LiteralPath $financialActivePath -Raw | ConvertFrom-Json
& (Join-Path $PSScriptRoot 'start-financial-pilot.ps1') -Resume -RunName $financialActive.run_name
