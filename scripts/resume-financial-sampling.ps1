param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$samplingArguments = @{ Resume = $true }
if ($Probe) { $samplingArguments.Probe = $true }
& (Join-Path $PSScriptRoot 'start-financial-sampling.ps1') @samplingArguments
