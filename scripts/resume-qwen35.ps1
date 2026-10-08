param([string]$RunName='financial-qwen35-v1')
& (Join-Path $PSScriptRoot 'start-qwen35.ps1') -Resume -RunName $RunName
