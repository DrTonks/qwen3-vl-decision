param([string]$RunName='financial-service-v2-main')
& (Join-Path $PSScriptRoot 'start-financial-service-v2.ps1') -Resume -RunName $RunName
