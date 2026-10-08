param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$preauthArguments = @{ Resume = $true }
if ($Probe) { $preauthArguments.Probe = $true }
& (Join-Path $PSScriptRoot 'start-financial-preauth.ps1') @preauthArguments
