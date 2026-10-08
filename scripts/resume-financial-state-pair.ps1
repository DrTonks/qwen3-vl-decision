param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$statepairArguments = @{ Resume = $true }
if ($Probe) { $statepairArguments.Probe = $true }
& (Join-Path $PSScriptRoot 'start-financial-state-pair.ps1') @statepairArguments
